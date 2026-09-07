# GridGuard Frontend

React (Vite) dashboard for **GridGuard: Smart Electricity Theft Detection
System**. Implements the interface use cases from your SRS (UC1, UC4-UC15)
against the FastAPI backend.

## Setup

```bash
cd gridguard_frontend
npm install
npm run dev
```

Opens at **http://localhost:5173**. The dev server proxies `/api/*` to
`http://localhost:8000` (see `vite.config.js`) - start the backend first
(`uvicorn app.main:app --reload` from `gridguard_backend/`), then the
frontend.

Log in with the seeded admin account: `admin@gridguard.local` / `ChangeMe123!`

## What's built

| Page | Route | Use case(s) |
|---|---|---|
| Login | `/login` | UC1 |
| Dashboard | `/` | UC4 |
| Datasets (upload) | `/datasets` | UC3 |
| Anomaly results | `/anomalies` | UC6, UC7, UC8 |
| Consumer detail (chart) | `/consumers/:datasetId/:consumerId` | UC5 |
| Alerts | `/alerts` | UC9, UC10 |
| Reports | `/reports` | UC11 |
| ML models (admin) | `/models` | UC2 (select active), UC12 (retrain) |
| Thresholds (admin) | `/thresholds` | UC13 |
| System logs (admin) | `/logs` | UC14 |

Admin-only pages are guarded client-side (`RequireAdmin` in
`src/components/RouteGuards.jsx`) - the backend independently enforces the
same restriction, so this is a UX convenience, not the security boundary.

## Design system

See `src/styles/tokens.css` for the full rationale. Short version: a dark
"control-room" base (how real utility SCADA rooms are actually lit), with
two accents drawn from the subject itself - **copper** (the material of
power infrastructure, and what theft targets) for brand/primary actions,
and a **cyan telemetry trace** for live/normal status. Risk tiers
(Low/Medium/High) use cyan/amber/red consistently everywhere - that color
coding is functional, not decorative.

The signature visual is `src/components/RiskGauge.jsx` - risk scores
render as an analog meter dial with a copper needle instead of a generic
progress bar, since this is a tool about literal electricity meters. The
loading state (`GridPulse` in `src/components/Common.jsx`) is a sweeping
horizontal line evoking a live telemetry feed, used during dataset
processing and model retraining.

## Known gaps / next steps

- No password-change UI yet (backend doesn't have the endpoint either -
  see backend README).
- Admin user creation is via `POST /auth/register` directly (no UI form for
  it) - add one if you want admins to create accounts through the app
  rather than the API docs.
- Token is stored in `localStorage` (see `src/api/client.js`) - simpler for
  an FYP build; a production system would prefer an httpOnly cookie to
  reduce XSS exposure.
- `ConsumerDetailPage`'s anomaly highlighting is a simple client-visible
  heuristic (>60% single-day change, or <15% of the consumer's mean) for
  marking points on the chart - it's independent of the trained model's
  score, just a visual aid layered on the raw series.
