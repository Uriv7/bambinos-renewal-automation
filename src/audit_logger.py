"""Machine-readable audit trail. Timestamps are the deterministic as-of time so reruns are reproducible."""
from __future__ import annotations

import pandas as pd

COLUMNS = ["seq", "case_id", "invoice_id", "step", "rule", "result", "detail", "logged_at"]


class AuditLogger:
    def __init__(self, as_of: pd.Timestamp):
        self.as_of = as_of
        self.rows: list[dict] = []

    def log(self, case_id, invoice_id, step, rule, result, detail=""):
        self.rows.append({"seq": len(self.rows) + 1, "case_id": case_id, "invoice_id": invoice_id or "",
                          "step": step, "rule": rule, "result": result, "detail": detail,
                          "logged_at": str(self.as_of)})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=COLUMNS)
