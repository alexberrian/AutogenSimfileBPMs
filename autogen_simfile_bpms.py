import csv
import vamp
import soundfile as sf
import argparse
import pathlib
import sys
import numpy as np
from warnings import warn
from typing import List
import simfile


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
    RUN_FROM_CANDIDATES = {"audio_input", "audio_path", "beats_path"}

    def __init__(self, audio: np.ndarray = None, sampling_rate: int = None, input_audio_path=None,
                 input_beats_path=None, input_beats_sampling_rate=0,
                 input_simfile_path=None, output_simfile_path=None, output_txt_path=None,
                 output_beat_markers_bpms_csv_path=None, overwrite_input_simfile=False,
                 alternate_plugin_identifier=None):
        self.audio = audio
        self.sampling_rate = sampling_rate
        self.input_audio_path = pathlib.Path(input_audio_path) if input_audio_path is not None else None
        self.input_beats_path = pathlib.Path(input_beats_path) if input_beats_path is not None else None
        if input_beats_sampling_rate:
            self.sampling_rate = input_beats_sampling_rate
            self.input_beats_in_samples = True
        else:
            self.input_beats_in_samples = False
        self.input_simfile_path = pathlib.Path(input_simfile_path) if input_simfile_path is not None else None
        self.output_simfile_path = pathlib.Path(output_simfile_path) if output_simfile_path is not None else None
        self.output_txt_path = pathlib.Path(output_txt_path) if output_txt_path is not None else None
        self.output_beat_markers_bpms_csv_path = pathlib.Path(output_beat_markers_bpms_csv_path) \
            if output_beat_markers_bpms_csv_path is not None else None
        self.overwrite_input_simfile = overwrite_input_simfile
        self.plugin_identifier = alternate_plugin_identifier if alternate_plugin_identifier is not None else \
                                 self.PLUGIN_IDENTIFIER
        self.run_from = None
        self._verify_initialization_and_set_running_order()

        self.beats_timestamp_data = BeatsTimestampData()
        self.bpms_data = BPMsData()
        self.offset = 0.
        self.simfile_bpms = None

    def _verify_initialization_and_set_running_order(self):
        # Override order: Input beats path > input audio array > input audio path
        if self.input_audio_path is not None:
            if not self.input_audio_path.is_file():
                raise ValueError("{} is not a valid file path for the input audio".format(self.input_audio_path))
        if self.input_beats_path is not None:
            self.run_from = "beats_path"
            if not self.input_beats_path.is_file():
                raise ValueError("{} is not a valid file path for the input beats CSV".format(self.input_beats_path))
            if self.input_audio_path is not None:
                warn("WARNING: Will not load audio from {} because you have specified an existing file path {} "
                     "from which the beat timestamps will be extracted.".format(self.input_audio_path,
                                                                                self.input_beats_path))
            if self.audio is not None:
                warn("WARNING: Will not compute beat timestamps from the input audio, because you have specified "
                     "an existing file path {} from which the beat timestamps "
                     "will be extracted.".format(self.input_beats_path))
        else:  # No input CSV of beats
            if self.audio is not None and self.input_audio_path is not None:
                self.run_from = "audio_input"
                warn("WARNING: Will not load audio from {} because you have passed an audio array in the "
                     "initialization of this object.".format(self.input_audio_path))
            elif self.audio is None and self.input_audio_path is not None:
                self.run_from = "audio_path"
            else:
                raise ValueError("You must do one of the following things: initialize the audio array, "
                                 "set the input audio path, or set the input beats path.")
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
        if self.run_from not in self.RUN_FROM_CANDIDATES:
            raise ValueError("Invalid run configuration {}, must be one of the options "
                             "'{}'".format(self.run_from, "', '".join(self.RUN_FROM_CANDIDATES)))

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

    def calculate_beat_timestamps_from_vamp_plugin(self, return_beats=False):
        if self.audio is None:
            raise ValueError("No audio loaded!")
        data = [x for x in vamp.process_audio(self.audio, self.sampling_rate, self.plugin_identifier)]
        timestamp_type = 'seconds'
        self.beats_timestamp_data = self._convert_beats_data_from_dicts_to_BeatsTimestampData(data, timestamp_type)

        if return_beats:
            return self.beats_timestamp_data

    def load_beat_timestamps_from_path(self):
        if self.input_beats_path is None:
            raise ValueError("No input beats path specified!")
        elif not self.input_beats_path.is_file():
            raise ValueError("Invalid path to input beats file {}".format(self.input_beats_path))
        else:
            timestamp_type: str = 'unset'
            with open(self.input_beats_path, "r") as infile:
                read_data = []
                csvread = csv.reader(infile)
                row = next(csvread)
                first_beat_time = float(row[0])
                if not self.input_beats_in_samples:
                    timestamp_type = 'seconds'
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
                        self.input_beats_in_samples = False
                    else:
                        timestamp_type = 'samples'
                read_data.append(row)
                for row in csvread:
                    read_data.append(row)
                self.beats_timestamp_data = self._convert_beats_data_from_lists_to_BeatsTimestampData(read_data,
                                                                                                      timestamp_type)

    def convert_timestamps_to_bpms(self):
        if len(self.beats_timestamp_data.beats) == 0:
            try:
                self.calculate_beat_timestamps_from_vamp_plugin()
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

    def convert_bpms_to_simfile_format(self):
        beats_bpms = ["{}={}\n".format(beat_marker, bpm) for beat_marker, bpm in
                      zip(self.bpms_data.beat_markers, self.bpms_data.bpms)]
        self.simfile_bpms = ",".join(beats_bpms)

    def write_output_csv(self):
        with open(self.output_beat_markers_bpms_csv_path, "w") as outfile:
            csvwrite = csv.writer(outfile)
            for beat_marker, bpm in zip(self.bpms_data.beat_markers, self.bpms_data.bpms):
                csvwrite.writerow([beat_marker, bpm])

    def write_output_txt_oneline(self):
        """
        Write out a text file that only contains the two lines that you're gonna
        stick into the Stepmania .sm file (or .ssc).

        Sample output:
        #OFFSET:-0.0234;
        #BPMS:0.000=132.000,149.000=66.000,173.000=132.000;

        :return:
        """

        stepmania_offset_out = "#OFFSET:{};\n".format(self.offset)
        if self.simfile_bpms is None:
            self.convert_bpms_to_simfile_format()
        stepmania_bpms_out = "#BPMS:" + self.simfile_bpms + ";"

        with open(self.output_txt_path, "w") as outfile:
            outfile.write(stepmania_offset_out)
            outfile.write(stepmania_bpms_out)

    def write_output_simfile(self):
        sm = simfile.open(str(self.input_simfile_path))
        sm.offset = self.offset
        if self.simfile_bpms is None:
            self.convert_bpms_to_simfile_format()
        sm.bpms = self.simfile_bpms
        with open(self.output_simfile_path, 'w', encoding='utf-8') as outfile:
            sm.serialize(outfile)

    def run(self):
        if self.run_from == "audio_path":
            self.load_audio_from_path()
            self.calculate_beat_timestamps_from_vamp_plugin()
        elif self.run_from == "audio_input":
            self.calculate_beat_timestamps_from_vamp_plugin()
        elif self.run_from == "beats_path":
            self.load_beat_timestamps_from_path()
        elif self.run_from in self.RUN_FROM_CANDIDATES:
            raise ValueError("Unsupported run_from option {}".format(self.run_from))
        else:
            raise ValueError("Invalid run configuration {}, must be one of the options "
                             "'{}'".format(self.run_from, "', '".join(self.RUN_FROM_CANDIDATES)))
        self.convert_timestamps_to_bpms()
        if self.output_simfile_path is not None:
            self.write_output_simfile()
        if self.output_txt_path is not None:
            self.write_output_txt_oneline()
        if self.output_beat_markers_bpms_csv_path is not None:
            self.write_output_csv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_audio_path", help="Path to input audio file")
    parser.add_argument("--input_beats_path", help="Path to input CSV file containing beat markers. "
                                                   "Use this if you have generated beat markers from the "
                                                   "audio separately (using Sonic Visualiser for example)")
    parser.add_argument("--input_beats_sampling_rate", help="Use this option if the input CSV's beat locations "
                                                            "are given in samples, "
                                                            "and specify the sampling rate in Hz.", type=int)
    parser.add_argument("--input_simfile_path", help="(OPTIONAL) Path to input .sm or .ssc file for the song whose "
                                                     "BPMS and OFFSET you are finding")
    parser.add_argument("--output_simfile_path", help="(OPTIONAL) Path to output .sm or .ssc file where the generated "
                                                      "#BPMS and #OFFSET lines will be written")
    parser.add_argument("--output_txt_path", help="(OPTIONAL) Output path to text file where only the "
                                                  "#BPMS and #OFFSET lines will be written")
    parser.add_argument("--output_beat_markers_bpms_csv_path",
                        help="(OPTIONAL) Path to output CSV with the beat markers and BPMs")
    parser.add_argument("--overwrite_input_simfile", help="(OPTIONAL) Use this option to overwrite the "
                                                          "existing input simfile",
                        action="store_true")
    parser.add_argument("--alternate_plugin_identifier", help="(OPTIONAL) Use an alternate plugin, for example"
                                                              " 'qm-vamp-plugins:qm-tempotracker'; note, "
                                                              "the detected beats must be provided in the same format "
                                                              "as the default plugin used here or there will be an "
                                                              "error.  "
                                                              "Default plugin "
                                                              "used is {}".format(AudioBeatsToBPMs.PLUGIN_IDENTIFIER))
    args = parser.parse_args()

    if args.input_beats_sampling_rate is not None:
        pass

    atbpm = AudioBeatsToBPMs(input_audio_path=args.input_audio_path, input_beats_path=args.input_beats_path,
                             input_beats_sampling_rate=args.input_beats_sampling_rate,
                             input_simfile_path=args.input_simfile_path, output_simfile_path=args.output_simfile_path,
                             output_txt_path=args.output_txt_path,
                             output_beat_markers_bpms_csv_path=args.output_beat_markers_bpms_csv_path,
                             overwrite_input_simfile=args.overwrite_input_simfile,
                             alternate_plugin_identifier=args.alternate_plugin_identifier)
    atbpm.run()


if __name__ == "__main__":
    main()
