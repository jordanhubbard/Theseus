"""Clean-room reimplementation of nntplib's public surface.

This module provides the exception hierarchy and namedtuple types that
nntplib exposes, without importing the original module.
"""

from collections import namedtuple


# --------------------------------------------------------------------------
# Exception hierarchy
# --------------------------------------------------------------------------

class NNTPError(Exception):
    """Base class for all NNTP-related exceptions."""

    def __init__(self, *args):
        Exception.__init__(self, *args)
        try:
            self.response = args[0]
        except IndexError:
            self.response = 'No response given'


class NNTPReplyError(NNTPError):
    """Unexpected [123]xx reply."""
    pass


class NNTPTemporaryError(NNTPReplyError):
    """4xx errors."""
    pass


class NNTPPermanentError(NNTPReplyError):
    """5xx errors."""
    pass


class NNTPProtocolError(NNTPError):
    """Response does not begin with [1-5]."""
    pass


class NNTPDataError(NNTPError):
    """Error in response data."""
    pass


# --------------------------------------------------------------------------
# Named tuples
# --------------------------------------------------------------------------

GroupInfo = namedtuple('GroupInfo', ['group', 'last', 'first', 'flag'])

ArticleInfo = namedtuple('ArticleInfo', ['number', 'message_id', 'lines'])


# --------------------------------------------------------------------------
# Default port
# --------------------------------------------------------------------------

NNTP_PORT = 119
NNTP_SSL_PORT = 563


# --------------------------------------------------------------------------
# Invariant verification helpers
# --------------------------------------------------------------------------

def nntplib2_exceptions():
    """Verify the NNTP exception hierarchy is correct."""
    # NNTPError is base and inherits from Exception
    if not issubclass(NNTPError, Exception):
        return False
    # Subclasses inherit from NNTPError
    for cls in (NNTPReplyError, NNTPProtocolError, NNTPDataError):
        if not issubclass(cls, NNTPError):
            return False
    # Temporary and Permanent inherit from NNTPReplyError
    for cls in (NNTPTemporaryError, NNTPPermanentError):
        if not issubclass(cls, NNTPReplyError):
            return False
    # Each is distinct
    classes = [
        NNTPError, NNTPReplyError, NNTPTemporaryError,
        NNTPPermanentError, NNTPProtocolError, NNTPDataError,
    ]
    if len(set(classes)) != len(classes):
        return False
    # Instances carry the response attribute
    try:
        err = NNTPError('500 server error')
        if err.response != '500 server error':
            return False
        empty = NNTPError()
        if empty.response != 'No response given':
            return False
    except Exception:
        return False
    return True


def nntplib2_groupinfo():
    """Verify the GroupInfo namedtuple has the right shape."""
    if GroupInfo._fields != ('group', 'last', 'first', 'flag'):
        return False
    info = GroupInfo('comp.lang.python', '100', '1', 'y')
    if info.group != 'comp.lang.python':
        return False
    if info.last != '100':
        return False
    if info.first != '1':
        return False
    if info.flag != 'y':
        return False
    if tuple(info) != ('comp.lang.python', '100', '1', 'y'):
        return False
    return True


def nntplib2_articleinfo():
    """Verify the ArticleInfo namedtuple has the right shape."""
    if ArticleInfo._fields != ('number', 'message_id', 'lines'):
        return False
    art = ArticleInfo(42, '<abc@example.com>', [b'line1', b'line2'])
    if art.number != 42:
        return False
    if art.message_id != '<abc@example.com>':
        return False
    if art.lines != [b'line1', b'line2']:
        return False
    if tuple(art) != (42, '<abc@example.com>', [b'line1', b'line2']):
        return False
    return True


__all__ = [
    'NNTPError',
    'NNTPReplyError',
    'NNTPTemporaryError',
    'NNTPPermanentError',
    'NNTPProtocolError',
    'NNTPDataError',
    'GroupInfo',
    'ArticleInfo',
    'NNTP_PORT',
    'NNTP_SSL_PORT',
    'nntplib2_exceptions',
    'nntplib2_groupinfo',
    'nntplib2_articleinfo',
]