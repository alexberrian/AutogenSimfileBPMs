import csv
import vamp
import soundfile as sf
import argparse
import pathlib
import sys
import numpy as np
from warnings import warn
from typing import List


class SingleBeatTimestampData(object):
    def __init__(self, timestamp: float = None, label: str = None):
        self.timestamp = timestamp
        self.label = label

    def set_timestamp(self, timestamp: float):
        if timestamp >= 0.:
            self.timestamp = timestamp
        else:
            raise ValueError("Invalid timestamp {} (is it negative?)".format(timestamp))

    def set_label(self, label: str):
        if label in {"1", "2", "3", "4"}:
            self.label = label
        else:
            raise ValueError("Invalid beat label {}, should be '1', '2', '3', '4'".format(label))


class BeatsTimestampData(object):
    VALID_TIMESTAMP_TYPES = ['samples', 'seconds']
    TIMESTAMP_UNSET_TYPE = 'unset'

    def __init__(self, data: List[SingleBeatTimestampData] = None, timestamp_type: str = None):
        self.beats = data if data is not None else []
        self.timestamp_type = timestamp_type if timestamp_type is not None else self.TIMESTAMP_UNSET_TYPE

    def set_data(self, data: List[SingleBeatTimestampData]):
        self.beats = data

    def set_timestamp_type(self, timestamp_type: str):
        if timestamp_type in self.VALID_TIMESTAMP_TYPES:
            self.timestamp_type = timestamp_type
        elif timestamp_type == self.TIMESTAMP_UNSET_TYPE:
            raise ValueError("Cannot set timestamp_type to {} here, "
                             "it must be one of the following options: "
                             "'{}'".format(self.TIMESTAMP_UNSET_TYPE, "', '".join(self.VALID_TIMESTAMP_TYPES) ))
        else:
            raise ValueError("Invalid timestamp type '{}'".format(timestamp_type))


class BPMsData(object):
    def __init__(self, bpms: List[float] = None, beat_markers: List[int] = None):
        self.bpms = bpms if bpms is not None else []
        self.beat_markers = beat_markers if beat_markers is not None else []

    def set_bpms(self, bpms: List[float]):
        self.bpms = bpms

    def set_beat_markers(self, beat_markers: List[int]):
        self.beat_markers = beat_markers


class AudioBeatsToBPMs(object):
    SEC_DIFF_TOLERANCE = 1e-8
    MIN_FIRST_BEAT_SEC_FOR_WARN = 10.
    PLUGIN_IDENTIFIER = "qm-vamp-plugins:qm-barbeattracker"  # https://vamp-plugins.org/plugin-doc/qm-vamp-plugins.html

    def __init__(self, audio: np.ndarray = None, sampling_rate: int = None, input_audio_path=None,
                 input_beats_csv_path=None,
                 input_simfile_path=None, output_simfile_path=None, output_txt_path=None,
                 output_beat_markers_bpms_csv_path=None, overwrite_input_simfile=False,
                 alternate_plugin_identifier=None):
        self.audio = audio
        self.sampling_rate = sampling_rate
        self.input_audio_path = pathlib.Path(input_audio_path) if input_audio_path is not None else None
        self.input_beats_csv_path = pathlib.Path(input_beats_csv_path) if input_beats_csv_path is not None else None
        self.input_simfile_path = pathlib.Path(input_simfile_path) if input_simfile_path is not None else None
        self.output_simfile_path = pathlib.Path(output_simfile_path) if output_simfile_path is not None else None
        self.output_txt_path = pathlib.Path(output_txt_path) if output_txt_path is not None else None
        self.output_beat_markers_bpms_csv_path = pathlib.Path(output_beat_markers_bpms_csv_path) \
            if output_beat_markers_bpms_csv_path is not None else None
        self.overwrite_input_simfile = overwrite_input_simfile
        self.plugin_identifier = alternate_plugin_identifier if alternate_plugin_identifier is not None else \
                                 self.PLUGIN_IDENTIFIER
        self.beats_timestamp_data = BeatsTimestampData()
        self.bpms_data = BPMsData()

        if self.input_audio_path is not None:
            self.load_audio_from_path(self.input_audio_path)

    def _verify_inputs(self):
        if self.audio is not None and self.input_audio_path is not None:
            raise ValueError("Ambiguous input, cannot pass both audio and input audio path in initialization")
        if self.overwrite_input_simfile:
            if self.input_simfile_path is None:
                raise ValueError("Cannot specify --overwrite_input_simfile without --input_simfile_path")
            elif self.output_simfile_path is not None and self.output_simfile_path != self.input_simfile_path:
                raise ValueError("Ambiguous input: cannot specify both --overwrite_input_simfile and "
                                 "--output_simfile_path, unless the input simfile path is the same as the output")
            else:
                resolved = False
                while not resolved:
                    user_response = input("WARNING: Are you sure you want to overwrite the "
                                          "existing #OFFSET and #BPMS fields in the input simfile {}? "
                                          "(y/n) ".format(self.input_simfile_path))
                    if user_response.lower() in ["y", "yes"]:
                        resolved = True
                        self.output_simfile_path = self.input_simfile_path
                    elif user_response.lower() in ["n", "no"]:
                        print("Stopping program.")
                        sys.exit()
        else:  # If --overwrite_input_simfile is not specified
            if self.output_simfile_path is not None:
                if self.input_simfile_path is None:
                    raise ValueError("Cannot specify --output_simfile_path without --input_simfile_path")
                elif self.output_simfile_path.exists():
                    resolved = False
                    while not resolved:
                        user_response = input("WARNING: The output simfile path {} already exists.  "
                                              "Are you sure you want to overwrite the "
                                              "existing #OFFSET and #BPMS fields in this simfile? "
                                              "(y/n) ".format(self.output_simfile_path))
                        if user_response.lower() in ["y", "yes"]:
                            resolved = True
                        elif user_response.lower() in ["n", "no"]:
                            print("Stopping program.")
                            sys.exit()

    def read_input_csv(self):
        timestamp_type: str = 'unset'
        with open(self.input_beats_csv_path, "r") as infile:
            read_data = []
            csvread = csv.reader(infile)
            row = next(csvread)
            first_beat_time = float(row[0])
            if self.sampling_rate is None:  # TODO: THIS NEEDS TO BE CHANGED because audio may be read in too!
                timestamp_type = 'samples'
                if first_beat_time > self.MIN_FIRST_BEAT_SEC_FOR_WARN:
                    warn("WARNING: Your first timestamp {} from the input CSV is at greater than {} seconds. "
                         "Are you sure the units are in seconds and not samples? "
                         "If they are samples, please specify the sampling rate using the flag "
                         "--samples; for instance --samples 48000, or "
                         "otherwise you will get very inaccurate BPMs.".format(first_beat_time,
                                                                               self.MIN_FIRST_BEAT_SEC_FOR_WARN))
            else:
                if int(first_beat_time) != first_beat_time:
                    warn("The first beat time {} is detected to be in units of seconds, but you specified the "
                         "sampling rate, which will not be used in the computation.")
                    timestamp_type = 'seconds'
            read_data.append(row)
            for row in csvread:
                read_data.append(row)
            self.beats_timestamp_data = self._convert_beats_data_from_lists_to_BeatsTimestampData(read_data,
                                                                                                  timestamp_type)

    def load_audio_from_path(self, input_audio_path=None):
        if input_audio_path is not None:
            self.input_audio_path = input_audio_path
        elif self.input_audio_path is None:
            raise ValueError("No input audio path has been specified!")
        elif not self.input_audio_path.is_file():
            raise ValueError("Input audio path {} isn't a file".format(self.input_audio_path))

        self.audio, self.sampling_rate = sf.read(self.input_audio_path, always_2d=True)
        self.audio = self.audio.T  # [channels, data]
        print("Audio loaded from {}".format(self.input_audio_path))

    def calculate_beats_from_vamp_plugin(self, return_beats=False):
        if self.audio is None:
            raise ValueError("No audio loaded!")
        data = [x for x in vamp.process_audio(self.audio, self.sampling_rate, self.plugin_identifier)]
        timestamp_type = 'seconds'
        self.beats_timestamp_data = self._convert_beats_data_from_dicts_to_BeatsTimestampData(data, timestamp_type)

        if return_beats:
            return self.beats_timestamp_data

    def convert_timestamps_to_bpms(self):
        if len(self.beats_timestamp_data.beats) == 0:
            try:
                self.calculate_beats_from_vamp_plugin()
            except ValueError:
                raise ValueError("Beats data is empty; "
                                 "did you load an audio file or an input CSV of beat information?")
        else:
            if self.beats_timestamp_data.timestamp_type == 'samples':
                first_beat_samples = int(self.beats_timestamp_data.beats[0].timestamp)
                self.offset = - first_beat_samples / self.sampling_rate
                beat_marker = 0
                last_beat_diff = 0
                for beat in self.beats_timestamp_data.beats[1:]:
                    second_beat_samples = int(beat.timestamp)
                    beat_diff = second_beat_samples - first_beat_samples
                    if last_beat_diff != beat_diff:
                        bpm = self.sampling_rate / beat_diff * 60  # CHANGE
                        self.bpms_data.bpms.append(bpm)
                        self.bpms_data.beat_markers.append(beat_marker)
                    first_beat_samples = second_beat_samples
                    beat_marker += 1
                    last_beat_diff = beat_diff
            elif self.beats_timestamp_data.timestamp_type == 'seconds':
                beat_marker = 0
                last_beat_diff = 0
                first_beat_sec = float(self.beats_timestamp_data.beats[0].timestamp)
                self.offset = - first_beat_sec
                for beat in self.beats_timestamp_data.beats[1:]:
                    second_beat_sec = float(beat.timestamp)
                    beat_diff = second_beat_sec - first_beat_sec
                    if abs(last_beat_diff - beat_diff) > self.SEC_DIFF_TOLERANCE:
                        bpm = 60 / beat_diff
                        self.bpms_data.bpms.append(bpm)
                        self.bpms_data.beat_markers.append(beat_marker)
                    first_beat_sec = second_beat_sec
                    beat_marker += 1
                    last_beat_diff = beat_diff
            else:
                raise ValueError("Invalid timestamp_type: {}".format(self.beats_timestamp_data.timestamp_type))

    @staticmethod
    def _convert_beats_data_from_dicts_to_BeatsTimestampData(beats_dicts: List[dict], timestamp_type: str):
        return BeatsTimestampData([SingleBeatTimestampData(timestamp=beat_dict['timestamp'], label=beat_dict['label'])
                                   for beat_dict in beats_dicts], timestamp_type)

    @staticmethod
    def _convert_beats_data_from_lists_to_BeatsTimestampData(beats_lists: List, timestamp_type: str):
        return BeatsTimestampData([SingleBeatTimestampData(timestamp=beat_list[0], label=beat_list[1])
                                   for beat_list in beats_lists], timestamp_type)

    @staticmethod
    def _convert_beats_data_from_dicts_to_lists(beats_dicts: List[dict]):
        return [[beat_dict['timestamp'], beat_dict['label']] for beat_dict in beats_dicts]

    @staticmethod
    def _convert_beats_data_from_lists_to_dicts(beats_list: List):
        return [{'timestamp': beat_list[0], 'label': beat_list[1]} for beat_list in beats_list]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_audio_path", help="Path to input audio file")
    parser.add_argument("--samples", help="Use this option if the input CSV's beat locations are given in samples, "
                                          "and specify the sampling rate in Hz.", type=int)
    parser.add_argument("--input_simfile_path", help="(OPTIONAL) Path to input .sm or .ssc file for the song whose "
                                                     "BPMS and OFFSET you are finding")
    parser.add_argument("--output_simfile_path", help="(OPTIONAL) Path to output .sm or .ssc file where the generated "
                                                      "#BPMS and #OFFSET lines will be written")
    parser.add_argument("--input_beats_csv_path", help="(OPTIONAL) Path to input CSV containing beat markers. "
                                                       "Use this if you have generated beat markers from the "
                                                       "audio separately (using Sonic Visualiser for example)")
    parser.add_argument("--output_txt_path", help="(OPTIONAL) Output path to text file where only the "
                                                  "#BPMS and #OFFSET lines will be written")
    parser.add_argument("--output_beat_markers_bpms_csv_path",
                        help="(OPTIONAL) Path to output CSV with the beat markers and BPMs")
    parser.add_argument("--overwrite_input_simfile", help="(OPTIONAL) Use this option to overwrite the "
                                                          "existing input simfile",
                        action="store_true")
    args = parser.parse_args()

    atbpm = AudioBeatsToBPMs(input_audio_path=args.input_audio_path)
    atbpm.calculate_beats_from_vamp_plugin()


if __name__ == "__main__":
    main()
