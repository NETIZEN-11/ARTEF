import json
import re
import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import TokenData
from app.guardrails import GuardrailStatus
from app.guardrails.engine import GuardrailEngine
from app.models.guardrails import Guardrail, GuardrailFinding
from app.monitoring import security_metrics
from app.providers.target_agent import TargetAgentProviderFactory
from app.repositories.agents import TargetAgentRepository

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)

MAX_MESSAGE_CHARS = 50_000  # per message
_engine = GuardrailEngine()


class MCPMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class MCPRequest(BaseModel):
    messages: list[MCPMessage]
    # Target agent the request is forwarded to once it passes the guardrails. Without one
    # the request is only checked (used by the Guardrails page's test box).
    agent_id: UUID | None = None
    model: str = "gpt-4o"
    guardrail_check: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: dict[str, Any] | None = None


class MCPResponse(BaseModel):
    request_id: str
    forwarded: bool
    agent_name: str | None = None
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    guardrail_results: dict[str, Any] | None = None
    latency_ms: int
    timestamp: datetime


class MCPProxyConfig(BaseModel):
    name: str
    endpoint_url: str
    model_provider: str = "openai"
    guardrail_enabled: bool = True
    rate_limit: int = 100
    timeout_seconds: int = 30


class GuardrailCheckResult(BaseModel):
    passed: bool
    blocked: bool
    severity: str | None = None
    guardrail_type: str | None = None
    confidence: float = 0.0
    source: str = "builtin"  # "builtin" engine pattern or "custom" rule from the Guardrails page
    guardrail_id: str | None = None
    guardrail_name: str | None = None


async def check_guardrails(
    text: str, db: AsyncSession, direction: str = "input"
) -> list[GuardrailCheckResult]:
    """Check text against the built-in engine and the active custom guardrails.

    Every match is counted in the security metrics. Matches of custom guardrails are also
    stored as GuardrailFinding rows (blocked, warned or monitored, per the rule's status).
    """
    results: list[GuardrailCheckResult] = []
    engine_results = (
        await _engine.evaluate_input(text) if direction == "input" else await _engine.evaluate_output(text)
    )
    for r in engine_results:
        results.append(
            GuardrailCheckResult(
                passed=False,
                blocked=r.blocked,
                severity=r.severity.value if r.severity else None,
                guardrail_type=r.guardrail_type.value if r.guardrail_type else None,
                confidence=r.confidence,
            )
        )

    rules = (
        await db.execute(select(Guardrail).where(Guardrail.is_active.is_(True), Guardrail.pattern.is_not(None)))
    ).scalars().all()
    for rule in rules:
        if rule.status == GuardrailStatus.ALLOWED:
            continue
        try:
            matched = re.search(rule.pattern, text, re.IGNORECASE)
        except re.error:
            logger.warning("guardrail_invalid_pattern", guardrail_id=str(rule.id))
            continue
        if not matched:
            continue
        blocked = rule.status == GuardrailStatus.BLOCKED
        results.append(
            GuardrailCheckResult(
                passed=False,
                blocked=blocked,
                severity=rule.severity.value,
                guardrail_type=rule.guardrail_type.value,
                confidence=1.0,
                source="custom",
                guardrail_id=str(rule.id),
                guardrail_name=rule.name,
            )
        )
        db.add(
            GuardrailFinding(
                guardrail_id=rule.id,
                input_text=text[:5000] if direction == "input" else "",
                output_text=text[:5000] if direction == "output" else None,
                severity=rule.severity,
                status=rule.status,
                evidence=json.dumps({"direction": direction, "matched": matched.group(0)[:200]}),
            )
        )

    for r in results:
        security_metrics.record_guardrail_hit(r.guardrail_type or "unknown", r.severity or "medium", r.blocked)
    return results


def _blocked(code: str, message: str, results: list[GuardrailCheckResult]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": code,
            "message": message,
            "blocked_items": [r.model_dump() for r in results if r.blocked],
        },
    )


def _reply_text(raw: Any) -> str:
    if isinstance(raw, dict):
        for key in ("text", "response", "output", "content"):
            if key in raw:
                return str(raw[key])
    return str(raw)


@router.post("/proxy", response_model=MCPResponse)
async def proxy_request(
    request: MCPRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Check a request against the guardrails, forward it to the selected target agent, and
    check the agent's reply. Nothing is generated here: without an agent the request is
    only checked, and the response says it was not forwarded."""
    start_time = time.time()
    request_id = str(uuid4())

    if any(len(m.content) > MAX_MESSAGE_CHARS for m in request.messages):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "OVERSIZED_CONTENT", "message": f"Messages are limited to {MAX_MESSAGE_CHARS} characters"},
        )

    prompt = "\n".join(m.content for m in request.messages if m.role == "user") or ""
    input_results: list[GuardrailCheckResult] = []
    if request.guardrail_check:
        input_results = await check_guardrails(prompt, db, "input")
        if any(r.blocked for r in input_results):
            await db.commit()  # keep the findings; raising rolls the request session back
            raise _blocked("GUARDRAIL_BLOCKED", "Request blocked by guardrails", input_results)

    agent_name = None
    content = None
    output_results: list[GuardrailCheckResult] = []
    if request.agent_id is not None:
        agent = await TargetAgentRepository(db).get(request.agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Target agent not found")
        try:
            provider = TargetAgentProviderFactory.create_provider(
                "http",
                endpoint_url=agent.endpoint_url,
                auth_config=agent.auth_config,
                request_template=agent.request_template,
                response_extraction=agent.response_extraction,
                timeout=agent.timeout_seconds,
                max_retries=agent.max_retries,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Target agent configuration invalid: {e}") from e
        try:
            raw = await provider.call(prompt)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Target agent call failed: {e}") from e
        finally:
            await provider.close()
        agent_name = agent.name
        content = _reply_text(raw)

        if request.guardrail_check:
            output_results = await check_guardrails(content, db, "output")
            if any(r.blocked for r in output_results):
                await db.commit()
                raise _blocked("GUARDRAIL_BLOCKED_OUTPUT", "Agent response blocked by guardrails", output_results)

    results = input_results + output_results
    return MCPResponse(
        request_id=request_id,
        forwarded=request.agent_id is not None,
        agent_name=agent_name,
        content=content,
        tool_calls=None,
        guardrail_results={"results": [r.model_dump() for r in results]} if results else None,
        latency_ms=int((time.time() - start_time) * 1000),
        timestamp=datetime.now(),
    )


@router.get("/config")
async def get_mcp_config(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    """Get MCP proxy configuration."""
    return {"proxy_enabled": True, "default_model": settings.PRIMARY_JUDGE_MODEL}


@router.post("/config", dependencies=[Depends(require_role(["admin"]))])
async def update_mcp_config(config: MCPProxyConfig):
    """Proxy settings are not stored: requests are forwarded to registered target agents,
    which are managed on the Agents page."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MCP proxy settings are not stored. Register the upstream as a target agent instead.",
    )
