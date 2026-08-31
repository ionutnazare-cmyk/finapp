"""Reports page.

Exports the selected portfolio's valuation (and optional dividend income)
as an Excel workbook or PDF document — see Sprint 1.14. Both formats
render from the exact same aggregated data, so they can never disagree
with each other.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from finapp.application.exceptions import ApplicationError
from finapp.application.use_cases.export_portfolio_report import (
    ExportPortfolioReport,
    ReportFormat,
)
from finapp.domain.exceptions import DomainError
from finapp.infrastructure.reporting.excel_exporter import ExcelPortfolioReportExporter
from finapp.infrastructure.reporting.pdf_exporter import PdfPortfolioReportExporter
from finapp.presentation.streamlit_common import (
    get_dividend_provider,
    get_market_data_provider,
    get_portfolio_repository,
    select_or_create_portfolio,
)

st.set_page_config(page_title="Reports — FinApp", page_icon="🧾", layout="wide")

_EXTENSION = {ReportFormat.EXCEL: "xlsx", ReportFormat.PDF: "pdf"}
_MIME_TYPE = {
    ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ReportFormat.PDF: "application/pdf",
}


def render() -> None:
    st.title("Reports 🧾")
    st.caption(
        "Export this portfolio's valuation and dividend income as an Excel "
        "workbook or a PDF document."
    )

    portfolio = select_or_create_portfolio(key_prefix="reports")
    if portfolio is None:
        st.info("Select or create a portfolio in the sidebar to get started.")
        return

    if portfolio.is_empty():
        st.info("This portfolio has no positions yet — buy something first on Portfolio Overview.")
        return

    col1, col2 = st.columns(2)
    with col1:
        report_format = st.radio(
            "Format",
            [ReportFormat.EXCEL, ReportFormat.PDF],
            format_func=lambda f: "Excel (.xlsx)" if f == ReportFormat.EXCEL else "PDF",
        )
    with col2:
        include_dividends = st.checkbox("Include dividend income", value=True)

    if not st.button("Generate report"):
        return

    use_case = ExportPortfolioReport(
        get_portfolio_repository(),
        get_market_data_provider(),
        ExcelPortfolioReportExporter(),
        PdfPortfolioReportExporter(),
        dividend_provider=get_dividend_provider() if include_dividends else None,
    )

    extension = _EXTENSION[report_format]
    file_name = f"{portfolio.name}_report.{extension}"

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / file_name
            use_case.execute(
                portfolio.name,
                output_path,
                report_format,
                include_dividend_income=include_dividends,
            )
            file_bytes = output_path.read_bytes()
    except (ApplicationError, DomainError) as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface any unexpected export error
        st.error(f"Couldn't generate report: {exc}")
        return

    st.success("Report generated.")
    st.download_button(
        "Download report",
        data=file_bytes,
        file_name=file_name,
        mime=_MIME_TYPE[report_format],
    )


render()
