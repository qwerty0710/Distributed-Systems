import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/home', methods=['GET'])
def req_home():
    server_id = os.getenv('SERVER_ID')
    args=request.args
    print(args['req_id'])
    response = {
        "message": f"Hello from Server: {server_id}",
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/heartbeat', methods=['GET'])
def req_heartbeat():
    return '', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
