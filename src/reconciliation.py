"""Orchestrates the end-to-end reconciliation over the five datasets."""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .audit_logger import AuditLogger
from .config import EngineConfig
from .data_loader import Datasets
from .duplicate_detector import find_duplicate_invoices, group_forms_by_invoice
from .eligibility_engine import Context, evaluate_invoice
from .exception_handler import build_exception
from .scheduling_validator import active_schedule_rows, find_session_overlaps
from .validators import is_transposition, parse_ts


def resolve_as_of(ds: Datasets, cfg: EngineConfig) -> pd.Timestamp:
    if cfg.as_of:
        return pd.Timestamp(cfg.as_of)
    stamps = []
    for df in (ds.invoices, ds.forms, ds.bookings, ds.schedule):
        for col in ("created_at", "updated_at", "paid_at", "approved_at", "allocated_at"):
            if col in df.columns:
                stamps += [parse_ts(v) for v in df[col]]
    stamps = [s for s in stamps if s is not None]
    return max(stamps) if stamps else pd.Timestamp("1970-01-01")


def reconcile(ds: Datasets, cfg: EngineConfig | None = None) -> dict:
    cfg = cfg or EngineConfig()
    as_of = resolve_as_of(ds, cfg)
    audit = AuditLogger(as_of)
    for ex in ds.excluded:
        audit.log("-", "", "load", "L01_SOFT_DELETED_EXCLUDED", "INFO", f"{ex['table']} id {ex['id']} deleted_at {ex['deleted_at']}")
    for w in ds.warnings:
        audit.log("-", "", "load", "L02_SCHEMA_WARNING", "INFO", w)

    all_forms = ds.forms.to_dict("records")
    bookings_by_invoice = defaultdict(list)
    for b in ds.bookings.to_dict("records"):
        bookings_by_invoice[str(b["invoice_id"])].append(b)
    sched = ds.schedule
    ctx = Context(
        cfg=cfg, as_of=as_of, forms_by_invoice=group_forms_by_invoice(ds.forms), all_forms=all_forms,
        invoice_ids=set(ds.invoices["id"].astype(str)),
        ref_by_student={r["student_id"]: r for r in ds.reference.to_dict("records")},
        ref_rows=ds.reference.to_dict("records"), bookings_by_invoice=bookings_by_invoice,
        sched_by_booking=active_schedule_rows(sched),
        dup_invoices=find_duplicate_invoices(ds.invoices, cfg.duplicate_invoice_window_days),
        student_overlaps=defaultdict(list), educator_overlaps=defaultdict(list), audit=audit)
    for k, a, b in find_session_overlaps(sched, "student_id"):
        ctx.student_overlaps[k].append((k, a, b))
    for k, a, b in find_session_overlaps(sched, "educator_id"):
        ctx.educator_overlaps[k].append((k, a, b))

    cases = [evaluate_invoice(inv, ctx) for inv in ds.invoices.sort_values("id", key=lambda s: s.astype(int)).to_dict("records")]

    # Forms that reference an invoice id that does not exist: never silently dropped.
    inv_by_student = {r["student_id"]: r for r in ds.invoices.to_dict("records")}
    for f in all_forms:
        if str(f["invoice_id"]) in ctx.invoice_ids:
            continue
        hint, rel = "", None
        cand = inv_by_student.get(f["student_id"])
        if cand and is_transposition(str(f["invoice_id"]), str(cand["id"])):
            hint, rel = f" Probable intended invoice {cand['id']} (same student_id, digit transposition) - hint only, not applied.", f"CASE-{cand['id']}"
        cid = f"CASE-FORM-{f['id']}"
        audit.log(cid, f["invoice_id"], "linkage", "R04_FORM_LINKED", "FAIL", f"form {f['id']} references unknown invoice {f['invoice_id']}")
        audit.log(cid, f["invoice_id"], "decision", "R17_DECISION", "EXCEPTION", "INVOICE_NOT_FOUND")
        cases.append({
            "case_id": cid, "record_type": "faculty_form", "invoice_id": str(f["invoice_id"]), "invoice_number": None,
            "faculty_form_id": f["id"], "suppressed_duplicate_form_ids": "", "booking_id": None, "booking_status": None,
            "student_id": f["student_id"], "user_id": f["user_id"], "educator_id": f["educator_id"], "class_id": f["class_id"],
            "target_batch_id": None, "same_batch_renewal": None, "payment_status": None, "net_amount": None, "standard_fee": None,
            "form_amount_paid": f["amount_paid"], "sessions": cfg.standard_sessions, "preferred_days": f["preferred_days"],
            "preferred_time": f["preferred_time_slot"], "decision": "EXCEPTION", "reason_codes": ["INVOICE_NOT_FOUND"],
            "info_codes": [], "details": {"INVOICE_NOT_FOUND": [f"form {f['id']} cites invoice {f['invoice_id']} which does not exist.{hint}"]},
            "notes": [f"Related case {rel}"] if rel else [], "match_method": "NONE", "match_confidence": 0.0,
            "payment_age_hours": None, "teacher_followup_stage": "correction_needed", "scheduled_sessions": 0,
            "booking_sessions_count": None, "booking_age_hours": None, "form_approval_status": f["approval_status"],
            "idempotency_key": None, "mobile_masked": f["parent_mobile"], "registered_mobile_masked": None,
            "educator_name": f["educator_name"], "parent_name_masked": None})

    exceptions = [build_exception(c, as_of) for c in cases if c["decision"] == "EXCEPTION"]
    return {"as_of": as_of, "cases": cases, "exceptions": exceptions, "audit": audit.to_frame(), "ctx": ctx, "cfg": cfg}
