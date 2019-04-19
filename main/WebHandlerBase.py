#! /usr/bin/python
#coding=utf-8

import GlobalVars
import Utils
from SocketClientControl import *
from pubsub import pub
import ErrorCode


class WebHandlerBase(object):
    
    def __init__(self):
        self.controlClient = None
    
    def sendCommand(self, msgId, payload):
        cmd = {}
        cmd["cmdType"] = msgId
        cmd["payload"] = payload
        try:
            buf = self._syncTxAndRx(json.dumps(cmd))
        except:
            buf = None
        finally:
            del cmd
        return buf

    # 同步发送数据并接受响应
    def _syncTxAndRx(self, msg):
        try:
            ret = self.controlClient.send2(msg)
            if ret <= 0:
                return None
            buf = self.controlClient.recv()
        except Exception as e:
            Utils.logError('===>_syncTxAndRx error: %s' % e)
            time.sleep(2)
            ret = self.controlClient.send2(msg)
            if ret <= 0:
                return None
            buf = self.controlClient.recv()
        return buf

    # 新处理方式  待确认是否使用
    # def _syncTxAndRx(self, msg):
    #     try:
    #         ret = self.controlClient.send2(msg)
    #         if ret <= 0:
    #             return None
    #         buf = self.controlClient.recv()
    #         if buf is not None:
    #             self.uninit()
    #     except Exception as e:
    #         Utils.logError('===>_syncTxAndRx error: %s' % e)
    #         time.sleep(2)
    #         ret = self.controlClient.send2(msg)
    #         if ret <= 0:
    #             return None
    #         buf = self.controlClient.recv()
    #         if buf is not None:
    #             self.uninit()
    #     finally:
    #         if self.controlClient is not None:
    #             self.uninit()
    #     return buf

    def init(self):
        self.controlClient = SocketClientControl()
        self.controlClient.start()
        Utils.logDebug("WebHandlerBase init socket success")
    
    def uninit(self):
        self.controlClient.stop()
        self.controlClient = None
        Utils.logDebug("WebHandlerBase uninit socket success")
        
    def successWithObj(self, obj):
        return obj
    
    def successWithMsg(self, tip):
        # ret = {}
        # ret["msg"] = tip
        if tip == None:
            return self.failWithMsg("网关故障，重启可恢复")
        return json.loads(tip)
        # return ret;

    def failWithMsg(self, tip):
        return self.failWithMsg2(ErrorCode.ERR_GENERAL, tip)

    def failWithMsg2(self, err, tip):
        return {"ret": err, "msg": tip}