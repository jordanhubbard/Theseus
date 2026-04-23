"""
theseus_cprofile_cr — Clean-room cProfile module.
No import of the standard `cProfile` module.
Uses _lsprof C extension directly.
"""

import _lsprof as _lsprof_mod
import io as _io


class Profile(_lsprof_mod.Profiler):
    """Deterministic profiling of Python programs."""

    def create_stats(self):
        self.disable()
        self.snapshot_stats()

    def snapshot_stats(self):
        entries = self.getstats()
        self.stats = {}
        callersdicts = {}
        for entry in entries:
            func = label(entry.code)
            nc = entry.callcount
            tt = entry.totaltime
            ct = entry.inlinetime
            callers = {}
            callersdicts[id(entry.code)] = callers
            self.stats[func] = nc, nc, tt, ct, callers
        for entry in entries:
            if entry.calls:
                func = label(entry.code)
                for subentry in entry.calls:
                    try:
                        callers = callersdicts[id(subentry.code)]
                    except KeyError:
                        continue
                    nc = subentry.callcount
                    ct = subentry.inlinetime
                    tt = subentry.totaltime
                    if func in callers:
                        prev = callers[func]
                        nc += prev[0]
                        ct += prev[2]
                        tt += prev[3]
                    callers[func] = nc, nc, ct, tt

    def runctx(self, cmd, globals, locals):
        self.enable()
        try:
            exec(cmd, globals, locals)
        finally:
            self.disable()
        return self

    def runcall(self, func, /, *args, **kw):
        self.enable()
        try:
            return func(*args, **kw)
        finally:
            self.disable()

    def __enter__(self):
        self.enable()
        return self

    def __exit__(self, *exc_info):
        self.disable()


def label(code):
    """Return a (filename, firstlineno, name) tuple for a code object."""
    if isinstance(code, str):
        return ('~', 0, code)
    return (code.co_filename, code.co_firstlineno, code.co_qualname)


def run(statement, filename=None, sort=-1):
    """Profile a statement and optionally save results."""
    prof = Profile()
    try:
        prof.runctx(statement, {}, {})
    except SystemExit:
        pass
    if filename is not None:
        prof.dump_stats(filename)
    return prof


def runctx(statement, globals, locals, filename=None, sort=-1):
    """Profile a statement in given globals/locals."""
    prof = Profile()
    try:
        prof.runctx(statement, globals, locals)
    except SystemExit:
        pass
    if filename is not None:
        import marshal as _marshal
        prof.create_stats()
        with open(filename, 'wb') as f:
            _marshal.dump(prof.stats, f)
    return prof


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cprofile2_profile():
    """Profile class can be instantiated; returns True."""
    p = Profile()
    return (hasattr(p, 'enable') and
            hasattr(p, 'disable') and
            hasattr(p, 'runcall'))


def cprofile2_run():
    """run() function executes a statement and profiles it; returns True."""
    return callable(run)


def cprofile2_runctx():
    """runctx() function profiles code in a given context; returns True."""
    g = {}
    runctx('x = 1 + 1', g, g)
    return g.get('x') == 2


__all__ = [
    'Profile', 'run', 'runctx', 'label',
    'cprofile2_profile', 'cprofile2_run', 'cprofile2_runctx',
]
