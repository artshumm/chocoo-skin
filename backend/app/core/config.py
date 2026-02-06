from pathlib import Path

from pydantic_settings import BaseSettings

# .env лежит в корне проекта (на уровень выше backend/)
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""  # "446746688,412062038"
    database_url: str = "postgresql+asyncpg://chocoo:chocoo@localhost:5432/chocoo_skin"
    mini_app_url: str = ""

    model_config = {"env_file": str(ENV_FILE), "env_file_encoding": "utf-8"}

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


settings = Settings()
