#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2
import json
import hashlib
import socket
import Utils

header = {'Content-Type': 'application/json'}
url = "http://api.nbhope.cn:8088/api"
app_key = "7F6F11C355BB46CCA91C606F761762FB"
secret = "ED767F9C40884BDCAF856CB6E9B61926"


# 请求服务器时间
def get_server_time():
    data = {"Cmd": "GetServerTime"}
    request = urllib2.Request(url=url, headers=header, data=json.dumps(data))
    response = urllib2.urlopen(request)
    rtn = json.loads(response.read())
    return_data = rtn.get("Data", None)
    if return_data is None:
        return None
    server_time = return_data.get("Time", None)
    return server_time


# 模拟登录
def verify_external_user(server_time, mobile_no):
    # gen_url_opener()
    sign = gen_sign(mobile_no, secret, server_time)
    Utils.logDebug("Sign: %s" % sign)
    data = {"Cmd": "VerifyExternalUser",
            "Data": {"MobileNo": mobile_no, "AppKey": app_key, "Time": server_time, "Sign": sign}}

    request = urllib2.Request(url=url, headers=header, data=json.dumps(data))
    rtn = urllib2.urlopen(request)
    if rtn is not None:
        return json.loads(rtn.read())
    return None


# 播放音乐
def music_play_ex(token, device_id, song_index):
    data = {"Cmd": "MusicPlayEx", "Data": {"DeviceId": device_id, "Index": song_index, "Token": token}}
    Utils.logDebug("data is: %s" % str(data))

    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)
    # sock.settimeout(15)
    #
    # sock.connect(("api.nbhope.cn", 9898))
    sock = gen_socket()
    # data_str = json.dumps(data)
    # print "data_str is: %s" % data_str

    # data_buf = bytearray(data_str)
    # data_buf_len = len(data_buf)
    # head_buf = [0x48, 0x4F, 0x50, 0x45, 0xFF]
    # head_buf.append(data_buf_len >> 8 & 0xFF )
    # head_buf.append(data_buf_len & 0xFF)
    # for index, buf in enumerate(head_buf):
    #     data_buf.insert(index, buf)
    data_buf = gen_data_buf(data)
    print "data_buf is:"
    print data_buf

    try:
        sock.send(data_buf)
        rtn = sock.recv(1024 * 3)
        print rtn
    except socket.timeout:
        Utils.logError("HopeMusic connect timeout in music_play_ex()...")
        rtn = None
    finally:
        sock.close()
    return rtn


# 初始化设备状态，可以获取设备当前的播放状态、播放曲目、播放进度、音效等等
def init_state(device_id, token):
    data = {"Cmd": "InitState", "Data": {"DeviceId": device_id, "Token": token}}
    Utils.logDebug("data is: %s" % str(data))

    sock = gen_socket()
    data_buf = gen_data_buf(data)

    try:
        sock.send(data_buf)
        rtn = sock.recv(1024 * 3)
        Utils.logDebug("init_state rtn: %s" % rtn)

    except socket.timeout:
        Utils.logError("HopeMusic connect timeout in init_state()...")
        rtn = None
    finally:
        sock.close()

    if rtn is None:
        return None
    else:
        return json.loads(rtn[7:])


def music_volume_set(volume, device_id, token):
    data = {"Cmd": "MusicVolumeSet", "Data": {"Volume": volume, "DeviceId": device_id, "Token": token}}
    Utils.logDebug("data is: %s" % str(data))

    sock = gen_socket()
    data_buf = gen_data_buf(data)

    try:
        sock.send(data_buf)
        rtn = sock.recv(1024 * 3)
        print rtn
    except socket.timeout:
        Utils.logError("HopeMusic connect timeout in music_volume_set()...")
        rtn = None
    finally:
        sock.close()
    return rtn


# 生成请求签名字符串(MD5字符串必须大写)
def gen_sign(mobile_no, secret, server_time):
    src = "%suser|%sSecret#%sTime" % (mobile_no, secret, server_time)
    Utils.logDebug("Sign source: %s" % src)
    md5 = hashlib.md5()
    md5.update(src)
    return md5.hexdigest().upper()


# 生成发送 TCP/IP 请求的socket
def gen_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)
    sock.settimeout(10)
    sock.connect(("api.nbhope.cn", 9898))
    return sock


# 生成 TCP/IP 请求的数据包
def gen_data_buf(data):
    data_str = json.dumps(data)
    Utils.logDebug("data_str is: %s" % data_str)

    data_buf = bytearray(data_str)
    data_buf_len = len(data_buf)
    head_buf = [0x48, 0x4F, 0x50, 0x45, 0xFF]
    head_buf.append(data_buf_len >> 8 & 0xFF)
    head_buf.append(data_buf_len & 0xFF)
    for index, buf in enumerate(head_buf):
        data_buf.insert(index, buf)

    return data_buf


def hopeMusicActivateMode(state, dev_value):
    Utils.logDebug("activate mode in hope music, state:%s, dev_value: %s" % (str(state), str(dev_value)))
    if dev_value is None:
        Utils.logError("Hope cloud account: dev_value is None")
        return
    mobile_no = dev_value.get("mobile", None)
    device_id = dev_value.get("deviceId", None)
    song_index = dev_value.get("Index", 0)
    volume = 5

    if mobile_no is None or device_id is None:
        Utils.logError("Hope cloud account: mobile no or device_id is None")
        return

    server_time = get_server_time()
    rtn_dict = verify_external_user(server_time, mobile_no)
    if rtn_dict is None:
        Utils.logError("Hope cloud account: User login failed")
        return
    data = rtn_dict.get("Data")
    if data is not None:
        hope_token = data.get("Token", None)
        if hope_token is not None:
            state_dict = init_state(device_id, hope_token)
            if state_dict:
                curr_index = state_dict.get("Data").get("Index")
                curr_state = state_dict.get("Data").get("State")  # 2是播放；1是暂停
                if curr_state and curr_index:
                    if int(state) == 1 and curr_state == 2:  # 命令是打开并且当前正在播放
                        if int(curr_index) == int(song_index):
                            return  # 当前播放曲目就是模式中设定的曲目不在重复发送
                    elif int(state) == 1 and curr_state == 1:
                        music_play_ex(hope_token, device_id, song_index)
                        music_volume_set(volume, device_id, hope_token)
                    else:  # 模式中配置的是暂停音乐
                        if int(curr_state) == 1:
                            return
                        else:
                            state_dict = init_state(device_id, hope_token)
                            curr_index = state_dict.get("Data").get("Index")
                            music_play_ex(hope_token, device_id, curr_index)  # 暂停
    else:
        Utils.logError("Hope cloud account: login data error")
    return


if __name__ == '__main__':
    # gen_url_opener()
    server_time = get_server_time()  # get server time
    print "Server time: %s" % server_time
    login_rtn = verify_external_user(server_time, "13961782689")
    print login_rtn
    hope_token = login_rtn.get("Data").get("Token", None)  # get token
    state_dict = init_state(5605, hope_token)
    curr_index = state_dict.get("Data").get("Index")
    print curr_index
    print type(curr_index)
    # music_play_ex(hope_token, 5317, 11)  # play music
    # music_volume_set(3, 5317, hope_token)  # set volume
