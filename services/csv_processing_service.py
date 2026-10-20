import io
import re
import unicodedata
from typing import Iterable
from uuid import uuid4

import numpy as np
import pandas as pd
from fastapi import HTTPException, UploadFile, status

from schemas.schemas import (
    CampaignPerformance,
    ReportMetrics,
    ReportSource,
    UploadReportResponse,
)


class CSVProcessingError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


EXPECTED_MIME_TYPES = {"text/csv", "application/vnd.ms-excel", "application/csv"}


COLUMN_ALIASES: dict[str, list[str]] = {
    "campaign_name": [
        "campaign",
        "campaign_name",
        "campaignname",
        "nome_da_campanha",
        "nome da campanha",
        "ad campaign",
    ],
    "impressions": ["impressions", "impressoes", "impressões", "impr", "views"],
    "clicks": ["clicks", "cliques", "link_clicks", "click"],
    "spend": ["spend", "cost", "amount_spent", "gasto", "gastos", "investimento"],
    "ctr": ["ctr", "click_through_rate", "taxa_de_cliques", "taxa de cliques"],
    "cpc": ["cpc", "cost_per_click", "custo_por_clique", "custo por clique"],
    "cpm": ["cpm", "cost_per_mille", "custo_por_mil", "custo por mil"],
    "conversions": [
        "conversions",
        "results",
        "conversoes",
        "conversões",
        "purchases",
    ],
    "roas": ["roas", "purchase_roas", "return_on_ad_spend"],
    "revenue": ["revenue", "value", "purchase_value", "conversion_value", "receita"],
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    no_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", no_accents.lower()).strip("_")
    return cleaned


def _safe_numeric(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    text = text.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "none": pd.NA,
            "null": pd.NA,
            "-": pd.NA,
        }
    )
    text = text.str.replace(r"[\sR$\$€£]", "", regex=True)
    text = text.str.replace(".", "", regex=False)
    text = text.str.replace(",", ".", regex=False)
    text = text.str.replace("%", "", regex=False)
    text = text.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    values = pd.to_numeric(text, errors="coerce").fillna(0.0)
    return values


def _find_column(df: pd.DataFrame, aliases: Iterable[str]) -> str | None:
    normalized = {_normalize_text(col): col for col in df.columns}
    alias_keys = [_normalize_text(a) for a in aliases]

    # 1) Correspondência exata.
    for key in alias_keys:
        if key in normalized:
            return normalized[key]

    # 2) Correspondência aproximada (prefixo, sufixo ou token).
    for key in alias_keys:
        for norm_col, original in normalized.items():
            tokens = norm_col.split("_")
            if norm_col.startswith(key) or norm_col.endswith(key) or key in tokens:
                return original
    return None


def _detect_source(columns: list[str]) -> ReportSource:
    normalized_columns = {_normalize_text(name) for name in columns}
    meta_signals = {"amount_spent", "purchase_roas", "results"}
    google_signals = {"cost", "clicks", "impressions", "conversions", "campaign"}
    if normalized_columns.intersection(meta_signals):
        return ReportSource.META_ADS
    if normalized_columns.intersection(google_signals):
        return ReportSource.GOOGLE_ADS
    return ReportSource.UNKNOWN


def process_csv_report(upload_file: UploadFile) -> UploadReportResponse:
    if upload_file.content_type not in EXPECTED_MIME_TYPES:
        raise CSVProcessingError(
            "Tipo de arquivo inválido. Envie um CSV válido do Meta Ads ou Google Ads."
        )

    raw_content = upload_file.file.read()
    if not raw_content:
        raise CSVProcessingError("Arquivo CSV vazio.")

    read_errors: list[str] = []
    dataframe = None
    for separator in [",", ";", "\t"]:
        try:
            dataframe = pd.read_csv(
                io.BytesIO(raw_content),
                sep=separator,
                dtype=str,
                encoding="utf-8",
            )
            if len(dataframe.columns) > 1:
                break
        except UnicodeDecodeError:
            try:
                dataframe = pd.read_csv(
                    io.BytesIO(raw_content),
                    sep=separator,
                    dtype=str,
                    encoding="latin1",
                )
                if len(dataframe.columns) > 1:
                    break
            except Exception as exc:  # noqa: BLE001
                read_errors.append(str(exc))
        except Exception as exc:  # noqa: BLE001
            read_errors.append(str(exc))

    if dataframe is None or dataframe.empty:
        raise CSVProcessingError(
            f"Não foi possível ler o CSV. Detalhes: {'; '.join(read_errors) or 'formato inválido'}"
        )

    source = _detect_source(list(dataframe.columns))
    working_df = dataframe.copy()

    campaign_col = _find_column(working_df, COLUMN_ALIASES["campaign_name"])
    if campaign_col is None:
        working_df["campaign_name"] = "Campanha não identificada"
        campaign_col = "campaign_name"

    for metric in ["impressions", "clicks", "spend", "ctr", "cpc", "cpm", "conversions", "roas"]:
        column = _find_column(working_df, COLUMN_ALIASES[metric])
        if column is None:
            working_df[metric] = 0.0
        else:
            working_df[metric] = _safe_numeric(working_df[column])

    revenue_col = _find_column(working_df, COLUMN_ALIASES["revenue"])
    if revenue_col:
        working_df["revenue"] = _safe_numeric(working_df[revenue_col])
    else:
        working_df["revenue"] = 0.0

    grouped = (
        working_df.groupby(campaign_col, dropna=False)[
            ["impressions", "clicks", "spend", "conversions", "revenue"]
        ]
        .sum()
        .reset_index()
    )
    grouped[campaign_col] = grouped[campaign_col].fillna("Campanha não identificada").astype(str)

    def _ratio(numerator: pd.Series, denominator: pd.Series, factor: float = 1.0) -> pd.Series:
        result = (numerator / denominator.replace(0, np.nan)) * factor
        return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    grouped["ctr"] = _ratio(grouped["clicks"], grouped["impressions"], 100)
    grouped["cpc"] = _ratio(grouped["spend"], grouped["clicks"])
    grouped["cpm"] = _ratio(grouped["spend"], grouped["impressions"], 1000)
    grouped["roas"] = _ratio(grouped["revenue"], grouped["spend"])

    campaigns = [
        CampaignPerformance(
            campaign_name=row[campaign_col],
            impressions=round(float(row["impressions"]), 2),
            clicks=round(float(row["clicks"]), 2),
            spend=round(float(row["spend"]), 2),
            ctr=round(float(row["ctr"]), 4),
            cpc=round(float(row["cpc"]), 4),
            cpm=round(float(row["cpm"]), 4),
            conversions=round(float(row["conversions"]), 2),
            roas=round(float(row["roas"]), 4),
        )
        for _, row in grouped.iterrows()
    ]

    total_impressions = float(working_df["impressions"].sum())
    total_clicks = float(working_df["clicks"].sum())
    total_spend = float(working_df["spend"].sum())
    total_revenue = float(working_df["revenue"].sum())

    metrics = ReportMetrics(
        impressions=round(total_impressions, 2),
        clicks=round(total_clicks, 2),
        spend=round(total_spend, 2),
        ctr=round((total_clicks / total_impressions * 100) if total_impressions else 0.0, 4),
        cpc=round((total_spend / total_clicks) if total_clicks else 0.0, 4),
        cpm=round((total_spend / total_impressions * 1000) if total_impressions else 0.0, 4),
        conversions=round(float(working_df["conversions"].sum()), 2),
        roas=round((total_revenue / total_spend) if total_spend else 0.0, 4),
    )

    return UploadReportResponse(
        report_id=str(uuid4()),
        source=source,
        metrics=metrics,
        campaigns=campaigns,
        rows_processed=len(working_df),
    )
