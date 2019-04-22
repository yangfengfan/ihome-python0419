### -*- coding: utf-8 -*-
'''
Created on 2014-9-25

@author: shijunpu
'''
from ThreadBase import *
import threading
import socket
import json
import copy
import struct
import datetime
import time
import GlobalVars
import Utils
from DBManagerDevice import *
from DBManagerDeviceProp import *
from UtilsLock import *
import time


HEADER_LEN       = 5  # 起始码    事务号    命令字    数据长度(2)
TAILER_LEN       = 2  # 校验和    结束符
HEADERTAIL_LEN   = (HEADER_LEN + TAILER_LEN)  # 起始码    事务号    命令字    数据长度       校验和    结束符
CHECKSUM_START   = 2
START_FLAG       = 0x68
END_FLAG         = 0xED

# 设备命令定义
CMDID_DEVICECONFIG_DEVICE   = 0x01
CMDID_REGISTERDATA_DEVICE   = 0x02
CMDID_SEARCH_DEVICE         = 0x03
CMDID_CONTROL_DEVICE        = 0x04
CMDID_QUERY_DEVICE          = 0x05
CMDID_QUERY_ENERGY_ELEC     = 0x06
CMDID_QUERY_ENERGY_WATER    = 0x07
CMDID_QUERY_ENERGY_GAS      = 0x08
CMDID_LINK_DEVICE           = 0x09
CMDID_QUERY_CENTRAL_AIRCONDITION = 0x8A
CMDID_RECV_CENTRAL_AIRCONDITION = 0x0A

# 批量扫描设备命令
CMDID_BATCH_SCAN            = 0x83

# 中控命令
CMDID_HGC_CONTROL           = 0x14
CMDID_HGC_QUERY             = 0x15
CMDID_HGC_REPORT            = 0x1C

#设备类型ID定义   
DEVTYPEID_LIGHTAJUST        = 0x01
DEVTYPEID_LIGHT1            = 0x11
DEVTYPEID_GSM               = 0x12 # 门窗磁
DEVTYPEID_CURTAIN_SENSOR    = 0x13 # 幕帘
DEVTYPEID_ACOUSTO_OPTIC_ALARM = 0x16  # 声光报警器
DEVTYPEID_LCD_SWITCH        = 0x18  # LCD开关
DEVTYPEID_AIR_SENSOR        = 0x19  # 空气监测设备
DEVTYPEID_LOCK              = 0x20
DEVTYPEID_LIGHT2            = 0x21
DEVTYPEID_LIGHT3            = 0x31
DEVTYPEID_LIGHT4            = 0x41
DEVTYPEID_SOCKET            = 0x02
DEVTYPEID_CURTAIN           = 0x04
DEVTYPEID_SMOKE_SENSOR      = 0x05
DEVTYPEID_EXIST_SENSOR      = 0x06
DEVTYPEID_ENVIROMENT_SENSOR = 0x07
DEVTYPEID_OXYGEN_CO2_SENSOR = 0x08
DEVTYPEID_CH4CO_SENSOR      = 0x09
DEVTYPEID_WATER_SENSOR      = 0x0A
DEVTYPEID_RAY_SENSOR        = 0x0B  # 光照设备
DEVTYPEID_SOS_SENSOR        = 0x0C  # 报警
DEVTYPEID_FALL_SENSOR       = 0x0D  # 防跌倒
DEVTYPEID_SOV               = 0x0E  # 电磁阀
DEVTYPEID_MODE_PANNEL       = 0x0F  # 模式面板
DEVTYPEID_PROJECTOR         = 0x22
DEVTYPEID_AUDIO               = 0x23  # 音丽士背景音乐
DEVTYPEID_TABLE_WATER_FILTER = 0x24  # 台上净水器
DEVTYPEID_AIR_FILTER        = 0x25  # 空气净化器
DEVTYPEID_FLOOR_WATER_FILTER = 0x26  # 台下净水器
DEVTYPEID_LIGHTAJUST_PANNEL = 0x27  # 调光控制面板

DEVTYPEID_CENTRAL_AIRCONDITION = 0x50  # 中央空调
DEVTYPEID_HGC               = 0x51
DEVTYPEID_FLOOR_HEATING     = 0x52  # 地暖
DEVTYPEID_AIR_SYSTEM        = 0x53  # 新风系统
DEVTYPEID_WUHENG_SYSTEM     = 0X54  # 五恒系统

# 当设备类型为红外时,逻辑设备ID
DEVTYPEID_TV                = 0x1001
DEVTYPEID_IPTV              = 0x1002
DEVTYPEID_DVD               = 0x1003
DEVTYPEID_AIRCONDITION      = 0x1004
DEVTYPEID_INFRARED_DEV_MIN = DEVTYPEID_TV
DEVTYPEID_INFRARED_DEV_MAX = DEVTYPEID_AIRCONDITION
# 物理设备ID
DEVTYPEID_INFRARED          = 0x03


DEVTYPEID_ENERGY_ELEC       = 0x70
DEVTYPEID_ENERGY_WATER      = 0x71
DEVTYPEID_ENERGY_GAS        = 0x72

#设备类型名称定义   
DEVTYPENAME_LIGHTAJUST        = "LightAdjust"
DEVTYPENAME_LIGHT1            = "Light1"
DEVTYPENAME_LIGHT2            = "Light2"
DEVTYPENAME_LIGHT3            = "Light3"
DEVTYPENAME_LIGHT4            = "Light4"
DEVTYPENAME_SOCKET            = "Socket"
DEVTYPENAME_CURTAIN           = "Curtain"
DEVTYPENAME_SMOKE_SENSOR      = "Smoke"
DEVTYPENAME_EXIST_SENSOR      = "Exist"
DEVTYPENAME_ENVIROMENT_SENSOR = "Env"
DEVTYPENAME_OXYGEN_CO2_SENSOR = "O2CO2"
DEVTYPENAME_CH4CO_SENSOR      = "Ch4CO"
DEVTYPENAME_WATER_SENSOR      = "Water"
# DEVTYPENAME_RAY_SENSOR        = "Ray"
DEVTYPENAME_FALL_SENSOR       = "Fall"
DEVTYPENAME_SOS_SENSOR        = "SOS"
DEVTYPENAME_SOV               = "Sov"       # 电磁阀
DEVTYPENAME_PANNEL            = "Pannel"    # 模式面板
DEVTYPENAME_LOCK              = "Lock"    # 密码锁
DEVTYPENAME_PROJECTOR         = "Projector"

DEVTYNAME_CENTRAL_AIRCONDITION = "CAC"  # 中央空调 CentralAirConditioner
DEVTYPENAME_HGC               = "HGC"  # 中控
DEVTYPENAME_FLOOR_HEATING     = "FloorHeating"  # 地暖

DEVTYPENAME_TV                = "TV"
DEVTYPENAME_IPTV              = "IPTV"
DEVTYPENAME_DVD               = "DVD"
DEVTYPENAME_AIRCONDITION      = "AirCondition"
DEVTYPENAME_INFRARED          = "Infrared"

DEVTYPENAME_CAMERA            = "Camera"

DEVTYPENAME_UNKNOWN           = "notype"
DEVTYPENAME_ENERGY_ELEC       = "ElecMeter"
DEVTYPENAME_ENERGY_WATER      = "WaterMeter"
DEVTYPENAME_ENERGY_GAS        = "GasMeter"
DEVTYPENAME_GSM               = "Gsm" # 门窗磁
DEVTYPENAME_CURTAIN_SENSOR    = "CurtainSensor" # 幕帘
DEVTYPENAME_AUDIO               = "Audio" # 背景音乐
DEVTYPENAME_AIR_SYSTEM        = "AirSystem"  # 新风系统
DEVTYPENAME_TABLE_WATER_FILTER = "TableWaterFilter"  # 台上净水器
DEVTYPENAME_AIR_FILTER        = "AirFilter"   # 空气净化器
DEVTYPENAME_FLOOR_WATER_FILTER = "FloorWaterFilter"  # 台下净水器
DEVTYPENAME_ACOUSTO_OPTIC_ALARM = "AcoustoOpticAlarm"  # 声光报警器
DEVTYPENAME_AIR_SENSOR        = "AirSensor"  # 空气监测设备
DEVTYPENAME_LCD_SWITCH        = "LcdSwitch"  # LCD开关
DEVTYPENAME_WUHENG_SYSTEM     = "WHSystem"  # 五恒系统
DEVTYPENAME_LIGHTAJUST_PANNEL = "LightAdjustPannel" # 调光控制面板
DEVTYPENAME_RAY_SENSOR = "RaySensor"       # 光感器

class PacketParser:  
    def __init__(self):  
        self.transId = 1
        self.recvBuffer = ""
        
    def buildHeader(self, cmdId, bodyLen):
        self.transId += 1
        if self.transId >= 255:
            self.transId = 1
        try:
            header = struct.pack("=3BH", 0x68,self.transId,cmdId,bodyLen)
            return header
        except:
            Utils.logException("error when buildHeader")
            return ""
    
    def buildTailer(self, bodyBuffer):
        checkValue = self.calcCheckValue(bodyBuffer[CHECKSUM_START:])
        tailer = struct.pack("=2B", checkValue, 0xED)  
        return tailer
    
   
    # 根据配置文件的设备类型名称，获取到物理设备类型id和逻辑设备类型id的二元组
    # 用于红外设备的子类型，电视、空调、机顶盒时，物理设备和逻辑设备是不相同的
    @staticmethod
    def getDeviceTypeIdByName(deviceTypeName):
        dictDeviceTypeToId = {
                              DEVTYPENAME_LIGHTAJUST:       DEVTYPEID_LIGHTAJUST,
                              DEVTYPENAME_LIGHT1:           DEVTYPEID_LIGHT1,
                              DEVTYPENAME_LIGHT2:           DEVTYPEID_LIGHT2,
                              DEVTYPENAME_LIGHT3:           DEVTYPEID_LIGHT3,
                              DEVTYPENAME_LIGHT4:           DEVTYPEID_LIGHT4,
                              DEVTYPENAME_INFRARED:         DEVTYPEID_INFRARED,
                              DEVTYPENAME_TV:               DEVTYPEID_TV,
                              DEVTYPENAME_IPTV:             DEVTYPEID_IPTV,
                              DEVTYPENAME_DVD:              DEVTYPEID_DVD,
                              DEVTYPENAME_AIRCONDITION:     DEVTYPEID_AIRCONDITION,
                              DEVTYNAME_CENTRAL_AIRCONDITION: DEVTYPEID_CENTRAL_AIRCONDITION,
                              DEVTYPENAME_SOCKET:           DEVTYPEID_SOCKET,
                              DEVTYPENAME_CURTAIN:          DEVTYPEID_CURTAIN,
                              DEVTYPENAME_SMOKE_SENSOR:     DEVTYPEID_SMOKE_SENSOR,
                              DEVTYPENAME_EXIST_SENSOR:     DEVTYPEID_EXIST_SENSOR,
                              DEVTYPENAME_WATER_SENSOR:     DEVTYPEID_WATER_SENSOR,
                              DEVTYPENAME_OXYGEN_CO2_SENSOR:DEVTYPEID_OXYGEN_CO2_SENSOR,
                              DEVTYPENAME_CH4CO_SENSOR:     DEVTYPEID_CH4CO_SENSOR,
                              DEVTYPENAME_ENVIROMENT_SENSOR:DEVTYPEID_ENVIROMENT_SENSOR,
                              # DEVTYPENAME_RAY_SENSOR:      DEVTYPEID_RAY_SENSOR,
                              DEVTYPENAME_SOS_SENSOR:      DEVTYPEID_SOS_SENSOR,
                              DEVTYPENAME_FALL_SENSOR:     DEVTYPEID_FALL_SENSOR,
                              DEVTYPENAME_ENERGY_ELEC:     DEVTYPEID_ENERGY_ELEC,
                              DEVTYPENAME_ENERGY_WATER:    DEVTYPEID_ENERGY_WATER,
                              DEVTYPENAME_ENERGY_GAS:      DEVTYPEID_ENERGY_GAS,
                              DEVTYPENAME_SOV:             DEVTYPEID_SOV,
                              DEVTYPENAME_PANNEL:          DEVTYPEID_MODE_PANNEL,
                              DEVTYPENAME_HGC:             DEVTYPEID_HGC,
                              DEVTYPENAME_PROJECTOR:       DEVTYPEID_PROJECTOR,
                              DEVTYPENAME_LOCK:            DEVTYPEID_LOCK,
                              DEVTYPENAME_FLOOR_HEATING:   DEVTYPEID_FLOOR_HEATING,
                              DEVTYPENAME_GSM:             DEVTYPEID_GSM,
                              DEVTYPENAME_CURTAIN_SENSOR:  DEVTYPEID_CURTAIN_SENSOR,
                              DEVTYPENAME_AUDIO:             DEVTYPEID_AUDIO,
                              DEVTYPENAME_AIR_SYSTEM:      DEVTYPEID_AIR_SYSTEM,
                              DEVTYPENAME_TABLE_WATER_FILTER: DEVTYPEID_TABLE_WATER_FILTER,
                              DEVTYPENAME_FLOOR_WATER_FILTER: DEVTYPEID_FLOOR_WATER_FILTER,
                              DEVTYPENAME_AIR_FILTER:      DEVTYPEID_AIR_FILTER,
                              DEVTYPENAME_ACOUSTO_OPTIC_ALARM: DEVTYPEID_ACOUSTO_OPTIC_ALARM,
                              DEVTYPENAME_AIR_SENSOR: DEVTYPEID_AIR_SENSOR,
                              DEVTYPENAME_LCD_SWITCH:      DEVTYPEID_LCD_SWITCH,
                              DEVTYPENAME_WUHENG_SYSTEM:   DEVTYPEID_WUHENG_SYSTEM,
                              DEVTYPENAME_LIGHTAJUST_PANNEL: DEVTYPEID_LIGHTAJUST_PANNEL,
                              DEVTYPENAME_RAY_SENSOR: DEVTYPEID_RAY_SENSOR
        }
        return dictDeviceTypeToId.get(deviceTypeName, 0) #-1 超出了一个字节的表示范围
    
    #根据配置文件的设备类型名称，获取到物理设备类型id和逻辑设备类型id的二元组
    #用于红外设备的子类型，电视、空调、机顶盒时，物理设备和逻辑设备是不相同的
    @staticmethod
    def getDeviceTypeNameById(deviceTypeId):
        dictDeviceTypeId2Name = {DEVTYPEID_LIGHTAJUST:DEVTYPENAME_LIGHTAJUST,
                                 DEVTYPEID_LIGHT1:          DEVTYPENAME_LIGHT1,
                                 DEVTYPEID_LIGHT2:          DEVTYPENAME_LIGHT2,
                                 DEVTYPEID_LIGHT3:          DEVTYPENAME_LIGHT3,
                                 DEVTYPEID_LIGHT4:          DEVTYPENAME_LIGHT4,
                                 DEVTYPEID_INFRARED:        DEVTYPENAME_INFRARED,
                                 DEVTYPEID_TV:              DEVTYPENAME_TV,
                                 DEVTYPEID_IPTV:            DEVTYPENAME_IPTV,
                                 DEVTYPEID_AIRCONDITION:    DEVTYPENAME_AIRCONDITION,
                                 DEVTYPEID_CENTRAL_AIRCONDITION: DEVTYNAME_CENTRAL_AIRCONDITION,
                                 DEVTYPEID_DVD:             DEVTYPENAME_DVD,
                                 DEVTYPEID_SOCKET:          DEVTYPENAME_SOCKET,
                                 DEVTYPEID_CURTAIN:         DEVTYPENAME_CURTAIN,
                                 DEVTYPEID_SMOKE_SENSOR:    DEVTYPENAME_SMOKE_SENSOR,
                                 DEVTYPEID_EXIST_SENSOR:    DEVTYPENAME_EXIST_SENSOR,
                                 DEVTYPEID_WATER_SENSOR:    DEVTYPENAME_WATER_SENSOR,
                                 DEVTYPEID_OXYGEN_CO2_SENSOR:DEVTYPENAME_OXYGEN_CO2_SENSOR,
                                 DEVTYPEID_CH4CO_SENSOR:    DEVTYPENAME_CH4CO_SENSOR,
                                 DEVTYPEID_ENVIROMENT_SENSOR:DEVTYPENAME_ENVIROMENT_SENSOR,
                                 DEVTYPEID_ENERGY_ELEC:     DEVTYPENAME_ENERGY_ELEC,
                                 DEVTYPEID_ENERGY_WATER:     DEVTYPENAME_ENERGY_WATER,
                                 DEVTYPEID_ENERGY_GAS:      DEVTYPENAME_ENERGY_GAS,
                                 # DEVTYPEID_RAY_SENSOR:      DEVTYPENAME_RAY_SENSOR,
                                 DEVTYPEID_FALL_SENSOR:     DEVTYPENAME_FALL_SENSOR,
                                 DEVTYPEID_SOS_SENSOR:      DEVTYPENAME_SOS_SENSOR,
                                 DEVTYPEID_SOV:             DEVTYPENAME_SOV,
                                 DEVTYPEID_LOCK:            DEVTYPENAME_LOCK,
                                 DEVTYPEID_PROJECTOR:       DEVTYPENAME_PROJECTOR,
                                 DEVTYPEID_HGC:             DEVTYPENAME_HGC,
                                 DEVTYPEID_MODE_PANNEL:     DEVTYPENAME_PANNEL,
                                 DEVTYPEID_FLOOR_HEATING:   DEVTYPENAME_FLOOR_HEATING,
                                 DEVTYPEID_GSM:             DEVTYPENAME_GSM,
                                 DEVTYPEID_CURTAIN_SENSOR:  DEVTYPENAME_CURTAIN_SENSOR,
                                 DEVTYPEID_AUDIO:             DEVTYPENAME_AUDIO,
                                 DEVTYPEID_AIR_SYSTEM:      DEVTYPENAME_AIR_SYSTEM,
                                 DEVTYPEID_TABLE_WATER_FILTER: DEVTYPENAME_TABLE_WATER_FILTER,
                                 DEVTYPEID_FLOOR_WATER_FILTER: DEVTYPENAME_FLOOR_WATER_FILTER,
                                 DEVTYPEID_AIR_FILTER:      DEVTYPENAME_AIR_FILTER,
                                 DEVTYPEID_ACOUSTO_OPTIC_ALARM: DEVTYPENAME_ACOUSTO_OPTIC_ALARM,
                                 DEVTYPEID_AIR_SENSOR: DEVTYPENAME_AIR_SENSOR,
                                 DEVTYPEID_LCD_SWITCH:      DEVTYPENAME_LCD_SWITCH,
                                 DEVTYPEID_WUHENG_SYSTEM:   DEVTYPENAME_WUHENG_SYSTEM,
                                 DEVTYPEID_LIGHTAJUST_PANNEL: DEVTYPENAME_LIGHTAJUST_PANNEL,
                                 DEVTYPEID_RAY_SENSOR: DEVTYPENAME_RAY_SENSOR
                              }
        return dictDeviceTypeId2Name.get(deviceTypeId, "unknown")
    
    @staticmethod
    def getPhysicalDeviceTypeIdByName(devTypeName):
        logDevTypeId = PacketParser.getDeviceTypeIdByName(devTypeName)
        if DEVTYPEID_INFRARED_DEV_MIN <= logDevTypeId <= DEVTYPEID_INFRARED_DEV_MAX:
            return DEVTYPEID_INFRARED
        return logDevTypeId
        
    #根据ASCII的设备地址z-1B7C4501004B1200（19个字节），转换为十六进制的MAC地址（8个字节）
    def getMacAddrByDevAddr(self, devAddr1):
        devAddr = devAddr1.strip()
        if len(devAddr) != 20:
            Utils.logError("device addr %s: length are not 20" % (devAddr))
            return ""
        
        macAddrAscii = devAddr
        numbers = [0,0,0,0,0,0,0,0,0,0]
        iNum = 0
        try:
            for i in range(0,20,2):
                numbers[iNum] = int(macAddrAscii[i:i+2],16)
                iNum += 1
        except:
            Utils.logException("getMacAddrByDevAddr(%s) failed"%(macAddrAscii))
            return ""
            
        return struct.pack("=10B",numbers[0],numbers[1],numbers[2],numbers[3],numbers[4],numbers[5],numbers[6],numbers[7],numbers[8],numbers[9])
    
     #根据十六进制的MAC地址（8个字节）转换为ASCII的设备地址z-1B7C4501004B1200（19个字节）
    @staticmethod
    def getDevAddrByMac(macAddr):
        if len(macAddr) < 10:
            Utils.logError("device addr too short：%s" % (macAddr))
            return None
        
        numbers = struct.unpack("=10B",macAddr)
        devAddr = "%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X" % numbers
        return devAddr    

    def buildHGCqueryResponsePack(self, response):
        ret = []
        try:
            ##response = {'addr':hgcaddr, 'type':hgcType, 'ctrlDevType':ctrlDevType, 'ctrlDevNumber':ctrlDevNumber, 'returnType':returnType, 'buflen':len(devName), 'buf':devName}
            ##response = {'addr':hgcaddr, 'type':hgcType, 'ctrlDevType':ctrlDevType, 'ctrlDevNumber':ctrlDevNumber, 'returnType':returnType, 'buflen':1, 'buf':retV}
            devAddr = response.get("addr","") #z-1111111
            macAddr = self.getMacAddrByDevAddr(devAddr) # 去掉z-
            if(macAddr == ""):
                Utils.logError("buildHGCportConfiguredPack mac address invalid" % (macAddr))
                return ret

            deviceTypeName = response.get("type","") #HGC
            devTypeId = self.getPhysicalDeviceTypeIdByName(deviceTypeName)
            if(devTypeId == 0):
                Utils.logError( "buildHGCportConfiguredPack type:%s invalid" % (deviceTypeName))
                return ret
            buflen = response.get('buflen', None)
            data = response.get('buf', None)
            ctrlDevType = response.get('ctrlDevType', None)
            ctrlDevNumber = response.get('ctrlDevNumber', None)
            controlDeviceName = response.get('returnType', None)

            if buflen == None or data == None or ctrlDevType == None or ctrlDevNumber == None or controlDeviceName == None:
                return ret

            # totalBufLen = 15 + buflen
            # packNum = totalBufLen/25 + 1
            # currPack = 0
            # bodyBuffer = struct.pack("=8s7B", macAddr[0,7], currPack, packNum, devTypeId, ctrlDevType, ctrlDevNumber, controlDeviceName, buflen)
            # bodyBuffer = bodyBuffer + data

            tmpBuffer = struct.pack("=4B"+str(buflen)+"s", ctrlDevType, ctrlDevNumber, controlDeviceName, buflen, data)
            tmpBufferLen = len(tmpBuffer)

            packNum = tmpBufferLen/14 + 1
            currPack = 0

            while currPack < packNum:
                start = currPack*14
                end = (currPack+1)*14
                if end >= tmpBufferLen:
                    end = tmpBufferLen

                pack = tmpBuffer[start:end]
                bodyBuffer = struct.pack("=8s3B"+len(pack)+"s", macAddr[0:7], currPack, packNum, devTypeId, pack)
                headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                ret.append(buf)
                currPack += 1
        except:
            Utils.logException("error when buildHGCqueryResponsePack")
        return ret


    # 拼装同步HGC时间的数据包
    def buildSyncHgcTimePack(self, macAddr):
        Utils.logInfo("sync time to hgc...")

        macAddr = self.getMacAddrByDevAddr(macAddr)

        current_time = time.strftime('%y %m %d %H %M %S %w',time.localtime(time.time()))
        year, month, day, hour, minute, second, week_day = current_time.split(" ")
        year = 2000 + int(year)
        if week_day == "0" or week_day == 0:
            week_day = "7"
        # bodyBuffer = struct.pack("=10sBh6B", macAddr, 0x51, year, int(month, 16), int(day, 16), int(hour, 16),
        #                          int(minute, 16), int(second, 16), int(week_day, 16))
        bodyBuffer = struct.pack("=10sBh6B", macAddr, 0x51, year, int(month), int(day), int(hour), int(minute), int(second), int(week_day))
        buffer2 = struct.pack("=6B", 0, 0, 0, 0, 0, 0)
        bodyBuffer += buffer2
        headerBodyBuffer = self.buildHeader(0x9A, len(bodyBuffer)) + bodyBuffer
        buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        return buf


    # 拼装同步HGC配置的数据包
    def buildSyncHgcConfigPack(self, config, isConfigured):

        try:
            hgcAddr = config.get("addr", None)
            v_type = config.get("v_type", None)
            channel = config.get("channel", None)

            macAddr = self.getMacAddrByDevAddr(hgcAddr)

            controls = config.get("controls", None)
            control = controls[0]

            # 红外空调如何获取protocol?
            if v_type == 0x50 or v_type == "0x50" or v_type == 0x30 or v_type == "0x30":
                protocol = control.get("protocol", "0")
                addr = str(control.get("addr", "0"))
                if addr[:4] == "CAC_":
                    addr = addr[4:]
                bodyBuffer = struct.pack("=10s4B", macAddr, 0x51, int(v_type, 16), int(protocol), int(addr))
                buffer2 = struct.pack("=11B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                bodyBuffer += buffer2
                headerBodyBuffer = self.buildHeader(0x9B, len(bodyBuffer)) + bodyBuffer
                buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                return buf
            else:
                bodyBuffer = struct.pack("=10s4B", macAddr, 0x51, int(v_type, 16), int(channel), isConfigured)
                buffer2 = struct.pack("=11B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                bodyBuffer += buffer2
                headerBodyBuffer = self.buildHeader(0x9B, len(bodyBuffer)) + bodyBuffer
                buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                return buf
        except:
            Utils.logError("build syncHgcConfigPack error!!!")
            return ""

    # 中央空调的控制指令映射，20160916：修改为将设定温度也同步到中控，TODO 待测试
    def getControlCmd(self, key):
        if key == "set_on" or key == "status_on":
            return 0x2
        if key == "alarm":
            return 0x8
        if key == "error_code":
            return 0x9
        if key == "set_mode" or key == "status_mode":
            return 0x3
        if key == "set_airflowrate" or key == "status_airflowrate":
            return 0x4
        if key == "measured_temp":
            return 0x6
        if key == "set_airdirection" or key == "status_airdirection":
            return 0x5
        if key == "total_energy":
            return 0x7
        else:
            return None

    # 拼装同步HGC上设备名称或状态的数据包
    def buildSyncHgcDevPack(self, sparam):

        buffer_list = []

        try:
            hgcAddr = sparam.get("hgc_addr", None)
            macAddr = self.getMacAddrByDevAddr(hgcAddr)
            v_type = sparam.get("v_type", None)
            channel = sparam.get("channel", None)
            update = sparam.get("update", None)
            value = sparam.get("value")
            if update == 0x01:  # 名字
                new_name = sparam.get("new_name", None)
                new_name = new_name.encode("utf-8")
                data_len = len(new_name)
                if data_len > 9:
                    data_len = 9
                bodyBuffer = struct.pack("=10s5B10s", macAddr, 0x51, int(v_type, 16), int(channel), int(update), data_len, new_name)
                # buffer2 = struct.pack("=6B", 0,0,0,0,0,0)
                # bodyBuffer += buffer2
                headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                buffer_list.append(buf)
                return buffer_list
            if update == 0x00:  # 状态
                # 中央空调
                if v_type == 0x50 or v_type == "0x50":
                    keys = sparam.get("keys")
                    protocol = sparam.get("protocol")
                    addr = str(value.get("addr"))
                    if addr[:4] == "CAC_":
                        addr = addr[4:]

                    # 过滤不需要的数据
                    for key in keys:
                        # TODO 不将set_temp温度属性去除
                        if key == "addr" or key == "set_on" or key == "set_mode" or key == "set_airflowrate" or \
                                        key == "set_airdirection":
                            keys.remove(key)
                    Utils.logInfo("keys after remove:")
                    Utils.logInfo(keys)

                    if len(keys) > 0:
                        for key in keys:
                           
                            controlCmd = self.getControlCmd(key)
                            if controlCmd == 0x7:
                                data_len = 4
                                bodyBuffer = struct.pack("=10s6Bi", macAddr, 0x51, int(v_type, 16), int(protocol), int(addr),
                                                         controlCmd, data_len, int(value.get(key)))
                                buffer2 = struct.pack("=5B", 0, 0, 0, 0, 0)
                            elif controlCmd == 0x6: # 涉及温度，将实际温度和设定温度拼一起，设定温度在实际温度之后 TODO 待测试
                                data_len = 4
                                bodyBuffer = struct.pack("=10s6B2h", macAddr, 0x51, int(v_type, 16), int(protocol), int(addr),
                                             controlCmd, data_len, int(value.get("measured_temp")), int(value.get("set_temp")))
                                buffer2 = struct.pack("=5B", 0, 0, 0, 0, 0)
                                bodyBuffer += buffer2
                                headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                                buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                                buffer_list.append(buf)
                                return buffer_list # 当controCmd是 0x6时必定是两个温度值，但只需要拼一次报文
                            elif controlCmd != None:
                                data_len = 2
                                control_data = int(value.get(key))
                                
                                bodyBuffer = struct.pack("=10s6Bh", macAddr, 0x51, int(v_type, 16), int(protocol), int(addr), controlCmd, data_len,
                                                         control_data)
                                buffer2 = struct.pack("=7B", 0, 0, 0, 0, 0, 0, 0)
                            bodyBuffer += buffer2
                            headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                            buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                            buffer_list.append(buf)
                        
                        return buffer_list
                    else:
                        return None

                # 场景
                elif v_type == 0xF or v_type == "0xF":
                    modeId = value.get("modeId")
                    bodyBuffer = struct.pack("=10s6B", macAddr, 0x51, int(v_type, 16), int(channel), int(update), 1, int(modeId))
                    buffer2 = struct.pack("=9B", 0, 0, 0, 0, 0, 0, 0, 0, 0)
                    bodyBuffer += buffer2
                    headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                    buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                    buffer_list.append(buf)
                    return buffer_list

                # 灯，包括普通灯和调光灯
                elif v_type == 0x1 or v_type == "0x1":
                    type_name = sparam.get("type_name")
                    if type_name == "LightAdjust":
                        is_adjust = 1
                        coeff = value.get("coeff")
                        state = value.get("state")
                    else:
                        is_adjust = 0
                        coeff = 100  # 还是0？
                        state = value.get("state", "")
                        state2 = value.get("state2", "")
                        state3 = value.get("state3", "")
                        state4 = value.get("state4", "")
                        if state == "1" or state2 == "1" or state3 == "1" or state4 == "1" or state == 1 or state2 == 1 or state3 == 1 or state4 == 1:
                            state = "1"
                        else:
                            state = "0"
                    bodyBuffer = struct.pack("=10s8B", macAddr, 0x51, int(v_type, 16), int(channel), int(update), 3,
                                             int(state), int(is_adjust), int(coeff))
                    buffer2 = struct.pack("=7B", 0, 0, 0, 0, 0, 0, 0)
                    bodyBuffer += buffer2
                    headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                    buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                    buffer_list.append(buf)
                    return buffer_list

                # 插座
                elif v_type == 0x2 or v_type == "0x2":
                    state = value.get("state")
                    current = int(float(value.get("I")) * 100)
                    volt = int(float(value.get("U")) * 10)
                    power = int(float(value.get("P")) * 10)
                    energy = int(float(value.get("energy")) * 1000)
                    bodyBuffer = struct.pack("=10s6B3hi", macAddr, 0x51, int(v_type, 16), int(channel), int(update),
                                         5, int(state), int(current), int(volt), int(power), int(energy))
                    buffer2 = struct.pack("=5B", 0,0,0,0,0)
                    bodyBuffer += buffer2
                    headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
                    buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                    buffer_list.append(buf)
                    return buffer_list

        except Exception, e:
            Utils.logError("build SyncHgcDevPack error!!! %s" % e)
            return ""

    # 构造控制地暖的数据包
    def buildControlFLoorHeatingPack(self, sparam):

        if sparam is None:
            return ""

        hgc_addr = sparam.get("hgcAddr", None)
        value = sparam.get("value", None)
        if hgc_addr is None or value is None:
            return ""
        macAddr = self.getMacAddrByDevAddr(hgc_addr)
        state = value.get("state", "0")
        if state == "0" or state == 0:
            bodyBuffer = struct.pack("=10s2B", macAddr, 0x51, 0x52)
            buffer2 = struct.pack("=13B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            bodyBuffer += buffer2
        elif state == "1" or state == 1:
            bodyBuffer = struct.pack("=10s4BBHBH", macAddr, 0x51, 0x52, 7, 1, int(value.get("setRoomTemperature", 22)),
                                     int(value.get("measuredRoomTemperature", 0)), int(value.get("setFloorTemperature", 0)),
                                     int(value.get("measuredFloorTemperature", 0)))
            buffer2 = struct.pack("=5B", 0, 0, 0, 0, 0)
            bodyBuffer += buffer2
        else:
            return ""

        headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
        buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        return buf

    # 构造同步定时任务信息的数据包
    def buildSyncFLoorHeatingPack(self, sparam):

        if sparam is None:
            return ""

        hgc_addr = sparam.get("hgcAddr", None)
        time_task = sparam.get("timeTask", None)
        switch = sparam.get("timeTaskSwitch", None)
        if hgc_addr is None or time_task is None or len(time_task) == 0 or switch is None:
            return ""
        macAddr = self.getMacAddrByDevAddr(hgc_addr)

        try:
            buffer_list = list()

            # 定时功能处于关闭状态
            if switch == "off":
                # 工作日，flag：1和2
                bodyBuffer1 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, 1)
                bodyBuffer2 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, 2)
                buffer_zero = struct.pack("=10B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                bodyBuffer1 += buffer_zero
                bodyBuffer2 += buffer_zero
                headerBodyBuffer1 = self.buildHeader(0x95, len(bodyBuffer1)) + bodyBuffer1
                headerBodyBuffer2 = self.buildHeader(0x95, len(bodyBuffer2)) + bodyBuffer2
                entire_buffer_1 = headerBodyBuffer1 + self.buildTailer(headerBodyBuffer1)
                entire_buffer_2 = headerBodyBuffer2 + self.buildTailer(headerBodyBuffer2)

                buffer_list.append(entire_buffer_1)
                buffer_list.append(entire_buffer_2)

                # 休息日，flag：3和4
                bodyBuffer3 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, 3)
                bodyBuffer4 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, 4)
                buffer_zero = struct.pack("=10B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                bodyBuffer3 += buffer_zero
                bodyBuffer4 += buffer_zero
                headerBodyBuffer3 = self.buildHeader(0x95, len(bodyBuffer3)) + bodyBuffer3
                headerBodyBuffer4 = self.buildHeader(0x95, len(bodyBuffer4)) + bodyBuffer4
                entire_buffer_3 = headerBodyBuffer3 + self.buildTailer(headerBodyBuffer3)
                entire_buffer_4 = headerBodyBuffer4 + self.buildTailer(headerBodyBuffer4)

                buffer_list.append(entire_buffer_3)
                buffer_list.append(entire_buffer_4)

                return buffer_list

            # 定时功能处于打开状态
            else:

                for task in time_task:
                    type_flag = task.get("type")
                    if type_flag == "weekday":  # 工作日，1和2
                        type_flag = 1
                    if type_flag == "weekend":  # 休息日，3和4
                        type_flag = 3

                    time_list = task.get("taskList")

                    # 未设置定时
                    if time_list == "" or len(time_list) == 0:
                        bodyBuffer1 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, int(type_flag))
                        bodyBuffer2 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, int(type_flag)+1)
                        buffer_zero = struct.pack("=10B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                        bodyBuffer1 += buffer_zero
                        bodyBuffer2 += buffer_zero
                        headerBodyBuffer1 = self.buildHeader(0x95, len(bodyBuffer1)) + bodyBuffer1
                        headerBodyBuffer2 = self.buildHeader(0x95, len(bodyBuffer2)) + bodyBuffer2
                        entire_buffer_1 = headerBodyBuffer1 + self.buildTailer(headerBodyBuffer1)
                        entire_buffer_2 = headerBodyBuffer2 + self.buildTailer(headerBodyBuffer2)

                        buffer_list.append(entire_buffer_1)
                        buffer_list.append(entire_buffer_2)

                    # 只设置了4个或4个以下的定时时段
                    if len(time_list) > 0 and len(time_list) <= 4:
                        # 第一条
                        data_len = 2*len(time_list) + 2
                        bodyBuffer1 = struct.pack("=10s5B", macAddr, 0x51, 0x52, data_len, 2, int(type_flag))
                        for i in range(0, len(time_list)):
                            buffer2 = struct.pack("=2B", int(time_list[i].get("timeIndex", 0)), int(time_list[i].get("temperature", 0)))
                            bodyBuffer1 += buffer2
                        zero_remaining = 25 - 10 - 5 - 2*len(time_list)
                        for i in range(0, zero_remaining):
                            buffer_zero = struct.pack("=B", 0)
                            bodyBuffer1 += buffer_zero
                        headerBodyBuffer1 = self.buildHeader(0x95, len(bodyBuffer1)) + bodyBuffer1
                        entire_buffer_1 = headerBodyBuffer1 + self.buildTailer(headerBodyBuffer1)

                        # 第二条为全零
                        bodyBuffer2 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 2, 2, int(type_flag)+1)
                        buffer_zero = struct.pack("=10B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                        bodyBuffer2 += buffer_zero
                        headerBodyBuffer2 = self.buildHeader(0x95, len(bodyBuffer2)) + bodyBuffer2
                        entire_buffer_2 = headerBodyBuffer2 + self.buildTailer(headerBodyBuffer2)

                        buffer_list.append(entire_buffer_1)
                        buffer_list.append(entire_buffer_2)

                    # 设置了4个以上的定时时段
                    if len(time_list) > 4:
                        # 第一条
                        bodyBuffer1 = struct.pack("=10s5B", macAddr, 0x51, 0x52, 10, 2, int(type_flag))
                        for i in range(0, 4):
                            buffer2 = struct.pack("=2B", int(time_list[i].get("timeIndex", 0)), int(time_list[i].get("temperature", 0)))
                            bodyBuffer1 += buffer2
                        buffer_zero = struct.pack("=2B", 0, 0)
                        bodyBuffer1 += buffer_zero
                        headerBodyBuffer1 = self.buildHeader(0x95, len(bodyBuffer1)) + bodyBuffer1
                        entire_buffer_1 = headerBodyBuffer1 + self.buildTailer(headerBodyBuffer1)

                        # 第二条
                        data_len = 2*(len(time_list)-4) + 2
                        bodyBuffer2 = struct.pack("=10s5B", macAddr, 0x51, 0x52, data_len, 2, int(type_flag)+1)
                        for i in range(4, len(time_list)):
                            buffer2 = struct.pack("=2B", int(time_list[i].get("timeIndex", 0)), int(time_list[i].get("temperature", 0)))
                            bodyBuffer2 += buffer2
                        zero_remaining = 25 - 10 - 5 - 2 * (len(time_list)-4)
                        for i in range(0, zero_remaining):
                            buffer_zero = struct.pack("=B", 0)
                            bodyBuffer2 += buffer_zero
                        headerBodyBuffer2 = self.buildHeader(0x95, len(bodyBuffer2)) + bodyBuffer2
                        entire_buffer_2 = headerBodyBuffer2 + self.buildTailer(headerBodyBuffer2)

                        buffer_list.append(entire_buffer_1)
                        buffer_list.append(entire_buffer_2)

                return buffer_list

        except Exception as err:
            Utils.logError("buildSyncFLoorHeatingPack: %s" % err)
            return ""


    def buildHGCportConfiguredPack(self, response):
        ret = []
        try:
            ##response: {'addr':hgcaddr, 'type':hgcTypeId, 'ctrlDevType':ctrlDevType, 'ctrlDevNumber':ctrlDevNumber, 'configured':configured}
            devAddr = response.get("addr", "") #z-1111111
            macAddr = self.getMacAddrByDevAddr(devAddr) # 去掉z-
            if macAddr == "":
                Utils.logError("buildHGCportConfiguredPack mac address invalid" % (macAddr))
                return ret

            devTypeId = response.get("type","") #HGC
            # devTypeId = self.getPhysicalDeviceTypeIdByName(deviceTypeName)
            if devTypeId == 0:
                Utils.logError( "buildHGCportConfiguredPack type:%s invalid" % str(devTypeId))
                return ret
            configured = response.get('configured', 0x30)
            bodyBuffer = struct.pack("=10s2B", macAddr, devTypeId, configured)
            headerBodyBuffer = self.buildHeader(0x95, len(bodyBuffer)) + bodyBuffer
            buf = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
            ret.append(buf)
        except:
            Utils.logException("error when buildDeviceDataRequestPack")
        return ret

    #构件设备配置
    #{"z-1111":{"name":"device1","type":"light","room":"room1"}}
    #addr长度一定>=3
    def buildRegisterDataPack(self):
        try:
            bodyBuffer = struct.pack("=B", 0)
            headerBodyBuffer = self.buildHeader(CMDID_REGISTERDATA_DEVICE, len(bodyBuffer)) + bodyBuffer
            return headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("error when buildRegisterDataPack")
            return ""
    
    # 构件设备配置
    # old:#{"z-1111":{"name":"device1","type":"light","room":"room1"}}
    # {{"name":"device1","type":"light","room":"room1"},{...}}
    # addr长度一定>=3
    def buildConfigChangePack(self, allDevices):  # 该方法停用
        try:
            devsStr = ""
            validDevNum = 0
            bodyBuffer = ""
            for deviceItem in allDevices:
                deviceTypeName = deviceItem.get("type", None) #light
                devAddr = deviceItem.get("addr", None)
                if deviceTypeName is None or devAddr is None:
                    Utils.logError("buildConfigChangePack ignore error device: %s"%(deviceItem))
                    continue
                if deviceTypeName == DEVTYPENAME_CAMERA:# 摄像头等设备返回空
                    continue
                
                devTypeId = self.getPhysicalDeviceTypeIdByName(deviceTypeName)
                macAddr = self.getMacAddrByDevAddr(devAddr)
                if macAddr == None or len(macAddr) == 0: # 摄像头等设备返回空
                    continue
                if macAddr == "":
                    Utils.logError("buildConfigChangePack: device:%s has no addr" % (deviceItem))
                    continue
                
                if devTypeId <= 0:
                    Utils.logError("buildConfigChangePack: device:%s addr:%s, type name is invalid" % (deviceItem, devAddr))
                    continue
                
                devAddrBuffer = struct.pack("=10sB", macAddr, devTypeId)
                strTmp = "type:%s, addr:%s;" % (deviceTypeName, devAddr)
                devsStr = devsStr + strTmp 
                validDevNum += 1
                
                bodyBuffer += devAddrBuffer
            
            Utils.logDebug("Config Changed, request with %d:%s" % (validDevNum,devsStr))
            headerBodyBuffer = self.buildHeader(CMDID_DEVICECONFIG_DEVICE, len(bodyBuffer)) + bodyBuffer
            return  headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("error when buildConfigChangePack")
            return ""        

    # 起始码  事务号    命令字    数据长度    数据区                    校验和    结束符
    # 0x68            0x5    0x9    Mac[0:7]  Type         0xED
    # device:{"name":"device1","type":"light","room":"room1","addr":"z-11111111"}
    def buildDeviceDataRequestPack(self, device):
        try:
            devAddr = device.get("addr","") #z-1111111
            macAddr = self.getMacAddrByDevAddr(devAddr) # 去掉z-
            if(macAddr == ""):
                Utils.logError("device:%s address:%s invalid" % (device, macAddr))
                return None
            
            deviceTypeName = device.get("type","") #light
            devTypeId = self.getPhysicalDeviceTypeIdByName(deviceTypeName)
            if(devTypeId == 0):
                Utils.logError( "device:%s type:%s invalid" % (device, deviceTypeName))
                return None
            
            bodyBuffer = struct.pack("=10sB", macAddr,devTypeId)
            headerBodyBuffer = self.buildHeader(CMDID_QUERY_DEVICE, len(bodyBuffer)) + bodyBuffer
            return  headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("error when buildDeviceDataRequestPack")
            return ""        

    # 起始码    事务号    命令字    数据长度    数据区                    校验和    结束符
    # 0x68            0x8    0x1    0                     0xED
    def buildEnergyElecReqestPack(self):
        try:
            bodyBuffer = struct.pack("=B", 0)
            headerBodyBuffer = self.buildHeader(CMDID_QUERY_ENERGY_ELEC, len(bodyBuffer)) + bodyBuffer
            return  headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("error when buildEnergyElecReqestPack")
            return ""        
    # 起始码    事务号    命令字    数据长度    数据区    校验和    结束符
    # 0x68            0x3    01        0        0xED

    def buildSearchDeviceReqestPack(self):
        try:
            bodyBuffer = struct.pack("=B", 0)
            headerBodyBuffer = self.buildHeader(CMDID_SEARCH_DEVICE, len(bodyBuffer)) + bodyBuffer
            return headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("error when buildSearchDeviceReqestPack")
            return ""        
    # 起始码    事务号    命令字    数据长度    数据区                                                校验和    结束符
    # 0x68            0x4    0x1B    Mac[0:7] Type buf[0:17]        0xED

    def getPhysicalDevTypeId(self, logicDevTypeId):
        if DEVTYPEID_TV == logicDevTypeId or DEVTYPEID_IPTV == logicDevTypeId or DEVTYPEID_DVD == logicDevTypeId or \
                        DEVTYPEID_AIRCONDITION == logicDevTypeId:  # 红外伴侣
            return DEVTYPEID_INFRARED
        else:
            return logicDevTypeId

    # 中控组网成功
    def buildConfigHGCsuccessPack(self, addr):
        try:
            macAddr = self.getMacAddrByDevAddr(addr)
            buffer = struct.pack("=10s2B",macAddr,0x51,0x01)

            buffer2 = struct.pack("=13B", 0,0,0,0,0,0,0,0,0,0,0,0,0)
            buffer = buffer + buffer2

            buffer = self.pack0(buffer)
            headerBodyBuffer = self.buildHeader(0x90, len(buffer)) + buffer
            return headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("buildConfigHGCsuccessPack err: %s" %(addr))
            return

    # {'srcaddr':'','srctype':'','srcchannel':'','dstaddr':'','dsttype':'','dstchannel':'','state':''}
    def buildDeviceLinkReqestPack(self, config):
        try:
            srcaddr = config.get("srcaddr")
            srctype = config.get("srctype")
            srcchannel = config.get("srcchannel")
            dstaddr = config.get("dstaddr")
            dsttype = config.get("dsttype")
            dstchannel = config.get("dstchannel")
            state = config.get("state")

            srcMacAddr = self.getMacAddrByDevAddr(srcaddr)
            dstMacAddr = self.getMacAddrByDevAddr(dstaddr)

            if isinstance(srctype, unicode):
                srctype = srctype.encode('utf-8')
            if isinstance(dsttype, unicode):
                dsttype = dsttype.encode('utf-8')
            if isinstance(srcchannel, unicode):
                srcchannel = srcchannel.encode('utf-8')
            if isinstance(dstchannel, unicode):
                dstchannel = dstchannel.encode('utf-8')
            if isinstance(state, unicode):
                state = state.encode('utf-8')

            buffer = struct.pack("=10s2B10s3B",srcMacAddr,srctype,int(srcchannel)+1,dstMacAddr,dsttype,int(dstchannel)+1,int(state))
            headerBodyBuffer = self.buildHeader(CMDID_LINK_DEVICE, len(buffer)) + buffer
            return headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("device config err: %s" %(config))
            return

    # 控制命令格式 {"addr":"z-11111111","type":"Light","value":{"state":"1","coeff":"0"}}
    def buildControlReqestPack(self, deviceVal):
        try:
            devTypeName = deviceVal.get("type","")
            devTypeId = self.getDeviceTypeIdByName(devTypeName)
            if devTypeId <= 0:
                Utils.logError( "control cmd, devTypeId invalid：%s" % (deviceVal))
                return None
            
            value = deviceVal.get("value", {})
            devAddr = deviceVal.get("addr", "")
            if len(devAddr) < 3:
                Utils.logError( "control cmd, device addr：%s invalid" % (devAddr))
                return None

            macAddr = self.getMacAddrByDevAddr(devAddr)
            physicalDevTypeId = self.getPhysicalDevTypeId(devTypeId)
            macTypeBuffer = struct.pack("=10sB", macAddr, physicalDevTypeId)
            
            if DEVTYPEID_LIGHTAJUST == devTypeId:
                # 同时调节两路，因此需要从redis获取数值
                # state的值：stateN:0,N表示索引为N的灯打开
                state = value.get("state","0")
                lightCoeff = value.get("coeff", "100")
                if value.has_key("stateAll"):
                    state = value.get("stateAll", "0")
                    if int(lightCoeff) == 0:
                        lightCoeff = "100"

                lightingTime = value.get("lightingTime", "0")
                if state == "" or lightCoeff == "" or lightingTime == "":
                    Utils.logError('control light, value invalid, state or coeff is empty:%s' % (deviceVal))
                    return None
                bodyBuffer = struct.pack("=3B11s", int(state), int(lightCoeff), int(lightingTime), "")
            elif devTypeId in [DEVTYPEID_LIGHT1, DEVTYPEID_LIGHT2, DEVTYPEID_LIGHT3, DEVTYPEID_LIGHT4, DEVTYPEID_LCD_SWITCH]:
                # state的值：stateN:0,N表示索引为N的灯打开
                state1 = value.get("state", None)
                state2 = value.get("state2", None)
                state3 = value.get("state3", None)
                state4 = value.get("state4", None)
                stateAll = value.get("stateAll", None)
                # 20151009: multi-channel in one message
                # # lightIndex = 0
                # lightValue1 = 0
                # lightValue2 = 0
                # lightValue3 = 0
                # lightValue4 = 0
                # if(state1 != None):
                #     # lightIndex = 1
                #     lightValue1= state1
                # if(state2 != None):
                #     # lightIndex = 2
                #     lightValue2 = state2
                # if(state3 != None):
                #     # lightIndex = 3
                #     lightValue3 = state3
                # if(state4 != None):
                #     # lightIndex = 4
                #     lightValue4 = state4
                # # else:
                # #     Utils.logError('control light invalid,state value is empty:%s' % (deviceVal))
                # #     return None;
                # # lightValue = lightValue[0:1]
                # # bodyBuffer = struct.pack("=3B11s",int(lightIndex),int(lightValue),0,"")
                # bodyBuffer = struct.pack("=8B6s",int(lightValue1),0, int(lightValue2),0, int(lightValue3),0, int(lightValue4),0, "")

    
                lightIndex = 0
                if state1 is not None:
                    lightIndex = 1
                    lightValue = state1
                elif state2 is not None:
                    lightIndex = 2
                    lightValue = state2
                elif state3 is not None:
                    lightIndex = 3
                    lightValue = state3
                elif state4 is not None:
                    lightIndex = 4
                    lightValue = state4
                elif stateAll is not None:
                    lightIndex = 15
                    lightValue = stateAll
                else:
                    Utils.logError('control light invalid,state value is empty:%s' % (deviceVal))
                    return None

                if devTypeId == DEVTYPEID_LCD_SWITCH:  # LCD开关控制灯的命令
                    controlType = value.get('controlType', None)
                    index = int(value.get('index', lightIndex))
                    if str(controlType) in ['2', '3']:
                        # 控制类型不是None说明是同步开关名称操作
                        bodyBuffer = struct.pack("=2B12s", int(controlType), index, lightValue)
                    elif str(controlType) == '4':
                        # 同步LCD开关图表
                        bodyBuffer = struct.pack("=3B11s", 4, index, int(lightValue), "")
                    else:
                        # 控制类型是None的话说明是开关灯操作
                        bodyBuffer = struct.pack("=3B11s", 1, index, int(lightValue), "")

                else:
                    lightValue = lightValue[0:1]
                    bodyBuffer = struct.pack("=3B11s", int(lightIndex), int(lightValue), 0, "")
            # elif DEVTYPEID_SOCKET == devTypeId or DEVTYPEID_CURTAIN == devTypeId or DEVTYPEID_SOV == devTypeId:  # 插座, 电磁阀
            #     bodyBuffer = struct.pack("=B13s", int(value.get("state", "0")), "")
            elif DEVTYPEID_SOCKET == devTypeId or DEVTYPEID_CURTAIN == devTypeId:  # 插座, 红外入侵
                bodyBuffer = struct.pack("=B13s", int(value.get("state", "0")), "")
            elif DEVTYPEID_SOV == devTypeId:  # 电磁阀
                bodyBuffer = struct.pack("=B13s", int(value.get("set", "0")), "")
            elif DEVTYPEID_TV == devTypeId or DEVTYPEID_IPTV == devTypeId or DEVTYPEID_DVD == devTypeId or \
                            DEVTYPEID_AIRCONDITION == devTypeId: #红外伴侣
                subDevType = devTypeId - DEVTYPEID_TV  # 0: TV   1: 机顶盒   2: DVD   3: 空调
                # mode 0:control        1:learn        2:query
                bodyBuffer = struct.pack("=3B11s", int(value.get("mode", "0")), subDevType, int(value.get("key", "0")), "")
            elif DEVTYPEID_EXIST_SENSOR == devTypeId or DEVTYPEID_CURTAIN_SENSOR == devTypeId \
                    or DEVTYPEID_GSM == devTypeId:  # 存在传感器、门窗磁、幕帘(红外入侵)
                bodyBuffer = struct.pack("=2B12s", 0, int(value.get("set", "")), "")
            elif DEVTYPEID_LOCK == devTypeId:  # 智能门锁
                bodyBuffer = UtilsLock().controlBuffer(value)

            elif DEVTYPEID_PROJECTOR == devTypeId:  # 投影仪
                bodyBuffer = struct.pack("=B13s", int(value.get("state", "0")), "")

            elif DEVTYPEID_ACOUSTO_OPTIC_ALARM == devTypeId:  # 声光报警器
                bodyBuffer = struct.pack("=B13s", int(value.get("state", "0")), "")

            elif DEVTYPEID_CENTRAL_AIRCONDITION == devTypeId:  # 中央空调

                addr = str(value.get("addr", "CAC_1"))
                if addr[:4] == "CAC_":
                    addr = addr[4:]
                Utils.logInfo("CAC addr:%s"%addr)
                bodyBuffer = struct.pack("=4Bh8s", int(value.get("protocol", "1")),
                                         int(addr), int(value.get("controlCmd", "0")),
                                         int(value.get("length", "2")), int(value.get("controlData", "0")), "")

            elif DEVTYPEID_AUDIO == devTypeId: # 背景音乐(485接入的音丽士、华尔斯)
                cmd = int(value.get("cmd", "1"))
                data_len = value.get("dataLen", "1")
                volume = "6"  # 音量默认给6
                if cmd == 1:  # 开关命令
                    data = value.get("data", "1")
                elif cmd == 2:  # 音量，取值0-100
                    data = value.get("data", "30")
                elif cmd == 3:  # 音量逐级调节
                    data = value.get("data", "3")
                elif cmd == 4:  # 设备播放状态
                    data = value.get("data", "1")
                elif cmd == 5:  # 指定播放曲目的序号
                    data = value.get("data", 1)
                    volume = value.get("volume", "5")
                    maxVol = value.get("maxVol", 0)  # 最大音量
                    period = value.get("period", 0)  # 音量过度时间
                    date_len = 5  # 与叶工约定，修改协议后播放指定曲目数据长度都发5
                elif cmd == 6:  # 上一首、下一首
                    data = value.get("data", "2")
                else: # 按列表顺序切换曲目
                    data = value.get("data", "2")

                if data == "" or data is None:
                    data = "1"

                if volume == "0" or volume == 0:
                    volume = "5"

                if int(data_len) == 1:
                    bodyBuffer = struct.pack("=3B11s", cmd, int(data_len), int(data), "")
                else:
                    bodyBuffer = struct.pack("=2Bh3B7s", cmd, int(data_len), int(data), int(volume), int(maxVol), int(period), "")

            elif DEVTYPEID_AIR_SYSTEM == devTypeId:  # 新风系统(485协议接入)
                # 命令类型：1-运行状态(0停1运行)；2-手自动切换(0自动，1手动)；3-除尘开关(0关1开)；4-设置目标速度(1、2、3、4)
                cmd = int(value.get("cmd", "1"))
                data = int(value.get("data", "0"))
                bodyBuffer = struct.pack("=3B11s", cmd, 1, data, "")

            elif DEVTYPEID_WUHENG_SYSTEM == devTypeId:  # 五恒系统
                addrIndex = int(value.get("addrIndex", "1"))
                # 2-运行状态(0关1开)；3-模式(0关，1制冷，2制热，3除湿，4通风, 5加湿)；4-调整风量(1低俗，2中速，3高速)；5-控温(16~35度)
                cmd = int(value.get("cmd", "4"))
                data = int(value.get("data", "0"))
                bodyBuffer = struct.pack("=4B10s", addrIndex, cmd, 1, data, "")

            elif DEVTYPEID_FLOOR_HEATING == devTypeId:  # 非3.5寸屏接入的地暖
                cmd = int(value.get("cmd", "0"))
                data = value.get("data", None)
                if data is None:
                    Utils.logError("FloorHeating control param error...data is None")
                    return None

                if cmd == 2:  # 地暖设置温度，温度值最大为35,10倍后大于255，所以data_len数值为2
                    data = float(data)
                    if data < 5:
                        data = 5
                    elif data > 35:
                        data = 35
                    bodyBuffer = struct.pack("=2BH10s", cmd, 2, data * 10, "")

                else:  # 其他命令，data_len数值为1
                    bodyBuffer = struct.pack("=3B11s", cmd, 1, int(data), "")

            elif devTypeId == DEVTYPEID_AIR_FILTER:  # 空气净化器
                cmd = int(value.get("cmd", 1))
                if cmd <= 1:
                    Utils.logError("Air filter control command error,device addr: %s" % str(devAddr))
                    return None

                mode = int(value.get("data", 3))
                if cmd == 2 and mode == 4:
                    # 手动模式需要发送风速
                    windSpeed = int(value.get("speed", 10))  # 风速：0-100
                    if windSpeed < 0:
                        windSpeed = 10
                    elif windSpeed > 100:
                        windSpeed = 100
                    data_len = int(value.get("dataLen", 2))
                    bodyBuffer = struct.pack("=4B10s", cmd, data_len, mode, windSpeed, "")
                elif cmd == 5:
                    data_len = int(value.get("dataLen", 1))
                    screen = int(value.get("data", 0))  # 屏幕开关：0-息屏，1-亮屏
                    bodyBuffer = struct.pack("=3B11s", cmd, data_len, screen, "")
                else:
                    #  重置HEAP寿命、重置空气净化量以及其他控制模式
                    data_len = int(value.get("dataLen", 1))
                    bodyBuffer = struct.pack("=3B11s", cmd, data_len, mode, "")

            elif devTypeId == DEVTYPEID_LIGHTAJUST_PANNEL:  # 调光控制面板
                state = int(value.get("state", 0))
                if state == 1 and value.get("coldRate") is not None and value.get("warmRate") is not None:
                    # 节律模式还需要2个占空比
                    cold_rate = int(value.get("coldRate"))
                    warm_rate = int(value.get("warmRate"))
                    bodyBuffer = struct.pack("=BHH9s", state, warm_rate, cold_rate, '')
                else:
                    # 其他模式
                    bodyBuffer = struct.pack("=B13s", state, '')

            else:
                Utils.logError("control cmd, device type invalid: %s " % (devAddr))
                return None
            
            bodyBuffer = macTypeBuffer + bodyBuffer
            bodyBuffer = self.pack0(bodyBuffer)
            headerBodyBuffer = self.buildHeader(CMDID_CONTROL_DEVICE, len(bodyBuffer)) + bodyBuffer
            return headerBodyBuffer + self.buildTailer(headerBodyBuffer)
        except:
            Utils.logException("error when buildControlReqestPack")
            return ""

    # 构建退网命令
    # {"name": "dev1", "addr": "xxxx", "type": "type1"}
    def buildQuitNetworRequestPack(self, devParam):
        Utils.logDebug("buildQuitNetworRequestPack() devParam: %s" % str(devParam))
        try:
            devAddr = devParam.get("addr", None)
            devTypeName = devParam.get("type", None)
            if devAddr is None or devTypeName is None:
                Utils.logError("buildQuitNetworRequestPack failed, device addr: %s or device type: %s" % (str(devAddr), str(devTypeName)))
                return None
            if devTypeName in [DEVTYPENAME_TV, DEVTYPENAME_AIRCONDITION, DEVTYPENAME_IPTV, DEVTYPENAME_DVD]:
                # 红外设备在网关内部用的是虚拟类型，实际红外转发的ID是0x03
                devTypeId = 0x03
            else:
                devTypeId = self.getDeviceTypeIdByName(devTypeName)
            devMac = self.getMacAddrByDevAddr(devAddr)

            if devMac == "":
                Utils.logError("buildQuitNetworRequestPack -> has no addr")
                return None

            if devTypeId <= 0:
                Utils.logError("buildQuitNetworRequestPack -> addr:%s, type name is invalid" % devAddr)
                return None

            macTypeBuffer = struct.pack("=10sB", devMac, devTypeId)  # mac和设备类型
            cmdBody = struct.pack("=14s", "")  # 参数报文，退网命令置空
            bodyBuffer = macTypeBuffer + cmdBody  # 拼接报文体
            headerBodyBuffer = self.buildHeader(CMDID_DEVICECONFIG_DEVICE, len(bodyBuffer)) + bodyBuffer  # 报文头+报文体
            tailBuffer = self.buildTailer(headerBodyBuffer)  # 构建报文结尾
            return headerBodyBuffer + tailBuffer

        except Exception:
            Utils.logError("buildQuitNetworRequestPack error....")
            return ""

    def parse_code(self, payload):
        device_type = payload.get("device_type", None)
        file_name = payload.get("fid", None)
        line_index = payload.get("index", None)
        format_string = payload.get("format_string", None)
        c3rv = payload.get("c3rv", None)

        if not file_name or not line_index or not format_string or not c3rv:
            return None

        if format_string.endswith(","):
            format_string = format_string[:-1]
        format_string_list = format_string.split(",")
        if c3rv.endswith("|"):
            replace_list = c3rv.split("|")[:-1]
        else:
            replace_list = c3rv.split("|")

        if payload.get("device_type") == "TV": # infrared/TV/codes/ 下的文件各位数文件名新式是000.txt
            while len(str(file_name)) < 3:
                file_name = "0" + str(file_name)

        file_dir = "/ihome/etc/infrared/" + device_type + "/codes/" + str(file_name) + ".txt"
        if not os.path.exists(file_dir):  # 新版本会将码库直接做到网关系统内，为了兼容老版本先寻找原路径下文件，没有则找新的路径
            file_dir = "/etc/infrared/" + device_type + "/codes/" + str(file_name) + ".txt"
        with open(file_dir, "r") as f:
            line_list = f.readlines()

        target_line = line_list[int(line_index)-1]
        if target_line.endswith("\n"):
            target_line = target_line[:-1]
        if target_line.endswith("\r"):
            replacement_list = target_line.split(",")[:-1]
        else:
            replacement_list = target_line.split(",")

        count = 0
        for item in replace_list:
            start, offset = item.split("-")
            start = int(start)
            offset = int(offset)
            if start == 0 and offset == 0: # return the infrared code read from the file directly when the c3rv is 0-0
                format_int_list = []
                for tmp in replacement_list:
                    format_int_list.append(int(tmp, 16))
                return format_int_list
            else:
                for i in range(0, offset):
                    format_string_list[start + i] = replacement_list[count + i]
            count += offset
        format_int_list = []
        for item in format_string_list:
            format_int_list.append(int(item, 16))
        return format_int_list

    def buildInfraredControlPack(self, deviceVal):
        try:
            devTypeName = deviceVal.get("type", "")
            devTypeId = self.getDeviceTypeIdByName(devTypeName)
            if (devTypeId <= 0):
                Utils.logError("control cmd, devTypeId invalid：%s" % (deviceVal))
                return None

            value = deviceVal.get("value", {})
            devAddr = deviceVal.get("addr", "")
            if (len(devAddr) < 3):
                Utils.logError("control cmd, device addr：%s invalid" % (devAddr))
                return None

            macAddr = self.getMacAddrByDevAddr(devAddr)
            physicalDevTypeId = self.getPhysicalDevTypeId(devTypeId)
            macTypeBuffer = struct.pack("=10sB", macAddr, physicalDevTypeId)
            subDevType = devTypeId - DEVTYPEID_TV
            # if devTypeId == 0x1001:
                # Utils.logSuperDebug("deviceVal is %s" % str(deviceVal))
                # Utils.logSuperDebug("value in deviceVal is %s" % str(value))
            command_int_list = self.parse_code(value)
            Utils.logInfo("===>length of command_str_list: %s" % command_int_list)
            if not command_int_list:
                return None

            # 计算总共需要几个包
            full_pack = len(command_int_list) / 100
            remaining_buffer = len(command_int_list) % 100
            total_pack = full_pack
            if remaining_buffer > 0:
                total_pack = full_pack + 1

            buffer_list = []
            if full_pack > 0:
                for i in range(0, full_pack):
                    bodyBufferInfo = struct.pack("=2B", total_pack, i+1)
                    args = tuple(command_int_list[100*i:100*(i+1)])
                    bodyBufferData = struct.pack("=100B", *args)
                    bodyBuffer = macTypeBuffer + bodyBufferInfo + bodyBufferData
                    headerBodyBuffer = self.buildHeader(CMDID_CONTROL_DEVICE, len(bodyBuffer)) + bodyBuffer
                    one_entire_buffer = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                    buffer_list.append(one_entire_buffer)
            if remaining_buffer > 0:
                bodyBufferInfo = struct.pack("=2B", total_pack, total_pack)
                args = tuple(command_int_list[-remaining_buffer:])
                fmt = "=" + str(remaining_buffer) + "B"
                bodyBufferData = struct.pack(fmt, *args)
                bodyBuffer = macTypeBuffer + bodyBufferInfo + bodyBufferData
                headerBodyBuffer = self.buildHeader(CMDID_CONTROL_DEVICE, len(bodyBuffer)) + bodyBuffer
                last_buffer = headerBodyBuffer + self.buildTailer(headerBodyBuffer)
                buffer_list.append(last_buffer)
            Utils.logInfo("===>buildInfraredControlPack, buffer_list: %s" % buffer_list)
            return buffer_list
        except Exception as err:
            Utils.logError("===>buildInfraredControlPack error: %s" % err)
            return None

    def pack0(self, buffer):
        if len(buffer) == 25:
            return buffer
        bodyBuffer = []
        for item in buffer:
            bodyBuffer.append(item)

        while len(bodyBuffer) < 25:
            bodyBuffer.append(0)

        Utils.logHex('pack0', bodyBuffer)
        return struct.pack("=25B",
                           bodyBuffer[0],
                           bodyBuffer[1],
                           bodyBuffer[2],
                           bodyBuffer[3],
                           bodyBuffer[4],
                           bodyBuffer[5],
                           bodyBuffer[6],
                           bodyBuffer[7],
                           bodyBuffer[8],
                           bodyBuffer[9],
                           bodyBuffer[10],
                           bodyBuffer[11],
                           bodyBuffer[12],
                           bodyBuffer[13],
                           bodyBuffer[14],
                           bodyBuffer[15],
                           bodyBuffer[16],
                           bodyBuffer[17],
                           bodyBuffer[18],
                           bodyBuffer[19],
                           bodyBuffer[20],
                           bodyBuffer[21],
                           bodyBuffer[22],
                           bodyBuffer[23],
                           bodyBuffer[24]
                           )

    ##解析收到的设备命令
    # def parseRecvCmds(self,recvCmds):
    #     if(recvCmds == None):
    #         return;
    #
    #     #将这次收到的和以前剩余的连接起来
    #     self.recvCmds = self.recvCmds + recvCmds
    #
    #     cmdsValue = []
    #     while(True):
    #         if(len(self.recvCmds) < HEADERTAIL_LEN):
    #             break # 不完整的包
    #
    #         #解析出命令字
    #         try:
    #             startFlag,transId,cmdId,bodyLen = struct.unpack("=3BH", self.recvCmds[0:HEADER_LEN])
    #         except:
    #             Utils.logException("parseRecvCmds error")
    #             break;
    #
    #         #如果头标识不对
    #         if(startFlag != 0x69):
    #             Utils.logError("pack all command bufferLen=%d, startFlag invalid!" % (len(self.recvCmds)))
    #             self.recvCmds = ""
    #             break;
    #
    #         if(bodyLen > 3200):
    #             Utils.logError("pack command bodyLen=%d, all buffer len=%d,startFlag invalid!" % (bodyLen, len(self.recvCmds)))
    #             self.recvCmds = ""
    #             break;
    #
    #         if(len(self.recvCmds) < HEADERTAIL_LEN + bodyLen):
    #             if(len(self.recvCmds) > 3200):
    #                 Utils.logError("pack allCommandLen=%d, but there's not a entire pack. bodyLen=%d!" % (len(self.recvCmds),bodyLen))
    #                 self.recvCmds = ""
    #             break # 不完整的包
    #
    #         oneCmdBuffer = self.recvCmds[0:HEADERTAIL_LEN + bodyLen]
    #         self.recvCmds = self.recvCmds[HEADERTAIL_LEN + bodyLen:]
    #
    #         try:
    #             #解析该包, 一个包中可能包含有多个设备的命令数据
    #             cmdsValueInPack = self.parseCmdFromOneBuffer(oneCmdBuffer)
    #             if(cmdsValueInPack is not None):
    #                 for cmd in cmdsValueInPack:
    #                     cmdsValue.append(cmd)
    #         except: # 如果抛出了异常，说明包检验发生问题，应抛弃整个遗留的包，重新开始接受
    #             Utils.logException("parseRecvCmds packet error.")
    #             self.recvCmds = ""
    #
    #     return cmdsValue

    # def parseCmdFromOneBuffer(self, oneCmdBuffer):
    #     try:
    #         startFlag,transId,cmdId,bodyLen = struct.unpack("=3BH", oneCmdBuffer[0:HEADER_LEN])
    #     except: # 如果抛出了异常，说明包检验发生问题，应抛弃整个遗留的包，重新开始接受
    #         Utils.logException( "parseCmdFromOneBuffer解析数据错误" )
    #
    #     dataBody = oneCmdBuffer[HEADER_LEN:HEADER_LEN+bodyLen]
    #     checkValue,endFlag = struct.unpack("=2B", oneCmdBuffer[-2:])
    #     checkValueShould = self.calcCheckValue(oneCmdBuffer[CHECKSUM_START:-2])
    #     if(checkValue != checkValueShould):
    #         Utils.logError( "recv a command pack, but given checkValue is %d, should %d" % (checkValue, checkValueShould))
    #         return None
    #
    #     if(startFlag != START_FLAG or endFlag != END_FLAG):
    #         Utils.logError( "recv a command pack, start flag:%d, end flag:%d, invalid" % (startFlag, endFlag))
    #         raise NameError,("command Pack Flag error","please clear buffer")
    #         return None
    #
    #     # if(cmdIdResponse <= 0x80):
    #     #     Utils.logError( "recv a pack, cmdId:%d < 0x80" % (cmdIdResponse))
    #     #     return None
    #     #
    #     # cmdId = cmdIdResponse - 0x80
    #
    #     # if(cmdId != CMDID_SEARCH_DEVICE and cmdId != CMDID_CONTROL_DEVICE and cmdId != CMDID_QUERY_DEVICE
    #     #    and cmdId != CMDID_DEVICECONFIG_DEVICE and cmdId != CMDID_REGISTERDATA_DEVICE
    #     #    and cmdId != CMDID_QUERY_ENERGY_ELEC and cmdId != CMDID_QUERY_ENERGY_WATER and cmdId != CMDID_QUERY_ENERGY_GAS ):
    #     #     Utils.logError( "recv a pack, cmdId:%d, do not support this command" % (cmdIdResponse))
    #     #     return None
    #
    #     # return self.onAnyCmdResponse(cmdId, dataBody)
    #
    #     if(cmdId == GlobalVars.CMDID_DEVICE_LINKDEV): ##关联设备 控制命令
    #         ##应该不会走这个分支！！
    #         return self.onLinkDeviceCmd(cmdId, dataBody)

    # def onLinkDeviceCmd(self, cmdId, data):
    #     try:
    #         macAddr, devTypeId, buffer = struct.unpack("=10sB14s", data)
    #         devAddr = self.getDevAddrByMac(macAddr)
    #         if(devAddr  == "0000000000000000"):
    #             return None
    #         device = self.getDeviceStatusByAddr(devAddr)
    #         if(device is None):
    #             devPropObj = DBManagerDeviceProp().getDeviceByDevId(devAddr)
    #             if devPropObj == None:
    #                 Utils.logInfo( "do not config device with addr:%s" % (devAddr))
    #                 return None
    #             DBManagerDevice().initDevStatus(devPropObj)
    #             return None
    #
    #         value = None
    #
    #         if(devTypeId == DEVTYPEID_LIGHT1):
    #             state,coeff = struct.unpack("=2B", buffer[0:2])
    #             value = {'state':state}
    #         elif(devTypeId == DEVTYPEID_LIGHT2):
    #             state,coeff,state2,coeff2 = struct.unpack("=4B", buffer[0:4])
    #             value = {'state':state,'state2':state2}
    #         elif(devTypeId == DEVTYPEID_LIGHT3):
    #             state,coeff,state2,coeff2,state3,coeff3 = struct.unpack("=6B", buffer[0:6])
    #             value = {'state':state,'state2':state2,'state3':state3}
    #         elif(devTypeId == DEVTYPEID_LIGHT4):
    #             state,coeff,state2,coeff2,state3,coeff3,state4,coeff4 = struct.unpack("=8B", buffer[0:8])
    #             value = {'state':state,'state2':state2,'state3':state3,'state4':state4}
    #         elif(devTypeId == DEVTYPEID_MODE_PANNEL):
    #             state,state2,state3,state4,state5,state6 = struct.unpack("=6B", buffer[0:6])
    #             value = {'state':state,'state2':state2,'state3':state3,'state4':state4,'state5':state5,'state6':state6}
    #         if(value is None):
    #             print "mac: %s, value is none " % (macAddr)
    #             return None
    #     except:
    #         Utils.logException("unpack error in onDeviceQryCmdResponse, %d"%(devTypeId))
    #         return None
    #     #组织设备数据
    #     # curTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S');
    #     # [{"name":"device1","addr":"z-111111","type":"light","value":{"state":"1"}}]
    #     deviceRTData = [{"cmdId":cmdId, "name":device.get("name",""),"addr":devAddr,"type":device.get("type",""),"value":value}]
    #
    #     return deviceRTData
                
    # 解析收到的设备数据包, 返回得到的各个设备的数据
    def parseRecvData(self, recvBuffer):
        if(recvBuffer == None):
            return (None, None)
        
        # 将这次收到的和以前剩余的连接起来
        self.recvBuffer = self.recvBuffer + recvBuffer
        
        devicesValue = []
        while(True):
            # Utils.logError("while in PacketParser line 978...")
            if(len(self.recvBuffer) < HEADERTAIL_LEN):
                break # 不完整的包
            
            #解析出命令字
            try:
                startFlag,transId,cmdId,bodyLen = struct.unpack("=3BH", self.recvBuffer[0:HEADER_LEN])
                # Utils.logInfo("===>parseRecvData, cmdId: %s" % cmdId)
            except:
                Utils.logException("parseRecvData error")
                break
            
            #如果头标识不对
            if(startFlag != 0x68):
                Utils.logError("pack all bufferLen=%d, startFlag invalid!" % (len(self.recvBuffer)))
                self.recvBuffer = ""
                break
            
            if(bodyLen > 3200):
                Utils.logError("pack bodyLen=%d, all buffer len=%d,startFlag invalid!" % (bodyLen, len(self.recvBuffer)))
                self.recvBuffer = ""
                break
            
            if(len(self.recvBuffer) < HEADERTAIL_LEN + bodyLen):
                if(len(self.recvBuffer) > 3200):
                    Utils.logError("pack allBufferLen=%d, but there's not a entire pack. bodyLen=%d!" % (len(self.recvBuffer),bodyLen))
                    self.recvBuffer = ""
                break  # 不完整的包
            
            onePackBuffer = self.recvBuffer[0:HEADERTAIL_LEN + bodyLen]
            self.recvBuffer = self.recvBuffer[HEADERTAIL_LEN + bodyLen:]
            
            try:
                # 解析该包, 一个包中可能包含有多个设备的数据
                devicesValueInPack = self.parseAPackage(onePackBuffer)
                if devicesValueInPack is not None:
                    # 中控3.5寸屏上的控制命令，一个一个解析并下发
                    if cmdId == 0x14:
                        return (cmdId, devicesValueInPack)
                    for deviceVal in devicesValueInPack:
                        devicesValue.append(deviceVal)
            except: # 如果抛出了异常，说明包检验发生问题，应抛弃整个遗留的包，重新开始接受
                Utils.logException("parseRecvData packet error.")
                self.recvBuffer = ""
        return (cmdId, devicesValue)
    
    def parseAPackage(self, onePackBuffer):

        try:
            startFlag,transId,cmdId,bodyLen = struct.unpack("=3BH", onePackBuffer[0:HEADER_LEN])
        except: # 如果抛出了异常，说明包检验发生问题，应抛弃整个遗留的包，重新开始接受
            Utils.logException( "parseAPackage解析数据错误" )
                
        dataBody = onePackBuffer[HEADER_LEN:HEADER_LEN+bodyLen]
        checkValue,endFlag = struct.unpack("=2B", onePackBuffer[-2:])
        checkValueShould = self.calcCheckValue(onePackBuffer[CHECKSUM_START:-2])
        if(checkValue != checkValueShould):
            Utils.logError( "recv a pack, but given checkValue is %d, should %d" % (checkValue, checkValueShould))
            return None
        
        if(startFlag != START_FLAG or endFlag != END_FLAG):
            Utils.logError( "recv a pack, start flag:%d, end flag:%d, invalid" % (startFlag, endFlag))
            raise NameError,("Pack Flag error","please clear buffer") 
            return None
        
        if(cmdId > 0x80):
            # Utils.logError( "recv a pack, cmdId:%d < 0x80" % (cmdIdResponse))
            # return None
            cmdId = cmdId - 0x80

        # if(cmdId != CMDID_SEARCH_DEVICE and cmdId != CMDID_CONTROL_DEVICE and cmdId != CMDID_QUERY_DEVICE
        #    and cmdId != CMDID_DEVICECONFIG_DEVICE and cmdId != CMDID_REGISTERDATA_DEVICE
        #    and cmdId != CMDID_QUERY_ENERGY_ELEC and cmdId != CMDID_QUERY_ENERGY_WATER and cmdId != CMDID_QUERY_ENERGY_GAS ):
        #     Utils.logError( "recv a pack, cmdId:%d, do not support this command" % (cmdIdResponse))
        #     return None
        if cmdId == 0x03:  # 批量添加时上报的是 0x83，减去80后是 0x03
            # Utils.logSuperHex("onePackBuffer in parseAPackage", onePackBuffer)
            return self.onAnyCmdResponse(cmdId, onePackBuffer)
        else:
            return self.onAnyCmdResponse(cmdId, dataBody)

    #一个设备的查询命令返回
    #数据区                        
    #个数+[Mac[0:7] Type buf[0:17]]
    def onSearchDeviceCmdResponse(self, data):
        deviceNum = struct.unpack("=B", data[0:1])
        devsBuffer = data[1:]
        bufferP = 0
        devicesData = []
        for i in range(0, deviceNum):
            if(bufferP + 25 > len(devsBuffer)):
                break
            oneDevData = devsBuffer[bufferP:bufferP + 25]
            devicesRTData = self.onDeviceQryCmdResponse(oneDevData)
            for oneRec in devicesRTData:
                devicesData.append(oneRec)
            bufferP = bufferP + 25
            
        return devicesData

    def onBatchScanCmdResponse(self, data):
        retval, onePackBuffer = self._GetAPackFromBuffer(data)
        if retval == -1:
            return []
        # Utils.logSuperHex("onePackBuffer in onBatchScanCmdResponse()", onePackBuffer)
        Utils.logInfo('rx scan device response.')
        devices = []
        bodyLen = len(onePackBuffer)
        devNum = int(bodyLen / 25)
        bodyBuffer = data[5:devNum * 25 + 5]
        for i in range(0, devNum, 1):
            device = {}
            oneDevBuffer = bodyBuffer[i * 25:i * 25 + 25]
            macAddr, phyTypeid = struct.unpack("=10sB", oneDevBuffer[0:11])
            swverion, hwversion = struct.unpack("=2B", oneDevBuffer[-2:])
            numbers = struct.unpack("=10B", macAddr)
            devAddr = "%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X" % numbers
            if phyTypeid not in [0x01, 0x11, 0x21, 0x31, 0x41, 0x02, 0x04]:
                # 设备类型不是插座、调光单、多联灯、窗帘控制器，不批量添加
                continue
            # if (phyTypeid == 0x03):  # 红外就是0x03
            #     if (reqDevTypeId < DEVTYPEID_INFRARED_DEV_MIN or reqDevTypeId > DEVTYPEID_INFRARED_DEV_MAX):
            #         continue
            # # 如果是中控设备，还要判断是否接入了地暖
            # elif phyTypeid == 0x51:
            #     device["extraDevice"] = ""
            #     extra_device = struct.unpack("=B", oneDevBuffer[12])
            #     # 1为3.5寸，2为地暖
            #     if extra_device[0] == 2:
            #         device["extraDevice"] = "FloorHeating"
            # else:
            #     pass
                # if (typeName != "" and reqDevTypeId != phyTypeid):
                #     continue

            device["id"] = devAddr
            device["name"] = self._getDeviceDefaultName(phyTypeid)
            device["addr"] = devAddr
            device["softwareVer"] = Utils.calculateVersion(swverion)  # device software version
            device["hardwareVer"] = Utils.calculateVersion(hwversion)  # device hardware version
            device["type"] = self.getDeviceTypeNameById(phyTypeid)  # 设备类型
            device["roomId"] = "-1"
            device["areaId"] = "-1"  # 批量扫描时，首次扫到将房间ID和区域ID设为-1，以作为APP端查询的过滤条件
            devices.append(device)

        return devices

    def _GetAPackFromBuffer(self, recvBuffer):
        onePack = ""
        if (recvBuffer is None or len(recvBuffer) < HEADERTAIL_LEN):
            return (0, onePack)

        # 解析出命令字
        try:
            startFlag, transId, cmdId, bodyLen = struct.unpack("=3BH", recvBuffer[0:HEADER_LEN])
        except Exception as e:
            onePack = "%s" % (e)
            return (-1, onePack)

        # 如果头标识不对
        if (startFlag != 0x68):
            onePack = ("pack all bufferLen=%d, startFlag invalid!" % (len(recvBuffer)))
            recvBuffer = ""
            return (-1, onePack)

        if (bodyLen > 3200):
            onePack = ("pack bodyLen=%d, all buffer len=%d,startFlag invalid!" % (bodyLen, len(recvBuffer)))
            recvBuffer = ""
            return (-1, onePack)

        if (len(recvBuffer) < HEADERTAIL_LEN + bodyLen):
            if (len(recvBuffer) > 3200):
                onePack = (
                "pack allBufferLen=%d, but there's not a entire pack. bodyLen=%d!" % (len(recvBuffer), bodyLen))
                recvBuffer = ""
            return (-1, onePack)  # 不完整的包

        onePack = recvBuffer[HEADER_LEN:HEADER_LEN + bodyLen]
        recvBuffer = recvBuffer[HEADERTAIL_LEN + bodyLen:]
        return (1, onePack)

    def _getDeviceDefaultName(self, devType):
        name_dict = {
            0x01: "调光灯",
            0x11: "单联灯",
            0x21: "二联灯",
            0x31: "三联灯",
            0x41: "四联灯",
            0x02: "插座",
            0x04: "窗帘"
        }
        dev_name = name_dict.get(devType, "未知设备")
        return dev_name

    def time_t2String(self, timet):
        return ""

    # 中控上报数据解析，目前主要是地暖上报数据解析
    def onHGCReportRequest(self, data):

        try:
            result = []
            hgc_addr, hgc_type, device_type, data_length, report_cmd = struct.unpack("=10s4B", data[:14])
            devAddr = self.getDevAddrByMac(hgc_addr)

            if report_cmd == 0:
                result = [{'hgcAddr': devAddr, 'type': hgc_type, 'ctrlDevType': device_type, 'reportCmd': report_cmd,
                           'value': {'state': 0}}]
            elif report_cmd == 1:
                setRoomT, measuredRoomT, setFloorT, measuredFloorT, extra_data = struct.unpack("=BHBH5s", data[14:])
                result = [{'hgcAddr': devAddr, 'type': hgc_type, 'ctrlDevType': device_type, 'reportCmd': report_cmd,
                           'value': {'state': 1, "setRoomTemperature": setRoomT, "measuredRoomTemperature": float(self.F2S(measuredRoomT/10.0, 1)),
                           "setFloorTemperature": setFloorT, "measuredFloorTemperature": float(self.F2S(measuredFloorT/10.0, 1))}}]

            elif report_cmd == 2:
                flag, time_1, temp_1, time_2, temp_2, time_3, temp_3, time_4, temp_4, extra_data = struct.unpack("=9B2s", data[14:])
                task_type = ""
                pack_number = 0
                if flag == 1:
                    task_type = "weekday"
                    pack_number = 1
                if flag == 2:
                    task_type = "weekday"
                    pack_number = 2
                if flag == 3:
                    task_type = "weekend"
                    pack_number = 1
                if flag == 4:
                    task_type = "weekend"
                    pack_number = 2
                time_task = dict()
                time_task["type"] = task_type
                time_task["packNumber"] = pack_number
                time_task["updateTime"] = int(time.time())
                time_list = []

                if data_length-2 == 2:
                    item_1 = {"timeIndex": time_1, "temperature": temp_1}
                    time_list.append(item_1)
                elif data_length-2 == 4:
                    item_1 = {"timeIndex": time_1, "temperature": temp_1}
                    item_2 = {"timeIndex": time_2, "temperature": temp_2}
                    time_list.append(item_1)
                    time_list.append(item_2)
                elif data_length-2 == 6:
                    item_1 = {"timeIndex": time_1, "temperature": temp_1}
                    item_2 = {"timeIndex": time_2, "temperature": temp_2}
                    item_3 = {"timeIndex": time_3, "temperature": temp_3}
                    time_list.append(item_1)
                    time_list.append(item_2)
                    time_list.append(item_3)
                elif data_length-2 == 8:
                    item_1 = {"timeIndex": time_1, "temperature": temp_1}
                    item_2 = {"timeIndex": time_2, "temperature": temp_2}
                    item_3 = {"timeIndex": time_3, "temperature": temp_3}
                    item_4 = {"timeIndex": time_4, "temperature": temp_4}
                    time_list.append(item_1)
                    time_list.append(item_2)
                    time_list.append(item_3)
                    time_list.append(item_4)

                time_task["taskList"] = time_list
                result = [{'hgcAddr': devAddr, 'type': hgc_type, 'ctrlDevType': device_type, 'reportCmd': report_cmd,
                           'timeTask': time_task, "packNumber": pack_number}]

            return result

        except Exception as err:
            Utils.logException("onFloorHeatingCmdResponse: %s" % err)

    # 中央空调上报数据解析
    def onCentalAirCmdResponse(self, data):
        try:
            addr, set_on, status_on, alarm, error_code, set_mode, status_mode, set_airflowrate, status_airflowrate, \
            measured_temp, set_temp, total_energy, set_airdirection, status_airdirection = struct.unpack("=11hi2h", data)
            addr = str(addr)
            value = {"set_on":set_on, "status_on":status_on, "alarm":alarm, "error_code":error_code, "set_mode":set_mode,
                     "status_mode":status_mode, "set_airflowrate":set_airflowrate, "status_airflowrate":status_airflowrate,
                     "measured_temp":measured_temp, "set_temp":set_temp, "set_airdirection":set_airdirection,
                     "status_airdirection":status_airdirection, "total_energy":total_energy, "addr": "CAC_" + addr}

            # status表的地址有UNIQUE约束，在中央空调的地址前加“CAC_” "CAC_" + addr
            deviceRTData = {"name":"CentralAirConditioner", "addr": "CAC_" + addr, "type":DEVTYNAME_CENTRAL_AIRCONDITION,
                            "value":value, "time":int(time.time())}
            devciesData = [deviceRTData]
            return devciesData
        except:
            Utils.logException("onEnergyElecCmdResponse")

    # [{"name":"device1","addr":"z-111111","type":"light","value":{"state":"1"}}]
    def onEnergyElecCmdResponse(self, data):

        try:
            # Uab,Ubc,Uca,Ia,Ib,Ic,Pa,Pb,Pc,PF,WP,peak,valley,plane = struct.unpack("=9hh4i", data)
            addr,Uab,Ubc,Uca,Ia,Ib,Ic,Pa,Pb,Pc,PF,WP,peak,valley,plane = struct.unpack("=B9hh4i", data)
            addr = str(addr)

            value = {"Uab":self.I2S(Uab), "Ubc":self.I2S(Ubc), "Uca":self.I2S(Uca), "Ia":self.F2S(Ia/10.0,1),
                     "Ib":self.F2S(Ib/10.0,1), "Ic":self.F2S(Ic/10.0,1), "Pa":self.F2S(Pa/10.0,1), "Pb":self.F2S(Pb/10.0,1),
                     "Pc":self.F2S(Pc/10.0,1), "PF":self.F2S(PF/1000.0,3), "energy":self.F2S(WP/10.0,1),
                     "peak":self.F2S(peak/10.0,1), "valley":self.F2S(valley/10.0,1), "plane":self.F2S(plane/10.0,1)}

            deviceRTData = {"name": "energyElec", "addr": addr, "type": DEVTYPENAME_ENERGY_ELEC, "value": value, "time": int(time.time())}
            devciesData = [deviceRTData]
            return devciesData   
        except:
            Utils.logException("onEnergyElecCmdResponse")
         
    
    # [{"name":"device1","addr":"z-111111","type":"light","value":{"state":"1"}}]
    def onEnergyWaterCmdResponse(self, data):

        # energy,pressure = struct.unpack("=ii", data[0:8])
        # value = {"energy":energy,"pressure":pressure}

        # energy = struct.unpack("=i", data[0:4])
        addr, energy = struct.unpack("=Bi", data[0:5])
        addr = str(addr)

        pressure = 0
        value = {"energy":self.F2S(energy/100.0, 2),"pressure":pressure}

        deviceRTData = {"name": "energyWater", "addr": addr, "type": DEVTYPENAME_ENERGY_WATER, "value": value, "time": int(time.time())}
        devciesData = [deviceRTData]
        return devciesData    

    ##中控控制命令
    def onHGCcontrolRequest(self, data):

        try:
            # struct.unpack("=10s7B8s", data_info)
            macAddr, devTypeId, controlDevType = struct.unpack("=10s2B", data[:12])
            devAddr = self.getDevAddrByMac(macAddr)
            if(devAddr  == None):
                return None
            if controlDevType == 0x01:
                controlDevNumber, controlCmdLength, controlData, isAdjust, coeff, extraData = struct.unpack("=5B8s", data[12:])
                result = [{'addr': devAddr, 'type': devTypeId, 'ctrlDevType': controlDevType,
                           'ctrlDevNumber': controlDevNumber, 'controlData': controlData, "isAdjust": isAdjust, "coeff": coeff}]
            if controlDevType == 0x02 or controlDevType == 0x04 or controlDevType == 0x0f:
                controlDevNumber, controlCmdLength, controlData, extraData = struct.unpack("=3B10s", data[12:])
                result = [{'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'ctrlDevNumber':controlDevNumber, 'controlData':controlData}]
            if controlDevType == 0x03:
                controlData, extraData = struct.unpack("=B12s", data[12:])
                result = [{'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'controlData':controlData}]
            if controlDevType == 0x50:
                # TODO 以后中央空调的控制指令将是2个字节 "=4Bh7s"
                protocol, ACAddr, controlCmd, controlCmdLength, controlData, extraData = struct.unpack("=4Bh7s", data[12:])
                result = [{'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'ctrlDevNumber':ACAddr,
                           'protocol':protocol, 'controlCmd':controlCmd, 'controlData':controlData}]
            Utils.logInfo(result)

            return result
        except:
            Utils.logException("unpack error in onHGCcontrolRequest")
        return None

    ##中总控查询命令
    def onHGCqueryRequest(self, data):

        try:
            macAddr, devTypeId, controlDevType, channel, returnType, buffer = struct.unpack("=10s4B11s", data)
            devAddr = self.getDevAddrByMac(macAddr)

            if(devAddr  == None):
                return None
            return [{'addr':devAddr, 'type':devTypeId, 'ctrlDevType':controlDevType, 'channel':channel, 'returnType':returnType}]
        except:
            Utils.logException("unpack error in onHGCqueryRequest")
        return None

    def onEnergyGasCmdResponse(self, data):

        # energy = struct.unpack("=i", data[0:4])
        addr, energy = struct.unpack("=Bi", data[0:5])
        addr = str(addr)

        value = {"energy": energy}
        deviceRTData = {"name": "energyGas", "addr":addr, "type": DEVTYPENAME_ENERGY_GAS, "value": value, "time": int(time.time())}
        devciesData = [deviceRTData]
        return devciesData   
            
    #macAddr:11111111
    def getDeviceStatusByAddr(self, devAddr):
        # return GlobalVars.g_allDeviceInfo.get(devAddr,None)
        return DBManagerDevice().getDeviceByDevId(devAddr)
        
    #一个设备的查询命令返回(状态上报解析)
    # 数据区    校验和    结束符
    # 数据区结构：Mac[0:9] Type buf[0:13]
    # [{"name":"device1","addr":"z-111111","type":"light","value":{"state":"1"}}]
    def onDeviceQryCmdResponse(self, data):
        try:
            macAddr, devTypeId, buffer = struct.unpack("=10sB14s", data)

            devAddr = self.getDevAddrByMac(macAddr)
            if(devAddr  == None):
                return None
            device = self.getDeviceStatusByAddr(devAddr)
            if(device is None):
                devPropObj = DBManagerDeviceProp().getDeviceByDevId(devAddr)
                if devPropObj == None:
                    Utils.logInfo( "do not config device with addr:%s, type:%s" % (devAddr, str(devTypeId)))
                    return None
                DBManagerDevice().initDevStatus(devPropObj)
                device = self.getDeviceStatusByAddr(devAddr)

            value = None
            
            if(devTypeId == DEVTYPEID_LIGHTAJUST):
                # 20170314，调光灯添加一个延时时间字段 lightingTime -- chenjc
                state,coeff,lightingTime = struct.unpack("=3B", buffer[0:3])
                value = {'state':state,'coeff':self.I2S(coeff), 'lightingTime': lightingTime}
            elif(devTypeId == DEVTYPEID_LIGHT1):
                state,coeff = struct.unpack("=2B", buffer[0:2])
                value = {'state':state}
            elif(devTypeId == DEVTYPEID_LIGHT2):
                state,coeff,state2,coeff2 = struct.unpack("=4B", buffer[0:4])
                value = {'state':state,'state2':state2}
            elif(devTypeId == DEVTYPEID_LIGHT3):
                state,coeff,state2,coeff2,state3,coeff3 = struct.unpack("=6B", buffer[0:6])
                value = {'state':state,'state2':state2,'state3':state3}
            elif(devTypeId == DEVTYPEID_LIGHT4):
                state,coeff,state2,coeff2,state3,coeff3,state4,coeff4 = struct.unpack("=8B", buffer[0:8])
                value = {'state':state,'state2':state2,'state3':state3,'state4':state4}
            elif(DEVTYPEID_SOCKET == devTypeId):
                state,i,u,p,wp = struct.unpack("=Bhhhi", buffer[0:11])
                value = {'state':state,'I':self.F2S(i/100.0,2),'U':self.F2S(u/10.0,1),'P':self.F2S(p/10.0,1),'energy':self.F2S(wp/1000.0,3)}
            elif(DEVTYPEID_INFRARED == devTypeId):
                cmdId,tempLHigh,tempLow,humiHigh,humiLow = struct.unpack("=5B",buffer[0:5])

                if(cmdId == 0x02): #查询温度
                    temp = tempLHigh * 256 + tempLow
                    humid = humiHigh * 256 + humiLow
                    value = {'temp':self.F2S(temp/10.0,0),'humid':self.F2S(humid/10.0,0)}
                else:
                    value = {"state": "", "mode": ""}
            elif(DEVTYPEID_SMOKE_SENSOR == devTypeId): # 烟雾传感器或甲醛传感器
                state,degree,almtime = struct.unpack("=Bhi", buffer[0:7])
                value = {'state': state, 'smoke': degree, 'time': self.time_t2String(almtime)}
                # state, degree, lvolt, powerPercent = struct.unpack("=Bh2B", buffer[0:5]) # TODO 烟感传感器需要加上低电压
                # value = {'state': state, 'smoke': degree, 'lvolt': lvolt, 'powerPercent': powerPercent}
            elif(DEVTYPEID_EXIST_SENSOR == devTypeId): # 存在传感器
                # state,set = struct.unpack("=2B", buffer[0:2])
                state, set, lvolt, powerPercent = struct.unpack("=4B", buffer[0:4]) # 存在传感器加上欠压告警和电量百分比 -- 20161006-chenjc
                value = {'state':state,'set':set, "lvolt": lvolt, "powerPercent": powerPercent}
            elif(DEVTYPEID_ENVIROMENT_SENSOR == devTypeId): # PM2.5和温湿度传感器 -- 20160825-chenjc:领导要求温度带1位小数
                state,pm25,temp,humid,pa,almtime = struct.unpack("=B4hi", buffer[0:13])
                value = {'state':state,'pm25':pm25,'pa':self.F2S(pa/1000.0,4),'temp':self.F2S(temp/10.0,1),'humid':self.F2S(humid/10.0,0),'time':self.time_t2String(almtime)}
            elif(DEVTYPEID_OXYGEN_CO2_SENSOR == devTypeId): # 氧气或CO2传感器
                o2,co2 = struct.unpack("=2h", buffer[0:4])
                value = {'o2':self.F2S(o2/10.0,1),'co2':co2}
            elif(DEVTYPEID_CH4CO_SENSOR == devTypeId):  # CH4和CO传感器
                # state,ch4deg,codeg,almtime = struct.unpack("=Bhhi", buffer[0:9])
                # value = {'state': state, 'ch4': ch4deg/10.0, 'co': codeg/10.0, 'time': self.time_t2String(almtime)}
                state, ch4Alarm, coAlarm, codeg, ch4deg, reservedData = struct.unpack("=3BHHB", buffer[0:8])
                value = {'state': state, 'ch4': self.F2S(ch4deg/10.0, 2), 'co': self.F2S(codeg/10.0, 2), 'ch4Alarm': ch4Alarm, 'coAlarm': coAlarm}
            elif(DEVTYPEID_WATER_SENSOR == devTypeId):  # 水侵传感器
                # state,almtime = struct.unpack("=Bi", buffer[0:5])
                # value = {'state':state,'time':self.time_t2String(almtime)}
                state, lvolt, powerPercent = struct.unpack("=3B", buffer[0:3])
                value = {'state': state, 'lvolt': lvolt, 'powerPercent': powerPercent}
            elif (devTypeId == DEVTYPEID_RAY_SENSOR):
                state, ray = struct.unpack("=BH", buffer[0:3])
                value = {'state': state, 'ray': ray}
                if ray > 60000:
                    Utils.logError("------PackParser------buffer=%s" % buffer)
            elif(devTypeId == DEVTYPEID_SOS_SENSOR):
                state = struct.unpack("=B", buffer[0:1])
                value = {'state':state[0]}
            elif(devTypeId == DEVTYPEID_FALL_SENSOR):
                state = struct.unpack("=B", buffer[0:1])
                value = {'state':state[0]}
            # elif(devTypeId == DEVTYPEID_SOV) :
            #     state = struct.unpack("=B", buffer[0:1])
            #     value = {'state':state[0]}
            elif(devTypeId == DEVTYPEID_SOV) :
                state = struct.unpack("=B", buffer[0:1])
                value = {'set': state[0]}
            elif(devTypeId == DEVTYPEID_CURTAIN):
                state = struct.unpack("=B", buffer[0:1])
                value = {'state':state[0]}
            elif(devTypeId == DEVTYPEID_PROJECTOR):
                state = struct.unpack("=B", buffer[0:1])
                value = {'state':state[0]}
            elif(devTypeId == DEVTYPEID_MODE_PANNEL):
                state,state2,state3,state4,state5,state6 = struct.unpack("=6B", buffer[0:6])
                value = {'state':state,'state2':state2,'state3':state3,'state4':state4,'state5':state5,'state6':state6}
            elif(devTypeId == DEVTYPEID_LOCK):
                # state,state2,state3,state4,state5,state6 = struct.unpack("=6B", buffer[0:6])
                # value = {'state':state,'state2':state2,'state3':state3,'state4':state4,'state5':state5,'state6':state6}
                value = UtilsLock().parseStatus(buffer)

            elif(devTypeId == DEVTYPEID_HGC):
                value = {'state': ""}
            elif(devTypeId == DEVTYPEID_GSM): # 门窗磁 20160921-14:48
                state, setState, lvolt, powerPercent, position = struct.unpack("=5B", buffer[0:5])
                if device is not None:
                    # 叶工要求门窗磁和幕帘上报的状态中的撤防、布防状态不要写入数据库，只要将app控制的撤防、布防状态写入数据库
                    if device.get("value") is not None: # 新添加的设备可能没有value值
                        setState = device.get("value").get("set", "1")
                # state:0-无报警,1-有报警；set:0-撤防，1-设防；lvolt:0-电压正常，1-电压异常；position:0-门窗关闭，1-门窗未关
                value = {"state": state, "set": setState, "lvolt": lvolt, "powerPercent": powerPercent, "position": position}
            elif(devTypeId == DEVTYPEID_CURTAIN_SENSOR): # 幕帘
                # state:0-无报警,1-有报警；set:0-撤防，1-设防；lvolt:0-电压正常，1-电压异常；
                state, setState, lvolt, powerPercent = struct.unpack("=4B", buffer[0:4])
                if device is not None:
                    # 叶工要求门窗磁和幕帘上报的状态中的撤防、布防状态不要写入数据库，只要将app控制的撤防、布防状态写入数据库
                    if device.get("value") is not None:  # 新添加的设备可能没有value值
                        setState = device.get("value").get("set", "1")
                value = {"state": state, "set": setState, "lvolt": lvolt, "powerPercent": powerPercent}
            elif devTypeId == DEVTYPEID_AUDIO:# 485背景音乐
                state, volume, playState, currNo = struct.unpack("=3Bh", buffer[0:5])
                value = {"state": state, "volume": volume, "playState": playState, "currNo": currNo}
            elif devTypeId == DEVTYPEID_AIR_SYSTEM:  # 新风系统(485协议接入)
                co2, voc, humidity, temperature, dust, state, setSpeed = struct.unpack("=5h2B", buffer[0:12])
                run_state, mode, fan_relay, dedusting = self.cal_air_system_state(state)
                value = {"co2": co2, "voc": self.F2S(voc/100.0, 2), "humidity": self.F2S(humidity/10.0, 1),
                         "temperature": self.cal_air_system_temp(temperature), "dust": dust, "state": state,
                         "runState": run_state, "mode": mode, "fanRelay": fan_relay, "dedusting": dedusting,
                         "setSpeed": setSpeed}
            elif devTypeId == DEVTYPEID_WUHENG_SYSTEM:  # 五恒系统
                addrIndex = struct.unpack("=B", buffer[0])[0]
                if addrIndex == 0:
                    # 总数据上报
                    pannel_num, mode, temp, humid, pm25, co2, voc = struct.unpack("=2B5h", buffer[1: -1])
                    value = {"addrIndex": addrIndex, "pannel_num": pannel_num, "mode": mode,
                             "pm25": self.F2S(pm25 / 100.0, 2), "co2": co2, "voc": self.F2S(voc/ 1000.0, 3)}
                else:
                    # 面板状态上报
                    status, set_status, set_temp, temp, humid, wind_srate, wind_rate = struct.unpack("=3B2h2B", buffer[1: 10])
                    value = {"addrIndex": addrIndex, "state": status, "set_status": set_status, "set_temp": set_temp,
                             "temp": self.F2S(temp / 100.0, 2), "humid": self.F2S(humid / 100.0, 2), "wind_srate": wind_srate,
                             "windRate": wind_rate}
                # addrIndex, state, mode, wind_rate, temp, humid, pm25, co2, voc = struct.unpack("=4B5h", buffer)
                # value = {"addrIndex": addrIndex, "state": state, "mode": mode, "windRate": wind_rate,
                #          "temp": self.F2S(temp/100.0, 2), "humid": self.F2S(humid/100.0, 2), "pm25": self.F2S(pm25/100.0, 2),
                #          "co2": co2, "voc": self.F2S(voc/1000.0, 3), 'roomname': '房间%s' % str(addrIndex)}
            elif devTypeId == DEVTYPEID_TABLE_WATER_FILTER:  # 台上净水器
                package_index = struct.unpack("=B", buffer[0: 1])  # 数据包index
                if package_index[0] == 2:
                    # 水位状态、诊断状态、在线状态、原水TDS、净水TDS、滤芯级别(1-4)
                    wLevel, dState, state, rawTDS, pureTDS, fLevel1, fLevel2, fLevel3, fLevel4 = struct.unpack("=3B2H4B", buffer[1: 12])
                    rawCisternLevel, rawCisternPos, purifying, dewatering, machineState = self.cal_tableWaterFilter_diagnosis(dState)
                    value = {"waterLevel": wLevel, "diagnosis": dState, "state": state, "rawTDS": rawTDS,
                             "pureTDS": pureTDS, "filterLevel1": fLevel1, "filterLevel2": fLevel2,
                             "filterLevel3": fLevel3, "filterLevel4": fLevel4, "rawCisternLevel": rawCisternLevel,
                             "rawCisternPos": rawCisternPos, "purifying": purifying, "dewatering": dewatering,
                             "machineState": machineState}
                elif package_index[0] == 3:
                    # 设定温度、实际温度、今日热水日用量、今日温水日用量m、昨日热水日用量、昨日温水日用量、总用水量(单位：ml)
                    setTemp, actualTemp, tHotWater, tWarmWater, yHotWater, yWarmWater, totalWater = struct.unpack("=2B5H", buffer[1: 13])
                    value = {"setTemp": setTemp, "actualTemp": actualTemp, "tHotWater": tHotWater, "tWarmWater": tWarmWater,
                             "yHotWater": yHotWater, "yWarmWater": yWarmWater, "totalWater": totalWater, "energy": str(totalWater)}
                else:
                    pass

            elif devTypeId == DEVTYPEID_AIR_FILTER:  # 空气净化器
                package_index = struct.unpack("=B", buffer[0: 1])
                if package_index[0] == 2:
                    # 工作模式、风速1-100,、温度、湿度、PM2.5含量、AQI值
                    mode, rate, tempMark, temp, humidity, pm25, aqi, screen = struct.unpack("=3B4HB", buffer[1: 13])
                    value = {"mode": mode, "rate": rate, "temp": self.cal_airFilter_temp(tempMark, temp),
                             "humidity": (int(round(humidity / 100.0))), "pm25": pm25, "AQI": aqi, "screen": screen}
                elif package_index[0] == 3:
                    # TVOC浓度、质量等级、月空气累计净化量、周空气累计净化量
                    tvoc, qualityLevel, monthAccPur, yearAccPur = struct.unpack("=2H2L", buffer[1: 13])
                    value = {"TVOC": tvoc, "qualityLevel": qualityLevel, "monthAccPur": monthAccPur,
                             "yearAccPur": yearAccPur}
                elif package_index[0] == 4:
                    # HEAP寿命统计(小时)、总空气累计净化量、周空气累计净化量(单位：ug)
                    hepa, totalAccPur, weekAccPur = struct.unpack("=H2L", buffer[1: 11])
                    value = {"HEPA": hepa, "totalAccPur": totalAccPur, "weekAccPur": weekAccPur, "energy": str(totalAccPur)}
                else:
                    pass

            elif devTypeId == DEVTYPEID_FLOOR_WATER_FILTER:  # 台下净水器
                rawTDS, pureTDS, filter1, filter2, filter3, filter4, lackWater, leakWater, rinse = struct.unpack(
                    "=2H7B", buffer[0: 11])
                value = {"rawTDS": rawTDS, "pureTDS": pureTDS, "filterLevel1": filter1, "filterLevel2": filter2,
                         "filterLevel3": filter3, "filterLevel4": filter4, "lackWater": lackWater,
                         "leakWater": leakWater,
                         "rinse": rinse}

            elif devTypeId == DEVTYPEID_LIGHTAJUST_PANNEL:  # 调光灯控制面板
                mode_index = struct.unpack("=B", buffer[0])[0]
                value = {"state": mode_index}
                if mode_index == 1:
                    # 节律模式，后面还有2个字节的占空比
                    warm_rate, cold_rate = struct.unpack("=2H", buffer[1:5])
                    value['coldRate'] = cold_rate
                    value['warmRate'] = warm_rate

            elif devTypeId == DEVTYPEID_ACOUSTO_OPTIC_ALARM:  # 声光报警器
                state = struct.unpack("=B", buffer[0:1])  # 0：没报警；1：有报警
                value = {'state': state[0]}
            elif devTypeId == DEVTYPEID_FLOOR_HEATING:  # 非3.5寸屏接入的地暖
                # state, setTemp, actTemp, heaterType = struct.unpack("=B2HB", buffer[0: 6])  # 原解析方式
                # 20180910--协议变更，增加电加热地暖几个状态值
                # 开关状态，加热类型(0-不显示，1-水暖，2-电暖)，设定温度、实际温度，发热体设定温度， 发热体实际温度，防冻功能(0-关1-开)，设定的防冻温度
                state, heaterType, setTemp, actTemp, setHeaterTemp, actHeaterTemp, antifreezing, setAntiTemp = struct.unpack("=2B2H4B", buffer[0: 10])
                value = {"state": state, "heaterType": heaterType, "setTemp": self.F2S(setTemp / 10.0, 1),
                         "actTemp": self.F2S(actTemp / 10.0, 1), "setHeaterTemp": setHeaterTemp,
                         "actHeaterTemp": actHeaterTemp, "antifreezing": antifreezing, "setAntiTemp": setAntiTemp}

            elif devTypeId == DEVTYPEID_LCD_SWITCH:  # LCD开关
                active_channel, active_scene, state, state2, state3, state4, scene_state = struct.unpack("=7B", buffer[0: 7])
                value = {
                    "activeChannel": active_channel,
                    "activeScene": active_scene,
                    "state": state,
                    "state2": state2,
                    "state3": state3,
                    "state4": state4,
                    "sceneState": scene_state
                }
            elif devTypeId == DEVTYPEID_AIR_SENSOR:  # 空气监测设备
                temp, humid, pm25, co2, voc, hcho = struct.unpack("=6H", buffer[0: 12])
                value = {"temp": self.F2S(temp / 100.0, 1), "humid": self.F2S(humid / 100.0, 1), "pm25": pm25,
                         "co2": co2, "voc": self.F2S(voc / 1000.0, 2), "hcho": self.F2S(hcho / 1000.0, 2)}

            if(value is None):
                return None
        except:
            Utils.logException("unpack error in onDeviceQryCmdResponse, %d"%(devTypeId))
            return None
        #组织设备数据
        # curTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S');
        # [{"name":"device1","addr":"z-111111","type":"light","value":{"state":"1"}}]
        deviceRTData = [{"name":device.get("name",""),"addr":devAddr,"type":device.get("type",""),"value":value,"time":int(time.time())}]

        return deviceRTData
    
    #CMDID_DEVICECONFIG_DEVICE response
    def onDeviceConfigCmdResponse(self,data):
        return None
    
    #CMDID_REGISTERDATA_DEVICE response
    def onRegisterDataCmdResponse(self,data):
        return None
    
    def onAnyCmdResponse(self, cmdId, data):
        # refreshConfigThread
        if(cmdId == CMDID_DEVICECONFIG_DEVICE): 
            return self.onDeviceConfigCmdResponse(data)

        # readDataThread
        if(cmdId == CMDID_REGISTERDATA_DEVICE):
            return self.onRegisterDataCmdResponse(data)
        if(cmdId == CMDID_QUERY_DEVICE or cmdId == CMDID_CONTROL_DEVICE):
            return self.onDeviceQryCmdResponse(data)
        if(cmdId == CMDID_SEARCH_DEVICE):
            return self.onBatchScanCmdResponse(data)  # 批量添加时设备上报的是 0x83，减去80是0x03
            # return self.onSearchDeviceCmdResponse(data)
        if(cmdId == CMDID_QUERY_ENERGY_ELEC):
            return self.onEnergyElecCmdResponse(data)
        if(cmdId == CMDID_QUERY_ENERGY_WATER):
            return self.onEnergyWaterCmdResponse(data)
        if(cmdId == CMDID_QUERY_ENERGY_GAS):
            return self.onEnergyGasCmdResponse(data)
        if(cmdId == CMDID_HGC_CONTROL):
            return self.onHGCcontrolRequest(data)
        if(cmdId == CMDID_HGC_QUERY):
            return self.onHGCqueryRequest(data)
        if cmdId == CMDID_RECV_CENTRAL_AIRCONDITION:
            return self.onCentalAirCmdResponse(data)
        if cmdId == CMDID_HGC_REPORT:
            return self.onHGCReportRequest(data)

        Utils.logError("recv a pack, cmdId:%d, do not support this command" % (cmdId))
        return None

    def I2S(self,iValue):
        return "%d" % (iValue)
    
    def F2S(self,fValue, dotNum):   #  F2S(energy[0]/100.0, 2)
        if(dotNum == 0):
            return "%.0f" % (fValue)
        
        if(dotNum == 1):
            return "%.1f" % (fValue)
        
        if(dotNum == 2):
            return "%.2f" % (fValue)
        
        if(dotNum == 3):
            return "%.3f" % (fValue)
        
        if(dotNum == 4):
            return "%10.4f" % (fValue)

    # 换算新风系统上报的温度
    def cal_air_system_temp(self, temp):
        real_temp = (temp - 500) / 10
        return self.F2S(real_temp, 0)

    # 计算新风系统各个状态值
    def cal_air_system_state(self, state):
        #１取除尘开关状态
        state = state & 15  # 二进制的15 是 1111
        run_state = state & 1  # 运行模式 0停止1运行
        mode = (state >> 1) & 1  # 运行模式 0自动1手动
        fan_relay = (state >> 2) & 1  # 风扇继电器 0关1开
        dedusting = (state >> 3) & 1  # 除尘开关 0关1开
        return (run_state, mode, fan_relay, dedusting)

    # 计算台上净水器诊断状态数值
    def cal_tableWaterFilter_diagnosis(self, diagnosis):
        rawCisternLevel = diagnosis & 1  # 原水箱水位：0-正常，1-缺水
        rawCisternPos = (diagnosis >> 1) & 1  # 原水箱位置： 0-正常，1-移开
        purifying = (diagnosis >> 2) & 1  # 净水状态：0-正常，1-制水
        dewatering = (diagnosis >> 3) & 1  # 排水状态：0-正常，1-缺水
        machineState = (diagnosis >> 4) & 1  # 整机状态：0-正常，1-故障
        return rawCisternLevel, rawCisternPos, purifying, dewatering, machineState

    # 计算空气净化器的温度值
    def cal_airFilter_temp(self, mark, temp):
        rtn_temp = ""
        temp2 = int(round(temp / 100.0))
        if mark:  # mark == 1，表示温度值是负数
            rtn_temp = "-%s" % str(temp2)
        else:
            rtn_temp = str(temp2)
        return rtn_temp


    '''
    char_checksum 按字节计算校验和。每个字节被翻译为无符号整数
    @param data: 字节串
    @param byteorder: 大/小端
    '''
    def calcCheckValue(self, data):
        length = len(data)
        checksum = 0
        for i in range(0, length):
            values = struct.unpack("B",data[i:i+1])            
            checksum += values[0]
            checksum &= 0xFF # 强制截断
         
        return checksum
    
    ##是否是水电煤的设备类型
    def isEnergyDataType(self, devTypeId):
        if devTypeId == DEVTYPEID_ENERGY_ELEC or devTypeId == DEVTYPEID_ENERGY_WATER or devTypeId == DEVTYPEID_ENERGY_GAS:
            return True
        else:
            return False

