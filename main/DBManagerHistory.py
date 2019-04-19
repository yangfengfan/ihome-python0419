#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
from random import randint
from PacketParser import *


# 保存历史数据，供网关直连时查询

# 数据表名
TABLE_NAME_HISTORY  = "tbl_history"

KEY_ID = "id"
KEY_VERSION = "version"
# datatype     energy:水电煤插座等定期上报数据, or command:重发的socket命令
KEY_BACKUP_DATATYPE = "datatype"
KEY_BACKUP_DEVTYPE = "devicetype"          # socket,water,gas,elec, [socket命令字]
KEY_BACKUP_DEVID = "addr"
KEY_BACKUP_TIME = "timestamp"   # 请求备份的时间
KEY_BACKUP_ISNEW = "is_new"      # 是否是新产生的告警
KEY_BACKUP_DETAIL = "detail"    # 详细json str

MAX_AMOUNT = 2000   # 最大的存储记录条目数


class DBManagerHistory(object):
    __instant = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls):
        Utils.logDebug("__new__")
        if DBManagerHistory.__instant is None:
            DBManagerHistory.__lock.acquire()
            try:
                if DBManagerHistory.__instant is None:
                    Utils.logDebug("new DBManagerHistory singleton instance.")
                    DBManagerHistory.__instant = object.__new__(cls)
            finally:
                DBManagerHistory.__lock.release()
        return DBManagerHistory.__instant

    def __init__(self):
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_HISTORY
        self.tableversion = 1
        self.createBackupTable()

    def createBackupTable(self):
        Utils.logDebug("->createBackupTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_BACKUP_DATATYPE + "` varchar(10) NOT NULL,"
        create_table_sql += " `" + KEY_BACKUP_DEVTYPE + "` varchar(10) NOT NULL,"
        create_table_sql += " `" + KEY_BACKUP_DEVID + "` varchar(50),"
        create_table_sql += " `" + KEY_BACKUP_TIME + "` varchar(50),"
        create_table_sql += " `" + KEY_BACKUP_ISNEW + "` varchar(50),"
        create_table_sql += " `" + KEY_BACKUP_DETAIL + "` TEXT NOT NULL"
        create_table_sql += ", UNIQUE (" + KEY_BACKUP_DEVID + ", " + KEY_BACKUP_TIME + ") "
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

    def getAmountByType(self, dataType):

        result_dict = self.getBackupsByDataType(dataType)
        if result_dict:
            return len(result_dict.values())
        else:
            return 0

    def getAmountByTypes(self, data_type, device_type):
        try:
            conn = DBUtils.get_conn_rt()
            sql = "select count(*) from " + self.tablename
            sql += " where datatype='" + data_type + "'"
            sql += " and devicetype='" + device_type + "'"

            amount = DBUtils.fetchall(conn, sql)
            # 返回值格式： ===>getAmountByTypes, amount: [(60,)]
            Utils.logInfo("===>getAmountByTypes, amount: %s" % amount)
            if amount:
                return int(amount[0][0])
            return 0
        except Exception as err:
            Utils.logError("getAmountByTypes error: %s" % err)
            return 0

    def getAmountByTypeAndAddr(self, data_type, device_addr):
        try:
            conn = DBUtils.get_conn_rt()
            sql = "select count(*) from " + self.tablename
            sql += " where datatype='" + data_type + "'"
            sql += " and addr='" + device_addr + "'"

            amount = DBUtils.fetchall(conn, sql)
            # 返回值格式： ===>getAmountByTypes, amount: [(60,)]
            Utils.logInfo("===>getAmountByTypes, amount: %s" % amount)
            if amount:
                return int(amount[0][0])
            return 0
        except Exception as err:
            Utils.logError("getAmountByTypes error: %s" % err)
            return 0

    # 保存历史数据  not in use
    def saveHistoricalData(self, data_dict, dataType):

        addr = data_dict.get("addr", None)
        deviceTypeName = data_dict.get("deviceType", None)
        if not deviceTypeName:
            deviceTypeName = data_dict.get("type", None)
        timestamp = int(data_dict.get("time", int(time.time()))) + randint(1, 60)
        if addr is None or deviceTypeName is None or dataType == "":
            Utils.logError("saveHistoricalData, invalid object.")
            return None

        record_amount = self.getAmountByType(dataType)
        detailJsonStr = json.dumps(data_dict)
        if record_amount < MAX_AMOUNT:
            success = self.saveBackup(addr, dataType, deviceTypeName, None, detailJsonStr)
            if success is True:
                return data_dict
        else:
            # TODO，删除最老的数据，再保存新数据
            exceeded_amount = record_amount - MAX_AMOUNT + 1
            exceeded_record = self.getBackupsByDataType(dataType, limit=exceeded_amount)
            # for record_id in exceeded_record.keys():
            #     self.deleteBackupsById(record_id)
            keyIds = [(keyId,) for keyId in exceeded_record.keys()]
            self.deleteBackupsByIdInBatch(keyIds)
            success = self.saveBackup(addr, dataType, deviceTypeName, None, detailJsonStr)
            if success is True:
                return data_dict
            return None

    # 保存水电煤数据
    def saveHistoricalEnergy(self, jsonObj):
        addr = jsonObj.get("addr", None)
        deviceTypeName = jsonObj.get("type", None)
        timestamp = int(jsonObj.get("time", int(time.time()))) + randint(1, 60)
        value = jsonObj.get("value")
        value["delta"] = value.get("energy")
        if addr is None or deviceTypeName is None:
            Utils.logError("saveHistoricalEnergy, invalid object.")
            return None

        record_amount = self.getAmountByTypeAndAddr("energy", addr)
        detailJsonStr = json.dumps(jsonObj)
        if record_amount < MAX_AMOUNT:
            success = self.saveBackup(addr, "energy", deviceTypeName, None, detailJsonStr)
            if success is True:
                return jsonObj
        else:
            # TODO，删除最老的数据，再保存新数据
            exceeded_amount = record_amount - MAX_AMOUNT + 1
            exceeded_record = self.getBackupsByTypeAndAddr("energy", addr, limit=exceeded_amount)
            # for record_id in exceeded_record.keys():
            #     self.deleteBackupsById(record_id)
            keyIds = [(keyId, ) for keyId in exceeded_record.keys()]
            self.deleteBackupsByIdInBatch(keyIds)
            success = self.saveBackup(addr, "energy", deviceTypeName, None, detailJsonStr)
            if success is True:
                return jsonObj
            return None

    # 插座数据  not in use  20170412
    def saveBackupSocket(self, jsonObj):
        addr = jsonObj.get("addr", None)
        deviceTypeName = jsonObj.get("type", None)
        timestamp = int(jsonObj.get("time", int(time.time()))) + randint(1, 60)
        if addr is None or deviceTypeName is None:
            Utils.logError("saveBackupEnergy, invalid object.")
            return None

        record_amount = self.getAmountByTypeAndAddr("energy", addr)
        detailJsonStr = json.dumps(jsonObj)
        if record_amount < MAX_AMOUNT:
            success = self.saveBackup(addr, "energy", deviceTypeName, None, detailJsonStr)
            if success is True:
                return jsonObj
        else:
            # TODO，删除最老的数据，再保存新数据
            exceeded_amount = record_amount - MAX_AMOUNT + 1
            exceeded_record = self.getBackupsByTypeAndAddr("energy", addr, limit=exceeded_amount)
            # for record_id in exceeded_record.keys():
            #     self.deleteBackupsById(record_id)
            keyIds = [(keyId,) for keyId in exceeded_record.keys()]
            self.deleteBackupsByIdInBatch(keyIds)
            success = self.saveBackup(addr, "energy", "Socket", None, detailJsonStr)
            if success is True:
                return jsonObj
            return None

    # 保存历史告警
    def saveHistoricalAlarm(self, jsonObj):
        addr = jsonObj.get("addr", None)
        deviceTypeName = jsonObj.get("deviceType", None)
        timestamp = jsonObj.get("time", int(time.time())) + randint(1, 60)
        if addr is None or deviceTypeName is None:
            Utils.logError("saveHistoricalAlarm, invalid object.")
            return None

        record_amount = self.getAmountByType("alarms")
        detailJsonStr = json.dumps(jsonObj)
        if record_amount < MAX_AMOUNT:
            success = self.saveBackup(addr, "alarms", deviceTypeName, None, detailJsonStr)
            if success is True:
                return jsonObj
        else:
            # TODO，删除最老的数据，再保存新数据
            exceeded_amount = record_amount - MAX_AMOUNT + 1
            exceeded_record = self.getBackupsByDataType("alarms", limit=exceeded_amount)
            # for record_id in exceeded_record.keys():
            #     self.deleteBackupsById(record_id)
            keyIds = [(keyId,) for keyId in exceeded_record.keys()]
            self.deleteBackupsByIdInBatch(keyIds)
            success = self.saveBackup(addr, "alarms", deviceTypeName, None, detailJsonStr)
            if success is True:
                return jsonObj
            return None

    # detailJsonStr是备份所有属性的Json格式化串
    # op： "add"(默认), "delete"
    def saveBackup(self, addr, datatype, cmd, op, detailString):
        if datatype is None or detailString is None:
            Utils.logError('saveBackup() rx invalid inputs')
            return False
        Utils.logDebug("->saveBackup %s,%s,%s" % (cmd, op, detailString))
        try:
            timestamp = int(time.time()) + randint(1, 60)
            if datatype == "alarms":
                detail_dict = json.loads(detailString)
                timestamp = int(detail_dict.get("valueStr")[0].get("timestamp")) + randint(1, 60)
            is_new = "yes"
            save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?,?,?)"
            data = [(None, self.tableversion, datatype, cmd, addr, timestamp, is_new, detailString)]
            conn = DBUtils.get_conn_rt()
            return DBUtils.save(conn, save_sql, data)
        except Exception as err:
            Utils.logException('saveBackup() in DBManagerHistory异常: %s' % err)
            exc_str = traceback.format_exc()
            if exc_str is not None and exc_str.lower().find('database is locked') != -1:
                # database is locked.
                Utils.unlockDatabase()
        return False

    def deleteByKey(self, key, data, maxId):
        if data is None or data == "" or key is None:
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

    def getBackupsByDataType(self, datatype, limit=None):
        Utils.logDebug("->getBackupsByKey() %s" % datatype)
        if datatype is None or datatype == "":
            Utils.logError("getBackupsByKey rx invalid inputs")
            return

        backupsDict = {}
        try:
            conn = DBUtils.get_conn_rt()

            # 组装sql语句
            sql = "select * from " + self.tablename + " where"
            sql += " (" + KEY_BACKUP_DATATYPE + " = '" + datatype + "')"
            sql += " ORDER BY " + KEY_BACKUP_TIME + " asc "
            if limit is not None:
                sql += " limit " + str(limit) + " offset 0 "
            backuparr = DBUtils.fetchall(conn, sql)
            if backuparr is not None:
                for item in backuparr:
                    kid = item[0]
                    detail = json.loads(item[-1])
                    detail[str(kid)] = kid
                    backupsDict[str(kid)] = detail
        except Exception as err:
            Utils.logException('_getBackupsByKey()异常: %s' % err)
            backupsDict.clear()

        if backupsDict is None or len(backupsDict) == 0:
            return None
        else:
            return backupsDict

    def getBackupsByTypes(self, data_type, device_type, limit=None):

        if not data_type or not device_type:
            Utils.logError("getBackupsByTypes, invalid inputs")
            return

        backupsDict = {}
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where "
            sql += "datatype='" + data_type + "' and devicetype='" + device_type + "'"
            sql += " ORDER BY " + KEY_BACKUP_TIME + " asc "
            if limit is not None:
                sql += " limit " + str(limit) + " offset 0 "
            backuparr = DBUtils.fetchall(conn, sql)
            Utils.logInfo("===>getBackupsByTypes, backuparr: %s" % backuparr)
            if backuparr:
                for item in backuparr:
                    kid = item[0]
                    detail = json.loads(item[-1])
                    detail[str(kid)] = kid
                    backupsDict[str(kid)] = detail
                return backupsDict
            return None
        except Exception as err:
            Utils.logException('getBackupsByTypes()异常: %s' % err)
            backupsDict.clear()
            return None

    def getBackupsByTypeAndAddr(self, data_type, device_addr, limit=None):

        if not data_type or not device_addr:
            Utils.logError("getBackupsByTypes, invalid inputs")
            return

        backupsDict = {}
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where "
            sql += "datatype='" + data_type + "' and addr='" + device_addr + "'"
            sql += " ORDER BY " + KEY_BACKUP_TIME + " asc "
            if limit is not None:
                sql += " limit " + str(limit) + " offset 0 "
            backuparr = DBUtils.fetchall(conn, sql)
            Utils.logInfo("===>getBackupsByTypes, backuparr: %s" % backuparr)
            if backuparr:
                for item in backuparr:
                    kid = item[0]
                    detail = json.loads(item[-1])
                    detail[str(kid)] = kid
                    backupsDict[str(kid)] = detail
                return backupsDict
            return None
        except Exception as err:
            Utils.logException('getBackupsByTypes()异常: %s' % err)
            backupsDict.clear()
            return None


    def deleteBackupsByDataType(self, datatype, maxId):
        Utils.logDebug("->deleteBackupsByDataType %s" % datatype)
        if datatype is None or datatype == "":
            Utils.logError("deleteBackupsByDataType rx invalid inputs")
            return
        return self.deleteByKey(KEY_BACKUP_DATATYPE, datatype, maxId)

    def deleteBackupsByDevAddr(self, addr):
        Utils.logDebug("->deleteBackupsByDevAddr %s" % addr)
        if addr is None:
            Utils.logError("deleteBackupsByDevAddr rx invalid inputs")
            return
        return self.deleteByKey(KEY_BACKUP_DEVID, addr, 0)

    def deleteBackupsById(self, keyId):
        Utils.logDebug("->deleteBackupsById %s"%(keyId))
        conn = DBUtils.get_conn_rt()
        sql = "DELETE FROM " + self.tablename + " WHERE " + KEY_ID + " = " + str(keyId) + ""
        DBUtils.deleteone(conn, sql)

    def deleteBackupsByIdInBatch(self, keyIds):
        Utils.logDebug("->deleteBackupsByIdInBatch(): %s" % str(keyIds))
        sql = "DELETE FROM " + self.tablename + " WHERE " + KEY_ID + " =?"
        conn = DBUtils.get_conn_rt()
        DBUtils.executemany(conn, sql, keyIds)

    def getLastBackupByDevAddr(self, addr):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
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
            # 组装sql语句
            sql = "select * from " + self.tablename + " where( "
            where = " (" + KEY_BACKUP_DEVID + " = ?)"
            sql += where + " )"
            sort = " ORDER BY " + KEY_BACKUP_TIME + " asc "
            sql += sort
            return DBUtils.fetchone(conn, sql, addr)
        except:
            Utils.logException('getFirstBackupByDevAddr()异常')
            return None

    def getById(self, record_id):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where id = " + str(record_id)
            devarr = DBUtils.fetchall(conn, sql)
            # devarr应该是[(id, deviId, hostId, type, roomId, area, detail),(...)]数组格式
            if devarr:
                for dev in devarr:
                    detail = json.loads(dev[-1])
                    if not detail:
                        continue
                    detail['id'] = dev[0]
                    return detail
            return None
        except:
            Utils.logException('getById()异常')
            return None

    def updateById(self, record_id, detail_dict):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "update " + self.tablename + " set detail=?" + " where id = " + str(record_id)
            data = [(json.dumps(detail_dict),)]
            return DBUtils.update(conn, sql, data)
        except:
            Utils.logException('updateById()异常')
            return None

    def getByDevAddr(self, addr):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where addr ='" + str(addr) + "' order by timestamp"
            devarr = DBUtils.fetchall(conn, sql)
            # devarr应该是[(id, deviId, hostId, type, roomId, area, detail),(...)]数组格式
            if devarr:
                result_list = list()
                for dev in devarr:
                    detail = json.loads(dev[-1])
                    if not detail:
                        continue
                    detail['id'] = dev[0]
                    result_list.append(detail)
                return result_list
        except:
            Utils.logException('getByDevAddr()异常')
            return None

    def getByDevAddrAndTimeStamp(self, addr, start_time, end_time):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where addr='" + str(addr) + "'"
            sql += " and timestamp>=" + str(start_time)
            sql += " and timestamp<=" + str(end_time) + " order by timestamp"
            Utils.logInfo("===>sql: %s" % sql)
            devarr = DBUtils.fetchall(conn, sql)
            Utils.logInfo("===>sql result: %s" % devarr)
            # devarr应该是[(id, deviId, hostId, type, roomId, area, detail),(...)]数组格式
            if devarr:
                result_list = list()
                for dev in devarr:
                    detail = json.loads(dev[-1])
                    if not detail:
                        continue
                    detail['id'] = dev[0]
                    result_list.append(detail)
                return result_list
        except:
            Utils.logException('getByDevAddrAndTimeStamp()异常')
            return None

    def getByDatatypeAndTimeStamp(self, datatype, start_time, end_time, deviceType=None):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "select * from " + self.tablename + " where datatype='" + datatype + "'"
            if deviceType:
                sql += " and devicetype='" + deviceType + "'"
            sql += " and timestamp >=" + str(start_time)
            sql += " and timestamp <=" + str(end_time) + " order by timestamp"
            devarr = DBUtils.fetchall(conn, sql)
            # devarr应该是[(id, deviId, hostId, type, roomId, area, detail),(...)]数组格式
            if devarr:
                result_list = list()
                for dev in devarr:
                    detail = json.loads(dev[-1])
                    if not detail:
                        continue
                    detail['id'] = dev[0]
                    result_list.append(detail)
                return result_list
        except:
            Utils.logException('getByDevAddr()异常')
            return None

    def batchDeleteById(self, delete_list):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "DELETE from " + self.tablename + " where id in("
            for id in delete_list:
                sql += str(id) + ","
            sql = sql[:-1] + ")"
            Utils.logInfo("===>batchDeleteById, sql: %s" % sql)
            return DBUtils.deleteone(conn, sql)
        except:
            Utils.logException('getByDevAddr()异常')
            return None

    def getNewAlarms(self, user_phone, limit=500):
        try:
            conn = DBUtils.get_conn_rt()
            # 组装sql语句
            sql = "SELECT * from " + self.tablename + " where datatype='alarms' and is_new='yes' ORDER BY timestamp desc"
            if limit is not None:
                sql += " limit " + str(limit) + " offset 0 "
            Utils.logInfo("===>getNewAlarms, sql: %s" % sql)
            devarr = DBUtils.fetchall(conn, sql)
            msg_list = list()
            id_list = list()
            # alarm_list = list()
            if devarr:
                for dev in devarr:
                    detail = json.loads(dev[-1])
                    if not detail:
                        continue
                    # one_result = dict(id=dev[0], message=detail.get("valueStr")[0].get("message"))
                    # alarm_list.append(one_result)
                    if user_phone not in detail.get("userList"):
                        alarming = detail.get("valueStr")[0].get("alarming")
                        Utils.logInfo("===>alarming in getNewAlarms: %s" % alarming)
                        if detail.get("valueStr")[0].get("alarming") == "1" or detail.get("valueStr")[0].get("alarming") == 1:
                            id_list.append(dev[0])
                            msg_list.append(detail.get("valueStr")[0].get("message"))
            return id_list, msg_list
            # return alarm_list
        except Exception as err:
            Utils.logException('getNewAlarms() error: %s' % err)
            return None, None

    def updateIsNew(self, addr, timestamp):
        if not addr or not timestamp:
            return
        try:
            sql = "UPDATE " + self.tablename + " SET is_new='no'" + " WHERE addr='" + str(addr) + "'"
            sql += " and timestamp='" + str(timestamp) + "'"
            conn = DBUtils.get_conn_rt()
            success = DBUtils.update_all(conn, sql)
            return success
        except Exception as err:
            Utils.logError("updateIsNew() error: %s" % err)
            return None

    def updateIsNew2(self, id_list):
        if not id_list:
            return None
        try:
            sql = "UPDATE " + self.tablename + " SET is_new='no'" + " WHERE id in("
            for id in id_list:
                sql += str(id) + ","
            sql = sql[:-1] + ")"
            conn = DBUtils.get_conn_rt()
            success = DBUtils.update_all(conn, sql)
            return success
        except Exception as err:
            Utils.logError("updateIsNew() error: %s" % err)
            return None

    def updateUserList(self, id_list, user_phone):
        if not id_list:
            return None
        try:
            for alarm_id in id_list:
                self.__updateUserList(alarm_id, user_phone)
        except Exception as err:
            Utils.logError("===>updateUserList error: %s" % err)

    def __updateUserList(self, alarm_id, user_phone):
        if not id or not user_phone:
            return None
        try:
            detail = self.getById(alarm_id)
            detail.get("userList", []).append(user_phone)
            detail_str = json.dumps(detail)
            sql = "UPDATE " + self.tablename + " SET detail='" + detail_str + "' where id=" + str(alarm_id)
            conn = DBUtils.get_conn_rt()
            success = DBUtils.update_all(conn, sql)
            return success
        except Exception as err:
            Utils.logError("updateIsNew() error: %s" % err)
            return None

    def getAlarmTotal(self):
        try:
            sql = "SELECT count(*) from " + self.tablename + "' where datatype='alarms'"
            conn = DBUtils.get_conn_rt()
            success = DBUtils.update_all(conn, sql)
            return success
        except Exception as err:
            Utils.logError("updateIsNew() error: %s" % err)
            return None

