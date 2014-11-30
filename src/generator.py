from voluptuous import Schema, Required, All, Length, Range, MultipleInvalid
from threading import Lock
import yaml
import logging
import random
import time
import utils
import sys
import traceback
from Queue import Queue
from string import ascii_lowercase

from music21 import note
from athenaCL.libATH import grammar
from athenaCL.libATH import markov
from Cython.Compiler.Naming import cur_scope_cname

lock = Lock()

class Generator(object):
    OFFSET = 0
    VALUES = 1
    
    def __init__(self, filename, config):
        """
        >>> g = Generator("../resources/presets/default.yml", {})
        >>> g.state["instrument"]
        23
        >>> g.state["bpm"]
        110
        """        
        # The state of the generator describes what the generator will generate.
        # It follows the AthenaCL standard.
        self.file = filename
        
        # The Notebuffer is where generated notes are stored before being sent to 
        # the synthesizer
        self.queue = Queue()
        
        # This variable gives the size of the queue. This is required because Mac OS X
        # does not support queue.qsize()
        self.size = 0
        self.size_lock = Lock()
        
        self.schema = Schema({
            Required('instrument'): All(int, Range(min=1, max=32)),
            Required('bpm'): All(int, Range(30, 210)),
            Required('path'): {
                Required('pattern'): All(list, Length(8)),
                Required('order'): str
            },
            Required('pitch'): {
                Required('pattern'): [
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8))
                ],
                Required('order'): str
            },
            Required('rhythm'): {
                Required('pattern'): [
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8)),
                    All(list, Length(8))
                ],
                Required('order'): str,
                Required('dividor') : int
            },
            Required('amplitude'): {
                Required('pattern'): All(list, Length(8)),
                Required('order'): str
            }
        })
        
        self.loadState()
        
        # This is used to say if the music generation is active or not.
        self.active = True
        
        # This is used by the gui for playing/pausing.
        self.playing = False
    
    def loadState(self):
        """
        Loads the application generator state.
        """
        # This is the range of the selector for each feature.
        self.feature_sizes = { 'pitch' : 8, 'path' : 8, 'amplitude' : 8, 'rhythm' : 4}
        self.state = self.readState()
    
    def readState(self):
        # Read algorithm state
        try:
            with open(self.file) as f:
                state = yaml.load(f)
        except IOError:
            t, v, tb = sys.exc_info()
            print v
            traceback.print_tb(tb)
            sys.exit(1)
        
        # Check that preset file is well-formed.
        try:
            self.__checkStateFormat(state)
        except MultipleInvalid:
            t, v, tb = sys.exc_info()
            print v
            traceback.print_tb(tb)
            sys.exit(1)
        
        # Fills the blanks for all of the non markov stuff.
        for attributeName in ['rhythm', 'amplitude', 'path', 'pitch']:
            # Assign the order engine
            self.__computeOrderEng(state, attributeName)
        
        state['rhythm']['pattern'] = self.serialize_rhythm(state['rhythm']['pattern'])
        state['pitch']['pattern'] = self.serialize_pitch(state['pitch']['pattern'])
        
        # Indicates currently selected path on Path Map. Value can be 0-7.
        state['path']['selected'] = 0
        state['rhythm']['row_idx'] = 0
        state['rhythm']['col_idx'] = -1
        return state
    
    def __checkStateFormat(self, state):
        """
        Checks that the input state object is a dictionary valid
        which follows the expected format.
        """
        self.schema(state)
    
    def __computeOrderEng(self, parameters, attributeName):
        """
        This method computes the order parameter of some of the attributes of the state
        """
        if attributeName not in ["path", "rhythm", "pitch", "amplitude"]:
            raise Exception("Attempting to assign an order to an invalid attribute!")
        else:
            size = self.feature_sizes[attributeName]
            # If not already set, put a random value here.
            if parameters[attributeName]['order'] == 'cyclic':
                parameters[attributeName]['order_eng'] = CyclicGenerator(size)
            elif parameters[attributeName]['order'] == 'random':
                parameters[attributeName]['order_eng'] = UniformRandomGenerator(size)
            else:
                raise Exception("Order type %s is invalid!", parameters[attributeName]['order'])
        return
    
    def update(self, attribute, value):
        """
        This method updates the current state of the generator. Expected attribute/value
        combination are given below in the format:
        
            attribute : expected value
        
        List :
            "bpm" : int
            "instrument" : int
            "* order" : str
            "path select" : int
            "path pattern" : int
            "rhythm pattern %d" : list
            "pitch pattern %d" : list
            "amplitude pattern %d" : float
        """
        try:
            if attribute == "bpm":
                self.state['bpm'] = value
            elif attribute == "instrument":
                self.state['instrument'] = value
                self.__change_instrument(value)
            elif attribute == "path order":
                self.__updateOrder('path', value)
            elif attribute.startswith('path pattern'):
                selected_path = self.state['path']['selected']
                self.state['path']['pattern'][selected_path] = value
            elif attribute == 'path select':
                self.state['path']['selected'] = value
            elif attribute == "rhythm order":
                self.__updateOrder('rhythm', value)
            elif attribute.startswith("rhythm pattern"):
                idx = int(attribute.split(" ")[-1]) - 1
                self.state['rhythm']['pattern'][idx] = value
            elif attribute.startswith("rhythm dividor"):
                self.state['rhythm']['dividor'] = value
            elif attribute.startswith("pitch pattern"):
                idx = int(attribute.split(" ")[-1]) - 1
                self.state['pitch']['pattern'][idx] = value
            elif attribute.startswith("pitch order"):
                self.__updateOrder('pitch', value)
            elif attribute.startswith('amplitude pattern'):
                idx = int(attribute.split(" ")[-1]) - 1
                self.state['amplitude']['pattern'][idx] = value
            elif attribute.startswith("amplitude order"):
                self.__updateOrder('amplitude', value)
            else:
                # Should not happen
                raise Exception("generator.update() called with invalid attribute {}".format(attribute))
            return True
        except:
            t, v, tb = sys.exc_info()
            print t
            print v
            traceback.print_tb(tb)
            return False
    
    def __updateOrder(self, attribute, value):
        self.state[attribute]['order'] = value
        size = len(self.state[attribute]['list'])
        if value == "cyclic":
            self.state[attribute]['order_eng'] = CyclicGenerator(size)
        elif value == "random":
            self.state[attribute]['order_eng'] = UniformRandomGenerator(size)
        else:
            print "Unknown order: %s !" % value
    
    
    def serialize_rhythm(self, pattern):
        """
        The rhythm pattern's internal representation differs from that specified
        by the user and visible on the interface. As such the pattern must be
        serialized before being modified by the generator.
        
        >>> g = Generator("../resources/presets/default.yml", {})
        >>> pattern = [[0, 0, 0, 0, 1, 0, 0, 0], [1, 0, 0, 1, 0, 1, 0, 1], [1, 0, 0, 0, 1, 0, 0, 0], [1, 0, 0, 1, 0, 1, 0, 1]]
        >>> g.serialize_rhythm(pattern)
        [(4, [4]), (0, [3, 2, 2, 1]), (0, [4, 4]), (0, [3, 2, 2, 1])]
        """
        new_pattern = []
        for row in pattern:
            cur = 0
            while cur < 8 and row[cur] == 0:
                cur += 1
            offset = cur
            values = []
            while cur < 8:
                cur += 1
                val = cur - 1
                while cur < 8 and row[cur] == 0:
                    cur += 1
                values.append(cur - val)
            new_pattern.append((offset, values))
        return new_pattern

    def deserialize_rhythm(self, pattern):
        """
        The rhythm pattern's internal representation differs from that specified
        by the user and visible on the interface. As such the pattern must be
        deserialized before being viewed by the user.
        
        >>> g = Generator("../resources/presets/default.yml", {})
        >>> pattern = [(4, [4]), (0, [3, 2, 2, 1]), (0, [4, 4]), (0, [3, 2, 2, 1])]
        >>> g.deserialize_rhythm(pattern)
        [[0, 0, 0, 0, 1, 0, 0, 0], [1, 0, 0, 1, 0, 1, 0, 1], [1, 0, 0, 0, 1, 0, 0, 0], [1, 0, 0, 1, 0, 1, 0, 1]]
        """
        new_pattern = []
        for pair in pattern:
            row = []
            offset, values = pair
            cur = 0
            while cur < 8 and cur < offset:
                row.append(0)
                cur += 1
            for val in values:
                row.append(1)
                cur = 1
                while cur < 8 and cur < val:
                    row.append(0)
                    cur += 1
            new_pattern.append(row)
        return new_pattern
    
    def serialize_pitch(self, pattern):
        """
        The pitch pattern's internal representation differs from that specified
        by the user and visible on the interface. As such the pattern must be
        serialized before being modified by the generator.
        
        Note that there must always be one pitch. If a column has no 1's, then
        a 1 will be added on the 0 row (implicitly in the serialization output).
        
        >>> g = Generator("../resources/presets/default.yml", {})
        >>> pattern = g.deserialize_pitch(g.state['pitch']['pattern'])
        >>> g.serialize_pitch(pattern)
        [[0], [3, 0, -3], [0], [3, 0, -3], [0], [0], [0], [0]]
        """
        new_pattern = [[] for x in xrange(0,8)]
        for i in xrange(11):
            for j in xrange(8):
                if pattern[i][j] == 1:
                    new_pattern[j].append(5-i)
        
        # Fill in the holes with pitch 0.
        for column in new_pattern:
            if not column:
                column.append(0)
        
        return new_pattern
    
    def deserialize_pitch(self, pattern):
        """
        The pitch pattern's internal representation differs from that specified
        by the user and visible on the interface. As such the pattern must be
        deserialized before being viewed by the user.
        """
        new_pattern = [([0] * 8) for x in xrange(0,11)]
        for idx, column in enumerate(pattern):
            for cell in column:
                new_pattern[-cell+5][idx] = 1
        return new_pattern
    
    def generate(self):
        """
        This method generates one Music21 note according to the current state and stores it in the note buffer.
        """
        # Get the rhythm multiplier from the currently played row. If it is complete,
        # start another row. The rhythm multiplier may contain an offset (before which
        # and element is played), when the row starts with 0s.
        row_idx = self.state['rhythm']['row_idx']
        col_idx = self.state['rhythm']['col_idx']
        rhythm_pattern = self.state['rhythm']['pattern']
        if col_idx == -1:
            # Dealing with pattern offset
            
            mult = rhythm_pattern[row_idx][Generator.OFFSET]
            self.state['rhythm']['col_idx'] += 1
            
            # Define note duration from rhythm and bpm
            div = self.state['rhythm']['dividor']
            duration = (float(mult) * 60.0) / (float(div) * float(self.state['bpm']))
            # Store in note buffer
            n = NoteOffset(duration)
            self.queue.put(n)
            
        elif 0 <= col_idx and col_idx < len(rhythm_pattern[row_idx][Generator.VALUES]):
            # Dealing with pattern values
            
            mult = rhythm_pattern[row_idx][Generator.VALUES][col_idx]
            
            if col_idx == len(rhythm_pattern[row_idx][Generator.VALUES]) - 1:
                # If the column index points to the last value of pattern,
                # We need to choose the next row to be played. The duration
                # offset of that row must be added to the current multiplier
                # as well.
                self.state['rhythm']['row_idx'] = self.state['rhythm']['order_eng'].next()
                self.state['rhythm']['col_idx'] = -1
                row_idx = self.state['rhythm']['row_idx']
                mult += rhythm_pattern[row_idx][Generator.OFFSET]
            
            # Define note duration from rhythm and bpm
            div = self.state['rhythm']['dividor']
            duration = (float(mult) * 60.0) / (float(div) * float(self.state['bpm']))
            
            # Define note pitch from path. An "S" in the path can be used for silence.
            path = self.state['path']['pattern'][self.state['path']['order_eng'].next()]
            
            if path == 'S':
                # Add a single silent note.
                self.queue.put([Note(0, duration, 0)])
            else:
                # Assign velocity to instrument
                velocity = int(self.state['amplitude']['pattern'][self.state['amplitude']['order_eng'].next()] * 127) % 127
                
                path = note.Note(path).midi
                
                # Set the pitch modulations. If the size of the list of pitch modulations (pitches object) is
                # greater than one, than multiples notes will be played.
                pitches = self.state['pitch']['pattern'][self.state['pitch']['order_eng'].next()]
                
                notes = []
                for pitch in pitches:
                    # There is always at least one pitch.
                    notes.append(Note(path+pitch, duration, velocity))
                # Store in note queue
                self.queue.put(notes)
                self.incrementQueueSize()
        else:
            raise Exception("Invalid column index for rhythm pattern!") 
    
    def incrementQueueSize(self):
        self.size_lock.acquire()
        self.size += 1  # Should be using queue size instead.
        self.size_lock.release()
        
    def decrementQueueSize(self):
        self.size_lock.acquire()
        self.size -= 1  # Should be using queue size instead.
        self.size_lock.release()
    
    def __change_instrument(self, instrument):
        i = Instrument(instrument)
        self.queue.put(i)
    
    def __setupBuffer(self):
        """ This method sets up initial MIDI instrument, panning, volume"""
        # Setup midi instrument
        self.__change_instrument(self.state['instrument'])
        return
   
    # Main loop function
    def run(self):
        self.__setupBuffer()
        while self.active:
            time.sleep(.1)
            while self.playing:
                time.sleep(.1)
                if self.size < 5:
                    while self.size < 10:
                        self.generate()

class Note(object):
    def __init__(self, p, d, v):
        self.pitch = p
        self.duration = d
        self.velocity = v
    
    def __repr__(self):
        return "Note(%d,%f,%d)" % (self.pitch, self.duration, self.velocity)

class NoteOffset(object):
    def __init__(self, d):
        self.duration = d
    
    def __repr__(self):
        return "NoteOffset(%f)" % self.duration
        
class Instrument(object):
    def __init__(self, instrument):
        self.type = instrument

class RandomGenerator(object):
    def next(self):
        """ Generates a random value using the generator."""
        return

class CyclicGenerator(RandomGenerator):
    def __init__(self, size):
        self.__counter = 0
        self.__size = size
    def next(self):
        self.__counter = (self.__counter + 1) % self.__size
        return self.__counter

class UniformRandomGenerator(RandomGenerator):
    def __init__(self, size):
        self.__size = size
    
    def next(self):
        return random.randint(0, self.__size - 1)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    g = Generator("../resources/presets/default.yml", {})
    i = 10
    for j in xrange(i):
        g.generate()
    for j in xrange(i):
        print g.queue.get()
