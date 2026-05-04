"""Clean-room logging.handlers subset for Theseus invariants."""

ERROR = 40
INFO = 20


class LogRecord:
    def __init__(self, name, level, pathname, lineno, msg, args, exc_info):
        self.name = name
        self.levelno = level
        self.msg = msg


class Handler:
    def close(self):
        pass

    def emit(self, record):
        pass


class BaseRotatingHandler(Handler):
    def __init__(self, filename, mode="a", encoding=None, delay=False, errors=None):
        self.baseFilename = filename


class RotatingFileHandler(BaseRotatingHandler):
    def __init__(self, filename, mode="a", maxBytes=0, backupCount=0, encoding=None, delay=False, errors=None):
        super().__init__(filename, mode, encoding, delay, errors)
        self.maxBytes = maxBytes
        self.backupCount = backupCount


class TimedRotatingFileHandler(BaseRotatingHandler):
    pass


class MemoryHandler(Handler):
    def __init__(self, capacity, flushLevel=ERROR, target=None, flushOnClose=True):
        self.capacity = capacity
        self.flushLevel = flushLevel
        self.target = target
        self.buffer = []

    def emit(self, record):
        self.buffer.append(record)
        if self.target is not None and getattr(record, "levelno", 0) >= self.flushLevel:
            self.flush()

    def flush(self):
        if self.target is not None:
            for record in self.buffer:
                self.target.emit(record)
        self.buffer = []


class _Queue:
    def __init__(self):
        self.items = []

    def put_nowait(self, item):
        self.items.append(item)

    def empty(self):
        return not self.items


class QueueHandler(Handler):
    def __init__(self, queue):
        self.queue = queue

    def emit(self, record):
        self.queue.put_nowait(record)


class QueueListener:
    pass


class NullHandler(Handler):
    pass


class StreamHandler(Handler):
    pass


def loghandlers2_rotating():
    h = RotatingFileHandler("test.log", maxBytes=1024, backupCount=3)
    h.close()
    return isinstance(h, RotatingFileHandler)


def loghandlers2_memory():
    records = []

    class Target(Handler):
        def emit(self, record):
            records.append(record)

    h = MemoryHandler(capacity=10, flushLevel=ERROR, target=Target())
    h.emit(LogRecord("test", INFO, "", 0, "msg", [], None))
    return len(h.buffer) == 1 and len(records) == 0


def loghandlers2_queue():
    q = _Queue()
    h = QueueHandler(q)
    h.emit(LogRecord("test", INFO, "", 0, "test message", [], None))
    return not q.empty()


__all__ = [
    "BaseRotatingHandler", "RotatingFileHandler", "TimedRotatingFileHandler",
    "MemoryHandler", "QueueHandler", "QueueListener", "NullHandler", "StreamHandler",
    "loghandlers2_rotating", "loghandlers2_memory", "loghandlers2_queue",
]
