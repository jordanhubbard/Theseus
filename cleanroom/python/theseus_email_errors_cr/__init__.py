"""
theseus_email_errors_cr — Clean-room email.errors module.
No import of the standard `email.errors` module.
"""


class MessageError(Exception):
    """Base class for email-related errors."""


class MessageParseError(MessageError):
    """Base class for errors during message parsing."""


class HeaderParseError(MessageParseError):
    """Error while parsing a message header."""


class BoundaryError(MessageParseError):
    """Couldn't find terminating boundary."""


class MultipartConversionError(MessageError, TypeError):
    """Payload was already set to a non-list and multipart was called."""


class CharsetError(MessageError):
    """An illegal charset was given."""


class MessageDefect(ValueError):
    """Base class for defects found during parsing."""

    def __init__(self, line=None):
        super().__init__(line)
        self.line = line


class NoBoundaryInMultipartDefect(MessageDefect):
    """A message claimed to be a multipart but had no boundary parameter."""


class StartBoundaryNotFoundDefect(MessageDefect):
    """The claimed start boundary was never found."""


class CloseBoundaryNotFoundDefect(MessageDefect):
    """A start boundary was found but not the corresponding close boundary."""


class FirstHeaderLineIsContinuationDefect(MessageDefect):
    """A message had a continuation line as its first header line."""


class MisplacedEnvelopeHeaderDefect(MessageDefect):
    """A 'Unix-from' header was found in the middle of a header block."""


class MissingHeaderBodySeparatorDefect(MessageDefect):
    """Found a line with no leading whitespace and no colon before blank line."""


# Alias
MalformedHeaderDefect = MissingHeaderBodySeparatorDefect


class MultipartInvariantViolationDefect(MessageDefect):
    """A message claimed to be a multipart but no subparts were found."""


class InvalidMultipartContentTransferEncodingDefect(MessageDefect):
    """Multipart contained an invalid content-transfer-encoding."""


class UndecodableBytesDefect(MessageDefect):
    """Header contained bytes that could not be decoded."""


class InvalidBase64PaddingDefect(MessageDefect):
    """Base64 encoded sequence had an incorrect padding."""


class InvalidBase64CharactersDefect(MessageDefect):
    """Base64 encoded sequence had characters not in base64 alphabet."""


class InvalidBase64LengthDefect(MessageDefect):
    """Base64 encoded sequence had invalid length."""


class HeaderDefect(MessageDefect):
    """A header was found to be invalid."""


class InvalidHeaderDefect(HeaderDefect):
    """A header was found to be invalid during parsing."""


class HeaderMissingRequiredValue(HeaderDefect):
    """A header that must have a value was found without one."""


class NonPrintableDefect(MessageDefect):
    """A header contained characters that are not printable."""

    def __init__(self, non_printables):
        super().__init__(non_printables)
        self.non_printables = non_printables


class ObsoleteHeaderDefect(HeaderDefect):
    """An obsolete RFC 2822 construct was found."""


class NonASCIILocalPartDefect(HeaderDefect):
    """The local part of an address contained non-ASCII characters."""


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def emailerr2_message_error():
    """MessageError base class exists; returns True."""
    err = MessageError('test error')
    return (issubclass(MessageError, Exception) and
            str(err) == 'test error')


def emailerr2_defect():
    """MessageDefect and related defect classes exist; returns True."""
    defect = NoBoundaryInMultipartDefect('test line')
    return (issubclass(MessageDefect, ValueError) and
            issubclass(NoBoundaryInMultipartDefect, MessageDefect) and
            defect.line == 'test line')


def emailerr2_parse_defect():
    """HeaderParseError and MultipartConversionError exist; returns True."""
    return (issubclass(HeaderParseError, MessageParseError) and
            issubclass(MultipartConversionError, MessageError) and
            issubclass(MultipartConversionError, TypeError))


__all__ = [
    'MessageError', 'MessageParseError', 'HeaderParseError',
    'BoundaryError', 'MultipartConversionError', 'CharsetError',
    'MessageDefect', 'NoBoundaryInMultipartDefect',
    'StartBoundaryNotFoundDefect', 'CloseBoundaryNotFoundDefect',
    'FirstHeaderLineIsContinuationDefect', 'MisplacedEnvelopeHeaderDefect',
    'MissingHeaderBodySeparatorDefect', 'MalformedHeaderDefect',
    'MultipartInvariantViolationDefect',
    'InvalidMultipartContentTransferEncodingDefect',
    'UndecodableBytesDefect', 'InvalidBase64PaddingDefect',
    'InvalidBase64CharactersDefect', 'InvalidBase64LengthDefect',
    'HeaderDefect', 'InvalidHeaderDefect', 'HeaderMissingRequiredValue',
    'NonPrintableDefect', 'ObsoleteHeaderDefect', 'NonASCIILocalPartDefect',
    'emailerr2_message_error', 'emailerr2_defect', 'emailerr2_parse_defect',
]
