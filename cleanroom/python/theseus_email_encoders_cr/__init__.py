"""Clean-room reimplementation of ``email.encoders``.

Provides the same public callables as the standard library's
``email.encoders`` module, plus probe/invariant functions used by the
Theseus test harness.

This module does NOT import ``email.encoders`` and contains no code
copied from CPython's implementation.  It only relies on lower-level
standard-library primitives (``base64`` and ``quopri``) for the actual
content transfer encoding work, and re-implements the surrounding
message-mutation logic from scratch.
"""

import base64 as _b64
import quopri as _qp


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _set_cte(msg, value):
    """Replace any existing ``Content-Transfer-Encoding`` header."""
    try:
        del msg['Content-Transfer-Encoding']
    except Exception:
        pass
    msg['Content-Transfer-Encoding'] = value


def _b64_encode_bytes(data):
    """Return ``data`` encoded as a base64 ASCII string."""
    if not data:
        return ''
    encoded = _b64.encodebytes(data)
    had_newline = data.endswith(b'\n')
    if not had_newline and encoded.endswith(b'\n'):
        encoded = encoded[:-1]
    return encoded.decode('ascii')


def _qp_encode_bytes(data):
    """Return ``data`` encoded as a quoted-printable text string."""
    if not data:
        return ''
    encoded = _qp.encodestring(data, quotetabs=True)
    return encoded.decode('latin-1')


# ---------------------------------------------------------------------------
# Public encoder functions (mirroring email.encoders)
# ---------------------------------------------------------------------------

def encode_base64(msg):
    """Encode the message's payload in base64 and set the CTE header."""
    payload = msg.get_payload(decode=True)
    if payload is None:
        encoded_text = ''
    else:
        encoded_text = _b64_encode_bytes(payload)
    msg.set_payload(encoded_text)
    _set_cte(msg, 'base64')


def encode_quopri(msg):
    """Encode the message's payload as quoted-printable and set the CTE."""
    payload = msg.get_payload(decode=True)
    if payload is None:
        encoded_text = ''
    else:
        encoded_text = _qp_encode_bytes(payload)
    msg.set_payload(encoded_text)
    _set_cte(msg, 'quoted-printable')


def encode_7or8bit(msg):
    """Set the Content-Transfer-Encoding header to ``7bit`` or ``8bit``."""
    try:
        payload = msg.get_payload(decode=True, compat32=True)
    except TypeError:
        payload = msg.get_payload(decode=True)

    if payload is None:
        _set_cte(msg, '7bit')
        return

    if isinstance(payload, str):
        try:
            payload.encode('ascii')
            _set_cte(msg, '7bit')
            return
        except UnicodeEncodeError:
            _set_cte(msg, '8bit')
            return

    try:
        payload.decode('ascii')
    except (UnicodeDecodeError, UnicodeError, AttributeError):
        _set_cte(msg, '8bit')
    else:
        _set_cte(msg, '7bit')


def encode_noop(msg):
    """Do nothing — included for API parity with ``email.encoders``."""
    return None


# ---------------------------------------------------------------------------
# Lightweight message stub used only by the invariant probes below
# ---------------------------------------------------------------------------

class _StubMessage:
    """Minimal ``email.message.Message``-like object used for testing."""

    def __init__(self, payload=b''):
        self._payload = payload
        self._headers = []

    def get_payload(self, decode=False, compat32=True):
        if decode:
            if self._payload is None:
                return None
            if isinstance(self._payload, str):
                return self._payload.encode('latin-1')
            return self._payload
        return self._payload

    def set_payload(self, value):
        self._payload = value

    def __setitem__(self, name, value):
        self._headers.append((name, value))

    def __getitem__(self, name):
        for k, v in self._headers:
            if k.lower() == name.lower():
                return v
        return None

    def __delitem__(self, name):
        self._headers = [
            (k, v) for (k, v) in self._headers if k.lower() != name.lower()
        ]

    def __contains__(self, name):
        return self[name] is not None


# ---------------------------------------------------------------------------
# Theseus invariant probe functions
# ---------------------------------------------------------------------------

def emailenc2_encode_base64():
    """Probe — exercises ``encode_base64`` on a stub message."""
    msg = _StubMessage(b'Hello, world!')
    encode_base64(msg)
    if msg['Content-Transfer-Encoding'] != 'base64':
        return False
    payload = msg.get_payload()
    if not isinstance(payload, str):
        return False
    try:
        decoded = _b64.decodebytes(payload.encode('ascii'))
    except Exception:
        return False
    return decoded == b'Hello, world!'


def emailenc2_encode_quopri():
    """Probe — exercises ``encode_quopri`` on a stub message."""
    msg = _StubMessage(b'Hello = world!')
    encode_quopri(msg)
    if msg['Content-Transfer-Encoding'] != 'quoted-printable':
        return False
    payload = msg.get_payload()
    if not isinstance(payload, str):
        return False
    return '=3D' in payload


def emailenc2_encode_7or8bit():
    """Probe — exercises ``encode_7or8bit`` on stub messages."""
    seven = _StubMessage(b'plain ascii')
    encode_7or8bit(seven)
    if seven['Content-Transfer-Encoding'] != '7bit':
        return False

    eight = _StubMessage(b'high byte: \xe9')
    encode_7or8bit(eight)
    if eight['Content-Transfer-Encoding'] != '8bit':
        return False

    empty = _StubMessage(None)
    encode_7or8bit(empty)
    return empty['Content-Transfer-Encoding'] == '7bit'


__all__ = [
    'encode_base64',
    'encode_quopri',
    'encode_7or8bit',
    'encode_noop',
    'emailenc2_encode_base64',
    'emailenc2_encode_quopri',
    'emailenc2_encode_7or8bit',
]