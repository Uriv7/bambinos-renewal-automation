"""Schedule checks: existing rows per booking and overlap (student / teacher) detection."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd

from .validators import clean, norm_days, yes

DAY_IDX = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def active_schedule_rows(schedule: pd.DataFrame) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in schedule.to_dict("records"):
        if not yes(r.get("is_cancelled")):
            out[str(r["bookingrequest_id"])].append(r)
    return out


def _span(date, start, end):
    s = datetime.fromisoformat(f"{date} {start}")
    e = datetime.fromisoformat(f"{date} {end}")
    return s, e


def find_session_overlaps(schedule: pd.DataFrame, key: str) -> list[tuple]:
    """Overlapping non-cancelled sessions for the same `key` (student_id | educator_id).
    Sessions of the same batch on the same slot (a group class) are not conflicts for educator."""
    rows = [r for r in schedule.to_dict("records") if not yes(r.get("is_cancelled"))]
    by = defaultdict(list)
    for r in rows:
        by[r[key]].append(r)
    out = []
    for k, grp in by.items():
        for i, a in enumerate(grp):
            for b in grp[i + 1:]:
                if key == "educator_id" and a["classbatch_id"] == b["classbatch_id"] and \
                        a["class_date"] == b["class_date"] and a["start_time"] == b["start_time"]:
                    continue
                sa, ea = _span(a["class_date"], a["start_time"], a["end_time"])
                sb, eb = _span(b["class_date"], b["start_time"], b["end_time"])
                if sa < eb and sb < ea:
                    out.append((k, a["id"], b["id"]))
    return out


def batch_slot_conflicts(ref_rows: list[dict], educator_id: str, batch_id: str, session_minutes: int) -> list[str]:
    """Recurring-slot overlap: other active batches of the same educator on a shared weekday that overlap
    in time. Based on the reference table only (partial view of the batch catalogue)."""
    mine = next((r for r in ref_rows if r["current_classbatch_id"] == batch_id), None)
    if not mine or clean(mine["batch_start_time"]) is None:
        return []
    out = set()
    for r in ref_rows:
        if r["educator_id"] != educator_id or r["current_classbatch_id"] == batch_id or r.get("deleted_at"):
            continue
        shared = set(norm_days(mine["batch_days"])) & set(norm_days(r["batch_days"]))
        if not shared:
            continue
        a = datetime.fromisoformat(f"2000-01-01 {mine['batch_start_time']}")
        b = datetime.fromisoformat(f"2000-01-01 {r['batch_start_time']}")
        if abs((a - b).total_seconds()) < session_minutes * 60:
            out.add(r["current_classbatch_id"])
    return sorted(out)
