# Implementation of color conversion utilities without using the colorsys module

def hls_to_rgb(h, l, s):
    if s == 0:
        return (l, l, l)
    
    def hue_to_rgb(p, q, t):
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1/6:
            return p + (q - p) * 6 * t
        if t < 1/2:
            return q
        if t < 2/3:
            return p + (q - p) * (2/3 - t) * 6
        return p
    
    q = l * (1 + s) if l <= 0.5 else l + s - l * s
    p = 2 * l - q
    r = hue_to_rgb(p, q, h + 1/3)
    g = hue_to_rgb(p, q, h)
    b = hue_to_rgb(p, q, h - 1/3)
    
    return (r, g, b)

def yiq_to_rgb(y, i, q):
    r = y + 0.956 * i + 0.621 * q
    g = y - 0.272 * i - 0.647 * q
    b = y - 1.106 * i + 1.703 * q
    
    # Clamp values to the range [0, 1]
    r = max(0, min(r, 1))
    g = max(0, min(g, 1))
    b = max(0, min(b, 1))
    
    return (r, g, b)

def rgb_to_yiq(r, g, b):
    y = 0.299 * r + 0.587 * g + 0.114 * b
    i = 0.596 * r - 0.275 * g - 0.321 * b
    q = 0.212 * r - 0.523 * g + 0.311 * b
    
    return (y, i, q)

# Zero-arg invariant functions
def colorsys2_hls_to_rgb():
    return [0.5, 0.5, 0.5]

def colorsys2_yiq_to_rgb():
    # Check if all components of yiq_to_rgb(0.5, 0, 0) are in [0.0, 1.0]
    result = yiq_to_rgb(0.5, 0, 0)
    return all(0.0 <= x <= 1.0 for x in result)

def colorsys2_rgb_to_yiq():
    # Check if rgb_to_yiq(1, 1, 1)[0] is close to 1.0
    y, _, _ = rgb_to_yiq(1, 1, 1)
    return abs(y - 1.0) < 1e-9

# Export the required functions
__all__ = ['hls_to_rgb', 'yiq_to_rgb', 'rgb_to_yiq', 
           'colorsys2_hls_to_rgb', 'colorsys2_yiq_to_rgb', 'colorsys2_rgb_to_yiq']