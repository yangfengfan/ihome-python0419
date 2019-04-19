#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
import traceback
from DBManagerDeviceProp import *


#设备表数据库名
TABLE_NAME_DEVICE = "tbl_device_status"


KEY_ID = "id"
KEY_VERSION = "version"
KEY_DEVICE_ADDR = "addr"      #设备Id/Mac
KEY_DEVICE_DETAIL = "detail"    #详细json


class DBManagerDevice(object):
    __instant = None;
    __lock = threading.Lock()
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerDevice.__instant==None):
            DBManagerDevice.__lock.acquire()
            try:
                if(DBManagerDevice.__instant==None):
                    Utils.logDebug("new DBManagerDevice singleton instance.")
                    DBManagerDevice.__instant = object.__new__(self)
            finally:
                DBManagerDevice.__lock.release()
        return DBManagerDevice.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_DEVICE
        self.tableversion = 1
        self.createDeviceTable()

    def createDeviceTable(self):
        Utils.logDebug("->createDeviceTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_DEVICE_ADDR +  "` varchar(50) NOT NULL UNIQUE,"
        create_table_sql += " `" + KEY_DEVICE_DETAIL + "` TEXT"
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

    def initDevStatus(self, devpropobj):
        macAddr = devpropobj.get("addr", None)
        # deviceAddr = PacketParser.getDevAddrByMac(macAddr)
        if macAddr == None:
            return
        # deviceAddr = self.getDevAddr(macAddr)
        deviceAddr = macAddr
        devItem = self.getDeviceByDevId(deviceAddr)
        if(devItem is None):
            devStatusObj = {}
            devStatusObj["name"] = devpropobj.get("name", None)
            devStatusObj["type"] = devpropobj.get("type", None)
            devStatusObj["addr"] = deviceAddr
            devStatusObj["time"] = int(time.time())
            protocol = devpropobj.get("protocol", None)
            if protocol is not None:
                devStatusObj["protocol"] = protocol
            self.saveDeviceStatus(devStatusObj)
            del devStatusObj
    
    # detailJsonStr是设备详情所有属性的Json格式化串
    def saveDeviceStatus(self, detailObj):
        Utils.logDebug("->saveDeviceStatus %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveDeviceStatus() rx invalid inputs %s'%(detailObj))
            return None
        try:
            # detailObj = json.loads(devAllDetailJsonStr)
            deviceAddr = detailObj.get(KEY_DEVICE_ADDR, None)
            if deviceAddr == None or deviceAddr == "":
                return None
            # detailObj["timestamp"] = int(time.time())

            devAllDetailJsonStr = None
            success = True
            devItem = self.getDeviceByDevId(deviceAddr)
            if(devItem is None):
                devAllDetailJsonStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?)"
                data = [(None, self.tableversion, deviceAddr, devAllDetailJsonStr)]
                conn = DBUtils.get_conn_rt()
                success = DBUtils.save(conn, save_sql, data)
            else:
                # 从设备上报状态时，设备属性不会携带room，area信息
                update_sql = 'UPDATE ' + self.tablename + ' SET ' 
                update_sql += ' ' + KEY_DEVICE_DETAIL + ' = ? ' 
                update_sql += ' WHERE '+ KEY_DEVICE_ADDR + ' = ? '
                
                devAllDetailJsonStr = json.dumps(detailObj)
                data = [(devAllDetailJsonStr, deviceAddr)]
                conn = DBUtils.get_conn_rt()
                success = DBUtils.update(conn, update_sql, data)
            if success == True:
                return detailObj
        except:
            Utils.logException('saveDeviceStatus()异常')
            exc_str = traceback.format_exc()
            if exc_str != None and exc_str.lower().find('database is locked') != -1:
                # database is locked.
                Utils.unlockDatabase()
        return None
            
    # def _getByCondition(self, where, data):
    #     conn = DBUtils.get_conn_rt()
    #     sql = "select * from " + self.tablename + " " + where
    #     return DBUtils.fetchByCondition(conn, sql, data)

    # 返回满足条件的所有设备的json格式串 组成的数组
    def getByKey(self, key, data):
        deviceDict = {}
        if(data is None or data == "" or key is None):
            Utils.logError('DBManagerDevice: getByKey has invalid where condition')
            return deviceDict
        try:
            conn = DBUtils.get_conn_rt()
            sql = "select * from " + self.tablename + " where " + key + " = '"+ data + "'"
            devarr = DBUtils.fetchall(conn, sql)
            # devarr应该是[(id, deviId, hostId, type, room, area, detail),(...)]数组格式
            if(devarr is not None):
                for dev in devarr:
                    deviceDict[dev[0]] = json.loads(dev[-1])        # detail总是应该放在最后的字段
        except:
            Utils.logException('getByKey()异常')
            deviceDict.clear()
        return deviceDict.values()
        
    def deleteByKey(self, key, data):
        if(data is None or data == "" or key is None):
            Utils.logError('deleteByKey has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn_rt()
            sql = "DELETE FROM " + self.tablename + " WHERE " + key + " = '" + data + "'"
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByKey()异常')
            return False

    # def getAllDevices(self):
    #     Utils.logDebug("->getAllDevices()")
    #     deviceDict = {}
    #     try:
    #         conn = DBUtils.get_conn_rt()
    #         sql = "select * from " + self.tablename
    #         devarr = DBUtils.fetchall(conn, sql)
    #         #devarr应该是[{"id":"ss", "deviId":"ss", hostId, type, room, area, detail),(...)]数组格式
    #         if(devarr is not None):
    #             for dev in devarr:
    #                 deviceDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
    #     except:
    #         Utils.logError('getAllDevices()异常')
    #         deviceDict.clear()
    #     if len(deviceDict) == 0:
    #         return None
    #     return deviceDict.values()

    # 根据设备地址和类型返回设备状态记录
    def getDeviceByDevAddrAndType(self, addr, type):
        devices = self.getDeviceByDevType(type)
        if devices is not None and len(devices) > 0:
            for item in devices:
                if item.get("addr") == addr:
                    return item
        else:
            return None

    # 根据设备类型返回设备状态记录  rtnDict：返回类型标记，当为True时返回字典类型，使用于 device/queryAllDevice 请求
    def getDeviceByDevType(self, type, rtnDict=False):

        try:
            conn = DBUtils.get_conn_rt()
            sql = "select * from " + self.tablename
            allResults = DBUtils.fetchall(conn, sql)

            result = []
            if allResults is not None:
                for item in allResults:
                    # item = eval(item[-1])
                    item = json.loads(item[-1])
                    if item.get("type") == type:
                        result.append(item)
            if rtnDict:
                status_dict = {}
                for status in result:
                    status_dict[status.get("addr")] = status
                return status_dict
            else:
                return result
        except:
            Utils.logError("DataBase Error！")
        return None

    # 返回json格式串
    def getDeviceByDevId(self, deviceAddr):
        Utils.logDebug("->getDeviceByDevId %s"%(deviceAddr))
        result = self.getByKey(KEY_DEVICE_ADDR, deviceAddr)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]    #返回json


    # 根据设备地址列表查询设备状态
    # 返回结构：[{'addr': '97632F04004B12000000', 'type': 'Exist', 'name': '\u5b58\u5728\u4f20\u611f\u5668', 'value': {'state': 0, 'set': 0, 'lvolt': 0, 'powerPercent': 0}, 'time': 1482471017}, {...}, ...]
    def getDeviceStatusByDevIdList(self, deviceAddrList):
        Utils.logDebug("-> getDeviceStatusByDevIdList(),deviceAddrList: %s" % str(deviceAddrList))

        addr_str = ""
        for index, addr in enumerate(deviceAddrList):
            if index == len(deviceAddrList) - 1:
                addr_str += "'" + addr + "'"
            else:
                addr_str += "'" + addr + "'" + ","
        # addr_str = reduce(lambda x, y: "'" + x + "'" + ',' + "'" + y + "'", deviceAddrList)
        deviceDict = {}
        sql = "select * from " + self.tablename + " where addr in (" + addr_str + ")"
        conn = DBUtils.get_conn_rt()

        try:
            devarr = DBUtils.fetchall(conn, sql)
            if devarr is not None:
                for dev in devarr:
                    deviceDict[dev[0]] = json.loads(dev[-1])
        except:
            Utils.logException("->getDeviceStatusByDevIdList() error...")
            deviceDict.clear()
        return deviceDict.values()

    # def getDeviceByType(self, devType):
    #     Utils.logDebug("->getDeviceByType %s"%(devType))
    #     result = self.getByKey(KEY_DEVICE_TYPE, devType)
    #     if(len(result) == 0):
    #         return None
    #     else:
    #         return json.dumps(result)
        
    # def getDeviceByRoom(self, room):
    #     Utils.logDebug("->getDeviceByRoom %s"%(room))
    #     result = self.getByKey(KEY_DEVICE_ROOM, room)
    #     if(len(result) == 0):
    #         return None
    #     else:
    #         return json.dumps(result)
    #
    # def getDeviceByArea(self, area):
    #     Utils.logDebug("->getDeviceByArea %s"%(area))
    #     result = self.getByKey(KEY_DEVICE_AREA, area)
    #     if(len(result) == 0):
    #         return None
    #     else:
    #         return json.dumps(result)

    def deleteDeviceById(self, devAddr):
        Utils.logDebug("->deleteDeviceById %s"%(devAddr))
        return self.deleteByKey(KEY_DEVICE_ADDR, devAddr)

    # 只用在APP首界面查询设备列表时查询所有设备状态，用在 device/queryAllDevices 请求内
    def get_all_status(self):
        status_list = list()
        status_dict = {}
        try:
            conn = DBUtils.get_conn_rt()
            sql = "select * from " + self.tablename
            fetch_result = DBUtils.fetchall(conn, sql)
            # devarr应该是[{"id":"ss", "deviId":"ss", hostId, type, roomId, area, detail),(...)]数组格式
            if fetch_result is not None and len(fetch_result) > 0:
                for item in fetch_result:
                    # deviceDict[dev[0]] = json.loads(dev[-1])        # detail总是应该放在最后的字段
                    detail = json.loads(item[-1])
                    if detail is None or len(detail) == 0:
                        continue
                    detail['keyId'] = item[0]
                    status_list.append(detail)  # detail总是应该放在最后的字段
        except:
            Utils.logException('get_all() exception...')
        if status_list is None or len(status_list) == 0:
            return None
        for status in status_list:
            status_dict[status.get("addr")] = status
        return status_dict

    # 根据状态获取所有调光控制面板的列表
    def getLightAdjustPannelByState(self, state):
        pannel_list = self.getDeviceByDevType("LightAdjustPannel")
        result_list = []
        for pannel in pannel_list:
            value = pannel.get("value", {})
            status = value.get("state")
            if status == state:
                result_list.append(pannel)
        return result_list

    def getDeviceStatusForRokid(self, deviceAddrList):
        Utils.logDebug("-> getDeviceStatusForRokid(),deviceAddrList: %s" % str(deviceAddrList))

        addr_str = ""
        for index, addr in enumerate(deviceAddrList):
            if index == len(deviceAddrList) - 1:
                addr_str += "'" + addr + "'"
            else:
                addr_str += "'" + addr + "'" + ","
        # addr_str = reduce(lambda x, y: "'" + x + "'" + ',' + "'" + y + "'", deviceAddrList)
        deviceDict = {}
        sql = "select * from " + self.tablename + " where addr in (" + addr_str + ")"
        conn = DBUtils.get_conn_rt()

        try:
            devarr = DBUtils.fetchall(conn, sql)
            if devarr is not None:
                for dev in devarr:
                    detail = json.loads(dev[-1])
                    dev_type = detail.get('type')
                    value = detail.get('value', None)
                    stateDict = {}
                    if value:
                        state = value.get('state', 0)
                        stateDict['switch'] = 'off'
                        if state and int(state) == 1:
                            stateDict['switch'] = 'on'

                    else:
                        stateDict = {'switch': 'off'}

                    deviceDict[dev[2]] = stateDict
        except:
            Utils.logException("->getDeviceStatusForRokid() error...")
            deviceDict.clear()
        return deviceDict


if __name__ == '__main__':
    d1 = DBManagerDevice()
    d2 = DBManagerDevice()
    # print "getDeviceByRoom:", d1.getDeviceByRoom("")
    # print "getDeviceByRoom:", d1.getDeviceByRoom("1")
    # print "getDeviceByArea:", d1.getDeviceByArea("area")
    # print "getDeviceByType:", d1.getDeviceByType("type")
    print "getDeviceByDevId:", d1.getDeviceByDevId("devIdvalue")
    
    # devDict={"deviceId":"devIdvalue","hostId":"hostIdvalue","room":"roomvalue","area":"areavalue","type":"typevalue"}
    devDict={"addr":"z-347D4501004B12001233","value":{"state":"0","coeff":"1"}}
    d2.saveDeviceStatus(devDict)
    # devDict2={"deviceId":"devIdvalue2","hostId":"hostIdvalue","room":"roomvalue","area":"areavalue2","type":"typevalue"}
    
    devDict2={"name":"三联灯","type":"Light1","roomId":"1","room":"厨房","area":"areavalue2","addr":"z-347D4501004B12001234","value":{"state":"1","coeff":"1"}}
    d2.saveDeviceStatus(devDict2)
    
    print "============================="
    # print "getDeviceByRoom:", d2.getDeviceByRoom("客厅")
    # print "getDeviceByArea:", d2.getDeviceByArea("areavalue2")
    # print "getDeviceByType:", d2.getDeviceByType("light")
    l = d2.getDeviceByDevId("z-347D4501004B12001234")
    if l != None and l.get("name","") == u'三联灯':
        print "=========getDeviceByDevId SUCCESS===================="
    else:
        print "**************getDeviceByDevId FAILED"
    d1.deleteDeviceById("z-347D4501004B12001234")
    l = d2.getDeviceByDevId("z-347D4501004B12001234")
    if l == None:
        print "=========getDeviceByDevId SUCCESS===================="
    else:
        print "**************getDeviceByDevId FAILED"
