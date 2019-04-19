### -*- coding: utf-8 -*-

from DBManagerHGC import *
from GlobalVars import *
import socket
import time
import struct
import json
import hashlib
import os
from pubsub import pub
import GlobalVars
import Utils
import ErrorCode
import thread

##
## 处理从app或云端过来的配置和控制命令
##
class UtilsCommandHandlerBosheng(object):
    ip = None
    mac = None
    sock = None
    __instant = None;
    __lock = threading.Lock();

    #singleton
    def __new__(self):
        Utils.logDebug("__new__")
        if(UtilsCommandHandlerBosheng.__instant==None):
            UtilsCommandHandlerBosheng.__lock.acquire()
            try:
                if(UtilsCommandHandlerBosheng.__instant==None):
                    Utils.logDebug("new UtilsCommandHandlerBosheng singleton instance.")
                    UtilsCommandHandlerBosheng.__instant = object.__new__(self)
            finally:
                UtilsCommandHandlerBosheng.__lock.release()
        return UtilsCommandHandlerBosheng.__instant


    def sendBroadcast(self, message):
        Utils.logDebug("connecting to Bosheng Host.")
        if(self.sock != None):
            self.sock.close()
            self.sock = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(1)
        # s.bind(('', 12345))
        try:
            self.sock.sendto(message, ('255.255.255.255', 10061))
            message, address = self.sock.recvfrom(1024)
            print "Got data from", address,":",message
            self.ip = address[0]
            protocolId, address, len, machineType, model, iphoneNumber, nameId, nameLen = struct.unpack('!8B', message[0:8])
            print '####nameLen=',nameLen
            macbufstart = 12+nameLen
            print '####macbufstart:',macbufstart
            self.mac = message[macbufstart: macbufstart+6]
            Utils.logHex('self.mac', self.mac)
            numbers = struct.unpack("!6B",self.mac)
            devAddr = "%02X%02X%02X%02X%02X%02X" % numbers
            print '#####mac:',devAddr
        except:
            Utils.logException('sdfsdfsd')
            self.ip = None
            self.mac = None
            self.sock.close()
            self.sock = None

    def send(self, message):

        if self.sock == None:
            self.sendBroadcast(self.searchHost(0))
        if self.sock == None:
            Utils.logError('can not connect to Bosheng Host')
            return

        # Utils.logDebug("connecting to Bosheng Host.")
        # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.settimeout(3)
        # sock.connect()

        # Utils.logDebug("success connected to Bosheng Host.")

        self.sock.sendto(message, (self.ip, 10061))
        print '####send success'
        return message

    def recv(self):
        data, addr = self.sock.recvfrom(GlobalVars.MAX_SOCKET_PACKET_SIZE)
        return data

    def recvMulti(self):
        message=[]
        while True:
            try:
                data, addr = self.sock.recvfrom(GlobalVars.MAX_SOCKET_PACKET_SIZE)
                message.append(data)
            except:
                pass
                break
        return message


    def configHandler(self, cmdType):
        Utils.logInfo("handle command: %s"%(cmdType))

        # if cmdType > GlobalVars.TYPE_CMD_BG_MUSIC_BOSHENG_START and cmdType < GlobalVars.TYPE_CMD_BG_MUSIC_BOSHENG_END:
        #     return

    # def init(self):
    #     self.cmdTypeTableInit()
    #     self.channelTableInit()
    #     self.commandTableInit()

    def activeMode(self, params):
        ##u'params': {1: u'on', '2':'off', '3':'on'}
        Utils.logInfo("Controlling the audio,sparam is %s" % str(params))
        valueArr = params.values()
        if len(valueArr) == 0:
            return
        v1 = valueArr[0]
        for tmp in valueArr:
            if v1 != tmp:
                v1 = None
        if v1 != None:
            ##全关 或 全开
            if v1 == '1':
                msg = self.allPowerOn()
            else:
                msg = self.allPowerOff()
            self.send(msg)
            # s.recv()
            # msg = self.setAllSourceCloud()
            # self.send(msg)
            # s.recv()
            time.sleep(5)
            thread.exit()
            return
        else:
            ##单独控制通道的开关
            state = params.get("state", None)
            channel_list = params.get("AudioChannel", None)
            if state == None or (state != '1' and state != '0'):
                Utils.logError("Invalid audio state param...")
                return
            if state == "1":
                if channel_list == None or len(channel_list) < 1:
                    Utils.logInfo("channel_list is empty or None, allPowerOn")
                    msg = self.allPowerOn()
                    self.send(msg)
                    # s.recv();
                    time.sleep(5)
                    thread.exit()
                else:
                    for channel in channel_list:
                        msg = self.switchon(int(channel))
                        self.send(msg)
                        # s.recv()
                    time.sleep(5)
                    thread.exit()
            else:
                if channel_list == None or len(channel_list) < 1:
                    Utils.logInfo("channel_list is empty or None, allPowerOff")
                    msg = self.allPowerOff()
                    self.send(msg)
                    # s.recv()
                    time.sleep(5)
                    thread.exit()
                else:
                    for channel in channel_list:
                        msg = self.switchoff(int(channel))
                        self.send(msg)
                        # s.recv()
                    time.sleep(5)
                    thread.exit()
            return
            # for channel in params.keys():
            #     state = params.get(channel, None)
            #     if state == None:
            #         continue
            #     if state != '1' and state != '0':
            #         ## invalid state.
            #         continue
            #     if state == '1':
            #         msg = self.switchon(int(channel))
            #     else:
            #         msg = self.switchoff(int(channel))
            #     self.send(msg)
            #     s.recv()

    def _generalPacket(self, protocolId, addr, w1, w2):
        xor = addr ^ w1 ^ w2
        return struct.pack('5B', protocolId, addr, w1, w2, xor)

    def powerOnTimer(self, channelId, hour, min):
        ret = self._generalPacket(0xa1, 16 + channelId, hour, min)
        Utils.logHex('powerOnTimer', ret)
        return ret

    def cancelPowerOnTimer(self, channelId, hour, min):
        ret = self._generalPacket(0xa1, 16 + channelId, 0x88, 0x88)
        Utils.logHex('cancelPowerOnTimer', ret)
        return ret

    ##查询定时开机时间
    def queryPowerOnTime(self, channelId):
        ret = self._generalPacket(0xa7, 16 + channelId, 0x00, 0x00)
        Utils.logHex('queryPowerOnTime', ret)
        return ret

    def powerOffTimer(self, channelId, hour, min):
        ret = self._generalPacket(0xa2, 16 + channelId, hour, min)
        Utils.logHex('powerOffTimer', ret)
        return ret

    def cancelPowerOffTimer(self, channelId, hour, min):
        ret = self._generalPacket(0xa2, 16 + channelId, 0x88, 0x88)
        Utils.logHex('cancelPowerOffTimer', ret)
        return ret

    ##查询定时开机时间
    def queryPowerOffTime(self, channelId):
        ret = self._generalPacket(0xa8, 16 + channelId, 0x00, 0x00)
        Utils.logHex('queryPowerOffTime', ret)
        return ret

    def allPowerOn(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x01, 0)
        Utils.logHex('allPowerOn data is: ', ret)
        return ret

    def allPowerOff(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0xc0, 0)
        Utils.logHex('allPowerOff data is: ', ret)
        return ret

    def switchon(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x7, 0)
        Utils.logHex('switchon data is: ', ret)
        return ret

    def switchoff(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x3, 0)
        Utils.logHex('switchoff data is: ', ret)
        return ret

    def searchHost(self, channelId):
        protocolId = 0xce
        addr = 16 + channelId
        xor = protocolId^addr
        ret = struct.pack('3B', protocolId, addr, xor)
        Utils.logHex('searchHost', ret)
        return ret

    def searchHostResponse(self, data):
        Utils.logHex('data:', data)

        ret = {}
        try:
            protocolId,addr,len,machineType,model,iphoneNum,id, idLen = struct.unpack("=8B", data[0:8])
            fmt = ''+str(idLen)+'s'
            buf = struct.unpack(fmt, data[8:8+idLen])
            ret['machineType'] = machineType
            ret['model'] = model
            ret['iphoneNum'] = iphoneNum
            if id == 0x01:
                ret['name'] = buf
            if id == 0x02:
                ret['no'] = buf
            if addr >= 16:
                ret['channel'] = addr - 16
        except:
            Utils.logException("searchHostResponse error")

        Utils.logInfo('searchHostResponse:%s'%(ret))
        return ret

    def setHostname(self, channelId, name):
        protocolId = 0xee
        addr = 16 + channelId
        length = len(name) + 4
        fmt = '2B'+str(len(name))+'s'
        tmp = struct.pack(fmt, addr, length-1, name)
        xor = 0
        for oneByte in tmp:
            b = struct.unpack("B",oneByte)
            xor = xor ^ b[0]
        fmt = 'B' + fmt + 'B'
        ret = struct.pack(fmt, protocolId, addr, length, name, xor)
        Utils.logHex('searchHost', ret)
        return ret

    ## Link Tests.
    def linkTest(self, channelId):
        protocolId = 0xcf
        addr = 16 + channelId
        xor = protocolId^addr
        ret = struct.pack('3B', protocolId, addr, xor)
        Utils.logHex('linkTest', ret)
        return ret

    def lowVoiceMinus(self, channelId):
        ret = self._generalPacket(0xaf, 16 + channelId, 0x02, 0)
        Utils.logHex('lowVoiceMinus', ret)
        return ret

    def lowVoicePlus(self, channelId):
        ret = self._generalPacket(0xaf, 16 + channelId, 0x01, 0)
        Utils.logHex('lowVoicePlus', ret)
        return ret

    def highVoiceMinus(self, channelId):
        ret = self._generalPacket(0xaf, 16 + channelId, 0x12, 0)
        Utils.logHex('HighVoiceMinus', ret)
        return ret

    def highVoicePlus(self, channelId):
        ret = self._generalPacket(0xaf, 16 + channelId, 0x11, 0)
        Utils.logHex('HighVoicePlus', ret)
        return ret

    def volumnMinus(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x08, 0)
        Utils.logHex('volumnMinus', ret)
        return ret

    def volumnPlus(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x01, 0)
        Utils.logHex('volumnPlus', ret)
        return ret

    def setVolumn(self, channelId, value):
        ret = self._generalPacket(0xc0, 16 + channelId, 0x00, value)
        Utils.logHex('setVolumn', ret)
        return ret

    def lastSong(self, channelId, src):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x05, src)
        Utils.logHex('lastSong', ret)
        return ret

    def nextSong(self, channelId, src):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x09, src)
        Utils.logHex('nextSong', ret)
        return ret

    def play(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x02, 0x00)
        Utils.logHex('play', ret)
        return ret

    def pause(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x02, 0x01)
        Utils.logHex('pause', ret)
        return ret

    def muse(self, channelId):
        ret = self._generalPacket(0xab, 16 + channelId, 0x01, 0)
        Utils.logHex('muse', ret)
        return ret

    def museoff(self, channelId):
        ret = self._generalPacket(0xab, 16 + channelId, 0x00, 0)
        Utils.logHex('museoff', ret)
        return ret

    def setSourceMp3(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x0b, 0)
        Utils.logHex('setSourceMp3', ret)
        return ret

    def setSourceFM1(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x0a, 0)
        Utils.logHex('setSourceFM1', ret)
        return ret

    def setSourceFM2(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x10, 0)
        Utils.logHex('setSourceFM2', ret)
        return ret

    def setSourceAUX(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x0c, 0)
        Utils.logHex('setSourceAUX', ret)
        return ret

    def setSourceDVD(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x06, 0)
        Utils.logHex('setSourceDVD', ret)
        return ret

    def setSourceIPod(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x11, 0)
        Utils.logHex('setSourceIPod', ret)
        return ret

    def setSourceNetRadio(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x12, 0)
        Utils.logHex('setSourceNetRadio', ret)
        return ret

    def setSourceCloud(self, channelId):
        ret = self._generalPacket(0xa3, 16 + channelId, 0x13, 0)
        Utils.logHex('setSourceCloud', ret)
        return ret

    def setAllSourceMp3(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x02)
        Utils.logHex('setAllSourceMp3', ret)
        return ret

    def setAllSourceFM1(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x01)
        Utils.logHex('setAllSourceFM1', ret)
        return ret

    def setAllSourceFM2(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x04)
        Utils.logHex('setAllSourceFM2', ret)
        return ret

    def setAllSourceAUX(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x03)
        Utils.logHex('setAllSourceAUX', ret)
        return ret

    def setAllSourceDVD(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x00)
        Utils.logHex('setAllSourceDVD', ret)
        return ret

    def setAllSourceIPod(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x05)
        Utils.logHex('setAllSourceIPod', ret)
        return ret

    def setAllSourceNetRadio(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x06)
        Utils.logHex('setAllSourceNetRadio', ret)
        return ret

    def setAllSourceCloud(self):
        channelId = 0
        ret = self._generalPacket(0x90, 16 + channelId, 0x02, 0x07)
        Utils.logHex('setAllSourceCloud', ret)
        return ret

    def setEqNormal(self, channelId):
        ret = self._generalPacket(0xa4, 16 + channelId, 0x00, 0)
        Utils.logHex('setEqNormal', ret)
        return ret

    def setEqPop(self, channelId):
        ret = self._generalPacket(0xa4, 16 + channelId, 0x00, 1)
        Utils.logHex('setEqPop', ret)
        return ret

    def setEqSoft(self, channelId):
        ret = self._generalPacket(0xa4, 16 + channelId, 0x00, 2)
        Utils.logHex('setEqSoft', ret)
        return ret

    def setEqClassical(self, channelId):
        ret = self._generalPacket(0xa4, 16 + channelId, 0x00, 3)
        Utils.logHex('setEqClassical', ret)
        return ret

    def setEqJazz(self, channelId):
        ret = self._generalPacket(0xa4, 16 + channelId, 0x00, 4)
        Utils.logHex('setEqJazz', ret)
        return ret

    def setEqRock(self, channelId):
        ret = self._generalPacket(0xa4, 16 + channelId, 0x00, 5)
        Utils.logHex('setEqRock', ret)
        return ret

    def singleSongOn(self, channelId):
        ret = self._generalPacket(0xEA, 16 + channelId, 0x01, 0x01)
        Utils.logHex('singleSongOn', ret)
        return ret

    def singleSongOff(self, channelId):
        ret = self._generalPacket(0xEA, 16 + channelId, 0x01, 0x00)
        Utils.logHex('singleSongOff', ret)
        return ret

    def queryChannelInfo(self, channelId):
        ret = self._generalPacket(0xcc, 16 + channelId, 0, 0)
        Utils.logHex('queryChannelInfo', ret)
        return ret

    def chooseMusicStart(self, channelId):
        ret = self._generalPacket(0xE5, 16 + channelId, 0, 0)
        Utils.logHex('chooseMusicStart', ret)
        return ret

    def chooseMusicLastPage(self, channelId):
        ret = self._generalPacket(0xE5, 16 + channelId, 0x1, 0)
        Utils.logHex('chooseMusicNextPageUp', ret)
        return ret

    def chooseMusicNextPage(self, channelId):
        ret = self._generalPacket(0xE5, 16 + channelId, 0x2, 0)
        Utils.logHex('chooseMusicNextPageUp', ret)
        return ret

    def chooseMusicEnd(self, channelId):
        ret = self._generalPacket(0xE5, 16 + channelId, 0x3, 0)
        Utils.logHex('chooseMusicEnd', ret)
        return ret

    def chooseMusicDirectoryStart(self, channelId, number):
        ret = self._generalPacket(0xE2, 16 + channelId, number, 0x1)
        Utils.logHex('chooseMusicDirectoryStart', ret)
        return ret

    def chooseMusicDirectoryLastPage(self, channelId):
        ret = self._generalPacket(0xED, 16 + channelId, 0x1, 0x0)
        Utils.logHex('chooseMusicDirectoryLastPage', ret)
        return ret

    def chooseMusicDirectoryNextPage(self, channelId):
        ret = self._generalPacket(0xED, 16 + channelId, 0x2, 0x0)
        Utils.logHex('chooseMusicDirectoryLastPage', ret)
        return ret

    def chooseMusicDirectoryEnd(self, channelId):
        ret = self._generalPacket(0xED, 16 + channelId, 0x3, 0x0)
        Utils.logHex('chooseMusicDirectoryLastPage', ret)
        return ret

    def chooseMusic(self, channelId, number):
        ret = self._generalPacket(0xE3, 16 + channelId, number, 0x01)
        Utils.logHex('chooseMusicDirectoryLastPage', ret)
        return ret


if __name__ == '__main__':
    s = UtilsCommandHandlerBosheng()
    # channel = 0
    # source = 0x13
    # s.allPowerOff()
    # s.allPowerOn()
    # s.cancelPowerOffTimer(channel, 8, 8)
    # s.cancelPowerOnTimer(channel, 8, 8)
    # s.highVoiceMinus(channel)
    # s.highVoicePlus(channel)
    # s.linkTest(channel)
    # s.lowVoiceMinus(channel)
    # s.lowVoicePlus(channel)
    # s.muse(channel)
    # s.museoff(channel)
    # s.nextSong(channel, source)
    # s.lastSong(channel, source)
    # s.pause(channel)
    # s.play(channel)
    # s.queryChannelInfo(channel)
    # s.queryPowerOffTime(channel)
    # s.queryPowerOnTime(channel)
    # s.searchHost(channel)
    # s.setEqClassical(channel)
    # s.setEqRock(channel)
    # s.setEqSoft(channel)
    # s.setEqPop(channel)
    # s.setEqNormal(channel)
    # s.setEqJazz(channel)
    # s.volumnMinus(channel)
    # s.volumnPlus(channel)

    # message = s.searchHost(0)
    # s.sendBroadcast(message)
    # s2 = UtilsCommandHandlerBosheng()
    # print '#####s2.ip mac=',s2.ip
    #
    print '######pause....'
    s.send(s.pause(0))
    time.sleep(10)
    print '######continue....'
    s.send(s.play(0))
    message = s.recv()
    Utils.logHex('sdfsdf', message)

    print '###queryChannnelInfo'
    s.send(s.queryChannelInfo(0))
    message = s.recvMulti()
    for m in message:
        Utils.logHex('multi', m)

    print '####choose music'
    s.chooseMusicStart(0)
    s.chooseMusicNextPage(0)
    s.chooseMusicLastPage(0)
    s.chooseMusicEnd(0)

    s.chooseMusicDirectoryStart(0, 0)
    s.chooseMusicDirectoryNextPage(0)
    s.chooseMusicDirectoryLastPage(0)
    s.chooseMusicDirectoryEnd(0)