# -*- coding: utf-8 -*-
#
# by Steven Hazel

import tornado.httpclient
import tornado.httpserver

from httplib import responses
from monocle import _o, Return, VERSION, launch
from monocle.callback import Callback
from monocle.stack.network.http import HttpHeaders, HttpClient, extract_response


class HttpException(Exception): pass


class HttpClient(HttpClient):
    @classmethod
    @_o
    def query(self, url, headers=None, method='GET', body=None):
        _http_client = tornado.httpclient.AsyncHTTPClient()
        req = tornado.httpclient.HTTPRequest(url,
                                             method=method,
                                             headers=headers or {},
                                             body=body,
                                             # XXX: TODO
                                             #request_timeout=self.timeout
                                             )
        cb = Callback()
        _http_client.fetch(req, cb)
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
                value = yield launch(self.handler, request)
                code, headers, content = extract_response(value)
            except:
                code, headers, content = 500, {}, "500 Internal Server Error"
            request.write("HTTP/1.1 %s %s\r\n" %
                          (code, responses.get(code, 'Unknown')))
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
