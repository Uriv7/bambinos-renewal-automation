# Zero-touch automation design

## Principle
Deterministic code decides money and eligibility. AI helps with wording, classification of free-text remarks and investigation. Humans own exceptions.

## Target flow
```
Payment webhook -> verify -> reconcile to invoice -> identity match -> form reconcile (optional for same-batch)
 -> eligibility -> batch capacity -> schedule validation -> decision
     CLEAN     -> auto-approve -> create booking (idempotent) -> create schedule -> parent confirmation
     EXCEPTION -> queue -> owner -> follow-up -> human approval -> booking/schedule -> re-run reconciliation
```
Full Mermaid source: `workflow_diagram.mmd`. Component view: `system_architecture.md`.

## Re-engineered process (what changes, and why)
1. **Invoice-first renewal.** A paid renewal invoice creates the renewal record. The teacher form becomes *optional for same-batch* and mandatory only for batch change. Simulation on the official sample: auto-approvals 2 -> 5 of 13 (`results/whatif/invoice_first/`). This is a simulation of rules, not a production result.
2. **Gateway as source of truth.** Forms for non-Paid invoices are parked, never approved (84911).
3. **Capacity checks only for net-new seats.** Same-batch renewal does not consume a seat *if* the reference count includes the student (A1 - validate first; default is conservative).
4. **Invoice picker, not free text.** Eliminates the 84913/84931 class of error.
5. **Discount codes with approver id** replace verbal teacher offers.
6. **Timers, not memory:** 2 h teacher reminder, 12 h escalation, 4 business-hour scheduling SLA, 30 min P1 response.

## Idempotency and safety
- Deterministic key `sha256(invoice|form|student|batch|sessions|decision)[:16]`; ledger prevents re-execution; existing booking => never a second one (tested, and demonstrated: run 1 -> 3 simulated executions, run 2 -> 0).
- Originals never written (SHA-256 verified in tests).
- Full audit trail per rule per case (`results/audit_log.csv`, 206 rows for 14 cases).
- Failure policy: any unknown state => EXCEPTION, never approval.

## Honest status
Implemented: reconciliation engine, drafts, ledger simulation, dashboard. **Not implemented / not connected:** n8n beyond a local proof (the exported flow imports and executes in n8n 2.35.7 with a manual trigger; see `n8n_test_evidence.md`; schedule/webhook triggers and notifications are not built), Razorpay/Stripe webhooks, WhatsApp Business API, production DB, live LLM calls (code path exists, untested without a key). See `system_architecture.md` for the integration plan.
