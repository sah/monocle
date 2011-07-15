# -*- coding: utf-8 -*-
#
# by Steven Hazel

import socket
import asyncore

from monocle import _o, Return, launch
from monocle.callback import Callback
from monocle.stack.network import Connection, ConnectionLost
from monocle.asyncore_stack.eventloop import evlp


class _Connection(asyncore.dispatcher_with_send):
    def __init__(self, sock=None, evlp=evlp):
        asyncore.dispatcher_with_send.__init__(self, sock=sock, map=evlp._map)
        self.max_buffer_size = 104857600
        self.buffer = ""
        self.read_cb = None
        self.connect_cb = Callback()

    def attach(self, connection):
        self._write_flushed = connection._write_flushed
        self._closed = connection._closed

    def readable(self):
        return self.read_cb is not None

    def handle_connect(self):
        cb = self.connect_cb
        self.connect_cb = None
        cb(None)

    def handle_read(self):
        self.buffer += self.recv(8192)
        if len(self.buffer) >= self.max_buffer_size:
            # Reached maximum read buffer size
            self.disconnect()
            return
        # it's possible recv called handle_close
        if self.read_cb is not None:
            read_cb = self.read_cb
            self.read_cb = None
            read_cb(None)

    def handle_close(self):
        self.close()
        # XXX: get a real reason from asyncore
        reason = IOError("Connection closed")
        self._closed(reason)

    def initiate_send(self):
        asyncore.dispatcher_with_send.initiate_send(self)
        if len(self.out_buffer) == 0:
            self._write_flushed()

    # functions to support the StackConnection interface

    def write(self, data):
        self.send(data)

    def resume(self):
        self.read_cb = Callback()

    def reading(self):
        return self.readable()

    def closed(self):
        return not self.connected

    def disconnect(self):
        self.handle_close()


class _ListeningConnection(asyncore.dispatcher):
    def __init__(self, handler, evlp=evlp):
        asyncore.dispatcher.__init__(self, map=evlp._map)
        self.handler = handler

    def handle_accept(self):
        (conn, addr) = self.accept()
        connection = Connection(_Connection(sock=conn))
        connection._stack_conn.attach(connection)
        self.handler(connection)


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128, evlp=evlp):
        @_o
        def _handler(s):
            try:
                yield launch(handler, s)
            finally:
                s.close()
        self.handler = _handler
        self.evlp = evlp
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog
        self._conn = _ListeningConnection(self.handler, evlp=evlp)
        self._conn.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._conn.set_reuse_addr()

    @_o
    def stop(self):
        self._conn.close()


class Client(Connection):
    @_o
    def connect(self, host, port, evlp=evlp):
        self._stack_conn = _Connection(evlp=evlp)
        self._stack_conn.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self._stack_conn.connect((host, port))
        self._stack_conn.attach(self)
        yield self._stack_conn.connect_cb


def add_service(service):
    service._conn.bind((service.bindaddr, service.port))
    service._conn.listen(service.port)
