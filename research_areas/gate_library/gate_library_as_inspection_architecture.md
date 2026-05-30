# The Gate Library as Inspection Architecture

*A design note on why the gate library is the Benthamite inspection principle rendered at the apparatus layer, and what operating commitments that commits us to.*

Status: Active — 2026-04-14. Created after the sandbox_06 v3 clearance turned the treatise Chapter 2 opener from frame into central architecture. Referenced by: `research_areas/private/papers/treatise_principles_of_epistemic_verification.md` Chapter 2 opener; `research_areas/private/seams/GP-023_sandbox06_identifiability_hardening_seam.md`; `research_areas/private/EXPERIMENT_TRACK_RECORD.md` row F-GP023-S06-01.

## Claim

The gate library is not a catalogue of passing conditions. It is the operating implementation of the Benthamite inspection principle inside ZTARE: a structure that disciplines the generator through the pre-registered possibility of checks it cannot anticipate the composition of. Every design decision about the gate library that does not serve that principle is decorative; every design decision that serves it is central.

This note makes that commitment explicit and states the four operating rules that follow from it.

## Why the distinction matters

Bentham's 1787 *Panopticon* letters argued that what disciplined the occupants of the inspection house was not the fact of inspection but the **pre-registered possibility** of inspection from a vantage the occupant could not predict. The inspector did not need to be present; the occupant did not need to know when the inspector was looking. The structure had to be built so that inspection was *admissible at any time, from any angle, on any axis, without further negotiation*. That was the central property.

The corresponding property at the apparatus layer of ZTARE is not "the gates pass." It is: *the generator commits to an artifact against which any member of an open, extensible, pre-registered gate library can be executed at any time, without further negotiation, with no appeal to circumstances, and the generator does not know which composition of gates will be demanded.*

The first form is consistent with gaming. The second form is not, up to the limits of the library's coverage, because the generator cannot pre-image the composition it is disciplined against.

The sandbox_06 v3 result is the first live demonstration of this property holding at machine precision on a non-elementary transcendental target after the Layer-5 (α,β) identifiability catch. The nine-gate battery was **authored independently** of the generator's expressive repertoire and was **applied in composition** — not individually — to a thesis the generator had authored without foreknowledge of which gates the battery would expose next run. The mutator converged on the ground-truth functional form because the composition left no other basin that passed.

## The four operating commitments

### 1. Mutator must not see the composition it is graded against

A gate library is only inspection architecture if the generator does not know, ex ante, which gates will compose against its output. This is not the same as hiding a gate's existence or withholding its threshold. It is stronger: the generator must be unable to optimize against the *joint distribution* of gates that will fire on a given thesis.

Operational implications:

- The library must be extensible mid-program. Any gate that is immutable across a program is a gate the generator can solve once and stop worrying about. The library needs at least one dimension along which the operator can insert new gates without notice.
- The *order and subset* of gates applied to a given thesis should not be announced ahead of time. Full visibility of the library is acceptable; full visibility of the composition against a specific artifact is not.
- Composition must be pre-registered to the charter, not to the thesis. The generator is entitled to know the shape of the battery it is being checked against; it is not entitled to know which subset will bind on its particular run.

In sandbox_06, this commitment was honored by: all 9 deterministic gates declared in `project_charter.md` before any mutator run, but the mutator saw none of the farther-tail values, none of the peak locations, and none of the holdout residual at authoring time. The generator optimized against residuals it had to recover from visible evidence, which is a fundamentally different regression problem than optimizing against the gate values themselves.

### 2. The inward turn is a standing practice, not a response to crisis

The sandbox_06 catch — the Turn 44 (α,β) identifiability degeneracy caught by adversarial multi-start — is the inspection principle turned on its own specification. The operator ran a check the apparatus did not require, discovered that the pre-commit bootstrap had passed the wrong property (rank-5 collapse masked as rank-6 identifiability), and upgraded both the specification (v3 reparameterization) and the discipline (hardening seam R1–R6) before the generator was permitted to see the sandbox again.

The operational commitment is that this is **the ordinary mode**, not a one-time intervention. The apparatus inspects itself with the same suspicion it applies to the generator. Specifically:

- Every new sandbox family is audited for algebraic identifiability before mutator exposure (hardening seam R4, symbolic algebraic-combination audit).
- Every new gate is audited, at authoring time, for whether a generator could pass it without solving the underlying property it claims to test. The pre-commit bootstrap in sandbox_06 failed this audit and is the reference example.
- Every program closure runs one inward-turn review pass before the finding is promoted. What did the apparatus check that it should not have been satisfied with?

The practice has a name in the treatise: the eigenquestion-selection residual (§3.1). The inward turn is that residual made operational at the apparatus layer.

### 3. The composition must be non-anticipable

A gate library whose composition the generator can predict collapses to a single composed gate, and a single composed gate can be gamed. The inspection principle requires that the generator cannot reduce the battery to a scalar it has learned to satisfy.

Operational implications:

- Gates must be **algebraically independent** under the relevant thesis forms. Two gates that always co-pass or co-fail are one gate. The library's real cardinality is its independence rank under the generator's actual move set, not its nominal cardinality.
- The library must contain gates the mutator cannot see the variable alignment of. In sandbox_06, the farther-tail terminal gates at three ψ slices carry this property: the mutator knows the contract declares farther-tail discipline, but not the ψ values or the holdout multipliers, which are committed to the charter and sealed at generation time.
- **Composition novelty is earned, not assumed.** If a program runs long enough, the generator will start passing any fixed composition. The library has to turn over faster than the generator's adaptation rate. The hardening seam rules R1 (adversarial multi-start from clean data) and R3 (loss-surface equivalence disambiguation) are instances of this: they are not gates in the usual sense, they are *new composition axes* the generator cannot have anticipated.

### 4. No single inspector, and no inspector whose failure silently passes

The panoptic structure Bentham argued for was built so that the inspector could be absent and the property still held. ZTARE's equivalent is: no single gate, no single harness, and no single judge should be central for the decision to promote a thesis. Failure of any one inspector should be detectable and should not silently pass.

Operational implications:

- **Fail-closed harness semantics.** When the gate harness cannot run (import error, environment defect, signature mismatch), the result is not "no information" — it is *not passed*. The E-JUDGE-01 finding in the track record is the reference example: a judge that ignored its own `HARNESS DEFECT` instruction and scored anyway. The fix was a hard cap at 50 in the non-deterministic branch, which is the fail-closed commitment rendered as code.
- **Judge-layer caps are admissible but must be legible.** The sandbox_06 83 cap was a Meta-Judge soft-cap on mechanistic grounding, not an apparatus failure. The eval flagged `quarantine_legitimate: false` against itself. That is the inspection principle functioning correctly at the judge layer: the judge's own output surfaced the fact that its cap was on narrative grounds the apparatus did not require. A judge that silently applied the cap without surfacing that disagreement would have been a single-inspector failure.
- **Soft caps must be separable from hard passes.** The 9/9-gate pass and the 83 judge cap must be independently readable from the eval artifact. Folding them into a single score collapses the inspection structure the library is supposed to preserve.

## What this note does not commit to

- It does not claim the gate library is complete. Library coverage is a live empirical question (Layer-5 fractal Goodhart is the current frontier).
- It does not claim gate independence is achievable in all domains. In formalizable regions (H-SP3-01), theorem-prover-backed gates may compress the library; in soft domains, the library may have to be larger and turn over faster.
- It does not replace the adversarial-disagreement leg of ZTARE. The gate library is the compress-leg instrument; invert and adversarial-disagreement remain separate legs. All three must co-load.

## Live referents

- `projects/gp023_planck_sandbox_06/project_charter.md` — the 9-gate battery as charter-committed composition.
- `projects/gp023_planck_sandbox_06/latest_eval_results.json` — the first run in which the inspection principle held at machine precision on a non-elementary transcendental target.
- `research_areas/private/seams/GP-023_sandbox06_identifiability_hardening_seam.md` — the hardening seam that promoted the Turn 44 catch from one-off to standing discipline.
- `research_areas/private/papers/treatise_principles_of_epistemic_verification.md` Chapter 2 opener — the argument this note is the operational rendering of.
- `research_areas/private/EXPERIMENT_TRACK_RECORD.md` row F-GP023-S06-01 — the finding this architecture produced.

## Open items

- **GL-01** — Audit the gate_library control and precedent catalogs for independence rank under the current mutator move set. Expected outcome: some gates collapse under composition and need splitting or replacement.
- **GL-02** — Define a composition-novelty metric: how often does the library's joint distribution over firing subsets change per program? Currently implicit; needs to be explicit before H-GAMING-14 can be cleanly measured.
- **GL-03** — Draft the fail-closed harness contract as a standing specification, not a per-sandbox patch. E-JUDGE-01 is the root cause; a generic specification would close the class.
