"""Clean-room implementation of a tracemalloc-like module.

This is a behavioral stand-in: it tracks a started/stopped state and
exposes a minimal snapshot abstraction. It does NOT import the original
``tracemalloc`` module or any third-party library.
"""

import sys


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_state = {
    "tracing": False,
    "frames": 1,
    "traces": [],   # list of (size, traceback)
}


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def start(nframe=1):
    """Begin tracing memory allocations."""
    if not isinstance(nframe, int) or nframe < 1:
        raise ValueError("the number of frames must be >= 1")
    _state["tracing"] = True
    _state["frames"] = nframe
    _state["traces"] = []


def stop():
    """Stop tracing memory allocations and clear traces."""
    _state["tracing"] = False
    _state["traces"] = []


def is_tracing():
    """Return True if tracing is active."""
    return bool(_state["tracing"])


def get_tracemalloc_memory():
    """Return memory used by the (fake) tracemalloc module, in bytes."""
    return sys.getsizeof(_state) + sum(sys.getsizeof(t) for t in _state["traces"])


def get_traced_memory():
    """Return (current, peak) traced memory size."""
    total = sum(size for size, _ in _state["traces"])
    return (total, total)


def clear_traces():
    """Clear all collected traces."""
    _state["traces"] = []


def reset_peak():
    """Reset peak counter (no-op equivalent for this stand-in)."""
    return None


# ---------------------------------------------------------------------------
# Frame / Traceback / Statistic / Snapshot abstractions
# ---------------------------------------------------------------------------

class Frame(object):
    """A single frame in a traceback."""

    __slots__ = ("filename", "lineno")

    def __init__(self, filename, lineno):
        self.filename = filename
        self.lineno = lineno

    def __eq__(self, other):
        if not isinstance(other, Frame):
            return NotImplemented
        return self.filename == other.filename and self.lineno == other.lineno

    def __hash__(self):
        return hash((self.filename, self.lineno))

    def __repr__(self):
        return "<Frame filename=%r lineno=%r>" % (self.filename, self.lineno)

    def __str__(self):
        return "%s:%s" % (self.filename, self.lineno)


class Traceback(object):
    """A sequence of frames."""

    def __init__(self, frames):
        self._frames = tuple(frames)

    def __iter__(self):
        return iter(self._frames)

    def __len__(self):
        return len(self._frames)

    def __getitem__(self, index):
        return self._frames[index]

    def __eq__(self, other):
        if not isinstance(other, Traceback):
            return NotImplemented
        return self._frames == other._frames

    def __hash__(self):
        return hash(self._frames)

    def format(self, limit=None):
        frames = self._frames
        if limit is not None:
            frames = frames[-limit:]
        out = []
        for f in frames:
            out.append('  File "%s", line %d' % (f.filename, f.lineno))
        return out

    def __repr__(self):
        return "<Traceback %r>" % (self._frames,)


class Statistic(object):
    """Aggregated allocation statistic."""

    def __init__(self, traceback, size, count):
        self.traceback = traceback
        self.size = size
        self.count = count

    def __repr__(self):
        return "<Statistic size=%d count=%d>" % (self.size, self.count)


class Snapshot(object):
    """A snapshot of the traced memory blocks."""

    def __init__(self, traces):
        # Each trace is (size, traceback_tuple_of_frame_pairs)
        self._traces = list(traces)

    def statistics(self, key_type="filename"):
        groups = {}
        for size, tb in self._traces:
            if not tb:
                key = ("<unknown>", 0)
            elif key_type == "lineno":
                top = tb[0]
                key = (top.filename, top.lineno)
            else:  # filename
                top = tb[0]
                key = (top.filename, 0)
            if key not in groups:
                groups[key] = [0, 0, tb]
            groups[key][0] += size
            groups[key][1] += 1
        result = []
        for (fname, lineno), (size, count, tb) in groups.items():
            frame = Frame(fname, lineno)
            result.append(Statistic(Traceback([frame]), size, count))
        result.sort(key=lambda s: s.size, reverse=True)
        return result

    def __repr__(self):
        return "<Snapshot traces=%d>" % (len(self._traces),)


def take_snapshot():
    """Take a snapshot of current allocations.

    Requires tracing to be active (matches the original API contract).
    """
    if not _state["tracing"]:
        raise RuntimeError(
            "the tracemalloc module must be tracing memory allocations "
            "to take a snapshot"
        )
    return Snapshot(list(_state["traces"]))


# ---------------------------------------------------------------------------
# Helper used internally for tests — record a synthetic allocation
# ---------------------------------------------------------------------------

def _record(size, frames=None):
    """Record a synthetic allocation (test helper, not part of public API)."""
    if not _state["tracing"]:
        return
    if frames is None:
        frames = [Frame("<synthetic>", 1)]
    else:
        frames = [
            f if isinstance(f, Frame) else Frame(f[0], f[1])
            for f in frames
        ]
    _state["traces"].append((int(size), tuple(frames)))


# ---------------------------------------------------------------------------
# Invariant functions (return True iff the behavior holds)
# ---------------------------------------------------------------------------

def tracemalloc2_start_stop():
    """Verify start() and stop() toggle the tracing state."""
    # Ensure clean baseline
    stop()
    if is_tracing():
        return False
    start()
    if not is_tracing():
        return False
    stop()
    if is_tracing():
        return False
    # Custom nframe value
    start(5)
    ok = is_tracing() and _state["frames"] == 5
    stop()
    if not ok:
        return False
    # Invalid nframe must raise
    try:
        start(0)
    except ValueError:
        pass
    else:
        stop()
        return False
    return True


def tracemalloc2_is_tracing():
    """Verify is_tracing() reflects the tracing state accurately."""
    stop()
    if is_tracing() is not False:
        return False
    start()
    if is_tracing() is not True:
        return False
    stop()
    if is_tracing() is not False:
        return False
    return True


def tracemalloc2_snapshot():
    """Verify snapshot semantics: requires tracing, captures recorded data."""
    stop()
    # Must raise when not tracing
    try:
        take_snapshot()
    except RuntimeError:
        pass
    else:
        return False

    start()
    _record(100, [("a.py", 10), ("b.py", 20)])
    _record(250, [("a.py", 10)])
    _record(50,  [("c.py", 5)])

    snap = take_snapshot()
    if not isinstance(snap, Snapshot):
        stop()
        return False
    if len(snap._traces) != 3:
        stop()
        return False

    # get_traced_memory should sum sizes
    cur, peak = get_traced_memory()
    if cur != 400 or peak != 400:
        stop()
        return False

    # statistics by filename: a.py -> 350, c.py -> 50
    stats = snap.statistics("filename")
    by_file = {s.traceback[0].filename: s for s in stats}
    if "a.py" not in by_file or "c.py" not in by_file:
        stop()
        return False
    if by_file["a.py"].size != 350 or by_file["a.py"].count != 2:
        stop()
        return False
    if by_file["c.py"].size != 50 or by_file["c.py"].count != 1:
        stop()
        return False

    # statistics ordering: largest first
    if stats[0].size < stats[-1].size:
        stop()
        return False

    # Frame and Traceback formatting sanity
    f = Frame("x.py", 7)
    if str(f) != "x.py:7":
        stop()
        return False
    tb = Traceback([f])
    formatted = tb.format()
    if len(formatted) != 1 or "x.py" not in formatted[0]:
        stop()
        return False

    # clear_traces empties recorded data
    clear_traces()
    if get_traced_memory() != (0, 0):
        stop()
        return False

    stop()
    # After stop, snapshot should error again
    try:
        take_snapshot()
    except RuntimeError:
        pass
    else:
        return False
    return True