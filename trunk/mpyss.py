#!/usr/bin/env python2.4
# coding: utf-8

import sys, os, time, re, os.path
import optparse
import xml.sax
import xml.sax.handler
import cgi
import datetime
from cStringIO import StringIO

import config
import db
from reports import AllReports

def main(argv):
    options, args = parse_opions()
    conn = db.connect()
    if options.parse:
        print "parsing"
        if options.input == '-':
            input = sys.stdin
        else:
            input = file(options.input)
        get_data(conn, input, options.repo_url)
    if options.reports:
        generate_reports(options, conn)


def generate_reports(options, conn):
    output_dir = options.output_dir
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    reports = AllReports(options)
    cursor = conn.cursor()
    generator = OnePageHTMLStatsGenerator()
    generator.generate(options, reports, db.paramstyle(), cursor)


class SAXLogHandler(xml.sax.handler.ContentHandler):
    """Parser used to copy data from xml log to sql database."""

    def __init__(self, dbconn, repo_url):
        xml.sax.handler.ContentHandler.__init__(self)
        self.repo_url = repo_url
        self.dbconn = dbconn
        self.cursor = self.dbconn.cursor()

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
        self.current_characters = ''

    def add_current_logentry(self):
        number = self.number
        msg = self.msg
        date = parse_date(self.date)
        author = self.author

        db.execute(self.cursor, db.paramstyle(),
            '''
                delete from revision where
                    rv_repo_url = $url and rv_number = $number
            ''', {
                    'url': self.repo_url,
                    'number': number
        })

        db.execute(self.cursor, db.paramstyle(),
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
                'number': number,
                'author': author,
                'comment': msg,
                'timestamp': date
        })

        self.dbconn.commit()


def parse_opions():
    parser = optparse.OptionParser()
    parser.add_option("-u", "--url", dest="repo_url", help="Reporitory URL")
    parser.add_option("-r", "--reports", dest="reports", help="Generate reports", default=True)
    parser.add_option("-p", "--parse", dest="parse", help="Parse log file", default=False)
    parser.add_option("-i", "--input", dest="input",
        help="Input source file name (use - for standard input)",
        default=None)
    parser.add_option('-o', '--output-dir', dest='output_dir', default='mpy-svn-stats',
        help='Output directory (default: %default)')
    parser.add_option('-s', '--output-formats', dest='output_formats', default='html',
        help='Output formats, comma separated list  (default: %default, possible values: html)')

    options, args = parser.parse_args()

    if not options.repo_url: parser.error('Please specify repository url with -u.')

    if options.input:
        options.parse = True
    if options.parse and not options.input:
        options.input = '-'
    return (options, args)

def get_data(dbconn, input_stream, repo_url):
    handler = SAXLogHandler(dbconn, repo_url)
    parser = xml.sax.parse(input_stream, handler)

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

if __name__ == '__main__':
    main(sys.argv)

