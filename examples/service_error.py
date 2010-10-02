import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service, Service

@_o
def lower_one(conn):
    raise Exception("testing")
    yield

@_o
def top_one(conn):
    yield lower_one(conn)

add_service(Service(top_one, 12345))
eventloop.run()
