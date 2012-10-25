import tornado.ioloop
import time
import thread

from monocle import launch


class Task(object):
    def __init__(self, tornado_ioloop, timeout):
        self._timeout = timeout
        self._tornado_ioloop = tornado_ioloop

    def cancel(self):
        self._tornado_ioloop.remove_timeout(self._timeout)


class EventLoop(object):
    def __init__(self):
        self._tornado_ioloop = tornado.ioloop.IOLoop.instance()
        self.READ = self._tornado_ioloop.READ
        self._thread_ident = thread.get_ident()

    def queue_task(self, delay, callable, *args, **kw):
        def task():
            return launch(callable, *args, **kw)
        def queue():
            now = time.time()
            timeout = self._tornado_ioloop.add_timeout(now + delay, task)
            return Task(self._tornado_ioloop, timeout)

        if thread.get_ident() != self._thread_ident:
            self._tornado_ioloop.add_callback(queue)
        else:
            return queue()

    def run(self):
        self._tornado_ioloop.start()

    def halt(self):
        self._tornado_ioloop.stop()

    def _add_handler(self, *a, **k):
        self._tornado_ioloop.add_handler(*a, **k)

    def _remove_handler(self, *a, **k):
        self._tornado_ioloop.remove_handler(*a, **k)

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt
