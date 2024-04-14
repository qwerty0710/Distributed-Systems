build:
	docker compose build

run :
	docker compose up lb shm

down:
	docker compose down

clean:
	sudo docker rmi -f $(sudo docker images -aq)

cstop:
	sudo docker stop $(sudo docker ps -q)

cclean:
	docker container prune -f