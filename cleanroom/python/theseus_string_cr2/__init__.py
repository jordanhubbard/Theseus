"""
theseus_string_cr2 - Clean-room extended string utilities.
Do NOT import the `string` module.
"""

import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ascii_letters = ascii_lowercase + ascii_uppercase
digits = '0123456789'
punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""


# ---------------------------------------------------------------------------
# capwords
# ---------------------------------------------------------------------------

def capwords(s, sep=None):
    """Split s into words, capitalize each, and join with sep (or single space)."""
    if sep is None:
        words = s.split()
        return ' '.join(w.capitalize() for w in words)
    else:
        words = s.split(sep)
        return sep.join(w.capitalize() for w in words)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

class Formatter:
    """
    Advanced string formatter supporting {} positional and {name} keyword
    placeholders, as well as {0}, {1}, etc.
    """

    def format(self, format_string, *args, **kwargs):
        return self.vformat(format_string, args, kwargs)

    def vformat(self, format_string, args, kwargs):
        result, _ = self._vformat(format_string, args, kwargs, set(), 2)
        return result

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth,
                 auto_arg_index=0):
        if recursion_depth < 0:
            raise ValueError('Max string formatting recursion exceeded')

        result = []
        # Parse the format string into literal text and field specs
        for literal_text, field_name, format_spec, conversion in \
                self._parse(format_string):
            if literal_text:
                result.append(literal_text)

            if field_name is not None:
                # Determine the object to format
                obj, auto_arg_index = self.get_field(
                    field_name, args, kwargs, auto_arg_index)
                used_args.add(field_name)

                # Apply conversion
                obj = self.convert_field(obj, conversion)

                # Recursively format the format_spec
                format_spec, auto_arg_index = self._vformat(
                    format_spec, args, kwargs, used_args,
                    recursion_depth - 1, auto_arg_index)

                # Format the object
                result.append(self.format_field(obj, format_spec))

        return ''.join(result), auto_arg_index

    def _parse(self, format_string):
        """
        Yield (literal_text, field_name, format_spec, conversion) tuples.
        Handles {{ and }} escapes.
        """
        i = 0
        n = len(format_string)
        literal_chars = []

        while i < n:
            ch = format_string[i]

            if ch == '{':
                if i + 1 < n and format_string[i + 1] == '{':
                    # Escaped brace
                    literal_chars.append('{')
                    i += 2
                    continue
                # Start of a replacement field
                # Yield accumulated literal text
                literal_text = ''.join(literal_chars)
                literal_chars = []

                # Find matching closing brace (handle nested braces for format_spec)
                depth = 1
                j = i + 1
                while j < n and depth > 0:
                    if format_string[j] == '{':
                        depth += 1
                    elif format_string[j] == '}':
                        depth -= 1
                    j += 1

                if depth != 0:
                    raise ValueError('Single \'{\' encountered in format string')

                field_content = format_string[i + 1: j - 1]
                i = j

                # Parse field_content: field_name(!conversion)(:format_spec)
                conversion = None
                format_spec = ''

                # Split on '!' for conversion, but only outside nested braces
                excl_pos = self._find_outside_braces(field_content, '!')
                colon_pos = self._find_outside_braces(field_content, ':')

                if excl_pos != -1 and (colon_pos == -1 or excl_pos < colon_pos):
                    # Has conversion
                    if colon_pos != -1:
                        format_spec = field_content[colon_pos + 1:]
                        conversion = field_content[excl_pos + 1: colon_pos]
                    else:
                        conversion = field_content[excl_pos + 1:]
                    field_name = field_content[:excl_pos]
                elif colon_pos != -1:
                    field_name = field_content[:colon_pos]
                    format_spec = field_content[colon_pos + 1:]
                else:
                    field_name = field_content

                yield (literal_text, field_name, format_spec, conversion)

            elif ch == '}':
                if i + 1 < n and format_string[i + 1] == '}':
                    literal_chars.append('}')
                    i += 2
                    continue
                else:
                    raise ValueError('Single \'}\' encountered in format string')
            else:
                literal_chars.append(ch)
                i += 1

        # Yield any remaining literal text
        if literal_chars:
            yield (''.join(literal_chars), None, None, None)

    def _find_outside_braces(self, s, char):
        """Find the first occurrence of char outside of nested braces."""
        depth = 0
        for i, ch in enumerate(s):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            elif ch == char and depth == 0:
                return i
        return -1

    def get_field(self, field_name, args, kwargs, auto_arg_index=0):
        """
        Given a field_name string, return (obj, auto_arg_index).
        Handles auto-numbering ({}), explicit index ({0}), and keyword ({name}).
        Also handles attribute access and item access (e.g., {0.name}, {0[key]}).
        """
        # Split on '.' and '[' to get the first part
        first, rest = self._split_field_name(field_name)

        if first == '':
            # Auto-numbering
            obj = self.get_value(auto_arg_index, args, kwargs)
            auto_arg_index += 1
        else:
            try:
                index = int(first)
                obj = self.get_value(index, args, kwargs)
            except (ValueError, TypeError):
                obj = self.get_value(first, args, kwargs)

        # Apply attribute/item lookups
        for is_attr, key in rest:
            if is_attr:
                obj = getattr(obj, key)
            else:
                try:
                    obj = obj[int(key)]
                except (ValueError, TypeError, KeyError):
                    obj = obj[key]

        return obj, auto_arg_index

    def _split_field_name(self, field_name):
        """
        Split field_name into (first, [(is_attr, key), ...]).
        e.g. 'foo.bar[0]' -> ('foo', [(True, 'bar'), (False, '0')])
        """
        rest = []
        # Find first '.' or '['
        i = 0
        n = len(field_name)
        while i < n and field_name[i] not in ('.', '['):
            i += 1
        first = field_name[:i]

        while i < n:
            if field_name[i] == '.':
                i += 1
                j = i
                while j < n and field_name[j] not in ('.', '['):
                    j += 1
                rest.append((True, field_name[i:j]))
                i = j
            elif field_name[i] == '[':
                i += 1
                j = i
                while j < n and field_name[j] != ']':
                    j += 1
                rest.append((False, field_name[i:j]))
                i = j + 1  # skip ']'

        return first, rest

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            return args[key]
        else:
            return kwargs[key]

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        elif conversion == 's':
            return str(value)
        elif conversion == 'r':
            return repr(value)
        elif conversion == 'a':
            return ascii(value)
        else:
            raise ValueError(f'Unknown conversion specifier: {conversion!s}')

    def format_field(self, value, format_spec):
        return format(value, format_spec)


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

# Pattern for $identifier, ${identifier}, $$
_TEMPLATE_PATTERN = re.compile(
    r'\$(?:'
    r'(\$)|'                    # group 1: escaped $$
    r'\{([_a-z][_a-z0-9]*)\}|' # group 2: ${identifier}
    r'([_a-z][_a-z0-9]*)'      # group 3: $identifier
    r')',
    re.IGNORECASE
)


class Template:
    """
    String template with $-based substitution.
    """

    def __init__(self, template):
        self.template = template

    def substitute(self, mapping=None, **kwargs):
        if mapping is None:
            mapping = {}
        mapping = {**mapping, **kwargs}

        def replace(match):
            if match.group(1) is not None:
                return '$'
            key = match.group(2) or match.group(3)
            try:
                return str(mapping[key])
            except KeyError:
                raise KeyError(key)

        return _TEMPLATE_PATTERN.sub(replace, self.template)

    def safe_substitute(self, mapping=None, **kwargs):
        if mapping is None:
            mapping = {}
        mapping = {**mapping, **kwargs}

        def replace(match):
            if match.group(1) is not None:
                return '$'
            key = match.group(2) or match.group(3)
            if key in mapping:
                return str(mapping[key])
            # Leave the placeholder as-is
            return match.group(0)

        return _TEMPLATE_PATTERN.sub(replace, self.template)


# ---------------------------------------------------------------------------
# Zero-arg invariant functions
# ---------------------------------------------------------------------------

def string2_formatter_basic():
    """Formatter().format('hello {}', 'world') == 'hello world'"""
    return Formatter().format('hello {}', 'world')


def string2_template_safe():
    """Template('$x is $y').safe_substitute(x='hi') == 'hi is $y'"""
    return Template('$x is $y').safe_substitute(x='hi')


def string2_capwords():
    """capwords('hello world') == 'Hello World'"""
    return capwords('hello world')