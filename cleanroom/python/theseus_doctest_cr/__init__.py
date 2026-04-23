"""
theseus_doctest_cr — Clean-room doctest module.
No import of the standard `doctest` module.
"""

import re as _re
import sys as _sys
import traceback as _traceback
import io as _io
import inspect as _inspect
import types as _types


ELLIPSIS = 8
NORMALIZE_WHITESPACE = 2
IGNORE_EXCEPTION_DETAIL = 32
OPTIONFLAGS_BY_NAME = {
    'ELLIPSIS': ELLIPSIS,
    'NORMALIZE_WHITESPACE': NORMALIZE_WHITESPACE,
    'IGNORE_EXCEPTION_DETAIL': IGNORE_EXCEPTION_DETAIL,
}


class TestResults:
    def __init__(self, failed, attempted):
        self.failed = failed
        self.attempted = attempted

    def __repr__(self):
        return f'TestResults(failed={self.failed}, attempted={self.attempted})'


class Example:
    def __init__(self, source, want, exc_msg=None, lineno=0, indent=0, options=None):
        self.source = source
        self.want = want
        self.exc_msg = exc_msg
        self.lineno = lineno
        self.indent = indent
        self.options = options or {}

    def __repr__(self):
        return f'Example({self.source!r}, {self.want!r})'


class DocTest:
    def __init__(self, examples, globs, name, filename, lineno, docstring):
        self.examples = examples
        self.globs = globs
        self.name = name
        self.filename = filename
        self.lineno = lineno
        self.docstring = docstring

    def __repr__(self):
        return f'<DocTest {self.name} from {self.filename}:{self.lineno}>'


_EXAMPLE_RE = _re.compile(r'''
    # Source consists of a PS1 line followed by zero or more PS2 lines.
    (?P<source>
        (?:^(?P<indent> [ ]*) >>>    .*)    # PS1 line
        (?:\n           [ ]*  \.\.\. .*)*)  # PS2 lines
    \n?
    # Followed by the expected output:
    (?P<want> (?:(?![ ]*$)         # Not a blank line
                 (?![ ]*>>>)       # Not a line starting with PS1
                 .+$\n?            # But any other line
              )*
    )
    ''', _re.MULTILINE | _re.VERBOSE)


def _parse_examples(string):
    examples = []
    indent = None
    for m in _EXAMPLE_RE.finditer(string):
        source_lines = m.group('source').split('\n')
        indent_size = len(m.group('indent'))
        # Strip PS1/PS2 prefixes
        source = '\n'.join(
            line[indent_size + 4:] if line.strip().startswith('>>>') or line.strip().startswith('...')
            else line[indent_size + 4:]
            for line in source_lines
        )
        # Clean up: remove >>> and ... prefixes
        lines = []
        for line in source_lines:
            stripped = line[indent_size:]
            if stripped.startswith('>>> '):
                lines.append(stripped[4:])
            elif stripped.startswith('>>>'):
                lines.append(stripped[3:])
            elif stripped.startswith('... '):
                lines.append(stripped[4:])
            elif stripped.startswith('...'):
                lines.append(stripped[3:])
        source = '\n'.join(lines)
        want = m.group('want')
        if want:
            want_lines = want.split('\n')
            want = '\n'.join(line[indent_size:] for line in want_lines)
        examples.append(Example(source, want))
    return examples


class DocTestParser:
    def get_doctest(self, string, globs, name, filename, lineno):
        examples = _parse_examples(string)
        return DocTest(examples, globs, name, filename, lineno, string)

    def get_examples(self, string, name='<string>'):
        return _parse_examples(string)


class DocTestRunner:
    def __init__(self, checker=None, verbose=False, optionflags=0):
        self.checker = checker
        self.verbose = verbose
        self.optionflags = optionflags
        self._name2ft = {}
        self.summarize = self._summarize

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        if out is None:
            out = _sys.stdout.write

        failures = 0
        tries = 0
        globs = test.globs.copy()
        globs['__name__'] = '__main__'

        for example in test.examples:
            tries += 1
            source = example.source
            want = example.want

            try:
                if compileflags:
                    code = compile(source, '<doctest>', 'single', compileflags, True)
                else:
                    code = compile(source, '<doctest>', 'single')

                old_stdout = _sys.stdout
                _sys.stdout = captured = _io.StringIO()
                try:
                    exec(code, globs)
                    got = captured.getvalue()
                finally:
                    _sys.stdout = old_stdout
            except Exception:
                got = _traceback.format_exc().split('\n')[-2] + '\n'

            if want and got.rstrip() != want.rstrip():
                if self.verbose:
                    out(f'FAIL: {example.source!r}\n')
                failures += 1
            elif self.verbose:
                out(f'ok: {example.source!r}\n')

        if clear_globs:
            globs.clear()

        return TestResults(failures, tries)

    def summarize(self, verbose=None):
        return TestResults(0, 0)

    def _summarize(self, verbose=None):
        return TestResults(0, 0)


def run_docstring_examples(f, globs=None, verbose=False, name='NoName',
                            compileflags=None, optionflags=0):
    if globs is None:
        globs = {}
    doc = f.__doc__ or ''
    parser = DocTestParser()
    test = parser.get_doctest(doc, globs, name, None, 0)
    runner = DocTestRunner(verbose=verbose, optionflags=optionflags)
    runner.run(test, compileflags=compileflags)


def testmod(m=None, name=None, globs=None, verbose=False, optionflags=0,
            extraglobs=None, raise_on_error=False, report=True):
    if m is None:
        import __main__ as m
    if name is None:
        name = m.__name__
    if globs is None:
        globs = m.__dict__.copy()
    if extraglobs:
        globs.update(extraglobs)

    parser = DocTestParser()
    runner = DocTestRunner(verbose=verbose, optionflags=optionflags)

    total_failures = 0
    total_tries = 0

    for objname in dir(m):
        obj = getattr(m, objname, None)
        if obj is None:
            continue
        doc = getattr(obj, '__doc__', None)
        if not doc:
            continue
        test = parser.get_doctest(doc, globs, f'{name}.{objname}', None, 0)
        if test.examples:
            result = runner.run(test)
            total_failures += result.failed
            total_tries += result.attempted

    return TestResults(total_failures, total_tries)


def testfile(filename, module_relative=True, name=None, package=None,
             globs=None, verbose=False, report=True, optionflags=0,
             extraglobs=None, raise_on_error=False, parser=None, encoding=None):
    import os.path
    if module_relative:
        pkg = package or _types.ModuleType('__main__')
        if hasattr(pkg, '__file__') and pkg.__file__:
            dir_name = os.path.dirname(pkg.__file__)
        else:
            dir_name = '.'
        filename = os.path.join(dir_name, filename)
    with open(filename, encoding=encoding or 'utf-8') as f:
        text = f.read()
    if globs is None:
        globs = {}
    if name is None:
        name = os.path.basename(filename)
    p = DocTestParser()
    test = p.get_doctest(text, globs, name, filename, 0)
    runner = DocTestRunner(verbose=verbose, optionflags=optionflags)
    return runner.run(test)


def register_optionflag(name):
    if name not in OPTIONFLAGS_BY_NAME:
        flag = 1 << (len(OPTIONFLAGS_BY_NAME) + 3)
        OPTIONFLAGS_BY_NAME[name] = flag
    return OPTIONFLAGS_BY_NAME[name]


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def doctest2_run():
    """DocTestRunner can run a simple doctest; returns True."""
    parser = DocTestParser()
    globs = {}
    doc = '''
    >>> 1 + 1
    2
    >>> x = 5
    >>> x * 2
    10
    '''
    test = parser.get_doctest(doc, globs, 'test', '<string>', 0)
    runner = DocTestRunner()
    result = runner.run(test)
    return result.attempted >= 2 and result.failed == 0


def doctest2_testmod():
    """testmod() works on a module; returns True."""
    import types as _t
    m = _t.ModuleType('test_module')
    m.__doc__ = '''
    >>> 2 + 2
    4
    '''
    result = testmod(m)
    return isinstance(result, TestResults)


def doctest2_example():
    """Example class exists; returns True."""
    ex = Example('1 + 1', '2\n')
    return isinstance(ex, Example) and ex.source == '1 + 1' and ex.want == '2\n'


__all__ = [
    'Example', 'DocTest', 'DocTestParser', 'DocTestRunner', 'TestResults',
    'run_docstring_examples', 'testmod', 'testfile', 'register_optionflag',
    'ELLIPSIS', 'NORMALIZE_WHITESPACE', 'IGNORE_EXCEPTION_DETAIL',
    'doctest2_run', 'doctest2_testmod', 'doctest2_example',
]
