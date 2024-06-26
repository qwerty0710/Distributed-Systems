import asyncio
import math
import time
import requests
import matplotlib.pyplot as plt
import aiohttp

# Assuming the load balancer is running at http://localhost:5000
load_balancer_url = "http://localhost:5000"


# Function to make HTTP requests to the load balancer
async def make_request(session, endpoint):
    url = f"{load_balancer_url}{endpoint}"
    async with session.get(url) as response:
        return await response.json()


# A-1: Launch 10000 async requests on N = 3 server containers
async def task_A1():
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, "/home") for _ in range(10000)]
        return await asyncio.gather(*tasks)


server_counts = {}


# Plotting function for A-1
def plot_request_distribution(request_responses, server_count):
    global server_counts
    server_counts = {f"Server {i}": 0 for i in range(0, server_count)}

    for response in request_responses:
        try:
            server_number = response.get('message', '').split(':')[-1].strip()
            if server_number and server_number.isdigit():
                server_counts[f"Server {server_number}"] += 1
            else:
                print(f"Invalid server number extracted from response: {response}")
        except Exception as e:
            print(f"Failed to extract server number from response: {response}. Error: {e}")

    servers = list(server_counts.keys())
    request_counts = list(server_counts.values())

    addlabels(servers, request_counts)
    plt.bar(servers, request_counts)
    plt.xlabel('Server Containers')
    plt.ylabel('Request Count')
    plt.title('Request Distribution Among Server Containers')
    plt.show()


def addlabels(x, y):
    for i in range(len(x)):
        plt.text(i, y[i], y[i], ha='center')


# Run the A-1 task and plot the results
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    timeb = time.time()
    # Run the A-1 task
    server_count = 6
    request_responses = loop.run_until_complete(task_A1())

    # print(time.time()-timeb)
    # Plot the request distribution
    plot_request_distribution(request_responses, server_count)
    std_dvn = 0
    for key in server_counts.keys():
        std_dvn += ((server_counts[key] - 10000 / server_count) ** 2)
    std_dvn = math.sqrt(std_dvn / server_count)
    print(std_dvn)
