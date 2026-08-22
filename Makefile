.PHONY: sync fmt lint typecheck test check run dashboard clean

sync:
	uv sync --extra dev

fmt:
	uv run black .
	uv run ruff check --fix .

lint:
	uv run ruff check .
	uv run black --check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest

check: lint typecheck test

run:
	PYTHONPATH=src uv run finapp

dashboard:
	PYTHONPATH=src uv run streamlit run src/finapp/presentation/streamlit_app.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml dist build *.egg-info
