import yaml
import logging
import random
import time
import utils
import sys
import traceback
from Queue import Queue
from music21 import note
from string import ascii_lowercase
from athenaCL.libATH import grammar
from athenaCL.libATH import markov

class Generator(object):
    
    def __init__(self,filename):
        """
        >>> g = Generator("../resources/state.yml")
        >>> g.state["instrument"]
        45
        >>> g.state["bpm"]
        120
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
        self.sizes = {'rhythm':16,'field':8,'octave':4,'amplitude':4,'path':8,'panning':4}
        self.fills = {'rhythm':0,'field':0,'octave':0,'amplitude':.5,'panning':.5}
        self.mkvpathsmap = {}
        self.mkvpathsmap['idx']=[]
        self.mkvpathsmap['weight']=[]
#         self.mkvmap = {}
#         for attributeName in ['rhythm']:
#             self.mkvmap[attributeName] ={}
#             self.mkvmap[attributeName]['idx']=[]
#             self.mkvmap[attributeName]['weight']=[]
        self.state = self.readState()
        self.__bindMarkovPath()
    
    def readState(self):
        parameters = yaml.load(open(self.file))
        for attributeName in ['rhythm','amplitude','panning','field','octave']:
            order = parameters[attributeName]['order']
            parameters[attributeName]['order'] = order['type']
            parameters[attributeName]['order_args'] = order['args']
            self.__randomMarkov(parameters,attributeName)
            self.__fillList(parameters, attributeName, self.sizes[attributeName], self.fills[attributeName])
        parameters['path']['list'] = utils.make_set(parameters['path']['list'])
        self.__computeOrder(parameters,"rhythm")
        self.__computeOrder(parameters,"field")
        self.__computeOrder(parameters,"octave")
        self.__computeOrder(parameters,"amplitude")
        self.__computeOrder(parameters,"panning")
        self.__computeOrder(parameters,"path")
        return parameters
    
    def __fillList(self,parameters,attribute,size,fillVal):
        for i in range(len(parameters[attribute]['list']),size):
            parameters[attribute]['list'].append(fillVal)
    
    def __computeOrder(self,parameters,attributeName):
        """
        This method computes the order parameter of some of the attributes of the state
        """
        
        if attributeName not in ["path","rhythm","field","octave","amplitude","panning"]:
            raise Exception("Attempting to assign an order to an invalid attribute!")
        else:
            size = len(parameters[attributeName]['list'])
            #If not already set, put a random value here.
            parameters[attributeName]['order'] = order['type']
            parameters[attributeName]['order_args'] = order['args']
            if order['type']=='cyclic':
                parameters[attributeName]['order_eng'] = CyclicGenerator(size)
            elif order['type']=='uniformRandom':
                parameters[attributeName]['order_eng'] = UniformRandomGenerator(size)
            elif order['type']=='markov':
                parameters[attributeName]['order_eng'] = MarkovGenerator(order['args'])
            else:
                raise Exception("Order type %s is invalid!", order['type'])
        return
    
    def __randomMarkov(self,parameters,attributeName):
        #if not attributeName=='path':
        print "random markov"
        max = self.sizes[attributeName]
        size = len(parameters[attributeName]['list'])
        print str(parameters[attributeName])
        if 'order_args' not in parameters[attributeName]:
            print "random markov order args not in " + attributeName
            parameters[attributeName]['order_args'] = self.__randomMarkovString(size)
        elif parameters[attributeName]['order_args'] == 'None':
            print "random markov order args for " + attributeName + " is None"
            parameters[attributeName]['order_args'] = self.__randomMarkovString(size)
        else:
            try:
                print "random markov else"
                #Should work since markov and list have the same size
                ws = [w.split("=")[1] for w in parameters[attributeName]['order_args'].split(":")[1][1:-1].split("|")]
                
                for i in range(size,max):
                    ws.append(0)
                letters = ""
                weights = ""
                print attributeName + ":" + str(ws) + "size="+str(size) + ",max="+str(max)
                for i in range(max):
                    letters += str(self.alphabet[i])+"{"+str(i)+"}"
                    weights += str(self.alphabet[i])+"="+ws[i]+"|"
                weights = weights[:-1]
                parameters[attributeName]['order_args'] = letters+":{"+weights+"}"
            except:
                print "Make sure order_args and list have the same size for " + attributeName + " in your config file!"
                t,v,tb = sys.exc_info()
                print t
                print v
                traceback.print_tb(tb)
    
#     def __bindPath(self,attributeName):
#         if 'order_args' not in self.state[attributeName]:
#             self.state[attributeName]['order_args'] = self.__randomMarkovString(len(self.state['path']['list']))
#         elif self.state[attributeName]['order_args'] == 'None':
#             self.state[attributeName]['order_args'] = self.__randomMarkovString(len(self.state['path']['list']))
#         weights = self.state[attribute]['order_args'].split(":")[1][1:-1].split("|")
#         try:
#             for idx,p in enumerate(self.state['path']['list']):
#                 self.mkvpathsmap['idx'].append(idx)
#                 self.mkvpathsmap['weight'].append(weights[idx].split("=")[1])
#         except:
#             t,v,tb = sys.exc_info()
#             print t
#             print v
#             traceback.print_tb(tb)

    def __bindMarkovPath(self):
        #This method binds the path's markov weights with its list. This is required because the number of elements in the path is dynamic.
        if 'order_args' not in self.state['path']:
            self.state['path']['order_args'] = self.__randomMarkovString(len(self.state['path']['list']))
        elif self.state['path']['order_args'] == 'None':
            self.state['path']['order_args'] = self.__randomMarkovString(len(self.state['path']['list']))
        weights = self.state['path']['order_args'].split(":")[1][1:-1].split("|")
        try:
            for idx,p in enumerate(self.state['path']['list']):
                self.mkvpathsmap['idx'].append(idx)
                self.mkvpathsmap['weight'].append(weights[idx].split("=")[1])
        except:
            t,v,tb = sys.exc_info()
            print t
            print v
            traceback.print_tb(tb)
            
    def __updatePathMarkov(self):
        letters = ""
        weights = ""
        for i in range(len(self.mkvpathsmap['idx'])):
            letters += str(self.alphabet[i])+"{"+str(self.mkvpathsmap['idx'][i])+"}"
            weights += str(self.alphabet[i])+"="+str(self.mkvpathsmap['weight'][i])+"|"
        weights=weights[:-1]
        mkv = letters+":{"+weights+"}"
        self.state['path']['order_args'] = mkv
        self.state['path']['order_eng'] = MarkovGenerator(mkv) 
    
    def update(self,attribute,value):
        try:
            if attribute=="bpm":
                self.state['bpm']=value
            elif attribute=="instrument":
                self.state['instrument']=value
                self.__change_instrument(value)
            elif attribute=="path order":
                self.__updateOrder('path',value)
            elif attribute=='path list':
                if value in self.state['path']['list']:
                    #If the note is already in the path, it has to be removed.
                    idx = self.state['path']['list'].index(value)
                    del self.state['path']['list'][idx]
                    del self.mkvpathsmap['idx'][idx]
                    del self.mkvpathsmap['weight'][idx]
                    self.__updatePathMarkov()
                else: 
                    #Otherwise it has to be addded. If there are more than 8 notes, the first note in the list has to be removed as well.
                    if len(self.state['path']['list'])>=8:
                        del self.state['path']['list'][0]
                        del self.mkvpathsmap['idx'][0]
                        del self.mkvpathsmap['weight'][0]
                    found = False
                    for i in range(len(self.mkvpathsmap['idx'])):
                        if i not in self.mkvpathsmap['idx']:
                            self.state['path']['list'].append(value)
                            self.mkvpathsmap['idx'].append(i)
                            self.mkvpathsmap['weight'].append(10) #TODO: Warning need to change when covering markov
                            found = True
                            break
                    if not found:
                        self.state['path']['list'].append(value)
                        self.mkvpathsmap['idx'].append(len(self.mkvpathsmap['idx']))
                        self.mkvpathsmap['weight'].append(10) #TODO: Warning need to change when covering markov
                    self.__updatePathMarkov()
            elif attribute=="rhythm order":
                self.__updateOrder('rhythm',value)
            elif attribute.startswith("rhythm list"):
                self.state['rhythm']['list'][int(attribute.split(" ")[-1])] = value
            else:
                #Do nothing
                print "Nothing happens"
                return False
            return True
        except:
            t,v,tb = sys.exc_info()
            print t
            print v
            traceback.print_tb(tb)
            return False
    
    def __updateList(self,attribute,value):
        pass
    
    def __updateOrder(self,attribute,value):
        if not value==self.state[attribute]['order']:
            self.state[attribute]['order'] = value
            size = len(self.state[attribute]['list'])
            if value=="cyclic":
                self.state[attribute]['order_eng'] = CyclicGenerator(size)
            elif value=="uniformRandom":
                self.state[attribute]['order_eng'] = UniformRandomGenerator(size)
            else: 
                self.state['path']['order_eng'] = MarkovGenerator(self.state['path']['order_args'])
    
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
        pitch = self.state['path']['list'][self.mkvpathsmap['idx'].index(self.state['path']['order_eng'].next())]
        if pitch=='S':
            pitch = 0
        else:
            pitch = note.Note(pitch).midi
            #Alter note using field parameter
            field = self.state['field']['list'][self.state['field']['order_eng'].next()]
            pitch += field
            #Alter note using octave parameter
            octave = self.state['octave']['list'][self.state['octave']['order_eng'].next()]*12
            pitch += octave
            #Keep values between bounds
            if pitch < 0:
                pitch = 0
            if pitch > 127:
                pitch = 127
        
        #Assign velocity to instrument 
        velocity = int(self.state['amplitude']['list'][self.state['amplitude']['order_eng'].next()] * 127) % 127
        
        #Store in note buffer
        n = Note(pitch,duration,velocity)
        self.queue.put(n)
        self.size += 1
        return
    
    def __change_instrument(self,instrument):
        i = Instrument(instrument)
        self.queue.put(i)
    
    def __setupBuffer(self):
        """ This method sets up initial MIDI instrument, panning, volume"""
        #Setup midi instrument
        self.__change_instrument(self.state['instrument'])
        #Setup panning
        
        #Setup volume
        return
    
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
    g = Generator("../resources/state.yml")
    g.generate()
    g.generate()
    g.generate()
    print vars(g.queue.get())
    print vars(g.queue.get())
    print vars(g.queue.get())