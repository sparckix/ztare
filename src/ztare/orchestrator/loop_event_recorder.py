"""Loop-event recorder + low-yield tail helper (Phase 4g, 2026-05-06 PM).

Two small helpers extracted from autoresearch_loop:

  - ``record_loop_event`` — write a per-event payload to
    ``workspace/latest_loop_event.json`` (overwriting) and append to
    ``workspace/loop_events.jsonl`` (audit log). Called on stagnation
    pivots, refresh-specialists triggers, and other loop-control
    transitions.
  - ``latest_low_yield_tail`` — extract the suffix of the iteration
    history that has not improved score and has no novelty
    signals. Used by the underidentification verdict to summarise
    the stagnant tail.

Both pure / near-pure (record_loop_event takes RUN_ID + project as
args rather than reading module globals).

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ztare.common.file_io import write_json, append_jsonl


_EVENT_LABELS: dict[str, str] = {
    "topological_pivot_profile_injected": "structural_pivot_profile_injected",
    "topological_pivot_emergency": "emergency_structural_pivot",
    "v4_bounded_mutation_override": "v4_bounded_mutation_override",
    "pivot_skipped_gp149_i3": "pivot_skipped_by_weakest_link_class",
    "control_followup_observe": "control_followup_observe",
}


def event_label_for(event_type: str) -> str:
    """Return the operator-facing label for a compatibility event id."""
    return _EVENT_LABELS.get(event_type, event_type)


def record_loop_event(
    workspace_dir: Path,
    *,
    event_type: str,
    iteration_index: int,
    stagnation_count: int,
    falsification_mode: str,
    is_v4_project: bool,
    pivot_profile,
    pending_loop_action: str,
    mutator_model_id: str,
    judge_model_id: str,
    run_id,
    project_name: str,
) -> None:
    """Persist one loop-control event to the per-iter latest + audit jsonl.

    ``pivot_profile`` is None or a PivotProfile-like object with
    ``.name`` and ``.modules`` attrs. Both files are written atomically
    via the standard ``write_json`` / ``append_jsonl`` primitives.
    """
    profile_name = pivot_profile.name if pivot_profile else None
    profile_modules = list(pivot_profile.modules) if pivot_profile else []
    payload = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "event_label": event_label_for(event_type),
        "project": project_name,
        "iteration_index": iteration_index,
        "stagnation_count": stagnation_count,
        "falsification_mode": falsification_mode,
        "is_v4_project": is_v4_project,
        "pivot_profile": profile_name,
        "pivot_modules": profile_modules,
        "pending_loop_action": pending_loop_action,
        "mutator_model_id": mutator_model_id,
        "judge_model_id": judge_model_id,
    }
    write_json(str(workspace_dir / "latest_loop_event.json"), payload)
    append_jsonl(str(workspace_dir / "loop_events.jsonl"), payload)


def latest_low_yield_tail(history: list) -> list:
    """Return the suffix of ``history`` whose iters did not improve
    score and had no novelty signals.

    Walks ``history`` from the end; stops at the first iter that
    DID improve score or DID have novelty (attack ids, hinge ids,
    primitive ids, or verified axioms added). Returns the slice
    after that stop point in original order.

    Used by the underidentification verdict to summarise the
    stagnant tail when the loop hits its "underidentified after N"
    threshold.
    """
    tail = []
    for item in reversed(history):
        if item.score_improved or item.has_novelty():
            break
        tail.append(item)
    tail.reverse()
    return tail
