# generation A heap scan


def nlargest(n, iterable):
    if n <= 0:
        return []
    items = list(iterable)
    items.sort(reverse=True)
    return items[:n]
