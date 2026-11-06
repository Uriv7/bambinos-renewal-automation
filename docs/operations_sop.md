# Operations SOP - renewal to scheduling (proposed)

Roles are proposed (see `exception_ownership_matrix.md`). Thresholds are targets to validate with the Head of Operations.

## A. Daily operations
| Time | Task | Source | Done when |
|---|---|---|---|
| Start of day | Review queue sorted P1 -> P3 | `flagged_exceptions.csv` / dashboard "Exception ownership queue" | Every P1 acknowledged |
| Start of day | Clear high-priority payment issues (PAYMENT_NOT_VERIFIED, AMOUNT_MISMATCH, PARTIAL_PAYMENT) | Finance Ops checks the gateway dashboard | Each marked captured / failed / pending with a note |
| Hourly | Missing teacher forms: reminder at 2 h is automatic; Ops Executive calls teachers at 12 h | "Teacher forms awaiting" table | No paid invoice > 12 h without owner |
| Hourly | Unscheduled bookings (`booking_ready.csv`, `sla_status`) | dashboard | No ready booking > 4 business h |
| Every 4 h | SLA breaches review | dashboard | Breaches have an escalation |
| End of day | Re-run reconciliation; confirm open items have owner + next action; hand over | `python -m src.main` | Queue count + age recorded in the log |

## B. Teachers
1. Same-batch renewal: no action once the invoice is paid (target state); until then submit the form within 2 h of payment, selecting the invoice from the list.
2. Batch-change renewal: submit the form with parent's preferred batch/slot; never promise availability.
3. Never offer a discount unless Sales/Ops issued a code.
4. Respond to a discrepancy alert within 4 business hours; if unable, reply "cannot resolve" so Ops takes over.
5. Escalation: no reply at 12 h -> Ops Executive phones.

## C. Parent communication (drafts in `follow_up_messages.csv`; humans approve until trust is earned)
Payment confirmation after booking is created; same-batch: confirm continuity + schedule; batch change: ask for two preferred slots, promise nothing; delay: state next update time; discrepancy: ask via the **registered** number, never reveal amounts or payment ids in group chats.

## D. Exception management
Priorities and owners: `decision_matrix.md`. Procedure: acknowledge -> investigate using the explanation + probable-match hint (hint is not proof) -> fix the data at source -> re-run -> confirm decision. Escalate per matrix. Never edit results files by hand.

## E. Safety and reliability
- **Manual override:** Ops Manager may force-approve with a written reason; logged with user + timestamp.
- **Approval permissions:** auto-approve flag controlled by Head of Operations; discounts by Ops Manager only.
- **Audit log:** every rule outcome per case (`audit_log.csv`); append-only in production.
- **Rollback:** disable auto-approve flag; automation-created bookings are identified by idempotency key and can be cancelled in bulk.
- **Data access:** role-based; PII masked in analytics views.
- **Incident:** wrong auto-approval => freeze flag, list affected keys, notify parents, post-mortem in 48 h.

## F. Business continuity
During an outage the existing manual process runs unchanged; scheduled classes are never touched by the engine. On recovery run reconciliation over the outage window; idempotency keys prevent duplicate bookings; any record without a decision is an exception, not silently skipped.
