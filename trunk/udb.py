# $Id: udb.py 5 2007-06-18 00:53:42Z mpietrzak $

import re


def connect(type, host, port, database, username, password):
    conn_functions = {
            'oracle': connect_oracle,
            'postgresql': connect_postgresql,
            'sqlite': connect_sqlite,
            }
    conn_function = conn_functions[type]
    return conn_function(host, port, database, username, password)


def connect_oracle(host, port, database, username, password):
    import cx_Oracle
    if host and port:
        dsn = cx_Oracle.makedsn(host, port, database)
    else:
        dsn = database
    conn = cx_Oracle.connect(username, password, dsn)
    return Connection('oracle', cx_Oracle, conn)


def connect_postgresql(host, port, database, username, password):
    dsn = ''
    if host: dsn += "host='%s'" % host
    if port: dsn += "port='%d'" % port
    if database: dsn += "dbname='%s'" % database
    if username: dsn += "user='%s'" % username
    if password: dsn += "password='%s'" % password
    import psycopg2
    conn = psycopg2.connect(dsn)
    return Connection('postgresql', psycopg2, conn)


def connect_sqlite(host, port, database, username, password):
    import sqlite3
    conn = sqlite3.connect(database)
    return SQLiteConnection(sqlite3, conn)


class SQLException(Exception):
    def __init__(self, cause):
        self.cause = cause


class Connection:

    def __init__(self, driver_name, module, conn):
        self.paramstyle = module.paramstyle
        self.conn = conn
        self.driver_name = driver_name
        
    def cursor(self):
        return Cursor(self)
        
    def execute_script(self, script):
        cmds = [s.strip() for s in script.split(';')]
        curs = self.cursor()
        for cmd in cmds:
            curs.execute(cmd)

    def commit(self):
        return self.conn.commit()



class SQLiteConnection(Connection):
    def __init__(self, module, conn):
        Connection.__init__(self, 'sqlite', module, conn)

    def table_exists(conn, table_name):
        curs = conn.cursor()
        curs.execute(
            'select count(*) from sqlite_master where type = $type and name = $name',
            {'type': 'table', 'name': table_name})
        c = curs.fetchone()[0]
        if c == 0:
            return False
        elif c == 1:
            return True
        else:
            raise SQLException()
    

class Cursor:
    
    re_placeholder = r'(\$([a-zA-Z_][a-zA-Z0-9_]+))'
    
    def __init__(self, conn):
        self.conn = conn
        self.cursor = self.conn.conn.cursor()
        self.re_placeholder_re = re.compile(self.re_placeholder)
        
    def execute(self, sql, params=None):
        if params:
            sql, params = self._convert_command(sql, params)
            return self.cursor.execute(sql, params)
        else:
            return self.cursor.execute(sql)
    
    def _convert_command(self, sql, params):
        converters = {
                'named': self._convert_to_named,
                'pyformat': self._convert_to_pyformat,
                'qmark': self._convert_to_qmark,
            }
        converter = converters[self.conn.paramstyle]
        return converter(sql, params)
        
    def _convert_to_named(self, sql, params):
        sql = self.re_placeholder_re.sub(r':\2', sql)
        return (sql, params)
    
    def _convert_to_pyformat(self, sql, params):
        sql = self.re_placeholder_re.sub(r'%(\2)s', sql)
        return (sql, params)

    def _convert_to_qmark(self, sql, params):
        assert params
        matches = self.re_placeholder_re.findall(sql)
        qmark_params = []
        for match in matches:
            placeholder_name = match[1]
            qmark_params.append(params[placeholder_name])
        sql = self.re_placeholder_re.sub(r'?', sql)
        return (sql, qmark_params)
    
    def fetchone(self):
        return self.cursor.fetchone()
    
    def fetchall(self):
        return self.cursor.fetchall()

    def fetchmany(self, cnt):
        return self.cursor.fetchmany(cnt)

    def get_description(self):
        return self.cursor.description

    description = property(get_description)

    def __iter__(self):
        return self

    def next(self):
        return self.cursor.next()

