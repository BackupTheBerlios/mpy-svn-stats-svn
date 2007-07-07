#!/usr/bin/env python2.5
# coding: utf-8

import os, sys, time, string
import datetime
import common
from cStringIO import StringIO
from textwrap import dedent


def template(s, d=None):
    s = dedent(s.strip() + '\n')
    if d:
        return string.Template(s).substitute(d)
    else:
        return s

def tonumber(x):
    if isinstance(x, datetime.datetime):
        return tonumber(x - datetime.datetime(1, 1, 1, 0, 0, 0))
    elif isinstance(x, datetime.timedelta):
        return x.days * 3600 * 24 + x.seconds + x.microseconds / 1000000.0
    elif isinstance(x, (int, long, float)):
        return float(x)


class Graph:

    static_graph_count = 0

    def __init__(self, width=900, height=400,
            margin=20,
            ox_axis_title='',
            oy_axis_title=''):
        self.width = float(width)
        self.height = float(height)
        self.margin = float(margin)
        self.ox_axis_title = ox_axis_title
        self.oy_axis_title = oy_axis_title
        self.series_colors = {}
        self.data = {}
        self.series = set()
        self.local_graph_id = Graph.static_graph_count
        Graph.static_graph_count += 1

    def add_series(self, series_name):
        self.series.add(series_name)

    def add_value(self, series_name, key, value):
        assert series_name in self.series, Exception("unknown series name: %s" % series_name)
        self.data[(series_name, key)] = value

    def render_to_stream(self, stream, standalone=False):
        if standalone:
            stream.write('''\
                <?xml version="1.0" encoding="utf-8"?>
                <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
                         "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
            ''')
        stream.write(template('''\
            <svg:svg
                xmlns:svg="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                width="$width" height="$height" version="1.1">
        ''', {'width': self.width, 'height': self.height}))

        self.render_axes(stream)

        for series_name in self.series:
            self.render_series(stream, series_name)

        stream.write(template('''
            </svg:svg>
        '''))

    def render_series(self, stream, series_name):
        points = self.get_points_by_series_name(series_name)
#        stream.write(template("""
#            <polyline id="line" style="stroke: $series_color; stroke-width: 1.234; fill: none"
#        """, {'series_color': self.get_series_color(series_name)}))
        stream.write("""\
            <svg:defs>
                <svg:path id="path_%(graph_id)d_%(series_name)s"
                        fill="none" stroke="%(series_color)s" 
                        stroke-width="1.5"
            """  % {'graph_id': self.local_graph_id,
                'series_name': series_name,
                'series_color': self.get_series_color(series_name)})
        stream.write('d="\n')
        def point_to_pixel(p):
            x = p[0] * (self.width - self.margin * 2) + self.margin
            y = self.height - p[1] * (self.height - self.margin * 2) - self.margin
            return "%.2f %.2f" % (x,y)
        points_str = '\n'.join(
                    "%s %s" % (('M' if n==0 else 'L'), point_to_pixel(p))
                    for n,p in enumerate(points))
        stream.write(points_str)
        stream.write('"/>\n')
        stream.write('</svg:defs>\n');

        stream.write("""<svg:use xlink:href="#path_%(graph_id)d_%(series_name)s"/>""" % {
                'graph_id': self.local_graph_id,
                'series_name': series_name,
                'series_title': series_name})

        stream.write("""
                <svg:text font-family="Deja Vu Sans, Arial"
                        font-size="8pt"
                        fill="black"
                        dy="-1pt">
                    <svg:textPath
                        xlink:href="#path_%(graph_id)d_%(series_name)s"
                    >%(series_title)s</svg:textPath>
                </svg:text>
            """ % {
                'graph_id': self.local_graph_id,
                'series_name': series_name,
                'series_title': series_name,})

    def get_points_by_series_name(self, series_name):
        dd = [(x[0][1], x[1]) for x in self.data.iteritems() if x[0][0] == series_name]
        def point_key(point):
            return point[0]
        dd.sort(key=point_key)
        min, max = self.get_min_max()

        def pos(d):
            p = [None, None]
            for i in range(2):
                try:
                    p[i] = tonumber(d[i] - min[i]) / tonumber(max[i] - min[i])
                except (ZeroDivisionError, TypeError), e:
                    print 'self.data: ', repr(self.data)
                    print 'i: %s' % i
                    print 'd: ', repr(d)
                    print 'min: %s' % repr(min)
                    print 'max: %s' % repr(max)
                    raise e
            return p
        pts = [pos(d) for d in dd]
        return pts

    def get_min_max(self):
        minx, maxx, miny, maxy = [None] * 4

        def fnotnone(a, b, f):
            if a is None: return b
            elif b is None: return a
            else:
                return f(a, b)

        def notnonemin(a, b): return fnotnone(a, b, min)
        def notnonemax(a, b): return fnotnone(a, b, max)

        for k,v in self.data.iteritems():
            minx = notnonemin(minx, k[1])
            maxx = notnonemax(maxx, k[1])
            miny = notnonemin(miny, v)
            maxy = notnonemax(maxy, v)

        return ((minx, miny),(maxx, maxy))

    def render_axes(self, stream):
        sl = 10
        sw = 3
        oo = (self.margin, self.height - self.margin)
        ox = (self.width - self.margin, self.height - self.margin)
        oy = (self.margin, self.margin)
        ox1 = (ox[0] - sl, ox[1] - sw)
        ox2 = (ox[0] - sl, ox[1] + sw)
        oy1 = (oy[0] - sw, oy[1] + sl)
        oy2 = (oy[0] + sw, oy[1] + sl)

        self.svg_line(stream, (oo, ox), 'stroke-width: 1; stroke: black')
        self.svg_line(stream, (ox, ox1), 'stroke-width: 1; stroke: black')
        self.svg_line(stream, (ox, ox2), 'stroke-width: 1; stroke: black')
        self.svg_line(stream, (oo, oy), 'stroke-width: 1; stroke: black')
        self.svg_line(stream, (oy, oy1), 'stroke-width: 1; stroke: black')
        self.svg_line(stream, (oy, oy2), 'stroke-width: 1; stroke: black')

        if self.ox_axis_title:
            x = self.width - self.margin
            y = self.height - self.margin
            style="text-anchor: end"
            text = self.ox_axis_title
            stream.write(template('''
                <svg:text x="$x" y="$y" dy="11pt" style="$style">$text</svg:text>
            ''', {
                'x': x,
                'y': y,
                'text': text,
                'style': style
            }))

        if self.ox_axis_title:
            x = self.margin
            y = self.margin
            style="text-anchor: end"
            text = self.oy_axis_title
            stream.write(template('''
                <svg:g transform="translate($x, $y), rotate(-90)">
                    <svg:text dy="-4pt" style="$style"
                    >$text</svg:text>
                </svg:g>
            ''', {
                'x': x,
                'y': y,
                'text': text,
                'style': style
            }))

    def svg_line(self, stream, p, style='stoke:'):
        assert len(p) == 2
        stream.write(template('''
            <svg:line x1="$x1" y1="$y1" x2="$x2" y2="$y2" style="$style"/>
        ''', {
            'x1': p[0][0],
            'y1': p[0][1],
            'x2': p[1][0],
            'y2': p[1][1],
            'style': style,
        }))

    def svg_text(self, stream, text, x, y, style=''):
        stream.write(template('''
            <svg:text x="$x" y="$y" style="$style">$text</svg:text>
        ''', {
            'x': x,
            'y': y,
            'text': text,
            'style': style
        }))

    def get_series_color(self, series_name):
        return self.series_colors.get(series_name, 'black')

    def randomize_series_colors(self):
        colors = common.make_colors(self.series)
        for name, color in colors.iteritems():
            assert len(color) == 3
            svg_color = "#%02x%02x%02x" % tuple(color)
            self.series_colors[name] = svg_color


def main():
    d = Graph()
    d.ox_axis_title = 'Date'
    d.oy_axis_title = 'Number'
    d.add_series('sample')
    d.series_colors['sample'] = 'red'
    d.add_value('sample', datetime.datetime(2007,  1,  1,  0,  0,  0),  0)
    d.add_value('sample', datetime.datetime(2007,  1,  8,  0,  0,  0), 10)
    d.add_value('sample', datetime.datetime(2007,  1, 15,  0,  0,  0), 12)
    d.add_value('sample', datetime.datetime(2007,  1, 16,  0,  0,  0), 12.001)
    d.add_series('foo')
    d.add_value('foo', datetime.datetime(2007,  1,  1,  0, 0, 0), 7)
    d.add_value('foo', datetime.datetime(2007,  1, 10,  8, 0, 0), 7.1)
    d.add_value('foo', datetime.datetime(2007,  1, 10,  9, 0, 0), 2)
    d.add_value('foo', datetime.datetime(2007,  1, 10, 10, 0, 0), 6.9)
    d.add_value('foo', datetime.datetime(2007,  1, 20, 00, 0, 0), 7.666)
    d.render_to_stream(file('svgtest.xhtml', 'w'))


if __name__ == '__main__':
    main()
