# -*- coding: utf-8 -*-
from ThreadBase import *
from DBManagerTask import *
import Utils
import time
from pubsub import pub
import copy


class RepeatTaskHandler(ThreadBase):

    __instant = None
    __lock = threading.Lock()

    # 保存定时任务，格式{"taskTime": 1460627182, "task":[{"modeId": "1"}, {"controls":[]}]}
    # 任务按照time排序
    task_list = list()

    # 最近的一个定时任务
    delay_list = list()

    # 保存Timer的实例
    timer_list = list()

    # singleton
    def __new__(cls, arg):
        Utils.logDebug("__new__")
        if RepeatTaskHandler.__instant is None:
            RepeatTaskHandler.__lock.acquire()
            try:
                if RepeatTaskHandler.__instant is None:
                    Utils.logDebug("new RepeatTaskHandler singleton instance.")
                    RepeatTaskHandler.__instant = ThreadBase.__new__(cls)
            finally:
                RepeatTaskHandler.__lock.release()
        return RepeatTaskHandler.__instant

    def __init__(self, thread_id):
        ThreadBase.__init__(self, thread_id, "RepeatTaskHandler")
        # self.stopWatchDog()

    def run(self):
        self.init()
        Utils.logInfo("RepeatTaskHandler is running.")
        # self.load_tasks()
        switch_state = DBManagerTask().check_switch("repeat")
        if switch_state == "on":
            self.start_handling()
        else:
            self.stop()

    def stop(self):
        for timer in RepeatTaskHandler.timer_list:
            Utils.logInfo("===>cancel timer...")
            timer.cancel()
            # RepeatTaskHandler.timer_list.remove(timer)
        RepeatTaskHandler.timer_list = list()  # 解决任务列表没有完全清空的BUG
        ThreadBase.stop(self)

    # 从数据库读取所有定时任务, 并排序
    def load_tasks(self):
        self.task_list = None
        self.delay_list = None
        self.task_list = DBManagerTask().get_by_type("repeat")
        if self.task_list is not None and len(self.task_list) > 0:
            self.delay_list = self.get_delay_list()
            Utils.logInfo("===>task_list: %s" % self.task_list)
            Utils.logInfo("===>delay_list: %s" % self.delay_list)

    def get_delay_list(self):

        # 将重复任务转成延时任务存放
        delay_task_list = list()

        # tm_year=2016, tm_mon=4, tm_mday=21, tm_hour=12, tm_min=54, tm_sec=28, tm_wday=3, tm_yday=112, tm_isdst=0
        current_time_array = time.localtime()
        for task_item in self.task_list:
            # 存放执行时间和当前时间的时间差，单位 秒
            delay_time_list = list()
            repeat_list = task_item.get("repeat", None)
            if repeat_list is not None and len(repeat_list) > 0:
                for repeat_item in repeat_list:
                    operation_time = repeat_item.values()[0].split(":")
                    hour = int(operation_time[0])
                    minute = int(operation_time[1])
                    # 天数差
                    delta_day = int(repeat_item.keys()[0]) - int(current_time_array.tm_wday)
                    # 小时差
                    delta_hour = hour - current_time_array.tm_hour
                    # 分钟差
                    delta_min = minute - current_time_array.tm_min
                    # 总的时间差，单位 秒
                    delta_sum = 60*delta_min + 60*60*delta_hour + 60*60*24*delta_day
                    if delta_sum < 0:
                        delta_sum += 60*60*24*7
                    elif delta_sum == 0:
                        delta_sum = 30
                    delay_time_list.append(delta_sum)

                delay_time_list.sort()

            task_item["delay"] = delay_time_list
            delay_task_list.append(task_item)

        return delay_task_list

    def start_handling(self):
        Utils.logInfo("===>start to handle repeat task...")
        try:
            self.load_tasks()
            if self.delay_list is None or len(self.delay_list) == 0:
                Utils.logInfo("No Repeat task to execute...")
                self.stop()
                self.stopWatchDog()
            else:
                for task in self.delay_list:
                    for timeToDelay in task.get("delay"):
                        timer = threading.Timer(float(timeToDelay), RepeatTaskHandler.task_timer, (task,))
                        RepeatTaskHandler.timer_list.append(timer)
                        timer.start()
        except Exception, err:
            Utils.logError("TimeTaskHandler error: %s" % err)
        finally:
            pass

    @staticmethod
    def task_timer(task):
        Utils.logInfo("===>Wake up now, execute the repeat task, task_id: %s" % task.get("id"))
        RepeatTaskHandler.execute_task(task)
        new_timer = threading.Timer(float(60*60*24*7), RepeatTaskHandler.task_timer, (task,))
        RepeatTaskHandler.timer_list.append(new_timer)
        new_timer.start()

    @staticmethod
    def execute_task(task):

        mode_id = task.get('modeId', None)
        devices = task.get("devices", None)
        if mode_id:
            pub.sendMessage("door_open", sparam=task)
        if devices:
            devices["cmdSource"] = "task"  # 添加一个命令源参数，指明此控制命令来自定时或延时任务
            pub.sendMessage("publish_control_device", cmd="controlDevice", controls=devices)
