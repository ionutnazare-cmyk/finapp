# FinApp

FinApp is a local personal-finance application. Sprint 1 provides CSV transaction
import and a Streamlit dashboard. Sprint 2 adds a deterministic, Decimal-based
portfolio simulation engine.

## Architecture

The project uses Clean Architecture under `src/finapp`:

- `domain` contains framework-independent portfolio and transaction models.
- `application` contains use cases and provider/repository ports.
- `infrastructure` contains adapters, including the JSON static-price provider.
- `presentation` contains the Streamlit application and CLI.

## Setup and dashboard

```bash
uv sync --all-groups
uv run streamlit run src/finapp/presentation/streamlit_app.py
```

The dashboard accepts a transaction CSV with `date`, `description`, and `amount`.
`category` is optional. Positive amounts are income and negative amounts expenses.

## Simulation engine

The simulator creates one investment event for each month in the inclusive range,
allocates every contribution, records BUY ledger transactions, and retains unspent
cash (for example, where whole shares are required). Money is calculated with
`Decimal`; binary floating-point values are not used for financial calculations.

Prices are supplied outside the engine through a market-data provider. The included
adapter reads JSON in this format:

```json
{
  "TLV": {"2026-01-01": "40", "2026-02-01": "40"},
  "SNP": {"2026-01-01": "0.85", "2026-02-01": "0.85"},
  "H2O": {"2026-01-01": "120", "2026-02-01": "120"}
}
```

Run a simulation (the default price file is `prices.json`):

```bash
uv run finapp simulate \
  --from 2026-01 \
  --to 2027-12 \
  --monthly 4000 \
  --allocation TLV=40,SNP=35,H2O=25 \
  --prices prices.json
```

Use `--whole-shares` to disable fractional shares and `--broker-fee 2.50` to apply
a fixed fee to each executed BUY. The CLI prints the portfolio summary, allocation,
cash, and transactions.

## Quality checks

```bash
uv run ruff check .
uv run black --check .
uv run mypy src tests
uv run pytest
```
