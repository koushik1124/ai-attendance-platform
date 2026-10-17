import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.audit import add_audit_event
from app.services.auth import authenticate_user


router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        add_audit_event(
            db,
            action="auth.login_failed",
            entity_type="user",
            metadata={"reason": "invalid_credentials"},
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
        logger.warning("authentication_failed")
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")

    token, expires_in = create_access_token(str(user.id))
    add_audit_event(
        db,
        action="auth.login_succeeded",
        entity_type="user",
        entity_id=str(user.id),
        actor_user_id=user.id,
        metadata={"role": user.role.value},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    logger.info("authentication_succeeded user_id=%s", user.id)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
