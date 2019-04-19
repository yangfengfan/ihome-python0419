#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json

#告警数据库表名
TABLE_NAME_UPGRADE = "tbl_upgrade"

KEY_ID = "id"
KEY_VERSION = "version"
KEY_UPGRADE_FILENAME = "filename"       #升级文件名
KEY_UPGRADE_DETAIL = "detail"           #升级状态详细json

##deprecated.


##升级文件下载时，MD5对应软件包签名
##文件下载完成后，需要判断服务端的MD5是否和软件包计算得到的MD5一致？
##文件下载时，每次下载100KB
##文件的下载序列存储在seq
##retry对应同一seq重复发送的次数
##status对应软件升级的状态 #{"filename":"test.d","md5":"781e5e245d69b566979b86e28d23f2c7","seq":"0","retry":"2","status":"ongoing"}
class DBManagerUpgrade(object):
    __instant = None;
    __lock = threading.Lock();
    
    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerUpgrade.__instant==None):
            DBManagerUpgrade.__lock.acquire();
            try:
                if(DBManagerUpgrade.__instant==None):
                    Utils.logDebug("new DBManagerUpgrade singleton instance.")
                    DBManagerUpgrade.__instant = object.__new__(self);
            finally:
                DBManagerUpgrade.__lock.release()
        return DBManagerUpgrade.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_UPGRADE
        self.tableversion = 1
        self.createUpgradeTable()

    def createUpgradeTable(self):
        Utils.logDebug("->createUpgradeTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID +               "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION +          "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_UPGRADE_FILENAME + "` varchar(50) UNIQUE,"
        create_table_sql += " `" + KEY_UPGRADE_DETAIL +   "` TEXT"
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

    #detailJsonStr是升级详情所有属性的Json格式化串
    def saveUpgrade(self, upgradeDetailJsonStr):
        Utils.logDebug("->saveUpgrade %s"%(upgradeDetailJsonStr))
        if(upgradeDetailJsonStr == "" or upgradeDetailJsonStr is None):
            Utils.logError('saveUpgrade() rx invalid inputs %s'%(upgradeDetailJsonStr))
            return False
        try:
            detailObj = json.loads(upgradeDetailJsonStr)
            filename = detailObj.get(KEY_UPGRADE_FILENAME, None)
            
            if(filename is None):
                Utils.logError('json does not include filename attr')
                return False

            success = True
            detailObjInDB = self.getUpgadeDetailByFilename(filename)
            if(detailObjInDB is None):
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?)"
                data = [(None, self.tableversion, filename, upgradeDetailJsonStr)]
                conn = DBUtils.get_conn_rt()
                success = DBUtils.save(conn, save_sql, data)
            else:
                update_sql = 'UPDATE ' + self.tablename + ' SET ' 
                update_sql += ' ' + KEY_UPGRADE_DETAIL + ' = ? '
                update_sql += ' WHERE '+ KEY_UPGRADE_FILENAME + ' = ? '
                
                data = [(upgradeDetailJsonStr, filename)]
                conn = DBUtils.get_conn_rt()
                success = DBUtils.update(conn, update_sql, data)
            
            return success
        except:
            Utils.logException('saveUpgrade()异常 ')
            return False

    #返回满足条件的所有告警的json格式串 
    #conditionDict = {“filename”:"XX"}
    def getByCondition(self, conditionDict):
        detailDict = {}
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('getByCondition has invalid where condition')
            return detailDict
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
            
            detailarr = DBUtils.fetchall(conn, sql)
            #detailarr应该是[(id, version, filename, detail),(...)]数组格式
            if(detailarr is not None):
                for dev in detailarr:
                    detailDict[dev[0]] = json.loads(dev[-1])        #detail总是应该放在最后的字段
        except:
            Utils.logException('getByCondition()异常 ')
            detailDict.clear()
        return detailDict.values()
        
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
            Utils.logException('deleteByKey()异常 ')
            return False

    def getUpgadeDetailByFilename(self, filename):
        Utils.logDebug("->getUpgadeDetailByFilename %s"%(filename))
        conds = {}
        if(filename is None):
            Utils.logError("getUpgadeDetailByFilename rx invalid inputs")
        else:
            conds[KEY_UPGRADE_FILENAME] = "'" + filename + "'"
        result = self.getByCondition(conds)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]
    
    def getAllUpgradeDetails(self):
        Utils.logDebug("->getAllUpgradeDetails()")
        detailDict = {}
        try:
            conn = DBUtils.get_conn_rt()
            #组装sql语句
            sql = "select * from " + self.tablename 
        
            detailarr = DBUtils.fetchall(conn, sql)
            if(detailarr is not None):
                for dev in detailarr:
                    detailDict[dev[0]] = json.loads(dev[-1])
        except:
            Utils.logException('getAllUpgradeDetails()异常 ')
            detailDict.clear()

        if detailDict == None or len(detailDict) == 0:
            return None
        return detailDict.values()

    def deleteByFilename(self, filename):
        Utils.logDebug("->deleteByFilename %s"%(filename))
        conds = {}
        if(filename is None):
            Utils.logError("deleteByFilename rx invalid inputs")
        else:
            conds[KEY_UPGRADE_FILENAME] = "'" + filename + "'"
        return self.deleteByKey(conds)
        
if __name__ == '__main__':
    d1 = DBManagerUpgrade()
    d2 = DBManagerUpgrade()
    print "getUpgadeDetailByFilename(None):", d1.getUpgadeDetailByFilename(None)
    print "getUpgadeDetailByFilename(''):", d1.getUpgadeDetailByFilename('')

    detailDict={"filename":"test.d","md5":"781e5e245d69b566979b86e28d23f2c7","seq":"0","retry":"2","status":"ongoing"}
    d2.saveUpgrade(json.dumps(detailDict))
    detailDict2={"filename":"d.test","md5":"781e5e245d69b566979b86e28d23f2c8","seq":"4","retry":"1","status":"ongoing"}
    d1.saveUpgrade(json.dumps(detailDict2))

    print "============================="

    detailObjs = DBManagerUpgrade().getAllUpgradeDetails()
    if len(detailObjs) == 2:
        print "===================getAllUpgradeDetails SUCCESS"
    else:
        print "####################ERRROR1#########"

    detail1 = d1.getUpgadeDetailByFilename("test.d")
    if detail1.get("md5", "") == "781e5e245d69b566979b86e28d23f2c7":
        print "===================MD5 check SUCCESS"
    else:
        print "####################ERRROR1#########"
    detail2 = d2.getUpgadeDetailByFilename("d.test")
    if detail2.get("md5", "") == "781e5e245d69b566979b86e28d23f2c8":
        print "================MD5 check SUCCESS"
    else:
        print "####################ERRROR2#########"

    d1.deleteByFilename("d.test")
    detail3 = d1.getUpgadeDetailByFilename("d.test")
    if detail3 is not None:
        print "####################ERRROR3#########"
    else:
        print "======================Delete SUCCESS."

    