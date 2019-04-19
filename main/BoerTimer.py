#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
from ThreadBase import *
import GlobalVars
import Utils
from pubsub import pub
from random import *


'''
定时发布消息：水电煤
定时发布消息：定时闹铃
定时发布消息：数据库同步
定时发布消息：心跳
'''

pub_last_static_bkup_time = 0   #水电煤数据定时备份的时间（秒）
pub_last_database_sync_time = 0  #每天0点到6点之间可能会（随机）同步一次数据库
pub_last_heartbeat_time = 0  #上次发布心跳消息的时间


class BoerTimer(ThreadBase):
    def __init__(self, threadId):
        ThreadBase.__init__(self, threadId, "BoerTimer")
        self.interval = GlobalVars.WATCHDOG_INTERVAL
        
    def publishStaticBackupPerHourMessage(self):
        # 水电煤数据
        '''每半小时备份一次水电煤数据'''
        Utils.logDebug("->publishStaticBackupPerHourMessage")
        global pub_last_static_bkup_time
        currTime = time.time()
        if pub_last_static_bkup_time == 0:
            pub_last_static_bkup_time = currTime

        if(currTime - pub_last_static_bkup_time > 1800):
            Utils.logDebug("pub_last_static_bkup_time %s" %(pub_last_static_bkup_time))
            metaDict={}
            metaDict["type"] = "energy"
            Utils.logInfo("publish PUB_BACKUP_START energy")
            pub.sendMessage(GlobalVars.PUB_BACKUP_START, backup=metaDict, arg2=None)
            pub_last_static_bkup_time = currTime

    def publishDBSyncMessagePerDay(self):
        Utils.logDebug("->publishDBSyncMessagePerDay")
        global pub_last_database_sync_time
        now = time.time()
        tmTime = time.localtime(now)
        tmHour = tmTime[3]
        
        if(tmHour == 0 and pub_last_database_sync_time < now):
            # 早晨1点到6点之前，可随机触发发布一个数据库同步消息
            '''0点时大概确定同步数据库的时间，1点到6点之间'''
            '''之所以确定在1个小时之后，是不想pub_last_database_sync_time在1小时内重新赋值'''
            pub_last_database_sync_time = now + 3600 + random()*5*60*60
        else:
            if now >= pub_last_database_sync_time and (now - pub_last_database_sync_time < self.interval):
                metaDict={}
                metaDict["type"] = "database"
                Utils.logInfo("publish PUB_BACKUP_START database")
                pub.sendMessage(GlobalVars.PUB_BACKUP_START, backup=metaDict, arg2=None)
                Utils.logDebug("publishDBSyncMessagePerDay %s" %(pub_last_static_bkup_time))
        
    def publishCloudHeartbeatMessage(self):
        Utils.logDebug("->publishCloudHeartbeatMessage")
        global pub_last_heartbeat_time
        now = time.time()
        if(now - pub_last_heartbeat_time >= GlobalVars.HEARTBEAT_INTERVAL):
            pub_last_heartbeat_time = now
            Utils.logInfo("publish PUB_CLOUD_HEARTBEAT")
            pub.sendMessage(GlobalVars.PUB_CLOUD_HEARTBEAT, arg1=None, arg2=None)
            Utils.logDebug("publishCloudHeartbeatMessage %s"%(pub_last_heartbeat_time))

    def publishSoftWatchDogMessage(self):
        Utils.logDebug("->publish PUB_SOFT_WATCHDOG")
        pub.sendMessage(GlobalVars.PUB_SOFT_WATCHDOG, arg1="")

    def run(self):
        self.init()
        Utils.logInfo("BoerTimer is running.")
        while not self.stopped:
            try:
                Utils.logInfo("Timer loop1.")
                time.sleep(self.interval)   # 10秒触发一次
                Utils.logInfo("--------Boer Timer start running--------")
                self.publishSoftWatchDogMessage()
                self.publishCloudHeartbeatMessage()
                self.publishStaticBackupPerHourMessage()
                self.publishDBSyncMessagePerDay()
                Utils.logInfo("--------Boer Timer go to sleep--------")
            except:
                Utils.logException('BoerTimer exception.')
