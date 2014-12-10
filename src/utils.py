def dump_queue(queue):
    """
    Empties all pending items in a queue and returns them in a list.
    """
    result = []

    for i in iter(queue.get, 'STOP'):
        result.append(i)
    return result

def make_set(seq): # Order preserving
    ''' Modified version of Dave Kirby solution '''
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

def readState(self, file):
    # Read algorithm state
    try:
        with open(self.file) as f:
            state = yaml.load(f)
    except IOError:
        t, v, tb = sys.exc_info()
        print v
        traceback.print_tb(tb)
        sys.exit(1)
    
    # Check that preset file is well-formed.
    try:
        self.__checkStateFormat(state)
    except MultipleInvalid:
        t, v, tb = sys.exc_info()
        print v
        traceback.print_tb(tb)
        sys.exit(1)
    
    # Fills the blanks for all of the non markov stuff.
    for attributeName in ['rhythm', 'amplitude', 'path', 'pitch']:
        # Assign the order engine
        computeOrderEng(state, attributeName)
    
    state['rhythm']['pattern'] = self.serialize_rhythm(state['rhythm']['pattern'])
    state['pitch']['pattern'] = self.serialize_pitch(state['pitch']['pattern'])
    
    # Indicates currently selected path on Path Map. Value can be 0-7.
    state['path']['selected'] = 0
    state['rhythm']['row_idx'] = 0
    return state

def computeOrderEng(self, parameters, attributeName):
    """
    This method computes the order parameter of some of the attributes of the state
    """
    if attributeName not in ["path", "rhythm", "pitch", "amplitude"]:
        raise Exception("Attempting to assign an order to an invalid attribute!")
    else:
        size = self.feature_sizes[attributeName]
        # If not already set, put a random value here.
        if parameters[attributeName]['order'] == 'cyclic':
            parameters[attributeName]['order_eng'] = CyclicGenerator(size)
        elif parameters[attributeName]['order'] == 'random':
            parameters[attributeName]['order_eng'] = UniformRandomGenerator(size)
        else:
            raise Exception("Order type %s is invalid!", parameters[attributeName]['order'])
    return