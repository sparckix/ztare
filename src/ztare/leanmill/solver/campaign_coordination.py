"""Campaign-lane coordination — multi-node lemma partitioning over the shared work bus.

PHASE B of the distributed-systems slice (Phase A was state convergence: state_convergence.py +
the event-sourced library). This is the ONE adapter that lets several nodes run the SAME campaign
and split its lemmas instead of each re-proving all of them.

WHY THIS IS THIN, NOT A REWRITE
-------------------------------
The discovery lane already runs on `work_queue` (WAL SQLite, leases, node-stamped events). The
proving lane (autoformalize_notes campaigns) did not. This adapter wires the proving lane to the
SAME bus via two CAS primitives (`work_queue.claim_specific` / `finish_specific`): before a node
attacks a lemma it leases it; if another node holds the lease it skips (the result converges via the
fact-log merge, state_convergence — so skipping is correct, never lossy). It is the campaign-lane
CONSUMER of the canonical queue, not a parallel queue.

CONSISTENCY MODEL
-----------------
- Safety comes from Phase A: concurrent campaigns are already CORRECT (the CvRDT union of the fact
  logs dedups results). This adapter adds EFFICIENCY: nodes stop re-proving each other's lemmas.
- The only state needing linearizable compare-and-set is the lease — localized to the single-owner
  queue DB (WAL SQLite on the coordinator), exactly as DDIA prescribes (avoid consensus for the
  facts; localize the one CAS).
- A failed/abandoned lemma is RELEASED back to `queued` (lease expiry or explicit), so another node —
  possibly with a larger proven shelf — retries it. A solved lemma is terminal `done`.

OPT-IN, byte-parity when off: `ZTARE_LEANMILL_DISTRIBUTED_LEMMAS=1` turns it on; otherwise the
campaign runs its in-process loop exactly as before (this module is never consulted).
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ztare.leanmill import work_queue

_KIND = "campaign_lemma"


def distributed_enabled() -> bool:
    """Opt-in gate. Default OFF → the campaign loop is byte-identical to single-node."""
    return os.environ.get("ZTARE_LEANMILL_DISTRIBUTED_LEMMAS") == "1"


def _db_path() -> str:
    """The shared work-bus DB (same store the discovery lane + attempts ledger use)."""
    env = os.environ.get("ZTARE_LEANMILL_QUEUE_DB")
    if env:
        return env
    # src/ztare/leanmill/solver/campaign_coordination.py → parents[4] == repo root
    return str(Path(__file__).resolve().parents[4] / "analytics" / "public" / "queries" / "solver_lane_attempts.db")


def lemma_work_id(campaign: str, lemma: str) -> str:
    """Stable, node-agnostic id for one campaign lemma. Same campaign+lemma → same id on every node
    (so the lease and the INSERT-OR-IGNORE seed dedup), independent of local naming or order."""
    h = hashlib.sha256(f"{campaign}\x1f{(lemma or '').strip()}".encode("utf-8")).hexdigest()[:16]
    return f"camp_lemma__{h}"


def node() -> str:
    return work_queue.node_id()


def claim_lemma(campaign: str, lemma: str, *, lease_s: int, db_path: "str | None" = None) -> bool:
    """Lease this lemma for THIS node. Returns True iff this node should prove it now; False means
    another node holds it (skip — its result converges via the merge). Idempotent: re-claiming a
    lemma this node already holds returns True."""
    p = db_path or _db_path()
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    cx = work_queue.connect(p)
    try:
        wid = lemma_work_id(campaign, lemma)
        work_queue.enqueue(cx, kind=_KIND, priority=0, max_attempts=99,
                           payload={"work_id": wid, "campaign": campaign, "lemma": (lemma or "")[:2000]})
        return work_queue.claim_specific(cx, work_id=wid, worker_id=node(), lease_s=int(lease_s))
    finally:
        cx.close()


def complete_lemma(campaign: str, lemma: str, *, solved: bool, db_path: "str | None" = None) -> bool:
    """Mark this node's leased lemma terminal or release it; ``False`` means its lease was lost."""
    p = db_path or _db_path()
    cx = work_queue.connect(p)
    try:
        wid = lemma_work_id(campaign, lemma)
        return work_queue.finish_specific(cx, work_id=wid, worker_id=node(), done=bool(solved))
    finally:
        cx.close()


def _self_test() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    db = tempfile.mktemp(suffix=".db")
    os.environ["ZTARE_LEANMILL_QUEUE_DB"] = db
    os.environ["ZTARE_LEANMILL_DISTRIBUTED_LEMMAS"] = "1"
    try:
        ok("distributed_enabled honors the flag", distributed_enabled() is True)
        camp = "amm_cpmm_v2"
        lemmas = [f"lemma_{i}" for i in range(6)]

        # stable, distinct work-ids
        ids = {lemma_work_id(camp, l) for l in lemmas}
        ok("work-ids stable+distinct", len(ids) == 6 and lemma_work_id(camp, lemmas[0]) == lemma_work_id(camp, lemmas[0]))

        # simulate two nodes partitioning the same campaign (alternate who reaches each lemma first,
        # as concurrent nodes walking the list would; the other node must then be locked out)
        nA, nB = [], []
        for idx, l in enumerate(lemmas):
            owner = "nodeA" if idx % 2 == 0 else "nodeB"
            other = "nodeB" if idx % 2 == 0 else "nodeA"
            os.environ["LEANMILL_NODE_ID"] = owner
            got = claim_lemma(camp, l, lease_s=300)
            os.environ["LEANMILL_NODE_ID"] = other
            stolen = claim_lemma(camp, l, lease_s=300)
            ok(f"exactly one node owns {l}", got is True and stolen is False)
            (nA if owner == "nodeA" else nB).append(l)
        ok("partition splits the lemmas across both nodes",
           sorted(nA + nB) == sorted(lemmas) and not set(nA) & set(nB) and nA and nB)

        # node A finishes its lemmas (solved) → terminal done → node B cannot claim them
        for l in nA:
            os.environ["LEANMILL_NODE_ID"] = "nodeA"
            ok(f"owner can complete {l}", complete_lemma(camp, l, solved=True) is True)
        os.environ["LEANMILL_NODE_ID"] = "nodeB"
        ok("done lemmas are not re-claimable by another node", all(not claim_lemma(camp, l, lease_s=300) for l in nA))

        # a RELEASED (not solved) lemma returns to the queue → another node can claim it
        if nB:
            relq = nB[0]
            os.environ["LEANMILL_NODE_ID"] = "nodeB"
            ok("owner can release an unsolved lemma", complete_lemma(camp, relq, solved=False) is True)
            os.environ["LEANMILL_NODE_ID"] = "nodeA"
            ok("released (unsolved) lemma is re-claimable by another node", claim_lemma(camp, relq, lease_s=300) is True)

        # idempotent re-claim by the SAME holder
        os.environ["LEANMILL_NODE_ID"] = "nodeA"
        if nA:
            # nA[0] is done now; claim a fresh one to test idempotency
            fresh = "lemma_fresh"
            ok("first claim of fresh lemma", claim_lemma(camp, fresh, lease_s=300) is True)
            ok("idempotent re-claim by same node", claim_lemma(camp, fresh, lease_s=300) is True)
            cx = work_queue.connect(db)
            try:
                fresh_row = cx.execute(
                    "SELECT attempts FROM work_items WHERE work_id=?", (lemma_work_id(camp, fresh),)
                ).fetchone()
                ok("idempotent re-claim does not consume another attempt", fresh_row and fresh_row["attempts"] == 1)
            finally:
                cx.close()
            os.environ["LEANMILL_NODE_ID"] = "nodeB"
            ok("foreign node cannot finalize active lease", complete_lemma(camp, fresh, solved=True) is False)
            os.environ["LEANMILL_NODE_ID"] = "nodeA"
    finally:
        for k in ("ZTARE_LEANMILL_QUEUE_DB", "ZTARE_LEANMILL_DISTRIBUTED_LEMMAS", "LEANMILL_NODE_ID"):
            os.environ.pop(k, None)
        os.path.exists(db) and os.remove(db)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
