#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
from DBManagerDeviceProp import *
from DBManagerRoom import *

#设备表数据库名
TABLE_NAME_ROOM_AREA = "tbl_area"


KEY_ID = "id"
KEY_VERSION = "version"
KEY_AREA_ID = "areaId"        #功能区域名称
KEY_ROOM_ID = "roomId"        #所在的房间
KEY_AREA_DETAIL = "detail"    #详细json


###所有的device属性都添加一个"timestamp"，表明当前的device属性更新时间。
###属性同步到云端后，云端可根据timestamp决定哪个同步命令是最新的，从而不会拿旧的属性覆盖新的属性
###备份时不能修改"timestamp"的值。
class DBManagerRoomArea(object):
    __instant = None;
    __lock = threading.Lock();
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerRoomArea.__instant==None):
            DBManagerRoomArea.__lock.acquire();
            try:
                if(DBManagerRoomArea.__instant==None):
                    Utils.logDebug("new DBManagerRoomArea singleton instance.")
                    DBManagerRoomArea.__instant = object.__new__(self);
            finally:
                DBManagerRoomArea.__lock.release()
        return DBManagerRoomArea.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_ROOM_AREA
        self.tableversion = 1
        self.createAreaTable()

    def createAreaTable(self):
        Utils.logDebug("->createAreaTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_AREA_ID + "` varchar(10) NOT NULL,"
        create_table_sql += " `" + KEY_ROOM_ID + "` varchar(10) NOT NULL,"
        create_table_sql += " `" + KEY_AREA_DETAIL + "` TEXT,"
        create_table_sql += " CONSTRAINT ra UNIQUE (areaId, roomId)"
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
    
    #detailJsonStr是设备详情所有属性的Json格式化串
    def saveAreaProperty(self, detailObj):
        Utils.logDebug("->saveAreaProperty %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveAreaProperty() rx invalid inputs %s'%(detailObj))
            return None
        try:
            room = detailObj.get(KEY_ROOM_ID, None)
            area = detailObj.get(KEY_AREA_ID, None)
            if room is None or area is None:
                Utils.logError('saveAreaProperty() error params: room %s, area %s'%(room, area))
                return None

            # newtimestamp = None
            # if detailObj.has_key("timestamp"):
            #     newtimestamp = detailObj.get("timestamp")

            areaAllDetailJsonStr = None
            success = True
            item = self.getAreaBy(room, area)
            if(item is None):

                # detailObj["timestamp"] = int(time.time())
                areaAllDetailJsonStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?)"
                data = [(None, self.tableversion, area, room, areaAllDetailJsonStr)]
                conn = DBUtils.get_conn()
                success = DBUtils.save(conn, save_sql, data)
            else:
                # oldtimestamp = item.get("timestamp", None)
                # if oldtimestamp != None and newtimestamp != oldtimestamp:
                #     return item
                # detailObj["timestamp"] = int(time.time())
                #
                update_sql = 'UPDATE ' + self.tablename + ' SET ' 
                update_sql += ' ' + KEY_AREA_DETAIL + ' = ? ' 
                update_sql += ' WHERE '+ KEY_ROOM_ID + ' = ? and ' + KEY_AREA_ID + ' = ? '
                
                areaAllDetailJsonStr = json.dumps(detailObj)
                data = [(areaAllDetailJsonStr, room, area)]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)

                oldName = item.get("name")
                newName = detailObj.get("name")

                if newName != oldName:
                    # # 区域名称修改后，区域内的设备的属性表内的区域名称也要跟着修改
                    # devices = DBManagerDeviceProp().getDevicePropertyBy(room, area, None)
                    #
                    # if devices is not None and len(devices) > 0:
                    #     for device in devices:
                    #
                    #         device["areaname"] = newName
                    #         #DBManagerDeviceProp().saveDeviceProperty(device)
                    #     DBManagerDeviceProp().saveDeviceBatch(devices, devOpt=True)
                    #
                    # # 更新 tbl_room 表中对应房间的area信息 --- 20170703 chenjc
                    # roomProp = DBManagerRoom().getRoomByRoomId(room)
                    # area_list = roomProp.get("areas", [])
                    # for areaProp in area_list:
                    #     if areaProp.get("areaId") == area:
                    #         areaProp["name"] = newName
                    # roomProp["areas"] = area_list
                    # DBManagerRoom().saveRoomProperty(roomProp)

                    # 区域名称修改后，区域内的设备的属性表内的区域名称也要跟着修改
                    devices = DBManagerDeviceProp().getDevicePropertyBy(None, None, "all")

                    if devices is not None and len(devices) > 0:
                        for device in devices:
                            # Utils.logError('--------device====== %s' % str(device))
                            if device.get("roomId") == room and device.get("areaId") == area:
                                # Utils.logError('--------device["areaname"]====== %s' % str(device["areaname"]))
                                device["areaname"] = newName
                            if device.get("linkOnlyOneSwitch"):
                                if device.get("linkOnlyOneSwitch").get("deviceProp"):
                                    if device.get("linkOnlyOneSwitch").get("deviceProp").get("roomId") == room \
                                            and device.get("linkOnlyOneSwitch").get("deviceProp").get("areaId") == area:
                                        Utils.logError('--------device.get("linkOnlyOneSwitch").get("deviceProp")["areaname"]====== %s' % str(device.get("linkOnlyOneSwitch").get("deviceProp")["areaname"]))
                                        device.get("linkOnlyOneSwitch").get("deviceProp")["areaname"] = newName
                            if device.get("linkLightSensor"):
                                if device.get("linkLightSensor").get("deviceProp"):
                                    if device.get("linkLightSensor").get("deviceProp").get("roomId") == room \
                                            and device.get("linkLightSensor").get("deviceProp").get("areaId") == area:
                                        device.get("linkLightSensor").get("deviceProp")["areaname"] = newName
                            #DBManagerDeviceProp().saveDeviceProperty(device)
                        DBManagerDeviceProp().saveDeviceBatch(devices, devOpt=True)

                    # 更新 tbl_room 表中对应房间的area信息 --- 20170703 chenjc
                    roomProp = DBManagerRoom().getRoomByRoomId(room)
                    area_list = roomProp.get("areas", [])
                    for areaProp in area_list:
                        if areaProp.get("areaId") == area:
                            areaProp["name"] = newName
                    roomProp["areas"] = area_list
                    DBManagerRoom().saveRoomProperty(roomProp)

            if success == True:
                return detailObj
        except:
            Utils.logException('saveAreaProperty()异常 ')
        return None
            
    def getByCondition(self, conditionDict):
        resultDict = {}
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('getByCondition has invalid where condition')
            return resultDict
        try:
            conn = DBUtils.get_conn()
            
            #组装sql语句
            sql = "select * from " + self.tablename + " where( "
            where = ""
            for key in conditionDict.keys():
                if(where != ""):
                    where += " and "
                where += "(" + key + " = " + str(conditionDict[key]) + ")"
            sql += where + " )"
            
            alarmarr = DBUtils.fetchall(conn, sql)
            #alarmarr应该是[(id, timeId, devId, hostId, type, confirmed, detail),(...)]数组格式
            if(alarmarr is not None):
                for dev in alarmarr:
                    resultDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
        except:
            Utils.logException('getByCondition()异常 ')
            resultDict.clear()
        return resultDict.values()

    #返回满足条件的所有设备的json格式串 组成的数组
    # def _getByKey(self, key, data):
    #     deviceDict = {}
    #     if(data is None or data == "" or key is None):
    #         Utils.logError('_getByKey has invalid where condition')
    #         return deviceDict
    #     try:
    #         conn = DBUtils.get_conn()
    #         sql = "select * from " + self.tablename + " where " + key + " = '"+ data + "'"
    #         devarr = DBUtils.fetchall(conn, sql)
    #         #devarr应该是[(id, deviId, hostId, type, room, area, detail),(...)]数组格式
    #         if(devarr is not None):
    #             for dev in devarr:
    #                 deviceDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
    #     except:
    #         Utils.logError('_getByKey()异常 ')
    #         deviceDict.clear()
    #     return deviceDict.values()

    # def getAllAreas(self):
    #     Utils.logDebug("->getAllAreas()")
    #     deviceDict = {}
    #     try:
    #         conn = DBUtils.get_conn()
    #         sql = "select * from " + self.tablename
    #         devarr = DBUtils.fetchall(conn, sql)
    #         if(devarr is not None):
    #             for dev in devarr:
    #                 deviceDict[dev[0]] = json.loads(dev[-1])
    #                 #detail总是应该放在最后的字段
    #     except:
    #         Utils.logError('getAllAreas()异常 ')
    #         deviceDict.clear()
    #     if deviceDict == None:
    #         return None
    #     return deviceDict.values()
        
    #返回json格式串
    def getAreaBy(self, room, area):
        Utils.logDebug("->getAreaBy %s,%s"%(room, area))

        conds = {}
        if(room is None or area is None):
            Utils.logError("getAreaBy rx invalid inputs")
            return None
        else:
            conds[KEY_ROOM_ID] = "'" + room + "'"
            conds[KEY_AREA_ID] = "'" + area + "'"
        result = self.getByCondition(conds)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]

    def deleteAreaBy(self, room, area):
        Utils.logDebug("->deleteAreaBy %s,%s"%(room, area))
        if(room is None or area is None):
            Utils.logError('deleteAreaBy has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn()
            sql  = "DELETE FROM " + self.tablename 
            sql += " WHERE " + KEY_ROOM_ID + " = " + room + " and " + KEY_AREA_ID + " = " + area
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteAreaBy()异常 ')
            return False

    def deleteAreasByRoomId(self, room):
        Utils.logDebug("->deleteAreasByRoomId %s"%(room))
        if(room is None):
            Utils.logError('deleteAreasByRoomId has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn()
            sql  = "DELETE FROM " + self.tablename 
            sql += " WHERE " + KEY_ROOM_ID + " = " + room
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteAreasByRoomId()异常 ')
            return False

if __name__ == '__main__':
    d1 = DBManagerRoomArea()
    d2 = DBManagerRoomArea()
    print "getAreaBy:", d1.getAreaBy("devIdvalue",None)
    
    devDict={"roomId":"1","name":"客厅","areaId":"1","picture":"a1.png"}
    d2.saveAreaProperty(devDict)

    devDict2={"roomId":"1","name":"客厅","areaId":"2","picture":"a2.png"}
    d2.saveAreaProperty(devDict2)
    
    print "============================="
    r11 = d2.getAreaBy("1","1")
    if(r11.get("picture") == u'a1.png'):
        print "========getAreaBy:SUCCESS============"
    else:
        print "*********************getAreaBy:Failed"

    d1.deleteAreaBy("1","1")
    if d2.getAreaBy("1","1") == None:
        print "==========deleteAreaBy SUCCESS============"
    else:
        print "***********************deleteAreaBy Failed"

    devDict={"roomId":"1","name":"客厅","areaId":"1","picture":"a1.png"}
    d2.saveAreaProperty(devDict)

    d1.deleteAreasByRoomId("1")
    if d2.getAreaBy("1","1") == None and d1.getAreaBy("1", "2") == None:
        print "==========deleteAreaBy SUCCESS============"
    else:
        print "***********************deleteAreaBy Failed"