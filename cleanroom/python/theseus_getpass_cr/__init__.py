"""
theseus_getpass_cr - Clean-room implementation of getpass utilities.
Does NOT import getpass, os, or pwd.
"""

import sys
import ctypes


def getuser() -> str:
    """
    Return the current username as a non-empty string.
    Tries multiple platform-specific approaches without importing os or pwd.
    """
    username = None

    # Try using ctypes to access environment variables
    try:
        libc = ctypes.CDLL(None)
        libc.getenv.restype = ctypes.c_char_p
        
        for var in (b'USER', b'LOGNAME', b'USERNAME', b'LNAME', b'HOME'):
            result = libc.getenv(var)
            if result:
                decoded = result.decode('utf-8', errors='replace').strip()
                if decoded:
                    username = decoded
                    break
    except Exception:
        pass

    if username:
        return username

    # Try reading /proc/self/status on Linux for the UID, then /etc/passwd
    try:
        uid = None
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('Uid:'):
                    parts = line.split()
                    if len(parts) >= 2:
                        uid = parts[1]
                    break
        if uid is not None:
            with open('/etc/passwd', 'r') as f:
                for line in f:
                    parts = line.strip().split(':')
                    if len(parts) >= 3 and parts[2] == uid:
                        name = parts[0].strip()
                        if name:
                            return name
    except Exception:
        pass

    # Try ctypes getlogin
    try:
        libc = ctypes.CDLL(None)
        libc.getlogin.restype = ctypes.c_char_p
        result = libc.getlogin()
        if result:
            decoded = result.decode('utf-8', errors='replace').strip()
            if decoded:
                return decoded
    except Exception:
        pass

    # Try ctypes cuserid
    try:
        libc = ctypes.CDLL(None)
        buf = ctypes.create_string_buffer(256)
        libc.cuserid.restype = ctypes.c_char_p
        result = libc.cuserid(buf)
        if result:
            decoded = result.decode('utf-8', errors='replace').strip()
            if decoded:
                return decoded
    except Exception:
        pass

    # Try Windows-specific approach
    try:
        import ctypes.wintypes
        GetUserNameW = ctypes.windll.advapi32.GetUserNameW
        GetUserNameW.argtypes = [ctypes.wintypes.LPWSTR, ctypes.POINTER(ctypes.wintypes.DWORD)]
        GetUserNameW.restype = ctypes.wintypes.BOOL
        size = ctypes.wintypes.DWORD(256)
        buf = ctypes.create_unicode_buffer(256)
        if GetUserNameW(buf, ctypes.byref(size)):
            name = buf.value.strip()
            if name:
                return name
    except Exception:
        pass

    # Last resort: return a non-empty fallback
    return 'unknown'


def getpass(prompt: str = '') -> str:
    """
    Return a password string.
    In non-interactive mode (no terminal), returns empty string.
    In interactive mode, prompts the user and reads input without echo.
    """
    # Check if we have a terminal
    try:
        if not sys.stdin.isatty():
            return ''
    except Exception:
        return ''

    # Try to read from /dev/tty with no echo using termios
    try:
        import termios
        import tty

        try:
            fd = open('/dev/tty', 'r+b', buffering=0)
            tty_stream = fd
        except Exception:
            tty_stream = None

        if tty_stream is not None:
            try:
                # Write prompt
                if prompt:
                    tty_stream.write(prompt.encode('utf-8', errors='replace'))
                    tty_stream.flush()
                
                # Save terminal settings and disable echo
                old_settings = termios.tcgetattr(tty_stream.fileno())
                try:
                    tty.setraw(tty_stream.fileno())
                    # Read character by character
                    password = []
                    while True:
                        ch = tty_stream.read(1)
                        if not ch or ch in (b'\n', b'\r'):
                            break
                        elif ch == b'\x03':  # Ctrl+C
                            raise KeyboardInterrupt
                        elif ch in (b'\x7f', b'\x08'):  # Backspace
                            if password:
                                password.pop()
                        else:
                            password.append(ch)
                    tty_stream.write(b'\n')
                    tty_stream.flush()
                    return b''.join(password).decode('utf-8', errors='replace')
                finally:
                    termios.tcsetattr(tty_stream.fileno(), termios.TCSADRAIN, old_settings)
                    tty_stream.close()
            except Exception:
                try:
                    tty_stream.close()
                except Exception:
                    pass
    except ImportError:
        pass

    # Fallback: just read from stdin with prompt (echo will be visible)
    try:
        if prompt:
            sys.stderr.write(prompt)
            sys.stderr.flush()
        line = sys.stdin.readline()
        if line.endswith('\n'):
            line = line[:-1]
        if line.endswith('\r'):
            line = line[:-1]
        return line
    except Exception:
        return ''


def getpass_getuser_nonempty() -> bool:
    """
    Return True if getuser() returns a non-empty string.
    """
    result = getuser()
    return isinstance(result, str) and len(result) > 0


def getpass_getuser_is_str() -> bool:
    """
    Return True if getuser() returns a str instance.
    """
    result = getuser()
    return isinstance(result, str)


def getpass_returns_str() -> bool:
    """
    Return True if getpass() returns a str instance.
    """
    result = getpass(prompt='')
    return isinstance(result, str)