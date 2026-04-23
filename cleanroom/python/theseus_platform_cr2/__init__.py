import sys
import os


def python_version() -> str:
    """Return current Python version as string 'X.Y.Z'."""
    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro
    return f"{major}.{minor}.{micro}"


def python_version_tuple() -> tuple:
    """Return (major, minor, micro) as strings."""
    major = str(sys.version_info.major)
    minor = str(sys.version_info.minor)
    micro = str(sys.version_info.micro)
    return (major, minor, micro)


def machine() -> str:
    """Return machine type string (e.g. 'x86_64', 'arm64')."""
    try:
        return os.uname().machine
    except AttributeError:
        # Fallback for platforms that don't support os.uname() (e.g., Windows)
        # Try to determine from sys.platform and other hints
        import struct
        bits = struct.calcsize("P") * 8
        platform = sys.platform
        if platform.startswith("win"):
            if bits == 64:
                return "AMD64"
            else:
                return "x86"
        return "unknown"


def platform2_version_type() -> bool:
    """Return True if python_version() returns a str."""
    return isinstance(python_version(), str)


def platform2_version_format() -> bool:
    """Return True if python_version() has exactly 3 dot-separated parts."""
    return len(python_version().split('.')) == 3


def platform2_machine_str() -> bool:
    """Return True if machine() returns a str."""
    return isinstance(machine(), str)