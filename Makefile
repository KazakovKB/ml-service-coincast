.PHONY: up tests init-db down all

# Поднять все сервисы (без init-db и tests)
up:
	docker compose up -d --build database rabbitmq app web-proxy bot

# Запустить тесты
tests:
	docker compose run --rm tests

# Проинициализировать базу демо-данными
init-db:
	docker compose run --rm init-db

# Остановить и удалить все сервисы
down:
	docker compose down

all: up tests init-db