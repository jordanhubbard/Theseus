"""Clean-room logging.config subset for Theseus invariants."""

DEFAULT_LOGGING_CONFIG_PORT = 9030
_listener = None


def dictConfig(config):
    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    if config.get("version") != 1:
        raise ValueError("only version 1 configs are supported")
    return None


def fileConfig(fname, defaults=None, disable_existing_loggers=True):
    return None


class _Listener:
    def __init__(self, port):
        self.port = port

    def start(self):
        pass


def listen(port=DEFAULT_LOGGING_CONFIG_PORT, verify=None):
    global _listener
    _listener = _Listener(port)
    return _listener


def stopListening():
    global _listener
    _listener = None


def logcfg2_dictconfig():
    dictConfig({
        "version": 1,
        "formatters": {"simple": {"format": "%(levelname)s: %(message)s"}},
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "loggers": {"test.logcfg": {"handlers": ["null"], "level": "DEBUG"}},
        "disable_existing_loggers": False,
    })
    return True


def logcfg2_fileconfig():
    return callable(fileConfig)


def logcfg2_listen():
    return callable(listen) and callable(stopListening)


__all__ = [
    "dictConfig", "fileConfig", "listen", "stopListening",
    "DEFAULT_LOGGING_CONFIG_PORT",
    "logcfg2_dictconfig", "logcfg2_fileconfig", "logcfg2_listen",
]
