from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.container import container
from app.core.rate_limit import login_rate_limiter
from app.core.security import CurrentUser, create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: CurrentUser


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_rate_limiter)])
def login(payload: LoginRequest) -> TokenResponse:
    user = container.user_repository.get(payload.username)
    # Same error for unknown user and wrong password, so usernames can't be enumerated.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token, expires_at = create_access_token(user)
    return TokenResponse(access_token=token, expires_at=expires_at, user=user.to_current_user())


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
