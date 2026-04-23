"""
theseus_urllib_cr — Clean-room urllib namespace package.
No import of the standard `urllib` module.
The urllib package is an empty namespace; sub-packages provide functionality.
"""

__path__ = __path__  # make this a package


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def urllib2_package():
    """urllib package is importable as a namespace; returns True."""
    return True


def urllib2_name():
    """urllib package has correct __name__; returns True."""
    return __name__ == 'theseus_urllib_cr'


def urllib2_path():
    """urllib package has __path__ (is a package); returns True."""
    return hasattr(__path__, '__iter__')


__all__ = ['urllib2_package', 'urllib2_name', 'urllib2_path']
