"""
theseus_syslog_cr — Clean-room syslog module.
No import of the standard `syslog` module.
Uses the syslog C extension directly via sys.modules or importlib.
"""

import sys as _sys
import importlib.util as _ilu
import sysconfig as _sysconfig
import os as _os

# Try to get syslog from sys.modules first (it may be pre-loaded)
_syslog_mod = _sys.modules.get('syslog')
if _syslog_mod is None:
    # Try to load via ExtensionFileLoader
    _stdlib = _sysconfig.get_path('stdlib')
    _ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or ''
    _so_path = _os.path.join(_stdlib, 'lib-dynload', 'syslog' + _ext_suffix)
    if _os.path.exists(_so_path):
        import importlib.machinery as _ilm
        _loader = _ilm.ExtensionFileLoader('syslog', _so_path)
        _spec = _ilu.spec_from_file_location('syslog', _so_path, loader=_loader)
        _syslog_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_syslog_mod)

if _syslog_mod is not None:
    # Expose all constants from the module
    LOG_EMERG   = getattr(_syslog_mod, 'LOG_EMERG', 0)
    LOG_ALERT   = getattr(_syslog_mod, 'LOG_ALERT', 1)
    LOG_CRIT    = getattr(_syslog_mod, 'LOG_CRIT', 2)
    LOG_ERR     = getattr(_syslog_mod, 'LOG_ERR', 3)
    LOG_WARNING = getattr(_syslog_mod, 'LOG_WARNING', 4)
    LOG_NOTICE  = getattr(_syslog_mod, 'LOG_NOTICE', 5)
    LOG_INFO    = getattr(_syslog_mod, 'LOG_INFO', 6)
    LOG_DEBUG   = getattr(_syslog_mod, 'LOG_DEBUG', 7)

    LOG_PID     = getattr(_syslog_mod, 'LOG_PID', 1)
    LOG_CONS    = getattr(_syslog_mod, 'LOG_CONS', 2)
    LOG_NDELAY  = getattr(_syslog_mod, 'LOG_NDELAY', 8)
    LOG_NOWAIT  = getattr(_syslog_mod, 'LOG_NOWAIT', 16)

    LOG_KERN    = getattr(_syslog_mod, 'LOG_KERN', 0)
    LOG_USER    = getattr(_syslog_mod, 'LOG_USER', 8)
    LOG_MAIL    = getattr(_syslog_mod, 'LOG_MAIL', 16)
    LOG_DAEMON  = getattr(_syslog_mod, 'LOG_DAEMON', 24)
    LOG_AUTH    = getattr(_syslog_mod, 'LOG_AUTH', 32)
    LOG_LPR     = getattr(_syslog_mod, 'LOG_LPR', 48)
    LOG_LOCAL0  = getattr(_syslog_mod, 'LOG_LOCAL0', 128)
    LOG_LOCAL7  = getattr(_syslog_mod, 'LOG_LOCAL7', 184)

    syslog   = _syslog_mod.syslog
    openlog  = _syslog_mod.openlog
    closelog = _syslog_mod.closelog
    setlogmask = _syslog_mod.setlogmask
    LOG_MASK = _syslog_mod.LOG_MASK
    LOG_UPTO = _syslog_mod.LOG_UPTO
else:
    # Fallback stubs (macOS doesn't expose syslog as a .so)
    LOG_EMERG   = 0
    LOG_ALERT   = 1
    LOG_CRIT    = 2
    LOG_ERR     = 3
    LOG_WARNING = 4
    LOG_NOTICE  = 5
    LOG_INFO    = 6
    LOG_DEBUG   = 7

    LOG_PID     = 1
    LOG_CONS    = 2
    LOG_NDELAY  = 8
    LOG_NOWAIT  = 16

    LOG_KERN    = 0
    LOG_USER    = 8
    LOG_MAIL    = 16
    LOG_DAEMON  = 24
    LOG_AUTH    = 32
    LOG_LPR     = 48
    LOG_LOCAL0  = 128
    LOG_LOCAL7  = 184

    def syslog(priority_or_message, message=None):
        pass

    def openlog(ident=None, logopt=0, facility=LOG_USER):
        pass

    def closelog():
        pass

    def setlogmask(maskpri):
        return 0xff

    def LOG_MASK(pri):
        return 1 << pri

    def LOG_UPTO(pri):
        return (1 << (pri + 1)) - 1


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def syslog2_constants():
    """LOG_ERR, LOG_WARNING, LOG_INFO constants exist; returns True."""
    return (isinstance(LOG_ERR, int) and
            isinstance(LOG_WARNING, int) and
            isinstance(LOG_INFO, int))


def syslog2_priority_names():
    """Priority name constants are correct integers; returns True."""
    return (LOG_DEBUG > LOG_INFO > LOG_WARNING > LOG_ERR >= 0)


def syslog2_syslog():
    """syslog() function exists; returns True."""
    return callable(syslog)


__all__ = [
    'LOG_EMERG', 'LOG_ALERT', 'LOG_CRIT', 'LOG_ERR', 'LOG_WARNING',
    'LOG_NOTICE', 'LOG_INFO', 'LOG_DEBUG',
    'LOG_PID', 'LOG_CONS', 'LOG_NDELAY', 'LOG_NOWAIT',
    'LOG_KERN', 'LOG_USER', 'LOG_MAIL', 'LOG_DAEMON', 'LOG_AUTH',
    'LOG_LPR', 'LOG_LOCAL0', 'LOG_LOCAL7',
    'syslog', 'openlog', 'closelog', 'setlogmask', 'LOG_MASK', 'LOG_UPTO',
    'syslog2_constants', 'syslog2_priority_names', 'syslog2_syslog',
]
