"""theseus_csv_cr — clean-room CSV reader/writer.

No use of the stdlib `csv` module. Implements reader(), writer(),
DictReader, DictWriter from scratch.
"""

import io as _io


class Dialect:
    """Default 'excel'-like dialect."""
    delimiter = ','
    quotechar = '"'
    lineterminator = '\r\n'
    doublequote = True
    skipinitialspace = False


def _resolve_dialect(dialect):
    if dialect is None:
        return Dialect
    return dialect


def _parse_text(text, delim, quote):
    """Generator yielding rows (lists of strings) from CSV text."""
    field_chars = []
    row = []
    in_quotes = False
    field_started = False
    i = 0
    n = len(text)

    while i < n:
        c = text[i]

        if in_quotes:
            if c == quote:
                # check for escaped quote (doublequote)
                if i + 1 < n and text[i + 1] == quote:
                    field_chars.append(quote)
                    i += 2
                    continue
                else:
                    in_quotes = False
                    i += 1
                    continue
            else:
                field_chars.append(c)
                i += 1
                continue
        else:
            if c == quote and not field_started:
                in_quotes = True
                field_started = True
                i += 1
                continue
            elif c == delim:
                row.append(''.join(field_chars))
                field_chars = []
                field_started = False
                i += 1
                continue
            elif c == '\r':
                # consume CRLF or lone CR as a single row terminator
                if i + 1 < n and text[i + 1] == '\n':
                    i += 2
                else:
                    i += 1
                row.append(''.join(field_chars))
                yield row
                field_chars = []
                row = []
                field_started = False
                continue
            elif c == '\n':
                row.append(''.join(field_chars))
                yield row
                field_chars = []
                row = []
                field_started = False
                i += 1
                continue
            else:
                field_chars.append(c)
                field_started = True
                i += 1
                continue

    # tail: a field/row not terminated by a newline
    if field_started or field_chars or row:
        row.append(''.join(field_chars))
        yield row


def reader(f, dialect=None):
    """Return an iterator over rows (lists of strings) parsed from f.

    f may be a file-like object (with .read()) or an iterable of lines.
    """
    d = _resolve_dialect(dialect)
    delim = getattr(d, 'delimiter', ',')
    quote = getattr(d, 'quotechar', '"')

    if hasattr(f, 'read'):
        text = f.read()
    else:
        # iterable of lines — preserve embedded newlines as-is
        parts = []
        for line in f:
            parts.append(line)
        text = ''.join(parts)

    return _parse_text(text, delim, quote)


class _Writer:
    def __init__(self, f, dialect=None):
        d = _resolve_dialect(dialect)
        self.f = f
        self.delim = getattr(d, 'delimiter', ',')
        self.quote = getattr(d, 'quotechar', '"')
        self.lineterm = getattr(d, 'lineterminator', '\r\n')
        self.doublequote = getattr(d, 'doublequote', True)

    def _format_field(self, value):
        s = '' if value is None else str(value)
        needs_quote = (
            self.delim in s
            or self.quote in s
            or '\n' in s
            or '\r' in s
        )
        if needs_quote:
            if self.doublequote:
                escaped = s.replace(self.quote, self.quote + self.quote)
            else:
                escaped = s
            return self.quote + escaped + self.quote
        return s

    def writerow(self, row):
        line = self.delim.join(self._format_field(v) for v in row) + self.lineterm
        self.f.write(line)
        return len(line)

    def writerows(self, rows):
        for r in rows:
            self.writerow(r)


def writer(f, dialect=None):
    """Return a writer object with .writerow()/.writerows()."""
    return _Writer(f, dialect)


class DictReader:
    """Read CSV rows as dicts keyed by fieldnames (taken from header by default)."""

    def __init__(self, f, fieldnames=None, restkey=None, restval=None, dialect=None):
        self._reader = reader(f, dialect)
        self.restkey = restkey
        self.restval = restval
        self._fieldnames = fieldnames

    @property
    def fieldnames(self):
        if self._fieldnames is None:
            try:
                self._fieldnames = next(self._reader)
            except StopIteration:
                self._fieldnames = []
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, value):
        self._fieldnames = value

    def __iter__(self):
        return self

    def __next__(self):
        # ensure header consumed
        fnames = self.fieldnames
        row = next(self._reader)
        # skip blank rows the way csv does
        while row == []:
            row = next(self._reader)
        d = {}
        for idx, key in enumerate(fnames):
            if idx < len(row):
                d[key] = row[idx]
            else:
                d[key] = self.restval
        if len(row) > len(fnames):
            extras = row[len(fnames):]
            if self.restkey is not None:
                d[self.restkey] = extras
        return d


class DictWriter:
    """Write dicts as CSV rows in the order given by fieldnames."""

    def __init__(self, f, fieldnames, restval='', extrasaction='raise', dialect=None):
        self.fieldnames = list(fieldnames)
        self.restval = restval
        if extrasaction not in ('raise', 'ignore'):
            raise ValueError("extrasaction must be 'raise' or 'ignore'")
        self.extrasaction = extrasaction
        self._writer = writer(f, dialect)

    def writeheader(self):
        return self._writer.writerow(self.fieldnames)

    def _dict_to_list(self, rowdict):
        if self.extrasaction == 'raise':
            extras = [k for k in rowdict if k not in self.fieldnames]
            if extras:
                raise ValueError(
                    "dict contains fields not in fieldnames: " + repr(extras)
                )
        return [rowdict.get(k, self.restval) for k in self.fieldnames]

    def writerow(self, rowdict):
        return self._writer.writerow(self._dict_to_list(rowdict))

    def writerows(self, rowdicts):
        for r in rowdicts:
            self.writerow(r)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def csv2_write_read():
    """Round-trip plain rows through writer + reader."""
    buf = _io.StringIO()
    w = writer(buf)
    w.writerow(['a', 'b', 'c'])
    w.writerow(['1', '2', '3'])
    w.writerow(['x', 'y', 'z'])
    buf.seek(0)
    rows = list(reader(buf))
    return rows == [['a', 'b', 'c'], ['1', '2', '3'], ['x', 'y', 'z']]


def csv2_quoting():
    """Fields containing the delimiter, the quote char, or newlines must
    survive a write/read round trip exactly."""
    payloads = [
        ['hello, world', 'plain'],
        ['has "embedded" quote', 'simple'],
        ['line one\nline two', 'after'],
        ['mix: a,b "c"\nd', 'tail'],
        ['', 'empty-leading'],
        ['"', ','],   # awkward single-char fields
    ]

    buf = _io.StringIO()
    w = writer(buf)
    for row in payloads:
        w.writerow(row)
    buf.seek(0)
    got = list(reader(buf))
    if got != payloads:
        return False

    # Sanity: a field with a comma must be enclosed in the quote char
    # in the serialized form, and embedded quotes must be doubled.
    buf2 = _io.StringIO()
    writer(buf2).writerow(['a,b', 'c"d'])
    serialized = buf2.getvalue()
    if '"a,b"' not in serialized:
        return False
    if '"c""d"' not in serialized:
        return False
    return True


def csv2_dictreader():
    """DictReader picks up header from first row and yields dicts."""
    buf = _io.StringIO()
    dw = DictWriter(buf, fieldnames=['name', 'age', 'city'])
    dw.writeheader()
    dw.writerow({'name': 'Alice', 'age': '30', 'city': 'NYC'})
    dw.writerow({'name': 'Bob', 'age': '25', 'city': 'Paris, France'})
    dw.writerow({'name': 'Carol', 'age': '40', 'city': 'has "quotes"'})
    buf.seek(0)

    dr = DictReader(buf)
    if dr.fieldnames != ['name', 'age', 'city']:
        return False
    rows = list(dr)
    if len(rows) != 3:
        return False
    if rows[0] != {'name': 'Alice', 'age': '30', 'city': 'NYC'}:
        return False
    if rows[1] != {'name': 'Bob', 'age': '25', 'city': 'Paris, France'}:
        return False
    if rows[2] != {'name': 'Carol', 'age': '40', 'city': 'has "quotes"'}:
        return False
    return True


__all__ = [
    'Dialect',
    'reader',
    'writer',
    'DictReader',
    'DictWriter',
    'csv2_write_read',
    'csv2_quoting',
    'csv2_dictreader',
]