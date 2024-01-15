class Consistent_Hashing:
    def __init__(self, n, req_hash, server_hash, init_servers, virtual_servers):
        self.ring = [{}] * 512
        self.servers = {}
        self.slots = n
        self.req_hash = req_hash
        self.server_hash = server_hash
        for server in init_servers:
            for i in range(virtual_servers):
                self.ring[self.server_hash(server, i)] = {"server_id": server, "type": "server"}

    def get_req_slot(self, req_id, client_id):
        hash_slot = self.req_hash(req_id)
        while self.ring[hash_slot] is not {}:
            hash_slot = hash_slot + 1
            hash_slot = hash_slot % 512
        iter = hash_slot
        while self.ring[iter]["type"] != "server":
            iter = iter + 1
        self.ring[hash_slot] = {"client_id": client_id, "req_id": req_id, "type": "request", "server_slot": iter}

        return {"slot_no": hash_slot, "server": self.ring[iter]}

    def req_complete(self, req_id):
        for i in range(512):
            if self.ring[i]["req_id"] is req_id:
                self.ring[i] = {}
                return

    def server_del(self, server_ids):
        # reallocate if server is deleted
        non_deleted_server = {}
        for server in self.servers:
            flag = 0
            for del_server in server_ids:
                if del_server == server:
                    flag = 1
                    break
            if flag:
                break
            else:
                non_deleted_server = server

    def server_down(self, server_id):
        pass

    def add_server(self, server_id):
        # add the server and reallocate
        pass
