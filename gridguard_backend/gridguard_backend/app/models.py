"""
GridGuard Backend - ORM Models
Maps to the ERD / Database Schema in the SRS (sections 2.10, 2.11), with one
deliberate simplification worth noting in your report:

    DESIGN NOTE - bulk daily readings
    The SGCC dataset is 42k consumers x ~1000 daily readings. Storing that
    as one row per (consumer, date) - the textbook-normalized approach your
    ERD's consumption_records table implies - is ~40 million rows, which is
    impractical for SQLite and adds no real query benefit here (nothing
    filters by individual day server-side; the dashboard always pulls a
    whole consumer's series at once for the time-series chart, or the whole
    dataset at once for feature/model training). Instead, the full reading
    matrix for a dataset is stored ONCE as a compressed .npz array file on
    disk (data/uploads/dataset_<id>_series.npz), and each Consumer row just
    keeps a `series_row_index` pointing into it - O(1) lookup, no join over
    millions of rows. The relational DB stays reserved for what it's good
    at: structured records (users, results, alerts, thresholds, logs).
    A production system ingesting real-time smart meter data (NFR-13) would
    likely move this to a proper time-series database (e.g. TimescaleDB/
    InfluxDB) instead - noted here as a scalability constraint (C-1/NFR-13).
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="analyst")  # analyst | admin
    status = Column(String(20), nullable=False, default="active")  # active | disabled
    created_at = Column(DateTime, default=utcnow)

    datasets = relationship("Dataset", back_populates="uploaded_by_user")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False, default="csv")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    record_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="uploaded")  # uploaded|processing|completed|failed
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Bulk daily readings for every consumer in this dataset are NOT stored
    # as SQL rows (see module docstring) - they live in one compressed
    # .npz array file on disk, shape (n_consumers, n_days). dates_json holds
    # the shared date axis (identical for every consumer in a dataset, so
    # it's stored once here instead of once per consumer).
    series_file_path = Column(String(255), nullable=True)
    dates_json = Column(Text, nullable=True)

    uploaded_by_user = relationship("User", back_populates="datasets")
    consumers = relationship("Consumer", back_populates="dataset", cascade="all, delete-orphan")


class Consumer(Base):
    __tablename__ = "consumers"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    cons_no = Column(String(100), nullable=False, index=True)  # original consumer ID from the dataset
    meter_id = Column(String(100), nullable=True)
    area = Column(String(120), nullable=True)
    # Row position of this consumer inside the dataset's series_file_path
    # .npz array - O(1) lookup for the time-series endpoint without a join
    # over millions of rows.
    series_row_index = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    dataset = relationship("Dataset", back_populates="consumers")
    anomaly_results = relationship("AnomalyResult", back_populates="consumer", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("dataset_id", "cons_no", name="uq_dataset_consumer"),)


class Feeder(Base):
    """
    A group of consumers sharing a feeder/transformer connection point -
    the unit that feeder-level loss reconciliation (Non-Technical Loss
    detection) aggregates over. See app/services/feeder_loss_service.py
    for how consumers get assigned to feeders and how the loss numbers
    below are computed.

    is_synthetic=True means the source CSV had no real feeder/area/
    transformer column, so consumers were deterministically grouped by ID
    purely so this feature is demonstrable - the UI shows this flag
    honestly rather than presenting it as real grid topology.
    """
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    feeder_code = Column(String(60), nullable=False)
    is_synthetic = Column(Boolean, default=True)
    consumer_count = Column(Integer, default=0)
    avg_loss_pct = Column(Float, default=0.0)
    peak_loss_pct = Column(Float, default=0.0)
    loss_event_days = Column(Integer, default=0)       # days where loss_pct crossed the Medium cutoff
    risk_category = Column(String(10), default="Low")  # Low|Medium|High, from avg_loss_pct vs thresholds
    created_at = Column(DateTime, default=utcnow)

    dataset = relationship("Dataset")

    __table_args__ = (UniqueConstraint("dataset_id", "feeder_code", name="uq_dataset_feeder"),)


class FeederDailyLoss(Base):
    """
    One feeder's billed-vs-expected reconciliation for one day. Sized
    fine for plain SQL rows (num_feeders x num_days is orders of
    magnitude smaller than the per-consumer matrix - e.g. ~170 feeders x
    ~1000 days = ~170k rows for the SGCC dataset), unlike per-consumer
    daily readings which are kept out of SQL (see the module docstring
    above) for exactly that scale reason.
    """
    __tablename__ = "feeder_daily_loss"

    id = Column(Integer, primary_key=True, index=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False)  # "YYYY-MM-DD"
    billed_kwh = Column(Float, nullable=False)
    expected_kwh = Column(Float, nullable=True)
    loss_kwh = Column(Float, default=0.0)
    loss_pct = Column(Float, default=0.0)


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    model_name = Column(String(120), nullable=False)
    model_version = Column(String(40), nullable=False)
    algorithm_type = Column(String(60), nullable=False)  # e.g. HistGradientBoosting, IsolationForest
    file_path = Column(String(255), nullable=False)
    scaler_path = Column(String(255), nullable=True)
    metrics_json = Column(Text, nullable=True)
    training_dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    is_active = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=utcnow)


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    consumer_id = Column(Integer, ForeignKey("consumers.id"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=True)

    isoforest_anomaly = Column(Boolean, default=False)
    isoforest_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)         # FR-14
    risk_category = Column(String(10), default="Low")  # FR-15 / UC8: Low|Medium|High
    risk_source = Column(String(30), default="isolation_forest")
    actual_flag = Column(Integer, nullable=True)     # ground-truth label if the dataset had one, else null
    detected_at = Column(DateTime, default=utcnow)

    consumer = relationship("Consumer", back_populates="anomaly_results")
    alerts = relationship("Alert", back_populates="anomaly_result", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    anomaly_result_id = Column(Integer, ForeignKey("anomaly_results.id"), nullable=False, index=True)
    consumer_id = Column(Integer, ForeignKey("consumers.id"), nullable=False)
    severity = Column(String(10), nullable=False, default="Medium")  # Low|Medium|High
    status = Column(String(20), nullable=False, default="New")       # New|Reviewed|Resolved
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    anomaly_result = relationship("AnomalyResult", back_populates="alerts")
    notifications = relationship("NotificationLog", back_populates="alert", cascade="all, delete-orphan")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    channel = Column(String(20), nullable=False, default="email")
    recipient = Column(String(180), nullable=True)
    status = Column(String(30), nullable=False)  # Sent|Failed|Queued|Skipped(disabled)
    provider_response = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=utcnow)

    alert = relationship("Alert", back_populates="notifications")


class ThresholdConfig(Base):
    __tablename__ = "threshold_configs"

    id = Column(Integer, primary_key=True, index=True)
    threshold_type = Column(String(60), nullable=False, unique=True)  # e.g. risk_medium_cutoff
    threshold_value = Column(Float, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=utcnow)
    is_active = Column(Boolean, default=True)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    format = Column(String(10), nullable=False)  # csv|pdf
    date_from = Column(String(20), nullable=True)
    date_to = Column(String(20), nullable=True)
    consumer_filter = Column(String(100), nullable=True)
    risk_filter = Column(String(10), nullable=True)
    file_path = Column(String(255), nullable=False)
    generated_at = Column(DateTime, default=utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(60), nullable=False)  # login|logout|upload|retrain|threshold_change|alert|error...
    severity = Column(String(15), nullable=False, default="info")  # info|warning|error
    status = Column(String(20), nullable=False, default="success")  # success|failed
    details = Column(Text, nullable=True)
    related_table = Column(String(60), nullable=True)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)
