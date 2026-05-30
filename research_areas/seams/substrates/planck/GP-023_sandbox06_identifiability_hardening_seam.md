---
seam: GP-023 sandbox_06 identifiability hardening
opened: 2026-04-14
status: active (v3 audit cleared; forward rules below are standing)
parents: GP-023_ontology_trap_planck_mechanism_seam.md (Turn 44 / 44.1); INS-010
visibility: private (operator IP; contains pre-commit check design)
---

# Purpose

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` active (v3 audit cleared; forward rules below are standing) · `last_updated:` 2026-05-08


This seam converts the sandbox_06 v1 (α, β) identifiability catch of 2026-04-14 into standing rules for any future pre-commit identifiability check on any stress-test sandbox family. The catch itself is documented in `GP-023_ontology_trap_planck_mechanism_seam.md` Turn 44 / 44.1 and promoted as INS-010. The purpose of this file is not to re-tell the story; it is to state the rules that a pre-commit verifier operating under the discipline of distrusting green lights must satisfy going forward, so that the Layer-5 catch becomes a procedure rather than a happy accident.

# What failed and why — one paragraph

The sandbox_06 v1 ground truth was declared as six parameters (A, p, α, β, q, offset). The functional form contained α and β only inside the combination (α·phi)/(β·psi), so (α, β) → (α·c, β·c) was an exact global symmetry and the declared family was structurally rank five. The v1 pre-commit check was a bootstrap-under-noise test: starting from a fixed optimizer seed, add Gaussian noise to the visible surface, refit, measure consistency of the recovered parameters across noise realizations. The check passed cleanly because the optimizer fell into the same basin every time — which a degenerate family with a strong optimizer basin will do. The check was satisfying the *form* of an identifiability test (consistency of the recovered parameters under a perturbation) while missing the *intent* (identifiability of each parameter from the functional form of the generating model). The operator ran a second check that the pre-commit rules did not require — an adversarial multi-start fit from clean data with cross-seed consistency — and that second check produced APPARATUS SUSPECT, with the two unidentifiable parameters off by 70% and their ratio recovered to machine precision. That catch is Layer-5 of the fractal Goodhart catalogue (paper4 §5.4 next revision) and the operator-residual instance named in treatise §3.1.

# Forward rules — pre-commit identifiability check, standing version

Any future pre-commit identifiability check on a sandbox ground-truth family must satisfy *all* of the following before the sandbox can be sealed. No rule here is optional and no rule substitutes for another.

## R1. Adversarial multi-start from clean data

The check must fit the declared family against the *clean* (noise-free) evidence surface from at least three optimizer seeds, at least two of which are chosen to be adversarial in the sense that they start from points in the feasible region that are far from the truth along multiple parameter axes. "Adversarial" is operationalized as: start points that are not the optimizer's default seed, that are not within 20% of the truth on any parameter, and that exercise at least two distinct `popsize` / temperature regimes so that basin-of-attraction sameness across seeds is not a free parameter of the test. Clean data is non-negotiable — noise-bootstrap checks are permitted as an *additional* signal but not as a substitute for R1.

**Rationale.** The v1 failure mode was "same basin from a fixed seed under noise." R1 makes sameness of basin across adversarial seeds the test, so a degenerate family cannot satisfy it by having a strong default basin.

## R2. Per-parameter cross-seed consistency

Every declared parameter must satisfy `(max − min) / mean < TOL_XSEED` across all seeds from R1, where `TOL_XSEED ≤ 0.01` (one percent) for a sandbox that claims to be identifiable on the visible surface. A single parameter failing R2 is a fail of the whole check, regardless of how well the other parameters fare.

**Rationale.** A non-identifiable combination can show any value for its individual factors; cross-seed disagreement on the individual factors is the direct signature of non-identifiability. This is the check whose absence in v1 let the degeneracy through.

## R3. Loss-surface equivalence at the cross-seed disagreements

If R2 passes cleanly, R3 is skipped. If R2 shows any non-trivial cross-seed spread on a parameter, the check must additionally evaluate whether the spread is at a loss-equivalent region (evidence of a flat direction in the loss surface) or at a loss-distinct region (evidence that the seeds genuinely converged to different optima and the fitter has a basin problem independent of identifiability). This is the disambiguation between "unidentifiable GT" and "broken fitter."

**Rationale.** The sandbox_06 v1 case had a flat direction of the loss surface along (α, β) with `scale_factor = 1.697666` at equal loss. Distinguishing this from a basin failure is what separates a GT fix (reparameterize) from a fitter fix (tighten bounds / change optimizer).

## R4. Algebraic-combination audit on the symbolic form

Before the numerical checks in R1–R3 are run, the check must include a symbolic audit of the declared functional form that flags any parameter group entering through a single algebraic combination. In practice this means the operator (or a symbolic pass) inspects the generating expression and asks: for each pair (and triple) of declared parameters, is there a transformation that leaves the curve unchanged at every input? If yes, the family is rank-deficient on that group and must be reparameterized before any seal attempt. R4 is the cheap check and is performed before spending compute on R1.

**Rationale.** The v1 degeneracy was visible from one line of generator source (`ratio = (ALPHA * phi) / (BETA * psi)`) and would have been caught in thirty seconds by a symbolic audit pass. The fact that it was caught instead by R1/R2 under operator pressure is a cost the forward rule does not need to re-pay.

## R5. Reparameterize into identifiable combinations before mutator exposure

If R4 or R1–R3 find any rank-deficient group, the family must be reparameterized into identifiable combinations (e.g., `gamma = alpha / beta`) and the generator's numerical-equivalence self-check must assert that the reparameterized curve matches the original at the truth constants to machine precision. The mutator must never see a rank-deficient family, regardless of whether the v1 evidence surface would have been numerically identical.

**Rationale.** The mutator does not need the operator's view of the parameter space; it needs the evidence surface. Reparameterization preserves the evidence surface and removes a source of pre-commit gaming without changing the test the mutator takes.

## R6. Pre-committed failure criteria recorded before the check runs

The numerical thresholds for R1 (number of seeds, adversarial range), R2 (`TOL_XSEED`), and the RMSE / tail-error bars must be written into the check script itself before the check is executed and must be recoverable from version control. A check whose thresholds are set after the results are seen is not a pre-commit check; it is post-hoc rationalization under the form of one.

**Rationale.** This is the general pre-commit discipline from paper4, applied to the identifiability gate specifically. The v3 check in `fitter_audit_true_form_v3.py` already does this (thresholds are module-level constants, script is in git). R6 makes this standing rather than project-specific.

# Layer-5 integration

The catch that motivates this seam is the fifth layer of the fractal Goodhart catalogue:

- Layer 1 — Evaluator gaming (the rubric)
- Layer 2 — Kernel gaming (the judge)
- Layer 3 — Supervisor gaming (the orchestrator)
- Layer 4 — Drafting gaming (the mutator itself)
- **Layer 5 — Pre-commit verifier gaming (the operator's own test design)**

Layer 5 is distinct from the first four in that the gaming is not performed by an optimizer attacking a metric — it is performed by a *test specification* that satisfies the form of a check while missing its intent. The optimizer in this layer is the operator-under-time-pressure, and the metric being gamed is the pre-commit gate's functional definition. This seam's forward rules are the Layer 5 hardening; paper4 §5.4 next revision will cite this seam as the operational reference.

# Treatise §3.1 link

This seam is the operational back-end of the live instance now named at the end of treatise §3.1. The treatise passage makes the philosophical claim — that the operator's decision to run a second check the rules did not require is one unit of decisive residual work — and this seam is the procedure the decision has now been compiled into. The relationship is not accidental: this is exactly what the treatise means when it says the apparatus is what makes a check runnable and the residual is what decides to run it. Today, the residual decided. Tomorrow, the rules above will have decided, and the next catch at this level will need a new unit of residual work that the rules do not yet anticipate.

That asymmetry — residual work compiling one step at a time into apparatus rules, with the residual always staying one level out ahead — is the treatise's Chapter 3 claim rendered as an ongoing process rather than a fixed boundary. This seam is one step of that process.

# Status and follow-ups

- R1–R6 above are standing rules for any GP-023 sandbox sealing from 2026-04-14 forward.
- v3 sandbox_06 audit (`fitter_audit_true_form_v3.py`) satisfies R1, R2, R6. R4 was performed ad hoc on the v3 family during reparameterization; a standing R4 pass for future sandboxes is pending — open item **HRD-01** below.
- Pending: wire R4 (symbolic algebraic-combination audit) into a helper that any new sandbox's pre-commit checklist imports, so the audit is not left to operator vigilance each time.
- Pending: write the paper4 §5.4 Layer-5 paragraph from this seam's Layer-5 Integration section above.
- Pending: the sandbox_06 v3 seal packet itself (evidence files, charter, thesis seed, harness) is the next downstream work item and is tracked separately.

## Open items

- **HRD-01** — Build `sandbox_identifiability_prechecks.py` that exposes R1 multi-start, R2 cross-seed, R4 symbolic-audit helpers so a new sandbox's pre-commit script is ~30 lines rather than a bespoke re-implementation. Priority: before the next sandbox after sandbox_06 v3.
- **HRD-02** — Add a paper4 §5.4 Layer-5 paragraph citing INS-010 and this seam. Priority: next paper4 revision.
- **HRD-03** — Decide whether R1 should be tightened from "three seeds" to "five seeds, two adversarial, two default-regime, one low-popsize noisy-search" as a default. Deferred until a second sandbox runs the current rule and produces a data point on whether three is enough.
