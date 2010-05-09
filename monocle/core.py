# This code is based heavily on inlineCallbacks from Twisted 10.0, see LICENSE.

import sys
import types
import traceback

from deferred import Deferred, defer

from twisted_utils import mergeFunctionMetadata

try:
    from twisted.python.failure import Failure as TwistedFailure
    from twisted.internet.defer import Deferred as TwistedDeferred
except ImportError:
    class TwistedFailure: pass
    class TwistedDeferred: pass


def launch(df):
    def eb(e):
        if isinstance(e, Exception):
            import traceback
            import sys
            traceback.print_exception(type(e), e, sys.exc_info()[2])
    df.add_callback(eb)


def format_tb(e):
    s = ""
    for tb in reversed(e._monocle['tracebacks']):
        lines = tb.split('\n')
        first = lines[0]
        last = lines[-2]
        s += "\n" + '\n'.join(lines[1:-2])
    return first + s + "\n" + last


def _monocle_chain(to_gen, g, deferred):
    # This function is complicated by the need to prevent unbounded recursion
    # arising from repeatedly yielding immediately ready deferreds.  This while
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
            from_gen = None
        except Exception, e:
            tb = traceback.format_exc()
            if not hasattr(e, "_monocle"):
                e._monocle = {'tracebacks': []}
            e._monocle['tracebacks'].append(tb)
            deferred.callback(e)
            return deferred

        if not isinstance(from_gen,
                          (Deferred, TwistedDeferred)):
            deferred.callback(from_gen)
            return deferred

        state = {'waiting': True}

        # a deferred was yielded, get the result.
        def gotResult(r):
            if state['waiting']:
                state['waiting'] = False
                state['result'] = r
            else:
                _monocle_chain(r, g, deferred)
        if isinstance(from_gen, TwistedDeferred):
            from_gen.addBoth(gotResult)
        else:
            from_gen.add_callback(gotResult)

        if state['waiting']:
            # Haven't called back yet, set flag so that we get reinvoked
            # and return from the loop
            state['waiting'] = False
            return deferred

        to_gen = state['result']


def maybeDeferredGenerator(f, *args, **kw):
    try:
        result = f(*args, **kw)
    except Exception, e:
        tb = traceback.format_exc()
        if not hasattr(e, "_monocle"):
            e._monocle = {'tracebacks': []}
        e._monocle['tracebacks'].append(tb)
        return defer(e)

    if isinstance(result, types.GeneratorType):
        return _monocle_chain(None, result, Deferred())
    elif isinstance(result, Deferred):
        return result
    elif isinstance(result, TwistedDeferred):
        return result  # FIXME -- convert
    return defer(result)


# @_o
def _o(f):
    """
    monocle helps you write Deferred-using code that looks like a regular
    sequential function.  For example::

        @_o
        def foo():
            result = yield makeSomeRequestResultingInDeferred()
            print result

    When you call anything that results in a Deferred, you can simply yield it;
    your generator will automatically be resumed when the Deferred's result is
    available. The generator will be sent the result of the Deferred with the
    'send' method on generators, or if the result was a failure, 'throw'.

    Your coroutine-enabled generator will return a Deferred object, which
    will result in the return value of the generator (or will fail with a
    failure object if your generator raises an unhandled exception). Note that
    you can't use "return result" to return a value; use "yield result"
    instead. Falling off the end of the generator, or simply using "return"
    will cause the Deferred to have a result of None.

    The Deferred returned from your generator will call back with an
    exception if your generator raised an exception::

        @_o
        def foo():
            result = yield makeSomeRequestResultingInDeferred()
            if result == 'foo':
                # this will become the result of the Deferred
                yield 'success'
            else:
                # this too
                raise Exception('fail')
    """
    def unwindGenerator(*args, **kwargs):
        return maybeDeferredGenerator(f, *args, **kwargs)
    return mergeFunctionMetadata(f, unwindGenerator)

o = _o
