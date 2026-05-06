"""
theseus_winreg_cr - Clean-room winreg stub.

No import of the standard `winreg` module.  This is a Windows-only
API; on non-Windows platforms (and indeed always, since the original
package is not imported) the function stubs raise OSError.

Only Python standard-library built-ins are used.
"""

import sys as _sys

_ON_WINDOWS = _sys.platform == 'win32'

# ---------------------------------------------------------------------------
# Registry root key handle constants
# ---------------------------------------------------------------------------
HKEY_CLASSES_ROOT = 0x80000000
HKEY_CURRENT_USER = 0x80000001
HKEY_LOCAL_MACHINE = 0x80000002
HKEY_USERS = 0x80000003
HKEY_PERFORMANCE_DATA = 0x80000004
HKEY_CURRENT_CONFIG = 0x80000005
HKEY_DYN_DATA = 0x80000006

# ---------------------------------------------------------------------------
# Access-rights constants
# ---------------------------------------------------------------------------
KEY_QUERY_VALUE = 0x0001
KEY_SET_VALUE = 0x0002
KEY_CREATE_SUB_KEY = 0x0004
KEY_ENUMERATE_SUB_KEYS = 0x0008
KEY_NOTIFY = 0x0010
KEY_CREATE_LINK = 0x0020
KEY_WOW64_64KEY = 0x0100
KEY_WOW64_32KEY = 0x0200
KEY_WOW64_RES = 0x0300

KEY_READ = 0x20019
KEY_WRITE = 0x20006
KEY_EXECUTE = KEY_READ
KEY_ALL_ACCESS = 0xF003F

# ---------------------------------------------------------------------------
# Value type constants
# ---------------------------------------------------------------------------
REG_NONE = 0
REG_SZ = 1
REG_EXPAND_SZ = 2
REG_BINARY = 3
REG_DWORD = 4
REG_DWORD_LITTLE_ENDIAN = 4
REG_DWORD_BIG_ENDIAN = 5
REG_LINK = 6
REG_MULTI_SZ = 7
REG_RESOURCE_LIST = 8
REG_FULL_RESOURCE_DESCRIPTOR = 9
REG_RESOURCE_REQUIREMENTS_LIST = 10
REG_QWORD = 11
REG_QWORD_LITTLE_ENDIAN = 11

# ---------------------------------------------------------------------------
# Option / disposition / save-restore / notify constants
# ---------------------------------------------------------------------------
REG_OPTION_RESERVED = 0
REG_OPTION_NON_VOLATILE = 0
REG_OPTION_VOLATILE = 1
REG_OPTION_CREATE_LINK = 2
REG_OPTION_BACKUP_RESTORE = 4
REG_OPTION_OPEN_LINK = 8
REG_LEGAL_OPTION = 0x0F

REG_CREATED_NEW_KEY = 1
REG_OPENED_EXISTING_KEY = 2

REG_WHOLE_HIVE_VOLATILE = 1
REG_REFRESH_HIVE = 2
REG_NO_LAZY_FLUSH = 4
REG_FORCE_RESTORE = 8

REG_NOTIFY_CHANGE_NAME = 1
REG_NOTIFY_CHANGE_ATTRIBUTES = 2
REG_NOTIFY_CHANGE_LAST_SET = 4
REG_NOTIFY_CHANGE_SECURITY = 8
REG_LEGAL_CHANGE_FILTER = 0x0F

# Errors raised by the (real) winreg are plain OSError.
error = OSError


# ---------------------------------------------------------------------------
# HKEYType - clean-room handle object
# ---------------------------------------------------------------------------
class HKEYType:
    """A minimal, picklable stand-in for winreg.PyHKEY."""

    __slots__ = ('handle',)

    def __init__(self, handle=0):
        # Accept ints or other HKEYType instances transparently.
        if isinstance(handle, HKEYType):
            handle = handle.handle
        self.handle = int(handle)

    # --- numeric / boolean coercion -------------------------------------
    def __int__(self):
        return self.handle

    def __index__(self):
        return self.handle

    def __bool__(self):
        return self.handle != 0

    # --- equality / hashing ---------------------------------------------
    def __eq__(self, other):
        if isinstance(other, HKEYType):
            return self.handle == other.handle
        if isinstance(other, int):
            return self.handle == other
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash(self.handle)

    # --- key handle protocol --------------------------------------------
    def Close(self):
        self.handle = 0

    def Detach(self):
        h = self.handle
        self.handle = 0
        return h

    # --- context manager ------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.Close()
        return False

    def __repr__(self):
        return '<PyHKEY:0x%08x>' % (self.handle & 0xFFFFFFFF)


# ---------------------------------------------------------------------------
# Function stubs - Windows-only, always raise OSError here because the
# real `winreg` module cannot be imported in a clean-room build.
# ---------------------------------------------------------------------------
def _unavailable(name):
    if _ON_WINDOWS:
        raise OSError(
            "theseus_winreg_cr.%s: clean-room build cannot access the "
            "real Windows registry without importing winreg" % name
        )
    raise OSError("winreg.%s() is only available on Windows" % name)


def CloseKey(hkey):
    """Close a previously opened registry key."""
    if isinstance(hkey, HKEYType):
        hkey.Close()
        return None
    _unavailable('CloseKey')


def ConnectRegistry(computer_name, key):
    _unavailable('ConnectRegistry')


def CreateKey(key, sub_key):
    _unavailable('CreateKey')


def CreateKeyEx(key, sub_key, reserved=0, access=KEY_WRITE):
    _unavailable('CreateKeyEx')


def DeleteKey(key, sub_key):
    _unavailable('DeleteKey')


def DeleteKeyEx(key, sub_key, access=KEY_WOW64_64KEY, reserved=0):
    _unavailable('DeleteKeyEx')


def DeleteValue(key, value):
    _unavailable('DeleteValue')


def EnumKey(key, index):
    _unavailable('EnumKey')


def EnumValue(key, index):
    _unavailable('EnumValue')


def ExpandEnvironmentStrings(s):
    """Expand %VAR% style references in `s`.

    On non-Windows we mimic the winreg semantics by substituting from
    os.environ.  This is purely a convenience and does not touch the
    registry.
    """
    if not isinstance(s, str):
        raise TypeError("ExpandEnvironmentStrings expected a string")
    import os as _os
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == '%':
            end = s.find('%', i + 1)
            if end == -1:
                out.append(s[i:])
                break
            name = s[i + 1:end]
            if name == '':
                out.append('%')
            else:
                out.append(_os.environ.get(name, '%' + name + '%'))
            i = end + 1
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def FlushKey(key):
    _unavailable('FlushKey')


def LoadKey(key, sub_key, file_name):
    _unavailable('LoadKey')


def OpenKey(key, sub_key, reserved=0, access=KEY_READ):
    _unavailable('OpenKey')


def OpenKeyEx(key, sub_key, reserved=0, access=KEY_READ):
    _unavailable('OpenKeyEx')


def QueryInfoKey(key):
    _unavailable('QueryInfoKey')


def QueryValue(key, sub_key):
    _unavailable('QueryValue')


def QueryValueEx(key, value_name):
    _unavailable('QueryValueEx')


def SaveKey(key, file_name):
    _unavailable('SaveKey')


def SetValue(key, sub_key, type, value):
    _unavailable('SetValue')


def SetValueEx(key, value_name, reserved, type, value):
    _unavailable('SetValueEx')


def DisableReflectionKey(key):
    _unavailable('DisableReflectionKey')


def EnableReflectionKey(key):
    _unavailable('EnableReflectionKey')


def QueryReflectionKey(key):
    _unavailable('QueryReflectionKey')


# ---------------------------------------------------------------------------
# Invariant verification helpers
# ---------------------------------------------------------------------------
def winreg2_constants():
    """All required winreg constants exist with the canonical values."""
    checks = (
        HKEY_CLASSES_ROOT == 0x80000000,
        HKEY_CURRENT_USER == 0x80000001,
        HKEY_LOCAL_MACHINE == 0x80000002,
        HKEY_USERS == 0x80000003,
        HKEY_PERFORMANCE_DATA == 0x80000004,
        HKEY_CURRENT_CONFIG == 0x80000005,
        HKEY_DYN_DATA == 0x80000006,
        REG_NONE == 0,
        REG_SZ == 1,
        REG_EXPAND_SZ == 2,
        REG_BINARY == 3,
        REG_DWORD == 4,
        REG_DWORD_LITTLE_ENDIAN == 4,
        REG_DWORD_BIG_ENDIAN == 5,
        REG_LINK == 6,
        REG_MULTI_SZ == 7,
        REG_QWORD == 11,
        REG_QWORD_LITTLE_ENDIAN == 11,
        KEY_QUERY_VALUE == 0x0001,
        KEY_SET_VALUE == 0x0002,
        KEY_CREATE_SUB_KEY == 0x0004,
        KEY_ENUMERATE_SUB_KEYS == 0x0008,
        KEY_NOTIFY == 0x0010,
        KEY_CREATE_LINK == 0x0020,
        KEY_WOW64_32KEY == 0x0200,
        KEY_WOW64_64KEY == 0x0100,
        KEY_READ == 0x20019,
        KEY_WRITE == 0x20006,
        KEY_ALL_ACCESS == 0xF003F,
        REG_OPTION_VOLATILE == 1,
        REG_OPTION_NON_VOLATILE == 0,
        REG_CREATED_NEW_KEY == 1,
        REG_OPENED_EXISTING_KEY == 2,
        error is OSError,
    )
    return all(checks)


def winreg2_hkeytype():
    """HKEYType behaves like a registry handle stand-in."""
    # Construction with explicit handle
    k = HKEYType(0x12345678)
    if int(k) != 0x12345678:
        return False
    if not bool(k):
        return False
    if k != HKEYType(0x12345678):
        return False
    if hash(k) != hash(0x12345678):
        return False
    if not repr(k).startswith('<PyHKEY:'):
        return False

    # Detach returns and clears the handle
    detached = k.Detach()
    if detached != 0x12345678:
        return False
    if int(k) != 0:
        return False
    if bool(k):
        return False

    # Context manager closes the handle
    k2 = HKEYType(42)
    with k2 as alias:
        if alias is not k2:
            return False
        if int(alias) != 42:
            return False
    if int(k2) != 0:
        return False

    # Default construction
    k3 = HKEYType()
    if int(k3) != 0 or bool(k3):
        return False

    # Construction from another HKEYType
    k4 = HKEYType(HKEYType(7))
    if int(k4) != 7:
        return False

    return True


def winreg2_functions():
    """All advertised winreg functions are present and callable."""
    required = (
        'CloseKey', 'ConnectRegistry', 'CreateKey', 'CreateKeyEx',
        'DeleteKey', 'DeleteKeyEx', 'DeleteValue', 'EnumKey', 'EnumValue',
        'ExpandEnvironmentStrings', 'FlushKey', 'LoadKey',
        'OpenKey', 'OpenKeyEx', 'QueryInfoKey', 'QueryValue',
        'QueryValueEx', 'SaveKey', 'SetValue', 'SetValueEx',
        'DisableReflectionKey', 'EnableReflectionKey', 'QueryReflectionKey',
    )
    g = globals()
    for name in required:
        fn = g.get(name)
        if fn is None or not callable(fn):
            return False

    # CloseKey on an HKEYType handle should succeed without raising.
    h = HKEYType(0xCAFEBABE)
    try:
        CloseKey(h)
    except Exception:
        return False
    if int(h) != 0:
        return False

    # The other stubs must raise OSError when invoked.
    stubs_that_raise = (
        (OpenKey, (HKEY_CURRENT_USER, 'Software')),
        (CreateKey, (HKEY_CURRENT_USER, 'Software')),
        (DeleteKey, (HKEY_CURRENT_USER, 'Software')),
        (QueryValue, (HKEY_CURRENT_USER, 'Software')),
        (QueryValueEx, (HKEY_CURRENT_USER, 'Software')),
        (SetValue, (HKEY_CURRENT_USER, 'Software', REG_SZ, 'x')),
        (SetValueEx, (HKEY_CURRENT_USER, 'name', 0, REG_SZ, 'x')),
        (EnumKey, (HKEY_CURRENT_USER, 0)),
        (EnumValue, (HKEY_CURRENT_USER, 0)),
        (FlushKey, (HKEY_CURRENT_USER,)),
        (ConnectRegistry, (None, HKEY_LOCAL_MACHINE)),
    )
    for fn, args in stubs_that_raise:
        try:
            fn(*args)
        except OSError:
            continue
        except Exception:
            return False
        else:
            return False

    # ExpandEnvironmentStrings must work on plain strings.
    if ExpandEnvironmentStrings('hello') != 'hello':
        return False
    if not isinstance(ExpandEnvironmentStrings('%PATH%'), str):
        return False

    return True


__all__ = [
    # Class / error
    'HKEYType', 'error',
    # Root keys
    'HKEY_CLASSES_ROOT', 'HKEY_CURRENT_USER', 'HKEY_LOCAL_MACHINE',
    'HKEY_USERS', 'HKEY_PERFORMANCE_DATA', 'HKEY_CURRENT_CONFIG',
    'HKEY_DYN_DATA',
    # Access rights
    'KEY_QUERY_VALUE', 'KEY_SET_VALUE', 'KEY_CREATE_SUB_KEY',
    'KEY_ENUMERATE_SUB_KEYS', 'KEY_NOTIFY', 'KEY_CREATE_LINK',
    'KEY_WOW64_64KEY', 'KEY_WOW64_32KEY', 'KEY_WOW64_RES',
    'KEY_READ', 'KEY_WRITE', 'KEY_EXECUTE', 'KEY_ALL_ACCESS',
    # Value types
    'REG_NONE', 'REG_SZ', 'REG_EXPAND_SZ', 'REG_BINARY',
    'REG_DWORD', 'REG_DWORD_LITTLE_ENDIAN', 'REG_DWORD_BIG_ENDIAN',
    'REG_LINK', 'REG_MULTI_SZ', 'REG_RESOURCE_LIST',
    'REG_FULL_RESOURCE_DESCRIPTOR', 'REG_RESOURCE_REQUIREMENTS_LIST',
    'REG_QWORD', 'REG_QWORD_LITTLE_ENDIAN',
    # Options / dispositions / save / notify
    'REG_OPTION_RESERVED', 'REG_OPTION_NON_VOLATILE',
    'REG_OPTION_VOLATILE', 'REG_OPTION_CREATE_LINK',
    'REG_OPTION_BACKUP_RESTORE', 'REG_OPTION_OPEN_LINK',
    'REG_LEGAL_OPTION',
    'REG_CREATED_NEW_KEY', 'REG_OPENED_EXISTING_KEY',
    'REG_WHOLE_HIVE_VOLATILE', 'REG_REFRESH_HIVE',
    'REG_NO_LAZY_FLUSH', 'REG_FORCE_RESTORE',
    'REG_NOTIFY_CHANGE_NAME', 'REG_NOTIFY_CHANGE_ATTRIBUTES',
    'REG_NOTIFY_CHANGE_LAST_SET', 'REG_NOTIFY_CHANGE_SECURITY',
    'REG_LEGAL_CHANGE_FILTER',
    # Functions
    'CloseKey', 'ConnectRegistry', 'CreateKey', 'CreateKeyEx',
    'DeleteKey', 'DeleteKeyEx', 'DeleteValue',
    'EnumKey', 'EnumValue', 'ExpandEnvironmentStrings', 'FlushKey',
    'LoadKey', 'OpenKey', 'OpenKeyEx',
    'QueryInfoKey', 'QueryValue', 'QueryValueEx',
    'SaveKey', 'SetValue', 'SetValueEx',
    'DisableReflectionKey', 'EnableReflectionKey', 'QueryReflectionKey',
    # Invariants
    'winreg2_constants', 'winreg2_hkeytype', 'winreg2_functions',
]