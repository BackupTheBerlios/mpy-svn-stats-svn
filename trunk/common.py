"""Common functions / classes used by all modules."""

import datetime

def parse_date(str, type=datetime.datetime):
    try:
        year, month, day, hour, minute, second, microsecond = (0,) * 7
        year = int(str[0:4])
        month = int(str[5:7])
        day = int(str[8:10])
        hour = int(str[11:13])
        minute = int(str[14:16])
        second = int(str[17:19])
#        microsecond = int(str[20:22])
    except IndexError:
        pass
    return type(year, month, day, hour, minute, second)


def ensure_date(s, type=datetime.datetime):
    if isinstance(s, basestr):
        return parse_date(s, type)
    else:
        return s

