import csv
import argparse
from warnings import warn
# import msdparser  # https://pypi.org/project/msdparser/


class BeatsToBPMS(object):
    def __init__(self, input_beats_csv_path, sm_path=None, output_txt_path=None, 
                       output_beat_markers_bpms_csv_path=None, samples=None):
        self.input_beats_csv_path = input_beats_csv_path
        self.sm_path = sm_path
        self.output_txt_path = output_txt_path
        self.output_beat_markers_bpms_csv_path = output_beat_markers_bpms_csv_path
        self.sampling_rate = samples
        self.input_data = []
        self.bpms = []
        self.beat_markers = []

    def _verify_inputs(self):
        """
        Verify the command-line inputs
        :return:
        """
        pass

    def read_input_csv(self):
        with open(self.sm_path, "r") as infile:
            csvread = csv.reader(infile)
            for row in csvread:
                self.input_data.append(row)
        
    def convert_beats_to_bpm(self):
        first_beat_samples = int(self.input_data[0][0])  # Need to change if not samples
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

    def write_output_csv(self):
        with open(self.output_beat_markers_bpms_csv_path, "w") as outfile:
            csvwrite = csv.writer(outfile)
            for beat_marker, bpm in zip(self.beat_markers, self.bpms):
                csvwrite.writerow([beat_marker, bpm])

    def write_output_txt_oneline(self):
        """
        Write out a text file that only contains the one line that you're gonna
        stick into the Stepmania .sm file (or .ssc).

        Sample output:
        #BPMS:0.000=132.000,149.000=66.000,173.000=132.000;

        :return:
        """

        beats_bpms = ["{}={}".format(beat_marker, bpm) for beat_marker, bpm in
                      zip(self.beat_markers, self.bpms)]
        stepmania_bpms_out = "#BPMS:" + ",".join(beats_bpms) + ";"

        with open(self.output_txt_path, "w") as outfile:
            outfile.write(stepmania_bpms_out)

    def write_output_sm(self):
        pass


def main():
    # Will it work to parse here???
    parser = argparse.ArgumentParser()
    parser.add_argument("input_beats_csv_path", help="Path to CSV file containing beat information")
    parser.add_argument("--sm_path", help="Path to SM file where #BPMS and #OFFSET lines will be overwritten, "
                                         "overrides --output_txt_path usage")
    parser.add_argument("--output_txt_path", help="Output path to text file where #BPMS and #OFFSET lines will be written", 
                                            default="output_beats.txt")
    parser.add_argument("--output_beat_markers_bpms_csv_path", 
                        help="Specify this if you want a CSV with the beat markers and BPMs")
    parser.add_argument("--samples", help="Use this option if the beat locations are given in samples, "
                                          "and specify the sampling rate in Hz.", type=int)
    args = parser.parse_args()


if __name__ == "__main__":
    main()
