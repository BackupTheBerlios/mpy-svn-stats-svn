"""Define various reports."""


class Report(object):

    html_stylesheet = file('mpyss.css').read()

    def __init__(self, name, title):
        self.name = name
        self.title = title

    def __str__(self):
        return '%s(name=%s, title=%s)' % (self.__class__.__name__, self.name, self.title)

    def make_links(self, with_links):
        if with_links:
            return """
                <a name="%s"></a>
                <a href="#top">go to top</a>
            """ % self.name
        else:
            return ""


class ReportGroup(object):
    """Used to group similar reports.
    """

    def __init__(self, name, title):
        self.children = []
        self.children_by_name = {}
        self.name = name
        self.title = title

    def __get_item__(self, name):
        return self.children_by_name[name]

    def add(self, item):
        assert isinstance(item, Report) or isinstance(item, ReportGroup)
        assert item.name not in self.children_by_name.keys()
        self.children.append(item)
        self.children_by_name[item.name] = item


class SQLTableReport(Report):
    def __init__(self, name, title, sql, params):
        Report.__init__(self, name, title)
        self.sql = sql
        self.params = params

    def generate(self, paramstyle, cursor, format='html', with_links=True):
        db.execute(cursor=cursor, paramstyle=paramstyle, sql=self.sql, params=self.params)
        return self.format_result(format, cursor, with_links)

    def format_result(self, format, cursor, with_links):
        if format== 'html':
            return self.format_result_html(cursor, with_links)
        else:
            raise ValueError("unknown format: %s" % repr(format))

    def escape_html(self, text):
        return cgi.escape(text)

    def format_result_html(self, cursor, with_links):

        s = StringIO()

        s.write('<table>\n')
        s.write('<tr>\n')
        for col in cursor.description:
            s.write('<th>%s</th>\n' % self.escape_html(col[0]))
        s.write('</tr>\n')
        for row in cursor:
            s.write('<tr>\n')
            for value in row:
                s.write('\t<td>%s</td>\n' % self.escape_html(str(value)))
            s.write('</tr>\n')
        s.write('</table>\n')
    
        return ('''
            <div class="report">
                %(links)s
                <h2>%(title)s</h2>
                %(table)s
            </div>
        ''' % {
            'stylesheet': self.html_stylesheet,
            'title': self.escape_html(self.title),
            'table': s.getvalue(),
            'links': self.make_links(with_links),
        })


class GeneralStatsReport(Report):
    def __init__(self, repo_url):
        Report.__init__(self, 'general', 'General Statistics')
        self.repo_url = repo_url

    def generate(self, cursor, paramstyle, format='html', with_links=True):
        if format == 'html':
            return self.generate_html(cursor=cursor, paramstyle=with_links)
        else:
            raise ValueError('unsupported format: %s' % format)

    def generate_html(self, cursor,  paramstyle=None, with_links=True):
        cursor.execute(
            '''
                select
                    min(rv_number),
                    max(rv_number),
                    count(rv_number),
                    min(rv_timestamp),
                    max(rv_timestamp)
                from revision where rv_repo_url = $url
            ''',
            {'url': self.repo_url})
        
        result = cursor.fetchall()[0]

        (min_rv_num, max_rv_num, rv_count, min_tstamp, max_tstamp) = result
        if isinstance(min_tstamp, basestring): min_tstamp = parse_date(min_tstamp, datetime.datetime)
        if isinstance(max_tstamp, basestring): max_tstamp = parse_date(max_tstamp, datetime.datetime)
        age = max_tstamp - min_tstamp

        days = age.days
        months = age.days / 30.0
        years = age.days / 356.25

        avg_per_day = float(rv_count) / float(days)
        avg_per_month = float(rv_count) / float(months)
        avg_per_year = float(rv_count) / float(years)
    
        return '''
            <div class="report">
                %(links)s
                <h2>%(title)s</h2>
                <p>
                    Repository URL: <b>%(url)s</b>.<br/>
                    Smallest revision number: %(smallest_rv_number)d.<br/>
                    Biggest revision number: %(biggest_rv_number)d.<br/>
                    Revision count: %(rv_count)d.<br/>
                    First revision date: %(first_rv_date)s.<br/>
                    Last revision date: %(last_rv_date)s.<br/>
                    Repository age: %(age)s.<br/>
                    Average number of commits per year: %(avg_per_year).2f<br/>
                    Average number of commits per month: %(avg_per_month).2f<br/>
                    Average number of commits per day: %(avg_per_day).2f.<br/>
                </p>
            </div>
        ''' % {
            'title': self.title,
            'url': self.repo_url,
            'smallest_rv_number': min_rv_num,
            'biggest_rv_number': max_rv_num,
            'rv_count': rv_count,
            'first_rv_date': min_tstamp,
            'last_rv_date': max_tstamp,
            'age': age,
            'avg_per_day': avg_per_day,
            'avg_per_month': avg_per_month,
            'avg_per_year': avg_per_year,
            'links': self.make_links(with_links),
        }


class OnePageHTMLStatsGenerator(object):
    """Generate html stats and put then on one page, like previous versions od
    mpy-svn-stats did."""

    def escape(self, s):
        return cgi.escape(s)

    def _write_menu(self, s, reports):
        s.write('<div class="menu">\n')
        s.write('\t<h2>Contents</h2>\n')
        s.write('\t<ul>\n')
        for report in reports:
            s.write("\t\t<li><a href=\"#%s\">%s</a></li>\n" % (cgi.escape(report.name), cgi.escape(report.title)))
        s.write('\t</ul>\n')
        s.write('</div>')

    def generate(self, options, reports, paramstyle, cursor):

        s = StringIO()

        s.write("<h1>Statistics for <em>%s</em></h1>\n" % self.escape(options.repo_url))
        self._write_menu(s, reports)
        s.write('<div class="reports">\n')
        for report in reports:
            html = report.generate(
                cursor=cursor,
                paramstyle=paramstyle,
                format='html',
                with_links=True
            )
            s.write(html)
        s.write('</div>\n')

        filename = 'index.html'
        output_dir = options.output_dir

        output_file = file(os.path.join(output_dir, filename), 'w')

        output_file.write('''
            <html>
                <head>
                    <title>stats</title>
                    <style type="text/css">
                        %(css)s
                    </style>
                </head>
                <body>
                    %(body)s
                </body>
            </html>
        ''' % {
            'body': s.getvalue(),
            'css': file('mpy-svn-stats.css').read(),
        })

        return True


class AllReports(ReportGroup):
    """All reports."""

    def __init__(self, options):
        """Initialize (create) all reports."""
        ReportGroup.__init__(self, 'all_reports', 'MPY SVN Statistics')
        self.options = options
        self.create_reports()

    def create_reports(self):
        self.add(GeneralStatsReport())
        self.add(SQLTableReport('count', 'Total Revision Count',
                '''
                    select count(*) from revision
                    where rv_repo_url = $repo_url
                   
                ''', {'repo_url': options.repo_url}))
        self.add(SQLTableReport('authors_by_commits', 'Authors by commits',
            '''
                select rv_author as Author, count(*) as Count
                from revision
                where rv_repo_url = $repo_url
                group by rv_author
                order by Count desc

            ''', {'repo_url': options.repo_url}))


