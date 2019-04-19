# -*- coding: utf-8 -*-

import threading
import GlobalVars
import Utils
from pubsub import pub


class ThreadBase(threading.Thread):  
    def __init__(self, threadId, threadName):
        threading.Thread.__init__(self)  
        self.tid = threadId
        self.name = threadName
        self.stopped = False
        import Queue
        self.que = Queue.Queue()
        self.watchdog = True
        
    def stop(self):
        Utils.logInfo("Stop Thread tid=%s,name=%s" % (self.tid, self.name))
        self.stopped = True
        try:
            self.que.put("stop thread.")
        except:
            pass

    def stopWatchDog(self):
        Utils.logInfo("Watchdog is stopped! tid=%s, name=%s" % (self.tid, self.name))
        self.watchdog = False
        
    def watchdogHandler(self, arg1, arg2=None):
        Utils.logDebug("Watchdog is triggered! tid=%s,name=%s,arg1=%s,arg2=%s"%(self.tid, self.name, arg1, arg2))
        if self.watchdog is True:
            pub.sendMessage(GlobalVars.PUB_ALIVING, tid=self.tid, threadname=self.name)
        
    def init(self):
        try:
            pub.subscribe(self.watchdogHandler, GlobalVars.PUB_SOFT_WATCHDOG)
        except:
            Utils.logException("thread %s init failed" % self.name)
