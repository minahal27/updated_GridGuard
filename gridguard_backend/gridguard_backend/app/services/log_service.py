"""
GridGuard Backend - System Log Service
Implements FR-32 / UC14: every significant system event gets written here
so administrators have an audit trail (logins, uploads, retraining,
threshold changes, alert generation, errors).
"""
from sqlalchemy.orm import Session
from app import models


def log_event(
    db: Session,
    event_type: str,
    status: str = "success",
    severity: str = "info",
    user_id: int = None,
    details: str = None,
    related_table: str = None,
    related_id: int = None,
):
    entry = models.SystemLog(
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        status=status,
        details=details,
        related_table=related_table,
        related_id=related_id,
    )
    db.add(entry)
    db.commit()
    return entry
