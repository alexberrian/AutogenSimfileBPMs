# AutogenSimfileBPMs
Auto-generate BPMs for a [<b>Stepmania</b>](https://www.stepmania.com) or [<b>OutFox</b>](https://projectmoon.dance/) simfile.  
This code will detect the locations of a song's quarter beats, and automatically fill in the <b>#BPMS</b> and <b>#OFFSET</b> fields of an input simfile.

This is useful if you want to make simfiles for your favorite old songs with unstable tempos, where the BPM keeps changing.  
It's not intended for finding a song's single fixed tempo, and I've done very limited performance testing.  
This code depends on an existing beat tracking algorithm's implementation (see below).

## Setup

### 1. Installing the Queen Mary Vamp plugin for bar and beat tracking
You need to install the [<b>Queen Mary Bar and Beat Tracker Vamp plugin</b>](https://vamp-plugins.org/plugin-doc/qm-vamp-plugins.html#qm-barbeattracker), 
which you can [<b>download here</b>](https://code.soundsoftware.ac.uk/projects/qm-vamp-plugins/files).  
Please see [<b>this page</b>](https://www.vamp-plugins.org/download.html#install) for how to install Vamp plugins on your system. 

### 2. Python dependencies
You must also install and be able to run <b>python3.9</b> on your system.  This should already be there if you have a Mac, and may be there with your Linux installation too.  
Once you have python installed, you must also install the dependent Python packages by running
```
pip3 install -r requirements.txt
```
from the current directory.  You are encouraged to use a virtual environment if you know what that is, to avoid potential package conflicts.

The current Python package dependencies (listed in `requirements.txt`) are as follows:
```
numpy>=1.21.1
vamp>=1.1.0
soundfile>=0.10.3.post1
simfile>=2.0.0b5
```

## Sample commands
1. Load the audio from a song and make a new SSC file from an existing SSC file, automatically inserting #BPMS and #OFFSET fields that match the song.
```
python3 autogen_simfile_bpms.py --input_audio_path /path/to/unstable_bpm_song.ogg --input_simfile_path /path/to/simfile.ssc --output_simfile_path /path/to/simfile2.ssc
```
2. Load an existing CSV of potentially hand-modified output from a beat tracking algorithm (using [<b>Sonic Visualiser</b>](https://www.sonicvisualiser.org/) for instance) and convert it to BPMs:
```
python3 autogen_simfile_bpms.py --input_beats_path /path/to/unstable_bpm_song_beats.csv --input_simfile_path /path/to/simfile.ssc --output_simfile_path /path/to/simfile2.ssc
```
3. Same as #1 but overwrite the input simfile.  <b>NOTE:</b> as of now, you <i>must</i> specify `--overwrite_input_simfile` or the code won't actually save the output anywhere.  It won't ask you if you want to overwrite either.  That will be fixed later.
```
python3 autogen_simfile_bpms.py --input_audio_path /path/to/unstable_bpm_song.ogg --input_simfile_path /path/to/simfile.ssc --overwrite_input_simfile
``` 
4. Same as #1 but just export a text file with the #OFFSET and #BPMS fields only, which you could copy and paste into your existing simfile:
```
python3 autogen_simfile_bpms.py --input_audio_path /path/to/unstable_bpm_song.ogg --output_txt_path /path/to/text_file.txt
```
5. View a list of all the options
```
python3 autogen_simfile_bpms.py --help
```

## Warning
The accuracy of the generated BPMs completely depends on the accuracy of the underlying Vamp plugin for determining beat locations.  
I have found that it works rather well, but you might find it strange that it often seems to cycle between a small group of several fixed BPMs.  
That is probably due to some type of regularity constraint on the underlying beat tracking algorithm.  
It also may generate random beats for beatless passages (like silence or a spoken passage with no instrumental).

## Future work
<ul>
  <li>This has only been tested on Linux.  Please raise issues if this doesn't work on your system.</li>
  <li>As it stands right now, you need to put in an existing simfile to get a simfile out.  Future code functionality will hopefully have a simfile template option.</li>
</ul>

## Credits
The Queen Mary Bar and Beat Tracker Vamp plugin was written by Matthew Davies and Adam Stark.
