# monocle - An async programming framework with a blocking look-alike syntax.
By Greg Hazel and Steven Hazel.

monocle straightens out event-driven code using Python's generators.
It aims to be portable between event-driven I/O frameworks, and
currently supports Twisted and Tornado.

It's for Python 2.5 and up; the syntax it uses isn't supported
in older versions of Python.

## A Simple Example

Here's a simple monocle program that runs two concurrent lightweight
processes (called "oroutines") using Tornado's event loop:

    import monocle
    monocle.init("tornado")
    from monocle.stack import eventloop
    from monocle.util import sleep

    @monocle.o
    def print_every_second():
        while True:
            print "1"
            yield sleep(1)

    @monocle.o
    def print_every_two_seconds():
        while True:
            print "2"
            yield sleep(2)
	    
    monocle.launch(print_every_second)
    monocle.launch(print_every_two_seconds)
    eventloop.run()

## Related Work
monocle is similar to, and takes inspiration from:
Twisted's inlineCallbacks
BTL's yielddefer
diesel
Go's goroutines
