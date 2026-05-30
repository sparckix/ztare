# GP-023 Ontology Trap / Planck Mechanism Spec

## Status

Active — refreshed for Phase 3 on 2026-04-12 21:26:07 EDT

## Scope

- define GP-023 Phase 3 / Sandbox 03 only
- turn the converged GP-023 + GP-046 object into a run-ready but not-yet-invoked packet
- specify the sandbox_03 pre-registration, charter contract, farther-tail holdout, and structural-diversity runtime delta

Does not cover:

- executing the live sandbox_03 run
- interpreting a finished Phase 3 run
- deciding any post-Phase-3 kernel work beyond what GP-046 already fixed generically

## Decision

Do not open another brief debate seam. Draft the Phase 3 packet in one shot.

The live GP-023 object is no longer Phase 0 design and no longer "rerun sandbox_02 with the fitter enabled." Phase 2 plus GP-037 plus GP-045/046 changed the object enough that the correct move is a new packet:

- same contamination posture
- same hidden generator family
- fit primitive enabled
- explicit structural-diversity delta
- sealed farther-tail holdout for asymptotic/global-tail claims

Then stop before operator invocation.

## Problem

GP-023 already has a frozen early history:

- Phase 1 was too easy to over-interpret
- Phase 2 was non-diagnostic under its own pre-reg
- GP-035/037 removed missing parameter fitting as the primary bottleneck
- GP-045/046 showed that bounded-window late-tail behavior can be laundered into a false asymptotic mechanism story unless the contract distinguishes local fit from global-tail credit

So the open question is narrower now. The design burden is:

- make structural-diversity pressure explicit
- keep the contamination posture clean
- prevent a local late-tail surrogate from being mistaken for a licensed asymptotic law

## Why It Matters

If Sandbox_03 succeeds cleanly, GP-023 finally gets a live positive datum under a materially harder and more interpretable contract.

If it fails cleanly, the negative result is still valuable because it rules out "fitter absence" and "asymptotic overclaim" as trivial explanations and sharpens the next bottleneck.

Either way, the result is only valuable if it is uncontaminated, pre-registered, mechanically scored, and explicit about claim scope.

## Constraints

- do not run the live sandbox in this spec turn
- do not use recognizable historical physics vocabulary in the sandbox materials
- keep the sandbox_02 contamination posture unless the substrate changes again
- keep scoring mechanical rather than operator-vibes-based
- asymptotic/global-tail credit must be licensed by a farther-tail contract, not by bounded-window fit alone
- use the current shipped primitives only; do not invent a project-local repair menu

## Options

### Option A — Re-run sandbox_02 with the fitter enabled

**Description**

Treat GP-035 as the only missing variable and rerun sandbox_02 without changing the score surface.

**Pros**

- minimal new construction work
- isolates one apparatus change

**Cons**

- GP-037 already showed fitter absence is not the next binding bottleneck
- leaves the asymptotic-claim laundering surface unresolved
- would ask the wrong question

**Verdict**

Rejected.

### Option B — Open a separate short debate seam before drafting Phase 3

**Description**

Do another narrow debate artifact before writing Sandbox_03.

**Pros**

- can feel safer before drafting

**Cons**

- GP-023 and GP-046 are already converged enough on the decisive choice
- creates state split across too many artifacts
- adds delay without changing the build object

**Verdict**

Rejected.

### Option C — Draft Sandbox_03 / Phase 3 in one shot

**Description**

Write the full Phase 3 packet in one pass:

- project charter
- sandbox construction record
- farther-tail generator
- frozen harness + smoke gate
- Phase 3 pre-registration
- refreshed GP-023 spec

Then stop before operator invocation.

**Pros**

- matches the converged eigenquestion
- keeps all decisive rules in the packet that will actually be run
- avoids another debate-only detour

**Cons**

- still requires operator invocation for the live datum

**Verdict**

Recommended.

## Recommendation

Adopt Option C.

Phase 3 deliverables:

- [GP-023_planck_sandbox_03_pre_registration.md](/research_areas/private/seams/GP-023_planck_sandbox_03_pre_registration.md)
- [project_charter.md](/projects/gp023_planck_sandbox_03/project_charter.md)
- [sandbox_construction_record.md](/projects/gp023_planck_sandbox_03/sandbox_construction_record.md)
- [raw/generate_curve.py](/projects/gp023_planck_sandbox_03/raw/generate_curve.py)
- [gate_harness.py](/projects/gp023_planck_sandbox_03/gate_harness.py)
- [harness_smoke_gate.py](/projects/gp023_planck_sandbox_03/harness_smoke_gate.py)
- this spec

Phase 3 packet is complete when:

- the project packet exists on disk
- the farther-tail contract is declared in the charter
- the rubric explicitly enables the fit primitive and the chosen structural-diversity delta
- the board/seam reflect "ready for operator seal" rather than "draft next"

## Implementation Sketch

### Step 1 — Carry forward the clean substrate and contamination posture

Sandbox_03 keeps sandbox_02's:

- hidden generating law
- rename map
- visible evidence surface
- contamination-audit posture

This keeps Phase 3 comparable and prevents "new result because new sandbox" ambiguity.

### Step 2 — Add the two Phase 3 deltas explicitly

Delta A: `enable_fit_primitive: true`

Delta B: an explicit structural-diversity surface. For Sandbox_03 that is:

- `cold_residual_successor_mode: true`

The point is to make family escape auditable rather than implicit.

### Step 3 — Bind asymptotic/global-tail credit to a farther-tail contract

If the project allows floor / asymptotic / global-tail claims, the sandbox must include:

- `asymptotic_claim: true`
- `farther_tail_contract: true`
- a hidden farther-tail file
- deterministic farther-tail gates

That is the GP-046 B-first decision expressed as project contract.

### Step 4 — Freeze the deterministic scoring surface

Use:

- frozen `gate_harness.py`
- pre-run `harness_smoke_gate.py`
- deterministic charter gates
- champion binding, not latest binding

### Step 5 — Stop before live operator invocation

This spec produces the packet. It does not itself run the experiment.

## Open Questions

- does cold residual successor mode produce enough family escape on this substrate, or is a later Phase 4 still needed?
- after a live Sandbox_03 run, is the next binding object compression/parsimony or something else entirely?
- if Sandbox_03 fails cleanly, is the right next move another Planck slice or to close GP-023 negatively?
