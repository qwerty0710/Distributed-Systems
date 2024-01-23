import asyncio
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
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                else:
                    print(f"Received unexpected content type: {content_type}. Using default response.")
                    return {"message": "Unexpected response format", "status": "failure"}
        except aiohttp.client_exceptions.ClientOSError as e:
            print(f"Error: {e}. Retrying in 1 second.")
            time.sleep(1)  # Wait for 1 second before retrying
    raise RuntimeError("Failed to make request after multiple retries.")

# Function to simulate stopping a server container (simulate failure)
def simulate_server_failure():
    # You can use Docker SDK or other tools to stop a server container
    # For simplicity, let's assume you have a command to stop a container
    stopped_container_id = "6c70ca5951fd"
    # Replace the following line with the actual command to stop a container
    # Example: subprocess.run(["docker", "stop", stopped_container_id], check=True)
    print(f"Simulating server failure: Stopped container {stopped_container_id}")

# A-3: Test load balancer endpoints and simulate server failure
async def task_A3():
    # Test /rep endpoint
    async with aiohttp.ClientSession() as session:
        rep_response = await make_request(session, "/rep")
        print("Response from /rep endpoint:", rep_response)

    # Test /add endpoint (add new server instances)
    add_payload = {"n": 2, "hostnames": ["S7", "S8"]}
    async with aiohttp.ClientSession() as session:
        add_response = await session.post(f"{load_balancer_url}/add", json=add_payload)
        add_response_data = await add_response.json()
        print("Response from /add endpoint:", add_response_data)

    # Simulate stopping a server container (simulate failure)
    simulate_server_failure()

    # Wait for a brief moment to allow the load balancer to detect failure and spawn a new instance
    await asyncio.sleep(5)

    # Test /home endpoint again after failure (should route to a new instance)
    async with aiohttp.ClientSession() as session:
        home_response_after_failure = await make_request(session, "/home")
        print("Response from /home endpoint after failure:", home_response_after_failure)

# Run the A-3 task
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(task_A3())

