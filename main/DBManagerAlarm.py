#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
import traceback
from DBManagerHostId import *

#告警数据库表名
TABLE_NAME_ALARM = "tbl_alarm"

KEY_ID = "id"
KEY_VERSION = "version"
KEY_HOST_ID = "hostId"          #传感设备所在的网关
KEY_DEVICE_ADDR = "addr"      #传感设备Id/Mac
# KEY_ALARM_TIME_ID = "timeId"        #首次触发时间
KEY_ALARM_TYPE = "type"        #告警类型
KEY_ALARM_CONFIRM = "confirmed"        #确认：1, 0
KEY_ALARM_DETAIL = "detail"    #告警详细json


###所有的alarm属性都添加一个"timestamp"，表明当前的alarm属性更新时间。
###属性同步到云端后，云端可根据timestamp决定哪个同步命令是最新的，从而不会拿旧的属性覆盖新的属性
###备份时不能修改"timestamp"的值。
class DBManagerAlarm(object):
    __instant = None;
    __lock = threading.Lock()
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerAlarm.__instant==None):
            DBManagerAlarm.__lock.acquire();
            try:
                if(DBManagerAlarm.__instant==None):
                    Utils.logDebug("new DBManagerAlarm singleton instance.")
                    DBManagerAlarm.__instant = object.__new__(self)
            finally:
                DBManagerAlarm.__lock.release()
        return DBManagerAlarm.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_ALARM
        self.tableversion = 1
        self.createAlarmTable()

    def createAlarmTable(self):
        Utils.logDebug("->createAlarmTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID +           "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION +      "` INTEGER NOT NULL,"
        # create_table_sql += " `" + KEY_ALARM_TIME_ID+ "` INTEGER UNIQUE NOT NULL,"
        create_table_sql += " `" + KEY_DEVICE_ADDR +    "` varchar(50) UNIQUE NOT NULL,"
        create_table_sql += " `" + KEY_HOST_ID +      "` varchar(50),"
        create_table_sql += " `" + KEY_ALARM_TYPE +   "` varchar(20) NOT NULL,"
        create_table_sql += " `" + KEY_ALARM_CONFIRM+ "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_ALARM_DETAIL + "` TEXT"
        create_table_sql += " )"
        conn = DBUtils.get_conn_rt()
        DBUtils.create_table(conn, create_table_sql)

    ##检查数据库文件状态
    ##rt.db存放实时数据
    ##如果数据库文件损坏，fetchall()应抛出异常
    def checkDBHealthy(self):
        conn = DBUtils.get_conn_rt()
        sql = "select * from " + self.tablename
        DBUtils.fetchall(conn, sql)

    #detailJsonStr是告警详情所有属性的Json格式化串
    def saveAlarm(self, detailObj):
        Utils.logDebug("->saveAlarm %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveAlarm() rx invalid inputs %s'%(detailObj))
            return None
        try:
            # detailObj = json.loads(alarmAllDetailJsonStr)
            # timeId = detailObj.get(KEY_ALARM_TIME_ID, None)
            devId = detailObj.get(KEY_DEVICE_ADDR, None)
            
            if(devId is None):
                Utils.logError('json does not include addr')
                return None

            # hostId = detailObj.get(KEY_HOST_ID, None)
            alarmType = detailObj.get(KEY_ALARM_TYPE, None) #TODO, getInt...
            confirmed = detailObj.get(KEY_ALARM_CONFIRM, None) #TODO, getInt...
            detailObj["timestamp"] = int(time.time())

            hostProp = DBManagerHostId().getHost()
            hostId = hostProp.get("hostId", 'Boer-host')
            detailObj['hostId'] = hostId

            alarmAllDetailJsonStr = None
            success = True
            alarmItem = self.getAlarmByDevId(devId)
            if(alarmItem is None):
                alarmAllDetailJsonStr = json.dumps(detailObj)

                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?,?)"
                data = [(None, self.tableversion, devId, hostId, alarmType, confirmed, alarmAllDetailJsonStr)]
                conn = DBUtils.get_conn_rt()
                success = DBUtils.save(conn, save_sql, data)
            else:
                update_sql = "UPDATE " + self.tablename + " SET "
                update_sql += " " + KEY_HOST_ID + " = ? " 
                update_sql += "," + KEY_ALARM_TYPE + " = ? " 
                update_sql += "," + KEY_ALARM_CONFIRM + " = ? "   
                update_sql += "," + KEY_ALARM_DETAIL + " = ? " 
                update_sql += " WHERE "+ KEY_DEVICE_ADDR + " = ? "
                
                #把缺失的属性从数据库补齐
                # if devId == None:
                #     devId = alarmItem.get(KEY_DEVICE_ADDR, None)
                #     detailObj[KEY_DEVICE_ADDR] = devId
                #     updated = True
                if hostId == None:
                    hostId = alarmItem.get(KEY_HOST_ID, None)
                    detailObj[KEY_HOST_ID] = hostId
                if alarmType == None:
                    alarmType = alarmItem.get(KEY_ALARM_TYPE, None)
                    detailObj[KEY_ALARM_TYPE] = alarmType
                if confirmed == None:
                    confirmed = alarmItem.get(KEY_ALARM_CONFIRM, None)
                    detailObj[KEY_ALARM_CONFIRM] = confirmed
                
                alarmAllDetailJsonStr = json.dumps(detailObj)
                
                data = [(hostId, alarmType, confirmed, alarmAllDetailJsonStr, devId)]
                conn = DBUtils.get_conn_rt()
                success = DBUtils.update(conn, update_sql, data)

            if success == True:
                return detailObj
        except:
            Utils.logException('saveAlarm()异常')
            exc_str = traceback.format_exc()
            if exc_str != None and exc_str.lower().find('database is locked') != -1:
                # database is locked.
                Utils.unlockDatabase()
        return None

    #返回满足条件的所有告警的json格式串 
    #conditionDict = {“devId”:"xx22ddaa00","timeId":"151001235910"}
    def getByCondition(self, conditionDict, page=None, pagenum=None):
        alarmDict = {}
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('getByCondition has invalid where condition')
            return alarmDict
        try:
            conn = DBUtils.get_conn_rt()
            
            #组装sql语句
            sql = "select * from " + self.tablename + " where( "
            where = ""
            for key in conditionDict.keys():
                if(where != ""):
                    where += " and "
                where += "(" + key + " = " + str(conditionDict[key]) + ")"
            sql += where + " )"

            if page != None and pagenum != None:
                offset = (int(page))*int(pagenum)
                sql += " limit " + str(pagenum) + " offset " + str(offset)

            alarmarr = DBUtils.fetchall(conn, sql)
            #alarmarr应该是[(id, timeId, devId, hostId, type, confirmed, detail),(...)]数组格式
            if(alarmarr is not None):
                for dev in alarmarr:
                    alarmDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
        except:
            Utils.logException('getByCondition()异常')
            alarmDict.clear()
        return alarmDict.values()
        
    def deleteByKey(self, conditionDict):
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('deleteByKey has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn_rt()
            #组装sql语句
            sql = "DELETE FROM " + self.tablename + " WHERE( "
            where = ""
            for key in conditionDict.keys():
                if(where != ""):
                    where += " and "
                where += "(" + key + " = " + str(conditionDict[key]) + ")"
            sql += where + " )"
            
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByKey()异常')
            return False

    # def getAlarmByDevIdTimeId(self, addr, timeId):
    #     Utils.logDebug("->getAlarmByDevIdTimeId %s,%s"%(addr, timeId))
    #     conds = {}
    #     if(addr is None or addr == "" or timeId is None or timeId == ""):
    #         Utils.logError("getAlarmByDevIdTimeId rx invalid inputs")
    #     else:
    #         conds[KEY_ALARM_TIME_ID] = timeId
    #         conds[KEY_DEVICE_ADDR] = "'" + addr + "'"
    #     result = self.getByCondition(conds)
    #     if(len(result) == 0):
    #         return None
    #     else:
    #         return result[0]    #DeviceId和timeId可确定唯一的记录
        
    def getAlarmByDevId(self, addr):
        Utils.logDebug("->getAlarmsByDevId %s"%(addr))
        conds = {}
        if(addr is None or addr == ""):
            Utils.logError("getAlarmsByDevId rx invalid inputs")
        else:
            conds[KEY_DEVICE_ADDR] = "'" + addr + "'"
        result = self.getByCondition(conds)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]

    def getAlarmByDevIdAndType(self, addr, almType):
        Utils.logDebug("->getAlarmByDevIdAndType,addr:%s , almType:%s" % (addr, almType))
        conds = {}
        if (addr is None or addr == ""):
            Utils.logError("getAlarmByDevIdAndType rx invalid inputs")
        else:
            conds[KEY_DEVICE_ADDR] = "'" + addr + "'"
            conds[KEY_ALARM_TYPE] = "'" + almType + "'"
        result = self.getByCondition(conds)
        if (result == None or len(result) == 0):
            return None
        else:
            return result[0]

    def getAlarmByType(self, almType, page=None,pagenum=None):
        Utils.logDebug("->getAlarmByType %s"%(almType))
        conds = {}
        if(almType is None or almType == ""):
            Utils.logError("getAlarmByType rx invalid inputs")
        else:
            conds[KEY_ALARM_TYPE] =  "'" + str(almType) + "'"
        result = self.getByCondition(conds, page, pagenum)
        if(result == None or len(result) == 0):
            return None
        else:
            return result

    def getAlarmByConfirm(self, confirmed, page=None, pagenum=None):
        Utils.logDebug("->getAlarmByConfirm %s"%(confirmed))
        conds = {}
        if(confirmed is None or confirmed == ""):
            Utils.logError("getAlarmByConfirm rx invalid inputs")
            return None
        zero = '0'
        if confirmed == True:
            zero = '1'
        conds[KEY_ALARM_CONFIRM] = "'" + str(zero) + "'"
        result = self.getByCondition(conds, page, pagenum)
        if(result == None or len(result) == 0):
            return None
        else:
            return result

    def getAlarmCountByConfirm(self, confirmed):
        Utils.logDebug("->getAlarmCountByConfirm %s"%(confirmed))
        conds={}
        zero = '0'
        if confirmed == True:
            zero = '1'
        conds[KEY_ALARM_CONFIRM] = "'" + str(zero) + "'"
        return self._getAlarmCount(conds)

    def getAlarmCountByType(self, almType):
        Utils.logDebug("->getAlarmCountByType %s"%(almType))
        conds={}
        conds[KEY_ALARM_TYPE] = "'" + str(almType) + "'"
        return self._getAlarmCount(conds)

    def _getAlarmCount(self, conds):
        conn = DBUtils.get_conn_rt()
        sql = "select count(*) from " + self.tablename + " where( "
        where = ""
        # where += "(" + KEY_ALARM_CONFIRM + " = " + str(confirmed) + ")"
        for key in conds.keys():
            if(where != ""):
                where += " and "
            where += "(" + key + " = " + str(conds[key]) + ")"
        sql += where + " )"

        return DBUtils.count(conn, sql)
        
    def deleteAlarmByDevId(self, addr):
        Utils.logDebug("->deleteAlarmByDevId %s"%(addr))
        conds = {}
        if(addr is None or addr == ""):
            Utils.logError("deleteAlarmByDevId rx invalid inputs")
        else:
            # conds[KEY_ALARM_TIME_ID] = timeId
            conds[KEY_DEVICE_ADDR] = "'" + addr + "'"
        return self.deleteByKey(conds)

    def deleteAlarmByDevIdAndType(self, addr, almType):
        Utils.logDebug("->deleteAlarmByDevIdAndType,addr: %s, almType: %s" % (addr, almType))
        conds = {}
        if (addr is None or addr == ""):
            Utils.logError("deleteAlarmByDevIdAndType rx invalid inputs")
        else:
            # conds[KEY_ALARM_TIME_ID] = timeId
            conds[KEY_DEVICE_ADDR] = "'" + addr + "'"
            conds[KEY_ALARM_TYPE] = "'" + almType + "'"
        return self.deleteByKey(conds)

if __name__ == '__main__':
    d1 = DBManagerAlarm()
    d2 = DBManagerAlarm()
    print "getAlarmByConfirm:", d1.getAlarmByConfirm(None)
    print "getAlarmByType:", d1.getAlarmByType(0)
    print "getAlarmByConfirm:", d1.getAlarmByConfirm(0)

    alarmDict={"addr":"gas","confirmed":0,"type":"0","alarming":"1"}
    d2.saveAlarm(alarmDict)
    alarmDict2={"addr":"water","confirmed":0,"type":"1", "alarming":"1"}
    d1.saveAlarm(alarmDict2)

    print "============================="

    cnttype0 = d1.getAlarmCountByType("0")
    if cnttype0 == 1:
        print "===========getAlarmCountByType 0 SUCCESS=================="
    else:
        print "**********getAlarmCountByType 0 FAILED"
    cntconfirm = d1.getAlarmCountByConfirm("0")
    if cntconfirm == 2:
        print "===========getAlarmCountByConfirm 0 SUCCESS=================="
    else:
        print "**********getAlarmCountByConfirm 0 FAILED"

    cntconfirm4 = d1.getAlarmCountByConfirm("4")
    if cntconfirm4 == 0:
        print "===========getAlarmCountByConfirm 4 SUCCESS=================="
    else:
        print "**********getAlarmByConfirm 4 FAILED"

    print "getAlarmByType:", d1.getAlarmByType(0)
    a = d1.getAlarmByConfirm(0)
    if len(a) == 2:
        print "===========getAlarmByConfirm SUCCESS=================="
    else:
        print "**********getAlarmByConfirm FAILED"
    a = d1.getAlarmByDevId("water")
    if a.get("type", "") == "1":
        print "===========getAlarmByDevId SUCCESS=================="
    else:
        print "**********getAlarmByDevId FAILED"
    d1.deleteAlarmByDevId("water")
    a = d2.getAlarmByType(1)
    if a == None:
         print "===========deleteAlarmByDevId SUCCESS=================="
    else:
        print "**********deleteAlarmByDevId FAILED"
    
    