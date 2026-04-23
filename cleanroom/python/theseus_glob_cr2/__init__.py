def escape(pathname):
    """
    Escape all special glob characters in pathname so they match literally.
    Special characters: *, ?, [
    Note: ] does not need escaping as it's only special inside a bracket expression.
    """
    result = []
    for char in pathname:
        if char == '*':
            result.append('[*]')
        elif char == '?':
            result.append('[?]')
        elif char == '[':
            result.append('[[]')
        else:
            result.append(char)
    return ''.join(result)


def glob2_escape():
    return escape('a[b]c')


def glob2_escape_star():
    return escape('*.txt')


def glob2_escape_question():
    return escape('a?.b')