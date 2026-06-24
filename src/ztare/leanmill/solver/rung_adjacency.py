#!/usr/bin/env python3
"""Rung-adjacency attack prioritization (#121) — transport of the Kossel–Stranski kink-site mechanism
(crystal growth: lattices grow by attachment at maximum-coordination sites, not by high-barrier 2D
nucleation; surfaced by the 2026-06-12 research-isomorphism run on the library-building seam).

THE POLICY: among an audited decomposition's sub-lemmas, attack FIRST the ones with the highest
identifier-level COORDINATION to rungs the kernel has ALREADY closed (the durable cert ledger) — the
"attachment sites" where proven infrastructure, banked proofs and the retrieval shelf give the leaf the
most purchase per token. The deep isolated crux ("2D nucleation" — v3 burned 91 min on exactly this
shape) is attempted LAST, by which point its neighbours may have closed and lowered its barrier.

GOLDILOCKS SPLIT: this module is DETERMINISTIC and changes only the attack ORDER (budget efficiency)
plus an ADVISORY planner block — never WHAT is provable (each sub-lemma is solved independently against
the preamble; the composite kernel gate is untouched) and never the agent's strategic choices. Sound by
construction; ZTARE_LEANMILL_RUNG_ADJACENCY=0 reverts to planner (foundational-first) order.

The overlap score is a heuristic SIGNAL (shared significant identifiers), not a parser of record —
the canonical decl parsing stays in `statement_integrity`/`lean_source`.

  python -m ztare.leanmill.solver.rung_adjacency --selftest
"""
from __future__ import annotations

import os
import re
from typing import Optional

# Lean structural keywords + ubiquitous types: shared occurrences carry no adjacency information.
_STOP = frozenset({
    "theorem", "lemma", "example", "sorry", "admit", "Type", "Prop", "Sort", "where", "with", "fun",
    "match", "deriving", "instance", "structure", "inductive", "noncomputable", "variable", "open",
    "import", "namespace", "section", "attribute", "private", "protected", "partial", "mutual",
})


def identifier_tokens(stmt: str) -> "set[str]":
    """Significant identifiers (≥4 chars, dotted names kept whole) minus structural keywords."""
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_.']{3,}", stmt or "")) - _STOP


def adjacency_scores(candidates: "list[str]", proven_stmts: "list[str]") -> "list[float]":
    """Per-candidate coordination with the proven-rung vocabulary: |tokens ∩ proven-vocab| / |tokens|.
    0.0 for a candidate sharing nothing (the isolated 2D-nucleation shape)."""
    vocab: "set[str]" = set()
    for s in proven_stmts:
        vocab |= identifier_tokens(s)
    out: "list[float]" = []
    for c in candidates:
        t = identifier_tokens(c)
        out.append(round(len(t & vocab) / len(t), 4) if t else 0.0)
    return out


def attack_order(candidates: "list[str]", proven_stmts: "list[str]") -> "list[int]":
    """Indices of `candidates` in attack order: DESCENDING adjacency; ties keep the planner's
    (foundational-first) order — a STABLE reorder, so with no proven rungs it is the identity."""
    sc = adjacency_scores(candidates, proven_stmts)
    return [i for i in sorted(range(len(candidates)), key=lambda i: (-sc[i], i))]


def proven_statements(*, ledger: "Optional[object]" = None) -> "list[str]":
    """All-time integrity-VERIFIED kernel-closed rung statements from the durable cert ledger.
    REUSES `deep_closures_since` (the one ledger reader) with an epoch watermark — no parallel parser."""
    try:
        from ztare.leanmill.solver.autoformalize_notes import deep_closures_since
        rows = deep_closures_since("", ledger=ledger) if ledger is not None else deep_closures_since("")
        return [d["statement"] for d in rows if d.get("statement") and not d.get("integrity_unverified")]
    except Exception:  # noqa: BLE001 — advisory signal; no rungs ⇒ identity order (parity)
        return []


def render_adjacency_block(proven_stmts: "list[str]", *, goal: str = "", k: int = 8) -> str:
    """ADVISORY planner-prompt block: name the proven attachment sites so the agent can decompose TOWARD
    them (it still decides). Empty string when there is nothing proven (byte-parity).

    RELEVANCE-RANKED (2026-06-24): surface the proven rungs whose identifiers most OVERLAP the GOAL — the
    attachment sites the agent is actually likely to cite — instead of merely the k most RECENT, which silently
    HID the relevant banked atoms behind newer unrelated closures (the APR `waterfallDistribution_*` lemmas were
    banked all-time but never surfaced, so the planner re-derived from scratch). Reuses the module's own
    `identifier_tokens` overlap signal (same one driving attack-order); falls back to recency (last-k) when no
    goal is supplied — byte-parity. Still advisory + deterministic: it only changes WHICH proven sites are NAMED;
    the agent decides the decomposition and the kernel audits every lemma."""
    if not proven_stmts:
        return ""
    gtok = identifier_tokens(goal) if goal else set()
    if gtok:
        ranked = sorted(enumerate(proven_stmts),
                        key=lambda iz: (-len(identifier_tokens(iz[1]) & gtok), iz[0]))
        relevant = [s for _i, s in ranked if identifier_tokens(s) & gtok]
        chosen = (relevant or list(proven_stmts[-k:]))[:k]
    else:
        chosen = list(proven_stmts[-k:])
    heads = [s[:140] for s in chosen]
    return ("PROVEN-RUNG ATTACHMENT SITES (kernel-closed infrastructure you can CITE; prefer sub-lemmas "
            "that attach to these over isolated deep ones — proven neighbours lower the barrier):\n"
            + "\n".join(f"  • {h}" for h in heads) + "\n\n")


def enabled() -> bool:
    return os.environ.get("ZTARE_LEANMILL_RUNG_ADJACENCY", "1") != "0"


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    proven = ["theorem r1 : PowerSeries.derivativeFun f * Polynomial.eval₂ (algebraMap ℚ X) = y",
              "theorem r2 : RatFunc.num q ≠ 0"]
    cands = ["lemma a : ∀ z, Finset.sum z = 0",                                  # no overlap (isolated)
             "lemma b (f : PowerSeries ℚ) : PowerSeries.derivativeFun f = f",   # high overlap
             "lemma c : RatFunc.num p = Polynomial.eval₂ q r"]                  # medium overlap
    sc = adjacency_scores(cands, proven)
    ok("isolated candidate scores 0", sc[0] == 0.0)
    # c's tokens are ALL proven identifiers (2/2 = 1.0) > b (1/2) — full attachment beats partial
    ok("coordination ordering: full attachment > partial > isolated", sc[2] > sc[1] > sc[0])
    order = attack_order(cands, proven)
    ok("attack order = descending adjacency (c, b, a)", order == [2, 1, 0])
    ok("no proven rungs ⇒ identity order (parity)", attack_order(cands, []) == [0, 1, 2])
    ok("ties keep planner order (stable)", attack_order(["lemma x : A1", "lemma y : A2"], []) == [0, 1])
    blk = render_adjacency_block(proven)
    ok("advisory block names the rungs", "ATTACHMENT SITES" in blk and "derivativeFun" in blk)
    ok("no rungs ⇒ empty block (byte-parity)", render_adjacency_block([]) == "")
    ok("keywords are not signal", "theorem" not in identifier_tokens("theorem foo : Type"))
    # ledger leg (hermetic): reuse the deep_closures_since reader with a temp ledger
    import json
    import tempfile
    from pathlib import Path
    td = Path(tempfile.mkdtemp(prefix="radj_"))
    led = td / "c.jsonl"
    led.write_text(json.dumps({"ts": "2026-06-12T00:00:00+00:00", "target": "t1", "outcome": "closed",
                               "recompilable_probe": "import Mathlib\n\ntheorem t1 : 1 = 1 := by rfl\n",
                               "governance": {}}) + "\n"
                   + json.dumps({"ts": "2026-06-12T00:00:01+00:00", "target": "t2", "outcome": "closed",
                                 "recompilable_probe": "", "governance": {"integrity_unverified": True}})
                   + "\n", encoding="utf-8")
    pv = proven_statements(ledger=led)
    ok("ledger leg: verified rung in, unverified rung EXCLUDED",
       len(pv) == 1 and pv[0].startswith("theorem t1"))
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
