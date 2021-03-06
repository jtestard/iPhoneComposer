import gui
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
    parser.add_argument(
        "-p", "--preset-directory",
        required=False,
        default=currentdir+"/../resources/presets",
        action="store",
        dest="preset_dir",
        help = """
            Directory containing presets to be used in the application. Presets must be 
            within the root of that directory and must bear the name preset[x].yml, where
            x is a value from 1 to 12. That preset will be matched to its corresponding 
            position on the application.
            !! WARNING !! All 12 presets must be present in the root of the directory.
        """
    )
    
    options = parser.parse_args()

    # Obtaining configuration file names
    gen_filename = options.algorithm_filename 
    oscmap_filename = options.osc_filename
    config_filename = options.config_filename
    preset_dir = options.preset_dir
    
    # Building config object
    with open(config_filename) as config_file:
        config = yaml.load(config_file)

    # Building modules
    print "Building modules..."
    gen = generator.Generator(gen_filename, config)
    print "Generator setup complete"
    gui = gui.GUI(gen, config, preset_dir)
    print "GUI setup complete"
    midiout = midioutput.MidiOut(gen, gui, config)
    gui.set_midi_output(midiout)
    print "MidiOut setup complete"
    osc = touchosc.TouchOSC(gen, gui, oscmap_filename, config)
    gui.set_touch_osc(osc)
    midiout.set_touch_osc(osc)
    osc.set_midi_out(midiout)
    osc.set_preset_dir(preset_dir)
    print "OSC setup complete"
    
    # Building workers
    print("Building workers...")
    generator_worker = Thread(target=generator_task,args=(gen,))
    midiOut_worker = Thread(target=midiOut_task,args=(midiout,))
    osc_worker = Thread(target=osc_task,args=(osc,))
    
    # Start workers
    generator_worker.daemon = True
    midiOut_worker.daemon = True
    osc_worker.daemon = True
    generator_worker.start()
    midiOut_worker.start()
    osc_worker.start()
    
    # Start GUI
    gui.run()
