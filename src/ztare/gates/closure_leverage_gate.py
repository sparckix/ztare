"""G-CLOSURE-LEVERAGE — gate for closure-attempt prioritization (advisory v0.1).

Applies the GP-216/GP-219 vocabulary to the graph-structure scale (8th scale,
GP-216f fractal extension). Mechanizes the operational claim that closure
attempts should target high-leverage open obligations rather than arbitrary
ones.

# Definitions

For a closure attempt with declared `target_obligations` (list of declaration
names) against an artifact graph (projects/ns_millennium_hunt/workspace/queries/ns_trackb_artifact_graph.json
or equivalent), this gate computes:

  leverage(d) = number of receipt-tree declarations whose `uses_decl` list
                contains d's @id, when d is open

Then verifies the attempt's declared targets include at least one of the top-N
highest-leverage open obligations. The economic argument: proving a 27-user
obligation unblocks 27 downstream proofs; proving a 0-user leaf obligation
unblocks nothing further. Without the gate, an attempt can spend effort on
low-leverage targets without that being visible.

Cross-scale alias: this is the graph-scale instantiation of GP-219 proto-op C
(Quantitative Threshold Dichotomy) — every open obligation either exceeds the
top-N leverage threshold OR is a leaf, and the gate enforces that the attempt
addresses at least one of the former.

# Status: ADVISORY v0.1 (2026-05-05)

Ships in advisory mode (returns passed=True with warnings) until 3-5 closure
attempts on real NS Track B work confirm the leverage ranking is meaningful.
Flip to promote-blocking with `enforce_block=True` after validation.

# What this gate verifies (when active)

  M1. Rubric declares `target_obligations`: list of declaration names the
      closure attempt aims to close.
  M2. At least 1 declared target is in the top-N highest-leverage open
      obligations (default N=10).
  M3. If no declared target is in top-N, attempt is flagged as low-leverage.
      Caller may override with `accept_low_leverage: true` in rubric (with
      reason).

# Usage

    from src.ztare.gates.closure_leverage_gate import run_closure_leverage_gate
    result = run_closure_leverage_gate(
        rubric_data=rubric,
        artifact_graph_path="projects/ns_millennium_hunt/workspace/queries/ns_trackb_artifact_graph.json",
    )
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def compute_leverage_ranking(graph_path: Path, receipt_node_id: str) -> list[dict]:
    """Walk the artifact graph; compute leverage for each open obligation.

    leverage(d) = #(receipt-tree decls whose uses_decl contains d.@id) for
    d.status == 'open_obligation' and d in receipt-tree.

    Returns sorted list of {decl_id, decl_name, file, leverage, status}.
    """
    if not graph_path.exists():
        return []
    g = json.loads(graph_path.read_text())
    nodes = g.get("@graph", [])
    files = [n for n in nodes if n.get("@type") == "ns_lean_file"]
    decls = [n for n in nodes if n.get("@type") == "ns_lean_decl"]

    fwd_imports = {f["@id"]: set(f.get("imports", [])) for f in files}

    def reach(start):
        seen = {start}
        stack = [start]
        while stack:
            n = stack.pop()
            for nb in fwd_imports.get(n, []):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        return seen

    if receipt_node_id not in fwd_imports:
        return []
    receipt_tree = reach(receipt_node_id)

    # Count downstream users: how many decls in receipt-tree use this decl's @id
    decl_users: dict[str, set[str]] = defaultdict(set)
    for d in decls:
        if d.get("file") not in receipt_tree:
            continue
        for u in d.get("uses_decl", []):
            decl_users[u].add(d["@id"])

    open_obligations = [
        d for d in decls
        if d.get("status") == "open_obligation" and d.get("file") in receipt_tree
    ]

    ranking = []
    for d in open_obligations:
        ranking.append({
            "decl_id": d["@id"],
            "decl_name": d.get("name"),
            "file": d.get("file", ""),
            "leverage": len(decl_users[d["@id"]]),
            "status": d.get("status"),
        })
    ranking.sort(key=lambda r: -r["leverage"])
    return ranking


def run_closure_leverage_gate(
    rubric_data: dict[str, Any] | None = None,
    artifact_graph_path: str | Path | None = None,
    receipt_node_id: str = "ns_file:ns_gp216_bridge_composition_receipt",
    *,
    top_n: int = 10,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Verify closure attempt targets at least one top-N leverage obligation.

    Args:
        rubric_data: rubric metadata. Looks for:
          - `target_obligations`: list of declaration names attempt aims to close
          - `accept_low_leverage`: bool to override the gate (with explanation)
          - `low_leverage_reason`: str (required if accept_low_leverage)
        artifact_graph_path: path to JSON-LD artifact graph
        receipt_node_id: graph node id for the closure receipt (default NS Track B)
        top_n: leverage cutoff (must address top-N highest-leverage obligations)
        enforce_block: if True, return passed=False on violations.

    Returns:
        {"passed": bool, "blocking_active": bool, "violations": list[dict],
         "advisory_warnings": list[str], "top_leverage_obligations": list[dict],
         "matched_targets": list[str], "summary": str}
    """
    rubric_data = rubric_data or {}
    targets = rubric_data.get("target_obligations") or []
    accept_low = bool(rubric_data.get("accept_low_leverage"))
    low_reason = rubric_data.get("low_leverage_reason", "")

    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    # Default graph path
    if artifact_graph_path is None:
        artifact_graph_path = Path(__file__).resolve().parents[3] / "analytics" / "queries" / "ns_trackb_artifact_graph.json"
    artifact_graph_path = Path(artifact_graph_path)

    if not artifact_graph_path.exists():
        violations.append({
            "type": "graph_not_found",
            "severity": "advisory",
            "reason": (
                "Artifact graph not found at %s. Run projects/ns_millennium_hunt/scripts/ns_graph.py all first. "
                "Without graph, leverage ranking cannot be computed; gate cannot fire."
                % artifact_graph_path
            ),
        })
        return {
            "passed": True, "blocking_active": enforce_block,
            "violations": violations, "advisory_warnings": ["graph not generated"],
            "top_leverage_obligations": [], "matched_targets": [],
            "summary": "graph not generated; gate skipped"
        }

    ranking = compute_leverage_ranking(artifact_graph_path, receipt_node_id)
    top_leverage = ranking[:top_n]

    if not ranking:
        violations.append({
            "type": "no_open_obligations_found",
            "severity": "advisory",
            "reason": "Either receipt has 0 open obligations (closure complete?) or graph receipt_node_id is wrong.",
        })
        return {
            "passed": True, "blocking_active": enforce_block,
            "violations": violations, "advisory_warnings": [],
            "top_leverage_obligations": [], "matched_targets": [],
            "summary": "0 open obligations in receipt-tree"
        }

    # M1: target_obligations must be declared
    if not targets:
        violations.append({
            "type": "target_obligations_not_declared",
            "severity": "advisory" if not enforce_block else "blocking",
            "reason": (
                "Closure attempt has no declared target_obligations. The graph-scale "
                "version of GP-219 proto-C requires attempts to name which open "
                "obligations they target. Declared targets are checked against the "
                "leverage ranking computed from the artifact graph. Add "
                "`target_obligations: [...]` to rubric, listing declaration names."
            ),
        })
        warnings.append("no target_obligations declared")
        passed = (not enforce_block)
        return {
            "passed": passed, "blocking_active": enforce_block,
            "violations": violations, "advisory_warnings": warnings,
            "top_leverage_obligations": top_leverage, "matched_targets": [],
            "summary": "0 targets declared; %d open obligations in receipt-tree" % len(ranking),
        }

    # M2: check overlap with top-N
    top_n_names = {r["decl_name"] for r in top_leverage}
    matched = [t for t in targets if t in top_n_names]
    leverage_by_name = {r["decl_name"]: r["leverage"] for r in ranking}
    target_leverages = [(t, leverage_by_name.get(t, 0)) for t in targets]

    # M3: low-leverage attempt without explicit acceptance
    if not matched and not accept_low:
        violations.append({
            "type": "low_leverage_attempt_without_acceptance",
            "severity": "advisory" if not enforce_block else "blocking",
            "declared_target_leverages": target_leverages,
            "top_n_alternatives": [(r["decl_name"], r["leverage"]) for r in top_leverage[:5]],
            "reason": (
                "Closure attempt targets %d obligation(s) (%s) but none are in the top-%d "
                "leverage ranking. Top-leverage alternatives unblock %d-%d downstream proofs each. "
                "If targeting low-leverage obligations is deliberate (e.g., chokepoint not yet "
                "approachable), set `accept_low_leverage: true` and `low_leverage_reason: <one-sentence>` "
                "in rubric to acknowledge the tradeoff."
                % (len(targets), ", ".join(targets), top_n,
                   top_leverage[-1]["leverage"] if top_leverage else 0,
                   top_leverage[0]["leverage"] if top_leverage else 0)
            ),
        })
        warnings.append("low-leverage targets without explicit acceptance")
    elif not matched and accept_low:
        warnings.append(
            "low-leverage targets accepted with reason: %s" % (low_reason or "(no reason given)")
        )

    blocking_violations = [v for v in violations if v.get("severity") == "blocking"]
    passed = (not blocking_violations) if enforce_block else True

    summary_parts = [f"{len(targets)} target(s) declared", f"{len(matched)} in top-{top_n} leverage"]
    if violations:
        summary_parts.append(f"{len(violations)} violation(s)")
    if not enforce_block:
        summary_parts.append("ADVISORY mode")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "top_leverage_obligations": top_leverage,
        "matched_targets": matched,
        "target_leverages": target_leverages,
        "summary": "; ".join(summary_parts),
    }


# ── Self-tests ──────────────────────────────────────────────────────────


def _self_test() -> None:
    # Build a fake graph for testing
    import tempfile
    fake_graph = {
        "@graph": [
            {"@id": "ns_file:ns_gp216_bridge_composition_receipt", "@type": "ns_lean_file",
             "imports": ["ns_file:ns_dep1", "ns_file:ns_dep2"]},
            {"@id": "ns_file:ns_dep1", "@type": "ns_lean_file", "imports": []},
            {"@id": "ns_file:ns_dep2", "@type": "ns_lean_file", "imports": []},
            # An open obligation with 5 downstream users
            {"@id": "ns_decl:dep1.HighLeverageObligation", "@type": "ns_lean_decl",
             "name": "HighLeverageObligation", "file": "ns_file:ns_dep1",
             "status": "open_obligation", "uses_decl": []},
            # 5 closed theorems that USE the high-leverage obligation
            *[{"@id": f"ns_decl:dep1.user{i}", "@type": "ns_lean_decl",
               "name": f"user{i}", "file": "ns_file:ns_dep1", "status": "closed_theorem",
               "uses_decl": ["ns_decl:dep1.HighLeverageObligation"]} for i in range(5)],
            # A leaf open obligation with 0 downstream users
            {"@id": "ns_decl:dep2.LeafObligation", "@type": "ns_lean_decl",
             "name": "LeafObligation", "file": "ns_file:ns_dep2",
             "status": "open_obligation", "uses_decl": []},
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fake_graph, f)
        graph_path = f.name

    # T1: missing target_obligations → advisory violation
    r = run_closure_leverage_gate(rubric_data={}, artifact_graph_path=graph_path)
    assert r["passed"] is True
    assert any(v["type"] == "target_obligations_not_declared" for v in r["violations"])
    assert len(r["top_leverage_obligations"]) == 2
    assert r["top_leverage_obligations"][0]["decl_name"] == "HighLeverageObligation"
    assert r["top_leverage_obligations"][0]["leverage"] == 5

    # T2: low-leverage target only → advisory violation
    r = run_closure_leverage_gate(
        rubric_data={"target_obligations": ["LeafObligation"]},
        artifact_graph_path=graph_path,
    )
    assert any(v["type"] == "low_leverage_attempt_without_acceptance" for v in r["violations"])
    assert r["matched_targets"] == []

    # T3: high-leverage target → no violation
    r = run_closure_leverage_gate(
        rubric_data={"target_obligations": ["HighLeverageObligation"]},
        artifact_graph_path=graph_path,
    )
    assert "HighLeverageObligation" in r["matched_targets"]
    assert not any(v["type"] == "low_leverage_attempt_without_acceptance" for v in r["violations"])

    # T4: low-leverage + accept_low_leverage → no blocking violation, just warning
    r = run_closure_leverage_gate(
        rubric_data={"target_obligations": ["LeafObligation"], "accept_low_leverage": True,
                     "low_leverage_reason": "leaf obligation closes a known parsimony gap"},
        artifact_graph_path=graph_path,
    )
    assert r["passed"] is True
    assert any("low-leverage targets accepted" in w for w in r["advisory_warnings"])

    # T5: blocking mode with no targets → passed=False
    r = run_closure_leverage_gate(
        rubric_data={}, artifact_graph_path=graph_path, enforce_block=True,
    )
    assert r["passed"] is False

    import os
    os.unlink(graph_path)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    _self_test()
