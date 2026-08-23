"""Dividend adapters implementing :class:`finapp.application.ports.DividendProvider`."""

from __future__ import annotations

from finapp.infrastructure.dividends.csv_provider import CsvDividendProvider
from finapp.infrastructure.dividends.static_provider import StaticDividendProvider

__all__ = ["CsvDividendProvider", "StaticDividendProvider"]
