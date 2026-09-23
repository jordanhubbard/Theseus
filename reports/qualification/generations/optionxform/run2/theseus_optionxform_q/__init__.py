# generation B option class


class _Parser:
    def optionxform(self, name):
        return name.lower()


ConfigParser = _Parser
