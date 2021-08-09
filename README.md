# AutogenSimfileBPMs
Auto-generate BPMs for a (Stepmania) simfile.  
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
Once you have python installed, you must also install the dependent packages by running
```
pip3 install -r requirements.txt
```
from the current directory.  You are encouraged to use a virtual environment if you know what that is, to avoid potential package conflicts.

The current dependencies (listed in `requirements.txt`) are as follows:
```
numpy>=1.21.1
vamp>=1.1.0
soundfile>=0.10.3.post1
simfile>=2.0.0b5
```

## Sample commands
1. Load the audio from a song and make a new SSC file with #BPMS and #OFFSET fields that match the song.
```
python3 autogen_simfile_bpms.py --input_audio_path ~/unstable_bpm_song.ogg --input_simfile_path /path/to/simfile.ssc --output_simfile_path /path/to/simfile2.ssc
```
2. Load an existing CSV of potentially hand-modified output from a beat tracking algorithm (using [<b>Sonic Visualiser</b>](https://www.sonicvisualiser.org/) for instance) and convert it to BPMs:
```
python3 autogen_simfile_bpms.py --input_beats_path ~/unstable_bpm_song_beats.csv --input_simfile_path /path/to/simfile.ssc --output_simfile_path /path/to/simfile2.ssc
```

## Warning
The accuracy of the generated BPMs completely depends on the accuracy of the underlying Vamp plugin for determining beat locations.  
I have found that it works rather well, but you might find it strange that it often seems to cycle between a small group of several fixed BPMs.  
That is probably due to some type of regularity constraint on the underlying beat tracking algorithm.  
It also may generate random beats for beatless passages (like silence or a spoken passage with no instrumental).

## Future work
<ul>
<li>This has only been tested on Linux.  Please raise issues if this doesn't work on your system.</li>
</ul>

## Credits
The Queen Mary Bar and Beat Tracker Vamp plugin was written by Matthew Davies and Adam Stark.
