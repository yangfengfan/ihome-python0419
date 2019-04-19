#!/usr/bin/python
# -*- coding: utf-8 -*-

from BoerTimer import *
from HostControlServer import *
from HostReportServer import *
from HostCloudClient import *
from HostBackupServer import *
import time
from GlobalVars import *
# from DBManagerUpgrade import *
from pubsub import pub
import threading
import os
import hashlib
import base64
from SocketHandlerServer import *
import platform
import struct
import uuid
import os
import DBUtils
import GlobalVars
from DBManagerAction import *
from DBManagerDeviceProp import *
from DBManagerHostId import *
from DBManagerUser import *
from DBManagerAlarm import *
from DBManagerBackup import *
from DBManagerHistory import *
from DBManagerDevice import *
from DBManagerRoom import *
from DBManagerRoomArea import *
from DBManagerLinks import *
# from DBManagerUpgrade import *
from DBManagerTask import *
from HostExceptionServer import *
from DelayTaskHandler import *
from RepeatTaskHandler import *
from RokidConnector import *
from LightAdjustPannelMonitor import *
import os
import ssl
import sys
import statvfs
import Utils
import shutil
import hashlib
import thread
import urllib2
import urllib
if (platform.system()!="Windows"):
    import fcntl
import signal
import ctypes

#线程Id
TID_TIMER = 100
TID_CONTROL_SERVER= 101
TID_REPORT_SERVER = 102
TID_BACKUP_SERVER = 103
TID_CLOUD_CLIENT  = 104
TID_CONFIG_SERVER = 105
TID_REPORT_HANDLER = 106
TID_DELAY_TASK_HANDLER = 107
TID_REPEAT_TASK_HANDLER = 108
TID_EXCEPTION_SERVER = 110
TID_ROKID_SSDP_SERVER = 111
TID_ROKID_TCP_SERVER = 112
TID_LIGHTADJUST_PANNEL_MONITOR = 113


threadTimeAlivingDict = {}  # 线程Id对应的存活时间
threadIdInstanceDict = {}   # 线程Id对应的线程实例

def aliving(tid, threadname):
    Utils.logDebug("thread %s is aliving. thread name=%s"%(tid, threadname))
    threadTimeAlivingDict[tid] = 0

# def restartDownload(filename, md5):
#     Utils.logDebug("->restartDownload() %s"%(filename))
#     u = initParams(filename, md5, 0, 0, "ongoing")
#     DBManagerUpgrade().saveUpgrade(json.dumps(u))
#     tmp = _getSaveAsFilename(filename)
#     if os.path.exists(tmp):
#         os.remove(tmp)
#
# def initParams(filename, md5, seq, retry, status):
#     u = {}
#     u['filename'] = filename
#     u['md5'] = md5
#     u['seq'] = seq
#     u['retry'] = retry
#     u['status'] = status
#     return u

# 收到该消息，启动一个下载流程
# 该消息被其他线程触发
# 初始化MD5和序列号的字典后，有定时器每10s发出一个下载文件分片的请求
def downloading(url, md5):
    Utils.logDebug("->downloading() %s"%(url))
    # Utils.logHex("md5", md5)
    if url is not None and url != "":
        # param = {}
        # param['url'] = url
        # param['md5'] = md5
        thread.start_new_thread(_downloadFileFunc, (url, md5))

def restoreHostProp(url, md5):
    Utils.logDebug("->restoreHostProp() %s"%(url))
    if url is not None and url != "":
        thread.start_new_thread(_downloadConfigFileFunc, (url, md5))

def _downloadConfigFileFunc(url, md5):
    if url.lower().startswith('http') == False:
        url = 'https://'+url
    Utils.logInfo("start downloading from %s"%(url))
    # if os.path.exists(FILE_DOWNLOAD_PATH) == False:
    #     os.makedirs(FILE_DOWNLOAD_PATH)
    # filename = urllib2.unquote(url).decode('utf8').split('/')[-1]
    saveas = '/ihome/host.db.tmp'

    if sys.version_info >= (2,7,9):
        f = urllib2.urlopen(url, context=ssl._create_unverified_context())
    else:
        f = urllib2.urlopen(url)
    buf = f.read()

    with open(saveas, 'wb') as configFile:
        configFile.write(buf)
    f.close()

    tmpf = open(saveas, 'rb')
    tmp = tmpf.read()
    tmpf.close()

    # base解码
    # configf = base64.b64decode(tmp)

    """Decode base64, padding being optional.
    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.
    """
    missing_padding = 4 - len(tmp) % 4
    if missing_padding:
        tmp += b'='* missing_padding
    configf = base64.decodestring(tmp)

    # 删除文件，字典已经被清除
    if os.path.exists(saveas):
        os.remove(saveas)

    # md5_local = checkMD5(saveas)
    md5_local = hashlib.md5(configf).hexdigest()

    if md5 != md5_local:
        # 校验失败
        Utils.logInfo("File downloading MD5 check failed, %s,%s,%s"%(url, md5, md5_local))
    else:
        # 下载成功，应该通知驱动
        file_object = open('/ihome/etc/host.db', 'w')
        file_object.write(configf)
        file_object.close()

        # shutil.move(saveas, target)
        # Utils.logInfo("download file %s success, save as %s"%(saveas, target))
        # time.sleep(1)
        Utils.logInfo("Host config file restore success, reboot now...")
        time.sleep(1)
        os.system("reboot")


def _downloadFileFunc(url, md5):
    # url = param['url']
    # md5_server = param['md5']
    # url = param[0]
    # md5_server = param[1]
    # url = 'http://'+url
    if url.lower().startswith('http') == False:
        url = 'https://'+url
    Utils.logInfo("start downloading from %s"%(url))
    if os.path.exists(FILE_DOWNLOAD_PATH) == False:
        os.makedirs(FILE_DOWNLOAD_PATH)
    filename = urllib2.unquote(url).decode('utf8').split('/')[-1]
    saveas = _getSaveAsFilename(filename)

    if pyversion >= (2,7,9):
        f = urllib2.urlopen(url, context=ssl._create_unverified_context())
    else:
        f = urllib2.urlopen(url)
    buf = f.read()

    with open(saveas, 'wb') as upgradeFile:
        upgradeFile.write(buf)
    f.close()

    md5_local = checkMD5(saveas)

    if md5 != md5_local:
        # 校验失败
        Utils.logInfo("File downloading MD5 check failed, %s,%s,%s"%(url, md5, md5_local))
        # 删除文件，字典已经被清除
        if os.path.exists(saveas):
            os.remove(saveas)
    else:
        # 下载成功，应该通知驱动
        _downloadSuccess(filename)
        time.sleep(1)
        Utils.logInfo("reboot now...")
        time.sleep(1)
        os.system("reboot")

# 追加到文件中
# def append(filename, data):
#     if os.path.exists(FILE_DOWNLOAD_PATH) == False:
#         os.makedirs(FILE_DOWNLOAD_PATH)
#     f = open(_getSaveAsFilename(filename), 'wa')
#     f.write(data)
#     f.close()


def checkMD5(file):
    try:
        md5file = open(file, 'rb')
        md5 = hashlib.md5(md5file.read()).hexdigest()
        md5file.flush()
        md5file.close()
        return md5
    except:
        Utils.logException("checkMD5 exception:")
    return "None"


def _getSaveAsFilename(filename):
    return GlobalVars.FILE_DOWNLOAD_PATH + filename


def _getDownloadTargetFilename():
    return GlobalVars.FILE_DOWNLOAD_PATH + "ihome.tgz"

# 线程安全！只在main线程处理
# 收到下载文件分片的响应
# def fileDownload(fileinfoDict, arg2 = None):
#     Utils.logInfo("->fileDownload() %s"%(fileinfoDict))
#     if fileinfoDict == None:
#         return
#
#     filename = fileinfoDict["filename"]
#     seq = fileinfoDict["seq"]
#     length = fileinfoDict["length"]
#     encoded_data = fileinfoDict["data"]
#     if filename is None or seq is None or length is None or encoded_data is None:
#         Utils.logError("->fileDownload() param Error")
#         return
#
#     detailObj = DBManagerUpgrade().getUpgadeDetailByFilename(filename)
#     if detailObj is None:
#         Utils.logError("->fileDownload() not found meta record")
#         return
#     # data = base64.b64decode(encoded_data)
#     data = encoded_data
#     try:
#         localSeq = detailObj.get("seq", -2)
#         if seq != localSeq + 1:
#             #序号异常，丢弃
#             pass
#         else:
#             if length != 0:
#                 #追加到文件中
#                 append(filename, data)
#                 detailObj["seq"] = localSeq + 1
#             if length < GlobalVars.FILE_DOWNLOAD_SIZE:
#                 Utils.logInfo("->fileDownload() recv size < 50KB")
#                 #计算MD5并判断是否一致
#                 tmp = _getSaveAsFilename(filename)
#                 md5 = checkMD5(tmp)
#
#                 if md5 != detailObj.get("md5", ""):
#                     #校验失败
#                     Utils.logError("File downloading MD5 check failed, %s,%s,%s"%(filename, md5, detailObj.get("md5", "")))
#                     #删除文件，字典已经被清除
#                     if os.path.exists(tmp):
#                         os.remove(tmp)
#                     #下载完成,清除字典，不会处理后续的响应，也不会再次触发下载文件请求。
#                     DBManagerUpgrade().deleteByFilename(filename)
#
#                 else:
#                     ##下载成功，应该通知驱动
#                     _downloadSuccess(filename)
#
#                     detailObj["status"] = "done"
#                     DBManagerUpgrade().saveUpgrade(json.dumps(detailObj))
#
#                     time.sleep(1)
#                     Utils.logInfo("reboot now...")
#                     time.sleep(1)
#                     os.system("reboot")
#             else:
#                 DBManagerUpgrade().saveUpgrade(json.dumps(detailObj))
#     except:
#         Utils.logError("file download err, ")
#         ##文件可能被破坏，暂时应对措施为：重新开始
#         restartDownload(filename, detailObj.get("md5", ""))
#     return

def _downloadSuccess(filename):
    src = _getSaveAsFilename(filename)
    target = _getDownloadTargetFilename()
    if os.path.isfile(target):
        os.remove(target)
    shutil.move(src, target)
    Utils.logInfo("download file %s success, save as %s"%(src, target))

# def checkResendFileDownload():
#     Utils.logDebug("->checkResendFileDownload()")
#     detailObjs = DBManagerUpgrade().getAllUpgradeDetails()
#     if detailObjs is None:
#         return
#     for detailObj in detailObjs:
#         try:
#             if (detailObj.get("status", "") == "ongoing"):
#                 filename = detailObj.get("filename")
#                 no = detailObj.get("seq", -2)
#                 if(filename is not None and filename != ""):
#                     Utils.logInfo("publish PUB_FILE_DOWNLOAD_REQUEST %s,%s"%(filename, no))
#                     pub.sendMessage(GlobalVars.PUB_FILE_DOWNLOAD_REQUEST, fn = filename, seq = no)
#         except:
#             Utils.logError("checkResendFileDownload error ")

def stopThreadFunc(tid):
    try:
        Utils.logInfo('stop thread %d'%(tid))
        tb = threadIdInstanceDict[tid]
        if tb != None and isinstance(tb, ThreadBase) == True:
            tb.stop()
            tb.stopWatchDog()
            tb.join()
            Utils.logInfo('thread %d quit success!'%(tid))
            Utils.logInfo('restart thread %d'%(tid))
            restartThread(tid)
    except:
        Utils.logException('thread %d quit error!'%(tid))
        pass
    finally:
        Utils.logInfo('stopThread quit()')


def stopTaskHandler(tid):
    try:
        Utils.logInfo('stop task handler: %d' % tid)
        tb = threadIdInstanceDict[tid]
        if tb is not None and isinstance(tb, ThreadBase) == True:
            tb.stop()
            tb.stopWatchDog()
            tb.join()
            Utils.logInfo('thread %d quit success!' % tid)
            Utils.logInfo('thread is alive: %s' % tb.isAlive())
    except Exception as err:
        Utils.logException('stop task handler error: %s' % err)
        pass
    finally:
        pass


def restartHandler(threadname):
    if threadname == None:
        return
    Utils.logInfo("trying to restart thread: %s"%(threadname))
    tid = 0
    if threadname == "config":
        tid = TID_CONFIG_SERVER
    elif threadname == "cloud":
        tid = TID_CLOUD_CLIENT
    if tid == 0:
        return

    # cloud线程会在自己的线程调用restart_thread. 不能在自己的线程join，所以起一个新线程做这件事
    t = threading.Thread(target=stopThreadFunc, args=(tid,))
    t.setDaemon(True)
    t.start()


def checkThreadAliving():
    Utils.logDebug("->checkThreadAliving()")
    try:
        for tid in threadTimeAlivingDict.keys():
            if tid != TID_DELAY_TASK_HANDLER and tid != TID_REPEAT_TASK_HANDLER:
                '''
                定时增加所有子线程的计数
                '''
                threadTimeAlivingDict[tid] += GlobalVars.WATCHDOG_INTERVAL
                if threadTimeAlivingDict[tid] > 3*GlobalVars.WATCHDOG_INTERVAL:
                    '''有线程3个阶段都没有发送PUB_ALIVING'''
                    Utils.logCritical("Thread %s may have no response.."%(tid))
                    threadIdInstanceDict[tid].stop()
                    threadIdInstanceDict[tid].join()
                    Utils.logInfo("thread %s quit success, restart it."%(tid))
                    restartThread(tid)
    except:
        Utils.logException("checkThreadAliving error:")


def restartThread(tid):

    if tid == 0 or tid == TID_EXCEPTION_SERVER:
        hes = HostExceptionServer(TID_EXCEPTION_SERVER)
        hes.setDaemon(True)
        hes.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_EXCEPTION_SERVER] = 0
        threadIdInstanceDict[TID_EXCEPTION_SERVER] = hes
        Utils.logInfo("HostExceptionServer is running")

    if tid == 0 or tid == TID_CONFIG_SERVER:
        cfg = SocketHandlerServer(TID_CONFIG_SERVER)
        cfg.setDaemon(True)
        cfg.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_CONFIG_SERVER] = 0
        threadIdInstanceDict[TID_CONFIG_SERVER] = cfg
        Utils.logInfo("SocketHandlerServer is running")

    if tid == 0 or tid == TID_TIMER:
        timer = BoerTimer(TID_TIMER)
        timer.setDaemon(True)
        timer.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_TIMER] = 0
        threadIdInstanceDict[TID_TIMER] = timer
        Utils.logInfo("BoerTimer is running")
    
    # 接口线程放在最前面
    
    if tid == 0 or tid == TID_CONTROL_SERVER:
        controlServer = HostControlServer(TID_CONTROL_SERVER)
        controlServer.setDaemon(True)
        controlServer.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_CONTROL_SERVER] = 0
        threadIdInstanceDict[TID_CONTROL_SERVER] = controlServer
        Utils.logInfo("HostControlServer is running")

    if tid == 0 or tid == TID_CLOUD_CLIENT:
        cloudClient = HostCloudClient(TID_CLOUD_CLIENT)
        cloudClient.setDaemon(True)
        cloudClient.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_CLOUD_CLIENT] = 0
        threadIdInstanceDict[TID_CLOUD_CLIENT] = cloudClient
        Utils.logInfo("HostCloudClient Thread is running")
    
    if tid == 0 or tid == TID_BACKUP_SERVER:
        backupServer = HostBackupServer(TID_BACKUP_SERVER)
        backupServer.setDaemon(True)
        backupServer.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_BACKUP_SERVER] = 0
        threadIdInstanceDict[TID_BACKUP_SERVER] = backupServer
        Utils.logInfo("HostBackupServer is running")

    if tid == 0 or tid == TID_REPORT_SERVER:
        reportServer = HostReportServer(TID_REPORT_SERVER)
        reportServer.setDaemon(True)
        reportServer.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_REPORT_SERVER] = 0
        threadIdInstanceDict[TID_REPORT_SERVER] = reportServer
        Utils.logInfo("HostReportServer is running")

    if tid == 0 or tid == TID_ROKID_TCP_SERVER:
        rokidTCPServer = RokidBridgeServer(TID_ROKID_TCP_SERVER)
        rokidTCPServer.setDaemon(True)
        rokidTCPServer.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_ROKID_TCP_SERVER] = 0
        threadIdInstanceDict[TID_ROKID_TCP_SERVER] = rokidTCPServer
        Utils.logInfo("RokidBridgeServer is running")

    if tid == 0 or tid == TID_ROKID_SSDP_SERVER:
        rokidSSDPServer = SSDPServer(TID_ROKID_SSDP_SERVER)
        rokidSSDPServer.setDaemon(True)
        rokidSSDPServer.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_ROKID_SSDP_SERVER] = 0
        threadIdInstanceDict[TID_ROKID_SSDP_SERVER] = rokidSSDPServer
        Utils.logDebug('RokidSSDPServer is running')

    # if tid == 0 or tid == TID_REPORT_HANDLER:
    #     reportHandler = ReportHandlerServer(TID_REPORT_SERVER)
    #     reportHandler.setDaemon(True)
    #     reportHandler.start()
    #     time.sleep(1)
    #     threadTimeAlivingDict[TID_REPORT_SERVER]=0
    #     threadIdInstanceDict[TID_REPORT_SERVER] = reportHandler
    #     Utils.logInfo("ReportHandlerServer is running")

    if tid == 0 or tid == TID_DELAY_TASK_HANDLER:
        delay_task_handler = DelayTaskHandler(TID_DELAY_TASK_HANDLER)
        delay_task_handler.setDaemon(True)
        delay_task_handler.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_DELAY_TASK_HANDLER] = 0
        threadIdInstanceDict[TID_DELAY_TASK_HANDLER] = delay_task_handler
        Utils.logInfo("DelayTaskHandler is running")

    if tid == 0 or tid == TID_REPEAT_TASK_HANDLER:
        repeat_task_handler = RepeatTaskHandler(TID_REPEAT_TASK_HANDLER)
        repeat_task_handler.setDaemon(True)
        repeat_task_handler.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_REPEAT_TASK_HANDLER] = 0
        threadIdInstanceDict[TID_REPEAT_TASK_HANDLER] = repeat_task_handler
        Utils.logInfo("RepeatTaskHandler is running")

    if tid == 0 or tid == TID_LIGHTADJUST_PANNEL_MONITOR:
        lightadjust_pannel_monitor = LightAdjustPannelMonitor(TID_LIGHTADJUST_PANNEL_MONITOR)
        lightadjust_pannel_monitor.setDaemon(True)
        lightadjust_pannel_monitor.start()
        time.sleep(1)
        threadTimeAlivingDict[TID_LIGHTADJUST_PANNEL_MONITOR] = 0
        threadIdInstanceDict[TID_LIGHTADJUST_PANNEL_MONITOR] = lightadjust_pannel_monitor


MIN_DISK_USAGE_CHECKPOINT_M = 20
# 监控磁盘剩余空间, 1小时检查一次，剩余空间少于20M时需要清理磁盘空间
# lastCheckDiskUsageTime = 0


def checkDiskUsage():
    # import pdb
    # pdb.set_trace()
    # global lastCheckDiskUsageTime
    # now = int(time.time())
    # if now - lastCheckDiskUsageTime < 60*60:
    #     return
    # lastCheckDiskUsageTime = now
    Utils.logDebug("->checkDiskUsage()")
    monfs = "/"
    try:
        vfs=os.statvfs(monfs)
        available=vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/(1024*1024)
        # capacity=vfs[statvfs.F_BLOCKS]*vfs[statvfs.F_BSIZE]/(1024*1024*1024)
        Utils.logInfo("current available disk...%sM"%(available))
        if available <= MIN_DISK_USAGE_CHECKPOINT_M:
            # home下剩余不足20M，清理磁盘空间
            Utils.logInfo("Disk full... start to clean log files...")
            if os.path.isfile("../etc/host2M.log.1"):
                os.remove("../etc/host2M.log.1")
            if os.path.isfile("../etc/host2M.log.2"):
                os.remove("../etc/host2M.log.2")
            if os.path.isfile("../etc/host2M.log.3"):
                os.remove("../etc/host2M.log.3")
            if os.path.isfile("../etc/host2M.log.4"):
                os.remove("../etc/host2M.log.4")
            if os.path.isfile("../etc/host2M.log.5"):
                os.remove("../etc/host2M.log.5")
            if os.path.isfile("../etc/host.log"):
                os.remove("../etc/host.log")

            # 最后才删除实时-数据库文件
            vfs=os.statvfs(monfs)
            available=vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/(1024*1024)
            if available <= MIN_DISK_USAGE_CHECKPOINT_M:
                Utils.logInfo("Disk full... start to clean rt db files...")
                if os.path.isfile("../etc/rt.db"):
                    os.remove("../etc/rt.db")
    except:
        Utils.logException("checkDiskUsage error:")


def checkConfigDBHealthy():
    Utils.logInfo("->checkConfigDBHealthy()")
    try:
        # 检查任务数据库是否有变化
        delay_changed, repeat_changed = DBManagerTask().check_change()
        delay_switch, repeat_switch = DBManagerTask().check_switch("both")
        if (delay_changed == "delay" and delay_switch == "on") or delay_changed == "on":
            # 重启延时任务执行线程
            stopThreadFunc(TID_DELAY_TASK_HANDLER)
            DBManagerTask().reset_check()
        if (repeat_changed == "repeat" and repeat_switch == "on") or repeat_changed == "on":
            # 重启定时任务执行线程
            stopThreadFunc(TID_REPEAT_TASK_HANDLER)
            DBManagerTask().reset_check()

        if delay_changed == "off":
            # 停止延时任务执行线程
            stopTaskHandler(TID_DELAY_TASK_HANDLER)
            DBManagerTask().reset_check()
        if repeat_changed == "off":
            # 停止定时任务执行线程
            stopTaskHandler(TID_REPEAT_TASK_HANDLER)
            DBManagerTask().reset_check()

        # 数据库文件的MD5
        hostdb_md5 = 0
        if os.path.exists('../etc/host.db') == True:
            hostdb_md5 = checkMD5('../etc/host.db')
        # 备份文件的MD5
        hostdbbk_md5 = -1
        if os.path.exists('../etc/host.db.bk') == True:
            hostdbbk_md5 = checkMD5('../etc/host.db.bk')
        # 如果数据库和备份文件的MD5一样，无需继续比较
        if hostdb_md5 == hostdbbk_md5:
            return
    except Exception as err:
        Utils.logError("===>checkConfigDBHealthy() error: %s" % err)
        pass

    # 数据库文件与备份文件MD5不一致！
    # 需要备份或恢复。
    configDBHealthy = False

    try:
        DBManagerAction().checkDBHealthy()
        DBManagerDeviceProp().checkDBHealthy()
        DBManagerHostId().checkDBHealthy()
        DBManagerRoom().checkDBHealthy()
        DBManagerRoomArea().checkDBHealthy()
        DBManagerUser().checkDBHealthy()
        DBManagerLinks().checkDBHealthy()
        DBManagerTask().check_healthy()
        configDBHealthy = True
    except:
        # 出现异常？
        Utils.logException("checkConfigDBHealthy error! restore db file from last")
        configDBHealthy = False

    bkdbfile = '../etc/host.db.bk'
    curdbfile = '../etc/host.db'
    if configDBHealthy == False:
        # 恢复
        if os.path.exists(curdbfile):
            os.remove(curdbfile)

        Utils.logInfo("DB file corrupt, restore from last backup file...")
        shutil.copyfile(bkdbfile, curdbfile)
    else:
        # 备份即可
        Utils.logInfo("DB file updated...backup it.")
        shutil.copyfile('../etc/host.db', '../etc/host.db.bk')

def checkRTDBHealthy():
    Utils.logDebug("->checkRTDBHealthy()")
    rtDBHealthy = False
    #
    try:
        DBManagerAlarm().checkDBHealthy()
        DBManagerBackup().checkDBHealthy()
        DBManagerHistory().checkDBHealthy()
        DBManagerDevice().checkDBHealthy()
        # DBManagerUpgrade().checkDBHealthy()
        rtDBHealthy = True
    except:
        # 出现异常？
        Utils.logException("checkRTDBHealthy error! delete db file")
        rtDBHealthy = False

    if rtDBHealthy == False:
        # 恢复
        os.remove('../etc/rt.db')

def createDirs(dirs):
    if os.path.exists(dirs) == False:
        os.makedirs(dirs)

def createAdminIfNotExist():
    Utils.logDebug("->createAdminIfNotExist()")
    try:
        userObj = DBManagerUser().getUserDetailBy("admin")
        if(userObj != None):
            return

        userObj = {"username":"admin","password":"21232f297a57a5a743894a0e4a801fc3","nickname":"管理员"}
        DBManagerUser().saveUser(userObj)
    except:
        Utils.logException("createAdminIfNotExist() error")
    return

def sig_handler(sig, frame):
    print '!!!!!!!!!!!!!!!!!!!!!! recv signals!!!!!!!!!!!!!!!!!'

def handle_exception(exc_type, exc_value, exc_traceback):
    try:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        Utils.logUncaughtException(exc_type, exc_value, exc_traceback)
    finally:
        pass
    # Utils.logInfo('Uncaught exception type %s, value %s, trace %s'%(exc_type, exc_value, exc_traceback))

def main():
    Utils.logInfo('Restarting ihome...######## version:%s'%(str(GlobalVars.HOST_SOFT_VER)))
    sys.excepthook = handle_exception

    so = ctypes.CDLL('./libdriver.so')
    signal.signal(signal.SIGIO, sig_handler)
    so.sig()

    createDirs('/ihome/etc/cmd_files/')
    createDirs('/ihome/etc/device_cmds/')
    createDirs('/ihome/etc/upgrade/')

    createAdminIfNotExist()

    mac = Utils.get_mac_address()
    print 'host mac=',mac
    hostProp = DBManagerHostId().getHost()
    if hostProp == None:
        hostProp = DBManagerHostId().initHostProp(mac)
        if hostProp == None:
            Utils.logError("Failed to init Host property.")
            return
        Utils.logInfo("Host ID: %s"%(mac))
    else:
        preHostId = hostProp.get('hostId')
        softver = hostProp.get('softver', None)
        firmver = hostProp.get('firmver', None)

        channel_info = Utils.getPandId()
        area_info = Utils.getAreaInfo()

        pand_id = channel_info.get("pand_id", "")
        channel_no = channel_info.get("channel_no", "")
        zbsVer = channel_info.get("zbsVer", "")
        zbhVer = channel_info.get("zbhVer", "")
        if area_info:
            # 网关地区信息
            hostProp["country"] = area_info.get("contryCode", "")  # 国家码
            hostProp["city"] = area_info.get("cityCode", "")  # 城市编码，国内为电话区号
            hostProp["language"] = area_info.get("languageCode", "0")  # 0-中文；1-英文
            hostProp["developer"] = area_info.get("landDeveloperCode", "")  # 房地产开发商，如：碧桂园
            hostProp["neighbourhood"] = area_info.get("neighbourhood", "")  # 小区名，如：天玺
        #if mac != preHostId or Utils.getSoftwareVersion() != softver or Utils.getFirmwareVersion() != firmver:
        # print 'host property:', hostProp
        # Utils.logInfo("update host config: %s"%(mac))
        hostProp['hostId'] = mac
        hostProp['softver'] = Utils.getSoftwareVersion()
        hostProp['firmver'] = Utils.getFirmwareVersion()
        # 网关通道信息
        hostProp["pandId"] = pand_id
        hostProp["channelNo"] = channel_no
        # zigbee版本
        hostProp["zbsVer"] = zbsVer
        hostProp["zbhVer"] = zbhVer
        hostProp["timestamp"] = int(time.time())
        hostProp['registerHost'] = True
        DBManagerHostId().deleteByHostId(preHostId)
        DBManagerHostId().saveHostConfig(mac, hostProp.get("name"), hostProp)

    # SocketHandlerServer().start()
    # SocketHandlerServer().start()

    # 启动定时器线程
    restartThread(0)
    
    # 启动异常收集进程
    Utils.logInfo("All servers start success.")

    '''
    开始监控所有子线程，是否仍然活着
    如果收到子线程的PUB_ALIVING，则将字典里对应的计数清0
    '''
    pub.subscribe(aliving, GlobalVars.PUB_ALIVING)
    pub.subscribe(downloading, GlobalVars.PUB_FILE_UPGRADE)
    pub.subscribe(restoreHostProp, 'restore_host_prop')
    pub.subscribe(restartHandler, "restart_thread")
    # pub.subscribe(fileDownload, GlobalVars.PUB_FILE_DOWNLOAD_RESPONSE)
    
    # 启动后，是否需要判断从云端恢复配置?

    while True:
        try:
            time.sleep(GlobalVars.WATCHDOG_INTERVAL)    # 10s
            checkThreadAliving()
            # 检查是否重发文件下载请求的
            # checkResendFileDownload()
            checkDiskUsage()
            checkConfigDBHealthy()
            checkRTDBHealthy()
        except:
            Utils.logException('main exception.')

if __name__ == '__main__':
    main()
    Utils.logCritical("!!!!!!!!!!!Boer Host main application exits.")
