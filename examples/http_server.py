import sys

import monocle
from monocle import _o, Return
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service
from monocle.stack.network.http import HttpHeaders, HttpServer


@_o
def hello_http(req):
    content = "Hello, World!"
    headers = HttpHeaders()
    headers.add('Content-Length', len(content))
    headers.add('Content-Type', 'text/plain')
    headers.add('Connection', 'close')
    headers.add('Set-Cookie', 'test0=blar; Path=/')
    headers.add('Set-Cookie', 'test1=blar; Path=/')
    yield Return(200, headers, content)

add_service(HttpServer(hello_http, 8088))
eventloop.run()
