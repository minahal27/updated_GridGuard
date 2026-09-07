"""
GridGuard Backend - Auth Router
UC1: User Authentication (Login & Logout).

JWT is stateless, so "logout" here is a client-side concern (discard the
token) plus a system log entry for audit purposes (FR-32) - there is no
server-side session to invalidate. If true forced-logout / token
revocation is needed later, add a token blacklist table.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user
from app.services import log_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_service.log_event(db, event_type="user_registered", user_id=user.id, details=f"role={user.role}")
    return user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Uses OAuth2PasswordRequestForm (username + password fields) so this
    plugs directly into FastAPI's interactive docs and OAuth2PasswordBearer
    flow. The frontend can send `username` as the user's email.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        log_service.log_event(
            db, event_type="login_failed", status="failed", severity="warning",
            details=f"email={form_data.username}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    log_service.log_event(db, event_type="login", user_id=user.id)
    return schemas.Token(access_token=token, user=user)


@router.post("/logout")
def logout(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_service.log_event(db, event_type="logout", user_id=current_user.id)
    return {"detail": "Logged out. Discard the access token client-side."}


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user
