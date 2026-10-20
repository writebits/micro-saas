# TrafficReport AI 🚀

Micro-SaaS de automação de relatórios de tráfego pago (**Meta Ads / Google Ads**).
Faça upload de um CSV, extraia as métricas automaticamente com **Pandas**, gere
insights com **IA (OpenAI)** e exporte um **PDF** visual pronto para o cliente.

Construído com **FastAPI + Pandas + OpenAI + Jinja2/WeasyPrint**, com uma interface
web pronta para demonstração.

---

## ✨ Funcionalidades

- **`POST /api/v1/reports/upload`** — Recebe o CSV (Meta ou Google Ads), processa com
  Pandas e extrai as métricas: Impressões, Cliques, Gasto, CTR, CPC, CPM, Conversões e ROAS.
  Trata células nulas, formatação de moeda (`R$ 1.234,56`) e dados inconsistentes.
- **`POST /api/v1/reports/generate-insights`** — Envia um resumo em JSON das métricas
  para a OpenAI (`gpt-4o-mini`) e retorna 3 seções em Português: Resumo Executivo,
  Destaques/Gargalos e 3 Ações de Otimização.
- **`GET /api/v1/reports/{report_id}/pdf`** — Gera um PDF limpo (HTML/Jinja2) com
  cabeçalho da agência, cards de KPIs, tabela por campanha e os insights da IA.
- **Interface web** em `/` para usar tudo visualmente (ótimo para demonstrações).

> 💡 **Sem chave da OpenAI?** Sem problemas. A aplicação usa um *fallback* determinístico
> que gera os insights a partir das próprias métricas — ideal para desenvolvimento e
> para gravar a demo sem gastar créditos.

---

## 🗂 Estrutura do projeto

```
SaaS/
├── main.py                       # App FastAPI (rotas, CORS, estáticos)
├── config.py                     # Configurações via variáveis de ambiente
├── requirements.txt              # Dependências de produção
├── requirements-dev.txt          # Dependências de desenvolvimento (Playwright)
├── Dockerfile                    # Imagem de produção (com libs do WeasyPrint)
├── routers/
│   └── reports.py                # Endpoints da API
├── services/
│   ├── csv_processing_service.py # Processamento do CSV com Pandas
│   ├── openai_service.py         # Geração de insights (OpenAI + fallback)
│   ├── pdf_service.py            # Geração de PDF (WeasyPrint + fallback xhtml2pdf)
│   └── report_store.py           # Armazenamento em memória dos relatórios
├── schemas/
│   └── schemas.py                # Modelos Pydantic
├── templates/
│   └── report.html               # Template do PDF (Jinja2)
├── static/                       # Frontend (HTML/CSS/JS) + CSVs de exemplo
└── scripts/
    └── demo_recording.py         # Script de gravação automatizada (OBS)
```

---

## ▶️ Como rodar localmente

Pré-requisito: **Python 3.11+**.

```powershell
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate           # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. (Opcional) Configurar variáveis de ambiente
copy .env.example .env                 # e edite com sua OPENAI_API_KEY

# 4. Subir o servidor
uvicorn main:app --reload
```

Acesse:
- Interface: http://127.0.0.1:8000
- Documentação da API (Swagger): http://127.0.0.1:8000/docs

> **Nota sobre PDF no Windows:** o WeasyPrint precisa das bibliotecas GTK, que são
> difíceis de instalar no Windows. Por isso o projeto usa automaticamente um *fallback*
> em Python puro (`xhtml2pdf`), que funciona sem dependências nativas. Em produção
> (Docker/Linux), o WeasyPrint é usado para máxima qualidade.

---

## 🎬 Gravar um vídeo da demonstração (OBS)

O projeto inclui um script que **controla o navegador automaticamente** e desenha um
**cursor animado** na tela, para você apenas ligar o OBS e gravar.

```powershell
# 1. Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt
python -m playwright install chromium

# 2. Deixe o servidor rodando em um terminal
uvicorn main:app --reload

# 3. Em outro terminal, rode o script de gravação
python scripts/demo_recording.py
```

O script executa, de forma pausada e cinematográfica: digita o nome da agência,
carrega os dados de exemplo, processa o relatório, navega pelos KPIs e pela tabela,
gera os insights com IA e abre o PDF final. A janela fica aberta até você pressionar
ENTER no terminal.

Variáveis opcionais:

| Variável      | Padrão                       | Descrição                         |
|---------------|------------------------------|-----------------------------------|
| `DEMO_URL`    | `http://127.0.0.1:8000`      | URL do app                        |
| `DEMO_AGENCY` | `Growth Performance Co.`     | Nome da agência exibido           |
| `DEMO_SPEED`  | `700`                        | Ritmo das ações, em milissegundos |

Exemplo (mais lento, para uma narração calma):

```powershell
$env:DEMO_SPEED="1000"; python scripts/demo_recording.py
```

---

## ☁️ Deploy (publicar na internet)

### Opção A — Docker (recomendado)

```bash
docker build -t trafficreport-ai .
docker run -p 8000:8000 --env-file .env trafficreport-ai
```

### Opção B — Render / Railway / Fly.io

Qualquer plataforma que rode Docker funciona direto com o `Dockerfile`. Sem Docker,
use o comando de start:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

E configure as variáveis de ambiente (`OPENAI_API_KEY`, `DEFAULT_AGENCY_NAME`, etc.).

> ⚠️ **Produção:** o armazenamento de relatórios é **em memória** (ideal para MVP/demo).
> Para produção com múltiplas instâncias, troque `services/report_store.py` por Redis
> ou um banco de dados, mantendo a mesma interface (`save` / `get` / `update`).

---

## 🔧 Variáveis de ambiente

| Variável              | Padrão                    | Descrição                                      |
|-----------------------|---------------------------|------------------------------------------------|
| `OPENAI_API_KEY`      | *(vazio)*                 | Chave da OpenAI. Vazio = usa fallback local.   |
| `OPENAI_MODEL`        | `gpt-4o-mini`             | Modelo usado para os insights.                 |
| `DEFAULT_AGENCY_NAME` | `Sua Agência de Tráfego`  | Nome padrão da agência.                        |
| `APP_NAME`            | `TrafficReport AI`        | Nome exibido na interface.                     |
| `REPORT_TTL_ITEMS`    | `200`                     | Máximo de relatórios mantidos em memória.      |

---

## 📄 CSVs de exemplo

Há arquivos de exemplo em [`static/sample/`](static/sample/) (Meta Ads e Google Ads),
usados pelo botão **"Usar dados de exemplo"** na interface. Eles contêm, de propósito,
valores com formatação de moeda e células vazias para demonstrar a limpeza de dados.
