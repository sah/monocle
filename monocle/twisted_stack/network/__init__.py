# -*- coding: utf-8 -*-
#
# by Steven Hazel

from monocle.twisted_stack.eventloop import reactor
from twisted.internet.protocol import Factory, Protocol, ClientCreator, ServerFactory

from monocle import _o, Return, launch
from monocle.callback import Callback
from monocle.stack.network import Connection, ConnectionLost


class _Connection(Protocol):

    def attach(self, connection):
        self._write_flushed = connection._write_flushed
        self._closed = connection._closed

    def connectionMade(self):
        self.max_buffer_size = 104857600
        self.buffer = ""
        self.read_cb = None
        self.transport.pauseProducing()
        if hasattr(self, "factory"):
            connection = Connection(self)
            self.attach(connection)
        self.transport.registerProducer(self, False)
        if hasattr(self, "factory"):
            self.factory.handler(connection)

    def dataReceived(self, data):
        self.transport.pauseProducing()
        self.buffer += data
        if len(self.buffer) >= self.max_buffer_size:
            # Reached maximum read buffer size
            self.disconnect()
            return
        read_cb = self.read_cb
        self.read_cb = None
        read_cb(None)

    def connectionLost(self, reason):
        self._closed(reason.value)

    # functions to support IPullProducer

    def resumeProducing(self):
        if self._write_flushed:
            self._write_flushed()

    def stopProducing(self):
        # we just wait for the connection lost event
        pass

    # functions to support the StackConnection interface

    def write(self, data):
        self.transport.write(data)

    def resume(self):
        self.read_cb = Callback()
        self.transport.resumeProducing()

    def reading(self):
        return self.read_cb is not None

    def closed(self):
        return not (self.transport.connected and not self.transport.disconnecting)

    def disconnect(self):
        if self.transport:
            self.transport.loseConnection()


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        self.factory = Factory()
        self.factory.protocol = _Connection
        @_o
        def _handler(s):
            try:
                yield launch(handler, s)
            finally:
                s.close()
        self.factory.handler = _handler
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog


class Client(Connection):
    @_o
    def connect(self, host, port):
        self._stack_conn = _Connection()
        self._stack_conn.attach(self)
        c = ClientCreator(reactor, lambda: self._stack_conn)
        yield c.connectTCP(host, port)


def add_service(service):
    reactor.listenTCP(service.port, service.factory,
                      backlog=service.backlog,
                      interface=service.bindaddr)
