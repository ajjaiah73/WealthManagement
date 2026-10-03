"""JWT authentication and role-based authorisation.

- Passwords are bcrypt-hashed in the `users` table.
- Tokens are HS256 JWTs signed with JWT_SECRET (a random per-process secret
  when unset, so tokens simply expire on restart rather than being forgeable).
- The token is read from the `Authorization: Bearer` header, or from an
  `access_token` query parameter for EventSource/SSE, which cannot set headers.
- AUTH_ENABLED=false short-circuits to a local admin identity (tests/offline dev).
"""
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.domain.user import CurrentUser, Role, StoredUser

__all__ = ["CurrentUser", "Role", "create_access_token", "get_current_user", "hash_password",
           "require_roles", "verify_password"]

_ALGORITHM = "HS256"
_jwt_secret = settings.jwt_secret or secrets.token_urlsafe(48)

_LOCAL_USER = CurrentUser(user_id="local-admin", display_name="Local Admin (auth disabled)", role=Role.ADMIN)

DEMO_USERS: list[tuple[str, str, Role, str]] = [
    ("advisor", "Demo Advisor", Role.ADVISOR, "advisor-demo"),
    ("compliance", "Demo Compliance Officer", Role.COMPLIANCE_OFFICER, "compliance-demo"),
    ("admin", "Demo Administrator", Role.ADMIN, "admin-demo"),
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: StoredUser) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {
        "sub": user.username,
        "name": user.display_name,
        "role": user.role.value,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, _jwt_secret, algorithm=_ALGORITHM), expires_at


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if header:
        scheme, _, token = header.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()
    return request.query_params.get("access_token")


def get_current_user(request: Request) -> CurrentUser:
    if not settings.auth_enabled:
        return _LOCAL_USER
    token = _extract_token(request)
    if not token:
        raise _unauthorized("Not authenticated")
    try:
        payload = jwt.decode(token, _jwt_secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]})
        return CurrentUser(user_id=payload["sub"], display_name=payload.get("name", payload["sub"]),
                           role=Role(payload["role"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise _unauthorized("Invalid or expired token") from exc


def require_roles(*roles: Role) -> Callable[[CurrentUser], CurrentUser]:
    allowed = set(roles)

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to perform this action",
            )
        return user

    return _dependency


# Advisors prepare advice; admins can do anything; compliance officers are read-only reviewers.
require_advisor = require_roles(Role.ADVISOR, Role.ADMIN)
