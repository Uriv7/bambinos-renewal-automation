"""Load + validate the five official CSVs. Inputs are opened read-only; a SHA-256 fingerprint is recorded
so the run can prove the originals were not modified."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import FILES, SCHEMAS
from .validators import clean


class SchemaError(Exception):
    pass


@dataclass
class Datasets:
    invoices: pd.DataFrame
    forms: pd.DataFrame
    bookings: pd.DataFrame
    schedule: pd.DataFrame
    reference: pd.DataFrame
    fingerprints: dict = field(default_factory=dict)
    excluded: list = field(default_factory=list)   # soft-deleted rows (never silently dropped)
    warnings: list = field(default_factory=list)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_all(input_dir: str | Path) -> Datasets:
    input_dir = Path(input_dir)
    frames, prints, warnings = {}, {}, []
    missing = [f for f in FILES.values() if not (input_dir / f).exists()]
    if missing:
        raise SchemaError(f"Missing input file(s) in {input_dir}: {missing}")
    for key, fname in FILES.items():
        p = input_dir / fname
        prints[fname] = sha256(p)
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        gone = [c for c in SCHEMAS[key] if c not in df.columns]
        if gone:
            raise SchemaError(f"{fname}: missing required column(s) {gone}")
        extra = [c for c in df.columns if c not in SCHEMAS[key]]
        if extra:
            warnings.append(f"{fname}: unexpected extra column(s) {extra} (ignored)")
        df = df[SCHEMAS[key]].apply(lambda s: s.map(clean)).astype(object)
        df = df.where(df.notna(), None)
        frames[key] = df
    excluded = []
    for key, df in frames.items():
        # Reference rows stay (flagged by deleted_at) so the engine can raise BATCH_INACTIVE explicitly.
        if "deleted_at" in df.columns and key != "reference":
            gone_rows = df[df["deleted_at"].notna()]
            for _, r in gone_rows.iterrows():
                excluded.append({"table": key, "id": r.get("id") or r.get("student_id"), "deleted_at": r["deleted_at"]})
            frames[key] = df[df["deleted_at"].isna()].reset_index(drop=True)
    return Datasets(fingerprints=prints, excluded=excluded, warnings=warnings, **frames)
