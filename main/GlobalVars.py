# -*- coding: utf-8 -*-

import datetime
import logging 
import struct
import traceback
from logging.handlers import RotatingFileHandler

# 软件版本号！
HOST_SOFT_VER = 240
# 服务器IP地址
SERVER_URL = 'api.boericloud.com'

# 订阅发布消息名称
PUB_CLOUD_HEARTBEAT = "publish_cloud_heartbeat"           # 往云端发心跳消息
PUB_SOFT_WATCHDOG   = "publish_software_watchdog"         # 往各子线程发watchdog消息
PUB_ALIVING         = "publish_Iam_aliving"               # 子线程定时发布消息’我还活着‘’
PUB_CONTROL_DEVICE  = "publish_control_device"            # 设备控制类指令
PUB_START_PANNEL_LISTEN = "start_pannel_listen"           # 启动调光控制面板监控
PUB_STOP_PANNEL_LISTEN = "stop_pannel_listen"             # 停止调光控制面板监控
# PUB_ALARM           = "publish_alarm"                   # 设备告警类指令
# PUB_SYS_CONFIG      = "publish_sys_config"              # 系统配置类

PUB_SEND_RTDATA     = "publish_send_rtdata"               # 实时数据、告警的发送
# PUB_SEND_CMDRESPONSE     = "publish_send_cmd_response"  # 实时数据、告警的发送
PUB_BACKUP_START            = "publish_backup_start"      # 定时触发开始备份
PUB_SAVE_SOCKET_CMD         = "publish_save_socket"       # socket命令存入备份表

# 备份完成。接口线程按收到这个消息，才认为可以向云端发送实时数据。
# PUB_BACKUP_COMPLETE         = "publish_backup_complete"
PUB_RESEND_SOCKET           = "publish_resend_socket"     # 重发socket命令
PUB_BACKUP_ENERGY           = "publish_backup_energy"     # 把备份线程的水电煤发送给云端
PUB_BACKUP_SUCCESS          = "publish_backup_success"    # 备份包成功发送到云端

PUB_HEARBEAT_STATUS         = "publish_hearteat_status"   # 心跳丢失或恢复

PUB_FILE_UPGRADE            = "publish_file_upgrade"      # 软件升级
# PUB_FILE_DOWNLOAD_REQUEST   = "publish_file_download_request"   # 文件下载请求
# PUB_FILE_DOWNLOAD_RESPONSE  = "publish_file_download_response"  # 文件下载响应

WATCHDOG_INTERVAL  = 10  # 10秒钟进行一次watchdog检验
HEARTBEAT_INTERVAL = 20  # 20秒的心跳间隔

FILE_DOWNLOAD_PATH = "../etc/upgrade/"
FIRMWARE_VER_FILE  = "/smart_home/ver.log"
PAND_ID_FILE       = "/smart_home/pand_ID"  # 用于读取网关主机的pand_id，225版本暂未使用
AREA_CODE_FILE     = "/etc/GWID"  # 读取地区码

MAX_SOCKET_PACKET_SIZE = 1024*20

# 网络断开时是否启用备份功能
# False:不启用，网络断开时状态数据，水电煤数据，插座数据等丢失，网络连接时上报实时数据。
# True:启用，网络断开时，把所有数据存储在本地数据，连接时将所有数据发送给云端。本地数据库压力和瞬时云端压力都很大。
enableBackupWhenLinkdown = True

virtualDevAddr_Elec           = "g-elec-dispvalue"
virtualDevAddr_Gas            = "g-gas-dispvalue"
virtualDevAddr_Water          = "g-water-dispvalue"

TYPE_CMD_UPGRADE_NOTIFICATION = 1000
TYPE_CMD_MODIFY_HOST_CONFIG = 1001

TYPE_CMD_READ_HOST_CONFIG = 1002
TYPE_CMD_READ_ALARMS = 1003
TYPE_CMD_CONFIRM_ALARMS = 1004
TYPE_CMD_CONTROL_DEVICE = 1005
TYPE_CMD_REMOVE_DEVICE = 1006
TYPE_CMD_UPDATE_DEVICE = 1007
TYPE_CMD_QUERY_DEVICES = 1008
TYPE_CMD_QUERY_DEVICES_STATUS = 1009
TYPE_CMD_DISMISS_DEVICE = 1010
TYPE_CMD_QUERY_ROOM_PROP = 1016
TYPE_CMD_UPDATE_ROOM_PROP = 1017
TYPE_CMD_REMOVE_ROOM_PROP = 1018

TYPE_CMD_MODIFY_USER_CONFIG = 1019  # 修改用户属性
TYPE_CMD_MODIFY_HOSTNAME_CONFIG = 1020  # 修改网关名称
TYPE_CMD_VERIFY_USER_PWD = 1021  # 验证用户名密码

TYPE_CMD_QUERY_AREA_PROP = 1026
TYPE_CMD_UPDATE_AREA_PROP = 1027
TYPE_CMD_REMOVE_AREA_PROP = 1028

TYPE_CMD_MODIFY_MODE_NAME = 1029  # 修改模式名称

TYPE_CMD_QUERY_ROOM_MODE  = 1030
TYPE_CMD_UPDATE_ROOM_MODE = 1031
TYPE_CMD_REMOVE_ROOM_MODE = 1032
TYPE_CMD_ACTIVE_ROOM_MODE = 1033
TYPE_CMD_REMOVE_GLOBAL_MODE = 1034

TYPE_CMD_QUERY_LINK_ACTION  = 1035
TYPE_CMD_UPDATE_LINK_ACTION = 1036
TYPE_CMD_QUERY_GLOBAL_DATA  = 1037

TYPE_CMD_QUERY_GLOBAL_MODE  = 1038  # 查询全局模式

# 关联设备
TYPE_CMD_LINK_DEVICES = 1040
TYPE_CMD_QUERY_DEVICES_LINKS = 1041

# 备份、恢复网关属性
TYPE_CMD_BACKUP_HOST_PROP2 = 1042
TYPE_CMD_RESTORE_HOST_PROP = 1043

# 中控配置命令
TYPE_CMD_HCG_CONFIG        = 1044
TYPE_CMD_HCG_QUERY_CONFIG  = 1046
TYPE_CMD_HCG_DELETE_CONFIG = 1047

# 云账号验证网关安全码
TYPE_CMD_VERIFY_ADMIN_PWD = 1045

# 查询水电表地址
TYPE_CMD_QUERY_METER_ADDRS = 1051
# 修改水电表名称
TYPE_CMD_MODIFY_METER_NAME = 1052

# 查询某一设备的属性
TYPE_CMD_QUERY_ONE_DEVICE_PROP = 1053

# 读取所有设备的属性及状态的新增接口
TYPE_CMD_READ_ALL_DEVICE = 1054

# 设置地暖定时的接口
TYPE_CMD_SET_FLOOR_HEATING_TIME_TASK = 1055
# 打开或者关闭地暖定时
TYPE_CMD_SWITCH_FLOOR_HEATING_TIME_TASK = 1056

# 云端已经登陆后的直连登陆，保存及更新用户账户信息
TYPE_CMD_AUTHORIZED_LOGIN = 1057
# 普通直连登陆
TYPE_CMD_NORMAL_LOGIN = 1058
# 保存用户个人信息
TYPE_CMD_SAVE_USER_INFO = 1059
# 退出登录
TYPE_CMD_LOGOUT = 1060
# 删除网关上的用户
TYPE_CMD_DELETE_USER = 1061

# 设置定时任务
TYPE_CMD_SET_TIME_TASK = 1062
# 开启或者关闭定时任务
TYPE_CMD_SWITCH_TIME_TASK = 1063
# 查询定时任务是否开启
TYPE_CMD_QUERY_TASK_DETAIL = 1064

# 获取系统时间
TYPE_CMD_GET_SYS_TIME = 1065

# 查询全部模式，包括全局模式和房间模式
TYPE_CMD_GET_ALL_MODES = 1066

# 批量扫描时APP查询设备信息列表
TYPE_CMD_QUERY_BATCH_DEVICE = 1067

# 批量扫描后提交保存设备列表
TYPE_CMD_SAVE_BATCH_DEVICE = 1068

# APP发送开始扫描请求
TYPE_CMD_START_SCAN_BATCH = 1069

# APP发送停止扫描
TYPE_CMD_STOP_SCAN_BATCH = 1070


def get_cmd(request_url):
    if not request_url:
        return None
    if request_url == "/device/link":
        return TYPE_CMD_LINK_DEVICES
    elif request_url == "/device/querylink":
        return TYPE_CMD_QUERY_DEVICES_LINKS
    elif request_url == "/device/querylink":
        return TYPE_CMD_QUERY_DEVICES_LINKS
    elif request_url == "/device/cmd":
        return TYPE_CMD_CONTROL_DEVICE
    elif request_url == "/device/remove":
        return TYPE_CMD_REMOVE_DEVICE
    elif request_url == "/device/dismiss":
        return TYPE_CMD_DISMISS_DEVICE
    elif request_url == "/device/updateprop":
        return TYPE_CMD_UPDATE_DEVICE
    elif request_url == "/device/properties":
        return TYPE_CMD_QUERY_DEVICES
    elif request_url == "/device/queryOneProp":
        return TYPE_CMD_QUERY_ONE_DEVICE_PROP
    elif request_url == "/device/configHgc":
        return TYPE_CMD_HCG_CONFIG
    elif request_url == "/device/deleteHgcConfig":
        return TYPE_CMD_HCG_DELETE_CONFIG
    elif request_url == "/device/queryHgcConfig":
        return TYPE_CMD_HCG_QUERY_CONFIG
    elif request_url == "/device/modifyMeterName":
        return TYPE_CMD_MODIFY_METER_NAME
    elif request_url == "/device/setFloorHeatingTimeTask":
        return TYPE_CMD_SET_FLOOR_HEATING_TIME_TASK
    elif request_url == "/device/switchFloorHeatingTimeTask":
        return TYPE_CMD_SWITCH_FLOOR_HEATING_TIME_TASK

    elif request_url == "/host/showproperty":
        return TYPE_CMD_READ_HOST_CONFIG
    elif request_url == "/host/modifyproperty":
        return TYPE_CMD_MODIFY_HOST_CONFIG
    elif request_url == "/host/modifyHostName":
        return TYPE_CMD_MODIFY_HOSTNAME_CONFIG

    elif request_url == "/plan/show":
        return TYPE_CMD_QUERY_LINK_ACTION
    elif request_url == "/plan/update":
        return TYPE_CMD_UPDATE_LINK_ACTION
    elif request_url == "/plan/activate":
        return TYPE_CMD_ACTIVE_ROOM_MODE
    elif request_url == "/plan/modifyModeName":
        return TYPE_CMD_MODIFY_MODE_NAME

    elif request_url == "/room/remove":
        return TYPE_CMD_REMOVE_ROOM_PROP
    elif request_url == "/room/update":
        return TYPE_CMD_UPDATE_ROOM_PROP
    elif request_url == "/room/show":
        return TYPE_CMD_QUERY_ROOM_PROP
    elif request_url == "/room/removearea":
        return TYPE_CMD_REMOVE_AREA_PROP
    elif request_url == "/room/updatearea":
        return TYPE_CMD_UPDATE_AREA_PROP
    elif request_url == "/room/showarea":
        return TYPE_CMD_QUERY_AREA_PROP
    elif request_url == "/room/removemode":
        return TYPE_CMD_REMOVE_ROOM_MODE
    elif request_url == "/room/updatemode":
        return TYPE_CMD_UPDATE_ROOM_MODE
    elif request_url == "/room/showmode":
        return TYPE_CMD_QUERY_ROOM_MODE
    elif request_url == "/room/activemode":
        return TYPE_CMD_ACTIVE_ROOM_MODE

    else:
        return None

############################################################################################################
#################################### 泊声背景音乐 ####################################
############################################################################################################
TYPE_CMD_BG_MUSIC_BOSHENG_START = 2000              # 泊声背景音乐命令起始值
TYPE_CMD_BG_MUSIC_BOSHENG_SWITCH_ON = 2001          # "开机"
TYPE_CMD_BG_MUSIC_BOSHENG_SWITCH_OFF = 2002         # "关机"
TYPE_CMD_BG_MUSIC_BOSHENG_LOW_VOICE_MINUS = 2003    # "低音-"
TYPE_CMD_BG_MUSIC_BOSHENG_LOW_VOICE_PLUS = 2004     # "低音+"
TYPE_CMD_BG_MUSIC_BOSHENG_HIGH_VOICE_MINUS = 2005   # "高音-"
TYPE_CMD_BG_MUSIC_BOSHENG_HIGN_VOICE_PLUS = 2006    # "高音+"
TYPE_CMD_BG_MUSIC_BOSHENG_VOLUMN_MINUS = 2007       # "音量-"
TYPE_CMD_BG_MUSIC_BOSHENG_VOLUMN_PLUS = 2008        # "音量+"
TYPE_CMD_BG_MUSIC_BOSHENG_LAST_SONG = 2009          # "上一曲"
TYPE_CMD_BG_MUSIC_BOSHENG_NEXT_SONG = 2010          # "下一曲"
TYPE_CMD_BG_MUSIC_BOSHENG_PLAY = 2011               # "播放"
TYPE_CMD_BG_MUSIC_BOSHENG_PAUSE = 2012              # "暂停"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSE_ON = 2013            # "静音"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSE_OFF = 2014           # "取消静音"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_MP3 = 2015    # "MP3 音源"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_FM1 = 2016    # "FM1 音源"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_FM2 = 2017    # "FM2 音源"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_IPOD = 2018   # "iPod 音源"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_DVD = 2019    # "DVD 音源"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_AUX = 2020    # "AUX 音源"
TYPE_CMD_BG_MUSIC_BOSHENG_MUSICE_SOURCE_CLOUD = 2021  # "云音乐音源"
TYPE_CMD_BG_MUSIC_BOSHENG_SINGLE_PLAY_ON = 2022     # "单曲"
TYPE_CMD_BG_MUSIC_BOSHENG_SINGLE_PLAY_OFF = 2023    # "取消单曲"


# 其他命令在此之前添加
TYPE_CMD_BG_MUSIC_BOSHENG_END = 2100    # 泊声背景音乐命令结束值

# 调光面板节律标识 true：节律 false：节律以外
light_adjust_Pannel_flag = {}


############################################################################################################
####################################中控、关联设备等操控指令####################################
############################################################################################################
#CMDID_DEVICE_LINKDEV = 0x0
#CMDID_DEVICE_MODE_PANNEL = 0x1