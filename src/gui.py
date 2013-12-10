import Tkinter
import sys
import traceback
import OSC
import socket

class GUI(object):
    
    def __init__(self,gen):
        self.phoneIP = 'unknown'
        self.phonePort = 'unknown'
        
        self.__generator = gen
        try:
            self.__root=Tkinter.Tk()
            
            self.__root.geometry("1100x800+200+0")
            
            #Delete Window callback
            self.__root.protocol("WM_DELETE_WINDOW", self.exitCallback)
            self.__window = self.__root
            
            self.vars = {}
            
            #Label the application  
            self.__s = Tkinter.StringVar()
            self.__s.set('iPhone Composer')
            Tkinter.Label(self.__window,textvariable=self.__s,font=("Helvetica", 24)).grid(row=0,column=0)
            
            #Add a Paned Window to contain application state information
            paned = Tkinter.PanedWindow(self.__window,orient=Tkinter.VERTICAL)
            self.__createApplicationState(paned)
            paned.grid(row=1,column=0)
            
            #Add an output list that may be accessed publicly
            mainframe = Tkinter.Frame(self.__window, bd=2, relief=Tkinter.SUNKEN,width=500,height=600)
            
            #Output frame
            outputframe = Tkinter.Frame(mainframe,relief=Tkinter.SUNKEN,width=500,height=300)
            self.outputscrollbar = Tkinter.Scrollbar(outputframe)
            self.outputscrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
            Tkinter.Label(outputframe,text="Output").pack(side=Tkinter.TOP)
            self.output = Tkinter.Text(outputframe, bd=0, yscrollcommand=self.outputscrollbar.set)
            self.output.pack(pady=(10,10),padx=(10,10))
            self.output.configure(yscrollcommand = self.outputscrollbar.set)
            self.outputscrollbar.configure(command = self.output.yview)
            outputframe.pack_propagate(0)
            outputframe.pack(fill=None, expand=False)
            
            #OSC frame
            oscframe = Tkinter.Frame(mainframe,relief=Tkinter.SUNKEN,width=500,height=300)
            self.oscScrollbar = Tkinter.Scrollbar(oscframe)
            self.oscScrollbar.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
            Tkinter.Label(oscframe,text="OSC").pack(side=Tkinter.TOP)
            self.osc = Tkinter.Text(oscframe, bd=0, yscrollcommand=self.oscScrollbar.set)
            self.osc.pack(pady=(10,10),padx=(10,10))
            self.osc.configure(yscrollcommand = self.oscScrollbar.set)
            self.oscScrollbar.configure(command = self.osc.yview)
            oscframe.pack_propagate(0)
            oscframe.pack(fill=None, expand=False)
            
            mainframe.pack_propagate(0)
            mainframe.grid(row=1,column=1)
            
            #Create the buttons
            buttonPane = Tkinter.PanedWindow(self.__window,orient=Tkinter.VERTICAL)
            buttonPane.grid(row=2,column=0)
            self.__createButtons(buttonPane)
            buttonPane.pack_propagate(0)
            
            #Create the connection fields
            connectPane = Tkinter.PanedWindow(self.__window,orient=Tkinter.VERTICAL)
            connectPane.grid(row=2,column=1)
            self.__createConnect(connectPane)
            
            #Dictionaries
            self.__orderValue = {'cyclic':0,'markov':1,'uniformRandom':2}
            self.__invertOrderValue = {0:'cyclic',1:'markov',2:'uniformRandom'}
            
        except :
            t,v,tb = sys.exc_info()
            traceback.print_exception(t,v,tb)
            self.__root.quit()
            quit()
    
    def addToOutput(self,msg):
        self.output.insert(Tkinter.END,msg)
        self.output.yview(Tkinter.END)
        
    def addToOSC(self,msg):
        self.osc.insert(Tkinter.END,msg)
        self.osc.yview(Tkinter.END)
        
    def __createButtons(self,pane):
        #Add the play button
        play = Tkinter.Button(pane,text = "Play", command=self.playCallback)
        play.grid(row=0,column=0)
        
        #Add the pause button
        pause = Tkinter.Button(pane,text = "Pause", command=self.pauseCallback)
        pause.grid(row=0,column=1)
        
        #Add the clear button, which clears the output box.
        clear = Tkinter.Button(pane,text = "Clear", command=self.clearCallback)
        clear.grid(row=1,column=0)
        
        #Add the connect button
        Tkinter.Button(pane,text="Connect",command=self.connectCallback).grid(row=1,column=1) 
    
    def __createConnect(self,pane):
        self.phoneIPaddressVar = Tkinter.StringVar()
        self.phonePortVar = Tkinter.StringVar()
        self.phoneIPaddressVar.set("Unknown")
        self.phonePortVar.set("Unknown")
        Tkinter.Label(pane,text="Device IP Address : ").grid(row=0,column=0)
        Tkinter.Entry(pane,textvariable=self.phoneIPaddressVar).grid(row=0,column=1)
        Tkinter.Label(pane,text="Device Port : ").grid(row=1,column=0)
        Tkinter.Entry(pane,textvariable=self.phonePortVar).grid(row=1,column=1)
    
    def __updateConnect(self,ip,port):
        pass
    
    def clearCallback(self):
        #Clears the output box
        self.output.delete(0.0,Tkinter.END)
        self.osc.delete(0.0,Tkinter.END)
        pass
    
    def exitCallback(self):
       self.__generator.playing = False
       self.__generator.active = False
       #Close the osc thread by sending a quit osc message
       c = OSC.OSCClient()
       send_address = socket.gethostbyname(socket.gethostname()), 8000 
       c.connect(send_address)
       msg = OSC.OSCMessage()
       msg.setAddress('/quit')
       c.send(msg)
       c.close()
       print "Exiting... (generator no longer active)"
       self.__root.quit()
    
    def connectCallback(self):
        self.phoneIP = self.phoneIPaddressVar.get()
        self.phonePort = self.phonePortVar.get()
        c = OSC.OSCClient()
        send_address = socket.gethostbyname(socket.gethostname()), 8000 
        c.connect(send_address)
        msg = OSC.OSCMessage()
        msg.setAddress('/connect')
        msg.append(self.phoneIP)
        msg.append(int(self.phonePort))
        c.send(msg)
        c.close()
    
    def update(self,attribute,value):
        if attribute=='bpm':
            if not value==self.vars['bpm'].get():
                if self.__generator.update(attribute,value):
                    self.vars['bpm'].set(value)
        elif attribute=='instrument':
            if not value==self.vars['instrument'].get():
                if self.__generator.update(attribute,value):
                    self.vars['instrument'].set(value)
        elif attribute=='path order':
            if not value== self.vars['path']['order'].get():
                if self.__generator.update(attribute,value):
                    self.vars['path']['order'].set(value)
        elif attribute=='path list':
            if self.__generator.update(attribute,value):
                self.vars['path']['list'].set(str(self.__generator.state['path']['list']))
                self.vars['path']['order_args'].set(str(self.__generator.state['path']['order_args']))
        elif attribute=='rhythm order':
            if not value==self.vars['rhythm']['order'].get():
                if self.__generator.update(attribute,value):
                    self.vars['rhythm']['order'].set(value)
        elif attribute.startswith('rhythm list'):
            idx = int(attribute.split(" ")[-1])-1
            if not value==self.__generator.state['rhythm']['list'][idx]:
                if self.__generator.update(attribute,value):
                    self.vars['rhythm']['list'].set(str(self.__generator.state['rhythm']['list']))
        elif attribute.startswith('rhythm dividor'):
            if not value==self.vars['rhythm']['dividor'].get():
                if self.__generator.update(attribute,value):
                    self.vars['rhythm']['dividor'].set(value)
        elif attribute.startswith('field list'):
            if not value==self.__generator.state['field']['list'][int(attribute.split(" ")[-1])-1]:
                if self.__generator.update(attribute,value):
                    self.vars['field']['list'].set(self.__generator.state['field']['list'])
        elif attribute=='field order':
            if not value==self.vars['field']['order'].get():
                if self.__generator.update(attribute,value):
                    self.vars['field']['order'].set(value)
        elif attribute.startswith('octave list'):
            if not value==self.__generator.state['octave']['list'][int(attribute.split(" ")[-1])-1]:
                if self.__generator.update(attribute,value):
                    self.vars['octave']['list'].set(self.__generator.state['octave']['list'])
        elif attribute=='octave order':
            if not value==self.vars['octave']['order'].get():
                if self.__generator.update(attribute,value):
                    self.vars['octave']['order'].set(value)
        else:
            #not recognized
            pass
    
    def playCallback(self):
        self.__generator.playing = True
    
    def pauseCallback(self):
        self.__generator.playing = False
    
    def __orderValue(self,order_type):
        if order_type=='cyclic':
            return 0
        elif order_type=='markov':
            return 1
        elif order_type=='uniformRandom':
            return 2
        else:
            raise Exception("Order type %s is invalid!", order['type'])
            quit()
    
    def __order(self,pane,type,t_row):
        Tkinter.Label(pane,text=str(type+" order type")).grid(row=t_row,column=0)
        self.vars[type]['order'] = Tkinter.StringVar()
        self.vars[type]['order'].set(self.__generator.state[type]['order'])
        Tkinter.Entry(pane,textvariable=self.vars[type]['order'],state=Tkinter.DISABLED,width=50).grid(row=t_row,column=1)
        Tkinter.Label(pane,text=str(type+" order args")).grid(row=t_row+1,column=0)
        self.vars[type]['order_args'] = Tkinter.StringVar()
        self.vars[type]['order_args'].set(self.__generator.state[type]['order_args'].split(":")[1])
        Tkinter.Entry(pane,textvariable=self.vars[type]['order_args'],state=Tkinter.DISABLED,width=50).grid(row=t_row+1,column=1)
    
    def __createApplicationState(self,paned):
        #Label
        panedLabel = Tkinter.Label(paned,text="Texture 1")
        paned.add(panedLabel)
        
        #Internal pane
        internal = Tkinter.PanedWindow(paned)
        paned.add(internal)
        
        #Instrument
        Tkinter.Label(internal,text="Instrument").grid(row=0,column=0)
        self.vars['instrument'] = Tkinter.StringVar()
        self.vars['instrument'].set(self.__generator.state['instrument'])
        Tkinter.Entry(internal,textvariable=self.vars['instrument'],state=Tkinter.DISABLED,width=50).grid(row=0,column=1)
        
        #bpm
        Tkinter.Label(internal,text="bpm").grid(row=1,column=0)
        self.vars['bpm'] = Tkinter.StringVar()
        self.vars['bpm'].set(str(self.__generator.state['bpm']))
        Tkinter.Entry(internal,textvariable=self.vars['bpm'],state=Tkinter.DISABLED,width=50).grid(row=1,column=1)
        Tkinter.Frame(height=5, bd=1, relief=Tkinter.SUNKEN).grid(row=2,column=0)
        
        #path
        self.vars['path'] = {}
        Tkinter.Label(internal,text="path list").grid(row=3,column=0)
        self.vars['path']['list'] = Tkinter.StringVar()
        self.vars['path']['list'].set(str(self.__generator.state['path']['list']))
        Tkinter.Entry(internal,textvariable=self.vars['path']['list'],state=Tkinter.DISABLED,width=50).grid(row=3,column=1)
        self.__order(internal,"path",4)
        Tkinter.Frame(height=2, bd=1, relief=Tkinter.SUNKEN).grid(row=6,column=0)
        
        #rhythm
        self.vars['rhythm'] = {}
        Tkinter.Label(internal,text="rhythm list").grid(row=6,column=0)
        self.vars['rhythm']['list'] = Tkinter.StringVar()
        self.vars['rhythm']['list'].set(str(self.__generator.state['rhythm']['list']))
        Tkinter.Entry(internal,textvariable=self.vars['rhythm']['list'],state=Tkinter.DISABLED,width=50).grid(row=6,column=1)
        self.__order(internal,"rhythm",7)
        Tkinter.Label(internal,text="rhythm dividor").grid(row=9,column=0)
        self.vars['rhythm']['dividor'] = Tkinter.StringVar()
        self.vars['rhythm']['dividor'].set(str(self.__generator.state['rhythm']['dividor']))
        Tkinter.Entry(internal,textvariable=self.vars['rhythm']['dividor'],state=Tkinter.DISABLED,width=50).grid(row=9,column=1)
        
        #field
        self.vars['field']={}
        Tkinter.Label(internal,text="field list").grid(row=10,column=0)
        self.vars['field']['list'] = Tkinter.StringVar()
        self.vars['field']['list'].set(str(self.__generator.state['field']['list']))
        Tkinter.Entry(internal,textvariable=self.vars['field']['list'],state=Tkinter.DISABLED,width=50).grid(row=10,column=1)
        self.__order(internal,"field",11)
        Tkinter.Frame(height=2, bd=1, relief=Tkinter.SUNKEN).grid(row=13,column=0)
        
        #octave
        self.vars['octave'] = {}
        Tkinter.Label(internal,text="octave list").grid(row=14,column=0)
        self.vars['octave']['list'] = Tkinter.StringVar()
        self.vars['octave']['list'].set(str(self.__generator.state['octave']['list']))
        Tkinter.Entry(internal,textvariable=self.vars['octave']['list'],state=Tkinter.DISABLED,width=50).grid(row=14,column=1)
        self.__order(internal,"octave",15)
        Tkinter.Frame(height=2, bd=1, relief=Tkinter.SUNKEN).grid(row=17,column=0)
        
        #amplitude
        self.vars['amplitude'] = {}
        Tkinter.Label(internal,text="amplitude list").grid(row=18,column=0)
        self.vars['amplitude']['list'] = Tkinter.StringVar()
        self.vars['amplitude']['list'].set(str(self.__generator.state['amplitude']['list']))
        Tkinter.Entry(internal,textvariable=self.vars['amplitude']['list'],state=Tkinter.DISABLED,width=50).grid(row=18,column=1)
        self.__order(internal,"amplitude",19)
        Tkinter.Frame(height=2, bd=1, relief=Tkinter.SUNKEN).grid(row=21,column=0)
        
        #panning
        self.vars['panning'] = {}
        panningLabel = Tkinter.Label(internal,text="panning list").grid(row=22,column=0)
        self.vars['panning']['list'] = Tkinter.StringVar()
        self.vars['panning']['list'].set(str(self.__generator.state['panning']['list']))
        Tkinter.Entry(internal,textvariable=self.vars['panning']['list'],state=Tkinter.DISABLED,width=50).grid(row=22,column=1)
        self.__order(internal,"panning",23)
        Tkinter.Frame(height=2, bd=1, relief=Tkinter.SUNKEN).grid(row=25,column=0)
    
    def run(self):
        self.__root.mainloop()