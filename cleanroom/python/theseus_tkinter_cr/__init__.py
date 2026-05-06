"""Clean-room tkinter stub package (theseus_tkinter_cr).

This module provides a minimal, self-contained reimplementation of a small
subset of tkinter's surface area sufficient to satisfy the behavioral
invariants. It does NOT import tkinter or any third-party library.
"""

# ---------------------------------------------------------------------------
# Tk-style constants
# ---------------------------------------------------------------------------

# Geometry/anchor constants
N = "n"
S = "s"
E = "e"
W = "w"
NE = "ne"
NW = "nw"
SE = "se"
SW = "sw"
NS = "ns"
EW = "ew"
NSEW = "nsew"
CENTER = "center"

# Side/fill/orient
TOP = "top"
BOTTOM = "bottom"
LEFT = "left"
RIGHT = "right"
NONE = "none"
X = "x"
Y = "y"
BOTH = "both"
HORIZONTAL = "horizontal"
VERTICAL = "vertical"

# Relief
FLAT = "flat"
RAISED = "raised"
SUNKEN = "sunken"
GROOVE = "groove"
RIDGE = "ridge"
SOLID = "solid"

# State
NORMAL = "normal"
DISABLED = "disabled"
ACTIVE = "active"
HIDDEN = "hidden"

# Boolean-ish
TRUE = True
FALSE = False
YES = "yes"
NO = "no"
ON = "on"
OFF = "off"

# Cursor / selection / wrap
WORD = "word"
CHAR = "char"
NUMERIC = "numeric"
INSERT = "insert"
END = "end"
ANCHOR = "anchor"
SEL = "sel"
SEL_FIRST = "sel.first"
SEL_LAST = "sel.last"

# Other commonly-used
ALL = "all"
CURRENT = "current"
FIRST = "first"
LAST = "last"
BROWSE = "browse"
SINGLE = "single"
MULTIPLE = "multiple"
EXTENDED = "extended"
UNITS = "units"
PAGES = "pages"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_default_root = None


def _gen_name(prefix="widget"):
    _gen_name.counter += 1
    return "{0}{1}".format(prefix, _gen_name.counter)


_gen_name.counter = 0


# ---------------------------------------------------------------------------
# Variables (StringVar, IntVar, DoubleVar, BooleanVar)
# ---------------------------------------------------------------------------


class Variable(object):
    """Base class for value holders for widget options."""

    _default = None

    def __init__(self, master=None, value=None, name=None):
        self._master = master
        self._name = name or _gen_name("PY_VAR")
        self._traces = []  # list of (mode, callback)
        if value is not None:
            self._value = value
        else:
            self._value = self._default

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        # Fire write traces.
        for mode, cb in list(self._traces):
            if mode in ("w", "write"):
                try:
                    cb(self._name, "", "w")
                except TypeError:
                    try:
                        cb()
                    except Exception:
                        pass
                except Exception:
                    pass

    # Some tkinter code uses `initialize` as an alias of set.
    initialize = set

    def trace_add(self, mode, callback):
        self._traces.append((mode, callback))
        return (mode, callback)

    def trace_remove(self, mode, cbname):
        try:
            self._traces.remove((mode, cbname))
        except ValueError:
            pass

    def trace_info(self):
        return list(self._traces)

    # Legacy aliases
    def trace(self, mode, callback):
        return self.trace_add(mode, callback)

    trace_variable = trace

    def __str__(self):
        return self._name


class StringVar(Variable):
    _default = ""

    def get(self):
        v = self._value
        if v is None:
            return ""
        return str(v)


class IntVar(Variable):
    _default = 0

    def get(self):
        v = self._value
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0


class DoubleVar(Variable):
    _default = 0.0

    def get(self):
        v = self._value
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class BooleanVar(Variable):
    _default = False

    def get(self):
        v = self._value
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        try:
            return bool(int(v))
        except (TypeError, ValueError):
            return bool(v)


# ---------------------------------------------------------------------------
# Event / geometry-manager support objects
# ---------------------------------------------------------------------------


class Event(object):
    """A simple event object."""

    def __init__(self, **kwargs):
        self.type = kwargs.get("type", None)
        self.widget = kwargs.get("widget", None)
        self.x = kwargs.get("x", 0)
        self.y = kwargs.get("y", 0)
        self.x_root = kwargs.get("x_root", 0)
        self.y_root = kwargs.get("y_root", 0)
        self.char = kwargs.get("char", "")
        self.keysym = kwargs.get("keysym", "")
        self.keycode = kwargs.get("keycode", 0)
        self.num = kwargs.get("num", 0)
        self.state = kwargs.get("state", 0)
        self.time = kwargs.get("time", 0)
        self.width = kwargs.get("width", 0)
        self.height = kwargs.get("height", 0)


# ---------------------------------------------------------------------------
# Widget hierarchy
# ---------------------------------------------------------------------------


class Misc(object):
    """Internal mixin: mimics tkinter.Misc for option/config support."""

    def __init__(self):
        self._options = {}
        self._bindings = {}
        self._children = {}
        self._name = _gen_name("widget")

    # Configuration
    def configure(self, cnf=None, **kw):
        if cnf is None and not kw:
            return dict(self._options)
        if isinstance(cnf, dict):
            self._options.update(cnf)
        self._options.update(kw)
        return None

    config = configure

    def cget(self, key):
        return self._options.get(key)

    def __setitem__(self, key, value):
        self._options[key] = value

    def __getitem__(self, key):
        return self._options[key]

    def keys(self):
        return list(self._options.keys())

    # Binding
    def bind(self, sequence=None, func=None, add=None):
        if sequence is None:
            return list(self._bindings.keys())
        if func is None:
            return self._bindings.get(sequence)
        if add and sequence in self._bindings:
            existing = self._bindings[sequence]
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(func)
            self._bindings[sequence] = existing
        else:
            self._bindings[sequence] = func
        return func

    def unbind(self, sequence, funcid=None):
        self._bindings.pop(sequence, None)

    def bind_all(self, sequence=None, func=None, add=None):
        return self.bind(sequence, func, add)

    def event_generate(self, sequence, **kw):
        cb = self._bindings.get(sequence)
        if cb is None:
            return
        ev = Event(widget=self, **kw)
        if isinstance(cb, list):
            for c in cb:
                c(ev)
        else:
            cb(ev)

    # Lifecycle
    def destroy(self):
        for child in list(self._children.values()):
            try:
                child.destroy()
            except Exception:
                pass
        self._children.clear()
        self._options.clear()
        self._bindings.clear()

    # Geometry helpers
    def winfo_name(self):
        return self._name

    def winfo_children(self):
        return list(self._children.values())

    def winfo_exists(self):
        return 1

    def winfo_class(self):
        return type(self).__name__

    # Stubs for the main loop / update
    def update(self):
        pass

    def update_idletasks(self):
        pass

    def after(self, ms, func=None, *args):
        if func is not None:
            try:
                func(*args)
            except Exception:
                pass
        return "after#0"

    def after_idle(self, func, *args):
        try:
            func(*args)
        except Exception:
            pass
        return "after#0"

    def after_cancel(self, id):
        pass


class Pack(object):
    def pack(self, cnf=None, **kw):
        opts = {}
        if isinstance(cnf, dict):
            opts.update(cnf)
        opts.update(kw)
        self._pack_info = opts
        return None

    def pack_forget(self):
        if hasattr(self, "_pack_info"):
            self._pack_info = {}

    def pack_info(self):
        return getattr(self, "_pack_info", {})

    forget = pack_forget


class Place(object):
    def place(self, cnf=None, **kw):
        opts = {}
        if isinstance(cnf, dict):
            opts.update(cnf)
        opts.update(kw)
        self._place_info = opts
        return None

    def place_forget(self):
        if hasattr(self, "_place_info"):
            self._place_info = {}

    def place_info(self):
        return getattr(self, "_place_info", {})


class Grid(object):
    def grid(self, cnf=None, **kw):
        opts = {}
        if isinstance(cnf, dict):
            opts.update(cnf)
        opts.update(kw)
        self._grid_info = opts
        return None

    def grid_forget(self):
        if hasattr(self, "_grid_info"):
            self._grid_info = {}

    def grid_info(self):
        return getattr(self, "_grid_info", {})

    def grid_remove(self):
        self.grid_forget()

    def grid_configure(self, cnf=None, **kw):
        return self.grid(cnf, **kw)


class BaseWidget(Misc, Pack, Place, Grid):
    def __init__(self, master=None, cnf=None, **kw):
        Misc.__init__(self)
        self.master = master
        self.tk = None  # placeholder; this stub has no Tcl interpreter
        opts = {}
        if isinstance(cnf, dict):
            opts.update(cnf)
        opts.update(kw)
        self._options = opts
        if master is not None and hasattr(master, "_children"):
            master._children[self._name] = self


class Widget(BaseWidget):
    pass


class Tk(Misc, Pack, Place, Grid):
    """Toplevel application root."""

    def __init__(self, screenName=None, baseName=None, className="Tk",
                 useTk=1, sync=0, use=None):
        Misc.__init__(self)
        self.master = None
        self.tk = None
        self._title = className
        self._geometry = ""
        global _default_root
        if _default_root is None:
            _default_root = self

    def title(self, value=None):
        if value is None:
            return self._title
        self._title = value

    def geometry(self, value=None):
        if value is None:
            return self._geometry
        self._geometry = value

    def mainloop(self, n=0):
        # No event loop in this stub.
        return None

    def quit(self):
        return None

    def destroy(self):
        global _default_root
        Misc.destroy(self)
        if _default_root is self:
            _default_root = None


class Toplevel(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._title = ""

    def title(self, value=None):
        if value is None:
            return self._title
        self._title = value


class Frame(BaseWidget):
    pass


class LabelFrame(Frame):
    pass


class Label(BaseWidget):
    pass


class Button(BaseWidget):
    def invoke(self):
        cmd = self._options.get("command")
        if callable(cmd):
            return cmd()
        return None


class Entry(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._text = ""

    def get(self):
        return self._text

    def insert(self, index, string):
        # Very simple: append regardless of index.
        if index == 0 or index == "0":
            self._text = string + self._text
        else:
            self._text = self._text + string

    def delete(self, first, last=None):
        if first == 0 and (last is None or last == END):
            self._text = ""


class Text(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._content = ""

    def get(self, index1, index2=None):
        return self._content

    def insert(self, index, chars, *tags):
        self._content += chars

    def delete(self, index1, index2=None):
        self._content = ""


class Checkbutton(BaseWidget):
    def invoke(self):
        cmd = self._options.get("command")
        if callable(cmd):
            return cmd()


class Radiobutton(BaseWidget):
    def invoke(self):
        cmd = self._options.get("command")
        if callable(cmd):
            return cmd()


class Listbox(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._items = []

    def insert(self, index, *elements):
        if index == END or index == "end":
            self._items.extend(elements)
        else:
            try:
                idx = int(index)
                for i, el in enumerate(elements):
                    self._items.insert(idx + i, el)
            except (TypeError, ValueError):
                self._items.extend(elements)

    def delete(self, first, last=None):
        if first == 0 and (last is None or last == END):
            self._items = []
        else:
            try:
                idx = int(first)
                if last is None:
                    del self._items[idx]
                else:
                    if last == END:
                        del self._items[idx:]
                    else:
                        del self._items[idx:int(last) + 1]
            except (TypeError, ValueError):
                pass

    def size(self):
        return len(self._items)

    def get(self, first, last=None):
        if last is None:
            try:
                return self._items[int(first)]
            except (IndexError, ValueError):
                return ""
        if last == END:
            return tuple(self._items[int(first):])
        return tuple(self._items[int(first):int(last) + 1])

    def curselection(self):
        return ()


class Menu(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._entries = []

    def add(self, itemType, cnf=None, **kw):
        opts = {"type": itemType}
        if isinstance(cnf, dict):
            opts.update(cnf)
        opts.update(kw)
        self._entries.append(opts)

    def add_command(self, cnf=None, **kw):
        self.add("command", cnf, **kw)

    def add_cascade(self, cnf=None, **kw):
        self.add("cascade", cnf, **kw)

    def add_separator(self, cnf=None, **kw):
        self.add("separator", cnf, **kw)

    def add_checkbutton(self, cnf=None, **kw):
        self.add("checkbutton", cnf, **kw)

    def add_radiobutton(self, cnf=None, **kw):
        self.add("radiobutton", cnf, **kw)


class Canvas(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._items = {}
        self._next_id = 0

    def _new_item(self, kind, coords, opts):
        self._next_id += 1
        self._items[self._next_id] = {
            "type": kind,
            "coords": list(coords),
            "options": dict(opts),
        }
        return self._next_id

    def create_line(self, *coords, **kw):
        return self._new_item("line", coords, kw)

    def create_rectangle(self, *coords, **kw):
        return self._new_item("rectangle", coords, kw)

    def create_oval(self, *coords, **kw):
        return self._new_item("oval", coords, kw)

    def create_text(self, *coords, **kw):
        return self._new_item("text", coords, kw)

    def create_polygon(self, *coords, **kw):
        return self._new_item("polygon", coords, kw)

    def delete(self, *args):
        if not args or args[0] == ALL or args[0] == "all":
            self._items.clear()
            return
        for a in args:
            self._items.pop(a, None)

    def coords(self, item, *new):
        if item not in self._items:
            return []
        if new:
            self._items[item]["coords"] = list(new)
        return self._items[item]["coords"]


class Scrollbar(BaseWidget):
    pass


class Scale(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._value = kw.get("from_", 0)

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class Spinbox(BaseWidget):
    def __init__(self, master=None, cnf=None, **kw):
        BaseWidget.__init__(self, master, cnf, **kw)
        self._value = ""

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class PanedWindow(BaseWidget):
    pass


class OptionMenu(BaseWidget):
    def __init__(self, master, variable, value, *values, **kw):
        BaseWidget.__init__(self, master, **kw)
        self._variable = variable
        self._values = (value,) + values
        if variable is not None:
            try:
                variable.set(value)
            except Exception:
                pass


class Message(BaseWidget):
    pass


# ---------------------------------------------------------------------------
# Invariant-required predicate functions
# ---------------------------------------------------------------------------


def tkinter2_variables():
    """All the canonical variable holders exist and behave correctly."""
    try:
        s = StringVar()
        if s.get() != "":
            return False
        s.set("hello")
        if s.get() != "hello":
            return False

        i = IntVar()
        if i.get() != 0:
            return False
        i.set(7)
        if i.get() != 7:
            return False

        d = DoubleVar()
        if d.get() != 0.0:
            return False
        d.set(2.5)
        if abs(d.get() - 2.5) > 1e-9:
            return False

        b = BooleanVar()
        if b.get() is not False:
            return False
        b.set(True)
        if b.get() is not True:
            return False

        # Initial values via constructor.
        s2 = StringVar(value="x")
        if s2.get() != "x":
            return False
        i2 = IntVar(value=42)
        if i2.get() != 42:
            return False

        # Trace mechanism fires.
        bucket = []

        def cb(*args):
            bucket.append(1)

        s.trace_add("write", cb)
        s.set("again")
        if not bucket:
            return False

        # All inherit from Variable.
        for cls in (StringVar, IntVar, DoubleVar, BooleanVar):
            if not issubclass(cls, Variable):
                return False
        return True
    except Exception:
        return False


def tkinter2_constants():
    """The expected tkinter constants are present and have sensible values."""
    expected = [
        "N", "S", "E", "W", "NE", "NW", "SE", "SW", "NS", "EW", "NSEW",
        "CENTER", "TOP", "BOTTOM", "LEFT", "RIGHT", "X", "Y", "BOTH", "NONE",
        "HORIZONTAL", "VERTICAL",
        "FLAT", "RAISED", "SUNKEN", "GROOVE", "RIDGE", "SOLID",
        "NORMAL", "DISABLED", "ACTIVE", "HIDDEN",
        "TRUE", "FALSE", "YES", "NO",
        "WORD", "CHAR", "INSERT", "END", "ANCHOR", "SEL", "ALL",
        "BROWSE", "SINGLE", "MULTIPLE", "EXTENDED",
    ]
    g = globals()
    for name in expected:
        if name not in g:
            return False
        if g[name] is None:
            return False
    # Spot check a couple of canonical values.
    if N != "n" or S != "s" or E != "e" or W != "w":
        return False
    if HORIZONTAL != "horizontal" or VERTICAL != "vertical":
        return False
    if END != "end" or INSERT != "insert":
        return False
    if TRUE is not True or FALSE is not False:
        return False
    return True


def tkinter2_classes():
    """The expected widget/structural classes exist and instantiate."""
    expected = [
        "Tk", "Toplevel", "Frame", "LabelFrame",
        "Label", "Button", "Entry", "Text",
        "Checkbutton", "Radiobutton", "Listbox",
        "Menu", "Canvas", "Scrollbar", "Scale",
        "Spinbox", "PanedWindow", "OptionMenu", "Message",
        "Variable", "StringVar", "IntVar", "DoubleVar", "BooleanVar",
        "Widget", "Misc", "Event",
    ]
    g = globals()
    for name in expected:
        if name not in g:
            return False
        if not isinstance(g[name], type):
            return False
    try:
        root = Tk()
        f = Frame(root)
        Label(f, text="hi")
        b = Button(f, text="ok", command=lambda: None)
        b.pack()
        b.grid()
        b.place(x=0, y=0)
        b.configure(text="ok2")
        if b.cget("text") != "ok2":
            return False
        e = Entry(f)
        e.insert(0, "abc")
        if e.get() != "abc":
            return False
        t = Text(f)
        t.insert(END, "hello")
        if "hello" not in t.get("1.0", END):
            return False
        lb = Listbox(f)
        lb.insert(END, "a", "b")
        if lb.size() != 2:
            return False
        c = Canvas(f)
        item = c.create_line(0, 0, 10, 10)
        if item not in c._items:
            return False
        m = Menu(root)
        m.add_command(label="x", command=lambda: None)
        Toplevel(root)
        root.destroy()
        return True
    except Exception:
        return False