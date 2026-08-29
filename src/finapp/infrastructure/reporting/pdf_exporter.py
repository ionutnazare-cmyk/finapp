"""PDF export of a :class:`PortfolioReport`, using reportlab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from finapp.application.dto import PortfolioDividendIncome, PortfolioReport
from finapp.application.ports import PortfolioReportExporter

_TABLE_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]
)
_POSITION_HEADERS = (
    "Symbol",
    "Quantity",
    "Avg Cost",
    "Price",
    "Book Cost",
    "Market Value",
    "Unrealized P&L",
)
_DIVIDEND_HEADERS = ("Symbol", "Quantity Held", "Amount/Share", "Pay Date", "Total Income")


class PdfPortfolioReportExporter(PortfolioReportExporter):
    """Renders a :class:`PortfolioReport` as a single PDF document: a title
    and summary, a positions table, and (if dividend income was included in
    the report) a dividend income table.
    """

    def export(self, report: PortfolioReport, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()

        story: list[Any] = [
            Paragraph(f"Portfolio Report: {report.portfolio_name}", styles["Title"]),
            Paragraph(f"Generated: {report.generated_at.isoformat()}", styles["Normal"]),
            Spacer(1, 0.5 * cm),
            *self._summary_flowables(report, styles),
            Spacer(1, 0.5 * cm),
            Paragraph("Positions", styles["Heading2"]),
            self._positions_table(report),
        ]
        if report.dividend_income is not None and report.dividend_income.incomes:
            story.extend(
                [
                    Spacer(1, 0.5 * cm),
                    Paragraph("Dividend Income", styles["Heading2"]),
                    self._dividends_table(report.dividend_income),
                ]
            )

        document = SimpleDocTemplate(str(output_path), pagesize=A4)
        document.build(story)
        return output_path

    @staticmethod
    def _summary_flowables(report: PortfolioReport, styles: Any) -> list[Any]:
        valuation = report.valuation
        lines = (
            f"Total book cost: {valuation.base_currency_total_book_cost}",
            f"Total market value: {valuation.base_currency_total_market_value}",
            f"Total unrealized P&L: {valuation.base_currency_total_unrealized_pnl}",
        )
        return [Paragraph(line, styles["Normal"]) for line in lines]

    @staticmethod
    def _positions_table(report: PortfolioReport) -> Any:
        rows: list[list[str]] = [list(_POSITION_HEADERS)]
        for position in report.valuation.positions:
            rows.append(
                [
                    position.symbol,
                    str(position.quantity),
                    str(position.average_cost.amount),
                    str(position.market_price.amount),
                    str(position.book_cost.amount),
                    str(position.market_value.amount),
                    str(position.unrealized_pnl.amount),
                ]
            )
        table = Table(rows, repeatRows=1)
        table.setStyle(_TABLE_STYLE)
        return table

    @staticmethod
    def _dividends_table(dividend_income: PortfolioDividendIncome) -> Any:
        rows: list[list[str]] = [list(_DIVIDEND_HEADERS)]
        for income in dividend_income.incomes:
            rows.append(
                [
                    income.instrument.symbol,
                    str(income.quantity_held),
                    str(income.dividend.amount_per_share.amount),
                    income.dividend.pay_date.isoformat(),
                    str(income.total_income.amount),
                ]
            )
        rows.append(["Total", "", "", "", str(dividend_income.base_currency_total_income.amount)])
        table = Table(rows, repeatRows=1)
        table.setStyle(_TABLE_STYLE)
        return table
