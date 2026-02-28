VENV = .venv
PYTHON = $(VENV)/bin/python

.PHONY: run install clean

run: $(VENV)/bin/activate
	$(PYTHON) bot.py

install: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	touch $(VENV)/bin/activate

clean:
	rm -rf $(VENV)
