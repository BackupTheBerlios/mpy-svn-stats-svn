

default: mpy-svn-stats-stats


mpy-svn-stats-stats-generate:
	./mpyss.py -u svn://svn.berlios.de/mpy-svn-stats/ -r yes

mpy-svn-stats-stats-import:
	./mpyss.py -u svn://svn.berlios.de/mpy-svn-stats/ -i mpy-svn-stats.svnlog --no-reports

.PHONY: mpy-svn-stats.svnlog
mpy-svn-stats.svnlog:
	svn -v --xml log svn://svn.berlios.de/mpy-svn-stats/ | ./filter.py > mpy-svn-stats.svnlog

.PHONY: zope3.svnlog
zope3.svnlog:
	svn -v --xml log svn://svn.zope.org/repos/main/Zope3 | ./filter.py > zope3.svnlog

zope-stats-import:
	[ -f zope3.svnlog ] && ./mpyss.py -i zope3.svnlog -u svn://svn.zope.org/repos/main/Zope3

zope-stats-generate:
	./mpyss.py -r yes -u svn://svn.zope.org/repos/main/Zope3



tags:
	exuberant-ctags -R *
