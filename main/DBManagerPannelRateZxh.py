# -*- coding: utf-8 -*-

import DBUtils
import Utils
import threading
import json
import time

# 设备表数据库名
TABLE_NAME_PANNEL_RATE_ZXH = "tbl_zxh_pannel_rate"
KEY_ID = "id"
KEY_VERSION = "version"
KEY_TIME = "time"          # 时间整数，如：1015
KEY_BRIGHTNESS = "brightness"    # 亮度
KEY_COLORTEMP = "colortemp"  # 色温
KEY_LOCATION = "location"    # 地点


class DBManagerPannelRateZxh(object):
    __instance = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls):
        if DBManagerPannelRateZxh.__instance is None:
            DBManagerPannelRateZxh.__lock.acquire()
            try:
                if DBManagerPannelRateZxh.__instance is None:
                    DBManagerPannelRateZxh.__instance = object.__new__(cls)
            finally:
                DBManagerPannelRateZxh.__lock.release()
        return DBManagerPannelRateZxh.__instance

    def __init__(self):
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_PANNEL_RATE_ZXH
        self.tableversion = 1
        self.createTable()

    def createTable(self):
        Utils.logDebug("->create tbl_zxh_pannel_rate")
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
                (None, self.tableversion, 0, 3850, 1403, ''),
                (None, self.tableversion, 1, 3850, 1403, ''),
                (None, self.tableversion, 2, 3850, 1403, ''),
                (None, self.tableversion, 3, 3850, 1403, ''),
                (None, self.tableversion, 4, 3830, 2360, ''),
                (None, self.tableversion, 5, 3830, 2360, ''),
                (None, self.tableversion, 6, 3830, 2360, ''),
                (None, self.tableversion, 7, 3830, 2360, ''),
                (None, self.tableversion, 8, 3530, 2798, ''),
                (None, self.tableversion, 9, 3530, 2798, ''),
                (None, self.tableversion, 10, 3530, 2798, ''),
                (None, self.tableversion, 11, 3530, 2798, ''),
                (None, self.tableversion, 12, 2930, 3053, ''),
                (None, self.tableversion, 13, 2930, 3053, ''),
                (None, self.tableversion, 14, 2930, 3053, ''),
                (None, self.tableversion, 15, 2930, 3053, ''),
                (None, self.tableversion, 16, 2230, 3083, ''),
                (None, self.tableversion, 17, 2230, 3083, ''),
                (None, self.tableversion, 18, 2230, 3083, ''),
                (None, self.tableversion, 19, 2230, 3083, ''),
                (None, self.tableversion, 20, 1796, 3250, ''),
                (None, self.tableversion, 21, 1796, 3250, ''),
                (None, self.tableversion, 22, 1796, 3250, ''),
                (None, self.tableversion, 23, 1796, 3250, ''),
                (None, self.tableversion, 24, 1420, 3250, ''),
                (None, self.tableversion, 25, 1420, 3250, ''),
                (None, self.tableversion, 26, 1420, 3250, ''),
                (None, self.tableversion, 27, 1420, 3250, ''),
                (None, self.tableversion, 28, 1200, 3410, ''),
                (None, self.tableversion, 29, 1200, 3410, ''),
                (None, self.tableversion, 30, 1200, 3410, ''),
                (None, self.tableversion, 31, 1200, 3410, ''),
                (None, self.tableversion, 32, 830, 3545, ''),
                (None, self.tableversion, 33, 830, 3545, ''),
                (None, self.tableversion, 34, 830, 3545, ''),
                (None, self.tableversion, 35, 830, 3545, ''),
                (None, self.tableversion, 36, 615, 3710, ''),
                (None, self.tableversion, 37, 615, 3710, ''),
                (None, self.tableversion, 38, 615, 3710, ''),
                (None, self.tableversion, 39, 615, 3710, ''),
                (None, self.tableversion, 40, 370, 3750, ''),
                (None, self.tableversion, 41, 370, 3750, ''),
                (None, self.tableversion, 42, 370, 3750, ''),
                (None, self.tableversion, 43, 370, 3750, ''),
                (None, self.tableversion, 44, 155, 3750, ''),
                (None, self.tableversion, 45, 155, 3750, ''),
                (None, self.tableversion, 46, 155, 3750, ''),
                (None, self.tableversion, 47, 155, 3750, ''),
                (None, self.tableversion, 48, 0, 3950, ''),
                (None, self.tableversion, 49, 0, 3950, ''),
                (None, self.tableversion, 50, 0, 3950, ''),
                (None, self.tableversion, 51, 0, 3950, ''),
                (None, self.tableversion, 52, 0, 3900, ''),
                (None, self.tableversion, 53, 0, 3900, ''),
                (None, self.tableversion, 54, 0, 3900, ''),
                (None, self.tableversion, 55, 0, 3900, ''),
                (None, self.tableversion, 56, 0, 3908, ''),
                (None, self.tableversion, 57, 0, 3908, ''),
                (None, self.tableversion, 58, 0, 3908, ''),
                (None, self.tableversion, 59, 0, 3908, ''),
                (None, self.tableversion, 100, 0, 3908, ''),
                (None, self.tableversion, 101, 0, 3908, ''),
                (None, self.tableversion, 102, 0, 3908, ''),
                (None, self.tableversion, 103, 0, 3908, ''),
                (None, self.tableversion, 104, 0, 3907, ''),
                (None, self.tableversion, 105, 0, 3907, ''),
                (None, self.tableversion, 106, 0, 3907, ''),
                (None, self.tableversion, 107, 0, 3907, ''),
                (None, self.tableversion, 108, 35, 4070, ''),
                (None, self.tableversion, 109, 35, 4070, ''),
                (None, self.tableversion, 110, 35, 4070, ''),
                (None, self.tableversion, 111, 35, 4070, ''),
                (None, self.tableversion, 112, 235, 3860, ''),
                (None, self.tableversion, 113, 235, 3860, ''),
                (None, self.tableversion, 114, 235, 3860, ''),
                (None, self.tableversion, 115, 235, 3860, ''),
                (None, self.tableversion, 116, 455, 3840, ''),
                (None, self.tableversion, 117, 455, 3840, ''),
                (None, self.tableversion, 118, 455, 3840, ''),
                (None, self.tableversion, 119, 455, 3840, ''),
                (None, self.tableversion, 120, 697, 3700, ''),
                (None, self.tableversion, 121, 697, 3700, ''),
                (None, self.tableversion, 122, 697, 3700, ''),
                (None, self.tableversion, 123, 697, 3700, ''),
                (None, self.tableversion, 124, 880, 3590, ''),
                (None, self.tableversion, 125, 880, 3590, ''),
                (None, self.tableversion, 126, 880, 3590, ''),
                (None, self.tableversion, 127, 880, 3590, ''),
                (None, self.tableversion, 128, 1145, 3480, ''),
                (None, self.tableversion, 129, 1145, 3480, ''),
                (None, self.tableversion, 130, 1145, 3480, ''),
                (None, self.tableversion, 131, 1145, 3480, ''),
                (None, self.tableversion, 132, 1450, 3280, ''),
                (None, self.tableversion, 133, 1450, 3280, ''),
                (None, self.tableversion, 134, 1450, 3280, ''),
                (None, self.tableversion, 135, 1450, 3280, ''),
                (None, self.tableversion, 136, 1890, 3240, ''),
                (None, self.tableversion, 137, 1890, 3240, ''),
                (None, self.tableversion, 138, 1890, 3240, ''),
                (None, self.tableversion, 139, 1890, 3240, ''),
                (None, self.tableversion, 140, 2219, 2980, ''),
                (None, self.tableversion, 141, 2219, 2980, ''),
                (None, self.tableversion, 142, 2219, 2980, ''),
                (None, self.tableversion, 143, 2219, 2980, ''),
                (None, self.tableversion, 144, 3000, 2930, ''),
                (None, self.tableversion, 145, 3000, 2930, ''),
                (None, self.tableversion, 146, 3000, 2930, ''),
                (None, self.tableversion, 147, 3000, 2930, ''),
                (None, self.tableversion, 148, 3500, 2630, ''),
                (None, self.tableversion, 149, 3500, 2630, ''),
                (None, self.tableversion, 150, 3500, 2630, ''),
                (None, self.tableversion, 151, 3500, 2630, ''),
                (None, self.tableversion, 152, 4155, 2440, ''),
                (None, self.tableversion, 153, 4155, 2440, ''),
                (None, self.tableversion, 154, 4155, 2440, ''),
                (None, self.tableversion, 155, 4155, 2440, ''),
                (None, self.tableversion, 156, 5300, 2165, ''),
                (None, self.tableversion, 157, 5300, 2165, ''),
                (None, self.tableversion, 158, 5300, 2165, ''),
                (None, self.tableversion, 159, 5300, 2165, '')
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
        sql = "select brightness, colortemp from " + self.tablename + " where `time` == %d order by id" % t

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
