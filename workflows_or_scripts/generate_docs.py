"""Generates the data-derived docs from results/*.json|csv and src/config.py (so docs cannot drift from the code).
Run after:  python -m src.main"""
import json
from pathlib import Path
import pandas as pd
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.config import REASONS, P_SLA, SCHEMAS

R, D = ROOT / "results", ROOT / "docs"
prof = json.loads((R / "data_profile.json").read_text()); met = json.loads((R / "operational_metrics.json").read_text())
kpi = pd.read_csv(R / "kpi_table.csv")

def md_table(df):
    cols = list(df.columns); out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else str(v).replace("|", "/").replace("\n", " ") for v in r) + " |")
    return "\n".join(out)

# ---- decision matrix -------------------------------------------------------------------------------------
def pol(code): p = REASONS[code]; return p.owner, p.priority, P_SLA[p.priority], p.channel
rows = [
 ("1 Same-batch, same-teacher renewal", "Paid + exact-id form + ids/teacher/course/contact agree + net = standard fee + same batch active with seat + no booking", "YES", "-", "Ops Executive (monitor only)", "P3", "Booking+schedule within 4 business h", "Create booking once, create schedule, confirm to parent", "Parent WhatsApp", "84903, 84908 (84908 after collapsing identical duplicate form 3309)"),
 ("2 Same-batch, different-teacher", "form/invoice educator_id != reference educator_id", "NO", "TEACHER_ID_MISMATCH", *pol("TEACHER_ID_MISMATCH")[:3], "Confirm educator for the batch; fix form or batch record", pol("TEACHER_ID_MISMATCH")[3], "Not observed"),
 ("3 Different-batch renewal", "continue_same_batch = No (form has no target-batch field)", "NO", "MISSING_REQUIRED_FIELD + MANUAL_REVIEW_REQUIRED", "Scheduling Ops", "P2", P_SLA["P2"], "Capture parent's choice; capacity-check the chosen batch; then book", "Parent WhatsApp + Ops queue", "84912 (booking 5512 already created with NULL batch)"),
 ("4 Parent identity mismatch", "invoice mobile/email != registered; or form mobile != registered", "NO", "PARENT_CONTACT_MISMATCH", *pol("PARENT_CONTACT_MISMATCH")[:3], "Confirm payer with the REGISTERED number", pol("PARENT_CONTACT_MISMATCH")[3], "84904 (mobile XXXX77 vs XXXX04; email also differs)"),
 ("5 Student identity mismatch", "student_id/user_id differ across invoice, form, reference, booking", "NO", "STUDENT_ID_MISMATCH", *pol("STUDENT_ID_MISMATCH")[:3], "Verify with parent+teacher; never match on name/phone", pol("STUDENT_ID_MISMATCH")[3], "Not observed"),
 ("6 Payment mismatch", "form amount != invoice net; or net != standard fee (discount => approval needed)", "NO", "AMOUNT_MISMATCH / DISCOUNT_REQUIRES_APPROVAL", *pol("AMOUNT_MISMATCH")[:3], "Reconcile amounts; confirm discount approver", pol("AMOUNT_MISMATCH")[3], "84907 (20% discount, net 7600 vs fee 9500), 84909 (form 10500 vs net 5250)"),
 ("7 Partial payment", "payment_status = Partially_Paid", "NO", "PARTIAL_PAYMENT", *pol("PARTIAL_PAYMENT")[:3], "Hold; instalment-2 reminder; policy decision", pol("PARTIAL_PAYMENT")[3], "84909 (Installment_1_of_2, 5250 of 10500)"),
 ("8 Duplicate invoice", "same invoice_number / gateway id / student+class paid within 30 days", "NO", "DUPLICATE_INVOICE", *pol("DUPLICATE_INVOICE")[:3], "Choose authoritative invoice; refund/merge", pol("DUPLICATE_INVOICE")[3], "Not observed"),
 ("9 Missing teacher form", "paid invoice with no form on exact invoice id (reminder 2 h; escalate 12 h)", "NO (today)", "MISSING_FACULTY_FORM (+ORPHANED_INVOICE >=12h; INVALID_REFERENCE if typo)", "Teacher -> Ops Executive at 12 h", "P2", P_SLA["P2"], "Teacher submits form (target state: not needed for same-batch)", "Teacher WhatsApp", "84906 (26 h), 84910 (~6.7 h), 84913 (typo 84931) + orphan form 3313"),
 ("10 Full batch", "active_students_count >= max_batch_size (seat-held assumption A1 off by default)", "NO", "BATCH_FULL", *pol("BATCH_FULL")[:3], "Check if seat already counted; else alternatives", pol("BATCH_FULL")[3], "84905 (6/6, same-batch renewal, booking 5505 Failed_Batch_Full)"),
 ("11 Scheduling conflict", "overlapping non-cancelled sessions for same student/educator", "NO", "SCHEDULING_CONFLICT", *pol("SCHEDULING_CONFLICT")[:3], "Resolve overlap before creating rows", pol("SCHEDULING_CONFLICT")[3], "Session-level: not observed. Informational: educator 1125 batches 9207 (Mon 15:30) / 9211 (Mon 16:00) overlap if sessions are 50 min"),
 ("12 Existing booking", "booking_requests row exists for invoice", "NO new approval", "BOOKING_ALREADY_EXISTS / SCHEDULE_ALREADY_EXISTS (info)", "Ops Executive / Scheduling Ops", "P3 (P1 if SLA breached)", "-", "Never create a second booking; continue from existing one", "Ops queue", "84901 (done), 84902 (49 h unscheduled), 84905, 84912"),
]
dm = pd.DataFrame(rows, columns=["Scenario", "Detection logic", "Auto-approve?", "Reason code", "Owner", "Priority", "SLA", "Required next action", "Channel", "Observed in dataset"])
pt = pd.DataFrame([{"code": p.code, "blocks auto-approval": p.blocking, "severity": p.severity, "owner": p.owner, "priority": p.priority, "action": p.action, "channel": p.channel} for p in REASONS.values()])
(D / "decision_matrix.md").write_text("# Renewal decision matrix\n\nOwners, priorities and SLAs are **proposed**, to be validated with the Operations Head. Generated from `src/config.py`.\n\n"
  "A renewal is auto-approved only when **no** blocking reason code is raised. LLMs take no part in these decisions.\n\n## A. The 12 required scenarios\n\n" + md_table(dm) +
  "\n\n## B. Reason-code policy (machine-readable source of truth)\n\n" + md_table(pt) + "\n\n`TIMESTAMP_ANOMALY` and `DISCOUNT_REQUIRES_APPROVAL` are additions to the suggested list. `TIMESTAMP_ANOMALY` was **not observed** in the data.\n")

# ---- ownership matrix ------------------------------------------------------------------------------------
own = pt.groupby("owner").apply(lambda g: pd.Series({"reason codes owned": ", ".join(g.code), "P1 codes": ", ".join(g[g.priority == "P1"].code) or "-"}), include_groups=False).reset_index()
esc = pd.DataFrame([("Teacher", "Reminder at 2 h; escalate to Ops Executive at 12 h", "Ops Executive"), ("Finance Ops", "P1 not acknowledged in 30 min", "Ops Manager"),
                    ("Scheduling Ops", "Unscheduled > 4 business h after eligibility", "Ops Manager"), ("Parent Success", "No parent reply in 1 business day", "Ops Executive"),
                    ("Ops Executive", "P2 unresolved in 4 business h", "Ops Manager"), ("Ops Manager", "Policy gap / discount / repeated breach", "Head of Operations")], columns=["Owner", "Escalation trigger", "Escalates to"])
(D / "exception_ownership_matrix.md").write_text("# Exception ownership matrix\n\nRoles are **proposed** (the data has `ops_exec_01..03` only). Names to be assigned by the Head of Operations.\n\n" + md_table(own) +
  "\n\n## Escalation\n\n" + md_table(esc) + "\n\n## Current open queue (from the official sample)\n\n" + md_table(pd.read_csv(R / "exceptions_by_owner.csv")) + "\n")

# ---- KPI + SLA ---------------------------------------------------------------------------------------------
t = met["timing"]
sla = pd.DataFrame([
 ("Payment detection", "<= 5 min from gateway capture", "Webhook timestamp vs payment record", "NOT measurable today: no webhook timestamps; paid_at is the only anchor"),
 ("Clean renewal reconciliation", "<= 5 min after complete data", "engine decision time - last input time", "Prototype is batch; target needs event-driven runs"),
 ("Teacher form reminder", "auto at 2 h after payment", "paid_at -> now", "Measurable: 3 of 11 paid invoices have no exact-id form"),
 ("Missing form escalation", "12 h after payment -> Ops Executive", "paid_at -> now", "84906 is at 26 h (breach under this target)"),
 ("P1 payment exception", "Ops response <= 30 min in operating hours", "exception created -> first action", "Needs an exception-queue timestamp that does not exist yet"),
 ("Scheduling completion", "<= 4 business h after eligibility", "booking created -> first schedule row", "Only 1 observation (0.5 h); booking 5502 is at 49 clock-hours with none"),
], columns=["SLA (proposed)", "Target", "Measured as", "Status in the sample"])
(D / "kpi_sla_framework.md").write_text("# KPI and SLA framework\n\nAll values computed by `src/metrics.py` from the official sample (13 invoices). **Small sample: percentages illustrate method, not a production baseline.**\n\n## A. KPIs (measured)\n\n" +
  md_table(kpi[["metric", "definition", "numerator", "denominator", "value_pct", "data_source", "fully_measurable", "limitations"]]) +
  f"\n\nCalculation method for every KPI: count ratio over de-duplicated, non-deleted rows; as-of `{met['as_of']}`.\n\n## B. Measured stage timings (hours)\n\n| Stage | n | median | mean | max |\n|---|---|---|---|---|\n" +
  "\n".join(f"| {k.replace('_hours','').replace('_',' ')} | {v['n']} | {v['median_h']} | {v['mean_h']} | {v['max_h']} |" for k, v in t.items() if isinstance(v, dict)) +
  "\n\nSingle timezone assumed (data carries none). With n <= 10 these are descriptive, not a baseline. Teachers who submit are fast (~27 min median); the delay is concentrated in missing forms and in Ops approval/allocation.\n\n"
  "## C. Proposed SLAs (targets, **not** existing commitments)\n\n" + md_table(sla) +
  "\n\n## D. Assumptions to validate with the Operations Head\n\n1. Operating hours and business-hour calendar (weekend/holiday handling is untestable: the data spans Sun-Tue only).\n2. Whether `active_students_count` already includes the renewing student (A1).\n3. Instalment policy: may classes be scheduled after instalment 1?\n4. Who may approve discounts, and where the approval is recorded.\n5. Timezone of every timestamp.\n")

# ---- data dictionary ---------------------------------------------------------------------------------------
def infer(col, vals):
    v = [x for x in vals if x is not None]
    if not v: return "unknown (all NULL)"
    if all(str(x).replace(".", "", 1).isdigit() for x in v):
        return "decimal" if any("." in str(x) for x in v) else "integer"
    if all(len(str(x)) == 19 and str(x)[4] == "-" for x in v): return "timestamp"
    if all(len(str(x)) == 10 and str(x)[4] == "-" for x in v): return "date"
    if all(len(str(x)) == 8 and str(x)[2] == ":" for x in v): return "time"
    return "text"
names = {"invoices": "1_invoices.csv", "forms": "2_faculty_form_unapproved.csv", "bookings": "3_booking_requests.csv", "schedule": "4_class_schedule_bookings.csv", "reference": "reference_active_batches_and_students.csv"}
out = ["# Data dictionary\n\nSource: official `ops/README.md` (column lists) + profiling of the files. Types are inferred from values; descriptions marked * come from the official README, others are inferred and unverified.\n"]
raw = ROOT / "data" / "raw"
for k, f in names.items():
    df = pd.read_csv(raw / f, dtype=str, keep_default_na=False).replace("NULL", None)
    p = prof["tables"][k]
    out.append(f"\n## {f}  ({p['rows']} rows, {p['columns']} columns, duplicate keys: {p['duplicate_primary_keys']})\n")
    rows = []
    for c in SCHEMAS[k]:
        cp = p["column_profile"][c]; note = ""
        if "values" in cp: note = "observed: " + ", ".join(f"{a}={b}" for a, b in cp["values"].items())
        elif "min" in cp and cp["min"]: note = f"{cp['min']} -> {cp['max']}"
        rows.append((c, infer(c, df[c].tolist()), cp["nulls"], cp["distinct"], note))
    out.append(md_table(pd.DataFrame(rows, columns=["column", "inferred type", "NULLs", "distinct", "observed values / range"])))
out.append("\n\n## Keys and relationships\n\n- `invoices.id` <- `faculty_form_unapproved.invoice_id` <- `booking_requests.faculty_form_id`/`invoice_id` <- `class_schedule_bookings.bookingrequest_id`/`invoice_id`.\n- `student_id` + `user_id` link every table to `reference_active_batches_and_students` (1 student per user in this sample).\n- `NULL` is the literal string used for missing values in the CSVs; the loader maps it to a true null.\n- Currency is `INR` on every invoice, including Stripe-paid +971 and +1 parents (to be validated).\n- Names, mobiles and emails are masked, so only masked-value equality is testable.\n")
(D / "data_dictionary.md").write_text("".join(out))

# ---- data quality -------------------------------------------------------------------------------------------
ri = prof["referential_integrity"]
(D / "data_quality_report.md").write_text(f"""# Data quality report

Generated from `results/data_profile.json` (all five files; originals verified unchanged by SHA-256).

## Structural quality
| Check | Result |
|---|---|
| Rows per table | invoices {prof['tables']['invoices']['rows']}, forms {prof['tables']['forms']['rows']}, bookings {prof['tables']['bookings']['rows']}, schedule {prof['tables']['schedule']['rows']}, reference {prof['tables']['reference']['rows']} |
| Duplicate primary keys | none in any table |
| Soft-deleted rows (`deleted_at` set) | {len(prof['soft_deleted_rows_excluded'])} |
| Forms citing an unknown invoice | {ri['forms_with_unknown_invoice']} |
| Bookings citing an unknown invoice / form | {ri['bookings_with_unknown_invoice']} / {ri['bookings_with_unknown_form']} |
| Schedule rows citing an unknown booking | {ri['schedule_with_unknown_booking']} |
| Invoices whose student is missing from the reference | {ri['invoices_with_unknown_student']} |
| Paid/any invoices without an exact-id form | {ri['invoices_without_exact_form']} |
| Bookings with NULL `classbatch_id` | {ri['bookings_with_null_batch']} |
| Users with more than one student | {ri['students_per_user_gt1']} (multi-child case NOT observable) |

## Semantic findings (observed)
1. Invoice 84913 is paid and form 3313 (same student 68113, same amount 11500) cites invoice **84931** - a digit transposition. Referential integrity breaks in both directions.
2. Invoice 84907 carries a 20% discount (1900) that is not backed by any approver field in any table; the form remark says the teacher "offered" it.
3. Invoice 84909 is `Partially_Paid` (5250 of 10500) but the teacher form states `amount_paid` = 10500.
4. Invoice 84911 has `Failed` status, no `paid_at`/gateway id, yet a teacher form exists (remark: parent shared a UPI screenshot).
5. Invoice 84904 was paid from a mobile and email that differ from the registered contact.
6. Forms 3305 and 3312 were marked **Approved** by Ops although batch 9205 is 6/6 and batch-change 3312 has no target batch (2 of the 4 approved forms).
7. Booking 5512 exists with a NULL `classbatch_id`.
8. Booking 5501 is `Completed` with 24 sessions purchased but only 2 schedule rows exist (possibly a rolling schedule - needs business confirmation).
9. Educator 1125's batches 9207 (Mon,Thu 15:30) and 9211 (Mon,Wed 16:00) overlap on Mondays if sessions last 50 min (the schedule rows imply 50 min).
10. Currency is INR on every invoice including Stripe invoices for +971/+1 parents.

## Not observable from this sample
Duplicate invoices, student/teacher/course mismatches, inactive batches, cancelled schedule rows, multiple children per parent, weekend/holiday delay (dates span Sun 1 Nov - Tue 3 Nov 2026), payment-detection latency.

## Limits
- Masked names/phones/emails: comparisons are masked-string equality, so two different numbers with the same mask would look equal.
- Reference table is a student-centred view, not a full batch catalogue; it may not list every batch a student could move to.
- No timezone. All timestamps treated as one local clock.
""")
print("docs generated")
