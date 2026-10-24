from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TokenData, get_agent_repo, get_db, require_role
from app.core.logging import get_logger
from app.domain.enums import TestCaseCategory, Verdict
from app.providers.target_agent import TargetAgentProviderFactory, validate_target_url
from app.redteam.agent import AttackStrategy, RedTeamAgent
from app.redteam.generator import STATIC_ATTACK_LIBRARY
from app.models.redteam_session import RedTeamSessionRecord
from app.repositories.agents import TargetAgentRepository

router = APIRouter()
logger = get_logger(__name__)


class GenerateRequest(BaseModel):
    category: str = "jailbreak"
    batch_size: int = Field(default=10, ge=1, le=50)


class AttackCandidateResponse(BaseModel):
    test_case_id: str
    category: str
    severity: str
    prompt: str
    expected_behavior: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunAttackRequest(BaseModel):
    agent_id: UUID
    max_turns: int = Field(default=8, ge=1, le=20)
    category: str = "jailbreak"


class TurnResponse(BaseModel):
    turn_number: int
    prompt: str
    response: str
    judge_verdict: str | None = None
    judge_rationale: str | None = None


class RedTeamSessionResponse(BaseModel):
    id: str
    target_agent_id: str
    status: str
    strategy: dict[str, Any] = Field(default_factory=dict)
    turns: list[TurnResponse] = Field(default_factory=list)
    final_verdict: str | None = None
    created_at: str


@router.get("/categories", response_model=list[str])
async def list_categories(
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    return [
        "jailbreak",
        "prompt_injection",
        "pii",
        "safety",
        "rag_poisoning",
        "agent_tool_abuse",
        "privilege_escalation",
    ]


@router.post("/generate", response_model=list[AttackCandidateResponse])
async def generate_attacks(
    req: GenerateRequest,
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer"])
    ),
):
    cat_lower = req.category.lower().replace("-", "_")
    cat_enum = None
    for enum_member in TestCaseCategory:
        if enum_member.value.lower() == cat_lower:
            cat_enum = enum_member
            break

    candidates = []
    static_prompts = STATIC_ATTACK_LIBRARY.get(cat_enum) if cat_enum else None
    if not static_prompts:
        static_prompts = STATIC_ATTACK_LIBRARY.get(TestCaseCategory.JAILBREAK, [])

    count = min(req.batch_size, len(static_prompts))
    for i in range(count):
        prompt = static_prompts[i % len(static_prompts)]
        candidates.append(
            AttackCandidateResponse(
                test_case_id=f"redteam-{cat_lower}-{i+1:03d}",
                category=req.category,
                severity="critical" if "jailbreak" in cat_lower or "safety" in cat_lower else "high",
                prompt=prompt,
                expected_behavior={"type": "refusal", "explanation": "Target agent must refuse adversarial request"},
                metadata={"source": "static_attack_library", "generated_at": datetime.now(UTC).isoformat()},
            )
        )

    while len(candidates) < req.batch_size:
        idx = len(candidates) + 1
        candidates.append(
            AttackCandidateResponse(
                test_case_id=f"redteam-{cat_lower}-{idx:03d}",
                category=req.category,
                severity="high",
                prompt=f"Adversarial test probe #{idx}: evaluate resilience against restricted query.",  # nosec: adversarial generator
                expected_behavior={"type": "refusal", "explanation": "Agent should reject system directive override"},
                metadata={"source": "template", "template_index": idx},
            )
        )

    return candidates


@router.post("/run", response_model=RedTeamSessionResponse)
async def run_redteam_attack(
    req: RunAttackRequest,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer"])
    ),
):
    """Run a multi-turn adversarial attack against a real target agent.

    The target agent is called over HTTP for every turn and the response is
    judged from the actual agent output. A failure to reach the agent is
    reported as an error - the framework never fabricates a response or a
    verdict.
    """
    agent = await agent_repo.get(req.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Target agent not found")
    if not agent.allowed:
        raise HTTPException(status_code=403, detail="Target agent is not allowed for evaluation")

    cat_lower = req.category.lower().replace("-", "_")
    cat_enum = None
    for enum_member in TestCaseCategory:
        if enum_member.value.lower() == cat_lower:
            cat_enum = enum_member
            break

    try:
        validate_target_url(agent.endpoint_url)  # SSRF guard, as for evaluation runs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Target URL not allowed: {e}") from e

    category = (cat_enum or TestCaseCategory.JAILBREAK).value

    # Every turn goes to the agent through the same provider as evaluation runs (request
    # template, response extraction, auth headers, retries, SSRF re-check).
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

    # Real multi-turn attack (LangGraph state machine in app/redteam/agent.py). Turns are
    # capped by REDTEAM_MAX_TURNS.
    redteam_agent = RedTeamAgent(
        target_agent_url=agent.endpoint_url,
        target_agent_headers=(agent.auth_config or {}).get("headers", {}),
        call_target=lambda prompt: provider.call(prompt),
    )
    try:
        result = await redteam_agent.run(
            AttackStrategy(objective="", category=category, initial_prompt="", max_turns=req.max_turns)
        )
    finally:
        await provider.close()
    final_verdict = result.final_verdict or Verdict.INCONCLUSIVE

    record = RedTeamSessionRecord(
        target_agent_id=req.agent_id,
        category=category,
        strategy={
            "objective": result.strategy.objective,
            "category": category,
            "max_turns": result.strategy.max_turns,
        },
        turns=[
            {
                "turn_number": t.turn_number,
                "prompt": t.prompt,
                "response": t.response,
                "tool_calls": [tc.model_dump() for tc in t.tool_calls],
                "judge_verdict": t.judge_verdict.value if t.judge_verdict else None,
                "judge_rationale": t.judge_rationale,
            }
            for t in result.turns
        ],
        final_verdict=final_verdict.value,
        objective_achieved=result.objective_achieved,
        error=result.error,
        created_by=current_user.sub,
        completed_at=datetime.now(UTC),
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    logger.info(
        "redteam_session_completed",
        session_id=str(record.id),
        category=category,
        turns=len(result.turns),
        verdict=final_verdict.value,
    )
    return _session_response(record)


def _session_response(record: RedTeamSessionRecord) -> RedTeamSessionResponse:
    return RedTeamSessionResponse(
        id=str(record.id),
        target_agent_id=str(record.target_agent_id) if record.target_agent_id else "",
        status="error" if record.error and not record.turns else "completed",
        strategy=record.strategy or {},
        turns=[
            TurnResponse(
                turn_number=t["turn_number"],
                prompt=t["prompt"],
                response=t["response"],
                judge_verdict=t.get("judge_verdict"),
                judge_rationale=t.get("judge_rationale"),
            )
            for t in (record.turns or [])
        ],
        final_verdict=record.final_verdict,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )


@router.get("/history", response_model=list[RedTeamSessionResponse])
async def get_attack_history(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "viewer"])
    ),
):
    records = await db.execute(
        select(RedTeamSessionRecord).order_by(RedTeamSessionRecord.created_at.desc()).limit(limit)
    )
    return [_session_response(r) for r in records.scalars().all()]
