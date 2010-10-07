import monocle
from monocle import _o
from monocle.deferred import Deferred


class ConnectionLost(Exception):
    pass


class Connection(object):
    def __init__(self, stack_conn=None):
        self._stack_conn = stack_conn
        self.writing = False
        self._flush_dfs = []

    @_o
    def read(self, size):
        self._check_reading()
        while len(self._stack_conn.buffer) < size:
            self._check_closed()
            self._stack_conn.resume()
            yield self._stack_conn.drd
        tmp = self._stack_conn.buffer[:size]
        self._stack_conn.buffer = self._stack_conn.buffer[size:]
        yield Return(tmp)

    @_o
    def read_until(self, s):
        self._check_reading()
        while True:
            size = self._stack_conn.buffer.find(s)
            if size != -1:
                size += len(s)
                break
            self._check_closed()
            self._stack_conn.resume()
            yield self._stack_conn.drd
        tmp = self._stack_conn.buffer[:size]
        self._stack_conn.buffer = self._stack_conn.buffer[size:]
        yield Return(tmp)

    def readline(self):
        return self.read_until("\n")

    def write(self, data):
        self._check_closed()
        self.writing = True
        self._stack_conn.write(data)
        return self.flush()

    def _write_flushed(self, result=None):
        self.writing = False
        dfs = self._flush_dfs
        self._flush_dfs = []
        for df in dfs:
            df.callback(result)

    def flush(self):
        self._check_closed()
        df = Deferred()
        self._flush_dfs.append(df)
        if not self.writing:
            self._write_flushed()
        return df

    def _closed(self, reason):
        cl = ConnectionLost(str(reason))
        cl.original = reason
        self._write_flushed(cl)
        if self._stack_conn.drd:
            df = self._stack_conn.drd
            self._stack_conn.drd = None
            df.callback(cl)

    def close(self):
        self._stack_conn.disconnect()

    def _check_reading(self):
        if self._stack_conn.reading():
            raise IOError("Already reading")

    def _check_closed(self):
        if self._stack_conn.closed():
            raise IOError("Stream is closed")


if monocle._stack_name == 'twisted':
    from monocle.twisted_stack.network import *
elif monocle._stack_name == 'tornado':
    from monocle.tornado_stack.network import *
elif monocle._stack_name == 'asyncore':
    from monocle.asyncore_stack.network import *
