"""
theseus_configparser_cr2 - Clean-room configparser utilities.
No import of configparser or any third-party library.
"""


class ConfigParser:
    """
    A minimal ConfigParser implementation built from scratch.
    Supports read_dict, get, and sections methods.
    """

    def __init__(self):
        # Internal storage: dict of section_name -> dict of key -> value
        self._sections = {}

    def read_dict(self, dictionary):
        """
        Load configuration from a dictionary of the form:
            {'section_name': {'key': 'value', ...}, ...}
        """
        for section, values in dictionary.items():
            section = str(section)
            if section not in self._sections:
                self._sections[section] = {}
            for key, value in values.items():
                self._sections[section][str(key)] = str(value)

    def get(self, section, key):
        """
        Return the string value for the given section and key.
        Raises KeyError if section or key is not found.
        """
        section = str(section)
        key = str(key)
        if section not in self._sections:
            raise KeyError(f"No section: {section!r}")
        if key not in self._sections[section]:
            raise KeyError(f"No option {key!r} in section {section!r}")
        return self._sections[section][key]

    def sections(self):
        """
        Return a list of section names (excluding DEFAULT).
        """
        return list(self._sections.keys())


# ---------------------------------------------------------------------------
# Zero-argument invariant functions
# ---------------------------------------------------------------------------

def configparser2_read_dict():
    """
    Load {'sec': {'k': 'v'}} and retrieve 'v' from sec.
    Returns "v".
    """
    cfg = ConfigParser()
    cfg.read_dict({'sec': {'k': 'v'}})
    return cfg.get('sec', 'k')


def configparser2_sections():
    """
    Load two sections 'alpha' and 'beta', return their names as a list.
    Returns ["alpha", "beta"].
    """
    cfg = ConfigParser()
    cfg.read_dict({'alpha': {'x': '1'}, 'beta': {'y': '2'}})
    return cfg.sections()


def configparser2_get():
    """
    Load a dict config and get a specific key value as string.
    Returns "hello".
    """
    cfg = ConfigParser()
    cfg.read_dict({'greetings': {'message': 'hello'}})
    return cfg.get('greetings', 'message')