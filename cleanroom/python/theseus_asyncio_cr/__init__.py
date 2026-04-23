"""
theseus_asyncio_cr - Clean-room async event loop primitives.
Implements a minimal synchronous coroutine runner using generator-based coroutines.
No asyncio, concurrent, or threading imports.
"""


class _SleepSignal:
    """Signal yielded by sleep() to indicate suspension."""
    def __init__(self, delay):
        self.delay = delay


class _FutureWait:
    """Signal yielded to wait for a Future to complete."""
    def __init__(self, future):
        self.future = future


class Future:
    """A simple Future object that holds a result."""
    
    def __init__(self):
        self._result = None
        self._has_result = False
        self._callbacks = []
    
    def set_result(self, value):
        """Set the result of the future."""
        self._result = value
        self._has_result = True
        for cb in self._callbacks:
            cb(self)
        self._callbacks.clear()
    
    def result(self):
        """Get the result of the future. Raises if not yet set."""
        if not self._has_result:
            raise RuntimeError("Future result is not yet set")
        return self._result
    
    def done(self):
        """Return True if the future has a result."""
        return self._has_result
    
    def add_done_callback(self, cb):
        """Add a callback to be called when the future is done."""
        if self._has_result:
            cb(self)
        else:
            self._callbacks.append(cb)
    
    def __iter__(self):
        """Allow awaiting this future via yield from."""
        if not self._has_result:
            yield _FutureWait(self)
        return self._result


def sleep(delay):
    """
    Suspend the coroutine for `delay` steps.
    This is a generator function that yields a sleep signal.
    """
    if delay > 0:
        yield _SleepSignal(delay)


def _drive_coroutine(coro):
    """
    Drive a single coroutine (generator) to completion.
    Handles sleep signals and future waits.
    Returns the final result.
    """
    # Stack-based approach to handle nested generators (yield from)
    # We use a simple round-robin scheduler for sleep signals
    
    pending_sleep = 0
    result = None
    
    try:
        value_to_send = None
        while True:
            try:
                signal = coro.send(value_to_send)
                value_to_send = None
                
                if isinstance(signal, _SleepSignal):
                    # Just continue - in simulation we don't actually wait
                    pass
                elif isinstance(signal, _FutureWait):
                    # Drive until the future is done
                    fut = signal.future
                    if fut.done():
                        value_to_send = fut.result()
                    else:
                        # Future not done yet - just continue
                        # In a real scheduler we'd suspend, but here we just proceed
                        pass
                # else: unknown signal, ignore
                    
            except StopIteration as e:
                result = e.value
                break
    except Exception:
        raise
    
    return result


def run(coro):
    """
    Run a coroutine to completion, returning the result.
    Accepts both generator objects and generator functions called with no args.
    """
    # If it's a generator function, call it
    import types
    if isinstance(coro, types.GeneratorType):
        gen = coro
    elif callable(coro):
        gen = coro()
    else:
        raise TypeError(f"Expected a generator or coroutine, got {type(coro)}")
    
    return _drive_coroutine(gen)


def gather(*coros):
    """
    Run multiple coroutines concurrently (interleaved), returning a list of results.
    Uses a simple round-robin scheduler.
    """
    import types
    
    # Convert all to generators
    generators = []
    for coro in coros:
        if isinstance(coro, types.GeneratorType):
            generators.append(coro)
        elif callable(coro):
            generators.append(coro())
        else:
            raise TypeError(f"Expected a generator or coroutine, got {type(coro)}")
    
    n = len(generators)
    results = [None] * n
    done = [False] * n
    send_values = [None] * n
    
    # Round-robin until all are done
    max_iterations = 10000  # Safety limit
    iteration = 0
    
    while not all(done) and iteration < max_iterations:
        iteration += 1
        progress = False
        
        for i, gen in enumerate(generators):
            if done[i]:
                continue
            
            try:
                signal = gen.send(send_values[i])
                send_values[i] = None
                progress = True
                
                if isinstance(signal, _SleepSignal):
                    # Just continue next round
                    pass
                elif isinstance(signal, _FutureWait):
                    fut = signal.future
                    if fut.done():
                        send_values[i] = fut.result()
                # else: unknown signal, ignore
                    
            except StopIteration as e:
                results[i] = e.value
                done[i] = True
                progress = True
        
        if not progress:
            break
    
    return results


# ─── Test / demo coroutines ───────────────────────────────────────────────────

def _simple_coro():
    """A simple coroutine that returns 42."""
    yield  # at least one yield to make it a generator
    return 42


def _coro_returning(value):
    """A coroutine that returns a given value."""
    yield
    return value


def asyncio_run_simple():
    """
    Demonstrates run(simple_coro()) returns 42.
    Returns 42.
    """
    def simple_coro():
        yield
        return 42
    
    return run(simple_coro())


def asyncio_future_result():
    """
    Demonstrates Future.set_result(99); result() == 99.
    Returns 99.
    """
    fut = Future()
    fut.set_result(99)
    return fut.result()


def asyncio_gather_two():
    """
    Demonstrates gather returns results from both coros.
    Returns [1, 2].
    """
    def coro_one():
        yield
        return 1
    
    def coro_two():
        yield
        return 2
    
    return gather(coro_one(), coro_two())


# ─── Public API ──────────────────────────────────────────────────────────────

__all__ = [
    "run",
    "gather",
    "sleep",
    "Future",
    "asyncio_run_simple",
    "asyncio_future_result",
    "asyncio_gather_two",
]