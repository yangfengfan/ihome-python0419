## -*- coding: utf-8 -*-


from SocketThreadBase import *
import GlobalVars
import Utils
import json
from PacketParser import *
from pubsub import pub
from DBManagerAlarm import *
from DBManagerDevice import *
from BoerCloud import *
from SocketHandlerServer import *
# import smtplib
# from email.mime.text import MIMEText
import urllib2
import os
import shutil
import ssl
from sys import version_info as pyversion

class HostExceptionServer(ThreadBase):
    __instant = None
    __lock = threading.Lock()
    __exceptLock = threading.Lock()

    #singleton
    def __new__(self, arg):
        Utils.logDebug("__new__")
        if(HostExceptionServer.__instant==None):
            HostExceptionServer.__lock.acquire();
            try:
                if(HostExceptionServer.__instant==None):
                    Utils.logDebug("new HostExceptionServer singleton instance.")
                    HostExceptionServer.__instant = ThreadBase.__new__(self);
            finally:
                HostExceptionServer.__lock.release()
        return HostExceptionServer.__instant

    def __init__(self, threadId):
        ThreadBase.__init__(self, threadId, "HostExceptionServer")
        self.hostId = None
        self.firmver = None
        self.softver = None
        self.exceptionArr = []
        self.cloudConnected = False

    def run(self):
        self.init()     #call super.init()
        # self.subscribe()
        #心跳状态（网络状态）
        pub.subscribe(self.heartbeatHandler, GlobalVars.PUB_HEARBEAT_STATUS)

        Utils.logInfo("HostExceptionServer is running.")

        # self.upload()

        while not self.stopped:
            try:
                time.sleep(10)
                if self.cloudConnected is False:
                    pass
                else:
                    self.upload()
                    time.sleep(24*60*60)
                # self.handleException()
            except:
                Utils.logException('HostExceptionServer exception.')

    def checkMD5(self, file):
        try:
            md5file = open(file,'rb')
            md5 = hashlib.md5(md5file.read()).hexdigest()
            md5file.flush()
            md5file.close()
            return md5
        except:
            pass
        return "None"

    def upload(self):
        if self.cloudConnected is False:
            return
        try:
            if self.hostId == None:
                self.hostId = DBManagerHostId().getHostId()
            if self.hostId == None:
                return

            # if self.firmver == None or self.softver == None:
            #     hostProp = DBManagerHostId().getHost()
            #     self.firmver = str(hostProp.get("firmver", 0))
            #     self.softver = str(hostProp.get("softver", 0))

            url = "https://" + GlobalVars.SERVER_URL + ":8080/logs/report?hostId='" + self.hostId + "'"
            logfile = '/ihome/etc/host2M.log'
            # files = {'file': open(path, 'rb')}
            # r = requests.post(url, files=files)
            # print r.url,r.text

            if os.path.exists(logfile) == False:
                return
            uploadedfile = '/ihome_exception.log'
            if os.path.exists(uploadedfile) == True:
                logMd5  = self.checkMD5(logfile)
                lastMd5 = self.checkMD5(uploadedfile)
                if logMd5 == lastMd5:
                    return

            Utils.logInfo('++++++++++++++++start uploading exception file+++++++++++++++++++++++')
            # image_path = logfile
            # # url = 'http://outofmemory.cn/test-url/'
            # length = os.path.getsize(image_path)
            # png_data = open(image_path, "rb")
            # request = urllib2.Request(url, data=png_data)
            # request.add_header('Cache-Control', 'no-cache')
            # request.add_header('Content-Length', '%d' % length)
            # request.add_header('Content-Type', 'application/octet-stream')
            # res = urllib2.urlopen(request).read().strip()
            boundary = '----------%s' % hex(int(time.time() * 1000))
            data = []
            data.append('--%s' % boundary)

            fr=open(logfile,'rb')
            data.append('Content-Disposition: form-data; name="%s"; filename="host2M.log"' % 'log')
            data.append('Content-Type: %s\r\n' % 'application/octet-stream')
            data.append(fr.read())
            fr.close()
            data.append('--%s--\r\n' % boundary)

            # http_url='http://remotserver.com/page.php'
            http_body='\r\n'.join(data)

            try:
                #buld http request
                req=urllib2.Request(url, data=http_body)
                #header
                req.add_header('Content-Type', 'multipart/form-data; boundary=%s' % boundary)
                req.add_header('User-Agent', 'Mozilla/5.0')
                # req.add_header('Referer','http://remotserver.com/')
                #post data to server
                if pyversion >= (2,7,9):
                    resp = urllib2.urlopen(req, context=ssl._create_unverified_context(), timeout=5)
                else:
                    resp = urllib2.urlopen(req, timeout=5)
                #get response
                resp.read()
                Utils.logInfo('====upload exception file success!======IP：%s'%(GlobalVars.SERVER_URL))

                ##上传成功：
                shutil.copyfile(logfile, uploadedfile)
            except:
                Utils.logError('upload exception file error.IP：%s. reboot...'%(GlobalVars.SERVER_URL))
                if os.path.exists(logfile):
                    os.remove(logfile)
                time.sleep(1)
                os.system("cd /ihome")
                os.system("sh ihome.sh")
        except:
            Utils.logError('Error when uploading exception log file.IP：%s'%(GlobalVars.SERVER_URL))


    # def subscribe(self):
    #     try:
    #         pub.subscribe(self.exceptionHandler, 'publish_host_exception')
    #     finally:
    #         pass

    def heartbeatHandler(self, status, arg2=None): #status: "up", "down"
        Utils.logDebug("->heartbeatHandler() %s"%(status))
        if status == "up":
            if(self.cloudConnected != True):
                self.cloudConnected = True
                # self.resendSocketCommand()
        else:
            self.cloudConnected = False

    def exceptionHandler(self, trace, arg2=None):
        try:
            if self.hostId == None:
                self.hostId = DBManagerHostId().getHostId()
            if self.firmver == None or self.softver == None:
                hostProp = DBManagerHostId().getHost()
                self.firmver = str(hostProp.get("firmver", 0))
                self.softver = str(hostProp.get("softver", 0))
        finally:
            pass

        if self.hostId == None or trace == None:
            return
        traceDict = {}
        traceDict['time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        traceDict['traceback'] = trace
        Utils.logInfo('capture a new exception...')
        HostExceptionServer.__exceptLock.acquire();
        try:
            self.exceptionArr.append(traceDict)
        finally:
            HostExceptionServer.__exceptLock.release()

    def handleException(self):
        HostExceptionServer.__exceptLock.acquire()
        try:
            if len(self.exceptionArr) == 0:
                return

            buf = '\r\n###########################\r\n'
            for item in self.exceptionArr:
                buf += '\r\n\r\n'
                buf += "host: " + self.hostId
                buf += '\r\n'
                buf += "soft version: " + self.softver
                buf += '\r\n'
                buf += "firm version: " + self.firmver
                buf += '\r\n'
                buf += "time: " + item.get('time', "unknown exception time")
                buf += '\r\n'
                buf += "traceback:"
                buf += '\r\n'
                buf += item.get('traceback', "None")

            ## send buf to ...
            success = False
            # success = self.sendByEmail(buf)
            if success == True:
                del self.exceptionArr
                self.exceptionArr = []
        finally:
            HostExceptionServer.__exceptLock.release()

    # def sendByEmail(self, content):
    #
    #     # mailto_list=['boersmart@qq.com']
    #     to_list=['weifang.xiao@boerpower.com']
    #     mail_host="smtp.boerpower.com"  #设置服务器
    #     mail_user="weifang.xiao@boerpower.com"    #用户名
    #     mail_pass=""   #口令
    #     mail_postfix="boerpower.com"  #发件箱的后缀
    #
    #     me="hello"+"<"+mail_user+"@"+mail_postfix+">"
    #     msg = MIMEText(content,_subtype='plain',_charset='gb2312')
    #     msg['Subject'] = 'logs from ' + self.hostId
    #     msg['From'] = me
    #     msg['To'] = ";".join(to_list)
    #     try:
    #         server = smtplib.SMTP()
    #         server.connect(mail_host)
    #         server.login(mail_user,mail_pass)
    #         server.sendmail(me, to_list, msg.as_string())
    #         server.close()
    #         return True
    #     except:
    #         return False

if __name__ == '__main__':
    hes = HostExceptionServer(110)
    hes.sendByEmail('test send by email')