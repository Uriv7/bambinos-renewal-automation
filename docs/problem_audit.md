# Problem audit - Renewal -> Class Scheduling pipeline

**Evidence base:** the five official CSVs (13 invoices, 12 faculty forms, 4 booking requests, 2 schedule rows, 13 reference students), as of 2026-11-03 18:00 (latest timestamp in the data). Every number below is reproducible with `python -m src.main`. Findings from this sample show *which failure modes exist*, not their production frequency.

## 1. What the lifecycle actually looks like (measured)

| Stage | Count | Note |
|---|---|---|
| Invoices | 13 | 11 Paid, 1 Partially_Paid, 1 Failed |
| Paid invoices with an exact-id teacher form | 8 of 11 | 3 paid invoices have none (84906, 84910, 84913) |
| Forms approved by Ops | 4 of 12 | 8 forms still Pending |
| Booking requests | 4 | all 4 approved forms became bookings |
| Booking requests with any schedule row | 1 of 4 | 5502, 5505, 5512 have none |
| Paid invoices with a scheduled class | 1 of 11 | **5 of 11 paid invoices are > 24 h old with no scheduled class** |

## 2. Findings (all observed in the data)

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| F1 | Clean renewals wait for manual approval | Form 3303 / invoice 84903: clean, Pending for ~33 h | Pure latency on the happy path - the clearest automation win |
| F2 | Paid parent, no teacher form | 84906 (26 h), 84910 (6.7 h) | Renewal silently stalls; no reminder/owner exists |
| F3 | Typo breaks linkage both ways | Form 3313 cites 84931; paid invoice 84913 has no form | Manual keying of invoice id |
| F4 | Form submitted for an unpaid invoice | 84911 Failed, form 3311 (remark: UPI screenshot) | Risk of approving on a screenshot |
| F5 | Teacher overstates payment on a part-paid invoice | 84909: form 10500 vs paid 5250 | Instalment cases enter the same lane as full payments |
| F6 | Teacher-offered discount with no approver | 84907: 9500 -> 7600 (20%), remark "Offered 20% retention scholarship discount" | Revenue leakage / control gap |
| F7 | Payer differs from registered contact | 84904: mobile XXXX77 vs XXXX04, email also differs | Identity/fraud risk or legitimate payer (unverified) |
| F8 | Duplicate teacher submission | 3308/3309 identical payload, about 5 min apart (5 min 12 s) ("browser froze") | Duplicate work; harmless if collapsed deterministically |
| F9 | Ops approved forms that could not be booked | 3305 (batch 6/6 -> booking Failed_Batch_Full), 3312 (batch change, booking 5512 has NULL batch) | **2 of 4 approvals** passed review without the checks that later failed |
| F10 | Approved + clean but unscheduled | 5502 / 84902: 49 h with no schedule rows | Hand-off from approval to scheduling has no SLA/owner |
| F11 | Same-batch renewal blocked as "batch full" | 84905: student already in batch 9205 (6/6) | Likely false positive if the student's seat is already counted (assumption A1) |
| F12 | Partial scheduling vs purchased sessions | 5501: 24 purchased, 2 schedule rows | Unknown whether rolling scheduling is intended |

## 3. Edge-case coverage (requested categories)

| Category | Observed | Not observed (theoretical - needs more data) |
|---|---|---|
| A Invoice | Failed payment, partial payment, discount, payer mismatch | Duplicate invoice, missing student ref, invalid link, wrong gateway state |
| B Form | Missing form, duplicate form, wrong amount, form for unpaid invoice, typo'd invoice id | Student/teacher/course mismatch, missing required fields, delayed submission beyond 12 h on a *linked* form |
| C Booking | Approved-but-impossible bookings, NULL batch, awaiting parent selection | Duplicate booking requests, wrong teacher assignment |
| D Scheduling | Booking with no schedule, partial schedule | Duplicate schedule rows, student/teacher session conflicts, capacity violation after booking |
| E Business | Same-batch, batch-change, partial payment, existing booking, parent-contact mismatch, discount | Teacher-change renewal, multiple children per parent, weekend/holiday delay (data spans Sun-Tue), inactive batch |

The engine and tests cover the unobserved cases with synthetic fixtures, but they are **theoretical** for the company until validated with production data.

## 4. Question the steps before automating them

| Step | Why it exists (hypothesis) | Can it be removed? |
|---|---|---|
| Teacher submits renewal form | Teacher knows whether the child continues and the preferred slot; also acts as a payment claim | For **same-batch** renewals the form adds nothing the invoice + reference table lack (simulation: 2 -> 5 auto-approvals out of 13 without it). Keep it only for batch change / teacher notes |
| Ops verifies payment manually | Teachers submit before payment is confirmed (84911) | Yes - gateway status is the source of truth; replace with a deterministic check |
| Ops approval | Catches typos, amount, duplicates | Replace for clean cases; keep for the exception classes above |
| Parent/Ops picks batch | Needed when changing batch | Skip for same-batch renewals |

## 5. Root-cause hypotheses
Machine-readable in `results/root_cause_analysis.csv`. Each is a **hypothesis** to validate with Ops/teachers: the data shows symptoms, not intent.
