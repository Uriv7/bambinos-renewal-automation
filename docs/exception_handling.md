# Exception handling

Every non-approvable case becomes a row in `results/flagged_exceptions.csv` with: record id, invoice id, student id, reason code(s), explanation, severity, owner, priority, SLA, recommended action, channel, created timestamp.

## Lifecycle
OPEN -> ACKNOWLEDGED (owner) -> WAITING (parent/teacher reply) -> RESOLVED (data corrected) -> **re-run reconciliation** -> auto-approve or new exception. Closing an exception never edits the engine's decision by hand; the data is fixed and the engine re-decides (so audit stays honest).

## Prioritisation
P1 = a paying customer is blocked or money is uncertain (payment, amount, full batch): respond in 30 min (operating hours). P2 = data fix needed (contact, forms, batch change): 4 business hours. P3 = informational (duplicate collapsed, existing booking).

## Multi-code cases
All codes are listed; the **primary** code (ranked in `CODE_RANK`) sets owner/priority. Example 84909: AMOUNT_MISMATCH (P1, Finance Ops) + PARTIAL_PAYMENT. 84906: ORPHANED_INVOICE (escalated to Ops Executive after 12 h) + MISSING_FACULTY_FORM.

## Current open queue (official sample)
| Owner | Open | Cases |
|---|---|---|
| Finance Ops | 2 (2 x P1) | 84909, 84911 |
| Scheduling Ops | 1 (P1) | 84905 |
| Ops Executive | 4 | 84906, 84912, 84913, form 3313 |
| Ops Manager | 1 | 84907 |
| Parent Success | 1 | 84904 |
| Teacher | 1 | 84910 |

Plus one non-exception SLA item: booking 5502 (validated, unscheduled 49 h) -> Scheduling Ops, P1 (`booking_ready.csv`).

## AI role
LLM may classify free-text remarks (e.g. "Offered 20% retention scholarship discount" -> discount) and polish drafts. It cannot change a decision, amount, owner or reason code. Prompts: `prompts/`.
