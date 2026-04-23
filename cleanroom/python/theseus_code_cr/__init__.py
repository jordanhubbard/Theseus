"""
theseus_code_cr — Clean-room code module.
No import of the standard `code` module.
"""

import sys as _sys
import traceback as _traceback

try:
    from theseus_codeop_cr import compile_command as _compile_command
except ImportError:
    def _compile_command(source, filename='<input>', symbol='single'):
        try:
            return compile(source, filename, symbol)
        except SyntaxError:
            return None


class InteractiveInterpreter:
    """Python interactive interpreter."""

    def __init__(self, locals=None):
        if locals is None:
            locals = {'__name__': '__console__', '__doc__': None}
        self.locals = locals

    def runsource(self, source, filename='<input>', symbol='single'):
        try:
            code = _compile_command(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(filename)
            return False
        if code is None:
            return True
        self.runcode(code)
        return False

    def runcode(self, code):
        try:
            exec(code, self.locals)
        except SystemExit:
            raise
        except Exception:
            self.showtraceback()

    def showsyntaxerror(self, filename=None):
        _type, value, tb = _sys.exc_info()
        _sys.last_type = _type
        _sys.last_value = value
        _sys.last_traceback = tb
        if filename and _type is SyntaxError:
            try:
                msg, (dummy_filename, lineno, offset, line) = value.args
                value.args = msg, (filename, lineno, offset, line)
                value.filename = filename
            except Exception:
                pass
        self.write(_traceback.format_exception_only(_type, value)[-1])

    def showtraceback(self):
        _type, value, tb = _sys.exc_info()
        _sys.last_type = _type
        _sys.last_value = value
        _sys.last_traceback = tb
        tblist = _traceback.extract_tb(tb)
        del tblist[:1]
        lines = _traceback.format_list(tblist)
        if lines:
            lines.insert(0, "Traceback (most recent call last):\n")
        lines.extend(_traceback.format_exception_only(_type, value))
        self.write(''.join(lines))

    def write(self, data):
        _sys.stderr.write(data)


class InteractiveConsole(InteractiveInterpreter):
    """Emulate Python's interactive console."""

    def __init__(self, locals=None, filename='<console>'):
        super().__init__(locals)
        self.filename = filename
        self.resetbuffer()

    def resetbuffer(self):
        self.buffer = []

    def interact(self, banner=None, exitmsg=None):
        if banner is None:
            banner = f"Python {_sys.version}\nType 'exit()' or Ctrl-D to quit."
        if banner:
            self.write(banner + '\n')
        more = False
        while True:
            try:
                if more:
                    prompt = '... '
                else:
                    prompt = '>>> '
                try:
                    line = self.raw_input(prompt)
                except EOFError:
                    self.write('\n')
                    break
            except KeyboardInterrupt:
                self.write('\nKeyboardInterrupt\n')
                self.resetbuffer()
                more = False
            else:
                more = self.push(line)
        if exitmsg:
            self.write(exitmsg + '\n')

    def push(self, line):
        self.buffer.append(line)
        source = '\n'.join(self.buffer)
        more = self.runsource(source, self.filename)
        if not more:
            self.resetbuffer()
        return more

    def raw_input(self, prompt=''):
        return input(prompt)

    def write(self, data):
        _sys.stderr.write(data)


def interact(banner=None, readfunc=None, local=None, exitmsg=None):
    """Closely emulate the interactive Python interpreter."""
    console = InteractiveConsole(local)
    if readfunc is not None:
        console.raw_input = readfunc
    console.interact(banner, exitmsg)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def code2_interpreter():
    """InteractiveInterpreter can execute code; returns True."""
    globs = {}
    interp = InteractiveInterpreter(globs)
    interp.runcode(compile('x = 42', '<test>', 'exec'))
    return globs.get('x') == 42


def code2_console():
    """InteractiveConsole exists and is instantiatable; returns True."""
    console = InteractiveConsole({'__name__': '__console__'})
    return isinstance(console, InteractiveConsole)


def code2_push():
    """push() returns True for incomplete input; returns True."""
    console = InteractiveConsole()
    result = console.push('def f():')
    return result is True


__all__ = [
    'InteractiveInterpreter', 'InteractiveConsole', 'interact',
    'code2_interpreter', 'code2_console', 'code2_push',
]
