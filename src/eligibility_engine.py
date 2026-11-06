"""Rule engine for one invoice. Every rule is deterministic and writes to the audit trail.
AUTO_APPROVE is only possible when NO blocking reason code is raised.
LLMs are never consulted here."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .batch_capacity import batch_snapshot, check_capacity
from .config import REASONS, REQUIRED_FORM_FIELDS, EngineConfig
from .duplicate_detector import resolve_duplicate_forms
from .matching_engine import link_invoice_to_form
from .scheduling_validator import batch_slot_conflicts
from .validators import (clean, hours_between, norm_days, normalize_email, normalize_phone, parse_money, parse_ts, yes)

CODE_RANK = ["PAYMENT_NOT_VERIFIED", "DUPLICATE_INVOICE", "STUDENT_ID_MISMATCH", "AMOUNT_MISMATCH", "PARTIAL_PAYMENT",
             "BATCH_FULL", "BATCH_INACTIVE", "SCHEDULING_CONFLICT", "INVALID_REFERENCE", "INVOICE_NOT_FOUND",
             "ORPHANED_INVOICE", "TEACHER_ID_MISMATCH", "COURSE_MISMATCH", "DISCOUNT_REQUIRES_APPROVAL",
             "PARENT_CONTACT_MISMATCH", "MISSING_FACULTY_FORM", "TIMESTAMP_ANOMALY", "DUPLICATE_FACULTY_FORM",
             "MISSING_REQUIRED_FIELD", "MANUAL_REVIEW_REQUIRED"]


@dataclass
class Context:
    cfg: EngineConfig
    as_of: pd.Timestamp
    forms_by_invoice: dict
    all_forms: list
    invoice_ids: set
    ref_by_student: dict
    ref_rows: list
    bookings_by_invoice: dict
    sched_by_booking: dict
    dup_invoices: dict
    student_overlaps: dict
    educator_overlaps: dict
    audit: Any


class Case:
    def __init__(self, case_id, invoice_id, audit):
        self.case_id, self.invoice_id, self.audit = case_id, invoice_id, audit
        self.blocking: dict[str, list[str]] = {}
        self.info: dict[str, list[str]] = {}
        self.notes: list[str] = []

    def flag(self, code, detail, blocking=None):
        is_block = REASONS[code].blocking if blocking is None else blocking
        bucket = self.blocking if is_block else self.info
        if detail not in bucket.setdefault(code, []):
            bucket[code].append(detail)

    def log(self, step, rule, result, detail=""):
        self.audit.log(self.case_id, self.invoice_id, step, rule, result, detail)


def idempotency_key(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _eq(a, b):
    return clean(a) is not None and clean(b) is not None and str(a) == str(b)


def evaluate_invoice(inv: dict, ctx: Context) -> dict:
    cfg, as_of = ctx.cfg, ctx.as_of
    iid = str(inv["id"])
    c = Case(f"CASE-{iid}", iid, ctx.audit)
    ref = ctx.ref_by_student.get(inv["student_id"])
    net, gross, disc = parse_money(inv["net_amount"]), parse_money(inv["amount"]), parse_money(inv["discount_amount"])
    paid_at, inv_created = parse_ts(inv["paid_at"]), parse_ts(inv["created_at"])

    # R01 payment verification -------------------------------------------------------------------------------
    st = inv["payment_status"]
    if st == "Paid":
        if paid_at is not None and clean(inv["gateway_payment_id"]) and net and net > 0:
            c.log("payment", "R01_PAYMENT_VERIFIED", "PASS", f"Paid, gateway id present, paid_at {paid_at}")
        else:
            c.flag("PAYMENT_NOT_VERIFIED", "status is Paid but paid_at / gateway_payment_id / amount is missing")
            c.log("payment", "R01_PAYMENT_VERIFIED", "FAIL", "Paid without gateway evidence")
    elif st == "Partially_Paid":
        c.flag("PARTIAL_PAYMENT", f"{inv['payment_type']}: {net} received of {gross}")
        c.log("payment", "R01_PAYMENT_VERIFIED", "FAIL", f"Partially_Paid {net}/{gross}")
    else:
        c.flag("PAYMENT_NOT_VERIFIED", f"payment_status={st}; gateway_payment_id={clean(inv['gateway_payment_id'])}; "
                                       f"paid_at={clean(inv['paid_at'])}")
        c.log("payment", "R01_PAYMENT_VERIFIED", "FAIL", f"status {st}")

    # R02 invoice integrity -------------------------------------------------------------------------------------
    problems = []
    if not yes(inv["is_renewal"]):
        problems.append("is_renewal is not Yes")
        c.flag("MANUAL_REVIEW_REQUIRED", "invoice is not flagged as a renewal")
    if not str(inv["invoice_link"] or "").endswith(str(inv["invoice_number"])):
        problems.append("invoice_link does not end with invoice_number")
        c.flag("INVALID_REFERENCE", "invoice_link does not match invoice_number")
    if inv["payment_type"] == "Full" and None not in (gross, disc, net) and gross - disc != net:
        problems.append("amount - discount != net_amount")
        c.flag("AMOUNT_MISMATCH", f"invoice arithmetic: {gross} - {disc} != {net}")
    c.log("invoice", "R02_INVOICE_INTEGRITY", "FAIL" if problems else "PASS", "; ".join(problems))

    # R03 duplicate invoices ------------------------------------------------------------------------------------
    d = ctx.dup_invoices.get(iid)
    if d:
        c.flag("DUPLICATE_INVOICE", f"collides with invoice(s) {', '.join(d)}")
    c.log("invoice", "R03_DUPLICATE_INVOICE", "FAIL" if d else "PASS", ", ".join(d or []))

    # R04 form linkage (exact invoice id only) --------------------------------------------------------------------
    link = link_invoice_to_form(inv, ctx.forms_by_invoice, ctx.all_forms, ctx.invoice_ids)
    dup = resolve_duplicate_forms(link["forms"])
    form = dup["canonical"]
    pay_age = hours_between(paid_at, as_of)
    stage = "n/a"
    virtual = False
    if form is None and cfg.extra.get("invoice_first") and ref is not None and st == "Paid":
        # WHAT-IF SIMULATION ONLY (not the production rule set): derive the renewal from the paid invoice + reference.
        virtual = True
        form = {"id": f"VIRTUAL-{iid}", "educator_id": ref["educator_id"], "educator_name": ref["educator_name"], "user_id": inv["user_id"],
                "student_id": inv["student_id"], "parent_mobile": inv["mobile"], "class_id": ref["class_id"], "current_classbatch_id": ref["current_classbatch_id"],
                "invoice_id": iid, "amount_paid": inv["net_amount"], "sessions_purchased": str(cfg.standard_sessions), "continue_same_batch": "Yes",
                "preferred_days": ref["batch_days"], "preferred_time_slot": ref["batch_start_time"], "approval_status": "N/A", "approved_by": None, "created_at": None}
    if form is None:
        paid_ok = st == "Paid"
        if link["probable_form"]:
            pf = link["probable_form"]
            c.flag("INVALID_REFERENCE", f"form {pf['id']} references non-existent invoice {pf['invoice_id']}; probable match "
                                        f"to this invoice (confidence {link['confidence']}: {link['hint']}) - hint only")
            c.flag("MISSING_FACULTY_FORM", "no form is linked to this invoice by exact invoice id")
            stage = "correction_needed"
        elif paid_ok:
            c.flag("MISSING_FACULTY_FORM", f"paid {pay_age:.1f}h before as-of with no faculty form")
            if pay_age is not None and pay_age >= cfg.teacher_escalation_hours:
                c.flag("ORPHANED_INVOICE", f"no form {pay_age:.1f}h after payment (>= {cfg.teacher_escalation_hours:g}h escalation)")
                stage = "escalate"
            elif pay_age is not None and pay_age >= cfg.teacher_reminder_hours:
                stage = "reminder_due"
            else:
                stage = "not_yet_due"
        c.log("linkage", "R04_FORM_LINKED", "FAIL", f"method={link['method']} confidence={link['confidence']} {link['hint']}")
    else:
        c.log("linkage", "R04_FORM_LINKED", "PASS", "WHAT-IF: renewal derived from invoice + reference (no teacher form)" if virtual else f"form {form['id']} via exact invoice id")

    # R05 duplicate forms --------------------------------------------------------------------------------------
    if dup["duplicates"]:
        ids = ", ".join(str(x["id"]) for x in dup["duplicates"])
        if dup["identical"] and cfg.collapse_identical_duplicate_forms:
            c.flag("DUPLICATE_FACULTY_FORM", f"identical duplicate form(s) {ids} collapsed into earliest form {form['id']}", blocking=False)
            c.log("forms", "R05_DUPLICATE_FORM", "INFO", f"identical payload; kept {form['id']}, suppressed {ids}")
        else:
            c.flag("DUPLICATE_FACULTY_FORM", f"non-identical duplicate form(s) {ids}", blocking=True)
            c.log("forms", "R05_DUPLICATE_FORM", "FAIL", f"payload differs: {ids}")
    else:
        c.log("forms", "R05_DUPLICATE_FORM", "PASS", "no duplicates")

    # R06 student identity ---------------------------------------------------------------------------------------
    if ref is None:
        c.flag("INVALID_REFERENCE", f"student_id {inv['student_id']} not found in reference table")
        c.log("identity", "R06_STUDENT_IDENTITY", "FAIL", "student not in reference")
    else:
        bad = []
        if not _eq(ref["user_id"], inv["user_id"]):
            bad.append(f"user_id invoice {inv['user_id']} vs reference {ref['user_id']}")
        if form and (not _eq(form["student_id"], inv["student_id"]) or not _eq(form["user_id"], inv["user_id"])):
            bad.append("student/user ids differ between invoice and form")
        if ref.get("deleted_at"):
            c.flag("INVALID_REFERENCE", "student record is soft-deleted in reference")
        if bad:
            c.flag("STUDENT_ID_MISMATCH", "; ".join(bad))
        c.log("identity", "R06_STUDENT_IDENTITY", "FAIL" if bad else "PASS", "; ".join(bad) or "ids agree (names/phones not used)")

    # R07 teacher + course ---------------------------------------------------------------------------------------
    if ref is not None:
        same_batch = bool(form) and yes(form["continue_same_batch"])
        bad_t, bad_c = [], []
        for src, row in (("invoice", inv), ("form", form)):
            if row is None:
                continue
            if not _eq(row["educator_id"], ref["educator_id"]):
                bad_t.append(f"{src} educator {row['educator_id']} vs reference {ref['educator_id']}")
            if not _eq(row["class_id"], ref["class_id"]):
                bad_c.append(f"{src} class {row['class_id']} vs reference {ref['class_id']}")
        if bad_t and (same_batch or form is None):
            c.flag("TEACHER_ID_MISMATCH", "; ".join(bad_t))
        if bad_c and (same_batch or form is None):
            c.flag("COURSE_MISMATCH", "; ".join(bad_c))
        c.log("teacher_course", "R07_TEACHER_COURSE", "FAIL" if (bad_t or bad_c) else "PASS", "; ".join(bad_t + bad_c))

    # R08 parent contact -----------------------------------------------------------------------------------------
    if ref is not None:
        bad = []
        if normalize_phone(inv["mobile"]) != normalize_phone(ref["registered_mobile_masked"]):
            bad.append(f"paying mobile {inv['mobile']} differs from registered {ref['registered_mobile_masked']}")
        if form and normalize_phone(form["parent_mobile"]) != normalize_phone(ref["registered_mobile_masked"]):
            bad.append(f"form parent_mobile {form['parent_mobile']} differs from registered {ref['registered_mobile_masked']}")
        if normalize_email(inv["email"]) != normalize_email(ref["registered_email_masked"]):
            bad.append("invoice email differs from registered email")
        if bad:
            c.flag("PARENT_CONTACT_MISMATCH", "; ".join(bad))
        c.log("contact", "R08_PARENT_CONTACT", "FAIL" if bad else "PASS", "; ".join(bad) or "phone/email agree (masked comparison)")

    # R09 amounts ----------------------------------------------------------------------------------------------
    fee = parse_money(ref["standard_fee_24_sessions_inr"]) if ref else None
    form_amt = parse_money(form["amount_paid"]) if form else None
    bad = []
    if form_amt is not None and net is not None and form_amt != net:
        bad.append(f"teacher form amount {form_amt} vs gateway net amount {net}")
        c.flag("AMOUNT_MISMATCH", bad[-1])
    if form and clean(form["sessions_purchased"]) and int(float(form["sessions_purchased"])) != cfg.standard_sessions:
        c.flag("MANUAL_REVIEW_REQUIRED", f"sessions_purchased={form['sessions_purchased']} (standard fee only defined for {cfg.standard_sessions})")
    elif st == "Paid" and inv["payment_type"] == "Full" and fee is not None and net is not None and net != fee:
        if disc and disc > 0 and gross == fee:
            c.flag("DISCOUNT_REQUIRES_APPROVAL", f"net {net} = standard fee {fee} less discount {disc}; no approver recorded in any source table")
            bad.append("unapproved discount")
        else:
            c.flag("AMOUNT_MISMATCH", f"net amount {net} differs from standard fee {fee}")
            bad.append("net != standard fee")
    c.log("amount", "R09_AMOUNT", "FAIL" if bad else "PASS", "; ".join(bad) or f"net {net} agrees with form and standard fee {fee}")

    # R10 required fields + R11 batch validity ------------------------------------------------------------------
    target_batch = None
    same_batch = bool(form) and yes(form["continue_same_batch"])
    snap = batch_snapshot(None)
    if form:
        miss = [f for f in REQUIRED_FORM_FIELDS if clean(form.get(f)) is None]
        if miss:
            c.flag("MISSING_REQUIRED_FIELD", f"form {form['id']} missing: {', '.join(miss)}")
        c.log("form", "R10_REQUIRED_FIELDS", "FAIL" if miss else "PASS", ", ".join(miss))
        if same_batch:
            target_batch = form["current_classbatch_id"]
            if ref is not None and not _eq(target_batch, ref["current_classbatch_id"]):
                c.flag("INVALID_REFERENCE", f"form batch {target_batch} differs from student's current batch {ref['current_classbatch_id']}")
            snap = batch_snapshot(ctx.ref_by_student.get(inv["student_id"]) if ref else None)
            if ref is not None and not snap["active"]:
                c.flag("BATCH_INACTIVE", f"batch {target_batch} is soft-deleted")
            c.log("batch", "R11_BATCH_VALID", "PASS" if snap["active"] else "FAIL", f"batch {target_batch} exists={snap['exists']} active={snap['active']}")
        else:
            c.flag("MISSING_REQUIRED_FIELD", "batch-change renewal: the form has no target-batch field, so the new batch is unknown")
            c.flag("MANUAL_REVIEW_REQUIRED", "batch-change renewal needs parent batch selection and a capacity check on the chosen batch")
            c.log("batch", "R11_BATCH_VALID", "FAIL", f"continue_same_batch=No; preferred {form['preferred_days']} {form['preferred_time_slot']}; target unknown")

        # R12 capacity (only meaningful when the target batch is known)
        if same_batch and snap["exists"]:
            ok, why = check_capacity(snap, True, cfg.same_batch_seat_already_held)
            if not ok and snap["active"]:
                note = " Likely a false positive if the student's own seat is already counted (assumption A1, needs Ops validation)." if snap["seats_left"] == 0 else ""
                c.flag("BATCH_FULL", why + "." + note)
            c.log("capacity", "R12_BATCH_CAPACITY", "PASS" if ok else "FAIL", why)
        # R13 preference vs batch slot
        if same_batch and ref is not None:
            if norm_days(form["preferred_days"]) != norm_days(ref["batch_days"]) or str(form["preferred_time_slot"]) != str(ref["batch_start_time"]):
                c.flag("MANUAL_REVIEW_REQUIRED", "preferred slot differs from the batch's fixed slot")
            c.log("slot", "R13_SLOT_MATCHES_BATCH", "PASS", f"{form['preferred_days']} {form['preferred_time_slot']} == batch slot")

        # R14 timeline sanity
        fc = parse_ts(form["created_at"])
        if fc is not None and inv_created is not None and fc < inv_created:
            c.flag("TIMESTAMP_ANOMALY", f"form {form['id']} created {fc} before invoice created {inv_created} (gap {hours_between(fc, inv_created)}h)")
        elif fc is not None and paid_at is not None and fc < paid_at:
            c.flag("TIMESTAMP_ANOMALY", f"form {form['id']} created {fc} before payment at {paid_at}")
        c.log("timeline", "R14_TIMELINE", "FAIL" if "TIMESTAMP_ANOMALY" in c.blocking else "PASS", "")

    # R15 existing booking / schedule ---------------------------------------------------------------------------
    bks = ctx.bookings_by_invoice.get(iid, [])
    booking = bks[0] if bks else None
    sched = []
    if len(bks) > 1:
        c.flag("MANUAL_REVIEW_REQUIRED", f"{len(bks)} booking requests exist for one invoice")
    if booking:
        sched = ctx.sched_by_booking.get(str(booking["id"]), [])
        c.flag("BOOKING_ALREADY_EXISTS", f"booking {booking['id']} status {booking['request_status']}")
        if form and not virtual and not _eq(booking["faculty_form_id"], form["id"]) and str(booking["faculty_form_id"]) not in [str(x["id"]) for x in dup["duplicates"]]:
            c.flag("INVALID_REFERENCE", f"booking {booking['id']} points to form {booking['faculty_form_id']}, not {form['id']}")
        if not _eq(booking["student_id"], inv["student_id"]):
            c.flag("STUDENT_ID_MISMATCH", f"booking student {booking['student_id']} vs invoice {inv['student_id']}")
        if clean(booking["classbatch_id"]) is None:
            c.flag("MISSING_REQUIRED_FIELD", f"booking {booking['id']} has no classbatch_id (status {booking['request_status']})")
        if sched:
            c.flag("SCHEDULE_ALREADY_EXISTS", f"{len(sched)} schedule row(s) for booking {booking['id']} (sessions_count {booking['sessions_count']})")
        c.log("booking", "R15_EXISTING_BOOKING", "INFO", f"booking {booking['id']} {booking['request_status']}; schedule rows {len(sched)}")
        if booking["request_status"] == "Failed_Batch_Full" and "BATCH_FULL" not in c.blocking:
            c.flag("MANUAL_REVIEW_REQUIRED", "existing booking failed with Batch_Full but the engine's capacity check passes")
    else:
        c.log("booking", "R15_EXISTING_BOOKING", "PASS", "no booking exists; would be created exactly once")

    # R16 scheduling conflicts -------------------------------------------------------------------------------------
    conflicts, slot_info = [], []
    if same_batch and ref is not None:
        for b in batch_slot_conflicts(ctx.ref_rows, ref["educator_id"], ref["current_classbatch_id"], cfg.session_minutes):
            slot_info.append(f"educator {ref['educator_id']}: batch {ref['current_classbatch_id']} ({ref['batch_days']} {ref['batch_start_time']}) overlaps running batch {b} on a shared weekday "
                             f"assuming {cfg.session_minutes}-min sessions; pre-existing, informational only")
    conflicts += [f"student sessions overlap {x[1]}/{x[2]}" for x in ctx.student_overlaps.get(inv["student_id"], [])]
    conflicts += [f"educator sessions overlap {x[1]}/{x[2]}" for x in ctx.educator_overlaps.get(inv["educator_id"], [])]
    if conflicts:
        c.flag("SCHEDULING_CONFLICT", "; ".join(conflicts))
    for t in slot_info:
        c.flag("SCHEDULING_CONFLICT", t, blocking=False)
    c.log("conflicts", "R16_SCHEDULING_CONFLICT", "FAIL" if conflicts else ("INFO" if slot_info else "PASS"), "; ".join(conflicts + slot_info) or "no overlaps in available data")

    # Decision --------------------------------------------------------------------------------------------------
    if c.blocking:
        decision = "EXCEPTION"
    elif booking:
        s = booking["request_status"]
        if s == "Completed" and sched:
            decision = "ALREADY_PROCESSED"
        elif s == "Pending_Batch_Allocation":
            decision = "AWAITING_SCHEDULING"
        else:
            c.flag("MANUAL_REVIEW_REQUIRED", f"booking status {s} with {len(sched)} schedule rows is not a known clean state")
            decision = "EXCEPTION"
    else:
        decision = "AUTO_APPROVE"
    c.log("decision", "R17_DECISION", decision, "blocking: " + (", ".join(c.blocking) or "none"))

    codes = sorted(c.blocking, key=lambda k: CODE_RANK.index(k) if k in CODE_RANK else 99)
    if form and form["approval_status"] == "Approved" and decision == "EXCEPTION":
        c.notes.append(f"Form {form['id']} was already marked Approved by {form['approved_by']} despite the open issues above")
    sched_expected = int(float(booking["sessions_count"])) if booking and clean(booking["sessions_count"]) else None
    booking_age = hours_between(parse_ts(booking["created_at"]), as_of) if booking else None
    return {
        "case_id": c.case_id, "record_type": "invoice", "invoice_id": iid, "invoice_number": inv["invoice_number"],
        "faculty_form_id": form["id"] if form else None, "suppressed_duplicate_form_ids": "|".join(str(x["id"]) for x in dup["duplicates"]),
        "booking_id": booking["id"] if booking else None, "booking_status": booking["request_status"] if booking else None,
        "student_id": inv["student_id"], "user_id": inv["user_id"], "educator_id": inv["educator_id"], "class_id": inv["class_id"],
        "target_batch_id": target_batch, "same_batch_renewal": (None if form is None else same_batch),
        "payment_status": st, "net_amount": str(net), "standard_fee": str(fee) if fee is not None else None,
        "form_amount_paid": str(form_amt) if form_amt is not None else None, "sessions": cfg.standard_sessions,
        "preferred_days": form["preferred_days"] if form else None, "preferred_time": form["preferred_time_slot"] if form else None,
        "decision": decision, "reason_codes": codes, "info_codes": sorted(c.info), "details": {**c.blocking, **{k: v for k, v in c.info.items()}},
        "notes": c.notes, "match_method": link["method"], "match_confidence": link["confidence"],
        "payment_age_hours": pay_age, "teacher_followup_stage": stage,
        "scheduled_sessions": len(sched), "booking_sessions_count": sched_expected, "booking_age_hours": booking_age,
        "form_approval_status": form["approval_status"] if form else None,
        "idempotency_key": idempotency_key(iid, form["id"] if form else "-", inv["student_id"], target_batch, cfg.standard_sessions, decision),
        "mobile_masked": inv["mobile"], "registered_mobile_masked": ref["registered_mobile_masked"] if ref else None,
        "educator_name": (form or {}).get("educator_name") or (ref or {}).get("educator_name"),
        "parent_name_masked": inv["parent_name"],
    }
