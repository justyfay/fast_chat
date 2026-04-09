.PHONY: help \
        install lint format \
        migrate-up migrate-down migrate-create \
        run \
        docker-up docker-down docker-build docker-logs \
        celery celery-beat flower \
        clean

UV := uv run
APP := src.fast_chat.main:app
CELERY_APP := src.fast_chat.tasks.celery_app:celery

help: ## Справка
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости через uv
	uv sync

lint: ## Проверить код через ruff
	$(UV) ruff check .

format: ## Отформатировать код через ruff
	$(UV) ruff format .
	$(UV) ruff check --fix .

migrate-up: ## Применить все миграции
	$(UV) alembic upgrade head

migrate-down: ## Откатить последнюю миграцию
	$(UV) alembic downgrade -1

migrate-create: ## Создать новую миграцию: make migrate-create MSG="описание"
	$(UV) alembic revision --autogenerate -m "$(MSG)"

docker-pull: ## Скачать сторонние Docker-образы (без сборки)
	docker compose pull postgres pgadmin redis

docker-build: ## Собрать локальные Docker-образы
	docker compose build

docker-stop: ## Остановить все сервисы (без удаления контейнеров)
	docker compose stop

docker-down: ## Остановить и удалить контейнеры
	docker compose down

docker-start: docker-stop docker-pull docker-build  ## Поднять все сервисы
	docker compose up -d

docker-restart: docker-down docker-pull docker-build ## Пересобрать и перезапустить все сервисы
	docker compose up -d

celery: ## Запустить Celery worker, beat и flower
	$(UV) celery --app=$(CELERY_APP) worker -l INFO
	$(UV) celery --app=$(CELERY_APP) beat -l DEBUG
	$(UV) celery --app=$(CELERY_APP) flower

run-dev: docker-start celery ## Запустить сервер через uvicorn
	$(UV) uvicorn $(APP) --reload --host 0.0.0.0 --port 8000

run-dev-w-recreate: docker-restart celery ## Запустить сервер через uvicorn (с пересборкой всех сервисов)
	$(UV) uvicorn $(APP) --reload --host 0.0.0.0 --port 8000

run: docker-start celery  ## Запустить сервер через gunicorn (prod)
	$(UV) gunicorn $(APP) --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000


clean: ## Удалить кэш Python и ruff
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
