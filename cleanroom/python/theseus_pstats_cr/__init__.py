"""Clean-room implementation of a pstats-like profiling statistics module.

This module provides classes for analyzing profiler statistics without
importing the original `pstats` module.
"""

import os
import sys
import time
import marshal
import re


# ---------------------------------------------------------------------------
# SortKey enumeration (clean-room re-implementation)
# ---------------------------------------------------------------------------

class SortKey:
    """Enumeration of valid sort keys for Stats output."""

    CALLS = "calls"
    CUMULATIVE = "cumulative"
    FILENAME = "filename"
    LINE = "line"
    NAME = "name"
    NFL = "nfl"
    PCALLS = "pcalls"
    STDNAME = "stdname"
    TIME = "time"

    _ALL = (
        "calls", "cumulative", "filename", "line", "name",
        "nfl", "pcalls", "stdname", "time",
    )

    @classmethod
    def values(cls):
        return tuple(cls._ALL)

    @classmethod
    def is_valid(cls, key):
        if isinstance(key, str):
            return key in cls._ALL
        return False


# ---------------------------------------------------------------------------
# FunctionProfile — per-function stats record
# ---------------------------------------------------------------------------

class FunctionProfile:
    """Holds the profile data for a single function."""

    __slots__ = (
        "ncalls", "tottime", "percall_tottime",
        "cumtime", "percall_cumtime",
        "file_name", "line_number",
    )

    def __init__(self, ncalls=0, tottime=0.0, percall_tottime=0.0,
                 cumtime=0.0, percall_cumtime=0.0,
                 file_name="", line_number=0):
        self.ncalls = ncalls
        self.tottime = float(tottime)
        self.percall_tottime = float(percall_tottime)
        self.cumtime = float(cumtime)
        self.percall_cumtime = float(percall_cumtime)
        self.file_name = file_name
        self.line_number = int(line_number)

    def __repr__(self):
        return ("FunctionProfile(ncalls=%r, tottime=%r, percall_tottime=%r, "
                "cumtime=%r, percall_cumtime=%r, file_name=%r, "
                "line_number=%r)" % (
                    self.ncalls, self.tottime, self.percall_tottime,
                    self.cumtime, self.percall_cumtime,
                    self.file_name, self.line_number,
                ))

    def __eq__(self, other):
        if not isinstance(other, FunctionProfile):
            return NotImplemented
        return (
            self.ncalls == other.ncalls
            and self.tottime == other.tottime
            and self.percall_tottime == other.percall_tottime
            and self.cumtime == other.cumtime
            and self.percall_cumtime == other.percall_cumtime
            and self.file_name == other.file_name
            and self.line_number == other.line_number
        )

    def to_tuple(self):
        return (self.ncalls, self.tottime, self.percall_tottime,
                self.cumtime, self.percall_cumtime,
                self.file_name, self.line_number)


# ---------------------------------------------------------------------------
# StatsProfile — aggregated profile
# ---------------------------------------------------------------------------

class StatsProfile:
    """Aggregated profiling statistics: total_tt and per-function records."""

    __slots__ = ("total_tt", "func_profiles")

    def __init__(self, total_tt=0.0, func_profiles=None):
        self.total_tt = float(total_tt)
        self.func_profiles = dict(func_profiles) if func_profiles else {}

    def __repr__(self):
        return "StatsProfile(total_tt=%r, func_profiles=%r)" % (
            self.total_tt, self.func_profiles,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _func_std_string(func_name):
    file, line, name = func_name
    if file.startswith("~") and line == 0:
        # Built-in functions are represented as ('~', 0, '<built-in>')
        return name
    return "%s:%d(%s)" % (file, line, name)


def _count_calls(call_dict):
    n = 0
    for v in call_dict.values():
        if isinstance(v, tuple):
            n += v[0]
        else:
            n += v
    return n


_SORT_KEY_MAP = {
    "calls":       (((4, -1),), "call count"),
    "ncalls":      (((4, -1),), "call count"),
    "cumtime":     (((3, -1),), "cumulative time"),
    "cumulative":  (((3, -1),), "cumulative time"),
    "filename":    (((6, 1),), "file name"),
    "line":        (((7, 1),), "line number"),
    "module":      (((6, 1),), "file name"),
    "name":        (((8, 1),), "function name"),
    "nfl":         (((8, 1), (6, 1), (7, 1)), "name/file/line"),
    "pcalls":      (((0, -1),), "primitive call count"),
    "stdname":     (((9, 1),), "standard name"),
    "time":        (((2, -1),), "internal time"),
    "tottime":     (((2, -1),), "internal time"),
}


# ---------------------------------------------------------------------------
# Stats class
# ---------------------------------------------------------------------------

class Stats:
    """Clean-room re-implementation of a profiler-stats analyzer.

    Accepts profile data either as:
      * a path to a marshalled stats file produced by cProfile/profile,
      * an object with a ``create_stats()`` method (e.g. a Profile instance),
      * another Stats instance (merged in),
      * or a raw stats mapping passed via ``stats=`` keyword.
    """

    def __init__(self, *args, stream=None, stats=None):
        self.stream = stream if stream is not None else sys.stdout
        self.total_calls = 0
        self.prim_calls = 0
        self.total_tt = 0.0
        self.files = []
        self.fcn_list = None
        self.stats = {}
        self.sort_arg_dict = {}
        self.top_level = set()
        self.all_callees = None

        if stats is not None:
            self.stats = dict(stats)
            self._compute_totals()
        for arg in args:
            self.add(arg)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def add(self, *arg_list):
        if not arg_list:
            return self
        for item in arg_list:
            self._add_one(item)
        return self

    def _add_one(self, arg):
        if isinstance(arg, Stats):
            self._merge(arg.stats, arg.files, arg.total_tt,
                        arg.total_calls, arg.prim_calls, arg.top_level)
            return

        if isinstance(arg, str):
            with open(arg, "rb") as fh:
                data = marshal.load(fh)
            self._ingest_raw(data, files=[arg])
            return

        # Assume profile-like object
        if hasattr(arg, "create_stats"):
            arg.create_stats()
            data = getattr(arg, "stats", {})
            self._ingest_raw(data, files=[])
            return

        if isinstance(arg, dict):
            self._ingest_raw(arg, files=[])
            return

        raise TypeError("Cannot add object of type %r to Stats" %
                        type(arg).__name__)

    def _ingest_raw(self, data, files):
        # data: {func: (cc, nc, tt, ct, callers)}
        merged = {}
        total_calls = 0
        prim_calls = 0
        total_tt = 0.0
        top_level = set()

        for func, entry in data.items():
            cc, nc, tt, ct, callers = entry
            total_calls += nc
            prim_calls += cc
            total_tt += tt
            if not callers:
                top_level.add(func)
            merged[func] = (cc, nc, tt, ct, dict(callers))

        self._merge(merged, files, total_tt, total_calls, prim_calls,
                    top_level)

    def _merge(self, new_stats, files, total_tt, total_calls, prim_calls,
               top_level):
        for f in files:
            if f and f not in self.files:
                self.files.append(f)
        self.total_calls += total_calls
        self.prim_calls += prim_calls
        self.total_tt += total_tt
        self.top_level |= set(top_level)

        for func, entry in new_stats.items():
            cc, nc, tt, ct, callers = entry
            if func in self.stats:
                occ, onc, ott, oct_, ocallers = self.stats[func]
                merged_callers = dict(ocallers)
                for k, v in callers.items():
                    if k in merged_callers:
                        a = merged_callers[k]
                        b = v
                        if isinstance(a, tuple) and isinstance(b, tuple):
                            merged_callers[k] = tuple(
                                x + y for x, y in zip(a, b))
                        else:
                            merged_callers[k] = a + b
                    else:
                        merged_callers[k] = v
                self.stats[func] = (
                    occ + cc, onc + nc, ott + tt, oct_ + ct, merged_callers,
                )
            else:
                self.stats[func] = (cc, nc, tt, ct, dict(callers))

    def _compute_totals(self):
        total_calls = 0
        prim_calls = 0
        total_tt = 0.0
        top_level = set()
        for func, entry in self.stats.items():
            cc, nc, tt, ct, callers = entry
            total_calls += nc
            prim_calls += cc
            total_tt += tt
            if not callers:
                top_level.add(func)
        self.total_calls = total_calls
        self.prim_calls = prim_calls
        self.total_tt = total_tt
        self.top_level = top_level

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_stats(self, *fields):
        if not fields:
            self.fcn_list = None
            return self

        # Normalize SortKey enum-style entries (already strings here).
        norm_fields = []
        for f in fields:
            if isinstance(f, str):
                if f not in _SORT_KEY_MAP:
                    raise ValueError("Unknown sort key %r" % (f,))
                norm_fields.append(f)
            else:
                raise TypeError("Sort fields must be strings")

        def make_key(item):
            func, entry = item
            cc, nc, tt, ct, callers = entry
            if nc == 0:
                pcalls = 0.0
                pertot = 0.0
            else:
                pcalls = float(cc) / nc if nc else 0.0
                pertot = tt / nc if nc else 0.0
            percum = ct / nc if nc else 0.0
            file, line, name = func
            stdname = _func_std_string(func)
            row = (
                cc,            # 0 pcalls (primitive calls)
                nc,            # 1
                tt,            # 2 tottime
                ct,            # 3 cumtime
                nc,            # 4 calls
                pertot,        # 5
                file,          # 6
                line,          # 7
                name,          # 8
                stdname,       # 9
            )
            keys = []
            for fname in norm_fields:
                indices, _ = _SORT_KEY_MAP[fname]
                for idx, direction in indices:
                    val = row[idx]
                    if direction < 0:
                        if isinstance(val, (int, float)):
                            keys.append(-val)
                        else:
                            # Fallback: invert string ordering not trivial;
                            # negate via tuple of negative ord codes.
                            keys.append(tuple(-ord(c) for c in val))
                    else:
                        keys.append(val)
            return tuple(keys)

        items = list(self.stats.items())
        items.sort(key=make_key)
        self.fcn_list = [func for func, _ in items]
        return self

    def reverse_order(self):
        if self.fcn_list is not None:
            self.fcn_list.reverse()
        return self

    # ------------------------------------------------------------------
    # Stats profile
    # ------------------------------------------------------------------

    def get_stats_profile(self):
        func_profiles = {}
        for func, entry in self.stats.items():
            cc, nc, tt, ct, callers = entry
            file, line, name = func
            percall_tt = (tt / nc) if nc else 0.0
            percall_ct = (ct / cc) if cc else 0.0
            func_profiles[name] = FunctionProfile(
                ncalls=nc,
                tottime=tt,
                percall_tottime=percall_tt,
                cumtime=ct,
                percall_cumtime=percall_ct,
                file_name=file,
                line_number=line,
            )
        return StatsProfile(total_tt=self.total_tt,
                            func_profiles=func_profiles)

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _ordered_funcs(self):
        if self.fcn_list is not None:
            return list(self.fcn_list)
        return list(self.stats.keys())

    def print_stats(self, *amount):
        funcs = self._ordered_funcs()
        funcs = self._restrict(funcs, amount)
        out = self.stream
        out.write("   ncalls  tottime  percall  cumtime  percall "
                  "filename:lineno(function)\n")
        for func in funcs:
            cc, nc, tt, ct, callers = self.stats[func]
            ncalls_str = "%d/%d" % (nc, cc) if nc != cc else "%d" % nc
            percall_tt = (tt / nc) if nc else 0.0
            percall_ct = (ct / cc) if cc else 0.0
            out.write("%9s %8.3f %8.3f %8.3f %8.3f %s\n" % (
                ncalls_str, tt, percall_tt, ct, percall_ct,
                _func_std_string(func),
            ))
        return self

    def _restrict(self, funcs, selectors):
        for sel in selectors:
            if isinstance(sel, int):
                funcs = funcs[:sel]
            elif isinstance(sel, float) and 0.0 <= sel < 1.0:
                funcs = funcs[:int(len(funcs) * sel)]
            elif isinstance(sel, str):
                pat = re.compile(sel)
                funcs = [f for f in funcs if pat.search(_func_std_string(f))]
        return funcs

    def strip_dirs(self):
        new_stats = {}
        new_top = set()
        for func, entry in self.stats.items():
            file, line, name = func
            new_func = (os.path.basename(file), line, name)
            cc, nc, tt, ct, callers = entry
            new_callers = {}
            for cf, cv in callers.items():
                cfile, cline, cname = cf
                new_callers[(os.path.basename(cfile), cline, cname)] = cv
            if new_func in new_stats:
                occ, onc, ott, oct_, ocallers = new_stats[new_func]
                merged = dict(ocallers)
                for k, v in new_callers.items():
                    if k in merged:
                        a = merged[k]
                        if isinstance(a, tuple) and isinstance(v, tuple):
                            merged[k] = tuple(x + y for x, y in zip(a, v))
                        else:
                            merged[k] = a + v
                    else:
                        merged[k] = v
                new_stats[new_func] = (
                    occ + cc, onc + nc, ott + tt, oct_ + ct, merged,
                )
            else:
                new_stats[new_func] = (cc, nc, tt, ct, new_callers)
            if func in self.top_level:
                new_top.add(new_func)
        self.stats = new_stats
        self.top_level = new_top
        self.fcn_list = None
        self.files = []
        return self

    def dump_stats(self, filename):
        with open(filename, "wb") as fh:
            marshal.dump(self.stats, fh)
        return self


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def pstats2_sortkey():
    """Return True iff SortKey provides the canonical sort identifiers."""
    expected = {
        "CALLS", "CUMULATIVE", "FILENAME", "LINE", "NAME",
        "NFL", "PCALLS", "STDNAME", "TIME",
    }
    for attr in expected:
        if not hasattr(SortKey, attr):
            return False
        val = getattr(SortKey, attr)
        if not isinstance(val, str) or not val:
            return False
    if SortKey.CALLS != "calls":
        return False
    if SortKey.CUMULATIVE != "cumulative":
        return False
    if SortKey.TIME != "time":
        return False
    if not SortKey.is_valid(SortKey.NFL):
        return False
    if SortKey.is_valid("not_a_real_key"):
        return False
    return True


def pstats2_stats_class():
    """Return True iff the Stats class accepts data and computes totals."""
    raw = {
        ("a.py", 10, "alpha"): (1, 1, 0.20, 0.50, {}),
        ("b.py", 20, "beta"):  (2, 3, 0.10, 0.30,
                                {("a.py", 10, "alpha"): (3, 3, 0.05, 0.15)}),
    }
    s = Stats(stats=raw)
    if not isinstance(s, Stats):
        return False
    if abs(s.total_tt - 0.30) > 1e-9:
        return False
    if s.total_calls != 4:
        return False
    if s.prim_calls != 3:
        return False
    if ("a.py", 10, "alpha") not in s.top_level:
        return False

    s.sort_stats("cumulative")
    if s.fcn_list is None or len(s.fcn_list) != 2:
        return False
    # cumulative-descending: alpha (0.50) before beta (0.30)
    if s.fcn_list[0] != ("a.py", 10, "alpha"):
        return False

    s.sort_stats("calls")
    if s.fcn_list[0] != ("b.py", 20, "beta"):  # nc=3 > nc=1
        return False

    s.strip_dirs()
    if not all("/" not in f[0] for f in s.stats):
        return False
    return True


def pstats2_functionprofile():
    """Return True iff FunctionProfile / StatsProfile work correctly."""
    fp = FunctionProfile(
        ncalls=4, tottime=0.4, percall_tottime=0.1,
        cumtime=0.8, percall_cumtime=0.2,
        file_name="x.py", line_number=42,
    )
    if fp.ncalls != 4 or fp.line_number != 42:
        return False
    if abs(fp.tottime - 0.4) > 1e-9:
        return False
    if abs(fp.percall_cumtime - 0.2) > 1e-9:
        return False
    if fp.file_name != "x.py":
        return False

    raw = {
        ("p.py", 1, "fn1"): (2, 4, 0.40, 0.80, {}),
        ("q.py", 5, "fn2"): (1, 1, 0.10, 0.10, {}),
    }
    profile = Stats(stats=raw).get_stats_profile()
    if not isinstance(profile, StatsProfile):
        return False
    if abs(profile.total_tt - 0.50) > 1e-9:
        return False
    if "fn1" not in profile.func_profiles:
        return False
    fn1 = profile.func_profiles["fn1"]
    if not isinstance(fn1, FunctionProfile):
        return False
    if fn1.ncalls != 4:
        return False
    if abs(fn1.percall_tottime - 0.10) > 1e-9:
        return False
    if abs(fn1.percall_cumtime - 0.40) > 1e-9:  # ct/cc = 0.80/2
        return False
    if fn1.file_name != "p.py" or fn1.line_number != 1:
        return False

    fp2 = FunctionProfile(ncalls=4, tottime=0.4, percall_tottime=0.1,
                          cumtime=0.8, percall_cumtime=0.2,
                          file_name="x.py", line_number=42)
    if fp != fp2:
        return False
    return True


__all__ = [
    "SortKey",
    "Stats",
    "StatsProfile",
    "FunctionProfile",
    "pstats2_sortkey",
    "pstats2_stats_class",
    "pstats2_functionprofile",
]