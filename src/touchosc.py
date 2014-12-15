import OSC
import sys
import time, threading
import socket
from generator import Generator
import yaml
import Tkinter
import traceback
from pprint import pprint
from Queue import Queue,Empty
from numbers import Number
from _sqlite3 import Row

class TouchOSC(object):
    
    def __init__(self, gen, gui=None, filename=None, config=None):

        self.generator = gen
        
        #Used for transfer of OSC messages:
        self.__orderDict = {1:"cyclic",2:"random"}
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
        
        if not (gui and filename and config):
            return
        
        self.__gui = gui
        self.devicePort = config['device_port']
        self.applicationPort = config['application_port']
	self.is_connected = False
        
        # Creates a OSC server and client
        self.update_application_server()
        
        if not hasattr(self, 'server'):
            # Required for what comes next.
            raise Exception('Server not initialized!')
            sys.exit(1)

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
        self.server.addMsgHandler('/basic/play', self.play_handler)
        self.server.addMsgHandler('/basic/pause', self.pause_handler)
        self.server.addMsgHandler('/basic/mute', self.mute_handler)
        self.server.addMsgHandler('/basic/unmute', self.unmute_handler)
        
        self.server.daemon = True
        
        #Queue for osc messages
        self.__messageQueue = Queue()
    
    def set_preset_dir(self, preset_dir):
        self.preset_dir = preset_dir
    
    def set_midi_out(self, midi_out):
        self.midi_out = midi_out
    
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
        
        # This line has been causing some problems recently, not sure why. 
        # receive_address = socket.gethostbyname(socket.gethostname()), self.applicationPort
        # Quick workaround
        receive_address = '0.0.0.0', self.applicationPort
        try:
            self.server = OSC.ThreadingOSCServer(receive_address)
            self.client = OSC.OSCClient()
        except:
            t,v,tb = sys.exc_info()
            print v
            traceback.print_tb(tb)

    
    def connect(self,deviceIP, devicePort, applicationPort):
        """
        Connects to the phone client and calls send_state. Used when click connect on the
        GUI. Raises OSCClientError.
        """
        self.deviceIP = deviceIP
        self.devicePort = devicePort
        self.applicationPort = applicationPort
        address = self.deviceIP, self.devicePort
        # TODO: currently will not update application port correctly.
        # self.update_application_server()
        self.ip_port = "%s:%d" % (self.deviceIP, self.devicePort)
        self.client.connect(address)
        self.__gui.addToOSC(
                "Device IP: %s, device port : %d, application port : %d\n" % (
                    self.deviceIP,
                    self.devicePort,
                    self.applicationPort
                )
        )
        self.send_state()
        self.__gui.addToOSC("State sent successfully to device!")
	self.is_connected = True
    
    def send_state(self):
        """
        Sends the current state of the python application to the device.
        """
        print "============= State being sent ... ==============="
        self.set_zero_values('all')
        self.set_state_values('all')


    def set_zero_values(self, category):
        '''
        Set zero-style values for all patterns. Not that bpm, dividor and generators are not affected.
        '''
        default_addresses = []
        for attribute in self.generator.state:
            content = self.generator.state[attribute]
            if attribute=='instrument' and (category=='instrument' or category=='all'):
                for i in xrange(4):
                    for j in xrange(8):
                        default_addresses.append('/basic/instrument/%d/%d 0' %  (i+1,j+1))
            elif attribute=='path' and (category=='path' or category=='all'):
                # Path board default values
                for i in range(8):
                    default_addresses.append('/path/chosen%d %s' % (i+1,'?'))
            elif attribute=='rhythm' and (category=='rhythm' or category=='all'):
                # Rhythm pattern
                for i in xrange(4):
                    for j in xrange(8):
                            default_addresses.append("/rhythm/pattern/%d/%d 0" % (4-i,j+1));
            elif attribute=='pitch' and (category=='pitch' or category=='all'):
                # Pitch pattern
                for i in xrange(11):
                    for j in xrange(8):
                            default_addresses.append("/pitch/pattern/%d/%d 0" % (11-i,j+1))
            elif attribute=='amplitude' and (category=='amplitude' or category=='all'):
                # Default amplitude pattern
                for i in range(8):
                    default_addresses.append('/amplitude/pattern/'+str(i+1)+" 0")
                    default_addresses.append('/amplitude/l'+str(i+1)+" 0")
            else:
                #Not recognized
                pass
        for packet in default_addresses:
            addr, value = packet.split(" ")
            self.send_message(addr,value)

    
    def set_state_values(self, category):
        """
        Category can be the name of a musical feature or 'all'.
        """
        state_addresses = []
        for attribute in self.generator.state:
            content = self.generator.state[attribute]
            if attribute=='instrument' and (category=='instrument' or category=='all'):
                row = 4 - ((content - 1) / 8)
                col = content % 8
                state_addresses.append('/basic/instrument/%d/%d 1' % (row,col))
            elif attribute=='bpm' and (category=='bpm' or category=='all'):
                # BPM value and label
                state_addresses.append('/basic/bpm '+str(content))
                state_addresses.append('/basic/bpmValue '+str(content))
            elif attribute=='path' and (category=='path' or category=='all'):
                selected_path = content['selected']
                path = content['pattern'][selected_path]
                # The path value mentioned here is a note string (e.g. 'C3')
                state_addresses.append('/path/pattern'+ str(self.__pathDict[path])+" 1")
                state_addresses.append('/path/select/1/%d 1' % (selected_path+1))
                # Path chosen labels
                for idx, path in enumerate(content['pattern']):
                    state_addresses.append('/path/chosen'+ str(idx+1)+ ' '+ path)
                # Path generator option
                state_addresses.append('/path/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            elif attribute=='rhythm' and (category=='rhythm' or category=='all'):
                # Rhythm pattern
                external_pattern = self.generator.deserialize_rhythm(content['pattern'])
                for i in xrange(4):
                    for j in xrange(8):
                        if external_pattern[i][j] == 1:
                            state_addresses.append("/rhythm/pattern/%d/%d 1" % (4-i,j+1))
                # Rhythm dividor value and label
                state_addresses.append('/rhythm/dividor ' + str(self.__reverseDividorValue(content['dividor'])))
                state_addresses.append('/rhythm/dividorValue ' + str(content['dividor']))
                # Rhyhtm generator option
                state_addresses.append('/rhythm/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            elif attribute=='pitch' and (category=='pitch' or category=='all'):
                # Pitch pattern
                external_pattern = self.generator.deserialize_pitch(content['pattern'])
                for i in xrange(11):
                    for j in xrange(8):
                        if external_pattern[i][j] == 1:
                            state_addresses.append("/pitch/pattern/%d/%d 1" % (11-i,j+1))
                # Pitch generator option
                state_addresses.append('/pitch/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            elif attribute=='amplitude' and (category=='amplitude' or category=='all'):
                for i,p in enumerate(content['pattern']):
                    state_addresses.append('/amplitude/pattern/'+ str(i+1)+ " "+ str(p))
                    state_addresses.append('/amplitude/l'+ str(i+1)+ " "+ str(p))
                # Amplitude generator option
                state_addresses.append('/amplitude/generator/' +
                        str(self.__reverseOrderDict[content['order']])+"/1 1"
                )
            else:
                #Not recognized
                pass
        for packet in state_addresses:
            addr,value = packet.split(" ")
            self.send_message(addr,value)

    
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
    
    # OSC updates
    def run(self):
        try:
            st = threading.Thread( target = self.server.serve_forever )
            st.start()
            print "OSC server running on port 8000..."
        except:
            t2,v2,tb2 = sys.exc_info()
            print t2
            print v2
            traceback.print_tb(tb2)
        
        while self.generator.active:
            try:
                msg = str(self.__messageQueue.get())
                if msg.strip()=='/quit []':
                    break
                else:
                    addr,val = msg.strip().split(" ")
                    print "Address : %s, Value : %s" % (addr, val)
                    if addr.startswith('/basic/bpm'):
                        bpm = int(round(float(val[1:][:-1])))
                        self.update_bpm(bpm)
                    elif addr.startswith('/basic/instrument'):
                        value = int(round(float(val[1:][:-1])))
                        row, col = tuple(addr.split("/")[-2:])
                        row = int(row); col = int(col)
                        row = 4 - row
                        col = col - 1
                        self.update_instrument(row, col, value)
                    elif addr.startswith('/basic/preset'):
                        value = int(round(float(val[1:][:-1])))
                        row, col = tuple(addr.split("/")[-2:])
                        row = int(row); col = int(col)
                        row = 2 - row
                        self.update_preset(row, col, value)
                    elif addr.startswith('/path/generator'):
                        gen_number = addr.split("/")[-2]
                        gen_type = self.__orderDict[int(gen_number)]
                        value = int(round(float(val[1:][:-1])))
                        self.update_generator('path', gen_type,value)
                    elif addr.startswith('/path/pattern'):
                        row, col = tuple(addr.split("/")[-2:])
                        pattern_path = "/%s/%s" % (row, col) # Position on the path board
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.update_path(pattern_path,value)
                    elif addr.startswith('/path/algorithm'):
                        row, col = tuple(addr.split("/")[-2:])
                        algorithm_path = "/%s/%s" % (row, col) # Position on the path board
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.apply_algorithm('path',algorithm_path,value)
                    elif addr.startswith('/path/select'):
                        selected_path = int(addr.split("/")[-1])-1
                        value = int(round(float(val[1:][:-1])))
                        self.update_selected_path(selected_path, value)
                    elif addr.startswith('/rhythm/pattern'):
                        row, col = tuple(addr.split("/")[-2:])
                        row = int(row); col = int(col)
                        row = 4 - row
                        col = col - 1
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.update_rhythm(row, col, value)
                    elif addr.startswith('/rhythm/generator'):
                        gen_number = addr.split("/")[-2]
                        gen_type = self.__orderDict[int(gen_number)]
                        value = int(round(float(val[1:][:-1])))
                        self.update_generator('rhythm', gen_type, value)
                    elif addr.startswith('/rhythm/dividor'):
                        dividor = self.__dividorValue(float(val[1:][:-1]))
                        self.update_dividor(dividor)
                    elif addr.startswith('/rhythm/algorithm'):
                        row, col = tuple(addr.split("/")[-2:])
                        algorithm_path = "/%s/%s" % (row, col) # Position on the path board
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.apply_algorithm('rhythm',algorithm_path,value)
                    elif addr.startswith('/pitch/generator'):
                        gen_number = addr.split("/")[-2]
                        gen_type = self.__orderDict[int(gen_number)]
                        value = int(round(float(val[1:][:-1])))
                        self.update_generator('pitch', gen_type, value)
                    elif addr.startswith('/pitch/pattern'):
                        row, col = tuple(addr.split("/")[-2:])
                        row = int(row); col = int(col)
                        row = 11 - row
                        col = col - 1
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.update_pitch(row, col, value)
                    elif addr.startswith('/pitch/algorithm'):
                        row, col = tuple(addr.split("/")[-2:])
                        algorithm_path = "/%s/%s" % (row, col) # Position on the path board
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.apply_algorithm('pitch',algorithm_path,value)
                    elif addr.startswith('/amplitude/generator'):
                        gen_number = addr.split("/")[-2]
                        gen_type = self.__orderDict[int(gen_number)]
                        value = int(round(float(val[1:][:-1])))
                        self.update_generator('amplitude', gen_type, value)
                    elif addr.startswith('/amplitude/pattern'):
                        amplitude = float(val[1:][:-1])
                        list_idx = int(addr.split("/")[-1]) - 1
                        self.update_amplitude(amplitude,list_idx)
                    elif addr.startswith('/amplitude/algorithm'):
                        row, col = tuple(addr.split("/")[-2:])
                        algorithm_path = "/%s/%s" % (row, col) # Position on the path board
                        value = int(round(float(val[1:][:-1]))) # Value ( on or off)
                        self.apply_algorithm('amplitude',algorithm_path,value)
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

    
    def send_message(self,address,value):
        """
        Sends a message to the device. Assumes the 
        client attribute has been set.
        """
        msg = OSC.OSCMessage()
        msg.setAddress(address)
        msg.append(value)
        self.client.send(msg)

    def update_instrument(self, row, col, value):
        """
        Updates the generator instrument if value is
        not 0. Does this by matching (row, col) to
        an instrument number between 1 and 32.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_instrument(0,2,1)
        >>> osc.generator.state['instrument']
        3
        """
        if value != 0:
            instrument = row * 8 + col
            self.generator.update('instrument', instrument)
            if hasattr(self, 'client'):
                self.send_message('/basic/instrument/%d/%d' % (4-row, col+1), 1)

    def update_bpm(self,bpm):
        """
        Updates bpm.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_bpm(90)
        >>> osc.generator.state['bpm']
        90
        """
        self.generator.update('bpm', bpm)
        if hasattr(self, 'client'):
            self.send_message('/basic/bpmValue', bpm)
    
    def update_preset(self, row, col, value):
        """
        Updates preset.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.set_preset_dir("../resources/presets")
        >>> osc.update_preset(1,1,1)
        """
        if value != 0:
            preset = row * 8 + col
            self.generator.state = self.generator.readStateFromFile("%s/%s" % 
                (
                    self.preset_dir,
                    "preset%d.yml" % preset
                )
            )
            if hasattr(self, 'client'):
                self.send_state()

    def update_generator(self,category, gen_type, value):
        """
        Updates generator for category.
        gen_type may be 'cyclic' or 'random'.
        Only updates if value different from 0.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_generator('path','random',1)
        >>> osc.update_generator('rhythm','cyclic',1)
        >>> osc.generator.state['path']['order_eng']
        UniformRandomGenerator
        >>> osc.generator.state['rhythm']['order_eng']
        CyclicGenerator
        """
        if value != 0:
            if category in ['path','amplitude','rhythm','pitch']:
                self.generator.update("%s order" % category, gen_type)
            else:
                print "Error : unexpected generator category!"
        else:
            # Ignore calls to the generator with value 0.
            pass
        
    def apply_algorithm(self, category, algorithm, value):
        """
        If value is non-zero, applies the specified algorithm to the pattern
        of the specified category, then sends a response to the device to update
        the display accordingly.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.generator.state['path']['pattern']
        ['C4', 'C3', 'C3', 'C3', 'C3', 'C3', 'C3', 'C3']
        >>> osc.apply_algorithm('path','/2/6',1) ############### Test unimplemented
        Unimplemented algorithm selected...
        >>> osc.apply_algorithm('path','/3/2',1) ################## Test shift right
        >>> osc.generator.state['path']['pattern']
        ['C3', 'C4', 'C3', 'C3', 'C3', 'C3', 'C3', 'C3']
        >>> osc.generator.state['pitch']['pattern']
        [[3, 0, -3], [0], [0], [0], [0], [0], [0], [0]]
        >>> osc.apply_algorithm('pitch','/3/2',1)
        >>> osc.generator.state['pitch']['pattern']
        [[0], [3, 0, -3], [0], [0], [0], [0], [0], [0]]
        >>> osc.apply_algorithm('pitch','/3/3',1) ################ Test shift up
        >>> osc.generator.state['pitch']['pattern']
        [[1], [4, 1, -2], [1], [1], [1], [1], [1], [1]]
        >>> osc.apply_algorithm('rhythm','/3/3',1)
        >>> osc.generator.state['rhythm']['pattern']
        [(0, [4, 2, 2]), (0, [4, 4]), (0, [4, 4]), (0, [4, 4])]
        >>> osc.apply_algorithm('amplitude','/3/3',1)
        >>> osc.generator.state['amplitude']['pattern']
        [0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6]
        >>> osc.apply_algorithm('path','/3/3',1)
        >>> osc.generator.state['path']['pattern']
        ['C#3', 'C#4', 'C#3', 'C#3', 'C#3', 'C#3', 'C#3', 'C#3']
        >>> osc.apply_algorithm('pitch','/3/4',1) ################ Test shift down
        >>> osc.generator.state['pitch']['pattern']
        [[0], [3, 0, -3], [0], [0], [0], [0], [0], [0]]
        >>> osc.apply_algorithm('rhythm','/3/4',1)
        >>> osc.generator.state['rhythm']['pattern']
        [(0, [4, 4]), (0, [4, 2, 2]), (0, [4, 4]), (0, [4, 4])]
        >>> osc.apply_algorithm('amplitude','/3/4',1)
        >>> osc.generator.state['amplitude']['pattern']
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        >>> osc.apply_algorithm('path','/3/4',1)
        >>> osc.generator.state['path']['pattern']
        ['C3', 'C4', 'C3', 'C3', 'C3', 'C3', 'C3', 'C3']
        >>> osc.apply_algorithm('path','/3/5', 1) ################# Test Retrograde
        >>> osc.generator.state['path']['pattern']
        ['C3', 'C3', 'C3', 'C3', 'C3', 'C3', 'C4', 'C3']
        >>> osc.apply_algorithm('rhythm','/3/5',1)
        >>> osc.generator.state['rhythm']['pattern']
        [(3, [4, 1]), (1, [2, 4, 1]), (3, [4, 1]), (3, [4, 1])]
        >>> osc.apply_algorithm('pitch','/3/5',1)
        >>> osc.generator.state['pitch']['pattern']
        [[0], [0], [0], [0], [0], [0], [3, 0, -3], [0]]
        >>> osc.apply_algorithm('path','/2/1',1) ################# Test Inverse
        >>> osc.generator.state['path']['pattern']
        ['C3', 'C3', 'C3', 'C3', 'C3', 'C3', 'C2', 'C3']
        >>> osc.apply_algorithm('path','/2/2',1) ################# Test Inverse Retrograde
        >>> osc.generator.state['path']['pattern']
        ['C3', 'C4', 'C3', 'C3', 'C3', 'C3', 'C3', 'C3']
        """
        if value !=0:
            if algorithm == "/3/1" :
                algorithm = "shiftLeft"
            elif algorithm == "/3/2" :
                algorithm = "shiftRight"
            elif algorithm == "/3/3" :
                algorithm = "shiftUp"
            elif algorithm == "/3/4" :
                algorithm = "shiftDown"
            elif algorithm == "/3/5" :
                algorithm = "retrograde"
            elif algorithm == "/2/1" and category == "path" :
                algorithm = "inverse"
            elif algorithm == "/2/2" and category == "path" :
                algorithm = "retrograde-inverse"
            elif algorithm == "/2/3" and category == "path" :
                algorithm = "raiseOctave"
            elif algorithm == "/2/4" and category == "path" :
                algorithm = "lowerOctave"
            elif algorithm == "/2/5" and category == "path" :
                algorithm = "repeat"
            else:
                print "Unimplemented algorithm selected..."
                return
            if category in ['path','amplitude','rhythm','pitch']:
                self.generator.apply_algorithm(category, algorithm)
                if hasattr(self, 'client'):
                    self.set_zero_values(category)
                    self.set_state_values(category)
            else:
                print "Error : unexpected generator category!"
                return
    
    def update_path(self,pattern_path,value):
        """
        Updates path corresponding to current selection if value greater than 0.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_path('/4/1',1)
        >>> selected = osc.generator.state['path']['selected']
        >>> osc.generator.state['path']['pattern'][selected]
        'C2'
        """
        if value > 0:
            note = self.__reversePathDict[pattern_path]
            idx = self.generator.state['path']['selected']
            self.generator.update('path pattern %d' % idx, note)
            # We display the chosen path value in the chosen list on the phone.
            chosen = "chosen%d" % (idx+1)
            if hasattr(self, 'client'):
                self.send_message("/path/%s" % chosen, note)
        else:
            # Do nothing if this branch is hit
            pass
    
    def update_selected_path(self, selected_path, value):
        """
        Updates the selected path value and sets the board to be 
        that of the selected path.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_selected_path(0,1)
        >>> osc.generator.state['path']['selected']
        0
        """
        if value > 0:
            self.generator.update('path select', selected_path)
            if hasattr(self, 'client'):
                note = self.generator.state['path']['pattern'][selected_path]
                pattern_path = self.__pathDict[note]
                addr = '/path/pattern%s' % pattern_path
                self.send_message(addr,1.0)
        else:
            # Ignore the message. Nothing to do here.
            pass

    def update_rhythm(self, row, col, value):
        """
        Updates path pattern one row at a time if value is greater than 0.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_rhythm(0,1,1)
        >>> external_pattern = osc.generator.deserialize_rhythm(osc.generator.state['rhythm']['pattern'])
        >>> external_pattern[0]
        [1, 1, 0, 0, 1, 0, 0, 0]
        """
        external_pattern = self.generator.deserialize_rhythm(self.generator.state['rhythm']['pattern']) 
        full_row = external_pattern[row]
        full_row[col] = value
        self.generator.update('rhythm pattern %d' % row, full_row)
        if hasattr(self,'client'):
            row = 4 - row
            col = col + 1
            self.send_message("/rhythm/pattern/%d/%d" % (row, col), value)
    
    def update_dividor(self,dividor):
        """
        Update rhythm dividor.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_dividor(2)
        >>> osc.generator.state['rhythm']['dividor']
        2
        """
        self.generator.update('rhythm dividor', dividor)
        if hasattr(self, 'client'):
            self.send_message('/rhythm/dividorValue', dividor)
 
    def update_pitch(self, row, col, value):
        """
        Updates pitch pattern one column at a time if value is greater than 0.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_pitch(0,0,1)
        >>> external_pattern = osc.generator.deserialize_pitch(osc.generator.state['pitch']['pattern'])
        >>> external_pattern[0]
        [1, 0, 0, 0, 0, 0, 0, 0]
        """
        column = []
        external_pattern = self.generator.deserialize_pitch(self.generator.state['pitch']['pattern'])
        for r in external_pattern:
            column.append(r[col])
        column[row] = value
        self.generator.update('pitch pattern %d' % col, column)
        if hasattr(self,'client'):
            col = col + 1
            row = 11 - row
            self.send_message("/pitch/pattern/%d/%d" % (row, col), value)

    def update_amplitude(self,amplitude,list_idx):
        """
        Updates amplitude at list_idx with value amplitude.
        Sends acknowledgement message to device.
        
        >>> g = Generator("../resources/presets/test.yml", {})
        >>> osc = TouchOSC(g)
        >>> osc.update_amplitude(0.7, 0)
        >>> osc.generator.state['amplitude']['pattern'][0]
        0.7
        """
        self.generator.update('amplitude pattern %d' % list_idx, amplitude)
        if hasattr(self, 'client'):
            self.send_message('/amplitude/l%d' % (list_idx + 1), int(amplitude * 127))

    def reset_handler(self,addr, tags, data, source):
        try:
            if data[0]==1.0: #if reset is toggled 
                self.generator.loadState()
                self.send_state()
        except:
            print sys.exc_info()
    
    #Simple handler that justs prints
    def printing_handler(self,addr, tags, data, source):
        """
        Prints the incoming OSC messages from the device onto the desktop user interface.
        If the address string contains the substring '/position/', then it is assumed this
        message comes from the local feedback of a position indicator and is ignored.
        """
        try:
            if '/position/' not in addr:
                msg = "{} {}\n".format(addr,data)
                self.__messageQueue.put(msg)
        except:
            print sys.exc_info()
    
    def play_handler(self, add, tags, data, source):
        """
        Used when pressing on the play button.
        """
        if int(data[0]) > 0:
            self.generator.playing = True
    
    def pause_handler(self, add, tags, data, source):
        """
        Used when pressing on the pause button.
        """
        if int(data[0]) > 0:
            self.generator.playing = False
    
    def mute_handler(self, add, tags, data, source):
        """
        Used when pressing on the mute button.
        """
        if int(data[0]) > 0:
            self.midi_out.mute = True
    
    def unmute_handler(self, add, tags, data, source):
        """
        Used when pressing on the unmute button.
        """
        if int(data[0]) > 0:
            self.midi_out.mute = False

if __name__ == '__main__':
    import doctest
    doctest.testmod()
