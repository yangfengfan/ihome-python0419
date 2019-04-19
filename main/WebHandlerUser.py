# -*- coding: utf-8 -*-
from WebHandlerBase import WebHandlerBase
import Utils
import GlobalVars
from DBManagerUser import *
import ErrorCode
import os
import hashlib


class UserHandler(WebHandlerBase):

    def generateToken(self, username):
        token = hashlib.sha1(os.urandom(24)).hexdigest() + username
        return token

    def login(self, sparam):
        if sparam is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        username = sparam.get("username", None)
        password = sparam.get("password", None)
        if username is None or password is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        old_user = DBManagerUser().getUserDetailBy(username)
        if old_user is None:
            result = {"ret": ErrorCode.ERR_WRONG_USERNAME_PASSWORD_LOGIN, "message": "login接口用户不存在"}
            return self.successWithObj(result)

        try:
            if password == old_user.get("password", None):
                token = self.generateToken(username)
                old_user["token"] = token
                success = DBManagerUser().saveUser(old_user)
                if success is True:
                    user_info = old_user.get("userInfo", None)
                    result = {"ret": ErrorCode.SUCCESS, "message": "登陆成功", "token": token, "userInfo": user_info}
                    return self.successWithObj(result)
                else:
                    result = {"ret": ErrorCode.ERR_SQL_LOGIN, "message": "login接口数据库错误"}
                    return self.successWithObj(result)
            else:
                result = {"ret": ErrorCode.ERR_WRONG_USERNAME_PASSWORD, "message": "用户名密码错误"}
                return self.successWithObj(result)
        except Exception as err:
            Utils.logError("===>login error: %s" % err)
            result = {"ret": ErrorCode.ERR_SERVER_LOGIN, "message": "login服务器内部错误"}
            return self.successWithObj(result)

    def authorizedLogin(self, sparam):

        if sparam is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        username = sparam.get("username", None)
        if username is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        try:
            token = self.generateToken(username)
            sparam["token"] = token
            success = DBManagerUser().saveUser(sparam)
            if success is True:
                result = {"ret": ErrorCode.SUCCESS, "message": "登陆成功", "token": token}
                return self.successWithObj(result)
            else:
                result = {"ret": ErrorCode.ERR_SQL_AUTHORIZED, "message": "authorizedLogin接口数据库错误"}
                return self.successWithObj(result)
        except Exception as err:
            Utils.logError("===>authorizedLogin error: %s" % err)
            result = {"ret": ErrorCode.ERR_SERVER_AUTHORIZEDLOGIN, "message": "authorizedLogin服务器内部错误"}
            return self.successWithObj(result)

    def logout(self, sparam):

        if sparam is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        username = sparam.get("username", None)
        if username is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        try:
            old_user = DBManagerUser().getUserDetailBy(username)
            if old_user is None:
                result = {"ret": ErrorCode.ERR_WRONG_USERNAME_PASSWORD_LOGOUT, "message": "logout接口用户不存在"}
                return self.successWithObj(result)
            result = {"ret": ErrorCode.SUCCESS, "message": "退出登陆成功"}
            return self.successWithObj(result)
        except Exception as err:
            Utils.logError("===>logout error: %s" % err)
            result = {"ret": ErrorCode.ERR_SERVER_LOGOUT, "message": "logout服务器内部错误"}
            return self.successWithObj(result)

    def saveUserInfo(self, param):
        if param is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        username = param.get("username", None)
        user_info = param.get("userInfo", None)
        if username is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        old_user = DBManagerUser().getUserDetailBy(username)
        if old_user is None:
            result = {"ret": ErrorCode.ERR_USER_SAVEUSERINFO, "message": "saveUserInfo接口用户不存在"}
            return self.successWithObj(result)

        try:
            old_user["userInfo"] = user_info
            success = DBManagerUser().saveUser(old_user)
            if success is True:
                result = {"ret": ErrorCode.SUCCESS, "message": "保存成功"}
                return self.successWithObj(result)
            else:
                result = {"ret": ErrorCode.ERR_SQL_SAVE, "message": "saveUserInfo接口数据库错误"}
                return self.successWithObj(result)
        except Exception as err:
            Utils.logError("===>saveUserInfo error: %s" % err)
            result = {"ret": ErrorCode.ERR_SERVER_SAVE, "message": "saveUserInfo服务器内部错误"}
            return self.successWithObj(result)

    def deleteUser(self, param):
        if param is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        username = param.get("username", None)
        if username is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        old_user = DBManagerUser().getUserDetailBy(username)
        if old_user is None:
            result = {"ret": ErrorCode.ERR_USER_DELETEUSER, "message": "deleteUser接口用户不存在"}
            return self.successWithObj(result)

        try:
            success = DBManagerUser().deleteByKey({"username": username})
            if success is True:
                result = {"ret": ErrorCode.SUCCESS, "message": "删除成功"}
                return self.successWithObj(result)
            else:
                result = {"ret": ErrorCode.ERR_SQL_DELETE, "message": "deleteUser接口数据库错误"}
                return self.successWithObj(result)
        except Exception as err:
            Utils.logError("===>delete user error: %s" % err)
            result = {"ret": ErrorCode.ERR_SERVER_DELETEUSER, "message": "deleteUser服务器内部错误"}
            return self.successWithObj(result)

    def queryUserInfo(self, param):
        if param is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        username = param.get("username", None)
        if username is None:
            result = {"ret": ErrorCode.ERR_INVALID_PARAMS, "message": "参数错误"}
            return self.successWithObj(result)

        old_user = DBManagerUser().getUserDetailBy(username)
        if old_user is None:
            result = {"ret": ErrorCode.ERR_WRONG_USERNAME_PASSWORD_QUERY, "message": "queryUserInfo用户不存在"}
            return self.successWithObj(result)
        user_info = old_user.get("userInfo", None)
        if user_info is None:
            result = {"ret": ErrorCode.ERR_NO_SAVE_USER, "message": "未保存用户信息"}
            return self.successWithObj(result)
        result = {"ret": ErrorCode.SUCCESS, "userInfo": user_info}
        return self.successWithObj(result)

    def modifyUser(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_MODIFY_USER_CONFIG, param)
        return self.successWithMsg(buf)

    def verifyAdmin(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_VERIFY_ADMIN_PWD, param)
        return self.successWithMsg(buf)

    def verifyUser(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_VERIFY_USER_PWD, param)
        return self.successWithMsg(buf)
