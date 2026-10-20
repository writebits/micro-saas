import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configurações da aplicação, carregadas de variáveis de ambiente."""

    def __init__(self) -> None:
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.default_agency_name: str = os.getenv(
            "DEFAULT_AGENCY_NAME", "Sua Agência de Tráfego"
        )
        self.app_name: str = os.getenv("APP_NAME", "TrafficReport AI")
        # Mantém relatórios em memória por padrão (ideal para MVP/demonstração).
        self.report_ttl_items: int = int(os.getenv("REPORT_TTL_ITEMS", "200"))

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
