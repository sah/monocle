# -*- coding: utf-8 -*-
#
# by Steven Hazel

import os
import sys
import time
import re
import logging
import logging.handlers
from cgi import parse_qs
from functools import partial

from monocle.twisted_stack.eventloop import reactor
import twisted.internet.error
from twisted.internet.protocol import Factory, Protocol, ClientCreator, ServerFactory

from monocle import _o
from monocle.deferred import Deferred


class _Connection(Protocol):
    def __init__(self):
        try:
            Protocol.__init__(self)
        except AttributeError:
            pass
        self.buffer = ""
        self.drd = Deferred()

    def connectionMade(self):
        self.peer = self.transport.getPeer()
        self.transport.pauseProducing()
        try:
            self.factory.handler(Connection(self))
        except AttributeError:
            pass

    def dataReceived(self, data):
        self.transport.pauseProducing()
        self.buffer += data
        self.drd.callback(self.buffer)

    def resume(self):
        # resumeProducing throws an AssertionError if the following
        # condition isn't met; the right thing to do is just not
        # resume, because subsequent IO operations will have an error
        # for us.
        if self.transport.connected and not self.transport.disconnecting:
            self.transport.resumeProducing()
        self.drd = Deferred()

    def connectionLost(self, reason):
        self.drd.callback(reason.value)


class Connection(object):
    def __init__(self, proto=None):
        self._proto = proto

    @_o
    def read(self, size):
        while len(self._proto.buffer) < size:
            self._proto.resume()
            yield self._proto.drd
        tmp = self._proto.buffer[:size]
        self._proto.buffer = self._proto.buffer[size:]
        yield tmp

    @_o
    def read_until(self, s):
        while not s in self._proto.buffer:
            self._proto.resume()
            yield self._proto.drd
        tmp, self._proto.buffer = self._proto.buffer.split(s, 1)
        yield (tmp + s)

    def readline(self):
        return self.read_until("\n")

    @_o
    def write(self, data):
        self._proto.transport.write(data)

    def close(self):
        if self._proto.transport:
            self._proto.transport.loseConnection()


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        self.factory = Factory()
        self.factory.protocol = _Connection
        @_o
        def _handler(s):
            yield handler(s)
            s.close()
        self.factory.handler = _handler
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog


class Client(Connection):
    @_o
    def connect(self, host, port):
        c = ClientCreator(reactor, _Connection)
        self._proto = yield c.connectTCP(host, port)


def add_service(service):
    reactor.listenTCP(service.port, service.factory,
                      backlog=service.backlog,
                      interface=service.bindaddr)
