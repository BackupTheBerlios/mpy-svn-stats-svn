# config module. module globals define settings.

from pysqlite2 import dbapi2 as sqlite

db_module = sqlite
db_connection_params = ['mpyss.sqlite']

