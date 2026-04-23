"""
theseus_csv_cr2 - Clean-room CSV processing implementation.
No import of the original csv module.
"""


class Dialect:
    """Customizable CSV dialect settings."""
    
    def __init__(self, delimiter=',', quotechar='"', lineterminator='\r\n',
                 doublequote=True, skipinitialspace=False, strict=False):
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.lineterminator = lineterminator
        self.doublequote = doublequote
        self.skipinitialspace = skipinitialspace
        self.strict = strict


def _parse_line(line, dialect):
    """Parse a single CSV line into a list of fields."""
    fields = []
    current = []
    in_quotes = False
    i = 0
    
    while i < len(line):
        ch = line[i]
        
        if in_quotes:
            if ch == dialect.quotechar:
                if dialect.doublequote and i + 1 < len(line) and line[i + 1] == dialect.quotechar:
                    # Escaped quote
                    current.append(dialect.quotechar)
                    i += 2
                    continue
                else:
                    # End of quoted field
                    in_quotes = False
                    i += 1
                    continue
            else:
                current.append(ch)
        else:
            if ch == dialect.quotechar:
                in_quotes = True
                i += 1
                continue
            elif ch == dialect.delimiter:
                fields.append(''.join(current))
                current = []
                if dialect.skipinitialspace:
                    # Skip space after delimiter
                    while i + 1 < len(line) and line[i + 1] == ' ':
                        i += 1
            else:
                current.append(ch)
        
        i += 1
    
    fields.append(''.join(current))
    return fields


def _format_field(value, dialect):
    """Format a single field for CSV output."""
    value = str(value) if value is not None else ''
    
    needs_quoting = (
        dialect.delimiter in value or
        dialect.quotechar in value or
        '\n' in value or
        '\r' in value
    )
    
    if needs_quoting:
        if dialect.doublequote:
            escaped = value.replace(dialect.quotechar, dialect.quotechar * 2)
        else:
            escaped = value
        return dialect.quotechar + escaped + dialect.quotechar
    
    return value


class DictReader:
    """Reads CSV rows as dictionaries."""
    
    def __init__(self, f, fieldnames=None, dialect=None, **kwargs):
        """
        f: iterable of strings (lines) or file-like object
        fieldnames: optional list of field names; if None, first row is used
        dialect: Dialect instance or None for default
        """
        if dialect is None:
            dialect = Dialect(**kwargs) if kwargs else Dialect()
        self.dialect = dialect
        self._fieldnames = fieldnames
        self._rows = []
        self._parse(f)
    
    def _parse(self, f):
        lines = list(f)
        
        # Strip line terminators
        stripped = []
        for line in lines:
            line = line.rstrip('\r\n')
            stripped.append(line)
        
        if not stripped:
            return
        
        idx = 0
        if self._fieldnames is None:
            # First row is header
            self._fieldnames = _parse_line(stripped[0], self.dialect)
            idx = 1
        
        for line in stripped[idx:]:
            if not line:
                continue
            values = _parse_line(line, self.dialect)
            row = {}
            for i, fieldname in enumerate(self._fieldnames):
                if i < len(values):
                    row[fieldname] = values[i]
                else:
                    row[fieldname] = None
            self._rows.append(row)
    
    @property
    def fieldnames(self):
        return self._fieldnames
    
    def __iter__(self):
        return iter(self._rows)
    
    def __getitem__(self, index):
        return self._rows[index]
    
    def __len__(self):
        return len(self._rows)


class DictWriter:
    """Writes dictionaries as CSV rows."""
    
    def __init__(self, f, fieldnames, dialect=None, **kwargs):
        """
        f: file-like object with write method, or list to append to
        fieldnames: list of field names defining column order
        dialect: Dialect instance or None for default
        """
        if dialect is None:
            dialect = Dialect(**kwargs) if kwargs else Dialect()
        self.dialect = dialect
        self.fieldnames = fieldnames
        self._f = f
        self._written_lines = []
    
    def writeheader(self):
        """Write the header row."""
        header = self.dialect.delimiter.join(
            _format_field(f, self.dialect) for f in self.fieldnames
        )
        line = header + self.dialect.lineterminator
        self._write(line)
    
    def writerow(self, row):
        """Write a single row dict."""
        values = []
        for field in self.fieldnames:
            values.append(_format_field(row.get(field, ''), self.dialect))
        line = self.dialect.delimiter.join(values) + self.dialect.lineterminator
        self._write(line)
    
    def writerows(self, rows):
        """Write multiple row dicts."""
        for row in rows:
            self.writerow(row)
    
    def _write(self, line):
        self._written_lines.append(line)
        if hasattr(self._f, 'write'):
            self._f.write(line)
        elif isinstance(self._f, list):
            self._f.append(line)
    
    def getvalue(self):
        """Return all written content as a string."""
        return ''.join(self._written_lines)


# ── Invariant test functions ──────────────────────────────────────────────────

def csv2_dictreader():
    """
    DictReader(['name,age', 'alice,30'])[0]['name'] == 'alice'
    Returns 'alice'.
    """
    reader = DictReader(['name,age', 'alice,30'])
    return reader[0]['name']


def csv2_dictwriter():
    """
    DictWriter write + read roundtrip recovers values.
    Returns True if roundtrip succeeds.
    """
    fieldnames = ['name', 'age', 'city']
    rows = [
        {'name': 'alice', 'age': '30', 'city': 'New York'},
        {'name': 'bob', 'age': '25', 'city': 'Los Angeles'},
    ]
    
    output = []
    writer = DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    
    # output is a list of lines; read them back
    lines = []
    for line in output:
        # Split on line terminator
        parts = line.split('\r\n')
        for part in parts:
            if part:
                lines.append(part)
    
    reader = DictReader(lines)
    
    if len(reader) != len(rows):
        return False
    
    for i, original in enumerate(rows):
        recovered = reader[i]
        for key, val in original.items():
            if recovered.get(key) != val:
                return False
    
    return True


def csv2_dialect_pipe():
    """
    Reader with delimiter='|' splits on pipe.
    Returns ['a', 'b', 'c'].
    """
    dialect = Dialect(delimiter='|')
    reader = DictReader(['x|y|z', 'a|b|c'], dialect=dialect)
    row = reader[0]
    return [row['x'], row['y'], row['z']]