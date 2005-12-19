#!/usr/bin/env python

import msvnstats
import unittest
import datetime
import time

class TimeSpanLabelsTest(unittest.TestCase):

    def test01(self):
        start = datetime.datetime(2004, 01, 01)
        end = datetime.datetime(2004, 12, 01)
        
        labels = msvnstats.labels_for_time_span(start, end)
        self.assert_(len(labels) >= 10, len(labels))

    def test02(self):
        start = datetime.datetime(2004, 1, 1)
        end = datetime.datetime(2005, 12, 23)

        labels = msvnstats.labels_for_time_span(start, end)

        times = labels.keys()
        times.sort()

        min_time = times[0]

        self.assertEqual(min_time, start)

    def test03(self):
        start = datetime.datetime(1993, 12, 31, 23, 8)
        end = datetime.datetime(2005, 04, 23, 13, 13)
        (first,all) = self._get_first_date(start, end)
        self.assertEqual(first, datetime.datetime(1994, 1, 1))

    def _get_first_date(self, start, end):
        labels = msvnstats.labels_for_time_span(start, end)

        times = labels.keys()
        times.sort()

        min_time = times[0]

        return (min_time, labels)

    def test04(self):
        labels = msvnstats.labels_for_time_span(
            datetime.datetime(1990,  1, 1),
            datetime.datetime(1990, 12, 1))

        for month in range(1, 12):
            d = datetime.datetime(1990, month, 1)
            self.assert_(d in labels.keys())

if __name__ == '__main__':
    unittest.main()
