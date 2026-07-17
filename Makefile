.PHONY: up status logs restart down build daily-restart full-stop

up:
	@echo "Starting tg-monitoring via systemd"
	sudo systemctl enable --now tg-monitor.service

status:
	sudo systemctl status tg-monitor.service

logs:
	journalctl -u tg-monitor.service -f

restart:
	sudo systemctl restart tg-monitor.service

daily-restart:
	@echo "Performing daily restart of tg-monitoring via systemd"
	sudo systemctl restart tg-monitor.service

down:
	@echo "Stopping tg-monitoring via systemd"
	sudo systemctl stop tg-monitor.service

full-stop:
	@echo "Stopping tg-monitoring and disabling watchdog"
	sudo systemctl stop tg-monitoring-watchdog.timer tg-monitoring-watchdog.service
	sudo systemctl disable tg-monitoring-watchdog.timer
	sudo systemctl stop tg-monitor.service

build:
	@echo "Building tg-monitoring image"
	docker compose -f docker-compose.yml build
