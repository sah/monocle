# Sort of like Twisted's Deferred, but simplified.  We don't do
# callback chaining, since oroutines replace that mechanism.
class Callback(object):
    def __init__(self):
        self._handlers = []

    def add(self, handler):
        if hasattr(self, 'result'):
            handler(self.result)
        else:
            self._handlers.append(handler)

    def __call__(self, result):
        assert not hasattr(self, 'result'), "Already called back"
        for handler in self._handlers:
            handler(result)
        self.result = result


def defer(result):
    cb = Callback()
    cb.result = result
    return cb
