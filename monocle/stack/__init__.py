import monocle
if monocle._stack_name == 'twisted':
    from monocle.twisted_stack import *
elif monocle._stack_name == 'tornado':
    from monocle.tornado_stack import *

