#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import socket
import struct
import time
import Utils

'''
批量添加设备的工具类
属性：scanning: 扫描标记，初始值未False，当实例调用scan()方法后赋值未True，表示扫描中
      sock: socket对象，实例化一个端口为8899的端口，发送搜索设备命令，调用scan()方法时实例化该sock属性，
            调用stop_scan()方法后close 并置为None

方法：
    scan(): 开始扫描
    stop_scan(): 停止扫描
'''


class BatchScanner(object):

    def __init__(self):
        self.scanning = False
        self.sock = None
        # self.scanningTime = 0

    # Begin to scan devices
    def scan(self):
        Utils.logDebug("---------------------- Begin to scan device ----------------------")  # info
        self.scanning = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                               # 包号为2时表示批量添加  20170314
        data_buffer = struct.pack("=3BH25B2B", 0x68, 2, 0x03, 0x19, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0, 0x1C, 0xED)
        local_svr_addr = ('127.0.0.1', 8899)

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            Utils.logDebug("connect to device....")
            self.sock.connect(local_svr_addr)
        except:
            Utils.logError("Batch scanning error, socket connect failed....")

        while self.scanning:
            Utils.logDebug("scanning device.......")
            try:
                if self.sock is not None:
                    self.sock.send(data_buffer)
                    time.sleep(3)
                    # self.scanningTime += 3
                else:
                    break
            except Exception as e:
                Utils.logError("Batch scanning device error...")
                break

        if self.sock is not None:
            self.sock.close()

    # Stop scanning
    def stop_scan(self):
        self.scanning = False
        if self.sock is not None:
            self.sock = None

    # 监控扫描过程，超过2分钟停止扫描
    # def scanner_watchdog(self, stop_func):
    #     while self.scanningTime < 120:
    #         continue
    #     stop_func()
