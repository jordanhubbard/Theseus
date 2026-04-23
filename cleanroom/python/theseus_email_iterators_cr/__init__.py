"""
theseus_email_iterators_cr — Clean-room email.iterators module.
No import of the standard `email.iterators` module.
"""

import sys as _sys
import io as _io


def body_line_iterator(msg, decode=False):
    """Iterate over the lines of the message's payload."""
    for subpart in msg.walk():
        payload = subpart.get_payload(decode=decode)
        if isinstance(payload, str):
            for line in _io.StringIO(payload):
                yield line
        elif isinstance(payload, bytes):
            for line in _io.BytesIO(payload):
                yield line.decode('ascii', 'replace')


def typed_subpart_iterator(msg, maintype='text', subtype=None):
    """Iterate over the subparts matching the given MIME type."""
    for subpart in msg.walk():
        if subpart.get_content_maintype() == maintype:
            if subtype is None or subpart.get_content_subtype() == subtype:
                yield subpart


def walk(msg):
    """Recursively walk through the parts of a multipart message."""
    yield msg
    payload = msg.get_payload()
    if isinstance(payload, list):
        for subpart in payload:
            yield from walk(subpart)


# ---------------------------------------------------------------------------
# Stub message for testing
# ---------------------------------------------------------------------------

class _StubMessage:
    """Minimal message stub for invariant testing."""

    def __init__(self, payload='Hello, world!\nSecond line.\n', content_type='text/plain'):
        self._payload = payload
        self._content_type = content_type
        self._subparts = []

    def get_payload(self, decode=False):
        if decode and isinstance(self._payload, str):
            return self._payload.encode('ascii')
        return self._payload

    def get_content_maintype(self):
        return self._content_type.split('/')[0]

    def get_content_subtype(self):
        return self._content_type.split('/')[1]

    def walk(self):
        yield self
        for p in self._subparts:
            yield from p.walk() if hasattr(p, 'walk') else [p]

    def attach(self, subpart):
        self._subparts.append(subpart)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailitr2_body_line():
    """body_line_iterator() iterates over message body lines; returns True."""
    msg = _StubMessage('Line one.\nLine two.\n')
    lines = list(body_line_iterator(msg))
    return len(lines) == 2 and 'Line one.' in lines[0]


def emailitr2_typed_subpart():
    """typed_subpart_iterator() filters subparts by type; returns True."""
    msg = _StubMessage('Body text', 'text/plain')
    parts = list(typed_subpart_iterator(msg, 'text'))
    return len(parts) == 1 and parts[0] is msg


def emailitr2_walk():
    """walk() iterates over all message parts; returns True."""
    msg = _StubMessage('Body')
    parts = list(walk(msg))
    return len(parts) >= 1 and parts[0] is msg


__all__ = [
    'body_line_iterator', 'typed_subpart_iterator', 'walk',
    'emailitr2_body_line', 'emailitr2_typed_subpart', 'emailitr2_walk',
]
