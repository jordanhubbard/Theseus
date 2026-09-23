# generation A escape scan

def escape(pattern):
    parts = []
    for char in pattern:
        o = ord(char)
        if char == '_' or 48 <= o <= 57 or 65 <= o <= 90 or 97 <= o <= 122:
            parts.append(char)
        else:
            parts.append('\\' + char)
    return ''.join(parts)
