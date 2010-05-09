import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.experimental import Channel

@_o
def main():
    s = 2
    ch = Channel(s)
    for i in xrange(s):
        print i
        yield ch.fire(i)

    print ch.bufsize, len(ch._msgs)
    for i in xrange(s):
        print (yield ch.wait())
    print "done"

monocle.launch(main())
eventloop.run()
