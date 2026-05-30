# ZTARE Gates — registry and reading order

This directory holds the deterministic gate stack that runs around every iter of the autoresearch loop. The user-facing description of the design lives in `GP-157 (internal seam)`. This README is the navigation map for the code itself.

## How a gate runs

Every gate has a **phase** (when in the iter it runs), a **rubric flag** (the on/off switch the operator controls), an **input** (what it reads), and an **output** (what it writes). The Cage dispatcher (`cage.py::Cage`) topologically sorts gates by declared dependencies and calls each in phase order. Most gates are wired directly into `src/ztare/validator/autoresearch_loop.py`; a few are managed by `Cage` via `src/ztare/orchestrator/state.py::build_cage_runtime`.

```
SUBSTRATE_VALIDATE   →  PRE_FIT     →  FIT     →  POST_FIT   →  PRE_JUDGE   →  POST_JUDGE
   (once at boot)       (per iter)      (fit)     (per iter)    (per iter)     (per iter)
```

## Phase → gate index

### SUBSTRATE_VALIDATE (boot-time validation of the substrate spec)

| Gate | File | Rubric flag | What it does |
|---|---|---|---|
| substrate-meta validator | `cage.py::validate_substrate_meta` | always on | Asserts `cage_meta` carries `target_convention_homogeneity ∈ {homogeneous, heterogeneous}`, declares `min_rows_per_category`, etc. Hard-fails launch if missing. Spec §3 D1. |
| feature-coverage adequacy probe | `substrate_evaluation.py` | always on | Validates each feature key has minimum row coverage. Surfaces collapsed features. Spec §3 R8 dependency. |

### PRE_FIT (before scipy.optimize fits constants)

| Gate | File | Rubric flag | What it does |
|---|---|---|---|
| **R8** feature-coverage adequacy | `cage.py::check_feature_coverage_adequacy` | always on | Each feature the form references must have ≥30% non-None coverage on visible. Catches gp154-style "feature is None on every row" failure. |
| **R9** target-convention homogeneity | `cage.py::check_target_convention_homogeneity` | always on | If `cage_meta.target_convention_homogeneity == "heterogeneous"`, PARAMETRIC_FORM must reference `features['fit_convention']`. |
| substrate critic | `src/ztare/diagnostics/substrate_critic.py` | `enable_substrate_critic` | Computes feature_dimensionality_collapses + epistemic_voids + cross_class_signal. Output → `workspace/substrate_critique.json`. |
| noise profile | `src/ztare/diagnostics/noise_profile.py` | `enable_noise_profile` (auto-on for nd_features) | Pre-flight Breusch-Pagan / Shapiro-Wilk / Durbin-Watson on baseline residuals. Output → `workspace/noise_profile.json`. |
| pathology enforcement | inside `fit_primitive_features.py` | always on | Replaces extreme parameter values that escape declared init_range with init-range midpoints before scipy runs. |

### FIT (the fit primitive itself)

| Gate | File | Rubric flag | What it does |
|---|---|---|---|
| fit_primitive_features | `src/ztare/fit/fit_primitive_features.py` | `enable_fit_primitive_features` | scipy.optimize multi-start over PARAMETRIC_FORM. AST whitelist + parameter-range bounds + BIC budget. |
| fit_primitive (1D) | `src/ztare/fit/fit_primitive.py` | legacy 1D substrates | Single-axis curve_fit; superseded by fit_primitive_features for nd_features substrates. |
| weighted χ² adapter | inside `fit_primitive_features.py` | `fit_weighted_residuals` | Per-row σ from features dict, BIC = χ² + K·log(N). |
| robust-loss adapter | inside `fit_primitive_features.py` | `fit_robust_loss` | Huber loss for heavy-tail residuals. |

### POST_FIT (after fit, before falsification suite)

| Gate | File | Rubric flag | What it does |
|---|---|---|---|
| residual diagnostic | inside `fit_primitive_features.py` | always on | Per-categorical-group residual flagging (groups with mean|res| ≥ 1.5× overall). |
| **R10** cross-class extrapolation diagnostic | `cross_class_extrapolation_gate.py::run_cross_class_diagnostic` | always on when held-out classes exist | Per-class MRE on held-out classes + Spearman(per-row error, primary feature) within each held-out class + in-feature-range vs out-of-feature-range subset MRE. Flags `magnitude_coincidence` and `kernel_camouflage_rh18_candidate`. Output → `workspace/cross_class_extrapolation_iter_N.json`. **Mechanizes the manual gp163d backtest.** |
| post-fit noise classifier | `noise_profile.py::classify_residuals` | follows pre-flight | Refreshes noise verdict on actual fit residuals; can flip solver routing for next iter. |
| substrate critic refresh | `substrate_critic.py::refresh_critique_post_fit` | follows pre-flight | Updates critique with post-fit findings. |

### PRE_JUDGE (gate-harness evaluation, before LLM judge)

| Gate | File | Rubric flag | What it does |
|---|---|---|---|
| holdout-hard-gate | inside `autoresearch_loop.py` | `holdout_hard_gate` | Runs project's `gate_harness.py`. If holdout MRE ≥ threshold, hard-fails. |
| **R11** per-class farther-tail MRE ceiling | `cross_class_extrapolation_gate.py::per_class_mre_ceiling` | `enforce_per_class_farther_tail` | Each held-out class must independently satisfy MRE < threshold. Per-class overrides via `per_class_thresholds`. Excluded classes via `r11_excluded_classes` (e.g. classes with known data artifacts). |
| extrapolation-gap | `global_gates.py::_gate_extrapolation_gap` | `enable_extrapolation_gap` | Visible-vs-holdout regime span check. Has audit-class bypass. |
| asymptotic claim discipline | `asymptotic_claim_discipline.py` | `enable_asymptotic_claim_discipline` | Catches "infinity in title, finite in measurement" claims. |
| derived constraints | `derived_constraints.py` | `enable_derived_constraints` | Cross-iteration constraint provenance. |
| domain-match | `domain_match_gate.py` | `enable_domain_match` | Form's variable names must match substrate's evidence schema. |
| bridge scope contract | `bridge_scope_contract.py` | `enable_bridge_scope_contract` | If form claims X-class, must apply to X-class only or declare extension. |
| coordinate invariance | `coordinate_invariance_gate.py` | `enable_coordinate_invariance` | Form's predictions must be invariant under declared coordinate transforms. |
| continuum limit | `continuum_limit_gate.py` | `enable_continuum_limit` | Discrete-to-continuum extrapolation sanity. |
| ensemble ambiguity | `ensemble_ambiguity_gate.py` | `enable_ensemble_ambiguity` | Multi-form rivalry resolved by deterministic discriminator. |

### POST_JUDGE (after LLM judge, before promotion)

| Gate | File | Rubric flag | What it does |
|---|---|---|---|
| circularity (G-CIRC) | `circularity_gate.py` | `structural_blocker_enforcement ∈ {gate, both}` | Catches forms that derive their conclusion from their definition. |
| falsifiability (G-FALSIFY) | `falsifiability_gate.py` | `structural_blocker_enforcement ∈ {gate, both}` | Catches forms with no possible refutation. |
| ansatz survivor (G3) | `ansatz_survivor_gate.py` | (mode-dependent) | Proof-shortness via Lean REPL; gp146 lineage. |
| proof surveyability (G4) | `proof_surveyability_gate.py` | (mode-dependent) | Multi-step inference traceability. |
| translation diff (G5) | `translation_diff_gate.py` | (mode-dependent) | Lean compile diff on form changes. |
| Wasserstein-persistence | `wasserstein_persistence_gate.py` | `enable_wasserstein_persistence_gate` | Topological persistence of fit residuals; chaos-substrate G2. |
| PSLQ falsity audit | `pslq_falsity_audit_gate.py` | `enable_pslq_falsity_audit` | Integer-relation false-positive audit; chaos-substrate G3. |
| domain-prior leak audit | `prompt_leak_audit.py` | always on | Detects denylist terms in mutator prose post-hoc. |
| structural constraint extractor | `structural_constraint_extractor.py` | reads judge prose | Mines judge weakest-points for derived constraints to feed next iter. |

### Diagnostic-only (always run, never block)

| Gate | File | Phase | What it does |
|---|---|---|---|
| residual-norm | `residual_norm.py` | POST_FIT | Computes residual norm telemetry for paper traces. |
| corrector library | `corrector_library.py` | POST_FIT | Suggests grammar extensions when residuals show known corrector signatures (loglog, t·exp, etc.). |
| negative space extractor | `negative_space_extractor.py` | POST_JUDGE | Extracts what the form CAN NOT distinguish for next-iter discrimination. |
| semantic gate stabilization | `semantic_gate_stabilization.py` | POST_JUDGE | Cross-iteration consistency check for gate verdicts. |
| deterministic charter gates | `deterministic_charter_gates.py` | PRE_JUDGE | Per-charter custom gates (e.g. asymptote checks for specific physics substrates). |
| linear observable coercivity | `linear_observable_coercivity_gate.py` | POST_FIT | Checks that a declared linear observable has enough rank or a receipted quotient/coercivity argument for the claimed target structure. |

## How gates inform the briefing

Yes — gates feed the next iter's mutator briefing. This is the central apparatus loop, not a side channel. The flow:

```
   gate runs (per iter)
        ↓
   writes JSON to workspace/<gate-name>_<iter>.json
        ↓
   briefing provider reads JSON
        ↓
   briefing provider renders prose into MutatorBriefing
        ↓
   next iter's mutator prompt includes the prose
```

### Provider → gate dependency map

`src/ztare/orchestrator/briefing_providers/` consumes gate outputs:

| Provider | Reads from | Surfaces to mutator |
|---|---|---|
| `data_diagnostics.py` | substrate_critic.json + noise_profile.json | feature collapses, epistemic voids, solver routing recommendations |
| `fit_telemetry.py` | fit_features_result.json + residual diagnostic | last iter's K, BIC, fitted params, per-categorical-group residuals |
| `per_class_breakdown.py` | gate_harness_result.json | per-class MRE; **add R11 fail flags here** |
| `iter_trajectory.py` | eval_history.jsonl | last 5 iters' scores + weakest-points |
| `analogy_candidates.py` | analogy_log.jsonl | cross-domain candidate forms from ANALOGY |
| `asymptote_deviation.py` | global_gates.py output | declared-vs-fitted asymptote deltas |
| `contamination_defense.py` | denylist scan history | terms the mutator must avoid |

When a new gate ships, EITHER its output JSON gets a new briefing provider, OR an existing provider extends to read the new file. Otherwise the gate runs but the mutator never sees its findings — the apparatus learns nothing across iters. **R10's flag injection into briefing is the central wire-in for the kernel-camouflage detection to actually change mutator behavior.**

## How to add a new gate

1. **Decide the phase**: SUBSTRATE_VALIDATE / PRE_FIT / POST_FIT / PRE_JUDGE / POST_JUDGE.
2. **Write the gate module** in this directory with a clear `<gate>_gate.py` filename. Keep deterministic — no LLM calls except for special-case gates.
3. **Declare a rubric flag** for on/off control (default off for backwards compat). Document in spec §3.
4. **Wire into `autoresearch_loop.py`** at the right phase or register with `Cage` if dependency-managed.
5. **Add to GP-157 spec §3** as the next R-rule (R10, R11, R12 ...).
6. **Surface output to a briefing provider** so the mutator actually receives the gate's findings.
7. **Add to this README** under the right phase.
8. **Smoke test** in `tests/` with at least one canonical-pass and one canonical-fail input.

## Anti-patterns when adding gates

- Adding a gate that runs but doesn't surface to briefing — the mutator never learns from it. Worse than nothing because it costs compute without changing behavior.
- Adding a gate that hard-fails by default — breaks every existing run. New gates ship in observe-mode first (rubric-flagged off by default), get tested on 2-3 substrates, then get promoted to authoritative.
- Adding a gate that reads from another gate's internal state instead of its JSON output — couples gate implementations together. JSON is the contract.
- Skipping the spec update — future readers (and future you) need to know why each gate exists. The spec §3 R-rule table is the single source of truth.

## v5 Cage observe-mode → authoritative-mode promotion

Most rubrics currently have `cage_observe_mode: true` (Cage runs alongside, logs engagement matrix to `workspace/cage_engagement.jsonl`, doesn't enforce). To promote:

```
cage_observe_mode: false
cage_authoritative_mode: true
```

Effects:
- R8/R9 violations now hard-fail the candidate (previously: warning only).
- Future R10/R11 enforcement reads from rubric flags `enforce_per_class_farther_tail`, `r11_excluded_classes`, etc.
- Per-substrate gates (`enable_substrate_critic`, `enable_noise_profile`, etc.) keep their existing semantics.

The promotion is per-rubric, not global. Test on one homogeneous substrate (gp163d — R8/R9 should pass cleanly) before promoting on heterogeneous substrates (gp154 — R9 will refuse engagement until substrate is rebuilt).
