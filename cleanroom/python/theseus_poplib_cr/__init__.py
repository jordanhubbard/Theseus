"""Clean-room implementation of a POP3 client library.

Provides exception classes, protocol constants, and a response-parsing
helper compatible with the original poplib semantics, written from scratch
without importing the original module.
"""

import re as _re
import socket as _socket

try:
    import ssl as _ssl
    _HAVE_SSL = True
except ImportError:  # pragma: no cover
    _ssl = None
    _HAVE_SSL = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POP3_PORT = 110
POP3_SSL_PORT = 995

CR = b'\r'
LF = b'\n'
CRLF = CR + LF

_MAXLINE = 2048


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------

class error_proto(Exception):
    """Raised on any protocol-level error from the POP3 server."""
    pass


# ---------------------------------------------------------------------------
# Helper: response parsing
# ---------------------------------------------------------------------------

def _parse_response(resp):
    """Validate a server response line and return it.

    Raises ``error_proto`` if the response does not start with ``+OK`` /
    ``+`` style success token. Mirrors the behavior expected by clients of
    the original poplib._getresp helper.
    """
    if resp is None:
        raise error_proto('-ERR no response')
    if isinstance(resp, str):
        b = resp.encode('ascii', 'replace')
    else:
        b = bytes(resp)
    # Strip trailing CRLF for the check.
    stripped = b
    if stripped.endswith(CRLF):
        stripped = stripped[:-2]
    elif stripped.endswith(LF) or stripped.endswith(CR):
        stripped = stripped[:-1]
    if not stripped.startswith(b'+'):
        raise error_proto(stripped.decode('ascii', 'replace'))
    return b


def parse_response(resp):
    """Public helper that validates a POP3 response and returns it.

    The function accepts either ``bytes`` or ``str``. On a ``-ERR`` reply
    (or anything that does not start with ``+``) it raises ``error_proto``.
    """
    return _parse_response(resp)


# Internal helper: split a multi-line response payload into its lines
# with leading dot-stuffing removed and the terminating "." consumed.
def _parse_multiline(lines):
    out = []
    for line in lines:
        if isinstance(line, str):
            b = line.encode('ascii', 'replace')
        else:
            b = bytes(line)
        if b.endswith(CRLF):
            b = b[:-2]
        elif b.endswith(LF) or b.endswith(CR):
            b = b[:-1]
        if b == b'.':
            break
        if b.startswith(b'..'):
            b = b[1:]
        out.append(b)
    return out


# ---------------------------------------------------------------------------
# POP3 client
# ---------------------------------------------------------------------------

class POP3:
    """Minimal POP3 client.

    The implementation is intentionally focused on the protocol surface that
    is exercised by the invariants of this clean-room rewrite.
    """

    encoding = 'UTF-8'

    def __init__(self, host, port=POP3_PORT, timeout=_socket._GLOBAL_DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self._debugging = 0
        self.sock = self._create_socket(timeout)
        self.file = self.sock.makefile('rb')
        self._welcome = self._getresp()

    # -- networking ---------------------------------------------------------

    def _create_socket(self, timeout):
        return _socket.create_connection((self.host, self.port), timeout)

    def _putline(self, line):
        if self._debugging > 1:
            pass
        self.sock.sendall(line + CRLF)

    def _putcmd(self, line):
        if isinstance(line, str):
            line = line.encode(self.encoding)
        self._putline(line)

    def _getline(self):
        line = self.file.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise error_proto('line too long')
        if not line:
            raise error_proto('-ERR EOF')
        octets = len(line)
        if line[-2:] == CRLF:
            return line[:-2], octets
        if line[:1] == CR:
            return line[1:-1], octets
        return line[:-1], octets

    def _getresp(self):
        resp, _ = self._getline()
        if not resp.startswith(b'+'):
            raise error_proto(resp.decode('ascii', 'replace'))
        return resp

    def _getlongresp(self):
        resp = self._getresp()
        lines = []
        octets = len(resp) + 2
        while True:
            line, n = self._getline()
            octets += n
            if line == b'.':
                break
            if line.startswith(b'..'):
                line = line[1:]
            lines.append(line)
        return resp, lines, octets

    def _shortcmd(self, line):
        self._putcmd(line)
        return self._getresp()

    def _longcmd(self, line):
        self._putcmd(line)
        return self._getlongresp()

    # -- public API ---------------------------------------------------------

    def getwelcome(self):
        return self._welcome

    def user(self, user):
        return self._shortcmd('USER %s' % user)

    def pass_(self, pswd):
        return self._shortcmd('PASS %s' % pswd)

    def stat(self):
        retval = self._shortcmd('STAT')
        rets = retval.split()
        if len(rets) < 3:
            raise error_proto('STAT: malformed response: %r' % retval)
        return int(rets[1]), int(rets[2])

    def list(self, which=None):
        if which is not None:
            return self._shortcmd('LIST %s' % which)
        return self._longcmd('LIST')

    def retr(self, which):
        return self._longcmd('RETR %s' % which)

    def dele(self, which):
        return self._shortcmd('DELE %s' % which)

    def noop(self):
        return self._shortcmd('NOOP')

    def rset(self):
        return self._shortcmd('RSET')

    def quit(self):
        try:
            resp = self._shortcmd('QUIT')
        except error_proto as e:
            resp = bytes(str(e), 'ascii', 'replace')
        self.close()
        return resp

    def close(self):
        try:
            file = self.file
            self.file = None
            if file is not None:
                file.close()
        finally:
            sock = self.sock
            self.sock = None
            if sock is not None:
                try:
                    sock.shutdown(_socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()


if _HAVE_SSL:

    class POP3_SSL(POP3):
        """POP3 client that talks over an SSL/TLS-wrapped socket."""

        def __init__(self, host, port=POP3_SSL_PORT, keyfile=None, certfile=None,
                     timeout=_socket._GLOBAL_DEFAULT_TIMEOUT, context=None):
            if context is not None and (keyfile is not None or certfile is not None):
                raise ValueError(
                    "context and keyfile/certfile arguments are mutually exclusive")
            if context is None:
                context = _ssl.create_default_context()
                if keyfile is not None or certfile is not None:
                    context.load_cert_chain(certfile, keyfile)
            self._context = context
            self.keyfile = keyfile
            self.certfile = certfile
            POP3.__init__(self, host, port, timeout)

        def _create_socket(self, timeout):
            sock = POP3._create_socket(self, timeout)
            return self._context.wrap_socket(sock, server_hostname=self.host)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def poplib2_exceptions():
    """Verify the module exposes the expected POP3 exception type."""
    if not isinstance(error_proto, type):
        return False
    if not issubclass(error_proto, Exception):
        return False
    # The exception must be raisable and catchable.
    try:
        raise error_proto('test')
    except error_proto as e:
        if str(e) != 'test':
            return False
    except Exception:
        return False
    # And it should not collapse into a base Exception identity.
    if error_proto is Exception:
        return False
    return True


def poplib2_constants():
    """Verify the documented POP3 protocol constants are present and sane."""
    if POP3_PORT != 110:
        return False
    if POP3_SSL_PORT != 995:
        return False
    if CR != b'\r':
        return False
    if LF != b'\n':
        return False
    if CRLF != b'\r\n':
        return False
    if not isinstance(_MAXLINE, int) or _MAXLINE <= 0:
        return False
    return True


def poplib2_parse_response():
    """Verify response-parsing helpers handle +OK / -ERR replies correctly."""
    # Successful response is returned unchanged.
    ok = b'+OK 2 200\r\n'
    if parse_response(ok) != ok:
        return False

    # str inputs are accepted.
    ok_text = '+OK welcome'
    res = parse_response(ok_text)
    if not isinstance(res, (bytes, bytearray)) or not res.startswith(b'+OK'):
        return False

    # -ERR must raise error_proto.
    try:
        parse_response(b'-ERR bad login\r\n')
    except error_proto:
        pass
    else:
        return False

    # Garbage (no leading status byte) must also raise error_proto.
    try:
        parse_response(b'unexpected line')
    except error_proto:
        pass
    else:
        return False

    # None must raise error_proto.
    try:
        parse_response(None)
    except error_proto:
        pass
    else:
        return False

    # Multi-line termination handling: a "." line ends the payload, and
    # leading dot-stuffing is removed.
    lines = [b'first', b'..stuffed', b'.\r\n', b'after']
    out = _parse_multiline(lines)
    if out != [b'first', b'.stuffed']:
        return False

    return True