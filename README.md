# FinApp

Sprint 1.1 provides a local personal-finance foundation: CSV transaction import,
in-memory storage, monthly/category summaries, and a Streamlit dashboard.

## Run

```bash
uv sync --all-groups
uv run streamlit run src/finapp/presentation/streamlit_app.py
```

Import a CSV containing `date`, `description`, and `amount`; `category` is optional.
Positive amounts are income and negative amounts are expenses.

## Quality checks

```bash
uv run ruff check .
uv run black --check .
uv run mypy src tests
uv run pytest
```
