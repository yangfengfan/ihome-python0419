#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import struct
import time
import platform
import struct
import uuid
import os
import DBUtils
import GlobalVars
import Utils
from DBManagerHostId import DBManagerHostId
import Utils
if (platform.system()!="Windows"):
    import fcntl

packHeaderTailLen = 14
HEAD_FALG = "SCCG"
TAIL_FALG = "GCCS"
CMDID_SCAN = 1
CMDID_SETNETWORK = 2
CMDID_CONFIGHOSTNAME = 3
CMDID_SCAN_RESPONSE = 0x81
CMDID_SETNETWORK_RESPONSE = 0x82
CMDID_CONFIGHOSTNAME_RESPONSE = 0x83


# def setHostId():
#     DBManagerHostId().setHostId(get_mac_address())
    
# def setHostName(hostName):
#     DBManagerHostId().setHostName(hostName)

def getHostName():
    return DBManagerHostId().getHostName()

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if (platform.system()=="Windows"):
        localIP = socket.gethostbyname(socket.gethostname())
        return localIP
    else:
        #import fcntl
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    
def getLocalNetInfo():
    hostId = Utils.get_mac_address()
    ip1 = get_ip_address("eth0")
    mac1 = Utils.get_mac_address()
    hostname = getHostName()
    return (hostId,ip1,mac1,hostname)
 
'''
setLocalNetInfo("SJP","0123456789","wpa")
ssid="SJP"
password="0123456789"
encryptType="wpa"
'''


def setLocalNetInfo(ssid, password, encryptType):
    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!set to wifi client mode !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print "set wireless info: ssid,", ssid, "password", password, "encryptType", encryptType
    confPath = "/ihome/etc/wlan0-config"
    os.system("echo SSID=%s > %s" % (ssid, confPath))
    os.system("echo ENCRPY_MODE=%s >> %s" % (encryptType, confPath))
    os.system("echo PASSWORD=%s >> %s" % (password, confPath))
    os.system("echo DHCP_AUTO=1 >> %s" % (confPath))
    print "!!!!!!!!!!!!begin setwifi client!!!!!!!!!!!!!!!!!"
    # os.system("/ihome/setwificlient.sh")
    print "!!!!!!!!!!!!end setwifi client!!!!!!!!!!!!!!!!!!!"

    return 0


def sendToRequest(sock, responseData, destAddress):
    sock.sendto(responseData, destAddress)    
    print "send ResponseLen:", len(responseData), "to", destAddress
    return 0


def processRequest(sock, reqBuffer, addr):
    if len(reqBuffer) < packHeaderTailLen:
        print "!reciveDataLen: %d < %d" %(len(reqBuffer), packHeaderTailLen)
        return sendToRequest(sock,reqBuffer,addr)
    
    result = 0
    bufferHead = reqBuffer[0:8]
    bufferTail = reqBuffer[-6:]
    bufferBody = reqBuffer[8:-6]
    headFlag, version, length = struct.unpack("4s2h", bufferHead)
    tailCRC,tailFlag = struct.unpack("h4s", bufferTail)
    
    if length != len(bufferBody):
        print "!lenght invalid, should %d, Act %d" % (length, len(bufferBody))
        result = -1
    if headFlag != HEAD_FALG or tailFlag != TAIL_FALG:
        print "!headerFlag:%s, tailFlag:%s" % (headFlag, tailFlag)
        result = -2
    
    cmdId = -1
    if result == 0: #
        cmdId = struct.unpack("h", bufferBody[0:2])[0]
        if(cmdId != CMDID_SCAN and cmdId != CMDID_SETNETWORK and cmdId != CMDID_CONFIGHOSTNAME):
            print "CommandId=%d,invalid" % (cmdId)
            result = -3

    # return cmdId=requestId+0x80
    cmIdResponse = cmdId + 0x80
    version=1
        
    if result != 0:  # failure before
        bufferBody = struct.pack("2h", cmIdResponse, result)
        crc=1
        bufferHead = struct.pack("4s2h",HEAD_FALG,version,len(bufferBody))
        bufferTail = struct.pack("h4s",crc,TAIL_FALG)
        return sendToRequest(sock,bufferHead + bufferBody + bufferTail,addr)
    else:
        if cmdId == CMDID_SCAN:
            hostId, ip1, mac1, hostname = getLocalNetInfo()
            ipNum = 1
            bufferBody = struct.pack("h12sh16s18s18s", cmIdResponse, hostId,ipNum,ip1,mac1,hostname)
            crc=1
            bufferHead = struct.pack("4s2h",HEAD_FALG,version,len(bufferBody))
            bufferTail = struct.pack("h4s",crc,TAIL_FALG)
            print "recv scan from %s,host=%s,ip=%s,mac=%s,name=%s" %(addr,hostId,ip1,mac1,hostname)
            return sendToRequest(sock,bufferHead + bufferBody + bufferTail,addr)
        elif cmdId == CMDID_SETNETWORK:  # (cmdId == CMDID_SETNETWORK)
            cmdId, ssid, password, encryptType = struct.unpack("h32s16s4s", bufferBody)
            ssid = ssid.strip('\0')
            password = password.strip('\0')
            encryptType = encryptType.strip('\0')
            print "recv set network from %s,ssid=%s,password=%s,encryptType=%s" %(addr,ssid,password,encryptType)
            
            bufferBody = struct.pack("2h", cmIdResponse, result)
            crc=1
            bufferHead = struct.pack("4s2h",HEAD_FALG,version,len(bufferBody))
            bufferTail = struct.pack("h4s",crc,TAIL_FALG)
            ret = sendToRequest(sock, bufferHead + bufferBody + bufferTail,addr)
            result = setLocalNetInfo(ssid,password,encryptType) # slow operation, so return first!
            return ret
        else:  # (cmdId == CMDID_CONFIGHOSTNAME)
            cmdId, hostname = struct.unpack("h18s", bufferBody)
            hostname = hostname.strip('\0')
            print "recv set hostname with %s" %(hostname)

            bufferBody = struct.pack("2h", cmIdResponse, result)
            crc=1
            bufferHead = struct.pack("4s2h", HEAD_FALG, version, len(bufferBody))
            bufferTail = struct.pack("h4s", crc, TAIL_FALG)
            ret = sendToRequest(sock, bufferHead + bufferBody + bufferTail,addr)
            DBManagerHostId().setHostName(hostname)  # slow operation, so return first!
            return ret


def startService():
    # 首先初始化
    hostId = DBManagerHostId().getHostId()
    if hostId == None:
        hostId = Utils.get_mac_address()
        hostProp = DBManagerHostId().initHostProp(hostId)
        if hostProp == None:
            Utils.logError("Failed to init Host property.")
            return
    print "start listen for request"
    localAddress = ('0.0.0.0', 9999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(localAddress)
    # begin=time.time()

    # sock.settimeout(2)
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            if not data:
                continue
            print "receivedDataLen:", len(data), "from", addr
            destAddress = (addr[0], 9998)
            processRequest(sock, data, destAddress)
        except:  # ignore timeout
            Utils.logException('ScanService exception.')

    sock.shutdown(2)
    sock.close()

if __name__ == '__main__':
    startService()
