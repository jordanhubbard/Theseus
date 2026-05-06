"""Clean-room implementation of email.iterators.

Provides iterators over the parts of a MIME message tree. These functions
operate on email.message.Message-compatible objects via their public API
(is_multipart, get_payload, get_content_maintype, get_content_subtype,
get_content_type, get_default_type), so no email-package internals are
imported here.
"""

import sys
from io import StringIO


__all__ = [
    'walk',
    'body_line_iterator',
    'typed_subpart_iterator',
    'emailitr2_walk',
    'emailitr2_body_line',
    'emailitr2_typed_subpart',
]


def walk(self):
    """Walk over the message tree, yielding each subpart.

    The walk is performed in depth-first order. This is a generator.
    """
    yield self
    if self.is_multipart():
        for subpart in self.get_payload():
            yield from walk(subpart)


def body_line_iterator(msg, decode=False):
    """Iterate over the parts, returning string payloads line-by-line.

    Optional ``decode`` (default ``False``) is passed through to
    :meth:`Message.get_payload`.
    """
    for subpart in walk(msg):
        payload = subpart.get_payload(decode=decode)
        if isinstance(payload, str):
            for line in StringIO(payload):
                yield line


def typed_subpart_iterator(msg, maintype='text', subtype=None):
    """Iterate over the subparts with a given MIME content type.

    ``maintype`` is the main MIME type to match against (defaults to
    ``"text"``). Optional ``subtype`` is the MIME subtype to match; if
    omitted, only the main type is matched.
    """
    for subpart in walk(msg):
        if subpart.get_content_maintype() == maintype:
            if subtype is None or subpart.get_content_subtype() == subtype:
                yield subpart


class _Message:
    def __init__(self, content_type='text/plain', payload='', parts=None):
        self._content_type = content_type
        self._payload = payload
        self._parts = list(parts or [])

    def is_multipart(self):
        return bool(self._parts)

    def get_payload(self, decode=False):
        return self._parts if self._parts else self._payload

    def get_content_maintype(self):
        return self._content_type.split('/', 1)[0]

    def get_content_subtype(self):
        parts = self._content_type.split('/', 1)
        return parts[1] if len(parts) == 2 else 'plain'

    def get_content_type(self):
        return self._content_type

    def get_default_type(self):
        return 'text/plain'


def _sample_message():
    text = _Message('text/plain', 'hello\nworld\n')
    html = _Message('text/html', '<p>hello</p>\n')
    return _Message('multipart/mixed', parts=[text, html])


def emailitr2_walk():
    msg = _sample_message()
    return [part.get_content_type() for part in walk(msg)] == [
        'multipart/mixed',
        'text/plain',
        'text/html',
    ]


def emailitr2_body_line():
    return list(body_line_iterator(_sample_message()))[:2] == [
        'hello\n',
        'world\n',
    ]


def emailitr2_typed_subpart():
    parts = list(typed_subpart_iterator(_sample_message(), 'text', 'html'))
    return len(parts) == 1 and parts[0].get_content_type() == 'text/html'


def _structure(msg, fp=None, level=0, include_default=False):
    """A handy debugging aid that prints the MIME structure of ``msg``."""
    if fp is None:
        fp = sys.stdout
    tab = ' ' * (level * 4)
    print(tab + msg.get_content_type(), end='', file=fp)
    if include_default:
        print(' [%s]' % msg.get_default_type(), file=fp)
    else:
        print(file=fp)
    if msg.is_multipart():
        for subpart in msg.get_payload():
            _structure(subpart, fp, level + 1, include_default)
