#/bin/sh

mkdir -p ./tmp/

cd tmp

svn co svn://svn.berlios.de/mpy-svn-stats/trunk || exit

cp trunk/msvnstats.py ./ || exit

./msvnstats.py -o mpy-svn-stats svn://svn.berlios.de/mpy-svn-stats || exit
./msvnstats.py -o zope-stats svn://svn.zope.org/repos/main/Zope/trunk || exit

ssh mpietrzak@shell.berlios.de rm -rf /home/groups/mpy-svn-stats/htdocs/zope-stats /home/groups/mpy-svn-stats/htdocs/mpy-svn-stats || exit
scp -r ./mpy-svn-stats ./zope-stats mpietrzak@shell.berlios.de:/home/groups/mpy-svn-stats/htdocs/ || exit

cd ..

rm -rf tmp
