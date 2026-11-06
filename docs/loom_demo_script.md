# Loom demo script (target 2 min 40 s, optional deliverable)

Have ready: terminal in the repo root, browser on the dashboard, the PDF open. Speak plainly; do not read the screen.

| Time | Show | Say |
|---|---|---|
| 0:00-0:20 | PDF page 3 (executive summary) | "Bambinos renewals pass four manual hand-offs. In the official sample, 11 of 13 invoices are paid but only one has a scheduled class, and five paid renewals have waited over 24 hours." |
| 0:20-0:45 | Terminal: `python -m src.main --input data/raw --output results` | "One command reads the five official CSVs and decides every case. Thirteen invoices: two auto-approved, one ready to schedule, one already done, nine exceptions, plus one orphan form." |
| 0:45-1:15 | `results/auto_approved.csv`, then `flagged_exceptions.csv` | "Only 84903 and 84908 are auto-approved: paid, ids match, amount equals the fee, same active batch with a free seat, no booking yet. Everything else has a reason code and an owner. For example 84913 was paid but the teacher typed invoice 84931, so the engine hints at the match but never approves on it." |
| 1:15-1:35 | Run the command again | "Run it twice and nothing changes: zero new executions, three skipped. Existing bookings are never recreated." |
| 1:35-2:00 | Dashboard: `streamlit run dashboard/app.py`; filter Priority = P1 | "The Ops Head sees the queue by owner and priority. Filtering to P1 shows the three payment and capacity cases." |
| 2:00-2:25 | PDF page 10 (what-if chart) | "The biggest finding: for same-batch renewals the teacher form adds nothing the invoice doesn't already hold. A simulation without it moves auto-approvals from 2 to 5 of 13. That is a simulation on a small sample, not a result." |
| 2:25-2:40 | PDF page 18 | "What I have not done: no live payment, WhatsApp or database connection, and the n8n flow only ran locally with a manual trigger. I need five decisions from Ops, starting with whether the batch seat count already includes the renewing student." |

Do not claim: production integrations, live LLM use, or real savings (the hours figure is an assumption-based model).
