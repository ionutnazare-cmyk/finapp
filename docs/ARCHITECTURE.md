# Architecture

FinApp is built with **Clean Architecture**, **SOLID** principles, and
**Domain-Driven Design** patterns where they add clarity. This document defines
the layering rules established in Sprint 1.1 that all future sprints must follow.

## Layers

```
┌──────────────────────────────────────────────────────────┐
│ presentation   (Streamlit dashboard, CLI)                 │
├──────────────────────────────────────────────────────────┤
│ infrastructure (BVB data providers, Excel/PDF exporters,   │
│                 repositories, external APIs)               │
├──────────────────────────────────────────────────────────┤
│ application    (use cases, ports/interfaces, orchestration)│
├──────────────────────────────────────────────────────────┤
│ domain         (entities, value objects, domain services)  │
└──────────────────────────────────────────────────────────┘
```

### `domain/`

Framework-independent business rules: `Portfolio`, `Position`, `Dividend`,
`Instrument`, `Money`/`Currency` value objects, and domain services such as
dividend safety scoring or fair value estimation logic. No imports from
`application`, `infrastructure`, `presentation`, or any I/O library
(no `pandas`, `streamlit`, `requests`, etc. in this layer).

### `application/`

Use cases (e.g. `RunMonteCarloSimulation`, `RebalancePortfolio`,
`ProjectRetirement`) and the **ports** (abstract interfaces) that
`infrastructure` implements (e.g. `MarketDataProvider`, `PortfolioRepository`,
`ReportExporter`). Depends only on `domain`.

### `infrastructure/`

Concrete adapters implementing application ports: BVB data scrapers/API
clients, CSV/JSON/Excel repositories, PDF/Excel report writers. Depends on
`application` (to implement its ports) and `domain`.

### `presentation/`

The Streamlit dashboard and the CLI. Wires use cases to user input/output.
Depends on `application`, `infrastructure` (for composition/wiring), and
`domain`.

## Dependency Rule

Dependencies only point inward:

```
presentation → infrastructure → application → domain
presentation → application → domain
```

`domain` never imports from any other layer. `application` never imports from
`infrastructure` or `presentation`. This is enforced by convention and code
review in Sprint 1.1; automated import-linting may be added in a later sprint.

## Typing & Validation

- All domain entities and DTOs crossing layer boundaries use **Pydantic v2**
  models or frozen `dataclasses` for immutability where mutation isn't needed.
- `mypy --strict` is enforced across `src/`.
- Monetary values use `Decimal`, never `float`, to avoid rounding errors in
  financial calculations.

## Roadmap (indicative, subject to change)

| Sprint | Scope |
|--------|-------|
| 1.1 | Project bootstrap: repo skeleton, tooling, CI, empty layers — **done** |
| 1.2 | Core domain model: `Instrument`, `Position`, `Portfolio`, `Money` — **done** |
| 1.3 | BVB market data provider (infrastructure) + application port — **done** |
| 1.4 | Portfolio management use cases (add/remove position, valuation) — **done** |
| 1.5 | Monthly DCA investing use case — **done** |
| 1.6 | Dividend tracking and reinvestment — **done** |
| 1.7 | TLV bonus share handling — **done** |
| 1.8 | Streamlit dashboard: portfolio overview — **done** |
| 1.9 | Monte Carlo simulation engine — **done** |
| 1.10 | Portfolio optimization (SciPy-based) — **done** |
| 1.11 | Retirement planning module — **done** |
| 1.12 | Fair value estimation models — **done** |
| 1.13 | Dividend safety scoring |
| 1.14 | Excel/PDF reporting |
| 1.15 | Automatic BVB data update scheduler |

This table will be refined as each sprint is planned in detail.
