#!/usr/bin/env python2.5
# coding: utf-8

import sys, os, time, re, os.path
import optparse
import xml.sax
import xml.sax.handler
import cgi
import datetime
from cStringIO import StringIO
from textwrap import dedent
from ConfigParser import ConfigParser

import config
import db
from reports import AllReports, Report, ReportGroup
from common import parse_date, ensure_date


class OnePageHTMLStatsGenerator(object):
    """Generate html stats and put then on one page,
    like previous versions of mpy-svn-stats did.
    """

    def escape(self, s):
        return cgi.escape(s)

    def _write_menu(self, s, reports):
        s.write('<div class="menu">\n')
        s.write('\t<h2>Contents</h2>\n')
        s.write('\t<ul>\n')
        self._write_menu_from_list(s, [reports])
        s.write('\t</ul>\n')
        s.write('</div>')

    def _write_menu_from_list(self, s, reports):
        for child in reports:
            if isinstance(child, Report):
                s.write("""<li><a href="#%s">%s</a></li>\n""" % (self.escape(child.name), self.escape(child.title)))
            elif isinstance(child, ReportGroup):
                s.write("""
                    <li>
                        <a href="#%s">%s</a>
                        <ul>
                """ % (child.name, child.title))
                self._write_menu_from_list(s, child.children)
                s.write("""
                        </ul>
                    </li>""")

    def generate(self, options, reports, cursor):

        time_generated_start = datetime.datetime.now()

        s = StringIO()

        s.write("""
            <div class="header">
                <h1>Statistics for <em>%s</em></h1>
            </div>
        """ % self.escape(options.repo_url))
        self._write_menu(s, reports)
        s.write('<div class="reports">\n')
        for report in reports.get_all_reports():
            assert isinstance(report, Report), Exception('%s is not a report' % repr(report))
            try:
                html = report.generate(
                    cursor=cursor,
                    options=options,
                    format='html',
                    with_links=True
                )
                s.write(html)
            except (Exception, TypeError), e:
                print report, "failed"
                raise
        s.write('</div>\n')


        filename = 'index.xhtml'
        output_dir = options.output_dir

        output_file = file(os.path.join(output_dir, filename), 'w')

        time_generated_end = datetime.datetime.now()

        generated_in = time_generated_end - time_generated_start

        title = "MPY-SVN-STATS for %s" % options.repo_url

        output_file.write(dedent("""\
            <!DOCTYPE html PUBLIC
                "-//W3C//DTD XHTML 1.1 plus MathML 2.0 plus SVG 1.1//EN"
                "http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-flat.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml"
                    xml:lang="en">
                <head>
                    <title>%(title)s</title>
                    <meta http-equiv="Content-Type" content="text/xhtml; charset=utf-8" />
                    <style type="text/css">
                        %(css)s
                    </style>
                </head>
                <body>
                    %(body)s
                    <hr />
                    <p class="footer">
                        Generated by <a href="http://mpy-svn-stats.berlios.de/">mpy-svn-stats</a>
                        at %(time_generated)s
                        in %(seconds)s seconds
                    </p>
                </body>
            </html>
        """) % {
            'body': s.getvalue(),
            'css': file('mpyss.css').read(),
            'time_generated': time_generated_end.strftime('%Y-%m-%d %H:%M:%S'),
            'seconds': generated_in.seconds,
            'title': title,
        })

        return True


def main(argv):
    options, args = parse_options()
    conn = db.connect()
    db.create_db_if_needed(conn)
    if options.parse:
        print "parsing"
        if options.input == '-':
            print "reading from stdin"
            input = sys.stdin
        else:
            input = file(options.input)
        get_data(conn, input, options.repo_url)
    if options.reports:
        print "generating reports"
        generate_reports(options, conn)
    else:
        print "not generating reports"


def generate_reports(options, conn):
    output_dir = options.output_dir
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    reports = AllReports(options)
    cursor = conn.cursor()
    generator = OnePageHTMLStatsGenerator()
    generator.generate(options, reports, cursor)


class SAXLogParserHandler(xml.sax.handler.ContentHandler):
    """Parser used to copy data from xml log to sql database."""

    def __init__(self, dbconn, repo_url):
        xml.sax.handler.ContentHandler.__init__(self)
        self.repo_url = repo_url
        self.dbconn = dbconn
        self.cursor = self.dbconn.cursor()
        self.paths = None

    def startDocument(self):
        print "starting document"

    def endDocument(self):
        print "ending document"

    def startElement(self, name, attrs):
        self.current_characters = ''
        if name == 'logentry':
            self.number = int(attrs['revision'])
            self.msg = None
            self.author = None
            self.date = None
            self.paths = []
        elif name == 'path':
            self.current_path_action = attrs['action']

    def characters(self, content):
        self.current_characters += content

    def endElement(self, name):
        if name == 'logentry':
            self.add_current_logentry()
        elif name == 'author':
            self.author = self.current_characters
        elif name == 'date':
            self.date = self.current_characters
        elif name == 'msg':
            self.msg = self.current_characters
        elif name == 'path':
            self.current_path_path = self.current_characters
            self.paths.append((self.current_path_action, self.current_path_path))
            self.current_path_action = None
        self.current_characters = u''

    def add_current_logentry(self):
        number = int(self.number)
        msg = self.msg
        date = parse_date(self.date)
        author = self.author

        self.cursor.execute(
            '''
                delete from changed_path where
                    rv_repo_url = $url and rv_number = $number
            ''', {
                'url': self.repo_url,
                'number': number,
        })

        self.cursor.execute(
            '''
                delete from revision where
                    rv_repo_url = $url and rv_number = $number
            ''', {
                    'url': self.repo_url,
                    'number': number
        })

        self.cursor.execute(
            '''
                insert into revision (
                    rv_repo_url,
                    rv_number,
                    rv_author,
                    rv_timestamp,
                    rv_comment)
                values (
                    $url,
                    $number,
                    $author,
                    $timestamp,
                    $comment)
            ''', {
                'url': self.repo_url,
                'number': int(number),
                'author': author.encode('utf-8'),
                'comment': msg.encode('utf-8'),
                'timestamp': date
        })

        for action, path in self.paths:
            self.cursor.execute(
            '''
                insert into changed_path (
                    rv_repo_url,
                    rv_number,
                    cp_action,
                    cp_path)
                values (
                    $url,
                    $number,
                    $action,
                    $path)
            ''',{
                'url': self.repo_url,
                'number': int(self.number),
                'action': action.encode('utf-8'),
                'path': path.encode('utf-8'),
            })


def parse_options():
    parser = optparse.OptionParser()
    parser.add_option("-u", "--url", dest="repo_url", help="Reporitory URL")
    parser.add_option("-r", "--reports", action="store_true",
        dest="reports", help="Generate reports")
    parser.add_option("--no-reports", action="store_false",
        dest="reports", help="Do not generate reports")
    parser.add_option("-p", "--parse", action="store_true",
        dest="parse", help="Parse logs")
    parser.add_option("--no-parse", action="store_false",
        dest="parse", help="Do not parse logs")
    parser.add_option("-i", "--input", dest="input",
        help="Input source file name (use - for standard input)",
        default=None)
    parser.add_option('-o', '--output-dir', dest='output_dir', default='mpy-svn-stats',
        help='Output directory (default: %default)')
    parser.add_option('-s', '--output-formats', dest='output_formats', default='html',
        help='Output formats, comma separated list  (default: %default, possible values: html)')

    def handle_config_option(option, opt_str, filename, parser):
        print "loading config file \"%s\"" % filename
        cp = ConfigParser()
        cp.read(filename)
        s = cp.sections()[0]
        print "using section \"%s\"" % s
        if cp.has_option(s, 'url'):
            parser.values.repo_url = cp.get(s, 'url')
            print "url from config file: \"%s\"" % parser.values.repo_url
        parse = cp.get(s, 'parse', False)
        if parse:
            parser.values.parse = parse
        reports = cp.get(s, 'reports', False)
        if reports:
            parser.values.reports = reports
        input = cp.get(s, 'input', None)
        if input:
            parser.values.input = input
        output_dir = cp.get(s, 'output_dir', None)
        if output_dir: parser.values.output_dir = output_dir
            

    parser.add_option('-c', '--config', type='string', default=None, action='callback',
        callback=handle_config_option,
        help='Config file')

    options, args = parser.parse_args()

    if not options.repo_url: parser.error('Please specify repository url with -u.')

    if options.input and not options.parse:
        print "warning: input defined, but parse is not set - not parsing!"
    if options.parse and not options.input:
        options.input = '-'
    
    return (options, args)


def create_dates(dbconn):
    """Create dates table for use in joins."""
    curs = dbconn.cursor()
    if not dbconn.table_exists('calendar'):
        raise Exception()
    print "creating dates..."
    sql = 'select min(rv_timestamp), max(rv_timestamp) from revision'
    curs.execute(sql)
    min_date, max_date = map(ensure_date, curs.fetchone())
    print "min date: %s" % repr(min_date)
    print "max date: %s" % repr(max_date)
    min_year = min_date.year
    max_year = max_date.year
    for year in xrange(min_year, max_year+1):
        for month in range(1, 13):
            d = datetime.datetime(year, month, 1)
            curs.execute('''
                    select count(*)
                    from calendar
                    where timestamp = $timestamp
                    and calendar_type = 'month'
                ''',
                {'timestamp': d})
            cnt = curs.fetchone()[0]
            if cnt == 0:
                curs.execute(
                    '''insert into calendar (
                        timestamp, calendar_type,
                        year, month, day,
                        hour, minute, second
                    ) values (
                        $timestamp, $calendar_type,
                        $year, $month, $day,
                        $hour, $minute, $second
                    )
                    ''',
                    {'timestamp': d,
                        'calendar_type': 'month',
                        'year': d.year,
                        'month': d.month,
                        'day': d.day,
                        'hour': d.hour,
                        'minute': d.minute,
                        'second': d.second
                    })


def get_data(dbconn, input_stream, repo_url):
    handler = SAXLogParserHandler(dbconn, repo_url)
    parser = xml.sax.parse(input_stream, handler)
    create_dates(dbconn)
    dbconn.commit()


if __name__ == '__main__':
    main(sys.argv)

