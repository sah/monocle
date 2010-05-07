# -*- coding: utf-8 -*-
#
# by Steven Hazel

import errno
import functools
import socket

import tornado.ioloop
import tornado.iostream

from monocle import _o
from monocle.deferred import Deferred
from monocle.tornado_stack.eventloop import evlp


# This is perhaps too much of a wrapper; It would be nice to translate
# Tornado's IOStream interface more directly.
class Connection(object):
    def __init__(self, stream=None):
        self._stream = stream

    def read(self, size):
        df = Deferred()
        self._stream.read_bytes(size, df.callback)
        return df

    def read_until(self, s):
        df = Deferred()
        self._stream.read_until(s, df.callback)
        return df

    def readline(self):
        return self.read_until("\n")

    def write(self, data):
        df = Deferred()
        self._stream.write(data, lambda: df.callback(None))
        return df

    def close(self):
        self._stream.close()


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        @_o
        def _handler(s):
            yield handler(s)
            s.close()
        self.handler = _handler
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setblocking(0)
        self._sock.bind((self.bindaddr, self.port))
        self._sock.listen(self.backlog)

    def _connection_ready(self, fd, events):
        while True:
            try:
                s, address = self._sock.accept()
            except socket.error, e:
                if e[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                return
            s.setblocking(0)
            self.handler(Connection(tornado.iostream.IOStream(s)))

    def _add(self, evlp):
        evlp._add_handler(self._sock.fileno(),
                          self._connection_ready,
                          evlp.READ)


class Client(Connection):
    @_o
    def connect(self, host, port):
        s = socket.socket()
        s.connect((host, port))
        self._stream = tornado.iostream.IOStream(s)


def add_service(service, evlp=evlp):
    return service._add(evlp)
