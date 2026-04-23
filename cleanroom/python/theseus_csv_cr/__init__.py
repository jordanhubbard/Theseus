"""
theseus_csv_cr — Clean-room CSV reader/writer.
No import of the standard `csv` module.
"""

import io as _io
import re as _re


QUOTE_MINIMAL = 0
QUOTE_ALL = 1
QUOTE_NONNUMERIC = 2
QUOTE_NONE = 3


class Dialect:
    """Describes a CSV format."""
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = QUOTE_MINIMAL
    escapechar = None
    strict = False


class excel(Dialect):
    """Standard Excel CSV format."""
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\r\n'
    quoting = QUOTE_MINIMAL


class excel_tab(excel):
    """Excel CSV format with tab delimiter."""
    delimiter = '\t'


class unix_dialect(Dialect):
    """Unix-style CSV: newline line terminator, quoting all fields."""
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = QUOTE_ALL


_dialects = {
    'excel': excel,
    'excel-tab': excel_tab,
    'unix': unix_dialect,
}


def register_dialect(name, dialect=excel, **fmtparams):
    d = type(name, (dialect,), fmtparams)
    _dialects[name] = d


def get_dialect(name):
    try:
        return _dialects[name]()
    except KeyError:
        raise Exception(f"unknown dialect: {name!r}")


def _make_dialect(dialectname, **fmtparams):
    if isinstance(dialectname, str):
        d = get_dialect(dialectname)
    elif isinstance(dialectname, type) and issubclass(dialectname, Dialect):
        d = dialectname()
    elif isinstance(dialectname, Dialect):
        d = dialectname
    else:
        d = excel()
    for k, v in fmtparams.items():
        setattr(d, k, v)
    return d


def _quote_field(field, dialect):
    field = str(field)
    must_quote = (
        dialect.quoting == QUOTE_ALL
        or (dialect.delimiter in field)
        or (dialect.quotechar and dialect.quotechar in field)
        or '\n' in field or '\r' in field
    )
    if dialect.quoting == QUOTE_NONE:
        return field
    if not must_quote:
        return field
    qc = dialect.quotechar or '"'
    if dialect.doublequote:
        field = field.replace(qc, qc + qc)
    return qc + field + qc


def _parse_line(line, dialect):
    """Parse a single CSV line into a list of fields."""
    fields = []
    current = []
    in_quotes = False
    i = 0
    qc = dialect.quotechar or '"'
    dl = dialect.delimiter

    # Strip trailing newline
    line = line.rstrip('\r\n')

    while i < len(line):
        c = line[i]
        if in_quotes:
            if c == qc:
                if dialect.doublequote and i + 1 < len(line) and line[i + 1] == qc:
                    current.append(qc)
                    i += 2
                    continue
                else:
                    in_quotes = False
                    i += 1
                    continue
            else:
                current.append(c)
                i += 1
        else:
            if c == qc:
                in_quotes = True
                i += 1
            elif c == dl:
                fields.append(''.join(current))
                current = []
                i += 1
            else:
                current.append(c)
                i += 1
    fields.append(''.join(current))
    return fields


class reader:
    def __init__(self, csvfile, dialect='excel', **fmtparams):
        self._file = iter(csvfile)
        self._dialect = _make_dialect(dialect, **fmtparams)
        self.line_num = 0

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self._file)
        self.line_num += 1
        return _parse_line(line, self._dialect)


class writer:
    def __init__(self, csvfile, dialect='excel', **fmtparams):
        self._file = csvfile
        self._dialect = _make_dialect(dialect, **fmtparams)

    def writerow(self, row):
        fields = [_quote_field(f, self._dialect) for f in row]
        line = self._dialect.delimiter.join(fields) + self._dialect.lineterminator
        self._file.write(line)
        return line

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class DictReader:
    def __init__(self, f, fieldnames=None, restkey=None, restval=None,
                 dialect='excel', **fmtparams):
        self._reader = reader(f, dialect, **fmtparams)
        self.fieldnames = fieldnames
        self.restkey = restkey
        self.restval = restval
        self.line_num = 0

    def __iter__(self):
        return self

    @property
    def fieldnames(self):
        if self._fieldnames is None:
            try:
                self._fieldnames = next(self._reader)
            except StopIteration:
                pass
        self.line_num = self._reader.line_num
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, value):
        self._fieldnames = value

    def __next__(self):
        if self._fieldnames is None:
            self.fieldnames
        row = next(self._reader)
        self.line_num = self._reader.line_num
        while row == []:
            row = next(self._reader)
        d = dict(zip(self.fieldnames, row))
        lf = len(self.fieldnames)
        lr = len(row)
        if lr > lf:
            d[self.restkey] = row[lf:]
        elif lr < lf:
            for key in self.fieldnames[lr:]:
                d[key] = self.restval
        return d


class DictWriter:
    def __init__(self, f, fieldnames, restval='', extrasaction='raise',
                 dialect='excel', **fmtparams):
        self._writer = writer(f, dialect, **fmtparams)
        self.fieldnames = fieldnames
        self.restval = restval
        self.extrasaction = extrasaction

    def writeheader(self):
        return self._writer.writerow(self.fieldnames)

    def writerow(self, rowdict):
        row = [rowdict.get(k, self.restval) for k in self.fieldnames]
        return self._writer.writerow(row)

    def writerows(self, rowdicts):
        for row in rowdicts:
            self.writerow(row)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def csv2_write_read():
    """Write rows to StringIO then read back; returns True."""
    buf = _io.StringIO()
    w = writer(buf)
    w.writerow(['name', 'age'])
    w.writerow(['Alice', '30'])
    buf.seek(0)
    rows = list(reader(buf))
    return rows[0] == ['name', 'age'] and rows[1] == ['Alice', '30']


def csv2_quoting():
    """Fields with commas are properly quoted; returns True."""
    buf = _io.StringIO()
    w = writer(buf)
    w.writerow(['hello, world', 'foo'])
    line = buf.getvalue()
    return '"hello, world"' in line


def csv2_dictreader():
    """DictReader returns dicts with header keys; returns True."""
    data = 'name,age\nAlice,30\nBob,25\n'
    rows = list(DictReader(_io.StringIO(data)))
    return rows[0]['name'] == 'Alice' and rows[1]['age'] == '25'


__all__ = [
    'reader', 'writer', 'DictReader', 'DictWriter',
    'Dialect', 'excel', 'excel_tab', 'unix_dialect',
    'register_dialect', 'get_dialect',
    'QUOTE_MINIMAL', 'QUOTE_ALL', 'QUOTE_NONNUMERIC', 'QUOTE_NONE',
    'csv2_write_read', 'csv2_quoting', 'csv2_dictreader',
]
