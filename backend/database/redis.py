"""
DSFMP Fraud Detection — Redis Connection

Provides an async Redis client for:
- JWT token blacklisting (on logout)
- Real-time alert queue management
- ML score caching
- Rate limiting
"""

import time
from redis.asyncio import Redis, ConnectionPool

from config.settings import settings


# ── Connection Pool ───────────────────────────────
# Shared pool created once at import time; actual connections
# are established lazily on first use.
_pool: ConnectionPool | None = None
_redis_down_until: float = 0.0


async def get_redis() -> Redis | None:
    """
    Create or return the async Redis client.
    Returns None immediately if Redis is not available (graceful degradation).
    """
    global _pool, _redis_down_until
    now = time.monotonic()
    if now < _redis_down_until:
        return None
    try:
        if _pool is None:
            _pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                decode_responses=True,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
            )
        client = Redis(connection_pool=_pool)
        await client.ping()  # Verify connection is alive
        return client
    except Exception:
        _redis_down_until = now + 60.0
        return None


async def close_redis() -> None:
    """Close the Redis connection pool. Called during app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


# ── Key Prefixes ──────────────────────────────────
# Centralized key naming to prevent collisions.

class RedisKeys:
    """Redis key namespace constants."""

    @staticmethod
    def blacklisted_token(jti: str) -> str:
        """Key for a blacklisted JWT token."""
        return f"auth:blacklist:{jti}"

    @staticmethod
    def alert_queue() -> str:
        """Key for the real-time alert queue (Redis list)."""
        return "alerts:queue"

    @staticmethod
    def score_cache(entity_type: str, entity_id: str) -> str:
        """Key for cached ML risk score."""
        return f"scores:{entity_type}:{entity_id}"

    @staticmethod
    def rate_limit(user_id: str, endpoint: str) -> str:
        """Key for per-user rate limiting."""
        return f"ratelimit:{user_id}:{endpoint}"

    @staticmethod
    def session(user_id: str) -> str:
        """Key for active user session tracking."""
        return f"session:{user_id}"
