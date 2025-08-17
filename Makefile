.PHONY: up wait init-db tests down all

export COMPOSE_PROJECT_NAME := ml-service-coincast

up:
	docker compose up -d database rabbitmq app web-proxy bot worker

wait: up
	# ждём Postgres
	docker compose exec -T database sh -c 'until pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB -h 127.0.0.1; do sleep 1; done'
	# ждём RabbitMQ
	docker compose exec -T rabbitmq sh -c 'rabbitmq-diagnostics -q ping'

# Инициализация демо-данных
init-db: wait
	docker compose run --rm --no-deps init-db

# Тесты
tests: init-db
	docker compose run --rm --no-deps tests

down:
	docker compose down -v --remove-orphans

all: tests
