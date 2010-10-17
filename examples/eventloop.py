import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.util import sleep

@_o
def foo(x, z=1):
    yield sleep(1)
    print x

def bar(x, z=1):
    print x

@_o
def fail():
    raise Exception("whoo")
    yield sleep(1)

eventloop.queue_task(0, foo, x="oroutine worked")
eventloop.queue_task(0, bar, x="function worked")
eventloop.queue_task(0, fail)
eventloop.run()
