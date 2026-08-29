from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.export_portfolio_report import (
    ExportPortfolioReport,
    ReportFormat,
)
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from finapp.infrastructure.reporting.excel_exporter import ExcelPortfolioReportExporter
from finapp.infrastructure.reporting.pdf_exporter import PdfPortfolioReportExporter


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )


@pytest.fixture
def repository() -> InMemoryPortfolioRepository:
    tlv = Instrument(
        symbol="TLV", name="Banca Transilvania", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    repo = InMemoryPortfolioRepository()
    repo.save(portfolio)
    return repo


def test_exports_excel_format(repository: InMemoryPortfolioRepository, tmp_path: Path) -> None:
    use_case = ExportPortfolioReport(
        repository,
        StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")}),
        ExcelPortfolioReportExporter(),
        PdfPortfolioReportExporter(),
    )
    output_path = tmp_path / "report.xlsx"

    result = use_case.execute("Retirement", output_path, ReportFormat.EXCEL)

    assert result == output_path
    assert output_path.exists()


def test_exports_pdf_format(repository: InMemoryPortfolioRepository, tmp_path: Path) -> None:
    use_case = ExportPortfolioReport(
        repository,
        StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")}),
        ExcelPortfolioReportExporter(),
        PdfPortfolioReportExporter(),
    )
    output_path = tmp_path / "report.pdf"

    result = use_case.execute("Retirement", output_path, ReportFormat.PDF)

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")


def test_missing_portfolio_raises(tmp_path: Path) -> None:
    use_case = ExportPortfolioReport(
        InMemoryPortfolioRepository(),
        StaticMarketDataProvider({}),
        ExcelPortfolioReportExporter(),
        PdfPortfolioReportExporter(),
    )
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent", tmp_path / "report.xlsx", ReportFormat.EXCEL)
