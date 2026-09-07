"""
GridGuard Backend - Pydantic Schemas
Request/response contracts for the API. Kept separate from the ORM models
(app/models.py) so the DB shape and the wire format can evolve independently.
"""
import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth (UC1) ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(default="analyst", pattern="^(analyst|admin)$")


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Datasets (UC3) ----------
class DatasetOut(BaseModel):
    id: int
    file_name: str
    status: str
    record_count: int
    uploaded_at: datetime.datetime
    processed_at: Optional[datetime.datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# ---------- Dashboard (UC4) ----------
class DashboardSummary(BaseModel):
    dataset_id: int
    total_consumers: int
    total_anomalies: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    unresolved_alerts: int
    active_model: Optional[str]


# ---------- Dashboard charts (UC4 extension) ----------
class NetworkTrend(BaseModel):
    dataset_id: int
    dates: List[str]
    avg_consumption: List[Optional[float]]
    sampled: bool = False  # true if dates were downsampled for chart performance


class RiskHistogramBin(BaseModel):
    range_start: float
    range_end: float
    count: int


class RiskHistogram(BaseModel):
    dataset_id: int
    bins: List[RiskHistogramBin]


# ---------- Consumers / Time series (UC5, UC7) ----------
class TimeSeriesPoint(BaseModel):
    date: str
    value: Optional[float]


class ConsumerTimeSeries(BaseModel):
    cons_no: str
    consumer_id: int
    points: List[TimeSeriesPoint]
    anomaly_dates: List[str] = []


# ---------- Anomaly results / Risk (UC6, UC8) ----------
class AnomalyResultOut(BaseModel):
    id: int
    consumer_id: int
    cons_no: str
    isoforest_anomaly: bool
    isoforest_score: float
    risk_score: float
    risk_category: str
    risk_source: str
    actual_flag: Optional[int]
    detected_at: datetime.datetime

    class Config:
        from_attributes = True


class PaginatedAnomalyResults(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AnomalyResultOut]


# ---------- Alerts (UC9, UC10) ----------
class AlertOut(BaseModel):
    id: int
    consumer_id: int
    cons_no: str
    severity: str
    status: str
    message: str
    created_at: datetime.datetime
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: str = Field(pattern="^(Reviewed|Resolved)$")


# ---------- ML Models (UC2, UC12) ----------
class MLModelOut(BaseModel):
    id: int
    model_name: str
    model_version: str
    algorithm_type: str
    is_active: bool
    uploaded_at: datetime.datetime
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class RetrainRequest(BaseModel):
    dataset_id: int
    model_name: str = "GridGuard-Supervised"


# ---------- Thresholds (UC13) ----------
class ThresholdOut(BaseModel):
    threshold_type: str
    threshold_value: float
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class ThresholdUpdate(BaseModel):
    risk_medium_cutoff: float = Field(gt=0, lt=1)
    risk_high_cutoff: float = Field(gt=0, lt=1)


# ---------- Feeder-level loss reconciliation (network-wide NTL) ----------
class FeederOut(BaseModel):
    id: int
    feeder_code: str
    is_synthetic: bool
    consumer_count: int
    avg_loss_pct: float
    peak_loss_pct: float
    loss_event_days: int
    risk_category: str

    class Config:
        from_attributes = True


class FeederSummary(BaseModel):
    dataset_id: int
    feeder_count: int
    is_synthetic: bool
    total_billed_kwh: float
    total_expected_kwh: float
    total_loss_kwh: float
    overall_loss_pct: float
    high_risk_feeders: int
    medium_risk_feeders: int
    low_risk_feeders: int


class FeederTrend(BaseModel):
    feeder_id: int
    feeder_code: str
    dates: List[str]
    billed_kwh: List[float]
    expected_kwh: List[float]
    loss_pct: List[float]


class FeederThresholdUpdate(BaseModel):
    feeder_loss_medium_cutoff: float = Field(gt=0, lt=100)
    feeder_loss_high_cutoff: float = Field(gt=0, lt=100)


# ---------- Reports (UC11) ----------
class ReportRequest(BaseModel):
    dataset_id: int
    format: str = Field(pattern="^(csv|pdf)$")
    risk_filter: Optional[str] = Field(default=None, pattern="^(Low|Medium|High)$")
    consumer_filter: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    format: str
    file_path: str
    generated_at: datetime.datetime

    class Config:
        from_attributes = True


# ---------- System logs (UC14) ----------
class SystemLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    event_type: str
    severity: str
    status: str
    details: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True
