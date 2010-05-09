# -*- coding: utf-8 -*-
#
# by Steven Hazel

from collections import deque
from deferred import Deferred
from monocle.stack.eventloop import queue_task
from monocle import _o


# Go-style channels
class Channel(object):
    def __init__(self, bufsize=0):
        self.bufsize = bufsize
        self._msgs = deque()
        self._wait_df = None
        self._fire_df = None

    @_o
    def fire(self, value):
        if not self._wait_df:
            if len(self._msgs) >= self.bufsize:
                if not self._fire_df:
                    self._fire_df = Deferred()
                yield self._fire_df

        if not self._wait_df:
            assert (len(self._msgs) < self.bufsize)
            self._msgs.append(value)
            return

        assert(len(self._msgs) == 0)
        df = self._wait_df
        self._wait_df = None
        queue_task(0, df.callback, value)

    @_o
    def wait(self):
        popped = False
        if self._msgs:
            value = self._msgs.popleft()
            popped = True

        if not self._wait_df:
            self._wait_df = Deferred()
        wait_df = self._wait_df

        if self._fire_df:
            df = self._fire_df
            self._fire_df = None
            queue_task(0, df.callback, None)

        if not popped:
            value = yield wait_df
        yield value


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
    yield [(True, r) if x == i else None for i in xrange(len(a))]


waits = {}

@_o
def fire(name, value):
    if name in waits:
        df = waits[name]
        waits.pop(name)
        df.callback(value)

@_o
def wait(name):
    waits[name] = waits.get(name, Deferred())
    r = yield waits[name]
    yield r


# sequencing
sequences = {}

def enter_sequence(name):
    d = Deferred()
    sequence = sequences.get(name, collections.deque())
    id = uuid.uuid4().hex
    sequence.append({'id': id, 'deferred': d})
    sequences[name] = sequence
    if len(sequence) == 1:
        d.callback(id)
    return d

def exit_sequence(name, id, queue_task):
    sequence = sequences[name]
    section = sequence.popleft()
    assert section['id'] == id
    if sequence:
        queue_task(0, sequence[0]['deferred'].callback, sequence[0]['id'])
    else:
        sequences.pop(name)

def sequence(name, queue_task):
    outer = Deferred()
    inner = enter_sequence(name)

    @contextmanager
    def exiter(id):
        try:
            yield
        finally:
            exit_sequence(name, id, queue_task)

    def cb(id):
        outer.callback(exiter(id))
    inner.add_callback(cb)
    return outer
