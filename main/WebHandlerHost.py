#! /usr/bin/python
#coding=utf-8

import json
import datetime
import string
import time
import GlobalVars
import Utils
from DBManagerUser import *
from WebHandlerBase import *
from DBManagerHostId import *

    
# 请勿瞎改方法名，必须和url相对应
class UserLogin(WebHandlerBase):
    # 确保admin用户存在
    def autoCreateAdmin(self):
        userObj = DBManagerUser().getUserDetailBy("admin")
        if(userObj != None):
            return

        # hashlib.md5("admin").hexdigest()
        userObj = {"username": "admin", "password": "21232f297a57a5a743894a0e4a801fc3", "nickname": "管理员"}
        try:
            userInfo = DBManagerUser().saveUser(userObj)
        except:
            Utils.logException("autoCreateAdmin() error")
        return

    # 修改用户密码参数: {"name":"admin","password":"admin","email":"admin@163.com","mobile":"1391919199"}
    def modifyUser(self, param):
        self.autoCreateAdmin()
        userName =  param.get("username", "")
        if(userName == ""):
            return self.failWithMsg('username is not provided!')
    
        curTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            userObj = DBManagerUser().getUserDetailBy(userName)
            if(userObj == None):
                return self.failWithMsg('user not exist!')
            # 修改admin用户信息
            newpass = param.get("password", None)
            if(newpass is not None):
                userObj["password"] = newpass
            mobile = param.get("mobile", None)
            if(mobile is not None):
                userObj["mobile"] = mobile
            email = param.get("email", None)
            if(email is not None):
                userObj["email"] = email
            updatetime = userObj.get("createtime", None)
            if(updatetime is None):
                updatetime = curTime
            userObj["updatetime"] = curTime

            DBManagerUser().saveUser(userObj)
            return self.successWithMsg(json.dumps(userObj))
        except:
            return self.failWithMsg('modifyUser.save Exception')

    def login(self, param):
        Utils.logDebug("->login()")
        self.autoCreateAdmin()
        try:
            userName = param.get("username", "")
            userPassword = param.get("password", "")
        except:
            userObj = {"status": 1, "statusinfo": "参数错误"}
            return self.successWithObj(userObj)
    
        try:
            userObj = DBManagerUser().getUserDetailBy(userName)
        except:
            userObj = {"status": 2, "statusinfo": "无此用户"}
            return self.successWithObj(userObj)
    
        if(userObj == None):
            userObj = {"status": 2, "statusinfo": "无此用户"}
            return self.successWithObj(userObj)
        if userObj.get("password", "") == userPassword:
            userObj["status"] = 0
            userObj["statusinfo"] = ""
            hostId = DBManagerHostId().getHostId()
            if hostId != None:
                userObj["hostId"] = hostId

            return self.successWithObj(userObj)
        else:
            userObj = {"status": 3, "statusinfo": "网关安全码错误"}
            return self.successWithObj(userObj)

    def _verifypassword(self, param):
        return self.login(param)
    
    def resetpassword(self, param):
        return self.modifyUser(param)

    def verifyadminpassword(self, param):
        return self._verifypassword(param)
        
    def logout(self, param):
        return {"ret": ErrorCode.SUCCESS}
    
    def modifyproperty(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_MODIFY_HOST_CONFIG, sparam)
        return self.successWithMsg(buf)
    
    def showproperty(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_READ_HOST_CONFIG, param)
        return self.successWithMsg(buf)

    def queryglobaldata(self, param):
        Utils.logDebug("->queryglobaldata")
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_GLOBAL_DATA, param)
        return self.successWithMsg(buf)

    def modifyHostName(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_MODIFY_HOSTNAME_CONFIG, param)
        return self.successWithMsg(buf)
        # hostId = param.get("hostId", None)
        # hostName = param.get("hostName", None)
        #
        # if hostId == None or hostName == None:
        #     return (ErrorCode.ERR_INVALID_REQUEST, None)
        #
        # host = DBManagerHostId().getByHostId(hostId)
        #
        # if host == None:
        #     ##必须初始化过
        #     return (ErrorCode.ERR_GENERAL, None)
        # else:
        #     result = DBManagerHostId().setHostName(hostName)

    def backupHostProp2(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_BACKUP_HOST_PROP2, param)
        return self.successWithMsg(buf)

    def upgradeHost(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_UPGRADE_NOTIFICATION, param)
        return self.successWithMsg(buf)

    def restoreHostProp(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_RESTORE_HOST_PROP, param)
        return self.successWithMsg(buf)

    def time(self, param):
        # buf = self.sendCommand(GlobalVars.TYPE_CMD_GET_SYS_TIME, param)
        # return self.successWithMsg(buf)
        time_stamp = int(time.time())
        local_time = time.localtime()
        response_dict = dict(timestamp=time_stamp)
        time_str = time.strftime("%Y-%m-%d %H:%M:%S %A")
        response_dict["timeString"] = time_str
        # list, 年，月，日，时，分，秒，星期
        response_dict["timeList"] = [local_time.tm_year, local_time.tm_mon, local_time.tm_mday, local_time.tm_hour,
                                    local_time.tm_min, local_time.tm_sec, int(local_time.tm_wday) + 1]
        result_dict = dict(ret=0, response=response_dict)
        return self.successWithObj(result_dict)
