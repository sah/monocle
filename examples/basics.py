import monocle

@monocle.o
def square(x):
    yield x*x
    print "not reached"

@monocle.o
def fail():
    raise Exception("boo")
    print (yield square(2))

@monocle.o
def main():
    value = yield square(5)
    print value
    try:
        yield fail()
    except Exception, e:
        print "Caught exception:", type(e), str(e)

main()
