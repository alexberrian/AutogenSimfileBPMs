import vamp
import beats_to_bpms
import soundfile as sf
import argparse
import pathlib
import sys
import numpy as np


class AudioToBPMs(object):
    PLUGIN_IDENTIFIER = "qm-vamp-plugins:qm-barbeattracker"  # https://vamp-plugins.org/plugin-doc/qm-vamp-plugins.html

    def __init__(self, audio: np.ndarray = None, sampling_rate: int = None, input_audio_path=None,
                 input_simfile_path=None, output_simfile_path=None, output_txt_path=None,
                 output_beat_markers_bpms_csv_path=None, overwrite_input_simfile=False,
                 alternate_plugin_identifier=None):
        self.audio = audio
        self.sampling_rate = sampling_rate
        self.input_audio_path = pathlib.Path(input_audio_path) if input_audio_path is not None else None
        self.input_simfile_path = pathlib.Path(input_simfile_path) if input_simfile_path is not None else None
        self.output_simfile_path = pathlib.Path(output_simfile_path) if output_simfile_path is not None else None
        self.output_txt_path = pathlib.Path(output_txt_path) if output_txt_path is not None else None
        self.output_beat_markers_bpms_csv_path = pathlib.Path(output_beat_markers_bpms_csv_path) \
            if output_beat_markers_bpms_csv_path is not None else None
        self.overwrite_input_simfile = overwrite_input_simfile
        self.plugin_identifier = alternate_plugin_identifier if alternate_plugin_identifier is not None else \
                                 self.PLUGIN_IDENTIFIER

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

    def get_beats_from_vamp_plugin(self):
        if self.audio is None:
            raise ValueError("No audio loaded!")
        print(self.audio.shape)
        beats = [x for x in vamp.process_audio(self.audio, self.sampling_rate, self.plugin_identifier)]
        print(beats)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_audio_path", help="Path to input audio file")
    parser.add_argument("--input_beats_csv_path", help="Path to input CSV containing beat markers")
    parser.add_argument("--input_simfile_path", help="Path to input .sm or .ssc file")
    parser.add_argument("--output_simfile_path", help="Path to input .sm or .ssc file")
    parser.add_argument("--output_txt_path", help="Output path to text file where #BPMS and #OFFSET lines "
                                                  "will be written")
    parser.add_argument("--output_beat_markers_bpms_csv_path",
                        help="Specify this if you want a CSV with the beat markers and BPMs")
    parser.add_argument("--samples", help="Use this option if the beat locations are given in samples, "
                                          "and specify the sampling rate in Hz.", type=int)
    parser.add_argument("--overwrite_input_simfile", help="Use this option to overwrite the existing input simfile",
                        action="store_true")
    args = parser.parse_args()

    atbpm = AudioToBPMs(input_audio_path=args.input_audio_path)
    atbpm.get_beats_from_vamp_plugin()


if __name__ == "__main__":
    main()
