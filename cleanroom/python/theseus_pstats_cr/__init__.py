"""
theseus_pstats_cr — Clean-room pstats module.
No import of the standard `pstats` module.
"""

import enum as _enum
import dataclasses as _dataclasses
import io as _io
import os as _os


class SortKey(_enum.Enum):
    CALLS = 'calls'
    CUMULATIVE = 'cumulative'
    FILENAME = 'filename'
    LINE = 'line'
    NAME = 'name'
    NFL = 'nfl'
    PCALLS = 'pcalls'
    STDNAME = 'stdname'
    TIME = 'time'
    TOTTIME = 'tottime'


@_dataclasses.dataclass
class FunctionProfile:
    ncalls: str = ''
    tottime: float = 0.0
    percall_tottime: float = 0.0
    cumtime: float = 0.0
    percall_cumtime: float = 0.0
    file_name: str = ''
    line_number: int = 0


@_dataclasses.dataclass
class StatsProfile:
    total_tt: float = 0.0
    func_profiles: dict = _dataclasses.field(default_factory=dict)


_SORT_KEY_MAP = {
    SortKey.CALLS: 3,
    SortKey.CUMULATIVE: 6,
    SortKey.FILENAME: 0,
    SortKey.LINE: 1,
    SortKey.NAME: 2,
    SortKey.NFL: (2, 0, 1),
    SortKey.PCALLS: 3,
    SortKey.STDNAME: (0, 1, 2),
    SortKey.TIME: 4,
    SortKey.TOTTIME: 4,
}

_SORT_COMPAT = {
    'calls': SortKey.CALLS,
    'cumulative': SortKey.CUMULATIVE,
    'cumtime': SortKey.CUMULATIVE,
    'file': SortKey.FILENAME,
    'filename': SortKey.FILENAME,
    'module': SortKey.FILENAME,
    'line': SortKey.LINE,
    'name': SortKey.NAME,
    'nfl': SortKey.NFL,
    'pcalls': SortKey.PCALLS,
    'stdname': SortKey.STDNAME,
    'time': SortKey.TIME,
    'tottime': SortKey.TIME,
}


class Stats:
    """Minimal pstats.Stats implementation."""

    def __init__(self, *args, stream=None):
        self.stream = stream or _io.StringIO()
        self.stats = {}
        self.sort_arg_dict_default = {}
        self.fcn_list = None
        self.all_callees = None
        self.files = []
        self.total_calls = 0
        self.prim_calls = 0
        self.total_tt = 0.0
        self.top_level = set()
        for arg in args:
            self._load(arg)

    def _load(self, arg):
        if hasattr(arg, 'getstats'):
            # cProfile-style profiler
            entries = arg.getstats()
            self.files.append('<profile>')
            for entry in entries:
                code = entry.code
                if callable(code):
                    key = (code.__code__.co_filename, code.__code__.co_firstlineno, code.__code__.co_name)
                elif hasattr(code, 'co_filename'):
                    key = (code.co_filename, code.co_firstlineno, code.co_name)
                else:
                    key = ('<unknown>', 0, str(code))
                nc = entry.callcount
                tt = entry.inlinetime
                ct = entry.totaltime
                callers = {}
                if entry.calls:
                    for sub in entry.calls:
                        sc = sub.code
                        if hasattr(sc, 'co_filename'):
                            sk = (sc.co_filename, sc.co_firstlineno, sc.co_name)
                        else:
                            sk = ('<unknown>', 0, str(sc))
                        callers[sk] = (sub.callcount, sub.callcount, sub.inlinetime, sub.totaltime)
                if key in self.stats:
                    old = self.stats[key]
                    self.stats[key] = (old[0]+nc, old[1]+nc, old[2]+tt, old[3]+ct, {**old[4], **callers})
                else:
                    self.stats[key] = (nc, nc, tt, ct, callers)
                self.total_calls += nc
                self.prim_calls += nc
                self.total_tt += tt
        elif isinstance(arg, str):
            import marshal as _marshal
            with open(arg, 'rb') as f:
                data = _marshal.loads(f.read())
            self.stats.update(data)
            self.files.append(arg)
        elif isinstance(arg, Stats):
            self.stats.update(arg.stats)
            self.files.extend(arg.files)
            self.total_calls += arg.total_calls
            self.prim_calls += arg.prim_calls
            self.total_tt += arg.total_tt

    def strip_dirs(self):
        newstats = {}
        for (fn, ln, nm), v in self.stats.items():
            newstats[(_os.path.basename(fn), ln, nm)] = v
        self.stats = newstats
        self.fcn_list = None
        return self

    def sort_stats(self, *keys):
        if not keys:
            keys = (SortKey.STDNAME,)
        self.fcn_list = sorted(
            self.stats.keys(),
            key=lambda x: (x[2], x[0], x[1])
        )
        return self

    def print_stats(self, *restrictions):
        if self.fcn_list is None:
            self.sort_stats()
        print(f"{'ncalls':>10} {'tottime':>8} {'percall':>8} {'cumtime':>8} {'percall':>8}  filename:lineno(function)", file=self.stream)
        for key in self.fcn_list:
            nc, pc, tt, ct, _ = self.stats[key]
            fn, ln, nm = key
            pt = tt / nc if nc else 0.0
            pc2 = ct / nc if nc else 0.0
            print(f"{nc:>10} {tt:>8.3f} {pt:>8.3f} {ct:>8.3f} {pc2:>8.3f}  {fn}:{ln}({nm})", file=self.stream)
        return self

    def get_stats_profile(self) -> StatsProfile:
        func_profiles = {}
        for (fn, ln, nm), (nc, pc, tt, ct, _) in self.stats.items():
            func_profiles[f'{fn}:{ln}({nm})'] = FunctionProfile(
                ncalls=str(nc),
                tottime=tt,
                percall_tottime=tt/nc if nc else 0.0,
                cumtime=ct,
                percall_cumtime=ct/nc if nc else 0.0,
                file_name=fn,
                line_number=ln,
            )
        return StatsProfile(total_tt=self.total_tt, func_profiles=func_profiles)

    def print_callers(self, *restrictions):
        return self

    def print_callees(self, *restrictions):
        return self

    def add(self, *others):
        for other in others:
            if isinstance(other, Stats):
                self._load(other)
            else:
                self._load(Stats(other))
        return self

    def dump_stats(self, filename):
        import marshal as _marshal
        with open(filename, 'wb') as f:
            f.write(_marshal.dumps(self.stats))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pstats2_sortkey():
    """SortKey enum exists with CALLS member; returns True."""
    return isinstance(SortKey.CALLS, SortKey) and SortKey.CALLS.value == 'calls'


def pstats2_stats_class():
    """Stats class is present; returns True."""
    return isinstance(Stats, type) and Stats.__name__ == 'Stats'


def pstats2_functionprofile():
    """FunctionProfile and StatsProfile dataclasses exist; returns True."""
    fp = FunctionProfile(ncalls='1', tottime=0.1, percall_tottime=0.1, cumtime=0.2, percall_cumtime=0.2, file_name='f.py', line_number=10)
    sp = StatsProfile(total_tt=0.1, func_profiles={})
    return (isinstance(fp, FunctionProfile) and isinstance(sp, StatsProfile))


__all__ = [
    'SortKey', 'Stats', 'FunctionProfile', 'StatsProfile',
    'pstats2_sortkey', 'pstats2_stats_class', 'pstats2_functionprofile',
]
