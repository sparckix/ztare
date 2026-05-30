"""G-STAGNATION-SPECIAL-CASE-HINT — Director-assist gate for tb_NEW_POLYA Strategic Specialization.

Operationalizes tb_NEW_POLYA from the GP-216 theory-building vocabulary:
"solve a load-bearing special case that breaks a structural barrier; not
generic specialization."

When ZTARE score stagnates ≥N iterations on a substrate, this gate surfaces
a list of structurally-narrow special-case candidates derived from the
rubric's grammar / charter. The Director agent picks one
(judgment); the gate ensures the Director is presented with the option
rather than continuing blind iteration.

This is NOT a fail-closed gate (the panel-discipline rule). It is an
ADVISORY that injects a directive into the iteration prompt when stagnation
crosses threshold. The Director can:
  - Pick a special case from the surfaced candidates (deploy tb_NEW_POLYA)
  - Reject the hint as not applicable (continue current trajectory)
  - Add a new special case the gate missed (extend candidate list)

Failure modes this addresses:
  - Stagnation where the principal frame is wrong, not the parameters
    (GP-180/181-style — the substrate is searching wrong region of grammar)
  - Director not noticing stagnation has crossed actionable threshold
  - Iterations wasted on "more parameter sweep" when a special-case break
    would unblock

Selection of candidate special cases is rubric-specific. The gate provides
the *trigger* + *interface*; the rubric provides the candidate list via
metadata `special_case_candidates` schema:
  [
    {
      "name": "<descriptive>",
      "structural_barrier_addressed": "<which barrier this case breaks>",
      "instantiation_hint": "<how to set up this special case>",
      "complexity_class": "narrower" | "same" | "broader",
    }
  ]
"""
from __future__ import annotations

from typing import Any


def run_stagnation_hint_gate(
    iteration_history: list[dict],
    rubric_data: dict[str, Any] | None = None,
    *,
    stagnation_threshold: int = 3,
    score_field: str = "score",
    score_tolerance: float = 0.5,
) -> dict[str, Any]:
    """Detect stagnation and surface special-case candidates.

    Args:
        iteration_history: list of iteration dicts; each should contain a `score`.
        rubric_data: rubric metadata. Looks for `special_case_candidates` list.
        stagnation_threshold: number of consecutive iterations without score
          improvement (within tolerance) before gate fires.
        score_field: which field to read for score.
        score_tolerance: fluctuation absorbed before counting as no-improvement.

    Returns:
        {
          "fired": bool,           # whether stagnation threshold crossed
          "stagnation_iters": int, # how many consecutive flat iterations
          "best_score": float,
          "candidates_surfaced": list[dict],
          "directive": str | None, # text to inject into next iteration's prompt
          "summary": str,
        }
    """
    rubric_data = rubric_data or {}
    candidates = rubric_data.get("special_case_candidates", []) or []

    if len(iteration_history) < stagnation_threshold + 1:
        return {
            "fired": False,
            "stagnation_iters": 0,
            "best_score": None,
            "candidates_surfaced": [],
            "directive": None,
            "summary": f"insufficient history ({len(iteration_history)} iters < {stagnation_threshold + 1})",
        }

    # Find best score in history
    scores = [float(it.get(score_field, 0.0)) for it in iteration_history]
    best = max(scores)

    # Count consecutive no-improvement at end
    consecutive_flat = 0
    for i in range(len(scores) - 1, 0, -1):
        if scores[i] >= scores[i - 1] + score_tolerance:
            break
        consecutive_flat += 1

    fired = consecutive_flat >= stagnation_threshold

    if not fired:
        return {
            "fired": False,
            "stagnation_iters": consecutive_flat,
            "best_score": best,
            "candidates_surfaced": [],
            "directive": None,
            "summary": f"no stagnation: {consecutive_flat} flat iters < {stagnation_threshold}",
        }

    # Stagnation detected — build hint directive
    surfaced = candidates if candidates else []

    if not surfaced:
        directive = (
            f"\n\n=== STAGNATION DETECTED ({consecutive_flat} flat iterations) ===\n"
            f"Score has plateaued at {best:.2f} for {consecutive_flat} consecutive iterations within "
            f"tolerance {score_tolerance}.\n"
            f"\n"
            f"This is the tb_NEW_POLYA / Strategic Specialization trigger. The principal frame may be "
            f"wrong, not the parameters. Consider: which structurally-narrow special case, if solved, "
            f"would break the current barrier and force a reconfiguration of the rest of the search?\n"
            f"\n"
            f"No special-case candidates were declared in rubric metadata. Add "
            f"`special_case_candidates` to rubric for auto-surfacing on stagnation.\n"
        )
    else:
        directive_lines = [
            f"\n\n=== STAGNATION DETECTED ({consecutive_flat} flat iterations) ===",
            f"Score plateau at {best:.2f}. Consider one of the rubric's declared special-case candidates:",
            "",
        ]
        for i, c in enumerate(surfaced, 1):
            directive_lines.append(
                f"  {i}. {c.get('name', '?')} — addresses barrier: {c.get('structural_barrier_addressed', '?')}"
            )
            directive_lines.append(f"     setup: {c.get('instantiation_hint', '?')}")
            directive_lines.append(f"     complexity: {c.get('complexity_class', '?')}")
            directive_lines.append("")
        directive_lines.append(
            "Pick one of these special cases (or propose a missing one). Do NOT continue the current "
            "search trajectory blindly; the principal frame is suspect."
        )
        directive = "\n".join(directive_lines)

    return {
        "fired": True,
        "stagnation_iters": consecutive_flat,
        "best_score": best,
        "candidates_surfaced": surfaced,
        "directive": directive,
        "summary": (
            f"FIRED: {consecutive_flat} flat iters at score {best:.2f}; "
            f"{len(surfaced)} special-case candidates surfaced"
        ),
    }


def _self_test() -> None:
    """Smoke test."""
    # Test 1: no stagnation
    history = [
        {"iter": 0, "score": 50.0},
        {"iter": 1, "score": 55.0},
        {"iter": 2, "score": 62.0},
        {"iter": 3, "score": 70.0},
    ]
    r = run_stagnation_hint_gate(history)
    assert not r["fired"], f"Test 1 should not fire: {r}"
    print("  Test 1 PASS (no stagnation)")

    # Test 2: stagnation, no candidates
    history2 = [
        {"iter": 0, "score": 50.0},
        {"iter": 1, "score": 70.0},
        {"iter": 2, "score": 70.1},
        {"iter": 3, "score": 70.2},
        {"iter": 4, "score": 70.0},
    ]
    r = run_stagnation_hint_gate(history2)
    assert r["fired"], f"Test 2 should fire: {r}"
    assert "No special-case candidates were declared" in r["directive"]
    print(f"  Test 2 PASS (stagnation detected, {r['stagnation_iters']} flat iters)")

    # Test 3: stagnation with candidates
    rubric = {
        "special_case_candidates": [
            {
                "name": "Killing-mode flat-torus low-high",
                "structural_barrier_addressed": "smooth shear catalyst growth",
                "instantiation_hint": "set L = A·sin(K·y)·e_x with K=1, N=64",
                "complexity_class": "narrower",
            },
            {
                "name": "Resonant random tail high-high",
                "structural_barrier_addressed": "resonant overlap survivor search",
                "instantiation_hint": "sparse pairs at sample_size=5000, bounds 3-4",
                "complexity_class": "same",
            },
        ]
    }
    r = run_stagnation_hint_gate(history2, rubric)
    assert r["fired"]
    assert len(r["candidates_surfaced"]) == 2
    assert "Killing-mode" in r["directive"]
    print(f"  Test 3 PASS (stagnation + 2 candidates surfaced)")

    print("All self-tests passed.")


if __name__ == "__main__":
    _self_test()
