"""
theseus_optparse_cr — Clean-room reimplementation of optparse-style command line parsing.

This module provides a minimal command-line option parser implementation
written from scratch without referencing or importing the original optparse module.
"""

import sys as _sys


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OptParseError(Exception):
    """Base class for optparse2 errors."""
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg)

    def __str__(self):
        return self.msg


class OptionError(OptParseError):
    """Raised when an Option instance is created with invalid/inconsistent args."""
    def __init__(self, msg, option=None):
        self.option_id = str(option) if option is not None else ""
        OptParseError.__init__(self, msg)

    def __str__(self):
        if self.option_id:
            return "option %s: %s" % (self.option_id, self.msg)
        return self.msg


class OptionConflictError(OptionError):
    """Raised when conflicting options are added to a parser."""
    pass


class OptionValueError(OptParseError):
    """Raised by an option's callback when an invalid value was supplied."""
    pass


class BadOptionError(OptParseError):
    """Raised when an unrecognized option appears on the command line."""
    def __init__(self, opt_str):
        self.opt_str = opt_str

    def __str__(self):
        return "no such option: %s" % self.opt_str


class AmbiguousOptionError(BadOptionError):
    """Raised when an abbreviation matches multiple long options."""
    def __init__(self, opt_str, possibilities):
        BadOptionError.__init__(self, opt_str)
        self.possibilities = possibilities

    def __str__(self):
        return "ambiguous option: %s (%s?)" % (
            self.opt_str, ", ".join(self.possibilities))


# ---------------------------------------------------------------------------
# Values container
# ---------------------------------------------------------------------------

class Values(object):
    """Container holding parsed option values as attributes."""

    def __init__(self, defaults=None):
        if defaults:
            for (key, val) in defaults.items():
                setattr(self, key, val)

    def __repr__(self):
        return "Values(%r)" % self.__dict__

    def __eq__(self, other):
        if isinstance(other, Values):
            return self.__dict__ == other.__dict__
        if isinstance(other, dict):
            return self.__dict__ == other
        return NotImplemented

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return eq
        return not eq

    def _update(self, other_dict, mode):
        if mode == "careful":
            for (key, val) in other_dict.items():
                if hasattr(self, key):
                    continue
                setattr(self, key, val)
        elif mode == "loose":
            for (key, val) in other_dict.items():
                setattr(self, key, val)
        else:
            raise ValueError("invalid update mode: %r" % mode)

    def ensure_value(self, attr, value):
        if not hasattr(self, attr) or getattr(self, attr) is None:
            setattr(self, attr, value)
        return getattr(self, attr)


# ---------------------------------------------------------------------------
# Type checkers
# ---------------------------------------------------------------------------

def _check_int(option, opt, value):
    try:
        return int(value)
    except (ValueError, TypeError):
        raise OptionValueError(
            "option %s: invalid integer value: %r" % (opt, value))


def _check_long(option, opt, value):
    try:
        return int(value)
    except (ValueError, TypeError):
        raise OptionValueError(
            "option %s: invalid long integer value: %r" % (opt, value))


def _check_float(option, opt, value):
    try:
        return float(value)
    except (ValueError, TypeError):
        raise OptionValueError(
            "option %s: invalid floating-point value: %r" % (opt, value))


def _check_string(option, opt, value):
    return value


def _check_choice(option, opt, value):
    if value in option.choices:
        return value
    choices = ", ".join([repr(c) for c in option.choices])
    raise OptionValueError(
        "option %s: invalid choice: %r (choose from %s)" % (opt, value, choices))


_TYPE_CHECKER = {
    "int": _check_int,
    "long": _check_long,
    "float": _check_float,
    "string": _check_string,
    "choice": _check_choice,
}

_TYPES = ("string", "int", "long", "float", "choice")
_ACTIONS = ("store", "store_const", "store_true", "store_false",
            "append", "append_const", "count", "callback",
            "help", "version")
_STORE_ACTIONS = ("store", "store_const", "store_true", "store_false",
                  "append", "append_const", "count")
_TYPED_ACTIONS = ("store", "append", "callback")
_ALWAYS_TYPED_ACTIONS = ("store", "append")
_CONST_ACTIONS = ("store_const", "append_const")


# ---------------------------------------------------------------------------
# Option class
# ---------------------------------------------------------------------------

class Option(object):
    """A single command-line option."""

    ATTRS = ["action", "type", "dest", "default", "nargs", "const",
             "choices", "callback", "callback_args", "callback_kwargs",
             "help", "metavar"]

    def __init__(self, *opts, **attrs):
        self._short_opts = []
        self._long_opts = []
        self._set_opt_strings(opts)
        self._set_attrs(attrs)
        self._check_action()
        self._check_type()
        self._check_choice()
        self._check_dest()
        self._check_const()
        self._check_nargs()
        self._check_callback()

    def _set_opt_strings(self, opts):
        for opt in opts:
            if len(opt) < 2:
                raise OptionError(
                    "invalid option string %r: must be at least two characters long" % opt, self)
            elif len(opt) == 2:
                if not (opt[0] == "-" and opt[1] != "-"):
                    raise OptionError(
                        "invalid short option string %r: must be of form -x" % opt, self)
                self._short_opts.append(opt)
            else:
                if not (opt[0:2] == "--" and opt[2] != "-"):
                    raise OptionError(
                        "invalid long option string %r: must start with --, followed by non-dash" % opt, self)
                self._long_opts.append(opt)

    def _set_attrs(self, attrs):
        for attr in self.ATTRS:
            if attr in attrs:
                setattr(self, attr, attrs.pop(attr))
            else:
                if attr == "default":
                    setattr(self, attr, _NO_DEFAULT)
                else:
                    setattr(self, attr, None)
        if attrs:
            extra = sorted(attrs.keys())
            raise OptionError(
                "invalid keyword arguments: %s" % ", ".join(extra), self)

    def _check_action(self):
        if self.action is None:
            self.action = "store"
        elif self.action not in _ACTIONS:
            raise OptionError("invalid action: %r" % self.action, self)

    def _check_type(self):
        if self.type is None:
            if self.action in _ALWAYS_TYPED_ACTIONS:
                if self.choices is not None:
                    self.type = "choice"
                else:
                    self.type = "string"
        else:
            if self.type == "str":
                self.type = "string"
            if self.type not in _TYPES:
                raise OptionError("invalid option type: %r" % self.type, self)
            if self.action not in _TYPED_ACTIONS:
                raise OptionError(
                    "must not supply a type for action %r" % self.action, self)

    def _check_choice(self):
        if self.type == "choice":
            if self.choices is None:
                raise OptionError(
                    "must supply a list of choices for type 'choice'", self)
            elif not isinstance(self.choices, (tuple, list)):
                raise OptionError(
                    "choices must be a list of strings ('%s' supplied)"
                    % type(self.choices).__name__, self)
        elif self.choices is not None:
            raise OptionError(
                "must not supply choices for type %r" % self.type, self)

    def _check_dest(self):
        takes_value = (self.action in _STORE_ACTIONS and self.type is not None)
        if self.dest is None and takes_value:
            if self._long_opts:
                self.dest = self._long_opts[0][2:].replace("-", "_")
            else:
                self.dest = self._short_opts[0][1:]

    def _check_const(self):
        if self.action not in _CONST_ACTIONS and self.const is not None:
            raise OptionError(
                "'const' must not be supplied for action %r" % self.action, self)

    def _check_nargs(self):
        if self.action in _TYPED_ACTIONS:
            if self.nargs is None:
                self.nargs = 1
        elif self.nargs is not None:
            raise OptionError(
                "'nargs' must not be supplied for action %r" % self.action, self)

    def _check_callback(self):
        if self.action == "callback":
            if not callable(self.callback):
                raise OptionError(
                    "callback not callable: %r" % self.callback, self)
            if (self.callback_args is not None and
                    not isinstance(self.callback_args, tuple)):
                raise OptionError(
                    "callback_args must be a tuple", self)
            if (self.callback_kwargs is not None and
                    not isinstance(self.callback_kwargs, dict)):
                raise OptionError(
                    "callback_kwargs must be a dict", self)
        else:
            if self.callback is not None:
                raise OptionError(
                    "callback supplied for non-callback option", self)
            if self.callback_args is not None:
                raise OptionError(
                    "callback_args supplied for non-callback option", self)
            if self.callback_kwargs is not None:
                raise OptionError(
                    "callback_kwargs supplied for non-callback option", self)

    def __str__(self):
        return "/".join(self._short_opts + self._long_opts)

    __repr__ = __str__

    def takes_value(self):
        return self.type is not None

    def get_opt_string(self):
        if self._long_opts:
            return self._long_opts[0]
        return self._short_opts[0]

    def check_value(self, opt, value):
        checker = _TYPE_CHECKER.get(self.type)
        if checker is None:
            return value
        return checker(self, opt, value)

    def convert_value(self, opt, value):
        if value is None:
            return None
        if self.nargs == 1:
            return self.check_value(opt, value)
        return tuple([self.check_value(opt, v) for v in value])

    def process(self, opt, value, values, parser):
        value = self.convert_value(opt, value)
        return self.take_action(self.action, self.dest, opt, value, values, parser)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "store":
            setattr(values, dest, value)
        elif action == "store_const":
            setattr(values, dest, self.const)
        elif action == "store_true":
            setattr(values, dest, True)
        elif action == "store_false":
            setattr(values, dest, False)
        elif action == "append":
            current = getattr(values, dest, None)
            if current is None:
                current = []
                setattr(values, dest, current)
            current.append(value)
        elif action == "append_const":
            current = getattr(values, dest, None)
            if current is None:
                current = []
                setattr(values, dest, current)
            current.append(self.const)
        elif action == "count":
            current = getattr(values, dest, None) or 0
            setattr(values, dest, current + 1)
        elif action == "callback":
            args = self.callback_args or ()
            kwargs = self.callback_kwargs or {}
            self.callback(self, opt, value, parser, *args, **kwargs)
        elif action == "help":
            parser.print_help()
            parser.exit()
        elif action == "version":
            parser.print_version()
            parser.exit()
        else:
            raise ValueError("unknown action %r" % action)
        return 1


# Sentinel used to mark options without an explicit default.
class _NoDefault(object):
    def __repr__(self):
        return "(no default)"


_NO_DEFAULT = _NoDefault()


# ---------------------------------------------------------------------------
# OptionParser
# ---------------------------------------------------------------------------

class OptionParser(object):
    """A simple command-line option parser."""

    standard_option_list = []

    def __init__(self, usage=None, option_list=None, prog=None,
                 version=None, description=None, add_help_option=True):
        self.usage = usage
        self.prog = prog
        self.version = version
        self.description = description
        self.add_help_option = add_help_option

        self._short_opt = {}     # "-x" -> Option
        self._long_opt = {}      # "--xy" -> Option
        self.option_list = []
        self.defaults = {}

        for opt in self.standard_option_list:
            self._add_option_object(opt)

        if option_list:
            for opt in option_list:
                if isinstance(opt, Option):
                    self._add_option_object(opt)
                else:
                    # tuple/list (opts..., kwargs)?
                    self.add_option(*opt)

        if add_help_option:
            self.add_option("-h", "--help",
                            action="help",
                            help="show this help message and exit")
        if version:
            self.add_option("--version",
                            action="version",
                            help="show program's version number and exit")

    # -------- Option management --------

    def add_option(self, *args, **kwargs):
        if args and isinstance(args[0], Option):
            if len(args) > 1 or kwargs:
                raise TypeError(
                    "invalid arguments: option instance plus extras")
            option = args[0]
        else:
            option = Option(*args, **kwargs)
        self._add_option_object(option)
        return option

    def _add_option_object(self, option):
        # Check for conflicts.
        for opt_str in option._short_opts:
            if opt_str in self._short_opt:
                raise OptionConflictError(
                    "conflicting option string: %s" % opt_str, option)
        for opt_str in option._long_opts:
            if opt_str in self._long_opt:
                raise OptionConflictError(
                    "conflicting option string: %s" % opt_str, option)

        self.option_list.append(option)
        for opt_str in option._short_opts:
            self._short_opt[opt_str] = option
        for opt_str in option._long_opts:
            self._long_opt[opt_str] = option

        if option.dest is not None:
            if option.default is not _NO_DEFAULT:
                self.defaults[option.dest] = option.default
            elif option.dest not in self.defaults:
                self.defaults[option.dest] = None

    def get_option(self, opt_str):
        return (self._short_opt.get(opt_str)
                or self._long_opt.get(opt_str))

    def has_option(self, opt_str):
        return self.get_option(opt_str) is not None

    def remove_option(self, opt_str):
        option = self.get_option(opt_str)
        if option is None:
            raise ValueError("no such option %r" % opt_str)
        for s in option._short_opts:
            del self._short_opt[s]
        for s in option._long_opts:
            del self._long_opt[s]
        self.option_list.remove(option)

    # -------- Defaults --------

    def set_defaults(self, **kwargs):
        self.defaults.update(kwargs)

    def get_default_values(self):
        # Use a copy so callers cannot mutate the parser state.
        defaults = self.defaults.copy()
        return Values(defaults)

    # -------- Error handling --------

    def error(self, msg):
        """Print a usage message and exit."""
        prog = self._get_prog_name()
        self.print_usage(_sys.stderr)
        _sys.stderr.write("%s: error: %s\n" % (prog, msg))
        _sys.exit(2)

    def exit(self, status=0, msg=None):
        if msg:
            _sys.stderr.write(msg)
        _sys.exit(status)

    def _get_prog_name(self):
        if self.prog is not None:
            return self.prog
        argv0 = _sys.argv[0] if _sys.argv else "prog"
        # Strip directory.
        i = argv0.rfind("/")
        if i >= 0:
            argv0 = argv0[i + 1:]
        i = argv0.rfind("\\")
        if i >= 0:
            argv0 = argv0[i + 1:]
        return argv0

    # -------- Help --------

    def format_usage(self):
        if self.usage is None:
            usage = "%prog [options]"
        else:
            usage = self.usage
        prog = self._get_prog_name()
        return "Usage: " + usage.replace("%prog", prog) + "\n"

    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        if self.usage is not None or True:
            file.write(self.format_usage())

    def format_help(self):
        out = self.format_usage() + "\n"
        if self.description:
            out += self.description + "\n\n"
        out += "Options:\n"
        for option in self.option_list:
            opts = ", ".join(option._short_opts + option._long_opts)
            help_text = option.help or ""
            out += "  %-24s %s\n" % (opts, help_text)
        return out

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        file.write(self.format_help())

    def print_version(self, file=None):
        if file is None:
            file = _sys.stdout
        if self.version:
            prog = self._get_prog_name()
            file.write(self.version.replace("%prog", prog) + "\n")

    # -------- Parsing --------

    def parse_args(self, args=None, values=None):
        if args is None:
            args = _sys.argv[1:]
        else:
            args = list(args)

        if values is None:
            values = self.get_default_values()

        try:
            stop, positional = self._process_args(args, values)
        except (BadOptionError, OptionValueError, AmbiguousOptionError) as err:
            self.error(str(err))

        return values, positional

    def _process_args(self, rargs, values):
        """Walk through rargs, consuming options and values."""
        positional = []
        # We pop from the front; rargs is mutated.
        while rargs:
            arg = rargs[0]
            if arg == "--":
                # End of options.
                rargs.pop(0)
                positional.extend(rargs)
                rargs[:] = []
                break
            elif arg[:2] == "--":
                # Long option.
                rargs.pop(0)
                self._process_long_opt(arg, rargs, values)
            elif arg[:1] == "-" and len(arg) > 1:
                # Short option (possibly bundled).
                rargs.pop(0)
                self._process_short_opts(arg, rargs, values)
            else:
                positional.append(arg)
                rargs.pop(0)
        return False, positional

    def _match_long_opt(self, opt):
        if opt in self._long_opt:
            return opt
        # Allow unique prefix matching.
        possibilities = [o for o in self._long_opt if o.startswith(opt)]
        if not possibilities:
            raise BadOptionError(opt)
        if len(possibilities) == 1:
            return possibilities[0]
        raise AmbiguousOptionError(opt, possibilities)

    def _process_long_opt(self, arg, rargs, values):
        # arg starts with "--"
        if "=" in arg:
            opt, _, explicit = arg.partition("=")
            had_explicit_value = True
        else:
            opt = arg
            explicit = None
            had_explicit_value = False

        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]

        if option.takes_value():
            nargs = option.nargs
            if had_explicit_value:
                if nargs == 1:
                    value = explicit
                else:
                    # Need nargs - 1 more args.
                    if len(rargs) < nargs - 1:
                        self._not_enough_args(opt, nargs)
                    value = (explicit,) + tuple(rargs[:nargs - 1])
                    del rargs[:nargs - 1]
            else:
                if len(rargs) < nargs:
                    self._not_enough_args(opt, nargs)
                if nargs == 1:
                    value = rargs[0]
                    del rargs[0]
                else:
                    value = tuple(rargs[:nargs])
                    del rargs[:nargs]
        elif had_explicit_value:
            raise BadOptionError("%s option does not take a value" % opt)
        else:
            value = None

        option.process(opt, value, values, self)

    def _not_enough_args(self, opt, nargs):
        if nargs == 1:
            self.error("%s option requires an argument" % opt)
        else:
            self.error("%s option requires %d arguments" % (opt, nargs))

    def _process_short_opts(self, arg, rargs, values):
        # arg = "-xyz" or "-xfoo" or "-x"
        i = 1
        stop = False
        while i < len(arg) and not stop:
            opt = "-" + arg[i]
            i += 1
            if opt not in self._short_opt:
                raise BadOptionError(opt)
            option = self._short_opt[opt]

            if option.takes_value():
                nargs = option.nargs
                if i < len(arg):
                    # Remainder of arg is the value (only valid for nargs==1).
                    rest = arg[i:]
                    if nargs == 1:
                        value = rest
                    else:
                        if len(rargs) < nargs - 1:
                            self._not_enough_args(opt, nargs)
                        value = (rest,) + tuple(rargs[:nargs - 1])
                        del rargs[:nargs - 1]
                    stop = True
                else:
                    if len(rargs) < nargs:
                        self._not_enough_args(opt, nargs)
                    if nargs == 1:
                        value = rargs[0]
                        del rargs[0]
                    else:
                        value = tuple(rargs[:nargs])
                        del rargs[:nargs]
            else:
                value = None

            option.process(opt, value, values, self)


# ---------------------------------------------------------------------------
# Invariant entry points
# ---------------------------------------------------------------------------

def optparse2_parse():
    """Verify that OptionParser correctly parses a typical command line."""
    parser = OptionParser(add_help_option=False)
    parser.add_option("-f", "--file", dest="filename",
                      help="write report to FILE", metavar="FILE")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")
    parser.add_option("-n", "--count", type="int", dest="count", default=0)
    parser.add_option("-v", action="count", dest="vcount", default=0)
    parser.add_option("--mode", choices=["fast", "slow"], default="fast")

    # Test long-option = value.
    values, args = parser.parse_args(
        ["--file=out.txt", "-q", "-n", "5", "-vvv", "--mode", "slow", "extra1", "extra2"])
    if values.filename != "out.txt":
        return False
    if values.verbose is not False:
        return False
    if values.count != 5:
        return False
    if values.vcount != 3:
        return False
    if values.mode != "slow":
        return False
    if args != ["extra1", "extra2"]:
        return False

    # Test "--" terminator.
    values, args = parser.parse_args(["--", "-f", "ignored"])
    if args != ["-f", "ignored"]:
        return False

    # Test short opt with attached value: -fout
    values, args = parser.parse_args(["-fout"])
    if values.filename != "out":
        return False

    # Test bundled short flags.
    values, args = parser.parse_args(["-vvv"])
    if values.vcount != 3:
        return False

    # Test prefix matching of long options.
    values, args = parser.parse_args(["--fi=hello"])
    if values.filename != "hello":
        return False

    return True


def optparse2_defaults():
    """Verify that defaults are applied correctly."""
    parser = OptionParser(add_help_option=False)
    parser.add_option("-x", dest="x", default=10, type="int")
    parser.add_option("-y", dest="y", type="int")  # implicit None
    parser.add_option("-z", dest="z", default="hello")
    parser.set_defaults(y=99, w="set_via_method")
    parser.add_option("--no-default", dest="nodef", type="string")

    values, args = parser.parse_args([])
    if values.x != 10:
        return False
    if values.y != 99:
        return False
    if values.z != "hello":
        return False
    if getattr(values, "w", None) != "set_via_method":
        return False
    if values.nodef is not None:
        return False
    if args != []:
        return False

    # Override on command line.
    values, args = parser.parse_args(["-x", "1", "-y", "2", "-z", "world"])
    if values.x != 1 or values.y != 2 or values.z != "world":
        return False

    # get_default_values should produce the defaults independently.
    d = parser.get_default_values()
    if d.x != 10 or d.y != 99 or d.z != "hello":
        return False

    # set_defaults after add_option still wins.
    parser2 = OptionParser(add_help_option=False)
    parser2.add_option("-a", dest="a", default=1, type="int")
    parser2.set_defaults(a=42)
    v2, _ = parser2.parse_args([])
    if v2.a != 42:
        return False

    # ensure_value behavior on Values.
    v3 = Values()
    v3.ensure_value("foo", 7)
    if v3.foo != 7:
        return False
    v3.foo = None
    v3.ensure_value("foo", 8)
    if v3.foo != 8:
        return False
    v3.foo = 5
    v3.ensure_value("foo", 100)
    if v3.foo != 5:
        return False

    return True


def optparse2_error():
    """Verify error handling: unknown opt, missing value, bad type, ambiguous."""
    parser = OptionParser(add_help_option=False)
    parser.add_option("-n", dest="n", type="int")
    parser.add_option("--foo", dest="foo")
    parser.add_option("--foobar", dest="foobar")
    parser.add_option("--mode", choices=["a", "b"])

    # Override error/exit so we don't actually call sys.exit.
    captured = {"called": 0, "msg": None, "exit_status": None}

    def fake_error(msg):
        captured["called"] += 1
        captured["msg"] = msg
        raise SystemExit(2)

    def fake_exit(status=0, msg=None):
        captured["exit_status"] = status
        raise SystemExit(status)

    parser.error = fake_error
    parser.exit = fake_exit

    # 1. Unknown option.
    try:
        parser.parse_args(["--unknown"])
    except SystemExit:
        pass
    if captured["called"] < 1 or captured["msg"] is None:
        return False
    if "no such option" not in captured["msg"]:
        return False

    # 2. Bad integer value.
    captured["called"] = 0
    captured["msg"] = None
    try:
        parser.parse_args(["-n", "notanint"])
    except SystemExit:
        pass
    if captured["called"] < 1 or captured["msg"] is None:
        return False
    if "invalid integer" not in captured["msg"]:
        return False

    # 3. Missing value for option that requires one.
    captured["called"] = 0
    captured["msg"] = None
    try:
        parser.parse_args(["-n"])
    except SystemExit:
        pass
    if captured["called"] < 1 or captured["msg"] is None:
        return False
    if "requires an argument" not in captured["msg"]:
        return False

    # 4. Ambiguous prefix.
    captured["called"] = 0
    captured["msg"] = None
    try:
        parser.parse_args(["--foo=x"])
    except SystemExit:
        pass
    # --foo is exact match, so should NOT be ambiguous.
    if captured["called"] != 0:
        return False

    captured["called"] = 0
    captured["msg"] = None
    try:
        parser.parse_args(["--fo=x"])
    except SystemExit:
        pass
    if captured["called"] < 1 or captured["msg"] is None:
        return False
    if "ambiguous" not in captured["msg"]:
        return False

    # 5. Invalid choice.
    captured["called"] = 0
    captured["msg"] = None
    try:
        parser.parse_args(["--mode", "c"])
    except SystemExit:
        pass
    if captured["called"] < 1 or captured["msg"] is None:
        return False
    if "invalid choice" not in captured["msg"]:
        return False

    # 6. Conflicting options should raise OptionConflictError.
    p2 = OptionParser(add_help_option=False)
    p2.add_option("-x", dest="x")
    try:
        p2.add_option("-x", dest="x2")
    except OptionConflictError:
        pass
    else:
        return False

    # 7. Invalid option construction raises OptionError.
    try:
        Option("badopt")  # no leading dash
    except OptionError:
        pass
    else:
        return False

    # 8. error() default behavior calls sys.exit(2).
    p3 = OptionParser(add_help_option=False)
    try:
        p3.parse_args(["--definitely-not-an-option"])
    except SystemExit as e:
        if e.code != 2:
            return False
    else:
        return False

    return True


__all__ = [
    "OptionParser",
    "Option",
    "Values",
    "OptParseError",
    "OptionError",
    "OptionConflictError",
    "OptionValueError",
    "BadOptionError",
    "AmbiguousOptionError",
    "optparse2_parse",
    "optparse2_defaults",
    "optparse2_error",
]