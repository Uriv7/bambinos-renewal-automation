# KPI and SLA framework

All values computed by `src/metrics.py` from the official sample (13 invoices). **Small sample: percentages illustrate method, not a production baseline.**

## A. KPIs (measured)

| metric | definition | numerator | denominator | value_pct | data_source | fully_measurable | limitations |
|---|---|---|---|---|---|---|---|
| Paid invoices | Invoices with payment_status = Paid | 11 | 13 | 84.6 | 1_invoices | True | Status field taken at face value; no gateway ledger to cross-check |
| Unpaid / not-fully-paid invoices | Invoices that are not Paid (Failed + Partially_Paid) | 2 | 13 | 15.4 | 1_invoices | True |  |
| Orphaned paid invoices | Paid invoices with no faculty form linked by exact invoice id | 3 | 11 | 27.3 | 1_invoices, 2_faculty_form | True | Includes 84913 whose form exists but cites a mistyped invoice id |
| Faculty form submission rate (paid invoices) | Paid invoices with an exact-id linked form | 8 | 11 | 72.7 | 1,2 | True |  |
| Faculty form mismatch rate | Linked forms whose amount/contact/batch/timeline disagrees with invoice or reference | 2 | 10 | 20.0 | 1,2,ref | True | Small sample (n<20) |
| Duplicate invoice rate | Invoices colliding with another invoice (number, gateway id, student+class window) | 0 | 13 | 0.0 | 1_invoices | True | None observed in this sample |
| Duplicate faculty form rate | Invoices with >1 active form | 1 | 13 | 7.7 | 2_faculty_form | True | 1 extra form row(s) |
| Faculty forms with an unknown invoice id | Forms citing a non-existent invoice | 1 | 12 | 8.3 | 1,2 | True |  |
| Booking request creation rate (approved forms) | Approved forms that have a booking request | 4 | 4 | 100.0 | 2,3 | True |  |
| Booking requests with no schedule rows | Booking requests without any non-cancelled schedule booking | 3 | 4 | 75.0 | 3,4 | True | 5501 has 2 schedule rows for 24 sessions: partial scheduling cannot be judged without policy |
| Student identity mismatch rate | Invoices raising STUDENT_ID_MISMATCH | 0 | 13 | 0.0 | 1,2,ref | True | None observed; names are masked so only ids are comparable |
| Payment amount mismatch rate | Invoices raising AMOUNT_MISMATCH or DISCOUNT_REQUIRES_APPROVAL | 2 | 13 | 15.4 | 1,2,ref | True |  |
| Batch capacity issues | Invoices raising BATCH_FULL | 1 | 13 | 7.7 | ref, 3 | True | Reference counts may or may not include the renewing student (assumption A1) |
| Auto-approval eligibility rate | Invoices decided AUTO_APPROVE (no booking existed yet) | 2 | 13 | 15.4 | all | True | Conservative: partial/duplicate/contact/batch-change cases are held |
| Safe-to-schedule rate | AUTO_APPROVE + AWAITING_SCHEDULING + ALREADY_PROCESSED | 4 | 13 | 30.8 | all | True |  |
| Exception rate | Invoices decided EXCEPTION | 9 | 13 | 69.2 | all | True | Plus 1 form-level exception (orphan form 3313) |

Calculation method for every KPI: count ratio over de-duplicated, non-deleted rows; as-of `2026-11-03 18:00:00`.

## B. Measured stage timings (hours)

| Stage | n | median | mean | max |
|---|---|---|---|---|
| payment to form created | 10 | 0.45 | 0.49 | 0.83 |
| form created to ops approval | 4 | 1.54 | 1.58 | 2.5 |
| approval to booking created | 4 | 0.0 | 0.0 | 0.0 |
| booking created to first schedule | 1 | 0.5 | 0.5 | 0.5 |

Single timezone assumed (data carries none). With n <= 10 these are descriptive, not a baseline. Teachers who submit are fast (~27 min median); the delay is concentrated in missing forms and in Ops approval/allocation.

## C. Proposed SLAs (targets, **not** existing commitments)

| SLA (proposed) | Target | Measured as | Status in the sample |
|---|---|---|---|
| Payment detection | <= 5 min from gateway capture | Webhook timestamp vs payment record | NOT measurable today: no webhook timestamps; paid_at is the only anchor |
| Clean renewal reconciliation | <= 5 min after complete data | engine decision time - last input time | Prototype is batch; target needs event-driven runs |
| Teacher form reminder | auto at 2 h after payment | paid_at -> now | Measurable: 3 of 11 paid invoices have no exact-id form |
| Missing form escalation | 12 h after payment -> Ops Executive | paid_at -> now | 84906 is at 26 h (breach under this target) |
| P1 payment exception | Ops response <= 30 min in operating hours | exception created -> first action | Needs an exception-queue timestamp that does not exist yet |
| Scheduling completion | <= 4 business h after eligibility | booking created -> first schedule row | Only 1 observation (0.5 h); booking 5502 is at 49 clock-hours with none |

## D. Assumptions to validate with the Operations Head

1. Operating hours and business-hour calendar (weekend/holiday handling is untestable: the data spans Sun-Tue only).
2. Whether `active_students_count` already includes the renewing student (A1).
3. Instalment policy: may classes be scheduled after instalment 1?
4. Who may approve discounts, and where the approval is recorded.
5. Timezone of every timestamp.
