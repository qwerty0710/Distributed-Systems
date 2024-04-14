from enum import Enum


class Log():
    def __init__(self, msg_id, shard_id, op_type, data):
        self.msg_id = msg_id
        self.shard_id = shard_id
        self.op_type = op_type
        self.data = data


class op_type(str, Enum):
    WRITE = 'write'
    UPDATE = 'update'
    DELETE = 'del'

