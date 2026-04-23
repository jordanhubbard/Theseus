"""
Clean-room implementation of getopt functionality.
Do NOT import the original getopt module.
"""


class GetoptError(Exception):
    """Exception raised for getopt errors."""
    def __init__(self, msg, opt=''):
        self.msg = msg
        self.opt = opt
        super().__init__(msg)
    
    def __str__(self):
        return self.msg


def getopt(args, shortopts, longopts=None):
    """
    Parse command-line options.
    
    args: list of arguments to parse
    shortopts: string of short option characters; ':' after a char means it requires an argument
    longopts: list of long option strings; '=' suffix means it requires an argument
    
    Returns (opts, args) where opts is list of (option, value) pairs
    and args is the list of remaining non-option arguments.
    
    Raises GetoptError for unrecognized options.
    Stops processing at '--' or first non-option argument.
    """
    if longopts is None:
        longopts = []
    
    opts = []
    remaining = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == '--':
            # End of options
            remaining.extend(args[i+1:])
            break
        elif arg.startswith('--'):
            # Long option
            i, opt_pair = _parse_long_opt(arg, args, i, longopts)
            opts.append(opt_pair)
        elif arg.startswith('-') and len(arg) > 1:
            # Short option(s)
            new_opts, i = _parse_short_opts(arg, args, i, shortopts)
            opts.extend(new_opts)
        else:
            # Non-option argument: stop processing (standard getopt behavior)
            remaining.append(arg)
            remaining.extend(args[i+1:])
            break
        
        i += 1
    
    return opts, remaining


def gnu_getopt(args, shortopts, longopts=None):
    """
    Like getopt(), but does not stop at the first non-option argument.
    Non-option arguments are interspersed with options.
    
    Returns (opts, args) where opts is list of (option, value) pairs
    and args is the list of non-option arguments.
    """
    if longopts is None:
        longopts = []
    
    opts = []
    remaining = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == '--':
            # End of options
            remaining.extend(args[i+1:])
            break
        elif arg.startswith('--'):
            # Long option
            i, opt_pair = _parse_long_opt(arg, args, i, longopts)
            opts.append(opt_pair)
        elif arg.startswith('-') and len(arg) > 1:
            # Short option(s)
            new_opts, i = _parse_short_opts(arg, args, i, shortopts)
            opts.extend(new_opts)
        else:
            # Non-option argument: collect but continue processing
            remaining.append(arg)
        
        i += 1
    
    return opts, remaining


def _parse_long_opt(arg, args, i, longopts):
    """
    Parse a long option (--option or --option=value).
    Returns (new_index, (option, value)) tuple.
    """
    # Strip leading '--'
    if '=' in arg:
        opt_name, opt_val = arg[2:].split('=', 1)
        has_value = True
    else:
        opt_name = arg[2:]
        opt_val = None
        has_value = False
    
    # Find matching long option
    matched = None
    requires_arg = False
    
    for longopt in longopts:
        if longopt.endswith('='):
            name = longopt[:-1]
            req_arg = True
        else:
            name = longopt
            req_arg = False
        
        if name == opt_name:
            matched = name
            requires_arg = req_arg
            break
    
    if matched is None:
        raise GetoptError(f"option --{opt_name} not recognized", f"--{opt_name}")
    
    if requires_arg:
        if has_value:
            value = opt_val
        else:
            # Next argument is the value
            if i + 1 >= len(args):
                raise GetoptError(f"option --{opt_name} requires an argument", f"--{opt_name}")
            i += 1
            value = args[i]
    else:
        if has_value:
            raise GetoptError(f"option --{opt_name} must not have an argument", f"--{opt_name}")
        value = ''
    
    return i, (f"--{matched}", value)


def _parse_short_opts(arg, args, i, shortopts):
    """
    Parse short options from a single argument like '-abc' or '-aVALUE'.
    Returns (list_of_opt_pairs, new_index).
    """
    opts = []
    # arg starts with '-', characters after are option chars
    j = 1
    while j < len(arg):
        opt_char = arg[j]
        
        # Find this option in shortopts
        pos = shortopts.find(opt_char)
        if pos == -1:
            raise GetoptError(f"option -{opt_char} not recognized", f"-{opt_char}")
        
        # Check if it requires an argument (next char in shortopts is ':')
        requires_arg = (pos + 1 < len(shortopts) and shortopts[pos + 1] == ':')
        
        if requires_arg:
            # Rest of this argument is the value, or next argument
            rest = arg[j+1:]
            if rest:
                value = rest
                j = len(arg)  # consumed rest of arg
            else:
                # Next argument is the value
                if i + 1 >= len(args):
                    raise GetoptError(f"option -{opt_char} requires an argument", f"-{opt_char}")
                i += 1
                value = args[i]
                j = len(arg)
            opts.append((f"-{opt_char}", value))
        else:
            opts.append((f"-{opt_char}", ''))
            j += 1
    
    return opts, i


# Invariant test functions (zero-argument, return hardcoded results via actual computation)

def getopt_short():
    """getopt(['-a', '-b'], 'ab') == ([('-a',''),('-b','')], [])"""
    result, _ = getopt(['-a', '-b'], 'ab')
    return [[opt, val] for opt, val in result]


def getopt_long():
    """getopt(['--verbose'], '', ['verbose']) == ([('--verbose','')], [])"""
    result, _ = getopt(['--verbose'], '', ['verbose'])
    return [[opt, val] for opt, val in result]


def getopt_remaining():
    """getopt(['-a', 'rest'], 'a') == ([('-a','')], ['rest'])"""
    _, remaining = getopt(['-a', 'rest'], 'a')
    return remaining