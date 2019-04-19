# -*- coding: utf-8 -*-

import hashlib
import json
import GlobalVars
import Utils
from WebHandlerBase import *
from PacketParser import *
from WiseMusic import get_media_list


HEADER_LEN     = 5  # 起始码    事务号    命令字    数据长度(2)
TAILER_LEN     = 2  # 校验和    结束符
HEADERTAIL_LEN = (HEADER_LEN + TAILER_LEN)  # 起始码    事务号    命令字    数据长度       校验和    结束符


class DeviceHandler(WebHandlerBase):

    # 设备关联
    def link(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_LINK_DEVICES, sparam)
        return self.successWithMsg(buf)

    # 查询设备关联表
    def querylink(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_DEVICES_LINKS, sparam)
        return self.successWithMsg(buf)

    # 控制
    def cmd(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_CONTROL_DEVICE, sparam)
        return self.successWithMsg(buf)
    ##
    def remove(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_REMOVE_DEVICE, sparam)
        return self.successWithMsg(buf)
    ##
    def dismiss(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_DISMISS_DEVICE, sparam)
        return self.successWithMsg(buf)
    ##
    def updateprop(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_UPDATE_DEVICE, sparam)
        return self.successWithMsg(buf)

    ##
    def properties(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_DEVICES, sparam)
        return self.successWithMsg(buf)

    ##
    def status(self, sparam):
        Utils.logDebug("show device status")
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_DEVICES_STATUS, sparam)
        return self.successWithMsg(buf)

    def scan(self, sparam):
        Utils.logDebug("scan devices")
        # buf = self.sendCommand(-1, sparam)
        metaDict={}
        try:
            (result, response) = self._scanZigbee(sparam)
            metaDict["ret"] = result
            if response is not None:
                metaDict["response"] = response
        except:
            pass
        return self.successWithMsg(json.dumps(metaDict))

    def queryOneProp(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_ONE_DEVICE_PROP, param)
        return self.successWithMsg(buf)

    def configHgc(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_HCG_CONFIG, param)
        return self.successWithMsg(buf)

    def deleteHgcConfig(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_HCG_DELETE_CONFIG, param)
        return self.successWithMsg(buf)

    def queryHgcConfig(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_HCG_QUERY_CONFIG, param)
        return self.successWithMsg(buf)

    def queryMeterAddr(self, param):
        Utils.logDebug("===>query meter addr, param: %s" % param)
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_METER_ADDRS, param)
        return self.successWithMsg(buf)

    def modifyMeterName(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_MODIFY_METER_NAME, param)
        return self.successWithMsg(buf)

    def queryAllDevices(self, param):
        Utils.logDebug("===>query all devices, param: %s" % param)
        buf = self.sendCommand(GlobalVars.TYPE_CMD_READ_ALL_DEVICE, param)
        return self.successWithMsg(buf)

    def setFloorHeatingTimeTask(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_SET_FLOOR_HEATING_TIME_TASK, param)
        return self.successWithMsg(buf)

    def switchFloorHeatingTimeTask(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_SWITCH_FLOOR_HEATING_TIME_TASK, param)
        return self.successWithMsg(buf)

    def queryWiseMediaList(self, param):
        # buf = self.sendCommand(GlobalVars.TYPE_CMD_WISE_LIST, param)
        start = param.get("from", 0)
        end = param.get("to", None)
        if end is not None:
            end = int(end)

        song_list = get_media_list(int(start), end)
        if song_list:
            song_dict = {"songList": song_list}
            metaDict = dict(ret=ErrorCode.SUCCESS)
            metaDict['response'] = song_dict
            dataMD5 = hashlib.md5(json.dumps(song_dict)).hexdigest()
            metaDict['md5'] = dataMD5
            buf = json.dumps(metaDict)
            return self.successWithMsg(buf)
        else:
            return self.failWithMsg("歌曲列表为空")

    def startScanBatch(self, param):
        Utils.logDebug("--------------- startScanBatch ---------------")  # debug
        buf = self.sendCommand(GlobalVars.TYPE_CMD_START_SCAN_BATCH, param)
        return self.successWithMsg(buf)

    def stopScanBatch(self, param):
        Utils.logDebug("--------------- stopScanBatch ---------------")  # debug
        buf = self.sendCommand(GlobalVars.TYPE_CMD_STOP_SCAN_BATCH, param)
        return self.successWithMsg(buf)

    def queryDeviceBatch(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_BATCH_DEVICE, param)
        return self.successWithMsg(buf)

    def saveDeviceBatch(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_SAVE_BATCH_DEVICE, param)
        return self.successWithMsg(buf)


    # 扫描设备
    def _scanZigbee(self, params):
        # Utils.logError('----begin------_scanZigbee=params=%s**************' % str(params))
        if params == None:
            return (ErrorCode.SUCCESS, None)
        Utils.logInfo('Request to scan devices...%s'%(params))
        typeName = params.get("type", None)
        if typeName == None:
            return (ErrorCode.SUCCESS, None)

        reqDevTypeId = PacketParser.getDeviceTypeIdByName(typeName)
        # Utils.logError('----------_scanZigbee=reqDevTypeId=%s**************' % str(reqDevTypeId))
        # transId = 1
                                        # 包号为1时表示单个扫描  20170314
        buffer = struct.pack("=3BH25B2B",0x68,1,0x03,0x19,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0x1C,0xED)
        localSvrAddr = ('127.0.0.1', 8899)
        timeout = 3
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        try:
            sock.connect(localSvrAddr)
        except:
            return (ErrorCode.SUCCESS, None)

        try:
            nSent = sock.send(buffer)
        except:
            Utils.logException('Send request to driver failed.')
            sock.shutdown(2)
            sock.close()
            return (ErrorCode.SUCCESS, None)

        retval = -1
        onePackBuffer = ""

        beginTime = time.time()
        recvTotalBuffer = ""
        while(True):
            try:
                Utils.logInfo('Start receiving response from driver')
                recvBuffer = sock.recv(2048)
                if(recvBuffer is not None and len(recvBuffer) > 0):
                    recvTotalBuffer += recvBuffer

                retval, onePackBuffer = self._GetAPackFromBuffer(recvTotalBuffer)
                if(retval == -1 or retval == 1):  # 有一个完整的包,后者发生异常
                     break
            except:
                Utils.logException('Failed to receive response from driver')
                break

            nowTime = time.time()
            if(nowTime - beginTime > timeout) :  # 大于2秒
                retval = -1
                onePackBuffer = "超时未收到应答"
                break
        # 关闭socket
        sock.shutdown(2)
        sock.close()

        # 错误时给出提示
        if(retval == -1):
            return (ErrorCode.SUCCESS, None)

        Utils.logInfo('rx scan device response.')
        devices = []
        bodyLen = len(onePackBuffer)
        devNum = int(bodyLen / 25)
        bodyBuffer = recvTotalBuffer[5:devNum * 25 + 5]
        for i in range(0,devNum,1):
            device = {}
            oneDevBuffer = bodyBuffer[i*25:i*25+25]
            macAddr,phyTypeid = struct.unpack("=10sB",oneDevBuffer[0:11])

            # Utils.logError('----------_scanZigbee=macAddr=%s**************' % str(macAddr))
            # Utils.logError('----------_scanZigbee=phyTypeid=%s**************' % str(phyTypeid))

            swverion, hwversion = struct.unpack("=2B", oneDevBuffer[-2:])
            numbers = struct.unpack("=10B", macAddr)
            devAddr = "%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X" % numbers
            if(phyTypeid == 0x03):  # 红外就是0x03
                # Utils.logError('----------_scanZigbee0---------0x03**********')

                # macAddr,phyTypeid,cmd,logTypeId = struct.unpack("=10sB2B",oneDevBuffer[0:13])
                # logTypeId = logTypeId + DEVTYPEID_INFRARED_DEV_MIN
                if(reqDevTypeId < DEVTYPEID_INFRARED_DEV_MIN or reqDevTypeId > DEVTYPEID_INFRARED_DEV_MAX):
                    continue
                # if(logTypeId != reqDevTypeId):
                #     continue
            # 如果是中控设备，还要判断是否接入了地暖
            elif phyTypeid == 0x51:
                # Utils.logError('----------_scanZigbee0---------0x51**********')

                device["extraDevice"] = ""
                extra_device = struct.unpack("=B", oneDevBuffer[12])
                # 1为3.5寸，2为地暖
                if extra_device[0] == 2:
                    device["extraDevice"] = "FloorHeating"
            elif phyTypeid == 0x52:  # 新地暖分水暖和电暖 20180910
                # Utils.logError('----------_scanZigbee0---------0x52**********')
                heating_type = struct.unpack("=B", oneDevBuffer[12])
                Utils.logDebug("Heating type is %d" % heating_type)
                device["heaterType"] = heating_type[0]  # 1-水地暖，2-电地暖，水暖只有开关和设置温度，电地暖多几个控制指令2018-0910
            else:
                if(typeName != "" and reqDevTypeId != phyTypeid):
                    continue

            device["id"] = devAddr
            device["name"] = devAddr
            device["softwareVer"] = Utils.calculateVersion(swverion)    # device software version
            device["hardwareVer"] = Utils.calculateVersion(hwversion)   # device hardware version
            devices.append(device)
            # Utils.logError('-----end-----_scanZigbee=devices=%s**************' % str(devices))

        Utils.logInfo('scan response: %s'%(devices))
        return (ErrorCode.SUCCESS, devices)

    def _GetAPackFromBuffer(self,recvBuffer):
        onePack = ""
        if(recvBuffer is None or len(recvBuffer) < HEADERTAIL_LEN):
            return (0,onePack)

        # 解析出命令字
        try:
            startFlag,transId,cmdId,bodyLen = struct.unpack("=3BH", recvBuffer[0:HEADER_LEN])
        except Exception as e:
            onePack = "%s" % (e)
            return (-1,onePack)

        # 如果头标识不对
        if(startFlag != 0x68):
            onePack = ("pack all bufferLen=%d, startFlag invalid!" % (len(recvBuffer)))
            recvBuffer = ""
            return (-1, onePack)

        if(bodyLen > 3200):
            onePack = ("pack bodyLen=%d, all buffer len=%d,startFlag invalid!" % (bodyLen, len(recvBuffer)))
            recvBuffer = ""
            return (-1,onePack)

        if(len(recvBuffer) < HEADERTAIL_LEN + bodyLen):
            if(len(recvBuffer) > 3200):
                onePack = ("pack allBufferLen=%d, but there's not a entire pack. bodyLen=%d!" % (len(recvBuffer),bodyLen))
                recvBuffer = ""
            return (-1,onePack) # 不完整的包

        onePack = recvBuffer[HEADER_LEN:HEADER_LEN + bodyLen]
        recvBuffer = recvBuffer[HEADERTAIL_LEN + bodyLen:]
        return (1,onePack)



