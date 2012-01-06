import sys

import monocle
monocle.init(sys.argv[1])
from monocle import _o, launch
from monocle.util import sleep
from monocle.stack import eventloop
from monocle.stack.network.http import HttpClient

@_o
def req():
    client = HttpClient()
    yield client.connect("localhost", 12344, timeout=1)

def die():
  raise Exception("boom")

@_o
def fifth():
  die()

def fourth():
  return fifth()

@_o
def third():
  yield fourth()

def second():
  return third()

@_o
def first():
  yield second()

@_o
def first_evlp():
  try:
    yield sleep(1)
    yield req()
    yield launch(second)
  finally:
    eventloop.halt()

launch(first)
eventloop.queue_task(0, first_evlp)
eventloop.run()


