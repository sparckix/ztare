#!/usr/bin/env python3
"""v32_route_c_replay_batch.py — strict replay of curated rows through Route C.

For each curated row (proven Mathlib theorem):
  1. Read the Mathlib source file
  2. Extract the theorem's full signature (decl line(s) up to `:=`)
  3. Synthesize a row file: `import Mathlib\nimport Hammer\n\n<sig> := by sorry`
  4. Run route_c_layer_2c_dispatch on it (LLM must RE-DERIVE without gold tactic)
  5. Record: closed? / gap report / which round / compile error

This is the v2.1+ strict-replay methodology applied via the integrated
Route C pipeline (reused lean_fast_compile + archetype classifier +
semantic-masking LLM + termination guard).

Output: analytics/public/leanmill/results/v32_route_c_replay_results.json,
with per-row scratch files under $ZTARE_V32_TMPDIR or the platform temp dir.
"""
from __future__ import annotations
import json, os, re, sys, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TMP = Path(os.environ.get("ZTARE_V32_TMPDIR", tempfile.gettempdir()))


def extract_signature(source_path: str, theorem_name: str) -> str | None:
    """Extract `theorem <name> ... :` (signature, no proof) from a Mathlib file."""
    p = Path(source_path)
    if not p.exists():
        return None
    text = p.read_text()
    lines = text.splitlines()
    decl_re = re.compile(
        rf"^\s*(?:@\[[^\]]*\]\s*)?(?:theorem|lemma)\s+{re.escape(theorem_name)}(?=\s|\(|\{{|:|$)"
    )
    start = None
    for i, ln in enumerate(lines):
        if decl_re.search(ln):
            start = i
            break
    if start is None:
        return None
    # Collect signature lines until top-level `:=`
    sig_lines = []
    depth = 0
    found_assign = False
    for i in range(start, min(len(lines), start + 40)):
        ln = lines[i]
        # crude bracket-depth-aware := scan
        j = 0
        while j < len(ln):
            ch = ln[j]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            if depth == 0 and ln[j:j+2] == ":=":
                sig_lines.append(ln[:j].rstrip())
                found_assign = True
                break
            j += 1
        if found_assign:
            break
        sig_lines.append(ln)
    if not found_assign:
        return None
    sig = "\n".join(sig_lines).strip()
    # Drop leading attribute [...]
    sig = re.sub(r"^@\[[^\]]*\]\s*", "", sig)
    return sig


def main():
    tmp_root = DEFAULT_TMP
    tmp_root.mkdir(parents=True, exist_ok=True)
    curated_path = Path(os.environ.get("ZTARE_V32_CURATED_ROWS", tmp_root / "v32_curated_test_rows.json"))
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    rows = [r for r in curated["rows"] if not r.get("quarantined") and r.get("resolved_path")]
    print(f"# v32 Route C strict replay — {len(rows)} curated rows\n")

    results = []
    for r in rows:
        rid = r["row_id"]
        thm = r["theorem"]
        src = r["resolved_path"]
        print(f"--- {rid}: {thm} ---")
        sig = extract_signature(src, thm)
        if sig is None:
            print("  SIGNATURE EXTRACTION FAILED")
            results.append({"row_id": rid, "theorem": thm, "status": "sig_extract_failed"})
            continue
        # Synthesize row file
        row_text = f"-- v32 strict replay: {thm} (row_id {rid})\n-- source: {r['source_file']}\nimport Mathlib\nimport Hammer\n\n{sig} := by sorry\n"
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=f"_{rid}.lean", delete=False, dir=tmp_root)
        tmp.write(row_text)
        tmp.close()
        # Run Route C dispatch (subprocess to isolate; 2 rounds, compile on)
        out_json = str(tmp_root / f"v32_replay_{rid}.json")
        proc = None
        # Skip rows whose per-row json already exists (resume support)
        if Path(out_json).exists():
            print(f"  (resume) {out_json} exists — reusing")
        else:
            try:
                proc = subprocess.run(
                    ["python3", str(ROOT / "scripts/public/control/route_c_layer_2c_dispatch.py"),
                     "--row", tmp.name, "--max-rounds", "2", "--model", "gpt-4.1-mini",
                     "--compile", "--out", out_json],
                    cwd=str(ROOT), capture_output=True, text=True, timeout=500,
                )
            except subprocess.TimeoutExpired:
                results.append({"row_id": rid, "theorem": thm, "status": "dispatch_timeout_500s"})
                print("  DISPATCH TIMEOUT (500s) — continuing")
                continue
        try:
            res = json.load(open(out_json))
            verdict = res.get("closure_verdict")
            compiled = res.get("compiled_any")
            op = res.get("operation_type_chosen")
            rounds_info = []
            for rd in res.get("rounds", []):
                lc = rd.get("lean_compile", {})
                rounds_info.append({
                    "round": rd.get("round"),
                    "lemma": (rd.get("candidate", {}).get("lemma_name") or "?"),
                    "compiled": lc.get("compiled"),
                    "elapsed": lc.get("elapsed"),
                    "error_head": (lc.get("error_tail", "") or "")[:120],
                })
            results.append({
                "row_id": rid, "theorem": thm, "source_file": r["source_file"],
                "status": "ran", "verdict": verdict, "compiled_any": compiled,
                "operation_type": op, "rounds": rounds_info,
            })
            mark = "CLOSED" if compiled else "GAP_REPORT"
            print(f"  {mark} | op={op} | rounds={len(rounds_info)}")
        except Exception as e:
            results.append({"row_id": rid, "theorem": thm, "status": f"dispatch_error: {e}",
                            "stderr_tail": proc.stderr[-300:] if proc is not None else ""})
            print(f"  DISPATCH ERROR: {e}")

    n_closed = sum(1 for r in results if r.get("compiled_any"))
    n_gap = sum(1 for r in results if r.get("status") == "ran" and not r.get("compiled_any"))
    n_fail = sum(1 for r in results if r.get("status") != "ran")

    print("\n## Aggregate")
    print(f"  Closed (LLM re-derived without gold): {n_closed}/{len(rows)}")
    print(f"  Gap report (honest open): {n_gap}/{len(rows)}")
    print(f"  Harness/extraction failures: {n_fail}/{len(rows)}")

    out = {
        "n_rows": len(rows),
        "n_closed": n_closed,
        "n_gap_report": n_gap,
        "n_harness_fail": n_fail,
        "model": "gpt-4.1-mini",
        "methodology": "v2.1+ strict replay via integrated Route C pipeline (reused lean_fast_compile + archetype classifier + semantic masking + termination guard)",
        "results": results,
    }
    out_path = ROOT / "analytics/public/leanmill/results/v32_route_c_replay_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
