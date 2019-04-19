#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from functools import wraps
#
# from gevent import monkey
#
# monkey.patch_all()
# from gevent.socket import SocketType
# from gevent.ssl import wrap_socket
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


class SocketClientControl(object):

    def __init__(self):
        self.sock = None
        self.destaddr = ('127.0.0.1', 6789)
        self.recvBuffer = ""
        # import Queue
        # self.que = Queue.Queue()

    def parseData(self, data):
        if(data == None):
            return

        self.recvBuffer = self.recvBuffer + data
        _hlen = 2
        if(len(data) < _hlen):
            return

        #解析出命令字
        tmp = data[0:_hlen]
        datalen = int(struct.unpack("=h", tmp)[0])
        if(len(data) < _hlen + datalen):
            Utils.logError("client pack allBufferLen=%d, but there's not a entire pack. bodyLen=%d!" % (len(data),datalen))
            return

        msg = data[_hlen: _hlen + datalen]

        self.recvBuffer = self.recvBuffer[_hlen + datalen:]
        return msg

    # def socket_readint(self, sock, size=4):
    #     size_format = {
    #         1: 'b',
    #         2: 'h',
    #         4: 'i',
    #         8: 'l'
    #     }
    #     sock_buffer = []
    #     while len(sock_buffer) < size:
    #         recv_ret = self.sock.recv(size - len(sock_buffer))
    #         sock_buffer += recv_ret
    #
    #     ret = struct.unpack('>' + size_format[size], ''.join(sock_buffer))[0]
    #     del sock_buffer
    #     return int(ret)
        
    def send2(self, message):
        # Utils.logInfo('client %s ready to send %s'%(hex(id(self.sock)), message))
        msg_len = len(message)
        if msg_len < GlobalVars.MAX_SOCKET_PACKET_SIZE:
            cmd_len = struct.pack('=h', msg_len)
            return self.sock.sendto(cmd_len + message, self.destaddr)
        else:
            ##big message. store in file first.
            md5 = hashlib.md5(message).hexdigest()
            cmd_file_name = '/ihome/etc/cmd_files/'+md5+str(time.time())

            file_object = open(cmd_file_name, 'w')
            file_object.write(message)
            file_object.close( )
            msg_len = len(cmd_file_name)
            cmd_len = struct.pack('=h', msg_len)
            return self.sock.sendto(cmd_len + cmd_file_name, self.destaddr)
        
    def recv(self):
        # msg_len = self.socket_readint(self.sock, 2)
        # buf,saddr = self.sock.recvfrom(msg_len)
        data, addr = self.sock.recvfrom(GlobalVars.MAX_SOCKET_PACKET_SIZE)
        response = self.parseData(data)
        if '/ihome/etc/cmd_files' in response:
            # big message in files.
            if os.path.exists(response):
                file_object = open(response)
                try:
                    data = file_object.read()
                    return data
                finally:
                    file_object.close()
                    os.remove(response)
        else:
            return response
        failResp = {}
        failResp['ret'] = ErrorCode.ERR_GENERAL
        return json.dumps(failResp)
        
    def stop(self):
        # self.que.put("stop now.")
        Utils.logInfo("disconnect from inner control server.")
        # self.sock.shutdown(2)
        self.sock.close()
        self.sock = None
        self.recvBuffer = ""

    def start(self):    
        # logger.info('host port %s %s', self.config['SEGLORD_HOST'], self.config['SEGLORD_PORT'])
        # logger.info('public key path %s', str(self.config['PUBLIC_KEY_PATH']))
        if(self.sock != None):
            self.stop()

        Utils.logDebug("connecting to inner control server.")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except:
            Utils.logException("Failed to connect to inner control server. publish RESTART config...")
            pub.sendMessage("restart_thread", threadname="config")
            time.sleep(3)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(3.2)
        # self.sock.connect()
        self.recvBuffer = ""
        
        Utils.logDebug("success connected to inner control server.")

        # self.que.get()