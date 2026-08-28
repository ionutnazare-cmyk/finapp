# FinApp

Professional dividend investing and retirement optimizer, focused initially on the
**Bucharest Stock Exchange (BVB)**.

> Status: **Sprint 1.1 — Project Bootstrap**. Domain logic has not been implemented
> yet; this sprint establishes the repository skeleton, tooling, and CI so future
> sprints can build features on a stable foundation.

## Vision

FinApp will eventually support:

- Portfolio management
- Monthly DCA (dollar-cost averaging) investing
- Dividend reinvestment
- TLV bonus share tracking
- Monte Carlo simulations
- Portfolio optimization
- Retirement planning
- Fair value estimation
- Dividend safety scoring
- A Streamlit dashboard
- Excel/PDF reporting
- Automatic BVB data updates

## Architecture

FinApp follows **Clean Architecture** with **Domain-Driven Design** where it adds
clarity, and is built with strong typing (Pydantic v2 + dataclasses) throughout.

```
src/finapp/
├── domain/            # Entities, value objects, domain services. No framework deps.
├── application/       # Use cases, ports (interfaces), application services.
├── infrastructure/    # Adapters: data providers, repositories, file I/O, external APIs.
├── presentation/       # CLI and Streamlit dashboard entry points.
└── config.py          # Application-wide, environment-driven settings.
```

Dependency direction always points inward: `presentation` and `infrastructure`
depend on `application`, which depends on `domain`. `domain` depends on nothing
in this project.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details and the roadmap of
future sprints.

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency and environment management

## Getting started

```bash
# Install dependencies (creates .venv automatically)
uv sync --extra dev

# Run the CLI placeholder
PYTHONPATH=src uv run finapp

# Run the Streamlit dashboard
PYTHONPATH=src uv run streamlit run src/finapp/presentation/streamlit_app.py
```

Open the app and use the pages in the sidebar menu:

- **Portfolio Overview** — create a portfolio, buy/sell shares, and see
  valuation, dividend income, and bonus share issues
- **Monte Carlo** — project a range of future portfolio values
- **Retirement Planning** — simulate contributions then withdrawals, and your
  probability of running out of money
- **Portfolio Optimizer** — mean-variance optimal weights for a set of assets
  (not tied to a stored portfolio — enter your own assumptions)
- **Fair Value** — Gordon Growth DDM, dividend yield target, and P/E-relative
  valuation for any symbol (not tied to a stored portfolio)
- **Dividend Safety** — a transparent, rule-based dividend safety score
  (not tied to a stored portfolio) FinApp reads market prices, dividends, and bonus issues
from local CSV files under `./data/` (created automatically on first run —
edit them directly, then use the "Reload data files" button in the app):

```
data/quotes.csv          # symbol,price,currency,as_of
data/dividends.csv       # symbol,amount_per_share,currency,pay_date
data/bonus_issues.csv    # symbol,new_shares_per_held_share,record_date
data/portfolios/         # one JSON file per portfolio, written by the app
```

These files are gitignored by default since they hold your personal
portfolio data; see `tests/fixtures/*.csv` for example rows to get started.

> **Note:** `PYTHONPATH=src` works around an editable-install quirk on some
> `uv` setups where the local `finapp` package's `.pth` redirect isn't picked
> up by `uv run` even though `uv pip show finapp` reports it installed. If
> `uv run finapp` works for you without it, feel free to drop it. `make run`
> and `make dashboard` already include it.

## Quality checks

```bash
uv run ruff check .
uv run black --check .
uv run mypy src tests
uv run pytest
```

All four checks are enforced in CI on every push and pull request (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Project layout

```
finapp/
├── src/finapp/                 # Application source (see Architecture above)
├── tests/                      # PyTest test suite, mirrors src/finapp layout
├── docs/                       # Architecture notes and sprint roadmap
├── .github/workflows/ci.yml    # Lint, type-check, test pipeline
├── pyproject.toml              # Packaging, dependencies, tool configuration
├── Makefile                    # Convenience commands
└── README.md
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, coding standards,
and commit conventions.

## License

[MIT](LICENSE)
