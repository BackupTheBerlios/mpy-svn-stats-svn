#!/usr/bin/env python
# -*- coding: ascii -*-

def is_cool_number(number):
    """Function return true if numer is cool ;)
    """
    from math import log
    assert isinstance(number, int)
    tmp=int(log(number, 2))
    if 2**tmp==number:
        return True
    string=str(number)
    dict={}
    for i in string:
        dict[i]=i
    if len(dict)==1 and number>9:
        return True
    elif number > 99 and int(string[1:])==0:
        return True
    return False

if __name__ == '__main__':
    raise
