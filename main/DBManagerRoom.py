#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
from DBManagerDeviceProp import DBManagerDeviceProp

# 设备表数据库名
TABLE_NAME_ROOM = "tbl_room"


KEY_ID = "id"
KEY_VERSION = "version"
KEY_ROOM_ID = "roomId"        # 房间Id
KEY_ROOM_DETAIL = "detail"    # 详细json


# 所有的device属性都添加一个"timestamp"，表明当前的device属性更新时间。
# 属性同步到云端后，云端可根据timestamp决定哪个同步命令是最新的，从而不会拿旧的属性覆盖新的属性
# 备份时不能修改"timestamp"的值。
class DBManagerRoom(object):
    __instant = None
    __lock = threading.Lock()
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerRoom.__instant==None):
            DBManagerRoom.__lock.acquire()
            try:
                if(DBManagerRoom.__instant==None):
                    Utils.logDebug("new DBManagerRoom singleton instance.")
                    DBManagerRoom.__instant = object.__new__(self)
            finally:
                DBManagerRoom.__lock.release()
        return DBManagerRoom.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_ROOM
        self.tableversion = 1
        self.createRoomTable()

    def createRoomTable(self):
        Utils.logDebug("->createRoomTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_ROOM_ID + "` varchar(10) UNIQUE NOT NULL,"
        create_table_sql += " `" + KEY_ROOM_DETAIL + "` TEXT"
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
    
    # detailJsonStr是设备详情所有属性的Json格式化串
    def saveRoomProperty(self, detailObj):
        Utils.logDebug("->saveRoomProperty %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveRoomProperty() rx invalid inputs %s'%(detailObj))
            return None
        try:
            roomId = detailObj.get(KEY_ROOM_ID, None)
            if roomId is None:
                # return None
                # 如果是新增，找到最大的id，将新的id设为最大id+1
                id_list = self.getAllRoomIds()
                # Utils.logInfo("===>id_list: %s" % id_list)
                if id_list is not None and len(id_list) > 0:
                    roomId = id_list[-1] + 1
                else:
                    roomId = 1
                # 新计算方式：
                # maxIdInDB = self.getMaxRoomId()
                # if maxIdInDB:
                #     roomId = int(maxIdInDB) + 1
                # else:
                #     roomId = 1
                detailObj["roomId"] = str(roomId)

            newtimestamp = None
            if detailObj.has_key("timestamp"):
                newtimestamp = detailObj.get("timestamp")
            roomAllDetailJsonStr = None
            success = True
            adding = False
            item = self.getRoomByRoomId(roomId)
            if item is None:
                detailObj["timestamp"] = int(time.time())
                roomAllDetailJsonStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?)"
                data = [(None, self.tableversion, roomId, roomAllDetailJsonStr)]
                conn = DBUtils.get_conn()
                success = DBUtils.save(conn, save_sql, data)
                adding = True
            else:
                # oldtimestamp = item.get("timestamp", None)
                # if oldtimestamp is not None and newtimestamp != oldtimestamp:
                #     return item
                detailObj["timestamp"] = int(time.time())
                
                update_sql = 'UPDATE ' + self.tablename + ' SET ' 
                update_sql += ' ' + KEY_ROOM_DETAIL + ' = ? ' 
                update_sql += ' WHERE ' + KEY_ROOM_ID + ' = ? '
                
                roomAllDetailJsonStr = json.dumps(detailObj)
                data = [(roomAllDetailJsonStr, roomId)]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)

                # 判断房间名是否更改，更改后同步更新设备信息中的房间名等  20170703 chenjc
                # oldName = item.get("name")
                # newName = detailObj.get("name")
                # if oldName != newName:
                #     dev_list = DBManagerDeviceProp().getDevicesByRoomIdList([roomId])
                #     for dev in dev_list:
                #         dev["roomname"] = newName
                #     DBManagerDeviceProp().saveDeviceBatch(dev_list, devOpt=True)

                devices = DBManagerDeviceProp().getDevicePropertyBy(None, None, "all")
                new_name = detailObj.get("name")
                if devices is not None and len(devices) > 0:
                    for device in devices:
                        Utils.logError('--------device====== %s' % str(device))
                        if device.get("roomId") == roomId:
                            device["roomname"] = new_name
                        if device.get("linkOnlyOneSwitch"):
                            if device.get("linkOnlyOneSwitch").get("deviceProp"):
                                if device.get("linkOnlyOneSwitch").get("deviceProp").get("roomId") == roomId:
                                    device.get("linkOnlyOneSwitch").get("deviceProp")["roomname"] = new_name
                        if device.get("linkLightSensor"):
                            if device.get("linkLightSensor").get("deviceProp"):
                                if device.get("linkLightSensor").get("deviceProp").get("roomId") == roomId:
                                    device.get("linkLightSensor").get("deviceProp")["roomname"] = new_name
                        # DBManagerDeviceProp().saveDeviceProperty(device)
                    DBManagerDeviceProp().saveDeviceBatch(devices, devOpt=True)

            if success is True:
                # return detailObj
                room = self.getRoomByRoomId(roomId)
                if adding:
                    # 默认生成4个房间模式
                    self._save_roommode(roomId)

                # room["roomId"] = str(roomId)
                # Utils.logInfo("===>saveRoomProp: %s" % room)
                # print("===>saveRoomProp: %s" % room)
                return room
        except:
            Utils.logException('saveRoomProperty()异常 ')
        return None
            
    # def _getByCondition(self, where, data):
    #     conn = DBUtils.get_conn()
    #     sql = "select * from " + self.tablename + " " + where
    #     return DBUtils.fetchByCondition(conn, sql, data)

    # 返回满足条件的所有设备的json格式串 组成的数组
    def getByKey(self, key, data):
        deviceDict = {}
        if(data is None or data == "" or key is None):
            Utils.logError('DBManagerRoom: getByKey has invalid where condition')
            return deviceDict
        try:
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename + " where " + key + " = " + str(data) + ""
            devarr = DBUtils.fetchall(conn, sql)
            #devarr应该是[(id, deviId, hostId, type, room, area, detail),(...)]数组格式
            if(devarr is not None):
                for dev in devarr:
                    deviceDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
        except:
            Utils.logException('getByKey()异常 ')
            deviceDict.clear()
        return deviceDict.values()
        
    def deleteByKey(self, key, data):
        if(data is None or data == "" or key is None):
            Utils.logError('deleteByKey has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn()
            sql = "DELETE FROM " + self.tablename + " WHERE " + key + " = " + str(data) + ""
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByKey()异常 ')
            return False

    def getAllRooms(self):
        Utils.logDebug("->getAllRooms()")
        deviceDict = {}
        try:
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename
            devarr = DBUtils.fetchall(conn, sql)
            if(devarr is not None):
                for dev in devarr:
                    deviceDict[dev[0]] = json.loads(dev[-1])       
                    #detail总是应该放在最后的字段
        except:
            Utils.logException('getAllRooms()异常 ')
            deviceDict.clear()
        if deviceDict == None or len(deviceDict) == 0:
            return None
        return deviceDict.values()

    # 获取room表中的所有房间信息，返回信息列表，信息列表格式：
    # [{"type": type_name, "roomId": room_id, "name": name}, ...]
    def getInfoOfAllRooms(self):
        Utils.logDebug("->getInfoOfAllRooms()")
        info_list = []
        room_detail = self.getAllRooms()
        if room_detail != None and len(room_detail) > 0:
            for detail in room_detail:
                info_dict = {"type": detail.get("type"), "roomId": detail.get("roomId"), "name": detail.get("name")}
                info_list.append(info_dict)
        return info_list

    def getAllRoomIds(self):
        Utils.logDebug("->getAllRooms()")
        id_list = list()
        try:
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename
            devarr = DBUtils.fetchall(conn, sql)
            if devarr is not None:
                for dev in devarr:
                    id_list.append(dev[0])
            id_list.sort()
        except:
            Utils.logException('getAllRooms()异常 ')
        if id_list is None or len(id_list) == 0:
            return None
        return id_list

    def getMaxRoomId(self):
        Utils.logDebug("->getMaxRoomId()")
        try:
            conn = DBUtils.get_conn()
            sql = "select max(id) from " + self.tablename
            maxIdList = DBUtils.fetchall(conn, sql)
            maxId = None
            if maxIdList:
                maxId = maxIdList[0][0]
        except:
            Utils.logException('getMaxRoomId()异常')
            maxId = None
        return maxId

    # 查询房间ID和房间type的dict，返回dict类型，roomId为key，type为value
    # 模式触发时使用
    def getRoomTypeIdDict(self):
        Utils.logDebug("-> getRoomTypeIdDict <-a")
        roomdict = dict()
        try:
            roomlist = self.getInfoOfAllRooms()
            for room in roomlist:
                roomdict[room.get("roomId")] = room.get("type")
            return roomdict
        except:
            Utils.logError("getRoomTypeIdDict()异常")
            return None

    # 根据房间ID生成默认房间模式
    def _generate_roommode(self, roomId, serialNo):
        roommode = dict()
        roommode['devicelist'] = []
        roommode['timestamp'] = int(time.time())
        # roommode['hasActiveTask'] = '0'
        roommode['roomId'] = roomId
        roommode['serialNo'] = str(serialNo)
        if int(serialNo) == 0:
            name = '晨起_' + str(roomId)
            tag = '晨起'
        elif int(serialNo) == 1:
            name = '阅读_' + str(roomId)
            tag = '阅读'
        elif int(serialNo) == 2:
            name = '娱乐_' + str(roomId)
            tag = '娱乐'
        else:
            name = '睡眠_' + str(roomId)
            tag = '睡眠'

        roommode['name'] = name
        roommode['tag'] = tag
        return json.dumps(roommode)  # 直接返回json字符串

    # 将默认生成的房间模式写入数控
    def _save_roommode(self, roomId):
        livingup = self._generate_roommode(roomId, 0)
        reading = self._generate_roommode(roomId, 1)
        playing = self._generate_roommode(roomId, 2)
        sleeping = self._generate_roommode(roomId, 3)

        data = []
        data.append((1, roomId, '晨起_' + str(roomId), livingup))
        data.append((1, roomId, '阅读_' + str(roomId), reading))
        data.append((1, roomId, '娱乐_' + str(roomId), playing))
        data.append((1, roomId, '睡眠_' + str(roomId), sleeping))

        insertsql = 'INSERT INTO tbl_link_action (version,roomId,name,detail) VALUES(?,?,?,?)'
        conn = DBUtils.get_conn()
        DBUtils.executemany(conn, insertsql, data)
        
    # 返回json格式串
    def getRoomByRoomId(self, name):
        Utils.logDebug("->getRoomByRoomId %s"%(name))
        result = self.getByKey(KEY_ROOM_ID, name)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]    #返回json

    def deleteRoomByRoomId(self, roomId):
        Utils.logDebug("->deleteRoomByRoomId %s"%(roomId))
        return self.deleteByKey(KEY_ROOM_ID, roomId)

if __name__ == '__main__':
    d1 = DBManagerRoom()
    d2 = DBManagerRoom()
    print "getRoomByRoomId:", d1.getRoomByRoomId("devIdvalue")
    
    # devDict={"deviceId":"devIdvalue","hostId":"hostIdvalue","roomId":"1","areaId":"areavalue1","type":"typevalue"}
    devDict={"roomId":"1","name":"客厅","picurl":"1.png", "areas":[{"1":"a1"}]}
    d2.saveRoomProperty(devDict)

    devDict2={"roomId":"2","name":"厨房","picurl":"bg.png","areas":[{"2":"a2"}]}
    d2.saveRoomProperty(devDict2)
    
    print "============================="
    r2= d2.getRoomByRoomId("2")
    if(r2.get("picurl") == u'bg.png'):
        print "========getRoomByRoomId:SUCCESS============"
    else:
        print "**********************getRoomByRoomId:FAILED"

    all = d1.getAllRooms()
    if len(all) == 2:
        print "========getAllRooms:SUCCESS============"
    else:
        print "**********************getAllRooms:FAILED"

    d1.deleteRoomByRoomId("2")
    if d2.getRoomByRoomId("2") == None:
        print "==========deleteRoomByRoomId SUCCESS============"
    else:
        print "**********************deleteRoomByRoomId:FAILED"
    
    