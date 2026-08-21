# Contributing to FinApp

## Development environment

FinApp uses [`uv`](https://docs.astral.sh/uv/) for dependency and virtual
environment management, and Python 3.12.

```bash
uv sync --extra dev
```

## Workflow

1. Create a branch off `main`: `git checkout -b sprint-x.y-short-description`.
2. Make your changes inside the correct architectural layer (see
   [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
3. Add or update tests under `tests/`, mirroring the `src/finapp` package
   structure.
4. Run all quality gates locally before opening a pull request:

   ```bash
   uv run ruff check .
   uv run black --check .
   uv run mypy src tests
   uv run pytest
   ```

5. Open a pull request describing the sprint/task it addresses.

## Coding standards

- **Formatting**: `black`, line length 100. Run `uv run black .` to format.
- **Linting**: `ruff`, configuration in `pyproject.toml`.
- **Typing**: `mypy --strict`. All public functions and methods must be fully
  typed. No `Any` without justification.
- **Money**: always use `Decimal`, never `float`, for monetary values.
- **Immutability**: prefer frozen dataclasses / Pydantic models with
  `model_config = {"frozen": True}` for domain value objects.
- **Layering**: respect the dependency rule in
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — `domain` must never import
  from `application`, `infrastructure`, or `presentation`.

## Commit messages

Use concise, imperative-mood messages, optionally prefixed with the sprint
number, e.g.:

```
[1.1] Bootstrap project skeleton and tooling
```

## Tests

- Unit tests live under `tests/`, mirroring the `src/finapp` layout
  (e.g. `tests/domain/test_money.py`).
- Aim for high coverage on `domain` and `application` layers in particular,
  since they contain the core business logic.
