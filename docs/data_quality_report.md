# Data quality report

Generated from `results/data_profile.json` (all five files; originals verified unchanged by SHA-256).

## Structural quality
| Check | Result |
|---|---|
| Rows per table | invoices 13, forms 12, bookings 4, schedule 2, reference 13 |
| Duplicate primary keys | none in any table |
| Soft-deleted rows (`deleted_at` set) | 0 |
| Forms citing an unknown invoice | ['84931'] |
| Bookings citing an unknown invoice / form | [] / [] |
| Schedule rows citing an unknown booking | [] |
| Invoices whose student is missing from the reference | [] |
| Paid/any invoices without an exact-id form | ['84906', '84910', '84913'] |
| Bookings with NULL `classbatch_id` | ['5512'] |
| Users with more than one student | [] (multi-child case NOT observable) |

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
