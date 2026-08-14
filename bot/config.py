"""Configuración leída del entorno y validada al arrancar."""

from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    db_path: Path = Path("./rpg.db")
    log_level: str = "INFO"
    admin_ids: Annotated[frozenset[int], NoDecode] = frozenset()

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_admin_ids(cls, value: object) -> object:
        """Acepta ADMIN_IDS como lista separada por comas o espacios."""
        if isinstance(value, str):
            return [chunk for chunk in value.replace(",", " ").split() if chunk]
        return value


def load_settings() -> Settings:
    """Carga la configuración; revienta aquí y no a mitad de partida si falta algo."""
    return Settings()  # type: ignore[call-arg]
