"""
theseus_turtle_cr — Clean-room turtle module.
No import of the standard `turtle` module.
Provides turtle graphics API stubs; actual rendering requires display.
"""

import math as _math


_DEFAULT_SPEED = 3
_DEFAULT_COLOR = 'black'
_DEFAULT_FILLCOLOR = ''


class Vec2D(tuple):
    """2D vector class used by turtle."""

    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    def __add__(self, other):
        return Vec2D(self[0] + other[0], self[1] + other[1])

    def __sub__(self, other):
        return Vec2D(self[0] - other[0], self[1] - other[1])

    def __mul__(self, other):
        if isinstance(other, Vec2D):
            return self[0] * other[0] + self[1] * other[1]
        return Vec2D(self[0] * other, self[1] * other)

    def __abs__(self):
        return _math.hypot(*self)

    def rotate(self, angle):
        cos = _math.cos(_math.radians(angle))
        sin = _math.sin(_math.radians(angle))
        return Vec2D(self[0] * cos - self[1] * sin,
                     self[0] * sin + self[1] * cos)

    def __repr__(self):
        return f'({self[0]:.2f},{self[1]:.2f})'


class Turtle:
    """Turtle graphics object (stub)."""

    def __init__(self):
        self._pos = Vec2D(0.0, 0.0)
        self._angle = 0.0
        self._speed = _DEFAULT_SPEED
        self._color = _DEFAULT_COLOR
        self._fillcolor = _DEFAULT_FILLCOLOR
        self._pendown = True
        self._visible = True
        self._pensize = 1

    def forward(self, distance):
        angle = _math.radians(self._angle)
        dx = distance * _math.cos(angle)
        dy = distance * _math.sin(angle)
        self._pos = Vec2D(self._pos[0] + dx, self._pos[1] + dy)

    fd = forward

    def backward(self, distance):
        self.forward(-distance)

    back = bk = backward

    def right(self, angle):
        self._angle -= angle

    rt = right

    def left(self, angle):
        self._angle += angle

    lt = left

    def goto(self, x, y=None):
        if isinstance(x, tuple):
            x, y = x
        self._pos = Vec2D(float(x), float(y or 0.0))

    setpos = setposition = goto

    def setx(self, x):
        self._pos = Vec2D(float(x), self._pos[1])

    def sety(self, y):
        self._pos = Vec2D(self._pos[0], float(y))

    def setheading(self, to_angle):
        self._angle = float(to_angle)

    seth = setheading

    def home(self):
        self._pos = Vec2D(0.0, 0.0)
        self._angle = 0.0

    def pos(self):
        return self._pos

    position = pos

    def xcor(self):
        return self._pos[0]

    def ycor(self):
        return self._pos[1]

    def heading(self):
        return self._angle

    def distance(self, x, y=None):
        if isinstance(x, Vec2D):
            return abs(self._pos - x)
        return _math.hypot(self._pos[0] - x, self._pos[1] - (y or 0.0))

    def speed(self, speed=None):
        if speed is None:
            return self._speed
        self._speed = speed

    def pendown(self):
        self._pendown = True

    pd = down = pendown

    def penup(self):
        self._pendown = False

    pu = up = penup

    def isdown(self):
        return self._pendown

    def pencolor(self, *args):
        if args:
            self._color = args[0] if len(args) == 1 else args
        return self._color

    def fillcolor(self, *args):
        if args:
            self._fillcolor = args[0] if len(args) == 1 else args
        return self._fillcolor

    def color(self, *args):
        if args:
            if len(args) == 1:
                self._color = args[0]
            else:
                self._color, self._fillcolor = args[0], args[1]
        return self._color, self._fillcolor

    def pensize(self, width=None):
        if width is not None:
            self._pensize = width
        return self._pensize

    width = pensize

    def circle(self, radius, extent=None, steps=None):
        pass

    def dot(self, size=None, *color):
        pass

    def stamp(self):
        return 0

    def clearstamp(self, stampid):
        pass

    def clearstamps(self, n=None):
        pass

    def undo(self):
        pass

    def showturtle(self):
        self._visible = True

    st = showturtle

    def hideturtle(self):
        self._visible = False

    ht = hideturtle

    def isvisible(self):
        return self._visible

    def shape(self, name=None):
        return 'classic'

    def shapesize(self, stretch_wid=None, stretch_len=None, outline=None):
        return (1.0, 1.0, 1)

    def begin_fill(self):
        pass

    def end_fill(self):
        pass

    def filling(self):
        return False

    def clear(self):
        pass

    def reset(self):
        self._pos = Vec2D(0.0, 0.0)
        self._angle = 0.0
        self._pendown = True
        self._speed = _DEFAULT_SPEED

    def write(self, arg, move=False, align='left', font=('Arial', 8, 'normal')):
        pass

    def onclick(self, fun, btn=1, add=None):
        pass

    def onrelease(self, fun, btn=1, add=None):
        pass

    def ondrag(self, fun, btn=1, add=None):
        pass


class RawTurtle(Turtle):
    pass


class RawPen(RawTurtle):
    pass


# Module-level functions (delegate to a global turtle instance)
_turtle = None


def _get_turtle():
    global _turtle
    if _turtle is None:
        _turtle = Turtle()
    return _turtle


def forward(distance):
    _get_turtle().forward(distance)


fd = forward


def backward(distance):
    _get_turtle().backward(distance)


back = bk = backward


def right(angle):
    _get_turtle().right(angle)


rt = right


def left(angle):
    _get_turtle().left(angle)


lt = left


def goto(x, y=None):
    _get_turtle().goto(x, y)


setpos = setposition = goto


def home():
    _get_turtle().home()


def pos():
    return _get_turtle().pos()


position = pos


def xcor():
    return _get_turtle().xcor()


def ycor():
    return _get_turtle().ycor()


def heading():
    return _get_turtle().heading()


def speed(speed=None):
    return _get_turtle().speed(speed)


def pendown():
    _get_turtle().pendown()


pd = down = pendown


def penup():
    _get_turtle().penup()


pu = up = penup


def isdown():
    return _get_turtle().isdown()


def color(*args):
    return _get_turtle().color(*args)


def pencolor(*args):
    return _get_turtle().pencolor(*args)


def fillcolor(*args):
    return _get_turtle().fillcolor(*args)


def pensize(width=None):
    return _get_turtle().pensize(width)


width = pensize


def circle(radius, extent=None, steps=None):
    _get_turtle().circle(radius, extent, steps)


def dot(size=None, *color):
    _get_turtle().dot(size, *color)


def shape(name=None):
    return _get_turtle().shape(name)


def setheading(to_angle):
    _get_turtle().setheading(to_angle)


seth = setheading


def begin_fill():
    _get_turtle().begin_fill()


def end_fill():
    _get_turtle().end_fill()


def filling():
    return _get_turtle().filling()


def clear():
    _get_turtle().clear()


def reset():
    _get_turtle().reset()


def write(arg, move=False, align='left', font=('Arial', 8, 'normal')):
    _get_turtle().write(arg, move, align, font)


def showturtle():
    _get_turtle().showturtle()


st = showturtle


def hideturtle():
    _get_turtle().hideturtle()


ht = hideturtle


def isvisible():
    return _get_turtle().isvisible()


def done():
    pass


def bye():
    pass


def exitonclick():
    pass


def setup(width=None, height=None, startx=None, starty=None):
    pass


def screensize(canvwidth=None, canvheight=None, bg=None):
    return (400, 300)


def bgcolor(color=None):
    return 'white'


def bgpic(picname=None):
    return 'nopic'


def title(titlestring):
    pass


def tracer(n=None, delay=None):
    pass


def update():
    pass


def delay(delay=None):
    return 10


def listen(xdummy=None, ydummy=None):
    pass


def onkeypress(fun, key=None):
    pass


def onkey(fun, key):
    pass


def onkeyrelease(fun, key):
    pass


def mainloop():
    pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def turtle2_vec2d():
    """Vec2D arithmetic works; returns True."""
    v1 = Vec2D(3.0, 4.0)
    v2 = Vec2D(1.0, 2.0)
    return (abs(v1) == 5.0 and
            v1 + v2 == Vec2D(4.0, 6.0) and
            v1 * v2 == 11.0)


def turtle2_turtle():
    """Turtle instance movement tracking works; returns True."""
    t = Turtle()
    t.forward(100)
    t.left(90)
    x, y = t.pos()
    return (abs(x - 100.0) < 0.001 and
            abs(y) < 0.001 and
            t.heading() == 90.0)


def turtle2_global():
    """Global turtle functions work; returns True."""
    global _turtle
    _turtle = Turtle()
    forward(50)
    left(45)
    return (isinstance(pos(), Vec2D) and
            isinstance(heading(), float))


__all__ = [
    'Turtle', 'RawTurtle', 'RawPen', 'Vec2D',
    'forward', 'fd', 'backward', 'back', 'bk',
    'right', 'rt', 'left', 'lt',
    'goto', 'setpos', 'setposition',
    'home', 'pos', 'position', 'xcor', 'ycor', 'heading',
    'speed', 'pendown', 'pd', 'down', 'penup', 'pu', 'up', 'isdown',
    'color', 'pencolor', 'fillcolor', 'pensize', 'width',
    'circle', 'dot', 'shape', 'setheading', 'seth',
    'begin_fill', 'end_fill', 'filling', 'clear', 'reset', 'write',
    'showturtle', 'st', 'hideturtle', 'ht', 'isvisible',
    'done', 'bye', 'exitonclick', 'setup', 'screensize', 'bgcolor',
    'bgpic', 'title', 'tracer', 'update', 'delay', 'listen',
    'onkeypress', 'onkey', 'onkeyrelease', 'mainloop',
    'turtle2_vec2d', 'turtle2_turtle', 'turtle2_global',
]
