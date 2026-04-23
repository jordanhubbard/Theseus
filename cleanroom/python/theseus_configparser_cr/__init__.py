"""
Clean-room implementation of a ConfigParser-like INI file parser.
Does NOT import configparser or any third-party library.
"""


class ConfigParser:
    def __init__(self, default_section='DEFAULT'):
        self._default_section = default_section
        self._sections = {}  # OrderedDict-like, using regular dict (Python 3.7+ preserves order)
        self._defaults = {}

    def read_string(self, s):
        """Parse configuration from a string."""
        current_section = None
        
        for line in s.splitlines():
            # Strip inline comments and whitespace
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # Section header
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1].strip()
                if section_name == self._default_section:
                    current_section = None  # DEFAULT section
                else:
                    current_section = section_name
                    if current_section not in self._sections:
                        self._sections[current_section] = {}
                continue
            
            # Key-value pair
            if '=' in line or ':' in line:
                # Find the delimiter
                eq_pos = line.find('=')
                col_pos = line.find(':')
                
                if eq_pos == -1:
                    delim_pos = col_pos
                elif col_pos == -1:
                    delim_pos = eq_pos
                else:
                    delim_pos = min(eq_pos, col_pos)
                
                key = line[:delim_pos].strip().lower()
                value = line[delim_pos + 1:].strip()
                
                # Remove inline comments from value
                # (simple approach: don't strip inline comments to preserve values)
                
                if current_section is None:
                    self._defaults[key] = value
                else:
                    self._sections[current_section][key] = value

    def get(self, section, option, fallback=None):
        """Return value for option in section, or fallback if not found."""
        option = option.lower()
        
        if section in self._sections:
            if option in self._sections[section]:
                return self._sections[section][option]
        
        # Check defaults
        if option in self._defaults:
            return self._defaults[option]
        
        if fallback is not None:
            return fallback
        
        # Raise error if no fallback
        raise KeyError(f"No option '{option}' in section '{section}'")

    def sections(self):
        """Return list of section names, excluding DEFAULT."""
        return list(self._sections.keys())

    def has_section(self, section):
        """Return True if the section exists."""
        return section in self._sections

    def has_option(self, section, option):
        """Return True if the option exists in the section."""
        option = option.lower()
        if section in self._sections:
            if option in self._sections[section]:
                return True
        return option in self._defaults

    def options(self, section):
        """Return list of options in the given section."""
        if section not in self._sections:
            raise KeyError(f"No section: '{section}'")
        opts = dict(self._defaults)
        opts.update(self._sections[section])
        return list(opts.keys())

    def items(self, section=None):
        """Return list of (name, value) pairs for the section."""
        if section is None:
            return list(self._defaults.items())
        if section not in self._sections:
            raise KeyError(f"No section: '{section}'")
        result = dict(self._defaults)
        result.update(self._sections[section])
        return list(result.items())

    def set(self, section, option, value):
        """Set an option in a section."""
        option = option.lower()
        if section not in self._sections:
            raise KeyError(f"No section: '{section}'")
        self._sections[section][option] = value

    def add_section(self, section):
        """Add a section."""
        if section in self._sections:
            raise ValueError(f"Section '{section}' already exists")
        self._sections[section] = {}

    def remove_section(self, section):
        """Remove a section."""
        if section in self._sections:
            del self._sections[section]
            return True
        return False

    def remove_option(self, section, option):
        """Remove an option from a section."""
        option = option.lower()
        if section not in self._sections:
            raise KeyError(f"No section: '{section}'")
        if option in self._sections[section]:
            del self._sections[section][option]
            return True
        return False

    def defaults(self):
        """Return the defaults dictionary."""
        return dict(self._defaults)

    def read_dict(self, dictionary):
        """Load configuration from a dictionary."""
        for section, keys in dictionary.items():
            if section == self._default_section:
                for key, value in keys.items():
                    self._defaults[key.lower()] = str(value)
            else:
                if section not in self._sections:
                    self._sections[section] = {}
                for key, value in keys.items():
                    self._sections[section][key.lower()] = str(value)


def configparser_get():
    """Parse '[db]\nhost=localhost', get('db','host') == 'localhost'."""
    cp = ConfigParser()
    cp.read_string('[db]\nhost=localhost')
    return cp.get('db', 'host')


def configparser_sections():
    """sections() returns ['db']."""
    cp = ConfigParser()
    cp.read_string('[db]\nhost=localhost')
    return cp.sections()


def configparser_fallback():
    """get with fallback returns fallback when key absent."""
    cp = ConfigParser()
    cp.read_string('[db]\nhost=localhost')
    return cp.get('db', 'nonexistent_key', fallback='default_val')