import json
import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        redis_password: str,
        redis_db: int,
    ) -> None:
        self.redis_client: Redis | None = None
        try:
            client = Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password or None,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            client.ping()
            self.redis_client = client
            logger.info(
                "Connected to Redis cache host=%s port=%s db=%s",
                redis_host,
                redis_port,
                redis_db,
            )
        except RedisError as exc:
            logger.warning(
                "Redis cache unavailable at startup host=%s port=%s db=%s error=%s",
                redis_host,
                redis_port,
                redis_db,
                exc,
            )

    def get_resume_record(self, file_digest: str) -> dict[str, Any] | None:
        if self.redis_client is None:
            return None
        try:
            value = self.redis_client.get(file_digest)
            if not value:
                return None
            return json.loads(value)
        except RedisError as exc:
            logger.warning("Redis get failed for digest=%s: %s", file_digest, exc)
            return None

    def set_resume_record(self, file_digest: str, value: dict[str, Any]) -> None:
        if self.redis_client is None:
            return
        try:
            self.redis_client.set(file_digest, json.dumps(value, ensure_ascii=False))
        except RedisError as exc:
            logger.warning("Redis set failed for digest=%s: %s", file_digest, exc)
