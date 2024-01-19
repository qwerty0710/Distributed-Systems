import os
import json
import random
import requests
import asyncio
from flask import Flask, request, jsonify
from ConsistentHashing import Consistent_Hashing
from flask_apscheduler import APScheduler

app = Flask(__name__)

# Consistent Hashing

# Number of slots in the ring
m = 512
reqHash = lambda i: (i ** 2 + 2 * i + 17) % m
serverHash = lambda i, j: (i ** 2 + j ** 2 + j * 2 + 25) % m
server_replicas = Consistent_Hashing(m, reqHash, serverHash)
client_info = {}


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
    id = 111111
    while id in client_info.keys():
        id = random.randint(100000, 999999)
    return id


@app.route('/rep', methods=['GET'])
def get_replicas():
    names = []
    for key in server_replicas.servers.keys():
        names.append(server_replicas.servers[key]["name"])
    response = {
        "message": {
            "N": len(server_replicas.servers),
            "replicas": names
        },
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/add', methods=['POST'])
def add_replicas():
    global server_replicas

    req_id = generate_req_id()
    # map the request id to the server in the consistent hashing ring using the request hash function

    request_data = request.get_json(force=True)
    num_new_replicas = request_data["n"]
    hostnames = request_data["hostnames"]
    # Check if the length of the hostname list is less than or equal to the number of new replicas
    if len(hostnames) > num_new_replicas:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return jsonify(response), 400

    # add servers one by one and if n>hostname list then add random servers by generating server id and hostnames
    names = []
    for key in server_replicas.servers.keys():
        names.append(server_replicas.servers[key]["name"])
    for i in range(num_new_replicas):
        server_id = get_smallest_unoccupied_server_id()
        if i < len(hostnames):
            name = hostnames[i]
            if name in names:
                name = "randomserver" + str(server_id)
        else:
            name = "randomserver" + str(server_id)
        server_replicas.add_server(server_id, name)
        names.append(name)
        # spawn new server

    response = {
        "message": {
            "N": len(server_replicas.servers),
            "replicas": names
        },
        "status": "successful"
    }
    print(server_replicas.servers)
    return jsonify(response), 200


@app.route('/rm', methods=['DELETE'])
def remove_replicas():
    global server_replicas
    # req_id = generate_req_id()
    # add_client(request, req_id)
    request_data = request.get_json(force=True)
    num_replicas_to_remove = request_data["n"]
    # preferred hostnames to remove
    hostnames = request_data["hostnames"]
    # check if the length of the hostname list is less than or equal to the number of replicas to remove
    if len(hostnames) > num_replicas_to_remove:
        response = {
            "message": "<Error> Length of hostname list is more than newly added instances",
            "status": "failure"
        }
        return jsonify(response), 400
    names = []
    # remove servers one by one and if n>hostname list then remove random servers from the list of servers
    for i in range(num_replicas_to_remove):
        if i < len(hostnames):
            # remove the server from the list of servers
            for key in server_replicas.servers.keys():
                if server_replicas.servers[key]["name"] == hostnames[i]:
                    server_replicas.server_del(key)
                    break
        else:
            # remove random server from the list of servers
            server_key = random.choice(list(server_replicas.servers.keys()))
            server_replicas.server_del(server_key)
    for key in server_replicas.servers.keys():
        names.append(server_replicas.servers[key]["name"])
    response = {
        "message": {
            "N": len(server_replicas.servers),
            "replicas": names
        },
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/<path:path>', methods=['GET'])
def get(path):
    req_id = generate_req_id()
    req_slot = reqHash(req_id)
    server_id = server_replicas.ring[server_replicas.get_req_slot(req_slot)]
    # print("Request served by server " + str(server_id))
    client_ip = request.remote_addr
    client_port = request.environ.get('REMOTE_PORT')
    payload = {"ip": client_ip, "port": client_port}
    server_port = 5001 + server_id
    name = server_replicas.servers[server_id]["name"]
    if path == "home":
        res = requests.get(f"http://{name}:{server_port}/home", json=payload)
        if res.status_code == 200:
            # do stats
            pass
    else:
        errorr = {
            "message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
            "status": "failure"
        }
        return jsonify(errorr), 400
    return jsonify({}), 400


@app.errorhandler(404)
def own_404_page(error):
    pageName = request.args.get('url')
    errorr = {
        "message": f"<Error> ’/’ endpoint does not exist in server replicas",
        "status": "failure"
    }
    return jsonify(errorr), 400


# def test_job():
#     for key in server_replicas.servers.keys():
#         #res = requests.get(f"http://{name}:{server_port}/heartbeat", json=payload)
#         #if res.status_code == 200
#             pass


if __name__ == '__main__':
    app.run('0.0.0.0', 5000)
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(id='test-job', func=test_job, trigger='interval', seconds=1)
