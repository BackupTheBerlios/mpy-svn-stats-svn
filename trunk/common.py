"""Common functions / classes used by all modules."""

import datetime

def parse_date(str, type=datetime.datetime):
    try:
        year, month, day, hour, minute, second, microsecond = (1,1,1,0,0,0,0)
        year = int(str[0:4])
        month = int(str[5:7])
        if len(str) > 7:
            day = int(str[8:10])
            hour = int(str[11:13])
            minute = int(str[14:16])
            second = int(str[17:19])
#        microsecond = int(str[20:22])
    except IndexError:
        pass
    try:
        return type(year, month, day, hour, minute, second)
    except ValueError, e:
        print year, month, day, hour, minute, second
        raise e


def ensure_date(s, type=datetime.datetime):
    if isinstance(s, basestr):
        return parse_date(s, type)
    else:
        return s


def make_colors(collection):
    """Create different colors for each values."""
    saturation = 1.0
    brightness = 0.75
    colors = {}
    color_count = len(collection)
    n = 0
    for item in collection:
        
        hue = float(n) / float(color_count)
        n += 1

        assert hue >= 0.0 and hue <= 1.0

        i = int(hue * 6.0)
        f = hue * 6.0 - float(i)
        p = brightness * (1.0 - saturation)
        q = brightness * (1.0 - saturation * f)
        t = brightness * (1.0 - saturation * (1.0 - f))

        o = {
            0: (brightness, t, p),
            1: (q, brightness, p),
            2: (p, brightness, t),
            3: (p, q, brightness),
            4: (t, p, brightness),
            5: (brightness, p, q)
        }

        (r, g, b) = o[i]

        assert r >= 0.0 and r <= 1.0
        assert g >= 0.0 and g <= 1.0
        assert b >= 0.0 and b <= 1.0
        
        colors[item] = (int(r*256.0), int(g*256.0), int(b*256.0))

    return colors

