"""Batch validity + capacity using the reference table. Capacity is only as good as the reference snapshot."""
from __future__ import annotations

from .validators import parse_int


def batch_snapshot(ref_row: dict | None) -> dict:
    if not ref_row:
        return {"exists": False, "active": False, "count": None, "max": None, "seats_left": None}
    count, mx = parse_int(ref_row.get("active_students_count")), parse_int(ref_row.get("max_batch_size"))
    active = ref_row.get("deleted_at") is None
    return {"exists": True, "active": active, "count": count, "max": mx,
            "seats_left": (mx - count) if (count is not None and mx is not None) else None}


def check_capacity(snapshot: dict, same_batch_renewal: bool, seat_already_held: bool) -> tuple[bool, str]:
    """Returns (ok, explanation). A same-batch renewal only skips the seat check when the
    assumption A1 flag (seat already counted) has been explicitly enabled."""
    if not snapshot["exists"] or not snapshot["active"]:
        return False, "batch missing or inactive"
    if snapshot["seats_left"] is None:
        return False, "capacity data unavailable"
    if same_batch_renewal and seat_already_held:
        return True, "same-batch renewal; seat assumed already held (assumption A1 enabled)"
    if snapshot["seats_left"] <= 0:
        return False, f"batch full ({snapshot['count']}/{snapshot['max']})"
    return True, f"{snapshot['seats_left']} seat(s) left ({snapshot['count']}/{snapshot['max']})"
