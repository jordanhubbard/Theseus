from collections import namedtuple

ParsedUID = namedtuple('ParsedUID', ['uid', 'flags', 'body'])


def parse_flags(flags_str):
    """
    Parse an IMAP flags string like '(\\Seen \\Recent)' into a frozenset of flag strings.
    """
    flags_str = flags_str.strip()
    # Remove surrounding parentheses if present
    if flags_str.startswith('(') and flags_str.endswith(')'):
        flags_str = flags_str[1:-1]
    flags_str = flags_str.strip()
    if not flags_str:
        return frozenset()
    parts = flags_str.split()
    return frozenset(parts)


def parse_uid(uid_str):
    """
    Parse an IMAP UID string like 'UID 42' into an integer.
    """
    uid_str = uid_str.strip()
    parts = uid_str.split()
    # Expect format: 'UID <number>'
    if len(parts) == 2 and parts[0].upper() == 'UID':
        return int(parts[1])
    # Fallback: try to parse as plain integer
    return int(uid_str)


def imaplib_parse_flags_count():
    return len(parse_flags('(\\Seen \\Recent)'))


def imaplib_parse_flags_has_seen():
    return '\\Seen' in parse_flags('(\\Seen \\Recent)')


def imaplib_parse_uid():
    return parse_uid('UID 42')