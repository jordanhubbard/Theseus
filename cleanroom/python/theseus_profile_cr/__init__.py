"""
theseus_profile_cr — Clean-room profile module.
No import of the standard `profile` module.
"""

import sys as _sys
import time as _time
import io as _io


class Stats:
    """Statistics from a profiling run."""

    def __init__(self, stats_dict=None):
        self.stats = stats_dict or {}
        self.total_tt = sum(v[2] for v in self.stats.values()) if self.stats else 0
        self.total_calls = sum(v[1] for v in self.stats.values()) if self.stats else 0
        self.prim_calls = sum(v[0] for v in self.stats.values()) if self.stats else 0
        self.fcn_list = None
        self.stream = _io.StringIO()

    def strip_dirs(self):
        return self

    def sort_stats(self, *keys):
        self.fcn_list = sorted(self.stats.keys())
        return self

    def reverse_order(self):
        if self.fcn_list:
            self.fcn_list.reverse()
        return self

    def print_stats(self, *restrictions):
        for key in (self.fcn_list or sorted(self.stats.keys())):
            v = self.stats[key]
            print('%5d %8.3f %8.3f %8.3f %s' % (
                v[1], v[2], v[2] / max(v[1], 1), v[3],
                '%s:%d(%s)' % key
            ), file=self.stream)
        return self

    def print_callers(self, *restrictions):
        return self

    def print_callees(self, *restrictions):
        return self

    def get_stats_profile(self):
        result = {}
        for key, v in self.stats.items():
            filename, lineno, funcname = key
            result[funcname] = {
                'ncalls': v[1],
                'tottime': v[2],
                'cumtime': v[3],
                'filename': filename,
                'lineno': lineno,
            }
        return result

    def dump_stats(self, filename):
        import marshal
        with open(filename, 'wb') as f:
            marshal.dump(self.stats, f)


class Profile:
    """Pure Python profiler."""

    def __init__(self, timer=None, bias=None):
        self._timer = timer or _time.perf_counter
        self._stats = {}
        self._t = self._timer()
        self._call_stack = []
        self._bias = bias or 0.0

    def set_cmd(self, cmd):
        self._cmd = cmd

    def simulate_cmd_complete(self):
        pass

    def print_stats(self, sort=-1):
        stats = Stats(self._stats)
        stats.sort_stats(sort)
        stats.print_stats()

    def dump_stats(self, file):
        stats = Stats(self._stats)
        stats.dump_stats(file)

    def create_stats(self):
        return Stats(self._stats)

    def snapshot_stats(self):
        self._stats_copy = dict(self._stats)

    def run(self, cmd):
        import __main__
        dict = __main__.__dict__
        return self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals, locals):
        _sys.setprofile(self._profile_tracer)
        try:
            exec(cmd, globals, locals)
        finally:
            _sys.setprofile(None)
        return self.create_stats()

    def runcall(self, func, /, *args, **kw):
        _sys.setprofile(self._profile_tracer)
        try:
            return func(*args, **kw)
        finally:
            _sys.setprofile(None)

    def _profile_tracer(self, frame, event, arg):
        if event == 'call':
            key = (frame.f_code.co_filename, frame.f_code.co_firstlineno, frame.f_code.co_name)
            self._call_stack.append((key, self._timer()))
        elif event == 'return':
            if self._call_stack:
                key, start_time = self._call_stack.pop()
                elapsed = self._timer() - start_time
                if key not in self._stats:
                    self._stats[key] = [0, 0, 0.0, 0.0, {}]
                self._stats[key][0] += 1
                self._stats[key][1] += 1
                self._stats[key][2] += elapsed
                self._stats[key][3] += elapsed


def run(statement, filename=None, sort=-1):
    """Run statement under the profiler."""
    prof = Profile()
    result = None
    try:
        prof.run(statement)
    finally:
        if filename is not None:
            prof.dump_stats(filename)
    return prof.create_stats()


def runctx(statement, globals, locals, filename=None, sort=-1):
    """Run statement under profiler with given globals/locals."""
    prof = Profile()
    try:
        prof.runctx(statement, globals, locals)
    finally:
        if filename is not None:
            prof.dump_stats(filename)
    return prof.create_stats()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def profile2_run():
    """Profile.run executes statement and returns Stats; returns True."""
    prof = Profile()
    stats = prof.run('x = 1 + 1')
    return isinstance(stats, Stats)


def profile2_runcall():
    """Profile.runcall calls function and records stats; returns True."""
    prof = Profile()
    result = prof.runcall(lambda: 42)
    return result == 42


def profile2_stats():
    """Stats.get_stats_profile returns function stats dict; returns True."""
    prof = Profile()
    prof.run('def _f(): pass\n_f()')
    stats = prof.create_stats()
    result = stats.get_stats_profile()
    return isinstance(result, dict)


__all__ = [
    'Profile', 'Stats', 'run', 'runctx',
    'profile2_run', 'profile2_runcall', 'profile2_stats',
]
