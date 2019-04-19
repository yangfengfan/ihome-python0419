#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from functools import wraps
#
# from gevent import monkey
#
# monkey.patch_all()
# from gevent.socket import SocketType
# from gevent.ssl import wrap_socket
import socket,ssl
import time
# import logging
import struct
import json
from config import Config
from models import *
from helper import *
from pubsub import pub
import sys
import os
sys.path.append(os.path.join('..'))
import GlobalVars
import Utils
import Queue
import threading
import sys
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)


MSG_ID_DEVICE_STATUS = 100
MSG_ID_DATA_REPORT = 200
MSG_ID_COMMAND = 300
MSG_ID_COMMAND_RSP = 301
MSG_ID_REQUEST = 400
MSG_ID_REQUEST_RSP = 401
MSG_ID_HANDSHAKE = MSG_ID_COMMAND_RSP
MSG_ID_HEARTBEAT = MSG_ID_COMMAND_RSP
MSG_ID_ACK     = 0

MSG_REQUEST_TYPE_FILE_DOWNLOAD = 0


# class EventWorker(Actor):
#     __handlers = {}
#
#     def __init__(self, handlers):
#         Actor.__init__(self)
#         self.__handlers = handlers
#
#     def receive(self, message):
#         # msg_len = self.sock.recv(2)
#         # # logger.debug('%d', ord(msg_len[0]))
#         # msg_len = struct.unpack('>h', msg_len)[0] if len(msg_len) == 2 else struct.unpack('>b', msg_len)[0]
#         # msg_type = self.sock.recv(4)
#         # msg_type = struct.unpack('>i', msg_type)[0]
#         # logger.debug('got message length %s, message type %s', msg_len, msg_type)
#         # msg = self.sock.recv(msg_len - 4)
#         # decoded_msg = self._decode_msg(msg_type, msg)
#         self.__handlers[message.__class__](message) if message.__class__ in self.__handlers else None

# 与云端建立长连接的socket客户端
class LordClient(threading.Thread):
    defaults_config = {
        'SEGLORD_HOST': '127.0.0.1',
        'SEGLORD_PORT': '3654',
        'PUBLIC_KEY_PATH': 'public.pem'
    }
    cmd_handler = {}

    def __init__(self, host, regFlag):
        threading.Thread.__init__(self)
        self.config = Config(self.defaults_config)
        self.connection = None
        self.protover = 1
        self.hostId = host
        self.registerHost = regFlag
        self.que = Queue.Queue()
        self.stopped = False
        self.channel=None
        # connection = SocketType()
        # self.connection = wrap_socket(connection)

    def buildEnergyDataPacket(self, transId, detailJsonStr):
        msg = Data()
        msg.msgId = transId
        msg.version = self.protover
        msg.hostId = self.hostId
        msg.dataType = "energy"
        msg.payload = detailJsonStr
        msgtuple = (MSG_ID_DATA_REPORT, msg.SerializeToString())
        return msgtuple

    def buildRTDataPacket(self, transId, dataType, op, detailJsonStr):
        msg = Status()
        msg.msgId = transId
        msg.version = self.protover
        msg.hostId = self.hostId
        newDetailDict = {}
        newDetailDict["op"] = op
        newDetailDict["detail"] = detailJsonStr
        detailJsonStr = json.dumps(newDetailDict)

        msg.dataType = dataType
        msg.payload = detailJsonStr
        msgtuple = (MSG_ID_DEVICE_STATUS, msg.SerializeToString())
        return msgtuple

    def buildCmdResponsePacket(self, transId, cmdId, success, response):
        msg = CommandRes()
        msg.msgId = transId
        msg.version = self.protover
        msg.hostId = self.hostId
        msg.cmdId = cmdId   #对应的command msgId
        msg.result = success
        if response != None:
            msg.payload = response
        msgtuple = (MSG_ID_COMMAND_RSP, msg.SerializeToString())
        return msgtuple
        
    def buildFileDownloadRequest(self, transId, fn, seq): 
        payloadDict = {}
        payloadDict["filename"] = fn
        payloadDict["sequence"] = str(seq)
        
        msg = Request()
        msg.msgId = transId
        msg.version = self.protover
        msg.hostId = self.hostId
        msg.type = MSG_REQUEST_TYPE_FILE_DOWNLOAD
        msg.payload = json.dumps(payloadDict)
        msgtuple = (MSG_ID_REQUEST, msg.SerializeToString())
        return msgtuple

    #{"type":"device", "addr":"z-11111111"}
    def buildRemoveRecordsPacket(self, transId, dataType, detailJsonStr):
        return self.buildRTDataPacket(transId, dataType, "remove", detailJsonStr)
    #
    # def buildMultiRTDataPacket(self, transId, dataType, detailsArr):
    #     msg = Status()
    #     msg.msgId = transId
    #     msg.version = self.protover
    #     msg.dataType = dataType
    #     msg.payload = detailsArr
    #     msgtuple = (MSG_ID_DEVICE_STATUS, msg.SerializeToString())
    #     self.sendMessage(msgtuple)
    #     return msgtuple
    #
    def sendAck(self, transId):
        msg = Ack()
        msg.msgId = transId
        msg.version = self.protover
        # msg.hostId = self.hostId
        return self.sendMessage(MSG_ID_ACK, msg.SerializeToString())
        
    def buildHandshakePacket(self, transId):
        msg = CommandRes()
        msg.msgId = transId
        msg.version = self.protover
        msg.hostId = self.hostId
        msg.cmdType = 8081
        msg.cmdId = "handshake"   # 对应的command msgId
        msg.result = "success"

        payloadDict = {}
        payloadDict["registerHost"] = self.registerHost
        msg.payload = json.dumps(payloadDict)

        msgtuple = (MSG_ID_HANDSHAKE, msg.SerializeToString())
        return msgtuple
        
    def sendHeartbeat(self, transId):
        msg = CommandRes()
        msg.msgId = transId
        msg.version = self.protover
        msg.hostId = self.hostId
        msg.cmdType = 8080
        msg.cmdId = "heartbeat"   # 对应的command msgId
        msg.result = "success"

        return self.sendMessage(MSG_ID_HEARTBEAT, msg.SerializeToString())

    def restart(self):
        # self.channel.stop()
        # self.channel = None
        # time.sleep(1)
        if self.connection != None:
            self.stopSSLSocket()

        self.startSSLSocket()

    def stopSSLSocket(self):
        Utils.logInfo("close socket %s."%(hex(id(self.connection))))
        try:
            self.connection.shutdown(2)
        except:
            pass

        try:
            self.connection.close()
        except:
            pass

        self.connection = None
        Utils.logInfo("helper socket closed success.")
        if self.channel != None:
            self.channel.update(None)
            self.channel.stop()
            self.channel.join()
            Utils.logInfo("helper thread exit success.")
        else:
            Utils.logInfo('######self.channel = None')

    # 建立与云端的长连接
    def startSSLSocket(self):
        Utils.logInfo("connecting to cloud server.")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.settimeout(2)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.connection = ssl.wrap_socket(s)
        self.connection.connect((self.config['SEGLORD_HOST'], self.config['SEGLORD_PORT']))# HostCloudClient线程启动时注入与云端连接地址及端口
        # self.receiver = EventWorker(self.cmd_handler)
        # self.channel.update(self.connection)
        self.channel = SocketChannel(self.connection)
        # self.receiver.start()
        self.channel.setDaemon(True)
        self.channel.start()
        Utils.logInfo("connected to cloud server:%s. socket %s."%(self.config['SEGLORD_HOST'], hex(id(self.connection))))

    # def handle(self, data_type):
    #     def decorator(f):
    #         self.cmd_handler[data_type] = f
    #
    #         @wraps(f)
    #         def wrapper(*args, **kwargs):
    #             return f(args, kwargs)
    #
    #         return wrapper
    #
    #     return decorator
    #

    def stop(self):
        Utils.logInfo("client thread is to stop...")
        self.stopped = True
        try:
            self.que.put((-1, "stopme"))
        except:
            pass

    def sendMessage(self, code, msgStr):
        try:
            self.que.put((code, msgStr))
        except:
            Utils.logError("Message Queue error.")

    def run(self):
        # logger.info('host port %s %s', self.config['SEGLORD_HOST'], self.config['SEGLORD_PORT'])
        # logger.info('public key path %s', str(self.config['PUBLIC_KEY_PATH']))
        try:
            self.startSSLSocket()
        except:
            Utils.logException('start SSL socket exception...')

        ##Loop...
        Utils.logInfo("client thread is running...")
        while not self.stopped:
            try:
                message = self.que.get()

                if self.connection == None:
                    Utils.logInfo('client is waiting socket to work...')
                    # time.sleep(1)
                    continue

                if message[0] == -1 and message[1] == "stopme":
                    Utils.logInfo('stopme. exit client SSL socket.')
                    break
                #if self.connection == None:
                #    time.sleep(2)
                #    continue
                msg_type = struct.pack('>i', message[0])
                # msg_len = struct.pack('>i', len(message[1]) + 4)
                # # Utils.logInfo('ready to send %s,len:%s,type:%s,%s'%(message[0], msg_len, msg_type, message[1]))
                msg_len = struct.pack('>i', len(message[1]) + 4)
                # Utils.logInfo('ready to send %s,len:%s,type:%s,%s'%(message[0], msg_len, msg_type, message[1]))

                # Utils.logError('------20190326------ready to send %s,len:%s,type:%s,%s' % (message[0], msg_len, msg_type, message[1]))
                add_str = message[1].find("addr")
                if add_str != -1:
                    addr = message[1][add_str + 8:add_str + 28]
                    # Utils.logError('------20190326 get addr------%s' % addr)
                    # Utils.logError('------20190327 GlobalVars.light_adjust_Pannel_flag=%s' % GlobalVars.light_adjust_Pannel_flag)
                    # Utils.logError('------20190327 GlobalVars.light_adjust_Pannel_flag.get(addr)=%s' % GlobalVars.light_adjust_Pannel_flag.get(addr))
                    state_str = message[1].find("state")
                    # Utils.logError('------20190326 get state_str------%s' % state_str)
                    state = message[1][state_str + 8:state_str + 9]
                    # Utils.logError('------20190326 get state------%s' % state)
                    if GlobalVars.light_adjust_Pannel_flag.get(addr, None) is False and int(state) == 1:
                        # Utils.logError('------20190326 break this message------')
                        continue

                # Utils.logError('--------------------------')
                data = msg_len + msg_type + message[1]
                datalen = len(data)
                retry = 0
                while self.connection != None:
                    try:
                        # Utils.logInfo('try to send data:%s'%(data))
                        sendCnt = self.connection.send(data)
                        if datalen == sendCnt:
                            retry = 0
                            break
                        else:
                            Utils.logInfo('ssl send wrong data length:%d != %d'%(sendCnt, datalen))
                            time.sleep(1)
                    except:
                        Utils.logException('send by SSL socket exception.')
                        time.sleep(1)
                        retry += 1
                        if retry % 3 == 0:
                            ##3次重试没有解决问题，则重启ssl收发线程...
                            try:
                                Utils.logInfo('reset ssl socket channel after 3 times re-try.')
                                # pub.sendMessage("reset_ssl_channel", arg1=None, arg2=None)
                                self.restart()
                            except:
                                pass
                            finally:
                                break
            except:
                Utils.logException('exception when sending ssl packet')
                time.sleep(1)
        
        # self.send_handshake()
        # joinall([self.receiver, self.reporter])
        Utils.logInfo("Disconnected from cloud server.")
        self.stopSSLSocket()
