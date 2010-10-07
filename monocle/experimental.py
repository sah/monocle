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
        self._recv_cb = None
        self._send_cb = None

    @_o
    def send(self, value):
        if not self._recv_cb:
            if len(self._msgs) >= self.bufsize:
                if not self._send_cb:
                    self._send_cb = Callback()
                yield self._send_cb

        if not self._recv_cb:
            assert (len(self._msgs) < self.bufsize)
            self._msgs.append(value)
            return

        assert(len(self._msgs) == 0)
        cb = self._recv_cb
        self._recv_cb = None
        queue_task(0, cb, value)

    @_o
    def recv(self):
        popped = False
        if self._msgs:
            value = self._msgs.popleft()
            popped = True

        if not self._recv_cb:
            self._recv_cb = Callback()
        recv_cb = self._recv_cb

        if self._send_cb:
            cb = self._send_cb
            self._send_cb = None
            queue_task(0, cb, None)

        if not popped:
            value = yield recv_cb
        yield Return(value)


# Some ideas from diesel:

# This is really not a very good idea without limiting it to a set of
# cancelable operations...
@_o
def first_of(*a):
    cb = Callback()
    cb.called = False
    for i, d in enumerate(a):
        def cb(result, i=i):
            if isinstance(result, Exception):
                raise result
            if not cb.called:
                cb.called = True
                cb((i, result))
        d.register(cb)
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
