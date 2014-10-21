""" receiving OSC with pyOSC
https://trac.v2.nl/wiki/pyOSC
example by www.ixi-audio.net based on pyOSC documentation

this is a very basic example, for detailed info on pyOSC functionality check the OSC.py file 
or run pydoc pyOSC.py. you can also get the docs by opening a python shell and doing
>>> import OSC
>>> help(OSC)
"""
import OSC
import sys
import time, threading
import socket
import generator
import yaml
import Tkinter
import traceback
from Queue import Queue,Empty
from numbers import Number

class TouchOSC(object):
    
    def __init__(self,gen,gui,filename):
        
        self.__generator = gen
        self.__gui = gui
        
        #Use default input port 8000
        receive_address = socket.gethostbyname(socket.gethostname()), 8000
        
        try:
            self.server = OSC.ThreadingOSCServer(receive_address)
            self.client = OSC.OSCClient()
        except:
            t,v,tb = sys.exc_info()
            self.__gui.osc.insert(Tkinter.END,str(t)+":"+str(v))
        
        # this registers a 'default' handler (for unmatched messages), 
        # an /'error' handler, an '/info' handler.
        # And, if the client supports it, a '/subscribe' & '/unsubscribe' handler
        self.server.addDefaultHandlers()
        
        #Read in the oscmap
        self.oscmap = yaml.load(open(filename))
        for touchosctab in self.oscmap:
            self.server.addMsgHandler("/"+str(touchosctab),self.printing_handler)
            for touchoscop in self.oscmap[touchosctab]:
                oscaddr = "/"+str(touchosctab)+"/"+touchoscop
                self.server.addMsgHandler(oscaddr,self.printing_handler)
        
        #Set additional handlers
        self.server.addMsgHandler('/quit',self.printing_handler)
        self.server.addMsgHandler('/connect',self.connect_handler)
        self.server.addMsgHandler('/basic/reset',self.reset_handler)
        self.server.daemon = True
        
        #Used for transfer of OSC messages:
        self.__orderDict = {0:"cyclic",1:"markov",2:"uniformRandom"}
        self.__pathDict = {
                           "C2":"/4/1","C#2":"/4/2","D2":"/4/3","D#2":"/4/4","E2":"/4/5","F2":"/4/6",
                           "F#2":"/4/7","G2":"/4/8","G#2":"/4/9","A2":"/4/10","A#2":"/4/11","B2":"/4/12",
                           "C3":"/3/1","C#3":"/3/2","D3":"/3/3","D#3":"/3/4","E3":"/3/5","F3":"/3/6",
                           "F#3":"/3/7","G3":"/3/8","G#3":"/3/9","A3":"/3/10","A#3":"/3/11","B3":"/3/12",
                           "C4":"/2/1","C#4":"/2/2","D4":"/2/3","D#4":"/2/4","E4":"/2/5","F4":"/2/6",
                           "F#4":"/2/7","G4":"/2/8","G#4":"/2/9","A4":"/2/10","A#4":"/2/11","B4":"/2/12",
                           "C5":"/1/1","C#5":"/1/2","D5":"/1/3","D#5":"/1/4","E5":"/1/5","F5":"/1/6",
                           "F#5":"/1/7","G5":"/1/8","G#5":"/1/9","A5":"/1/10","A#5":"/1/11","B5":"/1/12"
                           }
        self.__reversePathDict = inv_map = {v:k for k, v in self.__pathDict.items()}
        self.__alphabetDict = {
                            1:"a",2:"b",3:"c",4:"d",5:"e",6:"f",7:"g",8:"h",9:"i",10:"j",11:"k",12:"l",13:"m",14:"n",15:"o",16:"p"
                            }
        self.__reverseAlphabetDict = {
                            "a":1,"b":2,"c":3,"d":4,"e":5,"f":6,"g":7,"h":8,"i":9,"j":10,"k":11,"l":12,"m":13,"n":14,"o":15,"p":16
                            }
        
        #Check registered callback (one per entry in the config file)
        #         for addr in self.server.getOSCAddressSpace():
        #             print addr
        
        #Queue for osc messages
        self.__messageQueue = Queue()
    
    def connect_handler(self,addr, tags, data, source):
        """
        Connects to the phone client and calls send_state
        """
        try:
            print "connecting"
            self.ip = data[0]
            self.port = data[1]
            self.__gui.addToOSC("Phone ip address : " + self.ip + ", phone port : " + str(self.port) + "\n")
            address = self.ip,self.port
            self.client.connect(address)
            self.send_state()
        except:
            t,v,tb = sys.exc_info()
            print str(t)
            print str(v)
            traceback.print_tb(tb)
    
    def send_state(self):
        """
        Sends the current state of the python application to the device.
        """
        addresses = [] #Actual values
        prereqs = [] #Reset values
        print "sending state"
        for attribute in self.__generator.state:
            content = self.__generator.state[attribute]
            if attribute=='instrument':
                addresses.append('/basic/instrument '+str(content))
            elif attribute=='bpm':
                addresses.append('/basic/bpm '+str(content))
            elif attribute=='path':
                for i in range(4):
                    for j in range(12):
                        prereqs.append('/path/list/'+str(i+1)+"/"+str(j+1)+" 0")
                for path in content['list']:
                    addresses.append('/path/list'+str(self.__pathDict[path])+" 1")
            elif attribute=='rhythm':
                for i in range(16):
                    prereqs.append('/rhythm/list/'+str(i+1)+" 0")
                for idx,r in enumerate(content['list']):
                    addresses.append('/rhythm/list/'+str(idx+1)+" "+str(float(r)))
            elif attribute=='field':
                for letter in self.__alphabetDict.values()[:8]:
                    prereqs.append('/pitch/field'+str(letter)+" 0")
                for idx,l in enumerate(content['list']):
                    addresses.append('/pitch/field'+str(self.__alphabetDict[idx+1])+" "+str(float(l)))
            elif attribute=='octave':
                for letter in self.__alphabetDict.values()[:4]:
                    prereqs.append('/pitch/octave'+str(letter)+" 0")
                for idx,l in enumerate(content['list']):
                    addresses.append('/pitch/octave'+str(self.__alphabetDict[idx+1])+" "+str(float(l)))
            elif attribute=='amplitude':
                for letter in self.__alphabetDict.values()[:4]:
                    prereqs.append('/volume/amplitude'+str(letter)+" 0")
                for idx,l in enumerate(content['list']):
                    addresses.append('/volume/amplitude'+str(self.__alphabetDict[idx+1])+" "+str(float(l)))
            elif attribute=='panning':
                for letter in self.__alphabetDict.values()[:4]:
                    prereqs.append('/volume/panning'+str(letter)+" 0")
                for idx,l in enumerate(content['list']):
                    addresses.append('/volume/panning'+str(self.__alphabetDict[idx+1])+" "+str(float(l)))
            else:
                #Not recognized
                pass
        print "==========PREREQUISITES============"
        for prereq in prereqs:
            print prereq
            addr,value = prereq.split(" ")
            msg = OSC.OSCMessage()
            msg.setAddress(addr)
            msg.append(value)
            self.client.send(msg)
        print "============ADDRESSES=============="
        for address in addresses:
            print address
            addr,value = address.split(" ")
            msg = OSC.OSCMessage()
            msg.setAddress(addr)
            msg.append(value)
            self.client.send(msg)
    
    def __send_markov(self,markov_args):
        
        pass
    
    #Rounding value for rhythm dividor
    def __dividorValue(self,r):
        if r < .25:
            return 2
        elif r < .5:
            return 4
        elif r < .75:
            return 6
        else:
            return 8 
    
    #Rounding value for rhythm
    def __rhythmValue(self,r):
        if r < .8:
            return 0
        elif r < 1.6:
            return 1
        elif r < 2.4:
            return 2
        elif r < 3.2:
            return 3
        else:
            return 4
    
    def __order(self,val):
        if val < .67:
            return 0
        elif val < 1.34:
            return 1
        else:
            return 2
    
    def run(self):
        try:
            st = threading.Thread( target = self.server.serve_forever )
            st.start()
            print "OSC server running on port 8000..."
            while True:
                try:
                    msg = self.__messageQueue.get()
                    if msg.strip()=='/quit []':
                        break
                    else:
                        addr,val = msg.strip().split(" ")
                        if addr=='/basic/bpm':
                            val = int(round(float(val[1:][:-1])))
                            self.__gui.update('bpm',val)
                        elif addr=='/basic/instrument':
                            val = int(round(float(val[1:][:-1])))
                            self.__gui.update('instrument',val)
                        elif addr.startswith('/path/order'):
                            self.update_path('order', val)
                        elif addr.startswith('/path/list'):
                            self.update_path(("/"+"/".join(addr.split("/")[-2:])),val)
                        elif addr.startswith('/rhythm/order'):
                            self.update_rhythm('order', val)
                        elif addr.startswith('/rhythm/list'):
                            self.update_rhythm(addr.split("/")[-1], val)
                        elif addr.startswith('/rhythm/dividor'):
                            self.update_rhythm('dividor', val)
                        elif addr.startswith('/pitch/field'):
                            if addr[-5:]=='order': #if the last 5 letters of the address are "order"
                                self.__gui.update('field order',self.__orderDict[self.__order(float(val[1:][:-1]))])
                            else:
                                self.__gui.update('field list '+str(self.__reverseAlphabetDict[addr[-1]]),int(round(float(val[1:][:-1]))))
                        elif addr.startswith('/pitch/octave'):
                            if addr[-5:]=='order':#if the last 5 letters of the address are "order"
                                self.__gui.update('octave order',self.__orderDict[self.__order(float(val[1:][:-1]))])
                            else:
                                self.__gui.update('octave list '+str(self.__reverseAlphabetDict[addr[-1]]),int(round(float(val[1:][:-1]))))
                        else:
                            pass
                    self.__gui.addToOSC(msg)
                except Empty:
                    time.sleep(.05)
                    pass
                except:
                    t,v,tb = sys.exc_info()
                    print t
                    print v
                    traceback.print_tb(tb)
            self.timed_out= True
            self.server.close()
            self.client.close()
            st.join()
        except:
            t2,v2,tb2 = sys.exc_info()
            print t2
            print v2
            traceback.print_tb(tb2)
    
    def update_rhythm(self,type,val):
        if type=='order':
            self.__gui.update('rhythm order',self.__orderDict[self.__order(float(val[1:][:-1]))])
        elif type=='dividor':
            self.__gui.update('rhythm dividor',self.__dividorValue(float(val[1:][:-1])))
        else: #Needs to stay as else (type will be the index of the rhythm to update)
            self.__gui.update('rhythm list '+type,self.__rhythmValue(float(val[1:][:-1])))
    
    def update_path(self,type,val):
        if type=='order':
            val = self.__order(float(val[1:][:-1]))
            self.__gui.update('path order',self.__orderDict[val])
        else:
            if not float(val[1:][:-1])==0.0:
                if len(self.__generator.state['path']['list'])>=8:
                    letter = self.__generator.state['path']['list'][0]
                    msg = OSC.OSCMessage()
                    msg.setAddress('/path/list'+self.__pathDict[letter])
                    msg.append(0.0)
                    self.client.send(msg)
            self.__gui.update('path list',self.__reversePathDict[type]) 
    
    def reset_handler(self,addr, tags, data, source):
        try:
            if data[0]==1.0: #if reset is toggled 
                self.__generator.loadState()
                self.send_state()
                print "state sent"
        except:
            print sys.exc_info()
    
    #Simple handler that justs prints
    def printing_handler(self,addr, tags, data, source):
        try:
            msg = "{} {}\n".format(addr,data)
            self.__messageQueue.put(msg)
        except:
            print sys.exc_info()
