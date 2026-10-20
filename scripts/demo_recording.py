"""
Script de gravação automatizada para demonstração (ideal para OBS).

O que ele faz:
- Abre o site em uma janela do Chromium (modo visível).
- Injeta um "cursor" animado na tela, para que o movimento do mouse apareça
  claramente na gravação.
- Executa, de forma pausada e cinematográfica, todo o fluxo do produto:
  digitar o nome da agência, carregar dados de exemplo, processar o relatório,
  gerar os insights com IA e abrir o PDF final.
- Mantém a janela aberta ao final até você pressionar ENTER no terminal.

Como usar:
  1. Deixe o backend rodando:  uvicorn main:app --reload
  2. Em outro terminal:        python scripts/demo_recording.py
  3. Ligue a gravação no OBS e aproveite. :)

Opções (variáveis de ambiente):
  DEMO_URL     -> URL do app (padrão: http://127.0.0.1:8000)
  DEMO_AGENCY  -> Nome da agência exibido (padrão: Growth Performance Co.)
  DEMO_SPEED   -> Atraso base entre ações, em ms (padrão: 700)
"""

import os
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(
        "Playwright não está instalado.\n"
        "Instale com:\n"
        "  pip install -r requirements-dev.txt\n"
        "  python -m playwright install chromium"
    )
    sys.exit(1)


URL = os.getenv("DEMO_URL", "http://127.0.0.1:8000")
AGENCY = os.getenv("DEMO_AGENCY", "Growth Performance Co.")
SPEED = int(os.getenv("DEMO_SPEED", "700"))


# Script injetado na página: desenha um cursor que segue o mouse.
CURSOR_SCRIPT = r"""
(() => {
  if (document.getElementById('demo-cursor')) return;
  const c = document.createElement('div');
  c.id = 'demo-cursor';
  c.innerHTML = `
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M5 3l14 7-6 2-2 6-6-15z" fill="#111827" stroke="#ffffff" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>`;
  c.style.cssText = 'position:fixed;left:0;top:0;z-index:999999;pointer-events:none;filter:drop-shadow(0 2px 3px rgba(0,0,0,.4));transition:transform .04s linear;';
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(c));
  if (document.body) document.body.appendChild(c);
  window.addEventListener('mousemove', (e) => {
    c.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
  });
})();
"""


def pause(factor: float = 1.0) -> None:
    time.sleep((SPEED / 1000.0) * factor)


def main() -> None:
    print(f"Abrindo demonstração em {URL} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=120, args=["--start-maximized"])
        context = browser.new_context(
            viewport=None,
            accept_downloads=True,
        )
        context.add_init_script(CURSOR_SCRIPT)
        page = context.new_page()

        page.goto(URL, wait_until="networkidle")
        pause(2)

        def move_to(selector: str, steps: int = 30) -> None:
            el = page.locator(selector).first
            el.scroll_into_view_if_needed()
            pause(0.4)
            box = el.bounding_box()
            if not box:
                return
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            page.mouse.move(cx, cy, steps=steps)
            pause(0.4)

        def click(selector: str) -> None:
            move_to(selector)
            page.locator(selector).first.click()
            pause(1)

        def type_text(selector: str, text: str) -> None:
            move_to(selector)
            page.locator(selector).first.click()
            page.locator(selector).first.fill("")
            page.locator(selector).first.type(text, delay=55)
            pause(1)

        # 1) Preenche o nome da agência.
        type_text("#agency", AGENCY)

        # 2) Carrega os dados de exemplo.
        click("#sampleBtn")
        pause(1.5)

        # 3) Processa o relatório (Pandas).
        click("#uploadBtn")
        page.wait_for_selector("#results:not(.hidden)", timeout=15000)
        pause(1.5)

        # 4) Passeia pelos KPIs e pela tabela de campanhas.
        move_to("#kpis")
        pause(1.2)
        page.mouse.wheel(0, 450)
        pause(1.2)
        move_to("#campaignTable")
        pause(1.5)

        # 5) Gera os insights com IA.
        click("#insightsBtn")
        page.wait_for_selector("#insights:not(.hidden)", timeout=30000)
        pause(1)
        page.mouse.wheel(0, 350)
        pause(2)

        # 6) Abre o PDF final (nova aba).
        with context.expect_page() as popup_info:
            click("#pdfBtn")
        pdf_page = popup_info.value
        try:
            pdf_page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        pause(4)

        print("\nDemonstração concluída! A janela ficará aberta para você finalizar a gravação.")
        try:
            input("Pressione ENTER aqui para fechar o navegador...")
        except (EOFError, KeyboardInterrupt):
            pass

        browser.close()


if __name__ == "__main__":
    main()
