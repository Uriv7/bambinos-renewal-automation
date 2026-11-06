"""CLI:  python -m src.main --input data/raw --output results"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from .config import EngineConfig
from .data_loader import SchemaError, load_all
from .data_profiler import profile
from .message_generator import generate_messages, polish_with_llm
from .metrics import compute_metrics
from .reconciliation import reconcile
from .report_generator import root_cause_table, run_markdown, theoretical_cases


def j(v):
    return "|".join(map(str, v)) if isinstance(v, (list, tuple)) else v


def write_csv(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")


def run(input_dir, output_dir, cfg: EngineConfig | None = None, use_llm=False, state_file=None) -> dict:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    ds = load_all(input_dir)
    res = reconcile(ds, cfg)
    cases, excs, as_of = res["cases"], res["exceptions"], res["as_of"]
    audit = res["audit"]
    inv_cases = [c for c in cases if c["record_type"] == "invoice"]

    rules_pass = audit[audit["result"] == "PASS"].groupby("case_id")["rule"].apply(lambda s: ", ".join(s)).to_dict()
    # --- decisions for every case (nothing silently dropped)
    allc = pd.DataFrame([{**{k: j(v) for k, v in c.items() if k not in ("details", "notes")},
                          "details": json.dumps(c["details"], ensure_ascii=False), "notes": "; ".join(c["notes"])} for c in cases])
    write_csv(allc, out / "case_decisions.csv")

    auto = [c for c in cases if c["decision"] == "AUTO_APPROVE"]
    cols = ["case_id", "invoice_id", "invoice_number", "faculty_form_id", "suppressed_duplicate_form_ids", "student_id", "user_id", "educator_id",
            "class_id", "target_batch_id", "sessions", "preferred_days", "preferred_time", "net_amount", "idempotency_key"]
    adf = pd.DataFrame([{k: c[k] for k in cols} | {"decision": "AUTO_APPROVE", "proposed_action": "CREATE_BOOKING_REQUEST (once) then CREATE_SCHEDULE",
                                                   "rules_passed": rules_pass.get(c["case_id"], ""),
                                                   "informational_flags": j(c["info_codes"])} for c in auto], columns=cols + ["decision", "proposed_action", "rules_passed", "informational_flags"])
    write_csv(adf, out / "auto_approved.csv")

    edf = pd.DataFrame(excs)
    write_csv(edf, out / "flagged_exceptions.csv")

    ready = [c for c in cases if c["decision"] in ("AUTO_APPROVE", "AWAITING_SCHEDULING")]
    bdf = pd.DataFrame([{"case_id": c["case_id"], "invoice_id": c["invoice_id"], "student_id": c["student_id"], "educator_id": c["educator_id"],
                         "class_id": c["class_id"], "classbatch_id": c["target_batch_id"], "sessions_to_schedule": c["sessions"],
                         "batch_days": c["preferred_days"], "batch_start_time": c["preferred_time"], "faculty_form_id": c["faculty_form_id"],
                         "booking_id": c["booking_id"],
                         "ready_type": "NEW_BOOKING" if c["decision"] == "AUTO_APPROVE" else "EXISTING_BOOKING_AWAITING_SCHEDULE",
                         "next_action": "Create booking request then schedule" if c["decision"] == "AUTO_APPROVE" else f"Create schedule for existing booking {c['booking_id']} (do NOT create another booking)",
                         "waiting_hours_since_booking": None if c["booking_age_hours"] is None else round(c["booking_age_hours"], 2),
                         "sla_status": ("BREACHED" if (c["booking_age_hours"] or 0) > res["cfg"].scheduling_sla_hours else "OK") if c["booking_id"] else "NOT_STARTED",
                         "idempotency_key": c["idempotency_key"]} for c in ready])
    write_csv(bdf, out / "booking_ready.csv")

    msgs = generate_messages(cases, excs, as_of)
    llm_note = "LLM not requested; deterministic templates"
    if use_llm:
        msgs, llm_note = polish_with_llm(msgs)
    write_csv(pd.DataFrame(msgs), out / "follow_up_messages.csv")

    if len(edf):
        g = edf.groupby("assigned_owner").agg(open_exceptions=("exception_id", "count"), p1_count=("priority", lambda s: int((s == "P1").sum())),
                                              cases=("record_id", lambda s: "|".join(x.replace("CASE-", "") for x in s)),
                                              reason_codes=("primary_reason_code", lambda s: "|".join(s))).reset_index()
        g = g.sort_values(["p1_count", "open_exceptions"], ascending=False)
    else:
        g = pd.DataFrame(columns=["assigned_owner", "open_exceptions", "p1_count", "cases", "reason_codes"])
    write_csv(g, out / "exceptions_by_owner.csv")
    write_csv(audit, out / "audit_log.csv")

    metrics = compute_metrics(ds, res)
    code_dist = {}
    for e in excs:
        for c in e["all_reason_codes"].split("|"):
            code_dist[c] = code_dist.get(c, 0) + 1
    summary = {"as_of": str(as_of), "records_processed": metrics["records"], "decisions": metrics["decisions"],
               "form_level_exceptions": metrics["form_level_exceptions"], "total_cases": len(cases),
               "reason_code_distribution": dict(sorted(code_dist.items(), key=lambda kv: -kv[1])),
               "primary_reason_distribution": edf["primary_reason_code"].value_counts().to_dict() if len(edf) else {},
               "exceptions_by_owner": g.set_index("assigned_owner")["open_exceptions"].to_dict() if len(g) else {},
               "engine_config": {k: v for k, v in vars(res["cfg"]).items() if k != "extra"},
               "input_fingerprints_sha256": ds.fingerprints, "kpis": metrics["kpis"]}
    (out / "reconciliation_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (out / "operational_metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    write_csv(pd.DataFrame(metrics["kpis"]), out / "kpi_table.csv")
    (out / "data_profile.json").write_text(json.dumps(profile(ds), indent=2, default=str))
    write_csv(root_cause_table(res), out / "root_cause_analysis.csv")
    (out / "reconciliation_report.md").write_text(run_markdown(res, metrics))

    # --- idempotency ledger (SIMULATED execution state; no production writes happen)
    sf = Path(state_file) if state_file else out / "processing_state.json"
    state = json.loads(sf.read_text()) if sf.exists() else {}
    new, skipped = [], []
    for c in ready:
        key = c["idempotency_key"]
        (skipped if key in state else new).append(c["case_id"])
        state.setdefault(key, {"case_id": c["case_id"], "action": "SIMULATED_CREATE_BOOKING" if c["decision"] == "AUTO_APPROVE" else "SIMULATED_CREATE_SCHEDULE", "first_seen_as_of": str(as_of)})
    sf.write_text(json.dumps(state, indent=2, sort_keys=True))
    run_report = {"new_simulated_executions": new, "skipped_already_executed": skipped, "llm": llm_note,
                  "inputs_unchanged": True, "note": "Run-specific facts live here so the other outputs stay byte-reproducible."}
    (out / "run_report.json").write_text(json.dumps(run_report, indent=2))
    return {"summary": summary, "run_report": run_report}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bambinos renewal -> scheduling reconciliation engine")
    ap.add_argument("--input", default="data/raw"); ap.add_argument("--output", default="results")
    ap.add_argument("--as-of", default=None, help="ISO timestamp for ageing; default = latest timestamp in data")
    ap.add_argument("--assume-same-batch-seat-held", action="store_true", help="Enable assumption A1 (needs Ops validation)")
    ap.add_argument("--whatif-invoice-first", action="store_true", help="SIMULATION: derive same-batch renewals from invoice+reference without a teacher form")
    ap.add_argument("--use-llm", action="store_true", help="Polish drafts with an LLM (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--state-file", default=None)
    a = ap.parse_args(argv)
    cfg = EngineConfig(as_of=a.as_of, same_batch_seat_already_held=a.assume_same_batch_seat_held, extra={'invoice_first': a.whatif_invoice_first})
    try:
        r = run(a.input, a.output, cfg, a.use_llm, a.state_file)
    except SchemaError as e:
        print(f"INPUT ERROR: {e}", file=sys.stderr); return 2
    s = r["summary"]
    print(f"Processed {s['records_processed']['invoices']} invoices | decisions {s['decisions']} | form-level exceptions {s['form_level_exceptions']}")
    print(f"Simulated executions: new={len(r['run_report']['new_simulated_executions'])} skipped={len(r['run_report']['skipped_already_executed'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
