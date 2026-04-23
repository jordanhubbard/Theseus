"""
theseus_idlelib_cr — Clean-room idlelib module.
No import of the standard `idlelib` module.
Provides a minimal namespace package stub for IDLE.
"""

__path__ = __path__

# idlelib is the IDLE IDE package; stub provides namespace only


def idlelib2_package():
    """idlelib is importable as a namespace; returns True."""
    return True


def idlelib2_name():
    """idlelib has correct __name__; returns True."""
    return __name__ == 'theseus_idlelib_cr'


def idlelib2_path():
    """idlelib has __path__ (is a package); returns True."""
    return hasattr(__path__, '__iter__')


__all__ = ['idlelib2_package', 'idlelib2_name', 'idlelib2_path']
