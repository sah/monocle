# This code is based heavily on inlineCallbacks from Twisted 10.0, see LICENSE.

import sys
import types
import traceback

from callback import Callback, defer

from twisted_utils import mergeFunctionMetadata

try:
    from twisted.python.failure import Failure as TwistedFailure
    from twisted.internet.defer import Deferred as TwistedDeferred
except ImportError:
    class TwistedFailure: pass
    class TwistedDeferred: pass


class Return(object):
    def __init__(self, value=None):
        self.value = value


class InvalidYieldException(Exception):
    pass


def launch(cb):
    cb2 = Callback()
    def eb(e):
        if isinstance(e, Exception):
            if hasattr(e, '_monocle'):
                print format_tb(e)
            else:
                import traceback
                import sys
                traceback.print_exception(type(e), e, sys.exc_info()[2])
        cb2(e)
    cb.register(eb)
    return cb2


def format_tb(e):
    s = ""
    for tb in reversed(e._monocle['tracebacks']):
        lines = tb.split('\n')
        first = lines[0]
        last = lines[-2]
        s += "\n" + '\n'.join(lines[1:-2])
    return first + s + "\n" + last


def _monocle_chain(to_gen, g, callback):
    # This function is complicated by the need to prevent unbounded recursion
    # arising from repeatedly yielding immediately ready callbacks.  This while
    # loop and the state variable solve that by manually unfolding the
    # recursion.

    while True:
        try:
            # Send the last result back as the result of the yield expression.
            if isinstance(to_gen, Exception):
                from_gen = g.throw(type(to_gen), to_gen)
            elif isinstance(to_gen, TwistedFailure):
                from_gen = to_gen.throwExceptionIntoGenerator(g)
            else:
                from_gen = g.send(to_gen)
        except StopIteration:
            # "return" statement (or fell off the end of the generator)
            from_gen = Return()
        except Exception, e:
            tb = traceback.format_exc()
            if not hasattr(e, "_monocle"):
                e._monocle = {'tracebacks': []}
            e._monocle['tracebacks'].append(tb)
            callback(e)
            return callback

        if isinstance(from_gen, Return):
            callback(from_gen.value)
            return callback
        elif not isinstance(from_gen,
                            (Callback, TwistedDeferred)):
            e = InvalidYieldException("Unexpected value '%s' of type '%s' yielded from o-routine '%s'.  O-routines can only yield Callback and Return types." % (from_gen, type(from_gen), g))
            return _monocle_chain(e, g, callback)

        state = {'waiting': True}

        # a callback was yielded, get the result.
        def gotResult(r):
            if state['waiting']:
                state['waiting'] = False
                state['result'] = r
            else:
                _monocle_chain(r, g, callback)
        if isinstance(from_gen, TwistedDeferred):
            from_gen.addBoth(gotResult)
        else:
            from_gen.register(gotResult)

        if state['waiting']:
            # Haven't called back yet, set flag so that we get reinvoked
            # and return from the loop
            state['waiting'] = False
            return callback

        to_gen = state['result']


def maybeCallbackGenerator(f, *args, **kw):
    try:
        result = f(*args, **kw)
    except Exception, e:
        tb = traceback.format_exc()
        if not hasattr(e, "_monocle"):
            e._monocle = {'tracebacks': []}
        e._monocle['tracebacks'].append(tb)
        return defer(e)

    if isinstance(result, types.GeneratorType):
        return _monocle_chain(None, result, Callback())
    elif isinstance(result, Callback):
        return result
    elif isinstance(result, TwistedDeferred):
        return result  # FIXME -- convert
    return defer(result)


# @_o
def _o(f):
    """
    monocle helps you write Callback-using code that looks like a regular
    sequential function.  For example::

        @_o
        def foo():
            result = yield makeSomeRequestResultingInCallback()
            print result

    When you call anything that results in a Callback, you can simply yield it;
    your generator will automatically be resumed when the Callback's result is
    available. The generator will be sent the result of the Callback with the
    'send' method on generators, or if the result was a failure, 'throw'.

    Your coroutine-enabled generator will return a Callback object,
    which will result in the return value of the generator (or will
    fail with a failure object if your generator raises an unhandled
    exception). Note that you can't use "return result" to return a
    value; use "yield Return(result)" instead. Falling off the end of
    the generator, or simply using "return" will cause the Callback to
    have a result of None.  Yielding anything other and a Callback or
    a Return is not allowed, and will raise an exception.

    The Callback returned from your generator will call back with an
    exception if your generator raised an exception::

        @_o
        def foo():
            result = yield makeSomeRequestResultingInCallback()
            if result == 'foo':
                # this will become the result of the Callback
                yield Return('success')
            else:
                # this too
                raise Exception('fail')
    """
    def unwindGenerator(*args, **kwargs):
        return maybeCallbackGenerator(f, *args, **kwargs)
    return mergeFunctionMetadata(f, unwindGenerator)

o = _o
