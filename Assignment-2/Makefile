build:
	docker compose build

run lb:
	docker compose up lb

run server:
	docker compose up server

down:
	docker compose down

clean:
	sudo docker rmi -f $(sudo docker images -aq)

rstop:
	docker container prune -f