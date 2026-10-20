import io
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from schemas.schemas import StoredReport

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _format_int(value: float) -> str:
    try:
        return f"{int(round(value)):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


def _format_currency(value: float) -> str:
    try:
        formatted = f"{float(value):,.2f}"
    except (ValueError, TypeError):
        formatted = "0.00"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_decimal(value: float, digits: int = 2) -> str:
    try:
        formatted = f"{float(value):,.{digits}f}"
    except (ValueError, TypeError):
        formatted = "0,00"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: float) -> str:
    return f"{_format_decimal(value)}%"


_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_env.filters["int_br"] = _format_int
_env.filters["currency_br"] = _format_currency
_env.filters["decimal_br"] = _format_decimal
_env.filters["percent_br"] = _format_percent


def render_report_html(report: StoredReport) -> str:
    template = _env.get_template("report.html")
    return template.render(
        report=report,
        metrics=report.metrics,
        campaigns=report.campaigns,
        insights=report.insights,
        agency_name=report.agency_name,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


def _html_to_pdf(html: str) -> bytes:
    # 1) WeasyPrint (melhor qualidade, usado em produção/Linux).
    try:
        from weasyprint import HTML  # type: ignore

        return HTML(string=html).write_pdf()
    except Exception:
        pass

    # 2) Fallback puro-Python (xhtml2pdf), funciona no Windows sem dependências nativas.
    from xhtml2pdf import pisa

    buffer = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError("Falha ao gerar o PDF do relatório.")
    return buffer.getvalue()


def generate_report_pdf(report: StoredReport) -> bytes:
    html = render_report_html(report)
    return _html_to_pdf(html)
