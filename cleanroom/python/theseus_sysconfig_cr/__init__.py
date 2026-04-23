import sys
import platform
import os

def get_python_version():
    """Return major.minor string like '3.9'."""
    major = sys.version_info.major
    minor = sys.version_info.minor
    return f"{major}.{minor}"

def get_platform():
    """Return platform string like 'linux-x86_64'."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Normalize system name
    if system == 'windows':
        system = 'win'
    elif system == 'darwin':
        system = 'macosx'
        # Try to get macOS version
        mac_ver = platform.mac_ver()[0]
        if mac_ver:
            # Format: macosx-10.15-x86_64
            parts = mac_ver.split('.')
            if len(parts) >= 2:
                system = f"macosx-{parts[0]}.{parts[1]}"
    elif system == 'linux':
        system = 'linux'
    elif system == 'freebsd':
        system = 'freebsd'
    
    # Normalize machine/arch
    if machine in ('x86_64', 'amd64'):
        machine = 'x86_64'
    elif machine in ('i386', 'i686', 'x86'):
        machine = 'i686'
    elif machine in ('aarch64', 'arm64'):
        machine = 'aarch64'
    elif machine.startswith('arm'):
        machine = 'arm'
    
    return f"{system}-{machine}"

def get_scheme_names():
    """Return tuple of known installation scheme names."""
    schemes = (
        'posix_prefix',
        'posix_home',
        'posix_user',
        'nt',
        'nt_user',
        'osx_framework_user',
    )
    return schemes

def get_config_vars():
    """Return dict of config variable name -> value."""
    config = {}
    
    # Python version info
    config['py_version'] = get_python_version()
    config['py_version_short'] = get_python_version()
    config['py_version_nodot'] = f"{sys.version_info.major}{sys.version_info.minor}"
    config['VERSION'] = get_python_version()
    
    # Platform info
    config['MULTIARCH'] = platform.machine()
    config['MACHINE'] = platform.machine()
    config['HOST_GNU_TYPE'] = f"{platform.machine()}-{platform.system().lower()}"
    
    # Python executable
    config['PYTHON'] = sys.executable
    config['prefix'] = sys.prefix
    config['exec_prefix'] = sys.exec_prefix
    config['base'] = sys.prefix
    config['platbase'] = sys.exec_prefix
    
    # Build info
    config['EXT_SUFFIX'] = _get_ext_suffix()
    config['SOABI'] = _get_soabi()
    
    # OS info
    config['OS'] = platform.system()
    config['PLATFORM'] = get_platform()
    
    # Byte order
    config['WORDS_BIGENDIAN'] = 1 if sys.byteorder == 'big' else 0
    
    # Sizeof types (common values)
    config['SIZEOF_LONG'] = 8 if sys.maxsize > 2**32 else 4
    config['SIZEOF_VOID_P'] = 8 if sys.maxsize > 2**32 else 4
    config['SIZEOF_SIZE_T'] = 8 if sys.maxsize > 2**32 else 4
    
    return config

def _get_soabi():
    """Get the SOABI string for shared objects."""
    try:
        impl = sys.implementation
        name = impl.name
        ver = f"{sys.version_info.major}{sys.version_info.minor}"
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == 'linux':
            return f"cpython-{ver}-{machine}-linux-gnu"
        elif system == 'darwin':
            return f"cpython-{ver}-darwin"
        elif system == 'windows':
            return f"cpython-{ver}"
        else:
            return f"cpython-{ver}-{machine}-{system}"
    except Exception:
        ver = f"{sys.version_info.major}{sys.version_info.minor}"
        return f"cpython-{ver}"

def _get_ext_suffix():
    """Get the extension suffix for shared objects."""
    soabi = _get_soabi()
    system = platform.system().lower()
    
    if system == 'windows':
        return f".{soabi}.pyd"
    elif system == 'darwin':
        return f".{soabi}.so"
    else:
        return f".{soabi}.so"


def sysconfig_version_type():
    """Return True if the Python version type (releaselevel) is accessible and valid.
    
    Checks that sys.version_info.releaselevel is one of the known valid values.
    """
    releaselevel = sys.version_info.releaselevel
    valid_levels = ('alpha', 'beta', 'candidate', 'final')
    return releaselevel in valid_levels


def sysconfig_version_format():
    """Return True if a formatted version string can be constructed from sys.version_info.
    
    Validates that major, minor, micro are integers and releaselevel is known.
    """
    try:
        major = sys.version_info.major
        minor = sys.version_info.minor
        micro = sys.version_info.micro
        releaselevel = sys.version_info.releaselevel
        serial = sys.version_info.serial
        
        # Check they are integers
        if not isinstance(major, int):
            return False
        if not isinstance(minor, int):
            return False
        if not isinstance(micro, int):
            return False
        if not isinstance(serial, int):
            return False
        
        base = f"{major}.{minor}.{micro}"
        
        if releaselevel == 'final':
            version_str = base
        elif releaselevel == 'alpha':
            version_str = f"{base}a{serial}"
        elif releaselevel == 'beta':
            version_str = f"{base}b{serial}"
        elif releaselevel == 'candidate':
            version_str = f"{base}rc{serial}"
        else:
            return False
        
        # Verify the string is non-empty and looks valid
        return len(version_str) > 0
    except Exception:
        return False


def sysconfig_scheme_names_nonempty():
    """Return True if the list of scheme names is non-empty, False otherwise."""
    names = get_scheme_names()
    return len(names) > 0


__all__ = [
    'get_python_version',
    'get_platform',
    'get_scheme_names',
    'get_config_vars',
    'sysconfig_version_type',
    'sysconfig_version_format',
    'sysconfig_scheme_names_nonempty',
]