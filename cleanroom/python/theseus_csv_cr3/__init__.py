"""
theseus_csv_cr3 — Clean-room CSV DictReader/DictWriter utilities.
Do NOT import the csv module.
"""

from collections import OrderedDict
from io import StringIO


def _parse_csv_line(line):
    """Parse a single CSV line into a list of fields, handling quoted fields."""
    fields = []
    current = []
    in_quotes = False
    i = 0
    # Strip trailing newline/carriage return
    line = line.rstrip('\r\n')
    
    while i < len(line):
        ch = line[i]
        if in_quotes:
            if ch == '"':
                # Check for escaped quote ""
                if i + 1 < len(line) and line[i + 1] == '"':
                    current.append('"')
                    i += 2
                    continue
                else:
                    in_quotes = False
                    i += 1
                    continue
            else:
                current.append(ch)
                i += 1
        else:
            if ch == '"':
                in_quotes = True
                i += 1
            elif ch == ',':
                fields.append(''.join(current))
                current = []
                i += 1
            else:
                current.append(ch)
                i += 1
    
    fields.append(''.join(current))
    return fields


def _format_csv_field(value):
    """Format a single field for CSV output, quoting if necessary."""
    s = str(value) if value is not None else ''
    # Need to quote if contains comma, quote, newline, or carriage return
    if ',' in s or '"' in s or '\n' in s or '\r' in s:
        s = '"' + s.replace('"', '""') + '"'
    return s


def _format_csv_line(fields):
    """Format a list of field values as a CSV line."""
    return ','.join(_format_csv_field(f) for f in fields) + '\r\n'


class DictReader:
    """
    Read CSV rows as OrderedDict objects.
    
    Parameters
    ----------
    f : iterable of str
        Each element is a CSV row (string).
    fieldnames : list of str, optional
        If provided, use these as the field names (no header row consumed).
        If None, the first row of f is used as the header.
    """

    def __init__(self, f, fieldnames=None):
        self._iter = iter(f)
        self._fieldnames = list(fieldnames) if fieldnames is not None else None
        self._header_read = fieldnames is not None  # if fieldnames given, no need to read header

    @property
    def fieldnames(self):
        if self._fieldnames is None:
            # Read the first row as header
            try:
                header_line = next(self._iter)
                self._fieldnames = _parse_csv_line(header_line)
                self._header_read = True
            except StopIteration:
                self._fieldnames = []
                self._header_read = True
        return self._fieldnames

    def __iter__(self):
        return self

    def __next__(self):
        # Ensure fieldnames are loaded (reads header if needed)
        names = self.fieldnames
        
        line = next(self._iter)  # raises StopIteration naturally
        values = _parse_csv_line(line)
        
        row = OrderedDict()
        for i, name in enumerate(names):
            if i < len(values):
                row[name] = values[i]
            else:
                row[name] = None
        
        # Handle extra values beyond fieldnames
        if len(values) > len(names):
            row[None] = values[len(names):]
        
        return row


class DictWriter:
    """
    Write dicts to a CSV file-like object.
    
    Parameters
    ----------
    f : file-like object
        Must have a write() method.
    fieldnames : list of str
        The field names (column headers).
    """

    def __init__(self, f, fieldnames):
        self._f = f
        self.fieldnames = list(fieldnames)

    def writeheader(self):
        """Write the header row."""
        self._f.write(_format_csv_line(self.fieldnames))

    def writerow(self, rowdict):
        """Write a single row dict."""
        values = [rowdict.get(name, '') for name in self.fieldnames]
        self._f.write(_format_csv_line(values))

    def writerows(self, rowdicts):
        """Write multiple row dicts."""
        for row in rowdicts:
            self.writerow(row)


# ---------------------------------------------------------------------------
# Zero-arg invariant functions
# ---------------------------------------------------------------------------

def csv3_dictreader():
    """
    Invariant: csv3_dictreader() → "Alice"
    
    Reads ['name,age', 'Alice,30'] with header in first row,
    returns the 'name' value of the first data row.
    """
    rows = ['name,age', 'Alice,30']
    reader = DictReader(rows)
    first_row = next(iter(reader))
    return first_row['name']


def csv3_dictwriter():
    """
    Invariant: csv3_dictwriter() → True
    
    Writes {'x': '1'} to a StringIO, then reads it back and verifies.
    """
    buf = StringIO()
    writer = DictWriter(buf, fieldnames=['x'])
    writer.writeheader()
    writer.writerow({'x': '1'})
    
    buf.seek(0)
    reader = DictReader(buf)
    row = next(iter(reader))
    return row.get('x') == '1'


def csv3_fieldnames():
    """
    Invariant: csv3_fieldnames() → ["a", "b"]
    
    DictReader with explicit fieldnames=['a','b'] has those fieldnames.
    """
    rows = ['1,2', '3,4']
    reader = DictReader(rows, fieldnames=['a', 'b'])
    return reader.fieldnames