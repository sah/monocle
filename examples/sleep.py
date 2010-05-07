import sys

import monocle
monocle.init(sys.argv[1])
from monocle import _o

from monocle.stack import eventloop
from monocle.util import sleep

@_o
def print_every_second():
    for i in xrange(5):
        print "1"
        yield sleep(1.0)

@_o
def print_every_two_seconds():
    for i in xrange(5):
        print "2"
        yield sleep(2.0)
    eventloop.halt()

print_every_second()
print_every_two_seconds()
eventloop.run()
