import gui
import generator
import midioutput
import touchosc
import os
import argparse

from tkFileDialog   import askopenfilename
from threading import Thread

def generator_task(generator):
    print "New generator worker started..."
    generator.run()
    return

def midiOut_task(midiout):
    print "New midi output worker started..."
    midiout.run()
    pass

def osc_task(osc):
    print "New osc worker started..."
    osc.run()
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    print "### iPhone Composer Python Music Generator ###"
    currentdir = os.path.dirname(os.path.realpath(__file__))
    
    parser.add_argument(
        "-f","--file",
        required=False,
        default=currentdir+"/../resources/default.yml",
        action="store",
        dest="filename",
        help = "file name"
    )
    options = parser.parse_args()

    # Obtaining configuration file names
    gen_filename = options.filename 
    oscmap_filename = currentdir+"/../resources/oscmap.yml"
    config_filename = "%s/../resources/oscmap.yml" % currentdir
    
    # Building config object
    with open(config_filename) as config_file:
        config = yaml.load(config_file)

    #Building modules
    gen = generator.Generator(gen_filename, config)
    gui = gui.GUI(gen, config)
    midiout = midioutput.MidiOut(gen, gui, config)
    osc = touchosc.TouchOSC(gen, gui, oscmap_filename, config)
    
    #Building workers
    generator_worker = Thread(target=generator_task,args=(gen,))
    midiOut_worker = Thread(target=midiOut_task,args=(midiout,))
    osc_worker = Thread(target=osc_task,args=(osc,))
    
    #Start workers
    generator_worker.start()
    midiOut_worker.start()
    osc_worker.start()
    
    #Start GUI
    gui.run()
    
    #Prepare interrupt
    generator_worker.join()
    midiOut_worker.join()
    pass
