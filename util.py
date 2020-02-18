
import sys
import sqlite3
from tornado import ioloop

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def print_with_carriage_return(s):
    sys.stdout.write('\r' + s)
    sys.stdout.flush()

async def db_connect(connect_str:str):
    current_loop = ioloop.IOLoop.current()
    conn = await current_loop.run_in_executor(None, sqlite3.connect, connect_str)
    return conn

async def db_execute(conn:sqlite3.Connection, sql_str:str):
    current_loop = ioloop.IOLoop.current()
    cursor = await current_loop.run_in_executor(None, conn.cursor)
    await current_loop.run_in_executor(None, cursor.execute, sql_str)
    return cursor

async def db_commit(conn:sqlite3.Connection):
    current_loop = ioloop.IOLoop.current()
    await current_loop.run_in_executor(None, conn.commit)

async def db_rollback(conn:sqlite3.Connection):
    current_loop = ioloop.IOLoop.current()
    await current_loop.run_in_executor(None, conn.rollback)

async def db_fetchall(cursor:sqlite3.Cursor):
    current_loop = ioloop.IOLoop.current()
    return await current_loop.run_in_executor(None, cursor.fetchall)
