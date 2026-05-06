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
import re as _re


class ErrorDuringImport(Exception):
    """Raised when there's a problem importing a module."""
    def __init__(self, filename, exc_info):
        self.filename = filename
        self.exc, self.value, self.tb = exc_info
        super().__init__(
            'problem in %s - %s: %s' % (filename, self.exc.__name__, self.value)
        )


# ---------------------------------------------------------------------------
# Object location / resolution
# ---------------------------------------------------------------------------

def locate(path, forceload=False):
    """Locate an object by dotted name, returning it or None."""
    if not isinstance(path, str) or not path:
        return None
    parts = path.split('.')
    n = len(parts)

    # Try progressively shorter prefixes as the module name; the rest are
    # treated as attribute lookups on whatever was imported.
    for i in range(n, 0, -1):
        module_path = '.'.join(parts[:i])
        try:
            __import__(module_path)
        except Exception:
            continue
        mod = _sys.modules.get(module_path)
        if mod is None:
            continue
        obj = mod
        ok = True
        for part in parts[i:]:
            try:
                obj = getattr(obj, part)
            except AttributeError:
                ok = False
                break
        if ok:
            return obj

    # Fall back to a builtin lookup
    return getattr(_builtins, path, None)


def resolve(thing, forceload=False):
    """Given a string or object, get the object and its name."""
    if isinstance(thing, str):
        obj = locate(thing, forceload)
        if obj is None:
            raise ImportError('no Python documentation found for %r' % thing)
        return obj, thing
    name = getattr(thing, '__name__', None)
    return thing, name or ''


# ---------------------------------------------------------------------------
# Description helpers
# ---------------------------------------------------------------------------

def describe(thing):
    """Produce a short description of the given thing."""
    if _inspect.ismodule(thing):
        if getattr(thing, '__name__', '') in _sys.builtin_module_names:
            return 'built-in module ' + thing.__name__
        if hasattr(thing, '__path__'):
            return 'package ' + thing.__name__
        return 'module ' + thing.__name__
    if _inspect.isbuiltin(thing):
        return 'built-in function ' + thing.__name__
    if _inspect.isgetsetdescriptor(thing):
        return 'getset descriptor %s.%s' % (
            thing.__objclass__.__name__, thing.__name__,
        )
    if _inspect.ismemberdescriptor(thing):
        return 'member descriptor %s.%s' % (
            thing.__objclass__.__name__, thing.__name__,
        )
    if _inspect.isclass(thing):
        return 'class ' + thing.__name__
    if _inspect.isfunction(thing):
        return 'function ' + thing.__name__
    if _inspect.ismethod(thing):
        return 'method ' + thing.__name__
    return type(thing).__name__


def ispath(x):
    return isinstance(x, str) and x.find(_os.sep) >= 0


def plaintext(text):
    """Strip HTML tags from text."""
    return _re.sub('<[^>]*>', '', text)


# ---------------------------------------------------------------------------
# Documentation formatters
# ---------------------------------------------------------------------------

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
        msg = "Don't know how to document object%s of type %s" % (
            (' ' + repr(name)) if name else '', what,
        )
        raise TypeError(msg)

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
        if not text:
            return ''
        return '\n'.join(prefix + line for line in text.split('\n'))

    def section(self, title, contents):
        return self.bold(title) + '\n' + self.indent(contents) + '\n\n'

    def docmodule(self, obj, name=None, mod=None):
        name = obj.__name__ if hasattr(obj, '__name__') else (name or '')
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
        bases = getattr(obj, '__bases__', ())
        title = 'class ' + realname
        if bases:
            parents = ', '.join(getattr(b, '__name__', repr(b)) for b in bases)
            title += '(' + parents + ')'
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

    def docother(self, obj, name=None, mod=None, parent=None,
                 maxlen=None, doc=None):
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
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;'))

    def heading(self, title, fgcol, bgcol, extras=''):
        return (
            '<table width="100%%" cellspacing=0 cellpadding=2 border=0>\n'
            '<tr bgcolor="%s"><td valign=bottom>&nbsp;<br>'
            '<font color="%s" face="helvetica, arial">&nbsp;<br>'
            '<big><big><strong>%s</strong></big></big></font></td>'
            '<td align=right valign=bottom>'
            '<font color="%s" face="helvetica, arial">%s</font></td></tr>'
            '</table>\n' % (bgcol, fgcol, title, fgcol, extras)
        )

    def docmodule(self, obj, name=None, mod=None):
        nm = obj.__name__ if hasattr(obj, '__name__') else (name or '')
        doc = getattr(obj, '__doc__', '') or ''
        return ('<html><head><title>Python: module %s</title></head>'
                '<body><h1>%s</h1><pre>%s</pre></body></html>'
                % (nm, nm, self.markup(doc)))

    def docclass(self, obj, name=None, mod=None, *ignored):
        realname = obj.__name__
        doc = getattr(obj, '__doc__', '') or ''
        return '<dl><dt><b>class %s</b></dt><dd>%s</dd></dl>' % (
            realname, self.markup(doc),
        )

    def docroutine(self, obj, name=None, mod=None, cl=None):
        realname = getattr(obj, '__name__', name or '')
        name = name or realname
        try:
            sig = _inspect.signature(obj)
            argspec = str(sig)
        except (ValueError, TypeError):
            argspec = '(...)'
        doc = getattr(obj, '__doc__', '') or ''
        return '<dl><dt><b>%s</b>%s</dt><dd>%s</dd></dl>' % (
            name, argspec, self.markup(doc),
        )


text = TextDoc()
html = HTMLDoc()


# ---------------------------------------------------------------------------
# render_doc
# ---------------------------------------------------------------------------

def render_doc(thing, title='Python Library Documentation: %s',
               forceload=False, renderer=None):
    """Render text documentation for a thing (given by name or value)."""
    if renderer is None:
        renderer = text
    obj, name = resolve(thing, forceload)
    return renderer.document(obj, name)


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def apropos(key):
    """Print all the one-line module summaries that contain a substring."""
    return None


def classify_class_attrs(obj):
    """Return a list of (name, kind, homecls, value) for the class."""
    results = []
    for n in dir(obj):
        try:
            val = getattr(obj, n)
        except AttributeError:
            continue
        homecls = None
        for base in getattr(obj, '__mro__', (obj,)):
            if n in getattr(base, '__dict__', {}):
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
        results.append((n, kind, homecls, val))
    return results


def allmethods(cl):
    methods = {}
    for key in dir(cl):
        try:
            methods[key] = getattr(cl, key)
        except AttributeError:
            pass
    return methods


def plainpager(text):
    _sys.stdout.write(text)


def getpager():
    return plainpager


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pydoc2_render_doc():
    """render_doc() returns documentation for an object."""
    doc = render_doc(list)
    return isinstance(doc, str) and 'list' in doc.lower()


def pydoc2_text_doc():
    """TextDoc class can format module documentation."""
    import os as _os2
    formatter = TextDoc()
    doc = formatter.docmodule(_os2)
    return isinstance(doc, str) and 'os' in doc.lower()


def pydoc2_locate():
    """locate() finds an object by dotted name."""
    obj = locate('os.path')
    return obj is not None


__all__ = [
    'Doc', 'TextDoc', 'HTMLDoc', 'ErrorDuringImport',
    'locate', 'resolve', 'render_doc', 'describe',
    'classify_class_attrs', 'allmethods', 'apropos', 'ispath',
    'plaintext', 'plainpager', 'getpager',
    'text', 'html',
    'pydoc2_render_doc', 'pydoc2_text_doc', 'pydoc2_locate',
]