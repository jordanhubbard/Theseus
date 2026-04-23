"""
theseus_optparse_cr — Clean-room optparse module.
No import of the standard `optparse` module.
"""

import sys as _sys
import os as _os
import textwrap as _textwrap


class OptParseError(Exception):
    pass


class OptionError(OptParseError):
    def __init__(self, msg, option):
        self.msg = msg
        self.option = option
        super().__init__(msg)

    def __str__(self):
        if self.option:
            return f"option {self.option.dest}: {self.msg}"
        return self.msg


class OptionConflictError(OptionError):
    pass


class OptionValueError(OptParseError):
    pass


class BadOptionError(OptParseError):
    def __init__(self, opt_str):
        self.opt_str = opt_str
        super().__init__(f"no such option: {opt_str}")


class AmbiguousOptionError(BadOptionError):
    def __init__(self, opt_str, possibilities):
        self.opt_str = opt_str
        self.possibilities = possibilities
        super().__init__(opt_str)


class HelpFormatter:
    NO_DEFAULT_VALUE = 'none'
    _long_opt_fmt = '--%-16s'
    _short_opt_fmt = '-%s'

    def __init__(self, indent_increment=2, max_help_position=24,
                 width=None, short_first=1):
        self.parser = None
        self.indent_increment = indent_increment
        self.max_help_position = max_help_position
        self.width = width or 80
        self.short_first = short_first
        self.current_indent = 0
        self.level = 0

    def indent(self):
        self.current_indent += self.indent_increment
        self.level += 1

    def dedent(self):
        self.current_indent -= self.indent_increment
        self.level -= 1

    def format_usage(self, usage):
        return f'Usage: {usage}\n'

    def format_heading(self, heading):
        return f'{"  " * self.level}{heading}:\n'

    def format_description(self, description):
        if description:
            return description + '\n'
        return ''

    def format_option(self, option):
        opts = ', '.join(option._short_opts + option._long_opts)
        if option.metavar:
            opts += f' {option.metavar}'
        indent = '  '
        if option.help:
            return f'{indent}{opts:<22}{option.help}\n'
        return f'{indent}{opts}\n'

    def format_option_strings(self, option):
        return ', '.join(option._short_opts + option._long_opts)


class IndentedHelpFormatter(HelpFormatter):
    pass


class TitledHelpFormatter(HelpFormatter):
    pass


def _match_abbrev(s, wordmap):
    if s in wordmap:
        return wordmap[s]
    possibilities = [word for word in wordmap if word.startswith(s)]
    if len(possibilities) == 1:
        return wordmap[possibilities[0]]
    elif not possibilities:
        raise BadOptionError(s)
    else:
        raise AmbiguousOptionError(s, possibilities)


class Values:
    def __init__(self, defaults=None):
        if defaults:
            for key, val in defaults.items():
                setattr(self, key, val)

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.__dict__!r}'

    def __eq__(self, other):
        if isinstance(other, Values):
            return self.__dict__ == other.__dict__
        elif isinstance(other, dict):
            return self.__dict__ == other
        return NotImplemented

    def _update_careful(self, dict):
        for attr, value in dict.items():
            if value is not None or not hasattr(self, attr):
                setattr(self, attr, value)

    def _update_loose(self, dict):
        self.__dict__.update(dict)

    def _update(self, dict, mode):
        if mode == 'careful':
            self._update_careful(dict)
        elif mode == 'loose':
            self._update_loose(dict)

    def read_module(self, module_name, mode='careful'):
        pass

    def read_file(self, filename, mode='careful'):
        pass

    def ensure_value(self, attr, value):
        if not hasattr(self, attr) or getattr(self, attr) is None:
            setattr(self, attr, value)
        return getattr(self, attr)


SUPPRESS_HELP = '==SUPPRESS=='
SUPPRESS_USAGE = '==SUPPRESS=='
NO_DEFAULT = ('NO', 'DEFAULT')


class Option:
    ALWAYS_TYPED_ACTIONS = ('store', 'append')
    BOOLEAN_ACTIONS = ('store_true', 'store_false', 'store_const', 'count',
                       'callback', 'help', 'version')
    TYPED_ACTIONS = ('store', 'append', 'callback')
    TYPE_CHECKER = {}

    TYPE_CHECKER['int'] = int
    TYPE_CHECKER['long'] = int
    TYPE_CHECKER['float'] = float
    TYPE_CHECKER['complex'] = complex
    TYPE_CHECKER['choice'] = lambda value, choices: value if value in choices else None

    TYPES = ('string', 'int', 'long', 'float', 'complex', 'choice')
    ACTIONS = ('store', 'store_const', 'store_true', 'store_false',
               'append', 'append_const', 'count', 'callback', 'help', 'version')

    def __init__(self, *opts, **attrs):
        self._short_opts = []
        self._long_opts = []
        self.dest = None
        self.action = 'store'
        self.type = None
        self.default = None
        self.nargs = 1
        self.const = None
        self.choices = None
        self.callback = None
        self.callback_args = None
        self.callback_kwargs = None
        self.help = None
        self.metavar = None

        for o in opts:
            if o.startswith('--'):
                self._long_opts.append(o)
                if self.dest is None:
                    self.dest = o[2:].replace('-', '_')
            elif o.startswith('-'):
                self._short_opts.append(o)
                if self.dest is None and len(o) == 2:
                    self.dest = o[1:]

        for key, val in attrs.items():
            setattr(self, key, val)

        if self.type is None and self.action in self.ALWAYS_TYPED_ACTIONS:
            self.type = 'string'

    def __repr__(self):
        return f'<Option {"/".join(self._short_opts + self._long_opts)}>'

    def takes_value(self):
        return self.type is not None

    def get_opt_string(self):
        if self._long_opts:
            return self._long_opts[0]
        if self._short_opts:
            return self._short_opts[0]
        return ''

    def check_value(self, opt, value):
        if self.type is None or self.type == 'string':
            return value
        if self.type == 'int':
            try:
                return int(value)
            except ValueError:
                raise OptionValueError(f'option {opt}: invalid integer value: {value!r}')
        if self.type == 'float':
            try:
                return float(value)
            except ValueError:
                raise OptionValueError(f'option {opt}: invalid float value: {value!r}')
        if self.type == 'choice':
            if value not in self.choices:
                choices = ', '.join(map(repr, self.choices))
                raise OptionValueError(f'option {opt}: invalid choice: {value!r} (choose from {choices})')
        return value

    def convert_value(self, opt, value):
        if value is not None:
            if self.nargs == 1:
                value = self.check_value(opt, value)
            else:
                value = tuple(self.check_value(opt, v) for v in value)
        return value

    def process(self, opt, value, values, parser):
        value = self.convert_value(opt, value)

        if self.action == 'store':
            setattr(values, self.dest, value)
        elif self.action == 'store_const':
            setattr(values, self.dest, self.const)
        elif self.action == 'store_true':
            setattr(values, self.dest, True)
        elif self.action == 'store_false':
            setattr(values, self.dest, False)
        elif self.action == 'append':
            current = getattr(values, self.dest) or []
            current.append(value)
            setattr(values, self.dest, current)
        elif self.action == 'count':
            current = getattr(values, self.dest) or 0
            setattr(values, self.dest, current + 1)
        elif self.action == 'callback':
            if self.callback:
                self.callback(self, opt, value, parser, *(self.callback_args or ()), **(self.callback_kwargs or {}))
        elif self.action == 'help':
            parser.print_help()
            parser.exit()
        elif self.action == 'version':
            parser.print_version()
            parser.exit()


class OptionGroup:
    def __init__(self, parser, title, description=None):
        self.option_list = []
        self.parser = parser
        self.title = title
        self.description = description

    def add_option(self, *opts, **kwargs):
        if len(opts) == 1 and isinstance(opts[0], Option):
            opt = opts[0]
        else:
            opt = Option(*opts, **kwargs)
        self.option_list.append(opt)
        return opt

    def get_description(self):
        return self.description or ''

    def format_help(self, formatter=None):
        result = []
        if self.title:
            result.append(f'  {self.title}:\n')
        for opt in self.option_list:
            if formatter:
                result.append(formatter.format_option(opt))
            else:
                opts = ', '.join(opt._short_opts + opt._long_opts)
                result.append(f'    {opts}\n')
        return ''.join(result)


class OptionParser:
    standard_option_list = []

    def __init__(self, usage=None, option_list=None, option_class=Option,
                 version=None, conflict_handler='error',
                 description=None, formatter=None, add_help_option=True,
                 prog=None, epilog=None):
        self.usage = usage
        self.version = version
        self.conflict_handler = conflict_handler
        self.description = description
        self.prog = prog or _os.path.basename(_sys.argv[0])
        self.epilog = epilog
        self.formatter = formatter or IndentedHelpFormatter()
        self.formatter.parser = self
        self.option_list = []
        self.option_groups = []
        self._short_opt = {}
        self._long_opt = {}
        self.defaults = {}
        self.option_class = option_class

        if add_help_option:
            self.add_option('-h', '--help', action='help',
                            help='show this help message and exit')
        if version:
            self.add_option('--version', action='version',
                            help="show program's version number and exit")

        if option_list:
            for opt in option_list:
                self.add_option(opt)

    def add_option(self, *opts, **attrs):
        if len(opts) == 1 and isinstance(opts[0], Option):
            option = opts[0]
        else:
            option = Option(*opts, **attrs)
        self.option_list.append(option)
        if option.default is not None:
            self.defaults[option.dest] = option.default
        elif option.dest and option.dest not in self.defaults:
            if option.action in ('store_true', 'store_false', 'count'):
                if option.action == 'count':
                    self.defaults[option.dest] = 0
                else:
                    self.defaults[option.dest] = None
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option
        return option

    def add_option_group(self, *args, **kwargs):
        if len(args) >= 1 and isinstance(args[0], OptionGroup):
            group = args[0]
        else:
            group = OptionGroup(self, *args, **kwargs)
        self.option_groups.append(group)
        return group

    def set_defaults(self, **kwargs):
        self.defaults.update(kwargs)

    def get_default_values(self):
        defaults = self.defaults.copy()
        return Values(defaults)

    def parse_args(self, args=None, values=None):
        if args is None:
            args = _sys.argv[1:]
        if values is None:
            values = self.get_default_values()

        largs = list(args)
        rargs = []

        while largs:
            arg = largs[0]
            if arg == '--':
                del largs[0]
                rargs.extend(largs)
                break
            elif arg.startswith('--'):
                self._process_long_opt(largs, values)
            elif arg.startswith('-') and len(arg) > 1:
                self._process_short_opts(largs, values)
            else:
                rargs.append(arg)
                del largs[0]

        return values, rargs

    def _process_long_opt(self, largs, values):
        arg = largs.pop(0)
        if '=' in arg:
            opt_str, value = arg.split('=', 1)
        else:
            opt_str = arg
            value = None

        opt = self._long_opt.get(opt_str)
        if opt is None:
            raise BadOptionError(opt_str)

        if opt.takes_value():
            if value is None:
                if largs:
                    value = largs.pop(0)
                else:
                    raise OptionValueError(f'{opt_str} option requires an argument')
        opt.process(opt_str, value, values, self)

    def _process_short_opts(self, largs, values):
        arg = largs.pop(0)
        stop = False
        i = 1
        while i < len(arg) and not stop:
            opt_str = '-' + arg[i]
            opt = self._short_opt.get(opt_str)
            if opt is None:
                raise BadOptionError(opt_str)
            i += 1
            if opt.takes_value():
                value = arg[i:] or (largs.pop(0) if largs else None)
                if value is None:
                    raise OptionValueError(f'{opt_str} option requires an argument')
                opt.process(opt_str, value, values, self)
                stop = True
            else:
                opt.process(opt_str, None, values, self)

    def format_usage(self, formatter=None):
        if self.usage:
            return f'Usage: {self.usage}\n'
        return ''

    def format_help(self, formatter=None):
        if formatter is None:
            formatter = self.formatter
        result = [self.format_usage(formatter)]
        if self.description:
            result.append(self.description + '\n')
        result.append('\nOptions:\n')
        for opt in self.option_list:
            if opt.help != SUPPRESS_HELP:
                result.append(formatter.format_option(opt))
        for group in self.option_groups:
            result.append(group.format_help(formatter))
        if self.epilog:
            result.append('\n' + self.epilog)
        return ''.join(result)

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        file.write(self.format_help())

    def print_version(self, file=None):
        if file is None:
            file = _sys.stdout
        file.write(f'{self.prog} {self.version}\n')

    def exit(self, status=0, msg=None):
        if msg:
            _sys.stderr.write(msg)
        _sys.exit(status)

    def error(self, msg):
        self.print_usage(_sys.stderr)
        self.exit(2, f'{self.prog}: error: {msg}\n')

    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        file.write(self.format_usage())


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def optparse2_parse():
    """OptionParser can parse simple options; returns True."""
    p = OptionParser()
    p.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    p.add_option('-n', '--name', dest='name', default='world')
    opts, args = p.parse_args(['-v', '--name', 'alice'])
    return opts.verbose is True and opts.name == 'alice'


def optparse2_defaults():
    """Option defaults are set correctly; returns True."""
    p = OptionParser()
    p.add_option('--count', type='int', dest='count', default=10)
    p.add_option('--flag', action='store_true', dest='flag', default=False)
    opts, _ = p.parse_args([])
    return opts.count == 10 and opts.flag is False


def optparse2_error():
    """OptionValueError exists as Exception subclass; returns True."""
    return issubclass(OptionValueError, Exception)


__all__ = [
    'OptionParser', 'OptionGroup', 'Option', 'Values',
    'OptParseError', 'OptionError', 'OptionConflictError', 'OptionValueError',
    'BadOptionError', 'AmbiguousOptionError',
    'IndentedHelpFormatter', 'TitledHelpFormatter',
    'SUPPRESS_HELP', 'SUPPRESS_USAGE', 'NO_DEFAULT',
    'optparse2_parse', 'optparse2_defaults', 'optparse2_error',
]
