VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: venv install run status logs restart stop enable disable fmt

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: venv

run:
		@if systemctl --user is-active --quiet tg-monitor.service; then \
			echo "tg-monitor.service is active; stop it before running make run"; \
			exit 1; \
		fi
		@if [ -f data/tg-monitor.pid ]; then \
			pid=$$(cat data/tg-monitor.pid 2>/dev/null || true); \
			if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
				echo "tg-monitoring already running with PID $$pid (lock file data/tg-monitor.pid)"; \
				exit 1; \
			else \
				echo "Removing stale lock file data/tg-monitor.pid"; \
				rm -f data/tg-monitor.pid; \
			fi; \
		fi
		@if [ -f logs/manual-run.pid ]; then \
			pid=$$(cat logs/manual-run.pid 2>/dev/null || true); \
			if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
				echo "Manual run already active with PID $$pid (logs/manual-run.pid)"; \
				exit 1; \
			else \
				rm -f logs/manual-run.pid; \
			fi; \
		fi
		@mkdir -p logs
		@log_file="logs/manual-run.log"; \
		 ts=$$(date '+%Y-%m-%d %H:%M:%S'); \
		 echo "$$ts starting manual bot run (logs -> $$log_file)"; \
		 (. $(VENV)/bin/activate && { \
			nohup $(PY) -m tgbot.main >> "$$log_file" 2>&1 </dev/null & \
			pid=$$!; \
			echo $$pid > logs/manual-run.pid; \
			echo "$$ts started manual bot PID $$pid" >> "$$log_file"; \
			echo "Manual bot PID $$pid"; \
		 })

status:
	systemctl --user status tg-monitor.service

logs:
	journalctl --user -u tg-monitor.service -f

restart:
		$(MAKE) stop
		systemctl --user enable --now tg-monitor.service
		@mkdir -p logs
		@echo "==== $$(date '+%Y-%m-%d %H:%M:%S') make restart ====" >> logs/systemd-restart.log
		@journalctl --user -u tg-monitor.service --since "1 minute ago" --no-pager >> logs/systemd-restart.log || true

stop:
		@systemctl --user stop tg-monitor.service >/dev/null 2>&1 || true
	@for i in 1 2 3 4 5; do \
		if systemctl --user is-active --quiet tg-monitor.service; then \
			sleep 1; \
		else \
			break; \
		fi; \
	done
	@if systemctl --user is-active --quiet tg-monitor.service; then \
		echo "Forcing tg-monitor.service to terminate"; \
		systemctl --user kill tg-monitor.service >/dev/null 2>&1 || true; \
		sleep 1; \
	fi
	@if systemctl --user is-active --quiet tg-monitor.service; then \
		echo "tg-monitor.service is still active"; \
		exit 1; \
	fi
		@if [ -f data/tg-monitor.pid ]; then \
			pid=$$(cat data/tg-monitor.pid 2>/dev/null || true); \
			if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
				echo "Killing leftover tg-monitoring process $$pid"; \
				kill $$pid >/dev/null 2>&1 || true; \
				for i in 1 2 3; do \
					kill -0 $$pid 2>/dev/null || break; \
					sleep 1; \
				done; \
			fi; \
			rm -f data/tg-monitor.pid; \
		fi
		@if [ -f logs/manual-run.pid ]; then \
			pid=$$(cat logs/manual-run.pid 2>/dev/null || true); \
			if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
				echo "Killing manual-run bot $$pid"; \
				kill $$pid >/dev/null 2>&1 || true; \
				for i in 1 2 3; do \
					kill -0 $$pid 2>/dev/null || break; \
					sleep 1; \
				done; \
			fi; \
			rm -f logs/manual-run.pid; \
		fi
		@systemctl --user disable tg-monitor.service >/dev/null 2>&1 || true

enable:
	mkdir -p ~/.config/systemd/user
	install -m 0644 systemd/tg-monitor.service ~/.config/systemd/user/tg-monitor.service
	systemctl --user daemon-reload
	systemctl --user enable --now tg-monitor.service
