"""
theseus_http_cr — Clean-room http module.
No import of the standard `http` module.
Provides HTTPStatus and HTTPMethod enumerations.
"""

import enum as _enum


class HTTPMethod(_enum.StrEnum):
    """HTTP request methods per RFC 7231 and IANA registry."""
    CONNECT = 'CONNECT'
    DELETE = 'DELETE'
    GET = 'GET'
    HEAD = 'HEAD'
    OPTIONS = 'OPTIONS'
    PATCH = 'PATCH'
    POST = 'POST'
    PUT = 'PUT'
    TRACE = 'TRACE'


class HTTPStatus(_enum.IntEnum):
    """HTTP status codes per RFC 9110 and IANA registry."""

    def __new__(cls, value, phrase='', description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.phrase = phrase
        obj.description = description
        return obj

    @property
    def is_informational(self):
        return 100 <= self.value <= 199

    @property
    def is_success(self):
        return 200 <= self.value <= 299

    @property
    def is_redirection(self):
        return 300 <= self.value <= 399

    @property
    def is_client_error(self):
        return 400 <= self.value <= 499

    @property
    def is_server_error(self):
        return 500 <= self.value <= 599

    # Informational
    CONTINUE = 100, 'Continue', 'Request received, please continue'
    SWITCHING_PROTOCOLS = 101, 'Switching Protocols', 'Switching to new protocol'
    PROCESSING = 102, 'Processing', 'WebDAV; request is being processed'
    EARLY_HINTS = 103, 'Early Hints', 'Used with Link header for preloading'

    # Success
    OK = 200, 'OK', 'Request fulfilled, document follows'
    CREATED = 201, 'Created', 'Document created, URL follows'
    ACCEPTED = 202, 'Accepted', 'Request accepted, processing continues off-line'
    NON_AUTHORITATIVE_INFORMATION = 203, 'Non-Authoritative Information', 'Request fulfilled from cache'
    NO_CONTENT = 204, 'No Content', 'Request fulfilled, nothing follows'
    RESET_CONTENT = 205, 'Reset Content', 'Clear input form for further input'
    PARTIAL_CONTENT = 206, 'Partial Content', 'Partial content follows'
    MULTI_STATUS = 207, 'Multi-Status', 'WebDAV; multiple status'
    ALREADY_REPORTED = 208, 'Already Reported', 'WebDAV; already reported'
    IM_USED = 226, 'IM Used', 'GET fulfilled; IM headers used'

    # Redirection
    MULTIPLE_CHOICES = 300, 'Multiple Choices', 'Object has several resources'
    MOVED_PERMANENTLY = 301, 'Moved Permanently', 'Object moved permanently'
    FOUND = 302, 'Found', 'Object moved temporarily'
    SEE_OTHER = 303, 'See Other', 'Object moved — see Method and URL list'
    NOT_MODIFIED = 304, 'Not Modified', 'Document has not changed since given time'
    USE_PROXY = 305, 'Use Proxy', 'Must use proxy'
    TEMPORARY_REDIRECT = 307, 'Temporary Redirect', 'Object moved temporarily — Method may change'
    PERMANENT_REDIRECT = 308, 'Permanent Redirect', 'Object moved permanently — Method may not change'

    # Client error
    BAD_REQUEST = 400, 'Bad Request', 'Bad request syntax or unsupported method'
    UNAUTHORIZED = 401, 'Unauthorized', 'No permission — see authorization schemes'
    PAYMENT_REQUIRED = 402, 'Payment Required', 'No payment — see charging schemes'
    FORBIDDEN = 403, 'Forbidden', 'Request forbidden — authorization will not help'
    NOT_FOUND = 404, 'Not Found', 'Nothing matches the given URI'
    METHOD_NOT_ALLOWED = 405, 'Method Not Allowed', 'Specified method is invalid for this resource'
    NOT_ACCEPTABLE = 406, 'Not Acceptable', 'URI not available in preferred format'
    PROXY_AUTHENTICATION_REQUIRED = 407, 'Proxy Authentication Required', 'Must authenticate with proxy first'
    REQUEST_TIMEOUT = 408, 'Request Timeout', 'Request timed out; try again later'
    CONFLICT = 409, 'Conflict', 'Request conflict'
    GONE = 410, 'Gone', 'URI no longer exists'
    LENGTH_REQUIRED = 411, 'Length Required', 'Client must specify Content-Length'
    PRECONDITION_FAILED = 412, 'Precondition Failed', 'Precondition in headers is false'
    CONTENT_TOO_LARGE = 413, 'Content Too Large', 'Entity too large'
    REQUEST_URI_TOO_LONG = 414, 'Request-URI Too Long', 'URI too long'
    UNSUPPORTED_MEDIA_TYPE = 415, 'Unsupported Media Type', 'Unsupported media type'
    REQUESTED_RANGE_NOT_SATISFIABLE = 416, 'Requested Range Not Satisfiable', 'Cannot satisfy request range'
    EXPECTATION_FAILED = 417, 'Expectation Failed', 'Expect condition could not be satisfied'
    IM_A_TEAPOT = 418, "I'm a Teapot", 'April Fool\'s joke'
    MISDIRECTED_REQUEST = 421, 'Misdirected Request', 'Server is not able to produce a response'
    UNPROCESSABLE_CONTENT = 422, 'Unprocessable Content', 'Request could not be processed'
    LOCKED = 423, 'Locked', 'WebDAV; resource is locked'
    FAILED_DEPENDENCY = 424, 'Failed Dependency', 'WebDAV; prior request failed'
    TOO_EARLY = 425, 'Too Early', 'Indicates that the server is unwilling to risk processing'
    UPGRADE_REQUIRED = 426, 'Upgrade Required', 'Client must switch to new protocol'
    PRECONDITION_REQUIRED = 428, 'Precondition Required', 'The origin server requires conditional request'
    TOO_MANY_REQUESTS = 429, 'Too Many Requests', 'Too many requests'
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, 'Request Header Fields Too Large', 'Header fields are too large'
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, 'Unavailable For Legal Reasons', 'The server is denying access to the resource'

    # Server error
    INTERNAL_SERVER_ERROR = 500, 'Internal Server Error', 'Server got itself in trouble'
    NOT_IMPLEMENTED = 501, 'Not Implemented', 'Server does not support this operation'
    BAD_GATEWAY = 502, 'Bad Gateway', 'Invalid responses from another server/proxy'
    SERVICE_UNAVAILABLE = 503, 'Service Unavailable', 'The server cannot process the request'
    GATEWAY_TIMEOUT = 504, 'Gateway Timeout', 'The gateway server did not receive a timely response'
    HTTP_VERSION_NOT_SUPPORTED = 505, 'HTTP Version Not Supported', 'Cannot fulfill request'
    VARIANT_ALSO_NEGOTIATES = 506, 'Variant Also Negotiates', 'Content Negotiation creates a circular reference'
    INSUFFICIENT_STORAGE = 507, 'Insufficient Storage', 'WebDAV; not enough storage'
    LOOP_DETECTED = 508, 'Loop Detected', 'WebDAV; infinite loop'
    NOT_EXTENDED = 510, 'Not Extended', 'Further extensions required'
    NETWORK_AUTHENTICATION_REQUIRED = 511, 'Network Authentication Required', 'Client needs to authenticate'


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def http2_status():
    """HTTPStatus enum has correct values; returns True."""
    return (HTTPStatus.OK == 200 and
            HTTPStatus.NOT_FOUND == 404 and
            HTTPStatus.OK.phrase == 'OK' and
            HTTPStatus.OK.is_success)


def http2_method():
    """HTTPMethod enum has standard methods; returns True."""
    return (HTTPMethod.GET == 'GET' and
            HTTPMethod.POST == 'POST' and
            HTTPMethod.DELETE in HTTPMethod)


def http2_categories():
    """HTTPStatus category properties work; returns True."""
    return (HTTPStatus.CONTINUE.is_informational and
            HTTPStatus.BAD_REQUEST.is_client_error and
            HTTPStatus.INTERNAL_SERVER_ERROR.is_server_error and
            not HTTPStatus.OK.is_client_error)


__all__ = [
    'HTTPMethod', 'HTTPStatus',
    'http2_status', 'http2_method', 'http2_categories',
]
