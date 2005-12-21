"""Define various reports."""

import datetime
import cgi
from cStringIO import StringIO

import db
from common import parse_date, ensure_date

class Report(object):

    html_stylesheet = file('mpyss.css').read()

    def __init__(self, name, title):
        self.name = name
        self.title = title

    def __str__(self):
        return '%s(name=%s, title=%s)' % (self.__class__.__name__, self.name, self.title)

    def html_make_links(self, with_links):
        if with_links:
            return """
                <div class="small_links">
                    <a name="%s"></a>
                    <a href="#top">go to top</a>
                </div>
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

    def get_all_reports(self):
        reports = []
        for child in self.children:
            if isinstance(child, Report):
                reports += [child]
            elif isinstance(child, ReportGroup):
                reports += child.get_all_reports()
            else:
                raise ValueError("bad thing found in reports group")
        return reports


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
                <h2>%(title)s</h2>
                %(links)s
                %(table)s
            </div>
        ''' % {
            'stylesheet': self.html_stylesheet,
            'title': self.escape_html(self.title),
            'table': s.getvalue(),
            'links': self.html_make_links(with_links),
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
                <h2>%(title)s</h2>
                %(links)s
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
            'links': self.html_make_links(with_links),
        }


class AllReports(ReportGroup):
    """All reports."""

    def __init__(self, options):
        """Initialize (create) all reports."""
        ReportGroup.__init__(self, 'all_reports', 'MPY SVN Statistics')
        self.options = options
        self.create_reports()

    def create_reports(self):
        options = self.options
        self.add(GeneralStatsReport(options.repo_url))
        self.create_commits_reports()

    def create_commits_reports(self):
        group = ReportGroup(name='commits', title='Commits Statistics')
        last_week = (datetime.datetime.now() - datetime.timedelta(7)).isoformat(' ')
        last_month = (datetime.datetime.now() - datetime.timedelta(30)).isoformat(' ')
        group.add(SQLTableReport('authors_by_commits', 'Authors by commits',
            '''
                select rv_author as Author, count(*) as Count
                from revision
                where rv_repo_url = $repo_url
                group by rv_author
                order by Count desc

            ''', {'repo_url': self.options.repo_url}))
        group.add(SQLTableReport('authors_by_commits_month', 'Authors by commits - last month',
            '''
                select rv_author as Author, count(*) as Count
                from revision
                where rv_repo_url = $repo_url
                and rv_timestamp >= $last_week
                group by rv_author
                order by Count desc

            ''', {
                'repo_url': self.options.repo_url,
                'last_week': last_week,
            }))
        group.add(SQLTableReport('authors_by_commits_week', 'Authors by commits - last week',
            '''
                select rv_author as Author, count(*) as Count
                from revision
                where rv_repo_url = $repo_url
                and rv_timestamp >= $last_month
                group by rv_author
                order by Count desc

            ''', {
                'repo_url': self.options.repo_url,
                'last_month': last_month,
            }))
        self.add(group)



