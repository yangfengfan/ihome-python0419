## -*- coding: utf-8 -*-


from ThreadBase import *
import GlobalVars
import Utils
import json
from PacketParser import *
from pubsub import pub
from DBManagerAlarm import *
from DBManagerBackup import *
from DBManagerDevice import *
from DBManagerDeviceProp import *
from DBManagerAction import *
from DBManagerHGC import *
from DBManagerHistory import *
import time
from WebHandlerBase import *
import ErrorCode
import copy
from SocketHandlerServer import SocketHandlerServer


class HostReportServer(ThreadBase):
    __instant = None
    __lock = threading.Lock()
    
    #singleton
    def __new__(self, arg):
        Utils.logDebug("__new__")
        if(HostReportServer.__instant==None):
            HostReportServer.__lock.acquire();
            try:
                if(HostReportServer.__instant==None):
                    Utils.logDebug("new HostReportServer singleton instance.")
                    HostReportServer.__instant = ThreadBase.__new__(self)
            finally:
                HostReportServer.__lock.release()
        return HostReportServer.__instant

    def __init__(self, threadId):
        ThreadBase.__init__(self, threadId, "HostReportServer")
        # self.destAddress = ("127.0.0.1", 8899)
        self.packParser = PacketParser()
        # self.registerDataSuccess = False
        # self.notifyDeviceConfigSuccess = False
        self.recvBuffer = ""

    def run(self):
        self.subscribe()
        self.init()
        Utils.logInfo("HostReportServer is running.")
        self.start_server()

    # def send_handle_request(self, data):
    #     self.que.get()
    #     pub.sendMessage("handle_reports", data=data)

    def start_server(self):
        Utils.logInfo("Device Socket Server is running.")
        server_socket = None
        while not self.stopped:
            try:
                if server_socket == None:
                    server_socket = self.setup_server()
                responseBuf = None
                clientsock, clientaddr = server_socket.accept()
                while not self.stopped:
                    try:
                        # self.que.get()
                        # Utils.logInfo('trying to rx socket data from client...%s'%(hex(id(s))))
                        data = clientsock.recv(GlobalVars.MAX_SOCKET_PACKET_SIZE)

                        if data == "":
                            self.close_socket(clientsock)
                            clientsock = None
                            break

                        if data is None or len(data) <= 0:
                            time.sleep(2)
                            continue

                        (cmdId, dataBuf) = self.onRecvDataBuffer(data)

                        # msgarr = self.packParser.parseCmdFromOneBuffer(data) # 返回控制命令

                        # Utils.logInfo('#@@devicesValue:%s'%(devicesValue))
                        # 组织设备数据
                        # curTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        if cmdId == CMDID_HGC_QUERY:
                            if dataBuf != None and len(dataBuf) > 0:
                                responseBuf = self.handleHGCquery(dataBuf[0])

                        elif cmdId == CMDID_HGC_CONTROL:
                            ##中控发送的控制命令
                            if dataBuf != None and len(dataBuf) > 0:
                                responseBuf = self.handleHGCcontrol(dataBuf[0])

                        elif cmdId == CMDID_HGC_REPORT:
                            # Utils.logSuperDebug("HGC reported,time %s " % time.strftime('%Y-%m-%d %H:%M:%S'))
                            # 中控发送的数据上报
                            if dataBuf != None and len(dataBuf) > 0:
                                responseBuf = self.handleHGCReport(dataBuf[0])

                        elif cmdId == CMDID_BATCH_SCAN:
                            # 批量添加设备，返回的是一个元素为字典的列表：[{"id": MacAddr, "name": MacAddr, "softwareVer": sver, "hardwareVer": hver}]
                            # 设备是一条一条上报的，列表只有一个元素
                            Utils.logDebug("--------------- CMDID_BATCH_SCAN ---------------")  # info
                            # pub.sendMessage(PUB_SAVE_BATCH_SCAN, device_prop=dataBuf[0])
                            # 批量插入、更新数据可以考虑使用 sqlite3 模块的 executemany() 函数
                            # http://jambecome.blog.51cto.com/5376248/1255463/
                            # Utils.logError('-------**hostreportserver*start_server=====**----dataBuf[0]=%s' % str(dataBuf[0]))
                            if len(dataBuf) >= 1:
                                DBManagerDeviceProp().newDeviceProperty(dataBuf[0], batch=True)  # TODO 确认添加方式之后确定使用DB工具
                            else:
                                continue

                        else:
                            # 其他，状态上报数据
                            # Utils.logError('-*****start_server:handleDevStatus----')
                            responseBuf = self.handleDevStatus(dataBuf)
                        self.sendResponse(clientsock, responseBuf)
                    except Exception, e:
                        Utils.logException('Error handling client socket. %s' % e)
                        self.close_socket(clientsock)
                        clientsock = None
                        responseBuf = None
                        break

                Utils.logException('reset client socket.')
            except Exception, e:
                Utils.logException('inner device socket server exception. %s' % e)
                # s.shutdown(2)
                self.close_socket(server_socket)
                server_socket = None
                # time.sleep(1)
            finally:
                pass

        # s.shutdown(2)
        self.close_socket(server_socket)
        Utils.logError('inner device socket server exit!...')
        time.sleep(10)

    def sendResponse(self, clientsock, responseBuf):
        if clientsock == None:
            print 'clientsock is NONE...'
            return
        if responseBuf == None:
            # 有失败情况，如何回复？
            # print 'no response...'
            # clientsock.send("no response...")
            return
        if isinstance(responseBuf, list):
            for buf in responseBuf:
                result = clientsock.send(buf)
                if(result > 0):
                    Utils.logInfo("send response to driver success.")
                else:
                    Utils.logError("send response to driver FAIL.")
        else:
            result = clientsock.send(responseBuf)
            if(result > 0):
                Utils.logInfo("send response to driver success2.")
            else:
                Utils.logError("send response to driver FAIL2.")

    # 处理中控的数据上报，目前主要是地暖的数据
    def handleHGCReport(self, report_dict):

        Utils.logDebug("handleHGCReport: %s" % report_dict)

        report_cmd = report_dict.get("reportCmd", None)
        if report_cmd is None:
            Utils.logError("reportCmd is None")
            return
        if report_cmd == 0 or report_cmd == 1:
            self.handleFloorHeatingStatus(report_dict)
        if report_cmd == 2:
            self.handleFloorHeatingTimeTask(report_dict)

    def handleFloorHeatingStatus(self, status_dict):
        # Utils.logSuperDebug("FloorHeatingStatus recv,time %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
        hgc_addr = status_dict.get("hgcAddr")
        floor_heating_addr = ""

        # 先要查到地暖的mac地址（添加时自动生成的时间戳）
        device_prop = DBManagerDeviceProp().getDeviceByDevType("FloorHeating")
        if device_prop is None or len(device_prop) == 0:
            Utils.logDebug("No floor heating device...")
        else:
            for item in device_prop:
                if item.get("hgcAddr", "") == hgc_addr:
                    floor_heating_addr = item.get("addr")
        if floor_heating_addr == "":
            Utils.logDebug("No corresponding hgc for the floor heating...")
            return

        hgc_addr = status_dict.get("hgcAddr")
        old_status = DBManagerDevice().getDeviceByDevId(floor_heating_addr)
        if old_status is None:
            new_status = dict()
            new_status["hgcAddr"] = hgc_addr
            new_status["addr"] = floor_heating_addr
            new_status["type"] = "FloorHeating"
            new_status["value"] = status_dict.get("value")
            new_status["time"] = str(int(time.time()))
            DBManagerDevice().saveDeviceStatus(new_status)
        else:
            if status_dict.get("value").get("state") == 0:
                old_status.get("value")["state"] = 0
            if status_dict.get("value").get("state") == 1:
                old_status["value"] = status_dict.get("value")
            old_status["time"] = str(int(time.time()))
            DBManagerDevice().saveDeviceStatus(old_status)

    def handleFloorHeatingTimeTask(self, time_task_dict):
        # Utils.logSuperDebug("FloorHeatingTimetask recv,time %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
        hgc_addr = time_task_dict.get("hgcAddr")
        old_prop = ""
        new_time_task = time_task_dict.get("timeTask")
        task_type = new_time_task.get("type")
        pack_number = new_time_task.get("packNumber")
        update_time = new_time_task.get("updateTime")

        # 先要查到地暖的mac地址（添加时自动生成的时间戳）
        device_prop = DBManagerDeviceProp().getDeviceByDevType("FloorHeating")
        if device_prop is None or len(device_prop) == 0:
            Utils.logDebug("No floor heating device...")
        for item in device_prop:
            if item.get("hgcAddr", "") == hgc_addr:
                old_prop = item
        if old_prop == "":
            Utils.logDebug("No corresponding hgc for the floor heating...")
            return

        old_time_task = old_prop.get("timeTask", None)
        if old_time_task is None or old_time_task == "":
            old_time_task = [{"type": "weekday", "syncState": "0", "taskList": []},
                                {"type": "weekend", "syncState": "0", "taskList": []}]
            old_prop["timeTask"] = old_time_task
        for item in old_time_task:
            if item.get("type") == task_type:

                # if item.get("syncState") == "0":
                #     item["syncState"] = "1"
                #     item["taskList"] = list()
                #     for add_item in new_time_task.get("taskList"):
                #         item["taskList"].append(add_item)

                if pack_number == 1:
                    item["taskList"] = list()
                    # 保存更新时间
                    item["updateTime"] = update_time
                    for add_item in new_time_task.get("taskList"):
                        item["taskList"].append(add_item)

                # elif item.get("syncState") == "1":
                #     item["syncState"] = "0"
                #     Utils.logInfo("===>set syncState to 0: %s" % item["syncState"])
                #     for add_item in new_time_task.get("taskList"):
                #         item["taskList"].append(add_item)

                elif pack_number == 2:
                    # 超时检测
                    pack1_time = item.get("updateTime", 0)
                    pack2_time = time_task_dict.get("updateTime", 0)
                    if pack1_time == 0 or (pack2_time - pack1_time) > 10:
                        item["taskList"] = []
                    else:
                        for add_item in new_time_task.get("taskList"):
                            item["taskList"].append(add_item)
                    # 重置更新时间
                    item["updateTime"] = 0

        old_prop["timeTaskSwitch"] = "on"
        DBManagerDeviceProp().saveDeviceProperty(old_prop)

    def handleHGCcontrol(self, commandObj):

        # {'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'ctrlDevNumber':controlDevNumber,
        # 'controlCmd':controlCmd, 'controlData':controlData}
        hgcaddr = commandObj.get('addr', None)
        ctrlDevType = commandObj.get('ctrlDevType', None)
        ctrlDevNumber = commandObj.get('ctrlDevNumber', 1)
        controlData = commandObj.get('controlData', None)
        adjust_coeff = commandObj.get('coeff', None)
        is_adjust = commandObj.get('isAdjust', None)

        ctrlDevTypeStr = ""
        if ctrlDevType is not None:
            int_type = int(ctrlDevType)
            tmp = str(hex(int_type))
            ctrlDevTypeStr = tmp[0:2] + tmp[2:].upper()


        # 中总控设备配置记录
        # {'addr':'hhggcc001122','v_type':0x1,'channel':1, 'controls':[{'addr':'dst-mac1','type':'Light2',
        # 'value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]}
        configObj = DBManagerHGC().getHGCconfig(hgcaddr, ctrlDevTypeStr, ctrlDevNumber)
        if configObj is None:
            Utils.logError("No configuration in HGC!!!")
            return

        if int(ctrlDevType) == 0x01 or int(ctrlDevType) == 0x02 or int(ctrlDevType) == 0x04 or int(ctrlDevType) == 0x0F:

            if configObj == None:
                # 返回未配置错误码
                return
            # 开关灯
            if int(ctrlDevType) == 0x01:

                controls = configObj.get('controls', None)
                # 'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]
                if controls != None and len(controls) > 0:
                    control = controls[0]
                    # {'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}}
                    # 调光灯
                    if control.get("type") == "LightAdjust" or is_adjust == 1:
                        Utils.logDebug("hgc control light_adjust")
                        ctrlDevState = control.get('value', None)
                        if ctrlDevState is not None and len(ctrlDevState) > 0:
                            ctrlDevState["state"] = str(controlData)
                            ctrlDevState["coeff"] = str(adjust_coeff)
                            control["value"] = ctrlDevState
                            self.sendControl2Driver(control)
                    # 普通灯
                    else:
                        ctrlDevState = control.get('value', None)
                        if ctrlDevState is not None and len(ctrlDevState) > 0:
                            newControls = []
                            for key in ctrlDevState.keys():
                                tmp_v = {}
                                tmp_v[key] = str(controlData)
                                control["value"] = tmp_v
                                control1 = copy.deepcopy(control)
                                newControls.append(control1)
                                control["value"] = ""
                            self.sendControl2Driver(newControls)
                return

            ## 插座,窗帘
            elif int(ctrlDevType) == 0x02 or int(ctrlDevType) == 0x04:
                controls = configObj.get('controls', None)

                if controls != None and len(controls) > 0:
                    control = controls[0]
                    ##{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}}
                    ctrlDevState = control.get('value', None)
                    if ctrlDevState is not None and len(ctrlDevState) > 0:
                        ## 插座和窗帘都只有一个state
                        control['value']["state"] = str(controlData)
                        self.sendControl2Driver(control)
                return

            ## 场景控制
            elif int(ctrlDevType) == 0xF:
                ## 场景控制
                controls = configObj.get('controls', None)

                if controls != None and len(controls) > 0:
                    control = controls[0]
                    ##{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}}
                    modeId = control.get('modeId', None)
                    if modeId != None:
                        webHandler = WebHandlerBase()
                        webHandler.init()
                        payload = {}
                        payload['modeId'] = modeId
                        webHandler.sendCommand(GlobalVars.TYPE_CMD_ACTIVE_ROOM_MODE, payload)
                        webHandler.uninit()
                        webHandler = None
                return

        ## 红外空调
        if int(ctrlDevType) == 0x03:
            controls = configObj.get('controls', None)
            if controls != None and len(controls) > 0:
                control = controls[0]
                ctrlDevState = control.get('value', None)
                if ctrlDevState is not None and len(ctrlDevState) > 0:
                    ## 将value中的state替换成接收到的控制指令
                    control['value']["key"] = str(controlData)
                    ##
                    self.sendControl2Driver(control)
            return

         ## 中央空调 TODO
        if int(ctrlDevType) == 0x50:
            controlCmd = commandObj.get('controlCmd', None)
            protocol = commandObj.get('protocol', None)
            controls = configObj.get('controls', None)
            if controls != None and len(controls) > 0:
                control = controls[0]
                ctrlDevState = control.get('value', None)
                if ctrlDevState is not None and len(ctrlDevState) > 0:

                    addr = str(control.get("addr"))
                    if addr[:4] == "CAC_":
                        addr = addr[4:]
                        control["addr"] = addr
                        control['value']['addr'] = addr

                    control['value']['controlCmd'] = controlCmd
                    control['value']['protocol'] = protocol
                    control['value']['controlData'] = controlData

                    self.sendControl2Driver(control)
            return

                    # ## 调光灯
        # if ctrlDevType == 0x02:
        #     controls = configObj.get('controls', None)
        #     ##'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]
        #     if controls != None and len(controls) > 0:
        #         control = controls[0]
        #         ##{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}}
        #         ctrlDevState = control.get('value', None)
        #         if ctrlDevState != None and len(ctrlDevState) > 0:
        #             tmp_v = {}
        #             for key in ctrlDevState.keys():
        #                 stateV = ctrlDevState.get(key, None)
        #                 if stateV == '1':
        #                     ##中总控配置按键实际控制的灯的通道号
        #                     tmp_v['coeff'] = controlData
        #                     break
        #             control['value'] = tmp_v
        #             ##
        #             self.sendControl2Driver(control)
        #     return

    def sendControl2Driver(self, control):

        if isinstance(control, list):
            Utils.logInfo("publish PUB_CONTROL_DEVICE controlDevice by hgc:%s"%(control))
            pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice",controls=control)
            return

        devicesToCtrol = []
        devicesToCtrol.append(control)
        Utils.logInfo("publish PUB_CONTROL_DEVICE controlDevice by hgc:%s"%(devicesToCtrol))
        pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice",controls=devicesToCtrol)

    def checkHGCPortConfig(self, hgcaddr, hgcType, ctrlDevType, ctrlDevNumber):
        configured = False
        configObj = DBManagerHGC().getHGCconfig(hgcaddr, ctrlDevType, ctrlDevNumber)
        ### {'addr':'hhggcc001122','v_type':0x1,'channel':1, 'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]}
        if configObj != None:
            controls = configObj.get('controls', None)
            ##'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]
            if controls != None and len(controls) > 0:
                control = controls[0]
                ## {'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}}
                ctrlDevAddr = control.get('addr', None)
                ctrlDevState = control.get('value', None)
                if ctrlDevAddr != None and ctrlDevState != None and len(ctrlDevState) > 0:
                    ##至此可以认为中总控设备的这个端口是配置了的
                    configured = True
        response = {'addr':hgcaddr, 'type':hgcType, 'ctrlDevType':ctrlDevType, 'ctrlDevNumber':ctrlDevNumber,
                    'configured':configured}
        return self.packParser.buildHGCportConfiguredPack(response)

    def handleHGCquery(self, commandObj):
        ## {'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'ctrlDevNumber':controlDevNumber, 'returnType':returnType}
        hgcaddr = commandObj.get('addr', None)
        hgcType = commandObj.get('type', None)
        ctrlDevType = commandObj.get('ctrlDevType', None)
        channel = commandObj.get('channel', None)
        returnType = commandObj.get('returnType', None)
        if returnType == 0xFF and channel == 0xFF and ctrlDevType == 0xFF:
            ##查询是否配置过该端口
            return self.checkHGCPortConfig(hgcaddr, hgcType, ctrlDevType, channel)

        ##中总控设备配置记录
        ### {'addr':'hhggcc001122','v_type':0x1,'channel':1, 'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]}

        # 查询时间，接收到的数据都为0 或者设备类型是0x18(LCD开关)
        if (returnType == 0 and channel == 0 and ctrlDevType == 0) or hgcType == 0x18:
            buf = self.packParser.buildSyncHgcTimePack(hgcaddr);
            pub.sendMessage("syncHgcTime", buffer=buf)
            return buf



        configObj = DBManagerHGC().getHGCconfig(hgcaddr, ctrlDevType, channel)
        if configObj is None or len(configObj) == 0:
            ##返回未配置错误码
            return
        controls = configObj.get('controls', None)
        ##'controls':[{'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}},{'addr':'dst-mac2',...}]
        if controls == None or len(controls) == 0:
            ##返回未配置错误码
            return
        control = controls[0]
        ## {'addr':'dst-mac1','type':'Light2','value':{'state':'0','state1':'1'}}
        ctrlDevAddr = control.get('addr', None)
        if ctrlDevAddr == None:
            return

        if returnType == 0:
            ctrlDevState = control.get('value', None)
            if ctrlDevState == None or len(ctrlDevState) == 0:
                ##返回未配置错误码
                return
            devStatusInDb = DBManagerDevice.getDeviceByDevId(ctrlDevAddr)
            valueInDb = devStatusInDb.get("value", None)
            retV = None
            if valueInDb != None:
                for key in ctrlDevState.keys():
                    stateV = ctrlDevState.get(key, None)
                    if stateV == '1':
                        ##中总控配置按键实际控制的灯的通道号
                        retV = valueInDb.get(key, None)
                        break
            ## retV是实际灯的状态值，返回给总中控
            ## {'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'ctrlDevNumber':controlDevNumber, 'returnType':returnType}
            response = {'addr':hgcaddr, 'type':hgcType, 'ctrlDevType':ctrlDevType, 'channel':channel, 'returnType':returnType, 'buflen':1, 'buf':retV}
            # return self.responseHGCquery(response)
            return self.packParser.buildHGCqueryResponsePack(response)
        elif returnType == 1:
            devPropObj = DBManagerDeviceProp().getDeviceByDevId(ctrlDevAddr)
            if devPropObj == None:
                return
            devName = devPropObj.get('name', None)
            if devName == None:
                return
            response = {'addr':hgcaddr, 'type':hgcType, 'ctrlDevType':ctrlDevType, 'channel':channel, 'returnType':returnType, 'buflen':len(devName), 'buf':devName}
            return self.packParser.buildHGCqueryResponsePack(response)
        else:
            return

    def handleDevStatus(self, devicesValue):
        # for i in list(range(10000)):
        #     Utils.logError("-----handleDevStatus****begin**=%s" % devicesValue)
        for deviceVal in devicesValue:
            try:
                value = deviceVal.get("value", None)
            except:
                Utils.logException("device's value is not an object:%s" % (deviceVal))
                continue

            if(value == None):
                Utils.logError("device: %s, value is none " % (deviceVal))
                continue

            # value["time"] = curTime

            # devAddr = deviceVal.get("addr", "")
            # 将设备实时数据写入家庭网关的redis库
            # self.writeRTDataToRedis(devAddr, deviceVal)

            # 检查value是否和数据库一致
            # 如一致，则无需再处理
            # Utils.logInfo('rx data from driver.....')
            (same, valid, keys) = self.checkValue(value, deviceVal.get("addr", None), deviceVal.get("type", None))
            if valid is False:
                Utils.logInfo('discard invalid packet')
                return None

            # 存储实时数据
            devTypeName = deviceVal.get("type", "")
            if devTypeName in ["Exist", "Gsm", "CurtainSensor"]:
                '''
                存在传感器、门窗磁、红外幕帘撤防后不需要显示告警状态
                由于设备机制变更，在设置撤防时只是修改设备状态库表中的状态，
                不将命令发到设备，所以设备本身不会再根据撤防布防状态上报
              '''
                deviceValTemp = copy.deepcopy(deviceVal)
                devAddr = deviceVal.get("addr", None)
                if devAddr is not None:
                    statusDetail = DBManagerDevice().getDeviceByDevAddrAndType(devAddr, devTypeName)  # 查询当前传感器状态
                    sts_value = statusDetail.get("value", None)

                    if sts_value is not None:
                        sensor_state = int(sts_value.get("set", "1"))
                        if sensor_state == 0:
                            deviceValTemp["value"]["state"] = 0
                            deviceValTemp["value"]["set"] = "0"
            if devTypeName in [DEVTYPENAME_TABLE_WATER_FILTER, DEVTYPENAME_AIR_FILTER]:
                # 这些设备的状态是分包上传的，不能直接存入状态库，需要在数据库原有数据基础上添加新数据之后存入
                devAddr = deviceVal.get("addr", None)
                if devAddr:
                    devStatusObj = DBManagerDevice().getDeviceByDevAddrAndType(devAddr, devTypeName)
                    valueInDb = devStatusObj.get("value", {})
                    valueInCome = deviceVal.get("value", None)
                    if valueInCome:
                        for key, value in valueInCome.items():
                            valueInDb[key] = value  # 将数据库数据和上报数据合并
                        deviceVal["value"] = valueInDb  # 将数据库数据和上报数据合并后复制给上报数据的value字段

            if devTypeName == DEVTYPENAME_LIGHTAJUST_PANNEL:
                # 如果是调光控制面板，state是1要每15分钟发一次控制，state是其他要取消
                devAddr = deviceVal.get("addr", None)
                if devAddr:
                    value = deviceVal.get("value", {})
                    state = int(value.get("state", 6))
                    devName = deviceVal.get("name", "调光控制面板")
                    addr_ray_sense = ""
                    props = DBManagerDeviceProp().getDeviceByDevAddrAndType(devAddr, DEVTYPENAME_LIGHTAJUST_PANNEL)
                    link_light_sensor = props.get("linkLightSensor", None)
                    if link_light_sensor is not None:
                        device_status = link_light_sensor.get("deviceStatus", None)
                        if device_status is not None:
                            addr_ray_sense = device_status.get("addr", "")
                    if state == 1:
                        Utils.logError("------set in rhythm mode------")
                        pub.sendMessage(GlobalVars.PUB_START_PANNEL_LISTEN, addr=devAddr, addr_ray_sense=addr_ray_sense, device_name=devName)
                        light_adjust_Pannel_flag[devAddr] = True
                    else:
                        Utils.logError("------not in rhythm mode------")
                        pub.sendMessage(GlobalVars.PUB_STOP_PANNEL_LISTEN, addr=devAddr)
                        light_adjust_Pannel_flag[devAddr] = False
                # Utils.logError('------20190326 light_adjust_Pannel_flag=%s------' % str(light_adjust_Pannel_flag))

                        # devicesToCtrol = []
                        # singleValue = {}
                        # singleValue["state"] = state
                        # devToCtrol = {"name": devName, "addr": devAddr, "value": singleValue, "type": devTypeName}
                        # devicesToCtrol.append(devToCtrol)
                        # pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice", controls=devicesToCtrol)
                        # Utils.logError('-----state-else---------------------devicesToCtrol-=%s' % (devicesToCtrol))

            if devTypeName == DEVTYPENAME_WUHENG_SYSTEM:
                # 五恒系统上报的数据每个面板上报一个索引地址
                devAddr = deviceVal.get("addr", None)
                if devAddr:
                    devStatusObj = DBManagerDevice().getDeviceByDevAddrAndType(devAddr, devTypeName)
                    valueInDb = devStatusObj.get("value", {})
                    valueInCome = deviceVal.get("value", None)
                    addrIndex = str(valueInCome.get("addrIndex"))  # 本次上报的五恒面板索引地址
                    if addrIndex == '0':
                        # 总数据包，把模式、PM2.5、CO2、VOC写入每一个面板状态数据
                        if valueInDb:
                            Utils.logDebug("valueInDb is: %s" % str(valueInDb))
                            for index, val in valueInDb.items():
                                val['mode'] = valueInCome.get('mode')
                                val['pm25'] = valueInCome.get('pm25')
                                val['voc'] = valueInCome.get('voc')
                                val['co2'] = valueInCome.get('co2')
                                if not val.has_key("roomname"):
                                    val['roomname'] = '房间%s' % str(index)
                                if not val.has_key("addrIndex"):
                                    val['addrIndex'] = int(index)
                                valueInDb[index] = val
                        else:
                            # 单个面板还没上报
                            pannel_num = int(valueInCome.get('pannel_num', 0))
                            for i in range(pannel_num):
                                val['mode'] = valueInCome.get('mode')
                                val['pm25'] = valueInCome.get('pm25')
                                val['voc'] = valueInCome.get('voc')
                                val['co2'] = valueInCome.get('co2')
                                val['roomname'] = '房间%s' % str(i)
                                val['addrIndex'] = int(addrIndex)
                                valueInDb[str(i)] = val
                        Utils.logDebug("valueInDb final is: %s" % str(valueInDb))
                    else:
                        # 单个面板数据
                        val = valueInDb.get(str(addrIndex))
                        if not val:
                            # 总数据包未上报，初始化为一个空字典
                            val = {}

                        val['state'] = valueInCome.get('state', 0)
                        val['set_status'] = valueInCome.get('set_status')
                        val['set_temp'] = valueInCome.get('set_temp')
                        val['temp'] = valueInCome.get('temp')
                        val['humid'] = valueInCome.get('humid')
                        val['wind_srate'] = valueInCome.get('wind_srate')
                        val['windRate'] = valueInCome.get('windRate')
                        valueInDb[str(addrIndex)] = val

                    deviceVal["value"] = valueInDb

                    # valueInCome['roomname'] = valueInDb.get('roomname', '房间%s' % str(addrIndex))
                    # if valueInCome:
                    #     # 五恒系统的value结构是 {"addrIndex1": {valueDict1}, "addrIndex2": {valueDict2}, ...}
                    #     valueInDb[str(addrIndex)] = valueInCome
                    #     deviceVal["value"] = valueInDb
            if devTypeName in [DEVTYPENAME_GSM, DEVTYPENAME_CURTAIN_SENSOR, DEVTYPENAME_EXIST_SENSOR]:
                newDeviceJsonObj = DBManagerDevice().saveDeviceStatus(deviceValTemp)
            else:
                newDeviceJsonObj = DBManagerDevice().saveDeviceStatus(deviceVal)
            # Utils.logError("-----handleDevStatus****devTypeName** %s" % devTypeName)
            if same == False:
                # 状态改变，需同步到云端
                self.saveDeviceStatusToCloud(newDeviceJsonObj, devTypeName)

                # 如果是门锁，并且正常打开，需执行开门联动模式
                if devTypeName == "Lock":
                    try:
                        Utils.logDebug("===>activate door open mode...")
                        lock_value = newDeviceJsonObj.get("value")
                        lock_state = lock_value.get("state")
                        if lock_state == "1" or lock_state == 1:
                            # 从DBManagerAction中查出开门模式的modeId
                            door_open_mode = DBManagerAction().getActionByName("开门模式")
                            # mode_is_on = door_open_mode.get("set")
                            # 检查开门模式是否处于激活状态
                            # if mode_is_on == "1" or int(mode_is_on) == 1:
                            if door_open_mode:  # 配置了开门模式才触发
                                modeId = door_open_mode.get("modeId")
                                sparam = {"modeId": modeId}
                                pub.sendMessage("door_open", sparam=sparam)
                    except Exception as err:
                        Utils.logError("开门模式执行失败... %s" % err)

                # 如果该设备配置在中控面板上，需要同步状态到中控面板
                v_type = self.getVtypeByName(devTypeName)
                devices_hgc = DBManagerHGC().getByVtype(v_type)
                if devices_hgc is not None and len(devices_hgc) > 0:
                    addr = str(newDeviceJsonObj.get("addr", None))
                    # status表的地址有UNIQUE约束，在中央空调的地址前加“CAC_”， 这里需要将“CAC_”去掉
                    # if addr[:3] == "CAC_":
                    #     addr = addr[4:]
                    for item in devices_hgc:
                        dev_addr = item.get("controls")[0].get("addr")
                        if str(dev_addr) == str(addr):
                            sparam = {}
                            protocol = item.get("controls")[0].get("value").get("protocol")
                            Utils.logDebug("protocol:%s"%protocol)
                            sparam["protocol"] = protocol
                            sparam["keys"] = keys
                            sparam["type_name"] = devTypeName
                            sparam["hgc_addr"] = item.get("addr")
                            sparam["channel"] = item.get("channel")
                            sparam["v_type"] = item.get("v_type")
                            sparam["update"] = 0x00
                            sparam["value"] = newDeviceJsonObj.get("value")
                            pub.sendMessage("syncHgcDevices", sparam=sparam)
            else:
                pass
                # Utils.logInfo('device status not changed. discard it.%s'%(newDeviceJsonObj))
                # return

            # 判断报警是否有改变, 根据state属性判断
            devTypeId = self.packParser.getPhysicalDeviceTypeIdByName(devTypeName)
            self.processDeviceAlarm(devTypeId, deviceVal)

            # 判断是否关联设备
            self.processModePannel(deviceVal)
        # 同时通知到线程cloudDataThread，以便从本地再写入云上
        # if(len(devicesValue) > 0):
        #     globalVars.publishCmdToLocal(globalVars.cmdType_DataToCloud, devicesValue)
        return None

    # 根据设备类型获取v_type
    def getVtypeByName(self, type_name):
        if type_name is None or type_name == "":
            return None
        if type_name == "LightAdjust" or type_name == "Light1" or type_name == "Light1" or type_name == "Light2" or type_name == "Light3" or type_name == "Light4":
            return 0x01
        if type_name == "Curtain":
            return 0x04
        if type_name == "AirCondition":
            return 0x03
        if type_name == "CAC":
            return 0x50
        if type_name == "Socket":
            return 0x02
        if type_name == "FloorHeating":
            return 0x52

    # 如果是模式面板，需触发对应的模式
    # deviceRTData格式：
    # {'time': 1516353645, 'type': u'Pannel', 'name': u'3\u573a\u666f\u9762\u677f', 'value': {'state3': 0, 'state2': 0, 'state': 1, 'state6': 0, 'state5': 0, 'state4': 0}, 'addr': 'C7B72507004B12000000'}
    def processModePannel(self, deviceRTData):
        devTypeName = deviceRTData.get("type", "")
        devTypeId = self.packParser.getPhysicalDeviceTypeIdByName(devTypeName)
        if devTypeId not in [DEVTYPEID_MODE_PANNEL, DEVTYPEID_LCD_SWITCH]:
            return

        devAddr = deviceRTData.get("addr", None)
        value = deviceRTData.get("value", None)
        if(value == None or devAddr == None):
            return

        if devTypeName == DEVTYPENAME_PANNEL:
            # 普通模式面板
            channelId = value.get('state', 0)
        else:
            # LCD开关
            channelId = value.get("sceneState", 0)

        if channelId > 0:
            self.modeEnabled(devAddr, channelId)

    def modeEnabled(self, addr, channelId):
        Utils.logDebug('mode pannel %s channel-%d is enabled.'%(addr, channelId))
        # modecfg:{"1":"modeId1", "2":"modeId2", ...}
        dev = DBManagerDeviceProp().getDeviceByDevId(addr)
        if dev == None:
            return
        modecfg = dev.get('modecfg', None)
        if modecfg == None:
            return

        ## {"1":"modeId1", "2":"modeId2", ...}
        modeId = modecfg.get(str(channelId), None)
        if not modeId:  # 是空字符串或者None都return
            return

        webHandler = WebHandlerBase()
        webHandler.init()
        payload = {}
        payload['modeId'] = modeId
        payload['cmdSource'] = "pannel" # TODO 接入Ketra，面板触发模式时开灯
        payload['roomname'] = dev.get("roomname")
        webHandler.sendCommand(GlobalVars.TYPE_CMD_ACTIVE_ROOM_MODE, payload)
        webHandler.uninit()
        webHandler = None

    def getChannelFrom(self, stateKey):
        return Utils.getChannelFrom(stateKey)

    def close_socket(self, sock):
        if sock != None:
            try:
                sock.close()
                sock.shutdown(2)
            except:
                pass

        sock = None

    def setup_server(self):
        host = "127.0.0.1"       # 网关名，可以是ip,像localhost的网关名,或""
        port = 9876     #端口
        addr = (host, port)

        # server = ThreadingTCPServer(addr, SocketDeviceServer)
        # server.serve_forever()
        svr_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
        svr_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        svr_socket.bind(addr)
        svr_socket.listen(10)
        self.recvBuffer = ""
        return svr_socket

    def subscribe(self):
        pass
        # pub.subscribe(self.controlHandler, GlobalVars.PUB_CONTROL_DEVICE)
        # pub.subscribe(self.alarmHandler, GlobalVars.PUB_ALARM)

    def onSockConnected(self):
        Utils.logDebug("->onSockConnected()")
        #do nothing.
        return

    # def onSockDisconnected(self):
    #     Utils.logDebug("->onSockDisconnected()")
    #     self.registerDataSuccess = False
    #     self.notifyDeviceConfigSuccess = False

    # def registerToDriver(self):
    #     Utils.logDebug("->registerToDriver()")
    #     #如果网络已经断开，那么设置注册为失败
    #     bufferRequest = self.packParser.buildRegisterDataPack()
    #     result = self.sendBuffer2(bufferRequest)
    #     if(result > 0):
    #         recvBuffer = self.receiveBufferFrom()
    #         if(recvBuffer == None or len(recvBuffer) <= 0):
    #             Utils.logError("Failed to rx RegisterData response(send len:%d)"% result)
    #             return False
    #
    #         (cmdId, result) = self.onRecvDataBuffer(recvBuffer)
    #         #如果返回值不是None则表示控制成功或通知成功
    #         if(result == None):
    #             Utils.logError("Parse Register Data response Failed")
    #         else:
    #             # self.lastRegisterTime = curTime
    #             return True
    #         return False
    #     else:
    #         Utils.logError("Register Data send failed.")
    #
    #     return False
    #
    # #启动后把所有设备发给驱动
    # def notifyDeviceConfigReloaded(self):
    #     Utils.logDebug("->notifyDeviceConfigReloaded()")
    #     allDeviceInfo = DBManagerDeviceProp().getAllDevices()
    #     if allDeviceInfo is None:
    #         return True
    #     bufferRequest = self.packParser.buildConfigChangePack(allDeviceInfo)
    #
    #     result = self.sendBuffer2(bufferRequest)
    #     if(result > 0):
    #         recvBuffer = self.receiveBufferFrom()
    #         (cmdId, result) = self.packParser.parseRecvData(recvBuffer) # 返回设备数据数组
    #         #如果返回值不是None则表示控制成功或通知成功
    #         if(result == None):
    #             Utils.logError("Config changed Failed")
    #             return False
    #         else:
    #             Utils.logInfo("Config changed Success")
    #             return True
    #     return False

    def checkValue(self, value, devaddr, devType):
        same = False
        valid = True
        keys = []  # 存储改变了的数据的key
        # devaddr = deviceVal.get("addr", None)
        # Utils.logInfo('.....1 %s'%(devaddr))
        if devaddr != None and value != None:
            if devType in [DEVTYPENAME_TABLE_WATER_FILTER, DEVTYPENAME_AIR_FILTER]:  # 设备是台上净水器、空气净化器(delos)时不校验有效性  20170405 -- chenjc
                keys = value.keys()
            else:
                try:
                    devItem = DBManagerDevice().getDeviceByDevAddrAndType(devaddr, devType)
                    #     Utils.logInfo('.....2 %s'%(devItem))
                    if(devItem != None):
                        valueInDb = devItem.get("value", None)
                        #Utils.logInfo('check %s reported value: %s'%(devaddr, value))
                        #Utils.logInfo('and value in db: %s'%(valueInDb))
                        if valueInDb != None:
                            if len(value) == len(valueInDb):
                                same = True
                                for key in value.keys():
                                    if 'time' not in key:
                                        tmp =  valueInDb.get(key, None)
                                        if tmp == None or str(tmp) != str(value.get(key, None)):
                                            ##不一致
                                            keys.append(key)
                                            same = False
                                            db_time = devItem.get("time", None)
                                            valid = self.checkEnergyData(devItem.get('type', None), value, valueInDb, db_time)
                                            # if not valid:
                                            #     ##水电气上报数据异常，不存储
                                            #     same = True
                                            # break
                except:
                    same = False
                    valid = False

        return (same, valid, keys)

    def checkEnergyData(self, devType, curValue, dbValue, db_time):

        valid = True
        invalidU = 500       ##电压超过500伏认为异常
        curr_time = int(time.time())


        time_interval = 0
        if curr_time is not None and db_time is not  None:
            time_interval = curr_time - db_time  # 两次上报的间隔
        try:
            if curValue is None:
                return False
            if devType == 'elec' or devType == 'ElecMeter':

                ## 电能表数据
                curEnergy = float(curValue.get('energy'))
                if curEnergy <= 0:
                    return False
                if dbValue != None:
                    dbEnergy = float(dbValue.get('energy'))
                    if dbEnergy != 0 and curEnergy/dbEnergy >= 10:
                        valid = False
                    if curValue.has_key('Uab'):
                        curU = float(curValue.get('Uab'))
                        if curU <= 0 or curU > invalidU:
                            valid = False
                    if curValue.has_key('Ubc'):
                        curU = float(curValue.get('Ubc'))
                        if curU > invalidU:
                            valid = False
                    if curValue.has_key('Uca'):
                        curU = float(curValue.get('Uca'))
                        if curU > invalidU:
                            valid = False
            elif devType == 'Socket':
                ## Socket
                curEnergy = float(curValue.get('energy'))
                if curEnergy < 0:  # 新插座有可能电能是0
                    return False
                if dbValue != None:
                    dbEnergy = float(dbValue.get('energy'))
                    if dbEnergy != 0 and (curEnergy - dbEnergy) >= 0.0014 * time_interval:
                        valid = False
                    if curValue.has_key('U'):
                        curU = float(curValue.get('U'))
                        if curU <= 0 or curU > invalidU:
                            valid = False
            elif devType == 'water' or devType == 'WaterMeter':
                ## Water
                curEnergy = float(curValue.get('energy'))
                if curEnergy <= 0:
                    return False
                if dbValue != None:
                    dbEnergy = float(dbValue.get('energy'))
                    if (dbEnergy != 0 and curEnergy/dbEnergy >= 10):
                        valid = False
        except:
            valid = False
        return valid

    def onRecvDataBuffer(self, recvBuffer):
        Utils.logDebug("->onRecvDataBuffer()")
        if(recvBuffer == None or len(recvBuffer) <= 0):
            return (None, None)
        # Utils.logHex('recvBuffer', recvBuffer)
        return self.packParser.parseRecvData(recvBuffer)  # 返回设备数据数组


    # 设备状态变化后，需同步到云端
    def saveDeviceStatusToCloud(self,newDeviceJsonObj, devTypeName):
        # Utils.logInfo('device status changed. save to database.')
        # time.sleep(0.2)

        devTypeId = self.packParser.getPhysicalDeviceTypeIdByName(devTypeName)

        # 将新状态同步到云端，水电煤数据定时备份
        if newDeviceJsonObj != None:
            if devTypeId == DEVTYPEID_SOCKET:
                # 插座，半小时保存一次电能数据
                pub.sendMessage("publish_save_socket_data", data=newDeviceJsonObj, arg2=None)
                # DBManagerBackup().saveBackupSocket(newDeviceJsonObj)
            elif devTypeId in [DEVTYPEID_AIR_FILTER, DEVTYPEID_TABLE_WATER_FILTER]:
                # 台上净水器、台下净水器、空气净化器数据写入
                pub.sendMessage("publish_save_filter_data",devTypeName=devTypeName, data=newDeviceJsonObj)
            elif self.packParser.isEnergyDataType(devTypeId) == False:
                # 普通设备状态
                metaDict={}
                metaDict["type"] = "devices"
                metaDict["valueStr"] = newDeviceJsonObj
                Utils.logDebug("publish PUB_SEND_RTDATA devices")
                pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)
            else:
                # 水电煤数据，存储到Backup表里
                pub.sendMessage("publish_save_energy_data", typename=devTypeName, data=newDeviceJsonObj)
                # DBManagerBackup().saveBackupEnergy(devTypeName, newDeviceJsonObj)

    def getAlarmTypeNameByDevTypeId(self, devTypeId, value):
        deviceType = list()
        dType = None
        if DEVTYPEID_SMOKE_SENSOR == devTypeId:  # 烟雾传感器或
            dType = "sensor"
            deviceType.append("火灾报警")
        elif DEVTYPEID_ENVIROMENT_SENSOR == devTypeId:  # 甲醛传感器
            dType = "sensor"
            deviceType.append("环境污染")
        elif DEVTYPEID_EXIST_SENSOR == devTypeId:  # 存在传感器
            dType = "sensor"
            if int(value.get("lvolt")) != None:
                deviceType.append("存在传感器欠压")
            if int(value.get("state")) != None:
                deviceType.append("非法入侵")
        elif DEVTYPEID_CH4CO_SENSOR == devTypeId:  # CH4和CO传感器
            dType = "sensor"
            deviceType.append("煤气超标")
        elif DEVTYPEID_WATER_SENSOR == devTypeId:  # 水侵传感器
            dType = "sensor"
            # deviceType.append("水浸报警")
            if int(value.get("lvolt")) != None:
                deviceType.append("水浸欠压")
            if int(value.get("state")) != None:
                deviceType.append("水浸报警")
        elif DEVTYPEID_FALL_SENSOR == devTypeId:  # 跌倒传感器
            dType = "sensor"
            deviceType.append("跌倒报警")
        elif DEVTYPEID_SOS_SENSOR == devTypeId:  # 一键报警
            dType = "sensor"
            deviceType.append("一键报警")
        elif DEVTYPEID_LOCK == devTypeId:  # 门锁告警
            dType = "sensor"
            if value.get('alarming', 0) == 1:
                if value.get('msg', '') != '':
                    deviceType.append(value.get('msg', ''))
            else:
                deviceType.append("门锁告警")
        elif DEVTYPEID_GSM == devTypeId:    # 门窗磁
            dType = "sensor"
            if int(value.get("lvolt")) != None:
                deviceType.append("门窗磁欠压")
            if int(value.get("state")) != None:
                deviceType.append("门窗磁报警")
        elif DEVTYPEID_CURTAIN_SENSOR == devTypeId:
            dType = "sensor"
            if int(value.get("lvolt")) != None:
                deviceType.append("红外入侵感应器欠压")
            if int(value.get("state")) != None:
                deviceType.append("红外入侵感应器报警")
        elif DEVTYPEID_TABLE_WATER_FILTER == devTypeId:
            if value.has_key("diagnosis"):
                dType = "filter"
                deviceType.append("净水器报警")
        elif DEVTYPEID_AIR_FILTER == devTypeId:
            if value.has_key("pm25"):
                dType = "filter"
                deviceType.append("室内PM2.5超标")

        return (deviceType, dType)
    
    # 报警记录的格式{"name":"light1",addr":"z-1111111","room":"room1","time":"2014-01-01 22:22:00","confirmed":1,"alarming":"1"}
    def processDeviceAlarm(self, devTypeId, deviceRTData):
        # Utils.logInfo("===>processDeviceAlarm, deviceRTData: %s" % deviceRTData)

        devAddr = deviceRTData.get("addr")
        value = deviceRTData.get("value", None)
        devName = deviceRTData.get("name", None)
        devType = deviceRTData.get("type", None) # 设备类型
        # timestamp_new = deviceRTData.get("time", int(time.time()))
        timestamp_old = 0 # 用于接收上一次低电压告警时间出
        
        if value is None or devAddr == "":
            return -1
        # 以下修改为适配存在传感器、幕帘、门窗磁同时有欠压告警和普通告警--20160927-chenjc
        almTypeNames = list()
        almTypeNames, dType = self.getAlarmTypeNameByDevTypeId(devTypeId, value)
        if dType == None:  # 该类型不需要判断报警,表示普通数据
            return 0

        # statusDetail = DBManagerDevice().getDeviceByDevId(devAddr)  # 查询当前传感器状态
        # sensor_state = statusDetail.get("value").get("set", 1)
        for index, almTypeName in enumerate(almTypeNames):
            # 是否取消告警的联动的重复操作
            cancel_process = ""
            name_flag = "欠压" in almTypeName
            try:
                lvoltAlarming = 0
                bCurAlarming = int(value.get("state", "0"))  # 告警状态？state==1为激活状态，0为未激活状态？
                isEnableAlarm = 1  # 是否布防，默认布防
                # 指纹锁取alarming字段
                if devTypeId == DEVTYPEID_LOCK:
                    bCurAlarming = int(value.get("alarming", "0"))
                if devTypeId in [DEVTYPEID_EXIST_SENSOR, DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM, DEVTYPEID_WATER_SENSOR]:
                # if devTypeId in [DEVTYPEID_EXIST_SENSOR, DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM]:
                    # 存在传感器、门窗磁和幕帘(红外入侵感应设备)除了普通告警外还有欠压告警
                    lvoltAlarming = int(value.get("lvolt", "0"))
                # 对于入侵报警，需要同时判断是否设防；只有设防并且状态为1才表示入侵
                # 对于幕帘、门窗磁一样要在设防并且状态为1时才要告警
                if devTypeId in [DEVTYPEID_EXIST_SENSOR, DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM]:
                    # 原代码中先判断了bCurAlarming == 1 20170525 -- chenjc
                    devStatus = DBManagerDevice().getDeviceByDevAddrAndType(devAddr, devType)
                    statusValue = devStatus.get("value", {})
                    isEnableAlarm = int(statusValue.get("set", "0"))
                    # isEnableAlarm = int(value.get("set", "1"))
                    # if isEnableAlarm == 0:
                    #     bCurAlarming = 0
                    #     Utils.logInfo('bCurAlarming2 = %d' % bCurAlarming)
                if devTypeId == DEVTYPEID_TABLE_WATER_FILTER:
                    rawCisternLevel = value.get("rawCisternLevel")
                    rawCisternPos = value.get("rawCisternPos")
                    dewatering = value.get("dewatering")
                    machineState = value.get("machineState")
                    filter1 = value.get("filterLevel1")
                    filter2 = value.get("filterLevel2")
                    filter3 = value.get("filterLevel3")
                    if (rawCisternLevel + rawCisternPos + dewatering + machineState) >= 1 or filter1 <= 10 \
                        or filter2 <= 10 or filter3 <= 10:
                        bCurAlarming = 1
                    else:
                        bCurAlarming = 0
                if devTypeId == DEVTYPEID_AIR_FILTER:
                    pm25 = value.get("pm25")
                    if pm25 >= 75:
                        bCurAlarming = 1
                    else:
                        bCurAlarming = 0
            except:
                Utils.logException("processDeviceAlarm, get alarm state failed")

            # 从本地读取出上次是否有报警
            t = deviceRTData.get("time", int(time.time()))  # 报警产生时间(原先是取不到值则赋值为0)
            produceTime = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
            bLastAlarming = 0
            bConfirmed = 0

            # 从本地缓存中读取报警
            try:
                if name_flag:
                    lastDevAlmRecStr = DBManagerAlarm().getAlarmByDevId(devAddr+"_lvolt")
                else:
                    lastDevAlmRecStr = DBManagerAlarm().getAlarmByDevId(devAddr)
                if lastDevAlmRecStr is not None:

                    # lastDevAlmRec = json.loads(lastDevAlmRecStr)
                    lastDevAlmRec = lastDevAlmRecStr
                    timestamp_old = lastDevAlmRec.get("timestamp", 0)
                    if name_flag:
                        bLastAlarming = int(lastDevAlmRec.get("lvolt", "0"))
                        # bLastAlarming = int(lastDevAlmRec.get("lvoltInforming", "0"))
                    else:
                        bLastAlarming = int(lastDevAlmRec.get("alarming", "0"))
                        produceTime = lastDevAlmRec.get("producetime", "")

                    # produce_time = time.strptime(produceTime, '%Y-%m-%d %H:%M:%S')
                    # produce_time_second = time.mktime(produce_time)
                    produce_time = lastDevAlmRec.get("timestamp", "0")

                    interval = int(t) - int(produce_time)

                    # if devTypeId in [DEVTYPEID_AIR_FILTER, DEVTYPEID_TABLE_WATER_FILTER]:
                    #     if interval <= 1200:  # 空气净化器和台上净水器上报频繁，30分钟内同种告警不重复发送推送
                    #         continue

                    # 所有传感器都会连续不断触发，如果已经处理过一次，下面的忽略
                    # if (name_flag and lvoltAlarming == 1 and bLastAlarming == 1) or \
                    #         (not name_flag and bCurAlarming == 1 and bLastAlarming == 1):
                    if not name_flag and bCurAlarming == 1 and bLastAlarming == 1:
                        # Utils.logInfo("===>repeated sensor alarm...")
                        cancel_process = "cancel"

                    # 如果找到了老的报警，那么产生时间为老的时间
                    bConfirmed = int(lastDevAlmRec.get("confirmed", "0"))

                if name_flag:
                    # 报警状态一致时说明报警不需要处理了
                    if lvoltAlarming == 0 and bLastAlarming == 0:
                        # 不重复报恢复告警
                        continue

                    # 新报警一定是未确认的
                    if lvoltAlarming == 1 and bLastAlarming == 0:
                        bConfirmed = 0

                    if lvoltAlarming == 0:
                        produceTime = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')

                    # 根据时间判断是否是重复的低压告警
                    if lvoltAlarming == 1 and t - timestamp_old <= 4:
                        # 短时间内的重复低压告警，但保存到数据库
                        room_name = ""
                        sensor_prop = DBManagerDeviceProp().getDeviceByAddr(devAddr)
                        if sensor_prop is not None and len(sensor_prop) > 0:
                            room_name = sensor_prop[0].get("roomname", "")

                        newDevAlmRec = {"name": devName, "type": almTypeName, "addr": devAddr + "_lvolt",
                                        "roomname": room_name,
                                        "producetime": produceTime, "confirmed": "%d" % bConfirmed,
                                        "lvolt": "%d" % lvoltAlarming, "alarming": "%d" % lvoltAlarming}
                        DBManagerAlarm().saveAlarm(newDevAlmRec)
                        continue
                else:
                    # 报警状态一致时说明报警不需要处理了
                    if (bCurAlarming == 1 and bLastAlarming == 1) or (bCurAlarming == 0 and bLastAlarming == 0):
                        # 不重复报恢复告警
                        continue

                    # 新报警一定是未确认的
                    if bCurAlarming == 1 and bLastAlarming == 0:
                        bConfirmed = 0

                    if bCurAlarming == 0:
                        produceTime = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')

                sensorAddr = deviceRTData.get("addr", "")
                # 云端报警记录的值
                sensor_prop = DBManagerDeviceProp().getDeviceByAddr(sensorAddr)
                # Utils.logInfo("===>sensor_prop: %s" % sensor_prop)
                room_name = ""
                if sensor_prop is not None and len(sensor_prop) > 0:
                    room_name = sensor_prop[0].get("roomname", "")

                # 暂时将密码和指纹开锁的报警屏蔽掉
                if "外部门开报警" in almTypeName:
                    bCurAlarming = 0

                if devTypeId in [DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM, DEVTYPEID_EXIST_SENSOR, DEVTYPEID_WATER_SENSOR]: # 门窗磁和幕帘有欠压告警
                # if devTypeId in [DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM, DEVTYPEID_EXIST_SENSOR]: # 门窗磁和幕帘有欠压告警
                    # alarmingNum = bCurAlarming
                    # if "欠压" in almTypeName: # 若是欠压告警，alarming设定为lvoltAlarming字段值
                    #     alarmingNum = lvoltAlarming
                    if name_flag:
                        newDevAlmRec = {"name": devName, "type": almTypeName, "addr": sensorAddr+"_lvolt", "roomname": room_name,
                                        "producetime": produceTime, "confirmed": "%d" % bConfirmed,
                                        "lvolt": "%d" % lvoltAlarming, "alarming": "%d" % lvoltAlarming}
                    else:
                        newDevAlmRec = {"name": devName, "type": almTypeName, "addr": sensorAddr, "roomname": room_name,
                                        "producetime": produceTime, "confirmed": "%d" % bConfirmed,
                                        "lvolt": "%d" % lvoltAlarming, "alarming": "%d" % bCurAlarming}
                else:
                    newDevAlmRec = {"name": devName, "type": almTypeName, "addr": sensorAddr, "roomname": room_name,
                                    "producetime": produceTime, "confirmed": "%d" % bConfirmed, "alarming": "%d" % bCurAlarming}

                if name_flag: # 若是欠压告警，alarming设定为lvoltAlarming字段值
                    alarmString = self.makeAlarmString(lvoltAlarming, sensorAddr, devName, almTypeName, produceTime)
                if devTypeId == DEVTYPEID_TABLE_WATER_FILTER:
                    alarmString = self.makeAlarmString(bCurAlarming, sensorAddr, devName, almTypeName, produceTime, value)
                else:
                    alarmString = self.makeAlarmString(bCurAlarming, sensorAddr, devName, almTypeName, produceTime)
                newDevAlmRec['message'] = alarmString

                # 取消联动触发
                if cancel_process != "":
                    newDevAlmRec['cancelProcess'] = cancel_process

                # 如果是存在传感器被触发，添加一个延迟时间
                # if DEVTYPEID_EXIST_SENSOR == devTypeId:
                #     newDevAlmRec["delay"] = 0  # 延迟20秒

                # 更新该条报警记录
                # newDevAlmRecStr = json.dumps(newDevAlmRec)
                # globalVars.localRedis.hset(globalVars.hostKeyAlarm,devAddr,newDevAlmRecStr)
                DBManagerAlarm().saveAlarm(newDevAlmRec)

                bakupAlarmDetailsArr = []
                # newDevAlmRec["addr"] = sensorAddr # 将地址重新置为真实地址(低压告警地址会加后缀 _lvolt)
                bakupAlarmDetailsArr.append(newDevAlmRec)
                # details = json.dumps(bakupAlarmDetailsArr)
                metaDict = {}
                metaDict["type"] = "alarms"
                metaDict["valueStr"] = bakupAlarmDetailsArr
                metaDict["deviceType"] = deviceRTData.get("type", "")
                metaDict["addr"] = devAddr
                metaDict["userList"] = list()

                # 将告警保存到历史数据表
                if cancel_process != "cancel":
                    DBManagerHistory().saveHistoricalAlarm(metaDict)
                if devTypeId in [DEVTYPEID_EXIST_SENSOR, DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM]:
                    if isEnableAlarm == 1:  # 这3种传感器只有布防时候发送告警，但仍要触发联动
                        pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)  # 将告警发往云端
                else:
                    pub.sendMessage(GlobalVars.PUB_SEND_RTDATA, rtdata=metaDict, arg2=None)  # 将告警发往云端

                # 报警状态不同,需要更新报警
                if (name_flag and lvoltAlarming == 0 and bLastAlarming == 1) or \
                        (not name_flag and bCurAlarming == 0):  # 报警恢复
                    # 当前报警已经确认、恢复了，那之前的报警肯定是取到了
                    Utils.logInfo('recover alarms... alarm = 0...addr:%s'%(devAddr))
                    # if(bConfirmed == 1): #报警已恢复且确认，则删除
                    # if name_flag:
                    #     DBManagerAlarm().deleteAlarmByDevId(devAddr+"_lvolt")
                    # else:
                    #     DBManagerAlarm().deleteAlarmByDevId(devAddr)
                    if not name_flag:
                        DBManagerAlarm().deleteAlarmByDevId(devAddr)
                    DBManagerAlarm().deleteAlarmByDevId(devAddr + "_lvolt")
                    # lastDevAlmRec = globalVars.localRedis.hdel(globalVars.hostKeyAlarm,devAddr)

                    newDevAlmRec["action"] = "recover"
                    if devTypeId in [DEVTYPEID_CURTAIN_SENSOR, DEVTYPEID_GSM, DEVTYPEID_EXIST_SENSOR, DEVTYPEID_CH4CO_SENSOR,
                                     DEVTYPEID_SMOKE_SENSOR, DEVTYPEID_ENVIROMENT_SENSOR, DEVTYPEID_OXYGEN_CO2_SENSOR,
                                     DEVTYPEID_SOS_SENSOR, DEVTYPEID_WATER_SENSOR]:
                        pub.sendMessage("cancelAlarm")
                        recover_mode_name = str(devAddr) + "_recover"
                        recover_mode = DBManagerAction().getActionByDevId(recover_mode_name)
                        if recover_mode and not name_flag:
                            modeId = recover_mode.get("modeId")
                            sparam = {"modeId": modeId}
                            pub.sendMessage("door_open", sparam=sparam)
                    # 报警恢复且已确认或未确认都要通知到云
                    # globalVars.publishCmdToLocal(globalVars.cmdType_AlarmToCloud, None)
                else:  # 新的报警产生了
                    Utils.logInfo('produce alarms... alarm = 1...addr:%s' % devAddr)
                    newDevAlmRec["action"] = "produce"
                    # 将报警动作推送到cloudDataAlarmThread中，以便再从本地推送到云上
                    # globalVars.publishCmdToLocal(globalVars.cmdType_AlarmToCloud, newDevAlmRec)
                    # 报警联动动作处理了
                if not name_flag:# 低电压告警不用触发联动配置
                    newDevAlmRec["isEnabled"] = isEnableAlarm
                    self.processAlmLinkActions(newDevAlmRec)
            except:
                Utils.logException("processDeviceAlarm failed")

    def makeAlarmString(self, alarming, addr, devName, almTypeName, produceTime, statusValue=None):
        hostName = ''
        if statusValue:  # 目前只有台上净水器和
            almTypeName = ""
            rawCisternLevel = statusValue.get("rawCisternLevel")
            rawCisternPos = statusValue.get("rawCisternPos")
            dewatering = statusValue.get("dewatering")
            machineState = statusValue.get("machineState")
            filter1 = statusValue.get("filterLevel1")
            filter2 = statusValue.get("filterLevel2")
            filter3 = statusValue.get("filterLevel3")
            if int(machineState) == 1:
                almTypeName += "整机故障"
            if int(rawCisternLevel) == 1:
                if len(almTypeName) == 0:
                    almTypeName += "原水箱缺水"
                else:
                    almTypeName += ",原水箱缺水"
            if int(rawCisternPos) == 1:
                if len(almTypeName) == 0:
                    almTypeName += "原水箱移开"
                else:
                    almTypeName += ",原水箱移开"
            # if int(dewatering) == 1:
            #     if len(almTypeName) == 0:
            #         almTypeName += "排水异常"
            #     else:
            #         almTypeName += ",排水异常"
            if filter1 <= 10 or filter2 <= 10 or filter3 <= 10:
                if len(almTypeName) == 0:
                    almTypeName += "滤芯剩余量过低"
                else:
                    almTypeName += ",滤芯剩余量过低"

        try:
            host = DBManagerHostId().getHost()
            hostName = host.get('name', None)
            if hostName == None:
                hostName = ''
        except:
            hostName = ''

        roomname = ''
        notename = ""
        try:
            devProp = DBManagerDeviceProp().getDeviceByDevId(addr)
            roomId = devProp.get('roomId', None)
            if roomId != None:
                rooms = host.get('room', None)
                if rooms != None:
                    for roomInfo in rooms:
                        if roomInfo.get('roomId', None) == roomId:
                            roomname = roomInfo.get('name', "")
                            notename = devProp.get('note', "")
                            break
        except:
            roomname = '未知房间的'
            notename = ""
            Utils.logException('error when parse device property.')
        if roomname != "":
            msg = '网关'+ hostName + ',' + roomname + ',' + devName + ','
        else:
            msg = '网关' + hostName + ',' + devName + ','
        if len(notename) > 0 and not notename.isspace():
            msg = msg + '(备注：' + notename + '),'
        msg = msg + '发生告警：'+almTypeName + '。(' + produceTime + ')'
        if alarming == 0:
            return msg + '-已恢复-'
        else:
            return msg

    def getDevAddr(self, macAddr):
        # if macAddr[0:2] == 'z-':
        #     return macAddr
        # return "z-" + macAddr
        return macAddr

    # 报警发生时处理联动动作
    # {"alarmactions":{"z-sssss":[{"devicename":"aa",,"addr":"z-11111111","actable":"1", "params": {"state3": "1",
    # "state2": "1", "state": "1", "state4": "1"}]}
    def processAlmLinkActions(self, newDevAlmRec):
        # Utils.logInfo("->processAlmLinkActions(): %s" % newDevAlmRec)

        cancel_process = newDevAlmRec.get("cancelProcess", None)
        if cancel_process is not None and cancel_process == "cancel":
            # Utils.logInfo("===>processAlmLinkActions canceled")
            return

        almAction = newDevAlmRec.get("action", "")
        if(almAction != "produce"):
            return
        devAddr = newDevAlmRec.get("addr", "")
        if(devAddr == ""):
            return 
        
        # globalVars.g_lockAllDeviceInfo.acquire()
        # 找到发生报警的设备
        # almDevice = globalVars.g_allDeviceInfo.get(devAddr, None)
        almDevice = DBManagerAction().getActionByDevId(devAddr)
        # globalVars.g_lockAllDeviceInfo.release()
        # 全局变量只会增删不会修改，所以拿出来即可。即使此时被删除，也不会影响
        if(almDevice == None):
            return
        
        alarmAct = almDevice.get("alarmAct", None)
        if(alarmAct == None):
            return
        
        actDevices = alarmAct.get("actList", None)
        if(actDevices == None or len(actDevices) == 0):
            return
        devicesToCtrol = []
        for actDevice in actDevices:
            actable = actDevice.get("actable", "1")
            if(actable == "0"):
                continue
            #下面是要控制的设备
            actDevAddrTemp = actDevice['deviceAddr']
            if(actDevAddrTemp == ""):
                continue
            else:
                actDevAddrTemp = self.getDevAddr(actDevAddrTemp)
            devtype = actDevice.get("devicetype", "")
            devName = actDevice.get("devicename", "")
            params = actDevice.get("params", "")

            if devtype == DEVTYPENAME_ACOUSTO_OPTIC_ALARM:
                isEnabled = actDevice.get("isEnabled", 1)
                if int(isEnabled) == 0:  # 当传感器撤防时，声光报警器不触发响应
                    continue

            # 删除设备后，报警联动时忽略该设备
            (devId, tmpDevice) = DBManagerDeviceProp().getDeviceByAddrName(actDevAddrTemp, devName)
            if tmpDevice is None:
                continue

            dismiss = tmpDevice.get('dismiss', False)
            if dismiss is True:
                continue
            
            # for i in range(1, 5):
            #     stateStr = ""
            #     if(i == 1):
            #         stateStr = "state"
            #     else:
            #         stateStr = "state" + bytes(i)
            #     stateValue = params.get(stateStr,None)
            #     if(stateValue is None):
            #         continue
            for key in params.keys():
                if 'set' not in key and 'state' not in key and 'coeff' not in key:
                    continue
                singleValue = {}
                v = params.get(key)
                singleValue[key] = v

                devToCtrol = {"name": devName, "addr": actDevAddrTemp, "value": singleValue, "type": devtype}
                if devtype == "AirSystem":
                    singleValue = {"cmd": 2, "data": 0}
                    devToCtrol = {"name": devName, "addr": actDevAddrTemp, "value": singleValue, "type": devtype}
                if devtype == "AirFilter":  # 空气净化器，配置入模式联动触发开机
                    singleValue = {"cmd": 2, "data": 254, "speed": 0, "dataLen": 1}
                    devToCtrol = {"name": devName, "addr": actDevAddrTemp, "value": singleValue, "type": devtype}
                devicesToCtrol.append(devToCtrol)
                # 发送控制命令到ContrlThread,以便在其中执行命令
                # Utils.logDebug("publish alarm-actions.alarm:%s: actions:%s"%(devAddr,devicesToCtrol))
                # globalVars.publishCmdToLocal(globalVars.cmdType_Control, devicesToCtrol)

        # 控制设备的数组创建完毕，发送到ControlThread...
        Utils.logInfo("publish PUB_CONTROL_DEVICE controlDevice :%s"%(devicesToCtrol))
        pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice", controls=devicesToCtrol)

if __name__ == '__main__':
    c1 = HostReportServer(101)
    c2 = HostReportServer(102)
    c2.start()
    time.sleep(5)
    # alarmsDict=[{"water"},{"gas"}]
    # pub.sendMessage(GlobalVars.PUB_ALARM, cmd="confirmAlarms",alarms=alarmsDict)
    
    rtDeviceControl=[{"name":"light","type":"Light1","roomId":"1","room":"测试房","addr":"347D4501004B12001234","value":{"state":"0"}}]
    pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="writeRTData",controls=rtDeviceControl)
    