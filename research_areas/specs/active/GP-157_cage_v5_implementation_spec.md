---
id: GP-157
status: active
summary: v5.0 implementation spec; Phase 1-3b shipped, Phase 3c-6 in flight
---

# GP-157 — Cage Orchestrator v5.0 Implementation Spec

**Status**: READY-FOR-IMPLEMENTATION (consolidated from gp158 audit champion 77 + lower-score nuggets + 2026-04-25 evening empirical findings)
**Date**: 2026-04-25 night
**Supersedes**: `GP-157_cage_orchestrator_substrate_agnostic_dispatch.md` seam (still authoritative for design rationale; this doc is the implementation contract)

## 1. Authority and dependencies

This spec consolidates findings from:
- gp158 champion thesis (score 77, iter 8) — 6 concrete defects with file:line citations
- gp158 lower-scored theses — 5 nugget defects the champion missed
- 11 reflexive-primitive rules R1-R9 + R5/R6/R7 panel-coverage rules
- gp154 empirical findings on substrate underdetermination + target heterogeneity
- 2026-04-25 day-and-evening 32-bug taxonomy (classes A through K)

## 2. Defect catalog the implementation MUST close

### From gp158 champion thesis (score 77)

**D1 — Reachability gap in dispatcher** (Class A, Bug #11 reincarnation)
```
def can_handle(substrate, gate):
    s_cls = substrate.meta["kind"]   # HARD lookup
    g_need = GATE_REQUIREMENTS[gate.name]
    ...
    # except KeyError: return False  ← silent skip
```
Audit substrates emit `meta["type"]`, not `meta["kind"]`. KeyError is rescued; dispatcher silently skips engagement. **Fix**: `can_handle` MUST raise on missing canonical metadata, not return False. Loud-fail over silent-skip.

**D2 — Hidden coupling in FitEngine.Protocol** (Class F + Bug #26 resurfaces)
Time-series substrates pass tensor-valued targets `y.shape == (N, T)` with inter-row covariance. Unified Protocol returns scalar residual per row → silently discards cross-time covariance → optimizer satisfies BIC with single huge coefficient on uncorrelated dimension (gp154 |param|=128 pattern). **Fix**: FitEngine Protocol must accept tensor targets and return per-row OR per-(row, time) residuals.

**D3 — Magic-number back-slide in `evaluate_set`** (Class E)
`near_miss_factor=1.5` as positional default. gp146 needs ~2.2. Per-project harnesses will re-introduce overrides → copy-paste divergence the consolidation was supposed to kill. **Fix**: canonical schema MUST include `near_miss_factor` as a per-substrate metadata field; `evaluate_set` reads from substrate.meta, never from positional default.

**D4 — Overfitting carry-over (3 instances)** (Classes B, E, A)
- (a) Bug #16 silent-crash → `assert_or_propagate_defect` still maps any exception to `rel_err = 1.0`. **Fix**: distinguish `RuntimeError` (defect) from `AssertionError` (falsification).
- (b) Bug #18 zero-signal near-miss → returns only `passed/near_miss` bool, discards distance value if `passed==False`. **Fix**: always return `(value, threshold)` pair so mutator gets gradient signal.
- (c) Bug #21 schema divergence → legacy `farther_tail` parser still in `test_thesis.py`. **Fix**: single canonical schema, deprecate legacy reader after migration.

**D5 — Adversarial bypass of `can_handle` yielding 100% crash** (Class B + Bug #16 survival)
Submit `PARAMETRIC_FORM = "params['θ'] * features['nonexistent']"` on gp155. should_engage token-scans successfully (only AST Call/Name validation). Runtime KeyError per row → caught, mapped to rel_err=1.0, gate records "model fit poorly", not "crashed 100%". **Fix**: pre-engage data-adequacy check (R8) — every feature key the form references MUST exist in features.py with ≥30% row coverage.

**D6 — Compositional deadlock with holdout-hard-gate** (Class A reachability + G-CIRC conflict)
Cage schedules FIT_POST gates concurrently. holdout-hard-gate depends on Framer's `FeatureFitResult` JSON. If alphabetical order: G-CIRC < holdout, holdout opens JSON before Framer creates it → FileNotFoundError → silent deadlock. **Fix**: explicit dependency graph (DAG), not alphabetical concurrent execution. Topological sort before dispatch.

### Nuggets from lower-scored theses (judge-WPs as forensic data)

**N1 — Race condition in holdout-hard-gate** (iter 2, score 24)
Even if D6's DAG is implemented, FileNotFoundError can race during transient FS sync. **Fix**: holdout-hard-gate MUST use atomic file-write protocol (write to `.tmp`, then `os.rename`). No `while not path.exists(): sleep()` — that's a Class B silent-deadlock pattern.

**N2 — Dispatcher ordering non-determinism** (iter 3, score 25)
`ThreadPoolExecutor.map(sorted(gates))` is non-deterministic without explicit dependency graph. v5.0 MUST ship with the DAG, not promise to add it. **Fix**: declare `gate.dependencies: list[GateName]` field; topological sort at dispatch.

**N3 — `substrate.meta` __getitem__ override** (iter 8, score 72)
If `meta` is a custom dict subclass, `.meta["kind"]` lookup behavior changes. **Fix**: v5.0 Protocol asserts `isinstance(substrate.meta, dict) and not isinstance(substrate.meta, ChainMap | UserDict | ...)` — plain dict only. Constrain at substrate-load time.

**N4 — `min_rows_per_category` substrate metadata** (iter 12, score 74) — strongest nugget
Substrate must declare its data-adequacy assumptions in metadata. **Fix**: required substrate-meta field `min_rows_per_category: int` (default 3); Cage's data-adequacy check (R8) reads this, refuses engagement if any categorical feature value count < min.

**N5 — Frozen-spec premise** (iter 13, score 68) — META-finding
Every defect can be patched away by minor implementation choices during coding. The audit is only valid if the spec ships AS WRITTEN. **Fix**: v5.0 implementation must declare each defect as either `MUST_FIX_NOW` or `MAY_FIX_DURING_IMPL`. The defect catalog above declares D1-D6 as MUST_FIX_NOW.

## 3. Reflexive primitive rules (R1-R9) the implementation MUST satisfy

| Rule | Constraint |
|---|---|
| **R1** | Cited line ranges still match the code at ship time (verifier: `validate_autoresearch_arch_map.py`) |
| **R2** | Proposed Protocol covers all current call sites; no breaking caller without migration sketch |
| **R3** | Schema unification has bidirectional migration path (legacy parser handles both shapes during migration window) |
| **R4** | `can_handle` correctly routes ≥2 of {gp154, gp155, gp156, gp146, gp077} substrates |
| **R5** | Every Cage Protocol method tested against ≥1 substrate from EACH class (1D, N-D, time-series, audit, literature) |
| **R6** | Every integration point has a real-file smoke test exercising dict iteration, categorical strings, missing-key paths, Unicode, multi-line, empty-dict |
| **R7** | Every panel transcript includes a Software-Integration-Engineer turn that pressure-tests AST/dict/Unicode/exception classes |
| **R8** | `can_handle` runs feature-coverage adequacy check: required form-features must have ≥30% row coverage in visible |
| **R9** | `can_handle` runs target-convention homogeneity check: substrate.meta declares `target_convention_homogeneity ∈ {homogeneous, heterogeneous}`; if heterogeneous, PARAMETRIC_FORM must reference `features['fit_convention']` |
| **R10** | POST_FIT phase runs cross-class extrapolation diagnostic: per-class MRE on held-out classes, Spearman correlation between per-row error and primary feature within each held-out class, in-feature-range vs out-of-feature-range subset MRE. Flags `magnitude_coincidence` when in-range MRE > out-of-range MRE on a held-out class. Flags `kernel_camouflage_rh18_candidate` when per-class Spearman ≈ 0 AND per-class MRE is good (signature of hardcoded constant fitting a class). Non-blocking diagnostic; surfaces to next-iter mutator briefing. (Mechanizes the manual backtest workflow that distinguished gp163d iter-3 real-radius-bridge from iter-5 RH-18 kernel-camouflage. Implementation: `src/ztare/gates/cross_class_extrapolation_gate.py::run_cross_class_diagnostic`.) |
| **R11** | PRE_JUDGE phase runs per-class farther-tail MRE ceiling: each held-out class must independently satisfy `MRE < threshold` (default `farther_tail_threshold` from rubric, optional per-class override via `rubric.per_class_thresholds`). Replaces aggregated farther-tail MRE which lets a populous class average out a sparse class's blowup. Hard-fails the iter when any held-out class exceeds its ceiling. Optional `excluded_classes` set (e.g. classes with known data artifacts surfaced by SubstrateCritic) skipped. Implementation: `src/ztare/gates/cross_class_extrapolation_gate.py::per_class_mre_ceiling`. |
| **R12** | PRE_FIT phase runs symbolic logic cage (GP-170): parses PARAMETRIC_FORM via SymPy after AST-rewrite of apparatus primitives (`where`/`sigmoid` to SymPy `Piecewise` / closed-form), declares symbols with INIT_RANGE-driven assumptions, and proves UNSAT/SAT/indeterminate against `cage_meta.algebraic_constraints` (provenance-required). Rejects forms whose algebraic structure provably violates substrate axioms before scipy fits. Includes regex pre-parser (fail-closed on Python control-flow keywords), trivial-wrapping detector (rejects `y = exp(constant)` against `y > 0` etc.), 15s wall-clock budget, data-belief reconciliation (refuses to engage if visible data violates declared constraint by >5%), `can_handle` carve-out for `py_exec` substrates, R1 templates distinguishing fundamental-violation from cross-domain-seed-needs-dimensional-bridging. Implementation: `src/ztare/gates/symbolic_logic_cage.py`. Phase 2 (Buckingham π dimensional consistency) deferred until GP-169 wired; Phase 3 (canonical-form dedup) and Phase 4 (symbolic limits) deferred per seam contract. |
| **R13** | PRE_FIT (preflight) + POST_FIT (per-iter refresh) — `substrate_critic`: deterministic probes that surface what the substrate's data shows, doesn't show, and cannot constrain. Pre-flight runs ONCE before iter 1 with `critique_substrate(visible, farther_tail, primary_feature_key, class_key, expected_y_over_x)`; per-iter refresh runs after each fit with `refresh_critique_post_fit` and appends post_fit_iter_N voids to `epistemic_voids` without overwriting pre-flight structural facts. Outputs: `workspace/substrate_critique.json` + `workspace/substrate_critique_suggestions.json`. `can_handle` engages when `cage_meta.class ∈ {nd_features, time_series}` and rubric does NOT set `disable_substrate_critic: true`. Per GP-157 §3a, this is the canonical opt-OUT pattern (default ON for matching substrate classes). Adapter: `src/ztare/diagnostics/substrate_critic.py::register_r13_gate`. Backport from direct-wire 2026-04-26. |
| **R14** | PRE_FIT (preflight) + POST_FIT (residual classifier) — `noise_profile`: four meta-diagnostics (Breusch-Pagan heteroscedasticity, Shapiro-Wilk / Jarque-Bera + skew/kurtosis non-Gaussian, Durbin-Watson autocorrelation, errors-in-X via explicit `sigma_x_*` keys). Pre-flight classifies the substrate's residuals from a baseline polyfit; auto-routes solver flags (`fit_weighted_residuals`, `fit_robust_loss="huber"`, `fit_correlated_errors`, `fit_use_odr`) into the rubric — operator-set flags always win (auto-route only fills absent keys). Per-iter post-fit re-classifies residuals from the actual fitted form. Outputs: `workspace/noise_profile.json` (rolling) + `workspace/noise_profile_post_fit_iter_N.json` (per-iter). `can_handle` engages when `cage_meta.class ∈ {nd_features, time_series, 1d_curve, 1d}` and rubric does NOT set `disable_noise_profile: true`. Adapter: `src/ztare/diagnostics/noise_profile.py::register_r14_gate`. Backport 2026-04-26. |
| **R15** | POST_FIT — `ANALOGY` (GP-164 L1): structurally-anonymized residual fingerprint queries a frontier LLM for cross-domain candidate forms when the operator-curated grammar exhausts. `can_handle` engages when `rubric.enable_analogy=true` AND `should_engage(rubric, fit_result_json, stagnation_count)` returns True (default thresholds: `stagnation_count ≥ analogy_min_stagnation=3` OR `pathological=true` on the prior fit). Default model is the iter's MUTATOR (`rubric.analogy_model_id` overrides). OBSERVE-mode by default (`enable_analogy_active=false`); active mode injects candidates into the next iter's mutator briefing. Output: `workspace/analogy_log.jsonl` (append-only audit). Adapter: `src/ztare/fit/analogy.py::register_r15_gate`. Backport 2026-04-26. |
| **R16** | PRE_FIT — `framer` (GP-152 v2.0, 1D path): runs `frame()` on the parsed (xdata, ydata) before fit primitive engagement; symmetry scan + transformation enumeration + branch-and-bound MDL search picks `(h_in, h_out)`. Ships in OBSERVE mode (data-flow into fit_parameters unchanged; chosen frame logged for telemetry). `can_handle` engages when `rubric.enable_framer=true` AND `cage_meta.class ∈ {nd_features, 1d, 1d_curve}` AND a 1D `fit_decl` is declared AND parsed (x, y) length ≥ 80 (framer's MIN_N precondition). Output: `workspace/framing_report.json`. Adapter: `src/ztare/framer/active_framer.py::register_r16_gate`. Backport 2026-04-26. **Deferred**: the N-D framer invocation that fires after `fit_primitive_features` writes `fit_features_result.json` is conceptually POST_FIT despite being framer-shaped, and its inputs depend on the per-iter `_vis` context loaded inside the fit primitive. Tracked as follow-up — migrating it requires the POST_FIT dispatcher to pass `_vis` and rubric-mirror context through the candidate object. |

### R10 + R11 dispatch architecture (Cage-routed, NOT autoresearch_loop-wired)

**R10 and R11 ship as Cage-registered gates with `can_handle` predicates. They do NOT receive direct autoresearch_loop wire-in.** This is the v5.0 design intent that R8 and R9 already follow. Every gate added after R9 — substrate_critic, noise_profile, ANALOGY, framer — bypassed this pattern and got wired directly into `autoresearch_loop.py`. That was a registry leak. New gates from R10 onward MUST follow the Cage-routed pattern. Existing direct-wired gates are tracked for backport in §8.6 (added below).

**`can_handle` predicates:**
- **R10** returns engaged when `substrate.cage_meta.class in {nd_features, time_series}` AND `farther_tail` non-empty AND `framer_primary_feature_key` is declared in rubric AND `substrate_class_key` is declared. Returns refused with diagnostic otherwise.
- **R11** returns engaged when R10 conditions are met AND `enforce_per_class_farther_tail: true` in rubric. The rubric flag is the OPT-IN switch (default `false` until R11 has been validated on ≥3 substrates).

**Phase routing:**
- R10 runs in POST_FIT, after fit_primitive_features but before judge.
- R11 runs in PRE_JUDGE, replacing the combined-class farther-tail evaluation when engaged.
- Both write JSON outputs to `workspace/`. Briefing providers (see §8.5 below) read those JSONs and surface findings to the next iter's mutator prompt. **The wire-in to autoresearch_loop is a single `cage.run_phase("POST_FIT", ctx)` call, not a per-gate if-block.**

**Substrate.meta inputs both gates read:**
- `cage_meta.class` — partitioning rule (nd_features uses cardinal feature keys; 1d uses x/y).
- `framer_primary_feature_key` — which feature acts as the bridge.
- `substrate_class_key` — which categorical key partitions held-out rows into classes.
- `expected_y_over_x` — direction of the algebraic constraint (used to identify classes where data artifacts conflict with the form's constraint, e.g. gp163d Class C deprojection y/x<1 vs McGaugh y≥x).
- `r11_excluded_classes` — classes to skip in R11's per-class enforcement (artifact-poisoned classes surface as honest_null, not gate failures).

**Briefing surfacing (R10):**
- `workspace/cross_class_extrapolation_iter_<N>.json` is consumed by `data_diagnostics` briefing provider.
- Flags `magnitude_coincidence` and `kernel_camouflage_rh18_candidate` get rendered into the next iter's prose with the implication strings the gate emits.
- Without this surfacing, the gate runs without changing mutator behavior — the apparatus learns nothing. Briefing-surfacing is part of the gate ship requirement, not a follow-on task.

## 3a. Architectural rule: new gates ship Cage-routed only

**Effective from R10 onward**: every new gate MUST register with the Cage default gate list and ship with a `can_handle` predicate that reads `substrate.cage_meta` plus row-structure features (number of classes, feature numeric-vs-categorical, etc.). Direct autoresearch_loop wire-in is FORBIDDEN for new gates.

**Rubric flags for new gates are opt-out overrides, not opt-in switches.** Default behavior is determined by `can_handle` reading `cage_meta`. Rubric flag `disable_<gate>: true` lets the operator override an auto-engaged gate; `enable_<gate>: true` is reserved for gates that ship in observe-mode first and need explicit opt-in (e.g. R11 enforcement during validation period).

**Why:** the autoresearch_loop's per-gate if-block stack creates a coupling explosion. 30+ gates × per-rubric configuration × per-loop wiring = unmaintainable. The Cage abstracts this by giving each gate the responsibility to know its own applicability via `can_handle`. autoresearch_loop's job becomes: call `cage.run_phase("X", ctx)` once per phase, get back the engagement matrix, render its outputs to briefing.

**Backport plan for existing direct-wired gates** (status as of 2026-04-26):
- substrate_critic → **MIGRATED (R13)** — Cage-routed dual-phase (PRE_FIT preflight + POST_FIT refresh). Adapters in `src/ztare/diagnostics/substrate_critic.py`. Opt-out via `disable_substrate_critic`. Default ON for nd_features/time_series.
- noise_profile → **MIGRATED (R14)** — Cage-routed dual-phase (PRE_FIT preflight + POST_FIT residual classifier). Adapters in `src/ztare/diagnostics/noise_profile.py`. Opt-out via `disable_noise_profile`. Auto-routes solver flags (operator-set flags always win).
- ANALOGY → **MIGRATED (R15)** — Cage-routed POST_FIT. Adapter in `src/ztare/fit/analogy.py`. `can_handle` gates on `enable_analogy=true` + stagnation/pathology via `should_engage`. OBSERVE-mode default; active mode behind `enable_analogy_active`.
- framer → **PARTIALLY MIGRATED (R16)** — 1D PRE_FIT path Cage-routed (adapter in `src/ztare/framer/active_framer.py`). N-D framer invocation that fires after `fit_primitive_features` is DEFERRED to a follow-up (its inputs depend on per-iter `_vis` context loaded inside the fit primitive; conceptually POST_FIT despite being framer-shaped).
- pathology enforcement → already in fit primitive, but its rubric flag should be moved to cage_meta. (Unchanged.)

**Migration mechanics** (Task #151, 2026-04-26):
- Each gate's adapter (R{N}_can_handle + R{N}_run + register_R{N}_gate) ships at the bottom of its existing module — no new files required for the gate logic itself.
- `build_cage_runtime` in `orchestrator/state.py` calls `register_r13_gate / register_r14_gate / register_r15_gate / register_r16_gate` on the live Cage instance.
- New orchestrator entry points: `orchestrator/pre_fit_dispatch.py` (preflight + per-iter PRE_FIT) and `orchestrator/post_fit_dispatch.py` (POST_FIT). Each defines a single `dispatch_*_cage(...)` function that walks the Cage's gates by phase + name filter and runs engaged adapters.
- autoresearch_loop's three legacy if-blocks (preflight: 130 lines; 1D framer: 41 lines; post-fit triple: 200 lines + ANALOGY: 95 lines) are replaced with single-line dispatcher calls. Net: ~293 lines removed from the loop body.

**LOC reduction**: autoresearch_loop.py 7654 → 7361 (−293 lines, −3.8%). Each removed if-block had its own try/except wrapper, telemetry print statements, and conditional skip logic — all preserved semantically inside the per-adapter run() functions and the dispatcher's log_lines aggregation.

### R10 + R11 reading map (legacy direct-wire compatibility window)

During the validation window (until R10/R11 prove out on 3 substrates), both gates can also be invoked directly via the cage_routed_gate interface from `cross_class_extrapolation_gate.py` for testing. Production ships through Cage exclusively.

## 3b. Orchestrator-level companions to the Cage (Phase-4g hooks)

Not every apparatus contribution is a Cage gate. Two recent additions live at the **orchestrator** layer because they fire at moments outside the per-iter PRE_FIT/POST_FIT/PRE_JUDGE/POST_JUDGE phases, but they share the Phase-4g architectural rule (one entry-point per phase, no inline if-block accretion):

### GP-168 Forced REFRAME iter mechanism
- **Module**: `src/ztare/orchestrator/forced_reframe.py` (shipped, wire-in pending).
- **Phase**: pre-mutator-call inside the iter (after iter_history is read, before the mutator prompt is built).
- **Trigger**: stagnation_count ≥ N OR same PARAMETRIC_FORM AST-bucket for M consecutive iters.
- **Effect**: rewrites the iter's mutator prompt to BAN the current architectural family and present alien-math framings as mandatory alternatives. Enforced via adherence rule on the next submission.
- **Generalization**: AST-bucket detection works for any substrate's PARAMETRIC_FORM. Triggers configurable via rubric (`gp168_stagnation_threshold`, `gp168_ast_bucket_threshold`, `gp168_max_consecutive_fires`). Banned-family description is generated from the iter history, not hardcoded per-substrate.

### GP-169 Cold-LLM Erdős seed (Phase 1 wired 2026-04-27)
- **Modules**: `src/ztare/fit/cold_llm_erdos_seed.py` (cold-LLM call + validation), `src/ztare/orchestrator/pre_iter1_dispatch.py` (one-call orchestrator entry point), `src/ztare/orchestrator/briefing_providers/cold_llm_seed.py` (renders MANDATORY-CONSIDER into iter 1+ briefing).
- **Phase**: ONCE before iter 1, plus per-iter rendering of the persisted artifact into the mutator briefing.
- **Effect**: anonymized residual fingerprint sent to a cold LLM (separate from mutator + judge), with explicit forbidden-domain clause. Returns 3 cross-domain candidate forms that get injected as architectural seeds.
- **Generalization audit**: opt-in via rubric flag `enable_cold_llm_erdos_seed`. Forbidden domain declared per-rubric (e.g. gp163d → `astrophysics`, gp154 → `computer_science`, gp077 → `number_theory`). Fingerprint computation reads any substrate's `features.py::visible_rows` + `farther_tail_rows`. Quantization (panel Blindspot 1 fix) makes the fingerprint match many substrate templates rather than uniquely identifying one. Strict identifier whitelist (panel Blindspot 4 fix) rejects `numpy.exp` / `math.gamma` / `scipy.special.*` so seeds are SymPy-parseable for downstream R12 (cross-seam Collision-1 fix). 30s wall-clock budget with degraded-mode contract (fewer than 2 valid candidates → seed mechanism auto-disabled for that iter, telemetry event `cold_seed_degraded`). NO substrate-specific code paths — fully apparatus-general.

Both GP-168 and GP-169 are explicitly NOT Cage gates (they fire outside the per-iter Cage phases) but they follow the same architectural rule: ONE entry point in autoresearch_loop calling a single orchestrator function. New work at the same architectural level (e.g. Forced-REFRAME wire-in) extends the existing dispatcher rather than adding inline if-blocks.

## 3c. Generalization audit (rubric vs apparatus boundaries)

Rule: every gate, every orchestrator hook, every briefing provider must be substrate-agnostic in IMPLEMENTATION. Substrate-specific configuration is declared in the rubric, not hardcoded in the apparatus.

Audit table for the recent shipments:

| Component | Substrate-agnostic implementation? | Substrate-specific config keys |
|---|---|---|
| R8 feature-coverage | yes | (no rubric keys; uses cage_meta + form's referenced features) |
| R9 convention-homogeneity | yes | `cage_meta.target_convention_homogeneity` |
| R10 cross-class extrapolation | yes | `framer_primary_feature_key`, `substrate_class_key` |
| R11 per-class MRE ceiling | yes | `enforce_per_class_farther_tail`, `r11_excluded_classes`, `per_class_thresholds`, `farther_tail_threshold` |
| R12 symbolic logic cage | yes | `cage_meta.algebraic_constraints` (provenance-required), `cage_meta.feature_dimensions` (Phase 2) |
| R13 substrate_critic (preflight + post-fit) | yes | `disable_substrate_critic` (opt-out), `framer_primary_feature_key`, `substrate_class_key`, `substrate_expected_y_over_x` |
| R14 noise_profile (preflight + post-fit) | yes | `disable_noise_profile` (opt-out), `framer_primary_feature_key`; auto-route writes `fit_weighted_residuals`, `fit_robust_loss`, `fit_correlated_errors`, `fit_use_odr`, `framer_sigma_provided` only when absent |
| R15 ANALOGY | yes | `enable_analogy` (opt-in), `enable_analogy_active`, `analogy_min_stagnation`, `analogy_model_id`, `analogy_domain_hint`, `framer_primary_feature_key` |
| R16 framer (1D PRE_FIT) | yes | `enable_framer` (opt-in), `framer_meta`, `framer_sigma_provided`, `framer_fit_degree` |
| GP-168 Forced REFRAME | yes | `gp168_stagnation_threshold`, `gp168_ast_bucket_threshold`, `gp168_max_consecutive_fires` |
| GP-169 Cold-LLM Erdős seed | yes | `enable_cold_llm_erdos_seed`, `cold_llm_seed_model_id`, `cold_llm_seed_forbidden_domain`, `cold_llm_seed_k_law_budget`, `cold_llm_seed_timeout_seconds` |
| Cold-LLM seed briefing provider | yes | reads `cold_llm_seed_iter0.json`, no substrate-specific logic |

No substrate name or substrate-specific behavior is hardcoded in any of the apparatus modules. Substrates that don't declare the relevant rubric keys get a clean refusal-to-engage with telemetry (not a crash, not a silent skip). The "Erdős" name in GP-169 is the philosophical inspiration; the mechanism is "cold cross-domain LLM seed at iter 1" and applies to any substrate where the operator wants to seed iter 1 with non-home-discipline forms.

**Task #151 backport audit (2026-04-26):** R13/R14/R15/R16 adapters all read substrate routing via `getattr(substrate, "meta", {})` + `getattr(substrate, "rubric_flags", {})` exclusively. None reference substrate names, project IDs, or hardcoded class lists beyond the canonical `cage_meta.class` taxonomy. The backport-introduced rubric keys (`disable_substrate_critic`, `disable_noise_profile`) are opt-out switches that match the §3a architectural rule: rubric flags for new gates are opt-out overrides, not opt-in switches. R15/R16 retain `enable_*` opt-in semantics because (a) R15 incurs a per-iter LLM call with token cost, and (b) R16 framer ships in OBSERVE mode pending live-mode promotion (validated by spec §7 steps 6-10); both defaults stay OFF until validated on ≥3 substrates per the established §3a precedent for hard-fail / cost-incurring gates.

## 4. Implementation phasing

### Phase 1 — Substrate-evaluation utility extraction (LOW RISK, START HERE)

**File**: `src/ztare/gates/substrate_evaluation.py` (new)
**Exports**:
```python
@dataclass
class EvalResult:
    n: int
    mean_relative_error: float
    max_relative_error: float
    per_row: list[dict]
    crash_count: int
    crash_rate: float
    crash_classes: dict[str, int]
    passed: bool
    near_miss: bool
    threshold: float
    near_miss_factor: float

def evaluate_set(
    rows: list[tuple[int, float]],
    i_model: Callable,
    features_module,
    *,
    threshold: float,
    near_miss_factor: float = 1.5,  # D3-fix: read from substrate.meta when present
    crash_threshold: float = 0.5,
) -> EvalResult: ...

def assert_or_propagate_defect(
    result: EvalResult,
    gate_name: str,
    *,
    is_preflight: bool = False,
) -> None:
    """Raise RuntimeError if crash_rate ≥ crash_threshold (harness defect),
    else AssertionError with [near_miss]/[hard_miss] tag if not passed.
    Skipped under is_preflight."""
```

**Migration**:
- gp154 + gp155 gate_harness.py reduce to ~40 lines: parse evidence, call `evaluate_set` + `assert_or_propagate_defect`, print JSON.
- Per-substrate `near_miss_factor` read from substrate.meta (D3 fix).
- Canonical schema: `{harness_ok, gates: [{name, passed, near_miss, value, threshold, near_miss_factor}], all_gates_pass, any_near_miss}` — both legacy and GP-156-shape consumers can read.

**Deliverables**:
1. New module + 100% unit tests for `evaluate_set` + `assert_or_propagate_defect`
2. Refactor gp154/gp155 gate_harness.py to use the utility
3. Update `test_thesis.py:2335-2470` legacy parser to read canonical schema
4. Verify all existing substrates pass pre-flight unchanged

**Estimated**: 2-3 hours.

### Phase 2 — FitEngine Protocol consolidation (MEDIUM RISK)

**File**: `src/ztare/fit/fit_engine.py` (new) + refactor `fit_primitive.py` and `fit_primitive_features.py`
**Exports**:
```python
class FitEngine(Protocol):
    def can_handle(self, substrate, candidate) -> tuple[bool, str]: ...
    def fit(self, declaration, evidence) -> FitResult: ...
    def write_result(self, workspace_dir, result) -> None: ...
    def residual_diagnostic(self, result, evidence) -> str: ...

class OneDFitEngine: ...           # adapter for fit_primitive
class FeatureVectorFitEngine: ...  # adapter for fit_primitive_features (Bug #31 closed-loop)
class TensorTargetFitEngine: ...   # NEW for D2 — tensor y.shape=(N,T)
```

**Constraints**:
- Drop AST whitelist? **Decision: KEEP** as footgun-protection (namespace lockdown is the security boundary; whitelist still prevents idiom confusion). Document that v5.0 retains it as belt-and-suspenders.
- Add `residual_diagnostic` to ALL adapters (1D primitive currently has it via `diagnose_residual_pattern`; N-D got it in Bug #31; tensor adapter is NEW).

**Deliverables**:
1. Protocol + 3 adapters + tests
2. Wire single `Cage.dispatch_fit(substrate, candidate)` call in autoresearch_loop replacing 1D + N-D parallel blocks
3. Verify gp154/gp155/gp077/gp146 run unchanged; new gp146-style tensor substrate as integration test

**Estimated**: 4-6 hours.

### Phase 3a — Dormant gate triage + wire-in (NEW 2026-04-25 night)

`make gates` shows 7 LIVE / 17 DORMANT. Every dormant gate must be
either WIRED into Cage's gate registry OR formally RETIRED with rationale.
No gate stays "built but dark code" past v5.0 ship. Per Class L finding
in gp158 evidence.

**Per-gate decisions required** (each must be reasoned, not bulk-handled):

| Gate | Substrate class | Default decision |
|---|---|---|
| ansatz_survivor_gate | proof_target | WIRE — used by GP-122 Lean REPL pipeline |
| asymptotic_claim_discipline | 1d + nd_features | WIRE — defends Class B silent failures |
| bridge_scope_contract | all | WIRE — universal contract gate |
| continuum_limit_gate | time_series + 1d | WIRE — Wasserstein-class substrate |
| coordinate_invariance_gate | 1d | WIRE — frame-invariance per GP-152 v2.0 |
| deterministic_charter_gates | 1d + nd_features | WIRE — charter contract |
| domain_match_gate | nd_features | WIRE — gp154/gp155 substrate match |
| ensemble_ambiguity_gate | nd_features | WIRE — multi-form scoring |
| prompt_leak_audit | meta_audit | WIRE — gp156/gp158 substrates |
| proof_surveyability_gate | proof_target | WIRE — GP-139 backbone |
| pslq_falsity_audit_gate | closed_form_constant | WIRE — GP-145 |
| residual_norm | 1d | WIRE — basic 1d telemetry |
| semantic_gate_stabilization | all | WIRE — universal, defends self-reference |
| translation_diff_gate | proof_target | WIRE — GP-122 hash canonicalization |
| wasserstein_persistence_gate | time_series_chaotic | WIRE — GP-143 |
| cage.py | (this module) | WIRE (orchestrator) |
| substrate_evaluation.py | (Phase 1 utility) | WIRE (utility) |

**RETIRE candidates**: NONE proposed by default — every dormant gate has a
real substrate-class affinity. Operator may RETIRE individually with
rationale recorded in `DECISION_LOG.md`.

**Phase 3a deliverable**: a `src/ztare/gates/registry.py` module exporting
`get_default_cage() -> Cage` that registers all 17 gates with their
phase / can_handle / dependencies / run callbacks. autoresearch_loop
imports this and calls `cage.dispatch(substrate, candidate)` once per
iter, replacing 7-14 scattered conditional-import dispatch sites.

**R6 integration-smoke-test requirement**: every gate registered in the
default Cage MUST have at least one substrate-and-candidate fixture
that exercises its engagement path. The fixture suite lives at
`src/ztare/gates/tests/integration/test_gate_engagement.py` with one
`test_<gate_name>_engages_on_<substrate>` per gate.

### Phase 3b — Cage dispatcher + `can_handle` (HIGHEST RISK)

**File**: `src/ztare/gates/cage.py` (new)
**Exports**:
```python
class Cage:
    def __init__(self, gates: list[Gate]): ...
    def dispatch(self, substrate, candidate) -> EngagementMatrix: ...
    def can_handle_with_diagnostic(self, gate, substrate, candidate) -> tuple[bool, str]: ...

@dataclass
class Gate:
    name: str
    can_handle: Callable[[substrate, candidate], tuple[bool, str]]
    dependencies: list[str]  # N2 fix: explicit DAG
    phase: Literal["FIT_PRE", "FIT_POST", "JUDGE_PRE", ...]
```

**Required gates and adequacy checks**:
- R8 data-adequacy: every form-feature has ≥30% coverage
- R9 target-homogeneity: substrate.meta.target_convention_homogeneity declared and respected
- N4 min-rows-per-category: substrate.meta.min_rows_per_category respected
- N3 plain-dict meta: `isinstance(substrate.meta, dict)` strict

**Substrate metadata schema** (substrate.meta required fields):
```python
{
    "type": str,                              # was "kind" — D1 fix
    "class": Literal["1d", "nd_features", "time_series", "audit", "literature"],
    "target_convention_homogeneity": Literal["homogeneous", "heterogeneous"],  # R9
    "min_rows_per_category": int,             # N4
    "near_miss_factor": float,                # D3
    "frame_invariant_y": bool,                # marks whether y is dimensionally consistent
}
```

**Substrate metadata enforcement**:
- `scripts/public/generate_substrate.py` schema validator REFUSES to ship without all required fields
- Cage dispatcher refuses to engage substrates lacking the metadata

**Deliverables**:
1. `cage.py` + dispatcher with explicit DAG (N2)
2. Substrate-meta schema validator in `scripts/public/generate_substrate.py`
3. Migrate gp154/gp155/gp156/gp158 substrates to declare required meta
4. Integration tests: every gate × every substrate-class pair has expected engagement assertion
5. Software-Integration-Engineer panel review (R7) BEFORE merge

**Estimated**: 1-2 days.

## 5. Anti-overfitting rule for v5.0

Every magic number in v5.0 MUST have one of:
- (a) Empirical derivation against ≥2 substrates from different classes (e.g., near_miss_factor calibrated per substrate via metadata, not hardcoded)
- (b) BIC / MDL theoretical justification (per GP-152 framer spec v2.0)
- (c) Audit trail: a documented gp158-class adversarial validation that the number is robust

The K_law=5 → 8 → 10 evolution is the ANTI-PATTERN: a Munger heuristic survived a sycophancy-loop audit (gp152/153) for weeks. v5.0 must not repeat this.

## 6. Backward compatibility window

All current substrates (gp154/gp155/gp156/gp077/gp145/gp146/gp150/gp158) must run UNCHANGED through Phase 1. Phase 2 + 3 introduce new Protocol; per-substrate migration via metadata declaration.

Legacy `test_thesis.py:2335-2470` parser remains during migration; deprecation warnings printed when legacy schema detected. Removal target: 30 days post Phase 3.

## 7. Verification protocol

After each phase:
1. `python -m pytest src/ztare/fit/tests/` — all green
2. `python3 scripts/public/validators/validate_autoresearch_arch_map.py ex-post` — 33/33 verified
3. `python3 scripts/public/validators/validate_rubric.py <every-active-rubric>` — all PASSED
4. End-to-end smoke test: launch gp155 (synthetic, fastest signal); expect score 90+ in 2-3 iters
5. Gate-engagement reachability matrix: assert every (gate × substrate-class) pair has explicit engagement entry

If any verifier red, STOP. Do not advance to next phase.

## 8. Scope expansion 2026-04-25 night — v6.0 items PROMOTED into v5.0

The user reviewed the spaghetti+docs assessment and decided: **"V6 needs to be V5"**.
The §8.1 (autoresearch refactor) and §8.3 (substrate validator) items
originally scoped to v6.0 are PROMOTED into v5.0. §8.2 (GP-XXX docs reform)
is also PROMOTED. A 5-perspective panel (Torvalds / Knuth / Karpathy /
Hickey / Kernighan) was launched to review the proposed split + atomic-commit
sequence; verdicts will be appended to GP-157 seam when the agent completes.

The 4-phase plan becomes:
  Phase 1 ✅ substrate_evaluation utility
  Phase 2 ✅ FitEngine Protocol
  Phase 3a ✅ gate registry (panel-triaged)
  Phase 3b ✅ Cage observe-mode wired into autoresearch_loop (additive)
  Phase 3c ✅ Cage authoritative dispatch (cage_authoritative_mode rubric flag, default off; dispatch_and_run added with 5 tests)
  Phase 4a ✅ IterContext dataclass (Hickey decomplecting target, 9 tests)
  Phase 4b ✅ orchestrator/telemetry.py (CageEngagementRecord + JSONL primitives, 8 tests)
  Phase 4c ✅ orchestrator/state.py (CageRuntime + mode resolution, 13 tests)
  Phase 4d ✅ orchestrator/prompt.py (substrate-contract-hint, 31 tests, NARROWED 2026-04-25 night to {nd_features} only) — fixes gp159 mutator-empty-Python; adds Contract C (scalar 1D) hint + verify_class_consistency_with_substrate to lock the gp159 wrong-class regression
  Phase 4e ⏳ orchestrator/parallel_mutator.py SKELETON shipped (18 tests) — pull-forward of GP-060 design + Gemini Pro MCTS framing. NOT YET WIRED — autoresearch_loop unchanged. Wire-in deferred per Linus atomic-commit discipline + cost concern (K× spend per iter; opt-in only).
  Phase 4f ✅ orchestrator/contract_adherence.py (18 tests) — adherence telemetry per operator concern that hint may be ignored amid ~15 prompt sections. JSONL emit per iter to workspace/contract_violations.jsonl.
  Phase 4g ⏳ orchestrator/main.py + dispatch.py + r1_retry.py (full modular split — pending stability soak)
  L1 ✅ typed-contract foundation: contract_table.py (SubstrateABI enum + ContractSpec dataclass + CONTRACT_REGISTRY) + protocols.py (PEP 544 ScalarModel/FeatureModel + adapt() boundary validator + ContractError) + render_evidence_template.py (auto-generate evidence.txt §D from ContractSpec — single source of truth for the test_model.py shape, eliminates the 5-source-contradiction failure mode by construction). 29 tests. Per Task #67 panel verdict.
  L70 ✅ Phase 2 wire-in AUTHORITATIVE: autoresearch_loop's fit dispatch routes through FitEngine.select_adapter(substrate, candidate). OneDFitEngine.fit + FeatureVectorFitEngine.fit return native FitSuccess|FitFailure for downstream isinstance compat. Legacy direct fit_parameters() call retained as safety-net fallback only when no adapter matches (closed_form_constant, proof_target). JSONL telemetry to workspace/fit_engine_dispatch.jsonl per fit. After full substrate-class coverage, fallback removes.

### Panel Failure-Mode Closure (Tasks #72-74, plus follow-on wires) — 2026-04-25 night

Per Gemini Pro panel review on Ada-style typed contracts + four failure-mode inversion. Concrete closures shipped:

  Gap #1 ✅ Popper-leakage sanitization (Failure Mode 1):
    src/ztare/validator/utilities/harness_failure_mode.py:sanitize_stderr_for_mutator
    strips file paths + line numbers + apparatus stack frames from raw stderr
    BEFORE it flows back to the mutator's prompt context. Operator-facing
    debate logs keep full stderr; mutator-facing summary uses sanitized leaf
    only. Closes the regex-around-traceback evasion attack surface.

  Gap #2 ✅ Nullable Ada contract fields (Failure Mode 2):
    ContractSpec extended with `nullable_feature_keys: frozenset[str]` +
    `nullable_asymptotic_limits: dict`. FEATURE_DICT spec declares
    intrinsic_dim_d nullable with limit float('inf') (LLM embedding-space
    limit) and noise_scale nullable with limit 0.0. Closes gp154 Class K
    case: 80/82 rows had intrinsic_dim_d=None, schema now treats that as
    physical absence (asymptotic limit), not contract violation.

  Gap #3a ✅ Structural probes (data-driven substrate identification):
    src/ztare/scaffold/substrate_probe.py — three deterministic O(N) probes
    (integer-fraction, lag-1 autocorrelation, shuffle-invariance) auto-classify
    substrates into {DISCRETE, DYNAMICAL_CHAOTIC, SCALAR_KINEMATIC, AMBIGUOUS}.
    Threshold tuning: autocorr_raw >= 0.85 + delta >= 0.5 for dynamical;
    ambiguous defaults to kinematic (false-positive on dynamical worse than
    false-negative). 13 tests including gp159-style sorted-monotonic vs.
    AR(1) chaotic discrimination.

  Gap #3b ✅ Auto-classification at substrate ingestion:
    src/ztare/scaffold/generate_substrate.py wires substrate_probe.classify_substrate
    into the rubric-write path. New substrates get cage_meta.class +
    class_provenance="auto_classified_at_ingestion" + class_confidence +
    class_diagnostics written automatically at substrate-construction time.
    Pushes class determination from operator-tagging (gp159 wrong-class
    source) to data-shape inference. Fail-soft when probe unavailable.

  Gap #3c ✅ SubstrateAmbiguityError + seal-time data-shape verification:
    SubstrateAmbiguityError class shipped (intended to raise to LLM mutator
    at R1 when probes inconclusive — epistemic handshake). Already wired:
    scripts/public/validators/validate_evidence.py:check #14 invokes verify_class_against_data
    on the y-column at make-seal time, refusing to seal when declared
    cage_meta.class disagrees with detected data shape. Catches gp159-class
    wrong-class regression at the LAST possible boundary before iter spend.

  Gap #4 ✅ Convention-bridging assertion:
    src/ztare/orchestrator/prompt.py:verify_convention_bridge_in_form
    static-checks the mutator's PARAMETRIC_FORM. When substrate declares
    target_convention_homogeneity='heterogeneous', the FORM must contain a
    bridge term keyed off features['fit_convention'] OR a per-convention
    coefficient. Without it, scipy silently averages incommensurable units
    (Class K trap). 5 tests pin behavior.

  Gap #5 ✅ Phase 1/2 immutable handoff (Failure Mode 3):
    src/ztare/orchestrator/fitted_model.py:FrozenFittedModel — frozen
    dataclass wrapping the I_model callable + fitted_params (MappingProxyType
    read-only) + symbolic expression + ABI label. Phase 1 (FitInstrument
    router) constructs; Phase 2 (gates) consumes as Final. Mutation attempts
    raise TypeError. 5 tests pin frozen invariants. Required when parallel
    mutator (Task #63) ships, since shared mutable state would race.

  Gap #6 ✅ Audit must-fail constraint (Failure Mode 4):
    test_thesis.py judge prompt (line ~683) extended with explicit rule:
    architectural / structural critiques must include either (a) compilable
    attack vector OR (b) file:line citation; theoretical-elegance proposals
    are penalized. Closes gp158-style audit-volume-over-validity drift.

  L2 ✅ typed evidence contract (Task #71) — SHIPPED 2026-04-25 night.
    src/ztare/orchestrator/evidence_contract.py:
      - EvidenceFormat enum (WHITESPACE_TABULAR, MARKDOWN_TABLE, SWEEP_BLOCK,
        CSV_HEADER, TSV_HEADER, JSON_LINES, NONE)
      - EvidenceSpec frozen dataclass (format, columns, independent_vars,
        delimiter, header_skip, min_rows, require_finite, require_monotone_in)
      - EvidenceContractError with canonical codes (NO_DECLARATION,
        FORMAT_UNREGISTERED, PARSE_FAILED, ROW_FLOOR_VIOLATION, NON_FINITE,
        NON_MONOTONE, COLUMN_COUNT_MISMATCH, NON_NUMERIC_CELL)
      - get_evidence_spec(rubric_data) reads `evidence_contract` block from rubric
    src/ztare/fit/parsers/__init__.py:
      - EVIDENCE_PARSER_REGISTRY: dict[EvidenceFormat, ParserFn]
      - 7 per-format parsers (one per EvidenceFormat value)
      - parse_evidence_typed(text, spec) — public dispatcher; format-driven,
        no sniffing
      - shared _validate_parsed (row floor / finite / monotone)
    22 tests including round-trip spike (whitespace ↔ markdown ↔ csv
    bit-identical (xs, ys) for equivalent data) + fail-loud semantics
    (typed path catches what heuristic silently dropped).
    Wired into make seal as check #15: when rubric declares
    `evidence_contract`, dispatch via spec; raises at seal time, not
    at iter time. Smoke-tested on gp159 actual evidence: parses 11 rows
    correctly via MARKDOWN_TABLE format.

  L1 enforcement at seal time ✅ — closes the previously-latent gap
  where ContractSpec was built but adapt() was never invoked. New
  scripts/public/validators/validate_evidence.py:check #16: when test_model.py exists,
  import + run adapt(module, spec) at seal time. Catches signature /
  required-globals / contract violations BEFORE any iter spend. Soft
  failure (warning) when test_model.py is the substrate placeholder
  with NaN-returning I_model — that's expected pre-mutator state and
  will fire as R1 strike on first submission.

  L3 ✅ declarative gate manifest (panel verdict 2026-04-25 night) — SHIPPED.
    src/ztare/orchestrator/gate_manifest.py:
      - GateType enum (10 unanimous-WIRE gates, Linus-syscall numbering 1-10:
        BOUNDS_CHECK, HOLDOUT_MRE, EXTRAPOLATION_MRE, ASYMPTOTIC_DISCIPLINE,
        MONOTONICITY, POSITIVITY, PARAMETER_COUNT, ANTI_RETRIEVAL,
        FRAME_INVARIANCE, DIMENSIONAL_CONSISTENCY)
      - EvaluativeGateSpec frozen dataclass (type, target_variable,
        parameters, binding, docstring)
      - PARAMETER_SCHEMAS dict[GateType, dict[str, type]] — strict-typed
        kwargs per gate type
      - GateContractError with canonical codes (UNKNOWN_GATE_TYPE,
        MISSING_PARAMETER, WRONG_PARAMETER_TYPE, EXTRA_PARAMETER,
        GATE_TYPE_NOT_REGISTERED)
      - validate_gate_spec(spec_dict) — strict (no extras, no missing,
        types match) → typed EvaluativeGateSpec
      - GATE_REGISTRY with 3 reference impls: BOUNDS_CHECK, HOLDOUT_MRE,
        ANTI_RETRIEVAL (other 7 validate but raise GATE_TYPE_NOT_REGISTERED
        on invocation — add incrementally as substrates need)
      - GateContext Protocol + evaluate_gate dispatcher
    25 tests in tests/orchestrator/test_gate_manifest.py covering enum
    coverage, strict validation (every error code), and impl correctness
    for the 3 shipped gates.
    Per Gemini Pro: replaces operator-authored imperative gate_harness.py
    files with rubric-declared `evaluative_gates: [...]` blocks. The Cage
    dispatcher reads, validates, instantiates pre-verified gate classes,
    runs against the FrozenFittedModel from Phase 1. Eliminates the
    gp160-class intent / mechanism translation gap by construction —
    operator cannot declare BOUNDS_CHECK and execute MRE; the mechanism
    IS the type.
    Arch map at docs/internal/architectural_maps/orchestrator_gate_manifest_architectural_map.md
    (16/16 claims green). Wire-in (next ship): scripts/public/validators/validate_evidence.py
    Check #17 + autoresearch_loop Phase 2 declarative dispatch +
    per-substrate gate_harness.py → rubric.evaluative_gates migration sweep.
  Phase 5 ⏳ docs reform: gp_index.md ✅ + lifecycle YAML frontmatter (5/132 canary, bulk pending)
  Phase 6 ⏳ generate_substrate.py schema validator (formerly v6.0 §8.3) — see §8.4 below for evidence-quality lint scope

Sequence rationale (Munger ordering): apparatus → docs. Don't pretty up
docs that describe code about to be refactored. Phase 4 (orchestrator
split) MUST land BEFORE Phase 5 (docs reform), or the refactor invalidates
the freshly-built index.

Specific deliverables for the now-in-scope phases:

### Phase 4 — modular orchestrator split (NEW v5.0 scope)

Target structure:
```
src/ztare/orchestrator/
  ├─ main.py        — top-level iter loop (~500 lines, was 6,300)
  ├─ dispatch.py    — Cage gate dispatcher integration
  ├─ state.py       — best_state + snapshot/restore + revert
  ├─ telemetry.py   — banners + JSONL writers + cost ledger
  ├─ prompt.py      — mutator/judge prompt assembly
  └─ r1_retry.py    — compiler-bounce retry loop
```

Migration discipline (Linus atomic-commit pattern):
1. Each split lands in ONE commit; arch-map verifier green per-commit
2. Old autoresearch_loop.py becomes a 50-line shim that imports from
   orchestrator/ during the migration window
3. After all 6 modules ship + observed-stable for ≥3 days, shim retires
4. Rollback = revert the shim's import directive; all old code is in
   orchestrator/ already

NOT in scope for v5.0: changing any iter-loop semantics. The split is
pure code-locality refactor; behavior must be identical pre/post split.

### Phase 5 — GP-XXX documentation reform (NEW v5.0 scope)

Three concrete fixes (operator-proposed; pending panel-refinement):

1. **`docs/internal/repo_audits/gp_index.md`** — auto-generated index. New script
   `scripts/public/control/build_gp_index.py` walks repo for GP-NNN references and writes
   a markdown table: `(id, kind, status, owner, last_updated, supersedes_chain)`.
   Run via `make gp-index` and as a pre-commit hook.

2. **Lifecycle states encoded in YAML frontmatter** — each `GP-NNN_*.md`
   gets `---\nid: GP-NNN\nstatus: <enum>\n---\n` header. Status enum:
   `proposed → debating → spec → implementing → shipped → archived → retired`.
   `make gp-archive GP=NNN` moves the file to `archived/` and updates the
   index.

3. **Per-artifact CHANGELOG sections** aggregated into `CHANGELOG.md` —
   each artifact ends with a `## Changelog` section. The indexer script
   aggregates all changelog sections into a project-wide append-only log.

### Phase 4d — substrate-class-aware mutator prompt (SHIPPED 2026-04-25 night)

Real fix for the gp159 mutator-empty-Python bug surfaced by parallel agent.
Root cause: the mutator prompt is substrate-class-blind. When neither
fit primitive is engaged AND the substrate is custom (cage_meta.class
∈ {nd_features, audit, literature, proof_target}), the standard prompt
describes the assert-based discriminator contract while evidence.txt
describes the I_model OVERRIDE contract. The mutator (gpt-4.1
particularly) sees the conflict and writes nothing → I_model returns
NaN → all iterations fail.

Module: `src/ztare/orchestrator/prompt.py` (~120 lines, 19 unit tests).

Key seam:
  `select_substrate_contract_hint(rubric_data) -> str` — returns the
  I_model OVERRIDE contract block when needed; "" otherwise. Wired into
  `mutate_thesis` between `fit_primitive_features_context` and
  `structural_memory_prompt`.

Contract block content:
  - Mandatory: `I_model(features) -> float`, return finite (no NaN).
  - Imports: `from features import visible_rows, holdout_rows`.
  - Forbidden: assert-based discriminator tests (legacy 1D contract).
  - Skeleton example so the mutator has a concrete starting shape.

**Operational risk acknowledged (operator concern 2026-04-25 night):**
the prompt has many sections — fit-primitive contexts, charter,
constraints, residual mode, structural memory, anti-pattern catalog,
DAG steering, R1 retry hints. The substrate-contract-hint is one
block among ~15. A motivated mutator may still skim past it. Three
mitigations available, ordered by cost:
  1. (Done) Block uses strong framing — `### CUSTOM SUBSTRATE — I_model
     OVERRIDE CONTRACT (read carefully)`, explicit FORBIDDEN list, NaN
     warning, full skeleton.
  2. (Future) Adherence telemetry: log when an iteration's emitted
     test_model.py contains `def assert_` AND the hint was active. If
     >X% of iters mis-write, escalate.
  3. (Future) Pre-flight: if cage_meta.class is custom + no fit primitive,
     reject runs whose evidence.txt lacks an `I_model` skeleton example
     in a `SUBMISSION CONTRACT:` section.

### Phase 6 — generate_substrate.py schema validator (NEW v5.0 scope)

Per Class K + R9: substrate constructors MUST declare canonical Cage
metadata at substrate-shipping time. `scripts/public/generate_substrate.py`
schema validator refuses to ship without:
  - `target_convention_homogeneity` ∈ {homogeneous, heterogeneous}
  - `min_rows_per_category` (int)
  - `near_miss_factor` (float)
  - `frame_invariant_y` (bool)
  - `class` ∈ valid substrate classes

Existing substrates migrate via `make migrate-substrate-meta PROJECT=<name>`
which prompts for missing fields and writes them into the rubric.

### §8.5 contract-prescriptiveness vs scientific exploration

Operator concern (2026-04-25 night): the substrate-contract hints
(Contracts A/B/C) prescribe how the mutator must shape test_model.py.
Is this prescription compatible with epistemic exploration?

**Answer (operator-honest):** the contracts prescribe *interface shape*
(function signature, return type, where MODEL_PARAMS is filled, NaN
prohibition), NOT *scientific content* (functional form, parameters,
families, mechanisms). The space of valid scientific answers is
unconstrained. Contract ≠ solvability claim — see
`feedback_no_solvability_gatekeeping.md`.

**What is panel-reviewed:** none of this. R8/R9 substrate-metadata
rules in cage.py were panel-derived from the gp158 audit, and the
contract hints are downstream of those rules. But the specific hint
text + Contract A/B/C taxonomy is agent-authored, not panel-debated.
A formal panel review pass on the hint text + violation taxonomy is
warranted before any further constraint-tightening (e.g., adding
Contracts D/E/F for time_series, closed_form_constant, proof_target).

**Three contracts in active service today:**
  - Contract A — assert-based discriminator suite (legacy 1D, no fit
    primitive, no authored test_model.py).
  - Contract B — `I_model(features: dict) -> float` (nd_features
    substrates with authored test_model.py + features.py).
  - Contract C — `I_model(d: float, params: dict = ...) -> float`
    (1D substrates that author their own test_model.py — gp159, gp160,
    gp161, gp145, gp146).

Hint scope is intentionally narrow: only fires when active contract
is non-trivial AND no fit primitive is engaged. False-positive rate
is the constraint — wrong hint injection is worse than missing hint
(gp159 wrong-class regression demonstrated this).

### §8.4 evidence-quality lint scope (operator-flagged 2026-04-25 night)

`make seal` currently checks GT leakage (sentinel/denylist) + harness
smoke tests, but NOT evidence-quality. Other agent flagged gaps:

  - **Inline data check**: evidence must contain actual data, not
    "run X to fetch the data" (mutator can't execute).
  - **Code-template GT leakage**: skeleton example in evidence must
    not encode the GT functional form (e.g., GT is a power law and
    skeleton uses `x ** alpha` — leaks the family).
  - **Required sections**: must contain `VISIBLE DATA:`,
    `SUBMISSION CONTRACT:`, `CONSTRAINTS:` markers (lint-set TBD).
  - **Anti-contamination**: detect known GT constants verbatim in
    evidence; detect structural hints matching the answer.

Tension: each substrate has different needs; a hard linter risks
overfitting to canonical substrates and rejecting valid novel ones.

Proposed shape:
  - SOFT lints (warnings, not failures) by default — emit advisory
    diagnostics during `make seal`.
  - Opt-in STRICT mode via rubric flag `evidence_strict_lint: true`
    that promotes lints to failures.
  - Lint set defined PER-CLASS (cage_meta.class drives which lints fire):
    nd_features substrates need a different lint set than time_series
    or proof_target substrates.

This requires panel-review before ship — the lint set design is the
decisive decision, not the mechanism. Tracked as Phase 7 (post-v5.0).

## 8a. ORIGINAL Future scope (now retained as historical context only)

These are real architectural concerns the operator raised; v5.0 is too
narrow to address them but they should be tracked.

### 8.1 autoresearch_loop.py spaghetti refactor (v6.0 candidate)

`src/ztare/validator/autoresearch_loop.py` is 6,200+ lines of deeply-nested
control flow with cross-cutting concerns (mutator dispatch, gate evaluation,
state snapshot/restore, telemetry, prompt assembly, R1 retry, framer
hooks, fit primitive dispatch, holdout-hard-gate, judge invocation). Each
edit risks line drift requiring `validate_autoresearch_arch_map.py`
re-baselining. The 2026-04-25 session shipped 32+ bugfixes; many were
exacerbated by the file's monolithic structure.

A kernel-patch-style refactor would split into:
- `src/ztare/orchestrator/main.py` — top-level iter loop (~500 lines)
- `src/ztare/orchestrator/dispatch.py` — Cage gate dispatcher
- `src/ztare/orchestrator/state.py` — best_state, snapshot/restore
- `src/ztare/orchestrator/telemetry.py` — banners, JSONL writers
- `src/ztare/orchestrator/prompt.py` — mutator/judge prompt assembly
- `src/ztare/orchestrator/r1_retry.py` — compiler-bounce retry loop

Each becomes independently testable; line drift becomes per-file not
cross-file; arch-map becomes a directory-level index instead of a single
6000-line region map.

NOT v5.0 scope. Defer to v6.0. Add to `DECISION_LOG.md` as a tracked
architectural debt.

### 8.2 GP-XXX naming convention review (v6.0 candidate)

The `GP-XXX` ID convention (project / seam / spec naming) accumulated
organically. Today there are 158 GP-numbered artifacts spanning seams,
specs, projects, postmortems, and research_areas. The mapping
`GP-NNN → artifact_kind` is implicit; new contributors need to grep
multiple directories to determine what GP-NNN refers to.

Proposal: add a top-level `docs/internal/repo_audits/gp_index.md` indexing every
GP-NNN with (kind, status, owning seam/spec, current owner, decision-log
references). Auto-generated by a script that walks the repo and extracts
GP-NNN occurrences from filenames + docstring frontmatter.

NOT v5.0 scope. Defer to v6.0 documentation pass.

### 8.3 Substrate constructor schema validator (NEW per Class K finding)

Per Class K (target-variable heterogeneity, gp154-grounded), substrate
constructors must declare `target_convention_homogeneity` AT
substrate-shipping time. `scripts/public/generate_substrate.py` should
refuse to write a substrate without this declaration. Schema validator
should also enforce N4 (`min_rows_per_category`) and the canonical
substrate-meta shape from §3 R-rules. Phase 3 includes this.

## 9. Rollback plan

Phase 1 is additive (new utility); rollback = revert the gate_harness.py changes; legacy parser unchanged.

Phase 2 is additive at FitEngine layer; rollback = unwire the dispatcher, leave Protocol module dormant.

Phase 3 introduces Cage; rollback = remove dispatcher, autoresearch_loop falls back to direct primitive calls. Substrate-meta declarations remain (not decisive at run time without Cage).
