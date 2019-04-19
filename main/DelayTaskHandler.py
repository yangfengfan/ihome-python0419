# -*- coding: utf-8 -*-
from ThreadBase import *
from DBManagerTask import *
import Utils
import time
from pubsub import pub


class DelayTaskHandler(ThreadBase):

    __instant = None
    __lock = threading.Lock()

    # 保存定时任务，格式{"taskTime": 1460627182, "task":[{"modeId": "1"}, {"controls":[]}]}
    # 任务按照time排序
    task_list = list()

    # 定时器list
    timer_list = list()

    # singleton
    def __new__(cls, arg):
        Utils.logDebug("__new__")
        if DelayTaskHandler.__instant is None:
            DelayTaskHandler.__lock.acquire()
            try:
                if DelayTaskHandler.__instant is None:
                    Utils.logDebug("new DelayTaskHandler singleton instance.")
                    DelayTaskHandler.__instant = ThreadBase.__new__(cls)
            finally:
                DelayTaskHandler.__lock.release()
        return DelayTaskHandler.__instant

    def __init__(self, thread_id):
        ThreadBase.__init__(self, thread_id, "DelayTaskHandler")
        # self.stopWatchDog()

    def run(self):
        self.load_tasks()
        self.init()
        Utils.logInfo("DelayTaskHandler is running.")
        switch_state = DBManagerTask().check_switch("delay")
        if switch_state == "on":
            self.start_handling()
        else:
            self.stop()

    def stop(self):
        for timer in DelayTaskHandler.timer_list:
            timer.cancel()
            Utils.logInfo("===>timer canceled...")
            # DelayTaskHandler.timer_list.remove(timer)
        DelayTaskHandler.timer_list = list()  # 解决任务列表没有完全清空的BUG
        ThreadBase.stop(self)

    # 从数据库读取所有定时任务, 并排序
    def load_tasks(self):
        self.task_list = DBManagerTask().get_by_type("delay")
        if self.task_list is not None and len(self.task_list) > 0:
            self.task_list.sort(key=lambda x: x["taskTimeStamp"], reverse=True)

    def start_handling(self):
        Utils.logInfo("===>start_handling...")
        try:
            self.load_tasks()
            if self.task_list is None or len(self.task_list) == 0:
                Utils.logInfo("No task to execute...")
                self.stop()
                self.stopWatchDog()
            else:
                delay_list = list()
                for task in self.task_list:
                    t = int(time.time())
                    current_time = t - t % 60  # 去掉最后的秒数
                    task_time = task.get("taskTimeStamp")
                    delay = task_time - current_time
                    if delay > 0:
                        task["delay"] = delay
                        delay_list.append(task)
                    else:
                        self.task_list.remove(task)
                        DBManagerTask().delete_task(task.get("id"))
                    delay_list.sort(key=lambda x: x["delay"])
                if delay_list is not None and len(delay_list) > 0:
                    Utils.logInfo("===>delay_list: %s" % delay_list)
                    for delay_task in delay_list:
                        timer = threading.Timer(float(delay_task.get("delay")), DelayTaskHandler.execute_task, (delay_task,))
                        DelayTaskHandler.timer_list.append(timer)
                        timer.start()
        except Exception, err:
            Utils.logError("TimeTaskHandler error: %s" % err)
        finally:
            pass

    @staticmethod
    def execute_task(task):
        try:
            Utils.logInfo("===>Wake up now, execute the delay task, task_id: %s" % task.get("id"))
            mode_id = task.get('modeId', None)
            devices = task.get("devices", None)
            if mode_id is not None:
                pub.sendMessage("door_open", sparam=task)
            if devices is not None:
                devices["cmdSource"] = "task"  # 添加一个命令源参数，指明此控制命令来自定时或延时任务
                pub.sendMessage("publish_control_device", cmd="controlDevice", controls=devices)
            DBManagerTask().delete_task(task.get("id"), update_check=False)
        except Exception as err:
            Utils.logError("===>Error while execute delay task: %s, error: %s" % (task.get("id"), err))


