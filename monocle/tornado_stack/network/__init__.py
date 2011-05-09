# -*- coding: utf-8 -*-
#
# by Steven Hazel

import errno
import socket

try:
    import ssl # Python 2.6+
except ImportError:
    ssl = None

import tornado.ioloop
from tornado.iostream import IOStream, SSLIOStream

from monocle import _o, launch
from monocle.callback import Callback
from monocle.stack.network import Connection as BaseConnection
from monocle.stack.network import ConnectionLost
from monocle.tornado_stack.eventloop import evlp


class _Connection:

    def __init__(self, iostream):
        self.iostream = iostream
        self.iostream.set_close_callback(self._close_called)
        self.read_cb = None
        self.connect_cb = None

    def attach(self, connection):
        self._write_flushed = connection._write_flushed
        self._closed = connection._closed

    def connect(self, address):
        cb = Callback()
        self.connect_cb = cb
        self.iostream.connect(address, self._connect_complete)
        return cb

    def read(self, size):
        cb = Callback()
        self.read_cb = cb
        self.iostream.read_bytes(size, self._read_complete)
        return cb

    def read_until(self, s):
        cb = Callback()
        self.read_cb = cb
        self.iostream.read_until(s, self._read_complete)
        return cb

    def _connect_complete(self, result=None):
        cb = self.connect_cb
        self.connect_cb = None
        cb(result)

    def _read_complete(self, result):
        cb = self.read_cb
        self.read_cb = None
        cb(result)

    def _close_called(self, reason=None):
        # XXX: get a real reason from Tornado
        if reason is None:
            reason = IOError("Connection closed")
        if self.connect_cb is not None:
            self._connect_complete(reason)
        self._closed(reason)

    # functions to support the StackConnection interface

    def write(self, data):
        self.iostream.write(data, self._write_flushed)

    def resume(self):
        self.iostream.resume()

    def reading(self):
        return self.iostream.reading()

    def closed(self):
        return self.iostream.closed()

    def disconnect(self):
        self.iostream.close()


class Connection(BaseConnection):

    def read(self, size):
        self._check_reading()
        return self._stack_conn.read(size)

    def read_until(self, s):
        self._check_reading()
        return self._stack_conn.read_until(s)


class Service(object):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        @_o
        def _handler(s):
            try:
                yield launch(handler, s)
            finally:
                s.close()
        self.handler = _handler
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog
        self.ssl_options = None
        self._evlp = None
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
            if self.ssl_options is not None:
                assert ssl, "Python 2.6+ and OpenSSL required for SSL"
                try:
                    s = ssl.wrap_socket(s,
                                        server_side=True,
                                        do_handshake_on_connect=False,
                                        **self.ssl_options)
                except ssl.SSLError, err:
                    if err.args[0] == ssl.SSL_ERROR_EOF:
                        s.close()
                        return
                    else:
                        raise
                except socket.error, err:
                    if err.args[0] == errno.ECONNABORTED:
                        s.close()
                        return
                    else:
                        raise
                iostream = SSLIOStream(s)
            else:
                iostream = IOStream(s)
            connection = Connection(_Connection(iostream))
            connection._stack_conn.attach(connection)
            self.handler(connection)

    def _add(self, evlp):
        self._evlp = evlp
        self._evlp._add_handler(self._sock.fileno(),
                                self._connection_ready,
                                self._evlp.READ)

    @_o
    def stop(self):
        if self._evlp:
            self._evlp._remove_handler(self._sock.fileno())


class SSLService(Service):

    def __init__(self, handler, port, bindaddr="", backlog=128,
                 ssl_options=None):
        if ssl_options is None:
            ssl_options = {}
        Service.__init__(self, handler, port, bindaddr, backlog)
        self.ssl_options = ssl_options


class Client(Connection):
    def __init__(self, *args, **kwargs):
        Connection.__init__(self, *args, **kwargs)
        self.ssl_options = None

    @_o
    def connect(self, host, port):
        s = socket.socket()
        if self.ssl_options is not None:
            iostream = SSLIOStream(s, ssl_options=self.ssl_options)
        else:
            iostream = IOStream(s)
        self._stack_conn = _Connection(iostream)
        self._stack_conn.attach(self)
        self._stack_conn.connect((host, port))
        yield self._stack_conn.connect_cb


class SSLClient(Client):

    def __init__(self, ssl_options=None):
        if ssl_options is None:
            ssl_options = {}
        Connection.__init__(self)
        self.ssl_options = ssl_options


def add_service(service, evlp=evlp):
    return service._add(evlp)
