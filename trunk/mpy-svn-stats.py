#!/usr/bin/python
# -*- coding: ascii -*-

"""
mpy-svn-stats is a simple statistics generator (log analyser) for
Subversion repositories.

It aims to be easy to use, but still provide some interesting information.

It's possible that the profile of the generated stats will promote
rivalisation in the project area.

Usage: mpy-svn-stats [-h] [-o dir] <url>

 -h      --help              - print this help message
 -o      --output-dir        - set output directory
 url - repository url
"""

import sys
import os
import getopt
import time, datetime
import xml.dom
from xml.dom.minidom import parseString

# conditional imports
try:
    import Image, ImageDraw
    _have_pil = True
except:
    _have_pil = False
    print >>sys.stderr, "importing Python Imaging Library failed; get http://www.pythonware.com/library/index.htm"

def main(argv):
    config = Config(argv)
    if config.is_not_good(): return config.usage()
    if config.want_help(): return config.show_help()
    if config.is_not_good(): raise "Unexpected error in configuration!"

    data = get_data(config)
    stats = generate_stats(config, data)
    output_stats(config, stats)

def get_data(config):
    """Get the analysis source data.
    """
    svn_binary = config.get_svn_binary()
    svn_repository = config.get_repository_url()
    assert(svn_binary)
    assert(svn_repository)
    command = '%s -v --xml log %s' % (svn_binary, svn_repository)
    print 'running command: "%s"' % command
    f = os.popen(command)
    xml_data = f.read()
    w = f.close()
    if w is not None:
        raise 'errors'
    return xml_data    

def generate_stats(config, data):
    try:
        dom = parseString(data)
    except Exception, x:
        print "failed to parse:\n%s\n" % data
        raise x
    return Stats(config, dom)

def output_stats(config, stats):
    output_dir = config.get_output_dir()
    f = file(output_dir + '/index.html', "w")
    f.write("""
        <!DOCTYPE html 
            PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
        <title>%(title)s</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <style type="text/css">

            body, td { font-size: 12pt }
        
            table.statistic {
                width: 80%%;
                margin-left: 10%%;
                margin-top: 10%%;
            }

            table.statistic tr td {
                border-style: solid;
                border-width: 1px;
                border-color: black;
                text-align: center;
            }

            table.statistic tr th {
                border-style: solid;
                border-width: 2px;
                border-color: black;
                background-color: lightgray;
            }

            p.foot {
                font-size: 75%%;
                text-align: center;
            }

            h1,h2,th,caption {
                font-family: Arial;
            }

            h1,h2 {
                text-align: center;
                background: lightgray;
                font-style: italic;
            }
        </style>
        </head>
        <body>
            <h1>%(title)s</h1>
        """ % {'title':'Stats for %s' % config.get_repository_url()})

    for statistic in stats:
        print """ writing "%s" """ % statistic.title()
        if isinstance(statistic, TableStatistic):
            f.write(
            """
            <table class="statistic">
                <caption>%(caption)s</caption>
            """ % {'caption': statistic.title()})
            if statistic.show_th():
                f.write("<tr>");
                if statistic.show_numbers(): f.write("<th></th>")
                for n in statistic.column_names(): f.write("<th>%s</th>\n" % n)
                f.write("</tr>\n")
            row_number = 0
            for row in statistic.rows():
                row_number += 1
                f.write("<tr>")
                if statistic.show_numbers(): f.write("<td>%d</td>\n" % row_number)
                for item in row: f.write("<td>%s</td>\n" % item)
                f.write("</tr>\n");
            f.write("""</table>""")
        elif isinstance(statistic, GraphStatistic):
            g = GraphImageWriter(config, 'abc', statistic)

    f.write("<hr/><p class='foot'>Generated by mpy-svn-stats at %s</p>" % str(datetime.datetime.now().ctime()))
    f.write("</body></html>");
        

class Config:
    def __init__(self, argv):
        self._argv = argv
        self._broken = False
        self._repository = None
        self._want_help = False
        self._error_message = None
        self._generate_all = True
        self._stats_to_generate = []
        self._svn_binary = 'svn'
        self._output_dir = 'mpy-svn-stats'

        try:
            optlist, args = getopt.getopt(argv[1:], 'ho:', ['help', 'output-dir='])
        except getopt.GetoptError, e:
            self._broken = True
            self._error_message = str(e)
            return None
        print "optlist: %s" % str(optlist)
        print "args: %s" % str(args)
        optdict = {}
        for k,v in optlist: optdict[k] = v
#        print "optdict: %s" % str(optdict)
        if optdict.has_key('-h') or optdict.has_key('--help'):
            self._want_help = True
            return None
        if len(args) != 1:
            self._broken = True
            self._repository = None
            return None

        self._repository = args[0]

        for key,value in optlist:
            if key == '-o': self._output_dir = value
            elif key == '--output-dir': self._output_dir = value
        

    def is_not_good(self):
        return self._broken

    def usage(self):
        if self._error_message is not None: print >>sys.stderr, 'Error: %s' % self._error_message
        print >>sys.stderr, 'Usage: %s [params] <repository-url>' % (self._argv[0])
        print >>sys.stderr, 'Use %s --help to get help.' % (self._argv[0])
        return -1

    def get_repository_url(self):
        return self._repository

    def get_svn_binary(self):
        return self._svn_binary

    def get_output_dir(self):
        return self._output_dir

    def want_statistic(self, type):
        """Test wherher statistic of type type is wanted.
        """
        if self._generate_all: return True
        else: return type in self._stats_to_generate

    def want_help(self):
        return self._want_help

    def show_help(self):
        print __doc__
        return None

class Stats:
    """General statistics container.
    Has stats items and implements a few
    methods.
    Purpose: store generated statistics ready
    to be output, but do not contain any
    information about presentation (so
    it is possible to use different output
    mediums).
    """
    def __init__(self, config, dom):
        self._statistics = []
        revisions = RevisionData(dom)
        if config.want_statistic('authors_by_commits'):
            self._statistics.append(AuthorsByCommits(config, revisions))
        if config.want_statistic('commits_by_time') and _have_pil:
            self._statistics.append(CommitsByTimeGraphStatistic(config, revisions))
        print "have %d revisions" % len(revisions)

    def __len__(self):
        len(self._statistics)

    def __getitem__(self, index):
        if not isinstance(index, int): raise TypeError('Int expected!')
        if index >= len(self._statistics): raise IndexError()
        return self._statistics[index]

class Statistic:
    """Abstract class for Stats' elements.
    """
    def __init__(self, title):
        self._title = title
        pass

    def title(self):
        assert(isinstance(self._title, str), 'Title of the statistic must be specified!')
        return self._title


class TableStatistic(Statistic):
    """A statistic that is presented as a table.
    """
    def __init__(self, title):
        Statistic.__init__(self, title)
    
    def rows(self):
        return self._data

    def show_numbers(self):
        return True

    def show_th(self):
        return True

class AuthorsByCommits(TableStatistic):
    """Specific statistic - show table author -> commit count sorted
    by commit count.
    """
    def __init__(self, config, revision_data):
        """Generate statistics out of revision data.
        """
        TableStatistic.__init__(self, 'Authors by total number of commits')
        assert(isinstance(revision_data, RevisionData))

        abc = {}

        for rv in revision_data.get_revisions():
            author = rv.get_author()
            if not abc.has_key(author): abc[author] = 1
            else: abc[author] += 1

        data = [(a, abc[a]) for a in abc.keys()]
        data.sort(lambda x,y: cmp(x[1], y[1]))

        self._data = data

    def column_names(self):
        return ('Author', 'Total number of commits')

class GraphStatistic(Statistic):
    """This stats are presented as a graph.
    """
    def __init__(self, title):
        Statistic.__init__(self, title)

    def keys(self):
        return self._keys

    def __getitem__(self, key):
        return self._data[key]

    def get_x_range(self):
        return (self._min_x, self._max_x)

    def get_y_range(self):
        return (self._min_y, self._max_y)

class CommitsByTimeGraphStatistic(GraphStatistic):
    """Show function f(time) -> commits by that time.
    """
    def __init__(self, config, revision_data):
        assert(isinstance(revision_data, RevisionData))
        GraphStatistic.__init__(self, 'Commits by time')
        self._revision_data = revision_data
        self._config = config

        data = {}
        count = 0
        date_min = 0
        date_max = 0
        first = True
        for rv in revision_data.values():
            count += 1
            # this goes in chronological order
            date = rv.get_date()
            data[date] = count

            if first:
                date_min = date
                date_max = date
                first = False
            else:
                if date < date_min: date_min = date
                elif date > date_max: date_max = date

        print "min date: %f" % date_min
        print "max date: %f" % date_max

        self._min_y = float(0)
        self._max_y = float(count)
        self._min_x = float(date_min)
        self._max_x = float(date_max)
        self._data = data
        self._keys = data.keys()
        self._keys.sort()


class GraphImageWriter:
    """A class that writes graphs to image files.
    Basically, a GraphStatistic contains data that
    make possible to draw a graph.
    That is: axis max, axis min, axis label,
    argument -> value pairs that define function.
    Also it may contain type in future releases.
    Now, lets just draw plots.
    """
    def __init__(self, config, name, graph_stats):
        """Initialise instance. Name will be used for
        image filename."""
        assert(isinstance(graph_stats, GraphStatistic))
        assert(_have_pil)
        self._stats = graph_stats
        self._config = config
        self.write_image()

    def write_image(self):
        """Do calculations, write image.
        """
        im = Image.new('RGB', (800,600), 'white')

        first = True
        min_x, max_x = self._stats.get_x_range()
        min_y, max_y = self._stats.get_y_range()
        last_x = last_y = 0.0
        cur_x = cur_y = 0.0

        draw = ImageDraw.Draw(im)

        print "x range: %f %f" % (min_x, max_x)
        

        for k in self._stats.keys():
            v = self._stats[k]
            print "k,v: %f %f" % (k,v)
            if not first:
                cur_x = float((k - min_x) / (max_x - min_x))
                cur_y = float((v - min_y) / (max_y - min_y))

                px1 = last_x * float(im.size[0])
                py1 = float(im.size[1]) - last_y * float(im.size[1])

                px2 = cur_x * float(im.size[0])
                py2 = float(im.size[1]) - cur_y * float(im.size[1])

                draw.line( (px1, py1, px2, py2), 'black')
                print "line: %f %f -> %f %f" % (px1, py1, px2, py2)
        
            last_x = float(cur_x)
            last_y = float(cur_y)
            first = False

        del draw
        im.save(self._config.get_output_dir() + '/graph.png')
        


class RevisionData:
    """Data about all revisions."""
    def __init__(self, dom):
        """Create revision data from xml.dom.Document."""

        log = dom.childNodes[0]
        revisions = []

        for logentry in log.childNodes:
            if logentry.nodeType != logentry.ELEMENT_NODE: continue
            if logentry.nodeType == logentry.ELEMENT_NODE and logentry.nodeName != 'logentry':
                raise '%s found, logentry expected' % str(logentry)

            revisions.append(RevisionInfo(logentry))
        self._revisions = revisions
        self._revisions_by_keys = {}
        for rv in self._revisions:
            self._revisions_by_keys[rv.get_revision_number()] = rv

        self._revisions_keys = self._revisions_by_keys.keys().sort()
        self._revisions.sort(lambda r1,r2: cmp(r1.get_revision_number(), r2.get_revision_number()))

    def get_revision(self, number):
        return self._revisions_by_keys[number]

    def __len__(self):
        return len(self._revisions)

    def __getitem__(self, index):
        return self._revisions_by_keys(index)

    def keys(self):
        return self._revisions_keys

    def get_revisions(self):
        return self._revisions

    def values(self):
        return self.get_revisions()

class RevisionInfo:
    def __init__(self, message): 
        self._modified_paths = []
        self._parse_message(message)
        self._have_diffs = 0
        self._diffs = []

    def get_author(self):
        return self._author

    def get_revision_number(self):
        return self._revision_number

    def get_modified_paths(self):
        return self._modified_paths

    def get_date(self):
        return self._date

    def _parse_message(self, message):
        assert(isinstance(message, xml.dom.Node))
        self._author = self._parse_author(message)
        self._revision_number = self._parse_revision_number(message)
        self._modified_paths = self._parse_paths(message)
        self._date = self._parse_date(message)

    def _parse_author(self, message):
        a = message.getElementsByTagName('author')
        assert(len(a) == 1)
        a[0].normalize()
        assert(len(a[0].childNodes) == 1)
        return a[0].childNodes[0].data

    def _parse_revision_number(self, message):
        return int(message.getAttribute('revision'))

    def _parse_paths(self, message):
        path_nodes = message.getElementsByTagName('path')
        modified_paths = []
        for path_node in path_nodes:
            path_node.normalize()
            action = path_node.getAttribute('action')
            path = self._get_element_contents(path_node)
            modified_paths.append(ModifiedPath(action, path))
        return modified_paths

    def _parse_date(self, message):

        date_element = message.getElementsByTagName('date')[0]
        isodate = self._get_element_contents(date_element)
        return time.mktime(time.strptime(isodate[:19], '%Y-%m-%dT%H:%M:%S'))

    def _get_element_contents(self, node):
        assert(isinstance(node, xml.dom.Node))
        children = node.childNodes
        contents = ''
        for child in children:
            if child.nodeType == child.TEXT_NODE:
                contents += child.data
        return contents

    def get_revision_number(self):
        return self._revision_number

def cool_revisions_authors(revisions):
    """Get authors of cool revisions.
    """
    r_to_a = {}
    for rv in revisions:
        n = rv.get_revision_number()
        if not is_number_cool(n): continue
        else: r_to_a[n] = rv.get_author()

    return r_to_a
    

class ModifiedPath:
    def __init__(self, action, path):
        assert(isinstance(action, str) and len(action) == 1,
            'should be one-letter string, is: %s' % str(action))
        assert(isinstance(path, str), 'should be modified path, is: %s' % str(path))
        self._action = action
        self._path = path

    def get_action(self):
        return self._action

    def get_path(self):
        return self._path



if __name__ == '__main__':
    main(sys.argv) 
#   make_stats(svn_binary=svn_binary, svn_repository=svn_repository) 
