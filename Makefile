.PHONY: run status logs restart stop

run:
	@echo "Starting tg-monitoring stack via Docker Compose"
	docker compose -f docker-compose.postgres.yml up -d

status:
	docker compose -f docker-compose.postgres.yml ps

logs:
	docker compose -f docker-compose.postgres.yml logs -f tg-monitoring

restart:
	$(MAKE) stop
	$(MAKE) run

stop:
	@echo "Stopping tg-monitoring stack"
	docker compose -f docker-compose.postgres.yml stop
