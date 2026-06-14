#!/usr/bin/env python3
"""WorkItem / WorkReceipt — the ONE typed contract for leanmill deliverables (#123; design:
docs/concepts/leanmill_work_items.md). Theorems, theory extensions (defs + API), and manifest
updates are instances of one contract, each completing with a receipt whose legs BIND existing
organs (cert ledger = formal leg; exogenous telemetry = tool leg; consumption stamping = consumer
leg). NO parallel governance: a receipt references organ verdicts, it never re-issues them.

NON-ANTHROPOMORPHIC INVARIANT (operator, 2026-06-13): items form a typed FRONTIER, not a to-do
list — traversal order belongs to the calibrated policy; receipts are machine-consumed first
(next-dispatch context) and human-rendered second (dashboard projection).

  python -m ztare.leanmill.contracts.work_items --selftest
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

WORK_RECEIPTS_LEDGER = "analytics/public/queries/work_receipts.jsonl"   # append-only, repo-relative


class WorkItem(BaseModel):
    """A typed deliverable on the campaign frontier. `conjecture` (#124) is the OPEN kind — it lives in
    the conjecture book (`ztare.leanmill.conjecture_book`) accumulating evidence events until it resolves
    into a `theorem_goal` receipt (proven) or a refutation; the other kinds complete with receipts."""
    kind: Literal["theorem_goal", "theory_extension", "manifest_update", "conjecture"]
    statement: str                       # the deliverable, formal where the kind allows
    residual_class: str = ""             # WHY it exists — the typed obstacle (solver residual / manifest node)
    patterns: "list[str]" = Field(default_factory=list)        # pattern-catalog ids steering the attempt
    anti_patterns: "list[str]" = Field(default_factory=list)   # named guards (anti-pattern / no-good ids)
    consumer_check: str = ""             # the HANDOFF OBLIGATION: what the next consumer must prove/cite/refute
    campaign: str = ""                   # run_tag scope


class WorkReceipt(BaseModel):
    """The completion record — append-only ledgered; legs REFERENCE organ verdicts, never re-issue them."""
    item: WorkItem
    verdict: Literal["completed", "rejected", "gap"]
    formal_leg: dict = Field(default_factory=dict)   # cert ref / compile+integrity verdict / manifest diff
    tool_leg: dict = Field(default_factory=dict)     # exogenous receipts (witness/SOS/abduce), referenced
    consumer_leg: dict = Field(default_factory=dict) # DEFERRED: stamped when a later item consumes this one
    gap_text: str = ""                               # honest-gap localization when verdict == "gap"
    ts: str = ""                                     # caller-supplied (workflow-safe: no ambient clock here)

    def append_to_ledger(self, repo_root: "Path | str") -> Path:
        led = Path(repo_root) / WORK_RECEIPTS_LEDGER
        led.parent.mkdir(parents=True, exist_ok=True)
        with led.open("a", encoding="utf-8") as f:
            f.write(self.model_dump_json() + "\n")
        return led


def stamp_consumer(ledger: Path, *, statement_contains: str, consumed_by: str,
                   evidence: str) -> int:
    """CONSUMER-LEG stamping (the ledger-evidenced-use rule): when a later item cites/builds on an
    earlier deliverable, stamp the earlier receipt. Value is demonstrated by consumption, never
    asserted — a theory_extension whose API is never consumed stays visibly consumer-leg-empty
    (decorative theory, the analogue of a decorative hypothesis). Append-only: emits a stamp
    RECORD rather than rewriting history. Returns the number of receipts matched."""
    try:
        rows = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return 0
    n = 0
    with ledger.open("a", encoding="utf-8") as f:
        for r in rows:
            if r.get("consumer_stamp_for") is not None:
                continue
            if statement_contains in ((r.get("item") or {}).get("statement") or ""):
                f.write(json.dumps({"consumer_stamp_for": (r.get("item") or {}).get("statement", "")[:120],
                                    "consumed_by": consumed_by, "evidence": evidence[:300]}) + "\n")
                n += 1
    return n


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    item = WorkItem(kind="theory_extension", statement="def FormalResidue ...",
                    residual_class="library_gap:residue_theory",
                    patterns=["PATTERN-008"], anti_patterns=["definition_editing"],
                    consumer_check="iso_lemma_residue must cite FormalResidue without re-deriving it",
                    campaign="p1n1_v7")
    rec = WorkReceipt(item=item, verdict="completed",
                      formal_leg={"compile": True, "append_only": True}, ts="2026-06-13T00:00:00+00:00")
    td = Path(tempfile.mkdtemp(prefix="wi_"))
    led = rec.append_to_ledger(td)
    ok("receipt appends to ledger", led.exists() and "FormalResidue" in led.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines()]
    ok("round-trips typed", rows[0]["item"]["kind"] == "theory_extension"
       and rows[0]["item"]["consumer_check"].startswith("iso_lemma_residue"))
    n = stamp_consumer(led, statement_contains="FormalResidue",
                       consumed_by="iso_lemma_residue", evidence="cites FormalResidue in proof")
    ok("consumer-leg stamped by consumption (ledger-evidenced use)", n == 1)
    rows2 = [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines()]
    ok("stamp is append-only (history never rewritten)",
       len(rows2) == 2 and rows2[1].get("consumed_by") == "iso_lemma_residue")
    try:
        WorkItem(kind="bogus", statement="x")
        ok("invalid kind rejected by the contract", False)
    except Exception:
        ok("invalid kind rejected by the contract", True)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
