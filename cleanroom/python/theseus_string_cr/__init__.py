# theseus_string_cr - Clean-room implementation of string module constants and Template

digits = '0123456789'
ascii_lowercase = 'abcdefghijklmnopqrstuvwxyz'
ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ascii_letters = ascii_lowercase + ascii_uppercase
punctuation = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
whitespace = ' \t\n\r\x0b\x0c'


import re as _re

class Template:
    """A string template with $-based substitution."""
    
    # Pattern to match $identifier, ${identifier}, or $$
    _pattern = _re.compile(
        r'\$\{([^}]+)\}'   # ${identifier}
        r'|\$([_a-zA-Z][_a-zA-Z0-9]*)'  # $identifier
        r'|\$\$'           # $$
        r'|\$'             # lone $ (invalid)
    )
    
    def __init__(self, template):
        self.template = template
    
    def substitute(self, **kws):
        def replace(match):
            # ${identifier}
            key = match.group(1)
            if key is not None:
                if key not in kws:
                    raise KeyError(key)
                return str(kws[key])
            # $identifier
            key = match.group(2)
            if key is not None:
                if key not in kws:
                    raise KeyError(key)
                return str(kws[key])
            # $$
            if match.group(0) == '$$':
                return '$'
            # lone $
            raise ValueError(f'Invalid placeholder in string: {match.group(0)!r}')
        
        return self._pattern.sub(replace, self.template)
    
    def safe_substitute(self, **kws):
        def replace(match):
            # ${identifier}
            key = match.group(1)
            if key is not None:
                if key not in kws:
                    return match.group(0)
                return str(kws[key])
            # $identifier
            key = match.group(2)
            if key is not None:
                if key not in kws:
                    return match.group(0)
                return str(kws[key])
            # $$
            if match.group(0) == '$$':
                return '$'
            # lone $
            return match.group(0)
        
        return self._pattern.sub(replace, self.template)


def string_template_sub():
    """Template('Hello $name').substitute(name='World') == 'Hello World'"""
    return Template('Hello $name').substitute(name='World')


def string_digits():
    """Returns the digits string."""
    return digits


def string_ascii_lower():
    """Returns the ascii_lowercase string."""
    return ascii_lowercase