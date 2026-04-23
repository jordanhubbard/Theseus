"""
theseus_xml_cr — Clean-room xml namespace package.
No import of the standard `xml` module.
The xml package is an empty namespace; sub-packages provide functionality.
"""

# xml is an empty namespace package; no exports

__path__ = __path__  # make this a package


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def xml2_package():
    """xml package is importable as a namespace; returns True."""
    return True


def xml2_name():
    """xml package has correct __name__; returns True."""
    return __name__ == 'theseus_xml_cr'


def xml2_path():
    """xml package has __path__ (is a package); returns True."""
    return hasattr(__path__, '__iter__')


__all__ = ['xml2_package', 'xml2_name', 'xml2_path']
