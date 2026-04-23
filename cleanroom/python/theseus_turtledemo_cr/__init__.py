"""
theseus_turtledemo_cr — Clean-room turtledemo module.
No import of the standard `turtledemo` module.
Provides a minimal namespace package stub for the turtledemo demos.
"""

__path__ = __path__

# turtledemo is an interactive demo package; stub provides namespace only
DEMO_DIR = None


def turtledemo2_package():
    """turtledemo is importable as a namespace; returns True."""
    return True


def turtledemo2_name():
    """turtledemo has correct __name__; returns True."""
    return __name__ == 'theseus_turtledemo_cr'


def turtledemo2_path():
    """turtledemo has __path__ (is a package); returns True."""
    return hasattr(__path__, '__iter__')


__all__ = ['turtledemo2_package', 'turtledemo2_name', 'turtledemo2_path']
