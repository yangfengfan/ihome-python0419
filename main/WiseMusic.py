#!/usr/bin/env python
# -*- coding: utf-8 -*-

from struct import pack, unpack, Struct
import socket
import traceback
import json
import time
import Utils


TCPCMD_PALPITANT = 0xC0		# 心跳包，服务端收到对方的心跳包返回机器型号(如BM209)
TCPCMD_PLAY_PAUSE = 0xC1    # 音乐播放/暂停
TCPCMD_PRE = 0xC2           # 音乐上一首
TCPCMD_NEXT = 0xC3          # 音乐下一首
TCPCMD_LOOPMODE = 0xC4      # 音乐循环模式
TCPCMD_VOL_CTRL = 0xC5      # 音乐播放声音控制
TCPCMD_PLAYSTATUS = 0XC6    # 音乐播放状态
TCPCMD_SHUTDOWN = 0XC7      # 关机
TCPCMD_DURATION = 0xC8      # 获取当前播放歌曲时长
TCPCMD_POSITION = 0xC9      # 获取进度位置
TCPCMD_SONGNAME = 0xCA      # 获取当前播放歌曲
TCPCMD_ROOMNAME = 0xCB      # 返回房间名号，用"::"分隔
TCPCMD_PROGRESS = 0xCC      # 设置进度条
TCPCMD_MEDIATYPE = 0xCD     # 1音乐，2电台, 3：视频,4：图片
TCPCMD_MEDIA_LIST_SIZE = 0xCE   # 返回歌曲总数
TCPCMD_GET_MEDIA_LIST = 0xCF    # 每次取一条，返回歌曲名和播放时长
TCPCMD_PLAY_POS = 0xD0          # 播放列表中的某一位置的歌曲
TCPCMD_ARTIST = 0xD1            # 获取当前歌曲艺术家，仅限音频
TCPCMD_VOL_SET = 0xD2           # 设置音量
TCPCMD_VOL_GET = 0xD3           # 获取音量
TCPCMD_UPDATE_ROOMNAME = 0xD4   # 修改房间名
TCPCMD_UPDATE_ROOMNO = 0xD5     # 修改房间号
TCPCMD_SIWTCH_SOUND_SOURCE = 0xD6   # 获取和设置音源
TCPCMD_GET_TIMER_SIZE = 0xD7        # 获取定时器列表总数，不带参数
TCPCMD_GET_TIMER_DATA = 0xD8        # 获取定时器数据
TCPCMD_SET_TIMER_DATA = 0xD9        # 设置定时器
TCPCMD_GET_TIMER_SWITCH = 0xDA      # 获取定时器开关
TCPCMD_SET_TIMER_SWITCH = 0xDB      # 设置定时器开关
TCPCMD_GET_SUBAREA_CONTROL = 0xDC   # 获取分区控制，仅限机型BM209
TCPCMD_SET_SUBAREA_CONTROL = 0xDD   # 设置分区控制，仅限机型BM209
TCPCMD_GET_EQ = 0xDE                # 不带参数获取当前音效
TCPCMD_SET_EQ = 0xDF                # 设置音效
TCPCMD_GET_EQ_SWITCH = 0xE0         # 获取音效开关
TCPCMD_SET_EQ_SWITCH = 0xE1         # 带参数0或1设置音效开关
TCPCMD_SET_MUTE = 0xE3              # 静音开关

WISE_PORT = 11000   # 华尔斯背景音乐UDP端口(为家卫士定制)


# 发送发现设备的广播
def start_broadcast():
    sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock_udp.bind(('', WISE_PORT))
    sock_udp.settimeout(5)  # 设置5秒超时
    rtn_msg, address = ('', None)
    model_type = ''

    body_buffer = []
    data = generate_msg_buffer(TCPCMD_PALPITANT, body_buffer)
    try:
        sock_udp.sendto(data, ("<broadcast>", WISE_PORT))
        while len(rtn_msg) <= len(data):
            rtn_msg, address = sock_udp.recvfrom(1024 * 5)

        rtn_info = rtn_msg[5: -5]
        model_type = unpack("!%ds" % len(rtn_info), rtn_info)
        Utils.logInfo("Received msg from (%s:%d)" % address)
    except socket.timeout as e:
        Utils.logError("socket time out, send heartbeat again")
        try:
            sock_udp.sendto(data, ("<broadcast>", WISE_PORT))
            while len(rtn_msg) <= len(data):
                rtn_msg, address = sock_udp.recvfrom(1024 * 5)

            rtn_info = rtn_msg[5: -5]
            model_type = unpack("!%ds" % len(rtn_info), rtn_info)
            Utils.logInfo("Received msg from (%s:%d)" % address)
        except socket.timeout:
            Utils.logError("Wise device connect timeout")
    except Exception as e:
        Utils.logError("Wise Music Start broadcast failed: %s" % e.message)
        # print traceback.format_exc()

    return sock_udp, rtn_msg, address, model_type


# 构建报文  protocolNo： 协议号； bodyBuffer：报文体数据内容部分
def generate_msg_buffer(protocolNo, bodyBuffer, frameNo=0x01):
    try:
        body_length = len(bodyBuffer)
        package_length = 4 + body_length
        fmt_str = "!%dB" % body_length
        if protocolNo in [TCPCMD_LOOPMODE, TCPCMD_VOL_CTRL] :  # 这些协议号的参数都是字符形式
            fmt_str = "!%ds" % body_length
        elif protocolNo in [TCPCMD_PROGRESS, TCPCMD_MEDIATYPE]:  # 这些协议号的参数都是整数类型，4个字节
            fmt_str = "!I"
        elif protocolNo in [TCPCMD_VOL_SET, TCPCMD_GET_MEDIA_LIST, TCPCMD_PLAY_POS, TCPCMD_SET_EQ]:  # 这些协议号的参数都是整数类型，小端序
            fmt_str = "<I"

        header_buffer = pack("!2BHB", 0x7E, 0x7E, package_length, protocolNo)
        end_buffer = pack("!3B", frameNo, 0x0D, 0x0A)
        s = Struct(fmt_str)
        body_buffer = s.pack(*tuple(bodyBuffer))

        return header_buffer + body_buffer + end_buffer
    except Exception as e:
        Utils.logError("Error!!! message: %s" % e.message)
    return None


# 暂停播放
def play_and_pause(sock=None, model_type='', address=None):
    if sock is None:
        sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_PLAY_PAUSE, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)

    if sock is not None:
        sock.close()

    return rtn_msg  # 7E 7E 00 04 C1 01 0D 0A 00 00


# 上一首
def play_pre():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_PRE, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)

    if sock is not None:
        sock.close()

    return rtn_msg  # 7E 7E 00 04 C2 01 0D 0A 00 00


# 下一首
def play_next():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_NEXT, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)

    if sock is not None:
        sock.close()

    return rtn_msg  # 7E 7E 00 04 C3 01 0D 0A 00 00


# 音乐循环模式设置
# mode_no: 0-获取当前播放模式；1-切换当前播放模式
# 服务端返回中：-1-error；0-normal；1-repeat all；2-repeat one；3-shuffle，小端序
def set_loop_mode(mode_no):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_LOOPMODE, [mode_no])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 C4 01 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    mode = unpack("<I", rtn_msg[5: -5])[0]
    return mode


# 音量控制
# vol_cmd: '0'-音量减；'1'-音量加，返回内容是小端序
def volume_control(vol_cmd):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_VOL_CTRL, [vol_cmd])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 C5 00 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    return rtn_code


# 模式中触发背景音乐暂停
def pause_in_mode(no_return_sock=True):
    sock, model_type, address, playState = play_status(no_return_sock)
    if int(playState) == 1:
        play_and_pause(sock, model_type, address)

# 获取播放状态
# 服务端返回：-1-no file; 0-invalid; 1-play; 2-pause; 3-pause; 4-paresync; 5-parecomplete; 6-complete。小端序
def play_status(no_return_sock=True):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_PLAYSTATUS, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 C6 01 00 00 00 01 0D 0A 00 00

    if sock is not None and no_return_sock:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    if no_return_sock:
        return rtn_code
    else:
        return sock, model_type, address, rtn_code


# 获取当前播放歌曲时长
# 返回的是毫秒级的时间数字，小端序
def get_duration():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_DURATION, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 0C C8 3D F6 06 00 00 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    duration = unpack("<q", rtn_msg[5: -5])[0]
    return duration


# 获取当亲播放进度，返回的是毫秒级的时间数字，返回值是小端序
def get_play_position():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_POSITION, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 0C C9 47 76 00 00 00 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    position = unpack("<q", rtn_msg[5: -5])[0]
    return position


# 获取当前播放的歌曲名
def get_song_name():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_SONGNAME, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 0A CA E6 BC 94 E5 91 98 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    name_buffer = rtn_msg[5: -5]
    song_name = unpack("!%ds" % len(name_buffer), name_buffer)[0]
    return song_name


# 获取房间名称， 房间名和房间号用"::"分隔
# 暂时不用，不加解析过程
def get_room_name():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_ROOMNAME, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)
    if sock is not None:
        sock.close()
    return rtn_msg  # 7E 7E 00 0D CB 72 6F 6F 6D 3A 3A 35 37 34 01 0D 0A 00 00


# 设置进度条，参数为毫秒级别的时间书，服务端返回时小端序
def set_progress(milli_time):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_PROGRESS, [milli_time])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 CC 00 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    return rtn_code


# 设置媒体类型
# media_mode: 1-音乐；2-电台;整数类型，服务端返回值是小端序
def set_media_mode(media_mode):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_MEDIATYPE, [media_mode])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 CD 00 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    return rtn_code


# 获取之前设置的媒体类型(歌曲列表内曲目总数)，服务端返回值是小端序
def get_media_list_size(no_return_sock=True):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_MEDIA_LIST_SIZE, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 CE 0B 00 00 00 01 0D 0A 00 00

    list_sum = unpack("<I", rtn_msg[5: -5])[0]
    if no_return_sock:
        if sock is not None:
            sock.close()
        return list_sum
    else:
        return sock, address, list_sum


# 获取媒体列表，每次获取一条，根据媒体列表曲目总数获取，歌曲信息以 "::"分隔
# index: 起始索引；list_size: 终止索引
# 返回的一条信息如下：
# 7E 7E 00 A3 CF 30 3A 3A 42 61 6E 64 61 72 69 2D E5 AE 89 E5 A6 AE E7 9A 84 E4 BB 99 E5 A2 83 3A 3A 32 30 36 37 36 30 3A 3A 3C 75 6E 6B 6E 6F 77 6E 3E 3A 3A 2F 6D 6E 74 2F 69 6E 74 65 72 6E 61 6C 5F 73 64 2F 4D 75 73 69 63 2F 32 30 36 5F 32 30 37 5F 32 30 35 5F 32 30 39 57 41 56 E6 AD 8C E6 9B B2 E5 86 85 E5 AD 98 2F 32 30 36 5F 32 30 37 5F 32 30 35 5F 32 30 39 57 41 56 E6 AD 8C E6 9B B2 E5 86 85 E5 AD 98 2F 42 61 6E 64 61 72 69 2D E5 AE 89 E5 A6 AE E7 9A 84 E4 BB 99 E5 A2 83 2E 77 61 76 01 0D 0A 00 00
def get_media_list(index=0, list_size=None):
    rtn_list = []
    if list_size is None:
        sock, address, list_size = get_media_list_size(False)  # 这里拿到的list_size是歌曲列表的长度值，最大索引值需要减去1
        list_size -= 1
    else:
        sock, rtn, address, model_type = start_broadcast()
        if len(model_type) == 0:
            return None

    while index <= list_size:  # APP会把起始索引和终止索引发过来
        data_buff = generate_msg_buffer(TCPCMD_GET_MEDIA_LIST, [index])
        sock.sendto(data_buff, (address[0], WISE_PORT))
        rtn_msg, addr = sock.recvfrom(1024 * 5)
        rtn_list.append(rtn_msg)
        index += 1

    if sock is not None:
        sock.close()

    # response = [parse_song_list(song_info) for song_info in  rtn_list]
    response = []
    for song_info in rtn_list:
        song_dict = parse_song_list(song_info)
        if song_dict:
            response.append(song_dict)
    return response


# 解析歌曲列表信息，返回一个包含歌曲索引、歌曲名、播放时长、演唱者、文件名等信息的字典
def parse_song_list(song_buffer):
    song_src = song_buffer[5: -5]
    song_info = unpack("<%ds" % len(song_src), song_src)[0]

    try:
        index, name, duration, artist, file_name = tuple(song_info.split("::"))
        song_dict = {"index": int(index), "title": name, "duration": long(duration), "artist": artist,
                     "file_name": file_name}
        return song_dict
    except:
        pass  # 歌曲信息解析后不是5项数据，过滤掉
    return None


# 指定播放歌曲，服务端返回值是小端序
def play_pos(song_index):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_PLAY_POS, [song_index])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 D0 00 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    return rtn_code


def play_and_set_vol(song_index, volume_num):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    # play music
    data_buff = generate_msg_buffer(TCPCMD_PLAY_POS, [song_index])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 D0 00 00 00 00 01 0D 0A 00 00

    # set volume
    if volume_num < 0 or volume_num > 15:
        volume_num = 6
    data_buff = generate_msg_buffer(TCPCMD_VOL_SET, [volume_num])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)

    if sock is not None:
        sock.close()


# 获取当前歌曲艺术家信息
def get_artist():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_ARTIST, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 0D D1 3C 75 6E 6B 6E 6F 77 6E 3E 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    artist_info = rtn_msg[5: -5]
    artist_name = unpack("<%ds" % len(artist_info), artist_info)[0]
    return artist_name


# 设定音量，音量取值范围 0～15，整数类型，4个字节，服务端返回值是小端序
def set_volume(volume_num):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    if volume_num < 0 or volume_num > 15:
        volume_num = 6
    data_buff = generate_msg_buffer(TCPCMD_VOL_SET, [volume_num])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)

    if sock is not None:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    return rtn_code  # 7E 7E 00 08 D2 03 00 00 00 01 0D 0A 00 00


# 获取当前音量，返回的音量值是小端序
def get_volume():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_VOL_GET, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 D3 03 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    rtn_code = unpack("<I", rtn_msg[5: -5])[0]
    return rtn_code


# 获取当前音效，返回的是字符类型的0~7，整数类型
def get_eq():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_GET_EQ, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 DE 01 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    eq_buffer = rtn_msg[5: -5]
    eq_code = unpack("<I", eq_buffer)[0]
    return str(eq_code)


# 设置音效
# eq_code：0-普通；1-摇滚；2-流行；3-舞曲；4-嘻哈；5-古典；6-超重低音；7-人声，字符类型
def set_eq(eq_code):
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_SET_EQ, [eq_code])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)  # 7E 7E 00 08 DF 01 00 00 00 01 0D 0A 00 00

    if sock is not None:
        sock.close()

    eq_buffer = rtn_msg[5: -5]
    eq_rtn = unpack("<I", eq_buffer)[0]
    return eq_rtn


# 静音开关
def set_mute():
    sock, rtn, address, model_type = start_broadcast()
    if len(model_type) == 0:
        return None

    data_buff = generate_msg_buffer(TCPCMD_SET_MUTE, [])
    sock.sendto(data_buff, (address[0], WISE_PORT))
    rtn_msg, addr = sock.recvfrom(1024 * 5)

    if sock is not None:
        sock.close()
    return rtn_msg  # 7E 7E 00 04 E3 01 0D 0A 00 00


# 解析返回内容
# def parse_data(msg_buffer):
#     protocol_no = unpack("!B", msg_buffer[4])[0]
#     data_len = unpack("!H", msg_buffer[2: 4])[0]
#     data_len -= 4
#     if data_len == 0:
#         pass  # 信息内容为空时如何处理
#         return
#     data_body = msg_buffer[5, 5 + data_len]
#     print_hex('rtn msg data body: ', data_body)


def print_hex(tip, buffer_info):
    disp = ""
    for onebyte in buffer_info:
        onestr = unpack("B", onebyte)
        disp = disp + " %02X" % (onestr)
    print tip + disp


if __name__ == '__main__':
    # sock, rtn, address = start_broadcast()
    # data_buff = generate_msg_buffer(TCPCMD_PLAY_PAUSE, [])
    # sock.sendto(data_buff, (address[0], WISE_PORT))
    # rtn_msg, addr = sock.recvfrom(1024 * 5)
    # print_hex("rsponse: ", rtn_msg)
    # parse_data(rtn_msg)

    # play_and_pause()
    # rtn_msg = set_loop_mode('0')
    rtn_msg = set_eq(0)
    print rtn_msg
    rtn_msg = get_eq()
    # print_hex("rtn_msg: ", rtn_msg)
    print rtn_msg
