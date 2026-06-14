# GP-075 — Rubric Generation for Unknown Domains

Canonical file-format note: this spec governs unknown-domain rubric design
principles. The current rubric JSON schema, `rubric_mode` contract, and
operator flag list are maintained in `docs/concepts/rubric_specification.md`.
When adding or changing a rubric field, update the canonical spec and link back
from here only if the change affects unknown-domain design.

## Status

Active

## Seam

research_areas/private/seams/GP-075_rubric_for_unknowns_seam.md

## Scope

- Taxonomy of GT-independent vs. GT-dependent rubric criteria
- Goodhart attack surface when the rubric is the optimization target
- Domain knowledge injection patterns for discovery mode
- The calibration → discovery transition requirements and boundary conditions
- Minimum falsifiable rubric apparatus by discovery regime (domain-specific vs. domain-general)

- **End-to-end unknown-domain experiment setup protocol** (added 2026-04-17) — evidence partitioning, charter writing for discovery mode, workspace structure for unknown dimensionality, Component C behavior without GT, holdout generation from finite corpus, run configuration flags

**Out of scope:**
- Implementation of a rubric generator (premature)
- ZTARE components beyond C (architecture astronauting)
- Specific domain applications (health, finance, physics) — too early

**Resolved track (debated Turns 7–10):**
- End-to-end pre-registration protocol for unknown-domain experiments — debated 2026-04-17 (Turns 7–10). Turn 7 proposed six-layer protocol; Turn 8 identified six flags against the spec; Turn 9 resolved all flags; Turn 10 accepted all resolutions. Spec updated with Phase 0 and constraint additions below.

## Decision

ZTARE can operate in discovery mode — generating structurally valid rubrics without ground truth — only under conditions that are more restrictive than the seam's initial framing assumed. The minimum falsifiable rubric apparatus for domain-specific discovery is prediction-testing against a fixed holdout partition established before any candidate runs; corpus exhaustion is a hard structural limit on this apparatus, not a design problem. For domain-general discovery, cross-domain transfer is the minimum apparatus, but it requires the candidate to make an explicit domain-generality claim, the two domains to share a constraint class, and a pre-fixed holdout in the target domain. Domain knowledge can be injected without leaking the answer key by specifying constraint classes rather than constraint values, but only when the constraint class is itself known; in genuinely dark domains where the constraint class is a discovery target, this mechanism collapses. The calibration-to-discovery transition conditions (stable data-generating process, available fixed holdout, known constraint class) form a spectrum rather than a binary gate, and Goodhart bites rubric criteria in order of their legibility to gradient-following optimizers, with a separate stochastic plausibility attack applicable to unspecified derivation quality criteria that the legibility framework does not model.

## Problem

ZTARE currently operates in calibration mode: synthetic substrates with known ground truths are used to verify that the apparatus can recover them. Transitioning to discovery mode — pointing ZTARE at real-world "dark datasets" where no ground truth exists — requires rubrics that do not presuppose the answer.

The core tension is structural: a rubric is an evaluation instrument. If the rubric encodes the answer (rubric-as-key), it is a crossword puzzle, not science. If the rubric encodes only methodology (rubric-as-method), the mutator can Goodhart on the methodology itself — INS-012 documents this at the eval layer. Three sub-problems follow:

1. **GT-independent criteria**: Which rubric dimensions are decisive without GT? Candidates include empirical fit on visible data, holdout generalization, parsimony, derivation quality, and internal consistency. None of these is individually sufficient in discovery mode; they are necessary conditions, not sufficient ones.

2. **Goodhart boundary**: When the rubric is the optimization target, which criteria get gamed first, and is the holdout gate a sufficient defense? INS-012 showed gaming at the specification layer; the same attack surface exists at the rubric layer.

3. **Domain knowledge injection**: Real-world rubrics require domain constraints (physical units, conservation laws, boundary conditions). How does ZTARE acquire these without a human encoding the answer key, and is there a structural pattern that avoids that collapse?

## Why It Matters

The discovery-mode transition is the difference between ZTARE as a calibration harness and ZTARE as a scientific instrument. If rubric generation for unknown domains is not principled, the apparatus will either (a) silently accept candidates that satisfy the rubric's methodology without finding any true law, or (b) reject valid candidates because the rubric encodes assumptions the domain violates. GP-073 sandbox_15 documented the inverse failure — a rubric that correctly rejected wrong candidates but gave the mutator no usable gradient over nine iterations. The discovery-mode failure is the mirror: a rubric that accepts wrong candidates with no external check. The scope of ZTARE's applicability to real-world problems depends entirely on resolving this.

## Constraints

- **Contamination constraint**: Tests used to evaluate a candidate cannot be generated from that candidate's own predictions. Any test-generation protocol that is candidate-conditioned is structurally identical to the charter contamination pattern (GP-023) and is disqualified.
- **Corpus exhaustion**: In genuinely dark domains, no new data can be generated on demand. The falsification surface is bounded by the finite corpus. This is a hard limit, not a design choice.
- **Constraint class knowledge**: Domain knowledge injection (constraint-class-not-value) works only when the constraint class is domain-agnostic or formally defined. When the constraint class is itself a discovery target, the mechanism fails.
- **Data-generating process stability**: Holdout generalization is only a valid falsification surface when the holdout was drawn from the same process as the training data. In unstable or regime-shifting domains, this assumption fails.
- **Attack model scope**: The legibility-based Goodhart ordering applies only to gradient-following optimizers. Rubrics with unspecified derivation quality criteria face a separate stochastic plausibility attack that the legibility framework does not model.
- **Component C disabled in discovery mode**: Self-referential operation (using the candidate's proposed dominant term to compute the residual hint) is candidate-conditioned and violates the contamination constraint. Component C is a calibration-mode accelerator only. In discovery mode, set `enable_component_c: false`.
- **Prior art**: INS-012 (rubric-as-eval gaming), GP-073 sandbox_15 (zero-gradient rubric failure), GP-074 Component C (positive-space geometric hints insufficient alone), GP-045 iter-7 (parsimonious wrong law scoring 100 inside fit window).

## Options

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Holdout gate as minimum apparatus** | Use fixed holdout partition (pre-fixed before any candidate runs) as the sole GT-independent falsification surface. Candidate must make explicit predictions about holdout before seeing it; failure is terminal. | Contamination-safe; existing ZTARE infrastructure; no new architecture required; strongest single-domain falsification surface available | Corpus exhaustion is a hard limit; tests generalization, not law-ness; designed for calibration mode, not discovery mode; cannot distinguish true law from lucky pattern | **Viable for domain-specific discovery within corpus limits; insufficient alone for domain-general discovery** |
| **B — Cross-domain transfer gate** | Candidate law discovered in domain A must make correct predictions in domain B without retraining. Holdout in domain B fixed before domain A run begins. | Strictly stronger falsification surface than single-domain holdout when conditions hold; harder to game (mutator cannot model both domains simultaneously); GT-independent | Requires domain B data available before domain A discovery run; requires candidate to make explicit domain-generality claim; requires domains to share a constraint class; domain B may not exist at discovery time | **Viable for domain-general discovery when conditions hold; not universally deployable** |
| **C — Constraint-class injection** | Human specifies the *type* of constraint (e.g., "this domain has a conservation law") without specifying which quantity is conserved. Rubric tests whether candidate satisfies some instance of the constraint class. | Does not leak the answer key; analogous to charter contamination rule (inject method, not target); works for physics, chemistry, formal systems | Fails when constraint class is itself a discovery target (economics, biology, social systems); requires human-in-the-loop for constraint class validation in dark domains; constraint class definition is itself domain knowledge | **Viable when constraint class is formally defined or domain-agnostic; fails for genuinely dark domains** |
| **D — Rubric criteria taxonomy only (no new apparatus)** | Define which existing criteria are GT-independent, rank them by Goodhart vulnerability, and use ensemble scoring across all criteria. | Low implementation cost; uses existing rubric machinery; provides design guidance | No individual criterion is sufficient in discovery mode; ensemble scoring does not resolve the falsification surface problem; Goodhart bites the ensemble if the ensemble is the optimization target | **Insufficient as a primary solution; useful as a design input alongside A or B** |
| **E — Active data collection / external oracle** | When corpus is exhausted or DGP is unstable, require active data collection or human-in-the-loop oracle to generate new falsifying tests. | Solves corpus exhaustion; can handle unstable DGPs; extends falsification surface indefinitely | Not a rubric design solution — it is a different architecture; out of scope for current ZTARE apparatus; high operational cost; human-in-the-loop reintroduces answer-leakage risk | **Required for genuinely dark domains where A and B fail; architecturally distinct from rubric generation** |

## Recommendation

Deploy **Option A (holdout gate) as the minimum apparatus for domain-specific discovery** and **Option B (cross-domain transfer) as the minimum apparatus for domain-general discovery**, with **Option C (constraint-class injection) as the domain knowledge injection pattern** where the constraint class is formally defined. Option D (criteria taxonomy) should be used as a design input to configure the rubric's criterion set, with the legibility ranking informing which criteria are included and how they are weighted. Option E is not a rubric solution — it is the correct escalation path when A and B both fail, and should be documented as such rather than treated as a rubric design choice.

The legibility ranking for gradient-following Goodhart attacks (most to least vulnerable): empirical fit on visible data → parsimony (explicit complexity measure) → internal consistency → holdout generalization → derivation quality (specified). Derivation quality (unspecified) is not in this ranking because it faces a separate stochastic plausibility attack, not a gradient-following attack; rubrics that include unspecified derivation quality criteria should be flagged as carrying a second attack surface that the legibility framework does not model.

The calibration-to-discovery transition should be treated as a spectrum gated on three continuous conditions: data-generating process stability, holdout availability (pre-fixed, representative, non-exhausted), and constraint class knowledge. Architectural decisions that require binary treatment of this boundary should note that the boundary is a simplification.

## Implementation Sketch

**Phase 0 — Pre-registration protocol for discovery-mode experiments** (added 2026-04-17, from Turn 7 six-layer analysis)

1. **Corpus manifest and partition**: Commit the partition before any candidate runs. Record partition method (random or stratified), ratio, and SHA-256 hash of holdout file in the pre-registration. If the corpus has known structure (temporal, spatial, categorical), document the stratification rationale. If the correlation structure is unknown, use random partition and document that assumption.
2. **Discovery-mode charter**: State only: (a) what the data represents (measurement type, units, domain); (b) what the model must output (function signature, return type); (c) what the evaluation criteria are (exact match, approximate match, classification). Do not state structural assumptions about the data (growth rate, symmetry, periodicity) unless derived from the visible data and documented as hypotheses, not facts.
3. **Workspace dimensionality**: If dimensionality is known, specify it in the rubric. If dimensionality is unknown, set `fit_required_dimensionality: null` and `fit_required_vars: null`. The gate harness evaluates on (input, output) pairs regardless of the model's internal parameterization.
4. **Component C**: Disabled in discovery mode (`enable_component_c: false`). Self-referential operation (candidate defines the residual, residual is the hint) violates the contamination constraint.
5. **Holdout budget**: Pre-specify maximum number of candidates tested against holdout. Holdout revealed as pass/fail only, never as individual (input, output) pairs. When the holdout budget is exhausted, the experiment terminates.
6. **Run configuration**: Set `discovery_mode: true`, `holdout_budget: N`, `enable_component_c: false`. Optionally set `constraint_class` if the constraint class is known.

**Phase 1 — Rubric configuration for domain-specific discovery**
1. Establish a fixed holdout partition from the target domain corpus before any candidate runs. Document the partition protocol in the pre-registration.
2. Configure the rubric's criterion set using the legibility ranking: include empirical fit, parsimony (with an explicit complexity measure), internal consistency, and holdout generalization. Exclude or separately flag any derivation quality criteria that are not fully specified, noting the stochastic plausibility attack surface.
3. The contamination-safety requirement is that the holdout was fixed before any candidate runs — this is satisfied by the existing loop architecture. A stronger two-phase protocol (candidate records explicit predictions before holdout is revealed) is a future implementation target, not a current capability. Terminal failure criterion: prediction failure on holdout rejects the candidate regardless of training fit.
4. At corpus-exhaustion threshold (to be defined per domain), escalate to Option E (active data collection or human-in-the-loop oracle). Do not attempt to extend rubric coverage past this threshold with rubric design alone.

**Phase 2 — Constraint-class injection for known constraint classes**
1. Human operator specifies the constraint class (e.g., "conservation structure exists," "boundary conditions of type X apply") without specifying the constraint value.
2. Rubric tests whether the candidate's proposed law satisfies some instance of the specified constraint class.
3. For domains where the constraint class is unknown, flag the domain as requiring human-in-the-loop constraint class validation before rubric generation proceeds. Do not generate rubrics for domains where the constraint class is a discovery target without this validation step. This determination requires human judgment and cannot be automated. The operator must explicitly assess whether the constraint class is known before proceeding. If the operator cannot make this determination, the domain should be treated as having an unknown constraint class and escalated to Option E.

**Phase 3 — Cross-domain transfer gate for domain-general claims**
1. When a candidate makes an explicit domain-generality claim, activate the cross-domain transfer gate.
2. Identify a structurally comparable target domain (same constraint class, same data-generating process type) with pre-fixed holdout data available.
3. Apply the candidate law to the target domain holdout without retraining. Failure is terminal for the domain-generality claim (the candidate may still be retained as a domain-specific result).

**Tracking**
- Tag each discovery run with its regime (domain-specific / domain-general) and its transition condition scores (DGP stability, holdout availability, constraint class knowledge) on the spectrum.
- Record which Goodhart attack surface (gradient-following vs. stochastic plausibility) is active for each rubric criterion. Flag any run where stochastic plausibility is the primary attack surface — these runs require a different defense than the legibility ordering provides.
- When INS-012 data is reviewed, cross-reference against the legibility ranking (see Open Question 2).

## Open Questions

1. **Cross-domain transfer deployment timing**: The cross-domain transfer gate requires domain B holdout data to be fixed before the domain A discovery run begins. In genuinely dark domains, domain B may not be identified until after domain A's candidate is proposed. Is there a protocol for retroactive cross-domain validation that preserves contamination safety, or does this require prospective domain B identification as a hard prerequisite?

2. **Legibility ranking empirical validation**: The predicted Goodhart attack order (empirical fit → parsimony → internal consistency → holdout → derivation quality specified) has not been validated against INS-012 data. What is the fastest path to falsification or confirmation? Which INS-012 runs are most diagnostic?

3. **Stochastic plausibility defense**: The debate identified that unspecified derivation quality criteria are exposed to a stochastic plausibility attack that the legibility framework does not model. What is the correct defense against this attack? Options not yet analyzed: adversarial judge scoring derivation quality, specification of derivation quality criteria post-hoc (with contamination risk), or exclusion of derivation quality from discovery-mode rubrics entirely.

4. **Spectrum operationalization**: The calibration-to-discovery transition conditions (DGP stability, holdout availability, constraint class knowledge) are continuous. What thresholds or scoring functions should be used to make go/no-go decisions in practice, and who has authority to set those thresholds?

5. **Constraint class validation for dark domains**: For domains where the constraint class is a discovery target, the recommendation is human-in-the-loop constraint class validation before rubric generation. What does this validation process look like structurally, and how does it avoid the same answer-leakage risk that constraint-value injection carries? The seam has identified the problem but not the solution.

6. **"Level 3 Gate is the truth machine" claim (from Gemini side-conversation)**: The minimum apparatus analysis establishes that the holdout gate is the weakest valid falsification surface, not that it is sufficient for truth-finding. The "truth machine" claim is about sufficiency (can the gate distinguish true laws from lucky patterns?), which is a stronger claim than the minimum apparatus analysis addresses. This claim requires separate examination and is not resolved by this spec.
