from functools import lru_cache
import json
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Resume Analysis Assistant"
    app_version: str = "0.1.0"
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LLM_API_KEY",
            "DASHSCOPE_API_KEY",
            "QWEN_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    llm_model: str = Field(
        default="qwen-doc-turbo",
        validation_alias=AliasChoices("LLM_MODEL", "QWEN_MODEL", "OPENAI_MODEL"),
    )
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "QWEN_BASE_URL", "OPENAI_BASE_URL"),
    )
    llm_timeout_seconds: int = 180
    redis_host: str = "124.223.70.93"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    cache_dir: Path = Path(".cache")
    resume_storage_dir: Path = Path("app/CV")
    cors_origins: Annotated[list[str], NoDecode] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if value is None or value == "":
            return ["*"]
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if "*" in cleaned and len(cleaned) > 1:
                cleaned = [item for item in cleaned if item != "*"]
            return cleaned or ["*"]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ["*"]
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                cleaned = [str(item).strip() for item in parsed if str(item).strip()]
            else:
                cleaned = [item.strip() for item in stripped.split(",") if item.strip()]
            if "*" in cleaned and len(cleaned) > 1:
                cleaned = [item for item in cleaned if item != "*"]
            return cleaned or ["*"]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.resume_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
