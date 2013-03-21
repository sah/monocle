import new

from monocle.stack.eventloop import queue_task
from monocle.callback import Callback

def sleep(seconds):
    cb = Callback()
    queue_task(seconds, cb, None)
    return cb

def monkeypatch(cls):
    def decorator(f):
        orig_method = None
        method = getattr(cls, f.func_name, None)
        if method:
            orig_method = lambda *a, **k: method(*a, **k)
        def g(*a, **k):
            return f(orig_method, *a, **k)
        g.func_name = f.func_name
        setattr(cls, f.func_name,
                new.instancemethod(g, None, cls))
    return decorator
