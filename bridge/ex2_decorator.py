import time
from functools import wraps

def timed(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        ms = (time.perf_counter() - start) * 1000
        print(f"{fn.__name__} took {ms:.2f} ms")
        return result
    return wrapper

@timed
def slow_query():
    time.sleep(0.2)
    return "done"

print(slow_query())