# -*- coding: utf-8 -*-


from ThreadBase import *
import GlobalVars
import Utils
import json
from PacketParser import *
from pubsub import pub
from DBManagerAlarm import *
from DBManagerDevice import *
from DBManagerBackup import *
from BoerCloud import *
from WebHandlerBase import *
from DBManagerHostId import *
from DBManagerHistory import *
import hashlib
import time
import random
import os


class CloudServerConfig(object):
    SEGLORD_HOST = GlobalVars.SERVER_URL
    SEGLORD_PORT = 3654

# 网络状态变化，如果是连接状态，则备份线程会启动同步实时数据。
# 实时数据如告警、设备状态等也能立即发送给云端，即使还在备份过程中
# 云端可能会收到实时的状态数据，以及备份线程发出的旧状态数据，需要云端判别json中的“timestamp”，新的覆盖旧的，旧的直接丢弃


class HostCloudClient(ThreadBase):
    __instant = None
    __lock = threading.Lock()
    __tansIdLock = threading.Lock()
    __removeLock = threading.Lock()

    __packetMetaDict = {}

    # singleton
    def __new__(self, arg):
        Utils.logDebug("__new__")
        if(HostCloudClient.__instant==None):
            HostCloudClient.__lock.acquire()
            try:
                if(HostCloudClient.__instant==None):
                    Utils.logDebug("new HostCloudClient singleton instance.")
                    HostCloudClient.__instant = ThreadBase.__new__(self)
            finally:
                HostCloudClient.__lock.release()
        return HostCloudClient.__instant

    def __init__(self, threadId):
        self.transId=int(time.time())  # Shared resource
        self.currHandshakeTransId = 0
        self.cloudConnected = False
        ThreadBase.__init__(self, threadId, "HostCloudClient")

    def getTransId(self):
        HostCloudClient.__tansIdLock.acquire()
        try:
            md5_hasher = hashlib.md5()
            md5_hasher.update('%.10f' % (time.time()))
            md5_hasher.update(str(random.random()))
            return md5_hasher.hexdigest().upper()
        finally:
            HostCloudClient.__tansIdLock.release()

    def removeByTransId(self, transId):
        HostCloudClient.__removeLock.acquire()
        try:
            if self.__packetMetaDict.has_key(transId):
                return self.__packetMetaDict.pop(transId,None)
        except:
            Utils.logException('removeByTransId failed...')
        finally:
            HostCloudClient.__removeLock.release()

    def reHandShake(self):
        self.lastCheckHBCounttime = 0
        self.lastHBsendtime = 0
        self.heartbeatLostCount = 0
        self.lastCheckACKtime = 0
        self.lastCheckHandshaketime = 0
        self.sendPacketTimeoutInterval = 2  # 超时2秒
        self.cloudConnected = False

        #
        # self.controlClient = SocketClientControl()
        # self.controlClient.start()

        # 启动后握手
        if self.currHandshakeTransId != 0:
            self.removeByTransId(self.currHandshakeTransId)
        self.currHandshakeTransId = 0
        self.handshakeAck = False
        self._sendHandShake()

    # 检查软件版本和固件版本号，更新网关属性，并备份到云端
    def checkSoftwareUpgrade(self):
        Utils.logInfo("checking software and firmware versions")
        try:
            firmver = Utils.getFirmwareVersion()
            softver = Utils.getSoftwareVersion()
            hostProp = DBManagerHostId().getHost()
            if(hostProp.get("softver", 0) != softver or hostProp.get("firmver", 0) != firmver):
                Utils.logInfo("new version found:software:%s, firmware:%s"%(firmver, softver))
                hostProp["softver"] = softver
                hostProp["firmver"] = firmver
                oldtimestamp = None
                if hostProp.has_key("timestamp"):
                    oldtimestamp = hostProp.get("timestamp")
                hostProp = DBManagerHostId().updateHostConfig(hostProp.get("hostId"), hostProp.get("name"), hostProp, oldtimestamp)
                if hostProp != None:
                    metaDict={}
                    metaDict["type"] = "hostconfig"
                    metaDict["valueStr"] = hostProp
                    Utils.logDebug("publish PUB_SEND_RTDATA hostconfig")
                    pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)
        except:
            Utils.logException("errors when check software/firmware version:")

    def run(self):
        ThreadBase.init(self)
        self.subscribe()
        try:
            hostProp = DBManagerHostId().getHost()
            # 生成与云端长连接的socket客户端对象
            self.cloudClient = LordClient(hostProp.get("hostId", None), hostProp.get("registerHost", True))
            self.cloudClient.config.from_object(CloudServerConfig)        #
            self.cloudClient.setDaemon(True)
            self.cloudClient.start()
            time.sleep(1)
        except:
            Utils.logException("HostCloudClient exception ")

        self.reHandShake()
        self.checkSoftwareUpgrade()

        Utils.logInfo("HostCloudClient is running.")
        while not self.stopped:
            try:
                time.sleep(self.sendPacketTimeoutInterval)
                self.checkHeartbeatCount()
                if self.handshakeAck == False:
                    self.checkHandshake()
                else:
                    self.checkACK()
            except:
                time.sleep(1)
                Utils.logException('HostCloudClient exception.')

        ##thread quit now!
        Utils.logInfo("HostCloudClient quit now...")
        #已经setDaemon(True)
        self.cloudClient.stop()
        self.cloudClient.join(10)

    def _sendHandShake(self):
        Utils.logInfo("_sendHandShakes()")

        self.currHandshakeTransId = self.getTransId()
        msgtuple = self.cloudClient.buildHandshakePacket(self.currHandshakeTransId)
        self.cloudClient.sendMessage(msgtuple[0], msgtuple[1])
        self.savePacketMeta(self.currHandshakeTransId, 0, msgtuple[0], msgtuple[1], saveOnFail=False)
        self.lastCheckHandshaketime = int(time.time())

    def checkHeartbeatCount(self):
        ##Handshake时也要监控无心跳次数
        # if self.cloudConnected == False:
        #     return

        now = int(time.time())
        if now - self.lastCheckHBCounttime < GlobalVars.HEARTBEAT_INTERVAL:
            return

        # 一个心跳周期检查一次
        self.lastCheckHBCounttime = now
        if now - self.lastHBsendtime >= GlobalVars.HEARTBEAT_INTERVAL:
            self.heartbeatLostCount += 1
        if self.heartbeatLostCount >= 3:
            ##心跳丢失3次
            Utils.logCritical("NO HEART BEAT RESPONSE %s times"%(self.heartbeatLostCount))
            Utils.logInfo("publish PUB_HEARBEAT_STATUS down")
            pub.sendMessage(GlobalVars.PUB_HEARBEAT_STATUS, status="down", arg2=None)
            self.cloudConnected = False

            self.restartSSL()
            time.sleep(1)
            self.reHandShake()     #没收到心跳，重新初始化，HandShake
        if self.heartbeatLostCount >= 6:
            Utils.logInfo("publish RESTART cloud...")
            pub.sendMessage("restart_thread", threadname="cloud")

    def checkHandshake(self):
        now = int(time.time())
        if(now - self.lastCheckHandshaketime < GlobalVars.HEARTBEAT_INTERVAL):
            return
        self.lastCheckHandshaketime = now
        Utils.logDebug("->checkHandshake()")
        entry = self.__packetMetaDict.get(self.currHandshakeTransId, None)
        if entry == None:
            return
        # Handshake没ACK，就一直重发
        ret = self.cloudClient.sendMessage(entry["code"], entry["command"])

    def checkACK(self):
        if self.cloudConnected == False:
            return
        now = int(time.time())
        if(now - self.lastCheckACKtime < self.sendPacketTimeoutInterval*5):  # *5是考虑网络状况不佳，或者数据较大时，原来2秒的超时时间过短，导致大量重发。
            return

        # 2秒钟检查一次
        Utils.logDebug("->checkACK()")
        # 超时
        for key in self.__packetMetaDict.keys():
            HostCloudClient.__removeLock.acquire()
            try:
                if self.__packetMetaDict.has_key(key) == False:
                    continue
                meta = self.__packetMetaDict.pop(key, None)
                if meta == None:
                    continue
                retry = meta.get("rety", 0)
                if retry >= 2:
                    # 超时失败
                    saveOnFail = meta.get("saveOnFail", False)
                    if saveOnFail == True:
                        # 实时数据同步失败，存储到Backup表
                        self.saveBackupCommand(meta["code"], meta["command"])
                    # 删除元数据
                    # self.removeByTransId(key)
                    self.linkDown()
                else:
                    # 重发
                    timestamp = meta.get("timestamp", 0)
                    if now - timestamp >= self.sendPacketTimeoutInterval:
                        ret = self.cloudClient.sendMessage(meta["code"], meta["command"])
                        meta["timestamp"] = now
                        meta["retry"] += 1
                        self.__packetMetaDict[key] = meta
            except:
                Utils.logError('checkACK exception...')
            finally:
                HostCloudClient.__removeLock.release()
        self.lastCheckACKtime = now

    def subscribe(self):
        pub.subscribe(self.sendRTDataHandler, GlobalVars.PUB_SEND_RTDATA)
        pub.subscribe(self.heartbeatTimerHandler, GlobalVars.PUB_CLOUD_HEARTBEAT)
        pub.subscribe(self.resendSocket, GlobalVars.PUB_RESEND_SOCKET)
        pub.subscribe(self.backupEnergyHandler, GlobalVars.PUB_BACKUP_ENERGY)
        pub.subscribe(self.recvMessageFromCloudHandler, "rx_ssl_packet")
        # pub.subscribe(self.resetSSLChannelHandler, "reset_ssl_channel")

        # pub.subscribe(self.fileHandler, GlobalVars.PUB_FILE_DOWNLOAD_REQUEST)
        # pub.subscribe(self.cmdResponseHandler, GlobalVars.PUB_SEND_CMDRESPONSE)

    def fileHandler(self, fn, seq):
        if self.cloudConnected == False:
            return
        msgtuple = self.cloudClient.buildFileDownloadRequest(self.getTransId(), fn, seq)
        self.cloudClient.sendMessage(msgtuple[0], msgtuple[1])
        # self.savePacketMeta(transId, 0, msgtuple[0], msgtuple[1], saveOnFail=True)

    def heartbeatTimerHandler(self, arg1, arg2=None):
        # if self.handshakeAck == False:    ##
        #     return
        Utils.logInfo("sending heart beat packet to cloud server.")
        self.cloudClient.sendHeartbeat(self.getTransId())

    #
    # 发送到云端，接收到云端的ACK后才算发送成功。
    # 实现是是异步，所以实时数据的发送，首先存到Backup表（带TransId）.
    # 如果收到成功的ACK，则从Backup表中删除（根据TransId）
    #
    def sendRTDataHandler(self, rtdata, arg2=None):
        Utils.logDebug("->sendRTDataHandler() %s"%(rtdata))
        cmd = rtdata["type"]
        details = rtdata["valueStr"]
        op = "update"


        # 如果rtData有delay属性，则应通知云端延时发送告警
        # rtdata是dict类型
        # details有时是dict，有时是list。当rtdata有delay这一项时details是list类型
        # if rtdata.has_key("delay"):
        #     details[0]["delay"] = rtdata.get("delay")

        if rtdata.has_key("op"):
            op = rtdata["op"]
        transId = self.getTransId()
        msgtuple = ()
        if op == "remove":
            msgtuple = self.cloudClient.buildRemoveRecordsPacket(transId, cmd, details)
        else:
            msgtuple = self.cloudClient.buildRTDataPacket(transId, cmd, op, details)
        if self.cloudConnected == False:
            self.saveBackupCommand(msgtuple[0], msgtuple[1])
            # 网络断开
            return
        self.cloudClient.sendMessage(msgtuple[0], msgtuple[1])
        self.savePacketMeta(transId, 0, msgtuple[0], msgtuple[1], saveOnFail=True)
        # if ret == None:
        #     self.linkDown()
        # else:
        #     #发送云端成功
        #     self.linkUp()
        if cmd == "alarms":
            Utils.logInfo("===>updateAlarmIsNew...")
            # pub.sendMessage("updateAlarmIsNew", addr=details[0].get("addr"), timestamp=details[0].get("timestamp"))
            DBManagerHistory().updateIsNew(details[0].get("addr"), details[0].get("timestamp"))
        return

    # def cmdResponseHandler(self, rtdata, arg2=None):
    #     Utils.logDebug("->cmdResponseHandler() %s"%(rtdata))
    #     if self.cloudConnected == False:
    #         #网络断开
    #         return
    #
    #     cmd = rtdata["cmdId"]
    #     success = rtdata["success"]
    #     transId = self.getTransId()
    #     msgtuple = self.cloudClient.buildCmdResponsePacket(transId, cmdId, success)
    #     self.cloudClient.sendMessage(msgtuple[0], msgtuple[1])
    #     self.savePacketMeta(transId, 0, msgtuple[0], msgtuple[1], saveOnFail=False)
    #     return ret
    #
    def saveBackupCommand(self, code, command):
        Utils.logDebug("->saveBackupCommand()")
        metaDict={}
        metaDict["code"] = code
        metaDict["command"] = command
        pub.sendMessage(GlobalVars.PUB_SAVE_SOCKET_CMD, backup = metaDict, arg2=None)
    
    # TODO,失败怎么办？
    def resendSocket(self, backup, arg2):
        Utils.logDebug("->resendSocket()")
        # keyId = backup["id"]
        code = backup["code"]
        command = backup["command"]
        Utils.logInfo('resendSocket command:code:%s'%(code))
        self.cloudClient.sendMessage(int(code), command)

        # if ret == None:
        #     self.linkDown()
        # else:
        #     self.linkUp()
        #     #发送成功
        #     Utils.logDebug("publish PUB_BACKUP_SUCCESS")
        #     pub.sendMessage(GlobalVars.PUB_BACKUP_SUCCESS, arg1=cmd, arg2=maxId)

        return

    # 备份水电煤数据成功后，从Backup表删除
    def backupEnergyHandler(self, backup, arg2):
        Utils.logDebug("->sendEnergyHandler()")
        maxId = backup["maxId"]
        jsonArr = backup["details"]
        # ret = self.sendBuffer(rtdata)
        # op = None
        payload = json.dumps(jsonArr)
        transId = self.getTransId()
        msgtuple = self.cloudClient.buildEnergyDataPacket(transId, payload)
        self.cloudClient.sendMessage(msgtuple[0], msgtuple[1])
        self.savePacketMeta(transId, maxId, msgtuple[0], msgtuple[1], saveOnFail=False)
        
        # if ret == None:
        #     self.linkDown()
        # else:
        #     self.linkUp()
        #     #发送成功
        #     Utils.logDebug("publish PUB_BACKUP_SUCCESS")
        #     pub.sendMessage(GlobalVars.PUB_BACKUP_SUCCESS, arg1=cmd, arg2=maxId)
        #
        return

    # 存储发送报文的元数据
    # 简单实现超时重发和失败机制
    def savePacketMeta(self, transId, maxId, code, msg, saveOnFail=False):
        HostCloudClient.__removeLock.acquire()
        metaDict = {}
        metaDict["maxId"] = maxId
        metaDict["saveOnFail"] = saveOnFail
        metaDict["retry"] = 0
        metaDict["timestamp"] = int(time.time())
        metaDict["command"] = msg
        metaDict["code"] = code
        try:
            self.__packetMetaDict[transId] = metaDict
        finally:
            HostCloudClient.__removeLock.release()

    def resetSSLChannelHandler(self, arg1=None, arg2=None):
        Utils.logInfo("reset ssl socket channel...")
        self.linkDown()

    def recvMessageFromCloudHandler(self, msg, arg2=None):
        if(msg == None):
            return
        Utils.logInfo("->recvMessageFromCloudHandler() %s"%(msg))
        try:
            if isinstance(msg, Ack):
                return self.ackHandler(msg)
            if self.handshakeAck != True:
                Utils.logInfo("Handshake failed, Discard %s"%(msg))
                return
            if isinstance(msg, Command):
                return self.commandHandler(msg)
            if isinstance(msg, RequestResp):
                return self.requestResponseHandler(msg)
        except:
            Utils.logException("recvMessageFromCloudHandler() error:")
            
    def ackHandler(self, ack):
        Utils.logDebug("ackHandler()")
        transId = ack.msgId
        if transId == self.currHandshakeTransId:
            Utils.logInfo("it's hand shake ACK")
            # 收到Handshake ACK
            self.currHandshakeTransId = 0
            self.handshakeAck = True

            try:
                if ack.payload != None:
                    jsonobj = json.loads(ack.payload)
                    timestr = jsonobj.get("timestr", None)
                    sysTimestr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if timestr != None and timestr != sysTimestr:
                        Utils.logInfo("set date time:%s"%(timestr))
                        oscmd = " date -s \"" + timestr + "\" &&hwclock --systohc"
                        os.system(oscmd)
                        Utils.logInfo("set date time:%s success."%(timestr))
            finally:
                pass

            if self.__packetMetaDict.has_key(transId):   # 删除
                self.removeByTransId(transId)
                self.heartbeatTimerHandler(None)
            # Handshake ACK后，以后不用再注册网关

            hostProp = DBManagerHostId().getHost()
            if hostProp.get("registerHost", True) is True:
                hostProp["registerHost"] = False
                oldtimestamp=None
                if hostProp.has_key("timestamp"):
                    oldtimestamp=hostProp.get("timestamp")
                DBManagerHostId().updateHostConfig(hostProp.get("hostId"), hostProp.get("name"), hostProp, oldtimestamp)
            return

        metaDict = None
        if self.__packetMetaDict.has_key(transId):   # 返回并删除
            metaDict = self.removeByTransId(transId)
        if metaDict is None:
            pass
        else:
            maxId = metaDict["maxId"]
            if maxId > 0:
                # 批量备份成功，需要从Backup表删除
                Utils.logInfo("publish PUB_BACKUP_SUCCESS %s"%(maxId))
                # 目前只有水电煤数据才需要删除Backup表中的数据
                pub.sendMessage(GlobalVars.PUB_BACKUP_SUCCESS, arg1="energy", arg2=maxId)
        self.linkUp()
        return
        
    def commandHandler(self, command):
        Utils.logDebug("Rx command from cloud:%s"%(command))
        cmdType = command.cmdType
        # 首先ACK
        transId = command.msgId
        self.cloudClient.sendAck(transId)
        
        if cmdType == GlobalVars.TYPE_CMD_UPGRADE_NOTIFICATION:
            # 云端通知网关开始升级。。。
            jsonobj = json.loads(command.payload)
            fn = jsonobj.get("url", None)
            mdfive = jsonobj.get("md5", None)
            if fn is None or mdfive is None:
                return
            Utils.logInfo("publish PUB_FILE_UPGRADE %s" % fn)
            pub.sendMessage(GlobalVars.PUB_FILE_UPGRADE, url=fn, md5=mdfive)
            # return #不能return，得发送ACK
        elif cmdType == GlobalVars.TYPE_CMD_RESTORE_HOST_PROP:
            # 云端通知网关开始恢复网关属性
            jsonobj = json.loads(command.payload)
            fn = jsonobj.get("url", None)
            mdfive = jsonobj.get("md5", None)
            if fn is None or mdfive is None:
                return
            Utils.logInfo("publish restore_host_prop %s" % fn)
            pub.sendMessage('restore_host_prop', url=fn, md5=mdfive)
        else:
            # 配置命令
            # if cmdType == self.cloudClient.TYPE_CMD_MODIFY_HOST_CONFIG
            # or cmdType == self.cloudClient.TYPE_CMD_READ_HOST_CONFIG:
            # Utils.logDebug("publish PUB_SYS_CONFIG")
            # pub.sendMessage(GlobalVars.PUB_SYS_CONFIG, cmd = command)
            start_exec = time.clock()
            webHandler = WebHandlerBase()
            webHandler.init()
            self.handleCommand(webHandler, command)
            webHandler.uninit()
            webHandler = None
            end_exec = time.clock()
            Utils.logInfo("Cloud command consumes %s seconds"%(str(end_exec-start_exec)))

    def handleCommand(self, webHandler, command):
        Utils.logDebug("handleCommand rx %s "%(command))
        respstr = webHandler.sendCommand(command.cmdType, json.loads(command.payload))
        if respstr != None:
            respObj = json.loads(respstr)
            if respObj != None:
                success = str(respObj.get("ret"))
                # payload = respObj.get("response")
                # if payload != None:
                #     payload = json.dumps(payload)
                # transId = self.getTransId()
                # msgtuple = self.cloudClient.buildCmdResponsePacket(transId, command.msgId, success, respstr)
                payload = respObj.get("response")
                if payload != None:
                    payload = json.dumps(payload)
                transId = self.getTransId()
                msgtuple = self.cloudClient.buildCmdResponsePacket(transId, command.msgId, success, payload)
                self.cloudClient.sendMessage(msgtuple[0], msgtuple[1])
                self.savePacketMeta(transId, 0, msgtuple[0], msgtuple[1], saveOnFail=False)

    def requestResponseHandler(self, resp):
        transId = resp.msgId
        self.cloudClient.sendAck(transId)

        reqType = resp.type
        payload = resp.payload
        # if reqType == GlobalVars.TYPE_REQUEST_FILE_DOWNLOAD:
        #     #文件下载响应
        #     jsonobj = json.loads(payload)
        #     fidict = {}
        #     fidict["filename"] = jsonobj.get("filename", None)
        #     fidict["seq"] = jsonobj.get("sequence", None)
        #     fidict["length"] = jsonobj.get("length", None)
        #     fidict["data"] = jsonobj.get("data", None)
        #     Utils.logInfo("publish PUB_FILE_DOWNLOAD_RESPONSE")
        #     pub.sendMessage(GlobalVars.PUB_FILE_DOWNLOAD_RESPONSE, fileinfoDict = fidict, arg2 = None)

    def restartSSL(self):
        # 重启socket貌似不能解决问题，改为重启本线程。
        # try:
        #     self.cloudClient.restart()    #关闭socket，重新连接
        # except:
        #     Utils.logError("reset socket error ")
        #     ##重启失败，则停止本线程的watchdog，约30秒后系统会重新启动初始化本线程。
        #     # self.stopWatchDog()
        #     Utils.logInfo("publish RESTART cloud...")
        #     pub.sendMessage("restart_thread", threadname="cloud")
        Utils.logInfo("publish RESTART cloud...")
        pub.sendMessage("restart_thread", threadname="cloud")

    def linkDown(self):
        #
        if self.cloudConnected == True:
            Utils.logInfo("publish PUB_HEARBEAT_STATUS down")
            pub.sendMessage(GlobalVars.PUB_HEARBEAT_STATUS, status="down", arg2=None)
            self.cloudConnected = False
            self.restartSSL()

        return self.cloudConnected
    
    def linkUp(self):
        if self.cloudConnected == False:
            Utils.logInfo("publish PUB_HEARBEAT_STATUS up")
            pub.sendMessage(GlobalVars.PUB_HEARBEAT_STATUS, status="up", arg2=None)
            self.cloudConnected = True
        self.heartbeatLostCount = 0
        return self.cloudConnected

if __name__ == '__main__':

    def backupToClould(datatype, detail):
        metaDict={}
        metaDict["type"] = datatype
        metaDict["valueStr"] = detail
        Utils.logDebug("publish PUB_SEND_RTDATA %s"%(datatype))
        pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)

    c1 = HostCloudClient(111)
    c2 = HostCloudClient(112)
    c2.start()
    time.sleep(5)
    #
    # metaDict={}
    # metaDict["type"] = "alarms"
    # metaDict["valueStr"] = "PUB_SEND_RTDATA tests...."
    # Utils.logDebug("publish PUB_SEND_RTDATA alarms")
    # pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)
    #
    # pub.sendMessage(GlobalVars.PUB_CLOUD_HEARTBEAT, arg1=None, arg2=None)
    #
    # ack = Ack()
    # pub.sendMessage("rx_ssl_packet", msg=ack, arg2=None)
    #
    # cmd = Command()
    # cmd.cmdType = 100
    # cmd.msgId="10010"
    # cmd.payload="{}"
    # pub.sendMessage("rx_ssl_packet", msg=cmd, arg2=None)

    ##send heartbeat
    # Utils.logDebug("publish PUB_CLOUD_HEARTBEAT")
    # pub.sendMessage(GlobalVars.PUB_CLOUD_HEARTBEAT, arg1=None, arg2=None)

    ##send device update request
    # value = {"name":"updatedeviceprop","type":"Light1","roomId":"1","addr":"z-007D4501004B12001234","value": {"state":"0"}, "linkaction":{"modeId":"2"}}
    # backupToClould("devices", value)

    # from DBManagerAction import *
    # action = DBManagerAction().getActionByName("晨起", "1")
    # if action != None:
    #     backupToClould("linkaction", action)

    # ##update host config
    # from DBManagerHostId import *
    # value = DBManagerHostId().getHost()
    # if value != None:
    #     backupToClould("hostconfig", value)

    ##send backup energy
    ret = DBManagerBackup().getBackupsByDataType("energy", 1000)
    if(ret != None):
        maxId = ret[0]
        detailsArr = ret[1]
        #发给接口线程
        Utils.logDebug("publish PUB_BACKUP_ENERGY")
        metaDict={}
        metaDict["maxId"] = maxId
        metaDict["details"] = detailsArr
        pub.sendMessage(GlobalVars.PUB_BACKUP_ENERGY, backup=metaDict, arg2 = None)

    # ##remove link action
    # metaDict={}
    # metaDict["type"] = "linkaction"
    # metaDict["op"] = "remove"
    # cond = {}
    # cond["roomId"] = "1"
    # cond["name"] = "晨起"
    # metaDict["valueStr"] = cond
    # Utils.logDebug("publish PUB_SEND_RTDATA")
    # pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)
