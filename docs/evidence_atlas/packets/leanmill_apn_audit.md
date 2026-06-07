---
description: "Evidence packet for the LeanMill APN audit and proof-governance discipline."
---
# LeanMill APN Audit Packet

> **Up:** [Evidence Packets](README.md)

## Scoped Claim

ZTARE has a public proof-governance audit packet for eight published
AlphaProof Nexus AICollaborator bare-Mathlib proofs, separating kernel
cleanliness, toolchain pinning, top-level anti-laundering checks, helper-level
advisory flags, and non-claims.

## Evidence Level

L3-L4 for audit/governance discipline. Not a theorem-prover performance claim.

## Primary Sources

- [Public claim register, F103](../../public_claim_register.md#gp-245-forecast-calibration-program-llm-forecasting-channels--operationalization)
- [APN audit summary](../../../analytics/public/queries/lane_b_apn_audit_summary.md)
- [APN audit receipts](../../../analytics/public/queries/lane_b_apn_audit_receipts.json)
- [LeanMill architecture](../../concepts/leanmill_architecture.md)
- [Closure-claim governance](../../concepts/closure_claim_governance.md)

## Runnable Anchor

```bash
lake build
```

`lake build` checks the local Lean workspace. It is not, by itself, the APN
sidecar audit. The APN packet's primary public evidence is the audit summary
and receipts.

## Evidence Summary

The public APN audit summary reports that all eight audited proofs compile
kernel-clean at the pinned v4.27 toolchain, use only allowlisted kernel axioms,
and are top-level L3-clean. It also records the important caveats: several
proofs are pinned-toolchain-only under native v4.30, helper-level
`gold_name_verbatim` flags are advisory rather than proof defects, and the
proofs largely compose existing Mathlib lemmas.

Here "L3-clean" is LeanMill proof-audit vocabulary, not the atlas evidence
level. The packet as a whole is L3-L4 in the atlas sense because it is a
decision-changing audit/governance packet with public receipts and controls.

## Non-Claims

- No claim that DeepMind or APN published fake proofs.
- No claim that LeanMill has a public miniF2F result.
- No claim that planner memory improves natural Mathlib proof closure.
- No claim that library-composition proofs have high novel-math content.

## Missing Upgrade

A stronger LeanMill packet needs either:

- a named public benchmark against baselines; or
- one externally reviewed proof artifact with complete receipts.

Until then, public LeanMill claims should stay scoped to audit/governance
discipline and proof-credit boundaries.
