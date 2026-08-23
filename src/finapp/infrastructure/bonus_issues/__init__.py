"""Bonus issue adapters implementing :class:`finapp.application.ports.BonusIssueProvider`."""

from __future__ import annotations

from finapp.infrastructure.bonus_issues.csv_provider import CsvBonusIssueProvider
from finapp.infrastructure.bonus_issues.static_provider import StaticBonusIssueProvider

__all__ = ["CsvBonusIssueProvider", "StaticBonusIssueProvider"]
