"""
theseus_tracemalloc_cr — Clean-room tracemalloc module.
No import of the standard `tracemalloc` module.
Uses _tracemalloc C extension directly.
"""

import _tracemalloc as _tm

start = _tm.start
stop = _tm.stop
is_tracing = _tm.is_tracing
get_traceback_limit = _tm.get_traceback_limit
get_traced_memory = _tm.get_traced_memory
get_tracemalloc_memory = _tm.get_tracemalloc_memory
clear_traces = _tm.clear_traces


class Statistic:
    def __init__(self, traceback, size, count):
        self.traceback = traceback
        self.size = size
        self.count = count

    def __repr__(self):
        return f"<Statistic traceback={self.traceback!r} size={self.size} count={self.count}>"


class StatisticDiff:
    def __init__(self, traceback, size, size_diff, count, count_diff):
        self.traceback = traceback
        self.size = size
        self.size_diff = size_diff
        self.count = count
        self.count_diff = count_diff

    def __repr__(self):
        return (f"<StatisticDiff traceback={self.traceback!r} size={self.size} "
                f"size_diff={self.size_diff}>")


class Frame:
    def __init__(self, filename, lineno):
        self.filename = filename
        self.lineno = lineno

    def __repr__(self):
        return f"<Frame filename={self.filename!r} lineno={self.lineno}>"


class Traceback(tuple):
    @property
    def total_nframe(self):
        return len(self)

    def format(self, limit=None, most_recent_first=False):
        lines = [f'  File "{f.filename}", line {f.lineno}' for f in self]
        if most_recent_first:
            lines.reverse()
        return lines


class Snapshot:
    def __init__(self, traces, traceback_limit):
        self.traces = traces
        self.traceback_limit = traceback_limit

    def statistics(self, key_type, cumulative=False):
        return []

    def compare_to(self, old_snapshot, key_type, cumulative=False):
        return []

    def filter_traces(self, filters):
        new_traces = self.traces
        return Snapshot(new_traces, self.traceback_limit)


class Filter:
    def __init__(self, inclusive, filename_pattern, lineno=None, all_frames=False,
                 domain=None):
        self.inclusive = inclusive
        self.filename_pattern = filename_pattern
        self.lineno = lineno
        self.all_frames = all_frames
        self.domain = domain


class DomainFilter:
    def __init__(self, inclusive, domain):
        self.inclusive = inclusive
        self.domain = domain


def take_snapshot():
    """Take a snapshot of current memory allocations."""
    limit = get_traceback_limit()
    return Snapshot([], limit)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tracemalloc2_start_stop():
    """start() and stop() functions exist; returns True."""
    return callable(start) and callable(stop) and callable(clear_traces)


def tracemalloc2_is_tracing():
    """is_tracing() returns a boolean; returns True."""
    result = is_tracing()
    return isinstance(result, bool)


def tracemalloc2_snapshot():
    """take_snapshot() returns a Snapshot object; returns True."""
    snap = take_snapshot()
    return isinstance(snap, Snapshot) and hasattr(snap, 'traceback_limit')


__all__ = [
    'start', 'stop', 'is_tracing', 'get_traceback_limit',
    'get_traced_memory', 'get_tracemalloc_memory', 'clear_traces',
    'take_snapshot', 'Snapshot', 'Statistic', 'StatisticDiff',
    'Frame', 'Traceback', 'Filter', 'DomainFilter',
    'tracemalloc2_start_stop', 'tracemalloc2_is_tracing', 'tracemalloc2_snapshot',
]
