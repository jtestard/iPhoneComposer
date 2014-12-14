from voluptuous import Schema, Required, All, Length, Range, MultipleInvalid
from threading import Lock
import yaml
import logging
import random
import time
import utils
import sys
import traceback
from copy import copy
from Queue import Queue
from string import ascii_lowercase
from numpy import rot90
from music21 import note
from athenaCL.libATH import grammar
from athenaCL.libATH import markov

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
        self.rhythm_lock = Lock()
        
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
        return self.readStateFromFile(self.file)
        
    def readStateFromFile(self, file):
        # Read algorithm state
        try:
            with open(file) as f:
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
            "rhythm pattern %d" : (row) list
            "pitch pattern %d" : (column) list
            "amplitude pattern %d" : float
        """
        try:
            if attribute == "bpm":
                self.state['bpm'] = value
            elif attribute == "instrument":
                self.state['instrument'] = value + 1
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
                idx = int(attribute.split(" ")[-1])
                cur = 0
                while cur < 8 and value[cur] == 0:
                    cur += 1
                offset = cur
                values = []
                while cur < 8:
                    cur += 1
                    val = cur - 1
                    while cur < 8 and value[cur] == 0:
                        cur += 1
                    values.append(cur - val)
                self.rhythm_lock.acquire() # Hot code which needs to be locked.
                self.state['rhythm']['pattern'][idx] = (offset, values)
                self.rhythm_lock.release()
            elif attribute.startswith("rhythm dividor"):
                self.state['rhythm']['dividor'] = value
            elif attribute.startswith("pitch pattern"):
                idx = int(attribute.split(" ")[-1])
                pitch_column = []
                for i in xrange(11):
                    if value[i] == 1:
                        pitch_column.append(5-i)
                self.state['pitch']['pattern'][idx] = pitch_column
            elif attribute.startswith("pitch order"):
                self.__updateOrder('pitch', value)
            elif attribute.startswith('amplitude pattern'):
                idx = int(attribute.split(" ")[-1])
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
    
    def apply_algorithm(self, category, algorithm):
        if algorithm == 'shiftLeft':
            self.shift_left(category)
        elif algorithm == 'shiftRight':
            self.shift_right(category)
        elif algorithm == 'shiftUp':
            self.shift_up(category)
        elif algorithm == 'shiftDown':
            self.shift_down(category)
        elif algorithm == 'retrograde':
            self.retrograde(category)
        elif algorithm == 'inverse':
            self.inverse(category)
        elif algorithm == 'retrograde-inverse':
            self.retrogradeInverse(category)
        elif algorithm == 'raiseOctave':
            self.raiseOctave(category)
        elif algorithm == 'lowerOctave':
            self.lowerOctave(category)
    
    def shift_left(self, category):
        if category == 'rhythm':
            self.shiftRhythmHorizontally(self, 1) # shift rhythm patten left-hand horzontally
        elif category == 'pitch':
            self.shiftPitchHorizontally(self, 1) # shift pitch patten left-hand horzontally
        else:
            self.state[category]['pattern'] = self.__rotate(self.state[category]['pattern'], -1)
    
    def shift_right(self, category):
        if category == 'rhythm':
            self.shiftRhythmHorizontally(self, -1) # shift rhythm patten right-hand horzontally
        elif category == 'pitch':
            self.shiftPitchHorizontally(self, -1) # shift pitch patten right-hand horzontally
        else:
            self.state[category]['pattern'] = self.__rotate(self.state[category]['pattern'], 1)

    def shift_up(self, category):
        if category == 'path':
            self.transposePath(1) # raise path chromatically (interval = 1)
        elif category == 'rhythm':
            self.shiftRhythmVertically(self, 1) # shift rhythm patten upward vertically
        elif category == 'pitch':
            self.shiftPitchVertically(self, 1) # shift pitch patten upward vertically
        elif category == 'amplitude':
            self.adjustAmplitude(0.1) # increase all amplitudes

    def shift_down(self, category):
        if category == 'path':
            self.transposePath(-1) # lower path chromatically (interval = -1)
        elif category == 'rhythm':
            self.shiftRhythmVertically(self, -1) # shift rhythm patten downward vertically
        elif category == 'pitch':
            self.shiftPitchVertically(self, -1) # shift pitch patten downward vertically
        elif category == 'amplitude':
            self.adjustAmplitude(-0.1) # decrease all amplitudes

    def retrograde(self, category):
        if category == 'rhythm':
            rhythm = self.deserialize_rhythm(self.state['rhythm']['pattern']) # deserialize
            [subList.reverse() for subList in rhythm] # reverse the mother list
            self.state['rhythm']['pattern'] = self.serialize_rhythm(rhythm) # serialize
        elif category == 'pitch':
            pitch = self.deserialize_pitch(self.state['pitch']['pattern']) # deserialize
            [subList.reverse() for subList in pitch] # reverse the mother list
            self.state['pitch']['pattern'] = self.serialize_pitch(pitch) # serialize
        else:
            # import pdb; pdb.set_trace()
            self.state[category]['pattern'].reverse()

    def inverse(self, category):
        if category == 'path':
            path = self.state['path']['pattern'] # read path
            restIndex = []
            noteIndex = []
            beforeInversion = [] # lenngth = len(noteIndex)
            afterInversion = [] # length = len(noteIndex)
            new_path = [] # length = len(path)
            for i in range(len(path)):
                if path[i] == 'S':
                    restIndex.append(i) # index all rests ('S')
                else:
                    noteIndex.append(i) # index all notes
            for i in range(len(noteIndex)):
                beforeInversion.append(note.Note(path[noteIndex[i]]).pitch.midi) # read all notes and convert pitch names to MIDI pitch numbers
                if i == 0: # initial note
                    afterInversion.append(beforeInversion[i]) # keep the same pitch
                else: # all other notes
                    afterInversion.append(afterInversion[i-1]-(beforeInversion[i]-beforeInversion[i-1])) # inverse transposition                
            if self.examineOverflow(afterInversion, 0, 127) is True: # all MIDI pitch numbers are within 0~127
                for i in range(len(restIndex)):
                    new_path[restIndex[i]] = 'S' # write all rests ('S')
                for i in range(len(noteIndex)):
                    new_path[noteIndex[i]] = note.Note(afterInversion[i]).nameWithOctave # convert MIDI pitch numbers to pitch names and write all notes
                self.state['path']['pattern'] = path # write path

    def retrogradeInverse(self, category):
        if category == 'path':
            self.inverse(category) # inverse before retrograde
            self.state['path']['pattern'].reverse() # retrograde after inverse

    def raiseOctave(self, category):
        if category == 'path':
            self.transposePath(12) # raise path by octave (interval = 12)
    
    def lowerOctave(self, category):
        if category == 'path':
            self.transposePath(-12) # lower path by octave (interval = -12)

    def shiftRhythmHorizontally(self, direction):
        rhythm = self.deserialize_rhythm(self.state['rhythm']['pattern']) # read rhythm and deserialize
        rhythm = rot90(rhythm, 3) # Rotate because pitches are column based.
        rhythm = rhythm.tolist()
        rhythm = self.__rotate(rhythm, direction) # directions: left = 1; right = -1
        rhythm = rot90(rhythm) # Rotate back.
        rhythm = rhythm.tolist()
        self.state['rhythm']['pattern'] = self.serialize_rhythm(rhythm) # serialize and write rhythm

    def shiftPitchHorizontally(self, direction):
        pitch = self.deserialize_pitch(self.state['pitch']['pattern']) # read pitch and deserialize
        pitch = rot90(pitch, 3) # Rotate because pitches are column based.
        pitch = pitch.tolist()
        pitch = self.__rotate(pitch, direction) # directions: left = 1; right = -1
        pitch = rot90(pitch) # Rotate back.
        pitch = pitch.tolist()
        self.state['pitch']['pattern'] = self.serialize_pitch(pitch) # serialize and write pitch

    def shiftRhythmVertically(self, direction):
        rhythm = self.deserialize_rhythm(self.state['rhythm']['pattern']) # read rhythm
        rhythm = self.__rotate(rhythm, direction) # directions: up = 1; down = -1
        self.state['rhythm']['pattern'] = self.serialize_rhythm(rhythm) # write rhythm

    def shiftPitchVertically(self, direction):
        pitch = self.deserialize_pitch(self.state['pitch']['pattern']) # read pitch
        pitch = self.__rotate(pitch, direction) # directions: up = 1; down = -1
        self.state['pitch']['pattern'] = self.serialize_pitch(pitch) # write pitch

    def transposePath(self, interval):
        path = self.state['path']['pattern'] # read path
        restIndex = []
        noteIndex = []
        temp_path = []
        new_path = []
        for i in range(len(path)):
            if path[i] == 'S':
                restIndex.append(i) # index all rests ('S')
            else:
                noteIndex.append(i) # index all notes
        for i in range(len(noteIndex)):
            temp_path.append(note.Note(path[noteIndex[i]]).pitch.midi + interval) # (1) read all notes (2) convert pitch names to MIDI pitch numbers (3) transpose
        if self.examineOverflow(temp_path, 0, 127) is True: # all MIDI pitch numbers are within 0~127
            for i in range(len(restIndex)):
                new_path[restIndex[i]] = 'S' # write all rests ('S')
            for i in range(len(noteIndex)):
                new_path[noteIndex[i]] = note.Note(temp_path[i]).nameWithOctave # convert MIDI pitch numbers to pitch names and write all notes
            self.state['path']['pattern'] = path # write path

    def adjustAmplitude(self, volume):
        amplitude = self.state['amplitude']['pattern'] # read amplitude
        for i in range(len(amplitude)):
            amplitude[i] = amplitude[i] + volume # adjust amplitude
        if self.examineOverflow(amplitude, 0, 1) is True: # all amplitudes are within 0~1
            self.state['amplitude']['pattern'] = amplitude # write amplitude
    
    def examineOverflow(self, dataList, minimum, maximum):
        for i in range(len(dataList)):
            if dataList[i] >= minimum and dataList[i] <= maximum: # grant permission and test next element until complete
                permission = True
            else: # deny permission if any element goes beyond limits
                permission = False
                break
        return permission

    def __rotate(self, l, n):
        return l[n:] + l[:n]        
   
    def __updateOrder(self, attribute, value):
        self.state[attribute]['order'] = value
        size = self.feature_sizes[attribute]
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
        
        >>> g = Generator("../resources/presets/default.yml", {})
        >>> pattern = g.deserialize_pitch(g.state['pitch']['pattern'])
        >>> g.serialize_pitch(pattern)
        [[0], [3, 0, -3], [0], [3, 0, -3], [0], [0], [3, 0, -3], [0]]
        """
        new_pattern = [[] for x in xrange(0,8)]
        for i in xrange(11):
            for j in xrange(8):
                if pattern[i][j] == 1:
                    new_pattern[j].append(5-i)
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
    
    def generate_row(self):
        """
        This method generates one row of Music21 notes according to the current state and stores it in the note buffer.
        """
        # Get the rhythm multiplier from the currently played row. If it is complete,
        # start another row. The rhythm multiplier may contain an offset (before which
        # and element is played), when the row starts with 0s.
         
        # Isn't changed by anyone else in the application.
        rhythm_generator = self.state['rhythm']['order_eng']
        rhythm_pi = rhythm_generator.next() # rhythm position indicator.
        self.state['rhythm']['row_idx'] = rhythm_pi
        row_idx = self.state['rhythm']['row_idx']
        
        # !! Hot code !! state can be changed at any moment,
        # but need a fixed rhythm pattern for the duration of the
        # function. That's why we copy.
        self.rhythm_lock.acquire()
        rhythm_pattern = copy(self.state['rhythm']['pattern'][row_idx])
        self.rhythm_lock.release()
        
        # I don't care if those change in the middle of the execution.
        bpm = self.state['bpm']
        dividor = self.state['rhythm']['dividor']
        amplitude_pattern = self.state['amplitude']['pattern']
        amplitude_generator = self.state['amplitude']['order_eng']
        path_pattern = self.state['path']['pattern']
        path_generator = self.state['path']['order_eng']
        pitch_pattern = self.state['pitch']['pattern']
        pitch_generator = self.state['pitch']['order_eng']
        
        # The row offset is the number of 0's before the 
        # first non-0 value appears on the row. 
        offset_mult = rhythm_pattern[Generator.OFFSET]
        duration = (float(offset_mult) * 60.0) / (float(dividor) * float(bpm))
        n = NoteOffset(duration)
        self.queue.put(n)
        self.incrementQueueSize()
        
        for idx, rhythm_mult in enumerate(rhythm_pattern[Generator.VALUES]):
            if idx == len([Generator.VALUES]) - 1:
                # The rhythm multiplier needs to last until the first
                # non zero value of the next row. Notice that if the next row
                # has no non-zero values, than the mult may not extend beyond that.
                rhythm_mult += offset_mult
            
            # Handle position indicators. Rhythm has to be obtained earlier
            # because the multiple notes correspond to the same rhythm position indicator.
            notes = []
            path_pi = path_generator.next()
            pitch_pi = pitch_generator.next()
            amplitude_pi = amplitude_generator.next()
            # Prepend position indices. Index positions start at 1 instead of 0.
            notes.insert(0,[path_pi + 1, 4 - rhythm_pi, pitch_pi + 1, amplitude_pi + 1])
            
            duration = (float(rhythm_mult) * 60.0) / (float(dividor) * float(bpm))
            path = path_pattern[path_pi]
            
            
            if path == 'S':
                # Add a single silent note.
                notes.append(Note(0, duration, 0))
                self.queue.put(notes)
                self.incrementQueueSize()
            else:
                # Assign velocity to instrument
                velocity = int(amplitude_pattern[amplitude_pi] * 127) % 127
                path = note.Note(path).midi
                 
                # Set the pitch modulations. If the size of the list of pitch modulations (pitches object) is
                # greater than one, than multiples notes will be played.
                pitches = pitch_pattern[pitch_pi]
                for pitch in pitches:
                    # There is always at least one pitch.
                    notes.append(Note(path+pitch, duration, velocity))
                
                if len(notes) > 1:
                    # Store in note queue
                    self.queue.put(notes)
                    self.incrementQueueSize()
                else:
                    # no pitch specified for that column
                    notes.append(Note(path,duration,0))
                    self.queue.put(notes)
                    self.incrementQueueSize()
    
    def incrementQueueSize(self):
        self.size_lock.acquire()
        self.size += 1  # Should be using queue size instead.
        size = self.size
        self.size_lock.release()
        return size
        
    def decrementQueueSize(self):
        self.size_lock.acquire()
        self.size -= 1  # Should be using queue size instead.
        size = self.size
        self.size_lock.release()
        return size
    
    def __change_instrument(self, instrument):
        i = Instrument(instrument)
        self.queue.put(i)
        self.incrementQueueSize()
    
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
                        self.generate_row()


class Note(object):
    
    def __init__(self, p, d, v):
        self.pitch = p
        self.duration = d
        self.velocity = v
    
    def __repr__(self):
        return "Note(%d,%f,%d)" % (
            self.pitch,
            self.duration,
            self.velocity
        )


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
    
    def encode_state(obj):
        str(obj)


class CyclicGenerator(RandomGenerator):
    
    def __init__(self, size):
        self.__counter = 0
        self.__size = size
        
    def next(self):
        value = self.__counter
        self.__counter = (self.__counter + 1) % self.__size
        return value
    
    def __repr__(self):
        return "CyclicGenerator"


class UniformRandomGenerator(RandomGenerator):
    
    def __init__(self, size):
        self.__size = size
    
    def next(self):
        return random.randint(0, self.__size - 1)
    
    def __repr__(self):
        return "UniformRandomGenerator"

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    g = Generator("../resources/presets/default.yml", {})
    i = 40
    for j in xrange(i):
        g.generate()
    for j in xrange(i):
        print g.queue.get()
