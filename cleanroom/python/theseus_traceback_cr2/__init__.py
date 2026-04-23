"""
theseus_traceback_cr2 — Clean-room extended traceback utilities.
Do NOT import traceback or linecache.
"""

import sys
import os


class FrameSummary:
    """Represents a single frame in a stack trace."""
    
    def __init__(self, filename, lineno, name, line=None):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        self._line = line
    
    @property
    def line(self):
        if self._line is None:
            self._line = self._read_line(self.filename, self.lineno)
        return self._line
    
    def _read_line(self, filename, lineno):
        """Read a specific line from a file without using linecache."""
        if not filename or filename == '<unknown>':
            return None
        try:
            with open(filename, 'r', errors='replace') as f:
                for i, line in enumerate(f, 1):
                    if i == lineno:
                        return line.rstrip('\n').rstrip('\r')
        except (OSError, IOError):
            pass
        return None
    
    def __repr__(self):
        return (f'<FrameSummary file {self.filename}, '
                f'line {self.lineno} in {self.name}>')


class StackSummary(list):
    """A list of FrameSummary objects representing a call stack."""
    
    @classmethod
    def from_frame_list(cls, frame_list):
        result = cls()
        result.extend(frame_list)
        return result


class TracebackException:
    """
    Stores information about an exception for later formatting.
    """
    
    def __init__(self, exc_type, exc_value, exc_tb, limit=None, lookup_lines=True):
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.exc_tb = exc_tb
        self.stack = self._extract_stack_from_tb(exc_tb, limit=limit)
        
        # Handle chained exceptions
        self.__cause__ = None
        self.__context__ = None
        self.__suppress_context__ = getattr(exc_value, '__suppress_context__', False)
        
        cause = getattr(exc_value, '__cause__', None)
        if cause is not None:
            self.__cause__ = TracebackException(
                type(cause), cause, cause.__traceback__, limit=limit
            )
        
        context = getattr(exc_value, '__context__', None)
        if context is not None and context is not cause:
            self.__context__ = TracebackException(
                type(context), context, context.__traceback__, limit=limit
            )
    
    @classmethod
    def from_exception(cls, exc, limit=None, lookup_lines=True):
        """Create a TracebackException from a live exception."""
        return cls(
            type(exc),
            exc,
            exc.__traceback__,
            limit=limit,
            lookup_lines=lookup_lines
        )
    
    def _extract_stack_from_tb(self, tb, limit=None):
        """Extract FrameSummary list from a traceback object."""
        frames = []
        if tb is None:
            return StackSummary.from_frame_list(frames)
        
        # Walk the traceback chain
        tb_list = []
        current = tb
        while current is not None:
            tb_list.append(current)
            current = current.tb_next
        
        if limit is not None:
            tb_list = tb_list[-limit:]
        
        for tb_frame in tb_list:
            frame = tb_frame.tb_frame
            lineno = tb_frame.tb_lineno
            filename = frame.f_code.co_filename
            name = frame.f_code.co_name
            frames.append(FrameSummary(filename, lineno, name))
        
        return StackSummary.from_frame_list(frames)
    
    def format_exception_only(self):
        """Format the exception type and value."""
        if self.exc_type is None:
            yield 'None\n'
            return
        
        module = getattr(self.exc_type, '__module__', None)
        qualname = getattr(self.exc_type, '__qualname__', self.exc_type.__name__)
        
        if module and module not in ('__main__', 'builtins'):
            type_str = f'{module}.{qualname}'
        else:
            type_str = qualname
        
        value_str = str(self.exc_value) if self.exc_value is not None else ''
        
        if value_str:
            yield f'{type_str}: {value_str}\n'
        else:
            yield f'{type_str}\n'
    
    def format(self, chain=True):
        """Format the exception with traceback."""
        if chain:
            if self.__cause__ is not None:
                yield from self.__cause__.format(chain=chain)
                yield '\nThe above exception was the direct cause of the following exception:\n\n'
            elif (self.__context__ is not None and
                  not self.__suppress_context__):
                yield from self.__context__.format(chain=chain)
                yield '\nDuring handling of the above exception, another exception occurred:\n\n'
        
        if self.stack:
            yield 'Traceback (most recent call last):\n'
            yield from format_list(self.stack)
        
        yield from self.format_exception_only()
    
    def __str__(self):
        return ''.join(self.format())


def format_list(extracted_list):
    """
    Format a list of FrameSummary objects into a list of strings.
    Each string is of the form:
        'File "filename", line N, in name\\n  code\\n'
    """
    result = []
    for frame in extracted_list:
        if isinstance(frame, FrameSummary):
            filename = frame.filename or '<unknown>'
            lineno = frame.lineno
            name = frame.name
            line = frame.line
        elif isinstance(frame, tuple):
            # Support legacy (filename, lineno, name, line) tuples
            filename, lineno, name = frame[0], frame[1], frame[2]
            line = frame[3] if len(frame) > 3 else None
        else:
            continue
        
        row = f'  File "{filename}", line {lineno}, in {name}\n'
        if line:
            row += f'    {line.strip()}\n'
        result.append(row)
    return result


def extract_stack(f=None, limit=None):
    """
    Extract the stack frames from the current call stack.
    Returns a StackSummary (which is a list subclass).
    """
    if f is None:
        try:
            f = sys._getframe(1)
        except AttributeError:
            return StackSummary()
    
    frames = []
    current = f
    while current is not None:
        filename = current.f_code.co_filename
        lineno = current.f_lineno
        name = current.f_code.co_name
        frames.append(FrameSummary(filename, lineno, name))
        current = current.f_back
    
    # Reverse so most recent call is last
    frames.reverse()
    
    if limit is not None:
        frames = frames[-limit:]
    
    return StackSummary.from_frame_list(frames)


def format_exc(exc=None, limit=None, chain=True):
    """
    Format an exception's traceback as a string.
    If exc is None, uses the current exception from sys.exc_info().
    """
    if exc is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is None:
            return 'NoneType: None\n'
        te = TracebackException(exc_type, exc_value, exc_tb, limit=limit)
    else:
        te = TracebackException.from_exception(exc, limit=limit)
    
    return ''.join(te.format(chain=chain))


# ── Invariant test functions ──────────────────────────────────────────────────

def traceback2_extract_stack():
    """Invariant: isinstance(extract_stack(), list) returns True."""
    result = extract_stack()
    return isinstance(result, list)


def traceback2_format_list():
    """Invariant: format_list([]) == []."""
    return format_list([])


def traceback2_tb_exception():
    """Invariant: TracebackException.from_exception(ValueError('test')).exc_type == ValueError."""
    te = TracebackException.from_exception(ValueError('test'))
    return te.exc_type == ValueError


__all__ = [
    'TracebackException',
    'FrameSummary',
    'StackSummary',
    'format_list',
    'extract_stack',
    'format_exc',
    'traceback2_extract_stack',
    'traceback2_format_list',
    'traceback2_tb_exception',
]