# generation A median scan

def median_low(data):
    values = sorted(data)
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return values[mid - 1]
