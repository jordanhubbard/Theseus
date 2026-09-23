# generation A shorten scan

def shorten(text, width=70, placeholder='[...]'):
    collapsed = ' '.join(text.strip().split())
    if len(collapsed) <= width:
        return collapsed
    plen = len(placeholder)
    if width < plen:
        raise ValueError("placeholder too large for max width")
    words = collapsed.split()
    for n in range(len(words), 0, -1):
        prefix = ' '.join(words[:n])
        if len(prefix) + 1 + plen <= width:
            return prefix + ' ' + placeholder
    return placeholder
