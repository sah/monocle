# -*- coding: utf-8 -*-
#
# by Steven Hazel

import urlparse
import ordereddict

import tornado.httpclient
import tornado.httpserver

from monocle import _o, VERSION
from monocle.deferred import Deferred


class HttpException(Exception): pass

HttpHeaders = ordereddict.OrderedDict

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
        df = Deferred()
        http_client.fetch(req, df.callback)
        response = yield df
        yield response


class HttpServer(object):
    def __init__(self, handler, port):
        self.handler = handler
        self.port = port

    def _add(self, el):
        self._http_server = tornado.httpserver.HTTPServer(
            self.handler,
            io_loop=el._tornado_ioloop)
        self._http_server.listen(self.port)


@_o
def http_respond(request, code, headers, content):
    request.write("HTTP/1.1 %s\r\n" % code)
    for name, value in headers.iteritems():
        request.write("%s: %s\r\n" % (name, value))
    request.write("\r\n")
    request.write(content)
    request.finish()

