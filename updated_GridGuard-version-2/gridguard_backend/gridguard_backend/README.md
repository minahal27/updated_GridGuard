# GridGuard Backend

FastAPI backend for **GridGuard: Smart Electricity Theft Detection System**
(FYP1, Quaid-i-Azam University). Implements the SRS use cases UC1-UC15 on
top of the ML engine (see `app/ml_engine/`, same code you already have,
now wired into the API rather than run as a standalone script).

## Setup

```bash
cd gridguard_backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

- API root: http://localhost:8000
- Interactive docs (Swagger UI): **http://localhost:8000/docs** - the fastest
  way to try every endpoint without writing any frontend code yet.
- On first run, the app creates `data/db/gridguard.db` (SQLite) and seeds:
  - a default admin account: `admin@gridguard.local` / `ChangeMe123!`
    **(change this password immediately - see "Security notes" below)**
  - default anomaly thresholds (Medium=0.5, High=0.7)

## Typical flow (matches your SRS use cases)

1. `POST /auth/login` (form fields `username`=email, `password`) -> get a
   bearer token. Use it as `Authorization: Bearer <token>` on everything else.
2. `POST /datasets` - upload the SGCC `data.csv` (multipart file upload).
   Returns immediately with `status: "uploaded"` - processing (preprocessing
   + feature engineering + model training) runs in the background and takes
   ~30-40s for the full 42k-consumer file.
3. `GET /datasets/{id}` - poll until `status: "completed"`.
4. `GET /dashboard/{dataset_id}` - summary stats (UC4).
5. `GET /anomalies/{dataset_id}?risk_category=High` - browse results (UC6/UC7).
6. `GET /consumers/{dataset_id}/{consumer_id}/timeseries` - chart data (UC5).
7. `GET /alerts?dataset_id={id}&status=New` - alerts auto-generated for
   every High-risk consumer as soon as processing finishes (UC9).
8. `PATCH /alerts/{alert_id}` - mark Reviewed/Resolved (UC10).
9. `POST /reports` then `GET /reports/{id}/download` - CSV/PDF export (UC11).
10. `POST /ml-models/retrain` (admin only) - UC12.
11. `PUT /thresholds` (admin only) - UC13.
12. `GET /logs` (admin only) - UC14.

## Project layout

```
app/
  main.py              FastAPI app, router registration, startup seeding
  config.py             paths, JWT secret, upload limits, SMTP settings
  database.py           SQLAlchemy engine/session
  models.py             ORM models (see the DESIGN NOTE at the top of this
                         file for how bulk daily readings are stored -
                         important, read it before assuming this matches
                         your ERD 1:1)
  schemas.py             Pydantic request/response models
  security.py            password hashing + JWT
  dependencies.py        get_current_user / require_admin FastAPI dependencies
  ml_engine/              your existing preprocessing/feature engineering/
                          anomaly detection code, unchanged in logic
  services/
    ml_service.py         bridges ml_engine <-> the database
    alert_service.py       alert generation + email (UC9/UC15)
    report_service.py      CSV/PDF export (UC11)
    log_service.py         system log writer (UC14)
  routers/                one file per use-case group (auth, datasets,
                           dashboard, consumers, anomalies, alerts,
                           ml_models, thresholds, logs, reports)
```

## Design decisions worth knowing (and worth a line in your SDD)

1. **Bulk daily readings live in a compressed `.npz` file per dataset, not
   in SQL rows.** The textbook-normalized `consumption_records` table your
   ERD sketches would be ~40 million rows for this dataset - impractical
   for SQLite and unnecessary since nothing filters by individual day
   server-side. Instead each `Consumer` row stores a `series_row_index`
   pointing into `data/uploads/dataset_<id>_series.npz`. Full explanation
   is in the docstring at the top of `app/models.py`.

2. **Dataset processing runs as a FastAPI BackgroundTask**, not inline in
   the upload request - a 42k-consumer dataset takes ~30-40s, too long to
   hold an HTTP request open. The frontend polls `GET /datasets/{id}`.

3. **Model "upload" (UC2 Flow A) is intentionally not a raw file upload
   endpoint.** Accepting an arbitrary pickled/joblib model file from a
   client and loading it server-side is a code-execution risk (joblib/pickle
   deserialization can run arbitrary code). Models in this system are only
   ever produced by the training pipeline itself (dataset upload or
   `/ml-models/retrain`) - UC2 Flow B (select which trained model is active)
   is fully implemented via `POST /ml-models/{id}/activate`.

4. **JWT is stateless** - "logout" (UC1) discards the token client-side and
   logs the event server-side for audit purposes; there's no server-side
   session to invalidate. Token expiry is 8 hours (`ACCESS_TOKEN_EXPIRE_MINUTES`
   in `config.py`).

## Security notes before you deploy or demo this

- **Change the default admin password** (`ChangeMe123!`) immediately - log
  in once and there's no "change password" endpoint yet (worth adding).
- **Set a real `SECRET_KEY`** via the `GRIDGUARD_SECRET_KEY` environment
  variable - the default in `config.py` is explicitly a placeholder.
- Email alerts (UC15) are **disabled by default**. Set
  `GRIDGUARD_SMTP_HOST`, `GRIDGUARD_SMTP_USER`, `GRIDGUARD_SMTP_PASSWORD`
  as environment variables to enable them (e.g. a Gmail app password, or
  any SMTP provider). Without them, alerts still generate and appear on
  the dashboard - only the email channel is skipped (logged as "Skipped"
  in `notification_logs`), matching UC9's documented alternate flow.

## Not built yet
- React frontend (next step)
- Password reset / change-password endpoint
- Rate limiting on `/auth/login`
