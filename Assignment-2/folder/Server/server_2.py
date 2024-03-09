from flask import Flask, request, jsonify
import sqlite3
import os
import table1 as db
app = Flask(__name__,template_folder='.')

# Endpoint to initialize shard tables in the server database
@app.route('/home' , methods =['GET'])
def home():
    return "Home"
@app.route('/config', methods=['POST'])
def initialize_shards():
    server_id = os.getenv('SERVER_ID', 'Unknown')
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    msg=server_id+':'
    msg+=str(student_db.create_table(conn,payload))
    msg+='configured'
    conn.close()
    return jsonify({
        "message": msg,
        "status": "success"
    }), 200

# Endpoint to send heartbeat responses
@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return jsonify({"Response": " "}),200

# Endpoint to copy data entries corresponding to one shard table in the server container
@app.route('/copy', methods=['GET'])
def copy_data():
    
    payload = request.json
    shards = payload.get('shards')
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    #data=student_db.copy(conn,payload)
    data=student_db.copy(conn,shards)
    
    
    return jsonify({
        shards[0] : data[0],
        shards[1] : data[1],
        "status": "success"
    }), 200

# Endpoint to read data entries from a shard in a particular server container
@app.route('/read', methods=['POST'])
def read_data():
    
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    data=student_db.read(conn,payload)
    return jsonify({
        "data": data,  # Provide the actual data read from the database
        "status": "success"
    }), 200

# Endpoint to write data entries in a shard in a particular server container
@app.route('/write', methods=['POST'])
def write_data():
    
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message,curr_idx=student_db.write(conn,payload)
    return jsonify({
        "message": message,  # Provide the actual data read from the database
        "current_idx": curr_idx,
        "status": "success"
    }), 200
    
# Endpoint to update a particular data entry in a shard in a particular server container
@app.route('/update', methods=['PUT'])
def update_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message=student_db.update(conn,payload)
    return jsonify({
        "message": message,
        "status": "success"
    }), 200


# Endpoint to delete a particular data entry in a shard in a particular server container
@app.route('/del', methods=['DELETE'])
def delete_data():
    payload = request.json
    student_db = db.StudentDatabase()
    conn = student_db.create_connection()
    message=student_db.delete(conn,payload)
    return jsonify({
        "message": message,
        "status": "success"
    }), 200

if  __name__ == '__main__':
    # app.run(debug=True,host='0.0.0.0')
    app.run(host='0.0.0.0',port=5000,debug=True)
