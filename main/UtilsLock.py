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

# 处理从app或云端过来的配置和控制命令


class UtilsLock():
    def controlBuffer(self, value):
        state = int(value.get("state", None))
        set = value.get('set', None)
        msg = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]   # msg[11]
        cmdType = 0x01
        bodyBuffer = []
        bodyBuffer.append(cmdType)
        if state != None:
            msg[0] = int(state)
            msg[10] = msg[10] | 0x1
        if set != None:
            msg[1] = int(set)
            msg[10] = msg[10] | 0x2
        for item in msg:
            bodyBuffer.append(item)

        while len(bodyBuffer) < 14:
            bodyBuffer.append(0)

        return struct.pack("=14B",
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
                           bodyBuffer[13]
                           )

    def parseStatus(self, buffer):
        #value = {'state':state,'state2':state2,'state3':state3,'state4':state4,'state5':state5,'state6':state6}
        value = {}
        cmdType = struct.unpack("=B", buffer[2:3])
        # 控制命令	0X01
        # 状态信息	0X02
        # 错误ACK	0X03
        # 查询状态	0X04
        # 确认ACK	0X05
        # 无效ACK	0X06
        # 设备报警	0X07
        # 主动上报信息	0X08
        value['alarming'] = 0
        value['state'] = 0
        AA, BB, CC, DD = struct.unpack("=4B", buffer[3:7])
        Utils.logInfo("===>AA: %s" % AA)
        Utils.logInfo("===>BB: %s" % BB)
        Utils.logInfo("===>CC: %s" % CC)
        Utils.logInfo("===>DD: %s" % DD)

        if cmdType[0] == 0x2 and AA == 0 and BB == 0 and CC == 0 and DD == 5:
            value['set'] = 1
            value['state'] = 1
            value['msg'] = ""
            return value

        parsed_aa, parsed_bb, parsed_cc, parsed_dd = UtilsLock.parse_data(AA, BB, CC, DD)
        msg_1, msg_2 = UtilsLock.parse_info(cmdType[0], parsed_aa, parsed_bb, parsed_cc, parsed_dd)

        if msg_1 != "":
            value['state'] = 1
        if msg_2 != "":
            value['alarming'] = 1

        # 20161026--chenjc：推送消息发现门锁的电量不足消息中会出现空白逗号，此处处理一下
        if msg_1 and msg_2:
            value['msg'] = msg_1 + ", " + msg_2
        else:
            msg_l = [msg for msg in [msg_1, msg_2] if msg is not None and len(msg)>0]
            if len(msg_1) > 0:
                value['msg'] = msg_l[0]
            else:
                value['msg'] = ""
        Utils.logInfo("===>parsed value: %s" % value)
        return value

    @staticmethod
    def parse_data(AA, BB, CC, DD):

        parsed_AA = 0
        parsed_BB = 0
        parsed_CC = 0
        parsed_DD = 0

        if AA != 0:
            parsed_AA = AA & 0xff
        if BB != 0:
            parsed_BB = BB & 0xff
        if CC != 0:
            parsed_CC = CC & 0xff
        if DD != 0:
            parsed_DD = DD & 0xff

        return parsed_AA, parsed_BB, parsed_CC, parsed_DD

    @staticmethod
    def parse_info(cmdType, parsed_AA, parsed_BB, parsed_CC, parsed_DD):
        message_1 = ""
        message_2 = ""
        parsed_BB += 1

        if cmdType == 0x2 or cmdType == 0x8:
            if parsed_AA == 1:
                # message_1 = "指纹1开的门"
                message_1 = "卡%d开的门" % parsed_BB
            if parsed_AA == 2:
                # message_1 = "指纹2开的门"
                message_1 = "指纹%d开的门" % parsed_BB
            if parsed_AA == 3:
                # message_1 = "指纹3开的门"
                message_1 = "密码%d开的门" % parsed_BB
            if parsed_AA == 4:
                # message_1 = "指纹4开的门"
                message_1 = "远程开门"
            # if parsed_AA == 5:
            #     message_1 = "指纹5开的门"
            # if parsed_AA == 6:
            #     message_1 = "指纹6开的门"
            # if parsed_AA == 7:
            #     message_1 = "指纹7开的门"
            # if parsed_AA == 8:
            #     message_1 = "指纹8开的门"
            # if parsed_AA == 9:
            #     message_1 = "其他指纹开的门"

            # if parsed_BB == 1:
            #     message_1 = "卡1开的门"
            # if parsed_BB == 2:
            #     message_1 = "卡2开的门"
            # if parsed_BB == 3:
            #     message_1 = "卡3开的门"
            # if parsed_BB == 4:
            #     message_1 = "卡4开的门"
            # if parsed_BB == 5:
            #     message_1 = "卡5开的门"
            # if parsed_BB == 6:
            #     message_1 = "卡6开的门"
            # if parsed_BB == 7:
            #     message_1 = "卡7开的门"
            # if parsed_BB == 8:
            #     message_1 = "卡8开的门"
            # if parsed_BB == 9:
            #     message_1 = "其他卡开的门"
            #
            # if parsed_BB == 16:
            #     message_1 = "密码1开的门"
            # if parsed_BB == 32:
            #     message_1 = "密码2开的门"
            # if parsed_BB == 48:
            #     message_1 = "密码3开的门"
            # if parsed_BB == 64:
            #     message_1 = "密码4开的门"
            # if parsed_BB == 80:
            #     message_1 = "密码5开的门"
            # if parsed_BB == 96:
            #     message_1 = "密码6开的门"
            # if parsed_BB == 112:
            #     message_1 = "密码7开的门"
            # if parsed_BB == 128:
            #     message_1 = "密码8开的门"
            # if parsed_BB == 144:
            #     message_1 = "其他密码开的门"

            if parsed_CC == 1:
                message_2 = "暴力破坏"
            if parsed_CC == 2:
                message_2 = "恶意破解"
            if parsed_CC == 8:
                message_2 = "布防请求"

            if parsed_DD == 1:
                message_2 = "门处于打开状态"
            if parsed_DD == 2:
                message_2 = "门处于长开状态"
            if parsed_DD == 8:
                message_2 = "门是从外部打开的"
            if parsed_DD == 16:
                message_2 = "有报警"
            if parsed_DD == 32:
                message_2 = "门未锁好"
            if parsed_DD == 64:
                message_2 = "胁迫开门"
            if parsed_DD == 128:
                message_2 = "电量不足"

        if cmdType == 0x7:
            if parsed_AA == 1:
                message_1 = "卡%d开的门" % parsed_BB
            if parsed_AA == 2:
                message_1 = "指纹%d开的门" % parsed_BB
            if parsed_AA == 3:
                message_1 = "密码%d开的门" % parsed_BB
            if parsed_AA == 4:
                message_1 = "远程开门"
            # if parsed_AA == 1:
            #     message_1 = "指纹1开的门"
            # if parsed_AA == 2:
            #     message_1 = "指纹2开的门"
            # if parsed_AA == 4:
            #     message_1 = "指纹3开的门"
            # if parsed_AA == 8:
            #     message_1 = "指纹4开的门"
            # if parsed_AA == 16:
            #     message_1 = "指纹5开的门"
            # if parsed_AA == 32:
            #     message_1 = "指纹6开的门"
            # if parsed_AA == 64:
            #     message_1 = "指纹7开的门"
            # if parsed_AA == 128:
            #     message_1 = "指纹8开的门"

            # if parsed_BB == 1:
            #     message_1 = "密码1开的门"
            # if parsed_BB == 2:
            #     message_1 = "密码2开的门"
            # if parsed_BB == 4:
            #     message_1 = "密码3开的门"
            # if parsed_BB == 8:
            #     message_1 = "密码4开的门"
            # if parsed_BB == 16:
            #     message_1 = "密码5开的门"
            # if parsed_BB == 32:
            #     message_1 = "密码6开的门"
            # if parsed_BB == 64:
            #     message_1 = "密码7开的门"
            # if parsed_BB == 128:
            #     message_1 = "密码8开的门"

            if parsed_CC == 1:
                message_2 = "卡1开的门"
            if parsed_CC == 2:
                message_2 = "卡2开的门"
            if parsed_CC == 4:
                message_2 = "卡3开的门"
            if parsed_CC == 8:
                message_2 = "卡4开的门"
            if parsed_CC == 16:
                message_2 = "卡5开的门"
            if parsed_CC == 32:
                message_2 = "卡6开的门"
            if parsed_CC == 64:
                message_2 = "卡7开的门"
            if parsed_CC == 128:
                message_2 = "卡8开的门"

            if parsed_DD == 1:
                message_2 = "门未锁好"
            if parsed_DD == 2:
                message_2 = "胁迫密码开门"
            if parsed_DD == 4:
                message_2 = "电量不足"
            if parsed_DD == 8:
                message_2 = "暴力破坏"
            if parsed_DD == 16:
                message_2 = "恶意破解"
            if parsed_DD == 128:
                message_2 = "外部门开报警"

        return message_1, message_2


if __name__ == '__main__':
    s = UtilsLock()
