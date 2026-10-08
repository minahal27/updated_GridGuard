/*
  datetime.js

  Every timestamp the API returns (created_at, uploaded_at, detected_at...)
  comes from Python's datetime.utcnow() - a naive UTC datetime with no
  timezone suffix, e.g. "2026-08-23T17:53:18.218549". When a string like
  that is handed to JavaScript's `new Date(...)`, the spec says a
  date-time WITHOUT an offset is parsed as LOCAL time, not UTC - so every
  timestamp in the app was silently shifted by the viewer's UTC offset
  (5 hours early for PKT). parseUtc() marks the string as UTC explicitly
  before parsing; use it (or formatDateTime) anywhere an API timestamp is
  displayed instead of calling `new Date()` directly.
*/
export function parseUtc(value) {
  if (!value) return null;
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasOffset ? value : `${value}Z`);
}

export function formatDateTime(value) {
  const d = parseUtc(value);
  return d ? d.toLocaleString() : "—";
}
