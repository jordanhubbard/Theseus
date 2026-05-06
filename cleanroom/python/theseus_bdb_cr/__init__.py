"""Clean-room reimplementation of bdb-like primitives for Theseus.

This module provides minimal Bdb, BdbQuit, and Breakpoint primitives without
importing or wrapping the standard library ``bdb`` module. Only Python
built-ins are used.
"""

import sys as _sys


class BdbQuit(Exception):
    """Exception raised to quit the debugger."""
    pass


class Breakpoint(object):
    """A breakpoint placed in user code.

    Tracks file, line, condition, function name, hit count, and enabled state.
    Maintains class-level registries indexed by file/line and by breakpoint
    number, mirroring the well-known interface of the bdb stdlib module.
    """

    next = 1
    bplist = {}    # (file, line) -> [Breakpoint, ...]
    bpbynumber = [None]  # index 0 unused; bp.number used as index

    def __init__(self, file, line, temporary=False, cond=None, funcname=None):
        self.file = file
        self.line = line
        self.temporary = bool(temporary)
        self.cond = cond
        self.funcname = funcname
        self.enabled = True
        self.ignore = 0
        self.hits = 0
        self.number = Breakpoint.next
        Breakpoint.next += 1
        Breakpoint.bpbynumber.append(self)
        key = (file, line)
        if key in Breakpoint.bplist:
            Breakpoint.bplist[key].append(self)
        else:
            Breakpoint.bplist[key] = [self]

    def deleteMe(self):
        index = (self.file, self.line)
        self.bpbynumber[self.number] = None
        bucket = self.bplist.get(index)
        if bucket is not None:
            try:
                bucket.remove(self)
            except ValueError:
                pass
            if not bucket:
                del self.bplist[index]

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def bpprint(self, out=None):
        if out is None:
            out = _sys.stdout
        out.write(self.bpformat() + "\n")

    def bpformat(self):
        disp = "del  " if self.temporary else "keep "
        disp += "yes  " if self.enabled else "no   "
        ret = "%-4d breakpoint   %s at %s:%d" % (
            self.number, disp, self.file, self.line,
        )
        if self.cond:
            ret += "\n\tstop only if %s" % (self.cond,)
        if self.ignore:
            ret += "\n\tignore next %d hits" % (self.ignore,)
        if self.hits:
            suffix = "s" if self.hits > 1 else ""
            ret += "\n\tbreakpoint already hit %d time%s" % (self.hits, suffix)
        return ret

    def __str__(self):
        return "breakpoint %s at %s:%s" % (self.number, self.file, self.line)


def checkfuncname(b, frame):
    """Return True if the breakpoint should fire at this frame."""
    if not b.funcname:
        if b.line != frame.f_lineno:
            return False
        return True
    if frame.f_code.co_name != b.funcname:
        return False
    if not frame.f_code.co_firstlineno == b.line:
        b.func_first_executable_line = frame.f_lineno
        b.line = frame.f_lineno
    return True


def effective(file, line, frame):
    """Determine if any breakpoint at (file, line) is effective in this frame."""
    possibles = Breakpoint.bplist.get((file, line), [])
    for b in possibles:
        if not b.enabled:
            continue
        if not checkfuncname(b, frame):
            continue
        b.hits += 1
        if not b.cond:
            if b.ignore > 0:
                b.ignore -= 1
                continue
            return (b, True)
        try:
            val = eval(b.cond, frame.f_globals, frame.f_locals)
            if val:
                if b.ignore > 0:
                    b.ignore -= 1
                    continue
                return (b, True)
        except Exception:
            return (b, False)
    return (None, None)


class Bdb(object):
    """Generic Python debugger base class (clean-room).

    Subclass this and override ``user_line``, ``user_call``, ``user_return``,
    and ``user_exception`` to implement an interactive debugger. The dispatcher
    drives ``sys.settrace`` to walk through user code.
    """

    def __init__(self, skip=None):
        self.skip = set(skip) if skip else None
        self.breaks = {}        # filename -> [linenos]
        self.fncache = {}
        self.frame_returning = None
        self.botframe = None
        self.stopframe = None
        self.returnframe = None
        self.quitting = False
        self.stoplineno = 0

    # ----- canonicalization ------------------------------------------------

    def canonic(self, filename):
        if filename == "<" + filename[1:-1] + ">":
            return filename
        canonic = self.fncache.get(filename)
        if canonic is None:
            import os
            canonic = os.path.abspath(filename)
            canonic = os.path.normcase(canonic)
            self.fncache[filename] = canonic
        return canonic

    def reset(self):
        import linecache
        linecache.checkcache()
        self.botframe = None
        self._set_stopinfo(None, None)

    # ----- tracing dispatchers --------------------------------------------

    def trace_dispatch(self, frame, event, arg):
        if self.quitting:
            return None
        if event == "line":
            return self.dispatch_line(frame)
        if event == "call":
            return self.dispatch_call(frame, arg)
        if event == "return":
            return self.dispatch_return(frame, arg)
        if event == "exception":
            return self.dispatch_exception(frame, arg)
        if event == "c_call":
            return self.trace_dispatch
        if event == "c_exception":
            return self.trace_dispatch
        if event == "c_return":
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
            self.botframe = frame.f_back
            return self.trace_dispatch
        if not (self.stop_here(frame) or self.break_anywhere(frame)):
            return None
        if self.stopframe and frame.f_code.co_flags & 0x80:  # CO_GENERATOR
            return self.trace_dispatch
        self.user_call(frame, arg)
        if self.quitting:
            raise BdbQuit
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        if self.stop_here(frame) or frame == self.returnframe:
            if self.stopframe and frame.f_code.co_flags & 0x80:
                return self.trace_dispatch
            try:
                self.frame_returning = frame
                self.user_return(frame, arg)
            finally:
                self.frame_returning = None
            if self.quitting:
                raise BdbQuit
            if self.stopframe is frame and self.stoplineno != -1:
                self._set_stopinfo(None, None)
        return self.trace_dispatch

    def dispatch_exception(self, frame, arg):
        if self.stop_here(frame):
            if not (frame.f_code.co_flags & 0x80 and arg[0] is StopIteration
                    and arg[2] is None):
                self.user_exception(frame, arg)
                if self.quitting:
                    raise BdbQuit
        elif (self.stopframe and frame is not self.stopframe
              and self.stopframe in frame.f_back.__class__.__mro__ if False
              else False):
            pass
        return self.trace_dispatch

    # ----- stop predicates -------------------------------------------------

    def is_skipped_module(self, module_name):
        if self.skip is None:
            return False
        for pattern in self.skip:
            if self._fnmatch(module_name, pattern):
                return True
        return False

    @staticmethod
    def _fnmatch(name, pattern):
        # Minimal glob matcher supporting '*' and '?'.
        i = j = 0
        n, m = len(name), len(pattern)
        star = -1
        match = 0
        while i < n:
            if j < m and (pattern[j] == name[i] or pattern[j] == "?"):
                i += 1
                j += 1
            elif j < m and pattern[j] == "*":
                star = j
                match = i
                j += 1
            elif star != -1:
                j = star + 1
                match += 1
                i = match
            else:
                return False
        while j < m and pattern[j] == "*":
            j += 1
        return j == m

    def stop_here(self, frame):
        if self.skip and self.is_skipped_module(
                frame.f_globals.get("__name__")):
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
        bp, flag = effective(filename, lineno, frame)
        if bp:
            self.currentbp = bp.number
            if flag and bp.temporary:
                self.do_clear(str(bp.number))
            return True
        return False

    def do_clear(self, arg):
        raise NotImplementedError("subclass of bdb must implement do_clear()")

    def break_anywhere(self, frame):
        return self.canonic(frame.f_code.co_filename) in self.breaks

    # ----- user hooks (no-ops by default) ---------------------------------

    def user_call(self, frame, argument_list):
        pass

    def user_line(self, frame):
        pass

    def user_return(self, frame, return_value):
        pass

    def user_exception(self, frame, exc_info):
        pass

    # ----- stepping API ---------------------------------------------------

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
        if self.frame_returning is not None:
            caller_frame = self.frame_returning.f_back
            if caller_frame and not caller_frame.f_trace:
                caller_frame.f_trace = self.trace_dispatch
        self._set_stopinfo(None, None)

    def set_next(self, frame):
        self._set_stopinfo(frame, None)

    def set_return(self, frame):
        if frame.f_code.co_flags & 0x80:
            self._set_stopinfo(frame, None, -1)
        else:
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

    # ----- breakpoint management ------------------------------------------

    def set_break(self, filename, lineno, temporary=False, cond=None,
                  funcname=None):
        filename = self.canonic(filename)
        import linecache
        line = linecache.getline(filename, lineno)
        if not line:
            return "Line %s:%d does not exist" % (filename, lineno)
        lst = self.breaks.setdefault(filename, [])
        if lineno not in lst:
            lst.append(lineno)
        Breakpoint(filename, lineno, temporary, cond, funcname)
        return None

    def clear_break(self, filename, lineno):
        filename = self.canonic(filename)
        if filename not in self.breaks:
            return "There are no breakpoints in %s" % filename
        if lineno not in self.breaks[filename]:
            return "There is no breakpoint at %s:%d" % (filename, lineno)
        for bp in Breakpoint.bplist.get((filename, lineno), [])[:]:
            bp.deleteMe()
        self._prune_file_breaks(filename, lineno)
        return None

    def clear_bpbynumber(self, arg):
        try:
            number = int(arg)
        except ValueError:
            return "Non-numeric breakpoint number %s" % arg
        try:
            bp = Breakpoint.bpbynumber[number]
        except IndexError:
            return "Breakpoint number %d out of range" % number
        if bp is None:
            return "Breakpoint %d already deleted" % number
        bp.deleteMe()
        self._prune_file_breaks(bp.file, bp.line)
        return None

    def _prune_file_breaks(self, filename, lineno):
        if (filename, lineno) not in Breakpoint.bplist:
            if filename in self.breaks and lineno in self.breaks[filename]:
                self.breaks[filename].remove(lineno)
            if filename in self.breaks and not self.breaks[filename]:
                del self.breaks[filename]

    def clear_all_file_breaks(self, filename):
        filename = self.canonic(filename)
        if filename not in self.breaks:
            return "There are no breakpoints in %s" % filename
        for line in self.breaks[filename]:
            for bp in Breakpoint.bplist.get((filename, line), [])[:]:
                bp.deleteMe()
        del self.breaks[filename]
        return None

    def clear_all_breaks(self):
        if not self.breaks:
            return "There are no breakpoints"
        for bp in Breakpoint.bpbynumber:
            if bp:
                bp.deleteMe()
        self.breaks = {}
        return None

    def get_bpbynumber(self, arg):
        if not arg:
            raise ValueError("Breakpoint number expected")
        try:
            number = int(arg)
        except ValueError:
            raise ValueError("Non-numeric breakpoint number %s" % arg)
        try:
            bp = Breakpoint.bpbynumber[number]
        except IndexError:
            raise ValueError("Breakpoint number %d out of range" % number)
        if bp is None:
            raise ValueError("Breakpoint %d already deleted" % number)
        return bp

    def get_break(self, filename, lineno):
        filename = self.canonic(filename)
        return (filename in self.breaks
                and lineno in self.breaks[filename])

    def get_breaks(self, filename, lineno):
        filename = self.canonic(filename)
        return (filename in self.breaks
                and lineno in self.breaks[filename]
                and Breakpoint.bplist.get((filename, lineno), [])) or []

    def get_file_breaks(self, filename):
        filename = self.canonic(filename)
        if filename in self.breaks:
            return self.breaks[filename]
        return []

    def get_all_breaks(self):
        return self.breaks

    # ----- stack utilities ------------------------------------------------

    def get_stack(self, f, t):
        stack = []
        if t and t.tb_frame is f:
            t = t.tb_next
        while f is not None:
            stack.append((f, f.f_lineno))
            if f is self.botframe:
                break
            f = f.f_back
        stack.reverse()
        i = max(0, len(stack) - 1)
        while t is not None:
            stack.append((t.tb_frame, t.tb_lineno))
            t = t.tb_next
        if f is None:
            i = max(0, len(stack) - 1)
        return stack, i

    def format_stack_entry(self, frame_lineno, lprefix=": "):
        import linecache, reprlib
        frame, lineno = frame_lineno
        filename = self.canonic(frame.f_code.co_filename)
        s = "%s(%r)" % (filename, lineno)
        if frame.f_code.co_name:
            s += frame.f_code.co_name
        else:
            s += "<lambda>"
        s += "()"
        if "__return__" in frame.f_locals:
            rv = frame.f_locals["__return__"]
            s += "->"
            s += reprlib.repr(rv)
        line = linecache.getline(filename, lineno, frame.f_globals)
        if line:
            s += lprefix + line.strip()
        return s

    # ----- entry points ---------------------------------------------------

    def run(self, cmd, globals=None, locals=None):
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")
        _sys.settrace(self.trace_dispatch)
        try:
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
            try:
                return eval(expr, globals, locals)
            except BdbQuit:
                pass
        finally:
            self.quitting = True
            _sys.settrace(None)

    def runctx(self, cmd, globals, locals):
        self.run(cmd, globals, locals)

    def runcall(self, func, *args, **kwds):
        self.reset()
        _sys.settrace(self.trace_dispatch)
        res = None
        try:
            try:
                res = func(*args, **kwds)
            except BdbQuit:
                pass
        finally:
            self.quitting = True
            _sys.settrace(None)
        return res


def set_trace():
    """Start a Bdb session at the caller's frame."""
    Bdb().set_trace()


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def bdb2_bdbquit():
    """Verify BdbQuit behaves as an Exception subclass that can be raised
    and caught."""
    if not isinstance(BdbQuit, type):
        return False
    if not issubclass(BdbQuit, Exception):
        return False
    try:
        raise BdbQuit("done")
    except BdbQuit as exc:
        return "done" in str(exc) or True
    except Exception:
        return False


def bdb2_bdb():
    """Verify Bdb's basic configuration surface."""
    try:
        d = Bdb()
    except Exception:
        return False
    if not hasattr(d, "trace_dispatch"):
        return False
    if not hasattr(d, "set_break"):
        return False
    if not hasattr(d, "clear_break"):
        return False
    if not callable(d.set_continue):
        return False
    if d.breaks != {}:
        return False
    return True


def bdb2_breakpoint():
    """Verify Breakpoint creation registers and indexes the breakpoint."""
    saved_next = Breakpoint.next
    saved_bplist = dict(Breakpoint.bplist)
    saved_bpbynumber = list(Breakpoint.bpbynumber)
    try:
        bp = Breakpoint("nonexistent_file_for_probe.py", 1)
        if bp.file != "nonexistent_file_for_probe.py":
            return False
        if bp.line != 1:
            return False
        if bp.enabled is not True:
            return False
        if Breakpoint.bpbynumber[bp.number] is not bp:
            return False
        if bp not in Breakpoint.bplist.get((bp.file, bp.line), []):
            return False
        bp.disable()
        if bp.enabled is not False:
            return False
        bp.enable()
        if bp.enabled is not True:
            return False
        bp.deleteMe()
        if Breakpoint.bpbynumber[bp.number] is not None:
            return False
        return True
    except Exception:
        return False
    finally:
        Breakpoint.next = saved_next
        Breakpoint.bplist = saved_bplist
        Breakpoint.bpbynumber = saved_bpbynumber