# Security / access control — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of access-control / identity results, produced end-to-end by
[LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints (through the
faithfulness firewall; each proof independently kernel-ratified with an axiom audit). Every file is
self-contained (`import Mathlib`) and carries a GENERATED provenance header emitted by
`promote_campaign_artifact.py` — not hand-authored.

## Contents

### `RbacNoPrivilegeEscalation.lean` — role-based access control: no privilege escalation
`reachable_blocks_effective_with_boundary_widening_witness`. Starting from an authorization state in which a
bounded identity `root` is **boundary-excluded** (outside the effective-permission set), **no admissible
delegation sequence** — any finite fold of admissible operations (`assignRole` / `addHierarchyEdge` /
`grantTrustPolicy`) — can make `root` effective at any reachable state (`root ∉ effective target`). The permission
reachability safety property: privilege never escalates across an adversarial operation stream. The theorem also
carries a **tight witness** — the naive self-grant `assignRole {root} {root}` *would* make `root` effective, and is
exactly the operation the admissibility predicate forbids — so the safety guarantee is not vacuous. Over an
arbitrary permission type (no fixed decidable carrier). Axiom-clean `[propext, Quot.sound]`.

### Definitions

The vocabulary the theorem is stated over — read them to check the faithfulness boundary; each is documented at
the top of its file.

**`RbacNoPrivilegeEscalation.lean`**
- `AuthState (Perm)` — an authorization state (`granted` / `boundary` permission sets)
- `effective (s : AuthState Perm) : Set Perm` — the permissions in force (`granted ∩ boundary`)
- `Operation (Perm)` — a delegation op (`assignRole` / `addHierarchyEdge` / `grantTrustPolicy`)
- `applyOp` / `postOps` — apply one / a finite sequence of operations to a state (a left fold)
- `AdmissibleOperation` / `AdmissibleSequence` — the operations a bounded identity is permitted to perform
- `BoundaryExcludes root s` — `root` is outside `s`'s effective set
- `Reachable root initial target` — `target` is reached from `initial` by some admissible sequence
