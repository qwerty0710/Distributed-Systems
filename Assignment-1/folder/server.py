import os

import gunicorn
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/home', methods=['GET'])
def home():
    server_id = os.getenv('SERVER_ID', 'Unknown')
    response = {
        "message": f"Hello from Server: {server_id}",
        "status": "successful"
    }
    return jsonify(response), 200


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return '', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threading=True)
