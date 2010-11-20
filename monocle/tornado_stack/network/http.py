# -*- coding: utf-8 -*-
#
# by Steven Hazel

import urlparse

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import tornado.httpclient
import tornado.httpserver

from monocle import _o, Return, VERSION, launch
from monocle.callback import Callback


class HttpException(Exception): pass

HttpHeaders = OrderedDict

class HttpClient(object):
    def __init__(self):
        self._proto = None

    @_o
    def request(self, url, headers=None, method='GET', body=None):
        http_client = tornado.httpclient.AsyncHTTPClient()
        req = tornado.httpclient.HTTPRequest(url,
                                             method=method,
                                             headers=headers or {},
                                             body=body)
        cb = Callback()
        http_client.fetch(req, cb)
        response = yield cb
        yield Return(response)


class HttpServer(object):
    def __init__(self, handler, port):
        self.handler = handler
        self.port = port

    def _add(self, el):
        @_o
        def _handler(request):
            try:
                code, headers, content = yield launch(self.handler, request)
            except:
                code, headers, content = 500, {}, "500 Internal Server Error"
            request.write("HTTP/1.1 %s\r\n" % code)
            headers.setdefault('Server', 'monocle/%s' % VERSION)
            headers.setdefault('Content-Length', str(len(content)))
            for name, value in headers.iteritems():
                request.write("%s: %s\r\n" % (name, value))
            request.write("\r\n")
            request.write(content)
            request.finish()
        self._http_server = tornado.httpserver.HTTPServer(
            _handler,
            io_loop=el._tornado_ioloop)
        self._http_server.listen(self.port)

