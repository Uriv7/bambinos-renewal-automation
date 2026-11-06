"""Pure normalisation helpers. Originals are never modified; callers keep raw values."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

import pandas as pd

NULL_TOKENS = {"", "null", "none", "nan", "na", "n/a"}


def is_missing(v) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(v, str) and v.strip().lower() in NULL_TOKENS


def clean(v):
    return None if is_missing(v) else (v.strip() if isinstance(v, str) else v)


def normalize_phone(v) -> str | None:
    """Canonical form for comparison: keep '+', digits and mask 'X'; drop spaces/dashes/brackets.
    The original value is always retained elsewhere."""
    v = clean(v)
    if v is None:
        return None
    s = re.sub(r"[^\d+Xx*]", "", str(v)).upper()
    return s or None


def normalize_email(v) -> str | None:
    v = clean(v)
    return None if v is None else str(v).strip().lower()


def parse_money(v) -> Decimal | None:
    v = clean(v)
    if v is None:
        return None
    try:
        return Decimal(str(v).replace(",", "")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def parse_ts(v) -> pd.Timestamp | None:
    v = clean(v)
    if v is None:
        return None
    t = pd.to_datetime(v, errors="coerce")
    return None if pd.isna(t) else t


def parse_int(v) -> int | None:
    v = clean(v)
    if v is None:
        return None
    try:
        return int(float(str(v)))
    except ValueError:
        return None


def yes(v) -> bool:
    return str(clean(v) or "").strip().lower() == "yes"


def norm_days(v) -> tuple[str, ...]:
    v = clean(v)
    return tuple(sorted(d.strip().title()[:3] for d in str(v).split(","))) if v else ()


def hours_between(a, b) -> float | None:
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 3600, 4)


def is_transposition(a: str, b: str) -> bool:
    """True when b equals a with exactly one pair of adjacent characters swapped (84913 vs 84931)."""
    a, b = str(a), str(b)
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
