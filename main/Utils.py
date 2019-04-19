#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import platform
import GlobalVars
if (platform.system()!="Windows"):
    import fcntl

from pubsub import pub
import datetime
import logging
import struct
import traceback
from logging.handlers import RotatingFileHandler
import socket

from json import dumps
# from Crypto.Cipher import AES
# import os
# import base64
#
# BS = AES.block_size
# pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
# unpad = lambda s : s[0:-ord(s[-1])]
#
# #key = os.urandom(16) # the length can be (16, 24, 32)
# #text = 'to be encrypted'
# key = '12345678901234567890123456789012' # the length can be (16, 24, 32)
# #text = '1234567890123456'
# #text = '1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890'
# #text = '中文坎坎坷坷吞吞吐吐yy语音男男女女'
#
# cipher = AES.new(key)
#
# def encryptAes(string):
#     #encrypted = cipher.encrypt(pad(text)).encode('hex')
#     encrypt = cipher.encrypt(pad(string))
#     print encrypt  # will be something like 'f456a6b0e54e35f2711a9fa078a76d16'
#     result = base64.b64encode(encrypt)
#     print result  # will be something like 'f456a6b0e54e35f2711a9fa078a76d16'
#
#
# def decryptAes(string):
#     #decrypted = unpad(cipher.decrypt(encrypted.decode('hex')))
#     decoded = base64.b64decode(string)
#     print decoded  # will be 'to be encrypted'
#     decrypted = unpad(cipher.decrypt(decoded))
#     print decrypted  # will be 'to be encrypted'


def getChannelFrom(stateKey):
    if stateKey == 'state':
        return 1
    if stateKey == 'state2':
        return 2
    if stateKey == 'state3':
        return 3
    if stateKey == 'state4':
        return 4
    if stateKey == 'state5':
        return 5
    if stateKey == 'state6':
        return 6
    return -1


def getFirmwareVersion():
    ver = 0
    try:
        tmp = GlobalVars.FIRMWARE_VER_FILE
        if os.path.exists(tmp):
            fh = open(tmp)
            ver = fh.readline()
            ver.replace("\r","")
            ver.replace("\n","")
            fh.flush()
            fh.close()
    except:
        logError('err')
    finally:
        print "firmware version:",str(ver)
        return int(ver)


# 读取网关pand_id（平时所说的网关通道）
def getPandId():
    pand_id, channel_no,zbsVer, zbhVer = (0, 0, 0, 0)
    pand_id_dict = {"pand_id": pand_id, "channel_no": channel_no, "zbsVer": zbsVer, "zbhVer": zbhVer}
    try:
        tmp = GlobalVars.PAND_ID_FILE
        if os.path.exists(tmp):
            content = ""
            with open(tmp, "rb") as fh:
                content = fh.readline()
                content = content.replace("\r", "")
                content = content.replace("\n", "")
            if len(content) > 0:
                info_list = content.split("/")
                pand_id = info_list[0]
                channel_no = info_list[1]
                try:
                    zbs_Ver = info_list[2]
                    zbh_Ver = info_list[3]
                    zbsVer = "{}.{}".format(zbs_Ver[0: 1], zbs_Ver[1:])
                    zbhVer = "{}.{}".format(zbh_Ver[0: 1], zbs_Ver[1:])
                except IndexError:
                    logInfo("No zigbee software version and hardware version found...")
        pand_id_dict = {"pand_id": pand_id, "channel_no": channel_no, "zbsVer": zbsVer, "zbhVer": zbhVer}
    except:
        logError("Get pand id failed...")
    finally:
        logInfo("Host pand id: %s, channel no: %s" % (pand_id, channel_no))
        return pand_id_dict


def getAreaInfo():
    try:
        gwid_file = GlobalVars.AREA_CODE_FILE
        countriyCode, cityCode, languageCode, landDeveloperCode, neighbourhood = ('', '', '', '', '')
        code_info = None
        if os.path.exists(gwid_file):
            with open(gwid_file, "rb") as fh:
                content = fh.readline()
                content = content.replace("\r", "")
                content = content.replace("\n", "")
            if len(content) > 0:
                info_list = content.split("/")
                countriyCode, cityCode, languageCode, landDeveloperCode, neighbourhood = tuple(info_list)
            code_info = {"contryCode": countriyCode, "cityCode": cityCode, "languageCode": languageCode,
                         "landDeveloperCode": landDeveloperCode, "neighbourhood": neighbourhood}
            return code_info
        else:
            return None
    except:
        logError("Get area info failed...")


def getSoftwareVersion():
    print "software version:",str(GlobalVars.HOST_SOFT_VER)
    return GlobalVars.HOST_SOFT_VER

def get_mac_address():
    macAddr = "-no-hostid-"

    if (platform.system()=="Windows"):
        mac = os.popen('getmac /NH')
        macaddrs = mac.read().split('\n')
        maclist = []
        for a in macaddrs:
            n = a.find('-')
            if n != -1:
                macAddr = a.split()[0]
                macAddr = macAddr.replace('-','')
                macAddr = macAddr.replace('\n','')
                maclist.append(macAddr)
                break
    else:
        tmpFilePath = "../etc/hostid_tmp" #/ihome/etc/hostid
        macAddr = ""
        try:
            # 判断是否已经存在"../etc"目录，已经存在则不再创建，
            # 避免Linux报出mkdir: can't create directory '../etc': File exists -- modified by chenjianchao 20151225
            if not os.path.exists("../etc"):
                os.system("mkdir ../etc")
            #os.system("ifconfig en0 | grep ether | awk '{print $2}' > %s" % (tmpFilePath))
            os.system("ifconfig eth0 | grep HWaddr | awk '{print $5}' > %s" % (tmpFilePath))
            fh = open(tmpFilePath)
            for  line in  fh.readlines():
                macAddr = line
                break
            fh.flush()
            fh.close()
            logDebug("get_mac_address of wlan0 = %s" % (macAddr))
        except:
            logException("open file %s failed" % (tmpFilePath))

        try:
            if(len(macAddr) == 0):
                os.system("ifconfig eth0 | grep HWaddr | awk '{print $5}' > %s" % (tmpFilePath))
                fh = open(tmpFilePath)
                for  line in  fh.readlines():
                    macAddr = line
                    break
                fh.flush()
                fh.close()
                logDebug("get_mac_address of eth0 = %s" % (macAddr))
        except:
            logException("open file %s failed" % (tmpFilePath))
        try:
            if os.path.isfile(tmpFilePath):
                os.remove(tmpFilePath)
        except:
            pass
    macAddr = macAddr.replace(':','')
    macAddr = macAddr.replace('\n','')
    macAddr = macAddr.upper()
    return macAddr

def ip2mac(ip):
    tmpFilePath = "/ihome/etc/ip2mac_tmp"
    arp = "arp " + ip + " | awk '{print $4}' > %s"
    os.system(arp)
    macAddr = None
    fh = open(tmpFilePath)
    for line in fh.readlines():
        macAddr = line
        break
    fh.flush()
    fh.close()
    return macAddr

def unlockDatabase():
    logInfo('database is locked, let me try...')
    # try to export the db and import it as followed when locked
    # sqlite3 rt.db ".dump" > rt.sql
    # cat rt.sql | sqlite3 rt.db
    # 或者试试：echo ".dump" | sqlite old.db | sqlite new.db
    src = '/ihome/etc/rt.db'
    target = '/ihome/etc/rt.db.bak'  # '/ihome/rt.db'
    try:
        if os.path.exists(target):
            os.remove(target)
        # import shutil
        # shutil.move(src, target)    #将rt.db移动到另一个目录
        # shutil.move(target, src)    #再移回原处
        import commands
        cmd_1 = "mv %s %s" % (src, target)
        cmd_2 = "mv %s %s" % (target, src)
        cmd_3 = 'sqlite3 /ihome/etc/rt.db "PRAGMA journal_mode=WAL;"'
        status, output = commands.getstatusoutput(cmd_1)
        logInfo("Rename rt.db to rt.db.bak, status: %s, output: %s" % (str(status), str(output)))
        status, output = commands.getstatusoutput(cmd_2)
        logInfo("Rename rt.db.bak back to rt.db, status: %s, output: %s" % (str(status), str(output)))
        status, output = commands.getstatusoutput(cmd_3)
        logInfo("Set sqlite3 journal_mode to WAL, status: %s, output: %s" % (str(status), str(output)))
        logInfo('done, keep watching on...database is locked.')
    except:
        pass


# 计算扫描设备是的软件和硬件版本号
def calculateVersion(verNo):
    fraction = verNo & 15  # 15的二进制是1111，取后四位是小数点后面的值
    integer = (verNo >> 4) & 15
    return "%d.%d" % (integer, fraction)


loggername = "BoerHost-"+str(GlobalVars.HOST_SOFT_VER)
logger = logging.getLogger(loggername)


# ===================================================================================
# Support function to get the local IP address
# ===================================================================================
def getMyIpAddress():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 0))
    outgoing_ip_address = s.getsockname()[0]
    s.close()
    return outgoing_ip_address


def loggerInit():
    myLogLevel = logging.ERROR
    logger.setLevel(myLogLevel)
    # create file handler which logs even debug messages
    fh = logging.FileHandler("../etc/host2M.log")
    fh.setLevel(myLogLevel)

    # create rotating file handler with a higher log level
    rotatingHandler = RotatingFileHandler("../etc/host2M.log",
            maxBytes=40*1024*1024,  #10M
            backupCount=10,
           )
    rotatingHandler.setLevel(myLogLevel)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(myLogLevel)
    # create formatter and add it to the handlers
    chformatter = logging.Formatter("%(asctime)s - %(message)s")
    ch.setFormatter(chformatter)
    fhformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(fhformatter)
    rotatingHandler.setFormatter(fhformatter)
    # add the handlers to logger
    logger.addHandler(ch)
    # logger.addHandler(fh)
    logger.addHandler(rotatingHandler)
loggerInit()

'''
日志打印函数
'''
def logDebug(msg):
    logger.debug(msg)

def logInfo(msg):
    logger.info(msg)

def logWarn(msg):
    logger.warn("!!!!WARNING!!!!WARNING %s"%(msg))

def logError(msg):
    # logger.error("!!!!ERROR!!!!!!!ERROR!!!!!!!ERROR!!!!!! %s, traceback:%s"%(msg, traceback.format_exc()))
    try:
        tracestr = traceback.format_exc()
        logger.error("!!!!ERROR!!!!!!!ERROR!!!!!!!ERROR!!!!!! %s, traceback:%s"%(msg, tracestr))
        # pub.sendMessage('publish_host_exception', trace=tracestr, arg2 = None)
    finally:
        pass

def logSuperDebug(msg):
    # !!!DO REMEBER!!! super debug,do not use this method,it can be used in only one situation: debug.
    try:
        logger.error("=====>>>>> superDebug: %s " % msg)
    finally:
        pass

def logCritical(msg):
    # logger.critical("!!!!---CRITICAL---!!!!!!!!!!---CRITICAL %s, traceback:%s"%(msg, traceback.format_exc()))
    try:
        tracestr = traceback.format_exc()
        logger.error("!!!!---CRITICAL---!!!!!!!!!!---CRITICAL %s, traceback:%s"%(msg, tracestr))
        # pub.sendMessage('publish_host_exception', trace=tracestr, arg2 = None)
    finally:
        pass

def logHex(tip,buffer):
    if buffer == None:
        return
    curTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S');
    disp = "%s:%s,bufLen:%d,hex:" % (curTime,tip,len(buffer))
    for oneByte in buffer:
        oneStr = struct.unpack("B",oneByte)
        disp = disp + " %02X" % (oneStr)
    logger.info(disp)

def logSuperHex(tip,buffer):
    # !!!DO REMEBER!!! super hex,do not use this method,it can be used in only one situation: debug.
    if buffer == None:
        return
    disp = "===>>>SUPER HEX:\n%s,bufLen:%d,hex:" % (tip,len(buffer))
    for oneByte in buffer:
        oneStr = struct.unpack("B",oneByte)
        disp = disp + " %02X" % (oneStr)
    logger.error(disp)

def logUncaughtException(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught exception@@@", exc_info=(exc_type, exc_value, exc_traceback))

def logException(msg):
    try:
        tracestr = traceback.format_exc()
        logger.error("!!!!EXCEPTION!!!!!! %s, traceback:%s"%(msg, tracestr))
        # pub.sendMessage('publish_host_exception', trace=tracestr, arg2 = None)
    finally:
        pass

import gc
#import objgraph
def disableGC():
    gc.disable()

def enableGC():
    # logInfo('enableGC')
    # Enable automatic garbage collection.
    gc.enable()
    gc.collect()
    # Set the garbage collection debugging flags.
    # gc.set_debug(gc.DEBUG_LEAK | gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_INSTANCES | gc.DEBUG_OBJECTS)
    # gc.set_debug(gc.DEBUG_LEAK)
    # return gc

# def checkGC(name):
#     logInfo('begin collect...%s'%name)
#     _unreachable = gc.collect()
#     if _unreachable > 0:
#         logError('unreachable object num:%d' % _unreachable)
#     _num = len(gc.garbage)
#     if _num > 0:
#         logError('garbage object num:%d' % _num)
#     # objgraph.show_growth()


# def BoerFormatTimeNow():
#     return hex(time.strftime("%y%m%d%H%M%S", time.localtime()))
