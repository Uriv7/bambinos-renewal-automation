#!/usr/bin/env bash
# Reproduce every deliverable from a clean checkout. Needs data/raw/*.csv (see README: how to obtain).
set -euo pipefail
cd "$(dirname "$0")/.."
python -c "import pandas, pytest, streamlit, plotly, matplotlib, reportlab" 2>/dev/null || python -m pip install -q -r requirements.txt
python -m pytest -q
rm -f results/processing_state.json
python -m src.main --input data/raw --output results
python -m src.main --input data/raw --output results          # 2nd run: proves idempotency (0 new executions)
for m in "base:" "a1:--assume-same-batch-seat-held" "invoice_first:--whatif-invoice-first"; do
  n=${m%%:*}; f=${m#*:}; python -m src.main --output "results/whatif/$n" $f --state-file "/tmp/state_$n.json" >/dev/null
done
python workflows_or_scripts/generate_docs.py
python workflows_or_scripts/make_figures.py
python workflows_or_scripts/build_report.py
python workflows_or_scripts/audit_claims.py
