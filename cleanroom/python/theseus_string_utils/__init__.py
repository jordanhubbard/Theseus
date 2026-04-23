# theseus_string_utils - clean-room implementation
# No import of 'string' module allowed

# Build ascii_letters from scratch
_lowercase = 'abcdefghijklmnopqrstuvwxyz'
_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
_ascii_letters = _lowercase + _uppercase
_ascii_lowercase = _lowercase
_ascii_uppercase = _uppercase

# digits string constant (internal)
_digits = '0123456789'

# whitespace
_whitespace = ' \t\n\r\x0b\x0c'

# punctuation
_punctuation = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'

# printable
_printable = _digits + _ascii_letters + _punctuation + _whitespace


# Callable versions of constants
def digits():
    """Return the string of digit characters '0123456789'."""
    return _digits


def ascii_letters():
    """Return the string of ASCII letters (lower + upper)."""
    return _ascii_letters


def ascii_letters_len():
    """Return the length of ascii_letters (52)."""
    return len(_ascii_letters)


def ascii_lowercase():
    """Return the string of ASCII lowercase letters."""
    return _ascii_lowercase


def ascii_uppercase():
    """Return the string of ASCII uppercase letters."""
    return _ascii_uppercase


def whitespace():
    """Return the string of whitespace characters."""
    return _whitespace


def punctuation():
    """Return the string of punctuation characters."""
    return _punctuation


def printable():
    """Return the string of printable characters."""
    return _printable


def capwords(s=None, sep=None):
    """
    Capitalize each word in s.
    If sep is None, splits on whitespace and joins with single space.
    Otherwise splits on sep and joins with sep.
    If called with no arguments, returns the capwords function itself.
    """
    if s is None:
        return capwords
    if sep is None:
        words = s.split()
        return ' '.join(word.capitalize() for word in words)
    else:
        words = s.split(sep)
        return sep.join(word.capitalize() for word in words)


class Template:
    """
    A simple string template that supports $key and ${key} substitution.
    """

    def __init__(self, tmpl: str):
        self.template = tmpl

    def substitute(self, mapping: dict) -> str:
        """
        Replace $key or ${key} with values from mapping.
        Raises KeyError if a key is not found in mapping.
        Raises ValueError for malformed placeholders.
        """
        result = []
        s = self.template
        i = 0
        n = len(s)

        while i < n:
            if s[i] == '$':
                i += 1
                if i >= n:
                    raise ValueError("Single '$' at end of template")

                if s[i] == '$':
                    # Escaped dollar sign
                    result.append('$')
                    i += 1
                elif s[i] == '{':
                    # ${key} form
                    i += 1
                    j = s.find('}', i)
                    if j == -1:
                        raise ValueError("Missing closing '}' in template")
                    key = s[i:j]
                    if not key:
                        raise ValueError("Empty key in ${} placeholder")
                    result.append(str(mapping[key]))
                    i = j + 1
                elif s[i].isalpha() or s[i] == '_':
                    # $key form - key is identifier chars
                    j = i
                    while j < n and (s[j].isalnum() or s[j] == '_'):
                        j += 1
                    key = s[i:j]
                    result.append(str(mapping[key]))
                    i = j
                else:
                    raise ValueError(f"Invalid placeholder at position {i}")
            else:
                result.append(s[i])
                i += 1

        return ''.join(result)

    def safe_substitute(self, mapping: dict) -> str:
        """
        Like substitute, but leaves unrecognized placeholders intact
        instead of raising KeyError.
        """
        result = []
        s = self.template
        i = 0
        n = len(s)

        while i < n:
            if s[i] == '$':
                i += 1
                if i >= n:
                    result.append('$')
                    break

                if s[i] == '$':
                    result.append('$')
                    i += 1
                elif s[i] == '{':
                    i += 1
                    j = s.find('}', i)
                    if j == -1:
                        result.append('${')
                        result.append(s[i:])
                        i = n
                    else:
                        key = s[i:j]
                        if not key:
                            result.append('${}')
                        elif key in mapping:
                            result.append(str(mapping[key]))
                        else:
                            result.append('${' + key + '}')
                        i = j + 1
                elif s[i].isalpha() or s[i] == '_':
                    j = i
                    while j < n and (s[j].isalnum() or s[j] == '_'):
                        j += 1
                    key = s[i:j]
                    if key in mapping:
                        result.append(str(mapping[key]))
                    else:
                        result.append('$' + key)
                    i = j
                else:
                    result.append('$')
                    result.append(s[i])
                    i += 1
            else:
                result.append(s[i])
                i += 1

        return ''.join(result)


def string_capwords():
    return capwords('hello world')

def string_digits():
    return _digits

def string_ascii_letters_len():
    return len(_ascii_letters)

string_ascii_letters = ascii_letters
string_ascii_lowercase = ascii_lowercase
string_ascii_uppercase = ascii_uppercase
string_whitespace = whitespace
string_punctuation = punctuation
string_printable = printable
string_Template = Template