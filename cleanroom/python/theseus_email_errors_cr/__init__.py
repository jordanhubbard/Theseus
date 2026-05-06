"""Clean-room implementation of email.errors.

Provides exception classes for email parsing errors and defect classes
for non-fatal parser issues. No dependency on the standard email.errors module.
"""


# -----------------------------------------------------------------------------
# Exception hierarchy
# -----------------------------------------------------------------------------

class MessageError(Exception):
    """Base class for errors generated when parsing/handling messages."""


class MessageParseError(MessageError):
    """Base class for message parser errors."""


class HeaderParseError(MessageParseError):
    """Error raised while parsing headers."""


class BoundaryError(MessageParseError):
    """Couldn't find a terminating boundary in a multipart message."""


class MultipartConversionError(MessageError, TypeError):
    """Raised when a non-multipart conversion is attempted."""


class CharsetError(MessageError):
    """An illegal charset was given."""


class HeaderWriteError(MessageError):
    """Error raised when writing a header that cannot be encoded."""


# -----------------------------------------------------------------------------
# Defect hierarchy (issues the parser worked around)
# -----------------------------------------------------------------------------

class MessageDefect(ValueError):
    """Base class for a message defect."""

    def __init__(self, line=None):
        if line is not None:
            super().__init__(line)
        else:
            super().__init__()
        self.line = line


class NoBoundaryInMultipartDefect(MessageDefect):
    """A message claimed to be a multipart but had no boundary parameter."""


class StartBoundaryNotFoundDefect(MessageDefect):
    """The claimed start boundary was never found."""


class CloseBoundaryNotFoundDefect(MessageDefect):
    """A start boundary was found, but no corresponding close boundary."""


class FirstHeaderLineIsContinuationDefect(MessageDefect):
    """A message had a continuation line as its first header line."""


class MisplacedEnvelopeHeaderDefect(MessageDefect):
    """A 'Unix-from' header was found in the middle of a header block."""


class MissingHeaderBodySeparatorDefect(MessageDefect):
    """Line with no leading whitespace and no colon before blank line."""


# Backwards-compatible alias
MalformedHeaderDefect = MissingHeaderBodySeparatorDefect


class MultipartInvariantViolationDefect(MessageDefect):
    """A message claimed to be a multipart but no subparts were found."""


class InvalidMultipartContentTransferEncodingDefect(MessageDefect):
    """An invalid content-transfer-encoding was set on the multipart itself."""


class UndecodableBytesDefect(MessageDefect):
    """Header contained bytes that could not be decoded."""


class InvalidBase64PaddingDefect(MessageDefect):
    """A base64-encoded sequence had an incorrect length."""


class InvalidBase64CharactersDefect(MessageDefect):
    """A base64-encoded sequence had characters not in base64 alphabet."""


class InvalidBase64LengthDefect(MessageDefect):
    """A base64-encoded sequence had invalid length (1 mod 4)."""


# -----------------------------------------------------------------------------
# Header-specific defects
# -----------------------------------------------------------------------------

class HeaderDefect(MessageDefect):
    """Base class for a header defect."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)


class InvalidHeaderDefect(HeaderDefect):
    """Header is not valid; message gives details."""


class HeaderMissingRequiredValue(HeaderDefect):
    """A header that must have a value had none."""


class NonPrintableDefect(HeaderDefect):
    """ASCII characters outside the ascii-printable range were found."""

    def __init__(self, non_printables):
        super().__init__(non_printables)
        self.non_printables = non_printables

    def __str__(self):
        return ("the following ASCII non-printables found in header: "
                "{}".format(self.non_printables))


class ObsoleteHeaderDefect(HeaderDefect):
    """Header uses syntax declared obsolete by RFC 5322."""


class NonASCIILocalPartDefect(HeaderDefect):
    """local_part contains non-ASCII characters."""


class InvalidDateDefect(HeaderDefect):
    """Header has an unparsable or invalid date."""


# -----------------------------------------------------------------------------
# Invariant validation functions
# -----------------------------------------------------------------------------

def emailerr2_message_error():
    """Validate the MessageError hierarchy is well-formed."""
    try:
        # MessageError must be an Exception subclass.
        if not issubclass(MessageError, Exception):
            return False
        # The standard parse-error subclasses must descend from MessageError.
        for cls in (MessageParseError, HeaderParseError, BoundaryError,
                    MultipartConversionError, CharsetError):
            if not issubclass(cls, MessageError):
                return False
        # MultipartConversionError must also be a TypeError.
        if not issubclass(MultipartConversionError, TypeError):
            return False
        # Instances must be raisable and catchable.
        try:
            raise HeaderParseError("bad header")
        except MessageError as exc:
            if "bad header" not in str(exc):
                return False
        return True
    except Exception:
        return False


def emailerr2_defect():
    """Validate the MessageDefect hierarchy is well-formed."""
    try:
        # MessageDefect must be a ValueError subclass (per the spec).
        if not issubclass(MessageDefect, ValueError):
            return False
        # All defect subclasses must descend from MessageDefect.
        defect_subclasses = (
            NoBoundaryInMultipartDefect,
            StartBoundaryNotFoundDefect,
            CloseBoundaryNotFoundDefect,
            FirstHeaderLineIsContinuationDefect,
            MisplacedEnvelopeHeaderDefect,
            MissingHeaderBodySeparatorDefect,
            MultipartInvariantViolationDefect,
            InvalidMultipartContentTransferEncodingDefect,
            UndecodableBytesDefect,
            InvalidBase64PaddingDefect,
            InvalidBase64CharactersDefect,
            InvalidBase64LengthDefect,
            HeaderDefect,
            InvalidHeaderDefect,
            HeaderMissingRequiredValue,
            NonPrintableDefect,
            ObsoleteHeaderDefect,
            NonASCIILocalPartDefect,
            InvalidDateDefect,
        )
        for cls in defect_subclasses:
            if not issubclass(cls, MessageDefect):
                return False
        # An instance with no line argument should still construct.
        d = MessageDefect()
        if d.line is not None:
            return False
        # An instance with a line argument should keep it.
        d2 = MessageDefect("bad line")
        if d2.line != "bad line":
            return False
        return True
    except Exception:
        return False


def emailerr2_parse_defect():
    """Validate parse-related defects construct and behave properly."""
    try:
        # Parse-related defects should accept a line argument.
        d = NoBoundaryInMultipartDefect("missing boundary")
        if d.line != "missing boundary":
            return False
        if "missing boundary" not in str(d):
            return False
        # Boundary defects should be MessageDefect instances.
        sb = StartBoundaryNotFoundDefect()
        cb = CloseBoundaryNotFoundDefect()
        if not isinstance(sb, MessageDefect):
            return False
        if not isinstance(cb, MessageDefect):
            return False
        # Header parse defects should also work.
        first = FirstHeaderLineIsContinuationDefect(" continuation")
        if first.line != " continuation":
            return False
        # MalformedHeaderDefect should alias MissingHeaderBodySeparatorDefect.
        if MalformedHeaderDefect is not MissingHeaderBodySeparatorDefect:
            return False
        # NonPrintableDefect should expose the non_printables attribute.
        npd = NonPrintableDefect("\x01\x02")
        if npd.non_printables != "\x01\x02":
            return False
        if "ASCII non-printables" not in str(npd):
            return False
        # Defects should be raisable as ValueError.
        try:
            raise InvalidBase64LengthDefect("bad length")
        except ValueError as exc:
            if "bad length" not in str(exc):
                return False
        return True
    except Exception:
        return False


__all__ = [
    # Exceptions
    "MessageError",
    "MessageParseError",
    "HeaderParseError",
    "BoundaryError",
    "MultipartConversionError",
    "CharsetError",
    "HeaderWriteError",
    # Defects
    "MessageDefect",
    "NoBoundaryInMultipartDefect",
    "StartBoundaryNotFoundDefect",
    "CloseBoundaryNotFoundDefect",
    "FirstHeaderLineIsContinuationDefect",
    "MisplacedEnvelopeHeaderDefect",
    "MissingHeaderBodySeparatorDefect",
    "MalformedHeaderDefect",
    "MultipartInvariantViolationDefect",
    "InvalidMultipartContentTransferEncodingDefect",
    "UndecodableBytesDefect",
    "InvalidBase64PaddingDefect",
    "InvalidBase64CharactersDefect",
    "InvalidBase64LengthDefect",
    "HeaderDefect",
    "InvalidHeaderDefect",
    "HeaderMissingRequiredValue",
    "NonPrintableDefect",
    "ObsoleteHeaderDefect",
    "NonASCIILocalPartDefect",
    "InvalidDateDefect",
    # Invariant validators
    "emailerr2_message_error",
    "emailerr2_defect",
    "emailerr2_parse_defect",
]