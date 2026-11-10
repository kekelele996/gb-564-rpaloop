from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.errors import AppError


def error_body(code: str, message: str, detail: str | None = None) -> dict:
    return {"code": code, "message": message, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=error_body(exc.code, exc.message, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422,
                            content=error_body("VALIDATION_ERROR", "请求参数校验失败", str(exc.errors())))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else None
        return JSONResponse(status_code=exc.status_code,
                            content=error_body(f"HTTP_{exc.status_code}", detail or "请求失败"))

    @app.exception_handler(Exception)
    async def handle_unknown(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "服务内部错误", str(exc)))
