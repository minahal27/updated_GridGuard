"""
GridGuard Backend - Report Service
UC11: Generate and Export Report. Builds a filtered report of anomaly
results for a dataset and exports it as CSV or PDF.
"""
import csv
import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app import models, config


def _filtered_results(db: Session, dataset_id: int, risk_filter: str = None, consumer_filter: str = None):
    query = (
        db.query(models.AnomalyResult, models.Consumer)
        .join(models.Consumer, models.AnomalyResult.consumer_id == models.Consumer.id)
        .filter(models.AnomalyResult.dataset_id == dataset_id)
    )
    if risk_filter:
        query = query.filter(models.AnomalyResult.risk_category == risk_filter)
    if consumer_filter:
        query = query.filter(models.Consumer.cons_no.ilike(f"%{consumer_filter}%"))
    return query.order_by(models.AnomalyResult.risk_score.desc()).all()


def generate_report(db: Session, dataset_id: int, fmt: str, generated_by: int, risk_filter: str = None, consumer_filter: str = None) -> models.Report:
    rows = _filtered_results(db, dataset_id, risk_filter, consumer_filter)

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"gridguard_report_{dataset_id}_{timestamp}.{fmt}"
    file_path = Path(config.REPORTS_DIR) / filename

    if fmt == "csv":
        _write_csv(file_path, rows)
    elif fmt == "pdf":
        _write_pdf(file_path, rows, dataset_id)
    else:
        raise ValueError(f"Unsupported report format: {fmt}")

    report = models.Report(
        generated_by=generated_by,
        dataset_id=dataset_id,
        format=fmt,
        consumer_filter=consumer_filter,
        risk_filter=risk_filter,
        file_path=str(file_path),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _write_csv(file_path: Path, rows):
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Consumer ID", "Risk Score", "Risk Category", "Isolation Forest Anomaly",
                          "Isolation Forest Score", "Actual Label", "Detected At"])
        for anomaly, consumer in rows:
            writer.writerow([
                consumer.cons_no,
                f"{anomaly.risk_score:.4f}",
                anomaly.risk_category,
                anomaly.isoforest_anomaly,
                f"{anomaly.isoforest_score:.4f}",
                anomaly.actual_flag if anomaly.actual_flag is not None else "N/A",
                anomaly.detected_at.strftime("%Y-%m-%d %H:%M"),
            ])


def _write_pdf(file_path: Path, rows, dataset_id: int):
    """
    Uses fpdf2 (pure-Python, no system dependencies) to build a simple
    tabular PDF report - consistent with FR-29's "export in PDF or CSV".
    """
    from fpdf import FPDF

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "GridGuard - Electricity Theft Detection Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Dataset ID: {dataset_id}    Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(4)

    col_widths = [45, 30, 30, 30, 30, 30, 45]
    headers = ["Consumer ID", "Risk Score", "Risk Category", "Anomaly (ISO)", "ISO Score", "Actual Label", "Detected At"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 8, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    max_rows = 2000  # keep the PDF a sane size; full detail is available via CSV export
    for anomaly, consumer in rows[:max_rows]:
        values = [
            consumer.cons_no,
            f"{anomaly.risk_score:.3f}",
            anomaly.risk_category,
            "Yes" if anomaly.isoforest_anomaly else "No",
            f"{anomaly.isoforest_score:.3f}",
            str(anomaly.actual_flag) if anomaly.actual_flag is not None else "N/A",
            anomaly.detected_at.strftime("%Y-%m-%d"),
        ]
        for w, v in zip(col_widths, values):
            pdf.cell(w, 7, str(v), border=1)
        pdf.ln()

    if len(rows) > max_rows:
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 8, f"... {len(rows) - max_rows} more rows omitted. Use the CSV export for the full dataset.", ln=True)

    pdf.output(str(file_path))
