# -*- coding: utf-8 -*-

import json
import GlobalVars
import Utils
from WebHandlerBase import *


class PlanHandler(WebHandlerBase):

    # 查询指定的联动预案或模式
    def show(self, param):
        Utils.logDebug("show link action, param: %s" % param)
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_LINK_ACTION, param)
        return self.successWithMsg(buf)

    # 更新联动预案或模式
    def update(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_UPDATE_LINK_ACTION, param)
        return self.successWithMsg(buf)

    # 激活联动预案或模式
    def activate(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_ACTIVE_ROOM_MODE, param)
        return self.successWithMsg(buf)

    # 查询全局模式
    def queryGlobalModes(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_GLOBAL_MODE, param)
        return self.successWithMsg(buf)

    def modifyModeName(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_MODIFY_MODE_NAME, param)
        return self.successWithMsg(buf)

    # 为情景模式设置定时任务
    def setTimeTask(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_SET_TIME_TASK, param)
        return self.successWithMsg(buf)

    # 开启或者关闭情景模式定时任务
    def switchTimeTask(self, param):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_SWITCH_TIME_TASK, param)
        return self.successWithMsg(buf)

    # 查询全部模式，包括全局模式和房间模式
    def allModes(self, param):
        Utils.logDebug("===>switchTimeTask, param: %s" % param)
        buf = self.sendCommand(GlobalVars.TYPE_CMD_GET_ALL_MODES, param)
        return self.successWithMsg(buf)


