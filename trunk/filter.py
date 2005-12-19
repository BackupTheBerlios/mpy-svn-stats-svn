#!/usr/bin/env python2.4

import sys
import re

s = '['
for i in range(32):
    s += chr(i)
s += ']+'

bad = re.compile(s)

for line in sys.stdin:
    print bad.sub('', unicode(line, 'utf-8', 'replace').encode('utf-8'))


