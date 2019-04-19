# -*- coding: utf-8 -*-

import json
import GlobalVars
import Utils
from WebHandlerBase import *


class WrapperRequestsHandler(WebHandlerBase):
    ##
    def request(self, param, cmdType):
        Utils.logDebug("wrapper request cmdType=%s"%(str(cmdType)))
        if cmdType == GlobalVars.TYPE_CMD_RESTORE_HOST_PROP:
            return self.failWithMsg2(ErrorCode.ERR_CMD_NO_CLOUD_LINK, '请登录云账号')
        buf = self.sendCommand(cmdType, param)
        return self.successWithMsg(buf)
