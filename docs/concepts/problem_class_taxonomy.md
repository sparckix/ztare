---
description: "The canonical problem-class taxonomy consumed by the gate-package recommender."
---
# Problem-Class Taxonomy

> **Up:** [Documentation map](../README.md)

**Status:** scaffold v0.1, 2026-05-04. Per-class hit rates are NOT YET populated and will be filled by Phase 2 mining (GP-212 spec, Phase B). Until then, this file is a documented taxonomy for charter authoring; it is not yet the empirical input to the gate-package recommender.

**Source seam:** `research_areas/private/seams/engine/GP-212_meta_solver_kernel_seam.md`
**Source spec:** `research_areas/private/specs/active/engine/GP-212_meta_solver_kernel_spec.md`

This file is the canonical taxonomy used by `src/ztare/validator/gate_package_recommender.py` to classify substrates and recommend gate packages. Each class lists its definition, canonical example, default rubric_mode, recommended gate flags, and anti-pattern emphasis.

The recommender's classification step uses embedding-based cosine similarity over the class definitions in §2 below. Operator-curated; do not let an LLM modify this file unsupervised.

---

## 1. How to read this file

Each class section is structured:

- **Name**, snake_case identifier
- **Definition**, one paragraph: what kinds of substrates fall in this class
- **Canonical example**, project slug + 1-line description
- **Default rubric_mode**, newton / kepler / calibration
- **Default cage_meta.substrate_class**, for the cage_v5 dispatch
- **Recommended gates**, rubric flag values that the mining empirically supports for this class
- **Anti-pattern emphasis**, which `anti_pattern_catalog.md` entries matter most
- **N (project count)**, number of completed projects classified into this class as of last refresh
- **Stability**, `unvalidated` / `populated_low` (N < 20) / `populated_stable` (N ≥ 20)

When the gate-package recommender runs against this taxonomy, classes with `stability: populated_stable` produce `confidence: high`, populated_low produces `medium`, unvalidated produces `low`, and below-novel-threshold produces `novel` (no recommendation).

---

## 2. Classes

### 2.1 qualitative_thesis_governance

**Definition:** Substrates whose target is a qualitative thesis defending a normative or descriptive governance claim, evaluated against adversarial structural critique. The thesis must produce both a structural characterization and an explicit governance/decision corollary derived from it. Outputs are not numerical; they are claims about admissibility, identification, or accountability under specified conditions.

**Canonical example:** `gp210_consciousness_theory`, necessary non-identification of consciousness, with fail-closed governance corollary

**Default rubric_mode:** newton (Generative Yield required)

**Default cage_meta.substrate_class:** `proof_target` or substrate-specific qualitative class

**Recommended gates:**
- `inject_antipattern_catalog: true` (mode: `hardkill`)
- `disable_evidence_fit_gate: true` (qualitative)
- `disable_uniqueness_gap_gate: true` (qualitative)
- `enable_dag_steering: true`
- `falsification_mode: "bounded_discriminator"`

**Anti-pattern emphasis:**
- `tail_generalization` (the central blindspot per GP-149)
- `overclaimed_scope`
- `unfalsifiable_claim`

**N:** 4-6 (gp169, gp210, paper7 §3.4, paper8), needs precise classification at refresh

**Stability:** `unvalidated` until Phase 2 mining

---

### 2.2 formal_proof_lean

**Definition:** Substrates whose target is a Lean 4 / Mathlib formal proof of a named theorem. The mutator emits Lean source; the harness compiles via `lake build` and audits axioms. Successful output is a closed proof with axiom dependencies restricted to the standard set.

**Canonical example:** `gp211_paper8_lean_proofs`, full Conservative Invariance for sites under categorical equivalence

**Default rubric_mode:** newton (Generative Yield required)

**Default cage_meta.substrate_class:** `lean_proof`

**Recommended gates:**
- `inject_antipattern_catalog: true` (mode: `hardkill`)
- `disable_evidence_fit_gate: true` (formal)
- `disable_uniqueness_gap_gate: true` (formal)
- `enable_mform_audit: true`
- LeanProofGate dispatch (per `src/ztare/gates/lean_proof_gate.py`)

**Anti-pattern emphasis:**
- `vacuous_theorem_statement`
- `smuggled_axiom`
- `decide_on_abstract_goal`
- `statement_narrowing_overclaim`

**N:** 1-2 (gp211, gp139)

**Stability:** `unvalidated` (N too small for stable hit rates)

---

### 2.3 quantitative_law_discovery

**Definition:** Substrates whose target is the discovery or recovery of a quantitative law / closed-form expression / scaling relation from observational evidence. Mutator proposes parametric forms; harness fits, scores against held-out evidence, and audits for asymptotic behavior. Successful output is a parametric form that survives both visible and farther-tail evaluation under the rubric mode.

**Canonical example:** `gp159_recursive_bayesian_law_recovery`, `gp160_asymptotic_wall`, `gp161_mdl_anti_goodhart`

**Default rubric_mode:** newton (discovery class explicit)

**Default cage_meta.substrate_class:** `nd_features` or `closed_form_constant` per the substrate

**Recommended gates:**
- `enable_fit_primitive: true`
- `fit_score_mode: "mre_2sigma"` or per substrate
- `farther_tail_region` populated per substrate
- `holdout_hard_gate: true`
- `inject_antipattern_catalog: true` (mode: `hardkill`)

**Anti-pattern emphasis:**
- `parameter_sensitivity`
- `asymptotic_extrapolation_failure`
- `polynomial_trap`
- `tail_generalization`

**N:** 8-12 (gp077, gp140, gp145, gp155, gp159, gp160, gp161, gp163d-related)

**Stability:** `unvalidated` (refresh after Phase 2 mining)

---

### 2.4 numerical_obstruction_audit

**Definition:** Substrates whose target is a structural obstruction claim about a known mathematical/physical object (e.g., Navier-Stokes regularity, sphere packing, etc.), supported by exhaustive numerical audits over a parameterized search space. The audits do not prove the global theorem; they bound the candidate-counterexample space and isolate the structural conjecture that, if true, would close the global claim.

**Canonical example:** NS Phase 5 work in `projects/ns_millennium_hunt/`, gain/tax tether and PSD certificate language

**Default rubric_mode:** newton (named conjecture + secondary observable required)

**Default cage_meta.substrate_class:** `audit` or substrate-specific numerical class

**Recommended gates:**
- `inject_antipattern_catalog: true` (mode: `both`)
- `disable_evidence_fit_gate: true` (claim is structural, not fit-based)
- `enable_dag_steering: true`
- `falsification_mode: "bounded_discriminator"`
- Pre-registration of search-space parameterization in charter

**Anti-pattern emphasis:**
- `finite_to_infinite_jump`
- `dense_slab_shortcut`
- `unpaid_asymptotic_constant`
- `parametrization_artifact`
- `statement_narrowing_overclaim`

**N:** 2-3 (NS Phase 5, gp043 escape work, gp060 parallel champion)

**Stability:** `unvalidated`

---

### 2.5 structural_diagnostic

**Definition:** Substrates whose target is a structural diagnosis of why a phenomenon resists explanation, for example, distribution-shift sensitivity, feature collapse, instrumentation invariance failure. The diagnosis itself is the deliverable. Successful output identifies the binding constraint and demonstrates it survives adversarial reframings.

**Canonical example:** `gp154_d_int_measurement` (distribution-shift wall), `gp163d_alien_invariant_bridge` (gravity instrument-audit)

**Default rubric_mode:** newton (with calibration components)

**Default cage_meta.substrate_class:** substrate-specific (often `audit` + structural tags)

**Recommended gates:**
- `inject_antipattern_catalog: true` (mode: `hardkill`)
- `enable_dag_steering: true`
- Cross-validation gate (within-distribution vs. holdout structural shift)
- `disable_uniqueness_gap_gate: true` if claim is structural

**Anti-pattern emphasis:**
- `feature_collapse`
- `wrong_yardstick`
- `representation_invariance_failure`
- `tail_generalization`

**N:** 2-4 (gp154, gp163d, gp157 variants)

**Stability:** `unvalidated`

---

### 2.6 cross_domain_methodology

**Definition:** Substrates whose target is the methodology itself, applied across distinct scientific or governance domains, where the deliverable is the operating-regime claim ("the apparatus discipline produces analogous structural results across N substrates with no shared physical content"). Composition of multiple domain-specific substrates under one organizing claim.

**Canonical example:** Paper 7 (cross-domain ZTARE substrate-prober: neural scaling, Navier-Stokes, gravity, consciousness)

**Default rubric_mode:** kepler (descriptive cross-substrate; no Generative Yield expected at the meta-level)

**Default cage_meta.substrate_class:** N/A, this is a meta-substrate; underlying domain substrates have their own classes

**Recommended gates:**
- Inherits from underlying domain substrates
- Plus `enable_mform_audit: true` for cross-domain consistency
- Methodology declared in advance; substrate-class composition explicit

**Anti-pattern emphasis:**
- `methodology_overclaim`
- `cross_domain_consistency_collapse`
- `n_equals_one_universality`

**N:** 1 (paper 7)

**Stability:** `unvalidated` (single-instance class)

---

## 3. Composition

A substrate may combine two classes (e.g., `gp211_paper8_lean_proofs` is BOTH `formal_proof_lean` AND `qualitative_thesis_governance` since the Lean proof links to a governance corollary). The recommender returns a composition when the top-2 classes both score above the match threshold AND together cover ≥ 80% of the charter's structural language. In composition mode the recommended gates are the union; conflicts are surfaced to the operator for resolution.

---

## 4. Refresh policy

This taxonomy is operator-curated. Refresh triggers:

- New substrate class encountered (≥ 3 projects share a structural pattern not covered by current classes)
- Mining run produces hit-rate evidence that an existing class's recommended gates underperform, flagged for re-evaluation
- Cross-LLM consistency check on a problem-class label drops below 75% (per GP-151 super-class threshold)

Each refresh bumps the file's version stamp at the top. The gate-package recommender reads the version and refuses to deploy with confidence > medium if its mining-hit-rate data is older than the taxonomy's most recent refresh.

---

## 5. Open questions for refresh

1. **Single-class vs multi-class projects.** Above the recommender returns up to two classes in composition. Is two enough, or do some projects span three? (NS Phase 5 spans `numerical_obstruction_audit` + `structural_diagnostic` + arguably `cross_domain_methodology` if we count it within paper 7 framing.)

2. **Class boundaries.** `quantitative_law_discovery` and `numerical_obstruction_audit` overlap on substrates that audit a parameterization to discover a law. Is the boundary clean?

3. **N=1 classes.** `cross_domain_methodology` has N=1 currently. Should the recommender deploy at N=1 with `low` confidence, or refuse until N ≥ some minimum?

4. **Historical re-classification.** All 84 existing projects need to be classified into this taxonomy for the mining hit-rate populator to work. Is that a separate operator task, or auto-attempt with operator review?

5. **Sub-class granularity.** `qualitative_thesis_governance` has 4-6 examples. Are sub-classes useful (e.g., `governance_protocol` vs `identification_theorem` vs `corpus_gradient_recapitulation_at_score_98`)? Or is the parent class sufficient?

These resolve at first refresh after Phase 2 mining.
