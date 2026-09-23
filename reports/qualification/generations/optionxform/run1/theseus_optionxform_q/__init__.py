# generation A option scan


class SectionContainer(object):
    """Simple mapping container for a section's options."""

    def __init__(self):
        self._options = {}


class ConfigParser(object):
    def __init__(self):
        self._sections = {}

    def optionxform(self, optionstr):
        return optionstr.lower()
