"""
theseus_csv - Clean-room CSV reader/writer implementation.
No import of the standard csv module.
"""


def _parse_row(line, delimiter=','):
    """Parse a single CSV line into a list of fields."""
    fields = []
    current = []
    i = 0
    length = len(line)
    
    while i < length:
        ch = line[i]
        
        if ch == '"':
            # Quoted field
            i += 1  # skip opening quote
            while i < length:
                c = line[i]
                if c == '"':
                    # Check for escaped quote ("")
                    if i + 1 < length and line[i + 1] == '"':
                        current.append('"')
                        i += 2
                    else:
                        i += 1  # skip closing quote
                        break
                else:
                    current.append(c)
                    i += 1
            # After closing quote, expect delimiter or end of line
            # (ignore any trailing chars before delimiter)
            while i < length and line[i] != delimiter:
                i += 1
        elif ch == delimiter:
            fields.append(''.join(current))
            current = []
            i += 1
        else:
            current.append(ch)
            i += 1
    
    fields.append(''.join(current))
    return fields


def reader(lines, delimiter=','):
    """
    Parse an iterable of strings into rows (lists of strings).
    
    Handles quoted fields, escaped quotes (""), and the given delimiter.
    Returns a list of lists of strings.
    """
    result = []
    for line in lines:
        # Strip trailing newline characters
        line = line.rstrip('\r\n')
        row = _parse_row(line, delimiter=delimiter)
        result.append(row)
    return result


def writer_row(fields, delimiter=','):
    """
    Serialize a list of fields into a CSV row string.
    
    Fields containing the delimiter, double-quote, or newline characters
    are quoted. Double-quotes within fields are escaped as "".
    """
    parts = []
    for field in fields:
        # Determine if quoting is needed
        needs_quote = (
            delimiter in field or
            '"' in field or
            '\n' in field or
            '\r' in field
        )
        if needs_quote:
            # Escape any existing double-quotes
            escaped = field.replace('"', '""')
            parts.append('"' + escaped + '"')
        else:
            parts.append(field)
    return delimiter.join(parts)


# --- Functions referenced in the invariants ---

def csv_parse_simple_row(lines=None):
    """
    Parse simple (unquoted) CSV rows.
    Default input: ['a,b,c'] -> [['a', 'b', 'c']]
    """
    if lines is None:
        lines = ['a,b,c']
    return reader(lines)


def csv_parse_quoted_row(lines=None):
    """
    Parse CSV rows with quoted fields.
    Default input: ['"hello, world",foo'] -> [['hello, world', 'foo']]
    """
    if lines is None:
        lines = ['"hello, world",foo']
    return reader(lines)


def csv_write_row(fields=None, delimiter=','):
    """
    Write a CSV row from a list of fields.
    Default input: ['a', 'b,c'] -> 'a,"b,c"'
    """
    if fields is None:
        fields = ['a', 'b,c']
    return writer_row(fields, delimiter=delimiter)