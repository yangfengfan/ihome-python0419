# -*- coding: utf-8 -*-


SUCCESS = 0
SUCCESS_SAME_TIMESTAMP = 100         # 时间戳一致，app可使用缓存数据



# 失败的错误码从50000开始
ERR_GENERAL = 50000                  # 未知错误
ERR_CMD_TYPE = 50001                 # 消息码错误
ERR_CMD_NO_CLOUD_LINK = 50002        # 需要云账号连接
ERR_CMD_NO_LOCAL_LINK = 50003        # 需要本地连接
ERR_CMD_DUPLICATE_DEVICE = 50004     # 设备重复添加
ERR_INVALID_REQUEST = 50100          # 无效请求
ERR_INVALID_PARAMS = 50101           # 参数错误
ERR_MSG_PARSE_ERR = 50105            # 消息解析错误
ERR_MSG_CONFLICT = 50106             # 数据过期
ERR_WRONG_USERNAME_PASSWORD = 50005  # 用户名密码错误
ERR_SCANNING = 50006                 # 网关已经有用户在扫描设备


ERR_SQL = 51100                      # 数据库错误
ERR_SQL_LOGIN = 51101                # login接口数据库错误
ERR_SQL_AUTHORIZED = 51102           # authorizedLogin接口数据库错误
ERR_SQL_SAVE = 51103                 # saveUserInfo接口数据库错误
ERR_SQL_DELETE = 51104               # deleteUser接口数据库错误
ERR_SQL_NORMALLOGIN = 51105          # normalLogin接口数据库错误
ERR_SQL_AUTH = 51106                 # authorizedLogin数据库错误
ERR_SQL_SAVEUSER = 51107             # saveUserInfo数据库错误
ERR_SQL_DELETEUSER = 51108           # deleteUser数据库错误

ERR_SERVER = 51201                   # 服务器内部错误
ERR_SERVER_LOGIN = 51202             # login服务器内部错误
ERR_SERVER_AUTHORIZEDLOGIN = 51203   # authorizedLogin服务器内部错误
ERR_SERVER_LOGOUT = 51204            # logout服务器内部错误
ERR_SERVER_SAVE = 51205              # saveUserInfo服务器内部错误
ERR_SERVER_DELETEUSER = 51206        # deleteUser服务器内部错误
ERR_SERVER_NORMALLOGIN = 51207       # normalLogin服务器内部错误
ERR_SERVER_AUTH = 51208              # authorizedLogin接口服务器内部错误
ERR_SERVER_login_SOCK = 51209        # logout接口服务器内部错误
ERR_SERVER_SAVEUSERINFO = 51210      # saveUserInfo接口服务器内部错误
ERR_SERVER_DELETE = 51211            # deleteUser接口服务器内部错误

ERR_USER = 51002                     # 用户不存在
ERR_WRONG_USERNAME_PASSWORD_LOGIN = 51301  # login接口用户不存在
ERR_WRONG_USERNAME_PASSWORD_LOGOUT = 51302 # logout接口用户不存在
ERR_USER_SAVEUSERINFO = 51303              # saveUserInfo接口用户不存在
ERR_USER_DELETEUSER = 51304                # deleteUser接口数据库错误
ERR_WRONG_USERNAME_PASSWORD_QUERY = 51305  # queryUserInfo用户不存在
ERR_USER_NORMALLOGIN = 51306               # normalLogin接口用户不存在
ERR_WRONG_USERNAME_PASSWORD_LOGOUT_SOCK = 51307 # logout用户不存在
ERR_USER_SAVE = 51308                      # saveUserInfo用户不存在
ERR_USER_DELETE = 51309                    # deleteUser用户不存在

ERR_NO_SAVE_USER = 51003             # 未保存用户信息

ERR_EXCEPTION = 51004                # 系统处理异常

ERR_INVALID_HOST = 51005             # 无效的网关配置(ID错误)
ERR_INVALID_HOST_VERIFYUSER = 51401  # verifyUserPassword接口无效的网关配置(ID错误)
ERR_INVALID_HOST_MODIFY = 51402      # modifyUserProperty接口无效的网关配置(ID错误)
ERR_INVALID_HOST_MODIFYHOST = 51403  # modifyHostName接口无效的网关配置(ID错误)
ERR_INVALID_HOST_MODIFYHOSTPRO = 51404 # modifyHostProperty接口无效的网关配置(ID错误)


ERR_FAIL_TO_DELETE = 51006           # 删除失败！！

ERR_BACKUPHOST2CLOUD_HOSTID_NONE = 52001        # backupHost2Cloud/hostId=None
ERR_BACKUPHOST2CLOUD = 52002                    # backupHost2Cloud默认返回
ERR_CONFIGHGC_SAVE = 52003                      # configHGC/saveHGCconfigs
ERR_LINKDEVICES_UPDATE = 52004                  # linkDevices/updateDeviceLinks
ERR_LINKDEVICES_SAVE = 52005                    # linkDevices/saveDeviceLinks
ERR_LINKDEVICES_DELETE = 52006                  # linkDevices/deleteByDbId
ERR_UPDATEROOMMODE = 52007                      # updateRoomMode
ERR_UPDATELINKACTION = 52008                    # updateLinkAction
ERR_UPDATEAREAPROP = 52009                      # updateAreaProp
ERR_UPDATEROOMPROP_HOSTPROP_NONE = 52010        # updateRoomProp/host_prop=None
ERR_UPDATEROOMPROP = 52011                      # updateRoomProp默认返回
ERR_QUERYDEVICESTATUS_EXCEPTION = 52012         # queryDeviceStatus/Exception
ERR_QUERYDEVICEWITHBATCH_EXCEPTION = 52013      # queryDeviceWithBatch/Exception

ERR_REMOVEDEVICES_EXCEPTION = 52014             # removeDevices/Exception
ERR_DISMISSDEVICES_EXCEPTION = 52015            # dismissDevices/Exception
ERR_MODIFYUSERPROPERTY_EXCEPTION = 52016        # modifyUserProperty/Exception
ERR_MODIFYHOSTNAME_HOST_NONE = 52017            # modifyHostName/host=None
ERR_MODIFYHOSTNAME_RESULT_NONE = 52018          # modifyHostName/result=None
ERR_MODIFYHOSTPROPERTY_HOST_NONE = 52019        # modifyHostProperty/host=None
ERR_MODIFYHOSTPROPERTY_HOSTPROP_NONE = 52020    # modifyHostProperty/hostProp=None
ERR_MODIFYMODENAME_RESULT_FALSE = 52021         # modifyModeName/result=FALSE
ERR_MODIFYMETERNAME_SAVE = 52022                # modifyMeterName/saveDeviceProperty
ERR_QUERYGLOBALMODE = 52023                     # queryGlobalMode默认返回
ERR_QUERYALLDEVICES_ALL_EXCEPTION = 52024       # query_all_devices/All_Exception
ERR_QUERYALLDEVICES_NOTALL_EXCEPTION = 52025    # query_all_devices/NotAll_Exception
ERR_SETTIMETASH_EXCEPTION = 52026               # set_time_task/Exception
ERR_SWITCHTIMETASK_CHECKCHANGE_NONE = 52027     # switch_time_task/check_change=None
ERR_SWITCHTIMETASK_EXCEPTION = 52028            # switch_time_task/Exception
ERR_QUERYTASKDETAIL = 52029                     # query_task_detail默认返回
ERR_QUERYTASKSWITCH_CHECKCHANGE_NONE = 52030    # query_task_switch_state/check_change=None
ERR_QUERYTASKSWITCH_EXCEPTION = 52031           # query_task_switch_state/Exception
ERR_FLOORHEATINGTIMETASK = 52032                # set_floor_heating_time_task/device_prop=none
ERR_FLOORHEATINGTIMETASK_OLDTIMETASK_NONE = 52033    # set_floor_heating_time_task/old_time_task=None
ERR_FLOORHEATINGTIMETASK_OPERATION_UPDATE = 52034    # set_floor_heating_time_task/operation=updateWeekend
ERR_FLOORHEATINGTIMETASK_EXCEPTION = 52035           # set_floor_heating_time_task/Exception
ERR_SWITCHFLTIMETASK_SPARM = 52036               # switch_FL_time_task/sparam=None
ERR_SWITCHFLTIMETASK_DEVICE_NONE = 52037         # switch_FL_time_task/device_addr=None
ERR_SWITCHFLTIMETASK_PROP = 52038                # switch_FL_time_task/device_prop=None
ERR_SWITCHFLTIMETASK_EXCEPTION = 52039           # switch_FL_time_task/Exception

ERR_SAVEDEVICEPROPERTY_DETAILOBJ_NONE = 52040    # saveDeviceProperty/detailObj=None
ERR_SAVEDEVICEPROPERTY_DEVICEADDR_NONE = 52041   # saveDeviceProperty/deviceAddr=None
ERR_SAVEDEVICEPROPERTY_NAME_NONE = 52042         # saveDeviceProperty/name=None
ERR_SAVEDEVICEPROPERTY = 52043                   # saveDeviceProperty/默认返回

ERR_NEWDEVICEPROPERTY_DETAILOBJ_NONE = 52044    # newDeviceProperty/detailObj=None
ERR_NEWDEVICEPROPERTY_DEVICEADDR_NONE = 52045   # newDeviceProperty/deviceAddr=None
ERR_NEWDEVICEPROPERTY_NAME_NONE = 52046         # newDeviceProperty/name=None
ERR_NEWDEVICEPROPERTY = 52047                   # newDeviceProperty/默认返回
ERR_RESTART = 52048
ERR_TEMPORARILY_NO_TIMING_FUNCTION = 55000






