"""滑动窗口限流：默认每分钟 240 次 / 客户端 IP，/api/health 不计数。"""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config.settings import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.window_seconds = 60
        self.limit = settings.RATE_LIMIT_PER_MINUTE
        self.buckets: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api") or path == "/api/health":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self.buckets[client]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0]))) if bucket else 1
            return JSONResponse(
                status_code=429,
                content={"code": "RATE_LIMITED",
                         "message": f"请求过于频繁，{retry_after}s 后重试（上限 {self.limit}/min）"},
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)
        return await call_next(request)
