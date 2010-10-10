import monocle
from monocle import Return, InvalidYieldException

@monocle.o
def square(x):
    yield Return(x*x)
    print "not reached"

@monocle.o
def fail():
    raise Exception("boo")
    print (yield square(2))

@monocle.o
def invalid_yield():
    yield "this should fail"

@monocle.o
def main():
    value = yield square(5)
    print value
    try:
        yield fail()
    except Exception, e:
        print "Caught exception:", type(e), str(e)

    try:
        yield invalid_yield()
    except InvalidYieldException, e:
        print "Caught exception:", type(e), str(e)
    else:
        assert False

monocle.launch(main)
