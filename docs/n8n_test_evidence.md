# n8n test evidence

Reproduce: `npm install n8n` (Node 20+) in any folder, then `python workflows_or_scripts/check_n8n.py <that folder>`.

## Tested (actually executed, n8n 2.35.7, CLI)
| Check | Result |
|---|---|
| `n8n import:workflow` of the shipped JSON | Successfully imported |
| Execution of the flow (test variant) | `status: success` |
| Node 2 runs the real engine (`python -m src.main`) | Outputs and ledger created |
| Parse CSV | 10 items (9 invoices + orphan form 3313) |
| `P1 exception?` IF node | TRUE branch 3 items: CASE-84905, CASE-84909, CASE-84911; FALSE branch 7 items |

## Differences between the shipped file and the executed variant
1. Schedule trigger replaced by a manual trigger (a one-shot CLI run cannot wait for a 5-minute schedule).
2. Paths point at this repo instead of `/opt/bambinos-renewal-automation`.
3. Execute-Command node and file access enabled through environment variables (n8n disables them by default).

## NOT tested / not built
- The 5-minute schedule trigger firing; running inside a long-lived n8n server or UI.
- Any payment webhook trigger or signature verification.
- Both "PLACEHOLDER" nodes are NoOp: **no Slack, WhatsApp, email or sheet integration exists**.
- Shell-command invocation of Python is a prototype shortcut; production should call the engine over HTTP.
