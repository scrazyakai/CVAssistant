from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    example_env = Path(".env.example")
    if example_env.exists():
        example_values: dict[str, str] = {}
        for raw_line in example_env.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            example_values[key.strip()] = value.strip()

        if not settings.llm_api_key:
            for candidate in ("LLM_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY", "OPENAI_API_KEY"):
                if example_values.get(candidate):
                    settings.llm_api_key = example_values[candidate]
                    break
        if settings.llm_model == "qwen-doc-turbo":
            for candidate in ("LLM_MODEL", "QWEN_MODEL", "OPENAI_MODEL"):
                if example_values.get(candidate):
                    settings.llm_model = example_values[candidate]
                    break
        if settings.llm_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1":
            for candidate in ("LLM_BASE_URL", "QWEN_BASE_URL", "OPENAI_BASE_URL"):
                if example_values.get(candidate):
                    settings.llm_base_url = example_values[candidate]
                    break
        if settings.redis_host == "124.223.70.93" and example_values.get("REDIS_HOST"):
            settings.redis_host = example_values["REDIS_HOST"]
        if settings.redis_port == 6379 and example_values.get("REDIS_PORT"):
            settings.redis_port = int(example_values["REDIS_PORT"])
        if not settings.redis_password and example_values.get("REDIS_PASSWORD"):
            settings.redis_password = example_values["REDIS_PASSWORD"]
        if settings.redis_db == 0 and example_values.get("REDIS_DB"):
            settings.redis_db = int(example_values["REDIS_DB"])
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.resume_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
