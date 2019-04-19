#!/usr/bin/python
# -*- coding: utf-8 -*-

import DBUtils
import GlobalVars
import Utils
import threading
import json

# 用户数据库表名
TABLE_NAME_USER = "tbl_user"

KEY_ID = "id"
KEY_VERSION = "version"
KEY_USER_NAME = "username"       # 用户名
KEY_USER_DETAIL = "detail"       # 用户信息详情


class DBManagerUser(object):
    __instant = None
    __lock = threading.Lock()
    
    # singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(DBManagerUser.__instant==None):
            DBManagerUser.__lock.acquire()
            try:
                if(DBManagerUser.__instant==None):
                    Utils.logDebug("new DBManagerUser singleton instance.")
                    DBManagerUser.__instant = object.__new__(self)
            finally:
                DBManagerUser.__lock.release()
        return DBManagerUser.__instant

    def __init__(self):  
        Utils.logDebug("__init__")
        self.tablename = TABLE_NAME_USER
        self.tableversion = 1
        self.createUpgradeTable()

    def createUpgradeTable(self):
        Utils.logDebug("->createUpgradeTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.tablename + "' ("
        create_table_sql += " `" + KEY_ID +               "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION +          "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_USER_NAME + "` varchar(50) UNIQUE,"
        create_table_sql += " `" + KEY_USER_DETAIL +   "` TEXT"
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

    # detailJsonStr是升级详情所有属性的Json格式化串
    def saveUser(self, detailObj):
        if(detailObj is None):
            Utils.logError('saveUser() rx invalid inputs')
            return False
        Utils.logDebug("->saveUser %s"%(detailObj))
        try:
            username = detailObj.get(KEY_USER_NAME, None)
            
            if(username is None):
                Utils.logError('json does not include username attr')
                return False
            userDetailJsonStr = json.dumps(detailObj)
            success = True
            detailObjInDB = self.getUserDetailBy(username)
            if(detailObjInDB is None):
                save_sql = "INSERT INTO " + self.tablename + " values (?,?,?,?)"
                data = [(None, self.tableversion, username, userDetailJsonStr)]
                conn = DBUtils.get_conn()
                success = DBUtils.save(conn, save_sql, data)
            else:
                update_sql = 'UPDATE ' + self.tablename + ' SET ' 
                update_sql += ' ' + KEY_USER_DETAIL + ' = ? '
                update_sql += ' WHERE '+ KEY_USER_NAME + ' = ? '
                
                data = [(userDetailJsonStr, username)]
                conn = DBUtils.get_conn()
                success = DBUtils.update(conn, update_sql, data)
            
            return success
        except:
            Utils.logException('saveUser()异常 ')
            return False

    # 返回满足条件的所有告警的json格式串
    # conditionDict = {“username”:"XX"}
    def getByCondition(self, conditionDict):
        detailDict = {}
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('getByCondition has invalid where condition')
            return detailDict
        try:
            conn = DBUtils.get_conn()

            # 组装sql语句
            sql = "select * from " + self.tablename + " where( "
            where = ""
            for key in conditionDict.keys():
                if(where != ""):
                    where += " and "
                where += "(" + key + " = " + str(conditionDict[key]) + ")"
            sql += where + " )"

            detailarr = DBUtils.fetchall(conn, sql)
            # detailarr应该是[(id, version, username, detail),(...)]数组格式
            if(detailarr is not None):
                for dev in detailarr:
                    detailDict[dev[0]] = json.loads(dev[-1])        # detail总是应该放在最后的字段
        except:
            Utils.logException('getByCondition()异常 ')
            detailDict.clear()
        return detailDict.values()
        
    def deleteByKey(self, conditionDict):
        if(conditionDict is None or len(conditionDict) == 0):
            Utils.logError('deleteByKey has invalid where condition')
            return False
        try:
            conn = DBUtils.get_conn()
            # 组装sql语句
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

    def getUserDetailBy(self, username):
        Utils.logDebug("->getUserDetailBy %s"%(username))
        conds = {}
        if(username is None):
            Utils.logError("getUserDetailBy rx invalid inputs")
        else:
            conds[KEY_USER_NAME] = "'" + username + "'"
        result = self.getByCondition(conds)
        if(result == None or len(result) == 0):
            return None
        else:
            return result[0]

if __name__ == '__main__':
    d1 = DBManagerUser()
    d2 = DBManagerUser()
    print "getUserDetailBy(None):", d1.getUserDetailBy(None)
    print "getUserDetailBy(''):", d1.getUserDetailBy('')

    detailDict={"username":"test.d","md5":"781e5e245d69b566979b86e28d23f2c7","seq":"0","retry":"2","status":"ongoing"}
    d2.saveUser(detailDict)
    detailDict2={"username":"d.test","md5":"781e5e245d69b566979b86e28d23f2c8","seq":"4","retry":"1","status":"ongoing"}
    d1.saveUser(detailDict2)

    print "============================="
    detail1 = d1.getUserDetailBy("test.d")
    if detail1.get("md5", "") == "781e5e245d69b566979b86e28d23f2c7":
        print "===================MD5 check SUCCESS"
    else:
        print "####################ERRROR1#########"
    detail2 = d2.getUserDetailBy("d.test")
    if detail2.get("md5", "") == "781e5e245d69b566979b86e28d23f2c8":
        print "====================MD5 check SUCCESS"
    else:
        print "####################ERRROR2#########"
