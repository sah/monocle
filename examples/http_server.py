import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service
from monocle.stack.network.http import HttpHeaders, HttpServer, http_respond

@_o
def hello_http(req):
    content = "Hello, World!"
    headers = HttpHeaders()
    headers['Content-Length'] = len(content)
    headers['Content-Type'] = 'text/plain'
    yield http_respond(req, 200, headers, content)

add_service(HttpServer(hello_http, 8088))
eventloop.run()
