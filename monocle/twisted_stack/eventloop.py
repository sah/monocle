import sys
import thread
import functools

from monocle import launch

# prefer fast reactors
# FIXME: this should optionally refuse to use slow ones
if not "twisted.internet.reactor" in sys.modules:
    try:
        from twisted.internet import epollreactor
        epollreactor.install()
    except:
        try:
            from twisted.internet import kqreactor
            kqreactor.install()
        except:
            try:
                from twisted.internet import pollreactor
                pollreactor.install()
            except:
                pass

from twisted.internet import reactor
try:
    from twisted.internet.error import ReactorNotRunning
except ImportError:
    ReactorNotRunning = RuntimeError


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
        self._thread_ident = thread.get_ident()

    def queue_task(self, delay, callable, *args, **kw):
        if thread.get_ident() != self._thread_ident:
            reactor.callFromThread(reactor.callLater, delay, launch, callable, *args, **kw)
        else:
            reactor.callLater(delay, launch, callable, *args, **kw)

    def run(self):
        if not self._halted:
            self._thread_ident = thread.get_ident()
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
