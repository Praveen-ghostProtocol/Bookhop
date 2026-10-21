"""Structured JSON logging.

One JSON object per line. Every line carries:
  ts         ISO-8601 UTC, so a retention policy is a timestamp comparison and
             nothing has to parse a human-readable date format;
  log_class  "security" for the CERT-In / DPDP r.6(1)(c) stream, else "app", so
             each class's retention floor is applied mechanically rather than by
             someone deciding which lines matter;
  request_id THREAT-MODEL §7.2 -- six hours is not long enough to grep blind.

Retention floors are in settings.LOG_RETENTION_DAYS. CERT-In's 180 days is
subsumed by DPDP r.8(3)/r.6(1)(e)'s one year (ADR-001 §2.7), so the number
applied is 365.

The host clock itself is not established here. NTP synchronisation to NPL/NIC
(CERT-In Direction (i)) is a chrony configuration in INFRA.md and lands in S8;
until then these timestamps are only as accurate as the machine's clock.
"""

import json
import logging
from datetime import datetime, timezone

from .request_context import current_request

#: Keys an `extra={...}` may not occupy. Derived from a live LogRecord so it
#: survives a Python upgrade, plus the fields this formatter computes itself.
#:
#: The computed five matter: `log_class` is what makes the retention floor
#: mechanical rather than a judgement call, and `event` is what a CERT-In
#: investigation reads. Before REVIEW-S0 S2 they were absent from this set, so
#: `extra={"log_class": "app", "event": "nothing happened"}` on a security
#: record silently relabelled and rewrote the line.
_COMPUTED = {"ts", "level", "logger", "log_class", "event", "request_id", "exc"}
_RESERVED = (
    set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
    | {"message", "asctime", "taskName"}
    | _COMPUTED
)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not getattr(record, "request_id", None):
            record.request_id = current_request().get("request_id")
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "log_class": "security" if record.name.startswith("bookhop.security") else "app",
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        # Anything passed as logger.info("x", extra={...}) rides along.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
