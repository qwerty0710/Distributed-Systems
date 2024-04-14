build:
	docker compose build

run lb:
	docker compose up lb

down:
	docker compose down

clean:
	sudo docker rmi -f $(sudo docker images -aq)

cstop:
	sudo docker stop $(sudo docker ps -q)

cclean:
	docker container prune -f