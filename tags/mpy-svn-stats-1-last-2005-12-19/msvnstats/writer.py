
class StatisticWriter(object):
    """Base class for all output generators.
    """

    def __init__(self, stat):
        self.config = None
        self.statistic = stat

    def configure(self, config):
        self.config = config

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.statistic)
