import collections

from monocle import _o, Return
from monocle.stack.network import ConnectionLost


class HttpHeaders(collections.MutableMapping):
    def __init__(self, headers=None):
        self.headers = []
        self.keys = set()
        if hasattr(headers, 'iteritems'):
            for k, v in headers.iteritems():
                self.add(k, v)
        else:
            for k, v in headers or []:
                self.add(k, v)

    def __len__(self):
        return len(self.headers)

    def keys(self):
        return [k for k, v in self.headers]

    def add(self, key, value):
        key = key.lower()
        self.keys.add(key)
        self.headers.append((key, value))

    def items(self):
        return self.headers

    def __iter__(self):
        return (k for k, v in self.headers)

    def iteritems(self):
        return (x for x in self.headers)

    def __repr__(self):
        return repr(self.headers)

    def __getitem__(self, key):
        key = key.lower()
        if not key in self.keys:
            raise KeyError(key)
        vals = [v for k, v in self.headers if k==key]
        if len(vals) == 1:
            return vals[0]
        else:
            return vals

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        return self.add(key, value)

    def __delitem__(self, key):
        key = key.lower()
        if not key in self.keys:
            raise KeyError(key)
        self.keys.remove(key)
        self.headers = [(k, v) for k, v in self.headers if k != key]


class HttpResponse(object):
    def __init__(self, code, msg=None, headers=None, body=None, proto=None):
        self.code = code
        self.msg = msg
        self.headers = headers
        self.body = body
        self.proto = proto


def parse_headers(lines):
    headers = HttpHeaders()
    for line in lines:
        k, v = line.split(":", 1)
        headers.add(k, v.lstrip())
    return headers


def parse_request(data):
    data = data[:-4]
    lines = data.split("\r\n")
    method, path, proto = lines[0].split(" ", 2)
    headers = parse_headers(lines[1:])
    return method, path, proto, headers


def parse_response(data):
    data = data[:-4]
    lines = data.split("\r\n")
    parts = lines[0].split(" ")
    proto = parts[0]
    code = parts[1]
    if len(parts) > 2:
        msg = parts[2]
    else:
        msg = ""
    headers = parse_headers(lines[1:])
    return proto, code, msg, headers


@_o
def read_request(conn):
    data = yield conn.read_until("\r\n\r\n")
    method, path, proto, headers = parse_request(data)
    body = None
    if method in ["POST", "PUT"] and "Content-Length" in headers:
        cl = int(headers["Content-Length"])
        body = yield conn.read(cl)
    yield Return(method, path, proto, headers, body)


@_o
def write_request(conn, method, path, headers, body=None):
    yield conn.write("%s %s HTTP/1.1\r\n" % (method, path))
    for k, v in headers.iteritems():
        yield conn.write("%s: %s\r\n" % (k, v))
    yield conn.write("\r\n")
    if body:
        yield conn.write(body)


@_o
def read_response(conn):
    data = yield conn.read_until("\r\n\r\n")
    proto, code, msg, headers = parse_response(data)

    proto = proto.lower()
    content_length = int(headers.get('Content-Length', 0))
    body = ""

    # Messages MUST NOT include both a Content-Length header field and
    # a non-identity transfer-coding. If the message does include a
    # non- identity transfer-coding, the Content-Length MUST be
    # ignored.
    if headers.get('Transfer-Encoding', '').lower() == 'chunked':
        while True:
            line = yield conn.read_until("\r\n")
            line = line[:-2]
            parts = line.split(';')
            chunk_len = int(parts[0], 16)
            body += yield conn.read(chunk_len)
            yield conn.read_until("\r\n")
            if not chunk_len:
                break
    elif content_length:
        body = yield conn.read(content_length)
    elif ((proto == 'http/1.0' and
           not headers.get('Connection', '').lower() == 'keep-alive')
          or
          (proto == 'http/1.1' and
           headers.get('Connection', '').lower() == 'close')):
        while True:
            try:
                body += yield conn.read_some()
            except ConnectionLost:
                break

    yield Return(HttpResponse(code, msg, headers, body, proto))


class HttpClient(object):
    DEFAULT_PORTS = {'http': 80,
                     'https': 443}

    def __init__(self):
        self.client = None
        self.scheme = None
        self.host = None
        self.port = None
        self._timeout = None

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout_setter(self, value):
        self._timeout = value
        if self.client:
            self.client.timeout = value

    @_o
    def connect(self, host, port, scheme='http', timeout=None):
        if timeout is not None:
            # this parameter is deprecated
            self.timeout = None

        if self.client and not self.client.is_closed():
            self.client.close()

        if scheme == 'http':
            self.client = Client()
        elif scheme == 'https':
            self.client = SSLClient()
        else:
            raise HttpException('unsupported url scheme %s' % scheme)
        self.scheme = scheme
        self.host = host
        self.port = port
        self.client.timeout = self._timeout
        yield self.client.connect(self.host, self.port)

    @_o
    def request(self, url, headers=None, method='GET', body=None):
        parts = urlparse.urlsplit(url)
        scheme = parts.scheme or self.scheme
        if parts.scheme and parts.scheme not in ['http', 'https']:
            raise HttpException('unsupported url scheme %s' % parts.scheme)
        host = parts.hostname or self.host
        path = parts.path
        if parts.query:
            path += '?' + parts.query

        if scheme != self.scheme:
            raise HttpException("URL is %s but connection is %s" %
                                (scheme, self.scheme))

        if not headers:
            headers = HttpHeaders()
        headers.setdefault('User-Agent', 'monocle/%s' % VERSION)
        headers.setdefault('Host', host)
        if body is not None:
            headers['Content-Length'] = str(len(body))

        yield write_request(self.client, method, path, headers, body)
        response = yield read_response(self.client)
        yield Return(response)

    def close(self):
        self.client.close()

    def is_closed(self):
        return self.client is None or self.client.is_closed()

    @classmethod
    @_o
    def query(cls, url, headers=None, method='GET', body=None):
        self = cls()
        parts = urlparse.urlsplit(url)
        host = parts.hostname
        port = parts.port or self.DEFAULT_PORTS[parts.scheme]

        if not self.client or self.client.is_closed():
            yield self.connect(host, port, scheme=parts.scheme)
        elif not (self.host, self.port) == (host, port):
            self.client.close()
            yield self.connect(host, port, scheme=parts.scheme)

        result = yield self.request(url, headers, method, body)
        self.close()
        yield Return(result)


import monocle
if monocle._stack_name == 'twisted':
    from monocle.twisted_stack.network.http import *
elif monocle._stack_name == 'tornado':
    from monocle.tornado_stack.network.http import *
