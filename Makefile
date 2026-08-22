.PHONY: help up down restart clean shell seed

help:
	@echo "kistn CLI - Development Commands"
	@echo "--------------------------------"
	@echo "  make up         - Build and start Docker containers in background"
	@echo "  make down       - Stop Docker containers"
	@echo "  make restart    - Restart Docker containers"
	@echo "  make clean      - Stop containers and purge all Docker volumes"
	@echo "  make shell      - Open interactive bash shell in the app container"
	@echo "  make seed       - Generate mock test files inside the app container"

up:
	docker compose up -d --build

down:
	docker compose down

restart: down up

clean:
	docker compose down -v

shell:
	docker compose exec -it app bash

seed:
	docker compose exec app bash /app/scripts/seed-data.sh

# test-setup: up
# 	@sleep 2
# 	$(MAKE) seed
# 	@echo "--- 1. Testing 'kistn setup' ---"
# 	docker compose exec app kistn setup --user u123456 --host mock-storagebox --port 22 --no-prompt
# 	@echo "--- 2. Testing 'kistn run' ---"
# 	docker compose exec app kistn run
# 	@echo "--- 3. Testing 'kistn status' ---"
# 	docker compose exec app kistn status
