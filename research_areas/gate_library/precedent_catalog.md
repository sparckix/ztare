# Precedent Catalog

Private first-slice inventory of failure families that motivated implemented controls.

Scope discipline:

- only repo-backed incidents, seams, papers, or postmortems
- only precedents linked to implemented controls or explicitly noted control gaps
- no full Paper 1 taxonomy dump by default

Last updated: 2026-04-12 13:11:05 EDT

## Criterion Reinterpretation Laundering

- **What:** a thesis misses a hard criterion, but the judge rewards an elegant rationale for why the criterion should not bind in that region.
- **Primary evidence:** `research_areas/private/seams/GP-023_ontology_trap_planck_mechanism_seam.md`
- **Controls motivated:**
  - `charter_declared_metric_thresholds`
  - `declared_gate_name_inventory`
- **Current state:** addressed by GP-030 deterministic charter gates.

## GP-037 Invalid Smoke Contract Failure

- **What:** the sandbox charter and the parser/harness contract drifted apart, so a supposedly sealed smoke was not actually exercising declared gates.
- **Primary evidence:** `research_areas/private/postmortems/gp037_invalid_smoke_contract_failure_2026_04_12.md`
- **Controls motivated:**
  - `charter_harness_fail_closed`
- **Current state:** fail-closed harness behavior exists; stronger seal-time invariant remains future work.

## Quarantine Laundering

- **What:** the model acknowledges a flaw, quarantines it rhetorically, then keeps the scored conclusion as if the flaw were background-only.
- **Primary evidence:** `legacy_combined:research_areas/HARDENING_BOARD.md` (`GP-012`)
- **Controls motivated:**
  - `quarantine_laundering_cap_67`
  - `quarantine_laundering_cap_83`
- **Current state:** implemented in `test_thesis.py`.

## Deferred Confirmation Laundering

- **What:** the thesis pushes decisive confirmation into a future observable, then seeks a present-tense high score anyway.
- **Primary evidence:** `legacy_combined:research_areas/HARDENING_BOARD.md` (`GP-014`)
- **Controls motivated:**
  - `deferred_confirmation_cap_67`
  - `deferred_confirmation_cap_83`
- **Current state:** implemented in `test_thesis.py`.

## Directional Forecast Overclaim

- **What:** a directional-forecast project tries to smuggle in a point probability or precise odds claim without a probabilistic charter.
- **Primary evidence:** `research_areas/seams/GP-022_forecast_project_typing_seam.md`
- **Controls motivated:**
  - `directional_forecast_point_probability_cap_50`
- **Current state:** implemented in `test_thesis.py`.

## No-Suite Mutation Admission

- **What:** mutator emits no falsification suite or the no-suite sentinel, but the candidate is still admitted and scored through fallback behavior.
- **Primary evidence:** `research_areas/seams/GP-026_runner_no_suite_rejection_seam.md`
- **Controls motivated:**
  - `suite_presence_guard`
- **Current state:** implemented in `mutation_suite_guard.py`; still marked verify on the board pending additional live closure.

## Hard Self-Reference

- **What:** the proof recomputes a thesis-authored target without independent grounding, so the falsification environment collapses into self-certification.
- **Primary evidence:** `src/ztare/validator/semantic_gate_stabilization.py`, `papers/paper1/` empirical taxonomy, `src/ztare/validator/forensic_reporter.py`
- **Controls motivated:**
  - `hard_self_reference_zero`
  - `self_referential_proof_cap_25`
- **Current state:** implemented, but provenance is still partly repo-local rather than seam-led.

## Anchor Proxy Drift

- **What:** a candidate rewrites the harness or naming scheme so declared anchors no longer bind to the same executable structure.
- **Primary evidence:** repo-local deterministic anchor coverage logic in `src/ztare/validator/proxy_signature.py` and `src/ztare/validator/test_thesis.py`
- **Controls motivated:**
  - `anchor_proxy_drift_cap_50`
  - `anchor_proxy_preservation_contract`
- **Current state:** implemented, but the exact seam-of-origin is not yet reconstructed.

## Scope Slip Without Declared Mutation

- **What:** the mutator changes more of the object than declared, or touches artifacts outside the declared scope/claim delta.
- **Primary evidence:** `research_areas/private/specs/active/GP-020_supervising_agent_closure_discipline_spec.md`, `src/ztare/validator/mutation_contract.py`
- **Controls motivated:**
  - `runner_r1_mutation_declaration_required`
  - `runner_r1_declared_vs_actual_scope_guard`
  - `bounded_discriminator_profile_pre_run_assert`
- **Current state:** implemented in runner admission.

## Portable Suite Drift

- **What:** a bounded-discriminator thesis relies on environment-specific dependencies or non-portable imports, so the suite cannot serve as a stable falsification environment.
- **Primary evidence:** repo-local runner guard in `src/ztare/validator/autoresearch_loop.py`
- **Controls motivated:**
  - `bounded_discriminator_stdlib_guard`
  - `bounded_discriminator_output_contract`
- **Current state:** implemented; exact first incident not yet promoted into a dedicated seam.

## Missing Fit Declaration Contract

- **What:** a fit-enabled project fails to emit the typed `FIT_DECLARATION`, or the contract itself is injected inconsistently, so the fit substrate is present but not actually callable.
- **Primary evidence:**
  - `research_areas/private/seams/GP-035_mutator_missing_fit_primitive_seam.md`
  - `research_areas/private/seams/GP-037_substrate_swap_3b_seam.md`
- **Controls motivated:**
  - `fit_declaration_required_when_enabled`
- **Current state:** implemented; GP-035 contract cleaned so the declaration requirement is unconditional when the rubric enables fitting.

## Pre-Seed Promotion Without Closed Debate

- **What:** findings work is promoted into the seed registry before the debate/spec boundary is closed, collapsing the pre-seed / post-seed distinction.
- **Primary evidence:** `research_areas/private/seams/GP-031_findings_birth_bridge_seam.md`
- **Controls motivated:**
  - `findings_promotion_requires_convergence`
  - `findings_promotion_requires_spec`
  - `findings_seed_id_uniqueness`
  - `findings_no_closed_on_arrival`
- **Current state:** implemented in `supervisor_findings_promotion.py`.

## Notes

- This precedent catalog is intentionally narrower than the full Paper 1 strategy list.
- If a failure family has no repo-backed incident or paper artifact, it does not enter slice 1 by default.
- Future machine-readable catalogs, public rule libraries, and attestation IDs are downstream of this private inventory, not prerequisites for it.
