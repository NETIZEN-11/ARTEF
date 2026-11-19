from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_user_repo
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.core.password_policy import validate_password_strength
from app.core.security import (
    TokenData,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    get_scopes_for_roles,
    needs_rehash,
    resolve_user_roles,
    verify_password,
)
from app.models.user import Role, User
from app.repositories.users import RoleRepository, UserRepository

router = APIRouter()
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repo),
):
    user = await user_repo.get_by_email_or_username(request.username)
    if not user or not verify_password(request.password, user.hashed_password):
        from app.core.rate_limit import _get_client_ip
        from app.monitoring import security_metrics

        logger.warning("login_failed", username=request.username)
        security_metrics.record_auth_failure("password", _get_client_ip(http_request))
        raise AuthenticationError("Invalid credentials")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Transparently upgrade hashes created before the SHA-256 pre-hashing
    # change so the full password entropy is preserved from now on.
    if needs_rehash(request.password, user.hashed_password):
        user.hashed_password = get_password_hash(request.password)
        await db.flush()
        logger.info("password_hash_upgraded", user_id=str(user.id))

    roles = resolve_user_roles(user)
    scopes = get_scopes_for_roles(roles)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )

    user.last_login = datetime.now(UTC)
    await db.commit()

    logger.info("login_success", user_id=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repo),
):
    try:
        token_data = decode_refresh_token(request.refresh_token)
    except Exception:
        raise AuthenticationError("Invalid refresh token")

    user = await user_repo.get(UUID(token_data.sub))
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    roles = resolve_user_roles(user)
    scopes = get_scopes_for_roles(roles)

    access_token = create_access_token(
        data={
            "sub": token_data.sub,
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": token_data.sub,
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )

    logger.info("token_refreshed", user_id=token_data.sub)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repo),
):
    from app.core.config import get_settings

    settings = get_settings()

    if settings.is_production:
        if not getattr(settings, "ALLOW_OPEN_REGISTRATION", False):
            all_users = await user_repo.list(skip=0, limit=1)
            if len(all_users) > 0:
                raise HTTPException(
                    status_code=403,
                    detail="Registration is disabled in production. Contact your administrator for an invitation.",
                )

    validate_password_strength(request.password, request.username, request.email)

    if await user_repo.get_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    if await user_repo.get_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # A newly registered account must carry a role. Without one the issued
    # token had an empty scope list and every protected endpoint answered
    # 403, so the user could sign in but not use the console.
    #
    # The very first account in a fresh installation becomes an admin;
    # every later account gets the read-only "viewer" role. An admin can
    # promote the account from the Settings page.
    role_repo = RoleRepository(db)
    is_first_user = await user_repo.count() == 0
    default_role_name = "admin" if is_first_user else "viewer"
    default_role = await role_repo.get_by_name(default_role_name)
    if default_role is None:
        default_role = Role(name=default_role_name, description=f"Auto-assigned {default_role_name} role")
        db.add(default_role)
        await db.flush()

    hashed_password = get_password_hash(request.password)
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        roles=[default_role],
    )
    user = await user_repo.create(user)

    # The roles are resolved *before* the commit: after `commit()` the
    # instance is expired and reading `user.roles` triggers a lazy load
    # outside the async context, which raises MissingGreenlet and turns the
    # registration into a 500.
    roles = resolve_user_roles(user)
    scopes = get_scopes_for_roles(roles)

    await db.commit()

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": roles,
            "scopes": scopes,
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,
    )


@router.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_active_user)):
    return {
        "id": current_user.sub,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "scopes": current_user.scopes,
    }
