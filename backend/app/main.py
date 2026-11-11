from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import app.core.sqlite_compat
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import RedTeamException, to_http_exception
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import rate_limit_dependency
from app.core.security import TokenData, require_role
from app.monitoring import security_metrics
from app.providers.llm import LLMProviderFactory

settings = get_settings()
logger = get_logger(__name__)


def _security_headers() -> dict[str, str]:
    """Security headers applied to every response, including error responses."""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
    # Only apply strict security headers in production
    if settings.is_production:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        headers["Pragma"] = "no-cache"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in _security_headers().items():
            response.headers[key] = value
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("application_starting", version=settings.APP_VERSION)

    await init_db()

    yield

    logger.info("application_shutting_down")
    # The LLM providers hold an httpx connection pool each. They are closed
    # here so that a graceful shutdown does not leak sockets.
    await LLMProviderFactory.close_all()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agent Red-Teaming & Evaluation Framework API",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding size limit to prevent DoS."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        max_bytes = 10 * 1024 * 1024  # 10MB
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    return JSONResponse(status_code=413, content={"detail": "Request entity too large"})
            except ValueError:
                pass
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)

cors_origins = settings.cors_origins_list
if settings.is_production and "*" in cors_origins:
    raise RuntimeError("Wildcard CORS origin not allowed in production with credentials")

# The development regex allows any localhost port to make credentialed
# requests, which is broader than the configured CORS_ORIGINS list. It is
# only enabled when the operator has not configured an explicit list.
cors_regex = (
    r"http://localhost:\d+"
    if settings.is_development and not cors_origins
    else None
)

# In development with no explicit origins configured, use wildcard and let regex handle it
cors_allow_origins = cors_origins if cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limit_dependency)])


@app.get("/api/v1/monitoring/dashboard")
async def monitoring_dashboard(
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    return security_metrics.get_security_dashboard()


@app.get("/api/v1/monitoring/alerts")
async def monitoring_alerts(
    severity: str | None = None,
    limit: int = 50,
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    return security_metrics.get_alerts(severity=severity, limit=limit)


class ClientErrorReport(BaseModel):
    """A client-side error reported by the browser."""

    type: str = Field(default="error", max_length=64)
    message: str = Field(default="", max_length=2000)
    source: str | None = Field(default=None, max_length=500)
    stack: str | None = Field(default=None, max_length=8000)
    timestamp: str | None = Field(default=None, max_length=64)


@app.post("/api/v1/monitoring/client-errors", status_code=202)
async def report_client_error(report: ClientErrorReport):
    """Accept a client-side error report.

    The endpoint is intentionally unauthenticated so that the browser can
    report an error that happened before or during authentication. The
    payload is size-limited, truncated and redacted server-side, and the
    rate limiter applies to it like to any other route.
    """
    alert = security_metrics.record_client_error(
        error_type=report.type,
        message=report.message,
        source=report.source,
        stack=report.stack,
    )
    return {"recorded": True, "alert_id": alert["id"]}


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    """CORS headers for error responses raised outside the CORS middleware.

    The middleware already sets the headers on normal responses; this helper
    only covers the exception path and mirrors the same allow-list.
    """
    origin = request.headers.get("origin", "")
    if not origin:
        return {}
    cors_origins = settings.cors_origins_list
    cors_regex = (
        r"http://localhost:\d+" if settings.is_development and not cors_origins else None
    )
    allowed = False
    if origin in cors_origins:
        allowed = True
    elif cors_regex:
        import re

        if re.match(cors_regex, origin):
            allowed = True
    if allowed:
        headers: dict[str, str] = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
        return headers
    return {}


@app.exception_handler(RedTeamException)
async def redteam_exception_handler(request: Request, exc: RedTeamException):
    headers = _cors_headers_for_request(request)
    headers.update(_security_headers())
    return JSONResponse(
        status_code=exc.status_code,
        content=to_http_exception(exc).detail,
        headers=headers,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # The message is logged server-side only; the client receives a generic
    # message so that stack traces, SQL fragments and configuration values are
    # never returned to a public caller.
    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True,
    )
    headers = _cors_headers_for_request(request)
    headers.update(_security_headers())
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        headers=headers,
    )


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "features": {
            "guardrails": "enabled",
            "mcp_proxy": "enabled",
            "code_scanning": "enabled",
            "model_security": "enabled",
            "monitoring": "enabled",
            "red_teaming": "enabled",
            "evaluations": "enabled",
        },
    }
