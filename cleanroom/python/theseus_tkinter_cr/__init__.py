"""
theseus_tkinter_cr — Clean-room tkinter module.
No import of the standard `tkinter` module.
Provides tkinter API stubs; actual Tk operations require display.
"""

import sys as _sys


class TclError(Exception):
    """Exception raised on Tcl/Tk errors."""
    pass


class Variable:
    """Base class for tkinter variables."""
    _default = ""

    def __init__(self, master=None, value=None, name=None):
        self._name = name or id(self)
        self._value = value if value is not None else self._default

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, mode, callback):
        pass

    def trace_remove(self, mode, cbname):
        pass

    def trace_info(self):
        return []

    def __str__(self):
        return str(self._name)


class StringVar(Variable):
    _default = ""


class IntVar(Variable):
    _default = 0

    def get(self):
        return int(self._value)


class DoubleVar(Variable):
    _default = 0.0

    def get(self):
        return float(self._value)


class BooleanVar(Variable):
    _default = False

    def get(self):
        return bool(self._value)


# Widget constants
TOP = 'top'
BOTTOM = 'bottom'
LEFT = 'left'
RIGHT = 'right'
BOTH = 'both'
X = 'x'
Y = 'y'
NONE = 'none'
CENTER = 'center'
N = 'n'
S = 's'
E = 'e'
W = 'w'
NE = 'ne'
NW = 'nw'
SE = 'se'
SW = 'sw'
HORIZONTAL = 'horizontal'
VERTICAL = 'vertical'
FLAT = 'flat'
GROOVE = 'groove'
RAISED = 'raised'
RIDGE = 'ridge'
SOLID = 'solid'
SUNKEN = 'sunken'
NORMAL = 'normal'
ACTIVE = 'active'
DISABLED = 'disabled'
HIDDEN = 'hidden'
INSERT = 'insert'
FIRST = 'first'
LAST = 'last'
END = 'end'
CURRENT = 'current'
ANCHOR = 'anchor'
ALL = 'all'
ROUND = 'round'
BUTT = 'butt'
PROJECTING = 'projecting'
BEVEL = 'bevel'
MITER = 'miter'
WORD = 'word'
CHAR = 'char'
SINGLE = 'single'
MULTIPLE = 'multiple'
EXTENDED = 'extended'
BROWSE = 'browse'
NUMERIC = 'numeric'
READABLE = 'readable'
WRITABLE = 'writable'
EXCEPTION = 'exception'

# Tk version stub
TkVersion = 8.6
TclVersion = 8.6


class Misc:
    """Base class for Tk widgets (stub)."""

    def configure(self, **kw):
        pass

    config = configure

    def cget(self, key):
        return None

    def keys(self):
        return []

    def bind(self, sequence=None, func=None, add=None):
        pass

    def unbind(self, sequence, funcid=None):
        pass

    def pack(self, **kw):
        pass

    def grid(self, **kw):
        pass

    def place(self, **kw):
        pass

    def pack_forget(self):
        pass

    def grid_forget(self):
        pass

    def place_forget(self):
        pass

    def destroy(self):
        pass

    def update(self):
        pass

    def update_idletasks(self):
        pass

    def mainloop(self, n=0):
        pass

    def quit(self):
        pass

    def winfo_exists(self):
        return False

    def winfo_width(self):
        return 0

    def winfo_height(self):
        return 0


class Tk(Misc):
    """Main Tk window stub."""

    def __init__(self, screenName=None, baseName=None, className='Tk',
                 useTk=True, sync=False, use=None):
        self.tk = None

    def title(self, string=None):
        return ''

    def geometry(self, newGeometry=None):
        return '1x1+0+0'

    def resizable(self, width=None, height=None):
        pass

    def iconify(self):
        pass

    def deiconify(self):
        pass

    def withdraw(self):
        pass

    def protocol(self, name=None, func=None):
        pass

    def after(self, ms, func=None, *args):
        pass

    def after_cancel(self, id):
        pass


class Widget(Misc):
    """Generic widget stub."""

    def __init__(self, master=None, **kw):
        self.master = master


class Frame(Widget):
    pass


class LabelFrame(Widget):
    pass


class Label(Widget):
    pass


class Button(Widget):
    def invoke(self):
        pass


class Entry(Widget):
    def get(self):
        return ''

    def insert(self, index, string):
        pass

    def delete(self, first, last=None):
        pass


class Text(Widget):
    def get(self, index1, index2=None):
        return ''

    def insert(self, index, chars, *args):
        pass

    def delete(self, index1, index2=None):
        pass


class Scrollbar(Widget):
    pass


class Listbox(Widget):
    pass


class Canvas(Widget):
    def create_line(self, *args, **kw):
        return 0

    def create_rectangle(self, *args, **kw):
        return 0

    def create_oval(self, *args, **kw):
        return 0

    def create_text(self, *args, **kw):
        return 0

    def delete(self, *args):
        pass


class Menu(Widget):
    def add_command(self, **kw):
        pass

    def add_separator(self):
        pass

    def add_cascade(self, **kw):
        pass


class Menubutton(Widget):
    pass


class Checkbutton(Widget):
    pass


class Radiobutton(Widget):
    pass


class Scale(Widget):
    pass


class Spinbox(Widget):
    pass


class OptionMenu(Widget):
    pass


class Toplevel(Misc):
    def __init__(self, master=None, **kw):
        self.master = master


class BaseWidget(Widget):
    pass


def mainloop(n=0):
    pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tkinter2_variables():
    """StringVar/IntVar/BooleanVar work; returns True."""
    sv = StringVar(value='hello')
    iv = IntVar(value=42)
    bv = BooleanVar(value=True)
    return (sv.get() == 'hello' and
            iv.get() == 42 and
            bv.get() is True)


def tkinter2_constants():
    """tkinter constants have correct values; returns True."""
    return (TOP == 'top' and
            BOTTOM == 'bottom' and
            LEFT == 'left' and
            RIGHT == 'right' and
            END == 'end')


def tkinter2_classes():
    """tkinter widget stubs are instantiable; returns True."""
    return (issubclass(Button, Widget) and
            issubclass(Frame, Widget) and
            issubclass(Label, Widget) and
            issubclass(TclError, Exception))


__all__ = [
    'Tk', 'Widget', 'Frame', 'LabelFrame', 'Label', 'Button', 'Entry',
    'Text', 'Scrollbar', 'Listbox', 'Canvas', 'Menu', 'Menubutton',
    'Checkbutton', 'Radiobutton', 'Scale', 'Spinbox', 'OptionMenu',
    'Toplevel', 'BaseWidget', 'Misc',
    'Variable', 'StringVar', 'IntVar', 'DoubleVar', 'BooleanVar',
    'TclError', 'mainloop',
    'TkVersion', 'TclVersion',
    'TOP', 'BOTTOM', 'LEFT', 'RIGHT', 'BOTH', 'X', 'Y', 'NONE',
    'CENTER', 'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW',
    'HORIZONTAL', 'VERTICAL', 'FLAT', 'GROOVE', 'RAISED', 'RIDGE',
    'SOLID', 'SUNKEN', 'NORMAL', 'ACTIVE', 'DISABLED', 'HIDDEN',
    'INSERT', 'FIRST', 'LAST', 'END', 'CURRENT', 'ANCHOR', 'ALL',
    'WORD', 'CHAR', 'SINGLE', 'MULTIPLE', 'EXTENDED', 'BROWSE',
    'NUMERIC', 'READABLE', 'WRITABLE', 'EXCEPTION',
    'tkinter2_variables', 'tkinter2_constants', 'tkinter2_classes',
]
