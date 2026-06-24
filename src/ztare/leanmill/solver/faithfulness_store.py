"""Faithfulness store — the FAITHFULNESS DUAL of `no_good_store` / `proof_cache` (the 10x the 2026-06-10
3-axis self-learning inventory found missing).

`proof_cache` memoizes verified PROOFs; `no_good_store` memoizes confirmed REFUTATIONS; this memoizes
confirmed FAITHFULNESS CORRESPONDENCES (NL ↔ the agreed formal statement) + cross-substrate CONFLICTS
(known mistranslation traps). The inventory's headline: the autoformalize / faithfulness axis is the ONLY
axis that learns NOTHING persistent — every firewall verdict (compile / round-trip / cross-vote kernel-
equivalence cliques / structural fingerprint) is recomputed COLD and discarded, even though the cross-vote
leg pays N cold Mathlib `↔` compiles each time, and `structural_faithfulness` runs in NO-OP advisory mode
because production never feeds it a stored reference (`autoformalize.py:221-222`). This store is the cached
dual:

  • a re-seen NL recalls its AGREED faithful statement (skip re-dispatching the formalizer panel);
  • `reference(nl)` feeds `structural_faithfulness(expected=...)` its stored fingerprint so the silent-
    weakening guard runs LOAD-BEARING instead of advisory-True;
  • a recorded cross-substrate `faithfulness_conflict` (from `cross_substrate_consensus`) is a translation-
    bug MEMO — "this NL has a known mistranslation trap" — the faithfulness analogue of a no-good.

EXTENSION POINT (cited, NOT a parallel build): sits beside `proof_cache.py` / `no_good_store.py` in the
solver package, mirrors their JSONL load/append idiom + the CONFIRMED-only soundness invariant. Store file
`OUT_DIR/solver_lane_faithfulness_store.jsonl`. It INFORMS generation (recall + reference + prompt_block); it
NEVER admits or blocks — the firewall's kernel legs remain the SOLE faithfulness arbiter, so even an
over-broad NL key can at worst surface a stale reference, never admit an unfaithful statement.

SOUNDNESS (mirrors no_good_store's CDCL discipline): record a correspondence ONLY when the firewall
CONFIRMED it faithful (`confirmed=True`) — a flaky/advisory admit is INADMISSIBLE (the standing rule: a
verdict is inadmissible without calibration). The selftest ships the POSITIVE control (a confirmed
correspondence recorded + recalled) AND the NEGATIVE control (an unconfirmed admit is NOT recorded) through
the SAME code path before anything consumes the store.

  python -m ztare.leanmill.solver.faithfulness_store --selftest
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def nl_key(nl: str) -> str:
    """The retrieval key for a natural-language claim — lowercase, whitespace-collapsed, stripped of
    surrounding punctuation (so a trivial paraphrase still hits). Coarse ON PURPOSE: the firewall re-checks
    faithfulness on a hit, so an over-broad key only ever surfaces a stale reference, never admits a wrong one."""
    return re.sub(r"\s+", " ", (nl or "").strip().lower()).strip(" .;:!?")


class FaithfulnessStore:
    """Persistent JSONL store of {nl_key -> [confirmed correspondence | conflict records]}. Append-only on
    disk (an audit trail); deduped in memory on (key, kind, statement|distinguishing). Mirrors `NoGoodStore`."""

    def __init__(self, path: "str | Path"):
        self.path = Path(path)
        self._mem: "dict[str, list[dict]]" = {}
        self._seen: set = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self._index(json.loads(line))
                    except Exception:  # noqa: BLE001
                        continue

    def _index(self, rec: dict) -> bool:
        key = rec.get("key")
        sig = (key, rec.get("kind"), rec.get("statement") or rec.get("distinguishing"))
        if not key or sig in self._seen:
            return False
        self._seen.add(sig)
        self._mem.setdefault(key, []).append(rec)
        return True

    def _append(self, rec: dict) -> bool:
        if not self._index(rec):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True

    def record(self, nl: str, statement: str, *, confirmed: bool, fingerprint=None, source: str = "") -> bool:
        """Record a CONFIRMED faithful correspondence NL→statement (the firewall ADMITTED it). CONFIRMED-only —
        a flaky/advisory admit is INADMISSIBLE. `fingerprint` is the agreed statement's structural fingerprint
        (for the load-bearing reference check). Returns whether newly stored."""
        if not confirmed or not (nl or "").strip() or not (statement or "").strip():
            return False
        return self._append({"key": nl_key(nl), "kind": "faithful", "nl": (nl or "")[:400],
                             # 4000 (was 600): keep the FULL statement so the #105 prior-confirmed short-circuit
                             # can EXACT-match a re-seen statement (a real RatFunc/Polynomial target exceeds 600).
                             "statement": statement.strip()[:4000], "fingerprint": fingerprint, "source": source})

    def record_conflict(self, nl: str, substrates: "list[str]", distinguishing: str, *, source: str = "") -> bool:
        """Record a cross-substrate FAITHFULNESS CONFLICT — ≥2 substrates disagreed on the same NL claim ⇒ a
        localized mistranslation (a 'do not trust a naive rendering here' memo). Disagreement IS the exogenous
        confirmation, so no separate `confirmed` flag is needed."""
        if not (nl or "").strip():
            return False
        return self._append({"key": nl_key(nl), "kind": "conflict", "nl": (nl or "")[:400],
                             "substrates": list(substrates or []), "distinguishing": (distinguishing or "")[:300],
                             "source": source})

    def reference(self, nl: str) -> "dict | None":
        """The stored faithful reference for an NL (the most-recent confirmed correspondence NOT marked
        kernel-FALSE): {statement, fingerprint}. Feeds `structural_faithfulness(expected=...)` so its silent-
        weakening guard runs LOAD-BEARING (vs the production no-op) and lets a re-seen NL skip re-formalization.
        EXCLUDES any rendering the ONE refutation ledger (`NoGoodStore`, failure class `statement_false`, keyed by
        the canonical statement normalizer) marked kernel-FALSE — a refuted faithful-but-false reference must
        never gate a STRENGTHENED reformalization (else the firewall rejects the corrected statement: the
        operator-caught false-negative). Single source of refutations — NO parallel store here. None if unseen or
        every confirmed rendering has since been refuted."""
        recs = [r for r in self._mem.get(nl_key(nl), []) if r.get("kind") == "faithful"]
        if not recs:
            return None
        _refuted = self._refuted_keys()
        if not _refuted:
            r = recs[-1]
            return {"statement": r.get("statement"), "fingerprint": r.get("fingerprint")}
        try:
            from ztare.leanmill.solver.proof_cache import _key_for as _kf
        except Exception:  # noqa: BLE001 — no normalizer ⇒ can't exclude; return the latest (advisory store)
            r = recs[-1]
            return {"statement": r.get("statement"), "fingerprint": r.get("fingerprint")}
        for r in reversed(recs):                       # most-recent confirmed correspondence not refuted
            if _kf(r.get("statement") or "") not in _refuted:
                return {"statement": r.get("statement"), "fingerprint": r.get("fingerprint")}
        return None

    def refuted_literal(self, nl: str) -> str:
        """The kernel-REFUTED literal rendering for an NL — a correspondence once admitted faithful, now marked
        `statement_false` in the one refutation ledger. This is BOTH the LICENSE (its existence proves the
        literal NL claim is kernel-false) AND the comparand for a disclosed strengthening (the firewall checks
        the strengthened candidate ADDS hypotheses + preserves the conclusion vs THIS). "" when the literal was
        never refuted (⇒ no license ⇒ the firewall stays strict). The license is non-fakeable: it exists only
        because a kernel ¬G was recorded at the single refutation chokepoint."""
        recs = [r for r in self._mem.get(nl_key(nl), []) if r.get("kind") == "faithful"]
        if not recs:
            return ""
        refuted = self._refuted_keys()
        if not refuted:
            return ""
        try:
            from ztare.leanmill.solver.proof_cache import _key_for as _kf
        except Exception:  # noqa: BLE001
            return ""
        for r in reversed(recs):
            if _kf(r.get("statement") or "") in refuted:
                return r.get("statement") or ""
        return ""

    def _refuted_keys(self) -> set:
        """The normalized-statement keys the ONE refutation ledger (`NoGoodStore`) marked kernel-FALSE (failure
        class `statement_false`) — consulted by `reference()` so a refuted rendering never gates. Lazy + cached;
        fail-open to empty (the consult is advisory). Same store + canonical key the proof_cache uses — one
        ledger, no parallel surface."""
        cached = getattr(self, "_refuted_cache", None)
        if cached is not None:
            return cached
        keys: set = set()
        try:
            from ztare.leanmill.solver.no_good_store import NoGoodStore
            keys = NoGoodStore(self.path.parent / "solver_lane_no_good_store.jsonl").statement_false_keys()
        except Exception:  # noqa: BLE001 — refutation-ledger consult is advisory; never break the reference
            keys = set()
        self._refuted_cache = keys
        return keys

    def conflicts(self, nl: str) -> "list[dict]":
        return [r for r in self._mem.get(nl_key(nl), []) if r.get("kind") == "conflict"]

    def prompt_block(self, nl: str, max_items: int = 3) -> str:
        """Agent-facing: a KNOWN-FAITHFUL rendering to anchor on + any KNOWN mistranslation traps for this NL.
        INFORMS the formalizer; the firewall still re-checks (this can never admit an unfaithful statement)."""
        ref = self.reference(nl)
        confs = self.conflicts(nl)[:max_items]
        if not ref and not confs:
            return ""
        lines: "list[str]" = []
        if ref:
            lines.append("PRIOR FAITHFUL RENDERING (anchor on this exact statement if it matches the NL):")
            lines.append("  " + (ref.get("statement") or ""))
        if confs:
            lines.append("KNOWN MISTRANSLATION TRAP(S) on this claim — an independent substrate disagreed:")
            for c in confs:
                lines.append(f"  - {', '.join(c.get('substrates') or [])}: {c.get('distinguishing')}")
        return "\n".join(lines) + "\n"

    def stats(self) -> dict:
        n_f = sum(1 for v in self._mem.values() for r in v if r.get("kind") == "faithful")
        n_c = sum(1 for v in self._mem.values() for r in v if r.get("kind") == "conflict")
        return {"n_keys": len(self._mem), "faithful": n_f, "conflict": n_c}

    def __len__(self):
        return sum(len(v) for v in self._mem.values())


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as d:
        store = FaithfulnessStore(Path(d) / "fs.jsonl")
        NL = "For all natural numbers a and b, a + b = b + a."
        STMT = "theorem t (a b : ℕ) : a + b = b + a := by sorry"

        # POSITIVE control: a CONFIRMED correspondence is recorded + recalled
        ok("records a confirmed faithful correspondence",
           store.record(NL, STMT, confirmed=True, fingerprint={"conclusion_op": "eq"}, source="firewall"))
        ref = store.reference(NL)
        ok("reference() recalls the agreed statement + fingerprint (the load-bearing feed)",
           ref is not None and ref["statement"] == STMT and ref["fingerprint"] == {"conclusion_op": "eq"})
        ok("a whitespace/case paraphrase of the NL hits the SAME key (coarse retrieval)",
           store.reference("  For All Natural Numbers A And B, A + B = B + A  ") is not None
           and store.reference("a different claim about prime factorization") is None)

        # NEGATIVE control: an UNCONFIRMED admit is NOT recorded (the inadmissible-without-calibration rule)
        ok("an UNCONFIRMED admit is refused (not recorded)",
           not store.record("some other claim", "theorem u : True := by sorry", confirmed=False))
        ok("the refused unconfirmed claim is absent", store.reference("some other claim") is None)

        # CONFLICT: a cross-substrate disagreement becomes a mistranslation-trap memo
        ok("records a cross-substrate faithfulness conflict",
           store.record_conflict(NL, ["lean", "smt_z3"], "z3: sat at a=0,b=1 (the rendering dropped a hypothesis)"))
        ok("conflicts() recalls the trap", len(store.conflicts(NL)) == 1)

        # prompt_block surfaces BOTH the faithful anchor and the trap to the agent
        blk = store.prompt_block(NL)
        ok("prompt_block surfaces the faithful anchor + the trap",
           "PRIOR FAITHFUL RENDERING" in blk and "MISTRANSLATION TRAP" in blk and "z3: sat" in blk)

        # persistence: a fresh store reloads from disk
        store2 = FaithfulnessStore(Path(d) / "fs.jsonl")
        ok("reloads from JSONL (persistent across process)", store2.reference(NL) is not None)
        ok("dedup: re-recording the same correspondence is a no-op",
           not store2.record(NL, STMT, confirmed=True, fingerprint={"conclusion_op": "eq"}))
        ok("stats: 1 faithful + 1 conflict", store2.stats()["faithful"] == 1 and store2.stats()["conflict"] == 1)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
