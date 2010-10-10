import sys
import os
from multiprocessing import Process, Pipe

import monocle
from monocle import _o, Return, launch
from monocle.core import Callback
monocle.init(sys.argv[1])

from monocle.stack import eventloop

class PipeForTwisted(object):
    def __init__(self, pipe):
        self.pipe = pipe
        self.callback = Callback()

    def doRead(self):
        self.callback(False)

    def fileno(self):
        return self.pipe.fileno()

    def connectionLost(self):
        self.callback(True)

    def logPrefix(self):
        return "Pipe"

    def doWrite(self):
        self.callback(False)


@_o
def child(chan, msg):
    while True:
        d = yield chan.recv()
        print d
        if d == "hello":
            yield chan.send(msg)

@_o
def parent(chan):
    yield chan.send("hello")
    print (yield chan.recv())
    yield chan.send("there")


class ProcChannel(object):
    def __init__(self, reader, writer, joiner=None):
        self.reader = reader
        self.writer = writer
        self.joiner = joiner

    @_o
    def send(self, value):
        w = PipeForTwisted(self.writer)
        eventloop.reactor.addWriter(w)
        lost = yield w.callback
        eventloop.reactor.removeWriter(w)

        if lost:
            raise Exception("connection lost")
        self.writer.send(value)

    @_o
    def recv(self):
        r = PipeForTwisted(self.reader)
        eventloop.reactor.addReader(r)
        lost = yield r.callback
        eventloop.reactor.removeReader(r)

        if lost:
            raise Exception("connection lost")
        yield Return(self.reader.recv())

    def join(self):
        if self.joiner:
            self.joiner.join()


def launch_proc(target, *args, **kwargs):
    tc, fp = Pipe()
    tp, fc = Pipe()
    pp = ProcChannel(fp, tp)

    def proc_wrapper():
        launch(target, pp, *args, **kwargs)
        eventloop.run()
    p = Process(target=proc_wrapper)
    p.start()
    cp = ProcChannel(fc, tc, p)
    return cp

chan = launch_proc(child, "yes")
launch(parent, chan)
eventloop.run()
chan.join()
