"""
theseus_email_encoders_cr — Clean-room email.encoders module.
No import of the standard `email.encoders` module.
"""

import base64 as _base64
import quopri as _quopri
import io as _io


def encode_base64(msg):
    """Encode a message's payload in Base64.
    Sets Content-Transfer-Encoding to 'base64'.
    """
    payload = msg.get_payload(decode=True)
    if payload is None:
        return
    encoded = _base64.encodebytes(payload)
    msg.set_payload(encoded)
    msg['Content-Transfer-Encoding'] = 'base64'


def encode_quopri(msg):
    """Encode a message's payload in quoted-printable.
    Sets Content-Transfer-Encoding to 'quoted-printable'.
    """
    payload = msg.get_payload(decode=True)
    if payload is None:
        return
    encoded = _quopri.encodestring(payload)
    msg.set_payload(encoded)
    msg['Content-Transfer-Encoding'] = 'quoted-printable'


def encode_7or8bit(msg):
    """Set the Content-Transfer-Encoding to 7bit or 8bit.
    Looks at the current payload to determine which.
    """
    payload = msg.get_payload(decode=True)
    if payload is None:
        msg['Content-Transfer-Encoding'] = '7bit'
        return
    if isinstance(payload, str):
        payload = payload.encode('ascii', 'surrogateescape')
    try:
        payload.decode('ascii')
        msg['Content-Transfer-Encoding'] = '7bit'
    except (UnicodeDecodeError, AttributeError):
        msg['Content-Transfer-Encoding'] = '8bit'


def encode_noop(msg):
    """Do nothing — let the payload pass through unchanged."""
    pass


# ---------------------------------------------------------------------------
# Helper message stub for testing (avoids importing email)
# ---------------------------------------------------------------------------

class _SimpleMsg:
    """Minimal email message stub for testing."""
    def __init__(self, payload=b'hello world'):
        self._payload = payload
        self._headers = {}

    def get_payload(self, decode=False):
        if decode:
            return self._payload
        return self._payload.decode('ascii', 'replace') if isinstance(self._payload, bytes) else self._payload

    def set_payload(self, payload):
        self._payload = payload

    def __setitem__(self, key, val):
        self._headers[key] = val

    def __getitem__(self, key):
        return self._headers.get(key)

    def __contains__(self, key):
        return key in self._headers


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailenc2_encode_base64():
    """encode_base64() encodes a message part in base64; returns True."""
    msg = _SimpleMsg(b'Hello, world!')
    encode_base64(msg)
    return (msg['Content-Transfer-Encoding'] == 'base64' and
            isinstance(msg.get_payload(), (bytes, str)))


def emailenc2_encode_quopri():
    """encode_quopri() encodes a message part in QP; returns True."""
    msg = _SimpleMsg(b'Hello, world!')
    encode_quopri(msg)
    return msg['Content-Transfer-Encoding'] == 'quoted-printable'


def emailenc2_encode_7or8bit():
    """encode_7or8bit() sets content-transfer-encoding; returns True."""
    msg = _SimpleMsg(b'Hello, world!')
    encode_7or8bit(msg)
    return msg['Content-Transfer-Encoding'] in ('7bit', '8bit')


__all__ = [
    'encode_base64', 'encode_quopri', 'encode_7or8bit', 'encode_noop',
    'emailenc2_encode_base64', 'emailenc2_encode_quopri', 'emailenc2_encode_7or8bit',
]
