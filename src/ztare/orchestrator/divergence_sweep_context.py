"""GP-076 predictive-divergence-sweep context formatter (Phase 4g, 2026-05-06).

Single helper extracted from autoresearch_loop. Formats the divergence
sweep state into a mutator-prompt fragment so the apparatus can:

  - Tell the mutator which library forms have been eliminated by
    holdout queries
  - Surface the surviving forms (intersection across queries) and
    direct the mutator to FIT one of them rather than invent a new
    topology
  - Communicate "library exhausted" when no library form survived
    the holdout gate

Pure function — no apparatus state, no module globals. Behaviour
preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).

See also: ``src/ztare/validator/predictive_divergence_sweep.py`` —
the GP-076 implementation that produces the sweep_state dict this
helper consumes.
"""
from __future__ import annotations


def format_sweep_context(sweep_state: dict) -> str:
    """Format GP-076 sweep state for mutator prompt injection.

    Returns "" if sweep_state is empty / no signal to surface. Otherwise
    returns a multi-line string with the LIBRARY-EXHAUSTED banner (if
    applicable), the per-query observations table, the surviving-form
    intersection, and the direct instruction to fit (rather than
    invent) when survivors exist.
    """
    if not sweep_state:
        return ""
    parts: list[str] = []
    if sweep_state.get("library_exhausted"):
        parts.append(
            "GP-076 DIVERGENCE SWEEP — LIBRARY EXHAUSTED:\n"
            "The deterministic corrector library has been fully searched. "
            "No library form survived the holdout gate. You must propose a "
            "NOVEL functional form for the corrector — do not reuse any "
            "standard form (step, heaviside, round, floor, ceil, etc.).\n"
        )
    query_history = sweep_state.get("query_history", [])
    if query_history:
        parts.append("GP-076 DIVERGENCE QUERY OBSERVATIONS (verified data points):")
        all_surviving: list[str] | None = None
        for q in query_history:
            surviving = q.get("surviving_forms", [])
            k_vals = q.get("surviving_k_values", {})
            k_str = ""
            if k_vals:
                k_str = "  fitted k: " + ", ".join(
                    f"{form}→k={k:.4f}" for form, k in k_vals.items()
                )
            parts.append(
                f"  corrector(v={q['query_v']}) = {q['observed']}  "
                f"[eliminated {len(q.get('eliminated', []))} candidates, "
                f"{q.get('survivors_after', '?')} remain: {surviving}]{k_str}"
            )
            if all_surviving is None:
                all_surviving = list(surviving)
            else:
                all_surviving = [s for s in all_surviving if s in surviving]
        parts.append(
            "These observations are confirmed experimental results. "
            "Your proposed corrector MUST match these values exactly.\n"
        )
        if all_surviving:
            parts.append(
                "SURVIVING LIBRARY FORMS (consistent with all query observations):\n"
                + "\n".join(f"  - {f}" for f in all_surviving)
                + "\n\nDIRECT INSTRUCTION: Fit the surviving form(s) above to the visible "
                "corrector data to find the best free parameter k. Do NOT invent a new "
                "topology — use one of the surviving forms exactly. Show your derivation "
                "of k from visible (v, corrector) pairs and verify it matches all query "
                "observations before writing the final expression.\n"
            )
    return "\n".join(parts)
