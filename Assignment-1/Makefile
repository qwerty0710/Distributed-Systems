build:
	docker compose build

run lb:
	docker compose up lb

run server:
	docker compose up server0 server1 server2

down:
	docker compose down

clean:
	docker ps -aq | xargs docker rm -f

rstop:
	docker container prune -f