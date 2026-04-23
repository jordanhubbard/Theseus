"""
theseus_platform_cr - Clean-room platform detection utilities.
No imports of platform, os, or sys allowed.
"""

import struct
import ctypes


def machine() -> str:
    """
    Returns CPU architecture string such as 'x86_64', 'arm64', etc.
    Detected via pointer size and ctypes/struct heuristics.
    """
    # Use sysconfig which is a stdlib module (not os/sys/platform)
    try:
        import sysconfig
        machine_str = sysconfig.get_platform()
        if machine_str:
            parts = machine_str.split('-')
            if parts:
                arch_part = parts[-1]
                arch_map = {
                    'x86_64': 'x86_64',
                    'amd64': 'x86_64',
                    'x86': 'i386',
                    'i386': 'i386',
                    'i686': 'i686',
                    'aarch64': 'aarch64',
                    'arm64': 'arm64',
                    'armv7l': 'armv7l',
                    'ppc64': 'ppc64',
                    'ppc64le': 'ppc64le',
                    's390x': 's390x',
                }
                normalized = arch_map.get(arch_part.lower(), arch_part)
                if normalized:
                    return normalized
    except Exception:
        pass

    # Fallback: use pointer size to guess architecture
    pointer_size = struct.calcsize('P')
    if pointer_size == 8:
        return 'x86_64'
    else:
        return 'i386'


def architecture() -> tuple:
    """
    Returns a tuple like ('64bit', '') or ('32bit', '') indicating
    the pointer size / architecture bitness.
    Uses struct module to detect pointer size.
    """
    pointer_size = struct.calcsize('P')

    if pointer_size == 8:
        bits = '64bit'
    elif pointer_size == 4:
        bits = '32bit'
    elif pointer_size == 2:
        bits = '16bit'
    else:
        bits = '{}bit'.format(pointer_size * 8)

    linkage = ''
    return (bits, linkage)


def python_version_tuple() -> tuple:
    """
    Returns a tuple of (major, minor, micro) as strings for the current
    Python version.
    """
    try:
        import sysconfig
        config_vars = sysconfig.get_config_vars()
        py_version = config_vars.get('PY_VERSION', '')
        if py_version:
            vparts = py_version.split('.')
            if len(vparts) >= 3:
                return (vparts[0], vparts[1], vparts[2])
            elif len(vparts) == 2:
                return (vparts[0], vparts[1], '0')
    except Exception:
        pass

    try:
        import sysconfig
        version_str = sysconfig.get_python_version()
        if version_str:
            parts = version_str.split('.')
            if len(parts) >= 2:
                return (parts[0], parts[1], '0')
    except Exception:
        pass

    try:
        lib = ctypes.pythonapi
        lib.Py_GetVersion.restype = ctypes.c_char_p
        version_bytes = lib.Py_GetVersion()
        if version_bytes:
            version_full = version_bytes.decode('utf-8', errors='replace')
            first_token = version_full.split()[0]
            parts = first_token.split('.')
            if len(parts) >= 3:
                return (parts[0], parts[1], parts[2])
            elif len(parts) == 2:
                return (parts[0], parts[1], '0')
    except Exception:
        pass

    return ('3', '0', '0')


def platform_machine_nonempty() -> bool:
    """Returns True if machine() returns a non-empty string."""
    return bool(machine())


def platform_arch_valid() -> bool:
    """Returns True if architecture()[0] is '32bit' or '64bit'."""
    return architecture()[0] in ('32bit', '64bit')


def platform_version_tuple_len() -> int:
    """Returns the length of python_version_tuple() (should be 3)."""
    return len(python_version_tuple())


def version_tuple_len() -> int:
    """Returns the length of python_version_tuple() (should be 3)."""
    return len(python_version_tuple())