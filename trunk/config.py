# config module. module globals define settings.

#from pysqlite2 import dbapi2 as sqlite
import sqlite3

db_module = sqlite3
db_connection_params = ['mpyss.sqlite']


def initdb():
    schema_sql = file('mpyss.sql').read()
    c = sqlite3.connect('mpyss.sqlite')
    for sql_cmd in schema_sql.split(';'):
        c.execute(sql_cmd)


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == 'initdb':
        initdb()
    else:
        print "usage: initdb -> init db"
