import time
import rtmidi
import generator
from Queue import Empty
import Tkinter

class MidiOut(object):
    def __init__(self,gen,gui):
        """ Test should be changed but good enough for now
        >>> g = generator.Generator("../resources/state.yml")
        >>> midiout = MidiOut(g)
        MIDI output chosen : SimpleSynth virtual input
        """
        self.__gui = gui
        #This is used by the gui for playing/pausing
        self.playing = False
        self.__generator = gen
        self.tracks = {}
        
        self.__midiOut = rtmidi.MidiOut()
        if self.__midiOut.get_ports():
            self.__midiOut.open_port(0)
            msg = "MIDI output chosen : {}\n".format(self.__midiOut.get_ports()[0])
        else:
            self.__midiOut.open_virtual_port("My virtual output")
            msg = "MIDI output chosen : my virtual output\n"
        self.__gui.addToOutput(msg)
        self.__setup()
    
    def __setup(self):
        for i in range(16):
            self.tracks[i+1]={}
        self.tracks[1]['instrument'] = self.__generator.state['instrument']
        self.__started = False
    
    def __del__(self):
        del self.__midiOut
    
    def run(self):
        while self.__generator.active:
            while self.__generator.playing:
                try:
                    note = self.__generator.queue.get()
                    if isinstance(note,generator.Note):
                        self.__generator.size -= 1
                        note_on = [0x90,note.pitch,note.velocity]
                        note_off = [0x80,note.pitch,0]
                        msg = "{}\n".format(vars(note))
                        self.__gui.addToOutput(msg)
                        self.__midiOut.send_message(note_on)
                        time.sleep(note.duration)
                        self.__midiOut.send_message(note_off)
                    elif isinstance(note,generator.Instrument):
                        if not note.type==self.tracks[1]['instrument'] or not self.__started:
                            program_change = [0xC0,note.type,0x00]
                            self.__midiOut.send_message(program_change)
                            msg = "{}\n".format(vars(note))
                            self.__gui.addToOutput(msg)
                            self.tracks[1]['instrument'] = note.type
                            self.__started = True
                except Empty:
                    time.sleep(.05)
                    pass
        return
    #Queue required in the future for better precision and multi pitches

if __name__ == '__main__':
    import doctest
    doctest.testmod()