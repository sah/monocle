# -*- coding: utf-8 -*-
#
# by Steven Hazel

import urlparse
import logging

from monocle import _o, Return, VERSION, launch
from monocle.callback import Callback
from monocle.stack.network.http import HttpHeaders, HttpResponse, write_request, read_response
from monocle.twisted_stack.eventloop import reactor
from monocle.twisted_stack.network import Service, Client, SSLClient

from twisted.internet import ssl
from twisted.internet.protocol import ClientCreator
from twisted.web import server, resource

log = logging.getLogger("monocle.twisted_stack.network.http")

class HttpException(Exception): pass


class _HttpServerResource(resource.Resource):
    isLeaf = 1

    def __init__(self, handler):
        self.handler = handler

    def render(self, request):
        @_o
        def _handler(request):
            try:
                code, headers, content = yield launch(self.handler, request)
            except Exception, e:
                print type(e), str(e)
                log.log_exception()
                code, headers, content = 500, {}, "500 Internal Server Error"
            try:
                request.setResponseCode(code)
                headers.setdefault('Server', 'monocle/%s' % VERSION)
                for name, value in headers.iteritems():
                    print name, value
                    request.setHeader(name, value)
                request.write(content)
                request.finish()
            except Exception, e:
                print type(e), str(e)
        _handler(request)
        return server.NOT_DONE_YET


class HttpServer(Service):
    def __init__(self, handler, port, bindaddr="", backlog=128):
        self.factory = server.Site(_HttpServerResource(handler))
        self.port = port
        self.bindaddr = bindaddr
        self.backlog = backlog
        self.ssl_options = None
        self._twisted_listening_port = None

