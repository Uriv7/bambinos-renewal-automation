# Renewal decision matrix

Owners, priorities and SLAs are **proposed**, to be validated with the Operations Head. Generated from `src/config.py`.

A renewal is auto-approved only when **no** blocking reason code is raised. LLMs take no part in these decisions.

## A. The 12 required scenarios

| Scenario | Detection logic | Auto-approve? | Reason code | Owner | Priority | SLA | Required next action | Channel | Observed in dataset |
|---|---|---|---|---|---|---|---|---|---|
| 1 Same-batch, same-teacher renewal | Paid + exact-id form + ids/teacher/course/contact agree + net = standard fee + same batch active with seat + no booking | YES | - | Ops Executive (monitor only) | P3 | Booking+schedule within 4 business h | Create booking once, create schedule, confirm to parent | Parent WhatsApp | 84903, 84908 (84908 after collapsing identical duplicate form 3309) |
| 2 Same-batch, different-teacher | form/invoice educator_id != reference educator_id | NO | TEACHER_ID_MISMATCH | Ops Executive | P2 | Resolve within 4 business hours | Confirm educator for the batch; fix form or batch record | Ops queue + WhatsApp (teacher) | Not observed |
| 3 Different-batch renewal | continue_same_batch = No (form has no target-batch field) | NO | MISSING_REQUIRED_FIELD + MANUAL_REVIEW_REQUIRED | Scheduling Ops | P2 | Resolve within 4 business hours | Capture parent's choice; capacity-check the chosen batch; then book | Parent WhatsApp + Ops queue | 84912 (booking 5512 already created with NULL batch) |
| 4 Parent identity mismatch | invoice mobile/email != registered; or form mobile != registered | NO | PARENT_CONTACT_MISMATCH | Parent Success | P2 | Resolve within 4 business hours | Confirm payer with the REGISTERED number | WhatsApp (parent, registered number) | 84904 (mobile XXXX77 vs XXXX04; email also differs) |
| 5 Student identity mismatch | student_id/user_id differ across invoice, form, reference, booking | NO | STUDENT_ID_MISMATCH | Ops Executive | P1 | Ops response within 30 min (operating hours) | Verify with parent+teacher; never match on name/phone | Ops queue | Not observed |
| 6 Payment mismatch | form amount != invoice net; or net != standard fee (discount => approval needed) | NO | AMOUNT_MISMATCH / DISCOUNT_REQUIRES_APPROVAL | Finance Ops | P1 | Ops response within 30 min (operating hours) | Reconcile amounts; confirm discount approver | Ops queue | 84907 (20% discount, net 7600 vs fee 9500), 84909 (form 10500 vs net 5250) |
| 7 Partial payment | payment_status = Partially_Paid | NO | PARTIAL_PAYMENT | Finance Ops | P2 | Resolve within 4 business hours | Hold; instalment-2 reminder; policy decision | WhatsApp (parent) + Ops queue | 84909 (Installment_1_of_2, 5250 of 10500) |
| 8 Duplicate invoice | same invoice_number / gateway id / student+class paid within 30 days | NO | DUPLICATE_INVOICE | Finance Ops | P1 | Ops response within 30 min (operating hours) | Choose authoritative invoice; refund/merge | Ops queue | Not observed |
| 9 Missing teacher form | paid invoice with no form on exact invoice id (reminder 2 h; escalate 12 h) | NO (today) | MISSING_FACULTY_FORM (+ORPHANED_INVOICE >=12h; INVALID_REFERENCE if typo) | Teacher -> Ops Executive at 12 h | P2 | Resolve within 4 business hours | Teacher submits form (target state: not needed for same-batch) | Teacher WhatsApp | 84906 (26 h), 84910 (~6.7 h), 84913 (typo 84931) + orphan form 3313 |
| 10 Full batch | active_students_count >= max_batch_size (seat-held assumption A1 off by default) | NO | BATCH_FULL | Scheduling Ops | P1 | Ops response within 30 min (operating hours) | Check if seat already counted; else alternatives | Ops queue + WhatsApp (parent) | 84905 (6/6, same-batch renewal, booking 5505 Failed_Batch_Full) |
| 11 Scheduling conflict | overlapping non-cancelled sessions for same student/educator | NO | SCHEDULING_CONFLICT | Scheduling Ops | P2 | Resolve within 4 business hours | Resolve overlap before creating rows | Ops queue | Session-level: not observed. Informational: educator 1125 batches 9207 (Mon 15:30) / 9211 (Mon 16:00) overlap if sessions are 50 min |
| 12 Existing booking | booking_requests row exists for invoice | NO new approval | BOOKING_ALREADY_EXISTS / SCHEDULE_ALREADY_EXISTS (info) | Ops Executive / Scheduling Ops | P3 (P1 if SLA breached) | - | Never create a second booking; continue from existing one | Ops queue | 84901 (done), 84902 (49 h unscheduled), 84905, 84912 |

## B. Reason-code policy (machine-readable source of truth)

| code | blocks auto-approval | severity | owner | priority | action | channel |
|---|---|---|---|---|---|---|
| PAYMENT_NOT_VERIFIED | True | Critical | Finance Ops | P1 | Check gateway dashboard for the order; confirm captured/failed/pending before any approval. | Ops queue + WhatsApp (parent) |
| INVOICE_NOT_FOUND | True | High | Ops Executive | P2 | Locate the intended invoice (see probable match) and ask the teacher to resubmit with the right invoice. | Ops queue + WhatsApp (teacher) |
| ORPHANED_INVOICE | True | High | Ops Executive | P2 | Paid invoice has no form and no probable candidate form; contact teacher/parent to identify the renewal. | Ops queue |
| MISSING_FACULTY_FORM | True | High | Teacher | P2 | Teacher submits the renewal form (reminder at 2h, escalate to Ops Executive at 12h). | WhatsApp (teacher) |
| DUPLICATE_INVOICE | True | High | Finance Ops | P1 | Confirm which invoice is authoritative; refund or merge the duplicate. | Ops queue |
| DUPLICATE_FACULTY_FORM | False | Low | Ops Executive | P3 | Identical duplicate collapsed to the earliest form; non-identical duplicates need review. | Audit log |
| AMOUNT_MISMATCH | True | High | Finance Ops | P1 | Reconcile invoice net amount vs teacher-entered amount vs standard fee before approving. | Ops queue |
| DISCOUNT_REQUIRES_APPROVAL | True | Medium | Ops Manager | P2 | Confirm the discount was authorised by Sales/Ops Head; record the approver. | Ops queue |
| STUDENT_ID_MISMATCH | True | Critical | Ops Executive | P1 | Verify student identity with parent/teacher; never approve on name or phone similarity. | Ops queue |
| PARENT_CONTACT_MISMATCH | True | Medium | Parent Success | P2 | Confirm with the registered parent number that the paying contact is authorised. | WhatsApp (parent, registered number) |
| TEACHER_ID_MISMATCH | True | High | Ops Executive | P2 | Confirm the educator for the batch; correct the form or the batch record. | Ops queue + WhatsApp (teacher) |
| COURSE_MISMATCH | True | High | Ops Executive | P2 | Confirm the course/level being renewed. | Ops queue |
| BATCH_INACTIVE | True | High | Scheduling Ops | P1 | Find an equivalent active batch and agree it with the parent. | Ops queue |
| BATCH_FULL | True | High | Scheduling Ops | P1 | Check whether the student's seat is already counted (same-batch renewal); otherwise offer alternatives. | Ops queue + WhatsApp (parent) |
| SCHEDULING_CONFLICT | True | High | Scheduling Ops | P2 | Resolve teacher/student overlap before creating schedule rows. | Ops queue |
| BOOKING_ALREADY_EXISTS | False | Low | Ops Executive | P3 | Do not create a new booking; continue from the existing one. | Audit log |
| SCHEDULE_ALREADY_EXISTS | False | Low | Ops Executive | P3 | Do not recreate schedule rows. | Audit log |
| PARTIAL_PAYMENT | True | High | Finance Ops | P2 | Hold scheduling per policy; send instalment-2 reminder; confirm instalment policy with Ops Head. | WhatsApp (parent) + Ops queue |
| MISSING_REQUIRED_FIELD | True | Medium | Ops Executive | P2 | Obtain the missing field (e.g. target batch) from teacher/parent. | Ops queue |
| INVALID_REFERENCE | True | High | Ops Executive | P2 | Fix the dangling/typo reference with the teacher; use the probable match as a hint only. | Ops queue + WhatsApp (teacher) |
| TIMESTAMP_ANOMALY | True | Medium | Ops Executive | P2 | Form was created before its invoice existed; verify the form really belongs to this invoice. | Ops queue |
| MANUAL_REVIEW_REQUIRED | True | Medium | Scheduling Ops | P2 | Human decision needed (e.g. batch-change renewal). | Ops queue |

`TIMESTAMP_ANOMALY` and `DISCOUNT_REQUIRES_APPROVAL` are additions to the suggested list. `TIMESTAMP_ANOMALY` was **not observed** in the data.
