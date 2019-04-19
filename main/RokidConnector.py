#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import time
import json
import threading

import Utils
from uuid import uuid1
from pubsub import pub
from ThreadBase import *
from PacketParser import *
from DBManagerDeviceProp import DBManagerDeviceProp
from DBManagerDevice import DBManagerDevice
from DBManagerAction import DBManagerAction


SSDP_ADDR = '239.255.255.250'
SSDP_PORT = 1900


# 该类负责通过SSDP协议发现若琪
class SSDPServer(ThreadBase):
    __instant = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls, arg):
        Utils.logDebug("__new__")
        if SSDPServer.__instant is None:
            SSDPServer.__lock.acquire()
            try:
                if SSDPServer.__instant is None:
                    Utils.logDebug("new SSDPServer singleton instance.")
                    SSDPServer.__instant = ThreadBase.__new__(cls)
            finally:
                SSDPServer.__lock.release()
        return SSDPServer.__instant

    def __init__(self, threadId):
        ThreadBase.__init__(self, threadId, "SSDPServer")
        self.__stopped = False
        self.__rokid_addr = None
        self.__thread_hb = None  # SSDP的心跳线程
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.usn_no = Utils.get_mac_address()  # 将网关的Mac作为usn码
        self.local_ip = Utils.getMyIpAddress()  # 本机IP
        any_ip = '0.0.0.0'

        # 绑定到任意地址和SSDP组播端口上
        self.__s.bind((any_ip, SSDP_PORT))

        # INFO: 添加到多播组
        self.__s.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
                            socket.inet_aton(SSDP_ADDR) + socket.inet_aton(self.local_ip))

    def run(self):
        Utils.logInfo('SSDP Server is running...')
        self.init()
        while not self.__stopped:
            data, addr = self.__s.recvfrom(2048)
            self.handle_request(data, addr)

        self.__s.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP,
                            socket.inet_aton(SSDP_ADDR) + socket.inet_aton(self.local_ip))
        self.__s.close()

    def handle_request(self, _data, _addr):
        if _data.startswith('M-SEARCH * HTTP/1.1\r\n'):
            self.__handle_search(_data, _addr)
        # elif _data.startswith('HTTP/1.1 200 OK\r\n'):
        #     self.__handle_ok(_data, _addr)

    def __handle_search(self, _data, _addr):
        props = self.__parse_props(['HOST', 'MAN', 'ST', 'MX'], _data)

        if props:
            if props['HOST'] != '%s:%d' % (SSDP_ADDR, SSDP_PORT) or props['MAN'] != '"ssdp:discover"' \
                    or props['ST'] != 'homebase:device':
                return

            self.__rokid_addr = _addr
            Utils.logDebug('RECV: \n%s' % str(_data))
            Utils.logSuperDebug('Find rokid: %d' % _addr[1])
            Utils.logSuperDebug('==========================================\n')

            response = 'NOTIFY * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nNT: homebase:device\r\n' \
                       'NTS: ssdp:alive\r\nUSN: uuid:%s\r\n' \
                       'LOCATION: tcp://%s:9666\r\nCACHE-CONTROL: max-age=1800\r\n' \
                       'DEVICE_TYPE: bridge' % (self.usn_no, self.local_ip)
            Utils.logDebug('Sending response to Rokid, response: \n%s' % response)
            self.__s.sendto(response, _addr)

            if self.__thread_hb is None:
                self.__heartbeat_thread()
        return

    def __handle_ok(self, _data, _addr):
        props = self.__parse_props(['ST'], _data)
        if not props:
            return

        Utils.logDebug(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        Utils.logDebug('RECV: %s' % str(_data))
        Utils.logDebug('ADDR: %s' % str(_addr))
        Utils.logDebug('Find service!!!!')

        self.is_find_service = True

    def __parse_props(self, target_keys, _data):
        lines = _data.split('\r\n')
        props = {}

        for line in lines:
            if line:
                index = line.find(':')
                if index:
                    props[line[:index]] = line[index + 1:].strip()

        if set(target_keys).issubset(set(props.keys())):
            return props

        return {}

        # for i in range(1, len(lines)):
        #     if not lines[i]:
        #         continue
        #
        #     index = lines[i].find(':')
        #     if index == -1:
        #         # return None
        #         return {}
        #
        #     props[lines[i][:index]] = lines[i][index + 1:].strip()
        #
        # if not set(target_keys).issubset(set(props.keys())):
        #     # return None
        #     return {}
        #
        # return props

    def __send_alive(self, target_addr=None):
        if target_addr is None:
            target_addr = self.__rokid_addr

        # NOTIFY * HTTP/1.1
        # HOST: 239.255.255.250:1900
        # NT: homebase:device
        # NTS: ssdp:alive
        # USN: uuid:f40c2981-7329-40b7-8b04-27f187aecfb8
        # LOCATION: http://10.0.0.107:10293
        # CACHE-CONTROL: max-age=1800
        # DEVICE_TYPE: bridge
        # SERVER: UPnP/1.1 homebase-ssdp/1.0.0

        heartbeat = 'NOTIFY * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nNT: homebase:device\r\n' \
                    'USN: uuid:%s\r\nLOCATION: tcp://%s:9666\r\n' \
                    'CACHE-CONTROL: max-age=1800\r\nDEVICE_TYPE: bridge\r\n' \
                    'SERVER: UPnP/1.1 homebase-ssdp/1.0.0' % (self.usn_no, self.local_ip)

        while not self.__stopped:  # 此处的stopped应该使用启动主线程的self._stopped
            Utils.logDebug('>>>>>>>>>>>>>>> %s <<<<<<<<<<<<<<<<' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
            Utils.logSuperDebug('Sending heartbeat to Rokid...')
            Utils.logSuperDebug('===================================')
            self.__s.sendto(heartbeat, target_addr)
            time.sleep(1800)

    def __heartbeat_thread(self):
        self.__thread_hb = threading.Thread(target=self.__send_alive, args=(self.__rokid_addr,))
        self.__thread_hb.setDaemon(True)
        self.__thread_hb.start()

    def stop(self):
        self.__stopped = True


# 该类负责接收若琪发送的查询、控制命令，并将命令转换成主机命令发送给主机
class RokidBridgeServer(ThreadBase):
    __instant = None
    __lock = threading.Lock()

    _server = None
    _ip = None
    _port = None

    _device_type_list = [DEVTYPENAME_LIGHT1, DEVTYPENAME_LIGHT2, DEVTYPENAME_LIGHT3, DEVTYPENAME_LIGHT4,
                         DEVTYPENAME_LIGHTAJUST, DEVTYPENAME_CURTAIN, DEVTYPENAME_SOCKET, DEVTYPENAME_FLOOR_HEATING,
                         DEVTYPENAME_TV, DEVTYPENAME_AIRCONDITION, DEVTYPENAME_AUDIO]

    # _device_type_enum = {
    #     "L1": DEVTYPENAME_LIGHT1, "L2": DEVTYPENAME_LIGHT2, "L3": DEVTYPENAME_LIGHT3,
    #     "L4": DEVTYPENAME_LIGHT4, "LA": DEVTYPENAME_LIGHTAJUST, "CT": DEVTYPENAME_CURTAIN,
    #     "SK": DEVTYPENAME_SOCKET, "AF": DEVTYPENAME_AIR_FILTER, "FH": DEVTYPENAME_FLOOR_HEATING,
    #     "TV": DEVTYPENAME_TV, "AC": DEVTYPENAME_AIRCONDITION, "AD": DEVTYPENAME_AUDIO
    # }

    # singleton
    def __new__(cls, arg):
        Utils.logDebug("__new__")
        if RokidBridgeServer.__instant is None:
            RokidBridgeServer.__lock.acquire()
            try:
                if RokidBridgeServer.__instant is None:
                    Utils.logDebug("new RokidConnector singleton instance.")
                    RokidBridgeServer.__instant = ThreadBase.__new__(cls)
            finally:
                RokidBridgeServer.__lock.release()
        return RokidBridgeServer.__instant

    def __init__(self, threadId):
        ThreadBase.__init__(self, threadId, "RokidBridgeServer")
        self._ip = Utils.getMyIpAddress()
        self._port = 9666
        self._stopped = False

        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # 绑定
        self._server.bind((self._ip, self._port))
        self._server.listen(3)

    def run(self):
        self.init()
        self.receiving_command()

    # 接收来自Rokid的命令数据
    def receiving_command(self):
        while not self._stopped:
            try:
                if self._server is None:
                    self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    # self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

                    # 绑定
                    self._server.bind((self._ip, self._port))
                    self._server.listen(3)

                Utils.logSuperDebug('RokidBridgeServer waiting for connecting...')
                client, client_addr = self._server.accept()
                Utils.logInfo('Client accepted...')

                while not self._stopped:
                    Utils.logInfo('Waiting for commands...')
                    try:
                        data = client.recv(1024 * 5)

                        Utils.logDebug('Data received, data: %s' % data)

                        if data == '':
                            client.close()
                            # client.shutdown(2)
                            # client = None
                            break

                        if data is None or len(data) <= 0:
                            time.sleep(.5)
                            continue

                        rtn = self.parse_data(data)
                        if rtn:
                            Utils.logDebug('sending return message: %s' % rtn)
                            client.send(rtn)

                    except Exception as e:
                        Utils.logError('===>>> 111111Error===> %s' % e.message)
                        continue

            except Exception as e:
                Utils.logError('===>>> 222222Error===> %s' % e.message)
                continue

    # 根据JSON-RPC规则解析收到的数据
    def parse_data(self, data):
        data = json.loads(data)

        method = data.get('method')
        if method == 'list':
            return self.handle_list(data)
        elif method == 'get':
            return self.handle_get(data)
        elif method == 'execute':
            return self.handle_execute(data)
        else:
            return None

    # 处理list命令
    def handle_list(self, data):
        # 生成返回内容的大致结构
        uid = uuid1()
        rtn = {'jsonrpc': '2.0', 'id': data.get('id', str(uid))}

        # 查询设备信息列表返回
        dev_info = DBManagerDeviceProp().getAllDevicesForRokid()
        dev_list = dev_info.get('devList', [])
        dev_addrs = dev_info.get('addrList', [])
        dev_status = DBManagerDevice().getDeviceStatusForRokid(dev_addrs)
        for dev in dev_list:
            addr = dev.get('addr')
            state = dev_status.get(addr, {'switch': 'off'})
            dev['state'] = state

        rtn_list = self.generate_device_list(dev_list)
        mode_list = DBManagerAction().getModeForRokid()
        rtn_list.extend(mode_list)
        rtn['result'] = rtn_list
        Utils.logSuperDebug('sending device list to Rokid,length=%d' % len(rtn_list))
        return json.dumps(rtn)

    # 处理get命令
    def handle_get(self, data):
        # TODO 查询设备状态并返回
        return json.dumps({})

    # 处理execute命令
    def handle_execute(self, data):
        # 生成返回内容的大致结构
        uid = uuid1()
        rtn = {'jsonrpc': '2.0', 'id': data.get('id', str(uid))}

        Utils.logDebug("The control command is: %s" % str(data))
        # 根据执行命令返回内容
        params = data.get('params')
        if params:
            deviceFromRokid = params.get('device')
            if deviceFromRokid:
                cmd_type = deviceFromRokid.get('type')
                if cmd_type == 'scene':
                    # 触发模式命令
                    Utils.logDebug('Activating mode....')
                    mode_id = deviceFromRokid.get('deviceId', '')
                    mode_id = mode_id[mode_id.rfind('_') + 1:]
                    sparam = {"modeId": mode_id}
                    pub.sendMessage("door_open", sparam=sparam)

                else:
                    # 生成设备控制命令
                    Utils.logDebug('Controlling device....')
                    controlParam = self._generate_cmd(params)
                    if controlParam:
                        pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice", controls=[controlParam])

        rtn['result'] = {'switch': 'on'}
        return json.dumps(rtn)

    def _generate_cmd(self, params):
        # {"addr":"z-11111111","type":"Light","value":{"state":"1","coeff":"0"}}
        # 设备相关信息
        deviceprop = params.get('device')
        devAddr = deviceprop.get('deviceId')
        if '_' in devAddr:
            devAddr = devAddr[: devAddr.rfind('_')]

        deviceInfo = deviceprop.get('deviceInfo', {})
        devType = deviceInfo.get('type', None)  # 网关系统内的设备类型
        if devType is None:
            # 如果设备类型在 deviceInfo 内没取到则查询数据库获得
            devDetail = DBManagerDeviceProp().getDeviceByAddr(devAddr)[0]
            devType = devDetail.get('type')

        # 控制相关信息
        actions = params.get('action', {})
        operation = actions.get('property')
        op_state = actions.get('name')
        state = "0"
        if op_state == 'on':
            state = "1"
        else:
            state = "0"

        value = {}
        param = {"addr": devAddr, "type": devType}

        if devType in [DEVTYPENAME_LIGHT1, DEVTYPENAME_SOCKET]:
            value["state"] = state

        elif devType in [DEVTYPENAME_LIGHT2, DEVTYPENAME_LIGHT3, DEVTYPENAME_LIGHT4]:
            index = deviceInfo.get('index', 1)

            if index == 1:
                value['state'] = state
            else:
                value['state{}'.format(index)] = state

        elif devType == DEVTYPENAME_LIGHTAJUST:
            coeff = 100
            if operation == 'switch':
                if op_state == 'on':
                    state = '1'
                else:
                    state = '0'
                coeff = '100'

            elif operation == 'brightness':
                if op_state == 'up':
                    statusObj = DBManagerDevice().getDeviceByDevId(devAddr)
                    value = statusObj.get('value', {})
                    if value:
                        coeffInDb = int(value.get('coeff', '100'))
                        if coeffInDb + 25 > 100:
                            coeff = 100
                        else:
                            coeff = coeffInDb + 25

                elif op_state == 'down':
                    statusObj = DBManagerDevice().getDeviceByDevId(devAddr)
                    value = statusObj.get('value', {})
                    if value:
                        coeffInDb = int(value.get('coeff', '100'))
                        if coeffInDb - 25 < 10:
                            coeff = 10
                        else:
                            coeff = coeffInDb - 25

                elif op_state == 'max':
                    coeff = '100'

                elif op_state == 'min':
                    coeff = '10'

                else:
                    coeff = actions.get('value', '100')
                state = '1'

            value['state'] = state
            value['coeff'] = str(coeff)

        elif devType == DEVTYPENAME_CURTAIN:
            if op_state == 'on':
                state = '1'
            elif op_state == 'off':
                state = '2'  # 关
            elif op_state == 'stop':
                state = '3'  # 暂停
            value['state'] = state

        # elif devType == DEVTYPENAME_AIR_FILTER:  # iCasa没有空气净化器
        #     # {"addr":"z-11111111","type":"Light","value":{"state":"1","coeff":"0"}}
        #     if operation == 'switch':
        #         # 开关机命令
        #         value['cmd'] = 2
        #         value['dataLen'] = 1
        #         if op_state == 'on':
        #             # 开机
        #             value['data'] = 254
        #         else:
        #             value['data'] = 255
        #     elif operation == 'mode':
        #         # 切换模式
        #         value['cmd'] = 2
        #         value['dataLen'] = 1
        #         if op_state == 'auto':
        #             # 自动模式
        #             value['data'] = 3
        #         elif op_state == 'sleep':
        #             # 睡眠模式
        #             value['data'] = 2
        #     elif operation == 'fanspeed':
        #         # 手动模式，调节风速
        #         value['cmd'] = 2
        #         value['dataLen'] = 1
        #         value['data'] = 4
        #         if op_state == 'up':
        #             # 调高风速
        #             devStatus = DBManagerDevice().getDeviceByDevId(devAddr)
        #             fanSpeed = int(devStatus.get('value').get('rate'))
        #             value['speed'] = fanSpeed + 2
        #         elif op_state == 'down':
        #             # 调低风速
        #             devStatus = DBManagerDevice().getDeviceByDevId(devAddr)
        #             fanSpeed = int(devStatus.get('value').get('rate'))
        #             value['speed'] = fanSpeed - 2
        #         elif op_state == 'max':
        #             # 最大风速
        #             value['speed'] = 100
        #         elif op_state == 'min':
        #             # 最小风速
        #             value['speed'] = 10
        #         else:
        #             fanSpeed = actions.get('value', '80')
        #             value['speed'] = int(fanSpeed)

        elif devType == DEVTYPENAME_FLOOR_HEATING:
            if operation == 'switch':
                # 开关机命令
                value['cmd'] = 1
                value['dataLen'] = state
            elif operation == 'temperature':
                value['cmd'] = 2
                if op_state == 'up':
                    devStatus = DBManagerDevice().getDeviceByDevId(devAddr)
                    temp = float(devStatus.get('value').get('setTemp'))
                    value['data'] = temp + 0.5
                elif op_state == 'down':
                    devStatus = DBManagerDevice().getDeviceByDevId(devAddr)
                    temp = float(devStatus.get('value').get('setTemp'))
                    value['data'] = temp - 0.5
                elif op_state == 'min':
                    value['data'] = 5.0
                elif op_state == 'max':
                    value['data'] = 35.0
                else:
                    temperature = actions.get('value', '25.0')
                    value['data'] = float(temperature)

        elif devType == DEVTYPENAME_AIRCONDITION:
            acObj = DBManagerDeviceProp().getDeviceByDevAddrAndType(devAddr, DEVTYPENAME_AIRCONDITION)
            Utils.logDebug('acObj: %s' % str(acObj))
            # 风速, 开关,  模式,   风向,  操作标记, 温度
            cWind, cOnoff, cMode, cWinddir, cKey, cTemp = 0, 0, 0, 0, 0, 25
            if acObj:
                acData = acObj.get('AcData', None)
                remoteInfo = acObj.get('remoteInfo', {})
                keySquency = remoteInfo.get('m_key_squency')
                index = remoteInfo.get('index')
                if acData:  # 先取出数据库内已有的
                    cWind = int(acData.get('cWind', 0))
                    cOnoff = int(acData.get('cOnoff', 0))
                    cMode = int(acData.get('cMode', 0))
                    cWinddir = int(acData.get('cWinddir', 0))
                    cKey = int(acData.get('cKey', 0))
                    cTemp = int(acData.get('cTemp', 25))

                if operation == 'switch':
                    cKey = 0
                    if op_state == 'on':
                        cOnoff = 0
                        acData['isOn'] = '1'
                    else:
                        cOnoff = 1
                        acData['isOn'] = '2'

                    acData['cOnoff'] = str(cOnoff)

                elif operation == 'temperature':
                    cKey = 2
                    temp = int(acData.get('temp')) - 16  # 根据红外文档：16-30度  0=16 。。。。 14=30
                    if op_state == 'up':
                        # 调高1度
                        cTemp = temp + 1
                    elif op_state == 'down':
                        # 调低1度
                        cTemp = temp - 1
                    else:
                        # 调到具体某一个温度
                        cTemp = int(actions.get('value', 25)) - 16  # 根据红外文档：16-30度  0=16 。。。。 14=30

                    acData['cTemp'] = str(cTemp)
                    acData['temp'] = str(cTemp + 16)  # 根据红外文档：16-30度  0=16 。。。。 14=30

                elif operation == 'fanspeed':
                    cKey = 3
                    wind = int(acData.get('wind'))
                    if op_state == 'up':
                        # 调高风速
                        cWind = wind + 1
                        if cWind > 3:
                            cWind = 3
                    elif op_state == 'down':
                        # 调低风速
                        cWind = wind - 1
                        if cWind < 0:
                            cWind = 1
                    elif op_state == 'min':
                        cWind = 1
                    elif op_state == 'max':
                        cWind = 3

                    acData['cWind'] = str(cWind)
                    acData['wind'] = str(cWind)

                elif operation == 'mode':
                    # 空调模式
                    cKey = 1
                    if op_state == 'auto':
                        cMode = 0
                        cTemp = 9  # 自动模式温度切换到25度
                        acData['mode'] = '4'
                    elif op_state == 'heat':
                        cMode = 4
                        cTemp = 9  # 制热模式，温度切换到25度
                        acData['mode'] = '2'
                    elif op_state == 'fan':
                        cMode = 3
                        acData['mode'] = '3'
                    elif op_state == 'cool':
                        cMode = 1
                        cTemp = 9  # 制冷模式，温度切换到25度
                        acData['mode'] = '1'

                    acData['cMode'] = str(cMode)
                    acData['cTemp'] = str(cTemp)
                    acData['temp'] = str(cTemp + 16)  # 根据红外文档：16-30度  0=16 。。。。 14=30

                elif operation == 'swing_mode':
                    if op_state == 'horizon':
                        # 水平方向
                        cWinddir = 2
                    elif op_state == 'vertical':
                        # 垂直方向
                        cWinddir = 3

                    acData['cWinddir'] = str(cWinddir)
                    acData['windDir'] = str(cWinddir)

                acData['cKey'] = str(cKey)

                if int(keySquency) == 15000:
                    # 15000类型的码库
                    index = cOnoff * 7500 + cMode * 1500 + cTemp * 100 + cWind * 25 + cWinddir * 5 + cKey + 1
                elif int(keySquency) == 3000:
                    # 3000类型的码库
                    index = cOnoff * 1500 + cMode * 300 + cTemp * 20 + cWind * 5 + cWinddir + 1
                else:
                    # 不支持的类型
                    return None

                param['extraCmd'] = 'newInfrared'
                remoteInfo['index'] = str(index)
                param['value'] = remoteInfo
                param['AcData'] = acData

                # 准备保存新的空调状态
                acObj['AcData'] = acData
                acObj['remoteInfo'] = remoteInfo
                DBManagerDeviceProp().saveDeviceProperty(acObj)  # 保存模式触发的空调状态
                return param

            else:
                # 数据库没有这个空调设备就直接回空
                return None

        elif devType == DEVTYPENAME_TV:
            tvObj = DBManagerDeviceProp().getDeviceByDevAddrAndType(devAddr, DEVTYPENAME_TV)
            Utils.logDebug('tv obj: %s' % str(tvObj))
            if tvObj:
                remoteInfo = tvObj.get('remoteInfo', {})
                index = '1'
                if operation == 'switch':
                    # 网关内使用的码库电视开关机取反码，数值一样
                    index = '1'

                elif operation == 'volume':
                    if op_state == 'up':
                        index = '34'
                    elif op_state == 'down':
                        index = '35'

                param['extraCmd'] = 'newInfrared'
                remoteInfo['index'] = str(index)
                param['value'] = remoteInfo
                return param

            else:
                # 数据库没有这个电视设备就直接回空
                return None

        param['value'] = value
        return param

    # 生成一个设备列表
    def generate_device_list(self, dev_list):
        # 查询设备列表，并根据若琪的文档生成JSON-RPC报文返回
        device_list = []

        for dev in dev_list:
            devObj = dict()
            dev_type = dev.get('type')
            state = dev.get('state')
            name = dev.get('name')
            d_addr = dev.get('addr')
            if dev_type not in self._device_type_list:
                # 过滤掉Rokid不支持的设备
                continue

            if dev_type in [DEVTYPENAME_LIGHT1, DEVTYPENAME_LIGHT2, DEVTYPENAME_LIGHT3, DEVTYPENAME_LIGHT4]:
                # 灯，根据路数生成多路灯
                self._generate_lignt_info(dev, device_list)
                continue
            elif dev_type == DEVTYPENAME_LIGHTAJUST:
                actions = {'switch': ['on', 'off'],
                           'brightness':  ['up', 'down', 'max', 'min', 'num']}
                tp = 'light'
            elif dev_type == DEVTYPENAME_SOCKET:
                actions = {'switch': ['on', 'off']}
                tp = 'socket'
            elif dev_type == DEVTYPENAME_CURTAIN:
                actions = {'switch': ['on', 'off', 'stop']}
                tp = 'curtain'
            # elif dev_type == DEVTYPENAME_AIR_FILTER:  # iCasa没有空气净化器
            #     actions = {'switch': ['on', 'off'],
            #                'mode':  ['auto', 'manual', 'sleep'],
            #                'fanspeed': ['up', 'down', 'max', 'min', 'num']}
                tp = 'airPurifier'
            elif dev_type == DEVTYPENAME_FLOOR_HEATING:
                actions = {'switch': ['on', 'off'],
                           'temperature': ['up', 'down', 'min', 'max', 'num']}
                tp = 'floorHeater'
            elif dev_type == DEVTYPENAME_AIRCONDITION:
                actions = {'switch': ['on', 'off'],
                           'temperature': ['up', 'down', 'num'],
                           'fanspeed': ['up', 'down', 'min', 'max'],
                           'mode': ['auto', 'heat', 'fan', 'cool'],
                           'swing_mode': ['horizon', 'vertical']}
                d_addr = d_addr + '_AC'
                tp = 'ac'
            elif dev_type == DEVTYPENAME_TV:
                actions = {'switch': ['on', 'off'],
                           'volume': ['up', 'down']}
                d_addr = d_addr + '_TV'
                tp = 'tv'

            deviceInfo = {'type': dev_type}  # 把网关上使用的设备类型放到若琪报文的deviceInfo里面，在处理 get命令时可以用来根据这个字段查询
            devObj['state'] = state
            devObj['type'] = tp
            devObj['name'] = name
            devObj['offline'] = False
            devObj['actions'] = actions
            devObj['deviceId'] = d_addr
            devObj['deviceInfo'] = deviceInfo
            device_list.append(devObj)

        return device_list

    def stop(self):
        self._stopped = True

    # 参数说明：
    #           dev -- 设备信息对象
    #           dev_list -- 整体的设备信息列表
    def _generate_lignt_info(self, dev, dev_list):
        d_type = dev.get('type')
        d_addr = dev.get('addr')
        light_names = dev.get('lightName', {})
        lightName = dev.get('name', '{}联灯'.format(self._castNumToCn(d_type[-1], d_type)))
        roomName = dev.get('roomname', '')

        if d_type == DEVTYPENAME_LIGHT1:
            deviceInfo = {'type': d_type}
            devObj = dict()
            state = dev.get('state')
            actions = {'switch': ['on', 'off']}
            deviceInfo['index'] = 1
            devObj['state'] = state
            devObj['type'] = 'light'
            devObj['name'] = lightName
            devObj['offline'] = False
            devObj['actions'] = actions
            devObj['deviceId'] = d_addr
            devObj['deviceInfo'] = deviceInfo
            devObj['parent'] = d_addr  # 单联灯的母设备就是它本身
            dev_list.append(devObj)
            return

        endNum = int(d_type[-1]) + 1
        for i in range(1, endNum):
            deviceInfo = {'type': d_type}
            devObj = dict()
            nameKey = 'name%d' % i
            name = light_names.get(nameKey)
            if not name:
                name = lightName + '第{}路灯'.format(self._castNumToCn(i, d_type))
            state = dev.get('state')
            actions = {'switch': ['on', 'off']}
            deviceInfo['index'] = i
            devObj['state'] = state
            devObj['type'] = 'light'
            devObj['name'] = name
            devObj['offline'] = False
            devObj['actions'] = actions
            devObj['deviceId'] = "%s_%d" % (d_addr, i)
            devObj['deviceInfo'] = deviceInfo
            devObj['parent'] = d_addr
            dev_list.append(devObj)

    def _castNumToCn(self, num, dev_type):
        if int(num) > 4:
            return "四"
        else:
            if dev_type == 'Light1':
                num_dic = {"1": "单", "2": "二", "3": "三", "4": "四"}
            else:
                num_dic = {"1": "一", "2": "二", "3": "三", "4": "四"}
            return num_dic.get(str(num))

# 负责与Rokid通讯的线程类  貌似实际上没用到
class RokidConnector(ThreadBase):
    __instant = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls, arg):
        Utils.logDebug("__new__")
        if RokidConnector.__instant is None:
            RokidConnector.__lock.acquire()
            try:
                if RokidConnector.__instant is None:
                    Utils.logDebug("new RokidConnector singleton instance.")
                    RokidConnector.__instant = ThreadBase.__new__(cls)
            finally:
                RokidConnector.__lock.release()
        return RokidConnector.__instant

    def __init__(self, threadId):
        ThreadBase.__init__(self, threadId, "RokidConnector")
        self.ssdpServer = SSDPServer()
        self.rokidBridgeServer = RokidBridgeServer()
        self.ssdpServerThread = None  # SSDP Server线程
        self.bridgeServerThread = None  # Rokid TCP Server线程

    def run(self):
        self.init()
        # 线程启动SSDPServer和RokidBridgeServer
        # 根据Rokid文档，先启动TCP协议的BridgeServer
        if self.bridgeServerThread is None:
            self.bridgeServerThread = threading.Thread(target=self.rokidBridgeServer.receiving_command)
            self.bridgeServerThread.setDaemon(True)
            self.bridgeServerThread.start()
        time.sleep(0.5)

        # 再启动SSDP准备发现Rokid
        if self.ssdpServerThread is None:
            self.ssdpServerThread = threading.Thread(target=self.ssdpServer.start)
            self.ssdpServerThread.setDaemon(True)
            self.ssdpServerThread.start()

    def stop(self):
        self.ssdpServer.stop()
        self.rokidBridgeServer.stop()
        self.ssdpServerThread = None
        self.bridgeServerThread = None
