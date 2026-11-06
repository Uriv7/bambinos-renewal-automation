"""Deterministic duplicate detection (invoices and faculty forms)."""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .config import FORM_PAYLOAD_FIELDS
from .validators import parse_money, parse_ts, clean


def group_forms_by_invoice(forms: pd.DataFrame) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in forms.to_dict("records"):
        out[str(r["invoice_id"])].append(r)
    for k in out:  # earliest first; id is the deterministic tiebreaker
        out[k].sort(key=lambda r: (str(r["created_at"]), int(r["id"])))
    return out


def form_payload(form: dict) -> tuple:
    return tuple(str(clean(form.get(f))) for f in FORM_PAYLOAD_FIELDS)


def resolve_duplicate_forms(forms_for_invoice: list[dict]) -> dict:
    """Returns canonical form + duplicates + whether every duplicate has an identical payload."""
    if not forms_for_invoice:
        return {"canonical": None, "duplicates": [], "identical": True}
    canon, dups = forms_for_invoice[0], forms_for_invoice[1:]
    identical = all(form_payload(d) == form_payload(canon) for d in dups)
    return {"canonical": canon, "duplicates": dups, "identical": identical}


def find_duplicate_invoices(invoices: pd.DataFrame, window_days: int) -> dict[str, list[str]]:
    """Invoice ids that collide with another invoice. Flags: duplicate invoice_number, duplicate gateway
    payment id, or the same student+class having >1 Paid/Partially_Paid invoice within the window."""
    hits: dict[str, set] = defaultdict(set)
    rows = invoices.to_dict("records")
    for key in ("invoice_number", "gateway_payment_id"):
        seen = defaultdict(list)
        for r in rows:
            if clean(r.get(key)) is not None:
                seen[r[key]].append(str(r["id"]))
        for ids in seen.values():
            if len(ids) > 1:
                for i in ids:
                    hits[i].update(x for x in ids if x != i)
    by_sc = defaultdict(list)
    for r in rows:
        if r["payment_status"] in ("Paid", "Partially_Paid"):
            by_sc[(r["student_id"], r["class_id"])].append(r)
    for grp in by_sc.values():
        for a in grp:
            for b in grp:
                if a is b:
                    continue
                ta, tb = parse_ts(a["created_at"]), parse_ts(b["created_at"])
                if ta is not None and tb is not None and abs((ta - tb).days) <= window_days:
                    hits[str(a["id"])].add(str(b["id"]))
    return {k: sorted(v) for k, v in hits.items()}
