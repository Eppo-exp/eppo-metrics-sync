make test:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Activating virtual environment and installing dependencies..."
	@. .venv/bin/activate && \
		pip freeze > /tmp/requirements_to_uninstall.txt && \
		if [ -s /tmp/requirements_to_uninstall.txt ]; then pip uninstall -y -r /tmp/requirements_to_uninstall.txt; fi && \
		pip install -r requirements.txt && \
		pytest tests
