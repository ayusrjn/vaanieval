from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_id
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import AuthResponse, MagicLinkRequest, MagicLinkVerifyRequest, MessageResponse
from app.services.auth_service import request_magic_link, revoke_session, verify_magic_link

router = APIRouter()


@router.post("/magic-link", response_model=MessageResponse)
def request_link(payload: MagicLinkRequest, db: Session = Depends(get_db)) -> MessageResponse:
    result = request_magic_link(db, payload.email)
    if result.token:
        return MessageResponse(message=f"Dev token generated: {result.token}")
    return MessageResponse(message="If an account exists for this email, a magic link will be sent.")


@router.post("/verify", response_model=AuthResponse)
def verify_link(
    payload: MagicLinkVerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    settings = get_settings()
    verified = verify_magic_link(db, payload.token)
    if not verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    response.set_cookie(
        key="session_token",
        value=verified.session_token,
        httponly=True,
        samesite=settings.session_cookie_samesite,
        secure=settings.session_cookie_secure,
    )

    return AuthResponse(
        user_id=verified.user.id,
        email=verified.user.email,
        workspace_id=verified.workspace.id,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    session_token: str | None = Cookie(default=None),
) -> MessageResponse:
    _ = user, workspace_id
    if session_token:
        revoke_session(db, session_token)
    settings = get_settings()
    response.delete_cookie(
        "session_token",
        samesite=settings.session_cookie_samesite,
        secure=settings.session_cookie_secure,
    )
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=AuthResponse)
def me(
    user=Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
) -> AuthResponse:
    return AuthResponse(user_id=user.id, email=user.email, workspace_id=workspace_id)
