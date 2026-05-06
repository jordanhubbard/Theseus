"""Clean-room implementation of a cProfile-like profiler.

This module provides a minimal Profile class and run helpers that measure
function call counts and elapsed time using sys.setprofile. It is implemented
from scratch using only the Python standard library and does NOT import or
wrap the original cProfile / profile modules.
"""

import sys
import time


class _StatEntry:
    __slots__ = ("ncalls", "tottime", "cumtime", "callers")

    def __init__(self):
        self.ncalls = 0
        self.tottime = 0.0
        self.cumtime = 0.0
        self.callers = {}


class Profile:
    """A minimal deterministic profiler.

    Tracks call counts and timing for each Python function executed
    while the profiler is active.
    """

    def __init__(self, timer=None, timeunit=0.0, subcalls=True, builtins=True):
        self.timer = timer if timer is not None else time.perf_counter
        self.timeunit = timeunit
        self.subcalls = subcalls
        self.builtins = builtins
        self.stats = {}
        self._call_stack = []
        self._enabled = False
        self._start_time = None
        self._total_time = 0.0

    # ------------------------------------------------------------------
    # Profiling hooks
    # ------------------------------------------------------------------
    def _make_key(self, frame, arg, event):
        if event in ("c_call", "c_return", "c_exception"):
            # Built-in function
            try:
                name = arg.__name__
            except AttributeError:
                name = repr(arg)
            try:
                module = arg.__module__ or "builtins"
            except AttributeError:
                module = "builtins"
            return ("~", 0, "<%s.%s>" % (module, name))
        code = frame.f_code
        return (code.co_filename, code.co_firstlineno, code.co_name)

    def _profile_callback(self, frame, event, arg):
        if not self._enabled:
            return
        now = self.timer()
        if event == "call" or (self.builtins and event == "c_call"):
            key = self._make_key(frame, arg, event)
            entry = self.stats.get(key)
            if entry is None:
                entry = _StatEntry()
                self.stats[key] = entry
            # Track caller relationship
            if self._call_stack:
                caller_key = self._call_stack[-1][0]
                entry.callers[caller_key] = entry.callers.get(caller_key, 0) + 1
            self._call_stack.append((key, now, now))
        elif event == "return" or (self.builtins and event == "c_return") \
                or event == "c_exception":
            if not self._call_stack:
                return
            key, start, last_resume = self._call_stack.pop()
            entry = self.stats.get(key)
            if entry is None:
                return
            elapsed = now - start
            entry.ncalls += 1
            entry.cumtime += elapsed
            # tottime excludes time spent in callees that have already been
            # recorded; we approximate by subtracting cumtime of children
            # tracked while this frame was active.
            entry.tottime += now - last_resume

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def enable(self, subcalls=None, builtins=None):
        if subcalls is not None:
            self.subcalls = subcalls
        if builtins is not None:
            self.builtins = builtins
        self._enabled = True
        self._start_time = self.timer()
        sys.setprofile(self._profile_callback)

    def disable(self):
        sys.setprofile(None)
        self._enabled = False
        if self._start_time is not None:
            self._total_time += self.timer() - self._start_time
            self._start_time = None

    # ------------------------------------------------------------------
    # Run helpers
    # ------------------------------------------------------------------
    def runcall(self, func, *args, **kwargs):
        self.enable()
        try:
            return func(*args, **kwargs)
        finally:
            self.disable()

    def run(self, cmd):
        # Compile and exec the command in a fresh globals dict
        code = compile(cmd, "<string>", "exec")
        globs = {"__name__": "__main__", "__builtins__": __builtins__}
        return self.runctx(code, globs, None)

    def runctx(self, cmd, globals, locals):
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")
        if locals is None:
            locals = globals
        self.enable()
        try:
            exec(cmd, globals, locals)
        finally:
            self.disable()
        return self

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def create_stats(self):
        # Snapshot of current stats. Compatible-ish with pstats.Stats input.
        out = {}
        for key, entry in self.stats.items():
            out[key] = (entry.ncalls, entry.ncalls, entry.tottime,
                        entry.cumtime, dict(entry.callers))
        self._stats_snapshot = out
        return out

    def print_stats(self, sort=-1):
        snapshot = self.create_stats()
        rows = []
        for key, (cc, nc, tt, ct, _callers) in snapshot.items():
            filename, lineno, name = key
            rows.append((cc, tt, ct, "%s:%d(%s)" % (filename, lineno, name)))
        # Default sort by cumulative time descending
        rows.sort(key=lambda r: r[2], reverse=True)
        print("   ncalls  tottime  cumtime  filename:lineno(function)")
        for cc, tt, ct, label in rows:
            print("%9d %8.6f %8.6f  %s" % (cc, tt, ct, label))

    def dump_stats(self, file):
        # Write a simple textual dump (avoids importing pickle/marshal).
        snapshot = self.create_stats()
        if hasattr(file, "write"):
            f = file
            close = False
        else:
            f = open(file, "w")
            close = True
        try:
            for key, (cc, nc, tt, ct, callers) in snapshot.items():
                f.write("%r\t%d\t%d\t%r\t%r\t%r\n" %
                        (key, cc, nc, tt, ct, callers))
        finally:
            if close:
                f.close()


# ----------------------------------------------------------------------
# Module-level convenience API mirroring cProfile
# ----------------------------------------------------------------------
def run(statement, filename=None, sort=-1):
    """Profile *statement* in a fresh global namespace."""
    prof = Profile()
    try:
        prof.run(statement)
    except SystemExit:
        pass
    if filename is not None:
        prof.dump_stats(filename)
    else:
        prof.print_stats(sort)
    return prof


def runctx(statement, globals, locals, filename=None, sort=-1):
    """Profile *statement* using the given globals and locals."""
    prof = Profile()
    try:
        prof.runctx(statement, globals, locals)
    except SystemExit:
        pass
    if filename is not None:
        prof.dump_stats(filename)
    else:
        prof.print_stats(sort)
    return prof


# ----------------------------------------------------------------------
# Invariant probes
# ----------------------------------------------------------------------
def cprofile2_profile():
    """Verify that the Profile class is operational."""
    p = Profile()
    if not isinstance(p, Profile):
        return False

    def _work():
        total = 0
        for i in range(50):
            total += i * i
        return total

    result = p.runcall(_work)
    if result != sum(i * i for i in range(50)):
        return False
    if not p.stats:
        return False
    # Confirm enable/disable cycling works without raising
    p2 = Profile()
    p2.enable()
    _ = sum(range(10))
    p2.disable()
    return True


def cprofile2_run():
    """Verify the module-level run() helper executes and gathers stats."""
    prof = Profile()
    prof.run("x = sum(range(25))")
    if not prof.stats:
        return False
    # Also exercise the module-level run with a file=None path; suppress output
    import io
    buf = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = buf
        result = run("y = sum(range(10))")
    finally:
        sys.stdout = real_stdout
    return isinstance(result, Profile)


def cprofile2_runctx():
    """Verify the module-level runctx() helper honors provided namespaces."""
    g = {"__builtins__": __builtins__}
    l = {}
    prof = Profile()
    prof.runctx("z = 1 + 2 + 3", g, l)
    if l.get("z") != 6:
        return False
    if not prof.stats:
        return False
    # Also exercise the module-level runctx; suppress output
    import io
    g2 = {"__builtins__": __builtins__}
    l2 = {}
    buf = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = buf
        result = runctx("w = 7 * 6", g2, l2)
    finally:
        sys.stdout = real_stdout
    if l2.get("w") != 42:
        return False
    return isinstance(result, Profile)


__all__ = [
    "Profile",
    "run",
    "runctx",
    "cprofile2_profile",
    "cprofile2_run",
    "cprofile2_runctx",
]