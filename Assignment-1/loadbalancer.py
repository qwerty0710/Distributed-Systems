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


# List of all the servers
# servers = server_replicas.servers


def get_smallest_unoccupied_server_id():
    occupied_ids = server_replicas.servers.keys()
    occupied_ids = sorted(occupied_ids)
    smallest_id = 0
    while smallest_id in occupied_ids:
        smallest_id += 1
    return smallest_id


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
    names = []
    for key in server_replicas.servers.keys():
        names.append(server_replicas.servers[key]["name"])
    for i in range(num_new_replicas):
        if i < len(hostnames):
            # assign the least unoccupied server id by
            server_id = get_smallest_unoccupied_server_id()
            name = hostnames[i]
            if name in names:
                name = "Randomserver" + str(server_id)
            server_replicas.add_server(server_id, name)
        else:
            server_id = get_smallest_unoccupied_server_id()
            # generate random server name
            server_name = "Randomserver" + str(server_id)
            server_replicas.add_server(server_id, server_name)

    response = {
        "message": {
            "N": len(server_replicas.servers),
            "replicas": names
        },
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/rm', methods=['DELETE'])
def remove_replicas():
    global server_replicas
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
    names = []
    for key in server_replicas.servers.keys():
        names.append(server_replicas.servers[key]["name"])
    # remove servers one by one and if n>hostname list then remove random servers from the list of servers
    for i in range(num_replicas_to_remove):
        if i < len(hostnames):
            # remove the server from the list of servers
            for key in server_replicas.servers.keys():
                if server_replicas.servers[key]["name"] == hostnames[i]:
                    server_replicas.server_del(server_replicas.servers[key]["id"])
                    break
        else:
            # remove random server from the list of servers
            server_key = random.choice(server_replicas.servers.keys())
            server_replicas.server_del(server_replicas.servers[server_key])

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
    if path == "home":
        print("bsdk")
    elif path == "heartbeat":
        print("mc")
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


def test_job():
    pass


if __name__ == '__main__':
    app.run('127.0.0.1', 5000)
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(id='test-job', func=test_job, trigger='interval', seconds=1)
