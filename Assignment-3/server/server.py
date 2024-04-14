import json
from argparse import Namespace

import uvicorn
# from flask_script import Manager, Server
import aiohttp
import os
import helper as db
from logFile import Log, op_type
from fastapi import FastAPI, Request

app = FastAPI()
# manager = Manager(app)

curr_idxs = {}

app.sid = int(os.getenv('SERVER_ID'))
app.server_name = str(os.getenv('SERVER_NAME'))

app.primary_server_for_shards_stored = {}
app.no_of_servers_for_shard = {}


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


@app.post('/server_count_change')
async def server_cnt_change(request: Request):
    payload = await request.json()
    app.no_of_servers_for_shard[payload.get('shard')] += int(payload.get('change'))


@app.post('/config', status_code=200)
async def config(request: Request):
    try:
        payload = await request.json()
        shards = payload.get('shards')
        for shard in shards:
            curr_idxs[shard] = 0
        student_db = db.StudentDatabase()
        conn = student_db.create_connection()
        msg = str(app.sid) + ':'
        msg += str(student_db.create_table(conn, payload))
        msg += 'configured'
        conn.close()
        return {
            "message": msg,
            "status": "success"
        }
        # return jsonify(str(payload.get('shards'))), 200
    except Exception as e:
        raise Exception(e)


@app.get('/heartbeat',status_code=200)
async def heartbeat():
    return {}


@app.get('/copy')
async def copy_data(request:Request):
    payload = await request.json()
    shards = payload.get('shards')
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.copy(conn, shards)
    conn.close()
    response = {}
    for i in range(len(shards)):
        response[shards[i]] = data[i]
    response["status"] = "success"
    return response


@app.exception_handler(500)
async def internal_error(error):
    return error


@app.exception_handler(Exception)
async def exception_handler(error):
    return "!!!!" + repr(error)


@app.post('/read')
async def read_data(request:Request):
    payload = await request.json()
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.read(conn, payload)
    conn.close()
    return {
        "data": data,
        "status": "success"
    }


@app.get('/get_latest_log_index')
async def get_latest_log_index(request:Request):
    max_index = -1
    logs = []
    with open('wal.log', 'r') as file:
        lines = file.readlines()
        for line in lines:
            logs.append(json.loads(line, object_hook=lambda d: Namespace(**d)))
    for log in logs:
        max_index = max(max_index, log.msg_id)
    return max_index


def commit_logs(logs):
    stud_db = db.StudentDatabase()
    conn = stud_db.create_connection()
    for log in logs:
        if log.op_type == op_type.WRITE:
            stud_db.write(conn,log)
        elif log.op_type == op_type.UPDATE:
            stud_db.write(conn,json.loads(log))
        elif log.op_type == op_type.DELETE:
            stud_db.delete(conn,json.loads(log))


async def crash_recovery():
    max_msg_id = -1
    logs = []
    with open('wal.log', 'r') as file:
        lines = file.readlines()
        for line in lines:
            logs.append(json.loads(line, object_hook=lambda d: Namespace(**d)))
    commit_logs(logs)
    for log in logs:
        max_msg_id = max(max_msg_id, log.msg_id)
    logs_to_do: list[Log] = []
    for shard, server_name in app.primary_server_for_shards_stored:
        ret_data = await make_request(server_name, {"shard": shard, "most_recent_msgid": max_msg_id}, "get_missed_logs",
                                      "POST")
        logs_to_do.append(ret_data)
    commit_logs(logs_to_do)

@app.post('/get_missed_logs')
async def get_missed_logs(request:Request):
    payload = await request.json()
    most_recent_msgid = payload.get('most_recent_msgid')
    shard = payload.get('shard')
    missed_logs = []
    logs = []
    with open('wal.log', 'r') as file:
        lines = file.readlines()
        for line in lines:
            logs.append(json.loads(line, object_hook=lambda d: Namespace(**d)))
    for log in logs:
        if log.shard_id == shard and log.msg_id > most_recent_msgid:
            missed_logs.append(log)
    return missed_logs, 200


def append_to_logs(msg_id, shard_id, op_type, data):
    new_Log = Log(msg_id,shard_id,op_type,data)
    with open('wal.log', 'w') as log_file:
        log_file.writelines([json.dumps(new_Log.__dict__)])
    log_file.close()


# needs change different behaviour for primary and secondary
@app.post('/write')
async def write_data(request: Request):
    payloadd = await request.json()
    if payloadd['primary'] != app.sid :
        try:
            shard_id = payloadd.get('shard')
            data = payloadd.get('data')
            append_to_logs(payloadd.get('msg_id'),shard_id,op_type.WRITE,data)
            student_db = db.StudentDatabase()
            conn = student_db.create_connection()
            if payloadd.get("try_again") == 1:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ? ORDER BY ROWID", (shard_id))
                entries_sorted = cursor.fetchall()
                if payloadd.get("curr_idx") < len(entries_sorted):
                    for i in range(payloadd["curr_idx"] + 1, len(entries_sorted)):
                        cursor.execute(f"DELETE FROM ? WHERE Stud_id=?", (payloadd.get("curr_idx"), entries_sorted[i],))
                        cursor.commit()
            message, curr_idx = student_db.write(conn, payloadd)
            # curr_idxs[payload['shard']]=curr_idx
            conn.close()
            return {
                "message": message,  # Provide the actual data read from the database
                "curr_idx": curr_idx,
                "status": "success"
            }
        except Exception as e:
            raise Exception(e)
    else:
        pass

@app.put('/update')
async def update_data(request:Request):
    payload = await request.json()
    append_to_logs(payload.get('msg_id'),payload.get('shard_id'),'update')
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message = student_db.update(conn, payload)
    conn.close()
    return {
        "message": message,
        "status": "success"
    }

@app.get('/get_all_data', methods=['GET'])
def get_all_data():
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.get_all_data_shards_wise(conn)
    conn.close()
    response = {}
    for i in range(len(data)):
        response[data[i][0]] = data[i][1]
    response["status"] = "success"
    return response




@app.delete('/del')
async def delete_data(request:Request):
    payload = await request.json()
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message = student_db.delete(conn, payload)
    conn.close()
    return {
        "message": message,
        "status": "success"
    }


@app.post("/leaderElection")
async def leaderElection(request:Request):
    payload = await request.json()
    app.primary_server_for_shards_stored[payload.get('shard_id')] = payload.get('server_id')


@app.post("/updateServerCount")
async def updateServerCount(request:Request):
    payload = await request.json()
    app.no_of_servers_for_shard[payload.get('shard')] = payload.get('servers')


if __name__ == "__main__":
    crash_recovery()
    uvicorn.run(app, host='0.0.0.0', port=5000)
