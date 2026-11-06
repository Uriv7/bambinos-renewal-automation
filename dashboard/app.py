"""Operations Head dashboard.  Run:  streamlit run dashboard/app.py
Reads results/*.csv produced by `python -m src.main`; generates them if missing. No figures are hard-coded."""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RES, RAW = ROOT / "results", ROOT / "data" / "raw"
NAVY, TEAL, AMBER, RED, GREY = "#1F3A5F", "#2A9D8F", "#E9A23B", "#C8553D", "#8A94A6"

st.set_page_config(page_title="Bambinos Renewal Operations", layout="wide")


@st.cache_data
def load():
    if not (RES / "case_decisions.csv").exists():
        from src.main import run
        run(RAW, RES)
    cases = pd.read_csv(RES / "case_decisions.csv", dtype=str)
    exc = pd.read_csv(RES / "flagged_exceptions.csv", dtype=str)
    ready = pd.read_csv(RES / "booking_ready.csv", dtype=str)
    owners = pd.read_csv(RES / "exceptions_by_owner.csv", dtype=str)
    metrics = json.loads((RES / "operational_metrics.json").read_text())
    inv = pd.read_csv(RAW / "1_invoices.csv", dtype=str)
    forms = pd.read_csv(RAW / "2_faculty_form_unapproved.csv", dtype=str)
    bks = pd.read_csv(RAW / "3_booking_requests.csv", dtype=str)
    sch = pd.read_csv(RAW / "4_class_schedule_bookings.csv", dtype=str)
    ref = pd.read_csv(RAW / "reference_active_batches_and_students.csv", dtype=str)
    return cases, exc, ready, owners, metrics, inv, forms, bks, sch, ref


def region(m):
    m = str(m)
    return "India" if m.startswith("+91") else "GCC (UAE)" if m.startswith("+971") else "US" if m.startswith("+1") else "Unknown"


cases, exc, ready, owners, metrics, inv, forms, bks, sch, ref = load()
inv_cases = cases[cases.record_type == "invoice"].copy()
inv_cases = inv_cases.merge(inv[["id", "paid_at", "created_at"]].rename(columns={"id": "invoice_id"}), on="invoice_id", how="left")
inv_cases["batch"] = inv_cases.student_id.map(ref.set_index("student_id")["current_classbatch_id"])
inv_cases["region"] = inv_cases.mobile_masked.map(region)
inv_cases["date"] = pd.to_datetime(inv_cases.paid_at.fillna(inv_cases.created_at)).dt.date
inv_cases = inv_cases.merge(exc[["record_id", "primary_reason_code", "priority", "assigned_owner", "recommended_action"]].rename(columns={"record_id": "case_id"}), on="case_id", how="left")

st.markdown(f"<h2 style='color:{NAVY};margin-bottom:0'>Renewal → Scheduling Operations</h2>", unsafe_allow_html=True)
st.caption(f"Snapshot as of {metrics['as_of']} (latest timestamp in the data). Source: official sample, {metrics['records']['invoices']} invoices. Owners/SLAs are proposed, not current policy.")

with st.sidebar:
    st.header("Filters")
    dmin, dmax = inv_cases.date.min(), inv_cases.date.max()
    dr = st.date_input("Payment date", (dmin, dmax), min_value=dmin, max_value=dmax)
    teachers = st.multiselect("Teacher (educator id)", sorted(inv_cases.educator_id.unique()))
    students = st.multiselect("Student id", sorted(inv_cases.student_id.unique()))
    batches = st.multiselect("Batch", sorted(inv_cases.batch.dropna().unique()))
    codes = st.multiselect("Exception type", sorted(exc.primary_reason_code.unique()))
    prios = st.multiselect("Priority", ["P1", "P2", "P3"])
    regions = st.multiselect("Region (derived from mobile prefix)", sorted(inv_cases.region.unique()))

f = inv_cases.copy()
if isinstance(dr, tuple) and len(dr) == 2:
    f = f[(f.date >= dr[0]) & (f.date <= dr[1])]
for col, sel in (("educator_id", teachers), ("student_id", students), ("batch", batches), ("primary_reason_code", codes), ("priority", prios), ("region", regions)):
    if sel:
        f = f[f[col].isin(sel)]

dec = f.decision.value_counts()
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Paid renewals", int((f.payment_status == "Paid").sum()))
c2.metric("Auto-approved", int(dec.get("AUTO_APPROVE", 0)))
c3.metric("Pending exceptions", int(dec.get("EXCEPTION", 0)))
c4.metric("Unscheduled bookings", int(((f.booking_id.notna()) & (f.scheduled_sessions.astype(int) == 0)).sum()))
c5.metric("Orphaned paid invoices", int(((f.payment_status == "Paid") & (f.match_method != "EXACT_INVOICE_ID")).sum()))
saved = int(dec.get("AUTO_APPROVE", 0)) * metrics["estimated_effort_saved_sample"]["assumptions"]["manual_minutes_per_clean_renewal_verification"] / 60
c6.metric("Est. hours saved*", f"{saved:.1f}")
t = metrics["timing"]["payment_to_form_created_hours"]
st.caption(f"*Illustrative: auto-approvals × 10 min assumed manual check (not measured). Average reconciliation time: **unavailable** (the engine does not yet run in production, so no reconciliation timestamps exist). "
           f"Measured manual step: payment → teacher form median {t['median_h']} h (n={t['n']}), form → Ops approval median {metrics['timing']['form_created_to_ops_approval_hours']['median_h']} h (n={metrics['timing']['form_created_to_ops_approval_hours']['n']}).")

a, b = st.columns(2)
paid = inv[inv.payment_status == "Paid"]
stages = [("Invoices", len(inv)), ("Paid", len(paid)), ("Teacher form linked", int(paid.id.isin(forms.invoice_id).sum())),
          ("Form approved by Ops", int((forms.approval_status == "Approved").sum())), ("Booking request", len(bks)), ("Scheduled (any session)", sch.bookingrequest_id.nunique())]
fig = go.Figure(go.Funnel(y=[s for s, _ in stages], x=[v for _, v in stages], marker={"color": [NAVY, "#34527D", TEAL, "#5BB5A8", AMBER, RED]}))
fig.update_layout(title="Renewal pipeline (all rows, unfiltered)", height=340, margin=dict(l=10, r=10, t=40, b=10))
a.plotly_chart(fig, width="stretch")
ed = f[f.decision == "EXCEPTION"].primary_reason_code.value_counts().reset_index()
ed.columns = ["reason", "cases"]
b.plotly_chart(px.bar(ed, x="cases", y="reason", orientation="h", title="Exceptions by primary reason", color_discrete_sequence=[RED]).update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10)), width="stretch")

a, b, c = st.columns(3)
daily = f.groupby("date").size().reset_index(name="renewals")
a.plotly_chart(px.bar(daily, x="date", y="renewals", title="Renewal invoices per day", color_discrete_sequence=[NAVY]).update_layout(height=300), width="stretch")
f["path"] = f.decision.map({"AUTO_APPROVE": "Auto-approve", "AWAITING_SCHEDULING": "Ready (existing booking)", "ALREADY_PROCESSED": "Already processed", "EXCEPTION": "Manual review"})
b.plotly_chart(px.pie(f, names="path", color="path", title="Auto vs manual review", hole=0.5, color_discrete_map={"Auto-approve": TEAL, "Ready (existing booking)": AMBER, "Already processed": GREY, "Manual review": RED}).update_layout(height=300), width="stretch", theme=None)
stg = f[f.teacher_followup_stage.notna()].teacher_followup_stage.value_counts().reset_index(); stg.columns = ["stage", "cases"]
c.plotly_chart(px.bar(stg, x="stage", y="cases", title="Teacher follow-up stage", color_discrete_sequence=[AMBER]).update_layout(height=300), width="stretch")
st.caption("Teacher follow-up SLA: reminder at 2 h, escalate at 12 h. SLA-breach views are limited to the teacher-form SLA and scheduling wait; payment-detection SLA is unavailable (no gateway webhook timestamps in the data).")


def show(title, df, cols, note=""):
    st.subheader(title)
    if note:
        st.caption(note)
    st.dataframe(df[cols] if len(df) else pd.DataFrame(columns=cols), hide_index=True, width="stretch")


ff = f.copy(); ff["payment_age_hours"] = pd.to_numeric(ff.payment_age_hours)
show("Invoices pending more than 12 hours", ff[(ff.payment_age_hours > 12) & ff.booking_id.isna()], ["invoice_id", "student_id", "payment_status", "payment_age_hours", "primary_reason_code", "assigned_owner"], "Paid > 12 h ago with no booking request.")
show("Teacher forms awaiting submission / correction", ff[ff.reason_codes.fillna("").str.contains("MISSING_FACULTY_FORM|INVALID_REFERENCE")], ["invoice_id", "educator_id", "educator_name", "teacher_followup_stage", "payment_age_hours", "recommended_action"])
unsched = ff[ff.booking_id.notna() & (ff.scheduled_sessions.astype(int) == 0)]
show("Booking requests awaiting scheduling", unsched, ["booking_id", "invoice_id", "booking_status", "decision", "primary_reason_code", "booking_age_hours"])
show("Payment mismatches / unverified", ff[ff.reason_codes.fillna("").str.contains("AMOUNT_MISMATCH|DISCOUNT|PARTIAL|PAYMENT_NOT_VERIFIED")], ["invoice_id", "payment_status", "net_amount", "form_amount_paid", "standard_fee", "reason_codes", "assigned_owner"])
show("Unscheduled students (no schedule rows)", ff[ff.scheduled_sessions.astype(int) == 0], ["student_id", "invoice_id", "decision", "reason_codes", "region"])
q = exc.merge(inv_cases[["case_id"]].rename(columns={"case_id": "record_id"}), on="record_id", how="inner") if len(f) else exc.iloc[0:0]
show("Exception ownership queue (with required action)", exc[exc.record_id.isin(f.case_id) | exc.record_type.eq("faculty_form")].sort_values(["priority", "assigned_owner"]),
     ["priority", "assigned_owner", "record_id", "primary_reason_code", "recommended_action", "sla_target"])
st.caption("Forms that cite unknown invoices (e.g. form 3313) appear in the queue even when invoice filters are set.")
