# Implementation log

## Phase 1 - Investigation
Cloned official repo; ops README + 5 CSVs copied to `data/raw/`; SHA-256 recorded before work. Official checklist: PDF (compulsory), GitHub repo with README/prompts/results/workflows_or_scripts (compulsory), Loom (optional). Python 3 + pandas/pytest/streamlit/plotly/reportlab available; network limited to GitHub/PyPI/npm.
Findings: tiny seeded sample; every row is an edge case. Currency INR everywhere. Dates Sun 1 Nov - Tue 3 Nov 2026.

## Phase 2 - Engine
Built `src/` (loader, validators, matching, duplicates, capacity, scheduling, eligibility, exceptions, messages, metrics, audit, CLI).
Verification found and fixed: (a) educator-1125 recurring-slot overlap wrongly blocked 84907/84911 -> made informational; (b) my own misread of a timestamp (no TIMESTAMP_ANOMALY exists in the data - removed from findings); (c) duplicate teacher messages for 84913; missing teacher message for 84909; (d) root-cause table crashed on zero findings (fixed, tested).

## Phase 3 - Tests
44 tests pass: 20 required scenarios + variants, immutability, idempotency, reproducibility, messages, metrics, schema errors, official-data expectations.

## Phase 4 - What-if
Added `--whatif-invoice-first` (SIMULATION). Auto-approvals 2 -> 5 of 13. Assumption A1 flag does not auto-approve 84905 (existing failed booking still needs a human).

## Phase 5 - Dashboard, docs, PDF
Dashboard passes headless AppTest. Docs generated from outputs where possible. PDF 19 pages; visually inspected; fixed cover overlap, self-listing TOC, clipped chart titles, orphaned heading, sparse pages. Added taxonomy appendix after re-reading the official checklist; moved scripts to `workflows_or_scripts/` and added an untested n8n draft.

## Open items
Run n8n flow with a real trigger and real notification channel (CLI execution with manual trigger already passed); live LLM test; validate A1/instalment/discount policy; owner names; 3-month data pull; optional Loom; publish and submit (needs user authorization).
