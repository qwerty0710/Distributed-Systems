import os
import json
import random
import requests
import asyncio
from flask import Flask, request, jsonify
from ConsistentHashing import Consistent_Hashing

app = Flask(__name__)

# Consistent Hashing

# Number of slots in the ring
m = 512
reqHash = lambda i: (i ** 2 + 2 * i + 17) % m
serverHash = lambda i, j: (i ** 2 + j ** 2 + j * 2 + 25) % m
server_replicas = Consistent_Hashing(m, reqHash, serverHash, 3)

# List of all the servers
servers = []


def get_smallest_unoccupied_server_id():
    occupied_ids = {server['id'] for server in servers}
    smallest_id = 1
    while smallest_id in occupied_ids:
        smallest_id += 1
    return smallest_id


@app.route('/rep', methods=['GET'])
def get_replicas():
    response = {
        "message": {
            "N": len(servers),
            "replicas": servers
        },
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/add', methods=['POST'])
def add_replicas():
    request_data = request.get_json()
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
    for i in range(num_new_replicas):
        if i < len(hostnames):
            # assign the least unoccupied server id by
            server_id = get_smallest_unoccupied_server_id()
            server_replicas.add_server(server_id, hostnames[i])
        else:
            server_id = get_smallest_unoccupied_server_id()
            # generate random server name
            server_name = "Randomserver" + str(server_id)
            server_replicas.add_server(server_id, server_name)
        # add the server to the list of servers
        servers.append({
            "id": server_id,
            "hostname": server_replicas.servers[str(server_id)]
        })

    response = {
        "message": {
            "N": len(servers),
            "replicas": servers
        },
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/rm', methods=['DELETE'])
def remove_replicas():
    request_data = request.get_json()
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

    # remove servers one by one and if n>hostname list then remove random servers from the list of servers
    for i in range(num_replicas_to_remove):
        if i < len(hostnames):
            # remove the server from the list of servers
            for server in servers:
                if server["hostname"] == hostnames[i]:
                    servers.remove(server)
                    server_replicas.server_del(server["id"])
                    break
        else:
            # remove random server from the list of servers
            server = random.choice(servers)
            servers.remove(server)
            server_replicas.server_del(server["id"])

    response = {
        "message": {
            "N": len(servers),
            "replicas": servers
        },
        "status": "successful"
    }
    return jsonify(response), 200

@app.route('/<path:path>', methods=['GET'])
def get(path):
    # get the hash slot of the request
    hash_slot = server_replicas.get_req_slot(path)
    # get the server id from the hash slot
    server_id = server_replicas.ring[hash_slot]
    # get the server hostname from the server id
    server_hostname = server_replicas.servers[str(server_id)]
    # get the response from the server
    response = requests.get("http://" + server_hostname + "/" + path)
    return response.text, response.status_code