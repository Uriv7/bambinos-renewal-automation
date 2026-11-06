"""Builds report/Bambinos_AI_Program_Manager_Operations_Case_Study.pdf from results/ + figures. Run tests live for the stated result."""
import json, re, subprocess, sys
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]; R = ROOT / "results"; FIG = ROOT / "report" / "figures"
OUT = ROOT / "report" / "Bambinos_AI_Program_Manager_Operations_Case_Study.pdf"
CANDIDATE = "Virender Gupta"
NAVY, TEAL, AMBER, RED, GREY, LIGHT = (colors.HexColor(x) for x in ("#1F3A5F", "#2A9D8F", "#E9A23B", "#C8553D", "#6B7585", "#EEF2F7"))

t = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
m = re.search(r"(\d+) passed", t.stdout); TESTS = f"{m.group(1)} passed" if m and t.returncode == 0 else "FAILURES - see pytest"
if t.returncode != 0: print(t.stdout[-1500:]); sys.exit("tests failing - refusing to build report")

cases = pd.read_csv(R / "case_decisions.csv", dtype=str); exc = pd.read_csv(R / "flagged_exceptions.csv", dtype=str)
met = json.loads((R / "operational_metrics.json").read_text()); kpi = pd.read_csv(R / "kpi_table.csv")
own = pd.read_csv(R / "exceptions_by_owner.csv")

ss = dict(
    body=ParagraphStyle("body", fontName="Helvetica", fontSize=9.2, leading=13, textColor=colors.HexColor("#222222"), spaceAfter=5, alignment=TA_LEFT),
    h1=ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=NAVY, spaceBefore=2, spaceAfter=8),
    h2=ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    cell=ParagraphStyle("cell", fontName="Helvetica", fontSize=7.4, leading=9.2), cellb=ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=7.4, leading=9.2, textColor=colors.white),
    cap=ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=7.6, leading=10, textColor=GREY, spaceAfter=8),
    bul=ParagraphStyle("bul", fontName="Helvetica", fontSize=9.2, leading=12.6, leftIndent=12, bulletIndent=2, spaceAfter=2.5),
    call=ParagraphStyle("call", fontName="Helvetica", fontSize=9, leading=12.5, textColor=NAVY, backColor=LIGHT, borderPadding=(6, 7, 6, 7), spaceBefore=4, spaceAfter=9),
    toc1=ParagraphStyle("toc1", fontName="Helvetica", fontSize=10, leading=17, leftIndent=6),
)
W = A4[0] - 2 * 18 * mm


class Doc(BaseDocTemplate):
    def __init__(self, fn):
        super().__init__(fn, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=17 * mm,
                         title="Bambinos.live AI Program Manager (Operations) - Case Study", author=CANDIDATE)
        fr = Frame(self.leftMargin, self.bottomMargin, W, A4[1] - self.topMargin - self.bottomMargin, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="cover", frames=[Frame(0, 0, A4[0], A4[1], leftPadding=18 * mm, rightPadding=18 * mm, topPadding=0, bottomPadding=0)], onPage=self.cover),
                               PageTemplate(id="body", frames=[fr], onPage=self.chrome)])

    def cover(self, c, d):
        c.setFillColor(NAVY); c.rect(0, A4[1] * .50, A4[0], A4[1] * .50, fill=1, stroke=0)
        c.setFillColor(TEAL); c.rect(0, A4[1] * .50 - 5, A4[0], 5, fill=1, stroke=0)

    def chrome(self, c, d):
        c.setFont("Helvetica", 7.5); c.setFillColor(GREY)
        c.drawString(18 * mm, A4[1] - 12 * mm, "Bambinos.live  |  AI Program Manager (Operations)  |  Renewal -> Scheduling case study")
        c.setStrokeColor(colors.HexColor("#D5DCE6")); c.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}"); c.drawString(18 * mm, 10 * mm, "Evidence: official sample data, as of 2026-11-03 18:00. Proposed targets are not company commitments.")

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "h1":
            txt = f.getPlainText(); key = f"h{self.page}_{abs(hash(txt))}"
            self.canv.bookmarkPage(key); self.notify("TOCEntry", (0, txt, self.page, key))


S = []
P = lambda x, st="body": S.append(Paragraph(x, ss[st]))
def H1(x, brk=True):
    if brk: S.append(PageBreak())
    else: S.append(Spacer(1, 10))
    S.append(Paragraph(x, ss["h1"]))
def H2(x): S.append(Paragraph(x, ss["h2"]))
def B(items):
    for i in items: S.append(Paragraph(i, ss["bul"], bulletText="-"))
def callout(x): S.append(Paragraph(x, ss["call"]))
def img(name, w=W, cap=None):
    from PIL import Image as PI
    iw, ih = PI.open(FIG / name).size
    blk = [Image(str(FIG / name), width=w, height=w * ih / iw)]
    if cap: blk.append(Paragraph(cap, ss["cap"]))
    S.append(KeepTogether(blk))
def tbl(rows, widths, fs=None, head=True, zebra=True):
    data = [[Paragraph(str(c), ss["cellb"] if (head and i == 0) else ss["cell"]) for c in r] for i, r in enumerate(rows)]
    tw = sum(widths); widths = [w / tw * W for w in widths]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    sty = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CBD3DF")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if head: sty.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra: sty += [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(sty)); S.append(t); S.append(Spacer(1, 6))

# ------------------------------------------------------------------ cover
S.append(NextPageTemplate("body"))
S.append(Spacer(1, 70 * mm))
S.append(Paragraph("Re-engineering the Student Renewal<br/>-> Class Scheduling Pipeline", ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=27, leading=33, textColor=colors.white)))
S.append(Spacer(1, 6 * mm))
S.append(Paragraph("A zero-touch, AI-assisted operating model with a working reconciliation prototype", ParagraphStyle("cs", fontName="Helvetica", fontSize=12.5, leading=17, textColor=colors.HexColor("#CFE8E4"))))
S.append(Spacer(1, 52 * mm))
for l, v in (("Role", "AI Program Manager (Operations) - Stage 2 take-home"), ("Company", "Bambinos.live"), ("Prepared for", "Head of Operations"), ("Candidate", CANDIDATE), ("Evidence base", "Official sample: 13 invoices, 12 faculty forms, 4 booking requests, 2 schedule rows, 13 reference students (snapshot 2026-11-03 18:00)")):
    S.append(Paragraph(f"<font color='#6B7585'>{l}</font>&nbsp;&nbsp;&nbsp;<b>{v}</b>", ParagraphStyle("cm", fontName="Helvetica", fontSize=9.5, leading=15, textColor=NAVY)))
S.append(PageBreak())
S.append(Paragraph("Contents", ParagraphStyle("ctitle", parent=ss["h1"])))
toc = TableOfContents(); toc.levelStyles = [ss["toc1"]]; toc.dotsMinLevel = 0; S.append(toc)

d = cases[cases.record_type == "invoice"]; dec = d.decision.value_counts()
# ------------------------------------------------------------------ 1 exec summary
H1("1. Executive summary")
callout("<b>Bottom line.</b> In the sample, 11 of 13 invoices are paid but only 1 has a scheduled class, and 5 of the 11 have waited more than 24 hours. The delay is not teacher speed (median 27 minutes when a form is submitted); it is missing forms, manual approval of clean renewals, and approvals that later cannot be booked. A deterministic engine can safely clear the clean cases and give every other case a named owner.")
B([f"<b>What the data shows.</b> 3 paid invoices have no exact-id teacher form (84906, 84910, 84913); form 3313 cites a non-existent invoice (84931, a digit transposition of 84913); 2 of the 4 forms Ops approved (3305, 3312) could not be booked; clean invoice 84903 has waited about 33 hours for approval; booking 5502 is validated yet unscheduled for 49 hours.",
   f"<b>What I built.</b> A Python reconciliation engine (16 checks plus a decision step, audit trail, idempotency ledger), exception ownership, follow-up drafts, a Streamlit dashboard, SOP, 30-60-90 plan and risk register. Automated tests: <b>{TESTS}</b> (run when this PDF was built).",
   f"<b>What it decides on the sample.</b> {dec.get('AUTO_APPROVE',0)} auto-approved (84903, 84908), {dec.get('AWAITING_SCHEDULING',0)} ready to schedule on an existing booking (84902), {dec.get('ALREADY_PROCESSED',0)} already processed (84901), <b>{dec.get('EXCEPTION',0)} exceptions plus 1 orphan form</b>. Re-running changes nothing: 0 new executions, 3 skipped.",
   "<b>Process insight.</b> For same-batch renewals the teacher form adds nothing the invoice and reference table lack. A <i>simulation</i> that makes it optional lifts clean auto-approvals from 2 to 5 of 13; the form stays mandatory for batch changes.",
   "<b>Value (assumption-based).</b> About 26 to 64 hours of manual checking avoided per 1,000 renewals a month, if each avoided check takes 10 minutes. Volume and minutes are assumptions to validate; the stronger case is latency.",
   "<b>Decisions needed from you:</b> (1) does the batch seat count already include the renewing student? (2) may classes start after instalment 1? (3) who approves discounts? (4) may the form become optional for same-batch renewals? (5) names for the six proposed owner roles."])
callout("<b>Honest scope.</b> Built and run: engine, tests, drafts, dashboard layout. <b>Not built or connected:</b> n8n (the workflow imports and runs locally in n8n 2.35.7 with a manual trigger, but its schedule trigger never fired and its notification nodes are placeholders), Razorpay/Stripe webhooks, WhatsApp Business API, production database, live LLM calls. The sample is small, so percentages illustrate method and are not a production baseline.")

# ------------------------------------------------------------------ 2 context
H1("2. Business context and the existing process")
P("Bambinos.live runs live small-group classes for children aged 4-16 across India, GCC and US/UK. Every renewal passes four manual hand-offs. The table pairs each stage with what the sample actually shows.")
tbl([["Stage", "Today (manual)", "Observed failure in the sample"],
     ["1 Invoice", "Parent pays via Razorpay/Stripe link", "1 Failed (84911), 1 Partially_Paid (84909), 1 discounted without approver (84907), 1 payer differs from registered contact (84904)"],
     ["2 Faculty form", "Teacher keys invoice link, amount, preferred slot", "3 paid invoices without form; typo'd invoice id (3313 -> 84931); duplicate (3308/3309); form for an unpaid invoice (3311); amount overstated (3310)"],
     ["3 Booking request", "Ops verifies payment, approves, booking created", "2 of 4 approved forms unbookable (3305 batch 6/6, 3312 batch change with NULL batch); 8 of 12 forms still pending; clean 3303 pending ~33 h"],
     ["4 Class schedule", "Parent/Ops picks batch; sessions scheduled", "3 of 4 bookings have no schedule rows; 5502 waiting 49 h; 5501 has 2 schedule rows for 24 purchased sessions"]], [1.1, 2.2, 5])
P("<b>Why this matters.</b> A paid renewal that does not become a scheduled class is a customer experience failure and a revenue-recognition risk. Each stage also relies on a person remembering to act, with no timer and no owner.")

# ------------------------------------------------------------------ 3 data + method
H1("3. Data understanding and methodology")
P("All five official CSVs were downloaded from the assessment repository into <font face='Courier'>data/raw/</font> and are never modified (SHA-256 verified before and after every run; tested). Missing values are the literal string NULL and are mapped to true nulls. Soft-deleted rows would be logged, never silently dropped.")
tbl([["File", "Rows", "Key / link", "Notes"],
     ["1_invoices", "13", "id; student_id, user_id", "11 Paid, 1 Partially_Paid, 1 Failed; all currency INR (also Stripe +971 / +1)"],
     ["2_faculty_form_unapproved", "12", "invoice_id -> invoices.id", "4 Approved, 8 Pending; 1 unknown invoice (84931); 1 duplicate"],
     ["3_booking_requests", "4", "faculty_form_id, invoice_id", "Completed, Pending_Batch_Allocation, Failed_Batch_Full, Awaiting_Parent_Batch_Selection"],
     ["4_class_schedule_bookings", "2", "bookingrequest_id", "Both rows belong to booking 5501 (50-min sessions)"],
     ["reference_active_batches", "13", "student_id; batch id", "Fee, batch days/time, seats (active vs max 6)"]], [2.2, .6, 2, 4])
H2("Method")
B(["<b>Exact identifiers only</b> link records (invoice id, student id, user id, booking id, batch id). Names are masked and never used; phone similarity is never identity.",
   "<b>Deterministic rules</b> decide payment, duplicates, matching, capacity and eligibility. LLMs are limited to wording and remark classification and cannot change a decision.",
   "<b>Every statistic is computed</b> from the files by <font face='Courier'>src/metrics.py</font>; the dashboard and this report read the same outputs. Measured baseline, proposed target, simulation and assumption are labelled separately.",
   "<b>Ageing</b> uses the latest timestamp in the data (2026-11-03 18:00) as 'now' for reproducibility. A single timezone is assumed; the files carry none.",
   "<b>Limits.</b> 13 invoices; masked identifiers (equal masks could hide different numbers); reference table is a student-centred view, not a full batch catalogue; dates span Sunday-Tuesday only, so weekend and holiday delay cannot be measured."])

# ------------------------------------------------------------------ 4 findings
H1("4. Root-cause analysis and actual findings")
P("Twelve findings were observed in the data. Root causes are <b>hypotheses</b> to validate with Ops and teachers: the data shows symptoms, not intent (<font face='Courier'>results/root_cause_analysis.csv</font>).")
tbl([["#", "Finding (evidence)", "Likely root cause (hypothesis)"],
     ["F1", "Clean 84903 waits ~33 h for approval", "Approval is manual for every row, including clean ones"],
     ["F2", "Paid, no form: 84906 (26 h), 84910 (6.7 h)", "Teacher step has no timer, reminder or owner"],
     ["F3", "Form 3313 cites 84931; paid 84913 has no form", "Invoice id keyed by hand (digits transposed)"],
     ["F4", "Form 3311 on Failed invoice 84911 (UPI screenshot)", "Teacher submits on parent's claim; payment not checked first"],
     ["F5", "84909: form says 10,500 paid; gateway shows 5,250", "Instalments flow through the full-payment lane"],
     ["F6", "84907: 20% discount (1,900) offered by teacher, no approver", "No discount-code or approval field in any table"],
     ["F7", "84904: payer mobile/email differ from registered", "No payer verification step"],
     ["F8", "3308/3309 identical forms about 5 min apart", "No idempotency on form submit (browser froze)"],
     ["F9", "Approved 3305 (batch 6/6) and 3312 (no target batch) cannot be booked", "Approval happens before capacity/target checks"],
     ["F10", "5502 validated but unscheduled for 49 h", "No SLA or owner on approval -> scheduling hand-off"],
     ["F11", "84905 'batch full' although the student already belongs to batch 9205", "Capacity check may treat a renewal as a new seat (assumption A1, to validate)"],
     ["F12", "5501: 24 sessions purchased, 2 schedule rows", "Rolling scheduling or an incomplete hand-off - unknown"]], [.4, 3.6, 3.4])
P("<b>Observed vs theoretical.</b> Not observed in this sample (covered by synthetic tests, theoretical for the company): duplicate invoices, student/teacher/course mismatches, inactive batches, session-level conflicts, multiple children per parent, weekend delay. No timestamp anomalies were found; one initially suspected case was a misreading and the engine correctly raised nothing.")

# ------------------------------------------------------------------ 5 leakage
H1("5. Operational leakage audit")
img("funnel.png", cap="Figure 1 - Only 1 of 11 paid invoices has a scheduled class. Source: files 1-4, all rows.")
img("ageing.png", cap="Figure 2 - Five paid invoices (84902-84906) are over 24 h old with no scheduled class. 84903 and 84908 are clean and wait only for approval.")
P("This is a snapshot, not proof of permanent loss: some renewals may be mid-process. It does show where time accumulates: before approval (84903), between approval and scheduling (84902) and in cases that no one owns (84906).")

# ------------------------------------------------------------------ 6 KPI/SLA
H1("6. KPI and SLA framework")
P("Definitions, numerators, denominators, sources and limitations for every KPI are in <font face='Courier'>docs/kpi_sla_framework.md</font> and <font face='Courier'>results/kpi_table.csv</font>. Selected measured values:")
pick = ["Paid invoices", "Orphaned paid invoices", "Faculty form submission rate (paid invoices)", "Faculty form mismatch rate", "Duplicate faculty form rate", "Booking requests with no schedule rows", "Payment amount mismatch rate", "Batch capacity issues", "Auto-approval eligibility rate", "Safe-to-schedule rate", "Exception rate"]
k = kpi.set_index("metric")
tbl([["KPI", "Num / Den", "Value", "Measurable"]] + [[x, f"{int(k.loc[x,'numerator'])} / {int(k.loc[x,'denominator'])}", f"{k.loc[x,'value_pct']}%", "Yes (n small)"] for x in pick], [4, 1.2, .9, 1.2])
tm = met["timing"]
H2("Measured stage timings (hours)")
tbl([["Stage", "n", "Median", "Max", "Reading"],
     ["Payment -> teacher form created", tm["payment_to_form_created_hours"]["n"], tm["payment_to_form_created_hours"]["median_h"], tm["payment_to_form_created_hours"]["max_h"], "Teachers who submit are quick"],
     ["Form created -> Ops approval", tm["form_created_to_ops_approval_hours"]["n"], tm["form_created_to_ops_approval_hours"]["median_h"], tm["form_created_to_ops_approval_hours"]["max_h"], "Approval is the slow human step (approved forms only)"],
     ["Approval -> booking created", tm["approval_to_booking_created_hours"]["n"], tm["approval_to_booking_created_hours"]["median_h"], tm["approval_to_booking_created_hours"]["max_h"], "Booking is created at approval"],
     ["Booking -> first schedule row", tm["booking_created_to_first_schedule_hours"]["n"], tm["booking_created_to_first_schedule_hours"]["median_h"], tm["booking_created_to_first_schedule_hours"]["max_h"], "One observation; 3 bookings have none"]], [3, .4, .7, .7, 3.4])
H2("Proposed SLAs (targets, not company commitments)")
tbl([["SLA", "Target", "Measurable today?"],
     ["Payment detection", "5 min from capture", "No - no webhook timestamps"],
     ["Clean renewal reconciliation", "5 min after complete data", "Not yet - prototype runs in batch"],
     ["Teacher form reminder / escalation", "2 h / 12 h after payment", "Yes - 84906 is at 26 h (breach)"],
     ["P1 payment exception", "Ops response within 30 min (operating hours)", "No - no exception timestamps yet"],
     ["Scheduling completion", "4 business hours after eligibility", "Partly - 5502 at 49 clock hours"]], [2.6, 3, 3])
P("Validate with the Operations Head: operating hours and holiday calendar, timezone, and who owns each target.")

# ------------------------------------------------------------------ 7 architecture
H1("7. Proposed zero-touch architecture")
P("<b>Principle:</b> deterministic code decides money and eligibility; AI drafts and classifies; humans own exceptions. <b>Re-engineering moves:</b> gateway as the source of truth; invoice-first renewal (teacher form optional for same-batch); capacity check only for net-new seats; invoice picker instead of free text; discount codes with approver; timers instead of memory.")
img("workflow.png", cap="Figure 3 - Target workflow. Clean cases flow to a once-only booking; everything else is owned and re-evaluated after the data is fixed.")
img("system.png", cap="Figure 4 - Components. Green = built and run; amber = partial (the n8n flow runs locally with a manual trigger only, no webhook or real notifications); grey = design only, not implemented or connected.")
H2("Questioning the steps before automating them")
tbl([["Step", "Why it exists (hypothesis)", "Proposal"],
     ["Teacher renewal form", "Captures intent and slot; doubles as a payment claim", "Optional for same-batch; mandatory for batch change"],
     ["Manual payment verification", "Teachers submit before payment is confirmed (84911)", "Replace with gateway status check"],
     ["Ops approval", "Catches typos, amounts, duplicates", "Auto for clean cases; human for the exception classes"],
     ["Parent / Ops batch pick", "Needed when changing batch", "Skip for same-batch renewals"]], [2, 3.4, 3])
img("whatif.png", cap="Figure 5 - SIMULATION on the same 13 invoices (not a production result): without the form requirement, auto-approvals rise from 2 to 5 (84906, 84910, 84913 join).")

# ------------------------------------------------------------------ 8 decision matrix
H1("8. Exception taxonomy and renewal decision matrix")
P("A renewal is auto-approved only if <b>no</b> blocking reason code is raised. Owners, priorities and SLAs are proposed. Full matrix with detection logic, channel and next action: <font face='Courier'>docs/decision_matrix.md</font>.")
tbl([["Scenario", "Auto?", "Reason code", "Owner / Pri", "Observed"],
     ["Same batch, same teacher", "Yes", "-", "monitor / P3", "84903, 84908"],
     ["Same batch, different teacher", "No", "TEACHER_ID_MISMATCH", "Ops Executive / P2", "Not observed"],
     ["Different-batch renewal", "No", "MISSING_REQUIRED_FIELD + MANUAL_REVIEW", "Scheduling Ops / P2", "84912"],
     ["Parent identity mismatch", "No", "PARENT_CONTACT_MISMATCH", "Parent Success / P2", "84904"],
     ["Student identity mismatch", "No", "STUDENT_ID_MISMATCH", "Ops Executive / P1", "Not observed"],
     ["Payment mismatch", "No", "AMOUNT_MISMATCH / DISCOUNT_REQUIRES_APPROVAL", "Finance Ops P1 / Ops Mgr P2", "84909, 84907"],
     ["Partial payment", "No", "PARTIAL_PAYMENT", "Finance Ops / P2", "84909"],
     ["Duplicate invoice", "No", "DUPLICATE_INVOICE", "Finance Ops / P1", "Not observed"],
     ["Missing teacher form", "No (today)", "MISSING_FACULTY_FORM (+ORPHANED >= 12 h)", "Teacher -> Ops Exec / P2", "84906, 84910, 84913"],
     ["Full batch", "No", "BATCH_FULL", "Scheduling Ops / P1", "84905"],
     ["Scheduling conflict", "No", "SCHEDULING_CONFLICT", "Scheduling Ops / P2", "Info only: educator 1125 batches overlap Mondays"],
     ["Existing booking", "Never new", "BOOKING_ALREADY_EXISTS (info)", "Ops Executive / P3", "84901, 84902, 84905, 84912"]], [2.1, .8, 2.7, 1.9, 2.1])

# ------------------------------------------------------------------ 9 exceptions
H1("9. Exception handling")
P("Each exception row carries record id, invoice id, student id, all reason codes, explanation, severity, owner, priority, SLA, recommended action, channel and a created timestamp. Closing an exception never edits the engine's decision: the data is fixed at source and the engine re-decides, so the audit trail stays honest.")
img("reasons.png", cap="Figure 6 - Reason codes across the 10 flagged records (9 invoices + orphan form 3313).")
img("owners.png", cap="Figure 7 - Proposed ownership of the open queue; red = P1 (84909, 84911, 84905).")
P("<b>Example (84909).</b> Payment status Partially_Paid (5,250 of 10,500) while the teacher entered 10,500. Codes: AMOUNT_MISMATCH + PARTIAL_PAYMENT. Owner Finance Ops, P1. Drafts: teacher amount check, parent instalment reminder, ops escalation. No amounts or gateway ids appear in teacher-facing drafts.")
P("<b>AI's role.</b> Classify free-text remarks (e.g. 'offered 20% retention scholarship discount') and polish drafts. It cannot approve, reject, or change an amount, owner or code. Prompts are in <font face='Courier'>prompts/</font>; the LLM path is optional (API key via environment) and was <b>not tested live</b>.")

# ------------------------------------------------------------------ 10 prototype
H1("10. Prototype implementation")
P("One command runs everything: <font face='Courier'>python -m src.main --input data/raw --output results</font>. Dashboard: <font face='Courier'>streamlit run dashboard/app.py</font>. Tests: <font face='Courier'>python -m pytest</font>.")
tbl([["Module", "Responsibility"],
     ["data_loader / validators", "Schema check, NULL handling, phone/email/money/time normalisation (originals kept), input fingerprints"],
     ["matching_engine / duplicate_detector", "Exact-id linkage; probable-match hints (never approve); identical-duplicate form collapse; duplicate invoice detection"],
     ["eligibility_engine", "17 audited steps (16 checks + decision): payment, integrity, duplicates, linkage, identity, teacher/course, contact, amount/discount, required fields, batch, capacity, slot, timeline, booking, conflicts, decision"],
     ["batch_capacity / scheduling_validator", "Seats from reference table (assumption A1 off by default); session and recurring-slot overlaps"],
     ["exception_handler / message_generator", "Owner, priority, SLA, action; deterministic drafts with optional LLM polish; nothing is sent"],
     ["metrics / report_generator / audit_logger", "KPIs with definitions, root-cause table, 206-row audit trail on the sample"],
     ["main", "CLI, idempotency ledger (simulated execution state), all output files"]], [2.6, 6])
H2("Safety properties demonstrated")
B(["<b>Idempotency:</b> first run on the official data creates 3 simulated executions; the second creates 0 and skips 3; outputs are byte-identical (tested).",
   "<b>Immutability:</b> input SHA-256 identical before and after (tested).",
   "<b>No silent drops:</b> every invoice and every orphan form gets a decision; counts reconcile (tested).",
   "<b>Fails safe:</b> unknown state, missing field or fuzzy match produces an exception, never an approval.",
   f"<b>Tests:</b> {TESTS}, covering the 20 required scenarios plus immutability, idempotency, ownership, messages, metrics, reproducibility and schema errors. Not tested: live LLM, browser rendering, any production integration."])

# ------------------------------------------------------------------ 11 results
H1("11. Actual prototype results")
lab = {"AUTO_APPROVE": "Auto-approve", "AWAITING_SCHEDULING": "Ready: schedule existing booking", "ALREADY_PROCESSED": "Already processed", "EXCEPTION": "Exception"}
em = exc.set_index("record_id")
rows = [["Case", "Decision", "Reason codes", "Owner / priority"]]
for _, c in cases.iterrows():
    cid = c.case_id
    codes = c.reason_codes if isinstance(c.reason_codes, str) else ("info: " + c.info_codes if isinstance(c.info_codes, str) else "-")
    o = f"{em.loc[cid,'assigned_owner']} / {em.loc[cid,'priority']}" if cid in em.index else ("Scheduling Ops / P1 (49 h wait)" if c.decision == "AWAITING_SCHEDULING" else "-")
    rows.append([cid.replace("CASE-", ""), lab[c.decision], codes.replace("|", ", "), o])
tbl(rows, [1.1, 2.3, 3.6, 2.3])
P(f"<b>Totals:</b> {len(d)} invoices + 1 orphan form processed; {dec.get('AUTO_APPROVE',0)} auto-approved ({dec.get('AUTO_APPROVE',0)/len(d):.1%}), {dec.get('AUTO_APPROVE',0)+dec.get('AWAITING_SCHEDULING',0)+dec.get('ALREADY_PROCESSED',0)} safe to schedule or done ({(dec.get('AUTO_APPROVE',0)+dec.get('AWAITING_SCHEDULING',0)+dec.get('ALREADY_PROCESSED',0))/len(d):.1%}), {dec.get('EXCEPTION',0)} invoice exceptions ({dec.get('EXCEPTION',0)/len(d):.1%}), 23 follow-up drafts, 206 audit rows. The 15% auto-approval rate is deliberately conservative on a hand-picked edge-case sample; do not read it as a production rate.")
P("<b>84905 nuance.</b> Under assumption A1 (the batch count already includes the student) the 'batch full' reason disappears, but the engine still stops: an existing booking failed and needs a human retry. It never silently re-approves.")

# ------------------------------------------------------------------ 12 dashboard
H1("12. Operations dashboard")
img("dashboard_real.png", w=W * .97, cap="Figure 8 - Screenshot of the running Streamlit dashboard (Chromium via Playwright), top of page. KPIs equal the engine output; filters were tested against independently computed values.")
B(["<b>KPI cards:</b> paid renewals, auto-approved, pending exceptions, unscheduled bookings, orphaned invoices, estimated hours saved (illustrative). Average reconciliation time is shown as unavailable: no production reconciliation timestamps exist.",
   "<b>Charts:</b> pipeline funnel, exceptions by reason, daily volume, auto vs manual split, teacher follow-up stage. Payment-detection SLA breaches are unavailable (no webhook timestamps).",
   "<b>Tables:</b> invoices pending over 12 h, forms awaiting submission, bookings awaiting scheduling, payment mismatches, unscheduled students, ownership queue with required action and SLA.",
   "<b>Filters:</b> date, teacher, student, batch, exception type, priority, region (derived from mobile prefix, not a source field)."])

# ------------------------------------------------------------------ 13 SOP
H1("13. SOP and ownership")
P("The SOP (<font face='Courier'>docs/operations_sop.md</font>) covers daily operations, teacher duties, parent communication, exception management, safety and continuity. Owners are <b>proposed</b>; the data only shows ops_exec_01 to 03.")
tbl([["Owner (proposed)", "Owns", "Escalates to"],
     ["Finance Ops", "Payment not verified, amount mismatch, partial payment, duplicate invoice (P1)", "Ops Manager if P1 unacknowledged in 30 min"],
     ["Scheduling Ops", "Batch full/inactive, conflicts, batch change, unscheduled bookings", "Ops Manager after 4 business h"],
     ["Ops Executive", "Invalid references, orphaned invoices, identity and teacher/course issues", "Ops Manager"],
     ["Parent Success", "Parent contact confirmation, batch-change conversations", "Ops Executive after 1 business day"],
     ["Teacher", "Submit or correct forms; 2 h reminder, 12 h escalation", "Ops Executive"],
     ["Ops Manager", "Discount approval, overrides, policy gaps", "Head of Operations"]], [1.6, 4.2, 2.4])
B(["<b>Safety:</b> kill switch on auto-approval; manual override with reason, user and timestamp; append-only audit; rollback by cancelling bookings by idempotency key; role-based data access.",
   "<b>Continuity:</b> during an outage the manual process runs as today and scheduled classes are never touched; on recovery, reconcile the outage window (idempotency prevents duplicates)."])

# ------------------------------------------------------------------ 14 roadmap
H1("14. 30-60-90 day roadmap")
tbl([["Phase", "Activities and deliverables", "Success metrics", "Go / no-go and rollback"],
     ["Days 1-30\nBaseline + shadow", "Validate A1, instalment and discount policy; 3-month production extract; time study; engine in shadow mode (no writes); 10-20 teacher pilot; train Ops on queue and dashboard", "Engine agrees with Ops outcome on 95% or more of shadow cases; zero false approvals", "Go if every disagreement is explained and the rule fixed. Rollback: stop the shadow job (nothing live)"],
     ["Days 31-60\nControlled auto-approval", "50-100 teachers; auto-approve same-batch, full-payment, clean cases only; webhook + n8n + idempotent booking creator; exception notifications (human-approved WhatsApp); weekly false-positive review", "Clean renewals scheduled within 4 business h; P1 owner in 30 min; zero duplicate bookings", "Go after 2 weeks with zero wrong approvals. Rollback: flip the flag; cancel by idempotency key"],
     ["Days 61-90\nScale", "200+ teachers; form optional for same-batch; batch-change self-service link; Metabase; threshold tuning; savings measured against the 30-day baseline", "Auto-approval share vs baseline; payment-to-first-class P50/P90; Ops hours per renewal", "Go on KPI targets met 2 weeks plus Head of Ops sign-off. Rollback: cohort back to shadow"]], [1.3, 4, 2.2, 2.6])
P("Dependencies: read-only DB or exports; webhook signing keys; approved WhatsApp templates; named owners. Change management by stakeholder is in <font face='Courier'>docs/change_management.md</font>.")

# ------------------------------------------------------------------ 15 risk
H1("15. Risk management", brk=False)
tbl([["Risk", "Mitigation", "Owner"],
     ["Wrong auto-approval of a payment", "Approval needs zero blocking codes; shadow period; kill switch; audit; 0-error go/no-go", "Head of Ops"],
     ["Duplicate booking", "Idempotency key + unique constraint; existing booking never recreated (tested)", "Engineering"],
     ["Assumption A1 (seat counted) is wrong", "Default off; validate; capacity check for net-new seats", "Scheduling Ops"],
     ["Masked identifiers hide mismatches", "Compare full numbers or hashes in production; student_id stays the anchor", "Engineering"],
     ["13-row sample overfits", "Treat rates as illustrative until the 3-month extract", "Program Manager"],
     ["Weekend/holiday behaviour untested", "Business calendar config; test on real data", "Program Manager"],
     ["LLM drafts hallucinate", "Wording only; template fallback; human approval; no new facts", "Program Manager"],
     ["Discount leakage continues", "Discount codes with approver id", "Ops Manager"]], [2.6, 4.6, 1.4])
P("Full register with likelihood and impact: <font face='Courier'>docs/risk_register.md</font>.")

# ------------------------------------------------------------------ 16 impact
H1("16. Business impact and estimated savings", brk=False)
P("<b>Model (transparent, assumption-driven):</b> hours saved per month = renewals x auto-approval share x manual minutes avoided / 60. Nothing here is a historical figure.")
tbl([["Input", "Value", "Basis"],
     ["Monthly renewals", "Unknown (1,000 used only to show scale)", "Assumption - obtain from Ops"],
     ["Auto-approval share, current rules", "15.4% (2 of 13)", "Measured on sample"],
     ["Auto-approval share, invoice-first", "38.5% (5 of 13)", "Simulation on sample"],
     ["Manual minutes per clean renewal", "10", "Assumption - run a time study"],
     ["Hours saved per 1,000 renewals", "about 25.6 (current) to about 64.1 (invoice-first)", "Output of the model"]], [2.6, 3.2, 2.6])
P("<b>Beyond hours.</b> Faster time to first class (the sample shows a clean renewal waiting 33 h); fewer approvals of unbookable forms; a control on discounts; visibility of 49-hour stalls. These are valued by the Operations Head, not estimated here.")

# ------------------------------------------------------------------ 17 conclusion
H1("17. Conclusion and recommendations", brk=True)
B(["<b>Start in shadow mode.</b> Run the engine beside Ops for 2-4 weeks and review every disagreement before any automatic action.",
   "<b>Fix the data-entry causes first:</b> invoice picker, discount codes, form idempotency. They remove whole exception classes.",
   "<b>Make the teacher form optional for same-batch renewals</b> once shadow results confirm the simulation.",
   "<b>Validate five assumptions</b> (seat counting, instalment policy, discount approver, form optionality, owner names) in the first week.",
   "<b>Keep AI in its lane:</b> wording and classification only, behind human approval, until measured error rates justify more."])
callout("<b>What is complete and what is not.</b> Complete: data audit, engine, tests, outputs, dashboard, documents, this report. Not complete: a production n8n workflow (the export ran locally only, with a manual trigger and placeholder notifications), payment/WhatsApp/DB integrations, live LLM test, the optional Loom walkthrough.")
H1("Appendix A. Reason-code taxonomy (rubric)")
P("Machine-readable source of truth: <font face='Courier'>src/config.py</font>. 'Blocks' = prevents auto-approval while open. Informational codes never page anyone.")
import sys; sys.path.insert(0, str(ROOT))
from src.config import REASONS
tbl([["Code", "Blocks", "Severity", "Owner", "Pri", "Required action"]] + [[p.code, "Yes" if p.blocking else "No", p.severity, p.owner, p.priority, p.action] for p in REASONS.values()], [2.5, .7, .8, 1.2, .4, 4.4])
S.append(Spacer(1, 4))
H2("Sources and assumptions")
B(["<b>Source:</b> official repository github.com/bambinoslive/AI-PM-hiring-take-home-assignments (ops/data, ops/README). Reproduce with <font face='Courier'>python -m src.main</font>.",
   "<b>A1</b> active_students_count may already include the renewing student (default: off). <b>A2</b> all timestamps share one timezone. <b>A3</b> 50-minute sessions (from schedule rows). <b>A4</b> 10 manual minutes per clean renewal. <b>A5</b> owner roles, priorities and SLAs are proposals. <b>A6</b> currency INR on every invoice, including Stripe +971/+1, taken at face value.",
   "<b>Repository note:</b> the official README restricts these assets to shortlisted candidates and gives no sharing terms, so the raw CSVs are excluded from git history (see .gitignore). Derived outputs contain masked values from the same data: share the repository privately or confirm with Bambinos first."])

Doc(str(OUT)).multiBuild(S)
print("built", OUT, "| tests:", TESTS)
