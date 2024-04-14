import json
from argparse import Namespace
from server import logFile

class random:
    def __init__(self, whoo, yuhh):
        self.whoo = whoo
        self.yuhh = yuhh


arr = [{'a': 1}]

with open('logs.log', 'a') as the_file:
    the_file.writelines([f'{json.dumps(random(logFile.op_type.DELETE, arr).__dict__)}\n'])
the_file.close()
# print(json.dumps(random(6, arr).__dict__))
with open('logs.log', 'r') as the_file:
    line = the_file.readlines()
    print(json.loads(line[0]).get('yuhh')[0]['a'])
the_file.close()
