#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time
from DBManagerHostId import DBManagerHostId

#设备表数据库名
TABLE_NAME_LINK_ACTION = "tbl_link_action"

KEY_ID = "id"
KEY_VERSION = "version"
KEY_DEVICE_ADDR = "addr"      #设备Id/Mac
KEY_ACTION_NAME = "name"      #联动计划名称
KEY_ACTION_ROOM = "roomId"      #房间模式计划
KEY_ACTION_DETAIL = "detail"    #详细json


class DBManagerAction(object):
    __instant = None
    __lock = threading.Lock()
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerAction.__instant==None):
            DBManagerAction.__lock.acquire();
            try:
                if(DBManagerAction.__instant==None):
                    Utils.logDebug("new DBManagerAction singleton instance.")
                    DBManagerAction.__instant = object.__new__(self);
            finally:
                DBManagerAction.__lock.release()
        return DBManagerAction.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_LINK_ACTION
        self.tableversion = 1
        self.createActionTable()
        self.checkGlobalMode('回家模式配置')
        self.checkGlobalMode('离家模式配置')
        self.checkGlobalMode('会客模式配置')
        # self.checkGlobalMode('Party模式配置')
        self.checkGlobalMode('就餐模式配置')
        self.checkGlobalMode('撤防模式配置')
        self.checkGlobalMode('布防模式配置')

    def checkGlobalMode(self, name):
        if self.getActionByName(name) == None:
            self._initGlobalLinkAction(name)

    def createActionTable(self):
        Utils.logDebug("->createActionTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_DEVICE_ADDR + "` varchar(50) UNIQUE,"
        create_table_sql += " `" + KEY_ACTION_ROOM + "` varchar(10) ,"
        create_table_sql += " `" + KEY_ACTION_NAME + "` varchar(50) ,"
        create_table_sql += " `" + KEY_ACTION_DETAIL + "` TEXT"
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

    def _initGlobalLinkAction(self, name):
        detailObj = {}
        detailObj["name"] = name
        detailObj["timestamp"] = int(time.time())
        actionAllDetailJsonStr = json.dumps(detailObj)
        save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?)"
        data = [(None, self.tableversion, None, 'global', name, actionAllDetailJsonStr)]
        conn = DBUtils.get_conn()
        DBUtils.save(conn, save_sql, data)

    # detailJsonStr是设备详情所有属性的Json格式化串
    # 存储告警联动计划
    def saveLinkAction(self, detailObj):
        Utils.logDebug("->saveLinkAction %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveLinkAction() rx invalid inputs %s'%(detailObj))
            return None
        try:
            deviceAddr = detailObj.get(KEY_DEVICE_ADDR, None)
            
            newtimestamp = None
            if detailObj.has_key("timestamp"):
                newtimestamp = detailObj.get("timestamp")

            actionItem = None
            modeId = detailObj.get('modeId', None)
            if modeId != None:
                actionItem = self.getActionByModeId(modeId)
            else:
                actionItem = self.getActionByDevId(deviceAddr)

            actionAllDetailJsonStr = None
            success = True
            if(actionItem is None):
                detailObj["timestamp"] = int(time.time())
                actionAllDetailJsonStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?)"
                data = [(None, self.tableversion, deviceAddr, None, None, actionAllDetailJsonStr)]
                conn = DBUtils.get_conn()
                DBUtils.save(conn, save_sql, data)

                ## 找到Id，并更新到detail里
                actionItem = self.getActionByDevId(deviceAddr)
                if actionItem == None:
                    return None
            else:
                oldtimestamp = actionItem.get("timestamp", None)
                if oldtimestamp != None and newtimestamp != oldtimestamp:
                    return actionItem
                detailObj["timestamp"] = int(time.time())

            detailObj['modeId'] = actionItem.get('modeId', None)
            actionAllDetailJsonStr = json.dumps(detailObj)
            update_sql  = "UPDATE " + self.tablename + " SET "
            update_sql += " " + KEY_ACTION_DETAIL + " = ? "
            update_sql += " WHERE "+ KEY_DEVICE_ADDR + " = ? "

            data = [(actionAllDetailJsonStr, deviceAddr)]
            conn = DBUtils.get_conn()
            success = DBUtils.update(conn, update_sql, data)
            if success == True:
                return detailObj
        except:
            Utils.logException('saveLinkAction()异常')
        return None
        
    # 存储模式联动计划
    def saveModeAction(self, detailObj):
        Utils.logDebug("->saveModeAction %s"%(detailObj))
        if detailObj is None:
            Utils.logError('saveModeAction() rx invalid inputs %s'%(detailObj))
            return None
        try:
            actionName = detailObj.get(KEY_ACTION_NAME, None)
            if actionName is None:
                return None
            roomId = detailObj.get(KEY_ACTION_ROOM, None)
            if roomId is None:
                roomId = "global"
                detailObj['roomId'] = roomId

            newtimestamp = None
            if detailObj.has_key("timestamp"):
                newtimestamp = detailObj.get("timestamp")

            actionItem = None
            modeId = detailObj.get('modeId', None)
            if modeId is not None:
                actionItem = self.getActionByModeId(modeId)
            else:
                actionItem = self.getActionByName(actionName, roomId)

            actionAllDetailJsonStr = None
            success = True
            if actionItem is None:
                detailObj["timestamp"] = int(time.time())
                actionAllDetailJsonStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?)"
                data = [(None, self.tableversion, None, roomId, actionName, actionAllDetailJsonStr)]
                conn = DBUtils.get_conn()
                DBUtils.save(conn, save_sql, data)

                # 找到Id，并更新到detail里
                actionItem = self.getActionByName(actionName, roomId)
                if actionItem is None:
                    return None
            else:
                oldtimestamp = actionItem.get("timestamp", None)
                if oldtimestamp is not None and newtimestamp != oldtimestamp:
                    Utils.logInfo('timestamp conflict, save mode failed.')
                    return actionItem
                detailObj["timestamp"] = int(time.time())

            detailObj['modeId'] = actionItem.get('modeId', None)
            actionAllDetailJsonStr = json.dumps(detailObj)
            update_sql  = "UPDATE " + self.tablename + " SET "
            update_sql += " " + KEY_ACTION_DETAIL + " = ? "
            update_sql += " WHERE "+ KEY_ID + " = ? "

            data = [(actionAllDetailJsonStr, modeId)]
            conn = DBUtils.get_conn()
            success = DBUtils.update(conn, update_sql, data)
            if success is True:
                return detailObj
        except:
            Utils.logException('saveModeAction()异常')
        return None

    def createGlobalMode(self, detailObj):
        '''
        新增全局模式
        :param detailObj: 全局模式信息
        :return:
        '''
        Utils.logDebug("->createGlobalMode %s" % (detailObj))
        if (detailObj is None):
            Utils.logError('createGlobalMode() rx invalid inputs %s' % (detailObj))
            return None

        try:
            actionName = detailObj.get(KEY_ACTION_NAME, None)
            if actionName == None:
                return None

            nowtime = int(time.time())
            detailObj["timestamp"] = nowtime
            actionAllDetailJsonStr = json.dumps(detailObj)
            save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?)"
            data = [(None, self.tableversion, None, 'global', actionName, actionAllDetailJsonStr)]
            conn = DBUtils.get_conn()
            DBUtils.save(conn, save_sql, data)

            mode = self._getGlobalModeByTimestamp(detailObj.get('name'), nowtime)
            if mode:
                modeId = mode.get('modeId')
                detailObj['modeId'] = modeId
                actionAllDetailJsonStr = json.dumps(detailObj)
                update_sql = "UPDATE " + self.tablename + " SET "
                update_sql += " " + KEY_ACTION_DETAIL + " = ? "
                update_sql += " WHERE " + KEY_ID + " = ? "

                data = [(actionAllDetailJsonStr, modeId)]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)
                if success is True:
                    return detailObj

        except:
            Utils.logException('createGlobalMode()异常')
        return None

    def _getGlobalModeByTimestamp(self, modename, timestamp):
        '''
        根据模式名字、时间戳查询新增的全局模式
        :param modename:
        :param timestamp:
        :return:
        '''
        sql = "SELECT * FROM " + self.tablename + " WHERE id > 6 AND roomId = 'global'"
        try:
            conn = DBUtils.get_conn()
            global_modes = DBUtils.fetchall(conn, sql)
            for mode_row in global_modes:
                mode = json.loads(mode_row[-1])
                if mode.get('timestamp') == timestamp and mode.get('name') == modename:
                    mode_id = mode_row[0]
                    mode['modeId'] = mode_id
                    return mode

        except Exception as e:
            Utils.logException('_getGlobalModeByTimestamp()异常: %s' % e.message)
            return None
    
    # def getByCondition(self, where, data):
    #     conn = DBUtils.get_conn()
    #     sql = "select * from " + self.tablename + " " + where
    #     return DBUtils.fetchByCondition(conn, sql, data)

    # 返回满足条件的所有设备的json格式串 组成的数组
    def getByCondition(self, conditionDict):
        alarmDict = {}
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('getByCondition has invalid where condition')
            return alarmDict.values()
        # try:
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
                detail = json.loads(dev[-1])        #detail总是应该放在最后的字段
                detail['modeId'] = dev[0]
                alarmDict[dev[0]] = detail
        # except Exception as e:
        #     Utils.logError('getByCondition()异常 %s'%(e))
        #     alarmDict.clear()
        return alarmDict.values()
        
    def deleteByKey(self, key, data):
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

    def getActionByModeId(self, modeId):
        Utils.logDebug("->getActionByModeId %s"%(str(modeId)))
        conds = {}
        conds[KEY_ID] = modeId
        result = self.getByCondition(conds)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]    #返回json
        
    #返回json格式串
    def getActionByDevId(self, deviceAddr):
        Utils.logDebug("->getActionByDevId %s"%(deviceAddr))
        conds = {}
        conds[KEY_DEVICE_ADDR] = "'" + deviceAddr + "'"
        result = self.getByCondition(conds)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]    #返回json

    def getActionByName(self, name, room = None):
        Utils.logDebug("->getActionByName %s,%s"%(name, room))
        conds = {}
        if room is None:
            room = "global"
        # if isinstance(name, unicode) == True:
        #     name = name.encode('utf-8')
        # conds[KEY_ACTION_NAME] = "'" + name + "'"
        conds[KEY_ACTION_ROOM] = "'" + room + "'"
        results = self.getByCondition(conds)
        if(results == None or len(results) == 0):
            return None

        for result in results:    #返回json
            nameV = result.get('name', None)
            if nameV == name:
                return result
        return None

    def getByName(self, mode_name):
        try:
            conn = DBUtils.get_conn()
            sql = "SELECT * FROM " + self.tablename + " WHERE " + KEY_ACTION_NAME + " = '" + mode_name + "'"
            result_list = DBUtils.fetchall(conn, sql)
            if result_list:
                return json.loads(result_list[0][-1])
            return None
        except:
            Utils.logException('getByName()异常')
            return None

    # 查找指定房间配置的所有模式，或查找所有全局模式配置
    def getActionByRoom(self, roomId):
        conds = {}
        if roomId is None:
            roomId = "global"
        Utils.logDebug("->getActionByRoom %s"%(roomId))
        conds[KEY_ACTION_ROOM] = "'" + roomId + "'"
        return self.getByCondition(conds)

    # 查找所有联动计划（传感器相关）
    def getAllLinkAction(self):
        Utils.logDebug("->getAllLinkAction")
        linkDict={}
        # try:
        conn = DBUtils.get_conn()
        #组装sql语句
        sql = "select * from " + self.tablename + " where( " + KEY_DEVICE_ADDR + " not null ) "
        modearr = DBUtils.fetchall(conn, sql)
        if(modearr is not None):
            for dev in modearr:
                detail = json.loads(dev[-1])        # detail总是应该放在最后的字段
                detail['modeId'] = dev[0]
                linkDict[dev[2]] = detail           # detail总是应该放在最后的字段

        # except Exception as e:
        #     Utils.logError('getAllLinkAction()异常 %s'%(e))
        #     modeDict.clear()
        return linkDict

    # 查询带有给定设备地址的
    def getLinkActionByDevInList(self, devaddr):
        linkActionList = []
        sql = "select * from " + self.tablename + " where detail like '%" + devaddr + "%'"
        conn = DBUtils.get_conn()
        modeArr = DBUtils.fetchall(conn, sql)
        if modeArr is not None:
            for mode in modeArr:
                detail = json.loads(mode[-1])
                detail['modeId'] = mode[0]
                linkActionList.append(detail)
        return linkActionList

    # 更新联动配置中的设备列表，用于删除设备之后使用
    # [{"modeId": 1, "devicelist":[{"devicename": "\u5355\u8054\u706f", "areaid": "3",
    # "deviceAddr": "F8668A0A004B12000000", "roomname": "\u4e3b\u5367", "devicetype": "Light1",
    # "deviceid": "F8668A0A004B12000000", "params": {"state": "1"}, "roomId": "2", "areaname": "\u65b0\u533a\u57df"},
    # ...,{...}]
    def updateDeviceList(self, devaddr):
        update_param = []
        linkActionList = self.getLinkActionByDevInList(devaddr)
        Utils.logDebug("linkActionList: %s\n" % str(linkActionList))
        for modeDetail in linkActionList:
            if modeDetail.has_key("alarmRecover") or modeDetail.has_key("alarmAct"):
                alarmRevoverInfo = modeDetail.get("alarmRecover")
                if alarmRevoverInfo:
                    modeInfo = alarmRevoverInfo.get("mode")
                    if modeInfo:
                        alarmRevoverDevList = modeInfo.get("devicelist")
                        if alarmRevoverDevList:
                            device_list = [dev for dev in alarmRevoverDevList if dev.get('deviceAddr') != devaddr]
                            modeInfo["devicelist"] = device_list
                            if modeInfo.has_key("deviceList"):
                                # modeInfo["deviceList"] = device_list  # 2.3.4版本开始清理冗余的deviceList，只保留devicelist
                                del modeInfo["deviceList"]
                            if modeInfo.has_key("timestamp"):
                                del modeInfo["timestamp"]
                    alarmRevoverInfo["mode"] = modeInfo

                alarmActInfo = modeDetail.get("alarmAct")
                if alarmActInfo:
                    actList = alarmActInfo.get("actList")
                    if actList:
                        device_list = [dev for dev in actList if dev.get('deviceAddr') != devaddr]
                        alarmActInfo["actList"] = device_list
                modeDetail["alarmRecover"] = alarmRevoverInfo
                modeDetail["alarmAct"] = alarmActInfo

            else:
                devicelist = modeDetail.get("devicelist", None)
                if devicelist:
                    if isinstance(devicelist, list):
                        device_list = [dev for dev in devicelist if dev.get("deviceAddr") != devaddr]
                        modeDetail['devicelist'] = device_list
                        if modeDetail.has_key("deviceList"):
                            # modeDetail['deviceList'] = device_list  # 2.3.4版本开始清理冗余的deviceList，只保留devicelist
                            del modeDetail['deviceList']

                    elif isinstance(devicelist, dict):
                        curr_host = DBManagerHostId().getHostId()
                        devlist = devicelist.get(curr_host, [])
                        dlist = [dev for dev in devlist if dev.get("deviceAddr") != devaddr]
                        devicelist[curr_host] = dlist
                        modeDetail['devicelist'] = devicelist
                        if modeDetail.has_key("deviceList"):
                            # modeDetail['deviceList'] = devicelist  # 2.3.4版本开始清理冗余的deviceList，只保留devicelist
                            del modeDetail['deviceList']

            update_param.append((json.dumps(modeDetail), str(modeDetail.get("modeId"))))

        update_sql = "UPDATE " + self.tablename + " SET detail=? WHERE id=?"
        conn = DBUtils.get_conn()
        DBUtils.executemany(conn, update_sql, update_param)

    def deleteActionByDevId(self, devAddr):
        Utils.logDebug("->deleteActionByDevId %s"%(devAddr))
        return self.deleteByKey(KEY_DEVICE_ADDR, devAddr)

    def deleteActionsByRoom(self, roomId):
        Utils.logDebug("->deleteActionsByRoom %s"%(roomId))
        return self.deleteByKey(KEY_ACTION_ROOM, roomId)

    def deleteActionsByName(self, roomId, name):
        Utils.logDebug("->deleteActionsByName %s,%s"%(roomId, name))
        conn = DBUtils.get_conn()
        sql  = "DELETE FROM " + self.tablename + " WHERE " + KEY_ACTION_ROOM + " = '" + roomId + "'"
        sql += " and " + KEY_ACTION_NAME + " = '" + name + "' "
        DBUtils.deleteone(conn, sql)

    def deleteActionById(self, modeId):
        '''
        删除模式ID大于6的全局模式
        :param modeId: 全局模式ID
        :return: True if success
        '''
        Utils.logDebug("->deleteActionById %s" % modeId)
        sql = "DELETE FROM " + self.tablename + " WHERE " + KEY_ID + " = " + str(modeId)
        try:
            conn = DBUtils.get_conn()
            return DBUtils.deleteone(conn, sql)
        except Exception as e:
            Utils.logError("deleteActionById() error: %s" % e.message)
            return None

    # 修改模式名称
    # 实际不改名称，在detail中添加一个tag
    def modifyModeName(self, modeId, newName):

        try:
            roomMode = self.getActionByModeId(modeId)
            roomMode["tag"] = newName

            update_sql = "UPDATE " + self.tablename + " SET "
            update_sql += " " + KEY_ACTION_DETAIL + " = ? "
            update_sql += " WHERE "+ KEY_ID + " = ? "

            roomModeStr = json.dumps(roomMode)
            data = [(roomModeStr, modeId)]

            conn = DBUtils.get_conn()
            success = DBUtils.update(conn, update_sql, data)

            if success is True:
                return True
            else:
                return False
        except:
            Utils.logError("DataBase Error！")
        return None


    # 开关开门模式
    def switch_door_open_mode(self, mode_id, mode_set):

        try:
            roomMode = self.getActionByModeId(mode_id)
            roomMode["set"] = mode_set

            update_sql = "UPDATE " + self.tablename + " SET "
            update_sql += " " + KEY_ACTION_DETAIL + " = ? "
            update_sql += " WHERE " + KEY_ID + " = ? "

            room_mode_string = json.dumps(roomMode)
            data = [(room_mode_string, mode_id)]

            conn = DBUtils.get_conn()
            success = DBUtils.update(conn, update_sql, data)

            if success is True:
                return True
            else:
                return False
        except:
            Utils.logError("DataBase Error！")
        return None

    # 查询所有的全局模式
    def getGlobalModes(self):

        condition = {KEY_ACTION_ROOM: "'global'"}
        results = self.getByCondition(condition)
        return results

    def getAllModesForPannel(self):
        try:
            sql = "SELECT id, roomId, DETAIL FROM tbl_link_action WHERE roomId is not null"
            conn = DBUtils.get_conn()
            result_list = DBUtils.fetchall(conn, sql)
            globalModeList = list()
            roomModeList = list()
            roomIdSet = set()
            mode_dict = dict(globalModeList=globalModeList)  # , roomModeList=roomModeList)
            if result_list:
                for item in result_list:
                    item_dict = json.loads(item[-1])
                    item_dict["roomId"] = item[1]
                    if "modeId" not in item_dict.keys():
                        item_dict["modeId"] = item[0]
                    if item[1] == "global":
                        mode_name = item_dict.get("name")
                        if '开门模式' not in mode_name and u'开门模式' not in mode_name:
                            globalModeList.append(item_dict)
                    else:
                        roomIdSet.add(int(item_dict.get("roomId")))
                        roomModeList.append(item_dict)
                for roomId in roomIdSet:
                    one_room_mode_list = list()
                    for roomMode in roomModeList:
                        if int(roomMode.get("roomId")) == int(roomId):
                            one_room_mode_list.append(roomMode)
                    mode_dict[roomId] = one_room_mode_list
            return mode_dict
        except Exception as err:
            Utils.logError("===>getAllModesForPannel error: %s" % err)
            return None

    def getModeForRokid(self):
        mode_list = self.getGlobalModes()
        rtn_list = []
        for mode in mode_list:
            modename = mode.get('name')
            if '开门模式' in modename or u'开门模式' in modename:  # 过滤掉开门模式
                continue

            modeinfo = {}
            modeid = mode.get('modeId')
            name = mode.get('tag', None)
            if not name:
                name = mode.get('name')
                if modename.endswith('配置') or modename.endswith(u'配置'):
                    name = modename[: -2]

            if not name.endswith('模式') or not name.endswith(u'模式'):  # 拼接"模式"两个字
                name += '模式'

            modeinfo['name'] = name
            modeinfo['type'] = 'scene'
            modeinfo['deviceId'] = 'mode_%s' % str(modeid)
            modeinfo['actions'] = {'switch': ['on']}
            rtn_list.append(modeinfo)

        return rtn_list

        
if __name__ == '__main__':
    d1 = DBManagerAction()
    d2 = DBManagerAction()
    print "getActionByDevId:", d1.getActionByDevId("")
    print "getActionByName:", d1.getActionByName("roomId", None)
    
    actionDict={"name":"回家模式","test":"testV1","alarmAct":{}}
    d2.saveModeAction(actionDict)
    
    devDict2={"addr":"z-347D4501004B12001233","test":"testV2","alarmAct":{}}
    d2.saveLinkAction(devDict2)
    
    actionDict3={"alarmAct":{}}
    d2.saveModeAction(actionDict3)
    
    print "============================="
    a2 = d2.getActionByDevId("z-347D4501004B12001233")
    if a2.get("test") == "testV2":
        print "============getActionByDevId SUCCESS============"
    else:
        print "################getActionByDevId FAILED#######"
        

    a1 = d1.getActionByName("回家模式")
    if a1.get("test") == "testV1":
        print "============getActionByName SUCCESS==============="
    else:
        print "################getActionByName FAILED#######"
    
    d1.deleteActionByDevId("z-347D4501004B12001233")
    print "getActionByDevId:", d2.getActionByDevId("z-347D4501004B12001234")
