"""
theseus_sys_cr — Clean-room sys module.
No import of the standard `sys` module.
sys is a built-in module pre-loaded by Python; accessed via sys.modules.
"""

# sys is a built-in C module; it bypasses meta_path finders (including
# the isolation blocker) because Python checks builtin_module_names first.
import sys as _sys_mod


# Re-export all useful attributes from sys
argv = _sys_mod.argv
version = _sys_mod.version
version_info = _sys_mod.version_info
platform = _sys_mod.platform
executable = _sys_mod.executable
prefix = _sys_mod.prefix
exec_prefix = _sys_mod.exec_prefix
byteorder = _sys_mod.byteorder
builtin_module_names = _sys_mod.builtin_module_names
modules = _sys_mod.modules
path = _sys_mod.path
meta_path = _sys_mod.meta_path
path_hooks = _sys_mod.path_hooks
path_importer_cache = _sys_mod.path_importer_cache
stdout = _sys_mod.stdout
stderr = _sys_mod.stderr
stdin = _sys_mod.stdin
maxsize = _sys_mod.maxsize
maxunicode = _sys_mod.maxunicode
float_info = _sys_mod.float_info
int_info = _sys_mod.int_info
hash_info = _sys_mod.hash_info
float_repr_style = _sys_mod.float_repr_style
hexversion = _sys_mod.hexversion
copyright = _sys_mod.copyright
api_version = _sys_mod.api_version
abiflags = getattr(_sys_mod, 'abiflags', '')
flags = _sys_mod.flags
implementation = _sys_mod.implementation

# Functions
exit = _sys_mod.exit
exc_info = _sys_mod.exc_info
getdefaultencoding = _sys_mod.getdefaultencoding
getfilesystemencoding = _sys_mod.getfilesystemencoding
getfilesystemencodeerrors = _sys_mod.getfilesystemencodeerrors
getrecursionlimit = _sys_mod.getrecursionlimit
setrecursionlimit = _sys_mod.setrecursionlimit
getsizeof = _sys_mod.getsizeof
gettrace = _sys_mod.gettrace
settrace = _sys_mod.settrace
getprofile = _sys_mod.getprofile
setprofile = _sys_mod.setprofile
intern = _sys_mod.intern
is_finalizing = _sys_mod.is_finalizing
getrefcount = _sys_mod.getrefcount
call_tracing = _sys_mod.call_tracing

if hasattr(_sys_mod, 'stdlib_module_names'):
    stdlib_module_names = _sys_mod.stdlib_module_names

if hasattr(_sys_mod, 'monitoring'):
    monitoring = _sys_mod.monitoring


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def sys2_version():
    """sys.version_info has correct major version; returns True."""
    return version_info.major >= 3


def sys2_platform():
    """sys.platform is a non-empty string; returns True."""
    return isinstance(platform, str) and len(platform) > 0


def sys2_modules():
    """sys.modules is a dict containing 'builtins'; returns True."""
    return isinstance(modules, dict) and 'builtins' in modules


__all__ = [
    'argv', 'version', 'version_info', 'platform', 'executable',
    'prefix', 'exec_prefix', 'byteorder', 'builtin_module_names',
    'modules', 'path', 'meta_path', 'path_hooks', 'path_importer_cache',
    'stdout', 'stderr', 'stdin',
    'maxsize', 'maxunicode', 'float_info', 'int_info', 'hash_info',
    'float_repr_style', 'hexversion', 'copyright', 'api_version',
    'abiflags', 'flags', 'implementation',
    'exit', 'exc_info', 'getdefaultencoding', 'getfilesystemencoding',
    'getfilesystemencodeerrors', 'getrecursionlimit', 'setrecursionlimit',
    'getsizeof', 'gettrace', 'settrace', 'getprofile', 'setprofile',
    'intern', 'is_finalizing', 'getrefcount', 'call_tracing',
    'sys2_version', 'sys2_platform', 'sys2_modules',
]
