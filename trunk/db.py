#!/usr/bin/env python2.4
# coding: utf-8

import sys, os, time
import string

import config

def connect():
    """Connect to database."""
    module = config.db_module
    conn = module.connect(*config.db_connection_params)
    assert conn is not None
    return conn

def db_module():
    return config.db_module

def paramstyle():
    return config.db_module.paramstyle

def execute(cursor, paramstyle, sql, params=None):
    """Execute something on cursor, but be paramstyle aware."""
    if params:
        sql, params = convert_params(paramstyle, sql, params)
#        print "sql: ", sql
#        print "params: ", params
        return cursor.execute(sql, params)
    else:
        return cursor.execute(sql)

def convert_params(paramstyle, sql, params):
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

def convert_params_qmark(sql, params):
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

def convert_params_pyformat(sql, params):
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


def db_timestamp(dt):
    return db_module().Timestamp(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

