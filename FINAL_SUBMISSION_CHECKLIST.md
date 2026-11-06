# Final submission checklist

Audit date: 2026-11-06. Every "Verified" row was executed during the audit; evidence is in the right-hand column.

## A. Compulsory deliverables (official checklist)
| Item | Status | Evidence |
|---|---|---|
| Case report PDF | Verified | `report/Bambinos_AI_Program_Manager_Operations_Case_Study.pdf`, 19 pages, no blank pages, all pages viewed, 40+ factual claims checked against data by `workflows_or_scripts/audit_claims.py` (0 failures) |
| Report content: problem audit, rubric/taxonomy, workflow architecture, SOP, metrics, 30-60-90 | Verified | Sections 4-6, 7, 8 + Appendix A (taxonomy), 13, 14 |
| GitHub repo contents: README, prompts/, results/, workflows_or_scripts/, PDF | Verified present | `git ls-files` |
| Repo published to GitHub | **PENDING - you** | No identity/credentials/authorization; see section E |
| Google form submitted | **PENDING - you** | https://forms.gle/gu5gzySRHTSd5Uou9 |

## B. Verification results
| Check | Result |
|---|---|
| Tests | **44 passed, 0 failed, 0 skipped** on a fresh copy of tracked files; also 44/44 on pandas 2.2.3 (declared lower bound) and 3.0.6 |
| Clean-state engine run | 13 invoices: 2 AUTO_APPROVE, 1 AWAITING_SCHEDULING, 1 ALREADY_PROCESSED, 9 EXCEPTION, plus 1 orphan-form exception (3313) |
| Dataset completeness | The 13 invoices ARE the complete official dataset: upstream repo is one commit with exactly 5 data files, all byte-identical to the local copies (13/12/4/2/13 rows) |
| Raw inputs unmodified | SHA-256 identical before and after every run |
| Auto-approved records (84903, 84908) | Independently audited by hand from raw CSVs: 11/11 checks each; reverse check found no clean invoice missed |
| Exceptions | Independently re-derived reason codes match the engine for all 9 invoices + orphan form. Caveat: same author wrote engine and checker, so this verifies the implementation, not the business rules |
| Idempotency | Runs 1, 2 and a fresh-state run give byte-identical outputs (except `run_report.json`, which records new vs skipped by design); ledger holds 3 unique actions |
| Dashboard | Live Streamlit server health OK; real-browser screenshot (Chromium); all 7 filters tested individually against independently computed values (pass); two defects found and fixed (pie colours, clipped title) |
| PDF vs data | 0 mismatches; two imprecise statements corrected ("5 min" -> 5 min 12 s; "16 rules" -> 16 checks + decision) |
| n8n | **Tested:** imports into n8n 2.35.7; executes end to end (manual-trigger variant), engine runs, P1 branch routes exactly 84905/84909/84911 and 7 others. **Not tested:** schedule trigger, webhook trigger, any notification (both nodes are NoOp placeholders). Evidence: `docs/n8n_test_evidence.md`, reproduce with `check_n8n.py` |
| Security | No secrets, no raw CSVs, no unmasked phone/email in tracked files; `.env` ignored; only `.env.example` |
| Requirements | Cover all third-party imports; `pip check` clean |

## C. Defects found and fixed during this audit
1. Audit script used `is None` on pandas NaN (my checker's bug, not the engine's) - fixed.
2. Dashboard pie chart colours were semantically misleading (and later ignored my map) - fixed with `color=` and `theme=None`; verified in a browser.
3. Dashboard chart title clipped - fixed.
4. `run_all.sh` aborted on pip under PEP 668 - now installs only when missing.
5. New n8n check script was auto-collected by pytest and broke the suite - renamed, `pytest.ini` pins `tests/`.
6. PDF/docs statements outdated or imprecise (screenshot, n8n, 5 min, 16 rules, data-sharing wording) - corrected.
7. `results/whatif/` was git-ignored although docs reference it - now tracked.

## D. Not done / limits (stated honestly)
- No live LLM call (code path exists; tested only without a key). No payment-gateway, WhatsApp or production-DB integration.
- n8n: local manual-trigger run only.
- Weekend/holiday behaviour untestable (data spans Sun-Tue). Dashboard combined filters and mobile layout untested.
- 13-row sample: percentages illustrate method. Owners, SLAs, savings are proposals or assumption-based.
- Optional Loom video not recorded; script in `docs/loom_demo_script.md`.
- No git commit exists (no git identity configured; I did not invent one). A `GITHUB_TOKEN` variable exists in the sandbox but was NOT used: its owner and scope are unverified and you have not authorised a target.

## E. Your actions
1. Review `git status`, then commit and publish (private recommended: the official README limits these assets to shortlisted candidates and `results/` holds masked data derived from them):
```bash
cd bambinos-renewal-automation
git config user.name "YOUR NAME"; git config user.email "YOUR@EMAIL"
git add -A && git status            # confirm NO data/raw/*.csv is listed
git commit -m "Bambinos AI PM (Operations) assessment: renewal reconciliation prototype"
# Option 1 - GitHub CLI (after `gh auth login`):
gh repo create bambinos-renewal-automation --private --source=. --remote=origin --push
# Option 2 - website: create an empty PRIVATE repo, then:
git remote add origin https://github.com/<YOU>/bambinos-renewal-automation.git
git branch -M main && git push -u origin main
```
2. Add reviewers as collaborators (or confirm with Bambinos if public is acceptable).
3. Optionally record the Loom using `docs/loom_demo_script.md`.
4. Submit the repo link and the PDF at the Google form.
5. Answer the five open policy questions (seat counting, instalments, discount approver, optional form, owner names) before the live review.
