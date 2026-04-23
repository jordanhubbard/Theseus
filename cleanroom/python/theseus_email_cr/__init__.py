"""
theseus_email_cr - Clean-room RFC 5322 email message parser.
"""


class Message:
    """A simple RFC 5322 email message container."""

    def __init__(self, headers, payload):
        """
        headers: list of (name, value) tuples
        payload: string body
        """
        self._headers = headers
        self._payload = payload

    def __getitem__(self, name):
        """Return the first header value matching name (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self._headers:
            if key.lower() == name_lower:
                return value
        return None

    def get(self, name, default=None):
        """Return the first header value matching name, or default."""
        result = self[name]
        if result is None:
            return default
        return result

    def get_payload(self):
        """Return the message body as a string."""
        return self._payload

    def keys(self):
        """Return list of header names."""
        return [key for key, value in self._headers]

    def values(self):
        """Return list of header values."""
        return [value for key, value in self._headers]

    def items(self):
        """Return list of (name, value) tuples."""
        return list(self._headers)


def message_from_string(s):
    """
    Parse an RFC 5322 email message string into a Message object.
    
    Headers are 'Name: value' lines separated from the body by a blank line.
    Supports folded headers (continuation lines starting with whitespace).
    """
    headers = []
    payload = ""

    # Normalize line endings
    s = s.replace('\r\n', '\n').replace('\r', '\n')

    # Split into lines
    lines = s.split('\n')

    i = 0
    n = len(lines)

    # Parse headers
    while i < n:
        line = lines[i]

        # Blank line signals end of headers
        if line == '':
            i += 1
            break

        # Check for header field: "Name: value"
        if ':' in line and not line[0].isspace():
            colon_pos = line.index(':')
            header_name = line[:colon_pos].strip()
            header_value = line[colon_pos + 1:].strip()

            # Handle folded headers (continuation lines start with whitespace)
            i += 1
            while i < n and lines[i] and lines[i][0] in (' ', '\t'):
                header_value += ' ' + lines[i].strip()
                i += 1

            headers.append((header_name, header_value))
        else:
            # Malformed header line, skip
            i += 1

    # Everything after the blank line is the payload
    payload = '\n'.join(lines[i:])

    return Message(headers, payload)


# ---------------------------------------------------------------------------
# Zero-argument invariant functions
# ---------------------------------------------------------------------------

def email_parse_from():
    """
    Parse 'From: user@host\\n\\nbody' and return msg['From'].
    Expected: 'user@host'
    """
    raw = "From: user@host\n\nbody"
    msg = message_from_string(raw)
    return msg['From']


def email_parse_subject():
    """
    Parse email with Subject header and return msg['Subject'].
    Expected: 'Hello'
    """
    raw = "Subject: Hello\n\n"
    msg = message_from_string(raw)
    return msg['Subject']


def email_payload():
    """
    Parse email with body and return get_payload().
    Expected: 'body text'
    """
    raw = "From: sender@example.com\n\nbody text"
    msg = message_from_string(raw)
    return msg.get_payload()