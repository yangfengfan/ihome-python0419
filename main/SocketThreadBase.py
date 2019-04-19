# -*- coding: utf-8 -*-

import threading
import GlobalVars
import Utils
import socket
from ThreadBase import *
from pubsub import pub
import time

RECV_BUFFER_SIZE = 4096


class SocketThreadBase(ThreadBase):  
    def __init__(self, threadId, threadName):
        ThreadBase.__init__(self, threadId, threadName)
        self.sockTimeout = 3    # 设置socket的超时时间
        self.destAddress = ("127.0.0.1", 8899)    # 子类里修改
        self.sock = None
        
    def init(self):
        ThreadBase.init(self)
        self.connectToServer()  

    def onSockConnected(self):
        pass

    def onSockDisconnected(self):
        pass
        
    def connectToServer(self):
        Utils.logDebug("->connectToServer.")
        try:
            if(self.sock != None):
                self.disconnect()

            Utils.logInfo("connecting to DRIVER.")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.settimeout(self.sockTimeout)
            
            self.sock.connect(self.destAddress)
            self.onSockConnected()
            Utils.logInfo("connected to DRIVER successful")
        except:
            Utils.logException("connect to driver %s failed" %(self.destAddress[0]))
            self.sock = None
            
        return self.sock
        
    # None表示连接断开，>=0表示发送成功或不成功但连接是好的
    # 表示是否尝试重连
    def sendBuffer2(self, buffer, retryConn = True):
        result = None
        if(self.sock != None):
            try:
                result = self.sock.send(buffer)
            except:
                self.disconnect()
                result = None
                Utils.logException("send data to %s failed" %(self.destAddress[0]))

        if(result == None): #说明网络连接有问题
            #尝试连接一次
            retConn = self.connectToServer()
            if(retConn != None): # 连接成功则尝试重新发送
                try: # 尝试重发一次
                    result = self.sock.send(buffer)
                except:
                    self.disconnect()
                    self.onSockDisconnected()
                    Utils.logCritical("after connected, try once more, to send data to %s failed" % (self.destAddress[0]))
                    result = None

        return result
    
    def disconnect(self):
        try:
            self.sock.shutdown(2)
        except:
            pass
        try:
            self.sock.close()
        except:
            pass
        self.sock = None
        Utils.logInfo("disconnect from DRIVER")
        time.sleep(1)
        
    #返回值：None表示断开连接了，""表示未收到数据，收到值则len(buffer)>0
    #表示是否尝试重连
    def receiveBufferFrom(self):
        buffer = ""
        bConnected = True
        if(self.sock == None):
            bConnected = False
        else:
            try:
                buffer = self.sock.recv(RECV_BUFFER_SIZE)
                if(buffer == None):
                    Utils.logDebug("rx nothing from server")
                    return ""
                else:
                    return buffer
            except:
                self.disconnect()
                Utils.logException("recv from server failed: %s" %(self.destAddress[0]))
                bConnected = False
        
        if(bConnected == False): #说明网络连接有问题
            #尝试连接一次
            retConn = self.connectToServer()
            if(retConn != None): # 连接成功则尝试重新发送
                try: # 尝试重发一次
                    buffer = self.sock.recv(RECV_BUFFER_SIZE)
                    if(buffer == None):
                        Utils.logDebug("rx nothing from server")
                        return ""
                    else:
                        return buffer
                except:
                    Utils.logCritical("after connected, try once more, to send data to %s failed" % (self.destAddress[0]))
                    self.disconnect()
                    self.onSockDisconnected()
                    return ""
                    
        return buffer