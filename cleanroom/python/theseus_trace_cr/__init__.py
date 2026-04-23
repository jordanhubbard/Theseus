"""
theseus_trace_cr — Clean-room trace module.
No import of the standard `trace` module.
"""

import sys as _sys
import os as _os
import os.path as _path
import gc as _gc


class CoverageResults:
    def __init__(self, counts=None, calledfuncs=None, infile=None, callers=None, outfile=None):
        self.counts = counts or {}
        self.calledfuncs = calledfuncs or {}
        self.callers = callers or {}
        self.infile = infile
        self.outfile = outfile

    def update(self, other):
        for key, value in other.counts.items():
            self.counts[key] = self.counts.get(key, 0) + value
        for key in other.calledfuncs:
            self.calledfuncs[key] = 1
        for key in other.callers:
            self.callers[key] = 1

    def write_results(self, show_missing=True, summary=False, coverdir=None):
        pass

    def write_results_file(self, path, lines, lnotab, lines_hit, encoding=None):
        pass


class Trace:
    def __init__(self, count=1, trace=1, countfuncs=0, countcallers=0,
                 ignoremods=(), ignoredirs=(), infile=None, outfile=None,
                 timing=False):
        self.count = count
        self.trace = trace
        self.countfuncs = countfuncs
        self.countcallers = countcallers
        self.infile = infile
        self.outfile = outfile
        self.timing = timing

        self.counts = {}
        self.calledfuncs = {}
        self.callers = {}
        self.ignore = _Ignore(ignoremods, ignoredirs)
        self._callerframeref = None

        if timing:
            import time
            self.start_time = time.time()
        else:
            self.start_time = None
        self.globaltrace = self._globaltrace_lt

    def run(self, cmd):
        import __main__
        dict = __main__.__dict__
        self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals=None, locals=None):
        if globals is None:
            globals = {}
        if locals is None:
            locals = {}
        self.globaltrace = self._globaltrace_lt if self.trace else self._globaltrace_count
        if self.count or self.trace:
            _sys.settrace(self.globaltrace)
        try:
            exec(cmd, globals, locals)
        finally:
            _sys.settrace(None)

    def runfunc(self, func, /, *args, **kw):
        result = None
        if not self.donothing:
            _sys.settrace(self.globaltrace)
        try:
            result = func(*args, **kw)
        finally:
            if not self.donothing:
                _sys.settrace(None)
        return result

    @property
    def donothing(self):
        return not (self.count or self.trace or self.countfuncs or self.countcallers)

    def file_module_function_of(self, frame):
        filename = frame.f_globals.get('__file__', None)
        if filename is None:
            filename = '<unknown>'
        elif filename.endswith(('.pyc', '.pyo')):
            filename = filename[:-1]
        modulename = frame.f_globals.get('__name__', None)
        funcname = frame.f_code.co_name
        return filename, modulename, funcname

    def _globaltrace_lt(self, frame, why, arg):
        if why == 'call':
            filename, modulename, funcname = self.file_module_function_of(frame)
            if self.ignore.names(filename, modulename):
                return None
            return self._localtrace
        return None

    def _globaltrace_count(self, frame, why, arg):
        if why == 'call':
            return self._localtrace
        return None

    def _localtrace(self, frame, why, arg):
        if why == 'line':
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            self.counts[(filename, lineno)] = self.counts.get((filename, lineno), 0) + 1
        return self._localtrace

    def results(self):
        return CoverageResults(counts=self.counts.copy(),
                               calledfuncs=self.calledfuncs.copy(),
                               infile=self.infile,
                               callers=self.callers.copy(),
                               outfile=self.outfile)


class _Ignore:
    def __init__(self, modules=None, dirs=None):
        self._mods = set(modules or [])
        self._dirs = [_os.path.normpath(d) for d in (dirs or [])]
        self._ignore = {}

    def names(self, filename, modulename):
        if modulename in self._ignore:
            return self._ignore[modulename]
        for d in self._dirs:
            if filename.startswith(d):
                self._ignore[modulename] = True
                return True
        if modulename in self._mods:
            self._ignore[modulename] = True
            return True
        self._ignore[modulename] = False
        return False


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def trace2_create():
    """Trace() can be created with count=True; returns True."""
    t = Trace(count=True, trace=False)
    return hasattr(t, 'runfunc') and hasattr(t, 'results')


def trace2_runfunc():
    """runfunc() executes a function and returns its result; returns True."""
    t = Trace(count=True, trace=False)
    result = t.runfunc(lambda x: x * 2, 21)
    return result == 42


def trace2_results():
    """results() returns a CoverageResults after runfunc(); returns True."""
    t = Trace(count=True, trace=False)
    t.runfunc(lambda: sum(range(10)))
    r = t.results()
    return isinstance(r, CoverageResults)


__all__ = [
    'Trace', 'CoverageResults',
    'trace2_create', 'trace2_runfunc', 'trace2_results',
]
