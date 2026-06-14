"""Learned-context block — surface what leanmill has LEARNED about THIS target into the AGENT's prompt.

The goldilocks bridge (determinism + agentic + self-learning): the deterministic stores compound across runs
(`proof_cache` / `no_good_store` / `move_calibration` / …), but the RICHEST learner — `move_calibration`'s
per-`(move, error_class)` kernel-arbitrated close-rates — is consumed ONLY by the Python scheduler's
`move_policy`; the agent never sees it. So the agent re-derives move choice blind to "native_hammer is 0/29,
warm closes 38% on goals like this." This composes the EXISTING agent-facing learned signals into ONE block the
leaf reads, so the agent's own orchestration is informed by what compounded — not just the scheduler's.

PURE COMPOSITION (the interface verdict: a shared READ interface, NOT a unified store): it reuses
`no_good_store.NoGoodStore.prompt_block` + reads `move_calibration` — it reimplements nothing and adds no store.
The ≥2-consumer bar is met (no-good memo + the move track-record were already two independent prompt-injectors
at the `agentic_leaf` seam; this gives them one contract). DEFAULT-OFF (`ZTARE_LEANMILL_LEARNED_CONTEXT`) is
byte-identical to today's bare no-good injection (the move-stats block is added only flag-on), so it cannot
regress the prompt; flag-on adds the per-error-class (or marginal) move close-rates the agent was blind to.
"""
from __future__ import annotations

import os
from typing import Optional


def _stats_on() -> bool:
    # The NEW agent-facing move-stats surfacing. Default-OFF = byte-parity with the current no-good-only
    # injection; flip =1 to give the agent the apparatus's own kernel-arbitrated move track-record.
    return os.environ.get("ZTARE_LEANMILL_LEARNED_CONTEXT", "0") == "1"


def _move_stats_block(db_path, error_class: "Optional[str]", max_moves: int = 8) -> str:
    """Render the LEARNED per-(error-class, else marginal) move close-rates — the kernel-arbitrated signal the
    scheduler uses but the agent never saw. Empty on no DB / no data (fail-open). Reads `move_calibration`'s
    own aggregation; reimplements nothing. Advisory framing — a prior to spend budget well, never a constraint.

    DATA-ADMISSIBILITY GATE (operator's catch, 2026-06-10): a move's `0/N` is only REAL if that move's CARRIER
    was LIVE for those attempts. The attempts DB is contaminated by pre-carrier-fix rows where native_hammer /
    cold_shot_fanout / external_frontier_prover fed the kernel a never-parsing probe and recorded 0/N as
    DEAD-INSTRUMENT artifacts, not genuine losses (the carrier bug, fixed 2026-06-08; the rows persist).
    Surfacing that would TEACH THE AGENT THE BUG ("never use native_hammer"). So this is SUPPRESSED unless
    `ZTARE_LEANMILL_CALIBRATION_TRUSTED=1` asserts the DB was re-baselined on the fixed apparatus — the
    apparatus_certificate "a negative is inadmissible without calibration" rule, applied to the LEARNING DATA."""
    if os.environ.get("ZTARE_LEANMILL_CALIBRATION_TRUSTED") != "1":
        return ""                                  # contaminated DB ⇒ never teach the agent dead-instrument 0/Ns
    try:
        from ztare.leanmill.solver.move_calibration import _cells_from_db
        per_cell, per_move = _cells_from_db(db_path)
    except Exception:  # noqa: BLE001 — DB absent/locked/unmigrated ⇒ no learned stats (fail-open)
        return ""
    rows: "list[tuple[str, int, int]]" = []
    scope = ""
    if error_class:
        rows = [(m, c, t) for (m, ec), (c, t) in per_cell.items() if ec == error_class and t > 0]
        scope = f"error-class «{error_class}»"
    if not rows:                                   # unknown / unseen class ⇒ fall back to the marginal per-move
        rows = [(m, c, t) for m, (c, t) in (per_move or {}).items() if t > 0]
        scope = "all attempts so far"
    if not rows:
        return ""
    rows.sort(key=lambda r: (-(r[1] / r[2]) if r[2] else 0.0, -r[2]))   # best close-rate first, then most data
    lines = [f"-- 📊 LEARNED move track-record ({scope}) — the apparatus's OWN kernel-arbitrated close-rates "
             "(a caught cheat counts as a loss). Prefer what has CLOSED; don't burn budget on dead moves. "
             "Advisory, not a constraint:"]
    for m, c, t in rows[:max_moves]:
        lines.append(f"--   {m}: {c}/{t} closed ({100.0 * c / t:.0f}%)")
    return "\n".join(lines)


def render(goal: str, error_class: "Optional[str]" = None, *,
           no_good_path=None, db_path=None) -> str:
    """The ONE learned-context block injected into the leaf prompt. Composes (in order): the CONFIRMED
    prior-refutation memo for this exact goal (`no_good_store`, gated by `ZTARE_LEANMILL_NOGOOD`, default-on —
    parity with today's injection), then — flag-on (`ZTARE_LEANMILL_LEARNED_CONTEXT`) — the learned move
    track-record. Best-effort: any store error yields a shorter block, never raises. Returns "" if nothing
    learned applies (the caller appends unconditionally)."""
    blocks: "list[str]" = []
    if os.environ.get("ZTARE_LEANMILL_NOGOOD") != "0" and no_good_path is not None:
        try:
            from ztare.leanmill.solver.no_good_store import NoGoodStore
            ng = NoGoodStore(no_good_path).prompt_block(goal)
            if ng:
                blocks.append(ng)
        except Exception:  # noqa: BLE001 — informing is best-effort; never fail the solve
            pass
    if _stats_on() and db_path is not None:
        ms = _move_stats_block(db_path, error_class)
        if ms:
            blocks.append(ms)
    return "\n\n".join(blocks)


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    import ztare.leanmill.solver.learned_context as LC
    import ztare.leanmill.solver.move_calibration as MC

    # fixture: warm 11/29 (38%) on the class, native_hammer 0/29 (0%); marginal mirrors it
    per_cell = {("claude_warm", "exact_gap"): (11, 29), ("native_hammer", "exact_gap"): (0, 29)}
    per_move = {"claude_warm": (11, 29), "native_hammer": (0, 29)}
    _orig = MC._cells_from_db
    MC._cells_from_db = lambda db: (per_cell, per_move)                 # type: ignore
    os.environ.pop("ZTARE_LEANMILL_CALIBRATION_TRUSTED", None)
    try:
        ok("contaminated DB (no CALIBRATION_TRUSTED) ⇒ move-stats SUPPRESSED (don't teach the agent a bug)",
           LC._move_stats_block("X", "exact_gap") == "")
        os.environ["ZTARE_LEANMILL_CALIBRATION_TRUSTED"] = "1"          # assert re-baselined (test only)
        blk = LC._move_stats_block("X", "exact_gap")
        ok("move-stats renders the per-class close-rates (when DB trusted)", "claude_warm: 11/29 closed (38%)" in blk
           and "native_hammer: 0/29 closed (0%)" in blk)
        ok("move-stats orders best-close-rate first", blk.index("claude_warm") < blk.index("native_hammer"))
        ok("unknown class ⇒ falls back to the marginal (non-empty)",
           "all attempts so far" in LC._move_stats_block("X", "no_such_class"))

        # PARITY: with LEARNED_CONTEXT off, render returns EXACTLY the no-good block (the move-stats are absent)
        os.environ.pop("ZTARE_LEANMILL_LEARNED_CONTEXT", None)
        import ztare.leanmill.solver.no_good_store as NG
        _op = NG.NoGoodStore.prompt_block
        NG.NoGoodStore.prompt_block = lambda self, g, max_items=4: "-- ⚠ PRIOR REFUTED: x"   # type: ignore
        try:
            off = LC.render("g", "exact_gap", no_good_path="dummy", db_path="X")
            ok("flag OFF ⇒ only the no-good block (byte-parity with today)", off == "-- ⚠ PRIOR REFUTED: x")
            os.environ["ZTARE_LEANMILL_LEARNED_CONTEXT"] = "1"
            on = LC.render("g", "exact_gap", no_good_path="dummy", db_path="X")
            ok("flag ON ⇒ no-good block + the learned move track-record",
               "PRIOR REFUTED" in on and "LEARNED move track-record" in on)
            # NOGOOD=0 + stats on ⇒ only the stats (no-good suppressed)
            os.environ["ZTARE_LEANMILL_NOGOOD"] = "0"
            only = LC.render("g", "exact_gap", no_good_path="dummy", db_path="X")
            ok("NOGOOD=0 + stats on ⇒ only the learned track-record",
               "PRIOR REFUTED" not in only and "LEARNED move track-record" in only)
        finally:
            NG.NoGoodStore.prompt_block = _op                          # type: ignore
            os.environ.pop("ZTARE_LEANMILL_NOGOOD", None)
            os.environ.pop("ZTARE_LEANMILL_LEARNED_CONTEXT", None)
    finally:
        MC._cells_from_db = _orig                                      # type: ignore
        os.environ.pop("ZTARE_LEANMILL_CALIBRATION_TRUSTED", None)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
