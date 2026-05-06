"""Clean-room turtle graphics stub for theseus_turtle_cr.

This is a minimal clean-room implementation that does NOT import the
original `turtle` module. It provides simple Vec2D and Turtle classes
along with module-level (global) turtle functions, and exposes the
three invariant probe functions required by the spec.
"""

import math as _math


# ---------------------------------------------------------------------------
# Vec2D — a 2-element vector type, similar in spirit to turtle.Vec2D
# ---------------------------------------------------------------------------

class Vec2D(tuple):
    """A 2D vector represented as a 2-tuple of floats."""

    def __new__(cls, x, y):
        return tuple.__new__(cls, (float(x), float(y)))

    def __add__(self, other):
        return Vec2D(self[0] + other[0], self[1] + other[1])

    def __sub__(self, other):
        return Vec2D(self[0] - other[0], self[1] - other[1])

    def __mul__(self, other):
        if isinstance(other, Vec2D):
            # dot product
            return self[0] * other[0] + self[1] * other[1]
        return Vec2D(self[0] * other, self[1] * other)

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return Vec2D(self[0] * other, self[1] * other)
        return NotImplemented

    def __neg__(self):
        return Vec2D(-self[0], -self[1])

    def __abs__(self):
        return _math.hypot(self[0], self[1])

    def rotate(self, angle):
        """Rotate self by angle (in degrees) counterclockwise."""
        rad = _math.radians(angle)
        c = _math.cos(rad)
        s = _math.sin(rad)
        x, y = self[0], self[1]
        return Vec2D(x * c - y * s, x * s + y * c)

    def __repr__(self):
        return "(%.2f,%.2f)" % (self[0], self[1])


# ---------------------------------------------------------------------------
# Turtle — a clean-room turtle that tracks state without any graphics
# ---------------------------------------------------------------------------

class Turtle(object):
    """A non-drawing turtle that tracks position, heading, and pen state."""

    def __init__(self):
        self._pos = Vec2D(0.0, 0.0)
        self._heading = 0.0  # degrees, 0 = east, counter-clockwise positive
        self._pen_down = True
        self._mode = "standard"
        self._track = [Vec2D(0.0, 0.0)]

    # --- position / heading queries -----------------------------------------

    def position(self):
        return self._pos

    pos = position

    def xcor(self):
        return self._pos[0]

    def ycor(self):
        return self._pos[1]

    def heading(self):
        return self._heading

    def isdown(self):
        return self._pen_down

    # --- pen control --------------------------------------------------------

    def penup(self):
        self._pen_down = False

    pu = up = penup

    def pendown(self):
        self._pen_down = True

    pd = down = pendown

    # --- motion -------------------------------------------------------------

    def _set_pos(self, new_pos):
        self._pos = new_pos
        self._track.append(new_pos)

    def forward(self, distance):
        rad = _math.radians(self._heading)
        dx = distance * _math.cos(rad)
        dy = distance * _math.sin(rad)
        self._set_pos(Vec2D(self._pos[0] + dx, self._pos[1] + dy))

    fd = forward

    def backward(self, distance):
        self.forward(-distance)

    bk = back = backward

    def left(self, angle):
        self._heading = (self._heading + angle) % 360.0

    lt = left

    def right(self, angle):
        self._heading = (self._heading - angle) % 360.0

    rt = right

    def setheading(self, to_angle):
        self._heading = to_angle % 360.0

    seth = setheading

    def goto(self, x, y=None):
        if y is None:
            # x is a 2-tuple / Vec2D
            new_pos = Vec2D(x[0], x[1])
        else:
            new_pos = Vec2D(x, y)
        self._set_pos(new_pos)

    setpos = setposition = goto

    def setx(self, x):
        self._set_pos(Vec2D(x, self._pos[1]))

    def sety(self, y):
        self._set_pos(Vec2D(self._pos[0], y))

    def home(self):
        self._set_pos(Vec2D(0.0, 0.0))
        self._heading = 0.0

    def reset(self):
        self.__init__()

    def distance(self, x, y=None):
        if y is None:
            target = Vec2D(x[0], x[1])
        else:
            target = Vec2D(x, y)
        return abs(target - self._pos)

    def towards(self, x, y=None):
        if y is None:
            target = Vec2D(x[0], x[1])
        else:
            target = Vec2D(x, y)
        dx = target[0] - self._pos[0]
        dy = target[1] - self._pos[1]
        return _math.degrees(_math.atan2(dy, dx)) % 360.0


# ---------------------------------------------------------------------------
# Module-level "global" turtle — mirrors the procedural turtle API
# ---------------------------------------------------------------------------

_default_turtle = None


def _get_default():
    global _default_turtle
    if _default_turtle is None:
        _default_turtle = Turtle()
    return _default_turtle


def forward(distance):
    _get_default().forward(distance)


fd = forward


def backward(distance):
    _get_default().backward(distance)


bk = back = backward


def left(angle):
    _get_default().left(angle)


lt = left


def right(angle):
    _get_default().right(angle)


rt = right


def goto(x, y=None):
    _get_default().goto(x, y)


setpos = setposition = goto


def setheading(to_angle):
    _get_default().setheading(to_angle)


seth = setheading


def position():
    return _get_default().position()


pos = position


def xcor():
    return _get_default().xcor()


def ycor():
    return _get_default().ycor()


def heading():
    return _get_default().heading()


def penup():
    _get_default().penup()


pu = up = penup


def pendown():
    _get_default().pendown()


pd = down = pendown


def isdown():
    return _get_default().isdown()


def home():
    _get_default().home()


def reset():
    global _default_turtle
    _default_turtle = Turtle()


# ---------------------------------------------------------------------------
# Invariant probe functions
# ---------------------------------------------------------------------------

def turtle2_vec2d():
    """Verify Vec2D arithmetic, rotation, and abs behave correctly."""
    a = Vec2D(3, 4)
    b = Vec2D(1, 2)

    # basic construction yields floats
    if not (isinstance(a[0], float) and isinstance(a[1], float)):
        return False
    if a[0] != 3.0 or a[1] != 4.0:
        return False

    # addition / subtraction
    s = a + b
    if (s[0], s[1]) != (4.0, 6.0):
        return False
    d = a - b
    if (d[0], d[1]) != (2.0, 2.0):
        return False

    # scalar multiplication
    m = a * 2
    if (m[0], m[1]) != (6.0, 8.0):
        return False
    rm = 2 * a
    if (rm[0], rm[1]) != (6.0, 8.0):
        return False

    # dot product
    if a * b != 3.0 * 1.0 + 4.0 * 2.0:
        return False

    # negation
    n = -a
    if (n[0], n[1]) != (-3.0, -4.0):
        return False

    # abs (length)
    if abs(Vec2D(3, 4)) != 5.0:
        return False

    # rotation by 90 degrees: (1,0) -> (0,1)
    r = Vec2D(1, 0).rotate(90)
    if not (abs(r[0]) < 1e-9 and abs(r[1] - 1.0) < 1e-9):
        return False

    # rotation by 180 degrees: (1,0) -> (-1,0)
    r2 = Vec2D(1, 0).rotate(180)
    if not (abs(r2[0] + 1.0) < 1e-9 and abs(r2[1]) < 1e-9):
        return False

    return True


def turtle2_turtle():
    """Verify Turtle motion, heading, and pen state mechanics."""
    t = Turtle()

    # initial state
    if t.position() != (0.0, 0.0):
        return False
    if t.heading() != 0.0:
        return False
    if not t.isdown():
        return False

    # forward 100 along east
    t.forward(100)
    if abs(t.xcor() - 100.0) > 1e-9 or abs(t.ycor()) > 1e-9:
        return False

    # turn left 90, forward 50 -> y = 50
    t.left(90)
    if abs(t.heading() - 90.0) > 1e-9:
        return False
    t.forward(50)
    if abs(t.xcor() - 100.0) > 1e-9 or abs(t.ycor() - 50.0) > 1e-9:
        return False

    # right 90 returns to east
    t.right(90)
    if abs(t.heading()) > 1e-9:
        return False

    # backward
    t.backward(100)
    if abs(t.xcor() - 0.0) > 1e-9 or abs(t.ycor() - 50.0) > 1e-9:
        return False

    # pen control
    t.penup()
    if t.isdown():
        return False
    t.pendown()
    if not t.isdown():
        return False

    # absolute placement
    t.goto(10, 20)
    if t.position() != (10.0, 20.0):
        return False
    t.setx(7)
    if abs(t.xcor() - 7.0) > 1e-9:
        return False
    t.sety(8)
    if abs(t.ycor() - 8.0) > 1e-9:
        return False

    # setheading + heading wrap
    t.setheading(450)
    if abs(t.heading() - 90.0) > 1e-9:
        return False

    # distance / towards
    t.home()
    if t.position() != (0.0, 0.0) or t.heading() != 0.0:
        return False
    if abs(t.distance(3, 4) - 5.0) > 1e-9:
        return False
    if abs(t.towards(0, 1) - 90.0) > 1e-9:
        return False

    # reset returns to a clean state
    t.forward(42)
    t.reset()
    if t.position() != (0.0, 0.0) or t.heading() != 0.0:
        return False

    return True


def turtle2_global():
    """Verify module-level (global) turtle functions track a shared turtle."""
    reset()

    if position() != (0.0, 0.0):
        return False
    if heading() != 0.0:
        return False
    if not isdown():
        return False

    forward(10)
    if abs(xcor() - 10.0) > 1e-9 or abs(ycor()) > 1e-9:
        return False

    left(90)
    forward(5)
    if abs(xcor() - 10.0) > 1e-9 or abs(ycor() - 5.0) > 1e-9:
        return False

    right(90)
    if abs(heading()) > 1e-9:
        return False

    backward(10)
    if abs(xcor()) > 1e-9 or abs(ycor() - 5.0) > 1e-9:
        return False

    penup()
    if isdown():
        return False
    pendown()
    if not isdown():
        return False

    goto(3, 4)
    if position() != (3.0, 4.0):
        return False

    setheading(180)
    if abs(heading() - 180.0) > 1e-9:
        return False

    home()
    if position() != (0.0, 0.0) or heading() != 0.0:
        return False

    # aliases work too
    fd(1)
    bk(1)
    lt(45)
    rt(45)
    if abs(xcor()) > 1e-9 or abs(ycor()) > 1e-9:
        return False
    if abs(heading()) > 1e-9:
        return False

    reset()
    return True


__all__ = [
    "Vec2D",
    "Turtle",
    "forward", "fd",
    "backward", "back", "bk",
    "left", "lt",
    "right", "rt",
    "goto", "setpos", "setposition",
    "setheading", "seth",
    "position", "pos",
    "xcor", "ycor", "heading",
    "penup", "pu", "up",
    "pendown", "pd", "down",
    "isdown", "home", "reset",
    "turtle2_vec2d", "turtle2_turtle", "turtle2_global",
]