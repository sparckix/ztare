"""Latest-gate-surface formatter for mutator prompts (Phase 4g, 2026-05-06 PM).

Single helper extracted from autoresearch_loop. Formats the
deterministic-charter-gates results from an eval payload into a
multi-line string suitable for cold-successor mutator prompting.

Pure function — no apparatus state, no module globals. Falls back
to hard_fail_reasons + soft_score_caps when results is empty
(e.g., when the harness was never invoked).

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations


def format_gate_surface_for_prompt(eval_payload: dict) -> str:
    """Format latest gate surface for cold successor prompting.

    Reads ``eval_payload.score_contract.deterministic_charter_gates``;
    falls back to top-level hard_fail_reasons / soft_score_caps when
    the gate harness wasn't invoked. Returns a string with the
    ``LATEST GATE SURFACE:`` header followed by per-gate lines.
    """
    score_contract = (
        eval_payload.get("score_contract", {}) if isinstance(eval_payload, dict) else {}
    )
    det = score_contract.get("deterministic_charter_gates", {})
    results = det.get("results", [])
    lines = ["LATEST GATE SURFACE:"]
    if results:
        for item in results:
            name = item.get("name", "unknown")
            passed = bool(item.get("passed", False))
            status = "PASS" if passed else "FAIL"
            lines.append(f"  - {name}: {status}")
            reason = str(item.get("reason", "") or "")
            if reason:
                lines.append(f"    reason: {reason}")
    else:
        hard_fail_reasons = score_contract.get("hard_fail_reasons", [])
        soft_caps = score_contract.get("soft_score_caps", [])
        if hard_fail_reasons:
            lines.append("  Hard fail reasons:")
            for reason in hard_fail_reasons:
                lines.append(f"    - {reason}")
        if soft_caps:
            lines.append("  Soft caps:")
            for cap in soft_caps:
                lines.append(f"    - cap={cap.get('cap')}: {cap.get('reason', '')}")
    return "\n".join(lines)
