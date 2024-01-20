# Distributed-Systems
Following are some of the observations for the load balancer. <br />
# A-1 : Launch 10000 async requests on N = 3 server containers and report the request count handled by each server instance in a bar chart. Explain your observations in the graph and your view on the performance. <br />
# A-2 : increment N from 2 to 6 and launch 10000 requests on each such increment. Report the average load of the servers at each run in a line chart. Explain your observations in the graph and your view on the scalability of the load balancer implementation.
# A-3 : Test all endpoints of the load balancer and show that in case of server failure, the load balancer spawns a new instance quickly to handle the load.

# Run the following command to build the docker image of load balancer
```bash
sudo docker build -t lb .
```
# Run the following command to start the load balancer container
```bash
sudo docker run --rm --name lb --network net1 --ip=172.18.0.2 --network-alias lb -p 5000:5000 lb
```
# Run the following command to build the docker image of server
```bash
sudo docker build -t server -f "./Dockerfile_server" .
```
# Run the following command to start the server container
```bash
sudo docker run --rm --name server0 --network net1 --ip=172.18.0.3  -p 5001:5000 --network-alias server0 -e SERVER_ID=0 server
```

