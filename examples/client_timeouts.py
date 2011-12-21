import sys
import monocle
from monocle import _o, Return
monocle.init(sys.argv[1])
from monocle.stack import eventloop
from monocle.stack.network import Client

@_o
def main():
    c = Client()
    yield c.connect('google.com', 80)
    c.close()
    yield c.connect('google.com', 80, timeout=0)

monocle.launch(main)
eventloop.run()
