from monocle.stack.eventloop import queue_task
from monocle.callback import Callback

def sleep(seconds):
    cb = Callback()
    queue_task(seconds, cb, None)
    return cb
