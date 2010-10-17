import asyncore
import time
import functools

from monocle import launch

class EventLoop(object):
    def __init__(self):
        self._running = True
        self._queue = []
        self._map = {}

    def queue_task(self, delay, callable, *args, **kw):
        now = time.time()
        when = now + delay
        self._queue.append((when, callable, args, kw))
        self._queue.sort(reverse=True)

    def run(self):
        while self._running:
            timeout = 0
            if self._queue:
                next = self._queue[-1][0] - time.time()
                if next <= 0:
                    task = self._queue.pop()
                    launch(task[1], *task[2], **task[3])
                else:
                    timeout = next
            if self._map:
                asyncore.loop(timeout=timeout, use_poll=True, count=1,
                              map=self._map)
            else:
                time.sleep(0.1)

    def halt(self):
        self._running = False

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt
