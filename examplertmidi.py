import time
import rtmidi
from music21 import *

midiout = rtmidi.MidiOut()
available_ports = midiout.get_ports()

print available_ports
if available_ports:
    midiout.open_port(0)
else:
    midiout.open_virtual_port("My virtual output")

s = converter.parse('script04b.mid')

for e in s.recurse():
    if 'Note' in e.classes:
        note_on = [0x90,e.midi,e.volume.velocity]
        note_off = [0x80,e.midi,0]
        midiout.send_message(note_on)
        time.sleep(e.duration.quarterLength)
        midiout.send_message(note_off)
#note_on = [0x90, 60, 112] # channel 1, middle C, velocity 112
#note_off = [0x80, 60, 0]
#midiout.send_message(note_on)
#time.sleep(.5)
#midiout.send_message(note_off)

del midiout
