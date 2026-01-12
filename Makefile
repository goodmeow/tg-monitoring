.PHONY: up status logs restart down build

up:
	@echo "Starting tg-monitoring stack via Docker Compose"
	docker-compose -f docker-compose.postgres.yml up -d

status:
	docker compose -f docker-compose.postgres.yml ps

logs:
	docker compose -f docker-compose.postgres.yml logs -f tg-monitoring

restart:
	$(MAKE) down
	$(MAKE) up

down:
	@echo "Stopping tg-monitoring stack"
	docker-compose -f docker-compose.postgres.yml stop

build:
	@echo "Building tg-monitoring image"
	docker-compose -f docker-compose.postgres.yml build
