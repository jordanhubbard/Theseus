"""
theseus_traceback_cr — Clean-room traceback module.
No import of the standard `traceback` module.
"""

import sys as _sys
import linecache as _linecache
import io as _io


class FrameSummary:
    """Represents a single frame in a traceback."""

    def __init__(self, filename, lineno, name, *, lookup_line=True, locals=None, line=None):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        if line is None and lookup_line:
            self.line = _linecache.getline(filename, lineno, None).strip()
        else:
            self.line = line
        if locals is not None:
            self.locals = {k: repr(v) for k, v in locals.items()}
        else:
            self.locals = None

    def __eq__(self, other):
        if isinstance(other, FrameSummary):
            return (self.filename == other.filename and
                    self.lineno == other.lineno and
                    self.name == other.name and
                    self.locals == other.locals)
        return NotImplemented

    def __repr__(self):
        return '<FrameSummary file %s, line %d in %s>' % (self.filename, self.lineno, self.name)

    def __iter__(self):
        return iter([self.filename, self.lineno, self.name, self.line])

    def __getitem__(self, idx):
        return [self.filename, self.lineno, self.name, self.line][idx]

    def __len__(self):
        return 4


class StackSummary(list):
    """A list of FrameSummary instances."""

    @classmethod
    def extract(cls, frame_gen, *, limit=None, lookup_lines=True, capture_locals=False):
        result = []
        for f, lineno in frame_gen:
            co = f.f_code
            filename = co.co_filename
            name = co.co_name
            locals = f.f_locals if capture_locals else None
            result.append(FrameSummary(filename, lineno, name,
                                       lookup_line=lookup_lines, locals=locals))
            if limit is not None and len(result) >= limit:
                break
        return cls(result)

    @classmethod
    def from_list(cls, a_list):
        result = []
        for frame in a_list:
            if isinstance(frame, FrameSummary):
                result.append(frame)
            else:
                filename, lineno, name, line = frame
                result.append(FrameSummary(filename, lineno, name, line=line, lookup_line=False))
        return cls(result)

    def format(self):
        rows = []
        for frame in self:
            rows.append('  File "%s", line %d, in %s\n' % (frame.filename, frame.lineno, frame.name))
            if frame.line:
                rows.append('    %s\n' % frame.line)
            if frame.locals:
                for k, v in sorted(frame.locals.items()):
                    rows.append('    %s = %s\n' % (k, v))
        return rows

    def format_frame_summary(self, frame_summary):
        row = []
        row.append('  File "%s", line %d, in %s\n' % (
            frame_summary.filename, frame_summary.lineno, frame_summary.name))
        if frame_summary.line:
            row.append('    %s\n' % frame_summary.line)
        return ''.join(row)


class TracebackException:
    """An exception and its traceback."""

    def __init__(self, exc_type, exc_value, exc_tb, *, limit=None,
                 lookup_lines=True, capture_locals=False, compact=False,
                 _seen=None):
        if _seen is None:
            _seen = set()
        _seen.add(id(exc_value))

        if exc_value and exc_value.__cause__ is not None and id(exc_value.__cause__) not in _seen:
            cause = TracebackException(
                type(exc_value.__cause__),
                exc_value.__cause__,
                exc_value.__cause__.__traceback__,
                limit=limit,
                lookup_lines=lookup_lines,
                capture_locals=capture_locals,
                _seen=_seen,
            )
        else:
            cause = None

        if exc_value and exc_value.__context__ is not None and id(exc_value.__context__) not in _seen and not exc_value.__suppress_context__:
            context = TracebackException(
                type(exc_value.__context__),
                exc_value.__context__,
                exc_value.__context__.__traceback__,
                limit=limit,
                lookup_lines=lookup_lines,
                capture_locals=capture_locals,
                _seen=_seen,
            )
        else:
            context = None

        self.__cause__ = cause
        self.__context__ = context
        self.__suppress_context__ = (exc_value.__suppress_context__
                                     if exc_value else False)
        if exc_tb is not None:
            self.stack = StackSummary.extract(
                walk_tb(exc_tb),
                limit=limit,
                lookup_lines=lookup_lines,
                capture_locals=capture_locals,
            )
        else:
            self.stack = StackSummary()

        self.exc_type = exc_type
        self._str = _safe_string(exc_value, 'exception')
        self.filename = None
        self.lineno = None
        self.text = None
        self.offset = None
        self.msg = None
        if exc_type and issubclass(exc_type, SyntaxError):
            try:
                self.filename = exc_value.filename
                self.lineno = str(exc_value.lineno)
                self.text = exc_value.text
                self.offset = exc_value.offset
                self.msg = exc_value.msg
            except Exception:
                pass
        self.__notes__ = getattr(exc_value, '__notes__', None)

    @classmethod
    def from_exception(cls, exc, *args, **kwargs):
        return cls(type(exc), exc, exc.__traceback__, *args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, TracebackException):
            return self.__dict__ == other.__dict__
        return NotImplemented

    @property
    def _str(self):
        return self.__str_value

    @_str.setter
    def _str(self, v):
        self.__str_value = v

    def format_exception_only(self):
        yield from self._format_exception_only()

    def _format_exception_only(self):
        if self.exc_type is None:
            yield _format_final_exc_line(None, self._str)
            return

        stype = self.exc_type.__qualname__
        smod = self.exc_type.__module__
        if smod not in ('__main__', 'builtins'):
            stype = smod + '.' + stype

        if not issubclass(self.exc_type, SyntaxError):
            yield _format_final_exc_line(stype, self._str)
        else:
            filename = self.filename or '<unknown>'
            lineno = self.lineno or '?'
            yield '  File "%s", line %s\n' % (filename, lineno)
            if self.text is not None:
                yield '    %s\n' % self.text.strip()
            yield _format_final_exc_line(stype, self.msg)

    def format(self, *, chain=True):
        if chain:
            if self.__cause__ is not None:
                yield from self.__cause__.format(chain=chain)
                yield _cause_message
            elif self.__context__ is not None and not self.__suppress_context__:
                yield from self.__context__.format(chain=chain)
                yield _context_message
        if self.exc_type is not None:
            yield 'Traceback (most recent call last):\n'
        yield from self.stack.format()
        yield from self.format_exception_only()
        if self.__notes__ is not None:
            for note in self.__notes__:
                yield from [l + '\n' for l in ('Note: ' + note).splitlines()]


_cause_message = ('\nThe above exception was the direct cause of the following exception:\n\n')
_context_message = ('\nDuring handling of the above exception, another exception occurred:\n\n')


def _safe_string(value, what, func=str):
    try:
        return func(value)
    except Exception:
        return '<%s %s>' % (what, func.__name__)


def _format_final_exc_line(etype, value):
    valuestr = _safe_string(value, 'exception')
    if value is None or not valuestr:
        line = '%s\n' % etype
    elif etype is None:
        line = '%s\n' % valuestr
    else:
        line = '%s: %s\n' % (etype, valuestr)
    return line


def walk_stack(f):
    """Walk a stack yielding (frame, lineno) tuples."""
    if f is None:
        f = _sys._getframe().f_back
    while f is not None:
        yield f, f.f_lineno
        f = f.f_back


def walk_tb(tb):
    """Walk a traceback yielding (frame, lineno) tuples."""
    while tb is not None:
        yield tb.tb_frame, tb.tb_lineno
        tb = tb.tb_next


def extract_stack(f=None, limit=None):
    """Extract the raw traceback from the current stack frame."""
    stack = StackSummary.extract(walk_stack(f), limit=limit)
    stack.reverse()
    return stack


def extract_tb(tb, limit=None):
    """Extract the raw traceback from a traceback object."""
    return StackSummary.extract(walk_tb(tb), limit=limit)


def format_list(extracted_list):
    """Format a list of FrameSummary instances into strings."""
    return StackSummary.from_list(extracted_list).format()


def format_exception_only(exc, value=_sys.exc_info):
    """Format the exception part of a traceback."""
    if isinstance(exc, BaseException):
        return list(TracebackException(type(exc), exc, None).format_exception_only())
    return list(TracebackException(exc, value, None).format_exception_only())


def format_exception(exc, value=_sys.exc_info, tb=_sys.exc_info, limit=None, chain=True):
    """Format a stack trace and the exception information."""
    if isinstance(exc, BaseException):
        return list(TracebackException(
            type(exc), exc, exc.__traceback__, limit=limit
        ).format(chain=chain))
    return list(TracebackException(exc, value, tb, limit=limit).format(chain=chain))


def format_tb(tb, limit=None):
    """Format the traceback."""
    return format_list(extract_tb(tb, limit=limit))


def format_stack(f=None, limit=None):
    """Format the current stack."""
    return format_list(extract_stack(f, limit=limit))


def format_exc(limit=None, chain=True):
    """Format the current exception as a string."""
    return ''.join(format_exception(*_sys.exc_info(), limit=limit, chain=chain))


def print_list(extracted_list, file=None):
    if file is None:
        file = _sys.stderr
    for line in format_list(extracted_list):
        print(line, file=file, end='')


def print_exception(exc, value=_sys.exc_info, tb=_sys.exc_info, limit=None, file=None, chain=True):
    if file is None:
        file = _sys.stderr
    for line in format_exception(exc, value, tb, limit=limit, chain=chain):
        print(line, file=file, end='')


def print_exc(limit=None, file=None, chain=True):
    print_exception(*_sys.exc_info(), limit=limit, file=file, chain=chain)


def print_tb(tb, limit=None, file=None):
    if file is None:
        file = _sys.stderr
    print_list(extract_tb(tb, limit=limit), file=file)


def print_stack(f=None, limit=None, file=None):
    if file is None:
        file = _sys.stderr
    print_list(extract_stack(f, limit=limit), file=file)


def print_last(limit=None, file=None, chain=True):
    if not hasattr(_sys, 'last_type'):
        raise ValueError('no last exception')
    print_exception(_sys.last_type, _sys.last_value, _sys.last_traceback, limit=limit, file=file, chain=chain)


def clear_frames(tb):
    """Clear all references to local variables in the frames of a traceback."""
    while tb is not None:
        try:
            tb.tb_frame.clear()
        except RuntimeError:
            pass
        tb = tb.tb_next


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def traceback2_format_exc():
    """format_exc_test captures current exception as string; returns True."""
    try:
        raise ValueError('test error')
    except ValueError:
        s = format_exc()
    return isinstance(s, str) and 'ValueError' in s


def traceback2_extract_stack():
    """extract_stack_test returns list of FrameSummary; returns True."""
    stack = extract_stack()
    return isinstance(stack, list) and len(stack) > 0


def traceback2_format_exception():
    """format_exception produces list of strings; returns True."""
    try:
        raise RuntimeError('test')
    except RuntimeError as e:
        result = format_exception(e)
    return isinstance(result, list) and any('RuntimeError' in s for s in result)


__all__ = [
    'FrameSummary', 'StackSummary', 'TracebackException',
    'walk_stack', 'walk_tb',
    'extract_stack', 'extract_tb',
    'format_list', 'format_exception_only', 'format_exception',
    'format_tb', 'format_stack', 'format_exc',
    'print_list', 'print_exception', 'print_exc',
    'print_tb', 'print_stack', 'print_last',
    'clear_frames',
    'traceback2_format_exc', 'traceback2_extract_stack', 'traceback2_format_exception',
]
