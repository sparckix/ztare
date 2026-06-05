"""Embedder liveness — positive control for semantic retrieval / amnesia firewalls.

Generalizes the substrate_liveness lesson to the OTHER silent-failure instrument: an embedder
(gemini / openai) returns None on a dead key / quota / network, the consumer degrades to
brittle lexical (or empty), and a 'no neighbour / no prior work / no existing primitive' reads
as a real absence — green-lighting re-derivation and rebuilding (the treadmill the amnesia
firewall exists to prevent). Same bug class as the dead Lean REPL; this is the reusable guard.

Use BEFORE interpreting any 'nothing found' from a semantic layer:

    live, why = embedder_live(lambda t: _embed(t, role="query"), atlas_nonempty=bool(atlas))
    if not live:
        print(liveness_banner(live, why))   # loud; a null is INADMISSIBLE while dead
"""
from __future__ import annotations
from typing import Callable, Optional

DEFAULT_CANARY = "jaccard set similarity overlap divergence"


def embedder_live(
    embed_fn: Callable[[str], "list[float] | None"],
    *,
    canary: str = DEFAULT_CANARY,
    dim_min: int = 8,
    atlas_nonempty: Optional[bool] = None,
) -> "tuple[bool, str]":
    """Positive control: does the embedder return a sane vector for a canary phrase?
    `atlas_nonempty=False` short-circuits (no atlas on disk ⇒ semantic dead regardless)."""
    if atlas_nonempty is False:
        return False, "no atlas on disk (build/embed the atlas first)"
    try:
        v = embed_fn(canary)
    except Exception as e:  # noqa: BLE001
        return False, f"embedder raised: {str(e)[:120]}"
    if not v:
        return False, "embedder returned no vector (missing API key / quota / network)"
    if len(v) < dim_min:
        return False, f"embedder returned a degenerate vector (dim={len(v)})"
    return True, f"live (dim={len(v)})"


def liveness_banner(live: bool, reason: str, *, instrument: str = "semantic embedder") -> str:
    """A loud, fail-closed banner when the instrument is dead; empty string when live.
    Downstream: a 'nothing found' under a dead instrument is INADMISSIBLE, not an absence."""
    if live:
        return ""
    return (f"⚠️  {instrument.upper()} DEAD/UNAVAILABLE: {reason}\n"
            f"    Falling back to lexical/empty. A 'nothing found' result here is "
            f"INADMISSIBLE — it may be a dead instrument, not a real absence. Fix the "
            f"embedder (API key / quota / atlas) before concluding nothing exists or "
            f"re-deriving/rebuilding.")


def _self_test() -> int:
    fails = []
    live, _ = embedder_live(lambda t: [0.1] * 768)
    if not live: fails.append("good embedder should be live")
    live, why = embedder_live(lambda t: None)
    if live or "no vector" not in why: fails.append("None vector must be dead")
    live, _ = embedder_live(lambda t: [0.1] * 3)
    if live: fails.append("degenerate dim must be dead")
    live, why = embedder_live(lambda t: (_ for _ in ()).throw(RuntimeError("boom")))
    if live or "raised" not in why: fails.append("exception must be dead")
    live, _ = embedder_live(lambda t: [0.1] * 768, atlas_nonempty=False)
    if live: fails.append("no-atlas must be dead")
    if liveness_banner(True, "x") != "": fails.append("live ⇒ empty banner")
    if "INADMISSIBLE" not in liveness_banner(False, "x"): fails.append("dead ⇒ loud banner")
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
