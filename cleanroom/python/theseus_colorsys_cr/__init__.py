"""
theseus_colorsys_cr: Clean-room color system conversion library.
Implements RGB <-> HSV, RGB <-> HLS, RGB <-> YIQ conversions.
"""


def rgb_to_hsv(r, g, b):
    """Convert RGB to Hue-Saturation-Value.
    
    All inputs and outputs are floats in [0.0, 1.0].
    Hue is in [0.0, 1.0] (representing 0-360 degrees).
    """
    maxc = max(r, g, b)
    minc = min(r, g, b)
    v = maxc
    
    if maxc == minc:
        return 0.0, 0.0, v
    
    s = (maxc - minc) / maxc
    rc = (maxc - r) / (maxc - minc)
    gc = (maxc - g) / (maxc - minc)
    bc = (maxc - b) / (maxc - minc)
    
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2.0 + rc - bc
    else:
        h = 4.0 + gc - rc
    
    h = (h / 6.0) % 1.0
    return h, s, v


def hsv_to_rgb(h, s, v):
    """Convert HSV to RGB.
    
    All inputs and outputs are floats in [0.0, 1.0].
    """
    if s == 0.0:
        return v, v, v
    
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    
    if i == 0:
        return v, t, p
    elif i == 1:
        return q, v, p
    elif i == 2:
        return p, v, t
    elif i == 3:
        return p, q, v
    elif i == 4:
        return t, p, v
    elif i == 5:
        return v, p, q
    else:
        return v, t, p


def rgb_to_hls(r, g, b):
    """Convert RGB to Hue-Lightness-Saturation.
    
    All inputs and outputs are floats in [0.0, 1.0].
    Returns (h, l, s).
    """
    maxc = max(r, g, b)
    minc = min(r, g, b)
    
    l = (minc + maxc) / 2.0
    
    if minc == maxc:
        return 0.0, l, 0.0
    
    if l <= 0.5:
        s = (maxc - minc) / (maxc + minc)
    else:
        s = (maxc - minc) / (2.0 - maxc - minc)
    
    rc = (maxc - r) / (maxc - minc)
    gc = (maxc - g) / (maxc - minc)
    bc = (maxc - b) / (maxc - minc)
    
    if r == maxc:
        h = bc - gc
    elif g == maxc:
        h = 2.0 + rc - bc
    else:
        h = 4.0 + gc - rc
    
    h = (h / 6.0) % 1.0
    return h, l, s


def hls_to_rgb(h, l, s):
    """Convert HLS to RGB.
    
    All inputs and outputs are floats in [0.0, 1.0].
    """
    if s == 0.0:
        return l, l, l
    
    if l <= 0.5:
        m2 = l * (1.0 + s)
    else:
        m2 = l + s - l * s
    
    m1 = 2.0 * l - m2
    
    return (_hls_value(m1, m2, h + 1.0/3.0),
            _hls_value(m1, m2, h),
            _hls_value(m1, m2, h - 1.0/3.0))


def _hls_value(m1, m2, hue):
    """Helper for hls_to_rgb."""
    hue = hue % 1.0
    if hue < 1.0/6.0:
        return m1 + (m2 - m1) * hue * 6.0
    if hue < 0.5:
        return m2
    if hue < 2.0/3.0:
        return m1 + (m2 - m1) * (2.0/3.0 - hue) * 6.0
    return m1


def rgb_to_yiq(r, g, b):
    """Convert RGB to YIQ.
    
    Y is in [0.0, 1.0], I is in [-0.596, 0.596], Q is in [-0.523, 0.523].
    """
    y = 0.30 * r + 0.59 * g + 0.11 * b
    i = 0.74 * (r - y) - 0.27 * (b - y)
    q = 0.48 * (r - y) + 0.41 * (b - y)
    return y, i, q


def yiq_to_rgb(y, i, q):
    """Convert YIQ to RGB.
    
    Clamps output to [0.0, 1.0].
    """
    r = y + 0.9468822170900693 * i + 0.6235565819861433 * q
    g = y - 0.27478764629897834 * i - 0.6356910791873801 * q
    b = y - 1.1085450346420322 * i + 1.7090069284064666 * q
    
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    
    return r, g, b


# Invariant verification functions

def colorsys_rgb_to_hsv_red():
    """rgb_to_hsv(1.0, 0.0, 0.0) == (0.0, 1.0, 1.0)"""
    return rgb_to_hsv(1.0, 0.0, 0.0) == (0.0, 1.0, 1.0)


def colorsys_hsv_to_rgb_roundtrip():
    """hsv_to_rgb(*rgb_to_hsv(0.5, 0.2, 0.8)) ≈ (0.5, 0.2, 0.8)"""
    result = hsv_to_rgb(*rgb_to_hsv(0.5, 0.2, 0.8))
    eps = 1e-10
    return (abs(result[0] - 0.5) < eps and
            abs(result[1] - 0.2) < eps and
            abs(result[2] - 0.8) < eps)


def colorsys_rgb_to_hls_white():
    """rgb_to_hls(1.0, 1.0, 1.0)[1] == 1.0 (lightness)"""
    return rgb_to_hls(1.0, 1.0, 1.0)[1]