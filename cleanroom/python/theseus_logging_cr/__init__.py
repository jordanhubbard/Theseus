"""
theseus_logging_cr - Clean-room logging framework implementation.
Do NOT import the standard logging module.
"""

import time

# Level constants
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


class LogRecord:
    """Represents a single log event."""

    def __init__(self, name, level, message):
        self.name = name
        self.level = level
        self.levelname = _LEVEL_NAMES.get(level, str(level))
        self.message = message
        self.timestamp = time.time()

    def __repr__(self):
        return (
            f"LogRecord(name={self.name!r}, level={self.level}, "
            f"levelname={self.levelname!r}, message={self.message!r}, "
            f"timestamp={self.timestamp})"
        )


class Handler:
    """Base handler that receives log records."""

    def __init__(self, level=DEBUG):
        self.level = level
        self._records = []

    def emit(self, record):
        """Process a log record. Override in subclasses."""
        self._records.append(record)

    def set_level(self, level):
        self.level = level

    def handle(self, record):
        """Conditionally emit the record if its level >= handler level."""
        if record.level >= self.level:
            self.emit(record)


class Logger:
    """Logger with debug/info/warning/error/critical methods."""

    def __init__(self, name):
        self.name = name
        self.level = DEBUG
        self.handlers = []

    def set_level(self, level):
        self.level = level

    def add_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)

    def _log(self, level, message):
        if level < self.level:
            return
        record = LogRecord(name=self.name, level=level, message=message)
        for handler in self.handlers:
            handler.handle(record)

    def debug(self, message):
        self._log(DEBUG, message)

    def info(self, message):
        self._log(INFO, message)

    def warning(self, message):
        self._log(WARNING, message)

    def error(self, message):
        self._log(ERROR, message)

    def critical(self, message):
        self._log(CRITICAL, message)


def logging_format_message(record):
    """Format a LogRecord into a human-readable string."""
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.timestamp))
    return f"[{ts}] {record.levelname} {record.name}: {record.message}"


# --- Invariant functions ---

def logging_level_constants():
    """Returns True if level constants are correctly defined."""
    return DEBUG == 10 and INFO == 20 and WARNING == 30 and ERROR == 40 and CRITICAL == 50


def logging_handler_receives():
    """
    Creates a logger, attaches a handler, logs a message,
    and returns the message from the received record.
    """
    handler = Handler(level=DEBUG)
    logger = Logger("test")
    logger.add_handler(handler)
    logger.info("test message")
    if handler._records:
        return handler._records[-1].message
    return None


def logging_logger_name():
    """Returns the name of a logger created with 'myapp'."""
    logger = Logger("myapp")
    return logger.name


__all__ = [
    'Logger',
    'Handler',
    'LogRecord',
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL',
    'logging_level_constants',
    'logging_handler_receives',
    'logging_logger_name',
    'logging_format_message',
]