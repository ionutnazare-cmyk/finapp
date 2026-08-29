from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from finapp.application.dto import PortfolioReport, PortfolioValuation, PositionValuation
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.reporting.pdf_exporter import PdfPortfolioReportExporter


def _valuation() -> PortfolioValuation:
    position = PositionValuation(
        symbol="TLV",
        quantity=Decimal("100"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
        market_price=Money(amount=Decimal("4.50"), currency=Currency.RON),
        book_cost=Money(amount=Decimal("400.00"), currency=Currency.RON),
        market_value=Money(amount=Decimal("450.00"), currency=Currency.RON),
        unrealized_pnl=Money(amount=Decimal("50.00"), currency=Currency.RON),
    )
    return PortfolioValuation(
        portfolio_name="Retirement",
        base_currency_total_book_cost=Money(amount=Decimal("400.00"), currency=Currency.RON),
        base_currency_total_market_value=Money(amount=Decimal("450.00"), currency=Currency.RON),
        base_currency_total_unrealized_pnl=Money(amount=Decimal("50.00"), currency=Currency.RON),
        positions=(position,),
    )


def test_exports_a_valid_pdf_file(tmp_path: Path) -> None:
    report = PortfolioReport(
        portfolio_name="Retirement",
        generated_at=datetime(2026, 8, 27, tzinfo=UTC),
        valuation=_valuation(),
    )
    output_path = tmp_path / "report.pdf"

    result_path = PdfPortfolioReportExporter().export(report, output_path)

    assert result_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert output_path.read_bytes().startswith(b"%PDF")


def test_creates_parent_directories(tmp_path: Path) -> None:
    report = PortfolioReport(
        portfolio_name="Retirement",
        generated_at=datetime(2026, 8, 27, tzinfo=UTC),
        valuation=_valuation(),
    )
    output_path = tmp_path / "nested" / "dir" / "report.pdf"

    PdfPortfolioReportExporter().export(report, output_path)

    assert output_path.exists()


def test_handles_empty_portfolio_without_error(tmp_path: Path) -> None:
    empty_valuation = PortfolioValuation(
        portfolio_name="Empty",
        base_currency_total_book_cost=Money(amount=Decimal("0"), currency=Currency.RON),
        base_currency_total_market_value=Money(amount=Decimal("0"), currency=Currency.RON),
        base_currency_total_unrealized_pnl=Money(amount=Decimal("0"), currency=Currency.RON),
        positions=(),
    )
    report = PortfolioReport(
        portfolio_name="Empty",
        generated_at=datetime(2026, 8, 27, tzinfo=UTC),
        valuation=empty_valuation,
    )
    output_path = tmp_path / "empty.pdf"

    PdfPortfolioReportExporter().export(report, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
