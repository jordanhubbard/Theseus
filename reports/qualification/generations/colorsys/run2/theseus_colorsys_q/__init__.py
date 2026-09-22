# generation B convert class


class _Convert:
    @staticmethod
    def rgb_to_hsv(r, g, b):
        maximum = max(r, g, b)
        minimum = min(r, g, b)
        value = maximum
        if minimum == maximum:
            return 0.0, 0.0, value

        difference = maximum - minimum
        saturation = difference / maximum
        red_distance = (maximum - r) / difference
        green_distance = (maximum - g) / difference
        blue_distance = (maximum - b) / difference
        if r == maximum:
            hue = blue_distance - green_distance
        elif g == maximum:
            hue = 2.0 + red_distance - blue_distance
        else:
            hue = 4.0 + green_distance - red_distance
        hue = (hue / 6.0) % 1.0
        return hue, saturation, value

    @staticmethod
    def hsv_to_rgb(h, s, v):
        if s == 0.0:
            return v, v, v

        sector_value = h * 6.0
        sector = int(sector_value)
        fraction = sector_value - sector
        pale = v * (1.0 - s)
        falling = v * (1.0 - s * fraction)
        rising = v * (1.0 - s * (1.0 - fraction))
        sector %= 6
        if sector == 0:
            return v, rising, pale
        if sector == 1:
            return falling, v, pale
        if sector == 2:
            return pale, v, rising
        if sector == 3:
            return pale, falling, v
        if sector == 4:
            return rising, pale, v
        return v, pale, falling

    @staticmethod
    def rgb_to_hls(r, g, b):
        maximum = max(r, g, b)
        minimum = min(r, g, b)
        lightness = (minimum + maximum) / 2.0
        if minimum == maximum:
            return 0.0, lightness, 0.0

        difference = maximum - minimum
        if lightness <= 0.5:
            saturation = difference / (maximum + minimum)
        else:
            saturation = difference / (2.0 - maximum - minimum)

        red_distance = (maximum - r) / difference
        green_distance = (maximum - g) / difference
        blue_distance = (maximum - b) / difference
        if r == maximum:
            hue = blue_distance - green_distance
        elif g == maximum:
            hue = 2.0 + red_distance - blue_distance
        else:
            hue = 4.0 + green_distance - red_distance
        hue = (hue / 6.0) % 1.0
        return hue, lightness, saturation

    @staticmethod
    def _hls_value(low, high, hue):
        hue %= 1.0
        if hue < 1.0 / 6.0:
            return low + (high - low) * hue * 6.0
        if hue < 0.5:
            return high
        if hue < 2.0 / 3.0:
            return low + (high - low) * (2.0 / 3.0 - hue) * 6.0
        return low

    @classmethod
    def hls_to_rgb(cls, h, l, s):
        if s == 0.0:
            return l, l, l
        if l <= 0.5:
            high = l * (1.0 + s)
        else:
            high = l + s - l * s
        low = 2.0 * l - high
        return (
            cls._hls_value(low, high, h + 1.0 / 3.0),
            cls._hls_value(low, high, h),
            cls._hls_value(low, high, h - 1.0 / 3.0),
        )

    @staticmethod
    def rgb_to_yiq(r, g, b):
        y = 0.30 * r + 0.59 * g + 0.11 * b
        i = 0.74 * (r - y) - 0.27 * (b - y)
        q = 0.48 * (r - y) + 0.41 * (b - y)
        return y, i, q

    @staticmethod
    def yiq_to_rgb(y, i, q):
        r = y + 0.9468822170900693 * i + 0.6235565819861433 * q
        g = y - 0.27478764629897834 * i - 0.6356910791873801 * q
        b = y - 1.1085450346420322 * i + 1.7090069284064666 * q
        return (
            min(max(r, 0.0), 1.0),
            min(max(g, 0.0), 1.0),
            min(max(b, 0.0), 1.0),
        )


def rgb_to_hsv(r, g, b):
    return _Convert.rgb_to_hsv(r, g, b)


def hsv_to_rgb(h, s, v):
    return _Convert.hsv_to_rgb(h, s, v)


def rgb_to_hls(r, g, b):
    return _Convert.rgb_to_hls(r, g, b)


def hls_to_rgb(h, l, s):
    return _Convert.hls_to_rgb(h, l, s)


def rgb_to_yiq(r, g, b):
    return _Convert.rgb_to_yiq(r, g, b)


def yiq_to_rgb(y, i, q):
    return _Convert.yiq_to_rgb(y, i, q)
