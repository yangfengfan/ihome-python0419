#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time

#设备关联表数据库名
TABLE_NAME_LINK = "tbl_devices_link"


class DBManagerLinks(object):
    __instant = None;
    __lock = threading.Lock();
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerLinks.__instant==None):
            DBManagerLinks.__lock.acquire()
            try:
                if(DBManagerLinks.__instant==None):
                    Utils.logDebug("new DBManagerLinks singleton instance.")
                    DBManagerLinks.__instant = object.__new__(self);
            finally:
                DBManagerLinks.__lock.release()
        return DBManagerLinks.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_LINK
        self.tableversion = 1
        self.createLinkTable()

    def createLinkTable(self):
        Utils.logDebug("->createLinkTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " 'id' INTEGER primary key autoincrement,"
        create_table_sql += " 'version' INTEGER NOT NULL,"
        create_table_sql += " 'detail' TEXT"
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
    def saveDeviceLinks(self, detailObj):
        Utils.logDebug("->saveDeviceLinks %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveDeviceLinks() rx invalid inputs %s'%(detailObj))
            return (False, None)
        try:
            detailObj["timestamp"] = int(time.time())
            roomAllDetailJsonStr = json.dumps(detailObj)
            save_sql = "INSERT INTO " + self.tablename + " values (?,?,?)"
            data = [(None, self.tableversion, roomAllDetailJsonStr)]
            conn = DBUtils.get_conn()
            success = DBUtils.save(conn, save_sql, data)

            if success == True:
                return (True, detailObj)
        except:
            Utils.logException('saveDeviceLinks()异常 ')
        return (False, None)

    def updateDeviceLinks(self, dbId, detailObj):
        Utils.logDebug("->updateDeviceLinks %s"%(detailObj))
        try:
            newtimestamp = None
            if detailObj.has_key("timestamp"):
                newtimestamp = detailObj.get("timestamp")
            roomAllDetailJsonStr = None
            success = False
            item = self.getDeviceLinksByDbId(dbId)
            if(item is None):
                success = False
            else:
                oldtimestamp = item.get("timestamp", None)
                if oldtimestamp != None and newtimestamp != oldtimestamp:
                    return (False, item)
                detailObj["timestamp"] = int(time.time())

                update_sql = 'UPDATE ' + self.tablename + ' SET '
                update_sql += ' detail = ? '
                update_sql += ' WHERE (id = ?) '

                roomAllDetailJsonStr = json.dumps(detailObj)
                data = [(roomAllDetailJsonStr, str(dbId))]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)
            if success == True:
                return (True, detailObj)
        except:
            Utils.logException('updateDeviceLinks()异常 ')
        return (False, None)

    # def _getByCondition(self, where, data):
    #     conn = DBUtils.get_conn()
    #     sql = "select * from " + self.tablename + " " + where
    #     return DBUtils.fetchByCondition(conn, sql, data)

    #返回满足条件的所有设备的json格式串 组成的数组
    # def getByKey(self, key, data):
    #     deviceDict = {}
    #     if(data is None or data == "" or key is None):
    #         Utils.logError('getByKey has invalid where condition')
    #         return deviceDict
    #     try:
    #         conn = DBUtils.get_conn()
    #         sql = "select * from " + self.tablename + " where " + key + " = "+ str(data) + ""
    #         devarr = DBUtils.fetchall(conn, sql)
    #         #devarr应该是[(id, deviId, hostId, type, room, area, detail),(...)]数组格式
    #         if(devarr is not None):
    #             for dev in devarr:
    #                 deviceDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
    #     except:
    #         Utils.logError('getByKey()异常 ')
    #         deviceDict.clear()
    #     return deviceDict.values()

    def deleteByAddrChannel(self, addr, channel):
        if(addr is None or channel is None):
            Utils.logError('deleteByAddrChannel has invalid where condition')
            return False

        linksdict = self.getDeviceLinks(addr, channel)
        if linksdict == None or len(linksdict) == 0:
            return True
        for dbId in linksdict.keys():
            links = linksdict.get(dbId)
            controls = links.get('controls', None)
            if controls == None:
                return True

            ids = []
            for index in range(0, len(controls)):
                ##{'addr':'mac1','type':'Light2','channel':1}
                ctrl = controls[index]
                if ctrl.get('addr', None) == addr and ctrl.get('channel', None) == channel:
                    # found
                    ids.append(index)
            for id in ids:
                del controls[id]

            if len(controls) < 2:
                ##关联设备至少要两个设备
                return self.deleteByDbId(dbId)
            else:
                links['controls'] = controls
                (success, ret) = self.updateDeviceLinks(dbId, links)
                return success

    def deleteByAddr(self, addr):
        if(addr is None):
            Utils.logError('deleteByAddr has invalid input')
            return False

        linksdict = self.getAllDeviceLinks()
        for key in linksdict.keys():
            ## 从所有配置中，找到跟这个设备相关的关联配置
            conf = linksdict.get(key, None)
            if conf == None:
                continue

            ##:{'controls':[{'addr':'mac1','type':'Light2','channel':1},{'addr':'mac2','type':'Light2','channel':0}，...]}
            controls = conf.get('controls', None)
            if controls == None:
                self.deleteByDbId(key)
                continue

            ids=[]
            for index in range(0, len(controls)):
                ##{'addr':'mac1','type':'Light2','channel':1}
                ctrl = controls[index]
                if ctrl.get('addr', None) == addr:
                    # found
                    ids.append(index)
            if len(ids) > 0:
                for id in ids:
                    del controls[id]
                if len(controls) < 2:
                    ##关联设备至少要两个设备
                    self.deleteByDbId(key)
                else:
                    conf['controls'] = controls
                    self.updateDeviceLinks(key, conf)
        return True

    def deleteByDbId(self, dbId):
        try:
            conn = DBUtils.get_conn()
            sql = "DELETE FROM " + self.tablename + " WHERE id = " + str(dbId)
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByDbId()异常 ')
            return False

    #返回：{dbId:{'controls':[{...}], 'timestamp':1223234}}
    def getAllDeviceLinks(self):
        Utils.logDebug("->getAllDeviceLinks()")
        linksdict = {}
        try:
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename
            devarr = DBUtils.fetchall(conn, sql)
            if(devarr is not None):
                for dev in devarr:
                    tmp = json.loads(dev[-1])
                    tmp['dbId'] = dev[0]
                    linksdict[dev[0]] = tmp
                    #detail总是应该放在最后的字段
        except:
            Utils.logException('getAllDeviceLinks()异常 ')
            linksdict.clear()
        return linksdict

    #返回：[{'dbId':11,'controls':[{'addr':'dst-mac1','type':'Light2','channel':1},{'addr':'dst-mac2','type':'Light2',...}]}]
    #根据addr获取设备关联信息 -- added by chenjianchao
    def getDeviceLinksByAddr(self, addr, srcAddr=None):
        Utils.logDebug("->getDeviceLinksByAddr()根据设备地址获取相关配置")
        linksList = []
        try:
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename + " where detail like '%" + addr + "%'"
            links = DBUtils.fetchall(conn, sql)
            if links is not None:
                for link in links:
                    #temp数据形式如下：
                    #{"timestamp": 1449812307, "controls": [{"type": "Light1", "addr": "4DEA5A02004B12000000", "channel": "0"}]}
                    temp = json.loads(link[-1])
                    #del temp["timestamp"] # 去掉timestamp键值对
                    temp['dbId'] = link[0] # 拼凑数据格式，拼成与linkDevices()时一样的格式
                    controlsTemp = temp.get("controls", [])
                    if controlsTemp and srcAddr is not None:
                        srcAddrInDb = controlsTemp[0].get("addr")
                        if srcAddrInDb == srcAddr:  # 防止误解绑，源设备地址与当前绑定的源设备地址相同时不要去解绑掉
                            continue
                    linksList.append(temp)
        except:
            Utils.logException('getDeviceLinksByAddr()异常')
            return []
        return linksList


    def getDeviceLinksByDbId(self, dbId):
        Utils.logDebug("->getDeviceLinksByDbId")

        if dbId == None:
            return None

        conn = DBUtils.get_conn()
        sql = "select * from " + self.tablename + " where id = " + str(dbId)
        devarr = DBUtils.fetchall(conn, sql)
        if(devarr is not None):
            for dev in devarr:
                return json.loads(dev[-1])
        return None

    #返回json格式串
    # 返回形式： {"1": {"timestamp": 1499217115, "controls": [{"type": "Light3", "addr": "C9030F11004B12000000", "channel": "0"}, {"type": "Light1", "addr": "57F90E11004B12000000", "channel": "0"}], "dbId": 31}}
    def getDeviceLinks(self, addr, channel):
        Utils.logDebug("->getDeviceLinks %s %s"%(addr, channel))
        # # result = self.getByKey('addr', name)
        # conn = DBUtils.get_conn()
        # sql = "select * from " + self.tablename + " where (addr = '"+ addr + "' and channel = " + str(channel) + ")"
        # result = DBUtils.fetchall(conn, sql)
        # if(result == None or len(result) == 0):
        #     return None
        # else:
        #     return json.loads(result[0])    #返回json
        ret = {}
        # linksdict格式: {"1": {"timestamp": 1499217115, "controls": [{"type": "Light3", "addr": "C9030F11004B12000000", "channel": "0"}, {"type": "Light1", "addr": "57F90E11004B12000000", "channel": "0"}], "dbId": 31}}
        # 其中 key "1" 是数据库表 tbl_devices_link 中该条记录的ID，对应的 value是该条记录的 detail 列。返回值形式于此一致
        linksdict = self.getAllDeviceLinks()
        for key in linksdict.keys():
            conf = linksdict.get(key, None)
            if conf == None:
                continue
            ##:{'controls':[{'addr':'mac1','type':'Light2','channel':1},{'addr':'mac2','type':'Light2','channel':0}，...]}
            controls = conf.get('controls', None)
            if controls == None:
                continue
            for ctrl in controls:
                ##{'addr':'mac1','type':'Light2','channel':1}
                if ctrl.get('addr', None) == addr and ctrl.get('channel', None) == channel:
                    # found
                    ret[key] = conf
        return ret

if __name__ == '__main__':
    d1 = DBManagerLinks()
