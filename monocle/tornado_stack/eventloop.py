import tornado.ioloop
import time
import functools

class EventLoop(object):
    def __init__(self):
        self._tornado_ioloop = tornado.ioloop.IOLoop.instance()
        self.READ = self._tornado_ioloop.READ

    def queue_task(self, delay, callable, *args, **kw):
        def task():
            return callable(*args, **kw)
        if delay == 0:
            self._tornado_ioloop.add_callback(task)
        else:
            now = time.time()
            self._tornado_ioloop.add_timeout(now + delay, task)

    def run(self):
        self._tornado_ioloop.start()

    def halt(self):
        self._tornado_ioloop.stop()

    def _add_handler(self, *a, **k):
        self._tornado_ioloop.add_handler(*a, **k)

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt
