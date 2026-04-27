"""GP-157 v5.0 Phase 4a — IterContext dataclass (decomplecting target).

Hickey-style: pull per-iteration state out of the autoresearch_loop
module-level locals into a single typed object that Cage gates and
future orchestrator/{telemetry, state} extractions can consume
uniformly.

Phase 4a is additive: this dataclass exists, has tests, and is exposed
via `from src.ztare.orchestrator import IterContext`, but the existing
autoresearch_loop locals are untouched. Phase 4a-step-2 (separate commit)
will populate this from the existing locals at the top of each iteration
and pass it to the Cage observe-mode block. Phase 3c (Cage authoritative)
then uses IterContext as the canonical arg-marshaller for gate run callbacks.

Design rule: this is a *snapshot* of per-iteration inputs, not a
mutable god-object. If a field would be set by a downstream gate,
return a NEW IterContext with `.replace(field=value)` instead of
mutating in place. Frozen dataclass enforces this.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class IterContext:
    """Per-iteration state snapshot.

    Fields are intentionally limited at Phase 4a to those already consumed
    by the Cage observe-mode dispatch block in autoresearch_loop.py
    (~L3340-3360 + ~L3978-4015). Add fields here as additional consumers
    migrate; do NOT add speculative fields.
    """

    # ── Identity ─────────────────────────────────────────────────────────
    iteration_index: int
    """0-based index of the current iteration within the run."""

    run_id: int
    """Unique run identifier (UNIX timestamp at run start)."""

    project: str
    """GP-NNN project slug, e.g. 'gp154_scaling_law_exponents'."""

    # ── Filesystem ───────────────────────────────────────────────────────
    workspace_dir: Path
    """Per-run workspace dir; gates and telemetry write here."""

    # ── Rubric / config ──────────────────────────────────────────────────
    rubric_data: Mapping[str, Any]
    """The active rubric_data dict (read-only at this layer)."""

    # ── Cage v5.0 dispatch (Phase 3b/3c plumbing) ────────────────────────
    cage_observe_mode: bool = False
    """True iff rubric_data['cage_observe_mode'] is set."""

    cage_meta: Mapping[str, Any] | None = None
    """Substrate meta declared by the rubric (class, target_convention_homogeneity, ...)."""

    # ── Mutator/judge identity (used by telemetry) ───────────────────────
    mutator_model_id: str = ""
    judge_model_id: str = ""

    # ── Free-form extension ──────────────────────────────────────────────
    extras: Mapping[str, Any] = field(default_factory=dict)
    """Forward-compat slot for fields not yet promoted to first-class."""

    # ── Helpers ──────────────────────────────────────────────────────────

    def with_iteration(self, iteration_index: int) -> "IterContext":
        """Return a new IterContext with iteration_index advanced."""
        return replace(self, iteration_index=iteration_index)

    def cage_engagement_log_path(self) -> Path:
        """Canonical path for Cage engagement-matrix JSONL."""
        return self.workspace_dir / "cage_engagement.jsonl"

    def __post_init__(self) -> None:
        if self.iteration_index < 0:
            raise ValueError(f"iteration_index must be >= 0 (got {self.iteration_index})")
        if self.run_id < 0:
            raise ValueError(f"run_id must be >= 0 (got {self.run_id})")
        if not isinstance(self.workspace_dir, Path):
            raise TypeError(
                f"workspace_dir must be pathlib.Path (got {type(self.workspace_dir).__name__}). "
                f"Per Hickey: don't smuggle strings as paths — convert at the boundary."
            )
