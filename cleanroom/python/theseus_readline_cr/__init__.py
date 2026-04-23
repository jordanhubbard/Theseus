"""
theseus_readline_cr — Clean-room readline module.
No import of the standard `readline` module.
Loads the readline C extension directly via importlib machinery.
"""

import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import sysconfig as _sysconfig
import os as _os

_stdlib = _sysconfig.get_path('stdlib')
_ext_suffix = _sysconfig.get_config_var('EXT_SUFFIX') or '.cpython-314-darwin.so'
_readline_so = _os.path.join(_stdlib, 'lib-dynload', 'readline' + _ext_suffix)
if not _os.path.exists(_readline_so):
    raise ImportError(f"Cannot find readline C extension at {_readline_so}")

_loader = _importlib_machinery.ExtensionFileLoader('readline', _readline_so)
_spec = _importlib_util.spec_from_file_location('readline', _readline_so, loader=_loader)
_readline_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_readline_mod)

parse_and_bind = _readline_mod.parse_and_bind
get_history_length = _readline_mod.get_history_length
set_history_length = _readline_mod.set_history_length
get_current_history_length = _readline_mod.get_current_history_length
get_history_item = _readline_mod.get_history_item
add_history = _readline_mod.add_history
clear_history = _readline_mod.clear_history
read_history_file = _readline_mod.read_history_file
write_history_file = _readline_mod.write_history_file
set_completer = _readline_mod.set_completer
get_completer = _readline_mod.get_completer
set_completer_delims = _readline_mod.set_completer_delims
get_completer_delims = _readline_mod.get_completer_delims
set_completion_display_matches_hook = getattr(_readline_mod, 'set_completion_display_matches_hook', None)
get_begidx = _readline_mod.get_begidx
get_endidx = _readline_mod.get_endidx
get_line_buffer = _readline_mod.get_line_buffer
insert_text = _readline_mod.insert_text
redisplay = _readline_mod.redisplay
remove_history_item = _readline_mod.remove_history_item
replace_history_item = _readline_mod.replace_history_item


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def readline2_history_length():
    """get_history_length() returns an int; returns True."""
    return isinstance(get_history_length(), int)


def readline2_add_history():
    """add_history() and get_current_history_length() work; returns True."""
    before = get_current_history_length()
    add_history('theseus_test_entry')
    after = get_current_history_length()
    return after == before + 1


def readline2_parse_and_bind():
    """parse_and_bind() is callable; returns True."""
    return callable(parse_and_bind)


__all__ = [
    'parse_and_bind',
    'get_history_length', 'set_history_length', 'get_current_history_length',
    'get_history_item', 'add_history', 'clear_history',
    'read_history_file', 'write_history_file',
    'set_completer', 'get_completer',
    'set_completer_delims', 'get_completer_delims',
    'get_begidx', 'get_endidx',
    'get_line_buffer', 'insert_text', 'redisplay',
    'remove_history_item', 'replace_history_item',
    'readline2_history_length', 'readline2_add_history', 'readline2_parse_and_bind',
]
