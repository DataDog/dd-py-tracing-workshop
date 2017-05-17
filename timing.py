import time
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler("timing.log"))

def timing_decorator(func):
    def wrapped(*args, **kwargs):
        start = time.time()
        try:
            ret = func(*args, **kwargs)
        finally:
            end = time.time()
        log.info("function %s took %.2f seconds", func.__name__, end-start)
        return ret
    return wrapped    

class TimingContextManager(object):

    def __init__(self, name):
        self.name = name
        
    def __enter__(self):
        self.start = time.time()
        
    def __exit__(self):
        end = time.time()
        log.info("operation %s took %.2f seconds", self.name, end-start)