# theseus_logging_cr2 - Clean-room logging utilities
# Do NOT import logging or any third-party library

DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

_LEVEL_NAMES = {
    DEBUG: 'DEBUG',
    INFO: 'INFO',
    WARNING: 'WARNING',
    ERROR: 'ERROR',
    CRITICAL: 'CRITICAL',
}

_NAME_TO_LEVEL = {v: k for k, v in _LEVEL_NAMES.items()}


def getLevelName(level):
    """Return string name for numeric level (e.g. 20 -> 'INFO')."""
    if isinstance(level, int):
        return _LEVEL_NAMES.get(level, 'Level %d' % level)
    elif isinstance(level, str):
        return _NAME_TO_LEVEL.get(level, level)
    return 'Unknown'


class LogRecord:
    """Structured log record."""

    def __init__(self, name, level, pathname, lineno, msg, args, exc_info):
        self.name = name
        self.levelno = level
        self.levelname = getLevelName(level)
        self.pathname = pathname
        self.lineno = lineno
        self.msg = msg
        self.args = args
        self.exc_info = exc_info

        # Compute the message
        if args:
            try:
                self.message = msg % tuple(args)
            except (TypeError, ValueError):
                self.message = str(msg)
        else:
            self.message = str(msg)

    def getMessage(self):
        """Return the formatted message."""
        return self.message


class Formatter:
    """Format log records using % style format strings."""

    def __init__(self, fmt=None):
        if fmt is None:
            self._fmt = '%(levelname)s:%(name)s:%(message)s'
        else:
            self._fmt = fmt

    def format(self, record):
        """Format the specified record as text."""
        # Ensure message is set
        record.message = record.getMessage()

        # Build a dict of available attributes
        record_dict = {
            'name': record.name,
            'levelno': record.levelno,
            'levelname': record.levelname,
            'pathname': record.pathname,
            'lineno': record.lineno,
            'msg': record.msg,
            'args': record.args,
            'exc_info': record.exc_info,
            'message': record.message,
        }

        try:
            result = self._fmt % record_dict
        except (KeyError, TypeError, ValueError):
            result = record.message

        return result


# Zero-arg invariant functions

def logging2_formatter():
    """Formatter('%(message)s').format(LogRecord('root', 20, '', 0, 'hello', [], None)) == 'hello'"""
    fmt = Formatter('%(message)s')
    rec = LogRecord('root', 20, '', 0, 'hello', [], None)
    return fmt.format(rec)


def logging2_record_level():
    """LogRecord('root', 20, '', 0, 'msg', [], None).levelname == 'INFO'"""
    rec = LogRecord('root', 20, '', 0, 'msg', [], None)
    return rec.levelname


def logging2_level_name():
    """getLevelName(20) == 'INFO'"""
    return getLevelName(20)