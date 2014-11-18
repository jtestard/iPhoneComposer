import gui
import yappi
import generator
import midioutput
import touchosc
import os
import argparse
import yaml

from threading import Thread

def generator_task(generator):
    print "New generator worker started..."
    generator.run()
    return

def midiOut_task(midiout):
    print "New midi output worker started..."
    osc
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
        "-a","--algorithm-file",
        required=False,
        default=currentdir+"/../resources/presets/default.yml",
        action="store",
        dest="algorithm_filename",
        help = "File containing the state of the algorithm used by the application."
    )
    parser.add_argument(
        "-c","--config-file",
        required=False,
        default=currentdir+"/../resources/application/player1_config.yml",
        action="store",
        dest="config_filename",
        help="File containing application default configurations"
    )
    parser.add_argument(
        "-o","--osc-filename",
        required=False,
        default=currentdir+"/../resources/osc/oscmap.yml",
        action="store",
        dest="osc_filename",
        help="File containing osc control mappings"
    )
    options = parser.parse_args()

    # Obtaining configuration file names
    gen_filename = options.algorithm_filename 
    oscmap_filename = options.osc_filename
    config_filename = options.config_filename
    
    # Building config object
    with open(config_filename) as config_file:
        config = yaml.load(config_file)

    # Building modules
    print "Building modules..."
    gen = generator.Generator(gen_filename, config)
    print "Generator setup complete"
    gui = gui.GUI(gen, config)
    print "GUI setup complete"
    midiout = midioutput.MidiOut(gen, gui, config)
    print "MidiOut setup complete"
    osc = touchosc.TouchOSC(gen, gui, oscmap_filename, config)
    print "OSC setup complete"
    
    # Building workers
    print("Building workers...")
    generator_worker = Thread(target=generator_task,args=(gen,))
    midiOut_worker = Thread(target=midiOut_task,args=(midiout,))
    osc_worker = Thread(target=osc_task,args=(osc,))
    
    # Start workers
    yappi.start()
    generator_worker.daemon = True
    midiOut_worker.daemon = True
    osc_worker.daemon = True
    generator_worker.start()
    midiOut_worker.start()
    osc_worker.start()
    
    # Start GUI
    gui.run()
    yappi.get_func_stats().print_all() 
