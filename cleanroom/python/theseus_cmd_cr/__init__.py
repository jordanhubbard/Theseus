"""Clean-room implementation of a line-oriented command interpreter base class.

This module provides a `Cmd` base class similar in spirit to the standard
library's command-interpreter facility, written from scratch without
importing or referencing the original implementation.
"""


IDENTCHARS = (
    'abcdefghijklmnopqrstuvwxyz'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '0123456789_'
)


class Cmd:
    """Base class for simple line-oriented command interpreters."""

    identchars = IDENTCHARS
    prompt = '(Cmd) '
    ruler = '='
    lastcmd = ''
    intro = None
    doc_leader = ''
    doc_header = 'Documented commands (type help <topic>):'
    misc_header = 'Miscellaneous help topics:'
    undoc_header = 'Undocumented commands:'
    nohelp = '*** No help on %s'

    def __init__(self):
        self.cmdqueue = []
        self.lastcmd = ''

    def parseline(self, line):
        """Parse a line into (command, arguments, normalized_line).

        Strips surrounding whitespace, handles the '?' shorthand for help
        and the '!' shorthand for shell, and otherwise splits the leading
        identifier-style command word from its arguments.
        """
        if line is None:
            return None, None, ''
        line = line.strip()
        if not line:
            return None, None, line
        if line[0] == '?':
            line = 'help ' + line[1:]
        elif line[0] == '!':
            if hasattr(self, 'do_shell'):
                line = 'shell ' + line[1:]
            else:
                return None, None, line
        i = 0
        n = len(line)
        while i < n and line[i] in self.identchars:
            i += 1
        cmd_word = line[:i]
        args = line[i:].strip()
        return cmd_word, args, line

    def onecmd(self, line):
        """Parse a single line and dispatch to do_<cmd>(args)."""
        cmd_word, args, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd_word is None:
            return self.default(line)
        self.lastcmd = line
        if line == '':
            return self.default(line)
        if cmd_word == '':
            return self.default(line)
        try:
            func = getattr(self, 'do_' + cmd_word)
        except AttributeError:
            return self.default(line)
        return func(args)

    def emptyline(self):
        """Called when an empty line is entered. Default: do nothing."""
        return None

    def default(self, line):
        """Called when an unrecognized command is entered."""
        return '*** Unknown syntax: ' + line

    def precmd(self, line):
        """Hook executed just before the command line is interpreted."""
        return line

    def postcmd(self, stop, line):
        """Hook executed just after a command dispatch is finished."""
        return stop

    def preloop(self):
        """Hook called once before the cmdloop begins."""
        return None

    def postloop(self):
        """Hook called once after the cmdloop ends."""
        return None

    def get_names(self):
        """Return a list of attribute names defined on this instance/class."""
        names = []
        seen = set()
        cls = type(self)
        for klass in cls.__mro__:
            for attr in vars(klass):
                if attr not in seen:
                    seen.add(attr)
                    names.append(attr)
        return names

    def do_help(self, arg):
        """Default help command — looks up help_<topic> or do_<topic>.__doc__."""
        if arg:
            try:
                func = getattr(self, 'help_' + arg)
            except AttributeError:
                try:
                    doc = getattr(self, 'do_' + arg).__doc__
                    if doc:
                        return str(doc)
                except AttributeError:
                    pass
                return self.nohelp % (arg,)
            return func()
        return None

    def cmdloop(self, intro=None):
        """Minimal command loop using input(). Returns when stop is truthy."""
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            try:
                print(self.intro)
            except Exception:
                pass
        stop = None
        try:
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    try:
                        line = input(self.prompt)
                    except EOFError:
                        line = 'EOF'
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
        finally:
            self.postloop()


# ---------------------------------------------------------------------------
# Invariant test helpers — module-level functions exercised by the harness.
# ---------------------------------------------------------------------------


def cmd2_parseline():
    """Return True iff parseline correctly splits a simple command line."""
    interpreter = Cmd()
    cmd_word, args, line = interpreter.parseline('  hello world  ')
    return (
        cmd_word == 'hello'
        and args == 'world'
        and line == 'hello world'
    )


def cmd2_onecmd():
    """Dispatch a known command via onecmd and return its result."""

    class _Test(Cmd):
        def do_test(self, arg):
            return 'test ran'

    return _Test().onecmd('test')


def cmd2_default():
    """Trigger the default handler by issuing an unknown command."""

    class _Test(Cmd):
        def default(self, line):
            return 'unknown'

    return _Test().onecmd('nosuchcommand here')


__all__ = [
    'Cmd',
    'IDENTCHARS',
    'cmd2_parseline',
    'cmd2_onecmd',
    'cmd2_default',
]