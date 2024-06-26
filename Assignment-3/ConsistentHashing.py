import math
import os
import random


class Consistent_Hashing:

    def __init__(self, m, req_hash, server_hash, server_list):
        self.servers = {}
        self.ring = [-1] * m
        self.slots = m
        self.req_hash = req_hash
        self.server_hash = server_hash
        self.k = int(math.log2(m))
        for server in server_list:
            self.servers[str(server["server_id"])] = {}
            self.servers[str(server["server_id"])]["slots"] = []
            self.servers[str(server["server_id"])]["name"] = server["server_name"]
            random_id = random.randint(0, self.slots - 1)
            for i in range(self.k):
                hash_val = self.server_hash(random_id, i)
                add = 1
                while self.ring[hash_val] != -1:
                    hash_val = (hash_val + 1) % self.slots
                    # add = add + 1
                self.ring[hash_val] = server["server_id"]
                self.servers[str(server["server_id"])]["slots"].append(hash_val)
        print(self.servers)

    def get_servers(self):
        return self.servers

    def get_req_server(self, req_id):
        hash_slot = self.req_hash(req_id)
        while self.ring[hash_slot] == -1:
            hash_slot = hash_slot + 1
            hash_slot = hash_slot % self.slots
        return self.ring[hash_slot]

    def server_del(self, server_id):
        # reallocate if server is deleted
        for i in self.servers[str(server_id)]["slots"]:
            self.ring[int(i)] = -1
        del self.servers[server_id]

    def server_down(self, server_id):
        self.server_del(server_id)

    def add_server(self, server_id, server_preferred_name):
        # add the server and reallocate
        self.servers[str(server_id)] = {}
        self.servers[str(server_id)]["slots"] = []
        self.servers[str(server_id)]["name"] = server_preferred_name
        for i in range(self.k):
            random_id = random.randint(100000, 999999)
            hash_val = self.server_hash(random_id, i)
            # check if the slot is empty else find the next empty slot using linear probing
            while self.ring[hash_val] != -1:
                hash_val = (hash_val + 1) % self.slots
            self.ring[hash_val] = server_id
            self.servers[str(server_id)]["slots"].append(hash_val)
