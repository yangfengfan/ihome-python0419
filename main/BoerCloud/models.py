
from google.protobuf import message
from google.protobuf import reflection
from protocal import AckMsg_pb2 as AckMsg
from protocal import CommandMsg_pb2 as CommandMsg
from protocal import DataMsg_pb2 as DataMsg
from protocal import DeviceStatusMsg_pb2 as StatusMsg
from protocal import RequestMsg_pb2 as RequestMsg

__all__ = [
    'Ack', 'Data', 'Command', 'CommandRes', 'Status',
    'Request', 'RequestResp',
    'Handshake', 'Heartbeat'
]

class Ack(message.Message):

    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = AckMsg._ACKPROTO

class Data(message.Message):

    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = DataMsg._DEVICEDATAPROTO

class Command(message.Message):

    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = CommandMsg._DEVICECOMMANDPROTO

class CommandRes(message.Message):

    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = CommandMsg._DEVICECOMMANDRESPROTO

class Status(message.Message):

    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = StatusMsg._DEVICESTATUSPROTO

# class StatusValue(message.Message):
#
#     __metaclass__ = reflection.GeneratedProtocolMessageType
#     DESCRIPTOR = StatusMsg._DEVICESTATUSPROTO_STATUS

# class Alarm(message.Message):
#
#     __metaclass__ = reflection.GeneratedProtocolMessageType
#     DESCRIPTOR = StatusMsg._DEVICESTATUSPROTO_ALARMINFO

class Request(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = RequestMsg._REQUESTPROTO

class RequestResp(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = RequestMsg._REQUESTRESPPROTO

class Handshake(object):
    pass

class Heartbeat(object):
    pass