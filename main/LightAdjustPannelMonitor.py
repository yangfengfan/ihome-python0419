# -*- coding: utf-8 -*-

from ThreadBase import *
from pubsub import pub
from PacketParser import  *
from DBManagerDevice import *
import GlobalVars
import threading
import time
import Utils


class LightAdjustPannelMonitor(ThreadBase):
    __instant = None
    __lock = threading.Lock()

    # singleton
    def __new__(self, arg):
        Utils.logDebug("__new__")
        if (LightAdjustPannelMonitor.__instant == None):
            LightAdjustPannelMonitor.__lock.acquire()
            try:
                if (LightAdjustPannelMonitor.__instant == None):
                    Utils.logDebug("new LightAdjustPannelMonitor singleton instance.")
                    LightAdjustPannelMonitor.__instant = ThreadBase.__new__(self)
            finally:
                LightAdjustPannelMonitor.__lock.release()
        return LightAdjustPannelMonitor.__instant

    def __init__(self, tid):
        ThreadBase.__init__(self, tid, "LightAdjustPannelMonitor")
        self.pannelDict = {}

    def run(self):
        self.init()

        # 监听启动和停止调光定时发送事件
        pub.subscribe(self.start_pannel_listen, GlobalVars.PUB_START_PANNEL_LISTEN)
        pub.subscribe(self.stop_pannel_listen, GlobalVars.PUB_STOP_PANNEL_LISTEN)

        # 监测是否有处于节律模式的调光控制面板
        self.check_pannel_listen()

    # 启动一个新的定时发送线程
    def start_pannel_listen(self, addr, addr_ray_sense, device_name):
        if addr not in self.pannelDict:
            Utils.logDebug("Start monitor at: %s" % addr)
            if addr_ray_sense == "":
                Utils.logError("------PanelMonitor------")
                monitor = PannelMonitor(target=self.send_pannel_cmd, args=(addr, addr_ray_sense, device_name))
            else:
                Utils.logError("------PanelRaySenseMonitor------")
                monitor = PanelRaySenseMonitor(target=self.send_pannel_cmd, args=(addr, addr_ray_sense, device_name))
            monitor.setDaemon(True)
            monitor.start()
            self.pannelDict[addr] = monitor

    # 关闭一个定时发送线程
    def stop_pannel_listen(self, addr):
        Utils.logDebug("Stop monitor at: %s" % addr)
        monitor = self.pannelDict.get(addr, None)
        if monitor:
            monitor.stop()
            self.pannelDict.pop(addr)

    # 将命令发出
    def send_pannel_cmd(self, addr, addr_ray_sense, deviceName):
        Utils.logError("Send circadian mode to device: %s" % addr)
        device_cmd_param = {"name": deviceName, "addr": addr, "addrRaySense": addr_ray_sense, "value": {"state": 1}, "type": DEVTYPENAME_LIGHTAJUST_PANNEL}
        Utils.logError("------send_pannel_cmd------")
        pub.sendMessage(GlobalVars.PUB_CONTROL_DEVICE, cmd="controlDevice", controls=device_cmd_param)

    # 线程启动时监测网关内是否有处在节律模式的调光控制面板
    def check_pannel_listen(self):
        pannel_list = DBManagerDevice().getLightAdjustPannelByState(1)
        addr_ray_sense = ""
        for pannel in pannel_list:
            addr = pannel.get("addr")
            props = DBManagerDeviceProp().getDeviceByDevAddrAndType(addr, DEVTYPENAME_LIGHTAJUST_PANNEL)
            link_light_sensor = props.get("linkLightSensor", None)
            if link_light_sensor is not None:
                device_status = link_light_sensor.get("deviceStatus", None)
                if device_status is not None:
                    addr_ray_sense = device_status.get("addr", "")
            Utils.logError("------check_pannel_listen addr_ray_sense: %s" % addr_ray_sense)
            device_name = pannel.get("name", "调光控制面板")
            if len(addr) == 20:
                self.start_pannel_listen(addr, addr_ray_sense, device_name)


# 监控器线程类
class PannelMonitor(threading.Thread):

    def __init__(self, target, args):
        threading.Thread.__init__(self)
        self.__target = target
        self.__args = args
        self.__running = threading.Event()  # 用于停止线程
        self.__running.set()

    def run(self):
        while self.__running.is_set():
            if self.__target:
                self.__target(*self.__args)
                time.sleep(900)  # 每15分钟执行一次
    def stop(self):
        self.__running.clear()


# 监控器线程类调光面板3秒执行
class PanelRaySenseMonitor(threading.Thread):

    def __init__(self, target, args):
        threading.Thread.__init__(self)
        self.__target = target
        self.__args = args
        self.__running = threading.Event()  # 用于停止线程
        self.__running.set()

    def run(self):
        while self.__running.is_set():
            if self.__target:
                self.__target(*self.__args)
                time.sleep(4)  # 每3秒钟执行一次

    def stop(self):
        self.__running.clear()
