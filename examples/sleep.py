import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.util import sleep

@_o
def print_every_second():
    for i in xrange(5):
        print "1"
        yield sleep(1)

@_o
def print_every_two_seconds():
    for i in xrange(5):
        print "2"
        yield sleep(2)
    eventloop.halt()

monocle.launch(print_every_second())
monocle.launch(print_every_two_seconds())
eventloop.run()
