import asyncio
import json
import os
import random
from array import array

import aiohttp
from aiodocker import Docker

import uvicorn
from fastapi import FastAPI, Body, status, Request
from fastapi.responses import RedirectResponse
from ConsistentHashing import Consistent_Hashing
from lb_db_helper import db_helper
import sqlite3

app = FastAPI()

# Number of slots in the ring
# m = int(os.getenv("m"))
app.m = 512
# reqHash = lambda i: (67 * i ** 3 + 3 * i ** 2 + 53 * i + 97) % m
app.reqHash = lambda i: (i ** 2 + 2 * i + 17) % app.m
# serverHash = lambda i, j: (59 * i ** 2 + 73 + 29 * j ** 2 + j * 7 + 73) % m
app.serverHash = lambda i, j: (i ** 2 + j ** 2 + j * 2 + 25) % app.m
app.database_helper = db_helper("lb_db")

app.server_id_name_map = {}
app.shard_consistent_hashing = {}
app.client_info = {}
app.db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "port": "3306"
}


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
    # async def spawn_server(docker: Docker, name: str, server_id: int):
    #     container = await docker.containers.create_or_replace(name=name,
    #                                                           config={
    #                                                               "image": "server",
    #                                                               "networks": ["net1"],
    #                                                               "network_aliases": [name],
    #                                                               "environment": {"SERVER_ID": server_id},
    #                                                               "detach": True
    #                                                           })
    #     await container.start()
    # async with Docker() as docker:
    #     tasks = []
    #     for server_name in servers:
    #         server_id = get_smallest_unoccupied_server_id()
    #         tasks.append(spawn_server(docker, server_name, server_id))
    #     await asyncio.gather(*tasks)
    # print("helloooooooooooo")
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


async def make_request(server_name, payload, path):
    session_timeout = aiohttp.ClientTimeout(total=None, sock_connect=2, sock_read=2)
    async with aiohttp.ClientSession(timeout=session_timeout) as session:
        async with session.post(f"http://{server_name}:5000/{path}", data=json.dumps(payload), timeout=2) as response:
            return await response.json(content_type="application/json")


@app.post('/init', status_code=status.HTTP_200_OK)
async def init(N: int = Body(...), schema: dict = Body(...), shards: list[dict] = Body(...),
               servers: dict = Body(...)):
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
            shard_to_server[servers[server][i]].append(server_id)
    # passing server names and ids in a dict to consistent hashing for each shard
    for shard in shard_to_server.keys():
        server_config = []
        for server_id in shard_to_server[shard]:
            server_config.append({"server_name": app.server_id_name_map[str(server_id)], "server_id": server_id})
        app.shard_consistent_hashing[shard] = Consistent_Hashing(app.m, app.reqHash, app.serverHash, server_config)
    for shard in shards:
        app.database_helper.add_shard(shard)
    for server in servers.keys():
        for shard in servers[server]:
            app.database_helper.add_server(shard, server)
    await spawn_new_servers(app.server_id_name_map)

    # hit the '/config' endpoint of the servers to initialize the shards using aiohttp

    for sname in servers.keys():
        payload = {"shards": servers[sname], "schema": schema}
        await make_request(sname, payload, "config")

    response = {
        "message": "Configured database",
        "status": "success"
    }
    return response


@app.get('/rep')
async def get_replicas():
    names = check_heartbeat()
    response = {
        "message": {
            "N": len(names),
            "replicas": names
        },
        "status": "successful"
    }
    return response


@app.post('/add')
async def add_replicas(n: int = Body(...), new_shards: list[dict] = Body(...),
                       servers: dict = Body(...)) -> dict[str, str]:
    # map the request id to the server in the consistent hashing ring using the request hash function

    hostnames: array[str] = array("u", servers.keys())
    # Check if the length of the hostname list is less than or equal to the number of new replicas
    if len(hostnames) > n:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return response, status.HTTP_400_BAD_REQUEST

    # add servers one by one and if n>hostname list then add random servers by generating server id and hostnames
    names = []
    names = check_heartbeat()
    for i in range(n):
        server_id = get_smallest_unoccupied_server_id()
        if i < len(hostnames):
            name = hostnames[i]
            if name in names:
                name = "randomserver" + str(server_id)
        else:
            name = "randomserver" + str(server_id)

        # spawn new server
        await spawn_new_servers(name)
        names.append(name)
    message = "Add "
    for name in names:
        message = message + name + ", "
    message.removesuffix(", ")
    response = {
        "N": len(server_replicas.servers),
        "message": message,
        "status": "successful"
    }
    print(app.server_replicas.servers)
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


@app.get('/<path:path>')
async def get(path, request: Request):
    global server_replicas
    req_slot = generate_req_id()
    server_id = server_replicas.ring[server_replicas.get_req_slot(req_slot)]
    server_name = server_replicas.servers[str(server_id)]["name"]

    if path == "home":
        res = None
        await make_request(server_name, {}, "home")
        await asyncio.sleep(1)
        return RedirectResponse(request.url)
        # print("hallelujah!!")

        return res, 200
    else:
        errorr = {
            "message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
            "status": "failure"
        }
        return errorr, 400


if __name__ == '__main__':
    uvicorn.run('0.0.0.0', port=5000)  # Run the Flask app
