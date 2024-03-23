import requests

# URL where you want to send the request
url = 'http://0.0.0.0:5000/init'

# Body of the request (can be a dictionary, list, string, etc.)
body = {
    "N": 6,
            "schema": {
                "columns": ["Stud_id", "Stud_name", "Stud_marks"],
                "dtypes": ["Number", "String", "String"]},
            "shards": [{"Stud_id_low": 0, "Shard_id": "sh1", "Shard_size": 4096},
                       {"Stud_id_low": 4096, "Shard_id": "sh2", "Shard_size": 4096},
                       {"Stud_id_low": 8192, "Shard_id": "sh3", "Shard_size": 4096},
                       {"Stud_id_low": 12288, "Shard_id": "sh4", "Shard_size": 4096}],
            "servers": {"Server0": ["sh1", "sh2"],
                        "Server1": ["sh3", "sh4"],
                        "Server3": ["sh1", "sh3"],
                        "Server4": ["sh4", "sh2"],
                        "Server5": ["sh1", "sh4"],
                        "Server6": ["sh3", "sh2"]}
}

# Making the POST request with the specified body
response = requests.post(url, json=body)

# Checking the response status
if response.status_code == 200:
    print("Request successful!")
    print("Response body:", response.text)
else:
    print("Request failed with status code:", response.status_code)
