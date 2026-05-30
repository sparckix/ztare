"""R1 retry diagnostics — extracted from autoresearch_loop (Phase 4g, 2026-05-06).

The R1 retry mechanism (compiler-failure detection, lint-strike accounting,
mutator repair-prompt loop) is largely already extracted via
``src/ztare/orchestrator/format_r1_retry_skeleton`` (legacy, see imports in
autoresearch_loop) and ``src/ztare/fit/fit_declaration_retry``. What
remained inline in autoresearch_loop was a single ~55-line debug-logging
helper plus two session-level rail-off counters. This module owns those.

Phase 4g pulls these out as a contained, testable atomic unit. The
extracted helpers do not change apparatus behavior — they only move from
module-level globals + private functions in autoresearch_loop into a
named-import surface that future tests + future Phase 4 extractions can
depend on.

Behaviour preserved verbatim from the prior inline implementation
(see autoresearch_loop.py 2026-05-05 git history for the original).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# WAR Guard C (2026-04-27): rail-off pattern detection. Consecutive iters
# where R1 exhausts all 3 strikes indicate the mutator has gone off-rails
# (typically: pseudo-code essays, mid-submission truncation, contract
# violations on every retry). After this many consecutive exhaustions the
# loop logs a clear warning so the operator can stop the run instead of
# burning tokens on a model that won't recover. Reset on any successful
# R1 pass.
R1_EXHAUSTION_WARN_THRESHOLD = 2


class R1ExhaustionTracker:
    """Track consecutive R1 strike-exhaustion events across iters.

    Encapsulates what was previously two module-level globals
    (SESSION_CONSECUTIVE_R1_EXHAUSTIONS + SESSION_R1_EXHAUSTION_WARN_THRESHOLD)
    in autoresearch_loop. Instance state instead of module-global makes
    the rail-off semantics testable in isolation and survives the future
    Phase 4g main-loop extraction (where module-level globals would need
    explicit `global` declarations inside an extracted function — this
    class form sidesteps that entirely).

    Behaviour preserved verbatim from the prior module-global
    implementation (autoresearch_loop.py 2026-05-05 git history).
    """

    __slots__ = ("consecutive_count", "threshold")

    def __init__(self, threshold: int = R1_EXHAUSTION_WARN_THRESHOLD) -> None:
        self.consecutive_count = 0
        self.threshold = threshold

    def reset(self) -> None:
        """Reset on any successful R1 pass."""
        self.consecutive_count = 0

    def record_exhaustion(self) -> bool:
        """Increment counter; return True if the warn threshold is reached."""
        self.consecutive_count += 1
        return self.consecutive_count >= self.threshold


def log_r1_attempt(
    iter_index: int,
    strike_num: int,
    error_text: str,
    content: str,
    *,
    project_dir: str | Path,
    exhausted: bool = False,
    mutator_model: str = "",
) -> None:
    """Persist a failed R1 attempt to ``workspace/r1_debug/`` for postmortem.

    2026-04-27 visibility fix: the R1 retry path consumes mutator
    output and discards it on rejection. When an iter dies on R1
    strike-exhaustion the operator can see only the final 160-char
    error tail in stdout — the actual content of what the mutator
    was trying to express is gone. This helper appends each attempt
    (and the final exhausted attempt) to a per-iter markdown log so
    the operator can read the mutator's intent after the fact.

    Output path: ``{project_dir}/workspace/r1_debug/iter_{NNN}_r1_attempts.md``

    The function is best-effort: a debug-write failure is logged to
    stdout but never propagated, so the live run path is never disrupted
    by a logging issue.
    """
    try:
        debug_dir = Path(project_dir) / "workspace" / "r1_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        log_path = debug_dir / f"iter_{iter_index:03d}_r1_attempts.md"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = "EXHAUSTED" if exhausted else f"strike_{strike_num}"
        header = (
            f"## attempt #{strike_num} — {status} — {ts}"
            f"{' — model=' + mutator_model if mutator_model else ''}\n\n"
            f"**Rejection reason:**\n\n```\n{(error_text or '')[:2000]}\n```\n\n"
            f"**Mutator submission ({len(content or '')} chars):**\n\n"
            f"```\n{(content or '<empty>')[:30000]}\n```\n\n"
            "---\n\n"
        )
        # On strike 1, write a file header so the iter log is self-describing.
        if not log_path.exists():
            log_path.write_text(
                f"# R1 retry attempts — iter {iter_index}\n\n"
                "Each section below is one mutator submission that failed the R1\n"
                "lint check. The strike-1 entry is the original submission; later\n"
                "entries are retries that followed the apparatus's repair prompt.\n"
                "EXHAUSTED marks the final attempt that consumed the iter.\n\n",
                encoding="utf-8",
            )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(header)
    except Exception as _log_exc:  # noqa: BLE001
        # Logging is best-effort; never let a debug-write failure disrupt
        # the actual run path.
        print(f"⚠️  R1-debug log failed for iter {iter_index}: {_log_exc}")
