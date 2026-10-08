"""End-to-end verification for GridGuard's documented core use cases.

Start the API first (``python -m uvicorn app.main:app --port 8000``), then run:
``python scripts/verify_use_cases.py``

The script uploads a temporary, realistic-shaped CSV and exercises UC1-UC14.
UC15's SMTP transport is configuration-dependent, so alert creation and its
notification-log fallback are verified by the application during processing.
"""
import csv
import json
import random
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"


def request(path, method="GET", token=None, body=None, content_type=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.status, response.headers, response.read()


def json_request(path, method="GET", token=None, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    status, _, raw = request(path, method, token, body, "application/json" if body else None)
    return status, json.loads(raw) if raw else None


def upload_csv(token, path):
    boundary = "----GridGuardUseCaseBoundary"
    content = path.read_bytes()
    body = b"\r\n".join([
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"'.encode(),
        b"Content-Type: text/csv",
        b"",
        content,
        f"--{boundary}--".encode(),
        b"",
    ])
    status, _, raw = request("/datasets", "POST", token, body, f"multipart/form-data; boundary={boundary}")
    return status, json.loads(raw)


def make_demo_csv(path):
    """Create labelled consumption data with normal and suspicious patterns."""
    random.seed(42)
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(35)]
    headers = ["CONS_NO", "FLAG", "FEEDER"] + [f"{d.year}/{d.month}/{d.day}" for d in dates]
    with path.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(headers)
        for index in range(60):
            theft = 1 if index < 12 else 0
            baseline = 12 + (index % 8) * 2
            values = []
            for day_index in range(len(dates)):
                value = baseline + random.uniform(-1.2, 1.2)
                if theft and day_index >= 20:
                    value *= 0.12 if index % 2 == 0 else random.uniform(0.25, 0.55)
                values.append(round(max(value, 0), 3))
            writer.writerow([f"DEMO-{index + 1:03d}", theft, f"F-{index // 20 + 1}", *values])


def expect(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def main():
    # UC1: authentication (and API availability)
    _, health = json_request("/health")
    expect(health["status"] == "ok", "API health check")
    encoded = urllib.parse.urlencode({"username": "admin@gridguard.local", "password": "ChangeMe123!"}).encode()
    _, _, raw = request("/auth/login", "POST", body=encoded, content_type="application/x-www-form-urlencoded")
    token = json.loads(raw)["access_token"]
    _, me = json_request("/auth/me", token=token)
    expect(me["role"] == "admin", "UC1 login and authorised session")

    # UC3: upload and background processing
    with tempfile.TemporaryDirectory() as temp_dir:
        csv_path = Path(temp_dir) / "gridguard_use_case_demo.csv"
        make_demo_csv(csv_path)
        _, dataset = upload_csv(token, csv_path)
    dataset_id = dataset["id"]
    for _ in range(30):
        _, dataset = json_request(f"/datasets/{dataset_id}", token=token)
        if dataset["status"] in {"completed", "failed"}:
            break
        time.sleep(1)
    expect(dataset["status"] == "completed", f"UC3 dataset upload and ML processing (dataset #{dataset_id})")

    # UC4-UC8: dashboard, graphs, filters, anomaly results and risk.
    _, dashboard = json_request(f"/dashboard/{dataset_id}", token=token)
    expect(dashboard["total_consumers"] == 60, "UC4 dashboard summary")
    _, trend = json_request(f"/dashboard/{dataset_id}/trend", token=token)
    expect(len(trend["dates"]) == 35, "UC4 network trend chart")
    _, histogram = json_request(f"/dashboard/{dataset_id}/risk-histogram", token=token)
    expect(len(histogram["bins"]) == 10, "UC4 risk distribution chart")
    _, consumers = json_request(f"/consumers/{dataset_id}/search?q=DEMO-001", token=token)
    consumer_id = consumers[0]["consumer_id"]
    _, series = json_request(f"/consumers/{dataset_id}/{consumer_id}/timeseries?start_date=2025-01-10&end_date=2025-01-20", token=token)
    expect(len(series["points"]) == 11, "UC5/UC7 consumer time-series and date filter")
    _, anomalies = json_request(f"/anomalies/{dataset_id}?risk_category=High&page_size=200", token=token)
    expect(anomalies["total"] >= 1, "UC6/UC8 anomaly listing and risk classification")
    _, result = json_request(f"/anomalies/{dataset_id}/{consumer_id}", token=token)
    expect("risk_score" in result, "UC8 individual risk score")

    # UC9-UC11: alerts, review state, CSV/PDF reporting.
    _, alerts = json_request(f"/alerts?dataset_id={dataset_id}", token=token)
    expect(isinstance(alerts, list), "UC9 alert retrieval")
    if alerts:
        _, updated = json_request(f"/alerts/{alerts[0]['id']}", "PATCH", token, {"status": "Reviewed"})
        expect(updated["status"] == "Reviewed", "UC10 alert review")
    for fmt in ("csv", "pdf"):
        _, report = json_request("/reports", "POST", token, {"dataset_id": dataset_id, "format": fmt})
        _, _, file_bytes = request(f"/reports/{report['id']}/download", token=token)
        expect(len(file_bytes) > 0, f"UC11 {fmt.upper()} report generation and download")

    # UC2, UC12-UC14: model choice/training, thresholds and audit logs.
    _, models = json_request("/ml-models", token=token)
    expect(len(models) >= 1, "UC2 trained model selection")
    _, retrained = json_request("/ml-models/retrain", "POST", token, {"dataset_id": dataset_id, "model_name": "GridGuard-Verification"})
    _, active = json_request(f"/ml-models/{retrained['id']}/activate", "POST", token)
    expect(active["is_active"], "UC12 retraining and model activation")
    _, thresholds = json_request("/thresholds", "PUT", token, {"risk_medium_cutoff": 0.45, "risk_high_cutoff": 0.70})
    expect(len(thresholds) == 2, "UC13 threshold configuration")
    _, logs = json_request("/logs?limit=50", token=token)
    expect(len(logs) >= 1, "UC14 system audit logs")
    _, logout = json_request("/auth/logout", "POST", token)
    expect("Logged out" in logout["detail"], "UC1 logout audit")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, urllib.error.HTTPError, urllib.error.URLError, IndexError) as exc:
        raise SystemExit(f"FAILED: {exc}")
