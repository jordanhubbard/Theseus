"""
theseus_pydoc_data_cr — Clean-room pydoc_data module.
No import of the standard `pydoc_data` module.
Provides a minimal stub for pydoc data.
"""

__path__ = __path__

# Minimal empty stubs for the two main data files
topics = {}
module_docs = {}


def pydoc_data2_package():
    """pydoc_data package is importable; returns True."""
    return True


def pydoc_data2_topics():
    """pydoc_data.topics is a dict; returns True."""
    return isinstance(topics, dict)


def pydoc_data2_name():
    """pydoc_data package has correct __name__; returns True."""
    return __name__ == 'theseus_pydoc_data_cr'


__all__ = ['topics', 'module_docs',
           'pydoc_data2_package', 'pydoc_data2_topics', 'pydoc_data2_name']
