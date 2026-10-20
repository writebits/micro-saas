from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportSource(str, Enum):
    META_ADS = "meta_ads"
    GOOGLE_ADS = "google_ads"
    UNKNOWN = "unknown"


class CampaignPerformance(BaseModel):
    campaign_name: str = Field(..., description="Nome da campanha")
    impressions: float = 0
    clicks: float = 0
    spend: float = 0
    ctr: float = 0
    cpc: float = 0
    cpm: float = 0
    conversions: float = 0
    roas: float = 0


class ReportMetrics(BaseModel):
    impressions: float = 0
    clicks: float = 0
    spend: float = 0
    ctr: float = 0
    cpc: float = 0
    cpm: float = 0
    conversions: float = 0
    roas: float = 0


class UploadReportResponse(BaseModel):
    report_id: str
    source: ReportSource
    metrics: ReportMetrics
    campaigns: list[CampaignPerformance]
    rows_processed: int


class ErrorResponse(BaseModel):
    detail: str
    context: dict[str, Any] | None = None


class GenerateInsightsRequest(BaseModel):
    report_id: str = Field(..., description="ID do relatório processado no upload")
    agency_name: str | None = Field(
        default=None, description="Nome da agência para personalizar a análise"
    )


class CampaignInsights(BaseModel):
    resumo_executivo: str
    destaques_positivos_e_gargalos: str
    acoes_de_otimizacao: list[str]
    generated_by: str = Field(
        default="openai", description="openai | fallback (quando a IA não está configurada)"
    )


class GenerateInsightsResponse(BaseModel):
    report_id: str
    agency_name: str
    insights: CampaignInsights


class StoredReport(BaseModel):
    report_id: str
    agency_name: str
    source: ReportSource
    metrics: ReportMetrics
    campaigns: list[CampaignPerformance]
    rows_processed: int
    insights: CampaignInsights | None = None
