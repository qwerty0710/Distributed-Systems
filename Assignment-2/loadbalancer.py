import asyncio
import json
import os
import random
from array import array

import aiohttp
from aiodocker import Docker
import requests
import uvicorn
from fastapi import FastAPI, Body, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from docker
from ConsistentHashing import Consistent_Hashing
import mysql as sql
import mysql.connector

app = FastAPI()

# Number of slots in the ring
# m = int(os.getenv("m"))
app.m = 512
# reqHash = lambda i: (67 * i ** 3 + 3 * i ** 2 + 53 * i + 97) % m
app.reqHash = lambda i: (i ** 2 + 2 * i + 17) % app.m
# serverHash = lambda i, j: (59 * i ** 2 + 73 + 29 * j ** 2 + j * 7 + 73) % m
app.serverHash = lambda i, j: (i ** 2 + j ** 2 + j * 2 + 25) % app.m

app.server_replicas = {}
app.shard_consistent_hashing = {}
app.client_info = {}
app.db_config = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "root",
    "database": "metadata"
}


def add_client(request, req_id):
    global client_info
    client_info[req_id] = request.remote_addr


def get_smallest_unoccupied_server_id():
    global server_replicas
    occupied_ids = server_replicas.servers.keys()
    occupied_ids = list(map(int, occupied_ids))
    smallest_id = 0
    while smallest_id in occupied_ids:
        smallest_id = smallest_id + 1
    return smallest_id


def generate_req_id():
    id = random.randint(100000, 999999)
    return id


async def spawn_new_server(servers):
    async def spawn_server(docker, name, server_id):
        container = await docker.containers.create_or_replace({
            "name": name,
            "image": "server",
            "networks": ["net1"],
            "network_aliases": [name],
            "environment": {"SERVER_ID": server_id},
            "detach": True
        })
        await container.start()

    async with Docker() as docker:
        tasks = []
        for server_name in servers:
            server_id = get_smallest_unoccupied_server_id()
            tasks.append(spawn_server(docker, server_name, server_id))
        await asyncio.gather(*tasks)


def check_heartbeat(server=None, server_id=None):
    global server_replicas
    servers_alive = []
    if server is None:
        for key in server_replicas.servers.keys():
            server_name = server_replicas.servers[key]["name"]
            res = None
            try:
                res = requests.get(f"http://{server_name}:5000/heartbeat")
                if res is not None:
                    if res.status_code == 200:
                        servers_alive.append(server_name)

            except requests.exceptions.ConnectionError:
                server_id = key
                name = server_name
                cmd = os.popen(f"sudo docker run --rm --name {name} "
                               f"--network net1 "
                               f"--network-alias {name} "
                               f"-e SERVER_ID={server_id} "
                               f"-d server").read()
                if len(cmd) == 0:
                    print(f"Unable to start server with server id: {server_id}")
                    # server_replicas.server_del(server_id)
                else:
                    print(f"Successfully started server with server id: {server_id}")
                    servers_alive.append(server_name)


    else:
        res = None
        try:
            res = requests.get(f"http://{server}:5000/heartbeat")
            if res is not None:
                if res.status_code == 200:
                    servers_alive.append(server)

        except requests.exceptions.ConnectionError:
            cmd = os.popen(f"sudo docker run --rm --name {server} "
                           f"--network net1 "
                           f"--network-alias {server} "
                           f"-e SERVER_ID={server_id} "
                           f"-d server").read()
            if len(cmd) == 0:
                print(f"Unable to start server with server id: {server_id}")
                # server_replicas.server_del(server_id)
            else:
                print(f"Successfully started server with server id: {server_id}")
                servers_alive.append(server)

    return servers_alive


@app.post('/init')
async def init(n: int = Body(...), schema: dict[str, array[str]] = Body(...), shards: list[dict] = Body(...),
               servers: dict = Body(...)):
    # get data from the request fastAPI
    shard_to_server = {}
    for server in servers:
        shard_to_server[server] = []
        for shard in server:
            server_id = get_smallest_unoccupied_server_id()
            shard_to_server[shard].append(server_id)
    for shard in shard_to_server.keys():
        app.shard_consistent_hashing[shard] = Consistent_Hashing(n, app.reqHash, app.serverHash, shard_to_server[shard])
    # create shardT and mapT in SQL
    curx = sql.connector.connect(**app.db_config)
    cursor = curx.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS metadata")
    cursor.execute(f"USE metadata")
    cursor.execute(f"CREATE TABLE IF NOT EXISTS mapT (shard_id varchar(255), server_id INT)")
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS shardT (stud_id_low INT PRIMARY KEY, shard id INT NOT NULL, shard size INT NOT NULL, valid_idx INT NOT NULL)")
    curx.commit()
    for server in servers.keys():
        for shard in servers[server]:
            cursor.execute(f"INSERT INTO mapT (shard_id, server_id) VALUES ({shard}, {server})")
    for shard in shards:
        cursor.execute(
            f"INSERT INTO shardT (stud_id_low, shard_id, shard_size, valid_idx) VALUES ({shard['Stud_id_low']}, {shard['Shard_id']}, {shard['Shard_size']}, {shard['valid_idx']})")
    curx.commit()
    curx.close()
    # spawn the servers and initialize the shards
    for server_name in servers.keys():
        spawn_new_server(server_name[6:], server_name)

    # hit the '/config' endpoint of the servers to initialize the shards using aiohttp
    async def config_shards(server_name, payload):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://{server_name}:5000/config", data=json.dumps(payload)) as response:
                return await response.json(content_type="application/json")

    for server_name in servers.keys():
        payload = {"shards": servers[server_name], "schema": schema}
        await config_shards(server_name, payload)

    response = {
        "message": "Configured database",
        "status": "success"
    }
    return response, status.HTTP_200_OK


@app.get('/rep')
def get_replicas():
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
                       servers: dict[str, list[any]] = Body(...)):
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


        for server_name in servers.keys():

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
        try:
            res = requests.get(f"http://{server_name}:5000/home", timeout=1)
        except requests.exceptions.ConnectionError or requests.exceptions.Timeout:
            spawn_new_server(server_id, server_name)
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
