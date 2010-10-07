from monocle.stack.eventloop import queue_task
from monocle.callback import Callback

def sleep(seconds):
    d = Callback()
    queue_task(seconds, d.trigger, None)
    return d
