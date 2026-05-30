# GP-158 V5 Cage Orchestrator Audit — Public Claim Summary

> Public-evidence surface for the v5 cage-orchestrator design audit.
> Working directory private; cited by `docs/public_claim_register.md`
> under *Apparatus Self-Audits*.

## Claim

Six concrete v5.0 cage-orchestrator design defects were identified by
applying the reflexive-primitive rules (R1–R4) to the design
documents. Each defect is tied to an observable property in the
prose specification (line-anchored), so the audit survives a `grep
-diff` against the current repo and is not theoretical. Example
defect (#1, REACHABILITY GAP IN DISPATCHER): the `cage.dispatch.can_handle`
predicate's reference implementation at lines 313–325 of the internal
v5 super-architecture map fails the R1 reachability rule on a named
input class. Apparatus-internal champion score: **82 / 100**.

## What this audits

The audit verifies that the *orchestration layer* maintains contract
invariants across loop iterations — i.e., that the cage stays a cage
under the runtime orchestrator's behaviour, not only under the gate
stack's behaviour. Recorded as INS-043. The cap at 82 reflects that
the six defects are *named*, not all closed; the audit produces a
defect ledger and a fix priority, not a green check.

## Retest tag

*Original-run only (n=1); apparatus / framework claim.* Each defect
is anchored to a *line range* in the v5 super-architecture map;
re-running the audit against a v5.1 or v6 spec would re-open the
defect surface.

## Cross-reference

- Public claim register entry: `docs/public_claim_register.md`,
  section *Apparatus Self-Audits* (`gp158_v5_cage_orchestrator_audit`).
- Working directory (private): `projects/gp158_v5_cage_orchestrator_audit/`.
