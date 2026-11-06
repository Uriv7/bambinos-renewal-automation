"""Data profile + referential integrity checks (factual, computed from the files)."""
from __future__ import annotations

import pandas as pd

from .validators import parse_ts

DATE_COLS = ["created_at", "updated_at", "paid_at", "approved_at", "allocated_at", "class_date"]


def profile(ds) -> dict:
    out = {"tables": {}, "referential_integrity": {}, "input_fingerprints_sha256": ds.fingerprints, "soft_deleted_rows_excluded": ds.excluded}
    for name in ("invoices", "forms", "bookings", "schedule", "reference"):
        df = getattr(ds, name)
        cols = {}
        for c in df.columns:
            s = df[c]
            entry = {"nulls": int(s.isna().sum()), "distinct": int(s.dropna().nunique())}
            if c in DATE_COLS:
                ts = [parse_ts(v) for v in s.dropna()]
                entry["min"], entry["max"] = (str(min(ts)), str(max(ts))) if ts else (None, None)
            if c in ("payment_status", "approval_status", "request_status", "payment_type", "continue_same_batch", "booking_type", "currency", "payment_gateway"):
                entry["values"] = {str(k): int(v) for k, v in s.value_counts(dropna=False).items()}
            cols[c] = entry
        key = "student_id" if name == "reference" else "id"
        out["tables"][name] = {"rows": len(df), "columns": len(df.columns), "duplicate_primary_keys": int(df[key].duplicated().sum()), "column_profile": cols}
    inv_ids, form_ids, book_ids = set(ds.invoices["id"]), set(ds.forms["id"]), set(ds.bookings["id"])
    students = set(ds.reference["student_id"])
    ri = out["referential_integrity"]
    ri["forms_with_unknown_invoice"] = sorted(set(ds.forms["invoice_id"]) - inv_ids)
    ri["bookings_with_unknown_invoice"] = sorted(set(ds.bookings["invoice_id"]) - inv_ids)
    ri["bookings_with_unknown_form"] = sorted(set(ds.bookings["faculty_form_id"]) - form_ids)
    ri["schedule_with_unknown_booking"] = sorted(set(ds.schedule["bookingrequest_id"]) - book_ids)
    ri["invoices_with_unknown_student"] = sorted(set(ds.invoices["student_id"]) - students)
    ri["invoices_without_exact_form"] = sorted(inv_ids - set(ds.forms["invoice_id"]))
    ri["bookings_with_null_batch"] = sorted(ds.bookings[ds.bookings["classbatch_id"].isna()]["id"])
    ri["students_per_user_gt1"] = sorted(ds.reference.groupby("user_id")["student_id"].nunique().loc[lambda s: s > 1].index)
    out["time_coverage_note"] = "All timestamps are timezone-naive; a single timezone is assumed."
    return out
