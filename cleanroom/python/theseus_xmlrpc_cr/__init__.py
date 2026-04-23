"""
theseus_xmlrpc_cr — Clean-room xmlrpc namespace package.
No import of the standard `xmlrpc` module.
The xmlrpc package is an empty namespace; sub-packages provide functionality.
"""

__path__ = __path__  # make this a package


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xmlrpc2_package():
    """xmlrpc package is importable as a namespace; returns True."""
    return True


def xmlrpc2_name():
    """xmlrpc package has correct __name__; returns True."""
    return __name__ == 'theseus_xmlrpc_cr'


def xmlrpc2_path():
    """xmlrpc package has __path__ (is a package); returns True."""
    return hasattr(__path__, '__iter__')


__all__ = ['xmlrpc2_package', 'xmlrpc2_name', 'xmlrpc2_path']
