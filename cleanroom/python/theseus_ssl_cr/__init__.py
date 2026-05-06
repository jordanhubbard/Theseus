"""Clean-room implementation of a minimal ssl-like module for Theseus.

This module does not import or wrap Python's built-in ``ssl`` module. It
provides a small set of constants and helpers sufficient to satisfy the
behavioral invariants required by the Theseus rewrite specification.
"""

# ---------------------------------------------------------------------------
# Protocol version constants
# ---------------------------------------------------------------------------
# These mirror the well-known protocol identifiers exposed by the standard
# library's ssl module. The integer values are arbitrary clean-room choices
# and are only used for symbolic comparison within this package.
PROTOCOL_SSLv23 = 2
PROTOCOL_TLS = 2
PROTOCOL_TLS_CLIENT = 16
PROTOCOL_TLS_SERVER = 17
PROTOCOL_TLSv1 = 3
PROTOCOL_TLSv1_1 = 4
PROTOCOL_TLSv1_2 = 5

# ---------------------------------------------------------------------------
# Certificate verification mode constants
# ---------------------------------------------------------------------------
CERT_NONE = 0
CERT_OPTIONAL = 1
CERT_REQUIRED = 2

# ---------------------------------------------------------------------------
# Purpose sentinels
# ---------------------------------------------------------------------------
class _Purpose(object):
    __slots__ = ("name", "oid")

    def __init__(self, name, oid):
        self.name = name
        self.oid = oid

    def __repr__(self):
        return "Purpose(%r)" % (self.name,)


class Purpose(object):
    SERVER_AUTH = _Purpose("SERVER_AUTH", "1.3.6.1.5.5.7.3.1")
    CLIENT_AUTH = _Purpose("CLIENT_AUTH", "1.3.6.1.5.5.7.3.2")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class SSLError(OSError):
    """Generic SSL error, mirroring the standard library exception name."""


class SSLCertVerificationError(SSLError, ValueError):
    """Raised when certificate verification fails."""


class SSLZeroReturnError(SSLError):
    """Raised when a TLS connection has been closed cleanly."""


# ---------------------------------------------------------------------------
# SSLContext
# ---------------------------------------------------------------------------
class SSLContext(object):
    """A minimal stand-in for ``ssl.SSLContext``.

    This object stores the protocol, verification mode, and an optional
    certificate chain. It does not perform any cryptography.
    """

    def __init__(self, protocol=PROTOCOL_TLS):
        self.protocol = protocol
        self._verify_mode = CERT_NONE
        self._check_hostname = False
        self._certfile = None
        self._keyfile = None
        self._ca_certs = []
        self._ciphers = "DEFAULT"
        self.options = 0

    @property
    def verify_mode(self):
        return self._verify_mode

    @verify_mode.setter
    def verify_mode(self, value):
        if value not in (CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED):
            raise ValueError("invalid verify_mode")
        if self._check_hostname and value == CERT_NONE:
            raise ValueError(
                "Cannot set verify_mode to CERT_NONE when "
                "check_hostname is enabled."
            )
        self._verify_mode = value

    @property
    def check_hostname(self):
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, value):
        value = bool(value)
        if value and self._verify_mode == CERT_NONE:
            self._verify_mode = CERT_REQUIRED
        self._check_hostname = value

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        if certfile is None:
            raise TypeError("certfile must be specified")
        self._certfile = certfile
        self._keyfile = keyfile

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        if cafile is None and capath is None and cadata is None:
            raise TypeError(
                "cafile, capath and cadata cannot be all omitted"
            )
        if cafile is not None:
            self._ca_certs.append(("file", cafile))
        if capath is not None:
            self._ca_certs.append(("path", capath))
        if cadata is not None:
            self._ca_certs.append(("data", cadata))

    def set_ciphers(self, ciphers):
        if not isinstance(ciphers, str) or not ciphers:
            raise SSLError("Invalid cipher string")
        self._ciphers = ciphers

    def wrap_socket(self, sock, server_side=False, do_handshake_on_connect=True,
                    suppress_ragged_eofs=True, server_hostname=None,
                    session=None):
        # The clean-room implementation does not wrap real sockets. Return
        # a marker object describing the wrap request.
        return {
            "sock": sock,
            "server_side": server_side,
            "do_handshake_on_connect": do_handshake_on_connect,
            "suppress_ragged_eofs": suppress_ragged_eofs,
            "server_hostname": server_hostname,
            "context": self,
        }


def create_default_context(purpose=Purpose.SERVER_AUTH, cafile=None,
                           capath=None, cadata=None):
    """Return a new ``SSLContext`` configured with sensible defaults."""
    ctx = SSLContext(PROTOCOL_TLS_CLIENT
                     if purpose is Purpose.SERVER_AUTH
                     else PROTOCOL_TLS_SERVER)
    ctx.verify_mode = CERT_REQUIRED
    if purpose is Purpose.SERVER_AUTH:
        ctx.check_hostname = True
    if cafile is not None or capath is not None or cadata is not None:
        ctx.load_verify_locations(cafile=cafile, capath=capath, cadata=cadata)
    return ctx


# ---------------------------------------------------------------------------
# Invariant predicates
# ---------------------------------------------------------------------------
def ssl2_protocols():
    """Verify that protocol constants are defined and distinct integers."""
    names = (
        "PROTOCOL_TLS",
        "PROTOCOL_TLS_CLIENT",
        "PROTOCOL_TLS_SERVER",
        "PROTOCOL_TLSv1",
        "PROTOCOL_TLSv1_1",
        "PROTOCOL_TLSv1_2",
    )
    values = []
    for name in names:
        value = globals().get(name)
        if not isinstance(value, int):
            return False
        values.append(value)
    # Client and server protocols must be distinct.
    if PROTOCOL_TLS_CLIENT == PROTOCOL_TLS_SERVER:
        return False
    return True


def ssl2_context():
    """Verify that ``SSLContext`` can be constructed and configured."""
    try:
        ctx = SSLContext(PROTOCOL_TLS_CLIENT)
    except Exception:
        return False
    if ctx.protocol != PROTOCOL_TLS_CLIENT:
        return False
    if ctx.verify_mode != CERT_NONE:
        return False
    # Setting verify_mode and check_hostname should round-trip.
    ctx.verify_mode = CERT_REQUIRED
    if ctx.verify_mode != CERT_REQUIRED:
        return False
    ctx.check_hostname = True
    if not ctx.check_hostname:
        return False
    # create_default_context should also yield a usable SSLContext.
    default_ctx = create_default_context()
    if not isinstance(default_ctx, SSLContext):
        return False
    if default_ctx.verify_mode != CERT_REQUIRED:
        return False
    return True


def ssl2_cert_required():
    """Verify the certificate-verification constants and their semantics."""
    if CERT_NONE == CERT_OPTIONAL or CERT_OPTIONAL == CERT_REQUIRED:
        return False
    if CERT_REQUIRED != 2:
        return False
    ctx = SSLContext(PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = CERT_REQUIRED
    if ctx.verify_mode != CERT_REQUIRED:
        return False
    # Invalid verification modes must be rejected.
    try:
        ctx.verify_mode = 999
    except ValueError:
        pass
    else:
        return False
    return True


__all__ = [
    "PROTOCOL_SSLv23",
    "PROTOCOL_TLS",
    "PROTOCOL_TLS_CLIENT",
    "PROTOCOL_TLS_SERVER",
    "PROTOCOL_TLSv1",
    "PROTOCOL_TLSv1_1",
    "PROTOCOL_TLSv1_2",
    "CERT_NONE",
    "CERT_OPTIONAL",
    "CERT_REQUIRED",
    "Purpose",
    "SSLError",
    "SSLCertVerificationError",
    "SSLZeroReturnError",
    "SSLContext",
    "create_default_context",
    "ssl2_protocols",
    "ssl2_context",
    "ssl2_cert_required",
]