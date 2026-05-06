"""
theseus_string_module_cr — Clean-room string module.
No import of the standard `string` module.
"""

import re as _re

whitespace = ' \t\n\r\x0b\x0c'
ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ascii_letters = ascii_lowercase + ascii_uppercase
digits = '0123456789'
hexdigits = digits + 'abcdef' + 'ABCDEF'
octdigits = '01234567'
punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
printable = digits + ascii_letters + punctuation + whitespace


def capwords(s, sep=None):
    """Capitalize words in the string s."""
    if sep is None:
        return ' '.join(x.capitalize() for x in s.split())
    else:
        return sep.join(x.capitalize() for x in s.split(sep))


class _TemplateMetaclass(type):
    pattern = r"""
    \$(?:
      (?P<escaped>\$) |           # $$
      (?P<named>%(id)s)      |    # $identifier
      \{(?P<braced>%(id)s)\}  |   # ${identifier}
      (?P<invalid>)               # other ill-formed $ signs
    )
    """

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if 'pattern' in dct:
            pattern = cls.pattern
        else:
            pattern = _TemplateMetaclass.pattern % {
                'id': cls.idpattern,
            }
        cls.pattern = _re.compile(pattern, cls.flags | _re.VERBOSE)


class Template(metaclass=_TemplateMetaclass):
    """A string class for supporting $-substitutions."""

    delimiter = '$'
    idpattern = r'(?a:[_a-z][_a-z0-9]*)'
    braceidpattern = None
    flags = _re.IGNORECASE

    def __init__(self, template):
        self.template = template

    def _invalid(self, mo):
        i = mo.start('invalid')
        lines = self.template[:i].splitlines(keepends=True)
        if not lines:
            colno = 1
            lineno = 1
        else:
            colno = i - len(''.join(lines[:-1]))
            lineno = len(lines)
        raise ValueError('Invalid placeholder in string: line %d, col %d' %
                         (lineno, colno))

    def substitute(self, mapping={}, /, **kws):
        if mapping:
            mapping = {**mapping, **kws}
        else:
            mapping = kws

        def convert(mo):
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                val = mapping[named]
                return str(val)
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                self._invalid(mo)
            raise ValueError('Unrecognized named group in pattern', self.pattern)

        return self.pattern.sub(convert, self.template)

    def safe_substitute(self, mapping={}, /, **kws):
        if mapping:
            mapping = {**mapping, **kws}
        else:
            mapping = kws

        def convert(mo):
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                try:
                    return str(mapping[named])
                except KeyError:
                    return mo.group()
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                return mo.group()
            raise ValueError('Unrecognized named group in pattern', self.pattern)

        return self.pattern.sub(convert, self.template)

    def is_valid(self):
        for mo in self.pattern.finditer(self.template):
            if mo.group('invalid') is not None:
                return False
        return True

    def get_identifiers(self):
        ids = []
        for mo in self.pattern.finditer(self.template):
            named = mo.group('named') or mo.group('braced')
            if named is not None and named not in ids:
                ids.append(named)
            elif named is None and mo.group('invalid') is None and mo.group('escaped') is None:
                raise ValueError('Unrecognized named group in pattern', self.pattern)
        return ids


class Formatter:
    """String formatter."""

    def format(self, format_string, /, *args, **kwargs):
        return self.vformat(format_string, args, kwargs)

    def vformat(self, format_string, args, kwargs):
        used_args = set()
        result, _ = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(used_args, args, kwargs)
        return result

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth, auto_arg_index=0):
        if recursion_depth < 0:
            raise ValueError('Max string formatting recursion exceeded')
        result = []
        for literal_text, field_name, format_spec, conversion in self.parse(format_string):
            if literal_text:
                result.append(literal_text)
            if field_name is not None:
                if field_name == '':
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    auto_arg_index = -1
                obj, arg_used = self.get_field(field_name, args, kwargs)
                used_args.add(arg_used)
                obj = self.convert_field(obj, conversion)
                format_spec, auto_arg_index = self._vformat(
                    format_spec, args, kwargs, used_args, recursion_depth - 1, auto_arg_index
                )
                result.append(self.format_field(obj, format_spec))
        return ''.join(result), auto_arg_index

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            return args[key]
        return kwargs[key]

    def check_unused_args(self, used_args, args, kwargs):
        pass

    def format_field(self, value, format_spec):
        return format(value, format_spec)

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        if conversion == 's':
            return str(value)
        if conversion == 'r':
            return repr(value)
        if conversion == 'a':
            return ascii(value)
        raise ValueError("Unknown conversion specifier {0!s}".format(conversion))

    def parse(self, format_string):
        return _string_parse_format(format_string)

    def get_field(self, field_name, args, kwargs):
        first, rest = field_name, ''
        m = _re.match(r'^([^.\[]*)(.*)', field_name)
        if m:
            first, rest = m.group(1), m.group(2)
        try:
            obj = self.get_value(int(first) if first.isdigit() else first, args, kwargs)
        except (KeyError, IndexError):
            raise
        for m in _re.finditer(r'\.(\w+)|\[([^\]]+)\]', rest):
            if m.group(1):
                obj = getattr(obj, m.group(1))
            else:
                idx = m.group(2)
                try:
                    obj = obj[int(idx)]
                except (ValueError, TypeError):
                    obj = obj[idx]
        return obj, first


def _string_parse_format(format_string):
    """Parse a format string into (literal_text, field_name, format_spec, conversion) tuples."""
    i = 0
    n = len(format_string)
    while i < n:
        j = format_string.find('{', i)
        k = format_string.find('}', i)
        if j == -1 and k == -1:
            yield format_string[i:], None, None, None
            return
        if j == -1:
            j = n
        if k == -1:
            k = n
        if k < j:
            if k + 1 < n and format_string[k + 1] == '}':
                yield format_string[i:k + 1], None, None, None
                i = k + 2
                continue
            raise ValueError("Single '}' encountered in format string")
        if j < n:
            if j + 1 < n and format_string[j + 1] == '{':
                yield format_string[i:j + 1], None, None, None
                i = j + 2
                continue
        literal = format_string[i:j]
        depth = 1
        k = j + 1
        while k < n and depth > 0:
            if format_string[k] == '{':
                depth += 1
            elif format_string[k] == '}':
                depth -= 1
            k += 1
        field = format_string[j + 1:k - 1]
        conversion = None
        if '!' in field:
            field, _, conv_char = field.rpartition('!')
            if ':' in conv_char:
                conv_char, _, format_spec = conv_char.partition(':')
            else:
                format_spec = ''
            conversion = conv_char
        elif ':' in field:
            field, _, format_spec = field.partition(':')
        else:
            format_spec = ''
        yield literal, field, format_spec, conversion
        i = k


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def string2_digits():
    """digits constant contains 0-9; returns True."""
    return digits == '0123456789'


def string2_template():
    """Template substitutes variables correctly; returns True."""
    t = Template('Hello, $name!')
    return t.substitute(name='World') == 'Hello, World!'


def string2_capwords():
    """capwords capitalizes words in a string; returns True."""
    return capwords('the quick brown fox') == 'The Quick Brown Fox'


__all__ = [
    'ascii_letters', 'ascii_lowercase', 'ascii_uppercase',
    'digits', 'hexdigits', 'octdigits', 'printable', 'punctuation', 'whitespace',
    'capwords', 'Template', 'Formatter',
    'string2_digits', 'string2_template', 'string2_capwords',
]