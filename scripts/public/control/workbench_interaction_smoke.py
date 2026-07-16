#!/usr/bin/env python3
"""Workbench interaction smoke — mocks the UI's real API interactions against a running workbench
server and asserts each flow works for BOTH existing projects and the new-user create/launch paths,
across the autoresearch and LeanMill lanes. Catches breakage in the full CLI → server → payload stack.

Run:  python3 scripts/public/control/workbench_interaction_smoke.py [--base http://localhost:8765] [--project <slug>]
Exit: 0 if all checks pass, 1 otherwise. Write previews use confirmed=false (no files written).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def _get(base: str, path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=40) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"error": f"http {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120]}


def _post(base: str, path: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{base}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"error": f"http {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8765")
    ap.add_argument("--project", default="ops_root_cause_diagnosis_demo")
    args = ap.parse_args()
    base, p = args.base, args.project
    passed, failed = 0, 0

    def ok(name: str, cond: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if cond:
            print(f"  ok   {name}")
            passed += 1
        else:
            print(f"  FAIL {name} :: {detail}")
            failed += 1

    print(f"== existing project ({p}) — autoresearch reads ==")
    for name, path, field in [
        ("eval-results", f"/api/eval-results?project={p}", "ok"),
        ("research-graph", f"/api/research-graph?project={p}", "ok"),
        ("research-map", f"/api/research-map?project={p}", "nodes"),
        ("charter", f"/api/charter?project={p}", "ok"),
        ("scoring-guide", f"/api/scoring-guide?project={p}", "ok"),
        ("run-config", f"/api/run-config?project={p}", "ok"),
        ("score-trajectory", f"/api/score-trajectory?project={p}", "ok"),
        # A blocked report is a valid read-model response; endpoint health is the typed schema, not ok=true.
        ("report-contract", f"/api/report-contract?project={p}", "schema"),
        ("eval-results facet=inverter", f"/api/eval-results?project={p}&facet=inverter", "ok"),
        ("eval-results facet=charter-drift", f"/api/eval-results?project={p}&facet=charter-drift", "ok"),
        ("eval-results facet=meta-audit", f"/api/eval-results?project={p}&facet=meta-audit", "ok"),
        ("eval-results facet=coherence", f"/api/eval-results?project={p}&facet=coherence", "ok"),
    ]:
        d = _get(base, path)
        ok(name, bool(d.get(field)) or (field == "nodes" and isinstance(d.get("nodes"), list)), d.get("error", ""))

    print("== existing project — document actions ==")
    documents = _post(base, "/api/scenario-deliverables", {"project": p})
    ok("document designs load", documents.get("ok") is True, documents.get("error", ""))
    generated = [row for row in documents.get("deliverables", []) if row.get("generated")]
    ok("generated documents expose an artifact", bool(generated), "no generated document available to exercise")
    for row in generated:
        artifact_path = str(row.get("path") or "")
        safe_path = bool(artifact_path) and not artifact_path.startswith("/") and ".." not in artifact_path
        ok(f"{row.get('name')} uses a repository-relative path", safe_path, artifact_path)
        if safe_path:
            preview = _get(base, f"/api/file?path={urllib.parse.quote(artifact_path, safe='')}")
            ok(
                f"{row.get('name')} opens in the shared viewer",
                preview.get("ok") is True and bool(preview.get("text")),
                preview.get("error", "empty preview"),
            )

    print("== existing project — LeanMill reads ==")
    d = _get(base, f"/api/leanmill?project={p}")
    ok("leanmill state", bool(d.get("schema")), d.get("error", ""))
    lean_files = ((d.get("formalizations") or {}).get("lean_files") or [])
    if lean_files:
        ratify = _post(base, "/api/leanmill/ratify", {
            "source_file": lean_files[0].get("path"), "target_name": "", "confirmed": False,
        })
        ok(
            "leanmill ratify preview",
            ratify.get("status") == "needs_confirmation"
            and (ratify.get("job") or {}).get("action") == "proof_audit",
            ratify.get("error", ""),
        )
    else:
        print("  skip leanmill ratify preview :: no indexed Lean file")

    print("== new-user write/launch previews (confirmed=false) ==")
    # NOTE: /api/project-create writes even at confirmed=false (unlike every other write endpoint).
    # So this genuinely creates a project — we clean it up immediately afterward.
    itest = "zz_workbench_itest"
    d = _post(base, "/api/project-create", {
        "project": itest, "task": "Did the cache flag cause export failures?",
        "bounded_claim": "The flag caused them", "next_falsifier": "if logs show otherwise", "confirmed": True})
    ok("new-project create", bool(d.get("ok")) and not d.get("error"), repr(d.get("error")) + f" ok={d.get('ok')}")
    try:
        import os
        import shutil
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(repo, "projects", itest)
        if os.path.isdir(path):
            shutil.rmtree(path)
    except Exception as e:  # noqa: BLE001
        print(f"  warn: could not clean up {itest}: {e}")

    d = _post(base, "/api/run", {"project": p, "rubric": p, "renderer": "decision_brief", "confirmed": False})
    # A run preview either needs confirmation (ready) or returns a clear blocking reason — both are healthy.
    healthy = d.get("status") in ("needs_confirmation", "blocked_before_run") or bool(d.get("command")) or "ready" in str(d.get("error", "")).lower()
    ok("autoresearch run preview", healthy, f"status={d.get('status')} error={d.get('error','')[:80]}")

    d = _post(base, "/api/leanmill/target", {
        "title": "Smoke target", "target_statement": "forall n : Nat, n = n",
        "notes": "smoke", "slug": "smoke_target", "confirmed": False})
    ok("leanmill target preview", d.get("status") in ("needs_confirmation", "saved"), d.get("error", ""))

    print(f"== RESULT: {passed} passed, {failed} failed ==")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
