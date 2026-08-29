"""Use case: export a portfolio report to a file, in a chosen format."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from finapp.application.ports import (
    DividendProvider,
    MarketDataProvider,
    PortfolioReportExporter,
    PortfolioRepository,
)
from finapp.application.use_cases.build_portfolio_report import BuildPortfolioReport


class ReportFormat(StrEnum):
    """Which file format to export a portfolio report as."""

    EXCEL = "EXCEL"
    PDF = "PDF"


class ExportPortfolioReport:
    """Builds a portfolio report and writes it to disk in the requested format.

    Takes both exporters up front via constructor injection and picks
    between them per call, rather than needing a separate use case class
    per format for what's really the same operation with a format choice.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        market_data_provider: MarketDataProvider,
        excel_exporter: PortfolioReportExporter,
        pdf_exporter: PortfolioReportExporter,
        dividend_provider: DividendProvider | None = None,
    ) -> None:
        self._builder = BuildPortfolioReport(
            portfolio_repository, market_data_provider, dividend_provider
        )
        self._excel_exporter = excel_exporter
        self._pdf_exporter = pdf_exporter

    def execute(
        self,
        portfolio_name: str,
        output_path: Path,
        report_format: ReportFormat,
        include_dividend_income: bool = True,
    ) -> Path:
        report = self._builder.execute(
            portfolio_name, include_dividend_income=include_dividend_income
        )
        exporter = (
            self._excel_exporter if report_format == ReportFormat.EXCEL else self._pdf_exporter
        )
        return exporter.export(report, output_path)
