"""Follow-up drafts. Deterministic templates always work offline. If ANTHROPIC_API_KEY is set and
--use-llm is passed, the *wording only* may be polished by an LLM; decisions, reason codes and recipients are
never changed by it. All messages are DRAFTS - nothing is sent. Privacy: no payment amounts to teachers' group
chats, no child names (masked ids only), no gateway ids."""
from __future__ import annotations

import json
import os
import urllib.request

from .config import REASONS

SIGN = "- Bambinos.live Operations"


def _teacher(c, d):
    inv = c["invoice_number"] or f"invoice {c['invoice_id']}"
    code = d["code"]
    if code == "MISSING_FACULTY_FORM":
        return ("TEACHER_FORM_REMINDER", f"Hi {c['educator_name']}, we received a renewal payment ({inv}) for your student "
                f"(id {c['student_id']}) but no renewal form yet. Could you please submit it today so the classes can be scheduled? {SIGN}")
    if code == "INVALID_REFERENCE":
        return ("TEACHER_FORM_CORRECTION", f"Hi {c['educator_name']}, the renewal form for student id {c['student_id']} cites an invoice "
                f"number that does not match our records. Please resubmit it with the correct invoice link ({inv}). {SIGN}")
    if code == "INVOICE_NOT_FOUND":
        return ("TEACHER_FORM_CORRECTION", f"Hi {c['educator_name']}, form {c['faculty_form_id']} cites invoice {c['invoice_id']}, "
                f"which we cannot find. Please check the invoice link and resubmit. {SIGN}")
    if code == "AMOUNT_MISMATCH":
        return ("TEACHER_AMOUNT_CHECK", f"Hi {c['educator_name']}, the amount on your renewal form for student id {c['student_id']} does "
                f"not match the payment we received. Please recheck the invoice ({inv}) and confirm. {SIGN}")
    return None


def _parent(c, d):
    code = d["code"]
    if code == "PARENT_CONTACT_MISMATCH":
        return ("PARENT_CONTACT_CONFIRMATION", "Hello, we received a renewal payment for your child's class from a different number than "
                "the one on file. Could you please confirm that the payment was made by you or someone you authorised? " + SIGN)
    if code == "PARTIAL_PAYMENT":
        return ("PARENT_INSTALMENT_REMINDER", "Hello, we have received the first instalment for your child's renewal. Your second instalment "
                f"is pending; please complete it using your payment link (ref {c['invoice_number']}) so we can confirm the schedule. " + SIGN)
    if code == "PAYMENT_NOT_VERIFIED":
        return ("PARENT_PAYMENT_STATUS", f"Hello, we could not yet confirm your renewal payment (ref {c['invoice_number']}). If the amount "
                "was debited, please share the transaction reference and we will check right away; otherwise you can retry from the same link. " + SIGN)
    if code in ("BATCH_FULL", "MANUAL_REVIEW_REQUIRED") and c["same_batch_renewal"] is False:
        return ("PARENT_BATCH_CHANGE", "Hello, thank you for renewing. You asked for a different batch (weekend 11 AM). We are checking "
                "availability and will share the batch options shortly - please reply with a second preferred slot. " + SIGN)
    if code == "BATCH_FULL":
        return ("PARENT_BATCH_UPDATE", "Hello, thank you for renewing. We are confirming your child's seat for the next cycle and will update "
                "you shortly. No action is needed from you right now. " + SIGN)
    return None


def _ops(c, d):
    return ("OPS_ESCALATION", f"[{d['priority']}] {d['code']} - case {c['case_id']} (invoice {c['invoice_id']}, student {c['student_id']}). "
            f"{d['why']} Action: {d['action']}")


def _rows(c, d, recipient_type, recipient_id, channel, purpose, text):
    return {"case_id": c["case_id"], "recipient_type": recipient_type, "recipient_identifier": recipient_id, "channel": channel,
            "message_purpose": purpose, "related_invoice": c["invoice_id"], "related_student": c["student_id"], "reason_code": d["code"],
            "priority": d["priority"], "draft_message": text, "send_status": "DRAFT_NOT_SENT"}


def generate_messages(cases: list, exceptions: list, as_of) -> list[dict]:
    out, exmap = [], {e["record_id"]: e for e in exceptions}
    for c in cases:
        if c["decision"] == "AUTO_APPROVE":
            out.append({"case_id": c["case_id"], "recipient_type": "parent", "recipient_identifier": f"user:{c['user_id']} ({c['registered_mobile_masked']})",
                        "channel": "WhatsApp", "message_purpose": "PARENT_RENEWAL_CONFIRMED", "related_invoice": c["invoice_id"],
                        "related_student": c["student_id"], "reason_code": "AUTO_APPROVED", "priority": "P3",
                        "draft_message": f"Hello, your renewal payment (ref {c['invoice_number']}) is confirmed. Classes continue in the same batch; "
                                         f"you will receive the schedule shortly. {SIGN}", "send_status": "DRAFT_NOT_SENT (send only after booking is created)"})
        elif c["decision"] == "AWAITING_SCHEDULING":
            h = c["booking_age_hours"] or 0
            out.append({"case_id": c["case_id"], "recipient_type": "ops", "recipient_identifier": "Scheduling Ops", "channel": "Ops queue",
                        "message_purpose": "OPS_SCHEDULING_SLA", "related_invoice": c["invoice_id"], "related_student": c["student_id"],
                        "reason_code": "SCHEDULING_PENDING", "priority": "P1" if h > 4 else "P2",
                        "draft_message": f"[SLA] Booking {c['booking_id']} (invoice {c['invoice_id']}) is fully validated but has had no schedule rows for {h:.1f}h. Please create the schedule.",
                        "send_status": "DRAFT_NOT_SENT"})
    for e in exceptions:
        c = next(x for x in cases if x["case_id"] == e["record_id"])
        for code in c["reason_codes"]:
            pol = REASONS[code]
            d = {"code": code, "priority": pol.priority, "action": pol.action, "why": "; ".join(c["details"].get(code, []))}
            t = _teacher(c, d)
            if code == "MISSING_FACULTY_FORM" and "INVALID_REFERENCE" in c["reason_codes"]:
                t = None   # the correction request already covers it; avoid a redundant second message
            if t:
                out.append(_rows(c, d, "teacher", f"educator:{c['educator_id']}", "WhatsApp", t[0], t[1]))
            p = _parent(c, d)
            if p:
                out.append(_rows(c, d, "parent", f"user:{c['user_id']} ({c['registered_mobile_masked']})", "WhatsApp", p[0], p[1]))
        top = {"code": e["primary_reason_code"], "priority": e["priority"], "action": e["recommended_action"], "why": e["explanation"][:300]}
        purpose, text = _ops(c, top)
        out.append(_rows(c, top, "ops", e["assigned_owner"], "Ops queue", purpose, text))
    seen, uniq = set(), []
    for m in out:
        k = (m["case_id"], m["recipient_identifier"], m["message_purpose"])
        if k not in seen:
            seen.add(k); uniq.append(m)
    return uniq


def polish_with_llm(messages: list[dict]) -> tuple[list[dict], str]:
    """Optional. Requires ANTHROPIC_API_KEY. NOT exercised in this submission's tests (no key/credentials)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return messages, "LLM disabled: no ANTHROPIC_API_KEY; deterministic templates used"
    model = os.environ.get("BAMBINOS_LLM_MODEL", "claude-sonnet-5-5")
    done = 0
    for m in messages:
        if m["recipient_type"] == "ops":
            continue
        body = {"model": model, "max_tokens": 300, "system": "Rewrite the WhatsApp draft to be concise, polite and actionable. Keep every fact. Add no new facts, amounts or names. Return only the message.",
                "messages": [{"role": "user", "content": m["draft_message"]}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                txt = json.loads(r.read())["content"][0]["text"].strip()
            if txt:
                m["draft_message"], done = txt, done + 1
        except Exception:
            continue   # fall back to the template silently-but-safely; decisions are unaffected
    return messages, f"LLM polished {done} draft(s); decisions unchanged"
