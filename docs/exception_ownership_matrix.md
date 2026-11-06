# Exception ownership matrix

Roles are **proposed** (the data has `ops_exec_01..03` only). Names to be assigned by the Head of Operations.

| owner | reason codes owned | P1 codes |
|---|---|---|
| Finance Ops | PAYMENT_NOT_VERIFIED, DUPLICATE_INVOICE, AMOUNT_MISMATCH, PARTIAL_PAYMENT | PAYMENT_NOT_VERIFIED, DUPLICATE_INVOICE, AMOUNT_MISMATCH |
| Ops Executive | INVOICE_NOT_FOUND, ORPHANED_INVOICE, DUPLICATE_FACULTY_FORM, STUDENT_ID_MISMATCH, TEACHER_ID_MISMATCH, COURSE_MISMATCH, BOOKING_ALREADY_EXISTS, SCHEDULE_ALREADY_EXISTS, MISSING_REQUIRED_FIELD, INVALID_REFERENCE, TIMESTAMP_ANOMALY | STUDENT_ID_MISMATCH |
| Ops Manager | DISCOUNT_REQUIRES_APPROVAL | - |
| Parent Success | PARENT_CONTACT_MISMATCH | - |
| Scheduling Ops | BATCH_INACTIVE, BATCH_FULL, SCHEDULING_CONFLICT, MANUAL_REVIEW_REQUIRED | BATCH_INACTIVE, BATCH_FULL |
| Teacher | MISSING_FACULTY_FORM | - |

## Escalation

| Owner | Escalation trigger | Escalates to |
|---|---|---|
| Teacher | Reminder at 2 h; escalate to Ops Executive at 12 h | Ops Executive |
| Finance Ops | P1 not acknowledged in 30 min | Ops Manager |
| Scheduling Ops | Unscheduled > 4 business h after eligibility | Ops Manager |
| Parent Success | No parent reply in 1 business day | Ops Executive |
| Ops Executive | P2 unresolved in 4 business h | Ops Manager |
| Ops Manager | Policy gap / discount / repeated breach | Head of Operations |

## Current open queue (from the official sample)

| assigned_owner | open_exceptions | p1_count | cases | reason_codes |
|---|---|---|---|---|
| Finance Ops | 2 | 2 | 84909/84911 | AMOUNT_MISMATCH/PAYMENT_NOT_VERIFIED |
| Scheduling Ops | 1 | 1 | 84905 | BATCH_FULL |
| Ops Executive | 4 | 0 | 84906/84912/84913/FORM-3313 | ORPHANED_INVOICE/MISSING_REQUIRED_FIELD/INVALID_REFERENCE/INVOICE_NOT_FOUND |
| Ops Manager | 1 | 0 | 84907 | DISCOUNT_REQUIRES_APPROVAL |
| Parent Success | 1 | 0 | 84904 | PARENT_CONTACT_MISMATCH |
| Teacher | 1 | 0 | 84910 | MISSING_FACULTY_FORM |
