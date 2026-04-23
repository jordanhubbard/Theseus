import os
import re

def uuid4() -> str:
    """Generate a random UUID v4 string."""
    # Get 16 random bytes
    data = bytearray(os.urandom(16))
    
    # Set version to 4: bits 12-15 of time_hi_and_version field
    # Byte 6: version bits (top 4 bits = 0100)
    data[6] = (data[6] & 0x0F) | 0x40
    
    # Set variant to RFC 4122: bits 6-7 of clock_seq_hi_and_reserved
    # Byte 8: variant bits (top 2 bits = 10)
    data[8] = (data[8] & 0x3F) | 0x80
    
    # Format as xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    hex_str = data.hex()
    return '{}-{}-{}-{}-{}'.format(
        hex_str[0:8],
        hex_str[8:12],
        hex_str[12:16],
        hex_str[16:20],
        hex_str[20:32]
    )

def uuid_nil() -> str:
    """Return the nil UUID."""
    return '00000000-0000-0000-0000-000000000000'

_UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

def _uuid4_format_valid(uuid_str: str) -> bool:
    if not isinstance(uuid_str, str):
        return False
    return bool(_UUID_PATTERN.match(uuid_str))


def _uuid4_version_valid(uuid_str: str) -> bool:
    if not _uuid4_format_valid(uuid_str):
        return False
    parts = uuid_str.split('-')
    version_char = parts[2][0].lower()
    if version_char != '4':
        return False
    variant_char = parts[3][0].lower()
    return variant_char in ('8', '9', 'a', 'b')


def uuid4_is_valid_format() -> bool:
    return _uuid4_format_valid(uuid4())


def uuid4_has_version4() -> bool:
    return _uuid4_version_valid(uuid4())