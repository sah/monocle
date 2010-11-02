# -*- coding: utf-8 -*-
#
# by Steven Hazel

from collections import deque
from callback import Callback
from monocle.stack.eventloop import queue_task
from monocle import _o, Return


# Go-style channels
class Channel(object):
    def __init__(self, bufsize=0):
        self.bufsize = bufsize
        self._msgs = deque()
        self._recv_cbs = deque()
        self._send_cbs = deque()

    @_o
    def send(self, value):
        if not self._recv_cbs:
            if len(self._msgs) >= self.bufsize:
                cb = Callback()
                self._send_cbs.append(cb)
                yield cb

        if not self._recv_cbs:
            assert len(self._msgs) < self.bufsize, "No receive callback when buffer full (%s of %s slots used)" % (len(self._msgs), self.bufsize)
            self._msgs.append(value)
            return

        assert len(self._msgs) == 0, "Triggering receiver when buffer has %s slots full" % len(self._msgs)
        cb = self._recv_cbs.popleft()
        queue_task(0, cb, value)

    @_o
    def recv(self):
        popped = False
        if self._msgs:
            value = self._msgs.popleft()
            popped = True
        else:
            rcb = Callback()
            self._recv_cbs.append(rcb)

        if self._send_cbs:
            cb = self._send_cbs.popleft()
            queue_task(0, cb, None)

        if not popped:
            value = yield rcb
        yield Return(value)


# Some ideas from diesel:

# This is really not a very good idea without limiting it to a set of
# cancelable operations...
@_o
def first_of(*a):
    cb = Callback()
    cb.called = False
    for i, c in enumerate(a):
        def cb(result, i=i):
            if isinstance(result, Exception):
                raise result
            if not cb.called:
                cb.called = True
                cb((i, result))
        c.add(cb)
    x, r = yield cb
    yield Return([(True, r) if x == i else None for i in xrange(len(a))])


waits = {}

@_o
def fire(name, value):
    if name in waits:
        cb = waits[name]
        waits.pop(name)
        cb(value)

@_o
def wait(name):
    waits.setdefault(name, Callback())
    r = yield waits[name]
    yield Return(r)
