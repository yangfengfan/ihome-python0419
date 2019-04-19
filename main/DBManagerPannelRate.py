# -*- coding: utf-8 -*-

import DBUtils
import Utils
import threading
import json
import time

# 设备表数据库名
TABLE_NAME_PANNEL_RATE = "tbl_pannel_rate"
KEY_ID = "id"
KEY_VERSION = "version"
KEY_TIME = "time"          # 时间整数，如：1015
KEY_BRIGHTNESS = "brightness"    # 亮度
KEY_COLORTEMP = "colortemp"  # 色温
KEY_LOCATION = "location"    # 地点


class DBManagerPannelRate(object):
    __instance = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls):
        if DBManagerPannelRate.__instance is None:
            DBManagerPannelRate.__lock.acquire()
            try:
                if DBManagerPannelRate.__instance is None:
                    DBManagerPannelRate.__instance = object.__new__(cls)
            finally:
                DBManagerPannelRate.__lock.release()
        return DBManagerPannelRate.__instance

    def __init__(self):
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_PANNEL_RATE
        self.tableversion = 1
        self.createTable()

    def createTable(self):
        Utils.logDebug("->create tbl_pannel_rate")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_TIME + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_BRIGHTNESS + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_COLORTEMP + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_LOCATION + "` varchar(50)"
        create_table_sql += " )"
        conn = DBUtils.get_conn()
        DBUtils.drop_table(conn, self.tablename)
        conn = DBUtils.get_conn()
        DBUtils.create_table(conn, create_table_sql)
        self.check_to_insert()

    def check_to_insert(self):
        check_sql = "SELECT * FROM " + self.tablename
        conn = DBUtils.get_conn()
        fetch_result = DBUtils.fetchall(conn, check_sql)
        if not fetch_result:
            # 新增数据
            save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?)"
            value_list = [
                (None, self.tableversion, 0, 0, 0, ''),
                (None, self.tableversion, 15, 0, 0, ''),
                (None, self.tableversion, 30, 0, 0, ''),
                (None, self.tableversion, 45, 0, 0, ''),
                (None, self.tableversion, 100, 0, 0, ''),
                (None, self.tableversion, 115, 0, 0, ''),
                (None, self.tableversion, 130, 0, 0, ''),
                (None, self.tableversion, 145, 0, 0, ''),
                (None, self.tableversion, 200, 0, 0, ''),
                (None, self.tableversion, 215, 0, 0, ''),
                (None, self.tableversion, 230, 0, 0, ''),
                (None, self.tableversion, 245, 0, 0, ''),
                (None, self.tableversion, 300, 0, 0, ''),
                (None, self.tableversion, 315, 0, 0, ''),
                (None, self.tableversion, 330, 0, 0, ''),
                (None, self.tableversion, 345, 0, 0, ''),
                (None, self.tableversion, 400, 0, 0, ''),
                (None, self.tableversion, 415, 0, 0, ''),
                (None, self.tableversion, 430, 0, 0, ''),
                (None, self.tableversion, 445, 0, 0, ''),
                (None, self.tableversion, 500, 1, 0, ''),
                (None, self.tableversion, 515, 1, 0, ''),
                (None, self.tableversion, 530, 1, 1, ''),
                (None, self.tableversion, 545, 1, 4, ''),
                (None, self.tableversion, 600, 2, 8, ''),
                (None, self.tableversion, 615, 3, 12, ''),
                (None, self.tableversion, 630, 4, 16, ''),
                (None, self.tableversion, 645, 6, 24, ''),
                (None, self.tableversion, 700, 8, 32, ''),
                (None, self.tableversion, 715, 10, 40, ''),
                (None, self.tableversion, 730, 11, 49, ''),
                (None, self.tableversion, 745, 12, 53, ''),
                (None, self.tableversion, 800, 13, 57, ''),
                (None, self.tableversion, 815, 14, 61, ''),
                (None, self.tableversion, 830, 14, 62, ''),
                (None, self.tableversion, 845, 14, 66, ''),
                (None, self.tableversion, 900, 15, 70, ''),
                (None, self.tableversion, 915, 16, 74, ''),
                (None, self.tableversion, 930, 17, 78, ''),
                (None, self.tableversion, 945, 17, 78, ''),
                (None, self.tableversion, 1000, 18, 82, ''),
                (None, self.tableversion, 1015, 18, 82, ''),
                (None, self.tableversion, 1030, 18, 82, ''),
                (None, self.tableversion, 1045, 18, 82, ''),
                (None, self.tableversion, 1100, 18, 82, ''),
                (None, self.tableversion, 1115, 18, 82, ''),
                (None, self.tableversion, 1130, 18, 82, ''),
                (None, self.tableversion, 1145, 18, 82, ''),
                (None, self.tableversion, 1200, 18, 82, ''),
                (None, self.tableversion, 1215, 18, 82, ''),
                (None, self.tableversion, 1230, 18, 82, ''),
                (None, self.tableversion, 1245, 18, 82, ''),
                (None, self.tableversion, 1300, 18, 82, ''),
                (None, self.tableversion, 1315, 17, 78, ''),
                (None, self.tableversion, 1330, 17, 78, ''),
                (None, self.tableversion, 1345, 16, 74, ''),
                (None, self.tableversion, 1400, 15, 70, ''),
                (None, self.tableversion, 1415, 14, 66, ''),
                (None, self.tableversion, 1430, 14, 62, ''),
                (None, self.tableversion, 1445, 14, 61, ''),
                (None, self.tableversion, 1500, 13, 57, ''),
                (None, self.tableversion, 1515, 12, 53, ''),
                (None, self.tableversion, 1530, 11, 49, ''),
                (None, self.tableversion, 1545, 10, 40, ''),
                (None, self.tableversion, 1600, 8, 32, ''),
                (None, self.tableversion, 1615, 6, 24, ''),
                (None, self.tableversion, 1630, 4, 16, ''),
                (None, self.tableversion, 1645, 3, 12, ''),
                (None, self.tableversion, 1700, 2, 8, ''),
                (None, self.tableversion, 1715, 1, 4, ''),
                (None, self.tableversion, 1730, 1, 1, ''),
                (None, self.tableversion, 1745, 0, 1, ''),
                (None, self.tableversion, 1800, 0, 1, ''),
                (None, self.tableversion, 1815, 0, 0, ''),
                (None, self.tableversion, 1830, 0, 0, ''),
                (None, self.tableversion, 1845, 0, 0, ''),
                (None, self.tableversion, 1900, 0, 0, ''),
                (None, self.tableversion, 1915, 0, 0, ''),
                (None, self.tableversion, 1930, 0, 0, ''),
                (None, self.tableversion, 1945, 0, 0, ''),
                (None, self.tableversion, 2000, 0, 0, ''),
                (None, self.tableversion, 2015, 0, 0, ''),
                (None, self.tableversion, 2030, 0, 0, ''),
                (None, self.tableversion, 2045, 0, 0, ''),
                (None, self.tableversion, 2100, 0, 0, ''),
                (None, self.tableversion, 2115, 0, 0, ''),
                (None, self.tableversion, 2130, 0, 0, ''),
                (None, self.tableversion, 2145, 0, 0, ''),
                (None, self.tableversion, 2200, 0, 0, ''),
                (None, self.tableversion, 2215, 0, 0, ''),
                (None, self.tableversion, 2230, 0, 0, ''),
                (None, self.tableversion, 2245, 0, 0, ''),
                (None, self.tableversion, 2300, 0, 0, ''),
                (None, self.tableversion, 2315, 0, 0, ''),
                (None, self.tableversion, 2330, 0, 0, ''),
                (None, self.tableversion, 2345, 0, 0, ''),
                (None, self.tableversion, 2400, 0, 0, ''),
            ]
            conn = DBUtils.get_conn()
            DBUtils.save(conn, save_sql, value_list)

    # 检查数据库文件状态
    # host.db存放配置数据
    # 如果数据库文件损坏，fetchall()应抛出异常
    def checkDBHealthy(self):
        conn = DBUtils.get_conn()
        sql = "select * from " + self.tablename
        DBUtils.fetchall(conn, sql)

    def queryByTime(self, t):
        sql = "select brightness, colortemp from " + self.tablename + " where ABS(`time` - %d ) <= 15 order by id" % t

        try:
            conn = DBUtils.get_conn()
            results = DBUtils.fetchall(conn, sql)
            if results:
                return results[0]
            else:
                return None

        except:
            Utils.logException('queryByTime()异常 ')
            return None
