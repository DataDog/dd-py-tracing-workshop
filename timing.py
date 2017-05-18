from functools import wraps
import time
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler("timing.log"))

def timing_decorator(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        start = time.time()
        try:
            ret = func(*args, **kwargs)
        finally:
            end = time.time()
        log.info("function %s took %.3f seconds", func.__name__, end-start)
        return ret
    return wrapped

class TimingContextManager(object):

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_value, traceback):
        end = time.time()
        log.info("operation %s took %.3f seconds", self.name, end-self.start)
