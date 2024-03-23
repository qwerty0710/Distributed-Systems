# DISTRIBUTED SYSTEMS ASSIGNMENT 2
In the second assignment we implement a sharded database that stores only one table in multiple shards distributed across several server containers.There are several endpoints to handle requests to a specific server.
We also improve the load balancer from the previous assignment and finally analyse the performance of the developed distributed database.

## Run the following command to build the docker image of load balancer and server
```bash
sudo make build
```
## Run the following command to start the load balancer container
```bash
sudo make lb
```
## Run the following command to start the 3 initial server containers
```bash
sudo make server
```
