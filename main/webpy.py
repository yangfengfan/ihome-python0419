#!/usr/bin/python
#coding=utf-8

from web import *
import web
import json
import time
import os
import sys
# abspath = os.path.dirname(sys.path[0])
# serviceBaseHome = abspath + "/../cloud/www/ihome"
# print "serviceBase path:" + serviceBaseHome
# sys.path.append(serviceBaseHome)
from WebHandlerHost import *
from WebHandlerPlan import *
from WebHandlerWarning import *
from WebHandlerDevice import *
from WebHandlerRoom import *
from WebHandlerWrapperRequests import *
from WebHandlerUser import *
from WebHandlerEnergy import *
import Utils
import base64

# web.py 关键点http://www.cnblogs.com/sing1ee/archive/2012/03/18/2765031.html

urls = (
    '/', 'index',
    '/device/(.+)', 'DeviceAction',
    '/devices/(.+)', 'DeviceAction',
    '/room/(.+)', 'RoomAction',
    '/auth/(.+)', 'HostAction',
    '/host/(.+)', 'HostAction',
    '/plan/(.+)', 'PlanAction',
    '/alarm/(.+)', 'WarningAction',
    '/wrapper/(.+)', 'WrapperAction',
    '/energy/(.+)', 'EnergyAction',
    '/user/(.+)', 'UserAction'
    )
class index:
    def GET(self):
        web.seeother("/static/index.html")

class BaseAction:
    def handleRequest(self, data, handlerobj, method):
        paramObj = json.loads(data)
        paramStr = paramObj.get('sparam', '{}')
        try:
            # theObject = globals()[handler]()
            result = {}
            # 初始化socket
            start_exec = time.clock()
            handlerobj.init()
            methodObj = getattr(handlerobj, method, None)
            if methodObj is None:
                return method + " not exist"
            else:
                # 处理请求
                result = methodObj(paramStr)
            # 断开socket
            handlerobj.uninit()
            end_exec = time.clock()
            jsonResult = json.dumps(result)
            x64result = base64.encodestring(jsonResult)
            r = {}
            r['sresult'] = x64result
            return json.dumps(r)
        except:
            Utils.logException("webpy exception")
            failResp = {}
            failResp['ret'] = ErrorCode.ERR_RESTART
            failResp['msg'] = '网关故障，重启可恢复'
            return json.dumps(failResp)


class HostAction(BaseAction):

    def POST(self, method):
        if(method is None):
            return "invalid request."
        data = web.data()
        # appver = data[version]
        # globalVars.logMessage(appver);
        
        web.header('Content-type', 'application/json')
        # serviceName = data.get('service', '' )
#         methodName = data.get('method', '' )
#         if(serviceName == '' or methodName == ''):
#             return ("param error");
        return self.handleRequest(data, UserLogin(), method)


class PlanAction(BaseAction):

    def POST(self, method):
        if(method is None):
            return "invalid request."
        
        data = web.data()
        # appver = data[version]
        web.header('Content-type','application/json')
        return self.handleRequest(data, PlanHandler(), method)

class WarningAction(BaseAction):
    def POST(self, method):
        if(method is None):
            return "invalid request."
        
        data = web.data()
        # appver = data[version]
        web.header('Content-type','application/json')
        return self.handleRequest(data, WarningHandler(), method)


class DeviceAction(BaseAction):
    def POST(self, method):
        if(method is None):
            return "invalid request."
        
        data = web.data()
        # appver = data[version]
        web.header('Content-type','application/json')
        return self.handleRequest(data, DeviceHandler(), method)


class RoomAction(BaseAction):

    def POST(self, method):
        if(method is None):
            return "invalid request."
        data = web.data()
        # appver = data[version]
        web.header('Content-type', 'application/json')
        return self.handleRequest(data, RoomHandler(), method)


class WrapperAction(BaseAction):
    def POST(self, method):
        if(method is None):
            failResp = {}
            failResp['ret'] = ErrorCode.ERR_GENERAL
            failResp['msg'] = 'URL无法识别'
            return json.dumps(failResp)
        data = web.input(cmdTyp=0)
        if data.cmdType == 0:
            failResp = {}
            failResp['ret'] = ErrorCode.ERR_GENERAL
            failResp['msg'] = 'URL无法识别请求类型'
            return json.dumps(failResp)
        # appver = data[version]
        web.header('Content-type','application/json')
        # return self.handleRequest(data, WrapperRequestsHandler(), method)
        handlerobj = WrapperRequestsHandler()
        paramObj = json.loads(data)
        paramStr = paramObj.get('sparam', '{}')
        try:
            start_exec = time.clock()
            handlerobj.init()
            methodObj = getattr(handlerobj, method, None)
            if(methodObj is None):
                return method + " not exist"
            else:
                # 处理请求
                result = methodObj(paramStr, data.cmdTyp)
            # 断开socket
            handlerobj.uninit()
            end_exec = time.clock()
            jsonResult = json.dumps(result)
            x64result = base64.encodestring(jsonResult)
            r = {}
            r['sresult'] = x64result
            return json.dumps(r)
        except:
            Utils.logException("webpy exception")
            failResp = {}
            failResp['ret'] = ErrorCode.ERR_RESTART
            failResp['msg'] = '网关故障，重启可恢复'
            return json.dumps(failResp)


class EnergyAction(BaseAction):

    def POST(self, method):
        if method is None:
            return "invalid request."
        data = web.data()
        web.header('Content-type', 'application/json')
        return self.handleRequest(data, EnergyHandler(), method)


class UserAction(BaseAction):

    # @login_required
    def POST(self, method):
        if method is None:
            return "invalid request."
        data = web.data()
        # appver = data[version]
        web.header('Content-type', 'application/json')
        return self.handleRequest(data, UserHandler(), method)

if __name__ == "__main__": 
    app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()