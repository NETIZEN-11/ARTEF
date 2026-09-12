from datetime import datetime
from uuid import UUID
import difflib

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import (
    TokenData,
    get_audit_log_repo,
    get_feature_flag_repo,
    get_model_config_repo,
    get_prompt_version_repo,
    require_role,
)
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.domain.enums import ModelProvider, PromptVersionStatus
from app.models.feature_flag import FeatureFlag
from app.models.model_config import ModelConfig
from app.repositories import (
    AuditLogRepository,
    FeatureFlagRepository,
    ModelConfigRepository,
    PromptVersionRepository,
)

router = APIRouter()
settings = get_settings()


class ModelConfigResponse(BaseModel):
    id: UUID
    provider: ModelProvider
    model_name: str
    model_version: str
    role: str
    config: dict
    is_active: bool
    is_default: bool

    class Config:
        from_attributes = True


class ModelConfigCreate(BaseModel):
    provider: ModelProvider
    model_name: str
    model_version: str
    role: str
    config: dict = {}
    is_default: bool = False


class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_type: str
    version: str
    content: str
    variables: list[str]
    status: PromptVersionStatus
    created_by: UUID
    created_at: datetime | str
    promoted_at: datetime | str | None = None
    promoted_by: UUID | None

    class Config:
        from_attributes = True


class PromotePromptRequest(BaseModel):
    prompt_type: str
    version: str


class DeprecatePromptRequest(BaseModel):
    prompt_type: str
    version: str


class ArchivePromptRequest(BaseModel):
    prompt_type: str
    version: str


class PromptDiffRequest(BaseModel):
    prompt_type: str
    version_a: str
    version_b: str


@router.post("/prompts/promote")
async def promote_prompt(
    request: PromotePromptRequest,
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    prompt = await prompt_repo.get_by_type_version(request.prompt_type, request.version)
    if not prompt:
        raise NotFoundError("PromptVersion", f"{request.prompt_type}/{request.version}")

    await prompt_repo.demote_all(request.prompt_type)
    prompt.status = PromptVersionStatus.ACTIVE
    prompt.promoted_at = datetime.utcnow()
    prompt.promoted_by = UUID(current_user.sub)
    await prompt_repo.session.flush()

    return {"message": "Prompt promoted"}


@router.post("/prompts/deprecate")
async def deprecate_prompt(
    request: DeprecatePromptRequest,
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    prompt = await prompt_repo.get_by_type_version(request.prompt_type, request.version)
    if not prompt:
        raise NotFoundError("PromptVersion", f"{request.prompt_type}/{request.version}")

    if prompt.status != PromptVersionStatus.ACTIVE:
        raise ValueError("Can only deprecate active prompts")

    prompt.status = PromptVersionStatus.DEPRECATED
    prompt.promoted_at = None
    prompt.promoted_by = None
    await prompt_repo.session.flush()

    return {"message": "Prompt deprecated"}


@router.post("/prompts/archive")
async def archive_prompt(
    request: ArchivePromptRequest,
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    prompt = await prompt_repo.get_by_type_version(request.prompt_type, request.version)
    if not prompt:
        raise NotFoundError("PromptVersion", f"{request.prompt_type}/{request.version}")

    if prompt.status == PromptVersionStatus.ACTIVE:
        raise ValueError("Cannot archive active prompt. Deprecate first.")

    prompt.status = PromptVersionStatus.ARCHIVED
    await prompt_repo.session.flush()

    return {"message": "Prompt archived"}


@router.post("/prompts/diff")
async def diff_prompts(
    request: PromptDiffRequest,
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    prompt_a = await prompt_repo.get_by_type_version(request.prompt_type, request.version_a)
    prompt_b = await prompt_repo.get_by_type_version(request.prompt_type, request.version_b)
    
    if not prompt_a:
        raise NotFoundError("PromptVersion", f"{request.prompt_type}/{request.version_a}")
    if not prompt_b:
        raise NotFoundError("PromptVersion", f"{request.prompt_type}/{request.version_b}")
    
    # Compute diff
    import difflib
    diff = list(difflib.unified_diff(
        prompt_a.content.splitlines(keepends=True),
        prompt_b.content.splitlines(keepends=True),
        fromfile=f"{prompt_a.prompt_type} v{prompt_a.version}",
        tofile=f"{prompt_b.prompt_type} v{prompt_b.version}",
    ))
    
    return {
        "prompt_type": request.prompt_type,
        "version_a": request.version_a,
        "version_b": request.version_b,
        "diff": "".join(diff),
        "content_a": prompt_a.content,
        "content_b": prompt_b.content,
        "variables_a": prompt_a.variables,
        "variables_b": prompt_b.variables,
    }


class FeatureFlagResponse(BaseModel):
    id: UUID | str
    name: str
    enabled: bool
    description: str | None = None
    rollout_percentage: int = 100
    metadata: dict = {}

    class Config:
        from_attributes = True


class FeatureFlagUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    rollout_percentage: int | None = None
    target_roles: list[str] | None = None


class FeatureFlagCreate(BaseModel):
    name: str
    description: str | None = None
    enabled: bool = False
    rollout_percentage: int = 0
    target_roles: list[str] = []


ALL_ROLES = ["admin", "safety_engineer", "ml_engineer", "qa_engineer", "reviewer", "viewer"]
ADMIN_ROLES = ["admin", "safety_engineer"]


@router.get("/models", response_model=list[ModelConfigResponse])
async def list_models(
    model_repo: ModelConfigRepository = Depends(get_model_config_repo),
    current_user: TokenData = Depends(require_role(ALL_ROLES)),
):
    models = await model_repo.list()
    return [ModelConfigResponse.model_validate(m) for m in models]


@router.post("/models", response_model=ModelConfigResponse)
async def create_model(
    model: ModelConfigCreate,
    model_repo: ModelConfigRepository = Depends(get_model_config_repo),
    current_user: TokenData = Depends(require_role(ADMIN_ROLES)),
):
    new_model = ModelConfig(**model.model_dump())
    new_model = await model_repo.create(new_model)
    return ModelConfigResponse.model_validate(new_model)


@router.get("/prompts", response_model=list[PromptVersionResponse])
async def list_prompts(
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(ALL_ROLES)),
):
    prompts = await prompt_repo.list()
    return [PromptVersionResponse.model_validate(p) for p in prompts]


@router.get("/feature-flags", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    flag_repo: FeatureFlagRepository = Depends(get_feature_flag_repo),
    current_user: TokenData = Depends(require_role(ALL_ROLES)),
):
    flags = await flag_repo.list()
    result = []
    for f in flags:
        result.append(
            FeatureFlagResponse(
                id=f.id,
                name=f.name,
                enabled=f.enabled,
                description=f.description or "",
                rollout_percentage=f.rollout_percentage,
                metadata=f.flag_metadata if isinstance(f.flag_metadata, dict) else {},
            )
        )
    return result


@router.post("/feature-flags", response_model=FeatureFlagResponse)
async def create_feature_flag(
    flag: FeatureFlagCreate,
    flag_repo: FeatureFlagRepository = Depends(get_feature_flag_repo),
    current_user: TokenData = Depends(require_role(ADMIN_ROLES)),
):
    new_flag = FeatureFlag(
        name=flag.name,
        description=flag.description or "",
        enabled=flag.enabled,
        rollout_percentage=flag.rollout_percentage,
        metadata={"target_roles": flag.target_roles},
    )
    new_flag = await flag_repo.create(new_flag)
    return FeatureFlagResponse(
        id=new_flag.id,
        name=new_flag.name,
        enabled=new_flag.enabled,
        description=new_flag.description or "",
        rollout_percentage=new_flag.rollout_percentage,
        metadata=new_flag.flag_metadata if isinstance(new_flag.flag_metadata, dict) else {},
    )


@router.put("/feature-flags/{flag_id}")
@router.patch("/feature-flags/{flag_id}")
async def update_feature_flag(
    flag_id: UUID,
    update: FeatureFlagUpdate,
    flag_repo: FeatureFlagRepository = Depends(get_feature_flag_repo),
    current_user: TokenData = Depends(require_role(ADMIN_ROLES)),
):
    flag = await flag_repo.get(flag_id)
    if not flag:
        raise NotFoundError("FeatureFlag", str(flag_id))

    update_data = update.model_dump(exclude_unset=True)
    if "target_roles" in update_data:
        meta = flag.flag_metadata.copy() if isinstance(flag.flag_metadata, dict) else {}
        meta["target_roles"] = update_data.pop("target_roles")
        flag.flag_metadata = meta

    for key, value in update_data.items():
        if hasattr(flag, key) and value is not None:
            setattr(flag, key, value)

    await flag_repo.session.flush()
    return {"message": "Feature flag updated"}


@router.delete("/feature-flags/{flag_id}")
async def delete_feature_flag(
    flag_id: UUID,
    flag_repo: FeatureFlagRepository = Depends(get_feature_flag_repo),
    current_user: TokenData = Depends(require_role(ADMIN_ROLES)),
):
    flag = await flag_repo.get(flag_id)
    if not flag:
        raise NotFoundError("FeatureFlag", str(flag_id))
    await flag_repo.delete(flag)
    return {"message": "Feature flag deleted"}


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repo),
    current_user: TokenData = Depends(require_role(ALL_ROLES)),
):
    filters = {}
    if action:
        filters["action"] = action
    logs = await audit_repo.list(skip=offset, limit=limit, filters=filters)
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/config")
async def get_config(
    current_user: TokenData = Depends(require_role(ALL_ROLES)),
):
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "eval_mode": settings.EVAL_MODE,
        "judge_model": settings.PRIMARY_JUDGE_MODEL,
        "generator_model": settings.GENERATOR_MODEL,
        "planner_model": settings.PLANNER_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "cost_per_run_limit": settings.COST_PER_RUN_LIMIT_USD,
        "cost_daily_limit": settings.COST_DAILY_LIMIT_USD,
        "retention_days": {
            "transcripts": settings.TRANSCRIPT_RETENTION_DAYS,
            "critical_findings": settings.CRITICAL_FINDINGS_RETENTION_DAYS,
            "reports": settings.REPORT_RETENTION_DAYS,
            "audit_logs": settings.AUDIT_LOG_RETENTION_DAYS,
        },
    }
