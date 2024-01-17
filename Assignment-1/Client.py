import asyncio
import aiohttp

async def send_request(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def main():
    tasks = []
    for i in range(10000):
        task = asyncio.create_task(send_request("http://localhost:5000/home"))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    print(results)

if __name__ == '__main__':
    asyncio.run(main())
