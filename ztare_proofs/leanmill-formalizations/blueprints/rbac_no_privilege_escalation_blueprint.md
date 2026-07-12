# Role-based access control — no admissible delegation sequence escalates a bounded identity to a forbidden resource

Opens the **identity and authorization** frontier, and answers the AWS-Zelkova incumbent directly: Zelkova is a
static SMT check of a single policy ("does this JSON allow X now?"); the elite property is multi-step
**authorization reachability** — that no sequence of privilege operations can escalate a scoped identity. This is
the library's first result over a discrete permission structure with a reachability guarantee, the actual attack
vector in enterprise breaches (role-chaining past a boundary). The claim is a non-escalation invariant over
reachable authorization states: under a permission boundary a scoped contractor identity cannot widen, no
adversarial sequence of role assignments, role-hierarchy edges, and trust-policy grants can ever give that identity
an effective permission the boundary forbids. This is a discrete reachability guarantee — the identity counterpart
of the reachable-state solvency result — over sets of permissions rather than real-valued balances.

Assumption-accounting note: the results depend on (1) **effective permission = granted ∩ boundary** — an
identity's effective permissions are those its roles grant, capped by (intersected with) its permission boundary,
so the boundary is a ceiling no grant can exceed; (2) the **boundary is the load-bearing invariant** — admissible
operations (assigning a role, adding a role-hierarchy edge, granting a trust policy) may add GRANTS but may not add
the forbidden permission to the boundary; widening the boundary is a privilege grant by the account owner, not an
escalation, and lies outside the adversary's admissible moves; (3) the forbidden resource is **absent from the
opening boundary**. Surface where each is used. Model permissions as a `Set` over an arbitrary type; do **not** fix
a decidable finite enumeration as the whole model, and do not restrict to a single operation — the arbitrary-
sequence quantification is the point. A non-closure is an honest gap. Probe the banked DeFi `List.foldl`
reachable-state invariant for the induction.

## Domain
formalization-nonmath

## Theory file
rbac_reachability_theory.lean

## Vocabulary (build these as definitions — do not prove them)
- **Permission**: an abstract capability; a **root permission** is a distinguished forbidden capability.
- **AuthState**: an identity's granted permissions (the union of its assigned roles' permissions, closed under the
  role hierarchy) together with its permission boundary (a set of permissions capping the grant).
- **effective**: the identity's effective permissions — `granted ∩ boundary`.
- **BoundaryExcludes**: the boundary does not contain the forbidden root permission.
- **Operation**: assign a role, add a role-hierarchy edge, or grant a trust policy — each may enlarge `granted`; an
  operation is **admissible** when it does not add the root permission to the boundary.
- **applyOp / postOps**: apply an operation to an authorization state; apply a finite operation sequence in order
  (a left fold).

## Target
Consider a scoped identity — a contractor whose permission boundary excludes a forbidden root resource — under a
protocol that lets an adversary assign roles, add role-hierarchy edges, and grant trust policies, each of which may
enlarge the granted permissions but none of which may add the forbidden permission to the boundary. The claim is a
reachable-state non-escalation guarantee. Starting from a state whose boundary excludes the root permission, after
**any** finite admissible sequence of these operations — role-chaining, hierarchy edits, trust grants, in any order
— the identity's effective permissions never include the root permission: at every reachable authorization state
the escalation is blocked. No trajectory of admissible privilege operations reaches the forbidden resource; only
widening the boundary can, and that lies outside the adversary's admissible moves. Surface that the guarantee uses
the boundary-cap definition of effective permission and that the boundary invariant is load-bearing: dropping it
admits a boundary widening that reaches root.

## Lemmas
- Granting permissions cannot escalate past the boundary: enlarging `granted` while the boundary is fixed cannot
  bring a boundary-excluded permission into `effective`, since `effective = granted ∩ boundary`.
- Each admissible operation preserves boundary-exclusion of the root permission: an operation that does not add root
  to the boundary leaves a root-excluding boundary root-excluding.
- No reachable state escalates: from an opening state whose boundary excludes the root permission, every reachable
  state under a finite admissible operation sequence has the root permission outside its effective permissions — by
  induction on the sequence, discharging each step with the boundary-preservation lemma and the intersection fact.

## Idea
Model permissions as a `Set` (or `Finset`) and `effective = granted ∩ boundary`. The load-bearing fact is
elementary set reasoning: `root ∉ boundary → root ∉ granted ∩ boundary`, for any `granted` — so no grant, however
large, escalates while the boundary excludes root (`Set.not_mem_inter` / `Finset.not_mem_inter`). The per-operation
lemma is that an admissible operation does not add root to the boundary, so `BoundaryExcludes` is preserved. The
reachable-state invariant is a `List.foldl` induction over the operation sequence, mirroring the banked DeFi
admissible-sequence invariant: induct on the operations, discharge each step with `root ∉ boundary` preserved and
the intersection fact. Keep the permission carrier abstract; do not fix a decidable enumeration or collapse the
operation stream to a single step. Non-vacuity is that non-escalating reachable states exist — the opening state
itself, with a concrete forbidden root permission absent from the boundary.
