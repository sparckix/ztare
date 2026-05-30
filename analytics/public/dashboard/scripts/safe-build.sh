#!/usr/bin/env bash
# safe-build.sh — the ONLY sanctioned publish path for the dashboard.
# Spec: research_areas/private/.../dashboard_publish_safety_spec_2026_05_17.md
# (adversary-cleared with M1-M4). Fail-closed: any leak ⇒ exit 1, no
# deployable produced. `npm run build` maps here; `build:dev` is the
# raw, UNSAFE vite build (dev only).
set -euo pipefail
cd "$(dirname "$0")/.."                       # dashboard dir
DASH="$(pwd)"

echo "[safe-build] 1/6 refresh-data (stage pipeline JSON)"
bash scripts/refresh-data.sh >/dev/null

echo "[safe-build] 2/6 drop stale compiled views (avoid stale primer import)"
find src -name '*.js' -newer /dev/null -delete 2>/dev/null || true
rm -f src/data/_taste_context_primer.md public/data/_taste_context_primer.md

echo "[safe-build] 3a/6 public-scope the graph (drop private/internal nodes)"
python3 - "$DASH" <<'PY'
import json, sys, pathlib
dash = pathlib.Path(sys.argv[1])
# DENY prefixes: nodes whose id sits in a private/internal tree never
# ship to the public dashboard (kills the M3a structure-disclosure
# residual — projects/ workspace, private seams, docs/internal, …).
DENY = ("research_areas/private", "docs/internal", "projects/",
        "analytics/public/gnn", "/_archive/", ".pre_audit")
def private(nid):
    s = str(nid)
    return any(d in s for d in DENY)
for rel in ("src/data/reference_graph.json", "public/data/reference_graph.json"):
    p = dash / rel
    if not p.exists(): continue
    g = json.loads(p.read_text())
    nodes = g.get("nodes", [])
    keep_ids, dropped = set(), 0
    new_nodes = []
    for n in nodes:
        nid = n.get("id") if isinstance(n, dict) else n
        if private(nid): dropped += 1; continue
        keep_ids.add(nid); new_nodes.append(n)
    g["nodes"] = new_nodes
    for ek in ("edges", "links"):
        if ek in g:
            g[ek] = [e for e in g[ek]
                     if e.get("source", e.get("from")) in keep_ids
                     and e.get("target", e.get("to")) in keep_ids]
    p.write_text(json.dumps(g, ensure_ascii=False))
    print(f"  {rel}: dropped {dropped} private/internal node(s), "
          f"kept {len(new_nodes)}")

# Collapse private project paths in ALL staged JSON → one token. The
# public dashboard's value is the aggregate story (volume/taste/
# compounding by week/kind), NOT private project identities.
import re as _re
PROJ = _re.compile(r"projects/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.\-]+)*")
def _collapse(o):
    if isinstance(o, str): return PROJ.sub("projects/[internal]", o)
    if isinstance(o, list): return [_collapse(x) for x in o]
    if isinstance(o, dict): return {_collapse(k): _collapse(v) for k, v in o.items()}
    return o
cn = 0
for d in ("src/data", "public/data"):
    base = dash / d
    if not base.exists(): continue
    for p in base.rglob("*.json"):
        try: data = json.loads(p.read_text())
        except Exception: continue
        c = _collapse(data)
        if c != data: p.write_text(json.dumps(c, ensure_ascii=False)); cn += 1
print(f"  collapsed project paths in {cn} json file(s)")
PY

echo "[safe-build] 3/6 sanitize staged data (reuse adversary-hardened publish_mask — single source of truth)"
python3 - "$DASH" <<'PY'
import sys, pathlib
dash = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(dash.parents[2] / "scripts/private"))
import publish_mask as pm          # canonical, adversary-cleared, dogfooded
pm.dogfood()                       # gate: refuse if masker can't prove itself
n = 0
for d in ("src/data", "public/data"):
    base = dash / d
    if not base.exists(): continue
    for p in list(base.rglob("*.json")) + list(base.rglob("*.md")):
        ok, res = pm.process(p)
        if ok is None:
            print(f"FATAL: {res} — fail-closed"); sys.exit(1)
        if ok: p.write_text(res, encoding="utf-8"); n += 1
print(f"  publish_mask sanitized {n} file(s) (byte-stable textual)")
PY

echo "[safe-build] 4/6 tsc + vite build"
node_modules/.bin/tsc >/dev/null
node_modules/.bin/vite build >/dev/null 2>&1

echo "[safe-build] 5/6 strip dist → single deployable (index.html only)"
find dist -mindepth 1 -not -name index.html -delete 2>/dev/null || true
FILES="$(find dist -type f)"
if [ "$FILES" != "dist/index.html" ]; then
  echo "FATAL: dist contains more than index.html:"; echo "$FILES"; exit 1
fi

echo "[safe-build] 6/6 fail-closed leak assertion (scan EVERY dist file)"
FORBID='REDACTED_USER|research_areas/private|ztare-research-co|projects/[a-z][a-z0-9_-]{2,}|sk-ant-[A-Za-z0-9]|sk-openai-[A-Za-z0-9]|BEGIN [A-Z ]*PRIVATE KEY|ANTHROPIC_API_KEY["'"'"' :=]+[A-Za-z0-9]|OPENAI_API_KEY["'"'"' :=]+[A-Za-z0-9]'
LEAK=0
while IFS= read -r f; do
  if grep -aoE "$FORBID" "$f" | sort -u | grep -q .; then
    echo "LEAK in $f:"; grep -aoE "$FORBID" "$f" | sort | uniq -c
    LEAK=1
  fi
done < <(find dist -type f)
if [ "$LEAK" -ne 0 ]; then
  echo "FATAL: forbidden tokens in deployable — publish BLOCKED."; exit 1
fi

# M3a — prose tripwire is a DECLARED NON-CONTROL, not a mitigation.
echo
echo "================ PUBLISH-SAFETY: path/secret leak = CLEAN ================"
echo "NON-MECHANIZED RESIDUAL (spec M3a): path-masking does NOT catch private"
echo "PROSE inlined from private seams (e.g. graph_sowhat operational metrics)."
echo "Deploy is authorized ONLY after a human confirms the inlined narrative"
echo "is public-appropriate. This script does NOT grant that authorization."
echo "========================================================================"
echo "[safe-build] OK — dist/index.html is path/secret-clean (single file)."
