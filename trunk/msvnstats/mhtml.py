
import os
import os.path

# local
from writer import StatisticWriter


"""Output writer: multiple html pages.
"""

class MultiPageHTMLWriter(StatisticWriter):

    def __init__(self, stat):
        StatisticWriter.__init__(self, stat)

    def write(self, run_time):
        self.create_output_dir()

    def create_output_dir(self):
        self.output_dir = os.path.join(self.config.output_dir, 'multi-html')
        if not os.path.exists(self.output_dir):
            print "Creating directory \"%s\"" % self.output_dir
            os.makedirs(self.output_dir)


class GeneralStatsWriter(StatisticWriter):
    """General stats multi-page html writer."""

