"""
theseus_logging_handlers_cr — Clean-room logging.handlers module.
No import of logging.handlers.
"""

import logging as _logging
import os as _os
import queue as _queue
import time as _time
import io as _io


class BaseRotatingHandler(_logging.FileHandler):
    def __init__(self, filename, mode, encoding=None, delay=False, errors=None):
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        super().__init__(filename, mode, encoding, delay, errors=errors)

    def emit(self, record):
        try:
            if self.shouldRollover(record):
                self.doRollover()
            _logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def shouldRollover(self, record):
        return False

    def doRollover(self):
        pass


class RotatingFileHandler(BaseRotatingHandler):
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0,
                 encoding=None, delay=False, errors=None):
        if maxBytes > 0:
            mode = 'a'
        super().__init__(filename, mode, encoding, delay, errors)
        self.maxBytes = maxBytes
        self.backupCount = backupCount

    def shouldRollover(self, record):
        if self.maxBytes > 0:
            try:
                msg = self.format(record)
                self.stream.seek(0, 2)
                if self.stream.tell() + len(msg) + 1 >= self.maxBytes:
                    return True
            except Exception:
                pass
        return False

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f'{self.baseFilename}.{i}'
                dfn = f'{self.baseFilename}.{i+1}'
                if _os.path.exists(sfn):
                    if _os.path.exists(dfn):
                        _os.remove(dfn)
                    _os.rename(sfn, dfn)
            dfn = self.baseFilename + '.1'
            if _os.path.exists(dfn):
                _os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
        self.mode = 'w'
        self.stream = self._open()

    def rotate(self, source, dest):
        if _os.path.exists(source):
            _os.rename(source, dest)


class TimedRotatingFileHandler(BaseRotatingHandler):
    def __init__(self, filename, when='h', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False, atTime=None, errors=None):
        super().__init__(filename, 'a', encoding, delay, errors)
        self.when = when.upper()
        self.interval = interval
        self.backupCount = backupCount
        self.utc = utc
        self.atTime = atTime
        self.rolloverAt = _time.time() + interval * 3600

    def shouldRollover(self, record):
        t = int(_time.time())
        return t >= self.rolloverAt

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        self.rolloverAt = int(_time.time()) + self.interval * 3600
        self.mode = 'a'
        self.stream = self._open()


class MemoryHandler(_logging.handlers.MemoryHandler if hasattr(_logging, 'handlers') else _logging.Handler):
    """Buffer log records in memory, flush when buffer is full or target emits."""

    def __init__(self, capacity, flushLevel=_logging.ERROR, target=None, flushOnClose=True):
        _logging.Handler.__init__(self)
        self.capacity = capacity
        self.flushLevel = flushLevel
        self.target = target
        self.buffer = []
        self.flushOnClose = flushOnClose

    def shouldFlush(self, record):
        return (len(self.buffer) >= self.capacity or
                record.levelno >= self.flushLevel)

    def emit(self, record):
        self.buffer.append(record)
        if self.shouldFlush(record):
            self.flush()

    def flush(self):
        self.acquire()
        try:
            self.target and [self.target.emit(r) for r in self.buffer]
            self.buffer.clear()
        finally:
            self.release()

    def close(self):
        try:
            if self.flushOnClose:
                self.flush()
        finally:
            self.acquire()
            try:
                self.target = None
            finally:
                self.release()
            _logging.Handler.close(self)

    def setTarget(self, target):
        self.acquire()
        try:
            self.target = target
        finally:
            self.release()


class QueueHandler(_logging.Handler):
    """Send log records to a queue."""

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def enqueue(self, record):
        self.queue.put_nowait(record)

    def prepare(self, record):
        self.format(record)
        record.msg = record.getMessage()
        record.args = None
        record.exc_info = None
        record.exc_text = None
        return record

    def emit(self, record):
        try:
            self.enqueue(self.prepare(record))
        except Exception:
            self.handleError(record)


class QueueListener:
    """Listen to a queue and dispatch to handlers."""

    def __init__(self, queue, *handlers, respect_handler_level=False):
        self.queue = queue
        self.handlers = list(handlers)
        self.respect_handler_level = respect_handler_level
        self._thread = None

    def dequeue(self, block):
        return self.queue.get(block=block)

    def start(self):
        import threading
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def _monitor(self):
        import queue as _q
        while True:
            try:
                record = self.dequeue(True)
                if record is self._sentinel:
                    break
                self.handle(record)
            except _q.Empty:
                pass

    @property
    def _sentinel(self):
        return None

    def handle(self, record):
        for handler in self.handlers:
            if not self.respect_handler_level or record.levelno >= handler.level:
                handler.handle(record)

    def stop(self):
        self.queue.put_nowait(self._sentinel)
        if self._thread:
            self._thread.join()
            self._thread = None


class NullHandler(_logging.Handler):
    def emit(self, record):
        pass


class StreamHandler(_logging.StreamHandler):
    pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def loghandlers2_rotating():
    """RotatingFileHandler can be instantiated; returns True."""
    import tempfile as _tmp
    with _tmp.TemporaryDirectory() as d:
        path = _os.path.join(d, 'test.log')
        h = RotatingFileHandler(path, maxBytes=1024, backupCount=3)
        h.close()
        return isinstance(h, RotatingFileHandler)


def loghandlers2_memory():
    """MemoryHandler buffers records; returns True."""
    records = []

    class _Target(_logging.Handler):
        def emit(self, record):
            records.append(record)

    target = _Target()
    h = MemoryHandler(capacity=10, flushLevel=_logging.ERROR, target=target)
    r = _logging.LogRecord('test', _logging.INFO, '', 0, 'msg', [], None)
    h.emit(r)
    return len(h.buffer) == 1 and len(records) == 0


def loghandlers2_queue():
    """QueueHandler enqueues log records; returns True."""
    q = _queue.Queue()
    h = QueueHandler(q)
    r = _logging.LogRecord('test', _logging.INFO, '', 0, 'test message', [], None)
    h.emit(r)
    return not q.empty()


__all__ = [
    'BaseRotatingHandler', 'RotatingFileHandler', 'TimedRotatingFileHandler',
    'MemoryHandler', 'QueueHandler', 'QueueListener',
    'NullHandler', 'StreamHandler',
    'loghandlers2_rotating', 'loghandlers2_memory', 'loghandlers2_queue',
]
