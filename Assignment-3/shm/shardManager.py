import asyncio
import os
import time
import threading
import aiohttp
import uvicorn
import random
from fastapi import FastAPI, Body, status
from asgiref.sync import async_to_sync

app = FastAPI()

app.server_id_name_map = {}
app.server_id_name_map_lock = asyncio.Lock()
app.shard_primary_server_map = {}
app.shard_primary_server_map_lock = asyncio.Lock()
app.shard_server_mapping = {}
app.shard_server_mapping_lock = asyncio.Lock()
app.n = 512
app.db_schema=None


async def del_server(server_id):
    shards_to_change_leader = []
    for shard in app.shard_primary_server_map.keys():
        if app.shard_primary_server_map[shard] == server_id:
            shards_to_change_leader.append(shard)
    for shard in app.shard_server_mapping.keys():
        if server_id in app.shard_server_mapping[shard]:
            index = app.shard_server_mapping[shard].index(server_id)
            del app.shard_server_mapping[shard][index]
    for shard in shards_to_change_leader:
        # send req to get the id of the latest log to see which is the most updated server
        await change_leader(shard)

async def make_request(server_name, payload, path, method):
    try:
        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(f"http://{server_name}:5000/{path}", json=payload, timeout=2) as response:
                    content = await response.read()
                    # print(content)
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        print("return obj", return_obj, server_name)
                        return return_obj
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
            elif method == "GET":
                # print("OKKK")
                async with session.get(f"http://{server_name}:5000/{path}", json=payload,
                                       timeout=2) as response:
                    content = await response.read()
                    print("content", content)
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        print("return obj", return_obj)
                        return return_obj
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
            elif method == "PUT":
                async with session.put(f"http://{server_name}:5000/{path}", json=payload,
                                       timeout=2) as response:
                    content = await response.read()
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        return return_obj
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
            elif method == "DELETE":
                async with session.delete(f"http://{server_name}:5000/{path}", json=payload,
                                          timeout=2) as response:
                    content = await response.read()
                    print(content)
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        return return_obj
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
    except Exception as e:
        print(f"Exception {str(e)} in make request in {method} method of {path} for {server_name}")


# assigns the server with most updated logs as leader and notifies the servers about the change
async def change_leader(shard):
    server_with_most_updated_index = None
    most_updated_index = -1
    for server_ in app.shard_server_mapping[shard]:
        index = await make_request(app.server_id_name_map[server_], {}, "get_latest_log_index", "POST")
        if index > most_updated_index:
            most_updated_index = index
            server_with_most_updated_index = server_
    app.shard_primary_server_map[shard] = server_with_most_updated_index
    for server_ in app.shard_server_mapping[shard]:
        payload = {'shard': shard, 'server_id': app.server_id_name_map[server_]}
        await make_request(app.server_id_name_map[server_], payload, "leaderElection", "POST")
    app.shard_primary_server_map[shard] = server_with_most_updated_index
    await make_request('lb',{'primary_server_map':{shard:server_with_most_updated_index}},"elected_primary","POST")


class Heartbeat(threading.Thread):
    def __init__(self, server_list):
        super(Heartbeat, self).__init__()
        self.fails = {}
        # for arg in args:
        self.server_list = server_list
        # break
        for server in self.server_list:
            self.fails[str(server)] = 0
            print(f"server list {self.server_list}")

    async def make_request(self, server_id):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{str(app.server_id_name_map[str(server_id)])}:5000/heartbeat",
                                        timeout=2) as response:
                    content = await response.read()
                    if response.status != 404:
                        # ret_obj = await response.json(content_type="application/json")
                        # print(ret_obj)
                        return content
                    else:
                        return {"message": f"<Error> '/heartbeat’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
        except Exception as e:
            self.fails[server_id] += 1
            print(str(e))
            # acquire the lock for read and write for the shards in this server
            cmd = os.popen(f"sudo docker run --rm --name {app.server_id_name_map[server_id]} "
                           f"--network net1 "
                           f"--network-alias {app.server_id_name_map[server_id]} "
                           f"-e SERVER_ID={int(server_id)} "
                           # f"-p {5001 + int(server_id)}:5000 "
                           f"-d server").read()
            await asyncio.sleep(1)
            if len(cmd) == 0:
                print(f"Heartbeat failed to respawn {app.server_id_name_map[server_id]} trying again")
                self.fails[str(server_id)] += 1
            else:
                # release the lock after copying the data from shards to the server
                print(
                    f"{app.server_id_name_map[server_id]} respawned using heartbeat after {self.fails[server_id]} tries")
                await self.reconfig_server(server_id)
                self.fails[server_id] = 0

    async def shard_data_for_shard(self, shard):
        server_to_get_from = app.shard_primary_server_map[shard]
        # server_list_for_trying = app.shard_server_mapping[shard]
        # for tuplee in server_list_for_trying:
        #     server_list_for_trying.append(tuplee[0])
        # for server_to_try in server_list_for_trying:
        #     if self.fails[server_to_try] == 0:
        #         server_to_get_from = server_to_try
        #         break
        payload = {"shards": [shard]}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{str(app.server_id_name_map[str(server_to_get_from)])}:5000/copy",
                                   json=payload, timeout=2) as response:
                content = await response.read()
                print(content)
                ret_obj = await response.json(content_type="application/json")
                print(ret_obj)
                return ret_obj[shard]

    async def reconfig_server(self, server_id):
        payload = {}
        payload["schema"] = app.db_schema
        shard_list = []
        for shard in app.shard_server_mapping.keys():
            if server_id in app.shard_server_mapping[shard]:
                shard_list.append(shard)
        payload["shards"] = list(shard_list)
        print(payload)
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{str(app.server_id_name_map[str(server_id)])}:5000/config", json=payload,
                                    timeout=2) as response:
                content = await response.read()
                # print(content)
                if response.status != 404:
                    ret_obj = await response.json(content_type="application/json")
                    print(ret_obj)
                else:
                    print(
                        {"message": f"<Error> '/config’ endpoint in heartbeat thread does not exist in server replicas",
                         "status": "failure"}, 400)
        for shard in shard_list:
            data = await self.shard_data_for_shard(shard)
            write_payload = {"shard": shard, "curr_idx": 0, "try_again": 0, "data": data}
            print(write_payload)
            async with aiohttp.ClientSession() as session:
                async with session.post(f"http://{str(app.server_id_name_map[str(server_id)])}:5000/write",
                                        json=write_payload,
                                        timeout=2) as response:
                    content = await response.read()
                    print(content)
                    ret_obj = await response.json(content_type="application/json")
                    print("write heartbeat", ret_obj)

    @async_to_sync
    async def run(self, *args, **kwargs):

        print("Heartbeat running!!")
        while True:
            for server in list(app.server_id_name_map.keys()):
                if server not in self.fails.keys():
                    self.fails[server] = 0

                await self.make_request(server)
            for server in list(self.fails.keys()):
                if self.fails[server] > 5:

                    await app.server_id_name_map_lock.acquire()
                    del app.server_id_name_map[server]
                    app.server_id_name_map_lock.release()
                    # send req to the loadbalancer that a server is dead
                    await make_request("lb", {"server_id": server}, "server_dead", "POST")
                    # change the leader if the server is leader any of the shards that were present in it
                    shards_to_change_leader = []
                    for shard in app.shard_primary_server_map.keys():
                        if app.shard_primary_server_map[shard] == server:
                            shards_to_change_leader.append(shard)
                    # delete the server from all app.shard_server_map
                    for shard in app.shard_server_mapping.keys():
                        if server in app.shard_server_mapping[shard]:
                            index = app.shard_server_mapping[shard].index(server)
                            del app.shard_server_mapping[shard][index]
                    new_primary_servers = {}
                    for shard in shards_to_change_leader:
                        # send req to get the id of the latest log to see which is the most updated server
                        await change_leader(shard)

                        # select the new leader and assign it in new_primary_server map

                    # for shard in new_primary_servers.keys():
                    #     app.shard_primary_server_map[shard] = new_primary_servers[shard]
                    #     # send a req to "/newLeader" to all the servers that this shard is a part of
                    #     for server_containing_shard in app.shard_server_mapping[shard]:
                    #         pass

                    # shard_consistent_hashing changing
                    # asyncio.run(app.shard_consistent_hashing_lock.acquire())
                    # for shard in app.shard_consistent_hashing.keys():
                    #     if server in app.shard_consistent_hashing[shard].get_servers():
                    #         app.shard_consistent_hashing[shard].server_del(server)
                    # app.shard_consistent_hashing_lock.release()
                    # app.database_helper.del_server(str(server))
            time.sleep(1)

    # def copy_data(self,server_name):


@app.post("/init")
async def init(N: int = Body(...), schema: dict = Body(...), servers: dict[str, list] = Body(...),
               idnamemap: dict[str, str] = Body(...)):
    # store the serverlist, ids, all other things, in the loadbalancer without database
    # start heartbeat
    app.db_schema = schema
    app.n = N
    app.server_id_name_map = idnamemap
    print(servers)
    for server in servers.keys():
        for shard in servers[server]:
            if shard not in app.shard_server_mapping.keys():
                app.shard_server_mapping[shard] = []
            id_ = list(idnamemap.keys())[list(idnamemap.values()).index(server)]
            app.shard_server_mapping[shard].append(id_)
    thread_obj = Heartbeat(list(app.server_id_name_map.keys()))
    thread_obj.start()
    print(app.shard_server_mapping)
    # pick primary server and send it back to the loadbalancer
    for shard in app.shard_server_mapping.keys():
        random_server = app.shard_server_mapping[shard][
            random.randint(0, len(app.shard_server_mapping[shard]) - 1)]
        app.shard_primary_server_map[shard] = random_server
    print(app.shard_primary_server_map)
    await make_request('lb',{'primary_server_map':app.shard_primary_server_map},"elected_primary","POST")


@app.post("/add")
async def add(N: int = Body(...), new_shards: list[dict] = Body(...), servers: dict = Body(...),
              idnamemap: dict = Body(...)):
    # similar to lb you could add new shards and servers at the same time
    # this will get filtered data with actual server names from th loadbalancer sp we can directly add them to out meta data
    app.n += N
    for idd, name in idnamemap:
        app.server_id_name_map[idd] = name
    for server in servers.keys():
        for shard in servers[server]:
            id_ = list(idnamemap.keys())[list(idnamemap.values()).index(server)]
            app.shard_server_mapping[shard].append(id_)
    # elect leader for new shards
    for shard in new_shards:
        random_server = app.shard_server_mapping[shard["shard_id"]][
            random.randint(0, len(app.shard_server_mapping[shard["shard_id"]]) - 1)]
        app.shard_primary_server_map[shard] = random_server
    await make_request('lb',{'primary_server_map':app.shard_primary_server_map},'elected_primary',"POST")


@app.delete("/del")
async def delete():
    # delete a server
    pass


if __name__ == "__main__":
    uvicorn.run("0.0.0.0", port=4999)
