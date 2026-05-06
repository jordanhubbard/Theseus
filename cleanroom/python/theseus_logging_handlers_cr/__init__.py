"""Clean-room reimplementation of logging.handlers primitives.

This module provides minimal, from-scratch implementations of the
familiar logging handlers (rotating file, memory buffer, queue) without
importing the standard library's ``logging.handlers`` module.
"""

import os as _os
import sys as _sys
import time as _time


# ---------------------------------------------------------------------------
# Base handler
# ---------------------------------------------------------------------------

class Handler(object):
    """Very small logging handler base class."""

    def __init__(self, level=0):
        self.level = level
        self.formatter = None

    def setLevel(self, level):
        self.level = level

    def setFormatter(self, fmt):
        self.formatter = fmt

    def format(self, record):
        if self.formatter is not None:
            try:
                return self.formatter.format(record)
            except Exception:
                pass
        # Fallback: stringify a record-like object.
        msg = getattr(record, "msg", record)
        args = getattr(record, "args", None)
        if args:
            try:
                msg = msg % args
            except Exception:
                pass
        return str(msg)

    def handle(self, record):
        self.emit(record)

    def emit(self, record):
        raise NotImplementedError

    def flush(self):
        pass

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Rotating file handler
# ---------------------------------------------------------------------------

class BaseRotatingHandler(Handler):
    def __init__(self, filename, mode="a", encoding=None):
        Handler.__init__(self)
        self.baseFilename = _os.path.abspath(filename)
        self.mode = mode
        self.encoding = encoding
        self._stream = None

    def _open(self):
        if self.encoding is None:
            return open(self.baseFilename, self.mode)
        return open(self.baseFilename, self.mode, encoding=self.encoding)

    @property
    def stream(self):
        if self._stream is None:
            self._stream = self._open()
        return self._stream

    def close(self):
        if self._stream is not None:
            try:
                self._stream.close()
            finally:
                self._stream = None

    def flush(self):
        if self._stream is not None:
            try:
                self._stream.flush()
            except Exception:
                pass

    def emit(self, record):
        try:
            if self.shouldRollover(record):
                self.doRollover()
            msg = self.format(record)
            s = self.stream
            s.write(msg)
            if not msg.endswith("\n"):
                s.write("\n")
            s.flush()
        except Exception:
            pass

    def shouldRollover(self, record):
        return False

    def doRollover(self):
        pass


class RotatingFileHandler(BaseRotatingHandler):
    """Rotates the log file when it grows past ``maxBytes``."""

    def __init__(self, filename, mode="a", maxBytes=0, backupCount=0,
                 encoding=None):
        if maxBytes > 0:
            mode = "a"
        BaseRotatingHandler.__init__(self, filename, mode=mode,
                                     encoding=encoding)
        self.maxBytes = maxBytes
        self.backupCount = backupCount

    def shouldRollover(self, record):
        if self.maxBytes <= 0:
            return False
        try:
            msg = self.format(record) + "\n"
        except Exception:
            msg = ""
        try:
            self.stream.seek(0, 2)  # end
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return True
        except Exception:
            pass
        return False

    def doRollover(self):
        if self._stream is not None:
            try:
                self._stream.close()
            finally:
                self._stream = None
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                src = "%s.%d" % (self.baseFilename, i)
                dst = "%s.%d" % (self.baseFilename, i + 1)
                if _os.path.exists(src):
                    if _os.path.exists(dst):
                        _os.remove(dst)
                    _os.rename(src, dst)
            dst = self.baseFilename + ".1"
            if _os.path.exists(dst):
                _os.remove(dst)
            if _os.path.exists(self.baseFilename):
                _os.rename(self.baseFilename, dst)
        self.mode = "w"
        self._stream = self._open()
        self.mode = "a"


# ---------------------------------------------------------------------------
# Memory handler
# ---------------------------------------------------------------------------

class BufferingHandler(Handler):
    """Stores records in memory until ``shouldFlush`` returns True."""

    def __init__(self, capacity):
        Handler.__init__(self)
        self.capacity = capacity
        self.buffer = []

    def shouldFlush(self, record):
        return len(self.buffer) >= self.capacity

    def emit(self, record):
        self.buffer.append(record)
        if self.shouldFlush(record):
            self.flush()

    def flush(self):
        # Default: just discard.  Subclasses override.
        self.buffer = []

    def close(self):
        try:
            self.flush()
        finally:
            Handler.close(self)


class MemoryHandler(BufferingHandler):
    """Buffers records and forwards them to ``target`` on flush."""

    DEFAULT_FLUSH_LEVEL = 40  # ERROR

    def __init__(self, capacity, flushLevel=None, target=None,
                 flushOnClose=True):
        BufferingHandler.__init__(self, capacity)
        if flushLevel is None:
            flushLevel = self.DEFAULT_FLUSH_LEVEL
        self.flushLevel = flushLevel
        self.target = target
        self.flushOnClose = flushOnClose

    def shouldFlush(self, record):
        if len(self.buffer) >= self.capacity:
            return True
        lvl = getattr(record, "levelno", 0)
        return lvl >= self.flushLevel

    def setTarget(self, target):
        self.target = target

    def flush(self):
        if self.target is not None:
            for record in self.buffer:
                try:
                    self.target.handle(record)
                except Exception:
                    pass
        self.buffer = []

    def close(self):
        try:
            if self.flushOnClose:
                self.flush()
        finally:
            self.target = None
            Handler.close(self)


# ---------------------------------------------------------------------------
# Queue handler / listener
# ---------------------------------------------------------------------------

class QueueHandler(Handler):
    """Pushes log records onto a queue-like object (``put_nowait`` / ``put``)."""

    def __init__(self, queue):
        Handler.__init__(self)
        self.queue = queue

    def enqueue(self, record):
        if hasattr(self.queue, "put_nowait"):
            self.queue.put_nowait(record)
        elif hasattr(self.queue, "put"):
            self.queue.put(record)
        elif hasattr(self.queue, "append"):
            self.queue.append(record)
        else:
            raise TypeError("queue object does not support put/append")

    def prepare(self, record):
        # Caller may want the formatted message attached; preserve record.
        try:
            msg = self.format(record)
            if hasattr(record, "__dict__"):
                record.message = msg
        except Exception:
            pass
        return record

    def emit(self, record):
        try:
            self.enqueue(self.prepare(record))
        except Exception:
            pass


class QueueListener(object):
    """Pulls records from a queue and dispatches them to handlers.

    Uses a simple background thread; a sentinel value signals shutdown.
    """

    _sentinel = None

    def __init__(self, queue, *handlers, **kwargs):
        self.queue = queue
        self.handlers = list(handlers)
        self.respect_handler_level = bool(kwargs.get(
            "respect_handler_level", False))
        self._thread = None
        self._stopped = False

    def dequeue(self, block):
        if hasattr(self.queue, "get"):
            try:
                return self.queue.get(block)
            except TypeError:
                return self.queue.get()
        if hasattr(self.queue, "popleft"):
            return self.queue.popleft()
        if hasattr(self.queue, "pop"):
            return self.queue.pop(0)
        raise TypeError("queue object does not support get/pop")

    def prepare(self, record):
        return record

    def handle(self, record):
        record = self.prepare(record)
        for h in self.handlers:
            if self.respect_handler_level:
                lvl = getattr(record, "levelno", 0)
                if lvl < getattr(h, "level", 0):
                    continue
            try:
                h.handle(record)
            except Exception:
                pass

    def _monitor(self):
        while not self._stopped:
            try:
                record = self.dequeue(True)
            except Exception:
                _time.sleep(0.01)
                continue
            if record is self._sentinel:
                break
            self.handle(record)
            done = getattr(self.queue, "task_done", None)
            if done is not None:
                try:
                    done()
                except Exception:
                    pass

    def start(self):
        import threading
        self._stopped = False
        self._thread = threading.Thread(target=self._monitor)
        self._thread.daemon = True
        self._thread.start()

    def enqueue_sentinel(self):
        if hasattr(self.queue, "put_nowait"):
            try:
                self.queue.put_nowait(self._sentinel)
                return
            except Exception:
                pass
        if hasattr(self.queue, "put"):
            self.queue.put(self._sentinel)
        elif hasattr(self.queue, "append"):
            self.queue.append(self._sentinel)

    def stop(self):
        self._stopped = True
        try:
            self.enqueue_sentinel()
        except Exception:
            pass
        t = self._thread
        if t is not None:
            try:
                t.join(timeout=1.0)
            except Exception:
                pass
        self._thread = None


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def loghandlers2_rotating():
    """Verify that the rotating file handler rolls files over."""
    import tempfile
    import shutil

    tmpdir = tempfile.mkdtemp(prefix="theseus_lh_rot_")
    try:
        path = _os.path.join(tmpdir, "app.log")
        h = RotatingFileHandler(path, maxBytes=40, backupCount=2)
        try:
            for i in range(20):
                # Use a plain string as the "record"; format() will handle it.
                h.emit("entry-%02d-with-some-padding-text" % i)
            h.flush()
        finally:
            h.close()

        # Original log file must exist plus at least one rotated backup.
        if not _os.path.exists(path):
            return False
        if not _os.path.exists(path + ".1"):
            return False
        # backupCount=2 means we cap at .2.
        if _os.path.exists(path + ".3"):
            return False
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


class _CollectingHandler(Handler):
    def __init__(self):
        Handler.__init__(self)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class _LevelRecord(object):
    def __init__(self, msg, levelno=20):
        self.msg = msg
        self.levelno = levelno
        self.args = None


def loghandlers2_memory():
    """Verify that the MemoryHandler buffers and flushes on capacity/level."""
    target = _CollectingHandler()
    mh = MemoryHandler(capacity=3, flushLevel=40, target=target)

    # Below capacity, nothing should be flushed yet.
    mh.emit(_LevelRecord("a", 10))
    mh.emit(_LevelRecord("b", 20))
    if len(target.records) != 0:
        return False
    if len(mh.buffer) != 2:
        return False

    # Hitting capacity (3) should trigger a flush.
    mh.emit(_LevelRecord("c", 20))
    if len(target.records) != 3:
        return False
    if len(mh.buffer) != 0:
        return False

    # An ERROR-level record should flush immediately even below capacity.
    mh.emit(_LevelRecord("d", 20))
    mh.emit(_LevelRecord("e-error", 40))
    if len(target.records) != 5:
        return False
    if len(mh.buffer) != 0:
        return False

    mh.close()
    return True


def loghandlers2_queue():
    """Verify QueueHandler/QueueListener round-trip."""
    try:
        import queue as _queue_mod
    except ImportError:
        return False

    q = _queue_mod.Queue()
    qh = QueueHandler(q)

    target = _CollectingHandler()
    listener = QueueListener(q, target)
    listener.start()
    try:
        for i in range(5):
            qh.emit(_LevelRecord("msg-%d" % i, 20))
        # Wait briefly for the listener thread to drain the queue.
        deadline = _time.time() + 2.0
        while _time.time() < deadline and len(target.records) < 5:
            _time.sleep(0.01)
    finally:
        listener.stop()

    return len(target.records) == 5


__all__ = [
    "Handler",
    "BaseRotatingHandler",
    "RotatingFileHandler",
    "BufferingHandler",
    "MemoryHandler",
    "QueueHandler",
    "QueueListener",
    "loghandlers2_rotating",
    "loghandlers2_memory",
    "loghandlers2_queue",
]