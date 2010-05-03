# Like Twisted's Deferred, but simplified
class Deferred(object):
    def __init__(self):
        self._callbacks = []

    def add_callback(self, callback):
        if hasattr(self, 'result'):
            callback(self.result)
        else:
            self._callbacks.append(callback)

    def callback(self, result):
        for cb in self._callbacks:
            cb(result)
        self.result = result

def defer(result):
    d = Deferred()
    d.result = result
    return d
