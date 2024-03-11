#!/bin/bash
sudo docker stop $(sudo docker ps -q)
sudo docker container prune -f
sudo docker rmi -f $(sudo docker images -aq)
