



all: mpy-svn-stats-stats



zope: zope-stats-download zope-stats-import zope-stats-generate


mpy-svn-stats-stats: mpy-svn-stats.svnlog
	./mpyss.py -u svn://svn.berlios.de/mpy-svn-stats/ -i mpy-svn-stats.svnlog

mpy-svn-stats.svnlog:
	svn -v --xml svn://svn.berlios.de


zope-stats-download:
	svn -v --xml log svn://svn.zope.org/repos/main/Zope3 | ./filter.py > zope3.svnlog

zope-stats-import:
	[ -f zope3.svnlog ] && ./mpyss.py -i zope3.svnlog -u svn://svn.zope.org/repos/main/Zope3

zope-stats-generate:
	./mpyss.py -r yes -u svn://svn.zope.org/repos/main/Zope3

