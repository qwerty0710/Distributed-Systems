from flask import Flask, request, jsonify
import os
import helper as db

app = Flask(__name__)

# Placeholder for shard data
shard_data = {}

sid = os.getenv('SERVER_ID', 'Unknown')


@app.route('/config', methods=['POST'])
def config():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    msg = sid + ':'
    msg += str(student_db.create_table(conn, payload))
    msg += 'configured'
    conn.close()
    return jsonify({
        "message": msg,
        "status": "success"
    }), 200


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return '', 200


@app.route('/copy', methods=['GET'])
def copy_data():
    payload = request.json
    shards = payload.get('shards')
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.copy(conn, shards)
    response = {}
    for i in range(len(shards)):
        response[shards[i]] = data[i]
    response["status"] = "success"
    return jsonify(response), 200


@app.route('/read', methods=['POST'])
def read_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.read(conn, payload)
    return jsonify({
        "data": data,
        "status": "success"
    }), 200


@app.route('/write', methods=['POST'])
def write_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message, curr_idx = student_db.write(conn, payload)
    return jsonify({
        "message": message,  # Provide the actual data read from the database
        "current_idx": curr_idx,
        "status": "success"
    }), 200


@app.route('/update', methods=['PUT'])
def update_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message = student_db.update(conn, payload)
    return jsonify({
        "message": message,
        "status": "success"
    }), 200


@app.route('/del', methods=['DELETE'])
def delete_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message = student_db.delete(conn, payload)
    return jsonify({
        "message": message,
        "status": "success"
    }), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
