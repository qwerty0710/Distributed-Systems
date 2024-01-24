
# Distributed-Systems Assignment 1
# Run the following command to build the docker image of load balancer and server
```bash
sudo make build
```
# Run the following command to start the load balancer container
```bash
sudo make lb
```
# Run the following command to start the 3 initial server containers
```bash
sudo make server
```

Following are some of the observations for the load balancer. <br />
# A-1 : Launch 10000 async requests on N = 3 server containers and report the request count handled by each server instance in a bar chart. Explain your observations in the graph and your view on the performance. <br />
![Alt Text](Assignment-1/TestCode/N3.png?raw=true "Title")
<br />
<br />
As we can see from the above graph, the load balancer is able to distribute the load among the 3 servers but it is not fully equally distributed as it depends on the hash function. But the servers were able to handle 10000 asynchronous requests. <br />
# A-2 : increment N from 2 to 6 and launch 10000 requests on each such increment. Report the average load of the servers at each run in a line chart. Explain your observations in the graph and your view on the scalability of the load balancer implementation.


# A-3 : Test all endpoints of the load balancer and show that in case of server failure, the load balancer spawns a new instance quickly to handle the load.



