"""Clean-room reimplementation of pyclbr.

Provides Class and Function descriptors and a readmodule() that parses
Python source to extract top-level (and nested) class and function
definitions. No use of the original pyclbr.
"""

import os
import sys
import io
import tokenize


__all__ = [
    "Class",
    "Function",
    "readmodule",
    "readmodule_ex",
    "pyclbr2_class",
    "pyclbr2_function",
    "pyclbr2_readmodule",
]


class _Object(object):
    """Base descriptor: file/module/name/lineno/parent/children."""

    def __init__(self, module, name, file, lineno, parent=None):
        self.module = module
        self.name = name
        self.file = file
        self.lineno = lineno
        self.parent = parent
        self.children = {}
        if parent is not None:
            parent.children[name] = self


class Function(_Object):
    """Represents a function (or method) definition."""

    def __init__(self, module, name, file, lineno, parent=None, is_async=False):
        _Object.__init__(self, module, name, file, lineno, parent)
        self.is_async = is_async


class Class(_Object):
    """Represents a class definition."""

    def __init__(self, module, name, super_, file, lineno, parent=None):
        _Object.__init__(self, module, name, file, lineno, parent)
        # super_ is a list of names or Class objects (best-effort)
        self.super = list(super_) if super_ else []
        self.methods = {}


# ---------------------------------------------------------------------------
# Module locator
# ---------------------------------------------------------------------------

def _find_module(name, path=None):
    """Locate the source file for a (possibly dotted) module name.

    Returns (file_path, is_package).  Raises ImportError if not found.
    """
    parts = name.split(".")
    search = path

    # Walk dotted components.
    final_path = None
    is_pkg = False
    for i, part in enumerate(parts):
        last = (i == len(parts) - 1)
        found = None
        pkg = False
        candidates = search if search is not None else sys.path
        for entry in candidates:
            if entry == "":
                entry = os.getcwd()
            try:
                pkg_init = os.path.join(entry, part, "__init__.py")
                if os.path.isfile(pkg_init):
                    found = pkg_init
                    pkg = True
                    break
                py_file = os.path.join(entry, part + ".py")
                if os.path.isfile(py_file):
                    found = py_file
                    pkg = False
                    break
            except (OSError, TypeError):
                continue
        if found is None:
            raise ImportError("Cannot find module %r" % name)
        if last:
            final_path = found
            is_pkg = pkg
        else:
            if not pkg:
                raise ImportError(
                    "Module %r is not a package" % ".".join(parts[: i + 1])
                )
            search = [os.path.dirname(found)]
    return final_path, is_pkg


# ---------------------------------------------------------------------------
# Source parser using tokenize (no compile()/ast)
# ---------------------------------------------------------------------------

def _tokenize_file(path):
    """Yield tokens from the file, robust to encoding."""
    with open(path, "rb") as f:
        data = f.read()
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(data).readline))
    except tokenize.TokenizeError:
        # Fall back to whatever we got.
        tokens = []
    return tokens


def _collect_dotted_name(tokens, i):
    """Starting at tokens[i] which is a NAME, consume NAME ('.' NAME)*.

    Returns (name_string, new_index_after_name).
    """
    parts = [tokens[i].string]
    j = i + 1
    while (
        j + 1 < len(tokens)
        and tokens[j].type == tokenize.OP
        and tokens[j].string == "."
        and tokens[j + 1].type == tokenize.NAME
    ):
        parts.append(tokens[j + 1].string)
        j += 2
    return ".".join(parts), j


def _parse_bases(tokens, i):
    """Given tokens[i] is '(' just after a class name, parse a flat list of
    base-class name strings until the matching ')'.

    Returns (bases_list, index_after_close_paren).
    """
    assert tokens[i].type == tokenize.OP and tokens[i].string == "("
    depth = 1
    j = i + 1
    bases = []
    current_tokens = []

    def flush():
        # Reconstruct a base expression from collected tokens.
        text_parts = []
        for t in current_tokens:
            text_parts.append(t.string)
        text = "".join(text_parts).strip()
        # Skip keyword arguments like metaclass=Foo
        if "=" in text and not text.startswith("="):
            return
        if text:
            bases.append(text)

    while j < len(tokens) and depth > 0:
        tok = tokens[j]
        if tok.type == tokenize.OP and tok.string == "(":
            depth += 1
            current_tokens.append(tok)
        elif tok.type == tokenize.OP and tok.string == ")":
            depth -= 1
            if depth == 0:
                flush()
                j += 1
                break
            current_tokens.append(tok)
        elif tok.type == tokenize.OP and tok.string == "," and depth == 1:
            flush()
            current_tokens = []
        elif tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT):
            pass
        else:
            current_tokens.append(tok)
        j += 1
    return bases, j


def _parse_module_source(module_name, path):
    """Parse source file and return ordered dict {name: Class|Function}.

    Includes top-level definitions and (for classes) nested children.
    """
    tokens = _tokenize_file(path)
    if not tokens:
        return {}

    # Stack of (indent_col, container) where container is a Class
    # (for tracking nested members) or None for module level.
    # We track the column of the def/class keyword; anything indented
    # deeper belongs to that container.
    result = {}
    # stack entries: dict with keys 'col' (indent column of the body) and
    # 'class' (Class instance or None for module level).
    stack = [{"col": -1, "class": None}]

    i = 0
    n = len(tokens)
    at_line_start = True
    line_indent = 0

    while i < n:
        tok = tokens[i]
        ttype = tok.type
        tstring = tok.string

        if ttype == tokenize.INDENT:
            line_indent = len(tstring.expandtabs())
            i += 1
            continue
        if ttype == tokenize.DEDENT:
            i += 1
            continue
        if ttype in (tokenize.NEWLINE, tokenize.NL):
            at_line_start = True
            i += 1
            continue
        if ttype == tokenize.COMMENT:
            i += 1
            continue
        if ttype == tokenize.ENCODING:
            i += 1
            continue

        # Determine column for this token (use start col on its line).
        col = tok.start[1]
        lineno = tok.start[0]

        # Pop stack entries whose column is >= current column (we've exited).
        while len(stack) > 1 and col <= stack[-1]["col"]:
            stack.pop()

        parent_class = stack[-1]["class"]

        is_async_def = False
        # Detect 'async def'
        if (
            ttype == tokenize.NAME
            and tstring == "async"
            and i + 1 < n
            and tokens[i + 1].type == tokenize.NAME
            and tokens[i + 1].string == "def"
        ):
            is_async_def = True
            i += 1
            tok = tokens[i]
            ttype = tok.type
            tstring = tok.string

        if ttype == tokenize.NAME and tstring == "def":
            # Expect NAME after def
            j = i + 1
            # Skip whitespace tokens (shouldn't really occur in tokenize stream)
            while j < n and tokens[j].type in (tokenize.NL,):
                j += 1
            if j < n and tokens[j].type == tokenize.NAME:
                func_name = tokens[j].string
                func = Function(
                    module_name, func_name, path, lineno,
                    parent=parent_class, is_async=is_async_def,
                )
                if parent_class is None:
                    if func_name not in result:
                        result[func_name] = func
                else:
                    # Track as a method too.
                    parent_class.methods[func_name] = lineno
                # Push a frame so we know its body indent (one beyond col).
                stack.append({"col": col, "class": None})
                i = j + 1
                continue

        if ttype == tokenize.NAME and tstring == "class":
            j = i + 1
            if j < n and tokens[j].type == tokenize.NAME:
                cls_name = tokens[j].string
                k = j + 1
                bases = []
                if k < n and tokens[k].type == tokenize.OP and tokens[k].string == "(":
                    bases, k = _parse_bases(tokens, k)
                # Resolve simple base names against already-seen classes for
                # parity with the original API (best-effort).
                resolved = []
                for b in bases:
                    if b in result and isinstance(result[b], Class):
                        resolved.append(result[b])
                    else:
                        resolved.append(b)
                cls = Class(module_name, cls_name, resolved, path, lineno,
                            parent=parent_class)
                if parent_class is None:
                    if cls_name not in result:
                        result[cls_name] = cls
                stack.append({"col": col, "class": cls})
                i = k
                continue

        i += 1

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def readmodule(module, path=None):
    """Read a module and return a dict of {classname: Class}.

    Functions are excluded (matches stdlib pyclbr.readmodule).
    """
    full = readmodule_ex(module, path)
    classes = {}
    for name, obj in full.items():
        if isinstance(obj, Class):
            classes[name] = obj
    return classes


def readmodule_ex(module, path=None):
    """Read a module and return {name: Class|Function} for top-level defs."""
    file_path, _is_pkg = _find_module(module, path)
    return _parse_module_source(module, file_path)


# ---------------------------------------------------------------------------
# Invariant smoke-test helpers
# ---------------------------------------------------------------------------

def pyclbr2_class():
    """Verify that Class objects are constructed with expected attributes."""
    c = Class("m", "Foo", ["Bar"], "m.py", 10)
    if not isinstance(c, Class):
        return False
    if c.module != "m" or c.name != "Foo" or c.file != "m.py":
        return False
    if c.lineno != 10 or c.super != ["Bar"]:
        return False
    if c.methods != {} or c.children != {} or c.parent is not None:
        return False
    # Nested class registers itself as a child.
    inner = Class("m", "Inner", [], "m.py", 12, parent=c)
    if c.children.get("Inner") is not inner:
        return False
    return True


def pyclbr2_function():
    """Verify that Function objects are constructed with expected attributes."""
    f = Function("m", "do", "m.py", 5)
    if not isinstance(f, Function):
        return False
    if f.module != "m" or f.name != "do" or f.file != "m.py":
        return False
    if f.lineno != 5 or f.is_async or f.parent is not None:
        return False
    g = Function("m", "wait", "m.py", 8, is_async=True)
    if not g.is_async:
        return False
    return True


def pyclbr2_readmodule():
    """Round-trip: write a tiny module, parse it, check classes/funcs."""
    import tempfile
    src = (
        "class Alpha:\n"
        "    def one(self):\n"
        "        pass\n"
        "    def two(self):\n"
        "        pass\n"
        "\n"
        "class Beta(Alpha):\n"
        "    def three(self):\n"
        "        pass\n"
        "\n"
        "def helper():\n"
        "    return 1\n"
        "\n"
        "async def go():\n"
        "    return 2\n"
    )
    tmpdir = tempfile.mkdtemp(prefix="pyclbr2_")
    modname = "tinymod_for_pyclbr2"
    fpath = os.path.join(tmpdir, modname + ".py")
    try:
        with open(fpath, "w") as fh:
            fh.write(src)
        classes = readmodule(modname, [tmpdir])
        if "Alpha" not in classes or "Beta" not in classes:
            return False
        if not isinstance(classes["Alpha"], Class):
            return False
        # helper is a function so should be excluded from readmodule.
        if "helper" in classes:
            return False
        # Methods captured.
        alpha = classes["Alpha"]
        if "one" not in alpha.methods or "two" not in alpha.methods:
            return False
        # Beta should resolve Alpha as a Class object base.
        beta = classes["Beta"]
        if not beta.super:
            return False
        if not (beta.super[0] is alpha or beta.super[0] == "Alpha"):
            return False
        # readmodule_ex includes the functions.
        full = readmodule_ex(modname, [tmpdir])
        if "helper" not in full or not isinstance(full["helper"], Function):
            return False
        if "go" not in full or not full["go"].is_async:
            return False
        # Line numbers are 1-based and reasonable.
        if alpha.lineno < 1 or full["helper"].lineno < 1:
            return False
    finally:
        try:
            os.remove(fpath)
        except OSError:
            pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
    return True