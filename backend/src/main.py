from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.logging import setup_logging
from src.config.settings import settings
from src.middlewares.audit import AuditMiddleware
from src.middlewares.error_handler import register_exception_handlers
from src.middlewares.rate_limit import RateLimitMiddleware
from src.routes import audit, auth, board, health, interventions, materials, meta, processes, runs

setup_logging()

app = FastAPI(
    title="rpaloop 政务材料录入 RPA 录制回放台",
    description="流程录制回放、定位器稳健性评分、无人值守执行与异常接管",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

register_exception_handlers(app)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = settings.API_PREFIX
for router in (health.router, auth.router, processes.router, runs.router, interventions.router,
               materials.router, board.router, meta.router, audit.router):
    app.include_router(router, prefix=API)


@app.get("/")
def root() -> dict:
    return {"app": "rpaloop", "docs": "/api/docs", "health": "/api/health"}
