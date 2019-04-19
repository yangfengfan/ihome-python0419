# -*- coding: utf-8 -*-

import json
import GlobalVars
import Utils
from WebHandlerBase import *


class RoomHandler(WebHandlerBase):
    ##
    def remove(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_REMOVE_ROOM_PROP, sparam)
        return self.successWithMsg(buf)

    def update(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_UPDATE_ROOM_PROP, sparam)
        return self.successWithMsg(buf)

    ##
    def show(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_ROOM_PROP, sparam)
        return self.successWithMsg(buf)

    ##
    def removearea(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_REMOVE_AREA_PROP, sparam)
        return self.successWithMsg(buf)

    def updatearea(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_UPDATE_AREA_PROP, sparam)
        return self.successWithMsg(buf)

    ##
    def showarea(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_AREA_PROP, sparam)
        return self.successWithMsg(buf)

    ##
    def removemode(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_REMOVE_ROOM_MODE, sparam)
        return self.successWithMsg(buf)

    def removeglobalmode(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_REMOVE_GLOBAL_MODE, sparam)
        return self.successWithMsg(buf)

    def updatemode(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_UPDATE_ROOM_MODE, sparam)
        return self.successWithMsg(buf)

    ##
    def showmode(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_QUERY_ROOM_MODE, sparam)
        return self.successWithMsg(buf)

    ##
    def activemode(self, sparam):
        buf = self.sendCommand(GlobalVars.TYPE_CMD_ACTIVE_ROOM_MODE, sparam)
        return self.successWithMsg(buf)

