#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import os
import GlobalVars
import Utils
import multiprocessing


'''SQLite数据库是一款非常小巧的嵌入式开源数据库软件，也就是说
没有独立的维护进程，所有的维护都来自于程序本身。
在python中，使用sqlite3创建数据库的连接，当我们指定的数据库文件不存在的时候
连接对象会自动创建数据库文件；如果数据库文件已经存在，则连接对象不会再创建
数据库文件，而是直接打开该数据库文件。
    连接对象可以是硬盘上面的数据库文件，也可以是建立在内存中的，在内存中的数据库
    执行完任何操作后，都不需要提交事务的(commit)

    创建在硬盘上面： conn = sqlite3.connect('c:\\test\\test.db')
    创建在内存上面： conn = sqlite3.connect('"memory:')

    下面我们一硬盘上面创建数据库文件为例来具体说明：
    conn = sqlite3.connect('c:\\test\\hongten.db')
    其中conn对象是数据库链接对象，而对于数据库链接对象来说，具有以下操作：

        commit()            --事务提交
        rollback()          --事务回滚
        close()             --关闭一个数据库链接
        cursor()            --创建一个游标

    cu = conn.cursor()
    这样我们就创建了一个游标对象：cu
    在sqlite3中，所有sql语句的执行都要在游标对象的参与下完成
    对于游标对象cu，具有以下具体操作：

        execute()           --执行一条sql语句
        executemany()       --执行多条sql语句
        close()             --游标关闭
        fetchone()          --从结果中取出一条记录
        fetchmany()         --从结果中取出多条记录
        fetchall()          --从结果中取出所有记录
        scroll()            --游标滚动

'''

__lock = multiprocessing.Semaphore(1)

# 是否打印sql
SHOW_SQL = True


def __get_conn(path):
    '''获取到数据库的连接对象，参数为数据库文件的绝对路径
    如果传递的参数是存在，并且是文件，那么就返回硬盘上面改
    路径下的数据库文件的连接对象；否则，返回内存中的数据接
    连接对象'''
    conn = sqlite3.connect(path)
    conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
    if os.path.exists(path) and os.path.isfile(path):
        # Utils.logDebug('硬盘上面:[{}]'.format(path))
        return conn
    else:
        conn = None
        # Utils.logDebug('内存上面:[:memory:]')
        return sqlite3.connect(':memory:')


# 配置-数据库连接
def get_conn():
    return __get_conn('../etc/host.db')


# 实时-数据库连接
def get_conn_rt():
    return __get_conn('../etc/rt.db')   # 文件名修改，需同步修改其他引用的文件main.py


def get_cursor(conn):
    '''该方法是获取数据库的游标对象，参数为数据库的连接对象
    如果数据库的连接对象不为None，则返回数据库连接对象所创
    建的游标对象；否则返回一个游标对象，该对象是内存中数据
    库连接对象所创建的游标对象'''
    if conn is not None:
        return conn.cursor()
    else:
        return __get_conn('').cursor()

###############################################################
####            创建|删除表操作     START
###############################################################
def drop_table(conn, table):
    '''如果表存在,则删除表，如果表中存在数据的时候，使用该
    方法的时候要慎用！'''
    __lock.acquire()
    cu = None
    try:
        if table is not None and table != '':
            sql = 'DROP TABLE IF EXISTS ' + table
            if SHOW_SQL:
                Utils.logDebug('执行sql:[{}]'.format(sql))
            cu = get_cursor(conn)
            cu.execute(sql)
            conn.commit()
            Utils.logDebug('删除数据库表[{}]成功!'.format(table))
        else:
            Utils.logError('table not exist')
    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()


def create_table(conn, sql):
    '''创建数据库表：'''
    __lock.acquire()
    cu = None
    try:
        if sql is not None and sql != '':
            cu = get_cursor(conn)
            if SHOW_SQL:
                Utils.logDebug('执行sql:[{}]'.format(sql))
            cu.execute(sql)
            conn.commit()
            # _my_commit(conn)
            Utils.logDebug('创建数据库表[*]成功!')
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()

###############################################################
####            创建|删除表操作     END
###############################################################
def close_all(conn, cu):
    '''关闭数据库游标对象和数据库连接对象'''
    try:
        if cu is not None:
            cu.close()
            cu = None
    finally:
        if conn is not None:
            conn.close()
            conn = None

###############################################################
####            数据库操作CRUD     START
###############################################################
def save(conn, sql, data):
    '''插入数据'''
    __lock.acquire()
    cu = None
    try:
        success = False
        if sql is not None and sql != '':
            if data is not None:
                cu = get_cursor(conn)
                for d in data:
                    if SHOW_SQL:
                        Utils.logDebug('执行sql:[{}],参数:[{}]'.format(sql, d))
                    cu.execute(sql, d)
                    conn.commit()
                    success = True
            return success
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
            return success

    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()

def fetchall(conn, sql):
    '''查询所有数据'''
    cu = None
    try:
        if sql is not None and sql != '':
            cu = get_cursor(conn)
            if SHOW_SQL:
                Utils.logDebug('执行sql:[{}]'.format(sql))
            cu.execute(sql)
            r = cu.fetchall()
            # if r != None and len(r) > 0:
            #     for e in range(len(r)):
            #         Utils.logDebug(r[e])
            return r
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
    finally:
        close_all(conn, cu)


def fetchone(conn, sql, data):
    '''查询一条数据'''
    cu = None
    try:
        if sql is not None and sql != '':
            if data is not None:
                #Do this instead
                d = (data,)
                cu = get_cursor(conn)
                if SHOW_SQL:
                    Utils.logDebug('执行sql:[{}],参数:[{}]'.format(sql, data))
                cu.execute(sql, d)
                r = cu.fetchone()
                # if r != None and len(r) > 0:
                #     for e in range(len(r)):
                #         Utils.logDebug(r[e])
                return r
            else:
                Utils.logDebug('the [{}] equal None!'.format(data))
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
    finally:
        close_all(conn, cu)


def update(conn, sql, data):
    '''更新数据'''
    __lock.acquire()
    cu = None
    try:
        success = False
        if sql is not None and sql != '':
            if data is not None:
                cu = get_cursor(conn)
                for d in data:
                    if SHOW_SQL:
                        Utils.logDebug('执行sql:[{}],参数:[{}]'.format(sql, d))
                    cu.execute(sql, d)
                    conn.commit()
                    success = True
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
        return success
    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()


def update_all(conn, sql):
    '''更新所有数据'''
    __lock.acquire()
    cu = None
    try:
        success = False
        if sql is not None and sql != '':
            cu = get_cursor(conn)
            if SHOW_SQL:
                Utils.logDebug('执行sql:[{}]'.format(sql))
            cu.execute(sql)
            conn.commit()
            success = True
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
        return success
    except Exception as err:
        Utils.logError("update_all error: %s" % err)
        return False
    finally:
        close_all(conn, cu)
        __lock.release()

def count(conn, sql):
    cu = None
    try:
        if sql is not None and sql != '':
            cu = get_cursor(conn)
            if SHOW_SQL:
                Utils.logDebug('执行sql:[{}]'.format(sql))
            cu.execute(sql)
            r = cu.fetchone()
            if r != None and len(r) > 0:
                return r[0]
            return 0
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
    finally:
        close_all(conn, cu)

def delete(conn, sql, data):
    '''删除数据'''
    __lock.acquire()
    cu = None
    try:
        if sql is not None and sql != '':
            if data is not None:
                cu = get_cursor(conn)
                for d in data:
                    if SHOW_SQL:
                        Utils.logDebug('执行sql:[{}],参数:[{}]'.format(sql, d))
                    cu.execute(sql, d)
                    conn.commit()
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))

    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()

def deleteone(conn, sql):
    '''删除数据'''
    __lock.acquire()
    cu = None
    try:
        success = False
        if sql is not None and sql != '':
            cu = get_cursor(conn)
            cu.execute(sql)
            conn.commit()
            success = True
        else:
            Utils.logDebug('the [{}] is empty or equal None!'.format(sql))
        return success
    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()


def executemany(conn, sql, data):
    '''批量执行多次sql'''
    __lock.acquire()
    cu = None
    try:
        success = False
        if sql:
            cu = get_cursor(conn)
            cu.executemany(sql, data)
            conn.commit()
            success = True
        else:
            Utils.logInfo('the [{}] is empty or equal None!'.format(sql))
        return success
    except:
        raise
    finally:
        close_all(conn, cu)
        __lock.release()
