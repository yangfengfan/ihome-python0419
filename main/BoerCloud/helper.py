
import struct
from abc import ABCMeta, abstractmethod
# from gevent import Greenlet
# from gevent.queue import Queue
# from gevent.socket import SocketType

import threading
from models import *
from pubsub import pub
import time
import sys
import os
sys.path.append(os.path.join('..'))
import Utils

__all__ = ['SocketChannel']


# class Actor(Greenlet):
#
#     __metaclass__ = ABCMeta
#
#     def __init__(self):
#         self.inbox = Queue()
#         Greenlet.__init__(self)
#
#     @abstractmethod
#     def receive(self, message):
#         pass
#
#     def _run(self):
#         self.running = True
#
#         while self.running:
#             message = self.inbox.get()
#             self.receive(message)
#

class SocketChannel(threading.Thread):
    def __init__(self, sock):
        # assert isinstance(receiver, Actor)
        # assert isinstance(sock, SocketType)

        # Greenlet.__init__(self)
        threading.Thread.__init__(self)
        self.sock = sock
        self.running = True
        # self.receiver = receiver

    def socket_readint(self, size=4):
        size_format = {
            1: 'b',
            2: 'h',
            4: 'i',
            8: 'l'
        }
        sock_buffer = []
        # Utils.logInfo('helper socket_readint')
        while len(sock_buffer) < size and self.running == True:
            # Utils.logInfo('helper loop2 %d , %d, sock:%s'%(len(sock_buffer), size, hex(id(self.sock))))
            recv_ret = self.sock.recv(size - len(sock_buffer))
            if recv_ret == None or len(recv_ret) == 0:
                # Utils.logInfo('helper loop2 wait 0.5sec and continue')
                time.sleep(0.5)
                continue
            sock_buffer += recv_ret

        # Utils.logInfo('helper socket_readint end')
        ret = struct.unpack('>' + size_format[size], ''.join(sock_buffer))[0]
        # Utils.logInfo('sock_buffer:%s'%(sock_buffer))
        del sock_buffer
        return int(ret)


    def decode_msg(self, msg_type, msg):
        if msg == "":
            return None
        if msg_type == 100:
            return Handshake()
        # elif msg_type == 200:
        #     return Heartbeat()
        # elif msg_type == 300:
        #     return Data().ParseFromString(msg)
        # elif msg_type == 400:
        #     return Status().ParseFromString(msg)
        elif msg_type == 300:
            cmd = Command()
            cmd.ParseFromString(msg)
            return cmd
        elif msg_type == 301:
            cmd_res = CommandRes()
            cmd_res.ParseFromString(msg)
            return cmd_res
        elif msg_type == 0:
            ack = Ack()
            ack.ParseFromString(msg)
            return ack
        elif msg_type == 401:
            reqResp = RequestResp()
            reqResp.ParseFromString(msg)
            return reqResp
        return msg


    def stop(self):
        self.running = False
        Utils.logInfo("stop helper thread.")

    def update(self, connection):
        if connection == None:
            self.sock = None
            Utils.logInfo("update helper thread socket None.")
        else:
            self.sock = connection
            Utils.logInfo("update helper thread socket %s."%(hex(id(self.sock))))

    def run(self):
        while self.running:
            try:
                #if self.sock == None:
                #    time.sleep(2)
                #    continue
                if self.sock == None:
                    Utils.logInfo('helper is waiting socket channel to work...')
                    time.sleep(1)
                    continue
                msg_len = self.socket_readint(4)
                if msg_len < 0 or msg_len > 30000:
                    continue

                msg_type = self.socket_readint(4)
                msg = ""
                if msg_len > 10000:
                    Utils.logDebug("msg_len > 10000 !!!!!!!!!!!!!!!!!!!!!!!!")
                    last_loop = msg_len % 10000
                    loop_times = count = msg_len / 10000
                    if last_loop > 0:
                        loop_times = msg_len / 10000 + 1

                    while loop_times > 0:
                        if loop_times > 1:
                            Utils.logDebug("loop_times > 1, %d" % loop_times)
                            msg += self.sock.recv(10000)
                        else:
                            if last_loop > 0:
                                Utils.logDebug("loop_times == 1, %d, last_loop = %d" % (loop_times, last_loop))
                                msg += self.sock.recv(last_loop - 4)
                            else:
                                Utils.logDebug("last_loop == 0")
                                msg += self.sock.recv(9996)  # 10000 - 4
                        loop_times -= 1

                else:
                    Utils.logDebug("msg_len < 10000 =========================")
                    msg = self.sock.recv(msg_len - 4)  # receive message from cloud server
                Utils.logDebug("msg is: %s" % str(msg))
                # msg = self.sock.recv(msg_len - 4)  # receive message from cloud server
                decoded_msg = self.decode_msg(msg_type, msg)
                # self.receiver.inbox.put(decoded_msg)
                pub.sendMessage("rx_ssl_packet", msg=decoded_msg, arg2=None)
            except:
                Utils.logException('helper thread exception...')
                time.sleep(1)
