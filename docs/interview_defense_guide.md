# Interview defense guide

## 60-second story
Of 13 sample invoices, 11 were paid but only 1 had a scheduled class; 5 paid renewals were > 24 h old with none. The manual chain (teacher form -> Ops verify -> booking -> schedule) fails in predictable ways. I built a deterministic reconciliation engine that auto-approves only provably clean renewals (2 of 13 today; 5 of 13 in an invoice-first simulation), routes the other 9 invoices + 1 orphan form to named owners with reason codes, and never creates a booking twice.

## Core answers
- **Why the workflow fails:** manual keying (84931), no timers (84906 at 26 h), approvals before validation (2 of 4 approved forms were impossible to book), payments confused with claims (84911), no owner for hand-offs (5502 at 49 h).
- **Why the new one is better:** gateway-as-truth, invoice-first for same-batch, timers + owners, idempotent actions, audit trail.
- **Why 84903 and 84908 are auto-approved:** Paid with gateway id; ids/educator/course/contact agree; net = standard fee; same active batch with seats (3/6 and 5/6); no existing booking; no conflicts. 84908 had an identical duplicate form (same payload) collapsed, logged.
- **Why the rest are not:** each has a named blocker (see `decision_matrix.md`).
- **Preventing wrong approvals:** approval requires *zero* blocking codes; unknown state => exception; LLM has no authority; shadow mode first; kill switch.
- **Batch capacity:** from reference `active_students_count` vs `max_batch_size`; same-batch seat-held logic is assumption A1 and **off** by default.
- **Weekends:** untestable (data Sun-Tue). Plan: business-calendar config; SLAs in business hours; weekend scheduling queue; validate with 3 months of data.
- **Safe rollout:** shadow -> 10-20 teachers -> 50-100 happy-path only -> 200+; go/no-go on zero wrong approvals.
- **Not implemented:** n8n, gateway webhooks, WhatsApp API, production DB, live LLM test, production idempotency constraint.
- **Realistic savings:** 25-64 h per 1,000 renewals/month *under assumptions* (10 min/touch, volume unknown); the stronger case is latency.
- **After deployment:** weekly false-positive/negative review, add rules from exceptions, move more categories to auto as evidence accrues.

## Tough questions
1. *13 rows is tiny - why trust this?* I don't generalise the rates; the sample proves the failure modes exist and the engine handles them. Baseline comes from the 3-month pull in days 1-30.
2. *Why not just let an LLM approve?* Money decisions need determinism, repeatability and audit. The LLM only drafts/classifies.
3. *What if the engine auto-approves wrongly?* Conservative rule set, shadow mode, flag-off rollback, idempotency keys list affected bookings.
4. *Isn't removing the teacher form risky?* Only for same-batch full-payment renewals, and only after shadow validation; the form stays for batch change.
5. *Is 84905 really batch-full?* Unknown: 6/6 but the student is already a member. If counts include them it's a false positive (A1). I made it an exception, not an approval, and flagged the validation.
6. *Why is 84908 auto-approved with two forms?* Payload-identical (same fields, about 5 minutes apart, remark "browser froze"); collapsed to the earliest, logged; non-identical duplicates block.
7. *Why not approve 84904 - payment is verified?* Payer contact differs from registered (phone and email). A verified payment from an unverified payer is not an identity match; confirm via the registered number.
8. *Why hold 84907?* Discount of 1,900 with no approver anywhere; it may be legitimate but is a control gap.
9. *Why does 84909 have two codes?* Partial payment (5250/10500) and the teacher claimed 10500.
10. *Why doesn't the engine match 3313 to 84913?* It sees the digit transposition and same student/amount (confidence 0.8-1.0) but never approves on a fuzzy match; it asks the teacher to correct.
11. *How do you know 5 paid invoices are stuck > 24 h?* `payment_age_hours` vs as-of 2026-11-03 18:00; some may be mid-process, so it's a snapshot, not proven leakage.
12. *What's your as-of date?* Latest timestamp in data, for reproducibility; configurable with `--as-of`.
13. *Timezones?* Not in the data; single timezone assumed; flagged.
14. *How is idempotency shown?* Tests + run twice on real data: 3 new, then 0 new / 3 skipped; outputs byte-identical.
15. *What did you not test?* Live LLM calls, any production integration, the n8n flow beyond a local manual-trigger run (no schedule/webhook trigger, no real notifications), weekend behaviour. (Dashboard was checked in a real browser.)
16. *Currency is INR for US/UAE parents - a bug?* Possibly display-currency; I compared in INR only; needs confirmation.
17. *Why proposed owners/SLAs?* The data only shows `ops_exec_01..03`; roles are proposals for the Head of Ops to correct.
18. *What would you do first on day 1?* Validate A1, instalment and discount policy; pull 3 months; start the shadow run.
19. *How do you stop alert fatigue?* One reminder, one escalation; P1/P2/P3; informational codes don't page anyone.
20. *Biggest risk?* Over-trusting a small sample; second: masked identifiers hiding mismatches.
