# Bambinos.live - Renewal -> Class Scheduling automation (AI Program Manager, Operations)

Case report: [`report/Bambinos_AI_Program_Manager_Operations_Case_Study.pdf`](report/Bambinos_AI_Program_Manager_Operations_Case_Study.pdf) (19 pages).

## Business problem
Renewals pass four manual hand-offs (invoice -> teacher form -> booking request -> class schedule). In the official sample, 11 of 13 invoices are paid but only 1 has a scheduled class; 5 paid invoices have waited more than 24 hours; 3 paid invoices have no teacher form; 2 of 4 Ops-approved forms could not be booked.

## Solution
A deterministic Python reconciliation engine auto-approves **only** provably clean renewals, gives every other case reason codes and a named owner, drafts follow-ups, keeps an audit trail and never creates a booking twice. AI is limited to wording and remark classification and has no authority over decisions.

```
payment verify -> invoice reconcile -> identity -> form (optional if same batch) -> eligibility
 -> capacity -> conflicts -> decision:  CLEAN -> auto-approve -> booking once -> schedule -> parent confirm
                                        EXCEPTION -> owner queue -> fix data -> re-run engine
```
Diagrams: `docs/workflow_diagram.mmd`, `docs/system_architecture.md`, PDF figures 3-4.

## Status (read this first)
| Built and executed | Draft / design only (NOT connected or tested) |
|---|---|
| Engine (`src/`), 44 tests, outputs in `results/`, Streamlit dashboard (tested headless and in a real browser), docs, SOP, PDF | n8n flow (`workflows_or_scripts/n8n_renewal_reconciliation.json`): **tested** = imports + executes locally in n8n 2.35.7 with a manual trigger, engine runs, P1 routing correct; **not tested** = schedule trigger, production paths, any notification (nodes are placeholders), payment webhooks, WhatsApp API, production DB, live LLM calls |

Tested with Python 3.12.3; pandas 2.2.3 and 3.0.6 (44/44 tests on both), streamlit 1.66, plotly 7.1, matplotlib 3.11, reportlab 5.0.

## Install and run
```bash
python -m pip install -r requirements.txt
# 1. get the official CSVs into data/raw/ (see "Data" below)
python -m src.main --input data/raw --output results          # one command; run twice to see idempotency
streamlit run dashboard/app.py                                 # dashboard
python -m pytest                                               # tests
bash workflows_or_scripts/run_all.sh                           # everything incl. docs and PDF
```
Options: `--as-of "2026-11-03 18:00:00"`, `--assume-same-batch-seat-held` (assumption A1), `--whatif-invoice-first` (SIMULATION), `--use-llm` (needs `ANTHROPIC_API_KEY`, see `.env.example`; not tested live).

## Data
Five official CSVs from `github.com/bambinoslive/AI-PM-hiring-take-home-assignments/ops/data`: `1_invoices`, `2_faculty_form_unapproved`, `3_booking_requests`, `4_class_schedule_bookings`, `reference_active_batches_and_students`. The official README limits these assets to shortlisted candidates, so **raw files are git-ignored**; copy them into `data/raw/` yourself. Originals are never modified (SHA-256 checked in tests).

## Reconciliation rules (all audited per case)
Payment verified (Paid + gateway id + paid_at) | invoice arithmetic and link | duplicate invoice | exact invoice-id form linkage (fuzzy matches are hints only) | duplicate forms (identical payload collapsed, otherwise blocking) | student/user id identity | teacher and course | parent contact (masked compare) | amount vs form and standard fee, unapproved discount | required fields | batch active and same-batch consistency | capacity | slot vs batch | timeline | existing booking/schedule | session conflicts | decision. Any blocking code, unknown state or missing field means EXCEPTION.

## Reason codes
`PAYMENT_NOT_VERIFIED INVOICE_NOT_FOUND ORPHANED_INVOICE MISSING_FACULTY_FORM DUPLICATE_INVOICE DUPLICATE_FACULTY_FORM AMOUNT_MISMATCH STUDENT_ID_MISMATCH PARENT_CONTACT_MISMATCH TEACHER_ID_MISMATCH COURSE_MISMATCH BATCH_INACTIVE BATCH_FULL SCHEDULING_CONFLICT BOOKING_ALREADY_EXISTS SCHEDULE_ALREADY_EXISTS PARTIAL_PAYMENT MISSING_REQUIRED_FIELD INVALID_REFERENCE MANUAL_REVIEW_REQUIRED` plus `DISCOUNT_REQUIRES_APPROVAL` and `TIMESTAMP_ANOMALY` (added). Owner, priority and SLA per code: `docs/decision_matrix.md`.

## Sample output (official data, as of 2026-11-03 18:00)
| Decision | Invoices |
|---|---|
| Auto-approved | 2 (84903, 84908) |
| Ready: schedule existing booking | 1 (84902, waiting 49 h) |
| Already processed | 1 (84901) |
| Exceptions | 9 invoices + 1 orphan form (3313) |

Exception owners (proposed): Ops Executive 4, Finance Ops 2 (both P1), Scheduling Ops 1 (P1), Ops Manager 1, Parent Success 1, Teacher 1. Outputs: `auto_approved.csv`, `flagged_exceptions.csv`, `follow_up_messages.csv` (23 drafts, none sent), `booking_ready.csv`, `reconciliation_summary.json`, `audit_log.csv`, `exceptions_by_owner.csv`, plus `case_decisions.csv`, `operational_metrics.json`, `kpi_table.csv`, `data_profile.json`, `root_cause_analysis.csv`.

## Idempotency
Deterministic key per decision; ledger `results/processing_state.json` (simulated execution state). Run 1: 3 simulated executions; run 2: 0 new, 3 skipped; outputs byte-identical (tested). An existing booking is never recreated.

## Known limitations
13-row sample (rates illustrate method); masked identifiers; assumption A1 (seat counting) unvalidated and off by default; single timezone assumed; weekend behaviour untestable (data spans Sun-Tue); owners/SLAs are proposals; what-if numbers are a simulation; dashboard tested one filter at a time (combined filters, mobile layout untested); n8n: only the manual-trigger CLI variant executed (no schedule/webhook trigger, no notifications); LLM path untested.

## Security
No secrets in the repo (`.env.example` only). Drafts omit amounts, gateway ids and child names. Raw data excluded from git. Derived outputs hold masked values: share privately or confirm with Bambinos. No license file is included (data terms unclear).

## Future production integration
Signed gateway webhooks -> n8n -> engine over HTTP -> PostgreSQL with a unique idempotency column -> booking/schedule API -> WhatsApp Business templates (human-approved first) -> Metabase. Rollout: `docs/30_60_90_day_plan.md`.

## Layout
`src/` engine | `tests/` | `prompts/` (6 prompts) | `results/` | `dashboard/` | `docs/` (audit, dictionary, KPIs/SLAs, architecture, matrix, SOP, ownership, plan, risks, interview guide, self-assessment) | `report/` | `workflows_or_scripts/` | `IMPLEMENTATION_LOG.md`
