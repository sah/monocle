# -*- coding: utf-8 -*-
#
# by Steven Hazel

import urlparse

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from monocle import _o, Return, VERSION, launch
from monocle.callback import Callback
from monocle.twisted_stack.eventloop import reactor

from twisted.internet import ssl
from twisted.internet.protocol import ClientCreator
from twisted.web.http import HTTPClient as TwistedHTTPClient
from twisted.web import server, resource


class HttpException(Exception): pass

class HttpHeaders(OrderedDict): pass


class HttpResponse(object):
    def __init__(self, code, headers, body):
        self.code = code
        self.headers = headers
        self.body = body


class _HttpClient(TwistedHTTPClient):
    def __init__(self):
        try:
            TwistedHTTPClient.__init__(self)
        except AttributeError:
            pass
        self.code = None
        self.headers = OrderedDict()
        self.connect_cb = Callback()
        self.response_cb = Callback()

    def connectionMade(self):
        self.connect_cb(None)

    def handleStatus(self, protocol, code, message):
        self.code = code

    def handleHeader(self, name, value):
        self.headers[name] = value

    def handleResponse(self, data):
        self.response_cb(HttpResponse(self.code, self.headers, data))

    def close(self):
        if self.transport:
            self.transport.loseConnection()


class HttpClient(object):
    DEFAULT_PORTS = {'http': 80,
                     'https': 443}

    _HEADER_NORMS = dict(((x.lower(), x) for x in ['User-Agent', 'Host']))

    def __init__(self):
        self._proto = None

    def _normalize_header_name(self, name):
        return self._HEADER_NORMS.get(name.lower(), name)

    def _normalize_headers(self, headers):
        return OrderedDict(
            ((self._normalize_header_name(key), value)
             for key, value in headers.iteritems()))

    @_o
    def connect(self, host, port, scheme='http'):
        self.host = host
        self.port = port
        c = ClientCreator(reactor, _HttpClient)
        if scheme == 'http':
            self._proto = yield c.connectTCP(self.host, self.port)
        elif scheme == 'https':
            self._proto = yield c.connectSSL(self.host, self.port,
                                             ssl.ClientContextFactory())
        else:
            raise HttpException('unsupported url scheme %s' % scheme)
        yield self._proto.connect_cb

    @_o
    def request(self, url, headers=None, method='GET', body=None):
        parts = urlparse.urlsplit(url)
        if parts.scheme not in ['http', 'https']:
            raise HttpException('unsupported url scheme %s' % parts.scheme)
        host = parts.hostname
        port = parts.port or self.DEFAULT_PORTS[parts.scheme]
        path = '/' + url.split('/', 3)[3]

        if not headers:
            headers = OrderedDict()
        headers = self._normalize_headers(headers)
        headers.setdefault('User-Agent', 'monocle/%s' % VERSION)
        headers.setdefault('Host', host)
        if body is not None:
            headers.setdefault('Content-Length', str(len(body)))

        if not self._proto or not self._proto.transport.connected:
            yield self.connect(host, port, scheme=parts.scheme)

        self._proto.sendCommand(method, path)
        for k, v in headers.iteritems():
            self._proto.sendHeader(k, v)
        self._proto.endHeaders()
        if body is not None:
            self._proto.transport.write(body)

        response = yield self._proto.response_cb

        self._proto.close()
        self._proto = None

        yield Return(response)


class _HttpServerResource(resource.Resource):
    isLeaf = 1

    def __init__(self, handler):
        self.handler = handler

    def render(self, request):
        @_o
        def _handler(request):
            try:
                code, headers, content = yield launch(self.handler, request)
            except:
                code, headers, content = 500, {}, "500 Internal Server Error"
            request.setResponseCode(code)
            headers.setdefault('Server', 'monocle/%s' % VERSION)
            for name, value in headers.iteritems():
                request.setHeader(name, value)
            request.write(content)
            request.finish()
        _handler(request)
        return server.NOT_DONE_YET


class HttpServer(object):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        self.factory = server.Site(_HttpServerResource(handler))
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog

