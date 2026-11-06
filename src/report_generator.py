"""Root-cause table + human-readable run report."""
from __future__ import annotations

import pandas as pd

ROOT_CAUSES = {
    "PAYMENT_NOT_VERIFIED": ("Teacher submits form on a parent's screenshot; no automatic gateway check before approval", "Payment webhook as source of truth; forms for non-Paid invoices are parked automatically"),
    "PARTIAL_PAYMENT": ("Instalment invoices flow into the same pipeline as full payments; no instalment policy gate", "Explicit instalment rule + parent reminder; hold scheduling per Ops Head policy"),
    "AMOUNT_MISMATCH": ("Teacher types the amount by hand instead of reading it from the invoice", "Pre-fill amount from invoice; auto-compare net vs standard fee"),
    "DISCOUNT_REQUIRES_APPROVAL": ("Teachers can promise discounts; no approver field exists in any table", "Discount codes with approver id issued by Sales/Ops; invoice carries code"),
    "PARENT_CONTACT_MISMATCH": ("Payer is a different family member than the registered contact; no verification step", "Confirm with registered number via WhatsApp; whitelist authorised payers"),
    "MISSING_FACULTY_FORM": ("Renewal depends on a manual teacher step with no reminder or owner", "Auto-create the renewal from the paid invoice; teacher confirms only exceptions (form becomes optional)"),
    "ORPHANED_INVOICE": ("No escalation when the teacher step stalls", "12-hour escalation to Ops Executive"),
    "INVALID_REFERENCE": ("Invoice id typed manually (digit transposition) rather than selected", "Select-from-list invoice picker; reject unknown ids at entry"),
    "INVOICE_NOT_FOUND": ("Free-text invoice reference accepted without validation", "Validate invoice id at form submission"),
    "BATCH_FULL": ("Capacity check treats a same-batch renewal as a new seat request (to be validated)", "Seat-held logic for same-batch renewals; capacity check only for net-new seats"),
    "DUPLICATE_FACULTY_FORM": ("Browser freeze -> teacher resubmits; no idempotency on form", "Idempotency key per (invoice, student); duplicate submit returns existing form"),
    "MISSING_REQUIRED_FIELD": ("Batch-change renewals have no target-batch field on the form", "Add target batch/slot capture; parent selects via link"),
    "MANUAL_REVIEW_REQUIRED": ("Batch change needs a human decision on availability and parent preference", "Parent self-service batch picker with live capacity"),
    "TIMESTAMP_ANOMALY": ("Form created before the invoice existed (form likely prepared against a draft or wrong invoice)", "Block form creation until invoice exists"),
}


def root_cause_table(result) -> pd.DataFrame:
    rows = []
    cases = result["cases"]
    for code, (cause, fix) in ROOT_CAUSES.items():
        hit = [c for c in cases if code in c["reason_codes"] or code in c["info_codes"]]
        if hit:
            rows.append({"reason_code": code, "occurrences": len(hit), "evidence_records": "|".join(c["case_id"].replace("CASE-", "") for c in hit),
                         "observed_in_data": "Yes", "root_cause_hypothesis": cause, "proposed_fix": fix,
                         "confidence": "Hypothesis - validate with Ops Head/teachers (data shows the symptom, not the reason)"})
    cols = ["reason_code", "occurrences", "evidence_records", "observed_in_data", "root_cause_hypothesis", "proposed_fix", "confidence"]
    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values("occurrences", ascending=False, kind="stable") if len(df) else df


def theoretical_cases() -> list[str]:
    return ["DUPLICATE_INVOICE (same student/class paid twice)", "STUDENT_ID_MISMATCH", "TEACHER_ID_MISMATCH", "COURSE_MISMATCH",
            "BATCH_INACTIVE (soft-deleted batch)", "SCHEDULING_CONFLICT", "Multiple children under one parent", "Weekend/holiday delay (dates span Sun-Tue only)",
            "Cancelled schedule rows", "Same-batch seat-held semantics"]


def run_markdown(result, metrics) -> str:
    d = metrics["decisions"]
    lines = ["# Reconciliation run report", "", f"As-of: `{metrics['as_of']}`  |  invoices: {metrics['records']['invoices']}",
             "", "| Decision | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in d.items()]
    lines += ["", f"Form-level exceptions (orphan forms): {metrics['form_level_exceptions']}", "", "## Exceptions", "",
              "| Case | Primary reason | All codes | Owner | Priority |", "|---|---|---|---|---|"]
    for e in result["exceptions"]:
        lines.append(f"| {e['record_id']} | {e['primary_reason_code']} | {e['all_reason_codes']} | {e['assigned_owner']} | {e['priority']} |")
    return "\n".join(lines) + "\n"
