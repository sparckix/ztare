# ZTARE Rubric File Specification

**Status:** living document. Updated whenever the loop's rubric-field vocabulary changes.
**Last updated:** 2026-04-23.
**Authoritative source:** the actual field names + default values referenced in `src/ztare/validator/autoresearch_loop.py` via `rubric_data.get("<field>", <default>)`. If this doc disagrees with the source, the source wins and this doc should be corrected.

---

## 1. Purpose

A **rubric** is a JSON file at `rubrics/<slug>.json` that tells `autoresearch_loop.py` three things:

1. **How to judge the mutator's thesis** — the persona, the scoring dimensions, and the qualitative criteria.
2. **Which quantitative gates to run** — evidence-fit, uniqueness-gap, farther-tail, holdout, named-import.
3. **How to size the run** — stagnation thresholds, composition budget, holdout budget, discovery vs falsification mode.

A rubric that is structurally incoherent — e.g., claims a hidden-holdout gate but provides no `gate_harness.py` — either crashes the loop or silently defaults to a wrong configuration. Both are failure modes this spec exists to prevent.

---

## 2. Rubric flavors

Every rubric fits ONE of three flavors. Pick one before writing:

| Flavor | When to use | Characterized by |
|---|---|---|
| **Quantitative-discovery (blind GT)** | You have a ground-truth function and want the mutator to recover it blind. Phase B / Phase C per GP-096. | `fit_score_mode: "continuous_rmse"` or `"discrete_exact"`; `holdout_hard_gate: true`; `gate_harness.py` present; `evidence_holdout.txt` present. |
| **Quantitative-calibration (known GT, open)** | You have a GT and want to measure apparatus performance without hidden holdout. Instrument shakedown. | `fit_score_mode: "continuous_l2"` (default) or `"continuous_rmse"`; `holdout_hard_gate: false`; gates mostly default. |
| **Qualitative-thesis (no GT)** | Exploratory, thesis-driven, no numerical curve to fit. GP-131 / GP-133 / ztare_on_ztare class. | `disable_evidence_fit_gate: true` + reason; `disable_uniqueness_gap_gate: true` + reason; `fit_score_mode: "none"`; `holdout_hard_gate: false`; `enable_fit_primitive: false`. |

If you don't know which flavor you're writing, you are writing a broken rubric.

---

## 3. Required fields (all flavors)

| Field | Type | Meaning |
|---|---|---|
| `persona` | string | System-prompt persona for the LLM judge. Be specific, adversarial, domain-anchored. Not a placeholder. |
| `criteria` | object `{name: description}` | Named rubric criteria. Each value is the full scoring prompt for that criterion. |
| `dimensions` (optional for pure-criteria rubrics, required for weighted-dimension rubrics) | list of `{name, weight, description}` | Weighted rubric dimensions when you need explicit point allocation. Weights should sum to 100. |

---

## 4. Fit-scoring fields (quantitative flavors only)

| Field | Valid values | Default | Required when |
|---|---|---|---|
| `fit_score_mode` | `"continuous_l2"` \| `"continuous_rmse"` \| `"discrete_exact"` \| `"none"` | `"continuous_l2"` | Always — set to `"none"` for qualitative flavor. |
| `fit_required_vars` | list of variable names (e.g. `["n"]`, `["u", "psi"]`) | `["n"]` | Required for `discrete_exact`; recommended for all quantitative. |
| `fit_required_dimensionality` | int | — | For multi-variable targets; validator uses this to check thesis dimensions. |
| `fit_expression_grammar` | `"eml_only"` \| `"math_exp_only"` \| `"math_exp_trig"` \| `"py_exec"` \| omit | omit = full `math.*` | Controls the expression grammar for `fit_declaration`. `"eml_only"` restricts to `eml(x,y)=exp(x)−ln(y)`. `"math_exp_only"` restricts to `math.exp/log/sqrt`. `"math_exp_trig"` adds trig. `"py_exec"` allows full Python expression syntax (list comprehensions, generators, `range`, `sum`, `all`, etc.) — use for algorithmic/number-theoretic substrates with `discrete_exact`. |
| `python_model_grammar` | object | — | Python-side constraint on `test_model.py` shape. |
| `evidence_fit_mode` | string | — | Further-grained fit-mode selector inside the quantitative path. |
| `evidence_fit_threshold` | float | — | Hard threshold for the evidence-fit gate. |
| `gate_residual_threshold` | float | — | Residual ceiling used by gates. |
| `farther_tail_region` | object or `null` | `null` | Defines the farther-tail region; `null` means no farther-tail gate. |
| `farther_tail_contract` | object | — | Contract the thesis must satisfy in the farther tail. |
| `holdout_hard_gate` | bool | `false` | Enables the hidden-holdout hard gate — requires `gate_harness.py` + `evidence_holdout.txt`. |
| `holdout_budget` | int | `0` | Budget for holdout evaluations. |
| `composition_stagnation_threshold` | positive int | omit | Overrides the pivot-heuristic stagnation threshold for this project. When omitted, Newton-mode rubrics use 2 (pivot early), legacy/Kepler rubrics use 3. Set this only when a specific project needs more patience than its mode's default (e.g., a qualitative Newton substrate where score-0 streaks are expected). The override applies to both the pivot and emergency thresholds (emergency = pivot + 1). |

**`fit_score_mode = "none"` is REQUIRED for qualitative rubrics.** Anything else causes `global_evidence_fit` + `global_extrapolation_gap` gates to run against `test_model.py`, which will hard-fail and zero the score for any thesis-driven (non-numeric) project.

**The `fit_score_mode: "rubric_only"` value does NOT exist.** Invented values are silently treated as the default (`"continuous_l2"`), which causes the above hard-fail.

---

## 5. Gate-disabling fields (qualitative flavor primarily)

Every `disable_*_gate` field has a paired `disable_*_gate_reason` field. Writing the reason forces you to justify the disable AND provides provenance for future reviewers.

| Field | Paired reason field | Use when |
|---|---|---|
| `disable_evidence_fit_gate` | `disable_evidence_fit_gate_reason` | Evidence is text / qualitative; no numeric curve to fit. **Required: true for qualitative flavor.** |
| `disable_uniqueness_gap_gate` | `disable_uniqueness_gap_gate_reason` | Rival mechanisms are scored by rubric criteria, not by math-form keywords. **Typical for qualitative.** |
| `disable_parsimony_gate` | `disable_parsimony_gate_reason` | You're NOT minimizing parameter count (e.g. multi-paragraph strategy theses). |
| `disable_named_import_gate` | `disable_named_import_gate_reason` | You allow `test_model.py` to import external libraries (risky — default OFF). Include strong justification. |

Any `disable_*` flag WITHOUT its paired reason string should fail in review.

---

## 6. Run-discipline fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `composition_stagnation_threshold` | int | ≈10 | Iterations without structural change before stagnation-kill fires. |
| `composition_min_families` | int | — | Minimum structural families the mutator must propose before stagnation applies. |
| `composition_budget` | int | — | Maximum composition budget for the run. |
| `confirmation_threshold_runs` | int | — | Runs needed to confirm a constraint. |
| `gp103_stagnation_threshold` | int | ≈3 | GP-103 Compression-Gap-aware stagnation window. |
| `discovery_mode` | bool | `false` | Enables Phase-C discovery affordances (different gate semantics). |
| `falsification_mode` | string | `"continuous"` | `"bounded_discriminator"` is the qualitative-thesis variant. |
| `epistemic_alignment` | object | — | GP-105 M-form alignment audit configuration. |
| `cold_residual_successor_mode` | bool | `false` | Enables GP-045-style cold-residual treatment. |

---

## 7. Component / feature flags

| Field | Type | Default | Notes |
|---|---|---|---|
| `enable_fit_primitive` | bool | `true` | Whether to run the fit primitive. `false` for qualitative. |
| `enable_component_c` | bool | `false` | GP-074 Component C residual fingerprinting. |
| `enable_mform_audit` | bool | `false` | GP-105 M-Form alignment audit (qualitative rubrics typically enable this). |
| `enable_lean_proof` | bool | `false` | GP-088 Lean-4 proof gate — requires `lean_prover_model`. |
| `component_c_gt_module` | string | — | Path to Component C GT module if enabled. |
| `component_c_stagnation_k` | int | — | Component C stagnation threshold. |

---

## 8. Model flags

| Field | Valid values | Default | Notes |
|---|---|---|---|
| `general_office_model` | `"gemini"` \| `"gemini-pro"` \| `"claude"` \| `"claude-opus"` \| `"gpt4o"` \| `"gpt4.1"` \| `"gpt4.1-mini"` | set via flag | GP-105 auditor model — must differ from judge + mutator per Chandler separation. |
| `lean_prover_model` | same vocabulary | `"gpt4.1"` | Lean-proof gate model when `enable_lean_proof: true`. |

**Model labels are NOT raw API model IDs.** Valid labels are the ZTARE aliases enumerated above. `gemini-2.5-pro-preview-*` or similar raw IDs WILL fail the argparse `choices=` check.

---

## 9. Synthesis / reporting

| Field | Type | Notes |
|---|---|---|
| `synthesis_renderer` | string | Which synth renderer to use (`founder_memo`, `policy_essay`, etc.). See `src/ztare/synthesis/`. |
| `reviewer_domains` | list of strings | GP-079 domain lenses to inject into the skeptic persona. Read by findings runner; NOT by autoresearch_loop. |

---

## 10. Dynamic / committee rubrics

`make committee PROJECT=<slug>` writes `rubrics/dynamic_<slug>.json` — a multi-persona verification-panel rubric with a `committee` list instead of a single `persona`. Structure:

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

---

## 11. Worked examples

### 11a. Minimum qualitative-thesis rubric

```json
{
  "fit_score_mode": "none",
  "disable_evidence_fit_gate": true,
  "disable_evidence_fit_gate_reason": "qualitative thesis — text evidence, no numeric curve",
  "disable_uniqueness_gap_gate": true,
  "disable_uniqueness_gap_gate_reason": "rival mechanisms scored by rubric criteria, not keyword heuristic",
  "holdout_hard_gate": false,
  "enable_fit_primitive": false,
  "falsification_mode": "bounded_discriminator",
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

1. **Flavor declared explicitly** in a top-of-file comment or the `notes` field.
2. **No invented field names.** Every field appears in this spec OR in `grep rubric_data.get src/ztare/validator/autoresearch_loop.py`.
3. **`fit_score_mode` value is valid** — one of `{continuous_l2, continuous_rmse, discrete_exact, none}`.
4. **Every `disable_*_gate: true` has its paired `_reason` string.**
5. **If `holdout_hard_gate: true`**, both `gate_harness.py` and `evidence_holdout.txt` exist in the project.
6. **Model labels are ZTARE aliases**, not raw API IDs.
7. **`persona` is ≥3 sentences**, domain-anchored, names specific failure patterns it penalizes.
8. **`dimensions[].weight` sums to 100** (if dimensions are used).
9. **`criteria` names match `dimensions.name`** when both are present (no orphan criteria).

Run `python -m json.tool rubrics/<slug>.json` to verify JSON validity. Beyond that, there is currently no automated spec-conformance checker — this is an open gap (candidate for a `make rubric-lint` target).

---

## 13. Common mistakes this spec exists to prevent

| Mistake | Symptom | Fix |
|---|---|---|
| `fit_score_mode: "rubric_only"` (invented value) | `global_evidence_fit` + `global_extrapolation_gap` hard-fail, score zeroed | Use `"none"` + `disable_evidence_fit_gate: true` + reason. |
| `discrete_exact` without `fit_expression_grammar: "py_exec"` on algorithmic substrate | Mutator proposes list-comprehension or loop expressions; all fail `expression_validation_error`; score stuck at 0 forever | Add `"fit_expression_grammar": "py_exec"` to rubric. The default grammar only allows `arithmetic + math.*`. |
| Qualitative rubric without `disable_evidence_fit_gate: true` | Same as above — global gates run against stub `test_model.py`. | Add the disable flag + reason. |
| `holdout_hard_gate: true` without `gate_harness.py` | `make experiment-loop` aborts with "harness missing". | Generate the harness first; or set `holdout_hard_gate: false`. |
| Model label typed as raw API ID | argparse `choices=` rejects | Use ZTARE alias. |
| Using `make loop` when rubric has hard-gate | UNDERIDENTIFIED kills the run at iter 3 | Use `make experiment-loop` which auto-sets `--underidentified_after`. |
| Writing rubric by hand instead of `make generate-gp` | Structural omissions like missing `dimensions` or unpaired reason strings | Use `make generate-gp PROJECT=<slug> BRIEF="..."`. |

---

## 14. Historical context

- **GP-054** (Rubric Quality and Generation Spec) governs how rubrics are generated and reviewed — ties to `make rubric-review`.
- **GP-075** (Rubric Generation for Unknown Domains) governs taxonomy of GT-independent vs GT-dependent criteria in discovery mode.
- **GP-104 / `make generate-gp`** is the standard tool for fresh qualitative scaffolding; it produces Type-B rubric scaffolds that comply with this spec.

---

## 15. Change log

- **2026-04-23:** Initial version of this specification document. Filed after a hand-rolled rubric with `fit_score_mode: "rubric_only"` caused score-zero hard-fails on the ztare_on_ztare project. Triggering incident: the failure mode table in §13 is a direct post-mortem. (Author: claude_manager.)
- **2026-04-23 (later):** GP-133 Round 4 additions — §§ 16–20 below. Rubric-loader in `autoresearch_loop.py` enforces `py_exec` gates + `rubric_mode` discipline fail-closed. Architectural map updated with new region `rubric_preflight` and new exit `GP133_R4_gate`.

---

## 16. `rubric_mode` top-level field (GP-133 Round 4)

Every rubric SHOULD declare its epistemic mode. Enforced by the rubric-preflight gate in `autoresearch_loop.py`:

| Value | Meaning | Gate behavior |
|---|---|---|
| `"newton"` | Discovery-class. The `dimensions` list MUST include a dimension whose name contains `"Generative Yield"` (case-insensitive) with weight ≥15. | **Fail-closed:** autoresearch loop refuses to launch if the Generative Yield dimension is missing or under-weighted. |
| `"kepler"` | Descriptive-fit. No Generative Yield requirement. | Passes gate unconditionally. Outputs labeled Kepler-class descriptive findings. |
| `"calibration"` | Apparatus-shakedown. Discovery claims suppressed. | Passes gate unconditionally. Outputs labeled calibration-class. |
| unknown value | — | **Fail-closed:** refuses to launch. |
| absent | legacy unspecified | Passes gate (no warning emitted in current implementation; legacy rubrics continue to work). |

`make generate-gp` emits `rubric_mode: "kepler"` by default. Promotion to `rubric_mode: "newton"` requires principal signoff and rubric updates to include Generative Yield.

---

## 17. `fit_expression_grammar: "py_exec"` — gates + discipline (GP-133 Round 4)

When a rubric sets `fit_expression_grammar: "py_exec"`, two additional fields are **required**. Enforced by the rubric-preflight gate:

| Field | Type | Enforcement |
|---|---|---|
| `py_exec_authorized_by` | non-empty string | **Required.** Seam ID (e.g. `"GP-133-Round-4"`) or principal signoff string. Provenance for why this substrate qualifies for py_exec grammar. Missing/empty → fail-closed. |
| `expression_byte_budget` | positive int, default 200 | If missing, emits warning and defaults to 200. If present but non-positive-int, fail-closed. Anti-lookup-table defense — ternary-chain lookups pass parsimony but explode on byte length. |

**py_exec is never a default** in `make generate-gp` or any scaffolding tool. Explicit operator action only.

---

## 18. Generative Yield dimension (required for Newton-mode rubrics)

When `rubric_mode: "newton"`, the rubric's `dimensions` list MUST include a dimension whose name contains `"Generative Yield"` with weight ≥ 15% (recommended 20%). Enforced at rubric-preflight.

Scoring rubric for the dimension should distinguish:

- **0 points:** primitive predicts only the primary fitting target (Kepler-class naked fit).
- **Partial (~50%):** primitive names a secondary observable but no evaluation method.
- **Full:** primitive names a distinct mathematically-orthogonal secondary observable AND pre-commits to measurement method + expected value/range.

Trivial restatements of the fitting target score 0, not partial credit.

**Matching charter requirement:** project charters targeted by Newton-mode rubrics MUST require each primitive to include a `**Secondary observable**` field in the thesis format. Charter and rubric move in lock-step.

---

## 19. F-row extensions for discovery-class labeling (GP-133 Round 4)

F-rows in the experiment track record carry two new fields when the run's rubric has `rubric_mode: "newton"` OR `fit_expression_grammar: "py_exec"`:

| Field | Values | Notes |
|---|---|---|
| `discovery_class` | `recognition` \| `synthesis` \| `synthesis_incompressible` \| `derivation` \| `calibration` | Auto-classifier: `src/ztare/findings/discovery_class_classifier.py`. Default on py_exec + known-OEIS runs: `recognition`. |
| `predicted_secondary_observables` | list of `{observable, method, expected}` triples (may be empty) | Empty ⇒ Kepler-class descriptive finding. Non-empty with verified predictions ⇒ Newton-class generative finding. |

Staleness check: F-rows with missing `discovery_class` in Newton-mode or py_exec-mode runs are flagged stale. Any paper or patent citing `discovery_class: recognition` as "discovery" triggers a reviewer flag.

---

## 20. PR checklist — governance for new grammar / mode additions (GP-133 Round 4)

Any pull request that:

1. adds a new `fit_expression_grammar` value (e.g. introduces `lean_tactic`, `coq_expr`, `smt_z3`, future); OR
2. promotes a project from `rubric_mode: kepler` → `rubric_mode: newton` with external-citation intent; OR
3. changes default behavior of `make generate-gp` around rubric_mode or fit_expression_grammar;

must satisfy ALL of:

- **Panel review entry** appended to `research_areas/private/seams/mission/GP-133_multidisciplinary_discovery_panel_seam.md` (or successor discovery-panel seam) covering: epistemic framing, anti-gaming defenses, scope containment, governance implications.
- **Rubric-spec doc update** (this file) with the new mode/grammar documented in the appropriate section.
- **Rubric-loader gate update** in `autoresearch_loop.py` enforcing any required-field discipline for the new grammar or mode.
- **Architectural-map update** in `docs/internal/autoresearch_loop_architectural_map.md` if the gate changes region structure or exit taxonomy.
- **Principal signoff** in the PR description for any default-behavior change.

Retroactive: GP-133 Round 4 itself is the first application of this checklist. Future PRs follow the checklist prospectively.

---

## 21. Cage authoritative + reflexive-primitive flags (GP-157 / GP-167–GP-170, 2026-04-26)

The 2026-04-26 wave promoted the Cage Orchestrator from observe-mode to authoritative across substrates and added six apparatus-general flags. Loader gates live in `src/ztare/orchestrator/state.py::resolve_cage_mode` and the per-flag dispatch sites listed below.

### 21.1 Cage mode flags

| Field | Values | Source of truth | Notes |
|---|---|---|---|
| `cage_observe_mode` | bool | `orchestrator/state.py::resolve_cage_mode` | Cage runs alongside, logs engagement matrix to `workspace/cage_engagement.jsonl`, does NOT enforce verdicts. |
| `cage_authoritative_mode` | bool | same | Cage verdicts are authoritative; gate failures decrement scores via `apply_verdict_to_eval`. **`cage_authoritative_mode=true` IMPLIES observe-mode behaviour** — when both flags are set, authoritative wins. |
| `cage_meta` | object | `orchestrator/state.py::build_cage_runtime` | Required keys: `class` (substrate-class predicate), `target_convention_homogeneity`, plus optional `algebraic_constraints`, `feature_dimensions`. Read by `can_handle` predicates on each Cage-routed gate. |

Per GP-157 §3a (binding rule): all gates from R10 onward MUST be Cage-routed (register via `register_<name>_gate(s)(cage)` from `state.py::build_cage_runtime`). Direct-wire gates in `autoresearch_loop.py` are frozen — no new direct-wire imports allowed.

### 21.2 Per-class farther-tail flags (R10 / R11)

| Field | Default | Read by |
|---|---|---|
| `enforce_per_class_farther_tail` | `false` | `gates/cross_class_extrapolation_gate.py::dispatch_r10_r11_from_harness_json` |
| `r11_excluded_classes` | `[]` | same — class labels listed here skip R11 hard-fail enforcement; R10 cross-class diagnostic still runs |
| `r11_excluded_classes_reason` | string | informational — surfaced in seam audits |

R10 (cross-class extrapolation diagnostic, POST_FIT) always runs when Cage is active and substrate has `cage_meta.class` set. R11 (per-class MRE ceiling, PRE_JUDGE) only enforces when `enforce_per_class_farther_tail=true`.

### 21.3 GP-168 Forced-REFRAME flags

| Field | Default | Read by |
|---|---|---|
| `enable_forced_reframe` | `true` | `briefing_providers/forced_reframe.py::ForcedReframeBriefingProvider.applies` |
| `gp168_stagnation_threshold` | `3` | `orchestrator/forced_reframe.py::detect_forced_reframe_trigger` |
| `gp168_ast_bucket_threshold` | `5` | same |
| `gp168_max_consecutive_fires` | `2` | same — caps reframe budget so the apparatus does not lock the mutator into perpetual reframe loops |

Forced-REFRAME injects mandatory disjoint-architecture alternatives parsed from `research_areas/private/seams/engine/GP-164_*.md` §Appendix (loader: `orchestrator/alien_math_seam_loader.py`); falls back to a hardcoded list of 3 framings (RG-flow / multifractal Legendre / modular q-expansion) if the seam file is unavailable.

### 21.4 GP-169 Cold-LLM Erdős seed flags (Phase 1: iter-0 baseline)

| Field | Default | Read by |
|---|---|---|
| `enable_cold_llm_erdos_seed` | `false` | `orchestrator/pre_iter1_dispatch.py::dispatch_pre_iter1_cage` (iter-0 baseline) + `briefing_providers/cold_llm_seed.py::ColdLlmSeedBriefingProvider.applies` (per-iter render) |
| `cold_llm_seed_model_id` | **OPTIONAL** — defaults to the runtime mutator model when omitted or set to `"@mutator"` | same. Default behavior (since 2026-04-26): use whatever `MUTATOR_MODEL_ID` resolved to at run start. Set to a literal model id (e.g. `"claude-opus-4-6"`) only when the operator wants strict cross-family hygiene; the default trades cross-family for cost. The fallback flows through `pre_iter1_dispatch.dispatch_pre_iter1_cage(..., mutator_model_id=...)` and `cold_llm_seed_requery.maybe_requery_cold_seed(..., mutator_model_id=...)`. |
| `cold_llm_seed_forbidden_domain` | `null` | same. Free-form string injected into the cold-LLM prompt as a forbidden-domain clause; e.g. `"astrophysics"` for gp163d, `"machine learning, deep learning, neural-network scaling, AI"` for gp154. |
| `cold_llm_seed_k_law_budget` | `7` | same — max K per candidate form |
| `cold_llm_seed_timeout_seconds` | `30` | same — hard wall-clock budget; on timeout the seed mechanism degrades cleanly (iter-1 proceeds without the cold seed) |

### 21.5 GP-169 Phase 2 — Erdős re-query on stagnation (2026-04-26)

When stagnation triggers fire, the cold LLM is re-queried with the **current** residual fingerprint (computed from `noise_profile_post_fit_iter_*.json` + latest `analogy_log.jsonl` + `substrate_critique.json`). The refreshed candidates replace the iter-0 seed in the briefing via the same provider channel. Idempotent within a stagnation event (signature-cached); capped per run.

| Field | Default | Read by |
|---|---|---|
| `enable_erdos_requery_on_stagnation` | `true` (when cold-seed enabled) | `orchestrator/cold_llm_seed_requery.py::maybe_requery_cold_seed` |
| `erdos_requery_stagnation_threshold` | `2` | `cold_llm_seed_requery.py::detect_stagnation` |
| `erdos_requery_ast_bucket_threshold` | `3` | same |
| `erdos_requery_max_per_run` | `3` | `maybe_requery_cold_seed` |

The refreshed-seed banner in the mutator briefing (`🔎 GP-169 — REFRESHED (iter N, MANDATORY CONSIDER)`) signals the second cold draw. Iter-0 baseline is preserved on disk as `cold_llm_seed_iter0.json`; refreshes write `cold_llm_seed_requery_iter_NNN.json`.

### 21.6 Substrate-class + framer flags (read by new gates)

These are not new in this wave but are now read by R10/R11/R13–R16 and so must be set when adopting Cage authoritative mode:

| Field | Notes |
|---|---|
| `substrate_class_key` | feature key whose values define the substrate's class taxonomy (e.g. `"system_class"` for gp163d, `"study"` for gp154). R11 / SubstrateCritic / DataDiagnostics group residuals by this key. |
| `framer_primary_feature_key` | 1D projection axis for the active framer (e.g. `"radius_log10"` / `"N_log10"`). Required when `enable_framer=true`. |
| `enable_analogy` | bool — fires the L1 ANALOGY mechanism (cross-domain candidate forms triggered by residual fingerprint) |
| `enable_framer` | bool — fires the v2.0 active-framer (Box-Cox / log / no-transform via raw-coord BIC) |

### 21.7 Numeric-redaction in DataDiagnostics briefing (Task #140)

`briefing_providers/data_diagnostics.py` buckets all leakable numerics surfaced to the mutator:

- Row-fraction phrases (`X/Y rows`) → `"nearly all rows" / "majority of rows" / "minority" / "few rows"`
- Bare floats → `<small_value> / <value> / <large_value>`
- Regime-break magnitudes → bucketed; exact `split_at_x` held by gate harness, not surfaced
- `feature_dimensionality_collapses.relative_range` → bucketed (`"essentially constant (< 0.1%)"`, ...)

Numerics remain in `workspace/substrate_critique.json` for operator audit; only the briefing-rendered text is redacted. No rubric flag — unconditional protection against RH-13 / RH-18 mutator-side numeric memorization.

### 21.8 GP-170 Symbolic Logic Cage (R12)

R12 runs as a Cage-routed PRE_FIT gate that reduces `PARAMETRIC_FORM` via SymPy + AST-rewrite (`where()` → `Piecewise`, `sigmoid()` → closed form) and checks declared `cage_meta.algebraic_constraints` before the fit primitive sees the form. No additional rubric flag — engagement is gated by `cage_meta.algebraic_constraints` being a non-empty list.

### 21.8a Constant-laundering score cap (Gemini-Pro panel, 2026-04-26)

When the structural anti-pattern gates (R20 / R21 / R24) detect a form embedding hardcoded literals as hidden degrees of freedom, the apparatus deterministically caps the score below the Newton-step threshold. The judge does NOT perform AST analysis — LLMs are blind to AST topology and get talked out of it by mutator prose; the cap is enforced in `orchestrator/post_harness_dispatch.py::apply_verdict_to_eval` before the eval is finalized.

| Field | Default | Read by |
|---|---|---|
| `cage_constant_laundering_score_cap` | `50` | `post_harness_dispatch.py::dispatch_post_harness_cage` |
| `effective_parameter_count_slack` | `0` | `gates/structural_anti_pattern_gates.py::estimate_effective_parameter_count` (R21) — declared K must match effective K. Set higher only if the substrate has legitimate physical constants the mutator should be allowed to hardcode. |
| `enable_withheld_value_leakage_gate` | `true` | R20 |
| `enable_effective_parameter_count_gate` | `true` | R21 |
| `enable_apparatus_meta_runner_gate` | `true` | R22 (now consumes R20/R21/R24 verdicts + regex catalog for RH-13/RH-17) |
| `enable_feature_bump_pattern_gate` | `true` | R24 (NEW 2026-04-26) — AST-walk for `(feature - C)` / `(feature / C)` patterns |
| `withheld_value_leakage_monitored_keys` | `[]` (auto-includes all features referenced in PARAMETRIC_FORM) | R20 / R24 |

R20/R21/R24 verdicts feed R22 — the meta-runner translates structural detections into RH codes (RH-18, RH-18-ANCHOR, RH-EFFK-LAUNDER) for human-readable judge feedback. R22 retains a regex catalog only for orthogonal patterns the structural detectors don't cover (RH-13 categorical-as-continuous, RH-17 explicit lookup table).

### 21.8b Relationship to v4-era anti-gaming gates (GP-086)

The v4-era hardening pillars (`circularity_gate`, `falsifiability_gate`, `derived_constraints`, `structural_constraint_extractor`, `negative_space_extractor`, `bridge_scope_contract`, `domain_match_gate`, `asymptotic_claim_discipline`) detect **thesis-structural** properties: does the form have rivals, do parameters exceed evidence count, does the falsification suite exist, etc.

R20/R21/R24 detect **literal-structural** properties: do hardcoded numbers in the form coincide with substrate statistics, does declared K match effective K, does the form embed feature-relative bumps. These are orthogonal to the v4 pillars — both layers can co-fire on a single form, and neither replaces the other. R22 was always regex-based for RH-13/17/18; the 2026-04-26 refactor moved RH-18 detection to R24's AST walk so the iter-4 sigmoid-window escalation (which the regex missed) gets caught.

`v4_meta_runner.py` (stage-gating for hardening projects) is unrelated to R22 (apparatus-meta-runner): the former gates project promotions; the latter labels gaming patterns. Don't conflate.

### 21.8c META-GATE 2C — Post-run LLM diagnostic auditor (2026-04-26)

Post-run hook that calls a cross-family LLM to read the run's trace
(`eval_history.jsonl + cage_engagement.jsonl + substrate_critique.json
+ iteration_telemetry.jsonl`) and identify what apparatus-side detection
would have moved the needle when the run capped below the Newton-step
threshold. Default OFF — opt-in for production runs. The audit is a
PROPOSAL; the operator decides whether to act.

| Field | Default | Read by |
|---|---|---|
| `enable_post_run_meta_audit` | `false` | `validator/autoresearch_loop.py` (post-loop hook) → `orchestrator/post_run_meta_audit.py::run_post_run_meta_audit` |
| `meta_audit_model_id` | `claude-haiku-4-5` | same. Cross-family from mutator AND judge by convention. Override only when the operator wants to swap audit models. |

Cost contract: hard 30s wall-clock, ~5K input tokens, ~2K output tokens
per audit. On failure: log + continue. Writes
`workspace/post_run_meta_audit.{json,md}`.

Retroactive use: `make audit-run-meta PROJECT=<name>` runs the auditor
against an already-completed project's workspace without touching the
main loop.

### 21.8d META-GATE 2 — G-EVIDENCE-GAP-ENRICHMENT (EGE) (2026-04-26)

Pre-iter-1 trigger that fires when R26
(`withheld_class_feature_collapses` non-empty in
`substrate_critique.json`) reports a within-withheld-class data
ceiling. For each `(class, feature)` collapse, an LLM proposes
literature sources that publish per-system values of the collapsed
feature for the class's system_ids. The output is a list of
PROPOSALS; the operator reviews and (separately) decides whether to
run `make enrich-substrate`. EGE never auto-edits substrates.

| Field | Default | Read by |
|---|---|---|
| `enable_evidence_gap_enrichment_proposals` | `false` | `validator/autoresearch_loop.py` (post pre-iter-1 hook) → `orchestrator/evidence_gap_enrichment.py::propose_evidence_gap_enrichment` |
| `evidence_gap_model_id` | `@mutator` | same. The `@mutator` sentinel resolves to the runtime mutator model. Set to a literal model id (e.g. `claude-opus-4-6`) for cross-family hygiene — operators with WebSearch-capable model runtimes prefer Anthropic claude-opus or claude-sonnet here. |

Cost contract: hard 60s wall-clock per gap, ~3K input tokens, ~3K
output tokens. On failure: log + continue. Writes
`workspace/evidence_gap_enrichment_proposals.json`.

This is the apparatus-side trigger of the Karpathy RAM-loop pattern:
ZTARE stays ALU; EGE flags when the bottleneck is RAM (the substrate
is missing data the apparatus cannot synthesize). The OPERATOR-side
decision (do these proposals fit? does the substrate enrichment
generalize?) stays human.

### 21.9 Compatibility with older substrates

Substrates that pre-date this wave (no `cage_meta`, no per-class flags, no cold-seed) continue to run unchanged: the loader returns `mode="off"` from `resolve_cage_mode` when neither `cage_observe_mode` nor `cage_authoritative_mode` is set, all GP-168 / GP-169 hooks check their `enable_*` flags before firing, and the DataDiagnostics provider applies redaction unconditionally (a strict win — never leaks more than before).
