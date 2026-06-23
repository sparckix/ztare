---
description: "Review packet: the governance kernel rejecting compiling-but-laundered closures produced by its own agents, with ledger receipts and a runnable check."
---
# Anti-Laundering Catches Packet

> **Up:** [Review Packets](README.md)

## Scoped Claim

LeanMill's governance kernel has rejected, at solve time, proof closures produced by its own
agents that **compiled cleanly but altered the statement being proven** (`statement_altered_confirmed`).
Each rejection is recorded in the append-only closure-certificate ledger with the organ verdict and the
probe context, and the rejected attempt earns no credit anywhere downstream (no ratification, no proof
cache entry, no rung in the notes). The claim is narrow: the gates catch this laundering class when it
occurs; it is not a claim of completeness over all laundering classes (the
[specification-gaming catalog](../../gaming_behavior_catalog.md) tracks the known classes and their gates).

## Evidence Level

L3 — decision-changing in production: each catch withheld credit from a closure that would otherwise
have been banked, during live governed runs (2026-06-10 through 2026-06-12, multiple independent runs).
Not externally reviewed.

## Primary Sources

- [`analytics/public/queries/adhoc_closure_certificates.jsonl`](../../../analytics/public/queries/adhoc_closure_certificates.jsonl)
  — the ledger; rejected entries carry `outcome=rejected_governance` and the kernel's
  `confirmed` flags.
- [`src/ztare/leanmill/solver/statement_integrity.py`](../../../src/ztare/leanmill/solver/statement_integrity.py)
  — the organ that diffs the winning probe against the ORIGINAL definitions (the axis a
  probe-in-isolation audit cannot see).
- [`src/ztare/gates/lean_proof_gate.py`](../../../src/ztare/gates/lean_proof_gate.py) — the one
  anti-laundering kernel (`run_anti_laundering_kernel`) the solve path routes through.
- `solve_adhoc`'s governance block in
  [`src/ztare/leanmill/solver/solver_core.py`](../../../src/ztare/leanmill/solver/solver_core.py) —
  where a confirmed blocker rewrites the outcome to `rejected_governance` and the no-good store
  records the gamed shape for future runs.

## Runnable Anchor

```bash
python3 - <<'PY'
import json
hits = []
for ln in open("analytics/public/queries/adhoc_closure_certificates.jsonl"):
    c = json.loads(ln)
    if c.get("outcome") == "rejected_governance":
        k = (c.get("governance") or {}).get("governance_kernel") or {}
        hits.append((c.get("ts"), c.get("target"), k.get("confirmed")))
for h in hits:
    print(*h)
print(f"{len(hits)} governance rejection(s) on record")
PY
```

A reviewer can additionally recompile any entry's `recompilable_probe` against the pinned toolchain and
re-run `#print axioms` to reproduce the audit context.

## Evidence Summary

The packet's value is governance evidence: a proof attempt can compile and
still be rejected when it changes the statement under proof. The closure ledger
keeps those rejection receipts and the solve path withholds downstream credit.
That makes the catch inspectable after the run instead of relying on a reviewer
remembering a transient agent transcript.

## Non-Claims

- The rejected agents are this repository's own provers; no claim is made about other systems' agents
  (the external-artifact audit, `src/ztare/leanmill/audit_external.py`, extends the same organs to
  third-party proofs but its corpus run is still queued).
- Closure certificates written before 2026-06-12 may lack a recompilable probe (a fixed
  artifact-persistence gap, recorded in the
  [public claim register](../../public_claim_register.md#leanmill-governed-proof-search-and-autoformalization));
  rejection entries are unaffected (the rejection verdict does not depend on the persisted probe).
- Catch completeness is not claimed: these receipts demonstrate the gates fire on the
  statement-alteration class in production, nothing wider.

## Missing Upgrade

A stronger packet would run the same anti-laundering organs on an external
proof-artifact corpus and report the caught/clean split with independently
reviewed statement-integrity labels.
