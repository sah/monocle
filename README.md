# monocle - An async programming framework with a blocking look-alike syntax.
By Greg Hazel and Steven Hazel.

monocle straightens out event-driven code using Python's generators.
It aims to be portable between event-driven I/O frameworks, and
currently supports Twisted and Tornado.

It's for Python 2.5 and up; the syntax it uses isn't supported
in older versions of Python.

## A Simple Example

Here's a simple monocle program that runs two concurrent lightweight
processes (called "o-routines") using Tornado's event loop:

    import monocle
    monocle.init("tornado")
    from monocle.stack import eventloop
    from monocle.util import sleep

    @monocle.o
    def seconds():
        while True:
            yield sleep(1)
            print "1"

    @monocle.o
    def minutes():
        while True:
            yield sleep(60)
            print "60"
	    
    monocle.launch(seconds)
    monocle.launch(minutes)
    eventloop.run()

## @_o

It's important that code be dapper and well-dressed, so if you prefer,
you can don the monocle and use this handy shortcut for monocle.o:

    from monocle import _o

    @_o
    def seconds():
        while True:
            yield sleep(1)
            print "1"

It's true, this violates Python's convention that underscores indicate
variables for internal use.  But rules are for breaking.  Live a
little.

## Related Work
monocle is similar to, and takes inspiration from:

 * Twisted's inlineCallbacks
 * BTL's yielddefer
 * diesel
 * Go's goroutines
