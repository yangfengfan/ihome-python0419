# -*- coding: utf-8 -*-


from SocketThreadBase import *
import GlobalVars
import Utils
import json
from PacketParser import *
from pubsub import pub
from DBManagerAlarm import *
from DBManagerDevice import *
from DBManagerPannelRate import *
from BoerCloud import *
from SocketHandlerServer import *
import random
from DBManagerPannelRateZxh import *
from DBManagerPannelRateZxl import *


class HostControlServer(SocketThreadBase):
    __instant = None
    __lock = threading.Lock()
    __cmdlock = threading.Lock()
    __cfglock = threading.Lock()
    __quitlock = threading.Lock()

    # singleton
    def __new__(self, arg):
        Utils.logDebug("__new__")
        if (HostControlServer.__instant == None):
            HostControlServer.__lock.acquire()
            try:
                if (HostControlServer.__instant == None):
                    Utils.logDebug("new HostControlServer singleton instance.")
                    HostControlServer.__instant = SocketThreadBase.__new__(self)
            finally:
                HostControlServer.__lock.release()
        return HostControlServer.__instant

    def __init__(self, threadId):
        SocketThreadBase.__init__(self, threadId, "HostControlServer")
        self.destAddress = ("127.0.0.1", 8899)
        self.packParser = PacketParser()
        self.waitingCommands = []
        self.waitingConfigs = []
        self.waitingQuitNetworks = []  # 退网命令队列

    def backupToClould(self, datatype, detail):
        metaDict = {}
        metaDict["type"] = datatype
        metaDict["valueStr"] = detail
        Utils.logDebug("publish PUB_SEND_RTDATA %s" % (datatype))
        pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)

    # def startHandlerServer(self):
    #     host = "localhost"
    #     port = 6789
    #     addr = (host, port)
    #     # self.handlerServer = ThreadingTCPServer(addr, SocketHandlerServer)
    #     # self.handlerServer.serve_forever()
    #     self.handlerServer = SocketHandlerServer(addr)
    #     self.handlerServer.start()

    def run(self):
        self.init()  # call super.init()

        self.subscribe()

        Utils.logInfo("HostControlServer is running.")
        # Utils.logDebug("SocketHandlerServer is running.")
        while not self.stopped:
            try:

                self.que.get()  # 仅起阻塞线程的作用
                self.sendCommand2Driver()
                self.sendConfig2Driver()
                self.sendQuitNetwork2Driver()
            except:
                Utils.logException('HostControlServer exception.')

    def subscribe(self):
        pub.subscribe(self.controlHandler, GlobalVars.PUB_CONTROL_DEVICE)
        # pub.subscribe(self.alarmHandler, GlobalVars.PUB_ALARM)
        pub.subscribe(self.syncHgcConfig, "syncHgcConfig")
        pub.subscribe(self.syncHgcDevices, "syncHgcDevices")
        pub.subscribe(self.syncHgcTime, "syncHgcTime")
        pub.subscribe(self.syncFloorHeating, "syncFloorHeating")

    def sendCommand2Driver(self):
        Utils.logInfo("->sendCommand2Driver()")
        while True:
            try:
                ctrlObj = self.removeFromWaitingCmdlist()
                if ctrlObj == None:
                    break
                Utils.logInfo("sendCommand2Driver() %s" % (ctrlObj))
                start_exec = time.clock()
                self.controlDevice(ctrlObj)
                end_exec = time.clock()
                Utils.logInfo("Driver handles this command consumes %s seconds" % str(end_exec - start_exec))
            except:
                Utils.logException('sendCommand2Driver.')

    def sendConfig2Driver(self):
        Utils.logInfo("->sendConfig2Driver()")
        while True:
            try:
                cfgObj = self.removeFromWaitingConfiglist()
                if cfgObj == None:
                    break
                Utils.logInfo("sendConfig2Driver() %s" % (cfgObj))
                configType = cfgObj.get('type', None)
                if configType == None:
                    continue
                start_exec = time.clock()
                if configType == 'link_dev':
                    ##设备关联配置
                    self.configLinkDevice(cfgObj.get('config', None))
                elif configType == 'hgc_config_success':
                    ##中控设备组网成功
                    self.configHGCsuccess(cfgObj.get('addr', None))
                end_exec = time.clock()
                Utils.logInfo("Driver handles this command consumes %s seconds" % (str(end_exec - start_exec)))
            except:
                Utils.logException('sendConfig2Driver.')
                pass

    def sendQuitNetwork2Driver(self):
        Utils.logDebug("->sendQuitNetwork2Driver")
        while True:
            try:
                quitNetworkCmd = self.removeFromWaitingQuitNetworks()
                Utils.logInfo("send quit network cmd: %s" % str(quitNetworkCmd))  # info
                if quitNetworkCmd is None:
                    break
                start_exec = time.clock()
                self.sendQuitNetworking(quitNetworkCmd)
                end_exec = time.clock()
                Utils.logInfo("Driver handles this quit network cmd consumes %s seconds" % (str(end_exec - start_exec)))
            except Exception:
                Utils.logError("sendQuitNetwork2Driver failed...")

    # json=[{"name":"device1","type":"light","room":"room1","addr":"z-11111111"}]
    def controlHandler(self, cmd, controls=None):
        Utils.logDebug("->controlHandler %s,%s" % (cmd, controls))
        if (cmd is None or cmd == ""):
            Utils.logWarn("invalid alarms request.")
            return
        try:
            if (cmd == "controlDevice"):
                self.controlDevices(controls)
            if (cmd == "configDevice"):
                self.configDevices(controls)
            if cmd == "quitNetwork":
                self.quitNetwork(controls)  # 发送退网命令
        except:
            Utils.logException("controlHandler error,")

    # def alarmHandler(self, cmd, alarms=None):
    #     Utils.logDebug("->alarmHandler %s,%s"%(cmd,alarms))
    #     if(cmd is None or cmd == ""):
    #         Utils.logWarn("invalid alarms request.")
    #         return
    #     try:
    #         if(cmd == "confirmAlarms"):
    #             self.confirmAlarms(alarms)
    #     except:
    #         Utils.logError("alarmHandler error,")

    # [{"name":"device1","type":"light","room":"room1","addr":"z-11111111"}]
    def controlDevices(self, ctrlsObj):
        Utils.logDebug("->controlDevices:%s" % (ctrlsObj))
        HostControlServer.__cmdlock.acquire()
        try:
            if isinstance(ctrlsObj, dict):
                self.add2WaitingCmdlist(ctrlsObj)
            else:
                for ctrlObj in ctrlsObj:
                    # self.controlDevice(ctrlObj)
                    self.add2WaitingCmdlist(ctrlObj)
        finally:
            HostControlServer.__cmdlock.release()
        self.que.put('0')

    # [{"addr":"xxxx", "name":"dev1", "type":"type1"},{...}, ..., {...}]
    # 或者 {"addr": "xxxx", "name": "dev1", "type": "type1"}
    # 退网
    def quitNetwork(self, ctrlsObj):
        Utils.logDebug("->quitNetwork:%s" % (ctrlsObj))
        HostControlServer.__cmdlock.acquire()
        try:
            if isinstance(ctrlsObj, dict):
                self.waitingQuitNetworks.append(ctrlsObj)
            else:
                for ctrlObj in ctrlsObj:
                    self.waitingQuitNetworks.append(ctrlObj)
        finally:
            HostControlServer.__cmdlock.release()
        self.que.put('0')

    def configDevices(self, param):
        Utils.logDebug("->configDevices:%s" % (param))

        configType = param.get('type', None)
        if configType == None:
            return

        if configType == 'link_dev':
            configObjs = param.get('configs', None)
            for configObj in configObjs:
                cfg = {}
                cfg['type'] = configType
                cfg['config'] = json.dumps(configObj)
                self.add2WaitingConfiglist(cfg)
            self.que.put('0')
        elif configType == 'hgc_config_success':
            self.add2WaitingConfiglist(param)
            self.que.put('0')

    ##加入等待队列
    ##线程安全
    def add2WaitingCmdlist(self, deviceVal):
        Utils.logInfo('add2WaitingCmdlist %d,%s' % (len(self.waitingConfigs), deviceVal))
        # kiddingCmd = False  ## 快速切换设备状态，如“全局模式”，最开始未执行的指令可以被覆盖。
        # for cmd in self.waitingCommands:
        #     try:
        #         cmdDevType = cmd.get('type')
        #         cmdDevAddr = cmd.get('addr')
        #         cmdValue = cmd.get('value')
        #         curDevType = deviceVal.get('type')
        #         curDevAddr = deviceVal.get('addr')
        #         curValue = deviceVal.get('value')
        #         if cmdDevType == curDevType and cmdDevAddr == curDevAddr:
        #             kiddingCmd = True
        #             for cmdKey in cmdValue.keys():
        #                 if curValue.has_key(cmdKey) == False:
        #                     kiddingCmd = False
        #             if kiddingCmd == True:
        #                 Utils.logInfo('found duplicated command...')
        #                 break
        #     except:
        #         kiddingCmd = False
        # ##如果发现是重复指令，把前面的指令覆盖
        # if kiddingCmd == True:
        #     Utils.logInfo('remove duplicated command...count:%d'%(len(self.waitingCommands)))
        #     self.waitingCommands.remove(cmd)
        #     Utils.logInfo('remove duplicated command...success:%d'%(len(self.waitingCommands)))
        self.waitingCommands.append(deviceVal)

    def add2WaitingConfiglist(self, config):
        HostControlServer.__cfglock.acquire()
        Utils.logInfo('add2WaitingConfiglist %d,%s' % (len(self.waitingConfigs), config))
        try:
            self.waitingConfigs.append(config)
        finally:
            HostControlServer.__cfglock.release()

    # 从等待队列删除
    # 线程安全
    def removeFromWaitingCmdlist(self):
        deviceVal = None
        HostControlServer.__cmdlock.acquire()
        try:
            if len(self.waitingCommands) > 0:
                deviceVal = self.waitingCommands[0]
                del self.waitingCommands[0]
                Utils.logInfo('pop first command element %d,%s' % (len(self.waitingCommands), deviceVal))
        finally:
            HostControlServer.__cmdlock.release()
            return deviceVal

    def removeFromWaitingConfiglist(self):
        config = None
        HostControlServer.__cfglock.acquire()
        try:
            if len(self.waitingConfigs) > 0:
                config = self.waitingConfigs[0]
                del self.waitingConfigs[0]
                Utils.logInfo('pop first config element %d,%s' % (len(self.waitingConfigs), config))
        finally:
            HostControlServer.__cfglock.release()
            return config

    def removeFromWaitingQuitNetworks(self):
        quitNetworkCmd = None
        HostControlServer.__quitlock.acquire()
        try:
            if len(self.waitingQuitNetworks) > 0:
                quitNetworkCmd = self.waitingQuitNetworks[0]
                del self.waitingQuitNetworks[0]
                Utils.logInfo("pop first quit network element %d, %s" % (len(self.waitingQuitNetworks), quitNetworkCmd))
        finally:
            HostControlServer.__quitlock.release()
            return quitNetworkCmd

    def checkValue(self, curValue, devaddr):
        same = False
        # devaddr = deviceVal.get("addr", None)
        # Utils.logInfo('.....1 %s'%(devaddr))
        if devaddr != None and curValue != None:
            try:
                devItem = DBManagerDevice().getDeviceByDevId(devaddr)
                #     Utils.logInfo('.....2 %s'%(devItem))
                if (devItem != None):
                    valueInDb = devItem.get("value", None)
                    #         Utils.logInfo('.....3 %s'%(value))
                    #         Utils.logInfo('.....4 %s'%(valueInDb))
                    if valueInDb != None:
                        same = True
                        for key in curValue.keys():
                            if 'time' not in key:
                                tmp = valueInDb.get(key, None)
                                if tmp == None or str(tmp) != str(curValue.get(key, None)):
                                    ##不一致
                                    same = False
                                    break
            except:
                same = False

        Utils.logInfo('control server checkValue: same:%s' % (same))
        return same

    # 同步中控时间
    def syncHgcTime(self, buffer):

        if buffer is None:
            Utils.logWarn("invalid syncHgcTime request.")
            return

        result = self.sendBuffer2(buffer)

        if (result > 0):
            Utils.logInfo("success to sync HGC time")
            Utils.logHex("success to sync HGC time to %s" % (self.destAddress[0]), buffer)
        else:
            Utils.logInfo("failed to sync HGC time")
        return 0

    # 同步中控配置
    def syncHgcConfig(self, config, isConfigured):
        if config is None:
            Utils.logWarn("invalid syncHgcConfig request.")
            return
        buffer = self.packParser.buildSyncHgcConfigPack(config, isConfigured)
        if (buffer == None):
            Utils.logError("sync HGC config error!!!")
            return

        result = self.sendBuffer2(buffer)

        if (result > 0):
            Utils.logInfo("success to sync HGC config")
            Utils.logHex("success to sync HGC config to %s" % (self.destAddress[0]), buffer)
        else:
            Utils.logInfo("failed to sync HGC config")
        return 0

    # 同步中控上设备的名字或状态
    def syncHgcDevices(self, sparam):

        if sparam is None:
            Utils.logWarn("invalid syncHgcDevices request.")
            return

        buffer_list = self.packParser.buildSyncHgcDevPack(sparam)
        if buffer_list is None or len(buffer_list) == 0:
            Utils.logWarn("buffer_list is None or empty !!!")
            return

        result_list = []
        for buffer in buffer_list:
            result = self.sendBuffer2(buffer)
            result_list.append(result)

        for result in result_list:
            if (result > 0):
                Utils.logInfo("success to sync HGC devices")
                Utils.logHex("success to sync HGC devices to %s" % (self.destAddress[0]), buffer)
            else:
                Utils.logInfo("failed to sync HGC devices")
        return 0

    # 同步地暖的定时任务信息
    def syncFloorHeating(self, sparam):

        Utils.logInfo("sync Floor Heating: %s" % sparam)

        if sparam is None:
            Utils.logWarn("invalid syncFloorHeating request.")
            return

        buffer_list = self.packParser.buildSyncFLoorHeatingPack(sparam)
        if buffer_list is None or len(buffer_list) == 0:
            Utils.logWarn("buffer_list is None or empty !!!")
            return

        result_list = []
        for buffer in buffer_list:
            result = self.sendBuffer2(buffer)
            result_list.append(result)

        for result in result_list:
            if (result > 0):
                Utils.logInfo("success to sync FloorHeating devices")
                Utils.logHex("success to sync FloorHeating devices to %s" % (self.destAddress[0]), buffer)
            else:
                Utils.logInfo("failed to sync FloorHeating devices")
        return 0

    # {"name":"device1","type":"light","room":"room1","addr":"z-11111111"}
    def controlDevice(self, deviceVal):
        Utils.logError("->controlDevice:%s" % (deviceVal))
        try:
            devType = deviceVal.get("type", "")
            devAddr = deviceVal.get("addr", "")
            value = deviceVal.get("value", {})
        except:
            Utils.logException("device control command: %s" % (deviceVal))
            return

        # 新的红外控制命令
        extra_cmd = deviceVal.get("extraCmd", None)
        if extra_cmd == "newInfrared":
            buffer_list = self.packParser.buildInfraredControlPack(deviceVal)
            if buffer_list:
                for buffer in buffer_list:
                    result = self.sendBuffer2(buffer)
                    if result > 0:
                        Utils.logInfo("success to send control mac: %s" % devAddr)
                        Utils.logHex("success to send control to %s" % (self.destAddress[0]), buffer)
            else:
                Utils.logError("===>fail to build buffer for infrared device: %s" % devAddr)
            return 0

        # 中央空调需要将其地址长度增加到20
        if devType == DEVTYNAME_CENTRAL_AIRCONDITION:
            if devAddr[:4] == "CAC_":
                devAddr = devAddr[4:]
            oldAddr = str(devAddr)
            newAddr = ""
            for i in range(0, (20 - len(oldAddr))):
                newAddr += "0"
            newAddr = oldAddr + newAddr
            deviceVal["addr"] = newAddr

        # 控制预处理：如果是AjustLight，则需要补足另外一个值
        if (devType == DEVTYPENAME_LIGHTAJUST):
            try:
                # curDevValStr= globalVars.localRedis.hget(globalVars.hostKeyData, devAddr)
                curDevValStr = DBManagerDevice().getDeviceByDevId(devAddr)
                if curDevValStr == None:
                    ##新添加的设备
                    pass
                else:
                    # curDevVal = json.loads(curDevValStr)
                    # 此处处理渐变时间方式与ByDelos不同，家卫士APP与ByDelos上设置渐变时间的接口不同
                    curDevVal = curDevValStr
                    curDevice = DBManagerDeviceProp().getDeviceByAddr(devAddr)[0]
                    if (curDevVal is not None):
                        curValue = curDevVal.get("value", {})
                        curState = curValue.get("state", "0")
                        curCoeff = curValue.get("coeff", "0")
                        curLightingTime = curDevice.get("lightingTime", "0")

                        ctrlState = value.get("state", "")
                        ctrlCoeff = value.get("coeff", "")
                        ctrlLightingTime = value.get("lightingTime", "")

                        if (ctrlCoeff == ""):
                            ctrlCoeff = curCoeff
                        if (ctrlState == ""):
                            ctrlState = curState
                        if ctrlLightingTime == "":
                            ctrlLightingTime = curLightingTime

                        value["state"] = ctrlState
                        value["coeff"] = ctrlCoeff
                        value["lightingTime"] = ctrlLightingTime
                        deviceVal["value"] = value
            except:
                Utils.logException("control, pre process failed")

        # 检查设备当前状态，如果和目的的状态一致，则无需下发给驱动
        # 以免减少zigbee的压力
        # same = self.checkValue(deviceVal.get('value', None), devAddr)
        # if same == True:
        #     Utils.logInfo("%s status not changed."%(devAddr))
        #     return

        # 关闭投影仪需要发送2次指令
        if devType == DEVTYPENAME_PROJECTOR and value.get("state") == "2":
            Utils.logInfo("Shutdown projector, 1st command.")

            # delay = range(0, 1000000)
            # delay.sort(reverse=True)
            # del delay
            time.sleep(0.5)

            buffer = self.packParser.buildControlReqestPack(deviceVal)
            ret = self.sendBuffer2(buffer)
            if ret > 0:
                Utils.logInfo("success to send control mac: %s" % devAddr)
                Utils.logInfo("Now 2nd command.")

        # 门窗磁和幕帘由于使用纽扣电池供电，平时出于深度睡眠状态以节能并且一直出于设防状态
        # 当app发送改动设置时网关程序主动更新设备状态表中撤防、布防状态，设备端接收指令特殊处理不会改变状态
        # 此操作是为了兼容旧的存在传感器
        if devType in [DEVTYPENAME_CURTAIN_SENSOR, DEVTYPENAME_GSM, DEVTYPENAME_EXIST_SENSOR]:
            statusDetail = DBManagerDevice().getDeviceByDevAddrAndType(devAddr, devType)
            # {u'deviceName': u'\u95e8\u7a97\u78c1', u'addr': u'22642F04004B12000000', u'value': {u'set': u'0'}, u'roomName': u'\u5ba2\u5385', u'type': u'Gsm', u'areaName': u'\u65b0\u533a\u57df'}
            valueObj = {}
            if statusDetail is None:
                nowTime = int(time.time())
                deviceName = deviceVal.get("deviceName", "")
                statusDetail = {"time": nowTime, "name": deviceName, "type": devType,
                                "addr": devAddr}  # 如果是None，将statusDetail初始化为新的字典
                valueObj["set"] = deviceVal.get("value").get("set", "1")
            else:
                valueObj = statusDetail.get("value", {})
                valueObj["set"] = deviceVal.get("value").get("set", "1")
            statusDetail["value"] = valueObj
            # statusDetail["name"] = deviceVal.get("deviceName")
            DBManagerDevice().saveDeviceStatus(statusDetail)
            if devType != DEVTYPENAME_EXIST_SENSOR:  # 如果存在传感器为了兼容老设备需要将控制命令发出去，幕帘及门窗磁不需要下发命令
                return

        # 485协议接入的背景音乐设备
        if devType == DEVTYPENAME_AUDIO:
            audio_brand = deviceVal.get("brand", None)
            cmd = value.get("cmd", None)
            if audio_brand in ["Levoice", "Wise485"] and cmd == "5":  # 当背景音乐是音丽士并且是指定歌曲是将指定歌曲写入设备属性用于模式触发
                audio_prop = DBManagerDeviceProp().getDeviceByAddr(devAddr)[0]
                currNo = value.get("data", "1")
                volume = value.get("volume", "5")
                setSong = audio_prop.get("setSong", None)
                modeId = value.get('modeId', None)

                if volume == "0":
                    volume = "5"

                if modeId:
                    song_dict = audio_prop.get("songDict", {})
                    song_info = {"setSong": currNo, "setVolume": volume}
                    song_dict["mode_{}".format(modeId)] = song_info
                    audio_prop["songDict"] = song_dict
                elif setSong is not None and currNo != setSong:  # 当指定歌曲和当前数据库中已指定歌曲不同时才重新设定:
                    audio_prop["setSong"] = currNo
                    audio_prop["setVolume"] = volume
                DBManagerDeviceProp().saveDeviceProperty(audio_prop)  # 将指定的歌曲和音量存入属性作为指定曲目和指定音量，模式触发时使用

                # 调光灯控制面板
        if devType == DEVTYPENAME_LIGHTAJUST_PANNEL:
            try:
                # Utils.logError("----controlDevice----DEVTYPENAME_LIGHTAJUST_PANNEL--deviceVal------%s" % deviceVal)
                # Utils.logError("----controlDevice----DEVTYPENAME_LIGHTAJUST_PANNEL--devAddr------%s" % devAddr)
                props = DBManagerDeviceProp().getDeviceByDevAddrAndType(devAddr, devType)
                # Utils.logError("----controlDevice----DEVTYPENAME_LIGHTAJUST_PANNEL--props------%s" % props)
                link_only_one_switch = props.get("linkOnlyOneSwitch", None)
                # Utils.logError("------link_only_one_switch------%s" % link_only_one_switch)
                if link_only_one_switch is not None:
                    device_status = link_only_one_switch.get("deviceStatus", None)
                    if device_status is not None:
                        address_switch = device_status.get("addr", None)
                        # Utils.logError("------link_only_one_switch---address_switch---%s" % address_switch)
                        linked = device_status.get("linked", {})
                        link1 = linked.get("link1", None)
                        link2 = linked.get("link2", None)
                        link3 = linked.get("link3", None)
                        link4 = linked.get("link4", None)
                        light_key = ""
                        if link1 is not None and int(link1) == 1:
                            light_key = "state"
                        elif link2 is not None and int(link2) == 1:
                            light_key = "state2"
                        elif link3 is not None and int(link3) == 1:
                            light_key = "state3"
                        elif link4 is not None and int(link4) == 1:
                            light_key = "state4"
                        # Utils.logError("------cur_switch--light_key---%s" % light_key)
                        cur_switch = DBManagerDevice().getDeviceByDevId(address_switch)
                        # Utils.logError("------cur_switch------%s" % cur_switch)
                        if cur_switch is not None:
                            cur_name = cur_switch.get("name", None)
                            cur_type = cur_switch.get("type", None)
                            value_switch = cur_switch.get("value", {})
                            state_switch = value_switch.get(light_key, 0)
                            if state_switch == 0:
                                devicesToCtrol = []
                                singleValue = {}
                                singleValue[light_key] = "1"
                                dev_control = {"name": cur_name, "addr": address_switch, "value": singleValue,
                                               "type": cur_type}
                                devicesToCtrol.append(dev_control)
                                # Utils.logError("------controlDevice devicesToCtrol------%s" % devicesToCtrol)
                                pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice",
                                                controls=devicesToCtrol)
                                time.sleep(1)  # 控制开关后延时1秒等待开关开启

                # Utils.logError("------55555555555555555555555555555555555555555555555555------")
                state = int(value.get("state", 0))
                if state == 1:
                    link_light_sensor = props.get("linkLightSensor", None)
                    if link_light_sensor is not None:
                        device_status = link_light_sensor.get("deviceStatus", None)
                        if device_status is not None:
                            ray_address = device_status.get("addr", None)
                            ray_normal_low = 100
                            ray_normal_high = 1000
                            adjust_type = 0
                            zx_file = '/ihome/etc/zx'
                            if os.path.exists(zx_file) == True:
                                adjust_type = 1
                            cur_ray = DBManagerDevice().getDeviceByDevId(ray_address)
                            value_ray = cur_ray.get("value", {})
                            ray = value_ray.get("ray", None)
                            Utils.logError("ray_sense_value is: %s" % ray)
                            global brightness, colortemp
                            if ray is not None:
                                if ray < ray_normal_low:
                                    if adjust_type == 0:
                                        time_int = time.localtime().tm_hour * 100 + time.localtime().tm_min  # 平常表
                                        brightness, colortemp = DBManagerPannelRate().queryByTime(time_int)
                                    else:
                                        time_int = (time.localtime().tm_min % 2) * 100 + time.localtime().tm_sec
                                        brightness, colortemp = DBManagerPannelRateZxh().queryByTime(time_int)
                                elif ray > ray_normal_high:
                                    colortemp = 0
                                    brightness = 0
                                else:
                                    if adjust_type == 0:
                                        time_int = time.localtime().tm_hour * 100 + time.localtime().tm_min  # 平常表
                                        brightness, colortemp = DBManagerPannelRate().queryByTime(time_int)
                                    else:
                                        time_int = (time.localtime().tm_min % 2) * 100 + time.localtime().tm_sec
                                        brightness, colortemp = DBManagerPannelRateZxl().queryByTime(time_int)
                    else:  # 无光感绑定时
                        time_int = time.localtime().tm_hour * 100 + time.localtime().tm_min
                        brightness, colortemp = DBManagerPannelRate().queryByTime(time_int)
                    value['coldRate'] = colortemp
                    value['warmRate'] = brightness
                    deviceVal['value'] = value
                    Utils.logError("colortemp is: %s" % colortemp)
                    Utils.logError("brightness is: %s" % brightness)
                Utils.logError("--------------------------------------------------deviceVal: %s" % deviceVal)
            except:
                Utils.logError('Error when read zx')

                # 节律模式
                # addrRaySense = deviceVal.get("addrRaySense");
                # if (addrRaySense == None):
                #     time_int = time.localtime().tm_hour * 100 + time.localtime().tm_min
                #     brightness, colortemp = DBManagerPannelRate().queryByTime(time_int)
                #     value['coldRate'] = colortemp
                #     value['warmRate'] = brightness
                #     deviceVal['value'] = value
                # else:# 检测光感器数值范围
                #     Utils.logError("RaySense is exist")
                #     # 光感数值范围在2000-4000是正常范围,小于2000时候要开灯;大于4000的时候要判断是否有灯开着,有灯的情况下要关灯或者换其他灯
                #     rayNormalLow = 2000
                #     rayNormalHigh = 4000
                #     raySenseValue = 1400
                #     step = 500
                #     if (raySenseValue < rayNormalLow):#开灯3
                #         value["state"] = 3
                #         deviceVal['value'] = value
                #         self.controlDevice(deviceVal)
                #     if (raySenseValue > rayNormalHigh):#保持不变或者有灯开着情况要关灯或者换灯开
                #         value["state"] = 6
                #         deviceVal['value'] = value
                #         self.controlDevice(deviceVal)
                #     if (raySenseValue < 5000):
                #         raySenseValue = raySenseValue + step
                #     else:
                #         raySenseValue = raySenseValue - 4000
                #     Utils.logError("raySenseValue is: %d" % (raySenseValue))

        # 地暖的控制指令单独拼装
        # if devType == DEVTYPENAME_FLOOR_HEATING:
        #     buffer = self.packParser.buildControlFLoorHeatingPack(deviceVal)
        # else:
        #     buffer = self.packParser.buildControlReqestPack(deviceVal)
        buffer = self.packParser.buildControlReqestPack(deviceVal)  # 地暖该用485协议接入
        Utils.logError("----control---deviceVal-------%s--------" % deviceVal)
        if (buffer == None):
            # Utils.logError("recv device control command: %s, cannot build buffer" % deviceVal)
            return

        result = self.sendBuffer2(buffer)

        if (result > 0):
            Utils.logInfo("success to send control mac: %s" % (devAddr))
            Utils.logHex("success to send control to %s" % (self.destAddress[0]), buffer)
            # 更新缓存值，避免控制太慢
            self.updateLocalDevCacheValue(deviceVal)

            # #对设备控制类，暂时不关心返回的结果，默认控制成功
            # start_exec = time.clock()
            # recvBuffer = self.receiveBufferFrom()
            # # recvBuffer = None
            # end_exec = time.clock()
            # Utils.logInfo("rx buffer from driver consumes %s seconds"%(str(end_exec-start_exec)))
            # if(recvBuffer != None and len(recvBuffer) > 0):
            #     devicesData = self.packParser.parseRecvData(recvBuffer)
            #     if(devicesData == None or len(devicesData) <= 0):
            #         Utils.logInfo("recv control response len(%d),but no device data"%(len(recvBuffer)))
            #     else:
            #         #更新云上缓存（如果是来自云端的控制的话）
            #         # if(self.isFromCloud == True): #如果是来自云上的控制命令，需要更新
            #         #     self.updateCloudDevCacheValue(newDevValStr)
            #         # devStatusStr = json.dumps(deviceVal)
            #         self.backupToClould("devicestatus", deviceVal)
            #         for deviceData in devicesData:
            #             retDevAddr =  deviceData.get("addr","")
            #             if(retDevAddr != ""):
            #                 retDevStr = json.dumps(deviceData)
            #                 Utils.logDebug("write contrl ret device data of(%s): %s"%(retDevAddr, retDevStr))
            # else:
            #     Utils.logInfo("do not recv control response(%s)"%(devAddr))
        else:
            Utils.logInfo("failed to send control mac: %s" % (devAddr))
            Utils.logHex("failed to send control to %s" % (self.destAddress[0]), buffer)

        Utils.logDebug("end to control device:%s" % (deviceVal))
        return 0

    # 发送退网命令
    # {"addr": "xxxxx", "name": "dev1", "type": "type1"}
    def sendQuitNetworking(self, devParam):
        Utils.logDebug("->sendQuitNetworking param: %s" % str(devParam))
        try:
            buffer = self.packParser.buildQuitNetworRequestPack(devParam)
            if buffer is None:
                Utils.logError("sendQuitNetworking error, device mac is none.")
                return
            self.sendBuffer2(buffer)
        except Exception:
            Utils.logError("sendQuitNetworking failed...devParam: %s" % str(devParam))

    def configHGCsuccess(self, addr):
        Utils.logDebug("->configHGCsuccess %s" % (addr))

        buffer = self.packParser.buildConfigHGCsuccessPack(addr)
        if (buffer == None):
            Utils.logError("recv configHGCsuccess command: %s, cannot build buffer" % (addr))
            return

        result = self.sendBuffer2(buffer)
        if (result > 0):
            # self.updateLinkDeviceInDb(config)
            pass
        else:
            Utils.logError("failed to send configHGCsuccess: %s" % (addr))

    '''
    [{'srcaddr':'','srctype':'','srcchannel':'','dstaddr':'','dsttype':'','dstchannel':'','state':''},{}]
    '''

    def configLinkDevice(self, configobjs):
        Utils.logDebug("->configLinkDevice:%s" % (configobjs))
        if configobjs == None:
            return

        config = json.loads(configobjs)
        buffer = self.packParser.buildDeviceLinkReqestPack(config)
        if (buffer == None):
            Utils.logError("recv device config command: %s, cannot build buffer" % (config))
            return

        result = self.sendBuffer2(buffer)
        if (result > 0):
            # self.updateLinkDeviceInDb(config)
            pass

            # start_exec = time.clock()
            # recvBuffer = self.receiveBufferFrom()
            # end_exec = time.clock()
            # Utils.logInfo("rx buffer from driver consumes %s seconds"%(str(end_exec-start_exec)))
            # if(recvBuffer != None and len(recvBuffer) > 0):
            #     devicesData = self.packParser.parseRecvData(recvBuffer)
            #     if(devicesData == None or len(devicesData) <= 0):
            #         Utils.logInfo("recv control response len(%d),but no device data"%(len(recvBuffer)))
            #     else:
            #         #更新云上缓存（如果是来自云端的控制的话）
            #         # if(self.isFromCloud == True): #如果是来自云上的控制命令，需要更新
            #         #     self.updateCloudDevCacheValue(newDevValStr)
            #         # devStatusStr = json.dumps(deviceVal)
            #         self.backupToClould("devicestatus", deviceVal)
            #         for deviceData in devicesData:
            #             retDevAddr =  deviceData.get("addr","")
            #             if(retDevAddr != ""):
            #                 retDevStr = json.dumps(deviceData)
            #                 Utils.logDebug("write contrl ret device data of(%s): %s"%(retDevAddr, retDevStr))
            # else:
            #     Utils.logInfo("do not recv control response(%s)"%(devAddr))
        else:
            Utils.logError("failed to send config: %s" % (config))

        return 0

    # def updateLinkDeviceInDb(self, config):
    #     srcaddr = config.get("srcaddr")
    #     srctype = config.get("srctype")
    #     srcchannel = config.get("srcchannel")
    #     dstaddr = config.get("dstaddr")
    #     dsttype = config.get("dsttype")
    #     dstchannel = config.get("dstchannel")
    #     state = config.get("state")
    #
    #     if state == 0:
    #         ## remove link
    #         detailObj = DBManagerLinks().getDeviceLinks(srcaddr, srcchannel)
    #         if detailObj == None:
    #             Utils.logInfo('not found device link:%s %s'%(srcaddr, srcchannel))
    #             return
    #         #detailObj = {'timestamp':'', 'addr1':'channel1', 'addr2':'channel2',...}
    #         if detailObj.has_key(dstaddr):
    #             detailObj.pop(dstaddr, None)
    #             Utils.logInfo('remove device link success: %s'%(dstaddr))
    #     else:
    #         Utils.logInfo('add device link.')
    #         ## add link {'addr':"", 'channel':"", 'mmaacc':"channel2",}
    #         detailObj = DBManagerLinks().getDeviceLinks(srcaddr, srcchannel)
    #         if detailObj != None:
    #             detailObj[dstaddr] = dstchannel
    #         detailObj['addr'] = srcaddr
    #         detailObj['channel'] = srcchannel
    #         result = DBManagerLinks().saveDeviceLinks(detailObj)
    #         if result == None:
    #             Utils.logInfo('add device link failed.')
    #         else:
    #             Utils.logInfo('add device link success:%s'%(result))

    def updateValueProp(self, ctrlValue, newValue, paramName):
        paramValue = ctrlValue.get(paramName, "")
        if paramValue != "" and paramValue != None:
            newValue[paramName] = paramValue

    ## 用控制指令的值，更新数据库中相应的值
    ## 替换updateValueProp
    def updateValueProp2(self, ctrlValueDict, newValueDict):
        print('ctrlValueDict:', ctrlValueDict)
        for ctrlKey in ctrlValueDict.keys():
            ctrlValue = ctrlValueDict.get(ctrlKey)
            if ctrlValue != None and ctrlValue != "":
                newValueDict[ctrlKey] = ctrlValue
        print('after updateValueProp2: newValueDict:', newValueDict)

    # 更新缓存中的设备数据值
    def updateLocalDevCacheValue(self, deviceVal):
        Utils.logDebug("->updateLocalDevCacheValue:%s" % (deviceVal))
        try:
            devTypeName = deviceVal.get("type", "")
            devTypeId = self.packParser.getDeviceTypeIdByName(devTypeName)
            if (devTypeId <= 0):
                Utils.logError("updateLocalDevCacheValue:devTypeId invalid：%s" % (devTypeId))
                return None

            devAddr = deviceVal.get("addr", "")
            if (len(devAddr) < 3):
                Utils.logError("updateLocalDevCacheValue:devAddr invalid：%s " % (devAddr))
                return None

            ctrlValue = deviceVal.get("value", {})
            newValue = {}
            newDevValObj = {}
            # curDevValStr = globalVars.localRedis.hget(globalVars.hostKeyData, devAddr)
            curDevValStr = DBManagerDevice().getDeviceByDevId(devAddr)
            if (curDevValStr == None):
                # 如果读取不到已有数值，则直接返回，不要设置值，否则就成为虚拟值了
                # Utils.logInfo("updateLocalDevCacheValue:not found %s " % (devAddr))
                devpropobj = DBManagerDeviceProp().getDeviceByDevId(devAddr)
                if devpropobj == None:
                    return None
                # devStatusObj = {}
                # devStatusObj["name"] = devpropobj.get("name", None)
                # devStatusObj["type"] = devpropobj.get("type", None)
                # devStatusObj["addr"] = devAddr
                # curDevValStr = DBManagerDevice().saveDeviceStatus(devStatusObj)
                DBManagerDevice().initDevStatus(devpropobj)

            newDevValObj = (curDevValStr)  # may be null str, i.e. remote control
            if (newDevValObj is not None):
                newValue = newDevValObj.get("value", {})
            else:  # 可能没有初值，或者是红外遥控器等不会产生值的
                Utils.logDebug("updateLocalDevCacheValue:curDevValStr invalid：%s " % (curDevValStr))
                return None

            if (DEVTYPEID_LIGHTAJUST == devTypeId):
                self.updateValueProp(ctrlValue, newValue, "state")
                self.updateValueProp(ctrlValue, newValue, "coeff")
            elif (DEVTYPEID_LIGHT1 == devTypeId or DEVTYPEID_LIGHT2 == devTypeId or
                  DEVTYPEID_LIGHT3 == devTypeId or DEVTYPEID_LIGHT4 == devTypeId):
                # state的值：stateN:0,N表示索引为N的灯打开
                self.updateValueProp(ctrlValue, newValue, "state")
                self.updateValueProp(ctrlValue, newValue, "state2")
                self.updateValueProp(ctrlValue, newValue, "state3")
                self.updateValueProp(ctrlValue, newValue, "state4")
            elif DEVTYPEID_LOCK == devTypeId:
                self.updateValueProp(ctrlValue, newValue, "state")
                self.updateValueProp(ctrlValue, newValue, "set")
            elif (DEVTYPEID_SOCKET == devTypeId
                  or DEVTYPEID_CURTAIN == devTypeId):
                self.updateValueProp(ctrlValue, newValue, "state")
            elif (DEVTYPEID_EXIST_SENSOR == devTypeId
                  or DEVTYPEID_SOV == devTypeId):
                self.updateValueProp(ctrlValue, newValue, "set")
            elif (DEVTYPEID_EXIST_SENSOR == devTypeId):  # 插座
                self.updateValueProp(ctrlValue, newValue, "set")
            elif (
                    DEVTYPEID_TV == devTypeId or DEVTYPEID_IPTV == devTypeId or DEVTYPEID_DVD == devTypeId or DEVTYPEID_AIRCONDITION == devTypeId):  # 红外伴侣
                self.updateValueProp(ctrlValue, newValue, "mode")
                self.updateValueProp(ctrlValue, newValue, "state")
            # elif(DEVTYPEID_MODE_PANNEL == devTypeId): #模式面板
            #     self.updateValueProp2(ctrlValue, newValue)
            else:
                Utils.logDebug("updateLocalDevCacheValue:not found %s " % (devTypeId))
                return None

            newDevValObj["value"] = newValue
            # newDevStr = json.dumps(newDevValObj)
            # globalVars.localRedis.hset(globalVars.hostKeyData, devAddr, newDevStr)
            # 更新sqlite中该设备的状态值
            DBManagerDevice().saveDeviceStatus(newDevValObj)

            return newDevValObj
        except:
            Utils.logException("updateLocalDevCacheValue:exception ")
            return None

        return newDevValObj


if __name__ == '__main__':
    c2 = HostControlServer(102)
    c2.start()
    # time.sleep(5)
    # alarmsDict=[{"addr":"z-1111111"},{"addr":"z-1111112"}]
    # pub.sendMessage(GlobalVars.PUB_ALARM, cmd="confirmAlarms",alarms=alarmsDict)
    #
    # rtDeviceControl=[{"name":"light","type":"Light1","roomId":"1","room":"测试房","addr":"z-347D4501004B12001234","value":{"state":"0"}}]
    # pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="writeRTData",controls=rtDeviceControl)
