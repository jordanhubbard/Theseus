# generation A option scan

def getopt(args, shortopts):
    shortargs = {}
    idx = 0
    while idx < len(shortopts):
        ch = shortopts[idx]
        if ch == ':':
            idx += 1
            continue
        if idx + 1 < len(shortopts) and shortopts[idx + 1] == ':':
            shortargs[ch] = True
            idx += 2
        else:
            shortargs[ch] = False
            idx += 1

    opts = []
    leftover = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--':
            leftover.extend(args[i + 1:])
            break
        if len(arg) >= 2 and arg[0] == '-' and arg[1] != '-':
            j = 1
            while j < len(arg):
                opt = arg[j]
                if opt not in shortargs:
                    raise ValueError('option -%s not recognized' % opt)
                if shortargs[opt]:
                    if j < len(arg) - 1:
                        optarg = arg[j + 1:]
                        j = len(arg)
                    elif i + 1 < len(args):
                        optarg = args[i + 1]
                        i += 1
                        j = len(arg)
                    else:
                        raise ValueError('option -%s requires argument' % opt)
                    opts.append(('-' + opt, optarg))
                else:
                    opts.append(('-' + opt, ''))
                    j += 1
        elif len(arg) >= 2 and arg[0] == '-' and arg[1] == '-':
            raise ValueError('option %s not recognized' % arg)
        else:
            leftover.append(arg)
            leftover.extend(args[i + 1:])
            break
        i += 1

    return opts, leftover
