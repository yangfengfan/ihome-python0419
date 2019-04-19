# -*- coding: utf-8 -*-

import DBUtils
import Utils
import threading
import json
import time

# 设备表数据库名
TABLE_NAME_TASK = "tbl_task"
KEY_ID = "id"
KEY_VERSION = "version"
KEY_TASK_NAME = "name"      # 定时任务的名称
KEY_TASK_TYPE = "type"      # 定时任务的类型：延时任务（delay），重复任务(repeat)等
KEY_SWITCH_STATE = "switch"  # 定时任务的开关状态
KEY_TASK_DETAIL = "detail"    # 详细json


class DBManagerTask(object):

    __instance = None
    __lock = threading.Lock()

    # singleton
    def __new__(cls):
        if DBManagerTask.__instance is None:
            DBManagerTask.__lock.acquire()
            try:
                if DBManagerTask.__instance is None:
                    DBManagerTask.__instance = object.__new__(cls)
            finally:
                DBManagerTask.__lock.release()
        return DBManagerTask.__instance

    def __init__(self):
        Utils.logDebug("__init__")
        self.table_name = TABLE_NAME_TASK
        self.table_version = 1
        self.create_task_table()
        check_change = self.get_by_name("checkChange")
        if check_change is None:
            self.create_check_change()

    def create_check_change(self):

        detail_dict = dict()
        detail_dict["type"] = "check"
        detail_dict["delay"] = "NoChange"
        detail_dict["repeat"] = "NoChange"
        detail_dict["name"] = "checkChange"
        detail_dict["delaySwitchState"] = "on"
        detail_dict["repeatSwitchState"] = "on"
        detail_dict["switch"] = "na"
        detail_dict_str = json.dumps(detail_dict)
        save_sql = "INSERT INTO " + self.table_name + " values (?,?,?,?,?,?)"
        try:
            data = [(None, self.table_version, 'checkChange', 'check', "na", detail_dict_str)]
            conn = DBUtils.get_conn()
            success = DBUtils.save(conn, save_sql, data)
            if success is True:
                new_detail = self.get_by_name("checkChange")
                self.update_task(new_detail)
                return new_detail
        except Exception as err:
            Utils.logError("create_check_change() error... %s" % err)
            return None

    def update_check(self, task_type):

        Utils.logInfo("===>update_check...")

        if task_type is None:
            Utils.logError("task_type is None...")
            return None

        check_change = self.get_by_name("checkChange")
        check_change[task_type] = task_type
        check_change["timeStamp"] = int(time.time())
        # Utils.logError("------20190319 update_check check_change------%s" % check_change)
        self.update_task(check_change)

    def reset_check(self):
        check_change = self.get_by_name("checkChange")
        check_change["delay"] = "NoChange"
        check_change["repeat"] = "NoChange"
        self.update_task(check_change)

    def check_change(self):
        check_change = self.get_by_name("checkChange")
        delay_change = check_change["delay"]
        repeat_change = check_change["repeat"]
        return delay_change, repeat_change

    def check_switch(self, check_item):
        check_switch = self.get_by_name("checkChange")
        delay_switch = check_switch["delaySwitchState"]
        repeat_switch = check_switch["repeatSwitchState"]
        if check_item == "delay":
            return delay_switch
        elif check_item == "repeat":
            return repeat_switch
        elif check_item == "both":
            return delay_switch, repeat_switch
        else:
            return None

    def create_task_table(self):
        Utils.logDebug("->createActionTable")
        create_table_sql = "CREATE TABLE IF NOT EXISTS '" + self.table_name + "' ("
        create_table_sql += " `" + KEY_ID + "` INTEGER primary key autoincrement,"
        create_table_sql += " `" + KEY_VERSION + "` INTEGER NOT NULL,"
        create_table_sql += " `" + KEY_TASK_NAME + "` varchar(50) UNIQUE,"
        create_table_sql += " `" + KEY_TASK_TYPE + "` varchar(50) ,"
        create_table_sql += " `" + KEY_SWITCH_STATE + "` varchar(50) ,"
        create_table_sql += " `" + KEY_TASK_DETAIL + "` TEXT"
        create_table_sql += " )"
        conn = DBUtils.get_conn()
        DBUtils.create_table(conn, create_table_sql)

    # 检查数据库文件状态
    # host.db存放配置数据
    # 如果数据库文件损坏，fetchall()应抛出异常
    def check_healthy(self):
        conn = DBUtils.get_conn()
        sql = "select * from " + self.table_name
        DBUtils.fetchall(conn, sql)

    def add_task(self, task):
        if not task:
            return None

        task_name = task.get("modeId", str(int(time.time())))
        task_type = task.get("type", None)
        task_switch = task.get("switch", "on")
        task_detail = json.dumps(task)
        # Utils.logError("------20190319 add_task task_detail------%s" % task_detail)
        try:
            sql = "INSERT INTO " + self.table_name + " values (?,?,?,?,?,?)"
            values = [(None, self.table_version, str(task_name), task_type, task_switch, task_detail)]
            conn = DBUtils.get_conn()
            success = DBUtils.save(conn, sql, values)
            if success is True:
                # Utils.logError("------20190319 add success------")
                new_detail = self.get_by_name(task.get("name"))
                # Utils.logError("------20190319 new_detail------%s" % new_detail)
                self.update_task(new_detail)
                Utils.logInfo("===>update_check in add...")
                self.update_check(task_type)
                return new_detail
            else:
                return None
        except Exception as err:
            Utils.logError("add_task() error: %s" % err)
            raise

    def get_all(self):

        result_list = list()
        try:
            sql = "SELECT * FROM " + self.table_name
            conn = DBUtils.get_conn()
            fetch_result = DBUtils.fetchall(conn, sql)
            if fetch_result is not None:
                for item in fetch_result:
                    result = json.loads(item[-1])
                    result["id"] = item[0]
                    result_list.append(result)
            return result_list
        except Exception as err:
            Utils.logError("get_one_task() error: %s" % err)
            return None

    def get_by_name(self, task_name):

        if task_name is None:
            return None
        try:
            sql = "SELECT * FROM " + self.table_name + " WHERE name= " + "'" + str(task_name) + "'"
            conn = DBUtils.get_conn()
            fetch_result = DBUtils.fetchall(conn, sql)
            if fetch_result is not None and len(fetch_result) > 0:
                item = fetch_result[0]
                result_dict = json.loads(item[-1])
                result_dict["id"] = item[0]
                return result_dict
            else:
                return None
        except Exception as err:
            Utils.logError("get_by_name() error: %s" % err)
            return None

    def get_one_task(self, task_id):

        if task_id is None:
            return None
        try:
            result = dict()
            sql = "SELECT * FROM " + self.table_name + " WHERE id= " + str(task_id)
            conn = DBUtils.get_conn()
            fetch_result = DBUtils.fetchall(conn, sql)
            if fetch_result is not None and len(fetch_result) > 0:
                item = fetch_result[0]
                result = json.loads(item[-1])
                result["id"] = item[0]
            return result
        except Exception as err:
            Utils.logError("get_one_task() error: %s" % err)
            return None

    def get_by_type(self, task_type):

        if task_type is None:
            return None

        result_list = list()
        try:
            sql = "SELECT * FROM " + self.table_name + " WHERE type= " + "'" + task_type + "'"
            conn = DBUtils.get_conn()
            fetch_result = DBUtils.fetchall(conn, sql)
            if fetch_result is not None:
                for item in fetch_result:
                    result = json.loads(item[-1])
                    result["switch"] = item[-2]
                    if result["switch"] == "on":
                        result["id"] = item[0]
                        result_list.append(result)
            return result_list
        except Exception as err:
            Utils.logError("get_by_type() error: %s" % err)
            return None

    def get_active_tasks(self):

        result_list = list()
        try:
            sql = "SELECT * FROM " + self.table_name + " WHERE switch='on'"
            conn = DBUtils.get_conn()
            fetch_result = DBUtils.fetchall(conn, sql)
            if fetch_result is not None:
                for item in fetch_result:
                    result = json.loads(item[-1])
                    result_list.append(result)
            return result_list
        except Exception as err:
            Utils.logError("get_active_tasks() error: %s" % err)
            return None

    # 查询全剧模式的定时任务
    def get_global_mode_task(self, modeIds):
        result_dict = {}
        try:
            condition = ','.join(modeIds)
            sql = "SELECT name, detail FROM " + self.table_name + " WHERE name IN (" + condition + ") AND switch = 'on'"
            conn = DBUtils.get_conn()
            fetch_result = DBUtils.fetchall(conn, sql)
            if fetch_result:
                for item in fetch_result:
                    detail = json.loads(item[-1])
                    typo = detail.get('type')
                    if typo == "repeat":
                        result_dict[str(item[0])] = {'type': typo, 'cycle': detail.get('repeat')}
                    else:
                        result_dict[str(item[0])] = {'type': typo, 'cycle': detail.get('triggerTime')}
            return result_dict
        except Exception as e:
            Utils.logError("get_global_mode_task() error: %s" % e)
            return result_dict

    def delete_by_name(self, name):
        '''
        根据名字删除定时、延时任务（任务表中的任务名字其实是模式的ID）
        :param name: 定时、延时任务的名字
        :return: true if success
        '''
        try:
            task = self.get_by_name(name)
            if task:
                task_type = task.get("type")
                sql = "DELETE FROM " + self.table_name + " WHERE id= " + str(task.get('id'))
                conn = DBUtils.get_conn()
                DBUtils.deleteone(conn, sql)
                self.update_check(task_type)

        except Exception as e:
            Utils.logError("delete_by_name() error: %s" % e)
            return None

    def update_task(self, params):

        if params is None:
            return None

        Utils.logInfo("===>params: %s" % params)

        task_id = params.get("id", None)
        # Utils.logError("------20190319 update_task task_id------%s" % task_id)
        new_task_type = params.get("type", None)
        task_switch = params.get("switch", "on")
        if new_task_type == "check":
            task_switch = "na"
        if task_id is None:
            return None
        old_detail = self.get_one_task(task_id)
        # Utils.logError("------20190319 update_task old_detail------%s" % old_detail)
        old_task_type = old_detail.get("type", None)
        try:
            params_str = json.dumps(params)
            Utils.logInfo("===>params_str: %s" % params_str)
            # sql = "UPDATE " + self.table_name + " SET detail=? " + " WHERE id=" + str(task_id)
            sql = "UPDATE " + self.table_name + " SET type='" + new_task_type + "'"
            sql += ", switch='" + task_switch + "'"
            sql += ", detail='" + params_str + "'" + " WHERE id=" + str(task_id) + ";"
            Utils.logInfo("===>sql: %s" % sql)
            conn = DBUtils.get_conn()
            success = DBUtils.update_all(conn, sql)
            # Utils.logError("------20190319 UPDATE success------")
            if success is True:
                new_detail = self.get_one_task(task_id)
                # Utils.logError("------20190319 update_task new_detail------%s" % new_detail)
                Utils.logInfo("===>new_detail after update: %s" % new_detail)
                if new_task_type != "check":
                    # Utils.logError("------20190319 update_task new_task_type------%s" % new_task_type)
                    self.update_check(new_task_type)
                    if new_task_type != old_task_type:
                        # Utils.logError("------20190319 update_task old_task_type------%s" % old_task_type)
                        self.update_check(old_task_type)
                return new_detail
            else:
                return None
        except Exception as err:
            Utils.logError("get_one_task() error: %s" % err)
            return None

    def delete_task(self, task_id, update_check=True):

        if task_id is None:
            return None

        try:
            task = self.get_one_task(task_id)
            if not task:
                Utils.logInfo("===>task %s has been deleted..." % task_id)
                return
            task_type = task.get("type")
            sql = "DELETE FROM " + self.table_name + " WHERE id= " + str(task_id)
            conn = DBUtils.get_conn()
            DBUtils.deleteone(conn, sql)
            if update_check:
                self.update_check(task_type)
            return None
        except Exception as err:
            Utils.logError("get_one_task() error: %s" % err)
            return None

