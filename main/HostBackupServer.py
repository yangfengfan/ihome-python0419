# -*- coding: utf-8 -*-


import GlobalVars
import Utils
import json
from PacketParser import *
from pubsub import pub
from DBManagerAlarm import *
from DBManagerDevice import *
from DBManagerBackup import *
from DBManagerHistory import *


# 备份策略设计如下：
# 1. 实时数据，如设备状态备份，告警上报，...，直接在接口线程发送，如发送失败，则认为链路断开，保存Socket命令在Backup表里
# 2. 水电煤上报数据，属于定时触发的。在本线程中触发响应的消息后，将从响应的数据库中搜索出所有的数据，通知接口线程发送。
# 3. 如果2中触发时网络是断开的，则直接忽略本次同步，等待下次触发.
# 4. 水电煤数据在备份成功后，将已备份的数据（maxId）从数据库删除
# 5.如果网络恢复，则首先把优先级高的告警同步，然后是实时数据的同步。最后把水电煤数据同步。
class HostBackupServer(ThreadBase):
    __instant = None
    __lock = threading.Lock()
    
    # singleton
    def __new__(cls, arg):
        Utils.logDebug("__new__")
        if HostBackupServer.__instant is None:
            HostBackupServer.__lock.acquire()
            try:
                if HostBackupServer.__instant is None:
                    Utils.logDebug("new HostBackupServer singleton instance.")
                    HostBackupServer.__instant = ThreadBase.__new__(cls)
            finally:
                HostBackupServer.__lock.release()
        return HostBackupServer.__instant

    def __init__(self, threadId):
        self.cloudConnected = False
        self.sendingSocketCommand = False
        ThreadBase.__init__(self, threadId, "HostBackupServer")

    def run(self):
        self.subscribe()
        self.init()
        Utils.logInfo("HostBackupServer is running.")
        try:
            self.que.get()    # 仅起阻塞线程的作用
        except:
            Utils.logException("HostBackupServer loop error")

    def subscribe(self):
        # 将发送失败的socket命令写入到备份表，等待网络恢复后重发
        pub.subscribe(self.saveToBackupHandler, GlobalVars.PUB_SAVE_SOCKET_CMD)    
        # 定时触发备份流程
        pub.subscribe(self.backupStartHandler, GlobalVars.PUB_BACKUP_START)    
        # 备份成功
        pub.subscribe(self.backupSuccessHandler, GlobalVars.PUB_BACKUP_SUCCESS)   
        # 心跳状态（网络状态）
        pub.subscribe(self.heartbeatHandler, GlobalVars.PUB_HEARBEAT_STATUS)
        # 插座的实时数据
        pub.subscribe(self.saveSocketDataHandler, "publish_save_socket_data")
        # 水电煤的实时数据
        pub.subscribe(self.saveEnergyDataHandler, "publish_save_energy_data")
        # 台上净水器、台下净水器、空气净化器数据
        pub.subscribe(self.saveFilterDataHandler, "publish_save_filter_data")
        # 更新网关本地的告警信息
        pub.subscribe(self.updateAlarmUserList, "updateUserList")
        # 更新网关本地的告警信息
        pub.subscribe(self.updateAlarmIsNew, "updateAlarmIsNew")

    def updateAlarmIsNew(self, addr=None, timestamp=None):
        if not addr or not timestamp:
            return
        DBManagerHistory().updateIsNew(addr, timestamp)

    def updateAlarmUserList(self, id_list=None, user_phone=None):
        if not id_list or not user_phone:
            return
        DBManagerHistory().updateUserList(id_list, user_phone)

    def saveSocketDataHandler(self, data, arg2=None):
        if self.cloudConnected is False and GlobalVars.enableBackupWhenLinkdown is False:
            pass
        else:
            DBManagerBackup().saveBackupSocket(data)

    def saveEnergyDataHandler(self, typename, data):

        if self.cloudConnected is False and GlobalVars.enableBackupWhenLinkdown is False:
            pass
        else:
            DBManagerBackup().saveBackupEnergy(typename, data)

    def saveFilterDataHandler(self, devTypeName, data):
        if self.cloudConnected is False and GlobalVars.enableBackupWhenLinkdown is False:
            pass
        else:
            # 写入净水器、空气净化器的数据
            DBManagerBackup().saveBackupFilter(devTypeName, data)

    def saveToBackupHandler(self, backup, arg2=None):
        Utils.logDebug("->saveToBackupHandler() %s"%(backup))
        if self.cloudConnected is False and GlobalVars.enableBackupWhenLinkdown is False:
            pass
        else:
            code = backup["code"]
            command = backup["command"]
            DBManagerBackup().saveBackupCommand(code, command)

    def heartbeatHandler(self, status, arg2=None):  # status: "up", "down"
        Utils.logDebug("->heartbeatHandler() %s" % status)
        if status == "up":
            if(self.cloudConnected != True):
                self.cloudConnected = True
                self.resendSocketCommand()
        else:
            self.cloudConnected = False

    def backupSuccessHandler(self, arg1, arg2):
        Utils.logDebug("->backupSuccessHandler() %s,%s"%(arg1, arg2))
        datatype = arg1
        maxId = arg2
        # 删除Backup表中相应的数据
        DBManagerBackup().deleteBackupsByDataType(datatype, maxId)
        # 继续。。。
        if datatype == "energy":
            self.backupEnergy()

    def resendSocketCommand(self, limit=None):
        Utils.logDebug("->resendSocketCommand()")
        if self.sendingSocketCommand == True:
            return

        while True:
            Utils.logInfo('get one socket command from db and re-send.')
            self.sendingSocketCommand = True
            try:
                time.sleep(1)
                commandDict = DBManagerBackup().getOneSocketCommand()
                if commandDict == None or commandDict.has_key("keyId") == False:
                    Utils.logInfo("not found Socket command in backup.")
                    self.sendingSocketCommand = False
                    break
                # 发给接口线程
                Utils.logInfo("delete backup record %s"%(commandDict["keyId"]))
                DBManagerBackup().deleteBackupsById(commandDict["keyId"])
                Utils.logInfo("publish PUB_RESEND_SOCKET %s"%(commandDict['command']))
                pub.sendMessage(GlobalVars.PUB_RESEND_SOCKET, backup=commandDict, arg2 = None)
            except:
                Utils.logException('Backup Server exception.')
                pass

    def filter0(self, arr):
        Utils.logInfo("->filter0()")
        ret = []
        for tmp in arr:
            Utils.logInfo("->filter0() 1")
            if tmp.get('type', None) in [DEVTYPENAME_TABLE_WATER_FILTER, DEVTYPENAME_AIR_FILTER]:
                # 净水器和空气净化器不过滤
                ret.append(tmp)
                continue
            tmpvalue = tmp.get('value', None)
            if tmpvalue is None:
                continue
            energyv = tmpvalue.get('energy', None)
            if energyv is None:
                continue
            energyf = float(energyv)
            if energyf <= 0:
                continue
            ret.append(tmp)
        return ret

    def backupEnergy(self, ret=None):  # ret 为能耗数据
        Utils.logDebug("->backupEnergy()")
        if ret is None:
            ret = DBManagerBackup().getBackupsByDataType("energy", 50)
        # else:
        if ret is not None:
            maxId = ret[0]
            # detailsArr = ret[1]
            # 过滤掉 'energy'='0'的
            detailsArr = self.filter0(ret[1])
            # 发给接口线程
            Utils.logDebug("publish PUB_BACKUP_ENERGY")
            metaDict={}
            metaDict["maxId"] = maxId
            metaDict["details"] = detailsArr
            pub.sendMessage(GlobalVars.PUB_BACKUP_ENERGY, backup=metaDict, arg2=None)

    def backupDB(self):
        Utils.logDebug("->backupDB() do nothing.")
        ##do nothing
        pass
    
    # 定时触发
    def backupStartHandler(self, backup, arg2):
        Utils.logDebug("->backupStartHandler() %s" % backup)

        cmd = backup["type"]
        ret = None
        if cmd == "energy":
            # TODO，不管网络是否断开，先保存一条能耗记录到history表
            ret = DBManagerBackup().getBackupsByDataType("energy", 50)
            if ret is not None:
                maxId = ret[0]
                # detailsArr = ret[1]
                # 过滤掉 'energy'='0'的
                detailsArr = self.filter0(ret[1])
                for item in detailsArr:
                    DBManagerHistory().saveHistoricalEnergy(item)

        if self.cloudConnected is False:
            # 网络断开，不触发备份
            return
        
        # 首先查看是否有socket命令等待重发？
        self.resendSocketCommand()
        
        cmd = backup["type"]
        if cmd == "energy":
            self.backupEnergy(ret)
        elif cmd == "database":
            self.backupDB()
        else:
            Utils.logError("backupStartHandler() error backup. %s" % backup)
        return
    
if __name__ == '__main__':
    c1 = HostBackupServer(101)
    c2 = HostBackupServer(102)
    c2.start()
    time.sleep(1)
    
    metaDict = {}
    metaDict["code"] = 300
    metaDict["command"] = "socket command 300"
    Utils.logDebug("publish PUB_SAVE_SOCKET_CMD")
    pub.sendMessage(GlobalVars.PUB_SAVE_SOCKET_CMD, backup=metaDict, arg2=None)
    
    pub.sendMessage(GlobalVars.PUB_HEARBEAT_STATUS, status="up", arg2=None)

    commandDict = DBManagerBackup().getOneSocketCommand()
    if commandDict == None or commandDict.has_key("keyId") == False:
        print "==============PUB_SAVE_SOCKET_CMD SUCCESS==========="
    else:
        print "!!!!!!!!!!!!!!!!PUB_SAVE_SOCKET_CMD FAILED!!!!!!!!!!!"
    
    dbackup = DBManagerBackup()
    e={"addr":"z-347D4501004B12001233","value":{"state":"0","coeff":"1"}}
    dbackup.saveBackupEnergy("water", e)
    e2={"addr":"z-347D4501004B12001234","value":{"state":"1","coeff":"0"}}
    dbackup.saveBackupEnergy("gas", e2)
    
    metaDict={}
    metaDict["type"] = "energy"
    Utils.logDebug("publish PUB_BACKUP_START energy")
    pub.sendMessage(GlobalVars.PUB_BACKUP_START, backup=metaDict, arg2=None)
    
    Utils.logDebug("publish PUB_BACKUP_SUCCESS")
    ##目前只有水电煤数据才需要删除Backup表中的数据
    pub.sendMessage(GlobalVars.PUB_BACKUP_SUCCESS, arg1="energy", arg2=1200)
    
    energy = dbackup.getBackupsByDataType("energy")
    if energy is None:
        print "==============PUB_BACKUP_SUCCESS SUCCESS==========="
    else:
        print "!!!!!!!!!!!!!!!!PUB_BACKUP_SUCCESS FAILED!!!!!!!!!!!"