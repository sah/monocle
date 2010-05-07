import sys
import functools

# prefer fast reactors
# FIXME: this should optionally refuse to use slow ones
try:
    from twisted.internet import epollreactor
    epollreactor.install()
except:
    try:
        from twisted.internet import kqreactor
        kqreactor.install()
    except:
        try:
            from twisted.internet import iocpreactor
            iocpreactor.install()
        except:
            try:
                from twisted.internet import pollreactor
                pollreactor.install()
            except:
                pass

from twisted.internet import reactor
from twisted.internet.error import ReactorNotRunning


# thanks to Peter Norvig
def singleton(object, message="singleton class already instantiated",
              instantiated=[]):
    """
    Raise an exception if an object of this class has been instantiated before.
    """
    assert object.__class__ not in instantiated, message
    instantiated.append(object.__class__)


class EventLoop(object):
    def __init__(self):
        singleton(self, "Twisted can only have one EventLoop (reactor)")
        self._halted = False

    def queue_task(self, delay, callable, *args, **kw):
        return reactor.callLater(delay, callable, *args, **kw)

    def run(self):
        if not self._halted:
            reactor.run()

    def halt(self):
        try:
            reactor.stop()
        except ReactorNotRunning:
            self._halted = True
            pass

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt
