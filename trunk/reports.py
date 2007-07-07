"""Define various reports."""

from __future__ import division

import datetime
import cgi
from cStringIO import StringIO

import db
import svg
from common import parse_date, ensure_date

class Report(object):

    html_stylesheet = file('mpyss.css').read()

    def __init__(self, name, title):
        self.name = name
        self.title = title

    def __str__(self):
        return '%s(name=%s, title=%s)' % (self.__class__.__name__, self.name, self.title)

    def go_to_top_link(self, with_links):
        if with_links:
            return u"""
                <div class="small_links">
                    <a href="#top">go to top</a>
                </div>
            """
        else:
            return ''


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

    def generate(self, cursor, options, format='html', with_links=True):
        cursor.execute(self.sql, self.params)
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
        for row in cursor.fetchall():
            s.write('<tr>\n')
            for value in row:
                s.write('\t<td>%s</td>\n' % self.escape_html(str(value)))
            s.write('</tr>\n')
        s.write('</table>\n')
    
        return ('''
            <div class="report">
                <a id="%(anchor_name)s"></a>
                <h2>%(title)s</h2>
                %(go_to_top_link)s
                %(table)s
            </div>
        ''' % {
            'stylesheet': self.html_stylesheet,
            'title': self.escape_html(self.title),
            'table': s.getvalue(),
            'go_to_top_link': self.go_to_top_link(with_links),
            'anchor_name': self.name,
        })


class GeneralStatsReport(Report):
    def __init__(self, repo_url):
        Report.__init__(self, 'general', 'General Statistics')
        self.repo_url = repo_url

    def generate(self, cursor, options, format='html', with_links=True):
        if format == 'html':
            return self.generate_html(cursor=cursor, with_links=with_links)
        else:
            raise ValueError('unsupported format: %s' % format)

    def generate_html(self, cursor, with_links=True):
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
                <a id="%(anchor_name)s"></a>
                <h2>%(title)s</h2>
                %(go_to_top_link)s
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
            'anchor_name': self.name,
            'go_to_top_link': self.go_to_top_link(with_links),
        }


class GroupByAndCountSQLReport(SQLTableReport):
    """Group by report.
    Usually tabular representation of some simple aggregation is required.

    XXX

    """
    
    def __init__(self, name, title, group_by):
        sql, params = self.__make_sql(group_by=group_by)
        SQLTableReport.__init__(self, name, title, sql, params)

    def __make_sql(self, group_by):
        """Create standard "group by" sql code.
        group_by parameter is trusted - it's pasted directly into sql code.

        """

        sql = '''
                select %(group_by)s, count(*) as Count
                from revision
                where rv_repo_url = $repo_url
                and rv_timestamp >= $last_month
                group by %(group_by)s
                order by Count desc

        ''' % {
                'group_by': group_by,
        }
        params = {
                'repo_url': self.options.repo_url,
                'last_month': last_month,
        }

        return sql, params


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
        last_week = (datetime.datetime.now() - datetime.timedelta(7))
        last_month =(datetime.datetime.now() - datetime.timedelta(30))
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
                and rv_timestamp >= $last_month
                group by rv_author
                order by Count desc

            ''', {
                'repo_url': self.options.repo_url,
                'last_month': last_month,
            }))
        group.add(SQLTableReport('authors_by_commits_week', 'Authors by commits - last week',
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
        group.add(CommitsByAuthorsGraphReport(repo_url=self.options.repo_url))
        group.add(CommitsByAuthorsGraphReport(repo_url=self.options.repo_url, date_range='month'))
        group.add(CommitsByAuthorsGraphReport(repo_url=self.options.repo_url, date_range='week'))
        self.add(group)

    def create_number_of_changed_paths_reports(self):
        group = ReportGroup(name='changed_paths', title='Changed Paths Statistics')
        self.add(group)


class CommitsByAuthorsGraphReport(Report):
    """Graph number of commits committers made."""

    def __init__(self, repo_url, date_range='all'):
        name = 'commits_by_authors_graph_%s' % date_range
        title = self.make_title(date_range)
        Report.__init__(self, name, title)
        self.repo_url = repo_url
        self.date_range = date_range

    @staticmethod
    def make_title(date_range):
        if date_range == 'all':
            return 'Commits graph'
        elif date_range == 'month':
            return 'Commits graph for last month'
        elif date_range == 'week':
            return 'Commits graph for last week'
        else:
            raise Exception()

    def _get_authors(self, repo_url, cursor):
        sql = 'select distinct rv_author from revision where rv_repo_url = $url'
        params = {'url': repo_url}
        cursor.execute(sql, params)
        return [r[0] for r in cursor.fetchall()]

    def _get_data(self, repo_url, cursor, authors, date_range):
        """Return list of (author, date, count) triplets."""

        no_of_steps = 100
        seconds_in_day = 60 * 60 * 24
        def timedelta_to_seconds(t): return t.seconds + t.microseconds / 1000000 + t.days * seconds_in_day
        step = datetime.timedelta(
            seconds=(timedelta_to_seconds(date_range[1] - date_range[0])/no_of_steps)
        )
        span = step * 5
        span_days = timedelta_to_seconds(step) / seconds_in_day

        def generate_dates(d1, d2, step):
            d = d1
            while d < d2:
                yield d
                d += step

        def get_author_data(author):
            cursor.execute('''
                select min(rv_timestamp), max(rv_timestamp)
                from revision where rv_repo_url = $url
                and rv_author = $author
                and rv_timestamp >= $mindate and rv_timestamp <= $maxdate
            ''', {'url': repo_url, 'author': author,
                'mindate': date_range[0], 'maxdate': date_range[1]})
            mindate, maxdate = map(ensure_date, cursor.fetchone())
            if mindate is None and maxdate is None: return []
#            print "date range: %s %s" % (repr(mindate), repr(maxdate))
            author_data = []
            dates = list(generate_dates(mindate + step, maxdate, step))
            if maxdate not in dates: dates.append(maxdate)
            for date in dates:
                t1 = date - span
                t2 = date
                cursor.execute('''
                    select count(*)
                    from revision
                    where rv_repo_url = $url
                    and rv_author = $author
                    and rv_timestamp > $t1
                    and rv_timestamp <= $t2
                ''', {'t1': t1, 't2': t2,
                    'url': repo_url, 'author': author,})
                    #'mindate': date_range[0], 'maxdate': date_range[1]})
                cnt = cursor.fetchone()[0]
                if cnt:
                    a = cnt / (timedelta_to_seconds(t2-t1)/seconds_in_day)
                    author_data.append((author, date, a))
                elif cnt == 0:
                    author_data.append((author, date, 0))
                else:
                    raise Exception()
            return author_data

        data = []
        for author in authors:
            data += get_author_data(author)
        return data

    def get_date_range(self, cursor):
        cursor.execute('''
            select max(rv_timestamp), min(rv_timestamp)
            from revision
            where rv_repo_url = $url
        ''', {'url': self.repo_url})
        maxdate, mindate = map(ensure_date, cursor.fetchone())
        if self.date_range == 'month':
            mindate = max(mindate, maxdate - datetime.timedelta(days=30))
        elif self.date_range == 'week':
            mindate = max(mindate, maxdate - datetime.timedelta(days=7))
        return mindate, maxdate

    def generate(self, cursor, options, format='html', with_links=True):
        graph = svg.Graph()
        graph.ox_axis_title = 'Date'
        graph.oy_axis_title = 'Count'
        graph.add_series('foo')
        mindate, maxdate = self.get_date_range(cursor)
        authors = self._get_authors(self.repo_url, cursor)
        for author in authors:
            graph.add_series(author)
        graph.randomize_series_colors()
        for author, date, count in self._get_data(self.repo_url, cursor, authors, (mindate, maxdate)):
            graph.add_value(author, date, count)
        s = StringIO()
        graph.render_to_stream(s, standalone=False)
        svg_content = s.getvalue()
        return """
            <div class="report">
                <a id="%(anchor_name)s"></a>
                <h2>%(title)s</h2>
                %(go_to_top_link)s
                %(svg_content)s
            </div>
        """ % {
            'title': self.title,
            'anchor_name': self.name,
            'go_to_top_link': self.go_to_top_link(with_links),
            'svg_content': svg_content,
        }

