# generation A escape scan

def escape(pathname):
    out = []
    for ch in pathname:
        if ch == '*' or ch == '?' or ch == '[':
            out.append('[')
            out.append(ch)
            out.append(']')
        else:
            out.append(ch)
    return ''.join(out)
