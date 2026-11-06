# workflows_or_scripts

| File | Purpose | Status |
|---|---|---|
| `run_all.sh` | Reproduces tests, results, docs, figures and the PDF | Used |
| `generate_docs.py` | Writes data-derived docs from results + policy table | Used |
| `check_n8n.py` | Imports + executes the n8n flow locally and checks per-node results | Used (needs `npm install n8n`) |
| `audit_claims.py` | Checks PDF claims against raw data and results | Used |
| `make_figures.py` / `build_report.py` | Charts, diagrams, PDF case report | Used |
| `n8n_renewal_reconciliation.json` | Draft n8n flow: 5-minute schedule -> run engine -> read exceptions -> P1 branch | **Imports and executes in n8n 2.35.7 (`check_n8n.py`, manual-trigger variant). Schedule trigger never fired; notification nodes are placeholders** |
