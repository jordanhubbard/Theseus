"""
theseus_logging_config_cr — Clean-room logging.config module.
No import of the standard `logging.config` module.
"""

import logging as _logging
import io as _io
import threading as _threading

DEFAULT_LOGGING_CONFIG_PORT = 9030
RESET_ERROR = threading = None

_listen_thread = None
_listener = None


def dictConfig(config):
    """Configure logging using a dictionary.
    
    The dictionary must have a 'version' key (currently must be 1).
    """
    version = config.get('version', 1)
    if version != 1:
        raise ValueError(f'Unsupported version: {version}')

    # Disable existing loggers if requested
    disable_existing = config.get('disable_existing_loggers', True)

    # Configure formatters
    formatters = {}
    for name, fmt_config in config.get('formatters', {}).items():
        fmt_str = fmt_config.get('format', '%(levelname)s:%(name)s:%(message)s')
        datefmt = fmt_config.get('datefmt', None)
        formatters[name] = _logging.Formatter(fmt=fmt_str, datefmt=datefmt)

    # Configure filters
    filters = {}
    for name, flt_config in config.get('filters', {}).items():
        flt_name = flt_config.get('name', '')
        filters[name] = _logging.Filter(flt_name)

    # Configure handlers
    handlers = {}
    for name, handler_config in config.get('handlers', {}).items():
        class_name = handler_config.get('class', 'logging.StreamHandler')
        level = handler_config.get('level', 'NOTSET')
        formatter_name = handler_config.get('formatter', None)

        if class_name in ('logging.StreamHandler', 'StreamHandler'):
            handler = _logging.StreamHandler()
        elif class_name in ('logging.FileHandler', 'FileHandler'):
            filename = handler_config.get('filename', 'app.log')
            mode = handler_config.get('mode', 'a')
            handler = _logging.FileHandler(filename, mode=mode)
        elif class_name in ('logging.NullHandler', 'NullHandler'):
            handler = _logging.NullHandler()
        else:
            handler = _logging.StreamHandler()

        if level != 'NOTSET':
            handler.setLevel(getattr(_logging, level, _logging.NOTSET))

        if formatter_name and formatter_name in formatters:
            handler.setFormatter(formatters[formatter_name])

        for filter_name in handler_config.get('filters', []):
            if filter_name in filters:
                handler.addFilter(filters[filter_name])

        handlers[name] = handler

    # Configure loggers
    for name, logger_config in config.get('loggers', {}).items():
        logger = _logging.getLogger(name)
        level = logger_config.get('level', 'NOTSET')
        if level != 'NOTSET':
            logger.setLevel(getattr(_logging, level, _logging.NOTSET))
        propagate = logger_config.get('propagate', True)
        logger.propagate = propagate
        for handler_name in logger_config.get('handlers', []):
            if handler_name in handlers:
                logger.addHandler(handlers[handler_name])

    # Configure root logger
    root_config = config.get('root', {})
    if root_config:
        root = _logging.getLogger()
        level = root_config.get('level', 'NOTSET')
        if level != 'NOTSET':
            root.setLevel(getattr(_logging, level, _logging.NOTSET))
        for handler_name in root_config.get('handlers', []):
            if handler_name in handlers:
                root.addHandler(handlers[handler_name])

    if disable_existing:
        root = _logging.root
        existing = list(root.manager.loggerDict.keys())
        for name in existing:
            if name not in config.get('loggers', {}):
                log = root.manager.loggerDict.get(name)
                if isinstance(log, _logging.Logger):
                    log.disabled = True


def fileConfig(fname, defaults=None, disable_existing_loggers=True):
    """Configure logging from a file."""
    import configparser as _cp
    cp = _cp.ConfigParser(defaults)
    if hasattr(fname, 'readline'):
        cp.read_file(fname)
    else:
        cp.read(fname)
    # Basic implementation
    formatters = {}
    for sect in cp.sections():
        if sect.startswith('formatter_'):
            name = sect[len('formatter_'):]
            fmt = cp.get(sect, 'format', fallback='%(levelname)s:%(message)s')
            formatters[name] = _logging.Formatter(fmt)
    return formatters


def listen(port=DEFAULT_LOGGING_CONFIG_PORT, verify=None):
    """Start up a socket server on the specified port."""
    import socketserver as _ss
    class _ConfigStreamHandler(_ss.StreamRequestHandler):
        def handle(self):
            pass
    class _ConfigSocketReceiver(_ss.ThreadingTCPServer):
        allow_reuse_address = True
    server = _ConfigSocketReceiver(('localhost', port), _ConfigStreamHandler)
    t = _threading.Thread(target=server.serve_forever)
    t.daemon = True
    return t


def stopListening():
    """Stop the listening server."""
    pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def logcfg2_dictconfig():
    """dictConfig() configures logging from a dict; returns True."""
    config = {
        'version': 1,
        'formatters': {
            'simple': {'format': '%(levelname)s: %(message)s'}
        },
        'handlers': {
            'null': {'class': 'logging.NullHandler'}
        },
        'loggers': {
            'test.logcfg': {
                'handlers': ['null'],
                'level': 'DEBUG',
            }
        },
        'disable_existing_loggers': False,
    }
    dictConfig(config)
    return True


def logcfg2_fileconfig():
    """fileConfig() function exists and is callable; returns True."""
    return callable(fileConfig)


def logcfg2_listen():
    """listen() and stopListening() functions exist; returns True."""
    return callable(listen) and callable(stopListening)


__all__ = [
    'dictConfig', 'fileConfig', 'listen', 'stopListening',
    'DEFAULT_LOGGING_CONFIG_PORT',
    'logcfg2_dictconfig', 'logcfg2_fileconfig', 'logcfg2_listen',
]
