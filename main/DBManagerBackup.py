#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
from PacketParser import *


# 设备状态改变，水电煤数据上报，告警等，在上报时如果网络断开，无法同步更新到云端。
# 则将消息暂存在此，等待网络恢复后再次同步。

# 设备表数据库名
TABLE_NAME_BACKUP = "tbl_backup"

KEY_ID = "id"
KEY_VERSION = "version"
# datatype     energy:水电煤插座等定期上报数据, or command:重发的socket命令
KEY_BACKUP_TYPE = "datatype"
KEY_BACKUP_CMD = "cmd"          # socket,water,gas,elec, [socket命令字]
KEY_BACKUP_DEVID = "addr"
KEY_BACKUP_TIME = "timestamp"   # 请求备份的时间
KEY_BACKUP_DETAIL = "detail"    # 详细json str

# detail的存储格式为 {“op”:"add", "detail":"{"name":"二联灯","addr":"sdsf",...}"}
# detail里可能存放的是socket消息，可通过socket重发。对应的消息码在cmd字段
# 实时数据同步失败时，只保存响应的socket命令，网络恢复后直接调用socket发送即可
# 而定期上报的数据同步时，批量将数据通过socket发送，同时删除Backup表响应的数据
# 如果同步失败，也只保存socket命令


class DBManagerBackup(object):
    __instant = None
    __lock = threading.Lock()

    # singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerBackup.__instant==None):
            DBManagerBackup.__lock.acquire();
            try:
                if(DBManagerBackup.__instant==None):
                    Utils.logDebug("new DBManagerBackup singleton instance.")
                    DBManagerBackup.__instant = object.__new__(self);
            finally:
                DBManagerBackup.__lock.release()
        return DBManagerBackup.__instant

    def __init__(self):
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_BACKUP
        self.tableversion = 1
        self.createBackupTable()

    def createBackupTable(self):
        Utils.logDebug("->createBackupTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_BACKUP_TYPE +  "` varchar(10) NOT NULL,"
        create_table_sql += " `" + KEY_BACKUP_CMD +  "` varchar(10) NOT NULL,"
        create_table_sql += " `" + KEY_BACKUP_DEVID + "` varchar(50),"
        create_table_sql += " `" + KEY_BACKUP_TIME + "` varchar(50),"
        create_table_sql += " `" + KEY_BACKUP_DETAIL + "` TEXT NOT NULL"
        create_table_sql += " )"
        conn = DBUtils.get_conn_rt()
        DBUtils.create_table(conn, create_table_sql)

    # 检查数据库文件状态
    # rt.db存放实时数据
    # 如果数据库文件损坏，fetchall()应抛出异常
    def checkDBHealthy(self):
        conn = DBUtils.get_conn_rt()
        sql = "select * from " + self.tablename
        DBUtils.fetchall(conn, sql)

    # 保存水电煤数据
    def saveBackupEnergy(self, typeName, jsonObj):
        addr = jsonObj.get("addr", None)
        if addr is None:
            Utils.logError("saveBackupEnergy, invalid object.")
            return None

        now = int(time.time())

        if enableBackupWhenLinkdown is True:
            # 网络断 本地缓存时，考虑到网关存储能力，只缓存30天数据
            first = self.getFirstBackupByDevAddr(addr)
            if first != None :
                firstTs = int(first[-2])
                if firstTs != 0 and now - firstTs > 60*60*24*30:    # 已经超过30天
                    return None

        item = self.getLastBackupByDevAddr(addr)
        if item != None :
            timestamp = item[-2]
            if now - int(timestamp) < 60*30:    # 30分钟存储一次
                return None

        valid = True
        if item != None:
            valid = self.checkEnergyData(jsonObj, json.loads(item[-1]))
        if valid == False:
            Utils.logInfo('rx invalid energy data:%s'%(jsonObj))
            return None

        jsonObj["timestamp"] = now
        detailJsonStr = json.dumps(jsonObj)

        success = self.saveBackup(addr, "energy", typeName, None, detailJsonStr)
        if success == True:
            return jsonObj
        return None

    # 插座数据
    def saveBackupSocket(self, jsonObj):
        addr = jsonObj.get("addr", None)
        if addr is None:
            Utils.logError("saveBackupSocket, invalid object.")
            return None
        now = int(time.time())

        if enableBackupWhenLinkdown is True:
            # 网络断开，本地缓存时，考虑到网关存储能力，只缓存30天数据
            first = self.getFirstBackupByDevAddr(addr)
            if first != None :
                firstTs = int(first[-2])
                if firstTs != 0 and now - firstTs > 60*60*24*30:    # 已经超过30天
                    return None

        item = self.getLastBackupByDevAddr(addr)
        if item != None :
            timestamp = item[-2]
            if now - int(timestamp) < 60*30:    # 半个小时存储一次
                return None

        valid = True
        if item != None:
            valid = self.checkEnergyData(jsonObj, json.loads(item[-1]))

        if valid == False:
            Utils.logError('rx invalid socket data:%s'%(jsonObj))
            return None

        jsonObj["timestamp"] = now
        detailJsonStr = json.dumps(jsonObj)
        success = self.saveBackup(addr, "energy", DEVTYPENAME_SOCKET, None, detailJsonStr)
        if success == True:
            return jsonObj
        return None

    # 保存净水器、空气净化器的数据
    def saveBackupFilter(self, devTypeName, jsonObj):
        addr = jsonObj.get("addr", None)
        if addr is None:
            Utils.logError("saveBackupFilter, invalid object.")
            return None
        now = int(time.time())

        # 网络断开，本地缓存时，考虑到网关存储能力，只缓存30天数据
        first = self.getFirstBackupByDevAddr(addr)
        if first != None:
            firstTs = int(first[-2])
            if firstTs != 0 and now - firstTs > 60 * 60 * 24 * 30:  # 已经超过30天
                return None

        item = self.getLastBackupByDevAddr(addr)
        if item != None:
            timestamp = item[-2]
            if now - int(timestamp) < 60 * 30:  # 半个小时存储一次
                return None

        jsonObj["timestamp"] = now
        detailJsonStr = json.dumps(jsonObj)
        success = self.saveBackup(addr, "energy", devTypeName, None, detailJsonStr)
        if success == True:
            return jsonObj
        return None


    def checkEnergyData(self, curDevObj, devInDbObj):
        valid = True
        invalidU = 500       # 电压超过500伏认为异常

        curr_time = curDevObj.get("time", None)
        db_time = devInDbObj.get("time", None)
        time_interval = 0
        if curr_time is not None and db_time is not  None:
            time_interval = curDevObj.get("time") - devInDbObj.get("time")  # 两次上报的间隔
        try:
            devType = curDevObj.get('type', '')
            if devType == 'elec' or devType == 'ElecMeter':
                ## 电能表数据
                curValue = curDevObj.get('value', None)
                dbValue = devInDbObj.get('value', None)
                if curValue != None and dbValue != None:
                    curEnergy = float(curValue.get('energy'))
                    dbEnergy = float(dbValue.get('energy'))
                    if curEnergy <= 0 or (dbEnergy != 0 and curEnergy/dbEnergy >= 10):
                        valid = False
                    if curValue.has_key('Uab'):
                        curU = float(curValue.get('Uab'))
                        if curU <= 0 or curU > invalidU:
                            valid = False
                    if curValue.has_key('Ubc'):
                        curU = float(curValue.get('Ubc'))
                        if curU > invalidU:
                            valid = False
                    if curValue.has_key('Uca'):
                        curU = float(curValue.get('Uca'))
                        if curU > invalidU:
                            valid = False
            elif devType == 'Socket':
                ## Socket
                curValue = curDevObj.get('value', None)
                dbValue = devInDbObj.get('value', None)
                if curValue != None and dbValue != None:
                    curEnergy = float(curValue.get('energy'))
                    dbEnergy = float(dbValue.get('energy'))
                    if curEnergy < 0 or (curEnergy - dbEnergy) >= 0.0014 * time_interval:  # 新插座电能可能是0
                        valid = False
                    if curValue.has_key('U'):
                        curU = float(curValue.get('U'))
                        if curU <= 0 or curU > invalidU:
                            valid = False
            elif devType == 'water' or devType == 'WaterMeter':
                ## Water
                curValue = curDevObj.get('value', None)
                dbValue = devInDbObj.get('value', None)
                if curValue != None and dbValue != None:
                    curEnergy = float(curValue.get('energy'))
                    dbEnergy = float(dbValue.get('energy'))
                    if curEnergy <= 0 or (dbEnergy != 0 and curEnergy/dbEnergy >= 10):
                        valid = False
        except:
            valid = False
        return valid

    # 保存发往云端的socket命令
    def saveBackupCommand(self, code, command):
        return self.saveBackup(None, "command", code, None, command)

    # detailJsonStr是备份所有属性的Json格式化串
    # op： "add"(默认), "delete"
    def saveBackup(self, addr, datatype, cmd, op, detailString):
        if(datatype is None or detailString is None):
            Utils.logError('saveBackup() rx invalid inputs')
            return False
        Utils.logDebug("->saveBackup %s,%s,%s"%(cmd,op,detailString))
        try:
            timestamp = int(time.time())
            save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?,?)"
            data = [(None, self.tableversion, datatype, cmd, addr, timestamp, detailString)]
            conn = DBUtils.get_conn_rt()
            return DBUtils.save(conn, save_sql, data)
        except:
            Utils.logException('saveBackup()异常')
            exc_str = traceback.format_exc()
            if exc_str != None and exc_str.lower().find('database is locked') != -1:
                # database is locked.
                Utils.unlockDatabase()
        return False

    def deleteByKey(self, key, data, maxId):
        if(data is None or data == "" or key is None):
            Utils.logError('deleteByKey has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn_rt()
            sql = "DELETE FROM " + self.tablename + " WHERE " + key + " = '" + data + "'"
            if maxId > 0:
                sql += " and " + KEY_ID + " <= " + str(maxId)
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByKey()异常')
            return False

    # def getBackupsByCmd(self, cmd, limit=None):
    #     Utils.logDebug("->getBackupsByCmd() %s"%(cmd))
    #     if(cmd is None or cmd == ""):
    #         Utils.logError("getBackupsByCmd rx invalid inputs")
    #         return
    #     return self._getBackupsByKey(KEY_BACKUP_CMD, cmd, limit)
    #
    def getBackupsByDataType(self, datatype, limit=None):
        Utils.logDebug("->getBackupsByKey() %s"%(datatype))
        if(datatype is None or datatype == ""):
            Utils.logError("getBackupsByKey rx invalid inputs")
            return
        # return self._getBackupsByKey(KEY_BACKUP_TYPE, datatype, limit)
        backupsDict={}
        maxId = 0
        try:
            conn = DBUtils.get_conn_rt()

            #组装sql语句
            sql = "select * from " + self.tablename + " where"
            sql += " (" + KEY_BACKUP_TYPE + " = '" + datatype + "')"
            sql += " ORDER BY " + KEY_BACKUP_TIME + " asc "
            if limit != None:
                sql += " limit " + str(limit) + " offset 0 "
            backuparr = DBUtils.fetchall(conn, sql)
            if(backuparr is not None):
                for item in backuparr:
                    kid = item[0]
                    if(kid > maxId):
                        maxId = kid
                    backupsDict[str(kid)] = json.loads(item[-1])
        except:
            Utils.logException('_getBackupsByKey()异常')
            backupsDict.clear()

        if(backupsDict == None or len(backupsDict) == 0):
            return None
        else:
            return (maxId, backupsDict.values())

    # #备份过程中，可能有新的数据添加到备份表中。。
    # #为避免误删，引入此备份中按时间升序的最大记录Id。
    # def deleteBackupsByCmd(self, cmd, maxId):
    #     Utils.logDebug("->deleteBackupsByCmd %s"%(cmd))
    #     if(cmd is None or cmd == ""):
    #         Utils.logError("deleteBackupsByCmd rx invalid inputs")
    #         return
    #     return self.deleteByKey(KEY_BACKUP_CMD, cmd, maxId)

    def deleteBackupsByDataType(self, datatype, maxId):
        Utils.logDebug("->deleteBackupsByDataType %s"%(datatype))
        if(datatype is None or datatype == ""):
            Utils.logError("deleteBackupsByDataType rx invalid inputs")
            return
        return self.deleteByKey(KEY_BACKUP_TYPE, datatype, maxId)

    def deleteBackupsByDevAddr(self, addr):
        Utils.logDebug("->deleteBackupsByDevAddr %s"%(addr))
        if(addr is None):
            Utils.logError("deleteBackupsByDevAddr rx invalid inputs")
            return
        return self.deleteByKey(KEY_BACKUP_DEVID, addr, 0)

    def deleteBackupsById(self, keyId):
        Utils.logDebug("->deleteBackupsById %s"%(keyId))
        conn = DBUtils.get_conn_rt()
        sql = "DELETE FROM " + self.tablename + " WHERE " + KEY_ID + " = " + str(keyId) + ""
        DBUtils.deleteone(conn, sql)


    def getLastBackupByDevAddr(self, addr):
        try:
            conn = DBUtils.get_conn_rt()
            #组装sql语句
            sql = "select * from " + self.tablename + " where( "
            where = " (" + KEY_BACKUP_DEVID + " = ?)"
            sql += where + " )"
            sort = " ORDER BY " + KEY_BACKUP_TIME + " desc "
            sql += sort
            return DBUtils.fetchone(conn, sql, addr)
        except:
            Utils.logException('getLastBackupByDevAddr()异常')
            return None

    def getFirstBackupByDevAddr(self, addr):
        try:
            conn = DBUtils.get_conn_rt()
            #组装sql语句
            sql = "select * from " + self.tablename + " where( "
            where = " (" + KEY_BACKUP_DEVID + " = ?)"
            sql += where + " )"
            sort = " ORDER BY " + KEY_BACKUP_TIME + " asc "
            sql += sort
            return DBUtils.fetchone(conn, sql, addr)
        except:
            Utils.logException('getFirstBackupByDevAddr()异常')
            return None

    def getOneSocketCommand(self):
        itemDict={}
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where( datatype = ?) "
            sql += " ORDER BY " + KEY_BACKUP_TIME + " asc "
            item = DBUtils.fetchone(conn, sql, "command")
            if item != None:
                itemDict["keyId"] = item[0]
                itemDict["code"] = item[3]
                itemDict["command"] = item[-1]
        except:
            Utils.logException('getOneSocketCommand()异常')
            itemDict.clear()

        return itemDict

if __name__ == '__main__':
    d1 = DBManagerBackup()
    d2 = DBManagerBackup()
    print "getBackupsByCmd:", d1.getBackupsByDataType("", None)

    # devDict={"deviceId":"devIdvalue","hostId":"hostIdvalue","room":"roomvalue","area":"areavalue","type":"typevalue"}
    t1 = int(time.time())
    devDict={"name":"水","type":"Light2","roomId":"1","room":"客厅","addr":"z-347D4501004B12001233","value":{"state":"0","coeff":"1"}}
    d2.saveBackupEnergy("water", devDict)
    
    time.sleep(2)
    devDict2={"name":"插座","type":"Light1","roomId":"2","room":"厨房","area":"areavalue2","addr":"z-347D4501004B12001234","value":{"state":"1","coeff":"1"}}
    d1.saveBackupSocket(devDict2)

    time.sleep(2)
    devDict3={"name":"三联插座","roomId":"3","room":"厨房","area":"areavalue2","addr":"z-347D4501004B12001235","value":{"state":"1","coeff":"1"}}
    d1.saveBackupSocket(devDict3)
    
    print "============================="
    r = d2.getLastBackupByDevAddr("z-347D4501004B12001235")
    if r is None:
        print "===============getLastBackupByDevAddr SUCCESS============="
    else:
        print "!!!!!!!!!!!!!!!!!!!getLastBackupByDevAddr FAILED!!!!!!!!!"
    

    devDict3={"name":"三联插座","roomId":"1","room":"厨房","area":"areavalue2","addr":"z-347D4501004B12001235","value":{"state":"1","coeff":"1"}}
    d1.saveBackupCommand(300, "socket command")
    
    cmd = d1.getOneSocketCommand()
    if cmd != None and len(cmd) > 0 and cmd["keyId"] != 0:
        print "===============saveBackupCommand SUCCESS============="
    else:
        print "!!!!!!!!!!!!!!!!!!!saveBackupCommand FAILED!!!!!!!!!"

    d1.deleteBackupsById(cmd["keyId"])
    cmd = d1.getOneSocketCommand()
    if cmd != None and len(cmd) > 0:
        print "!!!!!!!!!!!!!!!!!!!deleteBackupsById FAILED!!!!!!!!!"
    else:
        print "===============deleteBackupsById SUCCESS============="
    
    