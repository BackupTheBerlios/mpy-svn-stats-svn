
import os
import os.path
import cStringIO as StringIO

# local
from msvnstats import GroupStatistic
from writer import StatisticWriter


"""Output writer: multiple html pages.
"""

class MultiPageHTMLWriter(StatisticWriter):
    """Base for multi-page html writers."""
    def menu_html(self, s):
        s.write(self.statistic.title)
        if isinstance(self.statistic, GroupStatistic):
            s.write('<ul>\n')
            for child in self.statistic.children:
                if child.is_wanted('multi_page_html'):
                    s.write('<li>\n')
                    child.writers['multi_page_html'].menu_html(s)
                    s.write('</li>\n')
            s.write('</ul>\n')

    def write_page(self, menu_html):
        """Write html file."""
        print u"Writing html file for %s" % self.statistic
        f = self.open_page_file()
        print u"Writing to %s" % f

    def open_page_file(self):
        fname = self.get_filename()
        return file(os.path.join(self.output_dir, fname), "w")

    def get_filename(self):
        return self.statistic.name + '.html'

    def get_output_dir(self):
        return os.path.join(self.config.output_dir, 'multi-html')

    output_dir = property(get_output_dir)


class TopMultiPageHTMLWriter(MultiPageHTMLWriter):

    def __init__(self, stat):
        StatisticWriter.__init__(self, stat)

    def write(self, run_time):
        """Write out stats recursively.
        General ideas:

         - each statistic has it's own html page
         - each statistic chooses it's own filename
         - statistic containment (groupping) doesn't alter generation proces
           besides navigation (menu)
         - general layout of page is:

           - header on top
           - tree menu to the left
           - main page on the right
           - some simple on bottom of page

        """
        self.create_output_dir()
        menu_html = self.generate_menu()
        self.generate_pages(menu_html=menu_html)

    def generate_menu(self):
        """Create (recursively) menu."""
        s = StringIO.StringIO()
        self.menu_html(s)
        return s.getvalue()

    def generate_pages(self, menu_html):
        """Write html files for each stats object."""
        flat = []
        stack = [self.statistic]
        while len(stack):
            stat = stack.pop()
            if isinstance(stat, GroupStatistic):
                stack.extend(stat.children)
            if stat.is_wanted('multi_page_html'):
                flat.append(stat)
            else:
                print u"%s is not wanted in multi-page-html mode" % stat
        print u"Generating %d pages..." % len(flat)
        for stat in flat:
            stat.writers['multi_page_html'].write_page(menu_html)

    def create_output_dir(self):
        if not os.path.exists(self.output_dir):
            print "Creating directory \"%s\"" % self.output_dir
            os.makedirs(self.output_dir)

    def get_filename(self):
        return 'index.html'


class GeneralStatsWriter(MultiPageHTMLWriter):
    """General stats multi-page html writer."""

