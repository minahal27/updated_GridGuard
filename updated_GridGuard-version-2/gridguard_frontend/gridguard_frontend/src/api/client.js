/*
  GridGuard API client.

  All requests go through /api/*, proxied to the FastAPI backend by Vite
  in dev (see vite.config.js) - in production, point this at the real API
  host by setting VITE_API_BASE.
*/
const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const TOKEN_KEY = "gridguard_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = "GET", body, isForm = false, params } = {}) {
  const url = new URL(API_BASE + path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }

  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload = body;
  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(url.pathname + url.search, { method, headers, body: payload });

  if (res.status === 204) return null;

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : await res.blob();

  if (!res.ok) {
    if (res.status === 401 && window.location.pathname !== "/login" && window.location.pathname !== "/welcome") {
      setToken(null);
      window.location.href = "/login";
    }
    const message = (isJson && data && (data.detail || data.message)) || res.statusText;
    throw new ApiError(typeof message === "string" ? message : JSON.stringify(message), res.status, data);
  }

  return data;
}

export const api = {
  // ---- Auth ----
  async login(email, password) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    const res = await fetch((API_BASE) + "/auth/login", { method: "POST", body: form });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(data?.detail || "Login failed", res.status, data);
    return data;
  },
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  changePassword: (payload) => request("/auth/change-password", { method: "PUT", body: payload }),
  register: (payload) => request("/auth/register", { method: "POST", body: payload }),
  listUsers: () => request("/auth/users"),

  // ---- Datasets ----
  listDatasets: () => request("/datasets"),
  getDataset: (id) => request(`/datasets/${id}`),
  loadDemoDataset: () => request("/datasets/demo", { method: "POST" }),
  async downloadDemoDataset() { const blob = await request("/datasets/demo/download"); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "gridguard_demo.csv"; a.click(); URL.revokeObjectURL(url); },
  async uploadDataset(file) {
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    const res = await fetch(API_BASE + "/datasets", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(data?.detail || "Upload failed", res.status, data);
    return data;
  },

  // ---- Dashboard ----
  getDashboard: (datasetId) => request(`/dashboard/${datasetId}`),
  getNetworkTrend: (datasetId) => request(`/dashboard/${datasetId}/trend`),
  getRiskHistogram: (datasetId) => request(`/dashboard/${datasetId}/risk-histogram`),

  // ---- Consumers / time series ----
  searchConsumers: (datasetId, q) => request(`/consumers/${datasetId}/search`, { params: { q } }),
  getTimeseries: (datasetId, consumerId, params) =>
    request(`/consumers/${datasetId}/${consumerId}/timeseries`, { params }),

  // ---- Anomaly results ----
  listAnomalies: (datasetId, params) => request(`/anomalies/${datasetId}`, { params }),
  getConsumerResult: (datasetId, consumerId) => request(`/anomalies/${datasetId}/${consumerId}`),

  // ---- Alerts ----
  listAlerts: (params) => request("/alerts", { params }),
  updateAlert: (id, status) => request(`/alerts/${id}`, { method: "PATCH", body: { status } }),
  getAlertNotifications: (id) => request(`/alerts/${id}/notifications`),

  // ---- ML models ----
  listModels: () => request("/ml-models"),
  activateModel: (id) => request(`/ml-models/${id}/activate`, { method: "POST" }),
  retrainModel: (payload) => request("/ml-models/retrain", { method: "POST", body: payload }),

  // ---- Thresholds ----
  getThresholds: () => request("/thresholds"),
  updateThresholds: (payload) => request("/thresholds", { method: "PUT", body: payload }),

  // ---- Feeders (network-wide loss reconciliation) ----
  listFeeders: (datasetId, params) => request(`/feeders/${datasetId}`, { params }),
  getFeederSummary: (datasetId) => request(`/feeders/${datasetId}/summary`),
  getFeederTrend: (datasetId, feederId) => request(`/feeders/${datasetId}/${feederId}/trend`),
  updateFeederThresholds: (payload) => request("/feeders/thresholds", { method: "PUT", body: payload }),

  // ---- Reports ----
  generateReport: (payload) => request("/reports", { method: "POST", body: payload }),
  listReports: (datasetId) => request("/reports", { params: { dataset_id: datasetId } }),
  async downloadReport(id, suggestedName) {
    // Plain <a href> won't carry the Authorization header, so fetch the
    // file as a blob ourselves and trigger the download manually.
    const blob = await request(`/reports/${id}/download`);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = suggestedName || `gridguard_report_${id}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  // ---- Logs ----
  listLogs: (params) => request("/logs", { params }),
};

export { ApiError };
