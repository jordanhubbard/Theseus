# generation A sign scan

def copysign(x, y):
    x = float(x)
    y = float(y)
    if x < 0.0:
        x = -x
    if y < 0.0:
        x = -x
    return x
