from monocle.stack.eventloop import queue_task
from monocle.deferred import Deferred

def sleep(seconds):
    d = Deferred()
    queue_task(seconds, d.callback, None)
    return d
