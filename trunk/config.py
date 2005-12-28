# config module. module globals define settings.

#from pysqlite2 import dbapi2 as sqlite
import psycopg

db_module = psycopg 
db_connection_params = ['dbname=mpyss user=mpyss']

