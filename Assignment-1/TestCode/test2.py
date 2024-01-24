import asyncio
import requests
import matplotlib.pyplot as plt
import aiohttp
import time

# Assuming the load balancer is running at http://localhost:5000
load_balancer_url = "http://localhost:5000"

# Function to make HTTP requests to the load balancer with a retry mechanism
async def make_request(session, endpoint):
    url = f"{load_balancer_url}{endpoint}"
    for _ in range(3):  # Retry up to 3 times
        try:
            async with session.get(url) as response:
                return await response.json()
        except aiohttp.client_exceptions.ClientOSError as e:
            print(f"Error: {e}. Retrying in 1 second.")
            time.sleep(1)  # Wait for 1 second before retrying
    raise RuntimeError("Failed to make request after multiple retries.")

# A-2: Increment N from 2 to 6 and launch 10000 requests on each such increment
async def task_A2(num_containers):
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, "/home") for _ in range(10000)]
        return await asyncio.gather(*tasks)

# Function to calculate average load
def calculate_average_load(request_responses):
    server_counts = {f"Server {i}": 0 for i in range(0, 3)}

    for response in request_responses:
        try:
            server_number = response.get('message', '').split(':')[-1].strip()
            if server_number and server_number.isdigit():
                server_counts[f"Server {server_number}"] += 1
            else:
                print(f"Invalid server number extracted from response: {response}")
        except Exception as e:
            print(f"Failed to extract server number from response: {response}. Error: {e}")

    total_requests = sum(server_counts.values())
    average_load = {server: count / total_requests for server, count in server_counts.items()}

    return average_load

# Corrected Plotting function for A-2
def plot_average_loads(average_loads):
    x_values = list(range(0, 7))

    for server, loads in average_loads.items():
        plt.plot(x_values, loads, marker='o', label=server)

    plt.xlabel('Number of Server Containers (N)')
    plt.ylabel('Average Load on Servers')
    plt.title('Average Load on Servers with Increasing N')
    plt.legend()
    plt.show()

# Run the A-2 task and plot the results
if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Perform A-2 for N from 2 to 6
    average_loads = {}
    for num_containers in range(2, 6):
        request_responses = loop.run_until_complete(task_A2(num_containers))
        average_load = calculate_average_load(request_responses)
        average_loads[f"N={num_containers}"] = list(average_load.values())

    # Plot the average loads
    plot_average_loads(average_loads)

