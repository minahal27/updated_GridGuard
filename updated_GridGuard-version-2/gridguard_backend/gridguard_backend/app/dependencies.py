"""
GridGuard Backend - Shared FastAPI dependencies
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_access_token
from app import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Guards UC2 (upload ML model), UC12 (retrain), UC13 (thresholds), UC14 (logs)
    - all listed as System Administrator / Utility Administrator actions in the SRS."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator privileges required")
    return current_user
