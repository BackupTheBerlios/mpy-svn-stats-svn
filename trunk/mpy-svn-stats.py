#!/usr/bin/python
# -*- coding: ascii -*-

"""
mpy-svn-stats is a simple statistics generator (log analyser) for
Subversion repositories.

It aims to be easy to use, but still provide some interesting information.

It's possible that the profile of the generated stats will promote
rivalisation in the project area.

Usage: mpy-svn-stats [-h] <url>

 -h      --help              - print this help message
 -o      --output-dir        - set output directory
 url - repository url
"""

import xml.dom
import os
import datetime
import sys
import getopt
from xml.dom.minidom import parseString

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
        <html><head><title>%(title)s</title>
        <body>
            <h1>%(title)s</h1>
        """ % {'title':'mpy-svn-stats for a repository'})

    for statistic in stats:
        print """ writing "%s" """ % statistic.title()
        if isinstance(statistic, TableStatistic):
            f.write("""<table><caption>%(caption)s</caption>""" % {'caption': statistic.title()})
            row_number = 0
            for row in statistic.rows():
                row_number += 1
                f.write("<tr>")
                if statistic.show_numbers(): f.write("<td>%d</td>\n" % row_number)
                for item in row: f.write("<td>%s</td>\n" % item)
                f.write("</tr>\n");
            f.write("""</table>""")

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
            optlist, args = getopt.getopt(argv[1:], 'ho:', ['help', 'output-dir'])
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

        


def is_number_cool(number):
    if number in [666, 69, 128, 256, 512, 1024]: return True
    if number in range(25, 76, 25): return True
    if number in range(100, 451, 50): return True
    if number in range(500, 2001, 100): return True
    return False

def make_stats(svn_repository, svn_binary='svn'):

    author_commits = {}

    for rv in revisions:
        author = rv.get_author()
        if author_commits.has_key(author):
            author_commits[author] += 1
        else:
            author_commits[author] = 1


    author_paths = {}
    for rv in revisions:
        author = rv.get_author()
        path_count = len(rv.get_modified_paths())
        if author_paths.has_key(author):
            author_paths[author] += path_count
        else:
            author_paths[author] = path_count

    print_head(svn_repository)
    print_sorted('Authors sorted by commit count', author_commits, key_name='author',
        value_name='commits')
    print_sorted('Authors sorted by total number of modified paths', author_paths,
        key_name='author',
        value_name='changed paths')

    print_sorted_by_keys('Cool revision numbers authors',
        cool_revisions_authors(revisions),
        key_name='revision number',
        value_name='author')
    print_foot()

def print_head(svn_repository):
    print """<html><head><title>Stats for %s</title>
    <style type="text/css">
        table tr td, table tr th {
            padding-left: 20px;
            padding-right: 20px;
            border: 1px solid gray;
            font-family: monospace;
        }

        table tr th {
            font-size: 110%%;
            font-weight: bold;
        }

        table caption {
            font-family: monospace;
            font-weight: bold;
            background-color: lightgray;
        }

        table {
            margin-left: 10%%;
            margin-right: 10%%;
            width: 70%%;
        }

        td.key {
            width: 50%%;
        }

        td.value {
            width: 50%%;
        }

        h1, h2 {
            font-family: Arial;
        }

        p.meta {
            font-family: monospace;
        }
    </style>
    </head><body>
    <h1>Stats for %s</h1>
    <p class="meta">Generated: %s</p>
    """ % (
        svn_repository,
        svn_repository,
        datetime.datetime.now().ctime())
        

def print_foot():
    print """</body></html>"""
    
def print_sorted(caption, dict, **kw):
    assert(isinstance(caption, str))

    keys = dict.keys()
    keys.sort(lambda a,b: cmp(dict[b], dict[a]))

    print """<table><caption>%(caption)s</caption>\n""" % {'caption': caption}
    if kw.has_key('key_name') or kw.has_key('value_name'):
        print """<tr><th class="key_name">%s</th><th class="value_name">%s</th></tr>""" % (
            kw.get('key_name', ''),
            kw.get('value_name', ''))
    for key in keys:
        print """<tr>
        <td class="key">%s</td>
        <td class="value">%s</td>
        </tr>\n""" % (key, dict[key])
    print """</table>\n\n"""

def print_sorted_by_keys(caption, data, key_name=None, value_name=None):
    print_table_head(caption, key_name=None, value_name=None)
    keys = data.keys()
    keys.sort()
    for key in keys:
        print_table_row(key, data[key])
    print_table_foot()

def print_table_head(caption, **kw):
    print """<table><caption>%(caption)s</caption>\n""" % {'caption': caption}
    if kw.has_key('key_name') or kw.has_key('value_name'):
        print """<tr><th class="key_name">%s</th><th class="value_name">%s</th></tr>""" % (
            kw.get('key_name', ''),
            kw.get('value_name', ''))

def print_table_foot():
    print """</table>\n\n"""
    
def print_table_row(key, value):
        print """<tr>
        <td class="key">%s</td>
        <td class="value">%s</td>
        </tr>\n""" % (key, value)

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

    def get_revision(self, number):
        return self._revisions_by_keys[number]

    def __len__(self):
        return len(self._revisions)

    def __getitem__(self, index):
        return self._revisions_by_keys(index)

    def keys(self):
        return self._revisions_by_keys.keys()

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

    def _parse_message(self, message):
        assert(isinstance(message, xml.dom.Node))
        self._author = self._parse_author(message)
        self._revision_number = self._parse_revision_number(message)
        self._modified_paths = self._parse_paths(message)

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