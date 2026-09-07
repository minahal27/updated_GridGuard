"""
GridGuard Backend - Alert Service
UC9 (Receive Alerts): generates alerts when a consumer's risk score
crosses the configured High-risk threshold.
UC15 (Send Email Alerts): attempts delivery via SMTP if configured; if
not configured or delivery fails, the alert still exists and is visible
on the dashboard (UC9's "Email Service Failure" alternate flow - the
alert itself is never lost, only the notification channel can fail).
"""
import logging
import smtplib
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from app import models, config
from app.services import log_service

logger = logging.getLogger("gridguard.alert_service")

DEFAULT_MEDIUM_CUTOFF = config.DEFAULT_THRESHOLDS["risk_medium_cutoff"]
DEFAULT_HIGH_CUTOFF = config.DEFAULT_THRESHOLDS["risk_high_cutoff"]


def get_active_thresholds(db: Session) -> dict:
    rows = db.query(models.ThresholdConfig).filter(models.ThresholdConfig.is_active == True).all()  # noqa: E712
    values = {r.threshold_type: r.threshold_value for r in rows}
    return {
        "risk_medium_cutoff": values.get("risk_medium_cutoff", DEFAULT_MEDIUM_CUTOFF),
        "risk_high_cutoff": values.get("risk_high_cutoff", DEFAULT_HIGH_CUTOFF),
    }


def _resolve_alert_recipients(db: Session) -> list:
    """
    Who UC15's email actually goes to.

    GRIDGUARD_ALERT_RECIPIENT (config.ALERT_RECIPIENT_OVERRIDE), if set,
    wins outright - a lot of real utilities route every theft alert to
    one shared ops/theft-desk mailbox rather than each analyst's personal
    inbox. If it's not set, falls back to every active admin account's
    registered email, since admins are the role responsible for
    reviewing/escalating alerts (UC10).
    """
    if config.ALERT_RECIPIENT_OVERRIDE:
        return [config.ALERT_RECIPIENT_OVERRIDE]
    admins = db.query(models.User).filter(models.User.role == "admin", models.User.status == "active").all()
    return [a.email for a in admins if a.email]


def generate_alerts_for_dataset(db: Session, dataset_id: int):
    """
    Scans a dataset's anomaly results and creates an Alert for every
    consumer at/above the High-risk threshold that doesn't already have
    an open (New/Reviewed) alert for their current result. Avoids
    duplicate alert spam on repeated processing/retraining runs.
    """
    thresholds = get_active_thresholds(db)
    high_cutoff = thresholds["risk_high_cutoff"]
    recipients = _resolve_alert_recipients(db)

    high_risk_results = (
        db.query(models.AnomalyResult)
        .filter(models.AnomalyResult.dataset_id == dataset_id, models.AnomalyResult.risk_score >= high_cutoff)
        .all()
    )

    created = 0
    for result in high_risk_results:
        existing_open = (
            db.query(models.Alert)
            .filter(models.Alert.anomaly_result_id == result.id, models.Alert.status != "Resolved")
            .first()
        )
        if existing_open:
            continue

        message = (
            f"High-risk consumption pattern detected for consumer "
            f"{result.consumer.cons_no} (risk score {result.risk_score:.2f}, "
            f"category {result.risk_category})."
        )
        alert = models.Alert(
            anomaly_result_id=result.id,
            consumer_id=result.consumer_id,
            severity=result.risk_category,
            status="New",
            message=message,
        )
        db.add(alert)
        db.flush()

        if recipients:
            for recipient in recipients:
                send_email_alert(db, alert, recipient=recipient)
        else:
            # Nobody to send to (no admin has an email, and no override
            # configured) - still record a Skipped notification so this
            # is visible in the logs rather than silently doing nothing.
            send_email_alert(db, alert, recipient="(no recipient configured)")
        created += 1

    db.commit()
    if created:
        log_service.log_event(
            db, event_type="alerts_generated",
            details=f"{created} new alert(s) for dataset {dataset_id}",
            related_table="datasets", related_id=dataset_id,
        )
    return created


def send_email_alert(db: Session, alert: models.Alert, recipient: str = None):
    """
    UC15: attempt to email the alert. Falls back gracefully - logged as
    'Skipped' if SMTP isn't configured (EMAIL_ENABLED is False by default;
    see app/config.py), the recipient isn't a real address (e.g. no admin
    has an email on file and no GRIDGUARD_ALERT_RECIPIENT override is
    set), or 'Failed' if delivery raised an error.
    """
    has_valid_recipient = bool(recipient) and "@" in recipient

    if not config.EMAIL_ENABLED:
        status = "Skipped"
        response = "SMTP not configured (set GRIDGUARD_SMTP_* env vars to enable)"
    elif not has_valid_recipient:
        status = "Skipped"
        response = "No valid recipient (set GRIDGUARD_ALERT_RECIPIENT or give an admin account an email)"
    else:
        try:
            msg = MIMEText(alert.message)
            msg["Subject"] = f"[GridGuard] {alert.severity}-risk alert - Consumer {alert.consumer.cons_no}"
            msg["From"] = config.SMTP_FROM_ADDRESS
            msg["To"] = recipient

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.sendmail(config.SMTP_FROM_ADDRESS, [recipient], msg.as_string())
            status = "Sent"
            response = "Delivered successfully"
        except Exception as exc:
            logger.warning("Email alert delivery failed: %s", exc)
            status = "Failed"
            response = str(exc)

    notification = models.NotificationLog(
        alert_id=alert.id,
        channel="email",
        recipient=recipient,
        status=status,
        provider_response=response,
    )
    db.add(notification)
    db.commit()
    return notification
