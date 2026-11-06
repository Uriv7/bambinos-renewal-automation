"""Turns blocking reason codes into owned, prioritised exception records."""
from __future__ import annotations

import pandas as pd

from .config import P_SLA, REASONS
from .eligibility_engine import CODE_RANK

SEV_ORDER = ["Critical", "High", "Medium", "Low"]
PRI_ORDER = ["P1", "P2", "P3"]


def build_exception(case: dict, as_of: pd.Timestamp) -> dict:
    codes = case["reason_codes"]
    pols = [REASONS[c] for c in codes]
    primary = REASONS[codes[0]]
    sev = min((p.severity for p in pols), key=SEV_ORDER.index)
    pri = min((p.priority for p in pols), key=PRI_ORDER.index)
    explanation = " | ".join(f"[{c}] " + "; ".join(case["details"].get(c, [])) for c in codes)
    actions, seen = [], set()
    for c in codes[:3]:
        a = REASONS[c].action
        if a not in seen:
            actions.append(a); seen.add(a)
    return {
        "exception_id": "EXC-" + case["case_id"].replace("CASE-", ""),
        "record_id": case["case_id"], "record_type": case["record_type"],
        "invoice_id": case["invoice_id"], "faculty_form_id": case.get("faculty_form_id"), "booking_id": case.get("booking_id"),
        "student_id": case["student_id"], "educator_id": case["educator_id"],
        "primary_reason_code": primary.code, "all_reason_codes": "|".join(codes),
        "explanation": explanation + ((" | NOTE: " + "; ".join(case["notes"])) if case["notes"] else ""),
        "severity": sev, "priority": pri, "sla_target": P_SLA[pri], "assigned_owner": primary.owner,
        "recommended_action": " THEN ".join(actions), "notification_channel": primary.channel,
        "teacher_followup_stage": case["teacher_followup_stage"], "payment_age_hours": case["payment_age_hours"],
        "created_at": str(as_of), "status": "OPEN",
    }
