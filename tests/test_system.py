import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import EngineConfig, FILES
from src.data_loader import SchemaError, load_all
from src.main import run
from tests.conftest import write_world

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
needs_raw = pytest.mark.skipif(not (RAW / FILES["invoices"]).exists(), reason="official raw data not present")


def digest(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(folder).glob("*.csv"))}


def test_invalid_schema_missing_column_is_rejected(tmp_path, world):
    d = write_world(world, tmp_path / "in")
    f = d / FILES["invoices"]
    df = pd.read_csv(f); df.drop(columns=["net_amount"]).to_csv(f, index=False)
    with pytest.raises(SchemaError):
        load_all(d)


def test_missing_file_is_rejected(tmp_path, world):
    d = write_world(world, tmp_path / "in"); (d / FILES["schedule"]).unlink()
    with pytest.raises(SchemaError):
        load_all(d)


def test_cli_returns_error_code_on_bad_input(tmp_path, capsys):
    from src.main import main
    assert main(["--input", str(tmp_path), "--output", str(tmp_path / "o")]) == 2


def test_inputs_are_never_modified(tmp_path, world):
    d = write_world(world, tmp_path / "in"); before = digest(d)
    run(d, tmp_path / "out"); run(d, tmp_path / "out")
    assert digest(d) == before


def test_rerun_is_reproducible_and_idempotent(tmp_path, world):
    d = write_world(world, tmp_path / "in")
    r1 = run(d, tmp_path / "o1")
    files = ["auto_approved.csv", "flagged_exceptions.csv", "booking_ready.csv", "follow_up_messages.csv", "audit_log.csv", "reconciliation_summary.json"]
    first = {f: (tmp_path / "o1" / f).read_bytes() for f in files}
    r2 = run(d, tmp_path / "o1")  # same output dir + same ledger
    assert len(r1["run_report"]["new_simulated_executions"]) == 1
    assert r2["run_report"]["new_simulated_executions"] == [] and len(r2["run_report"]["skipped_already_executed"]) == 1
    assert {f: (tmp_path / "o1" / f).read_bytes() for f in files} == first
    state = json.loads((tmp_path / "o1" / "processing_state.json").read_text()); assert len(state) == 1


def test_after_execution_snapshot_shows_existing_booking_not_a_new_one(tmp_path, world):
    from tests.test_scenarios import _booking
    world["bookings"] = [_booking()]
    run(write_world(world, tmp_path / "in"), tmp_path / "o")
    auto = pd.read_csv(tmp_path / "o" / "auto_approved.csv")
    assert len(auto) == 0   # already has a booking -> never emitted as new approval


def test_messages_are_drafts_and_respect_privacy(tmp_path, world):
    world["forms"] = []
    world["invoices"][0].update(created_at="2026-11-01 09:55:00")
    run(write_world(world, tmp_path / "in"), tmp_path / "o", EngineConfig(as_of="2026-11-01 13:00:00"))
    m = pd.read_csv(tmp_path / "o" / "follow_up_messages.csv")
    assert (m["send_status"].str.startswith("DRAFT")).all()
    teacher = m[m["recipient_type"] == "teacher"].iloc[0]
    assert "10000" not in teacher["draft_message"] and "pay_1" not in " ".join(m["draft_message"])
    assert teacher["reason_code"] == "MISSING_FACULTY_FORM"


def test_messages_work_without_llm_key(tmp_path, world, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = run(write_world(world, tmp_path / "in"), tmp_path / "o", use_llm=True)
    assert "no ANTHROPIC_API_KEY" in r["run_report"]["llm"]


def test_metrics_are_computed_from_data(tmp_path, world):
    world["forms"] = []
    run(write_world(world, tmp_path / "in"), tmp_path / "o")
    k = {x["metric"]: x for x in json.loads((tmp_path / "o" / "operational_metrics.json").read_text())["kpis"]}
    assert k["Paid invoices"]["numerator"] == 1 and k["Orphaned paid invoices"]["value_pct"] == 100.0
    assert k["Auto-approval eligibility rate"]["numerator"] == 0


def test_all_cases_accounted_for(tmp_path, world):
    s = run(write_world(world, tmp_path / "in"), tmp_path / "o")["summary"]
    assert sum(s["decisions"].values()) + s["form_level_exceptions"] == s["total_cases"]


@needs_raw
def test_official_dataset_expected_outcomes(tmp_path):
    s = run(RAW, tmp_path / "o")["summary"]
    assert s["records_processed"]["invoices"] == 13
    assert s["decisions"] == {"AUTO_APPROVE": 2, "AWAITING_SCHEDULING": 1, "ALREADY_PROCESSED": 1, "EXCEPTION": 9}
    assert s["form_level_exceptions"] == 1


@needs_raw
def test_official_auto_approved_are_exactly_84903_and_84908(tmp_path):
    run(RAW, tmp_path / "o")
    a = pd.read_csv(tmp_path / "o" / "auto_approved.csv", dtype=str)
    assert sorted(a["invoice_id"]) == ["84903", "84908"]
    assert a.set_index("invoice_id").loc["84908", "suppressed_duplicate_form_ids"] == "3309"
