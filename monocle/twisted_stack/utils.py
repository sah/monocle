from twisted.python.failure import Failure
from twisted.internet.defer import Deferred

def cb_to_df(cb):
    df = Deferred()
    def call_deferred_back(v, df=df):
        if isinstance(v, Exception):
            df.errback(Failure(v, type(v), None))
        else:
            df.callback(v)
    cb.add(call_deferred_back)
    return df
