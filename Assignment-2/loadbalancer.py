import asyncio
import json
import os
import random
import re
import time
from contextlib import asynccontextmanager
import threading
import aiohttp
import uvicorn
from fastapi import FastAPI, Body, status, Request
from ConsistentHashing import Consistent_Hashing
from lb_db_helper import db_helper


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(threading.current_thread())
    yield
    stop_heartbeat()


app = FastAPI(lifespan=lifespan)
# Number of slots in the ring
# m = int(os.getenv("m"))
app.m = 512
# reqHash = lambda i: (67 * i ** 3 + 3 * i ** 2 + 53 * i + 97) % app.m
app.reqHash = lambda i: (i ** 2 + 2 * i + 17) % app.m
# serverHash = lambda i, j: (59 * i ** 2 + 73 + 29 * j ** 2 + j * 7 + 73) % app.m
app.serverHash = lambda i, j: (i ** 2 + j ** 2 + j * 2 + 25) % app.m
app.database_helper = db_helper("lb_db")

app.server_id_name_map = {}
app.shard_consistent_hashing: dict[str, Consistent_Hashing] = {}
app.db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "port": "3306"
}
app.db_schema = {}
app.shard_locks: dict[str, asyncio.Lock] = {}
app.shard_consistent_hashing_lock = asyncio.Lock()
app.server_id_name_map_lock = asyncio.Lock()


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
                async with session.post(f"http://{str(app.server_id_name_map[str(server_id)])}:5000/heartbeat",
                                        timeout=2) as response:
                    content = await response.read()
                    if response.status != 404:
                        # ret_obj = await response.json(content_type="application/json")
                        # print(ret_obj)
                        return content
                    else:
                        return {"message": f"<Error> '/heatbeat’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
        except Exception as e:
            self.fails[server_id] += 1
            print(str(e))
            # acquire the lock for read and write for the shards in this server
            cmd = os.popen(f"sudo docker run --rm --name {app.server_id_name_map[server_id]} "
                           f"--network net1 "
                           f"--network-alias {app.server_id_name_map[server_id]} "
                           f"-e SERVER_ID={int(server_id)} "
                           f"-p {5001 + int(server_id)}:5000 "
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
        server_list_for_trying_db = app.database_helper.get_servers_for_shard(shard)
        server_to_get_from = server_list_for_trying_db[0][0]
        server_list_for_trying = []
        for tuplee in server_list_for_trying_db:
            server_list_for_trying.append(tuplee[0])
        for server_to_try in server_list_for_trying:
            if self.fails[server_to_try] == 0:
                server_to_get_from = server_to_try
                break
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
        shards = app.database_helper.get_shard_for_server(server_id)
        payload["schema"] = app.db_schema
        shard_list = []
        for tuplee in shards:
            shard_list.append(tuplee[0])
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

    def run(self, *args, **kwargs):

        print("Heartbeat running!!")
        while True:
            for server in list(app.server_id_name_map.keys()):
                if server not in self.fails.keys():
                    self.fails[server] = 0
                asyncio.run(self.make_request(server))
            for server in list(self.fails.keys()):
                if self.fails[server] > 5:
                    asyncio.run(app.server_id_name_map_lock.acquire())
                    del app.server_id_name_map[server]
                    app.server_id_name_map_lock.release()
                    # shard_consistent_hashing changing
                    asyncio.run(app.shard_consistent_hashing_lock.acquire())
                    for shard in app.shard_consistent_hashing.keys():
                        if server in app.shard_consistent_hashing[shard].get_servers():
                            app.shard_consistent_hashing[shard].server_del(server)
                    app.shard_consistent_hashing_lock.release()
                    app.database_helper.del_server(str(server))
            time.sleep(1)

    # def copy_data(self,server_name):


# variable locks done
def get_smallest_unoccupied_server_id():
    occupied_ids = []
    # await app.server_id_name_map_lock.acquire()
    for server_id in app.server_id_name_map.keys():
        occupied_ids.append(server_id)
    occupied_ids = list(map(int, occupied_ids))
    smallest_id = 0
    while smallest_id in occupied_ids:
        smallest_id = smallest_id + 1
    # app.server_id_name_map_lock.release()
    return smallest_id


# variable locks done
def get_shards_for_stud_id_range(low, high):
    shard_data = sorted(app.database_helper.get_shard_data(), key=lambda x: x[0])
    cont = 1
    i = 0
    shards_for_req = []
    while cont and (i < len(shard_data)):
        right_shard = shard_data[i][0] + shard_data[i][2]
        left_shard = shard_data[i][0]
        if high < left_shard or low > right_shard:
            if high < left_shard:
                cont = 0
        else:
            if right_shard > high:
                cont = 0
            shards_for_req.append(
                {"shard": shard_data[i][1], "range": {"low": max(left_shard, low), "high": min(high, right_shard)}})
        i = i + 1
    return shards_for_req


def get_shards_for_data_write(data):
    shard_data = sorted(app.database_helper.get_shard_data(), key=lambda x: x[0])
    shard_to_make_req = {}
    # for shard in shard_data:
    #     shard_to_make_req[shard[1]] = {}
    #     shard_to_make_req[shard[1]]["curr_idx"] = shard[3]
    #     shard_to_make_req[shard[1]]["data"] = []
    for data_entry in data:
        shard_index = int(data_entry["Stud_id"]) // int(shard_data[0][2])
        shard_to_map = shard_data[shard_index][1]
        if shard_to_map not in shard_to_make_req.keys():
            shard_to_make_req[shard_to_map] = {}
            shard_to_make_req[shard_to_map]["data"] = []
            shard_to_make_req[shard_to_map]["curr_idx"] = shard_data[shard_index][3]
        shard_to_make_req[shard_to_map]["data"].append(data_entry)
    return shard_to_make_req


def generate_req_id():
    id = random.randint(000000, 999999)
    return id


async def spawn_new_servers(servers_id_name_map):
    for server_id in servers_id_name_map.keys():
        cmd = os.popen(f"sudo docker run --rm --name {servers_id_name_map[server_id]} "
                       f"--network net1 "
                       f"--network-alias {servers_id_name_map[server_id]} "
                       f"-e SERVER_ID={int(server_id)} "
                       f"-p {5001 + int(server_id)}:5000 "
                       f"-d server").read()
        time.sleep(1)
        if len(cmd) == 0:
            print(f"Unable to start server with server id: {server_id} with name {servers_id_name_map[server_id]}")
            # server_replicas.server_del(server_id)
        else:
            print(f"Successfully started server with server id: {server_id} with name {servers_id_name_map[server_id]}")



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
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        return return_obj
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
    except Exception as e:
        print(f"Exception {str(e)} in make request in {method} method of {path} for {server_name}")


# except Exception as e:
#     return {"message": f"<Error> {e}",
#             "status": "failure"}, 400


@app.post('/init', status_code=status.HTTP_200_OK)
async def init(N: int = Body(...), schema: dict = Body(...), shards: list[dict] = Body(...),
               servers: dict = Body(...)):
    print(threading.current_thread())
    # store schema of the shards
    app.db_schema = schema
    # get data from the request fastAPI
    shard_to_server = {}
    shard_list = []
    # allocating memory for shard to server mapping
    for i in range(len(shards)):
        shard_to_server[shards[i]["Shard_id"]] = []
    # generating server id for each server and creating list of servers each shard is a part of
    for server in servers.keys():
        server_id = get_smallest_unoccupied_server_id()
        app.server_id_name_map[str(server_id)] = server
        for i in range(len(servers[server])):
            # print(server_id)
            shard_to_server[servers[server][i]].append(str(server_id))
    # passing server names and ids in a dict to consistent hashing for each shard
    for shard in shard_to_server.keys():
        server_config = []
        for server_id in shard_to_server[shard]:
            server_config.append({"server_name": app.server_id_name_map[str(server_id)], "server_id": server_id})
        print(server_config, "server configgggggg", shard)
        # shard_consistent_hashing  changed
        app.shard_consistent_hashing[shard] = Consistent_Hashing(app.m, app.reqHash, app.serverHash, server_config)
    print(str(app.shard_consistent_hashing))
    for shard in shards:
        shard["curr_idx"] = 0
        app.database_helper.add_shard(shard)
    for server in app.server_id_name_map.keys():
        for shard in servers[app.server_id_name_map[server]]:
            app.database_helper.add_server(shard, server)
    await spawn_new_servers(app.server_id_name_map)

    for shard in shards:
        app.shard_locks[shard["Shard_id"]] = asyncio.Lock()
    # hit the '/config' endpoint of the servers to initialize the shards using aiohttp

    for sname in servers.keys():
        print(sname)
        payload = {"shards": servers[sname], "schema": schema}
        await make_request(sname, payload, "config", "POST")
    # thread = threading.Thread(target=asyncio.run,args=[list(app.server_id_name_map.keys())])
    # thread.start()
    thread_obj = Heartbeat(list(app.server_id_name_map.keys()))
    thread_obj.start()
    response = {
        "message": "Configured database",
        "status": "success"
    }
    return response


# variable locks done
@app.get('/status')
async def get_status():
    shard_tuples = app.database_helper.get_shard_data()
    print("served at time", time.time())
    shards = []
    for stud_id_low, shard_id, shard_size, curr_idx in shard_tuples:
        shard_dict = {"stud_id_low": stud_id_low, "shard_id": shard_id, "shard_size": shard_size}
        shards.append(shard_dict)
    server_shard = app.database_helper.get_server_data()
    servers = {}
    for shard, server in server_shard:
        servers[server] = []
    for shard, server in server_shard:
        servers[server].append(shard)
    schema = app.db_schema
    n = len(servers)
    response = {"N": n, "shards": shards, "servers": servers, "schema": schema}

    return response


# @app.get('/rep')
# async def get_replicas():
#     names = check_heartbeat()
#     response = {
#         "message": {
#             "N": len(names),
#             "replicas": names
#         },
#         "status": "successful"
#     }
#     return response


@app.post('/add')
async def add_replicas(N: int = Body(...), new_shards: list[dict] = Body(...),
                       servers: dict = Body(...)) -> dict[str, str]:
    hostnames = list(servers.keys())
    if len(hostnames) != N:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return response
    names = []
    mapT_data = app.database_helper.get_server_data()
    old_shards = set()
    for shard, server in mapT_data:
        old_shards.add(shard)
    print(mapT_data)
    for shard, server_id in mapT_data:
        if not app.server_id_name_map_lock.locked():
            names.append(app.server_id_name_map[server_id])
    # adding the new data in database
    for shard in new_shards:
        shard["curr_idx"] = 0
        app.database_helper.add_shard(shard)

    # add servers one by one and if n>hostname list then add random servers by generating server id and hostnames
    # names = check_heartbeat()
    await app.server_id_name_map_lock.acquire()
    print("got id name map lock 1")
    new_server_names = []
    for hostname in hostnames:
        server_id = get_smallest_unoccupied_server_id()
        name = hostname
        if (name in names) or not (bool(re.match(r"^[a-zA-Z][a-zA-Z0-9-]{0,61}$", name))):
            name = "randomserver" + str(server_id)
            temp_shard_list = servers[hostname]
            del servers[hostname]
            servers[name] = temp_shard_list
        # spawn new server
        await spawn_new_servers({str(server_id): name})
        print(f"spawned server with server id {server_id}")
        config_payload = {"schema":app.db_schema, "shards":servers[name]}
        await make_request(name,config_payload,"config","POST")
        app.server_id_name_map[str(server_id)] = name
        names.append(name)
        new_server_names.append(name)
        for shard_ in servers[name]:
            app.database_helper.add_server(shard_, server_id)
    app.server_id_name_map_lock.release()
    print("release id name map lock 1")
    # add new server to the old shards consistent hashing
    all_shards_req = []  # all shards of this request old and new shards
    for server_name in servers.keys():
        for shard in servers[server_name]:
            all_shards_req.append(shard)
    # shard_consistent_hashing
    await app.shard_consistent_hashing_lock.acquire()
    for shard in all_shards_req:
        if shard in old_shards:  # if the shard is old shard
            servers_containing_shard = []
            for server_name in servers.keys():
                if shard in servers[server_name]:
                    servers_containing_shard.append(server_name)
            server_id_list = []
            await app.server_id_name_map_lock.acquire()
            for server_id in app.server_id_name_map.keys():
                if app.server_id_name_map[server_id] in servers_containing_shard:
                    server_id_list.append(server_id)
            app.server_id_name_map_lock.release()
            for new_server_id in server_id_list:
                if not app.server_id_name_map_lock.locked():
                    app.shard_consistent_hashing[shard].add_server(new_server_id,
                                                                   app.server_id_name_map[new_server_id])
    app.shard_consistent_hashing_lock.release()

    shard_server_list_mapping = {}
    for shard_mapt, server_mapt in mapT_data:
        if shard_mapt in shard_server_list_mapping.keys():
            shard_server_list_mapping[shard_mapt].append(app.server_id_name_map[server_mapt])
        else:
            shard_server_list_mapping[shard_mapt] = [app.server_id_name_map[server_mapt]]


    # bring the data stored in old shards to the new server
    for shard in all_shards_req:
        if shard in old_shards:
            new_server_names = []
            shard_stored_data = []
            for server_name in servers.keys():
                if shard in servers[server_name]:
                    new_server_names.append(server_name)
            for shard_server_name in shard_server_list_mapping[shard]:
                if shard_server_name not in new_server_names:
                    # shard_to_get_data = [shard]
                    # print(shard_to_get_data)
                    # payload = {"shards": ["sh3"]}
                    payload = {"shards": [str(shard)]}
                    # payload["shards"].append()
                    print(payload)
                    # print(str(app.shard_consistent_hashing["sh3"].servers))
                    print(shard_server_name)
                    req_data = await make_request(shard_server_name, payload, "copy", "GET")
                    shard_stored_data = req_data[shard]
                    # for data_tuple in req_data[shard]:
                    #     print(data_tuple, "--------")
                    #     for i, data_element in enumerate(data_tuple):
                    #         shard_stored_data[app.db_schema["columns"][i]] = data_element
                    break
            for new_server in new_server_names:
                request_payload = {
                    "shard": shard,
                    "curr_idx": 0,
                    "data": shard_stored_data
                }
                await make_request(new_server, request_payload, "write", "POST")

    # update the consistent hashing for newly added servers and shards
    for shard in new_shards:
        servers_containing_shard = []
        for server_name in servers.keys():
            if shard["Shard_id"] in servers[server_name]:
                servers_containing_shard.append(server_name)
        server_list = []
        await app.server_id_name_map_lock.acquire()
        await app.shard_consistent_hashing_lock.acquire()
        for server_id in app.server_id_name_map.keys():
            if app.server_id_name_map[server_id] in servers_containing_shard:
                server_list.append({"server_name": app.server_id_name_map[server_id], "server_id": server_id})
        app.shard_consistent_hashing[shard["Shard_id"]] = Consistent_Hashing(app.m, app.reqHash, app.serverHash,
                                                                             server_list)
        app.shard_consistent_hashing_lock.release()
        app.server_id_name_map_lock.release()
    for new_shard in new_shards:
        app.shard_locks[new_shard["Shard_id"]] = asyncio.Lock()
    message = "Add "
    for name in new_server_names:
        message = message + name + ", "
    # message.removesuffix(", ")
    response = {
        "N": f'{len(app.server_id_name_map)}',
        "message": message,
        "status": "successful"
    }
    # print(app.server_id_name_map)
    return response


@app.post('/read')
async def read_data(Stud_id: dict = Body(...)):
    range_stud_id = Stud_id["Stud_id"]
    print(range_stud_id)
    shard_list_for_req = get_shards_for_stud_id_range(range_stud_id["low"], range_stud_id["high"])
    read_output = []
    shards_queried = []
    for shard in shard_list_for_req:
        shards_queried.append(shard["shard"])
        req_id = generate_req_id()
        server_id = app.shard_consistent_hashing[shard["shard"]].get_req_server(req_id)
        server_name = app.server_id_name_map[server_id]
        payload = {"shard": shard["shard"], "Stud_id": shard["range"]}
        await app.shard_locks[shard["shard"]].acquire()
        app.shard_locks[shard["shard"]].release()
        shard_read_data = await make_request(server_name, payload, "read", "POST")
        print(shard_read_data)
        for data_element in shard_read_data["data"]:
            read_output.append(data_element)
    response = {
        "shards_queried": shards_queried,
        "data": read_output,
        "status": "success"
    }
    return response


@app.delete('/rm')
async def remove_replicas(n: int = Body(...), hostnames: list[str] = Body(...)):
    # check if the hostnames are valid
    names = []
    for shard, server_id in app.database_helper.get_server_data():
        names.append(app.server_id_name_map[server_id])

    # check if length of hostnames is less than or equal to n
    if len(hostnames) > n:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return response

    # check if the hostnames are valid
    for hostname in hostnames:
        if hostname not in names:
            response = {
                "message": f"<Error> '{hostname}’ is not a valid server. No server removed",
                "status": "failure"
            }
            return response

    # if n > length of hostnames then remove random servers by inserting names into hostnames
    if len(hostnames) < n:
        for svr in names:
            if svr not in hostnames:
                hostnames.append(svr)
                if len(hostnames) == n:
                    break


    # remove the servers from all places
    for hostname in hostnames:
        server_id = None
        for id, name in app.server_id_name_map.items():
            if name == hostname:
                server_id = id
                break

        if server_id is None:
            print(f"Server ID not found for hostname: {hostname}")
            continue

        del app.server_id_name_map[server_id]

        shards = app.database_helper.get_shard_for_server(server_id)
        shard_list = []
        for tuplee in shards:
            shard_list.append(tuplee[0])

        for shard in shard_list:
            app.shard_consistent_hashing[shard].server_del(server_id)

        # Delete the server from the database helper
        app.database_helper.del_server(str(server_id))

        # delete the server container using docker
        os.system(f"sudo docker container stop {hostname}")



    response = {
        "N": n,
        "servers": hostnames,
        "status": "successful"
    }
    return response


@app.post('/write')
async def write_data(data: dict = Body(...)):
    data1 = data["data"]
    # print(data)
    shard_data_map = get_shards_for_data_write(data1)
    print(shard_data_map)
    for shard in shard_data_map.keys():
        try_again = list(app.shard_consistent_hashing[shard].get_servers().keys())
        # while len(try_again):
        for server in try_again:
            payload = {"shard": str(shard), "data": []}
            for sdata in shard_data_map[shard]["data"]:
                payload["data"].append(sdata)
            payload["curr_idx"] = int(shard_data_map[shard]["curr_idx"])
            # payload["try_again"] = 1
            print(payload, "to server: ", server)
            try:
                # payload = {"shard": "sh1", "data": [{"Stud_id": 1, "Stud_name": "ABC", "Stud_marks": "95"}], "curr_idx": 0}
                response = await make_request(app.server_id_name_map[server], payload, "write", "POST")
                if payload["curr_idx"] + len(payload["data"]) == response["curr_idx"]:
                    print("done deal!!!")
                    # try_again.remove(server)
                else:
                    # print("heyyyyyyyyyyyy")
                    raise Exception("curr_idx less than sent curr_idx + data length")
            except Exception as e:
                print("exception in write", str(e))
                time.sleep(1)
        app.database_helper.update_curr_idx(shard,
                                            shard_data_map[shard]["curr_idx"] + len(shard_data_map[shard]["data"]))
    return {
        "message": f"{len(data1)} Data entries added",
        "status": "success"
    }


###### Implement locking
@app.put('/update')
async def update_data(stud_id: int = Body(...), data: dict = Body(...)):
    # find which shard this student id belongs to using mapT table
    shard_id = app.database_helper.get_shard_id(stud_id)
    shard_id = shard_id[0]
    # find all the servers which contains this shard
    servers_containing_shard = []
    for server_name in app.shard_consistent_hashing[shard_id].get_servers().values():
        servers_containing_shard.append(server_name["name"])

    # update the data in all the servers containing this shard
    for server_name in servers_containing_shard:
        request_payload = {
            "shard": shard_id,
            "data": data,
            "Stud_id": stud_id
        }
        await make_request(server_name, request_payload, "update", "PUT")

    response = {
        "message": f"Data entry for Student ID: {stud_id}' updated",
        "status": "success"
    }
    return response


@app.put('/del')
async def delete_data(stud_id: int = Body(...)):
    shard_id = app.database_helper.get_shard_id(stud_id)
    servers_containing_shard = []
    for server_name in app.shard_consistent_hashing[shard_id].get_servers().values():
        servers_containing_shard.append(server_name["name"])

    for server_name in servers_containing_shard:
        request_payload = {
            "shard": shard_id,
            "Stud_id": stud_id
        }
        await make_request(server_name, request_payload, "delete", "DELETE")

    response = {
        "message": f"Data entry for f'{stud_id}' deleted",
        "status": "success"
    }


# @app.get('/<path:path>')
# async def get(path, request: Request):
#     global server_replicas
#     req_slot = generate_req_id()
#     server_id = server_replicas.ring[server_replicas.get_req_slot(req_slot)]
#     server_name = server_replicas.servers[str(server_id)]["name"]
#
#     if path == "home":
#         res = None
#         await make_request(server_name, {}, "home")
#         await asyncio.sleep(1)
#         return RedirectResponse(request.url)
#         # print("hallelujah!!")
#
#         return res, 200
#     else:
#         errorr = {
#             "message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
#             "status": "failure"
#         }
#         return errorr, 400


def stop_heartbeat():
    pass


if __name__ == '__main__':
    uvicorn.run('0.0.0.0', port=5000)  # Run the Flask app
