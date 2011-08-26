import collections

class HttpHeaders(collections.MutableMapping):
    def __init__(self, headers=None):
        self.headers = []
        self.keys = set()
        if hasattr(headers, 'iteritems'):
            for k, v in headers.iteritems():
                self.add(k, v)
        else:
            for k, v in headers or []:
                self.add(k, v)
        
    def __len__(self):
        return len(self.headers)
                
    def keys(self):
        return [k for k, v in self.headers]
        
    def add(self, key, value):
        key = key.lower()
        self.keys.add(key)
        self.headers.append((key, value))
        
    def items(self):
        return self.headers
        
    def __iter__(self):
        return (k for k, v in self.headers)
        
    def iteritems(self):
        return (x for x in self.headers)
        
    def __repr__(self):
        return repr(self.headers)
        
    def __getitem__(self, key):
        key = key.lower()
        if not key in self.keys:
            raise KeyError(key)
        vals = [v for k, v in self.headers if k==key]
        if len(vals) == 1:
            return vals[0]
        else:
            return vals
        
    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        return self.add(key, value)
        
    def __delitem__(self, key):
        key = key.lower()
        if not key in self.keys:
            raise KeyError(key)
        self.keys.remove(key)
        self.headers = [(k, v) for k, v in self.headers if k != key]


import monocle
if monocle._stack_name == 'twisted':
    from monocle.twisted_stack.network.http import *
elif monocle._stack_name == 'tornado':
    from monocle.tornado_stack.network.http import *
