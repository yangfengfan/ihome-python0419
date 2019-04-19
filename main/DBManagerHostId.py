#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import time
import json
import Utils

TABLE_NAME_HOST = "tbl_host"

KEY_ID = "id"
KEY_VERSION = "version"
KEY_HOST_NAME = "name"
KEY_HOST_ID = "hostId"
KEY_HOST_DETAIL = "detail"

class DBManagerHostId(object):
    __instant = None;
    __lock = threading.Lock();
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerHostId.__instant==None):
            DBManagerHostId.__lock.acquire();
            try:
                if(DBManagerHostId.__instant==None):
                    Utils.logDebug("new DBManagerHostId singleton instance.")
                    DBManagerHostId.__instant = object.__new__(self);
            finally:
                DBManagerHostId.__lock.release()
        return DBManagerHostId.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_HOST
        self.tableversion = 1
        self.defaultHostId = "-no-hostid-"
        self.defaultHostName = "boer-host"
        self.createHostIdTable()
    
    def createHostIdTable(self):
        Utils.logDebug("->createHostIdTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_HOST_NAME + "` varchar(50) NOT NULL,"
        create_table_sql += " `" + KEY_HOST_ID + "` varchar(50) NOT NULL UNIQUE,"
        create_table_sql += " `" + KEY_HOST_DETAIL + "` TEXT"
        create_table_sql += " )"
        conn = DBUtils.get_conn()
        DBUtils.create_table(conn, create_table_sql)

    # 检查数据库文件状态
    # host.db存放配置数据
    # 如果数据库文件损坏，fetchall()应抛出异常
    def checkDBHealthy(self):
        conn = DBUtils.get_conn()
        sql = "select * from " + self.tablename
        DBUtils.fetchall(conn, sql)

    def getByHostId(self, hostId):
        conn = DBUtils.get_conn()
        fetchall_sql = "select * from " + self.tablename + " where " + KEY_HOST_ID + " = '" + hostId + "'"
        arr = DBUtils.fetchall(conn, fetchall_sql)
        if(arr != None and len(arr) > 0):
            host = arr[0]
            str = host[-1]
            if str != None:
                return json.loads(str)
        return None

    def checkHostConfigIntegerity(self, detailObj):
        if detailObj.has_key("softver") == False:
            return False
        if detailObj.has_key("firmver") == False:
            return False
        if detailObj.has_key("registerHost") == False:
            return False
        # if detailObj.has_key("numbers") == False:
        #     return False
        return True

    # 在host属性的detail中的room列表丢失而room表存在房间时更新host的detail数据
    def updateHostDetail(self, detail, hostId):
        if detail == None:
            Utils.logWarn("-> updateHostDetail(): detail is None")
            return None

        if self.checkHostConfigIntegerity(detail) == False:
            Utils.logError('@###Error host config! refused.')
            return None

        detail["timestamp"] = int(time.time())
        detailString = json.dumps(detail)

        update_sql = "UPDATE " + self.tablename + " SET "
        update_sql += KEY_HOST_DETAIL + " = ? "
        update_sql += " WHERE "+ KEY_HOST_ID + " = ? "
        data = [(detailString, hostId)]
        conn = DBUtils.get_conn()
        success = DBUtils.update(conn, update_sql, data)
        if success == True:
            return detail
        else:
            Utils.logWarn("Update host detail failed")
            return None


    def updateHostConfig(self, hostId, hostName, detailObj, oldtimestamp = None):
        if hostId == None or hostName == None or detailObj == None:
            return None
        Utils.logDebug("->updateHostConfig() %s"%(detailObj))

        if self.checkHostConfigIntegerity(detailObj) == False:
            Utils.logError('@###Error host config! refused.')
            return None

        # newtimestamp = None
        # if detailObj.has_key("timestamp"):
        #     newtimestamp = detailObj.get("timestamp")
        # if oldtimestamp != None and newtimestamp != oldtimestamp:
        #     return None

        detailObj["timestamp"] = int(time.time())

        detailString = json.dumps(detailObj)
        update_sql = "UPDATE " + self.tablename + " SET "
        update_sql += " " + KEY_HOST_NAME + " = ? " 
        update_sql += "," + KEY_HOST_DETAIL + " = ? "
        update_sql += " WHERE "+ KEY_HOST_ID + " = ? "
        data = [(hostName, detailString, hostId)]
        conn = DBUtils.get_conn()
        success = DBUtils.update(conn, update_sql, data)
        if success == True:
            return detailObj
        else:
            return None
    
    def saveHostConfig(self, hostId, hostName, detailObj):
        if hostId == None or hostName == None or detailObj == None:
            return False
        save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?)"
        try:
            data = [(None, self.tableversion, hostName, hostId, json.dumps(detailObj))]
        except UnicodeDecodeError:  # GWID 文件可能会是GBK编码，需要捕捉处理
            Utils.logInfo("saveHostConfig() data decode error with utf-8, try to decode with gbk")
            data = [(None, self.tableversion, hostName, hostId, json.dumps(detailObj, encoding='gbk'))]
        conn = DBUtils.get_conn()
        return DBUtils.save(conn, save_sql, data)

    def _deleteByKey(self, key, data):
        if(data is None or data == "" or key is None):
            Utils.logError('deleteByKey has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn()
            sql = "DELETE FROM " + self.tablename + " WHERE " + key + " = '" + data + "'"
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByKey()异常')
            return False

    def deleteByHostId(self, hostId):
        return self._deleteByKey(KEY_HOST_ID, hostId)

    def initHostProp(self, hostId, hostName = None):
        Utils.logDebug("->initHostProp %s"%(hostId))
        if(hostId is None or hostId == ""):
            return None
        try:
            if hostName == None:
                hostName = self.defaultHostName

            firmver = Utils.getFirmwareVersion()
            softver = Utils.getSoftwareVersion()
            channel_info = Utils.getPandId()
            area_info = Utils.getAreaInfo()

            pand_id = channel_info.get("pand_id", "")
            channel_no = channel_info.get("channel_no", "")
            zbsVer = channel_info.get("zbsVer", "")
            zbhVer = channel_info.get("zbhVer", "")

            hostDict = {}
            hostDict["name"] = hostName
            hostDict["hostId"] = hostId
            hostDict["registerHost"] = True
            hostDict["softver"] = softver
            hostDict["firmver"] = firmver
            hostDict["numbers"] = ""
            # 网关通道信息
            hostDict["pandId"] = pand_id
            hostDict["channelNo"] = channel_no
            # zigbee版本
            hostDict["zbsVer"] = zbsVer
            hostDict["zbhVer"] = zbhVer
            if area_info:
                # 网关地区信息
                hostDict["country"] = area_info.get("contryCode", "")  # 国家码
                hostDict["city"] = area_info.get("cityCode", "")  # 城市编码，国内为电话区号
                hostDict["language"] = area_info.get("languageCode", "0")  # 0-中文；1-英文
                hostDict["developer"] = area_info.get("landDeveloperCode", "")  # 房地产开发商，如：碧桂园
                hostDict["neighbourhood"] = area_info.get("neighbourhood", "")  # 小区名，如：天玺
            hostDict["timestamp"] = int(time.time())
            save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?)"
            try:
                data = [(None, self.tableversion, self.defaultHostName, hostId, json.dumps(hostDict))]
            except UnicodeDecodeError:  # GWID 文件可能会是GBK编码，需要捕捉处理
                Utils.logInfo("initHostProp() data decode error with utf-8, try to decode with gbk")
                data = [(None, self.tableversion, self.defaultHostName, hostId, json.dumps(hostDict, encoding='gbk'))]
            conn = DBUtils.get_conn()
            success = DBUtils.save(conn, save_sql, data)
            if success == True:
                return hostDict
            return None
        except:
            Utils.logException('initHostProp()异常')
        return None

    def setHostName(self, hostName):
        Utils.logDebug("->setHostName %s"%(hostName))
        try:
            detailObj = self.getHost()
            hostId = detailObj.get("hostId", None)
            detailObj["name"] = hostName
            oldtimestamp = None
            if detailObj.has_key("timestamp"):
                oldtimestamp = detailObj.get("timestamp")
            return self.updateHostConfig(hostId, hostName, detailObj, oldtimestamp)
        except:
            Utils.logException('setHostName()异常')
        return None

    def getHost(self):
        conn = DBUtils.get_conn()
        fetchall_sql = "select * from " + self.tablename
        result = DBUtils.fetchall(conn, fetchall_sql)
        if(result is None or len(result) < 1):
            return None
        host = result[0]
        return json.loads(host[-1])

    def getHostName(self):
        Utils.logDebug("->getHostName")
        hostName = None
        try:
            result = self.getHost()
            if result is not None and len(result) > 0:
                hostName = result.get("name", "")
                if isinstance(hostName, unicode) == True:
                    hostName = hostName.encode('utf-8')
            return hostName
        except:
            Utils.logException('getHostName()异常,')
        return None

    def getHostId(self):
        Utils.logDebug("->getHostId")
        hostId = None
        try:
            result = self.getHost()
            if result is not None:
                hostId = result.get("hostId", None)
            return hostId
        except:
            Utils.logException('getHostId()异常,')
            return hostId

if __name__ == '__main__':
    h1 = DBManagerHostId()
    h2 = DBManagerHostId()
    hostId = h1.getHostId()
    print hostId
    h1.initHostProp("ID valid or not?")
    print h2.getHostId()
    print h2.getHostName()
    print h2.setHostName("defalut hostname")
    print h1.getHostName()
