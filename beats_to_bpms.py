import csv
import argparse
from warnings import warn
import pathlib
import simfile  # https://simfile.readthedocs.io/_/downloads/en/latest/pdf/
import sys


class BeatsToBPMS(object):
    MIN_FIRST_BEAT_SEC_FOR_WARN = 10.
    SEC_DIFF_TOLERANCE = 1e-8

    def __init__(self, input_beats_csv_path, input_simfile_path=None, output_simfile_path=None, output_txt_path=None,
                 output_beat_markers_bpms_csv_path=None, samples=None, overwrite_input_simfile=False):
        self.input_beats_csv_path = pathlib.Path(input_beats_csv_path)
        self.input_simfile_path = pathlib.Path(input_simfile_path) if input_simfile_path is not None else None
        self.output_simfile_path = pathlib.Path(output_simfile_path) if output_simfile_path is not None else None
        self.output_txt_path = pathlib.Path(output_txt_path) if output_txt_path is not None else None
        self.output_beat_markers_bpms_csv_path = pathlib.Path(output_beat_markers_bpms_csv_path) \
            if output_beat_markers_bpms_csv_path is not None else None
        self.sampling_rate = samples
        self.input_beats_are_in_samples = False if samples is None else True
        self.overwrite_input_simfile = overwrite_input_simfile
        self._verify_command_line_inputs()
        self.input_data = []
        self.bpms = []
        self.beat_markers = []
        self.beats_bpms_sm_value = None
        self.offset = 0.

    def _verify_command_line_inputs(self):
        """
        Verify the command-line inputs
        :return:
        """
        if not self.input_beats_csv_path.is_file():
            raise ValueError("{} is not a valid input file path!".format(self.input_beats_csv_path))
        if self.sampling_rate is not None:
            try:
                self.sampling_rate = int(self.sampling_rate)
            except ValueError:
                raise ValueError("ERROR: Specified --samples with invalid sampling rate "
                                 "{}".format(self.sampling_rate))
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
        with open(self.input_beats_csv_path, "r") as infile:
            csvread = csv.reader(infile)
            row = next(csvread)
            first_beat_time = float(row[0])
            if self.sampling_rate is None:
                if first_beat_time > self.MIN_FIRST_BEAT_SEC_FOR_WARN:
                    warn("WARNING: Your first beat {} is at greater than {} seconds. "
                         "Are you sure the units are in seconds and not samples? "
                         "If they are samples, please specify the sampling rate using the flag "
                         "--samples; for instance --samples 48000.".format(first_beat_time,
                                                                           self.MIN_FIRST_BEAT_SEC_FOR_WARN))
            else:
                if int(first_beat_time) != first_beat_time:
                    warn("The first beat time {} is detected to be in units of seconds, but you specified the "
                         "sampling rate, which will not be used in the computation.")
                    self.input_beats_are_in_samples = False
                self.input_data.append(row)
            for row in csvread:
                self.input_data.append(row)
        
    def convert_beats_to_bpm(self):
        if self.sampling_rate is not None:
            first_beat_samples = int(self.input_data[0][0])  # Need to change if not samples
            self.offset = - first_beat_samples / self.sampling_rate
            beat_marker = 0
            last_beat_diff = 0
            for row in self.input_data[1:]:
                second_beat_samples = int(row[0]) # CHANGE
                beat_diff = second_beat_samples - first_beat_samples # CHANGE
                if last_beat_diff != beat_diff:
                    bpm = self.sampling_rate / beat_diff * 60  # CHANGE
                    self.bpms.append(bpm)
                    self.beat_markers.append(beat_marker)
                first_beat_samples = second_beat_samples
                beat_marker += 1
                last_beat_diff = beat_diff
        else:
            beat_marker = 0
            last_beat_diff = 0
            first_beat_sec = float(self.input_data[0][0])
            self.offset = - first_beat_sec
            for row in self.input_data[1:]:
                second_beat_sec = float(row[0])
                beat_diff = second_beat_sec - first_beat_sec
                if abs(last_beat_diff - beat_diff) > self.SEC_DIFF_TOLERANCE:
                    bpm = 60 / beat_diff
                    self.bpms.append(bpm)
                    self.beat_markers.append(beat_marker)
                first_beat_sec = second_beat_sec
                beat_marker += 1
                last_beat_diff = beat_diff

    def convert_bpms_to_sm_value(self):
        beats_bpms = ["{}={}\n".format(beat_marker, bpm) for beat_marker, bpm in
                      zip(self.beat_markers, self.bpms)]
        self.beats_bpms_sm_value = ",".join(beats_bpms)

    def write_output_csv(self):
        with open(self.output_beat_markers_bpms_csv_path, "w") as outfile:
            csvwrite = csv.writer(outfile)
            for beat_marker, bpm in zip(self.beat_markers, self.bpms):
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
        if self.beats_bpms_sm_value is None:
            self.convert_bpms_to_sm_value()
        stepmania_bpms_out = "#BPMS:" + self.beats_bpms_sm_value + ";"

        with open(self.output_txt_path, "w") as outfile:
            outfile.write(stepmania_offset_out)
            outfile.write(stepmania_bpms_out)

    def write_output_sm(self):
        sm = simfile.open(str(self.input_simfile_path))
        sm.offset = self.offset
        if self.beats_bpms_sm_value is None:
            self.convert_bpms_to_sm_value()
        sm.bpms = self.beats_bpms_sm_value
        with open(self.output_simfile_path, 'w', encoding='utf-8') as outfile:
            sm.serialize(outfile)

    def run(self):
        self.read_input_csv()
        self.convert_beats_to_bpm()

        if self.output_simfile_path is not None:
            self.write_output_sm()
        if self.output_txt_path is not None:
            self.write_output_txt_oneline()
        if self.output_beat_markers_bpms_csv_path is not None:
            self.write_output_csv()


def main():
    # Will it work to parse here???
    parser = argparse.ArgumentParser()
    parser.add_argument("input_beats_csv_path", help="Path to CSV file containing beat information")
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

    beats_to_bpms = BeatsToBPMS(args.input_beats_csv_path, args.input_simfile_path, args.output_simfile_path,
                                args.output_txt_path, args.output_beat_markers_bpms_csv_path, args.samples,
                                args.overwrite_input_simfile)
    beats_to_bpms.run()


if __name__ == "__main__":
    main()
