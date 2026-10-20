import json

from config import settings
from schemas.schemas import CampaignInsights, StoredReport

SYSTEM_PROMPT = (
    "Você é um analista sênior de tráfego pago (Meta Ads e Google Ads) de uma agência "
    "de marketing de performance. Escreve de forma clara, objetiva e em português do Brasil, "
    "sempre focado em resultados de negócio e próximos passos práticos."
)


def _build_user_prompt(report: StoredReport) -> str:
    summary = {
        "agencia": report.agency_name,
        "origem_dados": report.source.value,
        "metricas_totais": report.metrics.model_dump(),
        "campanhas": [c.model_dump() for c in report.campaigns[:25]],
    }
    return (
        "Analise o desempenho da campanha de tráfego pago a partir do resumo em JSON abaixo.\n\n"
        f"{json.dumps(summary, ensure_ascii=False, indent=2)}\n\n"
        "Responda ESTRITAMENTE em JSON válido com as chaves:\n"
        '- "resumo_executivo": string (parágrafo objetivo com os principais números e o veredito geral).\n'
        '- "destaques_positivos_e_gargalos": string (o que está indo bem e onde estão os gargalos, '
        "citando métricas como CTR, CPC, CPM, ROAS e conversões).\n"
        '- "acoes_de_otimizacao": array com EXATAMENTE 3 strings, cada uma uma ação prática e específica '
        "de otimização.\n"
        "Não inclua texto fora do JSON."
    )


def _br(value: float, decimals: int = 2) -> str:
    """Formata número no padrão brasileiro (1.234,56)."""
    s = f"{float(value):,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fallback_insights(report: StoredReport) -> CampaignInsights:
    m = report.metrics
    best = max(report.campaigns, key=lambda c: c.roas, default=None)
    worst = max(report.campaigns, key=lambda c: c.cpc, default=None)

    resumo = (
        f"No período analisado, a conta investiu R$ {_br(m.spend)}, gerando "
        f"{_br(m.impressions, 0)} impressões e {_br(m.clicks, 0)} cliques "
        f"(CTR de {_br(m.ctr)}%). Foram registradas {_br(m.conversions, 0)} conversões, "
        f"com CPC médio de R$ {_br(m.cpc)}, CPM de R$ {_br(m.cpm)} e ROAS de {_br(m.roas)}."
    )

    destaques_parts = []
    if best:
        destaques_parts.append(
            f"Destaque positivo: a campanha '{best.campaign_name}' apresentou o melhor ROAS "
            f"({_br(best.roas)}), sendo a mais eficiente em retorno."
        )
    if worst:
        destaques_parts.append(
            f"Gargalo: a campanha '{worst.campaign_name}' tem o CPC mais alto "
            f"(R$ {_br(worst.cpc)}), pressionando o custo de aquisição."
        )
    if m.ctr < 1:
        destaques_parts.append(
            "O CTR geral está abaixo de 1%, indicando oportunidade de melhorar criativos e segmentação."
        )
    destaques = " ".join(destaques_parts) or "Métricas dentro do esperado para o período."

    acoes = [
        "Realocar orçamento das campanhas de pior ROAS para as de melhor retorno, de forma gradual.",
        "Testar 2 a 3 novos criativos nas campanhas com CTR abaixo de 1% para reduzir o CPC.",
        "Revisar segmentação e públicos das campanhas com CPM elevado para melhorar a eficiência de entrega.",
    ]

    return CampaignInsights(
        resumo_executivo=resumo,
        destaques_positivos_e_gargalos=destaques,
        acoes_de_otimizacao=acoes,
        generated_by="fallback",
    )


def generate_insights(report: StoredReport) -> CampaignInsights:
    """Gera insights da campanha via OpenAI. Se a API não estiver configurada
    ou falhar, usa um fallback determinístico para não quebrar o fluxo."""
    if not settings.openai_enabled:
        return _fallback_insights(report)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(report)},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)

        acoes = data.get("acoes_de_otimizacao") or []
        if isinstance(acoes, str):
            acoes = [acoes]
        acoes = [str(a) for a in acoes][:3]
        while len(acoes) < 3:
            acoes.append("Revisar e otimizar continuamente com base nos dados de desempenho.")

        return CampaignInsights(
            resumo_executivo=str(data.get("resumo_executivo", "")).strip()
            or "Resumo não disponível.",
            destaques_positivos_e_gargalos=str(
                data.get("destaques_positivos_e_gargalos", "")
            ).strip()
            or "Sem destaques relevantes identificados.",
            acoes_de_otimizacao=acoes,
            generated_by="openai",
        )
    except Exception:
        # Qualquer erro de rede/credencial/parse cai no fallback determinístico.
        return _fallback_insights(report)
