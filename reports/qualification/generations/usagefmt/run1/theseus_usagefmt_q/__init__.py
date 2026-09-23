# generation A usage scan

class UsageLine(object):
    __slots__ = ("prog",)

    def __init__(self, prog):
        self.prog = prog

    def render(self):
        return "usage: %s [-h]\n" % self.prog


class ArgumentParser(object):
    def __init__(self, prog=None, **kwargs):
        if prog is None:
            import os
            import sys
            prog = os.path.basename(sys.argv[0])
        self._usage = UsageLine(prog)
        self.prog = prog

    def format_usage(self):
        return self._usage.render()
