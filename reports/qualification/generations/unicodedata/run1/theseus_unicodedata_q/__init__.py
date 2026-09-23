# generation A name scan

def name(character):
    if len(character) != 1:
        raise TypeError("name() argument must be a single character string")
    ch = character
    if "A" <= ch <= "Z":
        return "LATIN CAPITAL LETTER " + ch
    raise ValueError("no such name")
