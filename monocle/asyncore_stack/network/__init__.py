# -*- coding: utf-8 -*-
#
# by Steven Hazel

import errno
import functools
import socket
import asyncore

from monocle import _o
from monocle.deferred import Deferred
from monocle.asyncore_stack.eventloop import evlp


class _Connection(asyncore.dispatcher):
    def __init__(self, sock=None, evlp=evlp):
        asyncore.dispatcher.__init__(self, sock=sock, map=evlp._map)
        self.paused = True
        self.buffer = ""
        self.wbuf = ""
        self.drd = Deferred()
        self.dwd = None
        self.connect_df = Deferred()

    def handle_connect(self):
        self.connect_df.callback(None)

    def handle_read(self):
        if not self.paused:
            self.buffer += self.recv(8192)
            self.paused = True
            self.drd.callback(self.buffer)

    def resume(self):
        self.paused = False
        self.drd = Deferred()

    def handle_close(self):
        self.close()
        self.drd.callback(None)

    def write(self, data):
        self.wbuf += data
        self.dwd = Deferred()

    def handle_write(self):
        if self.wbuf:
            sent = self.send(self.wbuf)
            self.wbuf = self.wbuf[sent:]
        if self.dwd and not self.wbuf:
            self.dwd.callback(None)
            self.dwd = None


class Connection(object):
    def __init__(self, dispatcher=None):
        self._dispatcher = dispatcher

    @_o
    def read(self, size):
        while len(self._dispatcher.buffer) < size:
            self._dispatcher.resume()
            yield self._dispatcher.drd
        tmp = self._dispatcher.buffer[:size]
        self._dispatcher.buffer = self._dispatcher.buffer[size:]
        yield tmp

    @_o
    def read_until(self, s):
        while not s in self._dispatcher.buffer:
            self._dispatcher.resume()
            yield self._dispatcher.drd
        tmp, self._dispatcher.buffer = self._dispatcher.buffer.split(s, 1)
        yield (tmp + s)

    def readline(self):
        return self.read_until("\n")

    @_o
    def write(self, data):
        self._dispatcher.write(data)
        yield self._dispatcher.dwd

    def close(self):
        if self._dispatcher:
            self._dispatcher.close()


class Client(Connection):
    @_o
    def connect(self, host, port, evlp=evlp):
        self._dispatcher = _Connection(evlp=evlp)
        self._dispatcher.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._dispatcher.connect((host, port))
        yield self._dispatcher.connect_df


class _ListeningConnection(asyncore.dispatcher):
    def __init__(self, handler, evlp=evlp):
        asyncore.dispatcher.__init__(self, map=evlp._map)
        self.handler = handler

    def handle_accept(self):
        (conn, addr) = self.accept()
        self.handler(Connection(_Connection(sock=conn)))


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128, evlp=evlp):
        @_o
        def _handler(s):
            yield handler(s)
            s.close()
        self.handler = _handler
        self.evlp = evlp
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog
        self._conn = _ListeningConnection(self.handler, evlp=evlp)
        self._conn.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._conn.set_reuse_addr()


def add_service(service):
    service._conn.bind((service.bindaddr, service.port))
    service._conn.listen(service.port)
