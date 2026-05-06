"""Clean-room implementation of a subset of smtplib for Theseus.

Implements exception hierarchy, quoteaddr, and quotedata helpers from
scratch without importing the standard-library smtplib module.
"""

import re as _re


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class SMTPException(OSError):
    """Base class for all exceptions raised by this module."""


class SMTPNotSupportedError(SMTPException):
    """The command or option is not supported by the SMTP server."""


class SMTPServerDisconnected(SMTPException):
    """Not connected to any SMTP server."""


class SMTPResponseException(SMTPException):
    """Base class for all exceptions that include an SMTP error code."""

    def __init__(self, code, msg):
        self.smtp_code = code
        self.smtp_error = msg
        self.args = (code, msg)


class SMTPSenderRefused(SMTPResponseException):
    """Sender address refused.

    In addition to the attributes set by SMTPResponseException, this sets
    'sender' to the string that the SMTP refused.
    """

    def __init__(self, code, msg, sender):
        self.smtp_code = code
        self.smtp_error = msg
        self.sender = sender
        self.args = (code, msg, sender)


class SMTPRecipientsRefused(SMTPException):
    """All recipient addresses refused.

    The errors for each recipient are accessible through the attribute
    'recipients', which is a dictionary of exactly the same sort as
    SMTP.sendmail() returns.
    """

    def __init__(self, recipients):
        self.recipients = recipients
        self.args = (recipients,)


class SMTPDataError(SMTPResponseException):
    """The SMTP server didn't accept the data."""


class SMTPConnectError(SMTPResponseException):
    """Error during connection establishment."""


class SMTPHeloError(SMTPResponseException):
    """The server refused our HELO reply."""


class SMTPAuthenticationError(SMTPResponseException):
    """Authentication error.

    Most probably the server didn't accept the username/password
    combination provided.
    """


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


SMTP_PORT = 25
SMTP_SSL_PORT = 465
CRLF = "\r\n"
bCRLF = b"\r\n"
_MAXLINE = 8192  # more than 8 times larger than RFC 821, 4.5.3
_MAXCHALLENGE = 5  # Maximum number of AUTH challenges sent

OLDSTYLE_AUTH = _re.compile(r"auth=(.*)", _re.I)


# ---------------------------------------------------------------------------
# Address parsing helpers
# ---------------------------------------------------------------------------


def _parseaddr(addr):
    """Minimal RFC 822 address parser.

    Given a string, return a 2-tuple (realname, email_address).  If the
    address cannot be parsed, return ('', '').  This is a small,
    self-contained reimplementation that is intentionally permissive:
    it understands the ``Name <addr>`` form, bare ``<addr>``, and the
    plain ``addr`` form.
    """
    if addr is None:
        return ("", "")
    if not isinstance(addr, str):
        try:
            addr = addr.decode("ascii")
        except Exception:
            return ("", "")

    s = addr.strip()
    if not s:
        return ("", "")

    # Look for <...>
    lt = s.rfind("<")
    gt = s.rfind(">")
    if lt != -1 and gt != -1 and gt > lt:
        name = s[:lt].strip()
        # strip surrounding quotes from the name if present
        if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
            name = name[1:-1]
        email = s[lt + 1:gt].strip()
        return (name, email)

    # No angle brackets: treat the whole thing as the address.
    # If it contains whitespace, the result is undefined per RFC; we
    # mirror the standard library's behavior of returning ('', '').
    if any(c.isspace() for c in s):
        # Still try to recover a single token if there is exactly one
        # @-containing word.
        toks = s.split()
        ats = [t for t in toks if "@" in t]
        if len(ats) == 1:
            return ("", ats[0])
        return ("", "")
    return ("", s)


def quoteaddr(addrstring):
    """Quote a subset of the email addresses defined by RFC 821.

    Should be able to handle anything email.utils.parseaddr can handle.
    """
    displayname, addr = _parseaddr(addrstring)
    if (displayname, addr) == ("", ""):
        # parseaddr couldn't parse it, use it as-is and hope for the best.
        if isinstance(addrstring, bytes):
            try:
                addrstring = addrstring.decode("ascii")
            except Exception:
                addrstring = addrstring.decode("ascii", "replace")
        return "<%s>" % addrstring
    return "<%s>" % addr


def _addr_only(addrstring):
    """Return just the email portion of an address, or the original string."""
    displayname, addr = _parseaddr(addrstring)
    if (displayname, addr) == ("", ""):
        return addrstring
    return addr


def quotedata(data):
    """Quote data for email.

    Double leading '.', and change Unix newline '\\n', or Mac '\\r' into
    internet CRLF end-of-line.
    """
    return _re.sub(r"(?m)^\.", "..", _re.sub(r"(?:\r\n|\n|\r(?!\n))", CRLF, data))


def _quote_periods(bindata):
    return _re.sub(br"(?m)^\.", b"..", bindata)


def _fix_eols(data):
    return _re.sub(r"(?:\r\n|\n|\r(?!\n))", CRLF, data)


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------


def smtplib2_exceptions():
    """Verify that the exception hierarchy is wired correctly."""
    # Base exception
    if not issubclass(SMTPException, OSError):
        return False
    # Direct children of SMTPException
    for cls in (
        SMTPNotSupportedError,
        SMTPServerDisconnected,
        SMTPResponseException,
        SMTPRecipientsRefused,
    ):
        if not issubclass(cls, SMTPException):
            return False
    # Children of SMTPResponseException
    for cls in (
        SMTPSenderRefused,
        SMTPDataError,
        SMTPConnectError,
        SMTPHeloError,
        SMTPAuthenticationError,
    ):
        if not issubclass(cls, SMTPResponseException):
            return False

    # Verify instantiation behavior
    e = SMTPResponseException(550, "boom")
    if e.smtp_code != 550 or e.smtp_error != "boom":
        return False
    if e.args != (550, "boom"):
        return False

    s = SMTPSenderRefused(553, "nope", "x@y.z")
    if s.smtp_code != 553 or s.smtp_error != "nope" or s.sender != "x@y.z":
        return False
    if s.args != (553, "nope", "x@y.z"):
        return False

    r = SMTPRecipientsRefused({"a@b": (550, b"no")})
    if r.recipients != {"a@b": (550, b"no")}:
        return False

    return True


def smtplib2_quoteaddr():
    """Verify quoteaddr behavior."""
    if quoteaddr("foo@bar.com") != "<foo@bar.com>":
        return False
    if quoteaddr("<foo@bar.com>") != "<foo@bar.com>":
        return False
    if quoteaddr("Foo Bar <foo@bar.com>") != "<foo@bar.com>":
        return False
    if quoteaddr('"Foo Bar" <foo@bar.com>') != "<foo@bar.com>":
        return False
    # Address with no domain - parser still returns it.
    if quoteaddr("postmaster") != "<postmaster>":
        return False
    return True


def smtplib2_quotedata():
    """Verify quotedata behavior."""
    # Bare newlines become CRLF
    if quotedata("hello\nworld") != "hello\r\nworld":
        return False
    # Existing CRLF stays CRLF (not doubled)
    if quotedata("hello\r\nworld") != "hello\r\nworld":
        return False
    # Leading dot on a line is doubled
    if quotedata(".start") != "..start":
        return False
    if quotedata("ok\n.dot") != "ok\r\n..dot":
        return False
    # Combination
    if quotedata("a\n.b\nc") != "a\r\n..b\r\nc":
        return False
    # Lone CR becomes CRLF
    if quotedata("a\rb") != "a\r\nb":
        return False
    return True


__all__ = [
    "SMTPException",
    "SMTPNotSupportedError",
    "SMTPServerDisconnected",
    "SMTPResponseException",
    "SMTPSenderRefused",
    "SMTPRecipientsRefused",
    "SMTPDataError",
    "SMTPConnectError",
    "SMTPHeloError",
    "SMTPAuthenticationError",
    "SMTP_PORT",
    "SMTP_SSL_PORT",
    "CRLF",
    "bCRLF",
    "quoteaddr",
    "quotedata",
    "smtplib2_exceptions",
    "smtplib2_quoteaddr",
    "smtplib2_quotedata",
]