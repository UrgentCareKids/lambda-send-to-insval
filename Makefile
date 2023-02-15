SHELL:=/bin/bash
-include .env/local

export CONTAINER_NAME:=lambda-paylocity-api

.PHONY: help
help:
	@echo "build: build environment"
	@echo "up: bring up environment"
	@echo "logs: view the live logs on the container"
	@echo "execute: run the lambda function (requires 'make up')"
	@echo "format: format code (runs black)"
	@echo "shell: 'ssh' into container"
	@echo "down: clean up environment"

.PHONY: format
format:
	black src/

.PHONY: build
build:
	docker-compose build

.PHONY: up
up:
	docker-compose up -d

.PHONY: logs
logs:
	docker logs -f ${CONTAINER_NAME}

.PHONY: execute
execute:
	curl -XPOST "http://localhost:9090/2015-03-31/functions/function/invocations" -d '{"Records":[{"Sns":{"Message":{}}}]}'

.PHONY: shell
shell:
	docker exec -it ${CONTAINER_NAME} bash

.PHONY: down
down:
	docker-compose down --remove-orphans

# to fix