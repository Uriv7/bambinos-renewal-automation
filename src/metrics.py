"""KPI calculation with explicit definitions (numerator / denominator / measurability / limits)."""
from __future__ import annotations

import statistics

from .validators import hours_between, parse_ts


def _kpi(name, definition, num, den, source, measurable, limits, method="count ratio"):
    val = None if (den in (None, 0) or num is None) else round(100 * num / den, 1)
    return {"metric": name, "definition": definition, "numerator": num, "denominator": den, "value_pct": val,
            "calculation_method": method, "data_source": source, "fully_measurable": measurable, "limitations": limits}


def _time_stats(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return {"n": 0, "median_h": None, "mean_h": None, "max_h": None}
    return {"n": len(v), "median_h": round(statistics.median(v), 2), "mean_h": round(statistics.mean(v), 2), "max_h": round(max(v), 2)}


def compute_metrics(ds, result) -> dict:
    cases = [c for c in result["cases"] if c["record_type"] == "invoice"]
    inv, forms, bks, sched = ds.invoices, ds.forms, ds.bookings, ds.schedule
    n = len(inv)
    paid = [c for c in cases if c["payment_status"] == "Paid"]
    paid_ids = {c["invoice_id"] for c in paid}
    exact = {c["invoice_id"] for c in cases if c["match_method"] == "EXACT_INVOICE_ID"}
    orphan_paid = [c for c in paid if c["invoice_id"] not in exact]
    form_ids_valid = [f for f in forms.to_dict("records") if str(f["invoice_id"]) in set(inv["id"])]
    dup_forms = sum(1 for c in cases if c["suppressed_duplicate_form_ids"])
    dup_form_rows = sum(len(c["suppressed_duplicate_form_ids"].split("|")) for c in cases if c["suppressed_duplicate_form_ids"])
    has = lambda code: sum(1 for c in cases if code in c["reason_codes"])
    dec = lambda d: sum(1 for c in cases if c["decision"] == d)
    exc_cases = [c for c in result["cases"] if c["decision"] == "EXCEPTION"]
    booked_ids = set(bks["id"].astype(str))
    sched_booking_ids = {str(r["bookingrequest_id"]) for r in sched.to_dict("records")}
    unscheduled = [b for b in bks["id"].astype(str) if b not in sched_booking_ids]
    approved_forms = forms[forms["approval_status"] == "Approved"]
    approved_no_booking = [f for f in approved_forms.to_dict("records") if str(f["id"]) not in set(bks["faculty_form_id"].astype(str))]

    k = [
        _kpi("Paid invoices", "Invoices with payment_status = Paid", len(paid), n, "1_invoices", True, "Status field taken at face value; no gateway ledger to cross-check"),
        _kpi("Unpaid / not-fully-paid invoices", "Invoices that are not Paid (Failed + Partially_Paid)", n - len(paid), n, "1_invoices", True, ""),
        _kpi("Orphaned paid invoices", "Paid invoices with no faculty form linked by exact invoice id", len(orphan_paid), len(paid), "1_invoices, 2_faculty_form", True,
             "Includes 84913 whose form exists but cites a mistyped invoice id"),
        _kpi("Faculty form submission rate (paid invoices)", "Paid invoices with an exact-id linked form", len(paid) - len(orphan_paid), len(paid), "1,2", True, ""),
        _kpi("Faculty form mismatch rate", "Linked forms whose amount/contact/batch/timeline disagrees with invoice or reference", sum(1 for c in cases if c["faculty_form_id"] and set(c["reason_codes"]) & {"AMOUNT_MISMATCH", "PARENT_CONTACT_MISMATCH", "STUDENT_ID_MISMATCH", "TEACHER_ID_MISMATCH", "COURSE_MISMATCH", "TIMESTAMP_ANOMALY"}), sum(1 for c in cases if c["faculty_form_id"]), "1,2,ref", True, "Small sample (n<20)"),
        _kpi("Duplicate invoice rate", "Invoices colliding with another invoice (number, gateway id, student+class window)", has("DUPLICATE_INVOICE"), n, "1_invoices", True, "None observed in this sample"),
        _kpi("Duplicate faculty form rate", "Invoices with >1 active form", dup_forms, n, "2_faculty_form", True, f"{dup_form_rows} extra form row(s)"),
        _kpi("Faculty forms with an unknown invoice id", "Forms citing a non-existent invoice", len(forms) - len(form_ids_valid), len(forms), "1,2", True, ""),
        _kpi("Booking request creation rate (approved forms)", "Approved forms that have a booking request", len(approved_forms) - len(approved_no_booking), len(approved_forms), "2,3", True, ""),
        _kpi("Booking requests with no schedule rows", "Booking requests without any non-cancelled schedule booking", len(unscheduled), len(bks), "3,4", True, "5501 has 2 schedule rows for 24 sessions: partial scheduling cannot be judged without policy"),
        _kpi("Student identity mismatch rate", "Invoices raising STUDENT_ID_MISMATCH", has("STUDENT_ID_MISMATCH"), n, "1,2,ref", True, "None observed; names are masked so only ids are comparable"),
        _kpi("Payment amount mismatch rate", "Invoices raising AMOUNT_MISMATCH or DISCOUNT_REQUIRES_APPROVAL", sum(1 for c in cases if set(c["reason_codes"]) & {"AMOUNT_MISMATCH", "DISCOUNT_REQUIRES_APPROVAL"}), n, "1,2,ref", True, ""),
        _kpi("Batch capacity issues", "Invoices raising BATCH_FULL", has("BATCH_FULL"), n, "ref, 3", True, "Reference counts may or may not include the renewing student (assumption A1)"),
        _kpi("Auto-approval eligibility rate", "Invoices decided AUTO_APPROVE (no booking existed yet)", dec("AUTO_APPROVE"), n, "all", True, "Conservative: partial/duplicate/contact/batch-change cases are held"),
        _kpi("Safe-to-schedule rate", "AUTO_APPROVE + AWAITING_SCHEDULING + ALREADY_PROCESSED", dec("AUTO_APPROVE") + dec("AWAITING_SCHEDULING") + dec("ALREADY_PROCESSED"), n, "all", True, ""),
        _kpi("Exception rate", "Invoices decided EXCEPTION", sum(1 for c in cases if c["decision"] == "EXCEPTION"), n, "all", True, "Plus 1 form-level exception (orphan form 3313)"),
    ]
    forms_d, inv_d = {str(f["id"]): f for f in forms.to_dict("records")}, {str(r["id"]): r for r in inv.to_dict("records")}
    t_pay_form, t_form_appr, t_appr_book, t_book_sched = [], [], [], []
    for f in forms.to_dict("records"):
        i = inv_d.get(str(f["invoice_id"]))
        if i:
            t_pay_form.append(hours_between(parse_ts(i["paid_at"]), parse_ts(f["created_at"])))
        t_form_appr.append(hours_between(parse_ts(f["created_at"]), parse_ts(f["approved_at"])))
    for b in bks.to_dict("records"):
        f = forms_d.get(str(b["faculty_form_id"]))
        if f:
            t_appr_book.append(hours_between(parse_ts(f["approved_at"]), parse_ts(b["created_at"])))
        rows = [r for r in sched.to_dict("records") if str(r["bookingrequest_id"]) == str(b["id"])]
        if rows:
            t_book_sched.append(hours_between(parse_ts(b["created_at"]), min(parse_ts(r["created_at"]) for r in rows)))
    neg = [x for x in t_pay_form if x is not None and x < 0]
    timing = {
        "payment_to_form_created_hours": _time_stats([x for x in t_pay_form if x is None or x >= 0]),
        "payment_to_form_negative_anomalies": len(neg),
        "form_created_to_ops_approval_hours": _time_stats(t_form_appr),
        "approval_to_booking_created_hours": _time_stats(t_appr_book),
        "booking_created_to_first_schedule_hours": _time_stats(t_book_sched),
        "note": "Single timezone assumed (not stated in data). Averages over n<=5 are indicative only, not a baseline.",
    }
    stuck = []
    for c in cases:
        if c["booking_id"] and c["scheduled_sessions"] == 0:
            stuck.append({"booking_id": c["booking_id"], "invoice_id": c["invoice_id"], "status": c["booking_status"], "age_hours": round(c["booking_age_hours"], 2)})
    # Estimated manual effort saved: transparent assumption-driven, NOT a measured baseline.
    assumptions = {"manual_minutes_per_clean_renewal_verification": 10, "source": "ASSUMPTION - validate with Ops Head (time study needed)"}
    saved_min = dec("AUTO_APPROVE") * assumptions["manual_minutes_per_clean_renewal_verification"]
    return {
        "as_of": str(result["as_of"]), "records": {"invoices": n, "faculty_forms": len(forms), "booking_requests": len(bks), "schedule_rows": len(sched), "reference_students": len(ds.reference)},
        "decisions": {d: dec(d) for d in ("AUTO_APPROVE", "AWAITING_SCHEDULING", "ALREADY_PROCESSED", "EXCEPTION")},
        "form_level_exceptions": sum(1 for c in exc_cases if c["record_type"] == "faculty_form"),
        "kpis": k, "timing": timing, "unscheduled_bookings": stuck,
        "estimated_effort_saved_sample": {"assumptions": assumptions, "minutes": saved_min, "label": "ILLUSTRATIVE ONLY - sample of 13 invoices"},
        "forms_approved_before_validation": [c["faculty_form_id"] for c in exc_cases if c["form_approval_status"] == "Approved"],
    }
