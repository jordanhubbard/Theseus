"""
theseus_cmd_cr — Clean-room cmd module.
No import of the standard `cmd` module.
"""

import sys


class Cmd:
    """Base class for line-oriented command interpreters."""

    prompt = '(Cmd) '
    identchars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    ruler = '='
    lastcmd = ''
    intro = None
    doc_header = 'Documented commands (type help <topic>):'
    undoc_header = 'Undocumented commands:'
    misc_header = 'Miscellaneous help topics:'
    nohelp = "*** No help on %s"
    use_rawinput = True

    def __init__(self, completekey='tab', stdin=None, stdout=None):
        if stdin is not None:
            self.stdin = stdin
        else:
            self.stdin = sys.stdin
        if stdout is not None:
            self.stdout = stdout
        else:
            self.stdout = sys.stdout

    def parseline(self, line):
        """Parse a line into (command, args, line).
        Return (None, None, '') for empty; ('?', ...) for help; etc.
        """
        line = line.strip()
        if not line:
            return (None, None, '')
        if line[0] == '?':
            line = 'help ' + line[1:]
        if line[0] == '!':
            if hasattr(self, 'do_shell'):
                line = 'shell ' + line[1:]
            else:
                return (None, None, line)
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars:
            i += 1
        cmd, arg = line[:i], line[i:].strip()
        return (cmd, arg, line)

    def onecmd(self, line):
        """Interpret the argument as a command and dispatch to do_* methods."""
        cmd, arg, line = self.parseline(line)
        self.lastcmd = line
        if not line:
            return self.default(line)
        if cmd is None:
            return self.default(line)
        self.lastcmd = ''
        if cmd == '':
            return self.default(line)
        func = getattr(self, 'do_' + cmd, None)
        if func:
            return func(arg)
        else:
            return self.default(line)

    def default(self, line):
        """Called when no do_* method exists for the command."""
        self.stdout.write('*** Unknown syntax: %s\n' % line)

    def emptyline(self):
        """Called when an empty line is entered. Repeat last command."""
        if self.lastcmd:
            return self.onecmd(self.lastcmd)

    def do_help(self, arg):
        """List available commands or give help for a specific command."""
        if arg:
            func = getattr(self, 'help_' + arg, None)
            if func:
                func()
            else:
                do_func = getattr(self, 'do_' + arg, None)
                if do_func:
                    self.stdout.write(do_func.__doc__ or self.nohelp % arg)
                    self.stdout.write('\n')
                else:
                    self.stdout.write(self.nohelp % arg + '\n')
        else:
            names = [n for n in dir(self.__class__) if n.startswith('do_')]
            self.stdout.write('%s\n' % str(names))

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt and dispatch commands."""
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro) + '\n')
        stop = None
        while not stop:
            try:
                if self.use_rawinput:
                    line = input(self.prompt)
                else:
                    self.stdout.write(self.prompt)
                    self.stdout.flush()
                    line = self.stdin.readline()
                    if not line:
                        line = 'EOF'
                    else:
                        line = line.rstrip('\r\n')
            except EOFError:
                line = 'EOF'
            stop = self.onecmd(line)
        return stop


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cmd2_parseline():
    """parseline('hello world') returns ('hello', 'world', 'hello world'); returns True."""
    c = Cmd()
    cmd_part, args, line = c.parseline('hello world')
    return cmd_part == 'hello' and args == 'world' and line == 'hello world'


def cmd2_onecmd():
    """onecmd dispatches do_test method; returns 'test ran'."""
    class MyCLI(Cmd):
        def do_test(self, args):
            return 'test ran'

    c = MyCLI()
    return c.onecmd('test')


def cmd2_default():
    """onecmd with unknown command calls default; returns 'unknown'."""
    import io as _io
    out = _io.StringIO()

    class MyCLI(Cmd):
        def default(self, line):
            return 'unknown'

    c = MyCLI(stdout=out)
    return c.onecmd('nosuchthing')


__all__ = [
    'Cmd',
    'cmd2_parseline', 'cmd2_onecmd', 'cmd2_default',
]
