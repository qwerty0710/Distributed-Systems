import asyncio
import aiohttp
import json
import requests


async def send_request_rm(url):
    async with aiohttp.ClientSession() as session:
        payload = {
            "n": 1,
            "hostnames": ["server2"]
        }
        async with session.delete(url, data=json.dumps(payload)) as response:
            return await response.json(content_type="application/json")


async def send_request_home(url):
    async with aiohttp.ClientSession() as session:
        # payload = {
        #     "ip": "localhost",
        #     "port": 5005
        # }
        async with session.get(url) as response:
            return await response.json(content_type="application/json")


async def send_request_add(url):
    async with aiohttp.ClientSession() as session:
        payload = {
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
        async with session.get(url, data=json.dumps(payload)) as response:
            return await response.json(content_type="application/json")


payload = { # payload for adding a new shard
    "N": 2,
    "new_shards": [{"Stud_id_low": 12288, "Shard_id": "sh5", "Shard_size": 4096}],
    "servers": {"Server4": ["sh3", "sh5"], "Server[5]": ["sh2", "sh5"]}
}



async def main():
    tasks = []
    # task = asyncio.create_task(send_request_home("http://localhost:5000/home"))
    # tasks.append(task)
    # task = asyncio.create_task(send_request_add("http://localhost:5000/add"))
    # tasks.append(task)
    # results = await asyncio.gather(*tasks)
    # print(results)
    task = asyncio.create_task(send_request_add("http://0.0.0.0:5000/heartbeat"))
    tasks = []
    tasks.append(task)
    results = await asyncio.gather(task)
    print(results)


if __name__ == '__main__':
    asyncio.run(main())
