"""Per-run failure-mode diagnostics — the run-level OBSERVABILITY epilogue.

A governed solve records every move attempt (move / outcome / error_class / notes / wallclock_s / run_tag) to
`solver_lane_attempts.db`, but a run only ever PRINTED an opaque `N/M closed`. When a run closes nothing the
operator had to hand-query SQLite to learn *why* (the 2026-06-20 incident: 5 rungs, 0 closures — the real cause,
100% `unknown identifier` from a namespace-context bug, was invisible). This module reads those attempts back and
SURFACES the failure mode with a headline verdict, so a run says e.g. "STRUCTURAL — 92% unknown-identifier (scope
bug, not hard math)" instead of "0/5 closed".

Two surfaces:
  • `summarize_run(...)` / `render(...)` — call as an epilogue at the end of a run (filter by run_tag).
  • CLI: `python -m ztare.leanmill.run_diagnostics --run-tag T` or `--window-min 70`.

NO soundness surface — read-only over telemetry; it changes what the operator SEES, never a verdict.
"""
from __future__ import annotations

import os
import sqlite3
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_DB = _REPO / "analytics/public/queries/solver_lane_attempts.db"

# Refine the coarse `other_error` bucket from the attempt notes — THIS is what makes a scope/context bug visible
# (it was buried under `other_error` before). Ordered: first match wins. (substring, refined_class, is_structural).
# "structural" = the apparatus never got a clean shot at the MATH (scope/syntax/context) — a fixable infra/harness
# signal, NOT genuine difficulty. "genuine" = an honest proof gap (unsolved_goals / no_advance).
_REFINE = [
    ("unknown identifier", "unknown_identifier", True),
    ("unknown constant", "unknown_identifier", True),
    ("unknown namespace", "unknown_identifier", True),
    ("function expected", "unknown_identifier", True),   # a missing-def applied to args (the namespace-bug shape)
    ("ambiguous", "ambiguous_name", True),
    ("unexpected token", "syntax_error", True),
    ("unexpected identifier", "syntax_error", True),
    ("expected ", "syntax_error", True),
    ("type mismatch", "type_mismatch", True),
    ("failed to synthesize", "instance_missing", True),
    ("unsolved goals", "unsolved_goals", False),
    ("linarith failed", "tactic_failed", False),
    ("simp made no progress", "tactic_failed", False),
    ("ring failed", "tactic_failed", False),
    ("statement-false", "statement_false", False),
    # governance rejections — the firewall WORKING (a bad/altered/laundered proof correctly blocked), NOT a
    # scope/context bug. The apparatus got a clean shot; the agent produced something the firewall caught.
    ("signature_altered", "governance_block", False),
    ("statement_integrity", "governance_block", False),
    ("laundering", "governance_block", False),
    ("target_signature", "governance_block", False),
    ("does not follow", "lemma_no_compose", False),
    ("goal does not follow", "lemma_no_compose", False),
    # the leaf produced a proof that didn't compile (a genuine proof error, distinct from a scope/context bug)
    ("agentic_leaf open: compile_error", "leaf_proof_compile_error", False),
    ("compile_error", "leaf_proof_compile_error", False),
    ("dead instrument", "dead_instrument", True),
    ("inadmissible", "dead_instrument", True),
]


def _refine_class(error_class: "str | None", notes: "str | None") -> "tuple[str, bool]":
    """(refined_class, is_structural). Use the notes text to split the catch-all `other_error` into an actionable
    class; fall back to the recorded error_class."""
    blob = ((notes or "") + " " + (error_class or "")).lower()
    for sub, cls, structural in _REFINE:
        if sub in blob:
            return cls, structural
    ec = (error_class or "other_error").strip() or "other_error"
    # honest unproven goals are NOT structural; everything genuinely unknown stays "other_error" (structural-ish:
    # we couldn't even classify it, which itself is worth surfacing).
    return ec, ec not in ("unsolved_goals", "no_advance", "no_seed")


def _iso_span_minutes(stamps: "list[str]") -> "float | None":
    """Wall span in minutes from ISO-8601 attempt_at strings (lexicographic min/max — ISO sorts correctly)."""
    xs = [s for s in stamps if s]
    if len(xs) < 2:
        return None
    try:
        from datetime import datetime
        lo = datetime.fromisoformat(min(xs)); hi = datetime.fromisoformat(max(xs))
        return max(0.0, (hi - lo).total_seconds() / 60.0)
    except Exception:  # noqa: BLE001
        return None


def summarize_run(*, db_path: "str | Path | None" = None, run_tag: "str | None" = None,
                  since_iso: "str | None" = None, window_min: "float | None" = None) -> dict:
    """Read the attempts for ONE run (by run_tag, or a recent time window) and summarize the failure mode.
    Filter precedence: run_tag (exact) > since_iso > window_min (now-window) > all rows. Returns a dict
    (also feeds `render`). Never raises on a missing/locked DB — returns {"error": ...}."""
    db = Path(db_path) if db_path else _DEFAULT_DB
    if not db.exists():
        return {"error": f"no attempts DB at {db}", "total": 0}
    if since_iso is None and window_min:
        try:
            from datetime import datetime, timezone, timedelta
            since_iso = (datetime.now(timezone.utc) - timedelta(minutes=window_min)).isoformat()
        except Exception:  # noqa: BLE001
            since_iso = None
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cols = [r[1] for r in c.execute("PRAGMA table_info(attempts)")]
        sel = "move, outcome, error_class, notes, attempt_at" + (", ratified" if "ratified" in cols else "")
        where, args = "", []
        if run_tag and "run_tag" in cols:
            where, args = "WHERE run_tag = ?", [run_tag]
        elif since_iso:
            where, args = "WHERE attempt_at > ?", [since_iso]
        rows = c.execute(f"SELECT {sel} FROM attempts {where} ORDER BY attempt_at", args).fetchall()
        c.close()
    except Exception as e:  # noqa: BLE001
        return {"error": f"query failed: {e}", "total": 0}

    total = len(rows)
    by_move_outcome: Counter = Counter()
    by_class: Counter = Counter()
    structural = 0
    closed = 0
    ratified = 0
    stamps: list = []
    for row in rows:
        move, outcome, ec, notes, at = row[0], row[1], row[2], row[3], row[4]
        rat = row[5] if len(row) > 5 else None
        stamps.append(at)
        by_move_outcome[(move or "?", outcome or "?")] += 1
        if outcome == "closed":
            closed += 1
        if rat in (1, "1", True):
            ratified += 1
        if outcome not in ("closed", "advanced"):
            cls, is_struct = _refine_class(ec, notes)
            by_class[cls] += 1
            if is_struct:
                structural += 1
    fails = sum(by_class.values())
    span = _iso_span_minutes(stamps)
    headline, detail = _classify(total, closed, ratified, fails, structural, by_class, span)
    return {
        "total": total, "closed": closed, "ratified": ratified, "failures": fails,
        "structural_failures": structural, "wall_minutes": (round(span, 1) if span else None),
        "throughput_per_min": (round(total / span, 2) if span and span > 0 else None),
        "by_move_outcome": {f"{m}/{o}": n for (m, o), n in by_move_outcome.most_common()},
        "by_failure_class": dict(by_class.most_common()),
        "headline": headline, "detail": detail,
        "filter": (f"run_tag={run_tag}" if run_tag else (f"since={since_iso}" if since_iso else "ALL")),
    }


def _classify(total, closed, ratified, fails, structural, by_class, span) -> "tuple[str, str]":
    if total == 0:
        return "NO ATTEMPTS", "No move attempts recorded for this filter — the run never reached the solver, or the run_tag/window is wrong."
    if closed > 0:
        return "PRODUCTIVE", f"{closed} closure(s), {ratified} ratified. Lift/quality is in the closures, not this summary."
    struct_frac = (structural / fails) if fails else 0.0
    starved = bool(span and span > 5 and total / span < 0.5)
    top = next(iter(by_class), None)
    top_n = by_class.get(top, 0) if top else 0
    top_frac = (top_n / fails) if fails else 0.0
    if struct_frac >= 0.6:
        msg = (f"{int(struct_frac*100)}% of failures are STRUCTURAL (top: {top} ×{top_n}, {int(top_frac*100)}%) — the "
               f"apparatus isn't getting clean shots at the MATH (scope/context/syntax), NOT genuine difficulty. "
               f"Look at a context/namespace/import bug or a malformed harness feed BEFORE concluding 'hard'.")
        if starved:
            msg += f" ALSO throughput-starved ({total} attempts / {round(span)}min)."
        return "STRUCTURAL-FAIL", msg
    if starved:
        return "STARVED", (f"Only {total} attempts in {round(span)}min ({round(total/span,2)}/min) — wall-clock is "
                           f"eaten by slow dispatch, not move-verify cycles. Few shots on goal regardless of math.")
    if top in ("unsolved_goals", "no_advance", "lemma_no_compose", "tactic_failed", "statement_false"):
        return "GENUINE-HARD", (f"Failures are honest proof gaps (top: {top} ×{top_n}). The apparatus got clean "
                                f"shots and the math/decomposition didn't land — this is real difficulty, not a bug.")
    return "MIXED", f"No single dominant mode (top: {top} ×{top_n}). Inspect by_failure_class."


def render(summary: dict) -> str:
    if summary.get("error"):
        return f"[run-diagnostics] {summary['error']}"
    L = ["", "=" * 72, f"[run-diagnostics] {summary['headline']} — {summary['filter']}", "-" * 72,
         f"  attempts={summary['total']}  closed={summary['closed']}  ratified={summary['ratified']}"
         f"  failures={summary['failures']}  structural={summary['structural_failures']}"]
    if summary.get("wall_minutes") is not None:
        L.append(f"  wall={summary['wall_minutes']}min  throughput={summary['throughput_per_min']}/min")
    if summary.get("by_failure_class"):
        L.append("  failure classes: " + ", ".join(f"{k}×{v}" for k, v in summary["by_failure_class"].items()))
    if summary.get("by_move_outcome"):
        top = list(summary["by_move_outcome"].items())[:8]
        L.append("  move/outcome:    " + ", ".join(f"{k}×{v}" for k, v in top))
    L.append(f"  >> {summary['detail']}")
    L.append("=" * 72)
    return "\n".join(L)


def print_epilogue(*, run_tag=None, since_iso=None, window_min=None, db_path=None) -> dict:
    """Convenience for runners: compute + print + return the summary in one call."""
    s = summarize_run(db_path=db_path, run_tag=run_tag, since_iso=since_iso, window_min=window_min)
    print(render(s), flush=True)
    return s


def _main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Per-run failure-mode diagnostics from solver_lane_attempts.db")
    ap.add_argument("--db", default=None)
    ap.add_argument("--run-tag", default=None)
    ap.add_argument("--since", default=None, help="ISO-8601; rows with attempt_at > this")
    ap.add_argument("--window-min", type=float, default=None, help="last N minutes")
    a = ap.parse_args()
    s = summarize_run(db_path=a.db, run_tag=a.run_tag, since_iso=a.since, window_min=a.window_min)
    print(render(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
