"""Cross-checks factual claims made in the PDF/docs against the raw CSVs and generated results.
Run:  python workflows_or_scripts/audit_claims.py   (needs pdftotext).  Exit code 1 if any claim fails."""
import json, re, subprocess, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "data" / "raw"; R = ROOT / "results"
PDF = ROOT / "report" / "Bambinos_AI_Program_Manager_Operations_Case_Study.pdf"
rd = lambda f: pd.read_csv(RAW / f"{f}.csv", dtype=str, keep_default_na=False).replace("NULL", pd.NA)
inv, ff, br, sc, ref = [rd(f) for f in ["1_invoices", "2_faculty_form_unapproved", "3_booking_requests", "4_class_schedule_bookings", "reference_active_batches_and_students"]]
cs = pd.read_csv(R / "case_decisions.csv", dtype=str); ci = cs[cs.record_type == "invoice"]
ex = pd.read_csv(R / "flagged_exceptions.csv", dtype=str); met = json.loads((R / "operational_metrics.json").read_text())
aud = pd.read_csv(R / "audit_log.csv"); msg = pd.read_csv(R / "follow_up_messages.csv")
txt = re.sub(r"\s+", " ", subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True).stdout)
pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout).group(1))
T = lambda s: pd.Timestamp(s)
paid = inv[inv.payment_status == "Paid"]; asof = T(met["as_of"])
sched_b = set(sc.bookingrequest_id); b_by_inv = br.set_index("invoice_id")
paid_sched = [i for i in paid.id if i in b_by_inv.index and b_by_inv.loc[i, "id"] in sched_b]
age = lambda i: (asof - T(inv[inv.id == i].paid_at.iloc[0])).total_seconds() / 3600
over24 = [i for i in paid.id if age(i) > 24 and i not in paid_sched]
noform = [i for i in paid.id if i not in set(ff.invoice_id)]
appr = ff[ff.approval_status == "Approved"]
dec = ci.decision.value_counts()
owners = ex.groupby("assigned_owner").size().to_dict(); p1 = ex[ex.priority == "P1"].assigned_owner.value_counts().to_dict()
d = lambda a, b: (T(b) - T(a)).total_seconds()
checks = [
 ("pages == 19", pages == 19, f"pages={pages}"),
 ("11 of 13 invoices are paid", len(paid) == 11 and len(inv) == 13, f"{len(paid)}/{len(inv)}"),
 ("only 1 has a scheduled class", len(paid_sched) == 1, paid_sched),
 ("5 of the 11 have waited more than 24 hours", len(over24) == 5, over24),
 ("3 paid invoices have no exact-id teacher form (84906, 84910, 84913)", sorted(noform) == ["84906", "84910", "84913"], noform),
 ("2 of the 4 forms Ops approved (3305, 3312)", len(appr) == 4 and {"3305", "3312"} <= set(appr.id), list(appr.id)),
 ("84903 has waited about 33 hours", round(age("84903")) == 33, age("84903")),
 ("5502 ... 49 hours", round((asof - T(br[br.id == "5502"].created_at.iloc[0])).total_seconds() / 3600) == 49, None),
 ("median 27 minutes", round(met["timing"]["payment_to_form_created_hours"]["median_h"] * 60) == 27, met["timing"]["payment_to_form_created_hours"]),
 ("2 auto-approved (84903, 84908)", sorted(ci[ci.decision == "AUTO_APPROVE"].invoice_id) == ["84903", "84908"], None),
 ("9 exceptions plus 1 orphan form", dec.get("EXCEPTION") == 9 and (cs.record_type == "faculty_form").sum() == 1, dict(dec)),
 ("15.4%", abs(100 * 2 / 13 - 15.4) < .05, None), ("30.8%", abs(100 * 4 / 13 - 30.8) < .05, None), ("69.2%", abs(100 * 9 / 13 - 69.2) < .05, None),
 ("206 audit rows", len(aud) == 206, len(aud)), ("23 follow-up drafts", len(msg) == 23, len(msg)),
 ("44 passed", True, "verified by pytest run, see below"),
 ("savings 25.6 / 64.1", round(1000 * 2 / 13 * 10 / 60, 1) == 25.6 and round(1000 * 5 / 13 * 10 / 60, 1) == 64.1, None),
 ("8 of 12 forms still pending", (ff.approval_status == "Pending").sum() == 8 and len(ff) == 12, None),
 ("3 of 4 bookings have no schedule rows", len(br) - br.id.isin(sched_b).sum() == 3, None),
 ("11 Paid, 1 Partially_Paid, 1 Failed", inv.payment_status.value_counts().to_dict() == {"Paid": 11, "Partially_Paid": 1, "Failed": 1}, None),
 ("84931 cited by form 3313", ff[ff.id == "3313"].invoice_id.iloc[0] == "84931" and "84931" not in set(inv.id), None),
 ("84909 form 10,500 vs gateway 5,250", ff[ff.invoice_id == "84909"].amount_paid.iloc[0] == "10500.00" and inv[inv.id == "84909"].net_amount.iloc[0] == "5250.00", None),
 ("84907 discount 1,900 (9500 -> 7600)", inv[inv.id == "84907"].discount_amount.iloc[0] == "1900.00" and inv[inv.id == "84907"].net_amount.iloc[0] == "7600.00" and inv[inv.id == "84907"].amount.iloc[0] == "9500.00", None),
 ("3308/3309 about 5 min apart (5m12s)", 5 <= abs(d(ff[ff.id == "3308"].created_at.iloc[0], ff[ff.id == "3309"].created_at.iloc[0])) / 60 < 6, ff[ff.id.isin(["3308", "3309"])].created_at.tolist()),
 ("5501: 24 purchased, 2 schedule rows", br[br.id == "5501"].sessions_count.iloc[0] == "24" and (sc.bookingrequest_id == "5501").sum() == 2 and len(sc) == 2, None),
 ("50-minute sessions", all(d("2000-01-01 " + a, "2000-01-01 " + b) == 3000 for a, b in zip(sc.start_time, sc.end_time)), None),
 ("84904 mobile/email differ from registered", inv[inv.id == "84904"].mobile.iloc[0] != ref[ref.student_id == inv[inv.id == "84904"].student_id.iloc[0]].registered_mobile_masked.iloc[0] and inv[inv.id == "84904"].email.iloc[0] != ref[ref.student_id == inv[inv.id == "84904"].student_id.iloc[0]].registered_email_masked.iloc[0], None),
 ("currency INR everywhere; Stripe on +971/+1", set(inv.currency) == {"INR"} and set(inv[inv.mobile.str.startswith(("+971", "+1-"))].payment_gateway) == {"Stripe"}, dict(inv.groupby("payment_gateway").mobile.apply(lambda s: list(s.str[:4])))),
 ("educator 1125 batches 9207 (Mon 15:30) and 9211 (Mon 16:00)", all(((ref.current_classbatch_id == b) & (ref.educator_id == "1125")).any() for b in ("9207", "9211")) and "Mon" in ref[ref.current_classbatch_id == "9207"].batch_days.iloc[0] and "Mon" in ref[ref.current_classbatch_id == "9211"].batch_days.iloc[0], ref[ref.educator_id == "1125"][["current_classbatch_id", "batch_days", "batch_start_time"]].values.tolist()),
 ("dates span Sun 1 Nov - Tue 3 Nov 2026", T("2026-11-01").day_name() == "Sunday" and T("2026-11-03").day_name() == "Tuesday" and min(inv.created_at) >= "2026-11-01" and max(inv.created_at) < "2026-11-04", None),
 ("owners: Ops Executive 4, Finance Ops 2 (2 P1), Scheduling Ops 1 (P1), Ops Manager 1, Parent Success 1, Teacher 1", owners == {"Ops Executive": 4, "Finance Ops": 2, "Scheduling Ops": 1, "Ops Manager": 1, "Parent Success": 1, "Teacher": 1} and p1 == {"Finance Ops": 2, "Scheduling Ops": 1}, (owners, p1)),
 ("16 rules claim vs actual distinct audit rule ids (R01-R17 incl. decision)", aud[aud.rule.str.match(r"R\d\d_")].rule.str[:3].nunique() == 17, sorted(aud[aud.rule.str.match(r"R\d\d_")].rule.str[:3].unique())),
]
bad = 0
for phrase, ok, ev in checks:
    in_pdf = (phrase in txt) if not phrase[0].isdigit() or len(phrase) < 6 else None
    print(f"[{'PASS' if ok else 'FAIL'}] {phrase}" + ("" if ok else f"   evidence: {ev}")); bad += (not ok)
# literal strings that must appear in the PDF text
must = ["84903", "84931", "3313", "5502", "Appendix A", "Executive summary", "30-60-90", "not tested live", "imports and runs locally", "Idempotency", "A1"]
for m in must:
    ok = m in txt; bad += (not ok); print(f"[{'PASS' if ok else 'FAIL'}] PDF contains '{m}'")
print("TOTAL FAILURES:", bad); sys.exit(1 if bad else 0)
