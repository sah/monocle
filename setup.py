# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from monocle import VERSION

setup(name="monocle",
      version=VERSION,
      description="An async programming framework with a blocking look-alike syntax",
      author="Greg Hazel and Steven Hazel",
      author_email="sah@awesame.org",
      maintainer="Steven Hazel",
      maintainer_email="sah@awesame.org",
      url="http://github.com/saucelabs/monocle",
      packages=['monocle',
                'monocle.stack',
                'monocle.stack.network',
                'monocle.twisted_stack',
                'monocle.twisted_stack.network',
                'monocle.tornado_stack',
                'monocle.tornado_stack.network',
                'monocle.asyncore_stack',
                'monocle.asyncore_stack.network'],
      license='MIT'
      )
