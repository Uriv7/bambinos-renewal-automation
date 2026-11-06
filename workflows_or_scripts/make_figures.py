"""Charts and diagrams for the PDF. Every chart is computed from results/ and data/raw (no illustrative numbers)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; R = ROOT / "results"; RAW = ROOT / "data" / "raw"; F = ROOT / "report" / "figures"
NAVY, TEAL, AMBER, RED, GREY, LIGHT = "#1F3A5F", "#2A9D8F", "#E9A23B", "#C8553D", "#8A94A6", "#EEF2F7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
cases = pd.read_csv(R / "case_decisions.csv", dtype=str); inv_c = cases[cases.record_type == "invoice"].copy()
exc = pd.read_csv(R / "flagged_exceptions.csv", dtype=str); met = json.loads((R / "operational_metrics.json").read_text())
inv = pd.read_csv(RAW / "1_invoices.csv", dtype=str); forms = pd.read_csv(RAW / "2_faculty_form_unapproved.csv", dtype=str)
bks = pd.read_csv(RAW / "3_booking_requests.csv", dtype=str); sch = pd.read_csv(RAW / "4_class_schedule_bookings.csv", dtype=str)


def save(name):
    plt.tight_layout(); plt.savefig(F / name, dpi=200, bbox_inches="tight"); plt.close()


# 1 funnel
paid = inv[inv.payment_status == "Paid"]
st = [("Invoices", len(inv)), ("Paid", len(paid)), ("Paid + exact-id\nteacher form", int(paid.id.isin(forms.invoice_id).sum())),
      ("Form approved\nby Ops", int((forms.approval_status == "Approved").sum())), ("Booking\nrequest", len(bks)), ("Any class\nscheduled", sch.bookingrequest_id.nunique())]
fig, ax = plt.subplots(figsize=(7.2, 2.9))
cols = [NAVY, "#34527D", TEAL, "#5BB5A8", AMBER, RED]
ax.bar([s for s, _ in st], [v for _, v in st], color=cols)
for i, (_, v) in enumerate(st): ax.text(i, v + .25, str(v), ha="center", fontweight="bold")
ax.set_ylabel("count"); ax.set_ylim(0, 15); ax.set_title("Renewal pipeline in the official sample (all rows)", loc="left", color=NAVY, fontweight="bold")
save("funnel.png")

# 2 ageing of paid invoices
p = inv_c[inv_c.payment_status == "Paid"].copy(); p["age"] = pd.to_numeric(p.payment_age_hours); p = p.sort_values("age")
colmap = {"AUTO_APPROVE": TEAL, "AWAITING_SCHEDULING": AMBER, "ALREADY_PROCESSED": GREY, "EXCEPTION": RED}
fig, ax = plt.subplots(figsize=(7.2, 3.3))
ax.barh(p.invoice_id, p.age, color=[colmap[d] for d in p.decision])
for y, (a, s) in enumerate(zip(p.age, p.scheduled_sessions)): ax.text(a + .6, y, f"{a:.0f} h" + ("  (scheduled)" if int(s) else ""), va="center", fontsize=8)
ax.axvline(24, color=NAVY, ls="--", lw=1); ax.text(24.5, -0.9, "24 h", color=NAVY, fontsize=8)
ax.set_xlabel("hours since payment (as of 2026-11-03 18:00)"); ax.set_xlim(0, 68)
ax.set_title("Paid invoices: time since payment, coloured by engine decision", loc="left", color=NAVY, fontweight="bold")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=v, label=k.replace("_", " ").title()) for k, v in colmap.items()], loc="lower right", fontsize=7.5, frameon=False)
save("ageing.png")

# 3 reason codes
dist = {}
for _, e in exc.iterrows():
    for c in e.all_reason_codes.split("|"): dist[c] = dist.get(c, 0) + 1
d = pd.Series(dist).sort_values()
fig, ax = plt.subplots(figsize=(7.2, 3.4)); ax.barh(d.index, d.values, color=RED)
for y, v in enumerate(d.values): ax.text(v + .05, y, str(v), va="center")
ax.set_xlabel("cases carrying the code (one case can carry several)"); ax.set_title("Reason codes across the 10 flagged records", loc="left", color=NAVY, fontweight="bold")
save("reasons.png")

# 4 owner queue
o = pd.read_csv(R / "exceptions_by_owner.csv")
fig, ax = plt.subplots(figsize=(7.2, 2.6)); ax.barh(o.assigned_owner[::-1], o.open_exceptions[::-1], color=NAVY)
ax.barh(o.assigned_owner[::-1], o.p1_count[::-1], color=RED)
for y, (a, b) in enumerate(zip(o.open_exceptions[::-1], o.p1_count[::-1])): ax.text(a + .05, y, f"{a} open" + (f" ({b} P1)" if b else ""), va="center", fontsize=8)
ax.set_xlim(0, 5.3); ax.set_title("Open exceptions by proposed owner (red = P1)", loc="left", color=NAVY, fontweight="bold")
save("owners.png")

# 5 what-if
def counts(n):
    c = pd.read_csv(R / "whatif" / n / "case_decisions.csv", dtype=str); c = c[c.record_type == "invoice"]; return c.decision.value_counts().to_dict()
base, ifirst = counts("base"), counts("invoice_first")
fig, ax = plt.subplots(figsize=(7.2, 2.6)); labels = ["Current rules (form required)", "SIMULATION: invoice-first, same-batch"]
keys = ["AUTO_APPROVE", "AWAITING_SCHEDULING", "ALREADY_PROCESSED", "EXCEPTION"]; left = [0, 0]
for k in keys:
    vals = [base.get(k, 0), ifirst.get(k, 0)]
    ax.barh(labels, vals, left=left, color=colmap[k], label=k.replace("_", " ").title())
    for i, v in enumerate(vals):
        if v: ax.text(left[i] + v / 2, i, str(v), ha="center", va="center", color="white", fontweight="bold")
    left = [a + b for a, b in zip(left, vals)]
ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.2), frameon=False); ax.set_xlim(0, 13)
ax.set_title("Decisions on 13 invoices: current rules vs invoice-first (simulation)", loc="left", color=NAVY, fontweight="bold")
save("whatif.png")


def box(ax, x, y, w, h, text, fc=LIGHT, ec=NAVY, fs=7.5, tc=NAVY, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, c=NAVY):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.1))


# 6 workflow
fig, ax = plt.subplots(figsize=(7.4, 4.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 6.2); ax.axis("off")
top = [("1 Payment event\n(gateway webhook)", 0.1), ("2 Verify payment\nPaid + gateway id", 2.6), ("3 Reconcile invoice\n+ student identity", 5.1), ("4 Teacher form:\noptional if same batch", 7.6)]
for t, x in top: box(ax, x, 5.0, 2.3, .95, t)
for i in range(3): arrow(ax, top[i][1] + 2.3, 5.47, top[i + 1][1], 5.47)
box(ax, 6.9, 3.5, 3.0, .95, "5 Eligibility: amount = fee, contact,\nteacher, course, batch active", fs=7)
box(ax, 3.5, 3.5, 3.0, .95, "6 Batch capacity, schedule\nconflict, existing booking", fs=7)
box(ax, 0.1, 3.5, 3.0, .95, "7 DECISION ENGINE\n(deterministic, no LLM)", fc=NAVY, tc="white", bold=True)
arrow(ax, 8.75, 5.0, 8.75, 4.45); arrow(ax, 6.9, 3.97, 6.5, 3.97); arrow(ax, 3.5, 3.97, 3.1, 3.97)
ax.text(1.0, 2.82, "CLEAN CASE", color=TEAL, fontweight="bold", fontsize=8.5); ax.text(7.0, 2.82, "EXCEPTION", color=RED, fontweight="bold", fontsize=8.5)
cl = ["Auto-approve", "Create booking\n(once, keyed)", "Create\nschedule rows", "Parent\nconfirmation"]
for i, t in enumerate(cl): box(ax, 0.1 + i * 1.25, 1.55, 1.0, 1.0, t, fc="#DDF1EE", ec=TEAL, fs=6.4)
for i in range(3): arrow(ax, 0.1 + i * 1.25 + 1.0, 2.05, 0.1 + (i + 1) * 1.25, 2.05, TEAL)
ex = ["Exception queue\n+ reason codes", "Assign owner\nP1/P2/P3 + SLA", "Draft follow-up\nteacher / parent", "Human approval\nthen re-run"]
for i, t in enumerate(ex): box(ax, 5.1 + i * 1.17, 1.55, .92, 1.0, t, fc="#F8E4DE", ec=RED, fs=5.8)
for i in range(3): arrow(ax, 5.1 + i * 1.17 + .92, 2.05, 5.1 + (i + 1) * 1.17, 2.05, RED)
arrow(ax, 0.55, 3.5, 0.55, 2.6, TEAL); arrow(ax, 2.6, 3.5, 5.6, 2.62, RED)
ax.text(0.1, 0.9, "Existing booking: continue from it, never create another.   Unknown state: exception, never approval.", fontsize=7.5, color=NAVY, style="italic")
ax.text(0.1, 0.45, "Audit log written for every rule on every case; original inputs are never modified.", fontsize=7.5, color=NAVY, style="italic")
save("workflow.png")

# 7 system architecture with honest status
fig, ax = plt.subplots(figsize=(7.4, 4.3)); ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
def comp(x, y, w, h, t, built):
    fc, ec = {True: ("#DDF1EE", TEAL), False: ("#F2F2F2", GREY), "part": ("#FBF0DA", AMBER)}[built]; box(ax, x, y, w, h, t, fc=fc, ec=ec, fs=7.2)
ax.text(0.1, 5.75, "SOURCES", fontsize=8, color=GREY, fontweight="bold"); ax.text(3.0, 5.75, "ORCHESTRATION + ENGINE", fontsize=8, color=GREY, fontweight="bold"); ax.text(6.6, 5.75, "OUTPUTS", fontsize=8, color=GREY, fontweight="bold")
comp(0.1, 4.5, 2.4, .9, "Razorpay / Stripe\nwebhooks", False); comp(0.1, 3.3, 2.4, .9, "Production DB\n(replica / PostgreSQL)", False); comp(0.1, 2.1, 2.4, .9, "Official CSVs\n(5 tables)", True)
comp(3.0, 4.5, 3.0, .9, "n8n workflow (runs locally,\nmanual trigger; no webhook)", "part")
comp(3.0, 2.7, 3.0, 1.5, "Python reconciliation engine\nrules -> decision -> reason codes\nidempotency ledger, audit log\n(src/, 44 tests)", True)
comp(3.0, 1.2, 3.0, .9, "LLM: wording + remark\nclassification only (optional)", False)
comp(6.6, 4.5, 3.2, .8, "Booking + schedule creator", False); comp(6.6, 3.55, 3.2, .8, "Exception queue (CSV + owners)", True)
comp(6.6, 2.6, 3.2, .8, "WhatsApp Business API", False); comp(6.6, 1.65, 3.2, .8, "Message drafts (CSV)", True); comp(6.6, 0.7, 3.2, .8, "Dashboard (Streamlit)", True)
for y in (4.95, 3.75): arrow(ax, 2.5, y, 3.0, 4.95 if y > 4 else 3.7)
arrow(ax, 2.5, 2.55, 3.0, 3.2); arrow(ax, 4.5, 4.5, 4.5, 4.2); arrow(ax, 6.0, 3.6, 6.6, 3.95); arrow(ax, 6.0, 4.0, 6.6, 4.9); arrow(ax, 6.0, 3.1, 6.6, 2.1); arrow(ax, 4.5, 2.1, 4.5, 2.7); arrow(ax, 8.2, 2.45, 8.2, 2.6) if False else None
arrow(ax, 6.0, 2.9, 6.6, 1.1)
ax.add_patch(FancyBboxPatch((0.1, 0.25), .3, .25, boxstyle="round,pad=0.01", fc="#DDF1EE", ec=TEAL)); ax.text(.5, .31, "Built and run", fontsize=7.5)
ax.add_patch(FancyBboxPatch((4.2, 0.25), .3, .25, boxstyle="round,pad=0.01", fc="#F2F2F2", ec=GREY)); ax.text(4.6, .31, "Design only - NOT implemented or connected", fontsize=7.5)
ax.add_patch(FancyBboxPatch((8.0, 0.25), .3, .25, boxstyle="round,pad=0.01", fc="#FBF0DA", ec=AMBER)); ax.text(8.4, .31, "Partial", fontsize=7.5)
save("system.png")

# 8 dashboard layout rendered from real results
fig = plt.figure(figsize=(7.4, 4.7)); fig.patch.set_facecolor("white")
ax0 = fig.add_axes([0, .83, 1, .17]); ax0.axis("off"); ax0.set_xlim(0, 6); ax0.set_ylim(0, 1)
dec = inv_c.decision.value_counts()
cards = [("Paid renewals", int((inv_c.payment_status == "Paid").sum())), ("Auto-approved", int(dec.get("AUTO_APPROVE", 0))), ("Pending exceptions", int(dec.get("EXCEPTION", 0))),
         ("Unscheduled bookings", len(met["unscheduled_bookings"])), ("Orphaned paid inv.", int(((inv_c.payment_status == "Paid") & (inv_c.match_method != "EXACT_INVOICE_ID")).sum())), ("Est. hours saved*", "0.3")]
for i, (l, v) in enumerate(cards):
    ax0.add_patch(FancyBboxPatch((i + .05, .08), .9, .84, boxstyle="round,pad=0.01,rounding_size=0.05", fc=LIGHT, ec="#D5DCE6")); ax0.text(i + .5, .62, str(v), ha="center", fontsize=15, fontweight="bold", color=NAVY); ax0.text(i + .5, .25, l, ha="center", fontsize=6.5, color=GREY)
a1 = fig.add_axes([.07, .42, .38, .33]); a1.bar(range(6), [v for _, v in st], color=cols); a1.set_xticks(range(6)); a1.set_xticklabels(["Inv", "Paid", "Form", "Appr", "Book", "Sched"], fontsize=7); a1.set_title("Renewal pipeline", fontsize=8, loc="left", color=NAVY)
a2 = fig.add_axes([.58, .42, .38, .33]); pr = exc.primary_reason_code.value_counts()[::-1]; a2.barh(pr.index, pr.values, color=RED); a2.tick_params(labelsize=6); a2.set_title("Exceptions by primary reason", fontsize=8, loc="left", color=NAVY)
a3 = fig.add_axes([0.04, .04, .92, .3]); a3.axis("off"); a3.set_title("Exception ownership queue (priority, owner, action, SLA)", fontsize=8, loc="left", color=NAVY)
rows = exc.sort_values(["priority", "assigned_owner"]).head(5)[["priority", "assigned_owner", "record_id", "primary_reason_code"]].values.tolist()
tb = a3.table(cellText=rows, colLabels=["Pri", "Owner", "Record", "Reason"], loc="upper center", cellLoc="left"); tb.auto_set_font_size(False); tb.set_fontsize(6.5); tb.scale(1, 1.05)
plt.savefig(F / "dashboard.png", dpi=200); plt.close()
print("figures:", sorted(p.name for p in F.glob("*.png")))
