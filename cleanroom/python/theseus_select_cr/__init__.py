"""
theseus_select_cr — Clean-room select module.
No import of the standard `select` module.
Loads the select C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_select_so = _os.path.join(_stdlib, 'lib-dynload', 'select' + _ext_suffix)
if not _os.path.exists(_select_so):
    raise ImportError(f"Cannot find select C extension at {_select_so}")

_loader = _importlib_machinery.ExtensionFileLoader('select', _select_so)
_spec = _importlib_util.spec_from_file_location('select', _select_so, loader=_loader)
_select_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_select_mod)

select = _select_mod.select
error = _select_mod.error

if hasattr(_select_mod, 'poll'):
    poll = _select_mod.poll
    POLLIN = _select_mod.POLLIN
    POLLOUT = _select_mod.POLLOUT
    POLLPRI = _select_mod.POLLPRI
    POLLERR = _select_mod.POLLERR
    POLLHUP = _select_mod.POLLHUP
    POLLNVAL = _select_mod.POLLNVAL

if hasattr(_select_mod, 'kqueue'):
    kqueue = _select_mod.kqueue
    kevent = _select_mod.kevent
    KQ_FILTER_READ = _select_mod.KQ_FILTER_READ
    KQ_FILTER_WRITE = _select_mod.KQ_FILTER_WRITE
    KQ_FILTER_AIO = getattr(_select_mod, 'KQ_FILTER_AIO', None)
    KQ_EV_ADD = _select_mod.KQ_EV_ADD
    KQ_EV_DELETE = _select_mod.KQ_EV_DELETE
    KQ_EV_ENABLE = _select_mod.KQ_EV_ENABLE
    KQ_EV_DISABLE = _select_mod.KQ_EV_DISABLE
    KQ_EV_CLEAR = _select_mod.KQ_EV_CLEAR
    KQ_EV_EOF = _select_mod.KQ_EV_EOF
    KQ_EV_ERROR = _select_mod.KQ_EV_ERROR

if hasattr(_select_mod, 'epoll'):
    epoll = _select_mod.epoll
    EPOLLIN = _select_mod.EPOLLIN
    EPOLLOUT = _select_mod.EPOLLOUT
    EPOLLERR = _select_mod.EPOLLERR
    EPOLLHUP = _select_mod.EPOLLHUP
    EPOLLET = _select_mod.EPOLLET
    EPOLLONESHOT = getattr(_select_mod, 'EPOLLONESHOT', None)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def select2_select_empty():
    """select() with empty lists and timeout=0 returns immediately; returns True."""
    r, w, e = select([], [], [], 0)
    return r == [] and w == [] and e == []


def select2_pipe_ready():
    """select() detects data available on a pipe; returns True."""
    import os
    r_fd, w_fd = os.pipe()
    try:
        os.write(w_fd, b'x')
        readable, _, _ = select([r_fd], [], [], 0.1)
        return r_fd in readable
    finally:
        os.close(r_fd)
        os.close(w_fd)


def select2_error_class():
    """error exception class exists; returns True."""
    return issubclass(error, OSError)


__all__ = [
    'select', 'error',
    'select2_select_empty', 'select2_pipe_ready', 'select2_error_class',
]
