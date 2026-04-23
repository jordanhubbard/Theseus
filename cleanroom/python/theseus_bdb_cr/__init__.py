"""
theseus_bdb_cr — Clean-room bdb module.
No import of the standard `bdb` module.
"""

import sys as _sys
import os as _os
import fnmatch as _fnmatch
import linecache as _linecache


class BdbQuit(Exception):
    """Exception to quit the debugger."""
    pass


class Breakpoint:
    """Represents a debugger breakpoint."""

    next = 1
    bplist = {}
    bpbynumber = [None]

    def __init__(self, file, line, temporary=False, cond=None, funcname=None):
        self.file = file
        self.line = line
        self.temporary = temporary
        self.cond = cond
        self.funcname = funcname
        self.enabled = True
        self.ignore = 0
        self.hits = 0
        self.number = Breakpoint.next
        Breakpoint.next += 1
        Breakpoint.bpbynumber.append(self)
        if (file, line) in Breakpoint.bplist:
            Breakpoint.bplist[file, line].append(self)
        else:
            Breakpoint.bplist[file, line] = [self]

    def deleteMe(self):
        index = (self.file, self.line)
        Breakpoint.bpbynumber[self.number] = None
        Breakpoint.bplist[index].remove(self)
        if not Breakpoint.bplist[index]:
            del Breakpoint.bplist[index]

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def bpprint(self, out=None):
        if out is None:
            out = _sys.stdout
        if self.temporary:
            disp = 'del  '
        else:
            disp = 'keep '
        if self.enabled:
            disp += 'yes  '
        else:
            disp += 'no   '
        print(f'{self.number:3d} {disp} {self.file}:{self.line}', file=out)

    def __str__(self):
        return f'breakpoint {self.number} at {self.file}:{self.line}'


def checkfuncname(b, frame):
    if not b.funcname:
        return True
    if frame.f_code.co_name != b.funcname:
        return False
    return True


def effective(file, line, frame):
    possibles = Breakpoint.bplist.get((file, line), [])
    for b in possibles:
        if b.enabled == 0:
            continue
        if not checkfuncname(b, frame):
            continue
        if b.ignore > 0:
            b.ignore -= 1
            continue
        return b, True
    return None, False


class Bdb:
    """Base class for debuggers."""

    def __init__(self, skip=None):
        self.skip = set(skip) if skip else None
        self.breaks = {}
        self.fncache = {}
        self.frame_returning = None
        self._load_breakpoint = False
        self.quitting = False
        self.botframe = None
        self.stopframe = None
        self.returnframe = None

    def canonic(self, filename):
        if filename[0] == '<':
            return filename
        if filename in self.fncache:
            return self.fncache[filename]
        canonical = _os.path.abspath(filename)
        self.fncache[filename] = canonical
        return canonical

    def reset(self):
        import linecache as _lc
        _lc.checkcache()
        self.botframe = None
        self._set_stopinfo(None, None)

    def trace_dispatch(self, frame, event, arg):
        if self.quitting:
            return
        if event == 'line':
            return self.dispatch_line(frame)
        if event == 'call':
            return self.dispatch_call(frame, arg)
        if event == 'return':
            return self.dispatch_return(frame, arg)
        if event == 'exception':
            return self.dispatch_exception(frame, arg)
        if event == 'c_call':
            return self.trace_dispatch
        if event == 'c_exception':
            return self.trace_dispatch
        if event == 'c_return':
            return self.trace_dispatch
        return self.trace_dispatch

    def dispatch_line(self, frame):
        if self.stop_here(frame) or self.break_here(frame):
            self.user_line(frame)
            if self.quitting:
                raise BdbQuit
        return self.trace_dispatch

    def dispatch_call(self, frame, arg):
        if self.botframe is None:
            self.botframe = frame
        if not (self.stop_here(frame) or self.break_anywhere(frame)):
            return None
        self.user_call(frame, arg)
        if self.quitting:
            raise BdbQuit
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        if self.stop_here(frame) or frame == self.returnframe:
            try:
                self.frame_returning = frame
                self.user_return(frame, arg)
            finally:
                self.frame_returning = None
            if self.quitting:
                raise BdbQuit
        return self.trace_dispatch

    def dispatch_exception(self, frame, arg):
        if self.stop_here(frame):
            self.user_exception(frame, arg)
            if self.quitting:
                raise BdbQuit
        return self.trace_dispatch

    def is_skipped_module(self, module_name):
        if self.skip is None:
            return False
        for pattern in self.skip:
            if _fnmatch.fnmatch(module_name or '', pattern):
                return True
        return False

    def stop_here(self, frame):
        if self.skip and self.is_skipped_module(frame.f_globals.get('__name__')):
            return False
        if frame is self.stopframe:
            if self.stoplineno == -1:
                return False
            return frame.f_lineno >= self.stoplineno
        if not self.stopframe:
            return True
        return False

    def break_here(self, frame):
        filename = self.canonic(frame.f_code.co_filename)
        if filename not in self.breaks:
            return False
        lineno = frame.f_lineno
        if lineno not in self.breaks[filename]:
            lineno = frame.f_code.co_firstlineno
            if lineno not in self.breaks[filename]:
                return False
        b, flag = effective(filename, lineno, frame)
        if b:
            cond = b.cond
            if cond:
                try:
                    val = eval(cond, frame.f_globals, frame.f_locals)
                    if val:
                        if b.temporary:
                            self.do_clear(b.number)
                        return True
                except Exception:
                    pass
            elif b.temporary:
                self.do_clear(b.number)
            return True
        return False

    def do_clear(self, arg):
        pass

    def break_anywhere(self, frame):
        return self.canonic(frame.f_code.co_filename) in self.breaks

    def user_call(self, frame, argument_list):
        pass

    def user_line(self, frame):
        pass

    def user_return(self, frame, return_value):
        pass

    def user_exception(self, frame, exc_info):
        pass

    def _set_stopinfo(self, stopframe, returnframe, stoplineno=0):
        self.stopframe = stopframe
        self.returnframe = returnframe
        self.quitting = False
        self.stoplineno = stoplineno

    def set_until(self, frame, lineno=None):
        if lineno is None:
            lineno = frame.f_lineno + 1
        self._set_stopinfo(frame, frame, lineno)

    def set_step(self):
        self._set_stopinfo(None, None)

    def set_next(self, frame):
        self._set_stopinfo(frame, None)

    def set_return(self, frame):
        self._set_stopinfo(frame.f_back, frame)

    def set_trace(self, frame=None):
        if frame is None:
            frame = _sys._getframe().f_back
        self.reset()
        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        self.set_step()
        _sys.settrace(self.trace_dispatch)

    def set_continue(self):
        self._set_stopinfo(self.botframe, None, -1)
        if not self.breaks:
            _sys.settrace(None)
            frame = _sys._getframe().f_back
            while frame and frame is not self.botframe:
                del frame.f_trace
                frame = frame.f_back

    def set_quit(self):
        self.stopframe = self.botframe
        self.returnframe = None
        self.quitting = True
        _sys.settrace(None)

    def set_break(self, filename, lineno, temporary=False, cond=None, funcname=None):
        filename = self.canonic(filename)
        bp = Breakpoint(filename, lineno, temporary, cond, funcname)
        if filename in self.breaks:
            self.breaks[filename].append(lineno)
        else:
            self.breaks[filename] = [lineno]
        return None

    def clear_break(self, filename, lineno):
        filename = self.canonic(filename)
        if filename not in self.breaks:
            return f'There are no breakpoints in {filename}'
        if lineno not in self.breaks[filename]:
            return f'There is no breakpoint in {filename} at line {lineno}'
        blist = [bp for bp in Breakpoint.bplist.get((filename, lineno), [])
                 if bp.number > 0]
        for bp in blist:
            bp.deleteMe()
        self.breaks[filename].remove(lineno)
        if not self.breaks[filename]:
            del self.breaks[filename]
        return None

    def clear_all_breaks(self):
        if not self.breaks:
            return 'There are no breakpoints'
        for bp in Breakpoint.bpbynumber:
            if bp:
                bp.deleteMe()
        self.breaks = {}

    def get_breaks(self, filename, lineno):
        filename = self.canonic(filename)
        return (filename in self.breaks and
                lineno in self.breaks[filename] and
                Breakpoint.bplist[filename, lineno] or [])

    def get_file_breaks(self, filename):
        filename = self.canonic(filename)
        if filename in self.breaks:
            return self.breaks[filename]
        return []

    def get_all_breaks(self):
        return self.breaks

    def run(self, cmd, globals=None, locals=None):
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        if isinstance(cmd, str):
            cmd = compile(cmd, '<string>', 'exec')
        _sys.settrace(self.trace_dispatch)
        try:
            exec(cmd, globals, locals)
        except BdbQuit:
            pass
        finally:
            self.quitting = True
            _sys.settrace(None)

    def runeval(self, expr, globals=None, locals=None):
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        _sys.settrace(self.trace_dispatch)
        try:
            return eval(expr, globals, locals)
        except BdbQuit:
            pass
        finally:
            self.quitting = True
            _sys.settrace(None)

    def runcall(self, func, /, *args, **kwds):
        self.reset()
        _sys.settrace(self.trace_dispatch)
        res = None
        try:
            res = func(*args, **kwds)
        except BdbQuit:
            pass
        finally:
            self.quitting = True
            _sys.settrace(None)
        return res


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def bdb2_bdbquit():
    """BdbQuit exception class exists; returns True."""
    return issubclass(BdbQuit, Exception)


def bdb2_bdb():
    """Bdb class exists and is instantiatable; returns True."""
    db = Bdb()
    return isinstance(db, Bdb) and hasattr(db, 'set_trace')


def bdb2_breakpoint():
    """Breakpoint class exists with bpbynumber dict; returns True."""
    return (isinstance(Breakpoint, type) and
            isinstance(Breakpoint.bpbynumber, list) and
            isinstance(Breakpoint.bplist, dict))


__all__ = [
    'BdbQuit', 'Bdb', 'Breakpoint', 'checkfuncname', 'effective',
    'bdb2_bdbquit', 'bdb2_bdb', 'bdb2_breakpoint',
]
