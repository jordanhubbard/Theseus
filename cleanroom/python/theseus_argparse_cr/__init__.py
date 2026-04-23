"""
theseus_argparse_cr — Clean-room argparse subset.
No import of the standard `argparse` module.
"""

import sys


class Namespace:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __eq__(self, other):
        return isinstance(other, Namespace) and vars(self) == vars(other)

    def __repr__(self):
        args = ', '.join(f'{k}={v!r}' for k, v in sorted(vars(self).items()))
        return f'Namespace({args})'


class ArgumentError(Exception):
    pass


class _Action:
    def __init__(self, option_strings, dest, default, type_, action_type, const):
        self.option_strings = option_strings
        self.dest = dest
        self.default = default
        self.type = type_
        self.action_type = action_type
        self.const = const


class ArgumentParser:
    def __init__(self, prog=None, description=None, add_help=True):
        self.prog = prog or sys.argv[0]
        self.description = description
        self._actions = []
        self._option_string_actions = {}
        self._positionals = []

    def add_argument(self, *name_or_flags, **kwargs):
        action_type = kwargs.get('action', 'store')
        dest = kwargs.get('dest')
        default = kwargs.get('default', None)
        type_ = kwargs.get('type', None)

        option_strings = [f for f in name_or_flags if f.startswith('-')]
        positional_names = [f for f in name_or_flags if not f.startswith('-')]

        if option_strings:
            if dest is None:
                long_opts = [o for o in option_strings if o.startswith('--')]
                dest = (long_opts[0] if long_opts else option_strings[0]).lstrip('-').replace('-', '_')
        else:
            if dest is None:
                dest = positional_names[0].replace('-', '_')

        const = True if action_type == 'store_true' else (False if action_type == 'store_false' else None)
        if action_type == 'store_true' and default is None:
            default = False
        if action_type == 'store_false' and default is None:
            default = True

        act = _Action(option_strings, dest, default, type_, action_type, const)
        self._actions.append(act)
        for opt in option_strings:
            self._option_string_actions[opt] = act
        if not option_strings:
            self._positionals.append(act)
        return act

    def parse_args(self, args=None):
        if args is None:
            args = sys.argv[1:]
        namespace = Namespace()

        for action in self._actions:
            setattr(namespace, action.dest, action.default)

        positional_queue = list(self._positionals)
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in self._option_string_actions:
                action = self._option_string_actions[arg]
                if action.action_type in ('store_true', 'store_false'):
                    setattr(namespace, action.dest, action.const)
                    i += 1
                else:
                    i += 1
                    if i >= len(args):
                        raise ArgumentError(f"argument {arg}: expected one argument")
                    value = args[i]
                    if action.type is not None:
                        value = action.type(value)
                    setattr(namespace, action.dest, value)
                    i += 1
            elif arg.startswith('--') and '=' in arg:
                key, value = arg[2:].split('=', 1)
                dest = key.replace('-', '_')
                for action in self._actions:
                    if action.dest == dest and action.type is not None:
                        value = action.type(value)
                        break
                setattr(namespace, dest, value)
                i += 1
            elif positional_queue:
                action = positional_queue.pop(0)
                value = arg
                if action.type is not None:
                    value = action.type(value)
                setattr(namespace, action.dest, value)
                i += 1
            else:
                raise ArgumentError(f"unrecognized argument: {arg}")

        return namespace


def argparse2_positional():
    """Parse positional arg 'hello'; returns 'hello'."""
    parser = ArgumentParser()
    parser.add_argument('name')
    ns = parser.parse_args(['hello'])
    return ns.name


def argparse2_optional():
    """Parse --count 5 with type=int; returns 5."""
    parser = ArgumentParser()
    parser.add_argument('--count', type=int, default=0)
    ns = parser.parse_args(['--count', '5'])
    return ns.count


def argparse2_store_true():
    """Parse --verbose; Namespace.verbose is True; returns True."""
    parser = ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    ns = parser.parse_args(['--verbose'])
    return ns.verbose


__all__ = [
    'ArgumentParser', 'Namespace', 'ArgumentError',
    'argparse2_positional', 'argparse2_optional', 'argparse2_store_true',
]
