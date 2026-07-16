---
description: "The rubric JSON file format that drives autoresearch_loop.py."
---

# ZTARE Rubric File Specification

> Up: [Documentation map](../README.md)

*Status:* living document. Updated whenever the loop's rubric-field vocabulary changes.
*Last updated:* 2026-07-12.
*Authoritative source:* the actual field names + default values referenced in `src/ztare/validator/autoresearch_loop.py` via `rubric_data.get("<field>", <default>)`. If this doc disagrees with the source, the source wins and this doc should be corrected.

---

## 1. Purpose

A rubric is a JSON file at `rubrics/<slug>.json` that tells `autoresearch_loop.py` four things:

1. Which evidence carrier enters the kernel and which equality/binding rule governs it.
2. How to judge the mutator's thesis, the persona, the scoring dimensions, and the qualitative criteria.
3. Which quantitative gates to run, evidence-fit, uniqueness-gap, farther-tail, holdout, named-import.
4. How to size the run, stagnation thresholds, composition budget, holdout budget, discovery vs falsification mode.

A rubric that is structurally incoherent, e.g., claims a hidden-holdout gate but provides no `gate_harness.py`, either crashes the loop or silently defaults to a wrong configuration. Both are failure modes this spec exists to prevent.

---

## 2. Rubric flavors

Every rubric fits ONE of these flavors. Pick one before writing:

| Flavor | When to use | Characterized by |
|---|---|---|
| **Quantitative-discovery (blind GT)** | You have a ground-truth function and want the mutator to recover it blind. Phase B / Phase C per [GP-096](../../research_areas/seams/mission/discovery/GP-096_science_programme_decomposition_seam.md). | `fit_score_mode: "continuous_rmse"` or `"discrete_exact"`; `holdout_hard_gate: true`; `gate_harness.py` present; `evidence_holdout.txt` present. |
| **Quantitative-calibration (known GT, open)** | You have a GT and want to measure apparatus performance without hidden holdout. Instrument shakedown. | `fit_score_mode: "continuous_l2"` (default) or `"continuous_rmse"`; `holdout_hard_gate: false`; gates mostly default. |
| **Qualitative-thesis (no GT)** | Exploratory, thesis-driven, no numerical curve to fit. [GP-131](../../research_areas/seams/mission/discovery/GP-131_work_discovery_loop_seam.md) / [GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) / ztare_on_ztare class. | `disable_evidence_fit_gate: true` + reason; `disable_uniqueness_gap_gate: true` + reason; `fit_score_mode: "none"`; `holdout_hard_gate: false`; `enable_fit_primitive: false`. |
| **Worldmodel / interactive environment** | You have state/action transition evidence and want the mutator or deterministic miner to submit an executable transition law. ARC-AGI-3 / GP-250 class. | `evidence_carrier_kind: "transition_stream"`; `substrate_class: "interactive_environment"` or `fit_expression_grammar: "grid_dsl"`; `fit_score_mode: "discrete_exact"`; `require_i_model_in_submission: false`; project-local `gate_harness.py`; candidate carrier is `WORLD_MODEL_SPEC`, `PROGRAM`, or `step(observation, intervention, t)`. |

If you don't know which flavor you're writing, you are writing a broken rubric.

---

## 3. Required fields (all flavors)

| Field | Type | Meaning |
|---|---|---|
| `persona` | string | System-prompt persona for the LLM judge. Be specific, adversarial, domain-anchored. Not a placeholder. |
| `criteria` | object `{name: description}` | Named rubric criteria. Each value is the full scoring prompt for that criterion. |
| `dimensions` (optional for pure-criteria rubrics, required for weighted-dimension rubrics) | list of `{name, weight, description}` | Weighted rubric dimensions when you need explicit point allocation. Weights should sum to 100. |

### 3.1 Evidence-carrier identity

`evidence_carrier_kind` chooses the admission contract. It does not choose a
judge persona, candidate grammar, or score function.

| Value | Governing object | Admission and equality rule | Active consumer |
|---|---|---|---|
| `source_documents` | typed files under `raw/` | declared source type plus content digest; derived source index and compiled-evidence bindings must be current | document/claim evidence compiler |
| `transition_stream` | canonical `raw/episodes/episode_NNN.jsonl` logs | each non-empty log begins with a typed transition packet; byte identity binds any identity sidecar; fleet and evaluation slices cannot satisfy admission | episode replay, transition synthesis, worldmodel gates |

`source_documents` is the compatibility default. It includes structured text
formats such as CSV, TSV, JSON, and YAML, so existing quantitative substrates
retain their current path. Candidate scoring remains controlled by
`fit_score_mode` and the project gate; evidence-carrier admission does not turn
quantitative data into a qualitative substrate.

Existing rubrics with `substrate_class` in `{interactive_environment,
worldmodel, grid_world}` infer `transition_stream`. New interactive rubrics
should declare the field explicitly. A new carrier kind is not accepted by
analogy alone: add it only with a validator, a registered downstream consumer,
and an end-to-end first-fire test. Until then, tables/tensors/proof artifacts
continue through their already registered substrate paths.

---

## 4. Fit-scoring fields (quantitative flavors only)

| Field | Valid values | Default | Required when |
|---|---|---|---|
| `fit_score_mode` | `"continuous_l2"` \| `"continuous_rmse"` \| `"discrete_exact"` \| `"none"` | `"continuous_l2"` | Always, set to `"none"` for qualitative flavor. |
| `fit_required_vars` | list of variable names (e.g. `["n"]`, `["u", "psi"]`) | `["n"]` | Required for `discrete_exact`; recommended for all quantitative. |
| `fit_required_dimensionality` | int |, | For multi-variable targets; validator uses this to check thesis dimensions. |
| `fit_expression_grammar` | `"eml_only"` \| `"math_exp_only"` \| `"math_exp_trig"` \| `"py_exec"` \| omit | omit = full `math.*` | Controls the expression grammar for `fit_declaration`. `"eml_only"` restricts to `eml(x,y)=exp(x)−ln(y)`. `"math_exp_only"` restricts to `math.exp/log/sqrt`. `"math_exp_trig"` adds trig. `"py_exec"` allows full Python expression syntax (list comprehensions, generators, `range`, `sum`, `all`, etc.), use for algorithmic/number-theoretic substrates with `discrete_exact`. |
| `python_model_grammar` | object |, | Python-side constraint on `test_model.py` shape. |
| `evidence_fit_mode` | string |, | Further-grained fit-mode selector inside the quantitative path. |
| `evidence_fit_threshold` | float |, | Hard threshold for the evidence-fit gate. |
| `gate_residual_threshold` | float |, | Residual ceiling used by gates. |
| `farther_tail_region` | object or `null` | `null` | Defines the farther-tail region; `null` means no farther-tail gate. |
| `farther_tail_contract` | object |, | Contract the thesis must satisfy in the farther tail. |
| `holdout_hard_gate` | bool | `false` | Enables the hidden-holdout hard gate, requires `gate_harness.py` + `evidence_holdout.txt`. |
| `holdout_budget` | int | `0` | Budget for holdout evaluations. |
| `stop_on_gate_pass` | bool | `false` | Opt-in early stop: end the loop the moment a champion clears the deterministic hard gate (the holdout gate ran and did not fire, and the score is non-zero). Default off — governance runs the full `ITERS` budget and keeps falsifying above the gate floor. Turn on only for **exploit/harness** use cases that need a *gate-passing* model rather than maximal judge rigor — e.g. an interactive-substrate play loop where `ITERS` is a budget and each cycle should stop as soon as a valid model exists. The stop is a real success FLOOR (a gate pass), never a judge-score threshold, so it cannot be gamed into stopping on an unvalidated model. Requires `holdout_hard_gate: true` to be meaningful (else no hard gate runs and the flag is inert). The `--stop_on_gate_pass` CLI flag is an ad-hoc override with the same effect. |
| `composition_stagnation_threshold` | positive int | omit | Overrides the pivot-heuristic stagnation threshold for this project. When omitted, Newton-mode rubrics use 2 (pivot early), legacy/Kepler rubrics use 3. Set this only when a specific project needs more patience than its mode's default (e.g., a qualitative Newton substrate where score-0 streaks are expected). The override applies to both the pivot and emergency thresholds (emergency = pivot + 1). |

`fit_score_mode = "none"` is REQUIRED for qualitative rubrics. Anything else causes `global_evidence_fit` + `global_extrapolation_gap` gates to run against `test_model.py`, which will hard-fail and zero the score for any thesis-driven (non-numeric) project.

The `fit_score_mode: "rubric_only"` value does NOT exist. Invented values are silently treated as the default (`"continuous_l2"`), which causes the above hard-fail.

---

## 5. Gate-disabling fields (qualitative flavor primarily)

Every `disable_*_gate` field has a paired `disable_*_gate_reason` field. Writing the reason forces you to justify the disable AND provides provenance for future reviewers.

| Field | Paired reason field | Use when |
|---|---|---|
| `disable_evidence_fit_gate` | `disable_evidence_fit_gate_reason` | Evidence is text / qualitative; no numeric curve to fit. **Required: true for qualitative flavor.** |
| `disable_uniqueness_gap_gate` | `disable_uniqueness_gap_gate_reason` | Rival mechanisms are scored by rubric criteria, not by math-form keywords. **Typical for qualitative.** |
| `disable_parsimony_gate` | `disable_parsimony_gate_reason` | You're NOT minimizing parameter count (e.g. multi-paragraph strategy theses). |
| `disable_named_import_gate` | `disable_named_import_gate_reason` | You allow `test_model.py` to import external libraries (risky, default OFF). Include strong justification. |

Any `disable_*` flag WITHOUT its paired reason string should fail in review.

---

## 6. Run-discipline fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `composition_stagnation_threshold` | int | ≈10 | Iterations without structural change before stagnation-kill fires. |
| `composition_min_families` | int |, | Minimum structural families the mutator must propose before stagnation applies. |
| `composition_budget` | int |, | Maximum composition budget for the run. |
| `confirmation_threshold_runs` | int |, | Runs needed to confirm a constraint. |
| `gp103_stagnation_threshold` | int | ≈3 | Compression-gap-aware stagnation window ([GP-103](../../research_areas/seams/engine/GP-103_topology_induction_gap.md)). |
| `discovery_mode` | bool | `false` | Enables Phase-C discovery affordances (different gate semantics). |
| `falsification_mode` | string | `"continuous"` | `"bounded_discriminator"` is the qualitative-thesis variant. |
| `require_i_model_in_submission` | bool | inferred, legacy default `true` | Set `false` for qualitative/assertion-suite substrates. If omitted, the runner infers `false` for theorem-packet rubrics and for fully declared qualitative bounded-discriminator rubrics with fitting disabled, holdout disabled, and qualitative gate opt-outs present. |
| `epistemic_alignment` | object |, | M-form alignment audit configuration ([GP-105](../../research_areas/seams/reflexive/GP-105_mform_alignment_audit_seam.md)). |
| `cold_residual_successor_mode` | bool | `false` | Enables [GP-045](../../research_areas/seams/substrates/corrector/GP-045_cold_residual_01_pre_registration.md)-style cold-residual treatment. |

### 6.1 Worldmodel / interactive-environment contract

Interactive worldmodel substrates, such as ARC-AGI-3, are not scalar
`I_model` submissions and not qualitative assertion suites. Their submitted
artifact is an executable transition carrier:

- declare `evidence_carrier_kind: "transition_stream"`;
- declare `substrate_class: "interactive_environment"` or
  `fit_expression_grammar: "grid_dsl"` or `fit_score_mode: "discrete_exact"`;
- set `require_i_model_in_submission: false`;
- provide a project-local `gate_harness.py` that evaluates one of
  `WORLD_MODEL_SPEC`, `PROGRAM`, or `step(grid, action, t)`;
- keep replay/holdout gates as the candidate authority.

Prompt renderers may be called with sparse UI rubrics, but the substrate
contract must be hydrated from `rubrics/<slug>.json` before displaying
submission instructions. A worldmodel project must never be prompted to write a
scalar `I_model` merely because a diagnostic renderer omitted rubric fields.

---

## 7. Feature flags

| Field | Type | Default | Notes |
|---|---|---|---|
| `enable_fit_primitive` | bool | `true` | Whether to run the fit primitive. `false` for qualitative. |
| `enable_residual_diagnostics` | bool | `false` | Enables residual diagnostics ([GP-074](../../research_areas/seams/substrates/selkov/GP-074_component_c_residual_fingerprinting_seam.md)). |
| `enable_component_c` | bool | `false` | Legacy alias for `enable_residual_diagnostics`; accepted for old rubrics. |
| `enable_mform_audit` | bool | `false` | M-form alignment audit ([GP-105](../../research_areas/seams/reflexive/GP-105_mform_alignment_audit_seam.md)); qualitative rubrics typically enable this. |
| `enable_lean_proof` | bool | `false` | Lean-4 proof gate ([GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md)), requires `lean_prover_model`. |
| `residual_diagnostics_gt_module` | string | none | Sealed GT module used by residual diagnostics when enabled. |
| `residual_diagnostics_stagnation_k` | int | none | Residual-diagnostics stagnation threshold. |
| `component_c_gt_module` | string | none | Legacy alias for `residual_diagnostics_gt_module`; accepted for old rubrics. |
| `component_c_stagnation_k` | int | none | Legacy alias for `residual_diagnostics_stagnation_k`; accepted for old rubrics. |

---

## 8. Model flags

| Field | Valid values | Default | Notes |
|---|---|---|---|
| `general_office_model` | `"gemini"` \| `"gemini-pro"` \| `"claude"` \| `"claude-opus"` \| `"gpt4o"` \| `"gpt4.1"` \| `"gpt4.1-mini"` | set via flag | M-form audit model ([GP-105](../../research_areas/seams/reflexive/GP-105_mform_alignment_audit_seam.md)); must differ from judge + mutator per Chandler separation. |
| `lean_prover_model` | same vocabulary | `"gpt4.1"` | Lean-proof gate model when `enable_lean_proof: true`. |

*Model labels are NOT raw API model IDs.* Valid labels are the ZTARE aliases enumerated above. `gemini-2.5-pro-preview-*` or similar raw IDs WILL fail the argparse `choices=` check.

---

## 9. Synthesis / reporting

| Field | Type | Notes |
|---|---|---|
| `synthesis_renderer` | string | Which synth renderer to use (`founder_memo`, `policy_essay`, etc.). See `src/ztare/synthesis/`. |
| `reviewer_domains` | list of strings | Reviewer-domain lenses ([GP-079](../../research_areas/seams/protocol/GP-079_persona_library_unification_seam.md)) to inject into the skeptic persona. Read by findings runner; NOT by autoresearch_loop. |

---

## 10. Dynamic / committee rubrics

`make committee PROJECT=<slug>` writes `rubrics/dynamic_<slug>.json`, a multi-persona verification-panel rubric whose `committee` list replaces the single `persona`. Structure:

```json
{
  "committee": [
    {"name": "seat 1", "role": "...", "critique_frame": "...", "criteria": {...}},
    {"name": "seat 2", ...},
    {"name": "seat 3", ...}
  ],
  "fit_score_mode": "none",
  "disable_evidence_fit_gate": true,
  ...
}
```

Use the committee rubric as drop-in: `make experiment-loop PROJECT=<slug> RUBRIC=dynamic_<slug>`. Committee rubrics cost ~2-3× per iter but discriminate better than single-persona rubrics for exploratory projects.

Rubric-mode audit treats this shape as a `committee_panel`, a class distinct from
Newton/Kepler/calibration scoring rubrics. A panel can guide critique under
`--dynamic` and does not need `rubric_mode` or a Generative Yield dimension
unless it is promoted into a normal scoring rubric.

---

## 11. Worked examples

### 11a. Minimum qualitative-thesis rubric

```json
{
  "fit_score_mode": "none",
  "disable_evidence_fit_gate": true,
  "disable_evidence_fit_gate_reason": "qualitative thesis, text evidence, no numeric curve",
  "disable_uniqueness_gap_gate": true,
  "disable_uniqueness_gap_gate_reason": "rival mechanisms scored by rubric criteria, not keyword heuristic",
  "holdout_hard_gate": false,
  "enable_fit_primitive": false,
  "falsification_mode": "bounded_discriminator",
  "require_i_model_in_submission": false,
  "persona": "<adversarial domain-anchored reviewer, 3+ sentences>",
  "dimensions": [
    {"name": "...", "weight": 40, "description": "..."},
    ...
  ],
  "criteria": {
    "criterion_name": "What the judge scores for this criterion, prose.",
    ...
  }
}
```

The explicit `require_i_model_in_submission: false` pin is recommended for
readability. Our runner also infers the same assertion-suite contract when the
full qualitative bounded-discriminator pattern above is present.

### 11b. Minimum quantitative-discovery rubric (blind GT)

```json
{
  "fit_score_mode": "continuous_rmse",
  "fit_required_vars": ["n"],
  "evidence_fit_threshold": 0.05,
  "gate_residual_threshold": 0.05,
  "farther_tail_region": {"n": [7000, 100000]},
  "farther_tail_contract": {"max_global_residual": 0.05},
  "holdout_hard_gate": true,
  "holdout_budget": 1,
  "composition_stagnation_threshold": 10,
  "persona": "...",
  "criteria": {...}
}
```

Requires: `projects/<slug>/gate_harness.py` + `projects/<slug>/evidence_holdout.txt` + `make seal` before launch.

---

## 12. Validation checklist (before sealing a rubric)

1. Flavor declared explicitly in a top-of-file comment or the `notes` field.
2. No invented field names. Every field appears in this spec OR in `grep rubric_data.get src/ztare/validator/autoresearch_loop.py`.
3. `fit_score_mode` value is valid, one of `{continuous_l2, continuous_rmse, discrete_exact, none}`.
4. **Every `disable_*_gate: true` has its paired `_reason` string.**
5. If `holdout_hard_gate: true`, both `gate_harness.py` and `evidence_holdout.txt` exist in the project.
6. Model labels are ZTARE aliases, which are distinct from raw API IDs.
7. `persona` is ≥3 sentences, domain-anchored, names specific failure patterns it penalizes.
8. `dimensions[].weight` sums to 100 (if dimensions are used).
9. `criteria` names match `dimensions.name` when both are present (no orphan criteria).
10. `evidence_carrier_kind` names a registered admission contract; new
    interactive rubrics declare `transition_stream` explicitly.

Run `make validate-rubric PROJECT=<slug> RUBRIC=<slug>` before launch. That same deterministic validator is a prerequisite of `make loop`; it checks JSON structure, project-file presence, mode-specific rules such as Newton `Secondary observable` charter alignment, theorem-packet function exposure, and other launch blockers. Use `python -m json.tool rubrics/<slug>.json` only as a quick syntax check.

---

## 13. Common mistakes this spec exists to prevent

| Mistake | Symptom | Fix |
|---|---|---|
| `fit_score_mode: "rubric_only"` (invented value) | `global_evidence_fit` + `global_extrapolation_gap` hard-fail, score zeroed | Use `"none"` + `disable_evidence_fit_gate: true` + reason. |
| `discrete_exact` without `fit_expression_grammar: "py_exec"` on algorithmic substrate | Mutator proposes list-comprehension or loop expressions; all fail `expression_validation_error`; score stuck at 0 forever | Add `"fit_expression_grammar": "py_exec"` to rubric. The default grammar only allows `arithmetic + math.*`. |
| Qualitative rubric without `disable_evidence_fit_gate: true` | Same as above, global gates run against stub `test_model.py`. | Add the disable flag + reason. |
| `holdout_hard_gate: true` without `gate_harness.py` | `make experiment-loop` aborts with "harness missing". | Generate the harness first; or set `holdout_hard_gate: false`. |
| Model label typed as raw API ID | argparse `choices=` rejects | Use ZTARE alias. |
| Using `make loop` when rubric has hard-gate | UNDERIDENTIFIED kills the run at iter 3 | Use `make experiment-loop` which auto-sets `--underidentified_after`. |
| Hand-writing a rubric outside `make generate-gp` | Structural omissions like missing `dimensions` or unpaired reason strings | Use `make generate-gp PROJECT=<slug> BRIEF="..."`. |
| Treating a transition bank as document prose | Source check scans fleet/evaluation logs, demands document typing, or sends structured state packets to the evidence compiler | Set `evidence_carrier_kind: "transition_stream"`; retain only canonical episode logs at admission. |

---

## 14. Historical context

- [Pre-run rubric review](../../research_areas/seams/protocol/GP-054_rubric_quality_and_generation_seam.md) governs how rubrics are generated and reviewed, and ties to `make rubric-review`.
- [Rubric for unknown domains](../../research_areas/seams/protocol/GP-075_rubric_for_unknowns_seam.md) governs the taxonomy of GT-independent versus GT-dependent criteria in discovery mode. Historical seam: `GP-075`.
- [Qualitative scaffold generator](../../research_areas/seams/protocol/GP-104_qualitative_rubric_gate_configuration_seam.md) / `make generate-gp` is the standard tool for fresh qualitative scaffolding. It produces Type-B rubric scaffolds that comply with this spec. Historical seam: `GP-104`.

---

## 15. Change log

- 2026-04-23: Initial version of this specification document. Filed after a hand-rolled rubric with `fit_score_mode: "rubric_only"` caused score-zero hard-fails on the ztare_on_ztare project. Triggering incident: the failure mode table in §13 is a direct post-mortem. (Author: claude_manager.)
- 2026-04-23 (later): [GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) Round 4 additions, §§ 16-20 below. Rubric-loader in `autoresearch_loop.py` enforces `py_exec` gates + `rubric_mode` discipline fail-closed. Architectural map updated with new region `rubric_preflight` and new exit `GP133_R4_gate`.
- 2026-07-12: Added `evidence_carrier_kind` and carrier-indexed admission. Transition streams now bypass the document compiler and enter through episode-log identity/replay contracts; existing document and quantitative rubrics retain the compatibility path.

---

## 16. `rubric_mode` top-level field ([GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) Round 4)

Every rubric SHOULD declare its epistemic mode. Enforced by the rubric-preflight gate in `autoresearch_loop.py`:

| Value | Meaning | Gate behavior |
|---|---|---|
| `"newton"` | Discovery-class. The `dimensions` list MUST include a dimension whose name contains `"Generative Yield"` (case-insensitive) with weight ≥15. | **Fail-closed:** autoresearch loop refuses to launch if the Generative Yield dimension is missing or under-weighted. |
| `"kepler"` | Descriptive-fit. No Generative Yield requirement. | Passes gate unconditionally. Outputs labeled Kepler-class descriptive findings. |
| `"calibration"` | Apparatus-shakedown. Discovery claims suppressed. | Passes gate unconditionally. Outputs labeled calibration-class. |
| unknown value | invalid mode | **Fail-closed:** refuses to launch. |
| absent | legacy unspecified | Passes gate (no warning emitted in current implementation; legacy rubrics continue to work). |

`make generate-gp` emits `rubric_mode: "kepler"` by default. Promotion to `rubric_mode: "newton"` requires principal signoff and rubric updates to include Generative Yield.

---

## 17. `fit_expression_grammar: "py_exec"`, gates + discipline ([GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) Round 4)

When a rubric sets `fit_expression_grammar: "py_exec"`, two additional fields are required. Enforced by the rubric-preflight gate:

| Field | Type | Enforcement |
|---|---|---|
| `py_exec_authorized_by` | non-empty string | **Required.** Seam ID (e.g. `"GP-133-Round-4"`) or principal signoff string. Provenance for why this substrate qualifies for py_exec grammar. Missing/empty → fail-closed. |
| `expression_byte_budget` | positive int, default 200 | If missing, emits warning and defaults to 200. If present but non-positive-int, fail-closed. Anti-lookup-table defense, ternary-chain lookups pass parsimony but explode on byte length. |

py_exec is never a default in `make generate-gp` or any scaffolding tool. Explicit maintainer action only.

---

## 18. Generative Yield dimension (required for Newton-mode rubrics)

When `rubric_mode: "newton"`, the rubric's `dimensions` list MUST include a dimension whose name contains `"Generative Yield"` with weight ≥ 15% (recommended 20%). Enforced at rubric-preflight.

Scoring rubric for the dimension should distinguish:

- 0 points: primitive predicts only the primary fitting target (Kepler-class naked fit).
- Partial (~50%): primitive names a secondary observable but no evaluation method.
- Full: primitive names a distinct mathematically-orthogonal secondary observable AND pre-commits to measurement method + expected value/range.

Trivial restatements of the fitting target score 0.

*Tracked contract requirement:* Newton-mode rubrics should carry a
`secondary_observable_contract` object so the requirement survives even when a
project workspace is local or ignored. If the object is present, launch
preflight requires all four fields below to be non-empty:

```json
{
  "secondary_observable_contract": {
    "observable": "<what is measured beyond the primary fit/admission target>",
    "measurement": "<how the observable is computed or scored>",
    "expected_range": "<expected value, range, or pass condition>",
    "falsifier": "<what observation would refute the generative claim>"
  }
}
```

Project charters targeted by Newton-mode rubrics should also require each
primitive to include a `Secondary observable` field in the thesis format. The
rubric-level contract is the durable run surface and the charter is the
reviewer-facing local version. Launch preflight accepts a valid rubric-level
contract or a project charter that contains `Secondary observable`. Malformed
rubric-level contracts fail even if the charter contains the heading.

---

## 19. F-row extensions for discovery-class labeling ([GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) Round 4)

F-rows in the experiment track record carry two new fields when the run's rubric has `rubric_mode: "newton"` OR `fit_expression_grammar: "py_exec"`:

| Field | Values | Notes |
|---|---|---|
| `discovery_class` | `recognition` \| `synthesis` \| `synthesis_incompressible` \| `derivation` \| `calibration` | Auto-classifier: `src/ztare/findings/discovery_class_classifier.py`. Default on py_exec + known-OEIS runs: `recognition`. |
| `predicted_secondary_observables` | list of `{observable, method, expected}` triples (may be empty) | Empty ⇒ Kepler-class descriptive finding. Non-empty with verified predictions ⇒ Newton-class generative finding. |

Staleness check: F-rows with missing `discovery_class` in Newton-mode or py_exec-mode runs are flagged stale. Any paper or patent citing `discovery_class: recognition` as "discovery" triggers a reviewer flag.

---

## 20. PR checklist, governance for new grammar / mode additions ([GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) Round 4)

Any pull request that:

1. adds a new `fit_expression_grammar` value (e.g. introduces `lean_tactic`, `coq_expr`, `smt_z3`, future), OR
2. promotes a project from `rubric_mode: kepler` → `rubric_mode: newton` with external-citation intent, OR
3. changes default behavior of `make generate-gp` around rubric_mode or fit_expression_grammar,

must satisfy ALL of:

- Panel review entry appended to `GP-133 (internal seam)` (or successor discovery-panel seam) covering: epistemic framing, anti-gaming defenses, scope containment, governance implications.
- Rubric-spec doc update (this file) with the new mode/grammar documented in the appropriate section.
- Rubric-loader gate update in `autoresearch_loop.py` enforcing any required-field discipline for the new grammar or mode.
- Architecture-map update in the maintained autoresearch architecture map if the gate changes region structure or exit taxonomy. Public behavior changes also update the public architecture/capability docs.
- Principal signoff in the PR description for any default-behavior change.

Retroactive: [GP-133](../../research_areas/seams/mission/discovery/GP-133_R4_py_exec_sandbox_review.md) Round 4 itself is the first application of this checklist. Future PRs follow the checklist prospectively.

---

## 21. Cage authoritative + reflexive-primitive flags ([GP-157](../../research_areas/seams/apparatus/cage/GP-157_R10_R16_backport_scoping_2026_05_06.md) / [GP-167](../../research_areas/seams/mission/org/GP-167_multi_agent_interface_form_factor_seam.md)-[GP-170](../../research_areas/seams/engine/lean/GP-170_symbolic_logic_cage_seam.md), 2026-04-26)

The 2026-04-26 wave promoted the Cage Orchestrator from observe-mode to authoritative across substrates and added six apparatus-general flags. Loader gates live in `src/ztare/orchestrator/state.py::resolve_cage_mode` and the per-flag dispatch sites listed below.

### 21.1 Cage mode flags

| Field | Values | Source of truth | Notes |
|---|---|---|---|
| `cage_observe_mode` | bool | `orchestrator/state.py::resolve_cage_mode` | Cage runs alongside, logs engagement matrix to `workspace/cage_engagement.jsonl`, does NOT enforce verdicts. |
| `cage_authoritative_mode` | bool | same | Cage verdicts are authoritative; gate failures decrement scores via `apply_verdict_to_eval`. **`cage_authoritative_mode=true` IMPLIES observe-mode behaviour**, when both flags are set, authoritative wins. |
| `cage_meta` | object | `orchestrator/state.py::build_cage_runtime` | Required keys: `class` (substrate-class predicate), `target_convention_homogeneity`, plus optional `algebraic_constraints`, `feature_dimensions`. Read by `can_handle` predicates on each Cage-routed gate. |

Per [GP-157](../../research_areas/seams/apparatus/cage/GP-157_R10_R16_backport_scoping_2026_05_06.md) §3a (binding rule): all gates from R10 onward MUST be Cage-routed (register via `register_<name>_gate(s)(cage)` from `state.py::build_cage_runtime`). Direct-wire gates in `autoresearch_loop.py` are frozen, no new direct-wire imports allowed.

### 21.2 Per-class farther-tail flags (R10 / R11)

| Field | Default | Read by |
|---|---|---|
| `enforce_per_class_farther_tail` | `false` | `gates/cross_class_extrapolation_gate.py::dispatch_r10_r11_from_harness_json` |
| `r11_excluded_classes` | `[]` | same, class labels listed here skip R11 hard-fail enforcement; R10 cross-class diagnostic still runs |
| `r11_excluded_classes_reason` | string | informational, surfaced in seam audits |

R10 (cross-class extrapolation diagnostic, POST_FIT) always runs when Cage is active and substrate has `cage_meta.class` set. R11 (per-class MRE ceiling, PRE_JUDGE) only enforces when `enforce_per_class_farther_tail=true`.

### 21.3 Forced-REFRAME flags ([GP-168](../../research_areas/seams/mission/org/GP-168_org_design_unfalsifiability_seam.md))

| Field | Default | Read by |
|---|---|---|
| `enable_forced_reframe` | `true` | `briefing_providers/forced_reframe.py::ForcedReframeBriefingProvider.applies` |
| `gp168_stagnation_threshold` | `3` | `orchestrator/forced_reframe.py::detect_forced_reframe_trigger` |
| `gp168_ast_bucket_threshold` | `5` | same |
| `gp168_max_consecutive_fires` | `2` | same, caps reframe budget so the apparatus does not lock the mutator into perpetual reframe loops |

Forced-REFRAME injects mandatory disjoint-architecture alternatives parsed from `GP-164 (internal seam)*.md` §Appendix (loader: `orchestrator/alien_math_seam_loader.py`). Falls back to a hardcoded list of 3 framings (RG-flow / multifractal Legendre / modular q-expansion) if the seam file is unavailable.

### 21.4 Cold-LLM Erdős seed flags ([GP-169](../../research_areas/seams/engine/discovery/GP-169_cold_llm_synthetic_erdos_seam.md), Phase 1: iter-0 baseline)

| Field | Default | Read by |
|---|---|---|
| `enable_cold_llm_erdos_seed` | `false` | `orchestrator/pre_iter1_dispatch.py::dispatch_pre_iter1_cage` (iter-0 baseline) + `briefing_providers/cold_llm_seed.py::ColdLlmSeedBriefingProvider.applies` (per-iter render) |
| `cold_llm_seed_model_id` | **OPTIONAL**, defaults to the runtime mutator model when omitted or set to `"@mutator"` | same. Default behavior (since 2026-04-26): use whatever `MUTATOR_MODEL_ID` resolved to at run start. Set to a literal model id (e.g. `"claude-opus-4-6"`) only when a maintainer wants strict cross-family hygiene; the default trades cross-family for cost. The fallback flows through `pre_iter1_dispatch.dispatch_pre_iter1_cage(..., mutator_model_id=...)` and `cold_llm_seed_requery.maybe_requery_cold_seed(..., mutator_model_id=...)`. |
| `cold_llm_seed_forbidden_domain` | `null` | same. Free-form string injected into the cold-LLM prompt as a forbidden-domain clause; e.g. `"astrophysics"` for gp163d, `"machine learning, deep learning, neural-network scaling, AI"` for gp154. |
| `cold_llm_seed_k_law_budget` | `7` | same, max K per candidate form |
| `cold_llm_seed_timeout_seconds` | `30` | same, hard wall-clock budget; on timeout the seed mechanism degrades cleanly (iter-1 proceeds without the cold seed) |

### 21.5 Erdős re-query on stagnation ([GP-169](../../research_areas/seams/engine/discovery/GP-169_cold_llm_synthetic_erdos_seam.md), Phase 2, 2026-04-26)

When stagnation triggers fire, the cold LLM is re-queried with the current residual fingerprint (computed from `noise_profile_post_fit_iter_*.json` + latest `analogy_log.jsonl` + `substrate_critique.json`). Refreshed candidates replace the iter-0 seed in the briefing via the same provider channel. Idempotent within a stagnation event (signature-cached); capped per run.

| Field | Default | Read by |
|---|---|---|
| `enable_erdos_requery_on_stagnation` | `true` (when cold-seed enabled) | `orchestrator/cold_llm_seed_requery.py::maybe_requery_cold_seed` |
| `erdos_requery_stagnation_threshold` | `2` | `cold_llm_seed_requery.py::detect_stagnation` |
| `erdos_requery_ast_bucket_threshold` | `3` | same |
| `erdos_requery_max_per_run` | `3` | `maybe_requery_cold_seed` |

The refreshed-seed banner in the mutator briefing (`🔎 GP-169, REFRESHED (iter N, MANDATORY CONSIDER)`) signals the second cold draw. Iter-0 baseline is preserved on disk as `cold_llm_seed_iter0.json`; refreshes write `cold_llm_seed_requery_iter_NNN.json`.

### 21.6 Substrate-class + framer flags (read by new gates)

These predate this wave and are now read by R10/R11/R13-R16, so they must be set when adopting Cage authoritative mode:

| Field | Notes |
|---|---|
| `substrate_class_key` | feature key whose values define the substrate's class taxonomy (e.g. `"system_class"` for gp163d, `"study"` for gp154). R11 / SubstrateCritic / DataDiagnostics group residuals by this key. |
| `framer_primary_feature_key` | 1D projection axis for the active framer (e.g. `"radius_log10"` / `"N_log10"`). Required when `enable_framer=true`. |
| `enable_analogy` | bool, fires the L1 ANALOGY mechanism (cross-domain candidate forms triggered by residual fingerprint) |
| `enable_framer` | bool, fires the v2.0 active-framer (Box-Cox / log / no-transform via raw-coord BIC) |

### 21.7 Numeric redaction in DataDiagnostics briefing

`briefing_providers/data_diagnostics.py` buckets all leakable numerics surfaced to the mutator:

- Row-fraction phrases (`X/Y rows`) → `"nearly all rows" / "majority of rows" / "minority" / "few rows"`
- Bare floats → `<small_value> / <value> / <large_value>`
- Regime-break magnitudes → bucketed (exact `split_at_x` held privately by the gate harness)
- `feature_dimensionality_collapses.relative_range` → bucketed (`"essentially constant (< 0.1%)"`, ...)

Numerics remain in `workspace/substrate_critique.json` for maintainer audit; only the briefing-rendered text is redacted. No rubric flag, unconditional protection against RH-13 / RH-18 mutator-side numeric memorization.

### 21.8 Symbolic Logic Cage ([GP-170](../../research_areas/seams/engine/lean/GP-170_symbolic_logic_cage_seam.md), R12)

R12 runs as a Cage-routed PRE_FIT gate that reduces `PARAMETRIC_FORM` via SymPy + AST-rewrite (`where()` → `Piecewise`, `sigmoid()` → closed form) and checks declared `cage_meta.algebraic_constraints` before the fit primitive sees the form. No additional rubric flag, engagement is gated by `cage_meta.algebraic_constraints` being a non-empty list.

### 21.8aa Linear observable coercivity gate (2026-05-23)

Use this when a substrate asks a scalar or low-rank observable to recover, bound, or certify a higher-dimensional target structure. It is orthogonal to Buckingham/pi-group checks: dimensions may match while the observation map still has a kernel. Default is advisory. Strict mode skips the fit on violations.

| Field | Default | Read by |
|---|---|---|
| `enable_linear_observable_coercivity_gate` | `false` | `validator/autoresearch_loop.py` and Cage registry |
| `linear_observable_coercivity_targets` | `[]` | list of checks with `label`, `target_dimension`, `observable_rank`, optional `full_reconstruction_receipt`, `coercivity_receipt`, `kernel_quotient_dimension`, `kernel_quotient_receipt`, `kernel_witness_present`, `dimensionally_compatible`, `labels` |
| `linear_observable_coercivity_strict` | `false` | when true, any failed check skips the fit and writes `workspace/linear_observable_coercivity.json` |

### 21.8a Constant-laundering score cap (Gemini-Pro panel, 2026-04-26)

When the structural anti-pattern gates (R20 / R21 / R24) detect a form embedding hardcoded literals as hidden degrees of freedom, the apparatus deterministically caps the score below the Newton-step threshold. The judge does NOT perform AST analysis (LLMs are blind to AST topology and get talked out of it by mutator prose). That cap is enforced in `orchestrator/post_harness_dispatch.py::apply_verdict_to_eval` before the eval is finalized.

| Field | Default | Read by |
|---|---|---|
| `cage_constant_laundering_score_cap` | `50` | `post_harness_dispatch.py::dispatch_post_harness_cage` |
| `effective_parameter_count_slack` | `0` | `gates/structural_anti_pattern_gates.py::estimate_effective_parameter_count` (R21), declared K must match effective K. Set higher only if the substrate has legitimate physical constants the mutator should be allowed to hardcode. |
| `enable_withheld_value_leakage_gate` | `true` | R20 |
| `enable_effective_parameter_count_gate` | `true` | R21 |
| `enable_apparatus_meta_runner_gate` | `true` | R22 (now consumes R20/R21/R24 verdicts + regex catalog for RH-13/RH-17) |
| `enable_feature_bump_pattern_gate` | `true` | R24 (NEW 2026-04-26), AST-walk for `(feature - C)` / `(feature / C)` patterns |
| `withheld_value_leakage_monitored_keys` | `[]` (auto-includes all features referenced in PARAMETRIC_FORM) | R20 / R24 |

R20/R21/R24 verdicts feed R22, the meta-runner translates structural detections into RH codes (RH-18, RH-18-ANCHOR, RH-EFFK-LAUNDER) for human-readable judge feedback. R22 retains a regex catalog only for orthogonal patterns the structural detectors don't cover (RH-13 categorical-as-continuous, RH-17 explicit lookup table).

### 21.8b Relationship to v4-era anti-gaming gates ([GP-086](../../research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md))

The v4-era hardening pillars (`circularity_gate`, `falsifiability_gate`, `derived_constraints`, `structural_constraint_extractor`, `negative_space_extractor`, `bridge_scope_contract`, `domain_match_gate`, `asymptotic_claim_discipline`) detect thesis-structural properties: does the form have rivals, do parameters exceed evidence count, does the falsification suite exist, etc.

R20/R21/R24 detect literal-structural properties: do hardcoded numbers in the form coincide with substrate statistics, does declared K match effective K, does the form embed feature-relative bumps. These are orthogonal to the v4 pillars. Both layers can co-fire on a single form and neither replaces the other. R22 was always regex-based for RH-13/17/18. The 2026-04-26 refactor moved RH-18 detection to R24's AST walk so the iter-4 sigmoid-window escalation (which the regex missed) gets caught.

`v4_meta_runner.py` (stage-gating for hardening projects) is unrelated to R22 (apparatus-meta-runner). Former gates project promotions. Latter labels gaming patterns. Don't conflate.

### 21.8c META-GATE 2C, Post-run LLM diagnostic auditor (2026-04-26)

Post-run hook that calls a cross-family LLM to read the run's trace
(`eval_history.jsonl + cage_engagement.jsonl + substrate_critique.json
+ iteration_telemetry.jsonl`) and identify what apparatus-side detection
would have moved the needle when the run capped below the Newton-step
threshold. Default OFF, opt-in for production runs. The audit produces a
PROPOSAL. The maintainer decides whether to act.

| Field | Default | Read by |
|---|---|---|
| `enable_post_run_meta_audit` | `false` | `validator/autoresearch_loop.py` (post-loop hook) → `orchestrator/post_run_meta_audit.py::run_post_run_meta_audit` |
| `meta_audit_model_id` | `claude-haiku-4-5` | same. Cross-family from mutator AND judge by convention. Override only when the maintainer wants to swap audit models. |

Cost contract: hard 30s wall-clock, ~5K input tokens, ~2K output tokens
per audit. On failure: log + continue. Writes
`workspace/post_run_meta_audit.{json,md}`.

Retroactive use: `make audit-run-meta PROJECT=<name>` runs the auditor
against an already-completed project's workspace without touching the
main loop.

### 21.8d META-GATE 2, G-EVIDENCE-GAP-ENRICHMENT (EGE) (2026-04-26)

Pre-iter-1 trigger that fires when R26
(`withheld_class_feature_collapses` non-empty in
`substrate_critique.json`) reports a within-withheld-class data
ceiling. For each `(class, feature)` collapse, an LLM proposes
literature sources that publish per-system values of the collapsed
feature for the class's system_ids. The output is a list of
PROPOSALS. The maintainer reviews and (separately) decides whether to
run `make enrich-substrate`. EGE never auto-edits substrates.

| Field | Default | Read by |
|---|---|---|
| `enable_evidence_gap_enrichment_proposals` | `false` | `validator/autoresearch_loop.py` (post pre-iter-1 hook) → `orchestrator/evidence_gap_enrichment.py::propose_evidence_gap_enrichment` |
| `evidence_gap_model_id` | `@mutator` | same. The `@mutator` sentinel resolves to the runtime mutator model. Set to a literal model id (e.g. `claude-opus-4-6`) for cross-family hygiene, reviewers with WebSearch-capable model runtimes prefer Anthropic claude-opus or claude-sonnet here. |

Cost contract: hard 60s wall-clock per gap, ~3K input tokens, ~3K
output tokens. On failure: log + continue. Writes
`workspace/evidence_gap_enrichment_proposals.json`.

EGE separates two bottleneck types: the apparatus handles the
compute/search side, and EGE flags the cases where the limit is missing
data the apparatus cannot synthesize. The maintainer-side decision (do
these proposals fit? does the substrate enrichment generalize?) stays
human.

### 21.8e Parallel-mutator fan-out

The parallel-mutator path is opt-in through rubric fields. K=1 runs the
ordinary single mutator. The loop calls the
parallel-mutator wrapper only when `should_run_parallel(...)` is true.

| Field | Default | Read by |
|---|---|---|
| `parallel_mutator_k` | `1` | `orchestrator/blitz_dispatch.py::should_run_parallel` |
| `parallel_mutator_force` | `false` | same |
| `parallel_mutator_force_iters` | `[]` | same |
| `parallel_mutator_min_stagnation` | `1` | same |
| `parallel_mutator_k1_ablation_every` | `0` | same |
| `enable_recombination` | `false` | `orchestrator/blitz_dispatch.py::dispatch_mutator_blitz` |

Contract: no rubric flag, no fan-out. `parallel_mutator_k > 1` only
becomes active after `parallel_mutator_force`, `parallel_mutator_force_iters`,
or the stagnation threshold selects it. Subscription-backed mutators follow
the same rule; they are not parallelized because
`AGENT_MUTATOR=1` is set.

### 21.9 Compatibility with older substrates

Substrates that pre-date this wave (no `cage_meta`, no per-class flags, no cold-seed) continue to run unchanged. The loader returns `mode="off"` from `resolve_cage_mode` when neither `cage_observe_mode` nor `cage_authoritative_mode` is set. All [GP-168](../../research_areas/seams/mission/org/GP-168_org_design_unfalsifiability_seam.md) / [GP-169](../../research_areas/seams/engine/discovery/GP-169_cold_llm_synthetic_erdos_seam.md) hooks check their `enable_*` flags before firing, and the DataDiagnostics provider applies redaction unconditionally (it never leaks more than before).
