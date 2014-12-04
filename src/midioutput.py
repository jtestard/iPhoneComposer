import time
import rtmidi
import generator
from Queue import Empty

class MidiOut(object):
    def __init__(self, gen, gui, config):
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
        self.currently_playing = []
        
        self.__midiOut = rtmidi.MidiOut()
        channel_name = config['midi_channel']
        self.__midiOut.open_virtual_port(channel_name)
        msg = "MIDI output chosen : %s\n" % channel_name
        self.__gui.addToOutput(msg)
        self.__setup()
    
    def __setup(self):
        for i in range(16):
            self.tracks[i+1]={}
        self.tracks[1]['instrument'] = self.__generator.state['instrument']
        self.__started = False
    
    def __del__(self):
        del self.__midiOut
    
    def exit_notes(self):
        """
        Sends a note off events to all currently playing notes.
        Used when exiting or pausing the application.
        """
        for note_off in self.currently_playing:
            self.__send_notes(note_off)
        pass
    
    def __send_notes(self, note):
        if note[0] == 0x90:
            print "MIDI NOTE ON : %s" % note
        else:
            print "MIDI NOTE OFF : %s" % note
        self.__midiOut.send_message(note)
    
    def run(self):
        """
        """
        while self.__generator.active:
            time.sleep(.05)
            while self.__generator.playing:
                try:
                    note = self.__generator.queue.get()
                    size = self.__generator.decrementQueueSize()
                    if isinstance(note,list):
                        print "New list..."
                        # We received a list of notes
                        # Must change to note-off followed by note-on.
                        for element in note:
                            note_on = [0x90,element.pitch,element.velocity]
                            self.currently_playing.append([0x80,element.pitch,0])
                            msg = "%s\n" % ("{}".format(vars(element)))
                            self.__gui.addToOutput(msg)
                            self.__send_notes(note_on)
                        time.sleep(note[0].duration)
                        for note_off in self.currently_playing:
                            self.__send_notes(note_off)
                        self.currently_playing = []
                    elif isinstance(note, generator.NoteOffset):
                        # This is a pattern offset. We wait a little bit
                        time.sleep(note.duration)
                    elif isinstance(note,generator.Instrument):
                        if not note.type==self.tracks[1]['instrument'] or not self.__started:
                            program_change = [0xC0,note.type,0x00]
                            self.__midiOut.send_message(program_change)
                            msg = "{}\n".format(vars(note))
                            self.__gui.addToOutput(msg)
                            self.tracks[1]['instrument'] = note.type
                            self.__started = True
                    else:
                        print "Unknown object type"
                except Empty:
                    time.sleep(.05)
                    pass
                finally:
                    # Don't forget to stop notes if application terminates.
                    self.exit_notes()

        return
    #Queue required in the future for better precision and multi pitches

if __name__ == '__main__':
    import doctest
    doctest.testmod()
