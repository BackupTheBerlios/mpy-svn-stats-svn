
import os
import os.path

# local
from writer import StatisticWriter


"""Output writer: multiple html pages.
"""

class MultiPageHTMLWriter(StatisticWriter):
    """Base for multi-page html writers."""
    pass


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
        self.generate_menu()
        self.generate_pages()

    def generate_menu(self):
        """Create (recursively) menu."""
        pass

    def generate_pages(self):
        """Write html files for each stats object."""
        pass

    def create_output_dir(self):
        self.output_dir = os.path.join(self.config.output_dir, 'multi-html')
        if not os.path.exists(self.output_dir):
            print "Creating directory \"%s\"" % self.output_dir
            os.makedirs(self.output_dir)


class GeneralStatsWriter(StatisticWriter):
    """General stats multi-page html writer."""

