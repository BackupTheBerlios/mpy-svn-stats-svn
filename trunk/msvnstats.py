#!/usr/bin/env python
# -*- coding: ascii -*-

"""\
mpy-svn-stats is a simple statistics generator (log analyser) for
Subversion repositories.

It aims to be easy to use, but still provide some interesting information.

It's possible that the profile of the generated stats will promote
rivalisation in the project area.

Usage: mpy-svn-stats [-h] [-o dir] <url>

 -h      --help              - print this help message
 -o      --output-dir        - set output directory
         --svn-binary        - use different svn client instead of ``svn''
 url - repository url

Authors: Maciej Pietrzak, Joanna Chmiel, Marcin Mankiewicz
"""

import sys
import os
import time
import getopt
import time, datetime
import xml.dom
import locale
from cgi import escape
from xml.dom.minidom import parseString
from mpyfunctions import *

# conditional imports
try:
    import Image, ImageDraw
    _have_pil = True
except:
    _have_pil = False

def main(argv):
    config = Config(argv)
    if config.is_not_good(): return config.usage()
    if config.want_help(): return config.show_help()

    stats = AllStatistics()
    stats.configure(config)
    xmldata = get_data(config)
    
    run_time_start = time.time()
    
    revision_data = RevisionData(config.get_repository_url(), parseString(xmldata))
    stats.calculate(revision_data)
    
    run_time_end = time.time()
    
    stats.write(run_time=(run_time_end - run_time_start)) 

    print "got %d stats objects" % stats.count_all()
#    stats = generate_stats(config, data)
#    output_stats(config, stats)

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

def _create_output_dir(dir):
    """Create output dir."""
    if not os.path.isdir(dir):
        os.mkdir(dir)
        

class Config:
    def __init__(self, argv):
        self._argv = argv
        self._broken = False
        self._repository = None
        self._want_help = False
        self._error_message = None
        self._svn_binary = 'svn'
        self._output_dir = 'mpy-svn-stats'

        self._enabled_stats = []
        self._disabled_stats = []

        try:
            optlist, args = getopt.getopt(
                argv[1:],
                'ho:e:',
                [
                    'help', 
                    'output-dir=',
                    'svn-binary=',
                    'enable='
                ])
        except getopt.GetoptError, e:
            self._broken = True
            self._error_message = str(e)
            return None
        print "optlist: %s" % str(optlist)
        print "args: %s" % str(args)

        optdict = {}

        for k,v in optlist:
            optdict[k] = v

        if optdict.has_key('-h') or optdict.has_key('--help'):
            self._want_help = True
            return None
        if optdict.has_key('--with-diff-stats'):
            self._stats_to_generate.update('author_by_diff_size')
        if len(args) != 1:
            self._broken = True
            self._repository = None
            return None

        self._repository = args[0]

        for key,value in optlist:
            if key == '-o': self._output_dir = value
            elif key == '--output-dir': self._output_dir = value
            elif key == '--svn-binary': self._svn_binary = value
        

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


class Statistic:
    """Abstract class for Stats' elements.
    """

    wanted_by_default = True
    requires_graphics = False
    
    def __init__(self, name, title):
        assert isinstance(name, basestring), ValueError("name must be a string")
        assert isinstance(title, basestring), ValueError("title must be a string")
        self._name = name
        self._title = title
        self._writers = {}
        self._wanted_output_modes = []

    def title(self):
        assert(isinstance(self._title, basestring), 'Title of the statistic must be specified!')
        return self._title

    def name(self):
        assert isinstance(self._name, basestring), ValueError('Name must be a string')
        return self._name

    def is_wanted(self):
        return self._wanted

    def _want_output_mode(self, name, setting=True):
        if setting:
            if name not in self._wanted_output_modes:
                self._wanted_output_modes.append(name)
        else:
            if name in self._wanted_output_modes:
                self._wanted_output_modes.remove(name)

    def _set_writer(self, mode, writer):
        """Set writer object for mode.
        """
        assert isinstance(mode, str), ValueError("Mode must be a shor string (identifier)")
        assert isinstance(writer, StatisticWriter), ValueError("Writer must be a Writer instance")
        self._writers[mode] = writer

    def configure(self, config):
        self._configure_writers(config)

    def _configure_writers(self, config):
        for writer in self._writers.values():
            writer.configure(config)

    def write(self, run_time):
        """Write out stats using all wanted modes."""
        for mode in self._wanted_output_modes:
            writer = self._writers[mode]
            writer.write(run_time=run_time)

    def output(self, mode):
        writer = self._writers[mode]
        return writer.output()


class TableStatistic(Statistic):
    """A statistic that is presented as a table.
    """
    def __init__(self, name, title):
        Statistic.__init__(self, name, title)

        # we want to be printed with TableHTMLWriter by default
        self._set_writer('html', TableHTMLWriter(self))
        self._want_output_mode('html')
    
    def rows(self):
        return self._data

    def show_numbers(self):
        return True

    def show_th(self):
        return True

class GeneralStatistics(Statistic):
    """General (opening) statistics (like first commit, last commit, total commit count etc).
    Outputted by simple text.
    """
    def __init__(self):
        """Initialise."""
        Statistic.__init__(self, "general_statistics", "General statistics")
        self._set_writer('html', GeneralStatisticsHTMLWriter(self))
        self._want_output_mode('html')

    def configure(self, config):
        pass

    def calculate(self, revision_data):
        self._first_rev_number = revision_data.get_first_revision().get_number()
        self._last_rev_number = revision_data.get_last_revision().get_number()
        self._revision_count = len(revision_data)
        self._repository_url = revision_data.get_repository_url()
        self._first_rev_date = revision_data.get_first_revision().get_date()
        self._last_rev_date = revision_data.get_last_revision().get_date()

    def get_first_rev_number(self):
        return self._first_rev_number

    def get_last_rev_number(self):
        return self._last_rev_number

    def get_revision_count(self):
        return self._revision_count

    def get_repository_url(self):
        return self._repository_url

    def get_first_rev_date(self):
        return self._first_rev_date

    def get_last_rev_date(self):
        return self._last_rev_date
        

class AuthorsByCommits(TableStatistic):
    """Specific statistic - show table author -> commit count sorted
    by commit count.
    """
    def __init__(self):
        """Generate statistics out of revision data.
        """
        TableStatistic.__init__(self, 'authors_by_number_of_commits', 'Authors by total number of commits')

    def column_names(self):
        return ('Author', 'Total number of commits', 'Percentage of total commit count')

    def configure(self, config):
        """Handle configuration - decide whether we are wanted/or possible to
        be calculated and output.
        """

    def calculate(self, revision_data):
        """Do calculations based on revision data passed as
        parameter (which must be a RevisionData instance).

        This method sets internal _data member.
        Output writer can then get it by calling rows().
        """
        assert isinstance(revision_data, RevisionData), ValueError(
            "Expected RevisionData instance, got %s", repr(revision_data)
            )

        abc = {}

        for rv in revision_data.get_revisions():
            author = rv.get_author()
            if not abc.has_key(author): abc[author] = 1
            else: abc[author] += 1

        data = [(a, abc[a]) for a in abc.keys()]
        data.sort(lambda x,y: cmp(y[1], x[1]))

        rows = []

        for k,v in data:
            rows.append([k,
                    str(v),
                    "%.2f%%" % (float(v) * 100.0 / float(len(revision_data)))])
        
        self._data = rows


class AuthorsByChangedPaths(TableStatistic):
    """Authors sorted by total number of changed paths.
    """
    def __init__(self):
        """Generate statistics out of revision data.
        """
        TableStatistic.__init__(self, 'authors_number_of_paths', 'Authors by total number of changed paths')

    def configure(self, config):
        pass

    def calculate(self, revision_data):
        """Perform calculations."""
        assert(isinstance(revision_data, RevisionData))

        abp = {}
        max = 0

        for rv in revision_data.get_revisions():
            author = rv.get_author()
            modified_path_count  = len(rv.get_modified_paths())
            if not abp.has_key(author): abp[author] = modified_path_count
            else: abp[author] += modified_path_count
            max += modified_path_count

        data = [(a, abp[a]) for a in abp.keys()]
        data.sort(lambda x,y: cmp(y[1], x[1]))

        self._data = data

        rows = []

        for k,v in data:
            rows.append([k,
                str(v),
                "%.2f%%" % (float(v) * 100.0 / float(max))])

        self._data = rows

    def column_names(self):
        """Return names of collumns."""
        return ('Author', 'Total number of changed paths', 'Percentage of all changed paths')



class GraphStatistic(Statistic):
    """This stats are presented as a graph.

    This class holds graph abstract data.
    This is allways f(x) -> y graph, so
    there is a dict of (x,y) pairs.

    GraphStatistic does not do any output,
    GraphImageWriter and possibly others
    translate logical data info image file.
    """

    requires_graphics = True
    
    def __init__(self, name, title):
        Statistic.__init__(self, name, title)

    def keys(self):
        return self._keys

    def __getitem__(self, key):
        return self._data[key]

    def get_x_range(self):
        return (self._min_x, self._max_x)

    def get_y_range(self):
        return (self._min_y, self._max_y)


class TotalCommitsByTimeGraphStatistic(GraphStatistic):
    """Show function f(time) -> commits by that time.
    """
    def __init__(self, config, revision_data):
        assert(isinstance(revision_data, RevisionData))
        GraphStatistic.__init__(self, 'total_commit_count_in_time', 'Total commit count by time')
        self._revision_data = revision_data
        self._config = config

        data = {}
        count = 0
        date_min = 0
        date_max = datetime.datetime.now()
        date_max = time.mktime(time.strptime(datetime.datetime.now().isoformat()[:19], '%Y-%m-%dT%H:%M:%S'))
        first = True
        for rv in revision_data.values():
            count += 1
            # this goes in chronological order
            date = rv.get_date()
            data[date] = count

            if first:
                date_min = date
#                date_max = date
                first = False
            else:
                if date < date_min: date_min = date
#                elif date > date_max: date_max = date

        self._min_y = float(0)
        self._max_y = float(count)
        self._min_x = float(date_min)
        self._max_x = float(date_max)
        self._data = data
        self._keys = data.keys()
        self._keys.sort()


class GroupStatistic(Statistic):
    """Statistic class for grouping other statistics.
    Every object of this one can contain more statistics.
    Rendering this type of statistics means rendering
    all children stats, and putting it in one group
    (for example - in web page section).
    """
    def __init__(self, name, title):
        """Initialize internal variables. Must be called.
        """
        Statistic.__init__(self, name, title)
        self._child_stats = []

    def __getitem__(self, number):
        """Get a child Statistic object."""
        return self._child_stats[number]

    def append(self, statistic):
        """Append given statistic to child list.
        
        Parameters:
            - statistic - must be an instance of Statistic
        """
        assert isinstance(statistic, Statistic), ValueError(
            "Wrong parameter, expected Statistic instance, got %s" % (
                repr(statistic)))

        self._child_stats.append(statistic)

    def children(self): 
        """Get children."""
        return self._child_stats

    def configure(self, config):
        Statistic.configure(self, config)
        for child in self._child_stats:
            child.configure(config)

    def count_all(self):
        """Return the total number of leaf statistics in the group/tree.
        That is, group statistics are not included.
        """
        total = 0
        for stat in self._child_stats:
            if isinstance(stat, GroupStatistic):
                total += stat.count_all()
            else:
                total += 1
        return total

    def calculate(self, revision_data):
        """Pass data to children."""

        for child in self._child_stats:
            child.calculate(revision_data)


class AllStatistics(GroupStatistic):
    """This is a special type of group statistic - it
    is created at startup. It should create
    all statistics objects tree.
    
    After that, objects are queried whether they
    are to be calculated."""

    def __init__(self):
        """This constructor takes no parameters.
        """
        GroupStatistic.__init__(self, "mpy_svn_stats", "MPY SVN Statistics")
        self.append(GeneralStatistics())
        self.append(AuthorsByCommits())
        self.append(AuthorsByChangedPaths())
        self.append(AuthorsByCommitLogSize())
        self._set_writer('html', TopLevelGroupStatisticHTMLWriter(self))
        self._want_output_mode('html')


class StatisticWriter:
    """Abstract class for all output generators.
    """
    pass


class HTMLWriter(StatisticWriter):
    """An abstract class for HTML writing."""
    pass


class GroupStatisticHTMLWriter(HTMLWriter):
    """Class for writing group statistics (abstract)."""
    def __init__(self, group_statistic=None):
        self._statistic = group_statistic

    def set_statistic(self, statistic):
        self._statistic = statistic
        

class TopLevelGroupStatisticHTMLWriter(GroupStatisticHTMLWriter):
    """Class for writing one, top level
    GroupStatistic.

    """
    def __init__(self, statistic=None):
        GroupStatisticHTMLWriter.__init__(self, statistic)

    def configure(self, config):
        """Confugure - generally - get the output directory."""
        assert isinstance(config, Config), ValueError(
            "Expected Config instance, got %r instead" % repr(config))
        self._output_dir = config.get_output_dir()

    def write(self, run_time):
        """Write out generated statistics."""
        filename = self._output_dir + '/index.html'
        output_file = file(filename, "w")
        output_file.write(
            self._page_head()
            + self._page_body()
            + self._page_foot(run_time=run_time)
        );
        output_file.close()

    def _page_head(self):
        """Return HTML page head."""
        return """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
    <head>
        <meta name="Generator" content="mpy-svn-stats v. 0.1"/>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>mpy-svn-stats</title>
        <style type="text/css">
            body, td, li {
                font-size: 12px;
            }
        
            table.statistic {
                width: 80%;
                float: center;
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
                font-size: 75%;
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

            td.menu_column {
                padding-left: 1em;
                padding-right: 1em;
                vertical-align: top;
            }

            td.statistics_column {
                vertical-align: top;
            }

            .topLink a:link, .topLink a:active, .topLink a:visited {
                color: lightgray;
            }

            .topLink a:hover {
                color: gray;
            }
            
        </style>
    </head>
    <body>
        <h1><a name="top"></a>mpy-svn-stats</h1>
"""

    def _page_foot(self, run_time):
        """Return HTML page foot."""

        

        return """
        <hr/>
        <p class="foot">
        Stats generated by <a href="http://mpy-svn-stats.berlios.de">mpy-svn-stats</a> in %(run_time).2f seconds.
        </body></html>
        """ % {
            'run_time': run_time
        }

    def _page_body(self):
        return "<table><tr><td class=\"menu_column\">%(menu_column)s</td><td>%(body_column)s</td></tr></table>" % {
            'menu_column': self._page_menu(),
            'body_column': self._page_main()
            }

    def _page_menu(self):
        return "<ul class=\"menu\">" + self._recursive_menu(self._statistic) + "</ul>\n"

    def _recursive_menu(self, statistic):
        """Return statistic as li tag.
        """

        r = ""
        if isinstance(statistic, GroupStatistic):
            r += "<li>%s:\n<ul>\n" % statistic.title()
            for child in statistic.children():
                r += self._recursive_menu(child)

            r += "</ul>\n</li>\n"
        else:
            r += "<li><a href=\"#%s\">%s</a></li>\n" % (
                statistic.name(),
                statistic.title())
        return r

    def _page_main(self):
        flat = [] 
        stack = [self._statistic]

        while len(stack) > 0:
            stat = stack.pop()
            if not isinstance(stat, GroupStatistic):
                flat.append(stat)
            else:
                children = stat.children()
                children.reverse()
                stack.extend(children)

        r = ''

        for stat in flat:
            r += stat.output('html')

        return r


class TableHTMLWriter(HTMLWriter):
    """Output table."""

    def __init__(self, stat):
        assert isinstance(stat, TableStatistic), ValueError()
        self._statistic = stat

    def output(self):
        r = '\n'
        r += "<h2><a name=\"%s\"></a>%s</h2>\n" % (
            escape(self._statistic.name()),
            escape(self._statistic.title())
            )
        r += "<p class=\"topLink\" style=\"text-align: right\"><a href=\"#top\">top</a>\n"
        r += "<table class=\"statistic\">\n%s\n%s\n</table>\n\n" % (
            self._table_header(),
            self._table_body())
        return r

    def _table_header(self):
        r = "<tr>\n"
        r += "  <th>No</th>\n"
        for column_name in self._statistic.column_names():
            r += "  <th>" + escape(column_name) + "</th>\n"
        r += "</tr>\n"
        return r
        

    def _table_body(self):
        r = ''
        i = 1
        for row in self._statistic.rows():
            r += "<tr>\n"
            r += "  <td>%d</td>\n" % i
            for cell in row:
                r += "  <td>" + escape(cell) + "</td>\n"
            i += 1
            r += "</tr>\n"
        return r


class GeneralStatisticsHTMLWriter(HTMLWriter):
    """Specialised GeneralStatistics HTML Writer class."""

    def __init__(self, stat):
        self._statistic = stat

    def output(self):
        statistic = self._statistic
        return """
            <h2><a name=\"%(statistic_name)s\"></a>%(statistic_title)s</h2>

            <p>
                Statistics for repository at: <b>%(repository_url)s</b>.<br/>
                Smallest revision number: %(first_rev_number)s.<br/>
                Biggest revision number: %(last_rev_number)s.<br/>
                Revision count: %(revision_count)s.<br/>
                First revision date: %(first_rev_date)s (%(time_since_first_commit)s ago).<br/>
                Last revision date: %(last_rev_date)s. (%(time_since_last_commit)s ago).<br/>
                Age of the repository (from first to last revision): %(age_of_repository)s.<br/>
                Commits per year: %(commits_per_year)s.<br/>
                Commits per month: %(commits_per_month)s.<br/>
                Commits per day: %(commits_per_day)s.
            </p>
        """ % {
            'repository_url': escape(statistic.get_repository_url()),
            'statistic_name': escape(statistic.name()),
            'statistic_title': escape(statistic.title()),
            'revision_count': str(statistic.get_revision_count()),
            'first_rev_number': str(statistic.get_first_rev_number()),
            'last_rev_number': str(statistic.get_last_rev_number()),
            'first_rev_date': time.strftime('%c', time.gmtime(statistic.get_first_rev_date())),
            'last_rev_date': time.strftime('%c', time.gmtime(statistic.get_last_rev_date())),
            'age_of_repository': self._format_time_span(
                                            statistic.get_first_rev_date(),
                                            statistic.get_last_rev_date()
                                        ),
            'time_since_last_commit': self._format_time_span(
                                            statistic.get_last_rev_date(),
                                            time.time()
                                        ),
            'time_since_first_commit': self._format_time_span(
                                            statistic.get_first_rev_date(),
                                            time.time()
                                        ),
            'commits_per_year': ("%.2f" % (statistic.get_revision_count() * 365.25 * 24 * 60 * 60
                    / (statistic.get_last_rev_date() - statistic.get_first_rev_date()))
                ),
            'commits_per_month': ("%.2f" % (statistic.get_revision_count() * 30 * 24 * 60 * 60
                    / (statistic.get_last_rev_date() - statistic.get_first_rev_date()))
                ),
            'commits_per_day': ("%.2f" % (statistic.get_revision_count() * 24 * 60 * 60
                    / (statistic.get_last_rev_date() - statistic.get_first_rev_date()))
                ),
        }

    def _format_time_span(self, from_time, to_time):
        """Format time span as a string."""
        seconds = to_time - from_time
        reminder = seconds
        s = ''

        steps = [
            ('years', 365.25 * 24 * 60 * 60),
            ('months', 30 * 24 * 60 * 60),
            ('days', 24 * 60 * 60),
            ('hours', 60 * 60),
            ('minutes', 60),
        ]

        have_nonzero_step = False

        for step in steps:
            n = reminder / step[1]
            if int(n) > 0:
                have_nonzero_step = True
                reminder -= int(n) * step[1]
                s += '%d %s' % (int(n), step[0])
                if have_nonzero_step:
                    if step is steps[len(steps)-1]:
                        s += ' and '
                    else:
                        s += ' '

        s += '%d seconds' % int(reminder)
        
        return s

    
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
        self._name = name

    def get_image_fname(self):
        return self._name + '.png'

    def write(self):
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

        for k in self._stats.keys():
            v = self._stats[k]
#            print "k,v: %f %f" % (k,v)
            if not first:
                cur_x = float((k - min_x) / (max_x - min_x))
                cur_y = float((v - min_y) / (max_y - min_y))

                px1 = last_x * float(im.size[0])
                py1 = float(im.size[1]) - last_y * float(im.size[1])

                px2 = cur_x * float(im.size[0])
                py2 = float(im.size[1]) - cur_y * float(im.size[1])

                draw.line( (px1, py1, px2, py2), 'black')
#                print "line: %f %f -> %f %f" % (px1, py1, px2, py2)
        
            last_x = float(cur_x)
            last_y = float(cur_y)
            first = False

        del draw
        im.save(self._config.get_output_dir() + '/' + self._name + '.png')
        


class RevisionData:
    """Data about all revisions."""
    def __init__(self, url, dom):
        """Create revision data from xml.dom.Document."""

        self._repository_url = url

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

    def get_first_revision(self):
        return self._revisions[0]

    def get_last_revision(self):
        return self._revisions[len(self._revisions)-1]

    def get_repository_url(self):
        return self._repository_url

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

    def get_commit_log(self):
        return self._log

    def get_revision_number(self):
        return self._revision_number

    def get_number(self):
        """Same as get_revision_number."""
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
        self._log = self._parse_commit_log(message)

    def _parse_author(self, message):
        a = message.getElementsByTagName('author')
        assert(len(a) == 1)
        a[0].normalize()
        assert(len(a[0].childNodes) == 1)
        return a[0].childNodes[0].data

    def _parse_commit_log(self, message):
        l = message.getElementsByTagName('msg')
        l[0].normalize()
        try:
            return l[0].childNodes[0].data
        except:
            return ''

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


class AuthorsByCommitLogSize(TableStatistic):
    """Specific statistic - show table author -> commit log, sorted
    by commit log size.
    """
    def __init__(self):
        """Generate statistics out of revision data.
        """
        TableStatistic.__init__(self, 'authors_by_log_size', """Authors by total size of commit log messages""")

    def configure(self, config):
        """Handle configuration."""
        pass

    def column_names(self):
        return ('Author',
            'Total numer od characters in all log messages',
            'Percentage of all log messages')

    def calculate(self, revision_data):
        """Do calculations."""
        assert(isinstance(revision_data, RevisionData))

        abc = {}
        sum = 0
        
        for rv in revision_data.get_revisions():
            author = rv.get_author()
            log = rv.get_commit_log()
            size = len(log)
            if not abc.has_key(author): abc[author] = size
            else: abc[author] += size
            sum += size

        data = [(a, abc[a]) for a in abc.keys()]
        data.sort(lambda x,y: cmp(y[1], x[1]))

        rows = []

        for k,v in data:
            rows.append([k,
                str(v),
                "%2.2f%%" % (float(v) * 100.0 / float(sum))])

        self._data = rows


class AuthorsByDiffSize(TableStatistic):
    """Specific statistic - shows table author -> diffs size, sorted by
    size
    """

    wanted_by_default = False
    
    def __init__(self, config, revision_data):
        """Generate statistics out of revision data and `svn diff`.
        """
        TableStatistic.__init__(self, 'author_by_diff_size', 'Authors by total size of diffs')
        assert(isinstance(revision_data, RevisionData))

        abc = {}

        for rv in revision_data.get_revisions():
            author = rv.get_author()
            rev_number = rv.get_revision_number()
            command = "%s -r %d:%d diff %s" % (config.get_svn_binary(),
                rev_number-1, rev_number,
                config.get_repository_url())
            f = os.popen(command)
            result = f.read()
            f.close()
            if not abc.has_key(author): 
                abc[author] = (len(result), len(result.split()))
            else:
                abc[author] = (abc[author][0] + len(result), abc[author][1] + len(result.split()))

        data = [(a, abc[a][0], abc[a][1]) for a in abc.keys()]
        data.sort(lambda x,y: cmp(y[1], x[1]))

        self._data = data

    def column_names(self):
        return ('Author', 'Size of diffs', 'Number of lines in diffs')


if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL)
    main(sys.argv) 

