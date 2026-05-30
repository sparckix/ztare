#!/usr/bin/env python3
"""governance_in_context.py — THE single authoritative verifier.

False-positive-protocol #1 (operator-mandated 2026-05-18): exactly one
authoritative gate; no experiment defines its own "solved". This is
that gate, for leak-tight in-place-`sorry` rows (which only compile in
their real source-file module context — the lighter codex-pilot
`_verify` did NOT kernel-audit axioms; this does).

Given a sorried leak-tight file + target line + a candidate proof
block, it: substitutes the block for the `sorry` IN THE REAL MODULE
CONTEXT, elaborates via the persistent REPL, and returns one verdict —
  closure | axiom_smuggled | unverified | open
with the injected audit frontier bound in, and PERSISTS every ratified
closure (proof + audit + manifest) for post-hoc audit. The producer
can only obtain a verdict here; it can never write "closure" itself
(two-scoreboard, GP-241 no-self-bless applied to experiments).

Verdict rules (pre-registered, may not be relaxed post hoc):
  - any error on/after target line, or nearby `sorry` -> unverified/open
  - `sorryAx` or explicit local axiom-like decl       -> axiom_smuggled
  - else                                             -> closure (persisted)
Result self-carries provenance (#5): {verdict, axioms_deps,
persisted_path, verified_by}.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import authoritative_axioms as _AX  # noqa: E402

_STD = {"propext", "Classical.choice", "Quot.sound"}
_PERSIST = Path("/tmp/rung1/ratified_proofs")


def govern_in_context(L, sorried_file: str, target_line: int,
                      target_name: str, proof_block: str,
                      timeout: int = 120) -> dict:
    """L: PersistentLean. Authoritative, in-module-context."""
    blk = re.sub(r"^```\w*|```$", "", proof_block, flags=re.M).strip()
    if not blk or any(b in blk for b in
                      ("sorry", "admit", "native_decide", "axiom ")):
        return {"verified_by": _AX._VERIFIER, "verdict": "open",
                "axioms_deps": None, "persisted_path": None,
                "reason": "proof_block_empty_or_banned_token"}
    try:
        src = Path(sorried_file).read_text(errors="ignore")
    except Exception:
        return {"verified_by": _AX._VERIFIER, "verdict": "unverified",
                "axioms_deps": None, "persisted_path": None,
                "reason": "sorried_file_read_failed"}
    # substitute proof for the sorry, in the REAL module source; the
    # authoritative verifier does validity in true module context +
    # the in-module collectAxioms audit. NO #print axioms is appended
    # here (that was the module-incompatibility bug).
    new = re.sub(r":=\s*by\s*\n\s*sorry",
                 ":= by\n  " + blk.replace("\n", "\n  "), src, count=1)
    r = _AX.govern(L, new, target_line, target_name, timeout)
    # preserve this module's historical return key (`persisted_path`)
    return {"verified_by": r.get("verified_by"),
            "verdict": r.get("verdict"),
            "axioms_deps": r.get("axioms_deps"),
            "persisted_path": r.get("persisted"),
            "reason": r.get("reason")}


if __name__ == "__main__":
    # machine-safe logic self-test (mock REPL; NO Lean)
    _AX.isolate_selftest_ledger()   # never pollute the real ledger
    class _Mk:
        def __init__(self, msgs, sorries=None):
            self._m, self._s = msgs, sorries or []

        def open_file(self, p, timeout=120):
            return {"ok": True, "messages": self._m,
                    "errors": [m for m in self._m
                               if str(m.get("severity")) == "error"],
                    "sorries": self._s}

    clean = _Mk([{"severity": "info",
                  "data": "'foo' depends on axioms: [propext, "
                  "Classical.choice, Quot.sound]"}])
    r = govern_in_context(clean, "/dev/null", 1, "foo",
                           "exact trivial")
    print("clean ->", r["verdict"], r["axioms_deps"],
          "(expect closure)")
    smug = _Mk([{"severity": "info",
                 "data": "'foo' depends on axioms: [sorryAx, propext]"}])
    r2 = govern_in_context(smug, "/dev/null", 1, "foo", "exact bar")
    print("smuggled ->", r2["verdict"], "(expect axiom_smuggled)")
    bad = _Mk([{"severity": "error", "data": "type mismatch"}])
    r3 = govern_in_context(bad, "/dev/null", 1, "foo", "exact bar")
    print("error ->", r3["verdict"], "(expect open)")
    r4 = govern_in_context(clean, "/dev/null", 1, "foo",
                           "exact bar -- sorry")
    print("banned-token ->", r4["verdict"], "(expect open)")
    assert (r["verdict"], r2["verdict"], r3["verdict"], r4["verdict"]) \
        == ("closure", "axiom_smuggled", "open", "open")
    print("governance_in_context logic self-test PASS "
          "(mock; live run uses real PersistentLean)")
