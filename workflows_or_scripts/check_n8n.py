"""Imports and EXECUTES the n8n workflow in a local n8n install and verifies per-node results.
Usage:  python workflows_or_scripts/check_n8n.py [/path/to/dir/with/node_modules/n8n]
Prereq: `npm install n8n` in that dir (Node 20+). Test variant = same nodes, but (1) manual trigger replaces the
5-minute schedule trigger (a one-shot CLI run cannot wait for a schedule), (2) paths point at this repo, and
(3) Execute-Command + file access are enabled via env vars (n8n disables them by default)."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
N8N = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/n8ntest") / "node_modules" / ".bin" / "n8n"
out = Path(tempfile.mkdtemp(prefix="n8n_results_")); home = Path(tempfile.mkdtemp(prefix="n8n_home_")); state = out / "state.json"
env = {**os.environ, "N8N_USER_FOLDER": str(home), "N8N_DIAGNOSTICS_ENABLED": "false", "NODES_EXCLUDE": "[]", "N8N_RESTRICT_FILE_ACCESS_TO": str(out)}
w = json.loads((ROOT / "workflows_or_scripts" / "n8n_renewal_reconciliation.json").read_text())
w["id"], w["active"] = "bambinosAudit", False
old = w["nodes"][0]["name"]; new = "Manual trigger (test)"
w["nodes"][0] = {"parameters": {}, "name": new, "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0]}
w["connections"][new] = w["connections"].pop(old)
for n in w["nodes"]:
    if n["type"] == "n8n-nodes-base.executeCommand":
        n["parameters"]["command"] = f"cd {ROOT} && python3 -m src.main --input data/raw --output {out} --state-file {state}"
    if n["type"] == "n8n-nodes-base.readWriteFile":
        n["parameters"]["fileSelector"] = str(out / "flagged_exceptions.csv")
f = out / "wf.json"; f.write_text(json.dumps(w))
print("n8n version:", subprocess.run([str(N8N), "--version"], capture_output=True, text=True, env=env).stdout.strip().splitlines()[-1])
imp = subprocess.run([str(N8N), "import:workflow", f"--input={f}"], capture_output=True, text=True, env=env, timeout=300)
print("import:", "OK" if "Successfully imported 1 workflow" in imp.stdout else "FAILED\n" + imp.stdout[-500:] + imp.stderr[-500:])
ex = subprocess.run([str(N8N), "execute", "--id=bambinosAudit"], capture_output=True, text=True, env=env, timeout=600)
t = ex.stdout[ex.stdout.index("{"):]; d = json.JSONDecoder().raw_decode(t)[0]
def find(o):
    if isinstance(o, dict):
        if "runData" in o: return o["runData"]
        for v in o.values():
            r = find(v)
            if r: return r
    elif isinstance(o, list):
        for v in o:
            r = find(v)
            if r: return r
rd = find(d); res = {}
print("execution status:", d.get("status"), "| finished:", d.get("finished"))
for node, runs in rd.items():
    items = [len(b or []) for b in runs[0]["data"]["main"]]; res[node] = (runs[0]["executionStatus"], items); print(f"  {node[:64]:64s} {runs[0]['executionStatus']:8s} items/branch={items}")
p1 = [i["json"]["record_id"] for i in rd["P1 exception?"][0]["data"]["main"][0]]
print("P1 branch records:", p1)
ok = d.get("status") == "success" and sorted(p1) == ["CASE-84905", "CASE-84909", "CASE-84911"] and res["Parse CSV"][1] == [10]
print("VERDICT:", "PASS - workflow imports and executes; P1 routing correct" if ok else "FAIL"); sys.exit(0 if ok else 1)
