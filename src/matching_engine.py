"""Deterministic record linkage. Only exact stable identifiers can link records for approval.
Fuzzy/probable matches are returned for *investigation only* and never grant eligibility."""
from __future__ import annotations

from .validators import is_transposition, parse_money


def link_invoice_to_form(inv: dict, forms_by_invoice: dict, all_forms: list[dict], invoice_ids: set) -> dict:
    exact = forms_by_invoice.get(str(inv["id"]), [])
    if exact:
        return {"method": "EXACT_INVOICE_ID", "confidence": 1.0, "forms": exact, "probable_form": None, "hint": ""}
    best = None
    for f in all_forms:
        if str(f["invoice_id"]) in invoice_ids:
            continue  # that form is already linked to a real invoice
        if f["student_id"] != inv["student_id"]:
            continue  # never match on names or phones; student_id is the anchor
        score, why = 0.6, "same student_id"
        if parse_money(f["amount_paid"]) == parse_money(inv["net_amount"]):
            score += 0.2; why += ", same amount"
        if is_transposition(str(f["invoice_id"]), str(inv["id"])):
            score += 0.2; why += f", invoice id {f['invoice_id']} is a digit transposition of {inv['id']}"
        if best is None or score > best[0]:
            best = (round(score, 2), f, why)
    if best:
        return {"method": "PROBABLE_STUDENT_AMOUNT", "confidence": best[0], "forms": [], "probable_form": best[1],
                "hint": best[2]}
    return {"method": "NONE", "confidence": 0.0, "forms": [], "probable_form": None, "hint": ""}
