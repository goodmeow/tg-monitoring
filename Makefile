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
	. $(VENV)/bin/activate && $(PY) -m monitor.main

status:
	systemctl --user status tg-monitor.service

logs:
	journalctl --user -u tg-monitor.service -f

restart:
	systemctl --user restart tg-monitor.service

stop:
	systemctl --user disable --now tg-monitor.service || true

enable:
	mkdir -p ~/.config/systemd/user
	install -m 0644 systemd/tg-monitor.service ~/.config/systemd/user/tg-monitor.service
	systemctl --user daemon-reload
	systemctl --user enable --now tg-monitor.service

