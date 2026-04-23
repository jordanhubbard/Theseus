# theseus_concurrent_cr: Clean-room concurrent.futures-like executor
# No imports of concurrent, threading, or multiprocessing allowed.


class Future:
    """A result holder that stores the outcome of a callable invocation."""

    def __init__(self):
        self._result = None
        self._exception = None
        self._done = False

    def set_result(self, result):
        self._result = result
        self._done = True

    def set_exception(self, exception):
        self._exception = exception
        self._done = True

    def result(self):
        if self._exception is not None:
            raise self._exception
        return self._result

    def done(self):
        return self._done


class SynchronousExecutor:
    """Executes callables synchronously (no threads or processes)."""

    def submit(self, fn, *args, **kwargs):
        """Wrap fn(*args, **kwargs) in a Future and execute immediately."""
        future = Future()
        try:
            result = fn(*args, **kwargs)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        return future

    def map(self, fn, iterable):
        """Apply fn to each item in iterable, returning results in order."""
        results = []
        for item in iterable:
            future = self.submit(fn, item)
            results.append(future.result())
        return iter(results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


# Alias for compatibility
Executor = SynchronousExecutor


# --- Invariant functions ---

def concurrent_future_result():
    """submit(lambda: 42).result() == 42"""
    executor = SynchronousExecutor()
    future = executor.submit(lambda: 42)
    return future.result()


def concurrent_map_results():
    """list(map(str, [1, 2, 3])) == ['1', '2', '3']"""
    executor = SynchronousExecutor()
    return list(executor.map(str, [1, 2, 3]))


def concurrent_future_done():
    """submitted future.done() == True after completion"""
    executor = SynchronousExecutor()
    future = executor.submit(lambda: None)
    return future.done()