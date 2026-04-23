import sys
import types


def getmembers(obj, predicate=None):
    """Return list of (name, value) pairs for obj attributes."""
    results = []
    
    # Get names from dir()
    try:
        names = dir(obj)
    except Exception:
        names = []
    
    for name in names:
        try:
            value = getattr(obj, name)
        except AttributeError:
            continue
        except Exception:
            continue
        
        if predicate is None or predicate(value):
            results.append((name, value))
    
    return results


def isbuiltin(obj):
    """Return True if obj is a built-in function or bound method."""
    return isinstance(obj, (types.BuiltinFunctionType, types.BuiltinMethodType))


def ismodule(obj):
    """Return True if obj is a module."""
    return isinstance(obj, types.ModuleType)


# Invariant functions

def inspect2_getmembers_count():
    """len([m for m in getmembers(int) if not m[0].startswith('_')]) > 0"""
    members = getmembers(int)
    count = len([m for m in members if not m[0].startswith('_')])
    return count > 0


def inspect2_isbuiltin():
    """isbuiltin(len) == True"""
    return isbuiltin(len) == True


def inspect2_ismodule():
    """import os; ismodule(os) == True"""
    import os
    return ismodule(os) == True