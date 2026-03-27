from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.exceptions import RedisError
from time import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client, limit: int, window: int):
        super().__init__(app)
        self.redis = redis_client
        self.limit = limit
        self.window = window
        self._memory_limits: dict[str, tuple[int, float]] = {}

    def _check_memory_limit(self, key: str) -> bool:
        now = time()
        count, started_at = self._memory_limits.get(key, (0, now))
        if now - started_at >= self.window:
            self._memory_limits[key] = (1, now)
            return False

        if count >= self.limit:
            return True

        self._memory_limits[key] = (count + 1, started_at)
        return False

    @staticmethod
    def _too_many_requests_response() -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"},
        )

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"

        try:
            current_requests = await self.redis.get(key)
            if not current_requests:
                await self.redis.set(key, 1)
                await self.redis.expire(key, self.window)
            elif int(current_requests) >= self.limit:
                return self._too_many_requests_response()
            else:
                await self.redis.incr(key)
        except RedisError:
            # Fall back to local in-memory limit if Redis is unavailable.
            if self._check_memory_limit(key):
                return self._too_many_requests_response()

        response = await call_next(request)
        return response
