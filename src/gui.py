import Tkinter
import sys
import traceback
import OSC
import socket
from OSC import OSCClientError
import tkMessageBox
import subprocess

class GUI(object):
    
    def __init__(self,gen,config):
        # These will be set later (might consider removing them?)
        self.deviceIP = ''
        self.devicePort = 0
        self.applicationPort = 0
        self.config = config 
        
        self.__generator = gen
        try:
            self.__root=Tkinter.Tk()
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
            
            #Add an output list that may be accessed publicly
            mainframe = Tkinter.Frame(self.__window, bd=2, relief=Tkinter.SUNKEN,width=500,height=400)
            
            #Output frame
            outputframe = Tkinter.Frame(mainframe,relief=Tkinter.SUNKEN,width=500,height=200)
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
            oscframe = Tkinter.Frame(mainframe,relief=Tkinter.SUNKEN,width=500,height=200)
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
            mainframe.grid(row=1,column=0)
            
            #Create the buttons
            buttonPane = Tkinter.PanedWindow(self.__window,orient=Tkinter.VERTICAL)
            buttonPane.grid(row=2,column=0)
            self.__createButtons(buttonPane)
            buttonPane.pack_propagate(0)
            
            #Create the connection fields
            connectPane = Tkinter.PanedWindow(self.__window,orient=Tkinter.VERTICAL)
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
        self.deviceIPaddressVar = Tkinter.StringVar()
        self.devicePortVar = Tkinter.StringVar()
        self.applicationPortVar = Tkinter.StringVar()
        self.deviceIPaddressVar.set("Unknown")
        self.devicePortVar.set(str(self.config['device_port']))
        self.applicationPortVar.set(str(self.config['application_port']))
        Tkinter.Label(pane,text="OSC settings").grid(row=0,column=0)
        Tkinter.Label(pane,text="Device IP Address : ").grid(row=1,column=0)
        Tkinter.Entry(pane,textvariable=self.deviceIPaddressVar).grid(row=1,column=1)
        Tkinter.Label(pane,text="Device Input Port : ").grid(row=2,column=0)
        Tkinter.Entry(pane,textvariable=self.devicePortVar).grid(row=2,column=1)
        Tkinter.Label(pane,text="Application Input Port : ").grid(row=3,column=0)
        Tkinter.Entry(pane,textvariable=self.applicationPortVar).grid(row=3,column=1)
    
    def __updateConnect(self,ip,port):
        pass
    
    def clearCallback(self):
        #Clears the output box
        self.output.delete(0.0,Tkinter.END)
        self.osc.delete(0.0,Tkinter.END)
        pass
    
    def exitCallback(self):
        self.__midi_output.exit_notes()
        self.__generator.playing = False
        self.__generator.active = False
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
        self.__generator.playing = True
    
    def pauseCallback(self):
        self.__generator.playing = False
    
    def run(self):
        self.__root.mainloop()
