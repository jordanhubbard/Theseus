"""Clean-room implementation of a pure-Python profiler.

Provides a Profile class similar in spirit to the standard library's
profile module, plus a few helper functions used by the invariant
checks. No third-party imports; only Python standard library built-ins.
"""

import sys
import time


# ---------------------------------------------------------------------------
# Profile class
# ---------------------------------------------------------------------------

class Profile(object):
    """A simple deterministic, pure-Python profiler.

    Tracks call counts and cumulative/own time per (filename, lineno, name)
    function key by hooking sys.setprofile.
    """

    def __init__(self, timer=None, bias=0):
        self.timer = timer if timer is not None else time.perf_counter
        self.bias = bias
        # key -> [calls, total_time, cumulative_time]
        self.stats = {}
        # Stack of (key, call_start_time, child_total)
        self._stack = []
        self._enabled = False

    # -- core hook -------------------------------------------------------
    def _dispatcher(self, frame, event, arg):
        # We only care about call/return events for Python and C code.
        if event == "call" or event == "c_call":
            self._on_call(frame, event, arg)
        elif event == "return" or event == "c_return" or event == "c_exception":
            self._on_return(frame, event, arg)
        return None

    def _frame_key(self, frame, event, arg):
        if event == "c_call" or event == "c_return" or event == "c_exception":
            # arg is the C function being called
            try:
                name = arg.__name__
            except AttributeError:
                name = repr(arg)
            return ("<builtin>", 0, name)
        code = frame.f_code
        return (code.co_filename, code.co_firstlineno, code.co_name)

    def _on_call(self, frame, event, arg):
        key = self._frame_key(frame, event, arg)
        now = self.timer()
        self._stack.append([key, now, 0.0])

    def _on_return(self, frame, event, arg):
        if not self._stack:
            return
        key, start, child_total = self._stack.pop()
        now = self.timer()
        elapsed = now - start - self.bias
        if elapsed < 0:
            elapsed = 0.0
        own = elapsed - child_total
        if own < 0:
            own = 0.0
        rec = self.stats.get(key)
        if rec is None:
            self.stats[key] = [1, own, elapsed]
        else:
            rec[0] += 1
            rec[1] += own
            rec[2] += elapsed
        if self._stack:
            self._stack[-1][2] += elapsed

    # -- public API ------------------------------------------------------
    def enable(self):
        if not self._enabled:
            sys.setprofile(self._dispatcher)
            self._enabled = True

    def disable(self):
        if self._enabled:
            sys.setprofile(None)
            self._enabled = False

    def clear(self):
        self.stats = {}
        self._stack = []

    def run(self, cmd, globals=None, locals=None):
        """Profile execution of a string of Python code."""
        if globals is None:
            globals = {}
        if locals is None:
            locals = globals
        code_obj = compile(cmd, "<profile-run>", "exec")
        self.enable()
        try:
            exec(code_obj, globals, locals)
        finally:
            self.disable()
        return self

    def runctx(self, cmd, globals, locals):
        return self.run(cmd, globals, locals)

    def runcall(self, func, *args, **kwargs):
        """Profile a single function call and return its result."""
        self.enable()
        try:
            return func(*args, **kwargs)
        finally:
            self.disable()

    # -- reporting -------------------------------------------------------
    def get_stats(self):
        """Return a snapshot of accumulated stats as a plain dict."""
        out = {}
        for key, rec in self.stats.items():
            out[key] = (rec[0], rec[1], rec[2])
        return out

    def print_stats(self, stream=None):
        if stream is None:
            stream = sys.stdout
        rows = sorted(
            self.stats.items(),
            key=lambda kv: kv[1][2],
            reverse=True,
        )
        stream.write("ncalls  tottime  cumtime  filename:lineno(function)\n")
        for (filename, lineno, name), (ncalls, tot, cum) in rows:
            stream.write(
                "%6d  %7.6f  %7.6f  %s:%d(%s)\n"
                % (ncalls, tot, cum, filename, lineno, name)
            )

    def create_stats(self):
        # Compatibility hook; nothing to materialise beyond what we track.
        return self.get_stats()


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

def run(cmd, filename=None):
    """Run ``cmd`` under a fresh Profile and return the Profile instance."""
    p = Profile()
    p.run(cmd)
    return p


def runctx(cmd, globals, locals, filename=None):
    p = Profile()
    p.runctx(cmd, globals, locals)
    return p


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def profile2_run():
    """Profile.run executes code and accumulates at least one stat entry."""
    p = Profile()

    def _work():
        total = 0
        for i in range(50):
            total += i * i
        return total

    p.run("_work()", {"_work": _work}, {})
    stats = p.get_stats()
    if not isinstance(stats, dict):
        return False
    if len(stats) == 0:
        return False
    # Every record must be (ncalls, tottime, cumtime) with ncalls >= 1.
    for key, rec in stats.items():
        if not isinstance(key, tuple) or len(key) != 3:
            return False
        if len(rec) != 3:
            return False
        ncalls, tot, cum = rec
        if ncalls < 1:
            return False
        if tot < 0 or cum < 0:
            return False
    return True


def profile2_runcall():
    """Profile.runcall returns the function result and records the call."""
    p = Profile()

    def add(a, b):
        s = 0
        for _ in range(10):
            s += a + b
        return a + b

    result = p.runcall(add, 3, 4)
    if result != 7:
        return False
    stats = p.get_stats()
    if not stats:
        return False
    # Confirm the called function appears in the stats keyed by name.
    found = False
    for (fname, lineno, name) in stats.keys():
        if name == "add":
            found = True
            break
    return found


def profile2_stats():
    """Stats accumulate across multiple runs and survive clear()."""
    p = Profile()

    def f():
        return sum(range(20))

    def g():
        return f() + 1

    p.runcall(f)
    p.runcall(g)

    stats = p.get_stats()
    if not stats:
        return False

    names = {key[2] for key in stats.keys()}
    if "f" not in names or "g" not in names:
        return False

    # Total ncalls for f should be at least 2 (called directly and via g).
    f_calls = 0
    for (filename, lineno, name), (ncalls, tot, cum) in stats.items():
        if name == "f":
            f_calls += ncalls
    if f_calls < 2:
        return False

    # clear() should empty the stats.
    p.clear()
    if p.get_stats():
        return False

    return True


__all__ = [
    "Profile",
    "run",
    "runctx",
    "profile2_run",
    "profile2_runcall",
    "profile2_stats",
]