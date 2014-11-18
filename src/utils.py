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