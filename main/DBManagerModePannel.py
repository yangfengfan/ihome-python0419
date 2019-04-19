#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time


#设备表数据库名
TABLE_NAME_MODE_PANNEL = "tbl_mode_pannel"


KEY_ID = "id"
KEY_VERSION = "version"
#KEY_HOST_ID = "hostId"          #设备所在的网关，服务端可动态获取hostId
KEY_DEVICE_ADDR = "addr"      #设备Id/Mac
KEY_DEVICE_CHANNEL = "channelId"        #按键Id
KEY_DEVICE_DETAIL = "detail"    #详细json


###
#@Deprecated
##模式面板的配置都可以存储在设备属性里
##
class DBManagerModePannel(object):
    __instant = None
    __lock = threading.Lock()
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerModePannel.__instant==None):
            DBManagerModePannel.__lock.acquire();
            try:
                if(DBManagerModePannel.__instant==None):
                    Utils.logDebug("new DBManagerModePannel singleton instance.")
                    DBManagerModePannel.__instant = object.__new__(self)
            finally:
                DBManagerModePannel.__lock.release()
        return DBManagerModePannel.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_MODE_PANNEL
        self.tableversion = 1
        self.createModePannelTable()

    def createModePannelTable(self):
        Utils.logDebug("->createModePannelTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_DEVICE_ADDR + "` varchar(50) UNIQUE NOT NULL,"
        create_table_sql += " `" + KEY_DEVICE_CHANNEL + "` varchar(10),"
        create_table_sql += " `" + KEY_DEVICE_DETAIL + "` TEXT "
        create_table_sql += " )"
        conn = DBUtils.get_conn()
        DBUtils.create_table(conn, create_table_sql)

    ##检查数据库文件状态
    ##host.db存放配置数据
    ##如果数据库文件损坏，fetchall()应抛出异常
    def checkDBHealthy(self):
        conn = DBUtils.get_conn()
        sql = "select * from " + self.tablename
        DBUtils.fetchall(conn, sql)
    
    #detailJsonStr是模式面板配置详情所有属性的Json格式化串
    def saveModePannel(self, detailObj):
        Utils.logDebug("->saveModePannel %s"%(detailObj))
        if (detailObj is None):
            Utils.logError('saveModePannel() rx invalid inputs %s'%(detailObj))
            return None
        try:
            deviceAddr = detailObj.get(KEY_DEVICE_ADDR, None)
            channelId = detailObj.get(KEY_DEVICE_CHANNEL, None)
            if deviceAddr == None or channelId == None:
                return None

            newtimestamp = None
            if detailObj.has_key("timestamp"):
                newtimestamp = detailObj.get("timestamp")

            success = True
            keyId, item = self.getModePannelBy(deviceAddr, channelId)
            if(item is None):
                detailObj["timestamp"] = int(time.time())
                devAllDetailJsonStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?)"
                data = [(None, self.tableversion, deviceAddr, channelId, devAllDetailJsonStr)]
                conn = DBUtils.get_conn()
                success = DBUtils.save(conn, save_sql, data)
            else:
                #更新设备属性，需判断是否会污染
                oldtimestamp = item.get("timestamp", None)
                if oldtimestamp != None and newtimestamp != oldtimestamp:
                    return item
                detailObj["timestamp"] = int(time.time())

                update_sql = 'UPDATE ' + self.tablename + ' SET '
                update_sql += ',' + KEY_DEVICE_ADDR + ' = ? '
                update_sql += ',' + KEY_DEVICE_CHANNEL + ' = ? '
                update_sql += ',' + KEY_DEVICE_DETAIL + ' = ? '
                update_sql += ' WHERE '+ KEY_ID + ' = ? '
                #把缺失的属性从数据库补齐
                if channelId == None:
                    channelId = item.get(KEY_DEVICE_CHANNEL, None)
                    detailObj[KEY_DEVICE_CHANNEL] = channelId
                devAllDetailJsonStr = json.dumps(detailObj)
                data = [(deviceAddr, channelId, devAllDetailJsonStr, keyId)]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)
            if success == True:
                return detailObj
        except:
            Utils.logException('saveModePannel()异常')
        return None

    def getModePannelBy(self, devAddr, channelId):
        try:
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename + " where addr = '"+ devAddr + "' and channelId = " + str(channelId)
            devarr = DBUtils.fetchall(conn, sql)
            #devarr应该是[(id, deviId, hostId, type, channelId, area, detail),(...)]数组格式
            if(devarr is not None):
                for dev in devarr:
                    return (dev[0], dev[-1])        #detail总是应该放在最后的字段
        except:
            Utils.logException('getModePannelBy()异常')
        return (None, None)

    def removeByDevAddr(self, addr):
        try:
            conn = DBUtils.get_conn()
            sql = "DELETE FROM " + self.tablename + " WHERE addr = '" + addr + "'"
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('removeByDevAddr()异常')
            return False


if __name__ == '__main__':
    d1 = DBManagerModePannel()