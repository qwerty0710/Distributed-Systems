from enum import Enum


class Log:
    def __int__(self, msg_id, shard_id, op_type, data: object):
        self.msg_id = msg_id
        self.shard_id = shard_id
        self.op_type = op_type
        self.data = data


class op_type(str, Enum):
    WRITE = 'write'
    UPDATE = 'update'
    DELETE = 'del'

