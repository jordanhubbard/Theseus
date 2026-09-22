# generation A capwords split

def capwords(s, sep=None):
    return (sep or ' ').join(x.capitalize() for x in s.split(sep))
