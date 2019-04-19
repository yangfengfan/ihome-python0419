# -*- coding: utf-8 -*-

import DBUtils
import Utils
import threading
import json
import time

# 设备表数据库名
TABLE_NAME_PANNEL_RATE_ZXL = "tbl_zxl_pannel_rate"
KEY_ID = "id"
KEY_VERSION = "version"
KEY_TIME = "time"          # 时间整数，如：1015
KEY_BRIGHTNESS = "brightness"    # 亮度
KEY_COLORTEMP = "colortemp"  # 色温
KEY_LOCATION = "location"    # 地点


class DBManagerPannelRateZxl(object):
    __instance = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls):
        if DBManagerPannelRateZxl.__instance is None:
            DBManagerPannelRateZxl.__lock.acquire()
            try:
                if DBManagerPannelRateZxl.__instance is None:
                    DBManagerPannelRateZxl.__instance = object.__new__(cls)
            finally:
                DBManagerPannelRateZxl.__lock.release()
        return DBManagerPannelRateZxl.__instance

    def __init__(self):
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_PANNEL_RATE_ZXL
        self.tableversion = 1
        self.createTable()

    def createTable(self):
        Utils.logDebug("->create tbl_zxl_pannel_rate")
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
                (None, self.tableversion, 0, 65, 0, ''),
                (None, self.tableversion, 1, 65, 0, ''),
                (None, self.tableversion, 2, 65, 0, ''),
                (None, self.tableversion, 3, 65, 0, ''),
                (None, self.tableversion, 4, 84, 0, ''),
                (None, self.tableversion, 5, 84, 0, ''),
                (None, self.tableversion, 6, 84, 0, ''),
                (None, self.tableversion, 7, 84, 0, ''),
                (None, self.tableversion, 8, 109, 0, ''),
                (None, self.tableversion, 9, 109, 0, ''),
                (None, self.tableversion, 10, 109, 0, ''),
                (None, self.tableversion, 11, 109, 0, ''),
                (None, self.tableversion, 12, 140, 0, ''),
                (None, self.tableversion, 13, 140, 0, ''),
                (None, self.tableversion, 14, 140, 0, ''),
                (None, self.tableversion, 15, 140, 0, ''),
                (None, self.tableversion, 16, 203, 0, ''),
                (None, self.tableversion, 17, 203, 0, ''),
                (None, self.tableversion, 18, 203, 0, ''),
                (None, self.tableversion, 19, 203, 0, ''),
                (None, self.tableversion, 20, 286, 0, ''),
                (None, self.tableversion, 21, 286, 0, ''),
                (None, self.tableversion, 22, 286, 0, ''),
                (None, self.tableversion, 23, 286, 0, ''),
                (None, self.tableversion, 24, 419, 0, ''),
                (None, self.tableversion, 25, 419, 0, ''),
                (None, self.tableversion, 26, 419, 0, ''),
                (None, self.tableversion, 27, 419, 0, ''),
                (None, self.tableversion, 28, 661, 0, ''),
                (None, self.tableversion, 29, 661, 0, ''),
                (None, self.tableversion, 30, 661, 0, ''),
                (None, self.tableversion, 31, 661, 0, ''),
                (None, self.tableversion, 32, 917, 0, ''),
                (None, self.tableversion, 33, 917, 0, ''),
                (None, self.tableversion, 34, 917, 0, ''),
                (None, self.tableversion, 35, 917, 0, ''),
                (None, self.tableversion, 36, 1199, 54, ''),
                (None, self.tableversion, 37, 1199, 54, ''),
                (None, self.tableversion, 38, 1199, 54, ''),
                (None, self.tableversion, 39, 1199, 54, ''),
                (None, self.tableversion, 40, 1806, 289, ''),
                (None, self.tableversion, 41, 1806, 289, ''),
                (None, self.tableversion, 42, 1806, 289, ''),
                (None, self.tableversion, 43, 1806, 289, ''),
                (None, self.tableversion, 44, 3850, 403, ''),
                (None, self.tableversion, 45, 3850, 403, ''),
                (None, self.tableversion, 46, 3850, 403, ''),
                (None, self.tableversion, 47, 3850, 403, ''),
                (None, self.tableversion, 48, 3830, 1060, ''),
                (None, self.tableversion, 49, 3830, 1060, ''),
                (None, self.tableversion, 50, 3830, 1060, ''),
                (None, self.tableversion, 51, 3830, 1060, ''),
                (None, self.tableversion, 52, 3530, 1798, ''),
                (None, self.tableversion, 53, 3530, 1798, ''),
                (None, self.tableversion, 54, 3530, 1798, ''),
                (None, self.tableversion, 55, 3530, 1798, ''),
                (None, self.tableversion, 56, 2930, 2453, ''),
                (None, self.tableversion, 57, 2930, 2453, ''),
                (None, self.tableversion, 58, 2930, 2453, ''),
                (None, self.tableversion, 59, 2930, 2453, ''),
                (None, self.tableversion, 100, 3000, 2930, ''),
                (None, self.tableversion, 101, 3000, 2930, ''),
                (None, self.tableversion, 102, 3000, 2930, ''),
                (None, self.tableversion, 103, 3000, 2930, ''),
                (None, self.tableversion, 104, 3500, 2630, ''),
                (None, self.tableversion, 105, 3500, 2630, ''),
                (None, self.tableversion, 106, 3500, 2630, ''),
                (None, self.tableversion, 107, 3500, 2630, ''),
                (None, self.tableversion, 108, 4155, 1940, ''),
                (None, self.tableversion, 109, 4155, 1940, ''),
                (None, self.tableversion, 110, 4155, 1940, ''),
                (None, self.tableversion, 111, 4155, 1940, ''),
                (None, self.tableversion, 112, 5300, 1265, ''),
                (None, self.tableversion, 113, 5300, 1265, ''),
                (None, self.tableversion, 114, 5300, 1265, ''),
                (None, self.tableversion, 115, 5300, 1265, ''),
                (None, self.tableversion, 116, 2745, 690, ''),
                (None, self.tableversion, 117, 2745, 690, ''),
                (None, self.tableversion, 118, 2745, 690, ''),
                (None, self.tableversion, 119, 2745, 690, ''),
                (None, self.tableversion, 120, 1470, 175, ''),
                (None, self.tableversion, 121, 1470, 175, ''),
                (None, self.tableversion, 122, 1470, 175, ''),
                (None, self.tableversion, 123, 1470, 175, ''),
                (None, self.tableversion, 124, 1090, 69, ''),
                (None, self.tableversion, 125, 1090, 69, ''),
                (None, self.tableversion, 126, 1090, 69, ''),
                (None, self.tableversion, 127, 1090, 69, ''),
                (None, self.tableversion, 128, 854, 0, ''),
                (None, self.tableversion, 129, 854, 0, ''),
                (None, self.tableversion, 130, 854, 0, ''),
                (None, self.tableversion, 131, 854, 0, ''),
                (None, self.tableversion, 132, 551, 0, ''),
                (None, self.tableversion, 133, 551, 0, ''),
                (None, self.tableversion, 134, 551, 0, ''),
                (None, self.tableversion, 135, 551, 0, ''),
                (None, self.tableversion, 136, 380, 0, ''),
                (None, self.tableversion, 137, 380, 0, ''),
                (None, self.tableversion, 138, 380, 0, ''),
                (None, self.tableversion, 139, 380, 0, ''),
                (None, self.tableversion, 140, 253, 0, ''),
                (None, self.tableversion, 141, 253, 0, ''),
                (None, self.tableversion, 142, 253, 0, ''),
                (None, self.tableversion, 143, 253, 0, ''),
                (None, self.tableversion, 144, 186, 0, ''),
                (None, self.tableversion, 145, 186, 0, ''),
                (None, self.tableversion, 146, 186, 0, ''),
                (None, self.tableversion, 147, 186, 0, ''),
                (None, self.tableversion, 148, 130, 0, ''),
                (None, self.tableversion, 149, 130, 0, ''),
                (None, self.tableversion, 150, 130, 0, ''),
                (None, self.tableversion, 151, 130, 0, ''),
                (None, self.tableversion, 152, 98, 0, ''),
                (None, self.tableversion, 153, 98, 0, ''),
                (None, self.tableversion, 154, 98, 0, ''),
                (None, self.tableversion, 155, 98, 0, ''),
                (None, self.tableversion, 156, 71, 0, ''),
                (None, self.tableversion, 157, 71, 0, ''),
                (None, self.tableversion, 158, 71, 0, ''),
                (None, self.tableversion, 159, 71, 0, '')
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
