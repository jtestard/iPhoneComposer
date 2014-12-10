import Tkinter
from Tkinter import Menu, Tk, Scrollbar, Frame, PanedWindow, Button, Label, Entry
from Tkinter import Text, SUNKEN, VERTICAL, HORIZONTAL, LEFT, RIGHT, Y, X, TOP
from Tkinter import StringVar, END, FALSE
import sys
import traceback
import OSC
from generator import RandomGenerator
import socket
from json import dumps
from OSC import OSCClientError
import tkMessageBox
import subprocess
import simplejson as json

class GUI(object):
    
    def __init__(self, gen, config, preset_dir):
        # These will be set later (might consider removing them?)
        self.deviceIP = ''
        self.devicePort = 0
        self.applicationPort = 0
        self.config = config
        self.preset_dir = preset_dir
        
        self.generator = gen
        try:
            self.__root=Tk()
            screen_w = self.__root.winfo_screenwidth()
            screen_h = self.__root.winfo_screenheight()
            window_w = self.config['window_width']
            window_h = self.config['window_height']
            off_w = (screen_w - window_w)/2;
            off_h = (screen_h - window_h)/4; # use 4 instead of 2
            self.__root.geometry("%dx%d+%d+%d" % (
                window_w,
                window_h,
                off_w,
                off_h
            ))
            
            # Delete Window callback
            self.__root.protocol("WM_DELETE_WINDOW", self.exitCallback)
            self.__window = self.__root
            self.__root.wm_title("iPhoneComposer");
            self.__root.option_add('*tearOff', FALSE)
            
            # Create menu
            menubar = Menu(self.__root)
            preset_handlers = self.makeShowPresetHandlers()
            self.__root.config(menu=menubar)
            optionsMenu = Menu(menubar)
            menubar.add_cascade(label="Options",menu=optionsMenu) 
            optionsMenu.add_command(label="Show internal state", command=self.showInternalState)
            presetMenu = Menu(menubar)
            menubar.add_cascade(label="Presets",menu=presetMenu)
            for i in xrange(12):
                presetMenu.add_command(
                    label="Show preset %d state" % (i+1),
                    command=preset_handlers[i]
                )
            
            # Add an output list that may be accessed publicly
            mainframe = Frame(self.__window, bd=2, relief=SUNKEN,width=500,height=400)
            
            # Output frame
            outputframe = Frame(mainframe,relief=SUNKEN,width=500,height=200)
            self.outputscrollbar = Scrollbar(outputframe)
            self.outputscrollbar.pack(side=RIGHT, fill=Y)
            Label(outputframe,text="Output").pack(side=TOP)
            self.output = Text(outputframe, bd=0, yscrollcommand=self.outputscrollbar.set)
            self.output.pack(pady=(10,10),padx=(10,10))
            self.output.configure(yscrollcommand = self.outputscrollbar.set)
            self.outputscrollbar.configure(command = self.output.yview)
            outputframe.pack_propagate(0)
            outputframe.pack(fill=None, expand=False)
            
            # OSC frame
            oscframe = Frame(mainframe,relief=SUNKEN,width=500,height=200)
            self.oscScrollbar = Scrollbar(oscframe)
            self.oscScrollbar.pack(side=RIGHT, fill=Y)
            Label(oscframe,text="OSC").pack(side=TOP)
            self.osc = Text(oscframe, bd=0, yscrollcommand=self.oscScrollbar.set)
            self.osc.pack(pady=(10,10),padx=(10,10))
            self.osc.configure(yscrollcommand = self.oscScrollbar.set)
            self.oscScrollbar.configure(command = self.osc.yview)
            oscframe.pack_propagate(0)
            oscframe.pack(fill=None, expand=False)
            
            mainframe.pack_propagate(0)
            mainframe.grid(row=1,column=0)
            
            # Create the buttons
            buttonPane = PanedWindow(self.__window,orient=VERTICAL)
            buttonPane.grid(row=2,column=0)
            self.__createButtons(buttonPane)
            buttonPane.pack_propagate(0)
            
            # Create the connection fields
            connectPane = PanedWindow(self.__window,orient=VERTICAL)
            connectPane.grid(row=3,column=0)
            self.__createConnect(connectPane)   
            
        except :
            t,v,tb = sys.exc_info()
            traceback.print_exception(t,v,tb)
            self.__root.quit()
            quit()
    
    def set_midi_output(self, midi_output):
        self.__midi_output = midi_output
        
    def set_touch_osc(self, touch_osc):
        self.__touch_osc = touch_osc
    
    def raise_above_all(self,window):
        window.attributes('-topmost', 1)
        window.attributes('-topmost', 0)
    
    def showInternalState(self):
        self.showState(self.generator.state, "Application Internal State")
    
    def makeShowPresetHandlers(self):
        preset_handlers = []
        for i in xrange(1,13):
            preset_handlers.append(PresetHandler(self, i))
        return preset_handlers
        
    def showState(self, state, title):
        internal_state = "Instrument : %d\n" % state['instrument']
        internal_state += "BPM : %d\n" % state['bpm']
        internal_state += "Path Pattern : %s\n" % state['path']['pattern']
        internal_state += "Path Generator : %s\n" % state['path']['order']
        rhythm_pattern = self.generator.deserialize_rhythm(state['rhythm']['pattern'])
        internal_state += "Rhythm Pattern :\n"
        for pat in rhythm_pattern:
             internal_state += "%s\n" % pat
        internal_state += "Rhythm Generator : %s\n" % state['rhythm']['order']
        internal_state += "Pitch Pattern :\n"
        pitch_pattern = self.generator.deserialize_pitch(state['pitch']['pattern'])
        for pat in pitch_pattern:
             internal_state += "%s\n" % pat
        internal_state += "Pitch Generator : %s\n" % state['pitch']['order']
        internal_state += "Amplitude Pattern : %s\n" % state['amplitude']['pattern']
        internal_state += "Amplitude Generator : %s" % state['amplitude']['order']
        tkMessageBox.showinfo(
            title,
            internal_state
        )

    def addToOutput(self,msg):
        self.output.insert(END,msg)
        self.output.yview(END)
        
    def addToOSC(self,msg):
        self.osc.insert(END,msg)
        self.osc.yview(END)
        
    def __createButtons(self,pane):
        #Add the play button
        play = Button(pane,text = "Play", command=self.playCallback)
        play.grid(row=0,column=0)
        
        #Add the pause button
        pause = Button(pane,text = "Pause", command=self.pauseCallback)
        pause.grid(row=0,column=1)
        
        #Add the clear button, which clears the output box.
        clear = Button(pane,text = "Clear", command=self.clearCallback)
        clear.grid(row=1,column=0)
        
        #Add the connect button
        Button(pane,text="Connect",command=self.connectCallback).grid(row=1,column=1) 
    
    def __createConnect(self,pane):
        self.deviceIPaddressVar = StringVar()
        self.devicePortVar = StringVar()
        self.applicationPortVar = StringVar()
        self.deviceIPaddressVar.set("Unknown")
        self.devicePortVar.set(str(self.config['device_port']))
        self.applicationPortVar.set(str(self.config['application_port']))
        Label(pane,text="OSC settings").grid(row=0,column=0)
        Label(pane,text="Device IP Address : ").grid(row=1,column=0)
        Entry(pane,textvariable=self.deviceIPaddressVar).grid(row=1,column=1)
        Label(pane,text="Device Input Port : ").grid(row=2,column=0)
        Entry(pane,textvariable=self.devicePortVar).grid(row=2,column=1)
        Label(pane,text="Application Input Port : ").grid(row=3,column=0)
        Entry(pane,textvariable=self.applicationPortVar).grid(row=3,column=1)
    
    def __updateConnect(self,ip,port):
        pass
    
    def clearCallback(self):
        #Clears the output box
        self.output.delete(0.0,END)
        self.osc.delete(0.0,END)
        pass
    
    def exitCallback(self):
        self.__midi_output.exit_notes()
        self.generator.playing = False
        self.generator.active = False
        self.__root.quit()
        print "Exit was successful."
        sys.exit(0)
    
    def connectCallback(self):
        print "Connecting..."
        try:
            self.devicePort = int(self.devicePortVar.get())
            self.applicationPort = int(self.applicationPortVar.get())
            self.deviceIP = self.deviceIPaddressVar.get()
            self.__touch_osc.connect(self.deviceIP, self.devicePort, self.applicationPort)
        except ValueError:
            tkMessageBox.showinfo(
                "Incorrect IP/Port Combination", 
                "Please check that the IP/Port combination you entered is correct"
            )
        except OSCClientError:
            tkMessageBox.showinfo(
                "Unable to connect to the device", 
                "Please check that the IP/Port combination you entered is correct"
            ) 
        
    def playCallback(self):
        self.generator.playing = True
    
    def pauseCallback(self):
        self.generator.playing = False
    
    def run(self):
        self.__root.mainloop()


class PresetHandler:
    
    def __init__(self, gui, idx):
        self.gui = gui
        self.idx = idx
    
    def __call__(self):
        self.gui.showState(
            self.gui.generator.readStateFromFile("%s/%s" % (self.gui.preset_dir, "preset%d.yml" % self.idx)),
            "Preset %d State Preview" % self.idx
        )
