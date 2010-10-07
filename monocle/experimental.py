# -*- coding: utf-8 -*-
#
# by Steven Hazel

from collections import deque
from deferred import Deferred
from monocle.stack.eventloop import queue_task
from monocle import _o, Return


# Go-style channels
class Channel(object):
    def __init__(self, bufsize=0):
        self.bufsize = bufsize
        self._msgs = deque()
        self._recv_df = None
        self._send_df = None

    @_o
    def send(self, value):
        if not self._recv_df:
            if len(self._msgs) >= self.bufsize:
                if not self._send_df:
                    self._send_df = Deferred()
                yield self._send_df

        if not self._recv_df:
            assert (len(self._msgs) < self.bufsize)
            self._msgs.append(value)
            return

        assert(len(self._msgs) == 0)
        df = self._recv_df
        self._recv_df = None
        queue_task(0, df.callback, value)

    @_o
    def recv(self):
        popped = False
        if self._msgs:
            value = self._msgs.popleft()
            popped = True

        if not self._recv_df:
            self._recv_df = Deferred()
        recv_df = self._recv_df

        if self._send_df:
            df = self._send_df
            self._send_df = None
            queue_task(0, df.callback, None)

        if not popped:
            value = yield recv_df
        yield Return(value)


# Some ideas from diesel:

# This is really not a very good idea without limiting it to a set of
# cancelable operations...
@_o
def first_of(*a):
    df = Deferred()
    df.called = False
    for i, d in enumerate(a):
        def cb(result, i=i):
            if isinstance(result, Exception):
                raise result
            if not df.called:
                df.called = True
                df.callback((i, result))
        d.add_callback(cb)
    x, r = yield df
    yield Return([(True, r) if x == i else None for i in xrange(len(a))])


waits = {}

@_o
def fire(name, value):
    if name in waits:
        df = waits[name]
        waits.pop(name)
        df.callback(value)

@_o
def wait(name):
    waits.setdefault(name, Deferred())
    r = yield waits[name]
    yield Return(r)
