import json

from flask import Flask, request, jsonify
import os
import helper as db

app = Flask(__name__)

curr_idxs = {}

sid = int(os.getenv('SERVER_ID'))


@app.route('/config', methods=['POST'])
def config():
    try:
        payloadd = request.json
        shards = payloadd.get('shards')
        for shard in shards:
            curr_idxs[shard] = 0
        student_db = db.StudentDatabase()
        conn = student_db.create_connection()
        msg = str(sid) + ':'
        msg += str(student_db.create_table(conn, payloadd))
        msg += 'configured'
        conn.close()
        return jsonify({
            "message": msg,
            "status": "success"
        }), 200
        # return jsonify(str(payloadd.get('shards'))), 200
    except Exception as e:
        raise Exception(e)


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return jsonify({}), 200


@app.route('/copy', methods=['GET'])
def copy_data():
    payload = request.json
    shards = payload.get('shards')
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.copy(conn, shards)
    conn.close()
    response = {}
    for i in range(len(shards)):
        response[shards[i]] = data[i]
    response["status"] = "success"
    return jsonify(response), 200


@app.errorhandler(500)
def internal_error(error):
    return error


@app.errorhandler(Exception)
def exception_handler(error):
    return "!!!!" + repr(error)


@app.route('/read', methods=['POST'])
def read_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data = student_db.read(conn, payload)
    conn.close()
    return jsonify({
        "data": data,
        "status": "success"
    }), 200


@app.route('/write', methods=['POST'])
def write_data():
    payloadd = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    if payloadd.get("try_again") == 1:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ? ORDER BY ROWID",(payloadd.get("shard")))
        entries_sorted= cursor.fetchall()
        if payloadd.get("curr_idx")<len(entries_sorted):
            for i in range(payloadd["curr_idx"]+1,len(entries_sorted)):
                cursor.execute(f"DELETE FROM ? WHERE Stud_id=?", (payloadd.get("curr_idx"),entries_sorted[i],))
                cursor.commit()
    message, curr_idx = student_db.write(conn, payloadd)
    # curr_idxs[payload['shard']]=curr_idx
    conn.close()
    return jsonify({
        "message": message,  # Provide the actual data read from the database
        "curr_idx": curr_idx,
        "status": "success"
    }), 200


@app.route('/update', methods=['PUT'])
def update_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message = student_db.update(conn, payload)
    conn.close()
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
    conn.close()
    return jsonify({
        "message": message,
        "status": "success"
    }), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
