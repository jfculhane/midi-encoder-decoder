# midi-encoder-decoder
This is a simple midi parser that first creates a text array of 250 random notes with the script rnd250-d.py 
Then a second script takes the output: midi_sequence.txt and coverts it into a .mid binary using mido. That script is called texttomidi3.py. The output is output.mid.
A third script coverts the midi file back to a .csv file. That script is miditotext3.py. The output is output.csv

See the example-outputs folder for outputs. 

Customization:
The current random generator randomizes the length of the notes from 1 to 10. 
It also limits the random note from 1 to 60 instead of the full 127 midi notes.

The instrument program assignment and speed is in the texttomidi3.py script 
bpm=120.0, ticks_per_beat=480, program=101
The program uses the general midi assignments found here: https://en.wikipedia.org/wiki/General_MIDI
You must subtract the midi assignment by 1 so the listing of 102 is 101 in the script. Goblins. 

September 2025 - GC NEW MEDIA LLC
