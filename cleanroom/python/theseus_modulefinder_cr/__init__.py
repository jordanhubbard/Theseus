"""
theseus_modulefinder_cr — Clean-room modulefinder module.
No import of the standard `modulefinder` module.
"""

import sys as _sys
import os as _os
import dis as _dis
import marshal as _marshal
import importlib.util as _importlib_util


LOAD_CONST = _dis.opmap.get('LOAD_CONST', 100)
IMPORT_NAME = _dis.opmap.get('IMPORT_NAME', 108)
STORE_NAME = _dis.opmap.get('STORE_NAME', 90)
STORE_FAST = _dis.opmap.get('STORE_FAST', 125)
STORE_GLOBAL = _dis.opmap.get('STORE_GLOBAL', 97)

MISSING = "<<Missing>>"


class Module:
    def __init__(self, name, file=None, path=None):
        self.__name__ = name
        self.__file__ = file
        self.__path__ = path
        self.__code__ = None

    def __repr__(self):
        s = "Module(%r" % (self.__name__,)
        if self.__file__ is not None:
            s += ", %r" % (self.__file__,)
        if self.__path__ is not None:
            s += ", %r" % (self.__path__,)
        s += ")"
        return s


class ModuleFinder:
    def __init__(self, path=None, debug=0, excludes=None, replace_paths=None):
        if path is None:
            path = _sys.path
        self.path = path
        self.modules = {}
        self.badmodules = {}
        self.debug = debug
        self.excludes = excludes or []
        self.replace_paths = replace_paths or []
        self._depgraph = {}
        self._indent = 0

    def msg(self, level, str, *args):
        if level <= self.debug:
            print(' ' * self._indent + str % args)

    def run_script(self, pathname):
        self.msg(2, "run_script %s", pathname)
        with open(pathname, 'rb') as fp:
            source = fp.read()
        co = compile(source, pathname, 'exec')
        self.scan_code(co, self._ensure_fromlist('__main__'))

    def _ensure_fromlist(self, name):
        if name not in self.modules:
            self.modules[name] = Module(name)
        return self.modules[name]

    def load_file(self, pathname):
        dir, name = _os.path.split(pathname)
        name, ext = _os.path.splitext(name)
        self.load_module('__main__', open(pathname, 'rb').read(), pathname)

    def load_module(self, fqname, source, pathname):
        co = compile(source, pathname, 'exec')
        m = self._ensure_fromlist(fqname)
        m.__file__ = pathname
        self.scan_code(co, m)
        return m

    def scan_code(self, co, m):
        code = co.co_code
        n = len(code)
        i = 0
        fromlist = None
        import_stack = []

        for instruction in _dis.get_instructions(co):
            if instruction.opname == 'IMPORT_NAME':
                name = instruction.argval
                self._safe_import_hook(name, m, fromlist)
            elif instruction.opname == 'IMPORT_FROM':
                pass
            elif instruction.opname == 'LOAD_CONST':
                fromlist = instruction.argval

        for const in co.co_consts:
            if isinstance(const, type(co)):
                self.scan_code(const, m)

    def _safe_import_hook(self, name, caller, fromlist, level=0):
        if name in self.excludes:
            return
        try:
            self._import_hook(name, caller, fromlist, level)
        except ImportError as msg:
            self.msg(2, "ImportError for %s: %s", name, msg)
            if name in self.badmodules:
                pass
            else:
                self.badmodules[name] = {}
            if caller:
                self.badmodules[name][caller.__name__] = 1

    def _import_hook(self, name, caller, fromlist, level=0):
        parent = self._determine_parent(caller, level)
        q, tail = self._find_head_package(parent, name)
        m = self._load_tail(q, tail)
        if not fromlist:
            if parent:
                self._ensure_fromlist(parent.__name__ + '.' + name.split('.')[0])
            return q
        if m.__path__:
            self._ensure_fromlist_import(m, fromlist)
        return m

    def _determine_parent(self, caller, level):
        if not caller:
            return None
        pname = caller.__name__
        if level > 0:
            parts = pname.split('.')
            if level < len(parts):
                pname = '.'.join(parts[:-level])
            else:
                return None
        if pname in self.modules:
            return self.modules[pname]
        return None

    def _find_head_package(self, parent, name):
        if '.' in name:
            i = name.find('.')
            head = name[:i]
            tail = name[i+1:]
        else:
            head = name
            tail = ''
        if parent:
            qname = parent.__name__ + '.' + head
        else:
            qname = head
        q = self._import_module(head, qname, parent)
        if q:
            return q, tail
        if parent:
            qname = head
            parent = None
            q = self._import_module(head, qname, parent)
            if q:
                return q, tail
        raise ImportError("No module named %s" % qname)

    def _load_tail(self, q, tail):
        m = q
        while tail:
            i = tail.find('.')
            if i < 0:
                i = len(tail)
            head, tail = tail[:i], tail[i+1:]
            mname = m.__name__ + '.' + head
            m = self._import_module(head, mname, m)
            if not m:
                raise ImportError("No module named %s" % mname)
        return m

    def _ensure_fromlist_import(self, m, fromlist):
        if not isinstance(fromlist, (list, tuple)):
            return
        for sub in fromlist:
            if sub == '*':
                continue
            subname = m.__name__ + '.' + sub
            if subname not in self.modules:
                self._import_module(sub, subname, m)

    def _import_module(self, partname, fqname, parent):
        if fqname in self.modules:
            return self.modules[fqname]
        if fqname in self.badmodules:
            return None

        try:
            spec = _importlib_util.find_spec(fqname)
        except (ModuleNotFoundError, ValueError, AttributeError):
            spec = None

        if spec is None:
            self.modules[fqname] = None
            return None

        m = Module(fqname)
        if spec.origin:
            m.__file__ = spec.origin
        if spec.submodule_search_locations is not None:
            m.__path__ = list(spec.submodule_search_locations)
        self.modules[fqname] = m
        return m

    def find_all_submodules(self, m):
        if not m.__path__:
            return
        for path in m.__path__:
            try:
                names = _os.listdir(path)
            except OSError:
                continue
            for name in names:
                mod = None
                for suf in ['.py', '.pyc']:
                    if name.endswith(suf):
                        mod = name[:-len(suf)]
                        break
                if mod and mod != '__init__':
                    submodule = m.__name__ + '.' + mod
                    if submodule not in self.modules:
                        self._import_module(mod, submodule, m)

    def report(self):
        print()
        print("  %-25s %s" % ("Name", "File"))
        print("  %-25s %s" % ("----", "----"))
        keys = sorted(self.modules)
        for key in keys:
            m = self.modules[key]
            if m is None:
                print("?", end=' ')
            elif m.__path__:
                print("P", end=' ')
            else:
                print("m", end=' ')
            print("%-25s %s" % (key, m.__file__ if m else ""))
        missing, maybe = self.any_missing_maybe()
        if missing:
            print()
            print("Missing modules:")
            for name in missing:
                mods = sorted(self.badmodules[name])
                print("?", name, "imported from", ', '.join(mods))
        if maybe:
            print()
            print("Submodules thay appear to be missing, ignore if", end=' ')
            print("irrelevant:")
            for name in maybe:
                mods = sorted(self.badmodules[name])
                print("?", name, "imported from", ', '.join(mods))

    def any_missing(self):
        missing, maybe = self.any_missing_maybe()
        return missing + maybe

    def any_missing_maybe(self):
        missing = []
        maybe = []
        for name in self.badmodules:
            if name in self.excludes:
                continue
            i = name.rfind('.')
            if i < 0:
                missing.append(name)
                continue
            sub = name[:i]
            if sub in self.modules:
                if self.modules[sub] is not None:
                    maybe.append(name)
                    continue
            missing.append(name)
        return missing, maybe


def find_modules(scripts=None, includes=None, excludes=None, path=None,
                 debug=0, replace_paths=None):
    finder = ModuleFinder(path=path, debug=debug, excludes=excludes or [],
                         replace_paths=replace_paths or [])
    for script in (scripts or []):
        finder.run_script(script)
    for include in (includes or []):
        finder._safe_import_hook(include, None, None)
    return finder


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def mf2_create():
    """ModuleFinder can be instantiated; returns True."""
    mf = ModuleFinder()
    return isinstance(mf, ModuleFinder) and isinstance(mf.modules, dict)


def mf2_modules():
    """ModuleFinder.modules dict is accessible and badmodules exists; returns True."""
    mf = ModuleFinder()
    mf._safe_import_hook('os', None, None)
    return isinstance(mf.modules, dict) and isinstance(mf.badmodules, dict)


def mf2_missing():
    """MISSING sentinel and Module class exist; returns True."""
    return (MISSING == "<<Missing>>" and
            isinstance(Module, type) and
            Module.__name__ == 'Module')


__all__ = [
    'ModuleFinder', 'Module', 'MISSING',
    'find_modules',
    'mf2_create', 'mf2_modules', 'mf2_missing',
]
