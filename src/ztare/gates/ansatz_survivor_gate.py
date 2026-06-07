"""GP-144 Gate G3 — Ansatz Survivor (SPECULATIVE SHELL — SUPERSEDED 2026-06-07).

Status: 2026-04-24 — speculative shell; blocked on live Lean compilation
pipeline integration.

SUPERSEDED 2026-06-07 by leanmill: the blocker ("live Lean compilation pipeline /
GP-122 lean_repl") is now PROVIDED by the leanmill governed solver — `solve_adhoc`
is the live kernel-verified Lean pipeline, and the "pick the SHORTEST verifying
proof among top-K" idea this shell wanted IS already shipped as
`ztare.leanmill.solver.family_lemma_library.mdl_shortest` (the MDL description-length
proof-form selector). Do NOT build this out here; route any real ansatz-shortest-proof
selection through leanmill. The gate is left registry-WIRED (a benign advisory shell;
`proof_surveyability` declares a dependency on it and the gate-engagement tests assert
its ordering) — fully removing it is a separate gate-engagement refactor (drop the
dependency + update test_gate_engagement.py), NOT done here to avoid breaking the wired
pipeline. See the GP-144 seam.

PURPOSE
-------
Prevent wrong-ansatz chase: when Phase C produces multiple top-K candidates
that all pass admission, select the one whose LEAN PROOF IS SHORTEST, not
whose residual is lowest. Low-residual-but-verbose-proof signals path-
specific fitting; short-proof signals structural correctness.

Three sub-gates when fully implemented:
  1. Top-K Lean attempt: submit top-5 (not top-1) to GP-122 lean_repl.
     Rank by proof_line_count ascending. Winner = shortest verifiable.
  2. Independent-pipeline agreement: re-extract ansatz from 3 independent
     paths (disjoint time window, perturbed IC, alternate solver library).
     >=3 agreeing paths → champion; <3 → reject (path-dependent).
  3. Adversarial basis reformulation: operator-adjacent agent proposes
     functionally-equivalent ansatz in different basis. If both prove the
     same theorem → real structure. Only original works → fitted to basis.

STATUS
------
Blocked on:
  - Live GP-122 lean_repl invocation within autoresearch_loop (for 1)
  - Independent-extraction protocol (for 2) — needs Phase A/C extension
  - Adversarial agent handoff (for 3) — needs sibling-agent protocol

Shell signature stable; placeholder returns shell_not_fully_implemented.
"""
from __future__ import annotations

from typing import Any, Optional

GATE_ID = "ansatz_survivor"
PRODUCER = "GP-144.G3"


def top_k_lean_proof_shortness(
    candidates: list[dict[str, Any]],
    k: int = 5,
    project_dir: Optional[Any] = None,
    model: str = "gpt4.1",
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Submit top-k to Lean, rank by proof line count. Winner = shortest verifiable.

    IMPLEMENTED 2026-04-24 using GP-122 Lean REPL. For each of the top-k
    candidates (ordered by input list), writes a candidate-specific
    compression_results.json and invokes prove_from_compression. Measures the
    generated Lean file's line count as proxy for proof complexity. Returns
    the candidate whose proof (a) verifies AND (b) has the shortest line count.

    If fewer than k candidates verify, returns the shortest-verifying one
    with n_verified < k recorded.

    If project_dir is None, degrades to shell-deferred verdict (can't invoke
    lean_repl without a project workspace).
    """
    from pathlib import Path as _Path
    if project_dir is None:
        return {
            "implemented": False,
            "blocked_on": "project_dir required for lean_repl invocation",
            "reason": "G3 requires a project workspace to write candidate compression JSONs and Lean stubs.",
        }
    project_dir = _Path(project_dir)
    try:
        from src.ztare.formal.lean_repl import prove_from_compression
    except ImportError as e:
        return {
            "implemented": False,
            "blocked_on": f"lean_repl import failed: {e}",
            "reason": "GP-122 Lean REPL module unavailable in this environment.",
        }
    results = []
    for i, cand in enumerate(candidates[:k]):
        # Write this candidate as the SOLE compression_results.json entry
        # so prove_from_compression picks it up as 'best'.
        comp_entry = {
            "name": f"g3_cand_{i}",
            "expression": cand.get("expression") or cand.get("lean_theorem") or str(cand),
            "bic": cand.get("bic", 0.0),
            "k": cand.get("k", 0),
            "gates_passed": True,
        }
        comp_path = project_dir / "workspace" / "compression_results.json"
        comp_path.parent.mkdir(parents=True, exist_ok=True)
        # Save existing compression_results so we don't clobber downstream consumers
        _backup = None
        if comp_path.exists():
            _backup = comp_path.read_text()
        try:
            import json as _json
            comp_path.write_text(_json.dumps([comp_entry], indent=2))
            lean_result = prove_from_compression(
                project_dir=project_dir,
                model=model,
                max_attempts=max_attempts,
            )
            # Measure proof length from emitted .lean file
            lean_stub_path = project_dir / f"{project_dir.name}.lean"
            line_count = 0
            if lean_stub_path.is_file():
                line_count = lean_stub_path.read_text().count("\n")
            results.append({
                "candidate_index": i,
                "candidate_id": cand.get("candidate_id", f"cand_{i}"),
                "proved": bool(lean_result.get("proved")),
                "attempts": int(lean_result.get("attempts", 0)),
                "lean_line_count": line_count,
                "lean_error": lean_result.get("error"),
            })
        finally:
            # Restore backup
            if _backup is not None:
                comp_path.write_text(_backup)
            elif comp_path.exists():
                comp_path.unlink()

    verified = [r for r in results if r["proved"]]
    if not verified:
        return {
            "implemented": True,
            "passed": False,
            "reason": f"No candidate (of {len(results)} attempted) produced a verifying Lean proof.",
            "top_k_results": results,
            "n_verified": 0,
        }
    shortest = min(verified, key=lambda r: r["lean_line_count"] or float("inf"))
    return {
        "implemented": True,
        "passed": True,
        "winner_candidate_index": shortest["candidate_index"],
        "winner_line_count": shortest["lean_line_count"],
        "n_verified": len(verified),
        "n_attempted": len(results),
        "top_k_results": results,
        "reason": (
            f"proof_shortness_winner: candidate_index={shortest['candidate_index']} "
            f"verified with {shortest['lean_line_count']} lines; "
            f"{len(verified)}/{len(results)} candidates verified."
        ),
    }


def independent_pipeline_agreement(
    candidate: dict[str, Any],
    path_variants: list[str],
) -> dict[str, Any]:
    """Re-extract candidate from multiple independent paths. Require agreement."""
    return {
        "implemented": False,
        "blocked_on": "Phase A/C independent-extraction protocol",
        "reason": ("Phase A/C currently runs one extraction per iter. Independent-path "
                   "replication (disjoint time window + perturbed IC + alternate solver) "
                   "requires multi-extraction orchestration not yet in loop."),
    }


def adversarial_basis_reformulation(
    candidate: dict[str, Any],
    adversary_agent_id: str,
) -> dict[str, Any]:
    """Adversarial reformulation: another agent proposes same-theorem in
    different basis. Both must verify for structure-real verdict."""
    return {
        "implemented": False,
        "blocked_on": "Sibling-agent adversarial reformulation protocol",
        "reason": ("Requires handoff to a separate agent instance, lean compilation of "
                   "both forms, structural equivalence check. Not wired."),
    }


def run_gate(
    candidates: list[dict[str, Any]],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run G3 ansatz_survivor on a candidate ensemble.

    Currently: all sub-gates return deferred-stub results. Shell returns
    undecided verdict with explicit blocked-on reasons.
    """
    k = int(rubric_params.get("top_k", 5))
    r_shortness = top_k_lean_proof_shortness(candidates, k=k)
    r_agreement = independent_pipeline_agreement({}, rubric_params.get("path_variants", []))
    r_reformulation = adversarial_basis_reformulation({}, rubric_params.get("adversary_agent_id", ""))
    return {
        "name": GATE_ID,
        "passed": None,
        "actual": None,
        "threshold": None,
        "reason": "shell_not_fully_implemented: all three sub-gates blocked on Lean / phase-orchestration infra.",
        "penalty": 0,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "top_k_lean_shortness": r_shortness,
            "independent_agreement": r_agreement,
            "adversarial_reformulation": r_reformulation,
            "shell_fully_implemented": False,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    filtered["extra"] = {
        "shell_fully_implemented": gate_result.get("extra", {}).get("shell_fully_implemented"),
    }
    return filtered
