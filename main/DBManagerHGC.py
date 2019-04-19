#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json
import time

#设备关联表数据库名
TABLE_NAME_HGC = "tbl_hgc"


class DBManagerHGC(object):
    __instant = None
    __lock = threading.Lock()
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerHGC.__instant==None):
            DBManagerHGC.__lock.acquire();
            try:
                if(DBManagerHGC.__instant==None):
                    Utils.logDebug("new DBManagerHGC singleton instance.")
                    DBManagerHGC.__instant = object.__new__(self);
            finally:
                DBManagerHGC.__lock.release()
        return DBManagerHGC.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_HGC
        self.tableversion = 1
        self.createHGCTable()

    ### {'addr':'hhggcc001122','v_type':0x1,'channel':1, 'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]}
    def createHGCTable(self):
        Utils.logDebug("->createHGCTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " 'id' INTEGER primary key autoincrement,"
        create_table_sql += " 'version' INTEGER NOT NULL,"
        create_table_sql += " 'addr' varchar(10) NOT NULL,"
        create_table_sql += " 'v_type' INTEGER NOT NULL,"
        create_table_sql += " 'channel' INTEGER NOT NULL,"
        create_table_sql += " 'detail' TEXT,"
        create_table_sql += " UNIQUE (addr, v_type, channel) "
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
    
    #detailObj是HGC某个配置的详情
    ### {'addr':'hhggcc001122','v_type':0x1,'channel':1, 'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]}
    def saveHGCconfigs(self, detailObj):
        Utils.logDebug("->saveHGCconfigs %s"%(detailObj))
        if(detailObj is None):
            Utils.logError('saveHGCconfigs() rx invalid inputs %s'%(detailObj))
            return (False, None)
        try:
            addr = detailObj.get('addr', None)
            channel = detailObj.get('channel', None)
            v_type = detailObj.get('v_type', None)

            if addr == None or channel == None or v_type == None:
                return (False, None)

            newtimestamp = None
            if detailObj.has_key("timestamp"):
                newtimestamp = detailObj.get("timestamp")
            success = False
            item = self.getHGCconfig(addr, v_type, channel)
            if(item is None):
                detailObj["timestamp"] = int(time.time())
                detailStr = json.dumps(detailObj)
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?,?,?)"
                data = [(None, self.tableversion, addr, v_type, channel, detailStr)]
                conn = DBUtils.get_conn()
                success = DBUtils.save(conn, save_sql, data)
            else:
                oldtimestamp = item.get("timestamp", None)
                if oldtimestamp != None and newtimestamp != oldtimestamp:
                    return (False, item)
                detailObj["timestamp"] = int(time.time())
                
                update_sql = 'UPDATE ' + self.tablename + ' SET ' 
                update_sql += ' detail = ? '
                update_sql += ' WHERE (addr = ? and v_type = ? and channel = ?) '
                
                detailStr = json.dumps(detailObj)
                data = [(detailStr, addr, v_type, channel)]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)
            if success == True:
                return (True, detailObj)
        except:
            Utils.logException('saveHGCconfigs()异常 ')
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

    # def deleteByAddrChannel(self, addr, channel):
    #     if(addr is None or channel is None):
    #         Utils.logError('deleteByAddrChannel has invalid where condition')
    #         return False
    #     try:
    #         conn = DBUtils.get_conn()
    #         sql = "DELETE FROM " + self.tablename + " WHERE addr = '" + addr + "' and channel = '" + str(channel) + "'"
    #         DBUtils.deleteone(conn, sql)
    #         return True
    #     except:
    #         Utils.logException('deleteByAddrChannel()异常 ')
    #         return False
    #
    # def deleteByAddr(self, addr):
    #     if(addr is None):
    #         Utils.logError('deleteByAddr has invalid where condition')
    #         return False
    #     try:
    #         conn = DBUtils.get_conn()
    #         sql = "DELETE FROM " + self.tablename + " WHERE addr = '" + addr + "'"
    #         DBUtils.deleteone(conn, sql)
    #         return True
    #     except:
    #         Utils.logException('deleteByAddr()异常 ')
    #         return False
    #
    # def getAllDeviceLinks(self):
    #     Utils.logDebug("->getAllDeviceLinks()")
    #     linksdict = {}
    #     try:
    #         conn = DBUtils.get_conn()
    #         sql = "select * from " + self.tablename
    #         devarr = DBUtils.fetchall(conn, sql)
    #         if(devarr is not None):
    #             for dev in devarr:
    #                 linksdict[dev[0]] = json.loads(dev[-1])
    #                 #detail总是应该放在最后的字段
    #     except:
    #         Utils.logException('getAllDeviceLinks()异常 ')
    #         linksdict.clear()
    #     if linksdict == None or len(linksdict) == 0:
    #         return None
    #     return linksdict.values()

    # 根据v_type查询HGC配置
    def getByVtype(self, v_type):

        if v_type is None:
            return None
        try:
            tmp = str(hex(v_type))
            v_type = tmp[0:2] + tmp[2:].upper()
            conn = DBUtils.get_conn()
            sql = "select * from " + self.tablename + " where (v_type = '" + v_type + "')"
            result = DBUtils.fetchall(conn, sql)
            if(result is None or len(result) == 0):
                return None
            else:
                devices = []
                for item in result:
                    item = json.loads(item[-1])
                    devices.append(item)
                return devices
        except:
            Utils.logException("getByVtype exception!!!")


    #返回json格式串
    def getHGCconfig(self, addr, v_type, channel):
        Utils.logDebug("->getHGCconfig %s %s %s"%(addr, str(v_type), str(channel)))
        if addr == None:
            return None
        # result = self.getByKey('addr', name)
        conn = DBUtils.get_conn()
        sql = "select * from " + self.tablename + " where (addr = '"+ addr + "' and channel = " + str(channel) + " and v_type = '" + str(v_type) + "')"
        result = DBUtils.fetchall(conn, sql)
        if(result == None or len(result) == 0):
            return None
        else:
            return json.loads(result[0][-1])    #返回json

    #删除一条记录
    def deleteHGCconfig(self, addr, v_type, channel):
        Utils.logDebug("->getHGCconfig %s %s %s"%(addr, str(v_type), str(channel)))
        if addr == None:
            return None

        sql = "DELETE FROM " + self.tablename + " where (addr = '"+ addr + "' and channel = " + str(channel) + " and v_type = '" + str(v_type) + "')"

        try:
            conn = DBUtils.get_conn()
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByAddr()异常')
            return False


    ## 返回中控设备上 灯、插座、窗帘等的所有配置
    ## 返回 [{},{}]
    def queryHGCconfigByType(self, addr, v_type):

        ret = []
        if addr == None or v_type == None:
            return ret

        Utils.logDebug("->queryHGCconfigByType %s %s"%(addr, str(v_type)))
        conn = DBUtils.get_conn()
        sql = "select * from " + self.tablename + " where (addr = '"+ addr + "' and v_type = '" + str(v_type) + "')"
        result = DBUtils.fetchall(conn, sql)
        if(result == None or len(result) == 0):
            return ret
        else:
            for r in result:
                ret.append(json.loads(r[-1]))
            return ret   #返回json数组

    def deleteByAddr(self, addr):
        if addr == None:
            return False

        Utils.logDebug("->deleteByAddr %s"%(addr))
        try:
            conn = DBUtils.get_conn()
            sql = "DELETE FROM " + self.tablename + " WHERE (addr = '" + addr + "')"
            DBUtils.deleteone(conn, sql)
            return True
        except:
            Utils.logException('deleteByAddr()异常')
            return False


    # ## 根据设备地址删除记录
    # def deleteByDevAddr(self, HGCAddr, v_type, devAddr):
    #
    #     ret = self.queryHGCconfigByType(HGCAddr, v_type)
    #
    #     ## 同一个设备可能有多个通道，比如三联灯
    #     channels = []
    #
    #     for item in ret:
    #         controls = item.get("controls", None)
    #         if controls is not None:
    #             if controls[0].get("addr") == devAddr:
    #                 channel = item.get("channel")
    #                 channels.append(channel)
    #
    #     results = []
    #     for channel in channels:
    #         result = self.deleteHGCconfig(HGCAddr, v_type, channel)
    #         results.append(result)
    #
    #     for item in results:
    #         if item is False:
    #             return False
    #     return True


if __name__ == '__main__':
    d1 = DBManagerHGC()
