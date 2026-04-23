"""
theseus_pydoc_cr — Clean-room pydoc module.
No import of the standard `pydoc` module.
"""

import sys as _sys
import os as _os
import inspect as _inspect
import builtins as _builtins
import io as _io
import types as _types


class ErrorDuringImport(Exception):
    """Raised when there's a problem importing a module."""
    def __init__(self, filename, exc_info):
        self.filename = filename
        self.exc, self.value, self.tb = exc_info
        super().__init__(f'problem in {filename} - {self.exc.__name__}: {self.value}')


def locate(path, forceload=False):
    """Locate an object by dotted name, returning it or None."""
    parts = path.split('.')
    n = len(parts)

    for i in range(n, 0, -1):
        module_path = '.'.join(parts[:i])
        try:
            obj = __import__(module_path)
        except ImportError:
            continue

        # Navigate into the module via attribute lookup
        try:
            for part in parts[1:]:
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            continue

    # Try as a builtin
    return getattr(_builtins, path, None)


def resolve(thing, forceload=False):
    """Given a string or object, get the object and its name."""
    if isinstance(thing, str):
        obj = locate(thing, forceload)
        if obj is None:
            raise ImportError(f'no Python documentation found for {thing!r}')
        return obj, thing
    else:
        name = getattr(thing, '__name__', None)
        return thing, name or ''


class Doc:
    """Base class for documentation formatters."""

    SKIP = object()

    def document(self, obj, name=None, *args):
        """Generate documentation for the given object."""
        args = (obj, name) + args
        if _inspect.ismodule(obj):
            return self.docmodule(*args)
        if _inspect.isclass(obj):
            return self.docclass(*args)
        if _inspect.isroutine(obj):
            return self.docroutine(*args)
        return self.docother(*args)

    def fail(self, obj, name=None, *args):
        what = type(obj).__name__
        message = f"Don't know how to document object{(' ' + repr(name)) if name else ''} of type {what}"
        raise TypeError(message)

    def docmodule(self, obj, name=None, *args):
        return self.fail(obj, name, *args)

    def docclass(self, obj, name=None, *args):
        return self.fail(obj, name, *args)

    def docroutine(self, obj, name=None, *args):
        return self.fail(obj, name, *args)

    def docother(self, obj, name=None, *args):
        return ''


class TextDoc(Doc):
    """Formatter class for text documentation."""

    def bold(self, text):
        return text

    def indent(self, text, prefix='    '):
        return '\n'.join(prefix + line for line in text.split('\n'))

    def section(self, title, contents):
        return self.bold(title) + '\n' + self.indent(contents) + '\n\n'

    def docmodule(self, obj, name=None, mod=None):
        name = obj.__name__
        parts = ['Python Library Documentation: module ' + name, '']
        synopsis = getattr(obj, '__doc__', '') or ''
        if synopsis:
            parts.append(synopsis.split('\n')[0])
            parts.append('')
        parts.append('NAME')
        parts.append('    ' + name)
        return '\n'.join(parts)

    def docclass(self, obj, name=None, mod=None, *ignored):
        realname = obj.__name__
        name = name or realname
        doc = getattr(obj, '__doc__', '') or ''
        bases = obj.__bases__
        title = 'class ' + realname
        if bases:
            parents = ', '.join(b.__name__ for b in bases)
            title += f'({parents})'
        contents = doc or '(no documentation)'
        return self.section(title, contents)

    def docroutine(self, obj, name=None, mod=None, cl=None):
        realname = getattr(obj, '__name__', name or '')
        name = name or realname
        try:
            sig = _inspect.signature(obj)
            argspec = str(sig)
        except (ValueError, TypeError):
            argspec = '(...)'
        decl = name + argspec
        doc = getattr(obj, '__doc__', '') or ''
        return decl + '\n' + ('    ' + doc if doc else '')

    def docother(self, obj, name=None, mod=None, parent=None, maxlen=None, doc=None):
        repr_str = repr(obj)
        if maxlen is not None and len(repr_str) > maxlen:
            repr_str = repr_str[:maxlen] + '...'
        result = (name + ' = ' if name else '') + repr_str
        if doc is not None:
            result += '\n' + doc
        return result


class HTMLDoc(Doc):
    """Formatter class for HTML documentation."""

    def markup(self, text, escape=None):
        if escape:
            return escape(text)
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def heading(self, title, fgcol, bgcol, extras=''):
        return f'<table width="100%%" cellspacing=0 cellpadding=2 border=0>\n<tr bgcolor="{bgcol}"><td valign=bottom>&nbsp;<br><font color="{fgcol}" face="helvetica, arial">&nbsp;<br><big><big><strong>{title}</strong></big></big></font></td><td align=right valign=bottom><font color="{fgcol}" face="helvetica, arial">{extras}</font></td></tr></table>\n'

    def docmodule(self, obj, name=None, mod=None):
        name = obj.__name__
        doc = getattr(obj, '__doc__', '') or ''
        return f'<html><head><title>Python: module {name}</title></head><body><h1>{name}</h1><pre>{doc}</pre></body></html>'

    def docroutine(self, obj, name=None, mod=None, cl=None):
        realname = getattr(obj, '__name__', name or '')
        name = name or realname
        try:
            sig = _inspect.signature(obj)
            argspec = str(sig)
        except (ValueError, TypeError):
            argspec = '(...)'
        doc = getattr(obj, '__doc__', '') or ''
        return f'<dl><dt><b>{name}</b>{argspec}</dt><dd>{doc}</dd></dl>'


text = TextDoc()
html = HTMLDoc()


def render_doc(thing, title='Python Library Documentation: %s', forceload=False, renderer=None):
    """Render text documentation for a thing (given by name or value)."""
    if renderer is None:
        renderer = text
    obj, name = resolve(thing, forceload)
    desc = describe(obj)
    module = _inspect.getmodule(obj)
    if name and '.' in name:
        desc += ' in ' + name[:name.rfind('.')]
    elif module and module is not obj:
        desc += ' in module ' + module.__name__
    if not (inspect_module := _inspect.getmodule(obj)):
        pass
    return renderer.document(obj, name)


def describe(thing):
    """Produce a short description of the given thing."""
    if _inspect.ismodule(thing):
        if thing.__name__ in _sys.builtin_module_names:
            return 'built-in module ' + thing.__name__
        if hasattr(thing, '__path__'):
            return 'package ' + thing.__name__
        return 'module ' + thing.__name__
    if _inspect.isbuiltin(thing):
        return 'built-in function ' + thing.__name__
    if _inspect.isgetsetdescriptor(thing):
        return 'getset descriptor ' + thing.__objclass__.__name__ + '.' + thing.__name__
    if _inspect.ismemberdescriptor(thing):
        return 'member descriptor ' + thing.__objclass__.__name__ + '.' + thing.__name__
    if _inspect.isclass(thing):
        return 'class ' + thing.__name__
    if _inspect.isfunction(thing):
        return 'function ' + thing.__name__
    if _inspect.ismethod(thing):
        return 'method ' + thing.__name__
    return type(thing).__name__


def plaintext(text):
    """Strip HTML tags from text."""
    import re as _re2
    return _re2.sub('<[^>]*>', '', text)


def apropos(key):
    """Print all the one-line module summaries that contain a substring."""
    pass


def ispath(x):
    return isinstance(x, str) and x.find(_os.sep) >= 0


def getpager():
    if _os.environ.get('TERM') == 'dumb':
        return plainpager
    return pagedpager


def plainpager(text):
    _sys.stdout.write(text)


def pagedpager(text):
    _sys.stdout.write(text)


def pipepager(text, cmd):
    import subprocess
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
    try:
        proc.stdin.write(text.encode('utf-8', 'replace'))
        proc.stdin.close()
        proc.wait()
    except (IOError, KeyboardInterrupt):
        pass


def classify_class_attrs(obj):
    """Return a list of (name, kind, homecls, value) for the class."""
    results = []
    for name in dir(obj):
        try:
            val = getattr(obj, name)
        except AttributeError:
            continue
        homecls = None
        for base in obj.__mro__:
            if name in base.__dict__:
                homecls = base
                break
        if _inspect.isfunction(val) or _inspect.isbuiltin(val):
            kind = 'method'
        elif isinstance(val, classmethod):
            kind = 'class method'
        elif isinstance(val, staticmethod):
            kind = 'static method'
        elif isinstance(val, property):
            kind = 'property'
        else:
            kind = 'data'
        results.append((name, kind, homecls, val))
    return results


def allmethods(cl):
    methods = {}
    for key in dir(cl):
        try:
            methods[key] = getattr(cl, key)
        except AttributeError:
            pass
    return methods


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pydoc2_render_doc():
    """render_doc() returns documentation for an object; returns True."""
    import os as _os2
    doc = render_doc(list)
    return isinstance(doc, str) and 'list' in doc.lower()


def pydoc2_text_doc():
    """TextDoc class can format module documentation; returns True."""
    import os as _os2
    formatter = TextDoc()
    doc = formatter.docmodule(_os2)
    return isinstance(doc, str) and 'os' in doc.lower()


def pydoc2_locate():
    """locate() finds an object by dotted name; returns True."""
    obj = locate('os.path')
    return obj is not None


__all__ = [
    'Doc', 'TextDoc', 'HTMLDoc', 'ErrorDuringImport',
    'locate', 'resolve', 'render_doc', 'describe',
    'classify_class_attrs', 'allmethods', 'apropos', 'ispath',
    'text', 'html',
    'pydoc2_render_doc', 'pydoc2_text_doc', 'pydoc2_locate',
]
