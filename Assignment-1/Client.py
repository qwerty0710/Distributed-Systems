import asyncio
import aiohttp
import json
import requests


async def send_request_rm(url):
    async with aiohttp.ClientSession() as session:
        payload = {
            "n": 3,
            "hostnames": ["Rahul", "Adithya"]
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
            "n": 3,
            "hostnames": ["Rahul", "Adithya"]
        }
        async with session.post(url, data=json.dumps(payload)) as response:
            return await response.json(content_type="application/json")


async def main():
    tasks = []
    '''
    for i in range(10000):
        task = asyncio.create_task(send_request("http://localhost:5000/home"))
        tasks.append(task)
    '''
    # task = asyncio.create_task(send_request_home("http://localhost:5000/home"))
    # tasks.append(task)
    task = asyncio.create_task(send_request_add("http://localhost:5000/add"))
    tasks.append(task)
    results = await asyncio.gather(*tasks)
    print(results)
    task = asyncio.create_task(send_request_rm("http://localhost:5000/rm"))
    tasks = []
    tasks.append(task)
    results = await asyncio.gather(task)
    print(results)


if __name__ == '__main__':
    asyncio.run(main())
