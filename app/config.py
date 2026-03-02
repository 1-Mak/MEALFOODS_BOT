from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    max_bot_token: SecretStr
    miniapp_url: str = ""

    # 1С OData (этап 7, пока опциональные)
    e4_odata_url: str = ""
    e4_username: str = ""
    e4_password: SecretStr = SecretStr("")


settings = Settings()
