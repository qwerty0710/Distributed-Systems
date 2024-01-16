import math


class Consistent_Hashing:
    servers = {}

    def __init__(self, m, req_hash, server_hash):
        self.ring = [-1] * m
        self.slots = m
        self.req_hash = req_hash
        self.server_hash = server_hash
        self.k = int(math.log2(m))
        for server in range(3):
            self.servers[str(server)] = {}
            self.servers[str(server)]["slots"] = []
            self.servers[str(server)]["name"] = f"server{server}"
            for i in range(self.k):
                hash_val = self.server_hash(server, i)
                add = 2
                while self.ring[hash_val] != -1:
                    hash_val = (hash_val + add**2) % self.slots
                    add = add + 1
                self.ring[hash_val] = server
                self.servers[str(server)]["slots"].append(hash_val)

    def get_req_slot(self, req_id):
        hash_slot = self.req_hash(req_id)
        while self.ring[hash_slot] == -1:
            hash_slot = hash_slot + 1
            hash_slot = hash_slot % self.slots
        return hash_slot

    def server_del(self, server_id):
        # reallocate if server is deleted
        for i in self.servers[server_id]:
            self.ring[i] = -1
        del self.servers[server_id]

    def server_down(self, server_id):
        self.server_del(server_id)

    def add_server(self, server_id, server_preferred_name):
        # add the server and reallocate
        for i in range(self.k):
            hash_val = self.server_hash(server_id, i)
            # check if the slot is empty else find the next empty slot using linear probing
            while self.ring[hash_val] != -1:
                hash_val = (hash_val + 1) % self.slots
            self.ring[hash_val] = server_id
            self.servers[str(server_id)]["name"] = server_preferred_name
            self.servers[str(server_id)]["slots"].push(hash_val)


obj = Consistent_Hashing(512, lambda i: (i ** 2 + 2 * i + 17) % 512, lambda i, j: (i ** 2 + j ** 2 + j * 2 + 25) % 512)