import csv
import argparse
from warnings import warn


class BeatsToBPMS(object):
    def __init__(self, input_beats_csv_path, sm_path=None, output_txt_path=None, 
                       output_beat_markers_bpms_csv_path=None, samples=None):
        self.input_beats_csv_path = input_beats_csv_path
        self.sm_path = sm_path
        self.output_txt_path = output_txt_path
        self.output_beat_markers_bpms_csv_path = output_beat_markers_bpms_csv_path
        self.samples = samples

    def _verify_inputs(self):
        pass

    def read_input_csv(self):
        pass
        
    def convert_beats_to_bpm(self):
        pass
        
    def write_output_sm(self):
        pass
        
    def write_output_txt(self):
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
    
    

rows = []
with open("magellan_cut_beats.csv", "r") as infile:
    csvread = csv.reader(infile)
    for row in csvread:
        rows.append(row)
        
SAMPLING_RATE = 48000  # Can get this direct from the magellan_cut.wav too

bpms = []
beat_markers = []
first_beat_samples = int(rows[0][0])
beat_marker = 0
last_beat_diff = 0
for row in rows[1:]:
    second_beat_samples = int(row[0])
    beat_diff = second_beat_samples - first_beat_samples
    if last_beat_diff != beat_diff:
        bpm = SAMPLING_RATE / beat_diff * 60
        bpms.append(bpm)
        beat_markers.append(beat_marker)
        print(beat_marker, bpm)
    first_beat_samples = second_beat_samples
    beat_marker += 1
    last_beat_diff = beat_diff
    
with open("magellan_cut_beat_markers_and_bpms.csv", "w") as outfile:
    csvwrite = csv.writer(outfile)
    for beat_marker, bpm in zip(beat_markers, bpms):
        csvwrite.writerow([beat_marker, bpm])

#stepmania_bpms_out = "#BPMS:0.000=132.000,149.000=66.000,173.000=132.000;"
beats_bpms = ["{}={}".format(beat_marker, bpm) for beat_marker, bpm in zip(beat_markers, bpms)]
stepmania_bpms_out = "#BPMS:" + ",".join(beats_bpms) + ";"
print(stepmania_bpms_out)
        
with open("magellan_cut_sm_line.txt", "w") as outfile:
    outfile.write(stepmania_bpms_out)

if __name__ == "__main__":
    main()
