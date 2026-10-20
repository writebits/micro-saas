from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from config import settings
from schemas.schemas import (
    ErrorResponse,
    GenerateInsightsRequest,
    GenerateInsightsResponse,
    StoredReport,
    UploadReportResponse,
)
from services.csv_processing_service import CSVProcessingError, process_csv_report
from services.openai_service import generate_insights
from services.pdf_service import generate_report_pdf
from services.report_store import report_store


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post(
    "/upload",
    response_model=UploadReportResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Faz upload e processa um CSV do Meta Ads ou Google Ads",
)
def upload_report(
    file: UploadFile = File(...),
    agency_name: str | None = Form(default=None),
) -> UploadReportResponse:
    try:
        result = process_csv_report(file)
    except CSVProcessingError:
        raise
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao processar relatório: {exc}",
        ) from exc

    stored = StoredReport(
        report_id=result.report_id,
        agency_name=(agency_name or settings.default_agency_name).strip(),
        source=result.source,
        metrics=result.metrics,
        campaigns=result.campaigns,
        rows_processed=result.rows_processed,
    )
    report_store.save(stored)
    return result


@router.post(
    "/generate-insights",
    response_model=GenerateInsightsResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Gera insights da campanha com IA (OpenAI gpt-4o-mini)",
)
def generate_report_insights(payload: GenerateInsightsRequest) -> GenerateInsightsResponse:
    report = report_store.get(payload.report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relatório não encontrado. Faça o upload do CSV novamente.",
        )

    if payload.agency_name:
        report.agency_name = payload.agency_name.strip()

    try:
        insights = generate_insights(report)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao gerar insights: {exc}",
        ) from exc

    report.insights = insights
    report_store.update(report)

    return GenerateInsightsResponse(
        report_id=report.report_id,
        agency_name=report.agency_name,
        insights=insights,
    )


@router.get(
    "/{report_id}/pdf",
    responses={404: {"model": ErrorResponse}},
    summary="Gera o relatório visual em PDF",
)
def download_report_pdf(report_id: str) -> Response:
    report = report_store.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relatório não encontrado. Faça o upload do CSV novamente.",
        )

    if report.insights is None:
        report.insights = generate_insights(report)
        report_store.update(report)

    try:
        pdf_bytes = generate_report_pdf(report)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar o PDF: {exc}",
        ) from exc

    filename = f"relatorio-{report_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
