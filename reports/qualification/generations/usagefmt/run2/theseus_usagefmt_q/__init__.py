# generation B usage class


class _Usage:
    def __init__(self, prog=None, **kwargs):
        if prog is None:
            import sys
            prog = sys.argv[0]
        self.prog = prog

    def format_usage(self):
        return "usage: {0} [-h]\n".format(self.prog)


ArgumentParser = _Usage
