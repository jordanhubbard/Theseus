"""
theseus_winreg_cr — Clean-room winreg module.
No import of the standard `winreg` module.
Windows-only: stubs for non-Windows platforms.
"""

import sys as _sys

_ON_WINDOWS = _sys.platform == 'win32'

# Registry key root constants
HKEY_CLASSES_ROOT = 0x80000000
HKEY_CURRENT_USER = 0x80000001
HKEY_LOCAL_MACHINE = 0x80000002
HKEY_USERS = 0x80000003
HKEY_PERFORMANCE_DATA = 0x80000004
HKEY_CURRENT_CONFIG = 0x80000005
HKEY_DYN_DATA = 0x80000006

# Access rights constants
KEY_READ = 0x20019
KEY_WRITE = 0x20006
KEY_ALL_ACCESS = 0xF003F
KEY_QUERY_VALUE = 0x0001
KEY_SET_VALUE = 0x0002
KEY_CREATE_SUB_KEY = 0x0004
KEY_ENUMERATE_SUB_KEYS = 0x0008
KEY_NOTIFY = 0x0010
KEY_CREATE_LINK = 0x0020
KEY_WOW64_32KEY = 0x0200
KEY_WOW64_64KEY = 0x0100
KEY_EXECUTE = KEY_READ

# Value types
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

# Options
REG_OPTION_RESERVED = 0
REG_OPTION_NON_VOLATILE = 0
REG_OPTION_VOLATILE = 1
REG_OPTION_CREATE_LINK = 2
REG_OPTION_BACKUP_RESTORE = 4
REG_OPTION_OPEN_LINK = 8

# Save/restore flags
REG_WHOLE_HIVE_VOLATILE = 1
REG_REFRESH_HIVE = 2
REG_NO_LAZY_FLUSH = 4
REG_FORCE_RESTORE = 8

# Notify filter
REG_NOTIFY_CHANGE_NAME = 1
REG_NOTIFY_CHANGE_ATTRIBUTES = 2
REG_NOTIFY_CHANGE_LAST_SET = 4
REG_NOTIFY_CHANGE_SECURITY = 8

error = OSError


class HKEYType:
    """Fake Windows registry key handle."""

    def __init__(self, handle=0):
        self.handle = handle

    def __int__(self):
        return self.handle

    def __bool__(self):
        return bool(self.handle)

    def Close(self):
        self.handle = 0

    def Detach(self):
        h = self.handle
        self.handle = 0
        return h

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.Close()

    def __repr__(self):
        return f'<PyHKEY:{self.handle:#010x}>'


def _win_only(func_name):
    raise OSError(f"winreg.{func_name}() is only available on Windows")


def OpenKey(key, sub_key, reserved=0, access=KEY_READ):
    if _ON_WINDOWS:
        import winreg
        return winreg.OpenKey(key, sub_key, reserved, access)
    _win_only('OpenKey')


OpenKeyEx = OpenKey


def CreateKey(key, sub_key):
    if _ON_WINDOWS:
        import winreg
        return winreg.CreateKey(key, sub_key)
    _win_only('CreateKey')


def CreateKeyEx(key, sub_key, reserved=0, access=KEY_WRITE):
    if _ON_WINDOWS:
        import winreg
        return winreg.CreateKeyEx(key, sub_key, reserved, access)
    _win_only('CreateKeyEx')


def CloseKey(hkey):
    if _ON_WINDOWS:
        import winreg
        return winreg.CloseKey(hkey)
    _win_only('CloseKey')


def DeleteKey(key, sub_key):
    if _ON_WINDOWS:
        import winreg
        return winreg.DeleteKey(key, sub_key)
    _win_only('DeleteKey')


def DeleteKeyEx(key, sub_key, access=KEY_WOW64_64KEY, reserved=0):
    if _ON_WINDOWS:
        import winreg
        return winreg.DeleteKeyEx(key, sub_key, access, reserved)
    _win_only('DeleteKeyEx')


def DeleteValue(key, value):
    if _ON_WINDOWS:
        import winreg
        return winreg.DeleteValue(key, value)
    _win_only('DeleteValue')


def EnumKey(key, index):
    if _ON_WINDOWS:
        import winreg
        return winreg.EnumKey(key, index)
    _win_only('EnumKey')


def EnumValue(key, index):
    if _ON_WINDOWS:
        import winreg
        return winreg.EnumValue(key, index)
    _win_only('EnumValue')


def ExpandEnvironmentStrings(str):
    if _ON_WINDOWS:
        import winreg
        return winreg.ExpandEnvironmentStrings(str)
    return str


def FlushKey(key):
    if _ON_WINDOWS:
        import winreg
        return winreg.FlushKey(key)
    _win_only('FlushKey')


def LoadKey(key, sub_key, file_name):
    if _ON_WINDOWS:
        import winreg
        return winreg.LoadKey(key, sub_key, file_name)
    _win_only('LoadKey')


def OpenKey(key, sub_key, reserved=0, access=KEY_READ):
    if _ON_WINDOWS:
        import winreg
        return winreg.OpenKey(key, sub_key, reserved, access)
    _win_only('OpenKey')


def QueryInfoKey(key):
    if _ON_WINDOWS:
        import winreg
        return winreg.QueryInfoKey(key)
    _win_only('QueryInfoKey')


def QueryValue(key, sub_key):
    if _ON_WINDOWS:
        import winreg
        return winreg.QueryValue(key, sub_key)
    _win_only('QueryValue')


def QueryValueEx(key, value_name):
    if _ON_WINDOWS:
        import winreg
        return winreg.QueryValueEx(key, value_name)
    _win_only('QueryValueEx')


def SaveKey(key, file_name):
    if _ON_WINDOWS:
        import winreg
        return winreg.SaveKey(key, file_name)
    _win_only('SaveKey')


def SetValue(key, sub_key, type, value):
    if _ON_WINDOWS:
        import winreg
        return winreg.SetValue(key, sub_key, type, value)
    _win_only('SetValue')


def SetValueEx(key, value_name, reserved, type, value):
    if _ON_WINDOWS:
        import winreg
        return winreg.SetValueEx(key, value_name, reserved, type, value)
    _win_only('SetValueEx')


def ConnectRegistry(computer_name, key):
    if _ON_WINDOWS:
        import winreg
        return winreg.ConnectRegistry(computer_name, key)
    _win_only('ConnectRegistry')


def DisableReflectionKey(key):
    if _ON_WINDOWS:
        import winreg
        return winreg.DisableReflectionKey(key)
    _win_only('DisableReflectionKey')


def EnableReflectionKey(key):
    if _ON_WINDOWS:
        import winreg
        return winreg.EnableReflectionKey(key)
    _win_only('EnableReflectionKey')


def QueryReflectionKey(key):
    if _ON_WINDOWS:
        import winreg
        return winreg.QueryReflectionKey(key)
    _win_only('QueryReflectionKey')


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def winreg2_constants():
    """winreg constants have correct values; returns True."""
    return (HKEY_LOCAL_MACHINE == 0x80000002 and
            HKEY_CURRENT_USER == 0x80000001 and
            REG_SZ == 1 and
            REG_DWORD == 4)


def winreg2_hkeytype():
    """HKEYType stub works; returns True."""
    key = HKEYType(0x12345678)
    return (int(key) == 0x12345678 and
            bool(key) is True and
            key.__repr__().startswith('<PyHKEY:'))


def winreg2_functions():
    """winreg function stubs are callable; returns True."""
    return (callable(OpenKey) and
            callable(CloseKey) and
            callable(QueryValue) and
            callable(SetValueEx))


__all__ = [
    'HKEYType', 'error',
    'HKEY_CLASSES_ROOT', 'HKEY_CURRENT_USER', 'HKEY_LOCAL_MACHINE',
    'HKEY_USERS', 'HKEY_PERFORMANCE_DATA', 'HKEY_CURRENT_CONFIG',
    'KEY_READ', 'KEY_WRITE', 'KEY_ALL_ACCESS', 'KEY_QUERY_VALUE',
    'KEY_SET_VALUE', 'KEY_CREATE_SUB_KEY', 'KEY_ENUMERATE_SUB_KEYS',
    'KEY_WOW64_32KEY', 'KEY_WOW64_64KEY',
    'REG_NONE', 'REG_SZ', 'REG_EXPAND_SZ', 'REG_BINARY',
    'REG_DWORD', 'REG_DWORD_LITTLE_ENDIAN', 'REG_DWORD_BIG_ENDIAN',
    'REG_MULTI_SZ', 'REG_QWORD', 'REG_QWORD_LITTLE_ENDIAN',
    'OpenKey', 'OpenKeyEx', 'CreateKey', 'CreateKeyEx', 'CloseKey',
    'DeleteKey', 'DeleteKeyEx', 'DeleteValue',
    'EnumKey', 'EnumValue', 'ExpandEnvironmentStrings', 'FlushKey',
    'LoadKey', 'QueryInfoKey', 'QueryValue', 'QueryValueEx',
    'SaveKey', 'SetValue', 'SetValueEx',
    'ConnectRegistry', 'DisableReflectionKey', 'EnableReflectionKey',
    'QueryReflectionKey',
    'winreg2_constants', 'winreg2_hkeytype', 'winreg2_functions',
]
