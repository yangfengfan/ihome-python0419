# -*- coding: utf-8 -*-

import json
import GlobalVars
import Utils
import time
import datetime
from WebHandlerBase import *
from DBManagerHistory import *


class WarningHandler(WebHandlerBase):

    # 查询指定的联动预案或模式
    def show(self, param):
        Utils.logDebug("show warning")
        buf = self.sendCommand(GlobalVars.TYPE_CMD_READ_ALARMS, param)
        if buf == None:
            return self.failWithMsg("网关故障，重启可恢复")
        jobj = json.loads(buf)
        resultobj = {}
        resultobj['ret'] = jobj.get('ret', 0)
        respobj = jobj.get('response', None)
        if respobj != None:
            alarms = respobj.get('data', ())
            alarmstr = []
            for alarm in alarms:
                alarmstr.append(json.dumps(alarm))
            resultobj['alarms'] = alarmstr
            pager = respobj.get('pager', None)
            if pager != None:
                resultobj['pager'] = pager
        return self.successWithObj(resultobj)

    ##
    def confirm(self, param):
        Utils.logDebug("confirm warning")
        buf = self.sendCommand(GlobalVars.TYPE_CMD_CONFIRM_ALARMS, param)
        return self.successWithMsg(buf)

    def confirmRead(self, param):
        if not param:
            self.failWithMsg("Invalid param...")
        id = param.get("id", None)
        if id is None:
            self.failWithMsg("Invalid param...")
        alarm_dict = DBManagerHistory().getById(id)
        if not alarm_dict:
            self.failWithMsg("No such alarm...")
        alarm_dict.get("valueStr")["isRead"] = 1
        DBManagerHistory.updateById(id, alarm_dict)

    def show1(self, param):
        Utils.logDebug("===>alarm show1: %s" % param)
        if not param:
            self.failWithMsg("Invalid param...")

        date_time = param.get("alarmTime", None).split('-')
        start = int(param.get("start", 0))
        size = int(param.get("size", 10))
        alarm_type = param.get("type", "alarm_type")
        device_type = WarningHandler.get_device_type(alarm_type)
        start_date_time = datetime.datetime(int(date_time[0]), int(date_time[1]), int(date_time[2]), 0, 0, 0)
        start_timestamp = time.mktime(start_date_time.timetuple())
        end_date_time = datetime.datetime(int(date_time[0]), int(date_time[1]), int(date_time[2]), 23, 59, 59)
        end_timestamp = time.mktime(end_date_time.timetuple())

        result = DBManagerHistory().getByDatatypeAndTimeStamp("alarms", start_timestamp, end_timestamp, deviceType=device_type)
        alarm_list = list()
        pager = dict(size=str(size), start=str(start), total="0")
        if result is not None and len(result) > 0 and len(result) >= start:
            result.reverse()
            real_size = min(size, len(result)-start)
            for i in range(real_size):
                item = result[start+i]
                one_result_dict = dict(alarmId=item.get("id"), detail=item.get("valueStr")[0], isRead=item.get("isRead", 0))
                alarm_list.append(one_result_dict)
            pager["total"] = str(len(result))
        result_dict = dict(ret=0, alarms=alarm_list, pager=pager)
        Utils.logDebug("===>show1, result_dict: %s" % result_dict)
        return result_dict

    def delete1(self, param):
        if not param:
            self.failWithMsg("Invalid param...")
        alarm_id_list = param.get("alarmId", None)
        if not alarm_id_list:
            self.failWithMsg("Invalid param...")
        delete_list = list()
        for item in alarm_id_list:
            delete_list.append(item.get("alarmId"))
        result = DBManagerHistory().batchDeleteById(delete_list)
        if result:
            return {"ret": 0}
        self.failWithMsg("Internal sever error...")

    def batch_delete(self, param):
        if not param:
            self.failWithMsg("Invalid param...")

        date_time = param.get("alarmTime", None).split('-')
        start = int(param.get("start", 0))
        size = int(param.get("size", 10))
        alarm_type = param.get("type", "alarm_type")
        device_type = WarningHandler.get_device_type(alarm_type)
        start_date_time = datetime.datetime(int(date_time[0]), int(date_time[1]), int(date_time[2]), 0, 0, 0)
        start_timestamp = time.mktime(start_date_time.timetuple())
        end_date_time = datetime.datetime(int(date_time[0]), int(date_time[1]), int(date_time[2]), 23, 59, 59)
        end_timestamp = time.mktime(end_date_time.timetuple())

        result = DBManagerHistory().getByDatatypeAndTimeStamp("alarms", start_timestamp, end_timestamp,
                                                              deviceType=device_type)
        delete_list = list()
        if result:
            for item in result:
                delete_list.append(item.get("id"))
        if delete_list:
            Utils.logInfo("===>batch_delete, delete_list: %s" % delete_list)
            success = DBManagerHistory().batchDeleteById(delete_list)
            if success:
                return {"ret": 0}
            else:
                return {"ret": ErrorCode.ERR_GENERAL}
        return {"ret": 0}

    # @staticmethod
    # def get_device_type(alarm_type):
    #     device_type = ""
    #     if "火灾报警" in alarm_type:
    #         device_type = "Smoke"
    #     elif "环境污染" in alarm_type:
    #         device_type = "Env"
    #     elif "非法入侵" in alarm_type:
    #         device_type = "Exist"
    #     elif "煤气超标" in alarm_type:
    #         device_type = "Ch4CO"
    #     elif "水浸报警" in alarm_type:
    #         device_type = "Water"
    #     elif "跌倒报警" in alarm_type:
    #         device_type = "Fall"
    #     elif "一键报警" in alarm_type:
    #         device_type = "SOS"
    #     elif "门锁告警" in alarm_type:
    #         device_type = "Lock"
    #     return device_type

    @staticmethod
    def get_device_type(alarm_type):
        device_type = ""
        if alarm_type == u"火灾报警":
            device_type = u"Smoke"
        elif alarm_type == u"环境污染":
            device_type = u"Env"
        elif alarm_type == u"非法入侵" or alarm_type == u"存在传感器欠压":
            device_type = u"Exist"
        elif alarm_type == u"煤气超标":
            device_type = u"Ch4CO"
        elif alarm_type == u"水浸报警" or alarm_type == u"水浸欠压":
            device_type = u"Water"
        elif alarm_type == u"跌倒报警":
            device_type = "Fall"
        elif alarm_type == u"一键报警":
            device_type = "SOS"
        elif alarm_type == u"门锁告警":
            device_type = "Lock"
        elif alarm_type == u"门窗磁报警" or alarm_type == u"门窗磁欠压":
            device_type = u"Gsm"
        elif alarm_type == u"红外入侵感应器报警" or alarm_type == u"红外入侵感应器欠压":
            device_type = u"CurtainSensor"
        return device_type
