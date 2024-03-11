import asyncio
import json
import os
import random
import re
from array import array
from contextlib import asynccontextmanager
from copy import copy

import aiohttp
from aiodocker import Docker

import uvicorn
from fastapi import FastAPI, Body, status, Request
from fastapi.responses import RedirectResponse
from ConsistentHashing import Consistent_Hashing
from lb_db_helper import db_helper
import sqlite3


@asynccontextmanager
async def lifespan(app: FastAPI):
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


def get_smallest_unoccupied_server_id():
    occupied_ids = []
    for server_id in app.server_id_name_map.keys():
        occupied_ids.append(server_id)
    occupied_ids = list(map(int, occupied_ids))
    smallest_id = 0
    while smallest_id in occupied_ids:
        smallest_id = smallest_id + 1
    return smallest_id


async def generate_req_id():
    id = random.randint(000000, 999999)
    return id


async def spawn_new_servers(servers_id_name_map):
    for server_id in servers_id_name_map.keys():
        cmd = os.popen(f"sudo docker run --rm --name {servers_id_name_map[server_id]} "
                       f"--network net1 "
                       f"--network-alias {servers_id_name_map[server_id]} "
                       f"-e SERVER_ID={int(server_id)} "
                       f"-d server").read()
        if len(cmd) == 0:
            print(f"Unable to start server with server id: {server_id} with name {servers_id_name_map[server_id]}")
            # server_replicas.server_del(server_id)
        else:
            print(f"Successfully started server with server id: {server_id} with name {servers_id_name_map[server_id]}")


async def check_heartbeat():
    pass


async def make_request(server_name, payload, path, method):
    try:
        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(f"http://{server_name}:5000/{path}", json=payload,
                                        timeout=2) as response:
                    content = await response.read()
                    # print(content)
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        print(return_obj)
                        return return_obj
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
            elif method == "GET":
                # print("OKKK")
                async with session.get(f"http://{server_name}:5000/{path}", json=payload,
                                       timeout=2) as response:
                    content = await response.read()
                    # print(content)
                    if response.status != 404:
                        return_obj = await response.json(content_type="application/json")
                        print(return_obj)
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
        return {"message": f"<Error> {e}",
                "status": "failure"}, 400


@app.post('/init', status_code=status.HTTP_200_OK)
async def init(N: int = Body(...), schema: dict = Body(...), shards: list[dict] = Body(...),
               servers: dict = Body(...)):
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
        app.shard_consistent_hashing[shard] = Consistent_Hashing(app.m, app.reqHash, app.serverHash, server_config)
    print(str(app.shard_consistent_hashing))
    for shard in shards:
        shard["curr_idx"] = 0
        app.database_helper.add_shard(shard)
    for server in app.server_id_name_map.keys():
        for shard in servers[app.server_id_name_map[server]]:
            app.database_helper.add_server(shard, server)
    await spawn_new_servers(app.server_id_name_map)

    # hit the '/config' endpoint of the servers to initialize the shards using aiohttp
    for sname in servers.keys():
        payload = {"shards": servers[sname], "schema": schema}
        await asyncio.gather(asyncio.create_task(make_request(sname, payload, "config", "POST")))

    response = {
        "message": "Configured database",
        "status": "success"
    }
    return response


@app.get('/status')
async def get_status():
    shard_tuples = app.database_helper.get_shard_data()
    shards = []
    for stud_id_low, shard_id, shard_size in shard_tuples:
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
    hostnames = copy(list(servers.keys()))
    if len(hostnames) != N:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return response
    names = []
    mapT_data = app.database_helper.get_server_data()
    print(mapT_data)
    for shard, server_id in mapT_data:
        names.append(app.server_id_name_map[server_id])
    # adding the new data in database
    for shard in new_shards:
        shard["curr_idx"] = 0
        app.database_helper.add_shard(shard)
    for server in servers:
        for shard_ in server:
            app.database_helper.add_server(shard_, server)

    # add servers one by one and if n>hostname list then add random servers by generating server id and hostnames
    # names = check_heartbeat()
    new_server_names = []
    for i in range(len(hostnames)):
        server_id = get_smallest_unoccupied_server_id()
        name = hostnames[i]
        if (name in names) or not (bool(re.match(r"^[a-zA-Z][a-zA-Z0-9-]{0,61}$", name))):
            name = "randomserver" + str(server_id)
        # spawn new server
        await spawn_new_servers({str(server_id): name})
        hostnames[i] = name
        app.server_id_name_map[server_id] = name  ###
        names.append(name)
        new_server_names.append(name)

    # add new server to the old shards consistent hashing
    all_shards_req = [] # all shards of this request old and new shards
    for server_name in hostnames:
        for shard in servers[server_name]:
            all_shards_req.append(shard)
    for shard in all_shards_req:
        if shard in app.shard_consistent_hashing.keys():  # if the shard is old shard (consustent hashing is not yet updated)
            servers_containing_shard = []
            for server_name in hostnames:
                if shard in servers[server_name]:
                    servers_containing_shard.append(server_name)
            server_id_list = []
            for server_id in app.server_id_name_map.keys():
                if app.server_id_name_map[server_id] in servers_containing_shard:
                    server_id_list.append(server_id)
            for new_server_id in server_id_list:
                app.shard_consistent_hashing[shard].add_server(new_server_id, app.server_id_name_map[new_server_id])

    # bring the data stored in old shards to the new server
    for shard in all_shards_req:
        if shard in app.shard_consistent_hashing.keys():
            new_server_names = []
            shard_stored_data = {}
            for server_name in servers.keys():
                if shard in servers[server_name]:
                    new_server_names.append(server_name)
            for shard_server_name in app.shard_consistent_hashing[shard].get_servers().values():
                if shard_server_name not in new_server_names:
                    # shard_to_get_data = [shard]
                    # print(shard_to_get_data)
                    payload = {"shards": ["sh3"]}
                    # payload = {}
                    # payload["shards"] = []
                    # payload["shards"].append(str(shard))
                    print(payload)
                    # print(str(app.shard_consistent_hashing["sh3"].servers))
                    req_data = await make_request(shard_server_name["name"], payload, "copy", "GET")
                    shard_stored_data = {}
                    print(req_data)
                    for data_tuple in req_data:
                        for i, data_element in enumerate(data_tuple):
                            shard_stored_data[app.db_schema["columns"][i]] = data_element
                    break
            for new_server in new_server_names:
                request_payload = {
                    "shard": shard,
                    "curr_idx": 0,
                    "data": shard_stored_data[shard]
                }
                await make_request(new_server, request_payload, "write", "POST")

    # update the consistent hashing for newly added servers and shards
    for shard in new_shards:
        servers_containing_shard = []
        for server_name in servers.keys():
            if shard["Shard_id"] in servers[server_name]:
                servers_containing_shard.append(server_name)
        server_id_list = []
        for server_id in app.server_id_name_map.keys():
            if app.server_id_name_map[server_id] in servers_containing_shard:
                server_id_list.append(server_id)
        app.shard_consistent_hashing[shard["Shard_id"]] = Consistent_Hashing(app.m, app.reqHash, app.serverHash,
                                                                             server_id_list)

    message = "Add "
    for name in new_server_names:
        message = message + name + ", "
    message.removesuffix(", ")
    response = {
        "N": f'{len(app.server_id_name_map)}',
        "message": message,
        "status": "successful"
    }
    # print(app.server_id_name_map)
    return response


@app.delete('/rm')
async def remove_replicas(request: Request):
    global server_replicas
    request_data = json.loads(await request.body())[0]
    num_replicas_to_remove = request_data["n"]
    # preferred hostnames to remove
    hostnames = request_data["hostnames"]
    # check if the length of the hostname list is less than or equal to the number of replicas to remove
    if len(hostnames) > num_replicas_to_remove:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return response, status.HTTP_400_BAD_REQUEST
    names = []
    # remove servers one by one and if n>hostname list then remove random servers from the list of servers
    for i in range(num_replicas_to_remove):
        del_key = ""
        if i < len(hostnames):
            # remove the server from the list of servers
            for key in server_replicas.servers.keys():
                if server_replicas.servers[key]["name"] == hostnames[i]:
                    del_key = key
                    break
        else:
            # remove random server from the list of servers
            server_key = random.choice(list(server_replicas.servers.keys()))
            del_key = server_key
        os.system(
            f"sudo docker stop {server_replicas.servers[del_key]['name']} ")
        server_replicas.server_del(del_key)
    names = check_heartbeat()
    response = {
        "message": {
            "N": len(names),
            "replicas": names
        },
        "status": "successful"
    }
    return response


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
