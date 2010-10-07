# Sort of like Twisted's Deferred, but simplified.  We don't do
# callback chaining, since oroutines replace that mechanism.
class Callback(object):
    def __init__(self):
        self._handlers = []

    def register(self, handler):
        if hasattr(self, 'result'):
            handler(self.result)
        else:
            self._handlers.append(handler)

    def trigger(self, result):
        assert not hasattr(self, 'result'), "Already triggered"
        for handler in self._handlers:
            handler(result)
        self.result = result


def defer(result):
    cb = Callback()
    cb.result = result
    return cb
