"""审计中间件：记录所有变更类请求（POST/PUT/PATCH/DELETE），失败也记录状态码。"""
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.services.audit_service import write_audit
from src.utils.security import decode_access_token

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in MUTATING_METHODS and request.url.path.startswith("/api"):
            email, role = "anonymous", ""
            header = request.headers.get("authorization", "")
            if header.lower().startswith("bearer "):
                payload = decode_access_token(header.split(" ", 1)[1]) or {}
                email = payload.get("sub", "anonymous")
                role = payload.get("role", "")
            await run_in_threadpool(
                write_audit,
                email, role, f"{request.method} {request.url.path}",
                "", "", request.method, request.url.path, response.status_code, "",
            )
        return response
