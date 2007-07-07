#!/usr/bin/env python2.4
# coding: utf-8

import sys, os, time
import string

import udb

import config

def connect():
    """Connect to database."""
    conn = udb.connect(*config.db_connection_params)
    assert conn is not None
    return conn


def __convert_params(paramstyle, sql, params):
    """Convert params. Input tyle is string.Template style.
    Output style is specified by first parameter.
    Returns tuple of converted values: sql, params.
    """
    if paramstyle == 'qmark':
        return convert_params_qmark(sql, params)
    elif paramstyle == 'pyformat':
        return convert_params_pyformat(sql, params)
    else:
        raise Exception("paramstyle \"%s\" is not implemented" % paramstyle)

def __convert_params_qmark(sql, params):
    """Convert template style params to qmark style params."""
    template = string.Template(sql)
    matches = template.pattern.findall(template.template)
    qmark_repl = {}
    qmark_params = []
    for match in matches:
        if match[0]: continue
        name = match[1] or match[2]
        if not name: continue
        qmark_repl[name] = '?'
        qmark_params.append(params[name])
    qmark_sql = template.substitute(qmark_repl)
    return qmark_sql, tuple(qmark_params)

def __convert_params_pyformat(sql, params):
    template = string.Template(sql)
    matches = template.pattern.findall(template.template)
    sql_pyformat_repl = {}
    for match in matches:
        if match[0]: continue
        name = match[1] or match[2]
        if not name: continue
        sql_pyformat_repl[name] = '%%(%s)s' % name
    pyformat_sql = template.substitute(sql_pyformat_repl)
    return pyformat_sql, params

def __db_timestamp(dt):
    return db_module().Timestamp(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def __table_exists(conn, table_name):
    curs = conn.cursor()
    execute(curs, paramstyle(),
        'select count(*) from sqlite_master where type = $type and name = $name',
        {'type': 'table', 'name': table_name})
    c = curs.fetchone()[0]
    if c == 0:
        return False
    elif c == 1:
        return True
    else:
        raise Exception()


def create_db_if_needed(conn):
    if not conn.table_exists('revision'):
        conn.execute_script(file('mpyss.sql').read())

