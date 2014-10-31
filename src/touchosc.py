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
from pprint import pprint
from Queue import Queue,Empty
from numbers import Number

class TouchOSC(object):
    
    def __init__(self,gen,gui,filename,config):

        self.__generator = gen
        self.__gui = gui
        self.devicePort = config['device_port']
        self.applicationPort = config['application_port']
        
        # Creates a OSC server and client
        self.update_application_server() 

        # this registers a 'default' handler (for unmatched messages), 
        # an /'error' handler, an '/info' handler.
        # And, if the client supports it, a '/subscribe' & '/unsubscribe' handler
        self.server.addDefaultHandlers()
        
        #Read in the oscmap
        with open(filename) as f:
            self.oscmap = yaml.load(f)
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
        self.__orderDict = {1:"cyclic",2:"markov",3:"uniformRandom"}
        self.__reverseOrderDict = {v:k for k, v in self.__orderDict.items()}
        
        # Notice that 1/12 is a special value (translates into the silent value).
        self.__pathDict = {
                           "C2":"/4/1","C#2":"/4/2","D2":"/4/3","D#2":"/4/4","E2":"/4/5","F2":"/4/6",
                           "F#2":"/4/7","G2":"/4/8","G#2":"/4/9","A2":"/4/10","A#2":"/4/11","B2":"/4/12",
                           "C3":"/3/1","C#3":"/3/2","D3":"/3/3","D#3":"/3/4","E3":"/3/5","F3":"/3/6",
                           "F#3":"/3/7","G3":"/3/8","G#3":"/3/9","A3":"/3/10","A#3":"/3/11","B3":"/3/12",
                           "C4":"/2/1","C#4":"/2/2","D4":"/2/3","D#4":"/2/4","E4":"/2/5","F4":"/2/6",
                           "F#4":"/2/7","G4":"/2/8","G#4":"/2/9","A4":"/2/10","A#4":"/2/11","B4":"/2/12",
                           "C5":"/1/1","C#5":"/1/2","D5":"/1/3","D#5":"/1/4","E5":"/1/5","F5":"/1/6",
                           "F#5":"/1/7","G5":"/1/8","G#5":"/1/9","A5":"/1/10","A#5":"/1/11","S":"/1/12"
                           }
        self.__reversePathDict = {v:k for k, v in self.__pathDict.items()}
        self.__alphabetDict = {
                            1:"a",2:"b",3:"c",4:"d",5:"e",6:"f",7:"g",8:"h",9:"i",10:"j",11:"k",12:"l",13:"m",14:"n",15:"o",16:"p"
                            }
        self.__reverseAlphabetDict = {
                            "a":1,"b":2,"c":3,"d":4,"e":5,"f":6,"g":7,"h":8,"i":9,"j":10,"k":11,"l":12,"m":13,"n":14,"o":15,"p":16
                            }
        
        #Queue for osc messages
        self.__messageQueue = Queue()
    
    def update_application_server(self):
        """
        Creates and starts a OSC server. Creates but does not start a OSC client.
        """
        # Close OSC client and server if they exist
        if hasattr(self, 'server'):
            self.server.close()
        if hasattr(self, 'client'):
            self.client.close()
        # Create OSC server and client
        receive_address = socket.gethostbyname(socket.gethostname()), self.applicationPort        
        try:
            self.server = OSC.ThreadingOSCServer(receive_address)
            self.client = OSC.OSCClient()
        except:
            t,v,tb = sys.exc_info()
            self.__gui.osc.insert(Tkinter.END,str(t)+":"+str(v))

    
    def connect_handler(self,addr, tags, data, source):
        """
        Connects to the phone client and calls send_state
        """
        try:
            print "connecting"
            self.deviceIP = data[0]
            self.devicePort = data[1]
            self.applicationPort = data[2]
            self.__gui.addToOSC(
                    "Device IP: %s, device port : %d, application port : %d" % (
                        self.deviceIP,
                        self.devicePort,
                        self.applicationPort
                    )
            )
            address = self.deviceIP, self.devicePort
            # TODO: currently will not update application port correctly.
            # self.update_application_server()
            self.ip_port = "%s:%d" % (self.deviceIP, self.devicePort)
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
        state_addresses = [] # Values specified in the state 
        default_addresses = [] # Values required for display but not mentioned in state
        print "============= State being sent ... ==============="
        pprint(self.__generator.state)
        for attribute in self.__generator.state:
            content = self.__generator.state[attribute]
            if attribute=='instrument':
                # Instrument value and label
                state_addresses.append('/basic/instrument '+str(content))
                state_addresses.append('/basic/instrumentValue '+str(content))
            elif attribute=='bpm':
                # BPM value and label
                state_addresses.append('/basic/bpm '+str(content))
                state_addresses.append('/basic/bpmValue '+str(content))
            elif attribute=='path':
                # Path board default values
                for i in range(4):
                    for j in range(12):
                        default_addresses.append('/path/list/'+str(i+1)+"/"+str(j+1)+" 0")
                for i in range(8):
                    default_addresses.append('/path/chosen%d %s' % (i+1,'?'))
                selected_path = content['selected']
                path = content['list'][selected_path]
                # The path value mentioned here is a note string (e.g. 'C3')
                state_addresses.append('/path/list'+ str(self.__pathDict[path])+" 1")
                state_addresses.append('/path/select/1/%d 1' % (selected_path+1))
                # Path chosen labels
                for idx, path in enumerate(content['list']):
                    state_addresses.append('/path/chosen'+ str(idx+1)+ ' '+ path)
                # Path generator option
                state_addresses.append('/path/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
                # TODO: Put the send instructions for the path markov state here.
            elif attribute=='rhythm':
                # Default rhythm patterns
                for i in range(16):
                    default_addresses.append('/rhythm/list/'+str(i+1)+" 0")
                    default_addresses.append('/rhythm/lr'+str(i+1)+" 0")
                # State specified rhythm patterns
                for i,r in enumerate(content['list']):
                    state_addresses.append('/rhythm/list/'+str(i+1)+" "+str(r))
                    state_addresses.append('/rhythm/lr'+str(i+1)+" "+str(r))
                # Rhythm dividor value and label
                state_addresses.append('/rhythm/dividor ' + str(self.__reverseDividorValue(content['dividor'])))
                state_addresses.append('/rhythm/dividorValue ' + str(content['dividor']))
                # Rhyhtm generator option
                state_addresses.append('/rhythm/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            # TODO: State is defined using the "field" keyword while the interface uses "pitch".
            # A single naming should be used.
            elif attribute=='field':
                # Default pitch pattern
                for i in range(16):
                    default_addresses.append('/pitch/list/'+str(i+1)+" 0")
                    default_addresses.append('/pitch/lp'+str(i+1)+" 0")
                for i,p in enumerate(content['list']):
                    state_addresses.append('/pitch/list/'+ str(i+1)+ " "+ str(p))
                    state_addresses.append('/pitch/lp'+ str(i+1)+ " "+ str(p))
                # Pitch generator option
                state_addresses.append('/pitch/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            elif attribute=='amplitude':
                # Default amplitude pattern
                for i in range(16):
                    default_addresses.append('/amplitude/list/'+str(i+1)+" 0")
                    default_addresses.append('/amplitude/l'+str(i+1)+" 0")
                for i,p in enumerate(content['list']):
                    state_addresses.append('/amplitude/list/'+ str(i+1)+ " "+ str(p))
                    state_addresses.append('/amplitude/l'+ str(i+1)+ " "+ str(p))
                # Amplitude generator option
                state_addresses.append('/amplitude/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            elif attribute=='panning':
                # Default panning pattern
                for i in range(16):
                    default_addresses.append('/panning/list/'+str(i+1)+" 0")
                    default_addresses.append('/panning/l'+str(i+1)+" 0")
                for i,p in enumerate(content['list']):
                    state_addresses.append('/panning/list/'+ str(i+1)+ " "+ str(p))
                    state_addresses.append('/panning/l'+ str(i+1)+ " "+ str(p))
                # Panning generator option
                state_addresses.append('/panning/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            else:
                #Not recognized
                pass
        print "==========PREREQUISITES============"
        for packet in default_addresses:
            addr, value = packet.split(" ")
            self.send_message(addr,value)
        print "============ADDRESSES=============="
        for packet in state_addresses:
            addr,value = packet.split(" ")
            self.send_message(addr,value)
    
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
    
    #Rounding value for rhythm dividor
    def __reverseDividorValue(self,r):
        if r == 2:
            return .1
        elif r == 4:
            return .35
        elif r == 6:
            return .6
        else:
            return .85 
    
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
    
    # OSC updates
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
                        print "Address : %s, Value : %s" % (addr, val)
                        if addr=='/basic/bpm':
                            bpm = int(round(float(val[1:][:-1])))
                            self.update_bpm(bpm)
                        elif addr=='/basic/instrument':
                            instrument = int(round(float(val[1:][:-1])))
                            self.update_instrument(instrument)
                        elif addr.startswith('/path/generator'):
                            gen_number = addr.split("/")[-2]
                            gen_type = self.__orderDict[int(gen_number)]
                            value = int(round(float(val[1:][:-1])))
                            self.update_generator('path', gen_type,value)
                        elif addr.startswith('/path/list'):
                            row, col = tuple(addr.split("/")[-2:])
                            board_path = "/%s/%s" % (row, col) # Position on the path board
                            value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                            self.update_path(board_path,value)
                        elif addr.startswith('/path/select'):
                            selected_path = int(addr.split("/")[-1])-1
                            value = int(round(float(val[1:][:-1])))
                            self.update_selected_path(selected_path, value)
                        elif addr.startswith('/rhythm/list'):
                            rhythm = self.__rhythmValue(float(val[1:][:-1]))
                            list_idx = int(addr.split("/")[-1])
                            self.update_rhythm(rhythm,list_idx)
                        elif addr.startswith('/rhythm/generator'):
                            gen_number = addr.split("/")[-2]
                            gen_type = self.__orderDict[int(gen_number)]
                            value = int(round(float(val[1:][:-1])))
                            self.update_generator('rhythm', gen_type, value)
                        elif addr.startswith('/rhythm/dividor'):
                            dividor = self.__dividorValue(float(val[1:][:-1]))
                            self.update_dividor(dividor)
                        elif addr.startswith('/pitch/generator'):
                            gen_number = addr.split("/")[-2]
                            gen_type = self.__orderDict[int(gen_number)]
                            value = int(round(float(val[1:][:-1])))
                            self.update_generator('pitch', gen_type, value)
                        elif addr.startswith('/pitch/list'):
                            pitch = int(round(float(val[1:][:-1]))) 
                            list_idx = int(addr.split("/")[-1])
                            self.update_pitch(pitch,list_idx)
                        elif addr.startswith('/amplitude/list'):
                            amplitude = float(val[1:][:-1])
                            list_idx = int(addr.split("/")[-1])
                            self.update_amplitude(amplitude,list_idx)
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
    
    def send_message(self,address,value):
        print "Address: %s \t\t Message:%s" % (address, str(value))
        msg = OSC.OSCMessage()
        msg.setAddress(address)
        msg.append(value)
        self.client.send(msg)

    def update_instrument(self,instrument):
        self.__gui.update('instrument', instrument)
        self.send_message('/basic/instrumentValue', instrument)

    def update_bpm(self,bpm):
        self.__gui.update('bpm', bpm)
        self.send_message('/basic/bpmValue', bpm)

    def update_generator(self,category, gen_type, value):
        if value > 0:
            if category=='path':
                self.__gui.update('path order', gen_type)
            elif category=='rhythm':
                self.__gui.update('rhythm order', gen_type)
            elif category=='pitch':
                self.__gui.update('field order', gen_type)
            elif category=='amplitude':
                self.__gui.update('amplitude order', gen_type)
            elif category=='panning':
                self.__gui.update('panning order', gen_type)
            else:
                print "Error : unexpected generator category!"
        else:
            # Ignore calls to the generator with value 0.
            pass
    
    def update_path(self,board_path,value):
        # import pdb; pdb.set_trace()
        note = self.__reversePathDict[board_path]
        # TODO: This process is currently independent from the generator removal process.
        # This step should only happen as a consequence of a generator decision.
        if value > 0:
            idx = self.__generator.state['path']['selected']
            self.__gui.update('path list %d' % idx, note)
            # We display the chosen path value in the chosen list on the phone.
            try:
                chosen = "chosen%d" % (idx+1)
                self.send_message("/path/%s" % chosen, note)
            except ValueError:
                print "Error : Note %s not found in path when updating path." % note
        else:
            # Do nothing if this branch is hit
            pass
    
    def update_selected_path(self, selected_path, value):
        """
        Updates the selected path value and sets the board to be 
        that of the selected path.
        """
        # print 'value : %d' % value
        # import pdb; pdb.set_trace()
        if value > 0:
            self.__gui.update('path select', selected_path)
            note = self.__generator.state['path']['list'][selected_path]
            board_path = self.__pathDict[note]
            addr = '/path/list%s' % board_path
            self.send_message(addr,1.0)
        else:
            # Ignore the message. Nothing to do here.
            pass

    def update_rhythm(self,rhythm,list_idx):
        self.__gui.update('rhythm list %d' % list_idx, rhythm)
        self.send_message('/rhythm/lr%d' % list_idx, rhythm)
    
    def update_dividor(self,dividor):
        self.__gui.update('rhythm dividor', dividor)
        self.send_message('/rhythm/dividorValue', dividor)
 
    def update_pitch(self,pitch,list_idx):
        self.__gui.update('field list %d' % list_idx, pitch)
        self.send_message('/pitch/lp%d' % list_idx, pitch)

    def update_amplitude(self,amplitude,list_idx):
        self.__gui.update('amplitude list %d' % list_idx, amplitude)
        self.send_message('/amplitude/l%d' % list_idx, amplitude)

    def reset_handler(self,addr, tags, data, source):
        try:
            if data[0]==1.0: #if reset is toggled 
                self.__generator.loadState()
                self.send_state()
        except:
            print sys.exc_info()
    
    #Simple handler that justs prints
    def printing_handler(self,addr, tags, data, source):
        try:
            msg = "{} {}\n".format(addr,data)
            self.__messageQueue.put(msg)
        except:
            print sys.exc_info()
