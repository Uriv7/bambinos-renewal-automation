# Data dictionary

Source: official `ops/README.md` (column lists) + profiling of the files. Types are inferred from values; descriptions marked * come from the official README, others are inferred and unverified.

## 1_invoices.csv  (13 rows, 25 columns, duplicate keys: 0)
| column | inferred type | NULLs | distinct | observed values / range |
|---|---|---|---|---|
| id | integer | 0 | 13 |  |
| invoice_number | text | 0 | 13 |  |
| user_id | integer | 0 | 13 |  |
| student_id | integer | 0 | 13 |  |
| class_id | integer | 0 | 11 |  |
| educator_id | integer | 0 | 6 |  |
| parent_name | text | 0 | 13 |  |
| mobile | text | 0 | 13 |  |
| email | text | 0 | 13 |  |
| currency | text | 0 | 1 | observed: INR=13 |
| amount | decimal | 0 | 8 |  |
| discount_amount | decimal | 0 | 2 |  |
| net_amount | decimal | 0 | 9 |  |
| payment_type | text | 0 | 2 | observed: Full=12, Installment_1_of_2=1 |
| payment_mode | text | 0 | 3 |  |
| payment_gateway | text | 0 | 2 | observed: Razorpay=11, Stripe=2 |
| gateway_order_id | text | 0 | 13 |  |
| gateway_payment_id | text | 1 | 12 |  |
| invoice_link | text | 0 | 13 |  |
| payment_status | text | 0 | 3 | observed: Paid=11, Partially_Paid=1, Failed=1 |
| is_renewal | text | 0 | 1 |  |
| paid_at | text | 1 | 12 | 2026-11-01 10:15:22 -> 2026-11-03 16:50:00 |
| created_at | timestamp | 0 | 13 | 2026-11-01 10:12:00 -> 2026-11-03 16:45:00 |
| updated_at | timestamp | 0 | 13 | 2026-11-01 10:15:22 -> 2026-11-03 16:50:00 |
| deleted_at | text | 13 | 0 |  |
## 2_faculty_form_unapproved.csv  (12 rows, 23 columns, duplicate keys: 0)
| column | inferred type | NULLs | distinct | observed values / range |
|---|---|---|---|---|
| id | integer | 0 | 12 |  |
| educator_id | integer | 0 | 6 |  |
| educator_name | text | 0 | 6 |  |
| user_id | integer | 0 | 11 |  |
| student_id | integer | 0 | 11 |  |
| student_name | text | 0 | 11 |  |
| parent_mobile | text | 0 | 11 |  |
| class_id | integer | 0 | 9 |  |
| current_classbatch_id | integer | 0 | 9 |  |
| invoice_id | integer | 0 | 11 |  |
| invoice_link | text | 0 | 11 |  |
| amount_paid | decimal | 0 | 7 |  |
| sessions_purchased | integer | 0 | 1 |  |
| continue_same_batch | text | 0 | 2 | observed: Yes=11, No=1 |
| preferred_days | text | 0 | 6 |  |
| preferred_time_slot | time | 0 | 8 |  |
| remarks | text | 0 | 12 |  |
| approval_status | text | 0 | 2 | observed: Pending=8, Approved=4 |
| approved_by | text | 8 | 3 |  |
| approved_at | text | 8 | 4 | 2026-11-01 11:30:00 -> 2026-11-03 17:15:00 |
| created_at | timestamp | 0 | 12 | 2026-11-01 10:45:00 -> 2026-11-03 17:10:00 |
| updated_at | timestamp | 0 | 12 | 2026-11-01 11:30:00 -> 2026-11-03 17:15:00 |
| deleted_at | text | 12 | 0 |  |
## 3_booking_requests.csv  (4 rows, 20 columns, duplicate keys: 0)
| column | inferred type | NULLs | distinct | observed values / range |
|---|---|---|---|---|
| id | integer | 0 | 4 |  |
| faculty_form_id | integer | 0 | 4 |  |
| invoice_id | integer | 0 | 4 |  |
| user_id | integer | 0 | 4 |  |
| student_id | integer | 0 | 4 |  |
| class_id | integer | 0 | 4 |  |
| educator_id | integer | 0 | 4 |  |
| classbatch_id | text | 1 | 3 |  |
| sessions_count | integer | 0 | 1 |  |
| is_renewal | text | 0 | 1 |  |
| continue_same_batch | text | 0 | 2 | observed: Yes=3, No=1 |
| preferred_days | text | 0 | 3 |  |
| preferred_time | time | 0 | 3 |  |
| request_status | text | 0 | 4 | observed: Completed=1, Pending_Batch_Allocation=1, Failed_Batch_Full=1, Awaiting_Parent_Batch_Selection=1 |
| batch_allocated | text | 0 | 2 |  |
| allocated_by | text | 3 | 1 |  |
| allocated_at | text | 3 | 1 | 2026-11-01 12:00:00 -> 2026-11-01 12:00:00 |
| created_at | timestamp | 0 | 4 | 2026-11-01 11:30:00 -> 2026-11-03 17:15:00 |
| updated_at | timestamp | 0 | 4 | 2026-11-01 12:00:00 -> 2026-11-03 17:15:00 |
| deleted_at | text | 4 | 0 |  |
## 4_class_schedule_bookings.csv  (2 rows, 18 columns, duplicate keys: 0)
| column | inferred type | NULLs | distinct | observed values / range |
|---|---|---|---|---|
| id | integer | 0 | 2 |  |
| bookingrequest_id | integer | 0 | 1 |  |
| invoice_id | integer | 0 | 1 |  |
| classschedule_id | integer | 0 | 2 |  |
| classbatch_id | integer | 0 | 1 |  |
| class_id | integer | 0 | 1 |  |
| user_id | integer | 0 | 1 |  |
| student_id | integer | 0 | 1 |  |
| educator_id | integer | 0 | 1 |  |
| class_date | date | 0 | 2 | 2026-11-03 00:00:00 -> 2026-11-05 00:00:00 |
| start_time | time | 0 | 1 |  |
| end_time | time | 0 | 1 |  |
| booking_type | text | 0 | 1 | observed: Regular_Renewal=2 |
| is_cancelled | text | 0 | 1 |  |
| attended_class | text | 0 | 2 |  |
| created_at | timestamp | 0 | 1 | 2026-11-01 12:00:05 -> 2026-11-01 12:00:05 |
| updated_at | timestamp | 0 | 2 | 2026-11-01 12:00:05 -> 2026-11-03 18:00:00 |
| deleted_at | text | 2 | 0 |  |
## reference_active_batches_and_students.csv  (13 rows, 20 columns, duplicate keys: 0)
| column | inferred type | NULLs | distinct | observed values / range |
|---|---|---|---|---|
| student_id | integer | 0 | 13 |  |
| user_id | integer | 0 | 13 |  |
| student_name_masked | text | 0 | 13 |  |
| parent_name_masked | text | 0 | 13 |  |
| registered_mobile_masked | text | 0 | 13 |  |
| registered_email_masked | text | 0 | 13 |  |
| current_classbatch_id | integer | 0 | 11 |  |
| classbatch_name | text | 0 | 11 |  |
| class_id | integer | 0 | 11 |  |
| class_name | text | 0 | 11 |  |
| category_id | integer | 0 | 5 |  |
| category_name | text | 0 | 5 |  |
| educator_id | integer | 0 | 6 |  |
| educator_name | text | 0 | 6 |  |
| standard_fee_24_sessions_inr | decimal | 0 | 8 |  |
| batch_days | text | 0 | 7 |  |
| batch_start_time | time | 0 | 9 |  |
| active_students_count | integer | 0 | 4 |  |
| max_batch_size | integer | 0 | 1 |  |
| deleted_at | text | 13 | 0 |  |

## Keys and relationships

- `invoices.id` <- `faculty_form_unapproved.invoice_id` <- `booking_requests.faculty_form_id`/`invoice_id` <- `class_schedule_bookings.bookingrequest_id`/`invoice_id`.
- `student_id` + `user_id` link every table to `reference_active_batches_and_students` (1 student per user in this sample).
- `NULL` is the literal string used for missing values in the CSVs; the loader maps it to a true null.
- Currency is `INR` on every invoice, including Stripe-paid +971 and +1 parents (to be validated).
- Names, mobiles and emails are masked, so only masked-value equality is testable.
