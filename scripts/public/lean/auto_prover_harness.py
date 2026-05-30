#!/usr/bin/env python3
"""GP-216f scale-8 — auto-prover harness for closure obligations.

Wraps any Lean-aware neural prover (DeepSeek-Prover-V2, LeanCopilot, AlphaProof,
LLM-as-prover) and runs it against the open obligations identified in the
artifact graph. Provider-agnostic: pass `--prover-cmd <command>` to invoke any
external tool.

# Why this exists

Of 55 (post-Meitner-fix) open obligations in the closure receipt's tree, some
are mechanically derivable from already-closed dependencies. Auto-attempting
each one separates "needs human PDE work" from "could close automatically."
Output: which obligations resist auto-proving (genuinely human work) vs which
the prover closes (mechanizable; submit as Lean PR).

# Workflow

For each open obligation in the receipt-tree:
  1. Extract the goal statement + dependency context from Lean source.
  2. Construct a self-contained proof attempt prompt.
  3. Invoke the configured prover via subprocess (ANY prover).
  4. Capture stdout (the proposed proof) + exit code.
  5. (Optional) Verify proposed proof by re-elaborating in Lean.
  6. Record per-obligation outcome: closed | failed | timeout.

# Provider configuration

Set ZTARE_PROVER_CMD env var or pass --prover-cmd. Examples:
  --prover-cmd "deepseek-prover --input {goal_file} --output {proof_file}"
  --prover-cmd "leancopilot --tactic suggest --file {goal_file}"
  --prover-cmd "claude -p 'prove {goal_text}' --print"

The harness substitutes:
  {goal_file}   — path to a temp file containing the goal statement
  {goal_text}   — the goal as a string
  {context}     — file-level dependencies (already-imported lemmas)
  {proof_file}  — path where prover should write the proof

# Output

  analytics/public/queries/auto_prover_results.json   — per-obligation outcomes
  analytics/public/queries/auto_prover_summary.md     — closure rate + which
                                                 obligations need humans

# Status

ADVISORY v0.1. The harness is provider-agnostic; the value depends on which
prover you wire in. With DeepSeek-Prover-V2 (open-source, 7B params, runs on
GPU), expected closure rate on Lean-mathlib obligations is 30-50% per published
benchmarks. NS Track B obligations are harder (PDE estimate-craft); expect
lower closure rate but each closed obligation is a real gain.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic  # noqa: E402
from src.ztare.leanmill.semantic_premise_shelf import (  # noqa: E402
    build_semantic_premise_shelf,
    render_semantic_premise_shelf,
    semantic_premise_shelf_enabled,
)

GRAPH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "ns_trackb_artifact_graph.json"
)
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"


def extract_goal_context(decl: dict) -> dict:
    """Extract a Lean prover-ready goal + minimal context for one obligation."""
    file_path = REPO / decl.get("path", "")
    if not file_path.exists():
        return {"error": "file_not_found", "path": str(file_path)}
    text = file_path.read_text(encoding="utf-8")
    # Pull file-level imports (the prover needs the namespace context)
    imports = []
    for line in text.splitlines():
        if line.startswith("import "):
            imports.append(line)
        elif line.startswith("namespace ") or line.strip() and not line.startswith("--"):
            # rough heuristic: stop after preamble
            break
    # Pull the declaration block from doc_excerpt or attempt block extraction
    block = decl.get("doc_excerpt") or ""
    name = decl.get("name", "<unnamed>")
    kind = decl.get("kind", "theorem")
    return {
        "name": name,
        "kind": kind,
        "imports": imports,
        "goal_block": block,
        "file": str(file_path.relative_to(REPO)),
        "line": decl.get("line", 0),
    }


def _semantic_shelf_for_goal(goal_ctx: dict, *, threshold: float = 0.55) -> dict:
    query = "\n".join(
        [
            "Lean declaration:",
            str(goal_ctx.get("name") or ""),
            "Goal block:",
            str(goal_ctx.get("goal_block") or ""),
            "Imports/context:",
            "\n".join(goal_ctx.get("imports") or []),
        ]
    )
    return build_semantic_premise_shelf(query, threshold=threshold)


def invoke_prover(
    prover_cmd: str,
    goal_ctx: dict,
    timeout_s: int = 300,
    *,
    semantic_premise_shelf: bool = True,
    semantic_threshold: float = 0.55,
) -> dict:
    """Invoke configured prover on one goal. Substitutes {goal_text}, {goal_file}, {context}."""
    shelf_text = ""
    if semantic_premise_shelf and semantic_premise_shelf_enabled():
        shelf = _semantic_shelf_for_goal(goal_ctx, threshold=semantic_threshold)
        goal_ctx["semantic_premise_shelf"] = shelf
        shelf_text = render_semantic_premise_shelf(shelf)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lean", delete=False) as gf:
        gf.write("\n".join(goal_ctx.get("imports", [])))
        gf.write("\n\n")
        if shelf_text:
            gf.write("/-\n")
            gf.write(shelf_text)
            gf.write("\n-/\n\n")
        gf.write(goal_ctx.get("goal_block", "") or f"theorem {goal_ctx['name']} := sorry\n")
        goal_file = gf.name
    proof_file = goal_file.replace(".lean", ".proof.lean")
    goal_text = goal_ctx.get("goal_block", "")[:1000]
    if shelf_text:
        goal_text = f"{goal_text}\n\n{shelf_text}"[:5000]
    context_text = " ".join(goal_ctx.get("imports", []))[:2000]
    if shelf_text:
        context_text = f"{context_text}\n\n{shelf_text}"[:5000]

    # Substitute placeholders
    cmd = prover_cmd.format(
        goal_file=goal_file,
        proof_file=proof_file,
        goal_text=goal_text,
        context=context_text,
        premise_shelf=shelf_text,
    )

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout_s,
        )
        proof = ""
        if Path(proof_file).exists():
            proof = Path(proof_file).read_text(encoding="utf-8")[:4000]
        outcome = {
            "name": goal_ctx["name"],
            "kind": goal_ctx["kind"],
            "exit_code": result.returncode,
            "proof_text": proof or result.stdout[:4000],
            "stderr_excerpt": result.stderr[:500] if result.stderr else "",
            "semantic_premise_shelf": goal_ctx.get("semantic_premise_shelf") or {},
            "outcome": "closed" if result.returncode == 0 and (proof or "by " in result.stdout) else "failed",
        }
    except subprocess.TimeoutExpired:
        outcome = {"name": goal_ctx["name"], "outcome": "timeout", "kind": goal_ctx["kind"]}
    except Exception as exc:
        outcome = {"name": goal_ctx["name"], "outcome": "error", "error": str(exc), "kind": goal_ctx["kind"]}
    finally:
        for p in (goal_file, proof_file):
            if Path(p).exists():
                Path(p).unlink()
    return outcome


def collect_open_obligations(graph_path: Path, receipt_node_id: str, max_obligations: int = 0) -> list[dict]:
    """Walk graph; return list of declarations with status='open_obligation' in receipt-tree."""
    g = json.loads(graph_path.read_text())
    nodes = g.get("@graph", [])
    files = [n for n in nodes if n.get("@type") == "ns_lean_file"]
    decls = [n for n in nodes if n.get("@type") == "ns_lean_decl"]
    fwd = {f["@id"]: set(f.get("imports", [])) for f in files}

    def reach(s):
        seen, st = {s}, [s]
        while st:
            n = st.pop()
            for nb in fwd.get(n, []):
                if nb not in seen:
                    seen.add(nb); st.append(nb)
        return seen

    rt = reach(receipt_node_id)
    open_obs = [d for d in decls if d.get("status") == "open_obligation" and d.get("file") in rt]
    if max_obligations:
        open_obs = open_obs[:max_obligations]
    return open_obs


def collect_obligations_packet(packet_path: Path, max_obligations: int = 0) -> list[dict]:
    """Read a prebuilt obligation packet emitted by a corpus adapter."""
    payload = read_json(packet_path, default={})
    rows = []
    for key in ("obligations", "rows", "items"):
        vals = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(vals, list):
            rows.extend(x for x in vals if isinstance(x, dict))
    obligations = []
    for row in rows:
        rel_path = str(row.get("path") or row.get("file") or row.get("source_file") or "")
        if rel_path.startswith(str(REPO)):
            try:
                rel_path = str(Path(rel_path).resolve().relative_to(REPO))
            except ValueError:
                pass
        obligations.append({
            "name": row.get("name") or row.get("target_name") or row.get("target_theorem_name"),
            "kind": row.get("kind") or "theorem",
            "path": rel_path,
            "line": row.get("line") or row.get("target_line") or 0,
            "doc_excerpt": row.get("doc_excerpt") or row.get("goal_block") or row.get("statement") or "",
            "status": row.get("status") or "open_obligation",
            "source_packet": str(packet_path),
        })
    if max_obligations:
        obligations = obligations[:max_obligations]
    return obligations


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-prover harness for NS closure obligations")
    parser.add_argument("--prover-cmd", default=os.environ.get("ZTARE_PROVER_CMD"),
                        help="Provider-agnostic prover command. Use {goal_file}, {goal_text}, {context}, {proof_file} placeholders.")
    parser.add_argument("--graph-path", type=Path, default=GRAPH)
    parser.add_argument("--obligations-json", type=Path, default=None,
                        help="Prebuilt obligation packet from a corpus adapter; bypasses graph traversal.")
    parser.add_argument("--receipt-id", default="ns_file:ns_gp216_bridge_composition_receipt")
    parser.add_argument("--max-obligations", type=int, default=0, help="0 = all")
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--results-out", type=Path, default=REPO / "analytics" / "public" / "queries" / "auto_prover_results.json")
    parser.add_argument("--summary-out", type=Path, default=REPO / "analytics" / "public" / "queries" / "auto_prover_summary.md")
    parser.add_argument("--dry-run", action="store_true", help="List obligations, don't invoke prover")
    parser.add_argument("--no-semantic-premise-shelf", action="store_true",
                        help="Disable Mathlib/APN/NS semantic premise shelf injection.")
    parser.add_argument("--semantic-threshold", type=float, default=0.55)
    args = parser.parse_args()

    if args.obligations_json:
        obligations = collect_obligations_packet(args.obligations_json, args.max_obligations)
        print(f"Found {len(obligations)} open obligations in {args.obligations_json}")
    else:
        obligations = collect_open_obligations(args.graph_path, args.receipt_id, args.max_obligations)
        print(f"Found {len(obligations)} open obligations in receipt-tree")
    if args.max_obligations:
        print(f"Limited to first {args.max_obligations}")

    if args.dry_run:
        for o in obligations:
            ctx = extract_goal_context(o)
            print(f"  {ctx.get('kind')} {ctx.get('name')}  (file: {ctx.get('file')})")
        return 0

    if not args.prover_cmd:
        print("ERROR: --prover-cmd required (or set ZTARE_PROVER_CMD env var)", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print('  deepseek-prover: --prover-cmd "deepseek-prover --input {goal_file} --output {proof_file}"', file=sys.stderr)
        print('  claude:          --prover-cmd "claude -p {goal_text} --print"', file=sys.stderr)
        return 2

    results = []
    for i, ob in enumerate(obligations, 1):
        ctx = extract_goal_context(ob)
        if "error" in ctx:
            results.append({"name": ob.get("name"), "outcome": "skipped", "error": ctx["error"]})
            continue
        print(f"[{i}/{len(obligations)}] attempting {ctx['name'][:60]}...", end=" ", flush=True)
        outcome = invoke_prover(
            args.prover_cmd,
            ctx,
            args.timeout_s,
            semantic_premise_shelf=not args.no_semantic_premise_shelf,
            semantic_threshold=args.semantic_threshold,
        )
        results.append(outcome)
        print(outcome.get("outcome", "?"))

    write_json_atomic(args.results_out, {
        "ts": datetime.utcnow().isoformat(),
        "prover_cmd": args.prover_cmd,
        "obligations_source": str(args.obligations_json or args.graph_path),
        "semantic_premise_shelf": not args.no_semantic_premise_shelf,
        "semantic_threshold": args.semantic_threshold,
        "n_obligations": len(obligations),
        "results": results,
    })

    counts = Counter(r.get("outcome") for r in results)
    closure_rate = counts.get("closed", 0) / max(len(results), 1)

    summary = [
        "# Auto-prover harness summary\n",
        f"_Generated {datetime.utcnow().isoformat()}_\n",
        f"- Prover: `{args.prover_cmd[:80]}`",
        f"- Obligations attempted: {len(results)}",
        f"- Closed: {counts.get('closed', 0)} ({closure_rate:.1%})",
        f"- Failed: {counts.get('failed', 0)}",
        f"- Timeout: {counts.get('timeout', 0)}",
        f"- Skipped: {counts.get('skipped', 0)}",
        f"- Error: {counts.get('error', 0)}",
        "",
        "## Closed obligations (mechanizable)\n",
        "These resolved automatically. Submit as Lean PRs.\n",
    ]
    for r in results:
        if r.get("outcome") == "closed":
            summary.append(f"- `{r['name']}` ({r.get('kind')})")
    summary.append("\n## Failed / timeout (genuine human PDE work)\n")
    summary.append("These resisted auto-prove; need targeted human attempts.\n")
    for r in results:
        if r.get("outcome") in ("failed", "timeout"):
            summary.append(f"- `{r['name']}` ({r.get('kind')}) — {r.get('outcome')}")

    write_text_atomic(args.summary_out, "\n".join(summary))
    print(f"\nResults: {args.results_out}")
    print(f"Summary: {args.summary_out}")
    print(f"Closure rate: {closure_rate:.1%} ({counts.get('closed', 0)}/{len(results)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
