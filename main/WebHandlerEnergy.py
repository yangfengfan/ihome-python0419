# -*- coding: utf-8 -*-

import json
import GlobalVars
import Utils
from WebHandlerBase import *
from DBManagerHistory import *


class EnergyHandler(WebHandlerBase):

    def __getMeterData(self, addr_list, time_list):
        result_list = list()
        # interval==1800 ---> day, interval>1800 ---> month
        interval = abs(int(time_list[0]) - int(time_list[1]))
        for addr in addr_list:
            one_result_list = list()
            result = DBManagerHistory().getByDevAddrAndTimeStamp(addr, time_list[0], time_list[-1])
            if result:
                size = min(len(time_list), len(result))
                if interval < 10000:
                    for i in range(size):
                        payload = json.dumps(result[i])
                        timestamp = time_list[i]
                        one_result_dict = dict(addr=addr, payload=payload, time=timestamp)
                        one_result_list.append(one_result_dict)
                    while len(one_result_list) < len(time_list):
                        last_one = one_result_list[-1]
                        one_result_list.append(last_one)
                else:
                    for i in range(0, size, 48):
                        payload = json.dumps(result[i])
                        timestamp = time_list[i]
                        one_result_dict = dict(addr=addr, payload=payload, time=timestamp)
                        one_result_list.append(one_result_dict)
                    while len(one_result_list) < len(time_list):
                        last_payload = json.dumps(result[-1])
                        last_ts = time_list[-1]
                        last_one_dict = dict(addr=addr, payload=last_payload, time=last_ts)
                        one_result_list.append(last_one_dict)
            else:
                for ts in time_list:
                    one_result_dict = dict(addr=addr, payload=None, time=ts)
                    one_result_list.append(one_result_dict)
            for item in one_result_list:
                result_list.append(item)
        return result_list

    def __queryEnergyData(self, param):
        Utils.logDebug("===>queryEnergyData, param: %s" % param)
        if not param:
            self.failWithMsg("Invalid parameters...")
        try:
            addr_dict_list = param.get("addr", None)
            time_dict_list = param.get("time", None)
            if not addr_dict_list or not time_dict_list:
                self.failWithMsg("Invalid parameters...")
            addr_list = list()
            time_list = list()
            for addr_item in addr_dict_list:
                addr_list.append(addr_item.get("addr"))
            for time_item in time_dict_list:
                time_list.append(int(time_item.get("time")))
            # time_list.sort()
            result = self.__getMeterData(addr_list, time_list)
            if result:
                return dict(ret=0, response=result)
            return dict(ret=0, response=[])
        except Exception as err:
            Utils.logError("__queryEnergyData error: %s" % err)
            return dict(ret=ErrorCode.ERR_GENERAL)

    def query_elec(self, param):
        return self.__queryEnergyData(param)

    def query_socket(self, param):
        return self.__queryEnergyData(param)

    def query_water(self, param):
        return self.__queryEnergyData(param)

    def query_gas(self, param):
        return self.__queryEnergyData(param)
