# autoresearch_loop.py — Agent Self-Model

```
purpose:    token-optimized self-model FOR agents; not human prose
read_pre:   editing src/ztare/validator/autoresearch_loop.py
update_post: any change to phase|gate|exit|invariant|state-var
verifier:   scripts/validate_autoresearch_arch_map.py {ex-ante,ex-post,show}
format:     structured-block + dependency-chain + assert/check/why/trap; NO narrative paragraphs
seam:       GP-101 (open) — research_areas/private/seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md
discipline: line numbers drift → grep to confirm; if claim breaks, fix or revert; stale map worse than no map
```

## REGION INDEX

```
region: cli_args          lines: 190-341    entry: parser.add_argument
region: globals           lines: 342-422    entry: RUNTIME, MUTATOR_MODEL_ID, paths
region: artifact_mgmt     lines: 423-575    entry: _pop_seed_queue, _persist_best_candidate
  note: _project_state_paths includes fit_result.json — revert is atomic across prose AND math
region: gate_telemetry    lines: 576-1727   entry: _extract_iteration_gate_metrics
region: prepare_candidate lines: 1738-1830  entry: def _prepare_mutation_candidate
  note: GP-156 (2026-04-25) added inside prepare_candidate — Proposal 1
        validate_python_suite_imports (~L1766) catches import-time TypeError /
        AttributeError / NameError / ImportError + AST pre-flight rejection of
        module-level I_model() calls (programmatic contract enforcement);
        Proposal 2 attest_visible_mre (~L1781) catches fabricated visible-MRE
        prose claims. Both raise ValueError → upstream classifies as Runner R1
        rejection (or compiler-bounce retry — see main_loop note below).
region: llm_call          lines: 1868-1912  entry: def safe_mutate
region: prompt_assembly   lines: 1913-3210  entry: def compute_dag_steering_context
  note: compute_dag_steering_context (GP-134 DAG steering) → def mutate_thesis follows.
  note: non-V4 stagnation prompt escalation threshold is sourced from
        `pivot_heuristics.resolve_stagnation_pivot_state()`, not hardcoded in-place.
  note: GP-156 fit_primitive_features_context prompt section (~L2544-2570)
        injected when rubric.enable_fit_primitive_features=true; tells the
        mutator to declare PARAMETRIC_FORM + PARAMETER_NAMES + MODEL_PARAMS={}
        and includes explicit DO/DON'T patterns for the assert-timing /
        bare-identifier R1 failure modes.
region: grammar_helpers   lines: 3682-3692  entry: def build_model_grammar_failure_code
region: init              lines: 3694-3756  entry: if __name__ == "__main__"
region: rubric_preflight  lines: 3757-3867  entry: # --- GP-133 Round 4
  note: GP-133 R4 gates fire HERE (fail-closed). Checks py_exec_authorized_by +
        expression_byte_budget (when fit_expression_grammar=='py_exec') and
        Generative Yield dimension presence (when rubric_mode=='newton'). Raises
        SystemExit on violation BEFORE rubric-review / mutator / any LLM calls.
  note: Epistemic Airgap gate: after rubric_mode handling, checks rubric-level
        require_cross_family. CLI --require_cross_family checked earlier at model
        resolution (lines 328-340). Both raise SystemExit if mutator and judge
        share a provider family (openai/anthropic/google). Default: warn only.
        Makefile: CROSS_FAMILY=1 on loop/experiment-loop/discover/honeypot-loop.
region: postloop_helpers  lines: 4318-4400  entry: def _finalize_run_telemetry_once
region: main_loop         lines: 4411-7344  entry: --- Iteration {i + 1}
  note: loop-control action + pivot event logging must use the same
        `resolve_stagnation_pivot_state()` source of truth as prompt assembly.
  note: GP-152 Framer observe-mode hook fires inside main_loop at the
        post-mutation fit_parameters site (~line 4360) when rubric declares
        enable_framer=true. Writes framing_report.json; does not modify data.
  note: MutatorBriefing pre-prompt assembly at ~L2540-2730 (refactored
        2026-04-26). Reads workspace artifacts via 5 BriefingProviders
        (fit_telemetry, gate_gap, iter_trajectory, row_outliers,
        asymptote_deviation) defined under
        src/ztare/orchestrator/briefing_providers/. Persists
        workspace/mutator_briefing_iter_NNN.md per iter for operator
        audit. Adding a future provider = 1 file + 1 line in
        default_briefing(); no edit to this region.
  note: GP-156 Proposal 3 fit_primitive_features wire-in at ~L4587, gated by
        rubric flag enable_fit_primitive_features. Engages when substrate
        declares PARAMETRIC_FORM + PARAMETER_NAMES; reads in-memory python_code
        (NOT disk) via should_engage(python_code_override=...); reads canonical
        visible rows from features.visible_rows() (NOT test_model.VISIBLE_SET
        which the mutator overwrites); runs scipy.optimize multi-start with
        per-parameter init_range + auto-escalation (5x, 25x widening on flat-
        desert). Substitutes fitted MODEL_PARAMS into python_code via AST
        rewrite. Writes workspace/fit_features_result.json with rich verbose
        telemetry on every iter (`🧮 ─── dispatch ───` banner).
  note: GP-157 "Compiler Bounce" 3-strike free retry for R1 lint-class
        rejections (~L4331-4360 wrapping _prepare_mutation_candidate). Lint
        failures (AST, syntax, NameError, KeyError, missing I_model, missing
        PARAMETRIC_FORM) trigger up to 3 in-place mutator re-prompts with the
        specific error injected into the retry prompt. Iteration counter NOT
        advanced during retries. After MAX_R1_RETRIES=3 strikes, original
        ValueError propagates → iter consumed as catastrophic FAIL_RUNTIME.
        Cost model: lint failures cost ~$0.05 mutator-only per retry instead
        of ~$0.40 full-iter. Scientific failures (MRE > gate, judge hardkill)
        still consume iter — boundary preserved.
region: postloop          lines: 7340-7360  entry: print("🏁 OPTIMIZATION LOOP COMPLETE")
```

## PIPELINE: ITERATION DEPENDENCY CHAIN

Each phase consumes the output of the previous phase. No phase may be reordered.

```
PHASE_A (content_generation, lines ~2684-3053)
  input:  current_thesis:str, current_test_model:str, evidence_text:str, rubric_data:dict
  output: new_content:str
  branch:
    IF composition_seed.json exists:
      read seed[0] → _seed_expr, _seed_vars, _seed_params
      strip old fit_declaration from current_thesis via regex
      inject ```fit_declaration block with _seed_fd_block
      inject synthetic loud-fail ```python stub (fixed 2026-04-20, see INV-1 note)
      set _comp_seed_injected = True
      IF rubric_data["epistemic_alignment"] == True:
        preserve _existing_py = re.search(```python, new_content)
        call safe_mutate(alignment_prompt, model_id=resolve_model_id("gpt4.1"))
        ASSERT _seed_fd_block in _aligned  # full JSON block, not substring
        re-inject _existing_py into _aligned if ```python absent
        new_content = _aligned
    ELSE:
      new_content = mutate_thesis(current_thesis, current_test_model, ...)

PHASE_B (structural_validation, lines ~3054-3317)
  input:  new_content:str
  output: clean_thesis:str, python_code:str|None, mutation_declaration, mutation_validation
  calls:
    _prepare_mutation_candidate(raw_text=new_content, ...)
      → re.search(```python, working_text) → python_code
      → validate_python_suite_candidate(python_code)  # RAISES if None
      → evaluate_mutation_declaration(...)
  exit_on_fail:
    ValueError → Runner R1 exception → _pop_seed_queue, _restore_project_state, continue
    mismatch_code != CLEAN → Runner R1 mismatch → _pop_seed_queue, _restore_project_state, continue

PHASE_C (fit_primitive, lines ~3070-3175)
  gate:   rubric_data["enable_fit_primitive"] == True AND evidence_text != ""
  input:  new_content:str, python_code:str
  output: _fit_decl:FitDeclaration|None, _fit_result:FitSuccess|FitFailure|None, python_code:str (modified)
  calls:
    parse_fit_declaration(new_content) → _fit_decl
    fit_parameters(_fit_decl, evidence_text, ...) → _fit_result
    IF isinstance(_fit_result, FitSuccess) AND python_code is not None:
      python_code = substitute_fitted_params(python_code, _fit_result.fitted_params)
    update_structural_memory(workspace_dir, _fit_decl, _fit_result, ...)

PHASE_D (layer3_mandatory, lines ~3325-3420)
  input:  _fit_decl, _fit_result, python_code, rubric_data
  output: test_model.py written to disk
  branch:
    IF rubric_data["enable_fit_primitive"]:
      IF _fit_decl is not None AND isinstance(_fit_result, FitSuccess):
        write deterministic def f() from expression + fitted_params
        set _layer3_built = True
      ELSE:
        write loud-fail stub (raises RuntimeError)
        set _layer3_built = True
    IF NOT _layer3_built:
      write python_code to test_model.py (legacy LLM path)

PHASE_E (evaluation, lines ~3424-3593)
  input:  test_model.py on disk, thesis in WORKING_PATH
  output: new_eval:dict {score:int, weakest_point:str, score_contract:dict, ...}
  calls:
    subprocess.run(test_cmd)  # → test_thesis.py → latest_eval_results.json
    run_global_gates(...)     # GP-086 hard/soft gates
    evaluate_candidate_selection(...)
  writes:
    eval_history.jsonl (append, GP-102): {iteration, score, weakest_point[:200], gate_verdicts, timestamp}
  exit_on_fail:
    not admissible → Runner R3 rejection → _pop_seed_queue, _restore_project_state, continue

PHASE_F (promotion_or_revert, lines ~3595-3935)
  input:  new_eval:dict, best_score:int
  branch:
    IF new_eval["score"] > best_score:
      _persist_best_candidate(new_content, score=...)
      _promote_latest_artifacts_to_champion()
      best_state = _capture_project_state(...)
      IF _comp_seed_injected: delete composition_seed.json
    ELSE:
      _pop_seed_queue(workspace_dir, _comp_seed_injected)
      IF enable_component_c: analyze_residual(...), run_divergence_sweep(...)
      _restore_project_state(best_state)
  exception:
    CalledProcessError → pop seed, restore state, sleep 5

PHASE_G1 (gp087_residual_driven_injection, lines ~4129-4200)
  gate:   rubric_data["enable_fit_primitive"] == True
  input:  new_eval (score_contract + top-level score), fit_result.json, composition_seed.json
  output: composition_seed.json with tail-correction seeds (source="gp087_residual_driven")
  calls:
    _gp087_propose_tail_correction_seeds(new_eval, workspace_dir, rubric_data, iteration_index, stagnation_count)
      → TWO firing modes:
          Mode 1 (gate): any deterministic_charter_gates result with "farther_tail" in name failed
          Mode 2 (contract-stagnation): rubric farther_tail_contract==True AND score<100 AND stagnation>=1
      → reads champion expression from fit_result.json
      → composes each tail-correction primitive (reciprocal, harmonic, etc.) with champion
  source-aware seed check (2026-04-19):
    → if composition_seed.json exists, reads "source" field of entries
    → if any entry has source="gp087_residual_driven": sets _gp087_injected=True, blocks Component D (seeds already queued)
    → if all entries are source="component_d_autonomous": GP-087 may overwrite
    → if seed file absent: GP-087 writes fresh
  skip_if: new_eval has no score_contract (crash path)
  DEPENDS_ON: fit_result.json (champion expression — guaranteed to be champion after revert via INV-4)
  INFO_BOUNDARY: only primitive names reach the seed queue, no farther-tail values
  NOTE: GP-087 reads gate failure from new_eval (in-memory, failed iteration) but expression
        from fit_result.json (on-disk, restored to champion). This split is intentional:
        the failure triggers the injection, but the base expression must be the champion's.

PHASE_G1.5 (gp103_additive_composite, lines ~4278-4342)
  gate:   rubric_data["enable_fit_primitive"] == True
          AND NOT _gp087_injected
          AND stagnation_count >= gp103_stagnation_threshold (default 1)
  input:  structural_memory.json (best_visible_max_abs_residual per family)
  output: composition_seed.json (source="gp103_additive_composite", 2 seeds A+B and B+A)
  calls:
    detect_additive_composite_opportunity(workspace_dir, gate_threshold, stagnation_count, residual_ratio=3.0)
      → effective_ratio = max(1.5, 3.0 - 0.5*stagnation_count)  # decays as search stalls
      → returns (family_a, family_b) with regime-separated visible residuals
    generate_additive_composite_seeds(family_a, family_b, ind_vars, iteration_index)
      → ch0_/ch1_ prefixed parameter namespaces (INV-6 safe)
  skip_if: _gp103_tried_pairs contains this (fp_a, fp_b) pair already (Bug 4 guard)
  DEPENDS_ON: PHASE_G1 (GP-087) must NOT have fired
  NOTE: H-GP103-4 (log_with_additive_offset primitive) feeds into structural_memory
        fingerprinting so the trigger correctly separates log(u)^p from log(1+b*u) families

PHASE_G2 (component_d_feynman_wall, lines ~4125-4230)
  gate:   rubric_data["enable_fit_primitive"] == True
          AND NOT _gp087_injected
          AND NOT _gp103_injected
  input:  structural_memory.json, stagnation_count, evidence_text
  output: composition_seed.json (seed queue for next iteration)
  calls:
    detect_feynman_wall(workspace_dir, stagnation_count, ...)
    run_composition_loop(workspace_dir, evidence, ...) → round_results
    grammar_filter: remove expressions matching FORBIDDEN_MATH regex
    sort: saturating-first (_asymptotic_sort_key)
    write top-K to composition_seed.json
  DEPENDS_ON: PHASE_G1 (GP-087) and PHASE_G1.5 (GP-103) must NOT have fired

PHASE_F.5 (gp105_mform_audit, lines ~4202-4220 after revert block)
  gate:   rubric_data["enable_mform_audit"] == True
          AND _mform_audits_this_run < 2
          AND (i + 1) <= 10
          AND stochastic: p = 0.15 + 0.65 * sigmoid(score - 85)
  input:  new_eval["score"], workspace_dir, PROJECT_DIR, RUNTIME
  output: workspace/mform_pending.json (if gap detected); _mform_audits_this_run += 1
  calls:
    maybe_fire_mform_audit(score, iteration, audits_so_far, rubric_data, workspace_dir, project_dir, runtime)
      → should_fire_audit() — stochastic trigger
      → run_general_office_audit(charter_path, thesis_path, general_office_model, runtime)
      → write_mform_pending(finding, workspace_dir) if gap_detected
  async_boundary: finding applied at START of next PHASE_A (not same iteration)
  fail_silent: wrapped in try/except; loop continues unaffected
  state_var: _mform_audits_this_run (initialized to 0 before main loop)
  DEPENDS_ON: PHASE_F complete (score known, promote/revert decided)
  NOTE: General Office model must differ from JUDGE_MODEL_ID and MUTATOR_MODEL_ID (Chandler separation)
        rubric_data["general_office_model"] is the flag; default "gpt4.1"

PHASE_A_PREFIX (gp105_apply_pending, lines ~2884-2894 at start of each iteration)
  gate:   workspace/mform_pending.json exists
  input:  rubric_data (in-memory), workspace_dir, RUBRICS_DIR, args.rubric
  output: rubric_data (updated: new dimension appended, existing rebalanced); rubric JSON on disk updated
  calls:
    apply_mform_pending(rubric_data, workspace_dir, RUBRICS_DIR, rubric_name)
      → load_mform_pending() → delete pending file
      → append criterion to rubric["criteria"]
      → append dimension at 15% weight, rebalance existing proportionally
      → write rubric JSON to disk (test_thesis.py subprocess sees updated rubric)
      → _append_goodhart_log() to rubrics/goodhart_log.jsonl
  fail_silent: returns original rubric_data on error
```

## INVARIANTS (violation → silent failure)

```
INV-1: python_code_exists_before_fit
  assert: python_code is not None when _prepare_mutation_candidate returns
  check:  validate_python_suite_candidate(python_code) raises ValueError if None
  DEPENDS_ON: PHASE_C.substitute_fitted_params(python_code, params)
  DEPENDS_ON: PHASE_A.alignment_pass must preserve ```python block
  trap:   alignment pass or seed injection that drops ```python block
  fix:    preserve _existing_py before alignment, re-inject after
  BUG (fixed 2026-04-20): Component D / H-GP103-5 seed injection path bypasses
    mutate_thesis entirely — no LLM is called, so no Python block was generated.
    new_content = thesis + fit_declaration only → validate_python_suite_candidate(None)
    → ValueError → R1 rejection every iteration H-GP103-5 fired.
    Layer 3 Mandatory (PHASE_D) never reached because PHASE_B rejected first.
    Fix: append loud-fail sentinel ```python stub to new_content at injection site.
    Layer 3 Mandatory overwrites stub with deterministic f() before test_model.py
    is written to disk. Stub never executes. Zero interface changes.
    Diagnosed via Munger/Karpathy inversion: "why does system think no Python needed?"
    Answer: it never asked the LLM — seed injection entirely bypasses PHASE_A LLM path.

INV-2: fit_declaration_survives_alignment
  assert: _seed_fd_block in _aligned (full JSON block comparison)
  check:  line ~3014, fallback to unaligned injection if violated
  DEPENDS_ON: PHASE_A.safe_mutate(alignment_prompt) output must contain verbatim JSON
  trap:   _seed_expr[:40] substring match (old brittle check, now fixed)

INV-3: layer3_exclusive
  assert: when enable_fit_primitive, LLM python NEVER used for def f()
  check:  _layer3_built[0] flag gates legacy path at line ~3397
  DEPENDS_ON: fit_primitive.py:FitDeclaration + FitSuccess → deterministic def f()
  trap:   _fit_decl or _fit_result being stale from prior iteration

INV-4: state_restoration_on_all_exits
  assert: every early-exit calls _pop_seed_queue() AND _restore_project_state()
  assert: revert is atomic across prose (thesis) AND math (fit_result.json)
  check:  grep for "continue" in main_loop — each must have both calls upstream
  check:  fit_result.json MUST be in _project_state_paths (added 2026-04-19, GP-087 Frankenstein fix)
  check:  fit_result.json MUST exist before snapshot (Snapshot Vacuum fix 2026-04-19): baseline fit
          runs before _capture_project_state so snapshot records content not None; otherwise revert
          on a wiped workspace deletes fit_result.json and GP-087 starves
  DEPENDS_ON: _capture_project_state(best_state) snapshot taken at promotion
  exits:  R1_exception(~3221), R1_mismatch(~3314), R3_rejection(~3590), subprocess_crash(~3982)
  trap:   score-based revert (PHASE_F ELSE) does NOT continue — fall-through to PHASE_G1
          is architecturally necessary so GP-087 can read the failed gate results from
          new_eval (in-memory) while reading the champion expression from fit_result.json (on disk, now restored)

INV-5: seed_queue_lifecycle
  write:  PHASE_G1 (GP-087 tail correction) OR PHASE_G2 (Component D composition)
  read:   PHASE_A (start of next iteration)
  pop:    on failure (INV-4 exits)
  clear:  on success (line ~3758-3762)
  DEPENDS_ON: PHASE_G1 takes priority — if GP-087 fires, PHASE_G2 is skipped
  DEPENDS_ON: composition_stagnation_threshold controls PHASE_G2 firing frequency
  trap:   threshold=1 → queue rewritten every iter → pop is futile

INV-6: parameter_namespace_uniqueness
  assert: all parameter_names in a composition seed are unique (no duplicates)
  check:  champion_params and correction_params use different prefixes
  DEPENDS_ON: Component D uses "d2_" prefix for depth-2 compositions
  DEPENDS_ON: GP-087 uses "tail_" prefix for tail corrections
  trap:   new composition source reuses an existing prefix → duplicate assignments
          in test_model.py → SciPy fits wrong model → silent wrong answer

INV-7: gp087_information_boundary
  assert: composition_seed entries from GP-087 contain ONLY primitive names and expressions
  assert: NO farther-tail residual values, region boundaries, or gate thresholds in seed
  check:  _gp087_propose_tail_correction_seeds emits {source, expression, parameter_names, correction_primitive}
  DEPENDS_ON: PHASE_E deterministic_charter_gates (pass/fail signal only, not values)
  DEPENDS_ON: fit_result.json (champion expression)
  trap:   future "enrichment" that adds residual values to the seed — would break mutator blindness
          grammar_filter is the defense (removes illegal candidates at write time)

INV-8: composite_seed_warm_start
  assert: H-GP103-5 / Component D composite seeds carry initial_guesses built from
          best_visible_fitted_params of each contributing family
  check:  generate_additive_composite_seeds (structural_memory.py) builds prefixed
          initial_guesses: {f"ch0_{k}": v for family_a} ∪ {f"ch1_{k}": v for family_b}
  check:  autoresearch_loop.py PHASE_A seed injection passes initial_guesses from
          _seed_data into _seed_fd_dict → _seed_fd_block → FitDeclaration
  check:  FitDeclaration.initial_guesses propagates to fit_parameters (line ~481, ~621)
          via p0 = [declaration.initial_guesses.get(name, 1.0) ...]
  DEPENDS_ON: update_structural_memory stores best_visible_fitted_params on first creation
              and on every best-residual update
  BUG (fixed 2026-04-20): H-GP103-5 composite seeds had no initial_guesses.
    SciPy cold-started all parameters at p0=1.0. For 8-12 parameters spanning 5 decades
    of log-time, the Jacobian is numerically singular at that start point. SciPy escaped
    by collapsing the second family amplitude to zero → identical max|res|=1.79947 every
    iteration. The fix was not overfitting (topology capacity unchanged) — it was
    numerical conditioning. Warm-starting places the optimizer at a location where the
    Jacobian has full rank. Multi-start (n_starts=3) still explores beyond the warm-start
    valley if a better solution exists.
    Diagnosis: Munger inversion + Karpathy pattern recognition (identical residual across
    10 iters = deterministic attractor, not stochastic noise). Gemini Pro confirmed:
    "By passing initial_guesses, you are not changing the capacity of the equation to
    overfit. You are simply giving the hiker a map to the correct valley."
  trap:   new composite source that omits initial_guesses → silent optimization collapse
          → judge correctly penalizes "zero gain from added parameters" → false topology rejection
  trap:   prefix collision (ch0_ vs ch1_) if a future source uses same family twice
```

## EDIT LOOKUP: "I want to change X" → "read Y first"

```
change: seed injection logic
  read:  PHASE_A branch (2900-3053), INV-1, INV-2, INV-5
  also:  _pop_seed_queue (361-384), PHASE_G (3986-4122)

change: alignment pass (GP-100)
  read:  PHASE_A epistemic_alignment branch (2960-3025), INV-1, INV-2
  also:  _prepare_mutation_candidate (1395-1440), safe_mutate (1499-1540)

change: fit primitive (GP-035)
  read:  PHASE_C (3070-3175), PHASE_D (3325-3420), INV-3
  also:  fit_primitive.py, structural_memory.py

change: test_model.py generation
  read:  PHASE_D (3325-3420), INV-3
  also:  PHASE_B validate_python_suite_candidate, PHASE_C substitute_fitted_params

change: evaluation/scoring
  read:  PHASE_E (3424-3593)
  also:  test_thesis.py, global_gates.py, runner_selection.py

change: latest_evidence_gaps.json write behavior
  read:  _refresh_latest_evidence_gaps_from_eval (added 2026-04-21)
  note:  called at both init eval and each iteration eval, after _print_latest_artifact_status
  note:  returns early if no evidence_gaps in eval — safe for science track
  note:  evidence-fetch reads LATEST_EVIDENCE_GAPS_PATH; this fix keeps it current per iteration

change: champion promotion
  read:  PHASE_F (3595-3935), _persist_best_candidate (776-820)
  also:  champion_artifacts.py, _promote_latest_artifacts_to_champion (925-958)

change: GP-087 residual-driven injection
  read:  PHASE_G1 (~4092-4120), INV-5, INV-6
  also:  _gp087_propose_tail_correction_seeds (~988-1060), deterministic_charter_gates.py
  note:  information boundary — seed must NOT carry farther-tail values

change: Component D / composition
  read:  PHASE_G2 (~4125-4230), INV-5
  also:  topology_synthesizer.py, detect_feynman_wall, run_composition_loop
  note:  PHASE_G1 (GP-087) takes priority — G2 skips if G1 fired
  note:  PHASE_G1.5 (H-GP103-5) also takes priority — G2 skips if G1.5 fired

change: H-GP103-5 additive composite generator
  read:  PHASE_G1.5 (~4278-4342), structural_memory.py (detect_additive_composite_opportunity,
         generate_additive_composite_seeds), INV-5, INV-6
  also:  _gp103_tried_pairs (initialized at stagnation_count line ~2778 in init block)
  note:  requires stagnation_count >= gp103_stagnation_threshold (rubric flag, default 1)
  note:  pair-fingerprint guard (_gp103_tried_pairs) prevents infinite re-injection of same pair

change: H-GP103-4 structural memory granularity
  read:  PRIMITIVE_LABELS, _PrimitiveExtractor.visit_Call in structural_memory.py
  also:  PHASE_C update_structural_memory (~3307)
  note:  log_with_additive_offset now distinct from log in GP-048 primitive vocabulary

change: failure recovery / early exit
  read:  INV-4, all exit points (3221, 3314, 3590, 3982)
  also:  _pop_seed_queue (361-384), _restore_project_state (839-845)
  note:  fit_result.json is in _project_state_paths — any new stateful artifact must be added there too

change: mutator prompt
  read:  prompt_assembly region (1540-2400), def mutate_thesis
  also:  rubric flags table below (each flag injects context)

change: adding a new rubric flag
  read:  RUBRIC_FLAGS table, PHASE_A context assembly (2760-2900)
  also:  rubric JSON schema (check existing rubrics for format)
```

## RUBRIC FLAGS → CODE PATH SWITCH

```
flag: enable_fit_primitive        → gates: PHASE_C, PHASE_D, PHASE_G
flag: epistemic_alignment         → gates: PHASE_A alignment branch (seed path only)
flag: enable_component_c          → gates: PHASE_F residual analysis, GP-076 sweep
flag: composition_stagnation_threshold → controls: PHASE_G firing frequency
flag: fit_expression_grammar      → controls: PHASE_G grammar filter, PHASE_D helpers, PHASE_C _build_model_callable path (values: eml_only|math_exp_only|math_exp_trig|py_exec|omit)
flag: fit_score_mode              → controls: PHASE_C fit_parameters score_mode arg
flag: holdout_hard_gate           → controls: test_thesis.py scoring (external)
flag: cold_residual_successor_mode → controls: PHASE_A context assembly
flag: gp048_telemetry             → controls: PHASE_C telemetry write
flag: gp048_stagnation_injection_mode → controls: PHASE_A cohort context (stagnation≥3)
flag: gp048_farther_tail_veto_mode → controls: PHASE_A veto context
flag: farther_tail_contract        → controls: PHASE_G1 contract-stagnation mode (fires GP-087 when score<100 and stagnating)
flag: asymptotic_claim            → controls: test_thesis.py (external)
flag: farther_tail_contract       → controls: test_thesis.py (external)
flag: fit_required_dimensionality → controls: PHASE_C dimensionality check
flag: fit_required_vars           → controls: PHASE_C, PHASE_G var names
```

## RUBRIC FLAGS ADDED 2026-04-24 (GP-143 / GP-149)

```
flag: fit_score_mode: "dynamical_lattice"  → controls: PHASE_C dispatch to
    src/ztare/fit/continuous_chaotic/run_pipeline (GP-143 kernel promotion).
    Bypasses SciPy curve_fit. Provides autocorrelation-radius weak-form SINDy
    + Lyapunov-ergodic + Wasserstein-persistence gate composition. Rubric
    block `dynamical_lattice` carries method_a_variant, method_a_params,
    noise_envelope_sigma OR wasserstein_noise_floor, wasserstein_admit_factor,
    observation_T. Wiring status: module shipped 2026-04-24; PHASE_C dispatch
    insertion point identified at ~line 3070 but NOT YET applied (operator
    review pending per INV-10). Spec at
    research_areas/private/specs/active/GP-143_continuous_chaotic_kernel_integration_spec.md

flag: inject_antipattern_catalog: "off" | "hardkill" | "ceilingbreaker" | "both" | true | false
    (GP-149 I-1 + 2026-04-24 cross-LLM split)  → controls: PHASE_A
    grounding_payload assembly at ~line 1976.
      "off" / false  → no injection (default)
      "hardkill"     → inject ONLY Part 1 (cross-judge-validated structural blockers).
                       Safe default for any Newton-mode project.
      "ceilingbreaker" → inject ONLY Part 2 (ceiling-breakers). LLM-classifier-
                       disputed per 2026-04-24 cross-provider audit (48% three-way
                       agreement, κ≈0.57). Autoresearch EMITS WARNING when this
                       mode is used. Experimental.
      "both" / true  → inject both parts. Emits same warning as "ceilingbreaker".
    Catalog split by ## PART 1 / ## PART 2 markers in the canonical doc.

flag: min_distinct_weakest_classes_before_stagnation: int (GP-149 I-2)
    → controls: OBSERVE-MODE telemetry around pivot state resolution
    at ~line 3399. Currently observe-only: logs when pivot would fire but
    threshold not met. Default 0 (off). Cap ≤ 8 enforced by discipline note
    in seam.

flag: pivot_ineffective_class_mode: "off" | "observe" | "suppress"
    (GP-149 I-3)  → controls: same insertion point as I-2. Classifies the
    current weakest-point via src/ztare/validator/weakest_link_classifier.py;
    if class ∈ PIVOT_INEFFECTIVE_CLASSES, logs or records
    pivot_skipped_gp149_i3 loop event. Default off.

flag: enable_lean_proof: bool (GP-122; pre-existing, documented here for
    completeness)  → controls: post-champion Lean REPL invocation at
    ~line 3195. Fires when res['score'] >= 70 AND flag is true. Calls
    src/ztare/formal/lean_repl.prove_from_compression. Separate from the
    GP-143 / GP-149 flags.

flag: stagnation_trigger_mode: "score" | "new_class" (Task 12 / Gemini
    Inversion #3, added 2026-04-24)  → controls: stagnation accounting in
    src/ztare/validator/core/information_yield.py. "score" is legacy default.
    "new_class" resets stagnant_window when iteration's weakest-link class
    (classify_weakest_point) has not been seen earlier in the session. Works
    with gp103_stagnation_threshold and underidentified_after as belt-and-
    suspenders. Default "score" preserves legacy behavior. Source motivation:
    GP-148 champion persistence profile (≥85-score groups traverse ~10 classes
    over ~28 iters); score-only stagnation prematurely kills class-cycling.

flag: enable_fom: bool (GP-FOM post-gp150, added 2026-04-24)  → controls:
    post-champion fractional-operator diagnostic at ~line 3355 (immediately
    after GP-143 dispatch). Fires when champion score >= 70 AND flag true.
    Computes compute_fractional_derivative(chi_[-1,1], dx, alpha) and the
    fourth-moment tail signature of the result. Writes workspace/fom_diagnostic.json.
    OBSERVE-mode by default; LIVE mode requires companion flag
    fom_gate_stack_validated=true (GP-144 discipline: needs G1 full + GP-146
    pass). Rubric block `fom` carries alpha (default 1.5), n_grid (1024),
    length (2π). Kernel registration: METHOD_C_VARIANTS in
    src/ztare/fit/continuous_chaotic/__init__.py.

flag: fom_gate_stack_validated: bool (GP-FOM gate-cleared sentinel)  →
    controls: mode of GP-FOM dispatch (observe vs live). Operator sets
    this only after G1 continuum_limit_gate full implementation and GP-146
    Arnold cat map self-validation substrate have both passed. Default
    false. Acts as a GP-144 discipline gate preventing premature live
    FOM use.

flag: enable_framer: bool (GP-152 v2.0, 2026-04-24)
  fires:    line ~4213 pre fit_parameters
  default:  false
  preconds: dim∈{None,1} ∧ |independent_vars|==1 ∧ N≥80
  flow:     parse_evidence_for_fitting → (x,y) → framer.frame()
            frame: scope_check → Σ×Σ enum → sym+dim filter → B&B MDL_v2 (raw-coord BIC) → post-frame heterosc check
  output:   workspace/framing_report.json
  side_fx:  ∅ (observe-mode)
  promote:  needs framer_live_mode flag + spec §7 step 6 (A/B GP-148 archive)
  spec:     research_areas/private/specs/active/GP-152_framer_architecture_spec_v2.md
  impl:     src/ztare/framer/, src/ztare/framer_gates/
  backtest: scripts/framer/backtest_framer_mdl_v2_vs_v1.py (0 bits drift)

flag: structural_blocker_enforcement: "prompt"|"gate"|"both" (Task 22 / GP-151, 2026-04-24)
  modes:
    prompt: default; only inject_antipattern_catalog (LLM taxonomy)
    gate:   post-champion @line~3279: G-CIRC (DAG cycle on champion_probability_dag.json) + G-FALSIFY (test_model.py asserts ∧ DAG watch_signal ∧ thesis rival/discriminator); hardkill Part 1 SUPPRESSED; out → workspace/structural_blocker_gates_latest.json
    both:   prompt+gate (transition belt-and-suspenders)
  modules: src/ztare/gates/circularity_gate.py (6/6), src/ztare/gates/falsifiability_gate.py (8/8)
  cleared_by: GP-146 cert (2026-04-24, P0=92, plants 7/7)
```

## GP-143 CONTINUOUS-CHAOTIC KERNEL (2026-04-24)

```
region: src/ztare/fit/continuous_chaotic/
  module: __init__.py        | exports run_pipeline, SUBSTRATE_CLASS,
                               METHOD_A_VARIANTS
  module: generator.py       | Method A: autocorrelation-radius multi-grid
                               weak-form SINDy; entry point
                               run_weak_form_pipeline(trajectory, dt,
                               rubric_params, initial_state).
  module: autocorrelation.py | τ_decorr from autocorrelation 1/e crossing.
  module: lyapunov.py        | Lyapunov spectrum + Kaplan-Yorke +
                               ergodic_divergence_filter.
  module: certifier.py       | (NOT YET CREATED; currently inline in
                               generator.py) — to be split when certifier
                               paths evolve beyond current set.

promoted-from: projects/lorenz_bridge_test/apparatus_candidate/apparatus_v5_correct.py
champion: gp140 iter-10 CW-PT thesis (score 87 under o3 aggressive judge)
gated: by rubric flag fit_score_mode: "dynamical_lattice"
dispatch: POST-CHAMPION (not pre-fit). Lives after the GP-122 Lean block
  at autoresearch_loop.py ~line 3247. Fires when:
    res["score"] >= 70 AND rubric_data["fit_score_mode"] == "dynamical_lattice"
  Discipline: additive hook. Does NOT replace fit_parameters (which is
  gated by enable_fit_primitive; dynamical_lattice rubrics should set
  enable_fit_primitive=false). Legacy scalar path unchanged.
  Writes: workspace/continuous_chaotic_result.json (candidate count +
  certified count + champion coefficient matrix) for downstream G2 / Lean.
  Wired 2026-04-24 per GP-143 spec §6.
```

## GP-148 / GP-149 MINING INFRASTRUCTURE (2026-04-24)

```
region: scripts/mine_*.py
  mine_trajectories.py              | Stage 1 extractor → analytics/trajectory_archive.jsonl
  mine_trajectories_enrich.py       | Stage 1.5 enrichment → analytics/trajectory_archive_enriched.jsonl
  mine_weakest_link_taxonomy.py     | Regex-based 15-class taxonomy
  mine_weakest_link_llm_classify.py | LLM reclass on `other_unclustered`
  mine_pivot_effectiveness.py       | Per-cluster pivot Δ metrics
  mine_climb_triggers.py            | Δscore ≥+20 events by class
  mine_lollapalooza_hypothesis.py   | Popper P1 (high vs mid structural-features)
  mine_score_ceilings.py            | Wall-constraint identification
  mine_champion_trajectory_sequence.py | Class transition matrix for champions

region: src/ztare/validator/weakest_link_classifier.py
  runtime regex classifier used by GP-149 I-2 / I-3 observability hooks.
  9/9 smoke-test passing. Stdlib-only.

region: docs/concepts/anti_pattern_catalog.md
  canonical two-part anti-pattern catalog (structural-blocker /
  ceiling-breaker) injected by I-1 when rubric flag on.
```

## EXIT TAXONOMY

```
exit: R1_exception      line: ~3566  cause: _prepare_mutation_candidate raises
exit: R1_mismatch       line: ~3641  cause: mutation_declaration scope/claim check
exit: R3_rejection      line: ~3941  cause: candidate not admissible
exit: subprocess_crash  line: ~4341  cause: test_thesis.py crashes
exit: UNDERIDENTIFIED   line: ~3356  cause: pending_loop_action == UNDERIDENTIFIED → break
exit: budget_exhausted  line: ~4251  cause: default `run_exit_reason = "budget_exhausted"` set before main_loop; only changed if a structured exit fires
exit: GP133_R4_gate     line: ~3711-3725  cause: rubric-preflight refuses: py_exec missing auth/budget, or rubric_mode='newton' without Generative Yield dimension, or unknown rubric_mode value. SystemExit BEFORE main loop; no recovery.
recovery: all except UNDERIDENTIFIED/budget/GP133_R4_gate → _pop_seed_queue + _restore_project_state + continue
```

## KEY FUNCTIONS (grep targets)

```
func: _pop_seed_queue              sig: (workspace_dir:Path, injected:bool) → None
func: _prepare_mutation_candidate  sig: (raw_text, current_thesis, current_test_model, falsification_mode) → (decl, validation, thesis, python, full)
func: safe_mutate                  sig: (prompt, config=None, model_id=MUTATOR_MODEL_ID) → str
func: mutate_thesis                sig: (current_content, current_test_model, weakest_point, evidence, persona, stagnation_count, ...) → str
func: get_pivot_thresholds         IMPORTED FROM src/ztare/validator/pivot_heuristics.py
                                   sig: (is_v4_project:bool, rubric_mode:str|None) → (pivot_threshold:int, emergency_threshold:int|None)
func: resolve_stagnation_pivot_state IMPORTED FROM src/ztare/validator/pivot_heuristics.py
                                   sig: (is_v4_project:bool, falsification_mode:str|None, stagnation_count:int, rubric_mode:str|None) → PivotState
func: _persist_best_candidate      sig: (thesis_content, *, score, weakest_point, iteration, run_id, ...) → str
func: _promote_latest_artifacts_to_champion  sig: () → dict
func: _restore_project_state       sig: (snapshot:dict) → None
func: _capture_project_state       sig: (paths:tuple) → dict
func: _saved_best_comparison_anchor sig: (current_eval:dict) → dict
func: _gp087_propose_tail_correction_seeds  sig: (eval_results:dict, workspace_dir:Path, rubric_data:dict, iteration_index:int, stagnation_count:int=0) → list[dict]|None
func: _finalize_run_telemetry_once sig: () → None
func: _refresh_latest_evidence_gaps_from_eval  sig: (evaluation:dict, artifact_role:str) → None  # writes LATEST_EVIDENCE_GAPS_PATH; no-op if no gaps
```

## STATE VARIABLES (main loop scope)

```
var: best_score                 type: int       init: res["score"]
var: best_weakest_point         type: str       init: res["weakest_point"]
var: current_target_weakest_point type: str     init: best_weakest_point
var: best_state                 type: dict      init: _capture_project_state(...)  # includes fit_result.json since 2026-04-19
var: stagnation_count           type: int       init: 0
  note: prompt escalation / loop control / event logging thresholds are derived
        from `resolve_stagnation_pivot_state()`:
        - default / kepler / calibration: 3 → stagnation pivot, 4 → emergency
        - newton: 2 → stagnation pivot, 3 → emergency
        - V4: 3 → bounded override, no generic emergency stage
var: _gp103_tried_pairs         type: set[tuple[str,str]]  init: set()  # H-GP103-5 Bug 4 guard
var: _mform_audits_this_run     type: int       init: 0  # GP-105 M-Form audit counter (max 2/run)
var: last_failure_reason        type: str|None  init: None
var: pending_loop_action        type: LoopControlAction  init: CONTINUE
var: iteration_history          type: list[IterationSignal]  init: []
var: _comp_seed_injected        type: bool      init: False (per iteration)
var: current_mutator            type: str       init: MUTATOR_MODEL_ID (may escalate to DIRECTOR)
var: workspace_dir              type: Path      init: PROJECT_DIR / "workspace"
```

## BUG FIX (2026-04-21): latest_evidence_gaps.json never written by loop

**Bug:** `LATEST_EVIDENCE_GAPS_PATH` (`workspace/latest_evidence_gaps.json`) was declared and
read by `_promote_latest_artifacts_to_champion` but never written by the loop itself.
The log message "latest_evidence_gaps updated" in `_print_latest_artifact_status` was a lie —
no write existed behind it. The file was only written by `rubric-review` (manually triggered).
Consequence: `make evidence-fetch` always saw stale gaps from the last manual rubric-review,
never the gaps the judge identified during iterations.

**Fix:** Added `_refresh_latest_evidence_gaps_from_eval(evaluation, artifact_role)` called
immediately after `_print_latest_artifact_status` at both eval sites:
- Init eval (line ~2724, after initial thesis evaluation)
- Iteration loop (line ~3754, after each iteration evaluation)

**Regression safety:** Function returns early if `evaluation.get("evidence_gaps")` is empty
or None — no-op for science track projects where evidence_gaps is typically absent.
Uses `(evaluation.get("score_contract") or {})` for None-safe score_contract access.
Uses already-imported `time` module, no new imports.

**Edit lookup entry added below.**

---

## GP-088 ARCHITECTURAL CHANGES (2026-04-20)

### PHASE_A_PREFIX: GP-105 M-Form apply pending
Before main mutation: `apply_mform_pending()` loads `mform_pending.json` and
appends adversarial criterion to rubric at 15% weight. Qualitative projects only.

### PHASE_F.5: GP-105 M-Form audit fire
After promote/revert: `maybe_fire_mform_audit()` fires stochastically on high
scores. Cross-family model. Writes `mform_pending.json` for next iteration.
Max 2 audits per run. Qualitative projects only (enable_mform_audit flag).

### Signal construction: verified_axioms_added gate
`verified_axioms_added = len(axioms) if _candidate_improved else 0` — reverted
iterations get axioms=0 to prevent qualitative thesis claims from suppressing
stagnation (the seattle stagnation-stuck-at-0 bug).

### Component D seed selection: BIC sort + topology diversification
1. **BIC sort key**: `_asymptotic_sort_key` uses BIC (n*log(SSE/n) + k*log(n))
   instead of raw max_res. Penalizes overparameterized forms.
2. **Topology diversification**: Seeds grouped by structural class (log_polynomial,
   power_law, exponential, exponential_rational, rational, log_simple, other).
   Top seed from each class selected, remaining slots filled with global best.
   Prevents monoculture (GP-088: all-log queue crowded out power-law candidates).
3. **k_max parsimony filter REJECTED**: would have killed DFDO 12-param champion.
   The holdout gate is the correct filter, not parameter count.

### PHASE_F.7: GP-103 in-loop compression (after champion promotion)
After champion is promoted AND seed queue cleared: if `enable_fit_primitive` is True
AND champion has k >= 3 params, runs `compress_champion()` to try all low-k templates.
No hardcoded threshold — BIC decides whether compression improves the champion.
If a simpler form passes all gates, installs it to test_model.py. Does NOT modify
thesis.md (mutator owns thesis) or best_score (conservative — compressed form scores
at least as high). Next iteration's `_capture_project_state` snapshots the compressed
form. Fail-silent: compression errors do not affect the loop.

Interaction points:
- Reads: test_model.py (to count champion params), evidence.txt (for fitting),
  gate_harness.py (for gate verification)
- Writes: test_model.py (compressed form, only if improvement found)
- Does NOT write: thesis.md, best_score, stagnation_count, iteration_history
- Sequencing: fires AFTER _promote_latest_artifacts_to_champion + seed queue clear,
  BEFORE the else/revert branch. Next iteration captures the new state.

### fit_primitive.py: Exponent grid refinement
After main curve_fit: `detect_power_exponent_params()` finds `var**param` via AST.
`_refine_exponent_grid()` tries d in {0.25, 0.33, 0.5, 0.67, 1.0, 1.5, 2.0},
selects by BIC. Prevents finite-window exponent overfitting (GP-088: d=0.562→0.5).

### information_yield.py: Committee-rotation throttle
`_is_reframing_with_new_committee()` credit fires at most once between score
improvements. `_collect_flat_tail()` uses history-aware grace boundary. Prevents
--dynamic mode committee rotation from suppressing stagnation.

### information_yield.py: Class-novelty stagnation decoupling (Task 12, added 2026-04-24)
Rubric flag `stagnation_trigger_mode`: `"score"` (legacy, default) | `"new_class"`
(Gemini Inversion #3). When `"new_class"`, a weakest-link class not seen earlier
in the session counts as novelty — resets `stagnant_window` and suppresses
PIVOT/REFRESH/UNDERIDENTIFIED until the same class repeats.
- `IterationSignal.weakest_class` — populated by `_populate_weakest_class()` in
  `_evaluate_post_eval_loop_control` via `weakest_link_classifier.classify_weakest_point`
  (runtime regex, cheap, returns `""` on no match).
- `evaluate_information_yield(..., class_novelty_mode=bool)` — new kwarg. False
  preserves legacy exactly. True adds a grace-boundary branch (same short-circuit
  shape as `has_novelty()`) checking `latest.weakest_class not in prior_classes`.
- `_collect_flat_tail(..., class_novelty_mode=bool)` — same grace-boundary applied
  during flat-tail walk, using forward-indexed `history[:hist_idx]` lookup.
- Source motivation: GP-148 champion persistence profile shows ≥85-score groups
  traverse ~10 distinct weakest-link classes over ~28 iters. Score-only stagnation
  prematurely kills class-cycling behavior. gp150 run-1 died at iter 8 score 78
  with stagnation_count 4 — multiple distinct classes had surfaced.
- Wiring: all four `evaluate_information_yield` callsites in autoresearch_loop.py
  now pass `class_novelty_mode=(_stagnation_trigger_mode() == "new_class")`.
- Default preserves legacy: flag must be explicitly set in rubric. Existing projects
  unaffected.

### evidence fetch: OpenAI web search routing
`fetch_via_web_search(query, model)` routes to OpenAI when model starts with "gpt".
Falls back to Anthropic web_search tool otherwise.

### Import invariant (added 2026-04-21)
Any new code in the Component D seed selection block (~lines 4550-4695) that uses
stdlib functions (math.log, math.sqrt, etc.) MUST verify the module is imported at
file level. The BIC sort key added 2026-04-20 used `math.log` without `import math`
→ NameError killed topology diversification for the OEIS A000607 run (14 iterations).
Fixed: `import math` added to top-level imports.

### PHASE_F.7: GP-103 in-loop compression (added 2026-04-20, dynamic threshold 2026-04-21)
After champion promotion: if `enable_fit_primitive` AND champion k >= 3, runs
`compress_champion()`. If simpler form passes gates with better BIC, installs to
test_model.py. Dynamic threshold (k>=3, BIC decides) — no hardcoded minimum.
Does NOT modify thesis.md or best_score. Fail-silent.

### Grammar tiers (added 2026-04-21, py_exec added 2026-04-23)
- `math_exp_only`: exp, log, sqrt, arithmetic. Default.
- `math_exp_trig`: adds sin, cos. For substrates where periodicity not excluded.
- `eml_only`: only `eml(x,y) = exp(x) - ln(y)`. For gp023 EML-sandbox experiments.
- `py_exec`: full Python expression syntax — list comprehensions, generators, `range`,
  `sum`, `all`, `any`, boolean operators. For discrete number-theoretic substrates where
  the correct law requires algorithmic iteration (e.g., prime factorization). Bypasses
  AST whitelist validation; eval still sandboxed (no `__builtins__`, explicit allowlist).
  Activated by `fit_expression_grammar: "py_exec"` in rubric + `fit_score_mode: "discrete_exact"`.
  Implemented in `fit_primitive.py:_build_model_callable` (lines ~270-320).
  Lookup-table gaming still blocked: holdout gate + Parsimony judge penalty.
Grammar filter in Component D seed selection handles both: math_exp_only forbids
all trig; math_exp_trig forbids only hyperbolic (sinh/cosh/tanh).
py_exec bypasses Component D grammar filter entirely (no template expansion needed).

### Stage 2 compositional compression (added 2026-04-21, Stage 1 expanded 2026-04-21)
`compress_champion.py` has two stages:
- Stage 1: 26 additive templates (sqrt, log, power, exp, 1/n combinations)
  - Expanded from 22 to 26 (2026-04-21): added `loglog_affine`, `log_power_free`,
    `loglog_reciprocal`, `log_power_reciprocal`. See `compress_champion.py` lines 71-77.
- Stage 2: 13 depth-1 nested compositions (sqrt(n/log(n)), sqrt(n*log(n)), etc.)
Stage 2 only activates when Stage 1 returns 0 gate-passing forms (UNDERIDENTIFIED).
Same tight gates for both stages. Backtest: 9 substrates, 0 false positives.
A000607 (prime partitions): Stage 2 found sqrt(n/log(n))+log(n)+c at tight gates.

### evidence fetch: OpenAI routing (added 2026-04-20)
`fetch_via_web_search(query, model)` routes to OpenAI when model starts with "gpt".

### Makefile targets (added 2026-04-20/21, updated 2026-04-21)
- `make compress PROJECT=X`: runs GP-103 template enumeration compression
- `make prove PROJECT=X`: compiles gate results to Lean 4, copies to ztare_proofs/
- `make discover PROJECT=X RUBRIC=X ITERS=N ...`: full pipeline (loop → compress → margin_of_safety → prove)
  - Phase 2.5 call at Makefile line ~217: `python -m src.ztare.fit.margin_of_safety --project $(PROJECT)`

### Pipeline flow (updated 2026-04-22)
```
Phase 1   (autoresearch_loop)     LLM proposes topology, SciPy fits params
  ↓
Phase 2   (compress_champion)     Template enumeration strips to minimal form
  ↓                               Stage 1: 28 additive | Stage 2: 13 compositional
Phase 2.5 (margin_of_safety)      5 tests + closed-loop remediation
  ↓                               Split-half | Drift | Grammar probe | Autocorrelation | Extrapolation
  ↓ if PERSIST:
Phase 2.6 (diagnosis_feedback)    GP-113: injects diagnosis into derived_constraints
  ↓                               LLM reads constraint on next Phase 1b iteration
Phase 2.7 (post_underidentified)  Strategy A: log gap for cross-substrate accumulation
  ↓                               Strategy B: observable rotation (log, 1/z, diff)
  ↓                               Strategy C: scale expansion check
  ↓                               Strategy D: regime combinator
  ↓                               Strategy E: ROTATION FEEDBACK LOOP (GP-121 Fix 1)
  ↓                                 if rotation res < gate → write rotated evidence
  ↓                                 → recompress on rotated data → compose with inverse
  ↓                                 → validate on ORIGINAL holdout
Phase 3   (lean_compiler)         Gate results → Lean 4 #eval stubs + PSLQ conjectures
```

### FEEDBACK EDGES (GP-121/123, 2026-04-22)

The pipeline was originally a DAG (no feedback). These edges close the loops:

```
GP-113: judge diagnosis → derived_constraints → mutator prompt
  (failure feedback: what went wrong feeds into next iteration)

GP-115: compression residuals → grammar suggestions → constraint ledger
  (grammar expansion: what pattern the residuals show feeds into LLM mutator)
  GP-115 diagnostics logged to workspace/gp115_diagnostics.json

GP-119: champion thesis → Inverter agent → falsification tests → constraint ledger
  (post-champion audit: Munger inversion + Popper tests)
  Inverter reads probability DAG to target weakest node (GP-123)

GP-123: probability DAG → mutator prompt (dag_steering_context)
  (DAG steering: weakest 3 nodes injected into mutator prompt)
  Also: DAG → Inverter targeting (weakest node priority)

GP-121 Fix 1: observable rotation → rotated evidence → recompress → compose
  (rotation feedback: when 1/z or log(z) compresses, auto-close the loop)

GP-122: champion thesis → lean_compiler → Lean stub → lean_repl → proof attempt
  (post-champion Lean proof: fires when score >= 70 AND rubric.enable_lean_proof)
  (if Lean typechecks → machine-verified proof)
```

### k < n/3 CONSTRAINT (GP-121 Fix 2, 2026-04-22)

compress_champion.py line ~234: for datasets < 18 points, k_max = n_pts // 3
(no floor). Prevents Von Neumann elephant on small cross-entity substrates.

Key files:
- `src/ztare/fit/compress_champion.py` — Phase 2 (28+13 = 41 templates, k < n/3 guard)
- `src/ztare/fit/margin_of_safety.py` — Phase 2.5 (GP-112, GP-115 logging + constraint wiring)
- `src/ztare/fit/diagnosis_feedback.py` — Phase 2.6 (GP-113)
- `src/ztare/fit/post_underidentified.py` — Phase 2.7 (rotation + gap + ROTATION FEEDBACK)
- `src/ztare/fit/residual_grammar_expander.py` — GP-115 Layer 1 (wired into Phase 2.5)
- `src/ztare/fit/validity_horizon.py` — standalone scale-sweep diagnostic
- `src/ztare/fit/statistical_fingerprint.py` — GP-110 (wired into Phase 2 Stage 3b)
- `src/ztare/validator/inverter_agent.py` — GP-119 (post-champion, DAG-targeted)
- `src/ztare/formal/lean_compiler.py` — Phase 3

### Bug history
- Missing `import math` → Component D BIC sort crashes, topology diversification dead (OEIS A000607, 2026-04-21)
- verified_axioms_added from reverted iterations → stagnation stuck at 0 (qualitative)
- committee_digest rotation in --dynamic mode → stagnation stuck at 0
- Component D seed queue monoculture → log-land absorbing state (GP-088)
- Exponent overfitting d=0.562 vs d=0.5 → farther-tail gate failure (GP-088)

---

## GP-112 MARGIN OF SAFETY (2026-04-21)

### Phase 2.5: margin_of_safety.py
New file: `src/ztare/fit/margin_of_safety.py`. Wired into `make discover` between
Phase 2 (compress_champion) and Phase 3 (lean_compiler). Makefile line ~217 calls
`python -m src.ztare.fit.margin_of_safety --project $(PROJECT)`.

Dependencies: numpy, scipy, compress_champion output.
Output: `workspace/margin_of_safety.json`.

**5 margin tests:**
1. Split-half stability
2. Coefficient drift
3. Grammar completeness probe
4. Residual autocorrelation
5. Extrapolation stress

**Closed-loop remediation:** If any flag detected, exhausts a bounded enumeration
of grammar extensions (curated + grammar-derived) with BIC penalty per candidate.

**Residual characterization:** If PERSIST_GRAMMAR_EXHAUSTED, runs spectral
decomposition and multiplicative model trial on residuals.

### Neural scaling substrate (monotone_decay_01)
Set up as `monotone_decay_01` (renamed from `neural_scaling_01` per sentinel).
GP-072 7-phase sealed. Evidence: 164 real Pythia W&B data points (2 model sizes,
98 visible / 33 holdout / 33 farther-tail).

---

## GP-156 v2 AMENDMENTS (2026-04-25, post-00:26 session)

### Line drift — earlier map note said ~L4587; current is L4581

```
region: fit_primitive_features_dispatch  lines: 5387-5640  entry: print(f"🧮 ─── GP-156 fit_primitive_features dispatch ───")
  note: SIBLING block to fit_primitive 1D engine — NOT nested under
        rubric.enable_fit_primitive (Bug #11 fix shipped 2026-04-25).
        Gated only by rubric.enable_fit_primitive_features.
        Writes workspace/fit_features_result.json with full BIC telemetry:
        bic, sigma_sq, n_fit_rows, k_params (per GP-152 framer spec v2.0).
        GP-164 (2026-04-25 night) — wMDL/weighted-χ² mode: rubric flags
        fit_weighted_residuals (bool) and fit_sigma_key (str) thread
        through to fit_features. When weighted=True: objective uses
        ((y_pred-y_obs)/σ_i)², BIC = χ² + K·log(N), and the framer
        dispatch site auto-mirrors framer_sigma_provided=True (so the
        framer's heteroscedasticity guard does not fire on signal the
        weighted solver already models). σ=1 fallback per-row when key
        missing. Backward-compat: weighted=False unchanged.
```

### What shipped this session (24 bugs across 8 files)

| Region                        | Change                                                       |
|---|---|
| `fit_primitive_features.py`   | Bug #13 AST allows params[...] subscripts                    |
| `fit_primitive_features.py`   | Bug #19 row[...] alias rejected with rename hint             |
| `fit_primitive_features.py`   | Bug #20 math.X / np.X attribute calls allowed               |
| `fit_primitive_features.py`   | Bug #22 float/int/bool coercion in AST + safe namespace      |
| `fit_primitive_features.py`   | Bug #24 statement-block PARAMETRIC_FORM → ternary diagnostic |
| `fit_primitive_features.py`   | Bug #25 multi-line PARAMETRIC_FORM auto-paren-wrap retry     |
| `fit_primitive_features.py`   | substitute_fitted_model_params reverted to regex-only        |
| `fit_primitive_features.py`   | BIC field on FeatureFitResult (per GP-152 v2.0)              |
| `fit_primitive_features.py`   | k_law_max default 5→8 + BIC-justified budget                 |
| `fit_primitive_features.py`   | R8 sorted-by-id rows in load_visible_from_substrate          |
| `mutation_suite_guard.py`     | Bug #14 _ast_check_params_contract                           |
| `mutation_suite_guard.py`     | require_parametric_form param + force-opt-in (Bug #19 sequel)|
| `validator/test_thesis.py`    | Bug #15 APPARATUS CONTRACT section in judge prompt           |
| `validator/test_thesis.py`    | Bug #21 hard-gate respects near_miss + GP-156 schema parser  |
| `autoresearch_loop.py`        | Bug #11 sibling-block wire-in (outdented 110 lines)          |
| `autoresearch_loop.py`        | BIC printed in 🧮 banner + JSON                              |
| `autoresearch_loop.py`        | Bug #23 canonical assertion no alphabetical-sort req         |
| `autoresearch_loop.py`        | require_parametric_form plumbed at L1748                     |
| `gp{154,155}/gate_harness.py` | Bug #16 crash-rate harness defect (post-JSON-print)          |
| `gp{154,155}/gate_harness.py` | Bug #18 graduated near-miss band + tag                       |
| `tests/`                      | NEW: fit_primitive_features_fixture_regression.py 22 cases   |
| `docs/concepts/architecture.md` | NEW: section 6a fit primitives sibling-block architecture |

### Key call sites (post-2026-04-25 line numbers)

```
L1748: validate_python_suite_imports(... require_parametric_form=...)
L2521-2630: fit_primitive_features_context (mutator prompt section)
L2871: prompt interpolates fit_primitive_features_context
L4310: fit_primitive_features_k_max read from rubric (default 8)
L4581-4710: 🧮 dispatch banner + scipy.optimize call + JSON write
L4640: BIC telemetry line
test_thesis.py:993-1037: APPARATUS CONTRACT judge prompt section (Bug #15)
test_thesis.py:2335-2470: holdout hard-gate w/ near-miss respect (Bug #21)
```

### Reachability invariants (Bug #11 / #21 lessons)

```
assert: fit_primitive_features dispatch is at iter-body scope,
        gated ONLY by rubric.enable_fit_primitive_features,
        NOT nested under any other primitive's flag.
why:    Bug #11 — nested wire-in caused 30+ iters of zero engagement.
trap:   if you add a new fit-primitive-class block, place it as a SIBLING
        not a CHILD. Test with a substrate that opts in to ONLY the new
        flag — if engagement fires, the wire-in is reachable.
```

```
assert: hard-gate (test_thesis.py:2335) parses stdout JSON regardless of
        returncode. Translates GP-156-shape harness output (holdout/
        farther_tail/all_gates_pass) to legacy harness_ok/gates shape.
why:    Bug #21 — harness raises AssertionError after printing JSON;
        returncode!=0 made the legacy parser fall to the "harness error"
        branch, zeroing legitimate near-passes.
trap:   if you add a new harness output shape, update the in-flight
        translator at L2348-2380 OR add `harness_ok`+`gates` keys to
        your harness JSON for legacy-parser compat.
```

### Open primitive parity gap (1D vs N-D)

The 1D `fit_primitive` exposes `diagnose_residual_pattern` +
`format_residual_surface_for_prompt` which inject "where the form is wrong"
text into the next mutator prompt. The N-D primitive does NOT yet have
this. v5.0 Cage should consolidate. Until then, mutator on near-miss iters
sees only judge prose, not residual surface.


## GP-166 STATISTICAL META-DIAGNOSTICS + APPARATUS HARDENING (2026-04-25 night)

The apparatus stops assuming the data's epistemology and starts measuring it.
Five components shipped this session, all opt-in via rubric flags:

```
region: noise_profile_preflight  lines: ~4341 (post run-start sentinel)
  flag: rubric.enable_noise_profile (default False)
  what: classify_noise_profile(visible_data) runs four tests on a
        baseline-fit residual series — Breusch-Pagan (heteroscedasticity),
        Shapiro-Wilk / Jarque-Bera (normality), Durbin-Watson (autocorr),
        explicit-σ_x detection (errors-in-X). Auto-routes solver flags
        the operator did NOT explicitly set: fit_weighted_residuals,
        framer_sigma_provided, fit_robust_loss (telemetry-only),
        fit_correlated_errors (telemetry-only), fit_use_odr (telemetry-only).
  output: workspace/noise_profile.json (pre_flight stage)
  briefing: NoiseProfileBriefingProvider (priority 220) surfaces verdict
            + test statistics to mutator each iter.
```

```
region: noise_profile_per_iter  lines: ~5489 (immediately after fit dispatch
        writes fit_features_result.json)
  flag: rubric.enable_noise_profile (default False)
  what: classify_residuals(residuals, x) on the FITTED model's residuals.
        Distinguishes good fit + clean noise (solver was right call) from
        good fit + structured residuals (model misspecification, missing
        feature). Appends to workspace/noise_profile.json["per_iter"][i].
  cost: O(N) per iter (one eval pass over visible data + 4 stats tests).
```

```
region: pathology_enforcement  lines: ~5460 (between fit-result print
        and python_code substitution)
  flag: rubric.disable_pathology_substitute_block (default False, i.e.
        enforcement is ON by default)
  what: when fit_features_result.pathological=True, REFUSE to substitute
        catastrophic params into MODEL_PARAMS. Replace extreme values
        (those flagged in extreme_params) with init-range midpoints so
        the gate harness receives bounded values. Original fitted_params
        and substituted_params both persisted in fit_features_result.json
        under fitted_params and substituted_params keys.
  why: gp163d 2026-04-25 — k_m=-1,205,170 propagated to gate harness,
       caused 10^(-4.2M) underflow on cluster predictions, MRE=143.
       Detector caught it; enforcement was missing.
```

```
region: bounded_discriminator_features_allowlist
        validator/autoresearch_loop.py:1647 (_validate_bounded_discriminator_suite)
  what: when project_dir contains features.py, auto-extend
        runner_allowed_imports with "features" so the bounded-discriminator
        suite can `from features import visible_rows, holdout_rows, …`.
  why: gp159 / gp163d contract collision — the R1 stdlib-only rule was
       designed against apparatus-import bypass, not project-local
       substrate adapters. Without this fix, the mutator was forced to
       inline data, which then triggered the "module-level I_model call"
       R1 strike on the next attempt; the bounce consumed retry budget,
       leaving zero tokens for thesis prose.
```

```
region: harness_failure_classifier_fallback
        validator/utilities/harness_failure_mode.py
  what: when the regex-based exception name extractor misses (truncated
        stderr, gate-harness-internal print format), fall back to a
        substring match on "AssertionError" or a Python frame pointing
        at an `assert` statement. Returns FAIL_ASSERT instead of
        FAIL_OTHER in those cases.
  why: gp163d 2026-04-25 — mutator's own discriminator (assert ratio_S>10)
       firing was being labeled fail_other → harness_defect_cap → score
       capped at 50. Real self-falsifications need fail_assert label so
       the judge scores them as scientific findings, not tooling failures.
```

```
region: framer_scope_check_nd_fix
        framer/active_framer.py:124 (_check_scope)
  what: framer scope check now accepts EITHER enable_fit_primitive
        (1D path) OR enable_fit_primitive_features (N-D path). Previously
        gated only on the 1D flag, which auto-disabled the framer on
        every N-D substrate even when enable_framer=true.
  why: gp163d had enable_fit_primitive=False (correctly, since 1D solver
       doesn't apply) but enable_fit_primitive_features=True; the framer
       silently disabled with reason="fit_primitive_disabled".
```

### MutatorBriefing providers added this session (3 new, total 9)

```
fit_telemetry          (200) — existing; now surfaces pathology_substitute_blocked
noise_profile          (220) — NEW: GP-166 pre-flight + per-iter noise verdict
contamination_defense  (240) — NEW: GP-166 .denylist hit surfacing with line nums
gate_gap               (250) — existing
per_class_breakdown    (280) — NEW: per-class MRE + U-vs-S diagnosis
iter_trajectory        (300) — existing
framer_recommendation  (320) — existing (wired but currently DISABLED on N-D
                               via the framer_scope_check_nd_fix bug, now fixed)
analogy_candidates     (350) — existing
row_outliers           (400) — existing
asymptote_deviation    (450) — existing
```

### gp163d 2026-04-25 score trajectory under these fixes

iter-0 (pre-fix):       score 0  — R1 contract collision (features import banned)
iter-3 (Fix R1):        score 40 — clean S-form pre-commit, harness defect mis-cap
iter-3 (full set):      target 70-80 — Fix A uncaps real self-falsifications,
                                       Fix C blocks pathology propagation,
                                       Fix B closes contamination feedback loop.
