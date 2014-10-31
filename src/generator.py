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

class Generator(object):
    
    def __init__(self, filename, config):
        """
        >>> g = Generator("../resources/default.yml")
        >>> g.state["instrument"]
        45
        >>> g.state["bpm"]
        110
        """        
        #The state of the generator describes what the generator will generate.
        #It follows the AthenaCL standard.
        self.file = filename
        
        self.loadState()
        
        #The Notebuffer is where generated notes are stored before being sent to 
        #the synthesizer
        self.queue = Queue()
        
        #This variable gives the size of the queue. This is required because Mac OS X
        #does not support queue.qsize()
        self.size = 0
        
        #This is used to say if the music generation is active or not.
        self.active = True
        
        #This is used by the gui for playing/pausing
        self.playing = False
    
    def loadState(self):
        #This is a mapping between the path markov weights and the paths themselves. This
        #mapping is required because the index of a path may vary in the list.
        self.alphabet = list(ascii_lowercase)
        self.sizes = {'rhythm':16,'field':16,'amplitude':16,'path':8,'panning':16}
        self.fills = {'rhythm':1,'field':0,'amplitude':.5,'path':'S','panning':0}
        self.mkvpathsmap = {}
        self.mkvpathsmap['idx']=[]
        self.mkvpathsmap['weight']=[]
        self.state = self.readState()
        # self.__bindMarkovAndPath() # THIS METHOD SHOULD NO LONGER BE NECESSARY XXX
    
    def readState(self):
        # Read algorithm state
        with open(self.file) as f:
            parameters = yaml.load(f)

        #Fills the blanks for all of the non markov stuff.
        for attributeName in ['rhythm','amplitude','path','panning','field']:
            # TODO: check if this renaming is necessary
            order = parameters[attributeName]['order']
            parameters[attributeName]['order'] = order['type']
            parameters[attributeName]['order_args'] = order['args']
            #Fills the list if not of max size
            self.__fillList(parameters, attributeName, self.sizes[attributeName], self.fills[attributeName])
            #Assign random weights to the markov
            self.__randomMarkov(parameters,attributeName)
            #Assign the order engine
            self.__computeOrderEng(parameters,attributeName)
        
        # Indicates currently selected path on Path Map. Value can be 0-7.
        parameters['path']['selected'] = 0

        return parameters
    
    def __fillList(self,parameters,attribute,size,fillVal):
        """
        Fills parameters list with fill values for the corresponding attribute.
        """
        for i in xrange(len(parameters[attribute]['list']),size):
            parameters[attribute]['list'].append(fillVal)
    
    def __computeOrderEng(self,parameters,attributeName):
        """
        This method computes the order parameter of some of the attributes of the state
        """
        if attributeName not in ["path","rhythm","field","amplitude","panning"]:
            raise Exception("Attempting to assign an order to an invalid attribute!")
        else:
            size = len(parameters[attributeName]['list'])
            #If not already set, put a random value here.
            if parameters[attributeName]['order']=='cyclic':
                parameters[attributeName]['order_eng'] = CyclicGenerator(size)
            elif parameters[attributeName]['order']=='uniformRandom':
                parameters[attributeName]['order_eng'] = UniformRandomGenerator(size)
            elif parameters[attributeName]['order']=='markov':
                parameters[attributeName]['order_eng'] = MarkovGenerator(parameters[attributeName]['order_args'])
            else:
                raise Exception("Order type %s is invalid!", parameters[attributeName]['order'])
        return
    
    def __randomMarkov(self,parameters,attributeName):
        """
        This method creates random markov values when they are not specified.
        To self => is this necessary (can fill values be used instead)?
        """
        if 'order_args' not in parameters[attributeName]:
            parameters[attributeName]['order_args'] = self.__randomMarkovString(self.sizes[attributeName])
        elif parameters[attributeName]['order_args'] == 'None':
            parameters[attributeName]['order_args'] = self.__randomMarkovString(self.sizes[attributeName])
        else:
            try:
                #Should work since markov and list have the same size
                ws = [w.split("=")[1] for w in parameters[attributeName]['order_args'].split(":")[1][1:-1].split("|")]
                original_size = len(ws)
                for i in range(original_size,self.sizes[attributeName]):
                    ws.append(random.randint(1,20))
                letters = ""
                weights = ""
                for i in range(self.sizes[attributeName]):
                    letters += str(self.alphabet[i])+"{"+str(i)+"}"
                    weights += str(self.alphabet[i])+"="+str(ws[i])+"|"
                weights = weights[:-1]
                parameters[attributeName]['order_args'] = letters+":{"+weights+"}"
            except:
                print "Make sure order_args and list have the same size for " + attributeName + " in your config file!"
                t,v,tb = sys.exc_info()
                print t
                print v
                traceback.print_tb(tb)

    def update(self,attribute,value):
        try:
            if attribute=="bpm":
                self.state['bpm']=value
            elif attribute=="instrument":
                self.state['instrument']=value
                self.__change_instrument(value)
            elif attribute=="path order":
                self.__updateOrder('path',value)
            elif attribute.startswith('path list'):
                idx = int(attribute.split(" ")[-1])-1
                selected_path = self.state['path']['selected']
                self.state['path']['list'][selected_path] = value
            elif attribute=='path select':
                self.state['path']['selected'] = value
            elif attribute=="rhythm order":
                self.__updateOrder('rhythm',value)
            elif attribute.startswith("rhythm list"):
                idx = int(attribute.split(" ")[-1])-1
                self.state['rhythm']['list'][idx] = value
            elif attribute.startswith("rhythm dividor"):
                self.state['rhythm']['dividor'] = value
            elif attribute.startswith("field list"):
                idx = int(attribute.split(" ")[-1])-1
                self.state['field']['list'][idx] = value
            elif attribute.startswith("field order"):
                self.__updateOrder('field',value)
            elif attribute.startswith('amplitude list'):
                idx = int(attribute.split(" ")[-1])-1
                self.state['amplitude']['list'][idx] = value
            elif attribute.startswith("amplitude order"):
                self.__updateOrder('amplitude',value)
            else:
                #Should not happen
                raise Exception("generator.update() called with invalid attribute {}".format(attribute))
            return True
        except:
            t,v,tb = sys.exc_info()
            print t
            print v
            traceback.print_tb(tb)
            return False
    
    def __updateOrder(self,attribute,value):
        self.state[attribute]['order'] = value
        size = len(self.state[attribute]['list'])
        if value=="cyclic":
            self.state[attribute]['order_eng'] = CyclicGenerator(size)
        elif value=="uniformRandom":
            self.state[attribute]['order_eng'] = UniformRandomGenerator(size)
        elif value=="markov": 
            self.state[attribute]['order_eng'] = MarkovGenerator(self.state[attribute]['order_args'])
        else:
            print "Unknown order: %s !" % value
    
    def __randomMarkovString(self,size):
        letters = ""
        weights = ""
        for i in range(size):
            letters += str(self.alphabet[i])+"{"+str(i)+"}"
            weights += str(self.alphabet[i])+"="+str(random.randint(1,20))+"|"
        weights = weights[:-1]
        mkv = letters+":{"+weights+"}"
        return mkv
    
    def generate(self):
        """
        This method generates one Music21 note according to the current state and stores it in the note buffer
        """
        #Define note duration from rhythm and bpm
        div = self.state['rhythm']['dividor']
        mult = self.state['rhythm']['list'][self.state['rhythm']['order_eng'].next()]
        duration = (float(mult) * 60.0) / (float(div) * float(self.state['bpm']))
        
        #Define note pitch from path. An "S" in the path can be used for silence.
        pitch = self.state['path']['list'][self.state['path']['order_eng'].next()]
        
        if pitch=='S':
            pitch = 0
            silent = True
        else:
            pitch = note.Note(pitch).midi
            #Alter note using field parameter
            field = self.state['field']['list'][self.state['field']['order_eng'].next()]
            pitch += field
            #Keep values between bounds
            if pitch < 0:
                pitch = 0
            if pitch > 127:
                pitch = 127
            silent = False
        
        #Assign velocity to instrument
        if silent:
            velocity = 0
        else:
            velocity = int(self.state['amplitude']['list'][self.state['amplitude']['order_eng'].next()] * 127) % 127
        
        #Store in note buffer
        n = Note(pitch,duration,velocity)
        self.queue.put(n)
        self.size += 1 # Should be using queue size instead.
        return
    
    def __change_instrument(self,instrument):
        i = Instrument(instrument)
        self.queue.put(i)
    
    def __setupBuffer(self):
        """ This method sets up initial MIDI instrument, panning, volume"""
        #Setup midi instrument
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
    def __init__(self,p,d,v):
        self.pitch = p
        self.duration = d
        self.velocity = v
        
class Instrument(object):
    def __init__(self,instrument):
        self.type = instrument

class RandomGenerator(object):
    def next(self):
        """ Generates a random value using the generator."""
        return

class CyclicGenerator(RandomGenerator):
    def __init__(self,size):
        self.__counter = 0
        self.__size = size
    def next(self):
        self.__counter = (self.__counter + 1) % self.__size
        return self.__counter

class UniformRandomGenerator(RandomGenerator):
    def __init__(self,size):
        self.__size = size
    
    def next(self):
        return random.randint(0,self.__size-1)

class MarkovGenerator(RandomGenerator):
    def __init__(self,args):
        self.__mkv = markov.Transition()
        self.__mkv.loadTransition(args)
        self.__order = self.__mkv.getOrderMax()
        self.__past = []
    
    def next(self):
        value = self.__mkv.next(random.random(),self.__past,self.__order)
        self.__past.append(value)
        if len(self.__past) > self.__order:
            self.__past.pop(0)
        return int(value)

#!!! FIXME: The grammar generator is not working
class GrammarGenerator(RandomGenerator):
    def __init__(self,args):
        self.__g = grammar.Grammar()
        self.__g.load(args)
    
    def next(self):
        return int(self.__g.next())

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    g = Generator("../resources/default.yml")
    g.generate()
    g.generate()
    g.generate()
    print vars(g.queue.get())
    print vars(g.queue.get())
    print vars(g.queue.get())
