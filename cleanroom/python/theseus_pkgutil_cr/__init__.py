from collections import namedtuple
import importlib
import importlib.util
import importlib.machinery
import sys
import os

ModuleInfo = namedtuple('ModuleInfo', ['module_finder', 'name', 'ispkg'])


def resolve_name(name):
    """
    Import and return an object by dotted name string.
    Splits on the last dot to get module + attribute.
    """
    if '.' not in name:
        return importlib.import_module(name)
    
    parts = name.split('.')
    obj = None
    last_exc = None
    
    for i in range(len(parts), 0, -1):
        module_path = '.'.join(parts[:i])
        attr_parts = parts[i:]
        try:
            obj = importlib.import_module(module_path)
            for attr in attr_parts:
                obj = getattr(obj, attr)
            return obj
        except (ImportError, AttributeError) as e:
            last_exc = e
            continue
    
    raise ImportError(f"Cannot resolve name: {name}") from last_exc


def pkgutil_resolve_os():
    return resolve_name('os').__name__


def pkgutil_resolve_attr():
    return callable(resolve_name('os.path.join'))


def pkgutil_module_info():
    return ModuleInfo(None, 'test', False).name


def _pkgutil_module_info_impl(module, module_name):
    """
    Return a ModuleInfo namedtuple for the given module name.
    Contains (module_finder, name, ispkg).
    
    module: a module object or package path list
    module_name: the name of the module to look up
    """
    # Determine search path
    if isinstance(module, str):
        # module is actually the module_name, module_name is something else
        # Try to handle both calling conventions
        search_name = module_name
        try:
            parent = importlib.import_module(module)
            search_path = getattr(parent, '__path__', None)
        except ImportError:
            search_path = None
    elif hasattr(module, '__path__'):
        search_path = module.__path__
        search_name = module_name
    elif isinstance(module, list):
        search_path = module
        search_name = module_name
    else:
        search_path = None
        search_name = module_name

    # Search through sys.meta_path finders
    for finder in sys.meta_path:
        try:
            spec = finder.find_spec(search_name, search_path)
            if spec is not None:
                ispkg = spec.submodule_search_locations is not None
                return ModuleInfo(finder, search_name, ispkg)
        except (AttributeError, TypeError, ValueError):
            continue
    
    # Try using importlib.util.find_spec as fallback
    try:
        spec = importlib.util.find_spec(search_name)
        if spec is not None:
            ispkg = spec.submodule_search_locations is not None
            finder = spec.loader
            return ModuleInfo(finder, search_name, ispkg)
    except (ModuleNotFoundError, ValueError):
        pass
    
    return None


def iter_modules(path=None, prefix=''):
    """
    Yield ModuleInfo(module_finder, name, ispkg) for all submodules on path.
    If path is None, uses sys.path.
    """
    if path is None:
        path = sys.path
    
    yielded = set()
    
    for entry in path:
        try:
            if not isinstance(entry, str) or not os.path.isdir(entry):
                continue
            for item in os.listdir(entry):
                item_path = os.path.join(entry, item)
                name = None
                ispkg = False
                
                if os.path.isdir(item_path):
                    init = os.path.join(item_path, '__init__.py')
                    if os.path.isfile(init):
                        name = item
                        ispkg = True
                elif item.endswith('.py') and item != '__init__.py':
                    name = item[:-3]
                elif item.endswith(('.so', '.pyd')):
                    name = item.split('.')[0]
                
                if name and name not in yielded:
                    yielded.add(name)
                    full_name = prefix + name
                    module_finder = None
                    for f in sys.meta_path:
                        try:
                            spec = f.find_spec(full_name, [entry])
                            if spec is not None:
                                module_finder = f
                                break
                        except (AttributeError, TypeError, ValueError):
                            continue
                    yield ModuleInfo(module_finder, full_name, ispkg)
        except (OSError, PermissionError):
            continue


def get_loader(module_or_name):
    """
    Get a loader object for module_or_name.
    """
    if isinstance(module_or_name, str):
        name = module_or_name
    else:
        name = module_or_name.__name__
    
    try:
        spec = importlib.util.find_spec(name)
        if spec is not None:
            return spec.loader
    except (ModuleNotFoundError, ValueError):
        pass
    
    return None


def find_loader(fullname):
    """
    Find a loader for the given module name.
    """
    return get_loader(fullname)


def get_importer(path_item):
    """
    Retrieve a finder for the given path_item.
    """
    try:
        importer = sys.path_importer_cache[path_item]
    except KeyError:
        for path_hook in sys.path_hooks:
            try:
                importer = path_hook(path_item)
                sys.path_importer_cache[path_item] = importer
                return importer
            except ImportError:
                continue
        sys.path_importer_cache[path_item] = None
        return None
    return importer


def walk_packages(path=None, prefix='', onerror=None):
    """
    Yield ModuleInfo for all modules recursively on path.
    """
    def seen(p, m={}):
        if p in m:
            return True
        m[p] = True
        return False
    
    for info in iter_modules(path, prefix):
        yield info
        if info.ispkg:
            try:
                __import__(info.name)
            except ImportError:
                if onerror is not None:
                    onerror(info.name)
            except Exception:
                if onerror is not None:
                    onerror(info.name)
                else:
                    raise
            else:
                mod = sys.modules[info.name]
                pkg_path = getattr(mod, '__path__', None) or []
                pkg_path = [p for p in pkg_path if not seen(p)]
                yield from walk_packages(pkg_path, info.name + '.', onerror)