# Review — abduction/synthesis engines

Cluster: `spec_abduction.py`, `synthesis.py`, `spec_catalog.py`, `spec_nogood.py`, `version_space.py`, `population_enumerator.py`, `distinguishing_play.py`, `grammar_reflex.py`, `grammar_extension.py`, `closure_audit.py`, `operator_implement.py`, `operator_proposals.py`, `object_roles.py`, `spec_lean.py` + adjacent contracts (`refinement_ladder.py`, `carrier_loader.py`, `patch_base_carrier.py`, `worldmodel_control_outcome.py`, `evidence_consolidation.py`, play-loop call sites).
Scope: ~11,600 LOC (10,070 target + ~1,500 adjacent); every uncommitted change diffed against HEAD.

## 1. Correctness findings

**F1 — Holdout evidence steers hypothesis formation via probe constants (worst finding).**
`distinguishing_play.py:86-90` (also 353-390, 511-513): `_PROBE_DETECT_ROW=5, _PROBE_DETECT_COL=19, _PROBE_DETECT_VAL=3, _PROBE_CYCLE_LEN=4, _PROBE_T_PHASE=19` are module constants mined from **episode_002 — the holdout** (`hold = EpisodeLog.read_jsonl(episode_log_path(project, episode=2))` in arc3_play_loop.py:932). The spec_nogood firewall itself is sound — `visible_clauses()`/`assert_visible` filter correctly; both writers (`spec_abduction.py:1342` visible-log feed; `worldmodel_control_outcome.py:37-117`, which replays witnesses against episode_001 and raises on holdout refs) are genuinely visible-grounded. But the firewall checks provenance *tags*, not experiment-selection *lineage*: scripted probes fire exactly where the holdout says the model is untested; resulting observations flow into prune()/nogoods/the visible bank tagged `evidence:"visible"`, and the holdout stops being an independent test. This is the repo's own "master discriminator: can the agent choose the evidence distribution" failure class. Bonus: the constants are ls20 grid coordinates hardcoded in a nominally substrate-neutral module.

**F2 — Dead guarded-pair learner in the per-action assembler (pre-existing).**
`spec_abduction.py:1371-1372`: `set1 = [tr for tr in trs if expl([r1])]` — `expl()` is an all-or-nothing predicate over the whole action's transitions, and the branch is only reached after every single-rule candidate failed `expl`, so `set1`/`set2` are always empty and the `when_count`+`stop_if_applied` pair option (1374-1380) is unreachable. An action with two same-op variants separated by a count threshold can never assemble deterministically; falls to residual cards/LLM. Fix is per-transition: `frag1(tr.s,0,tr.t)==tr.s_next`.

**F3 — Fingerprint cache keyed on incomplete identity.**
`version_space.py:164-183, 236-246`: `version_space_fp_cache.jsonl` keyed on (candidate sha256, battery sha256), but battery rows are pure indices (`{row_index, provenance, provenance_count}`). A re-recorded visible episode of equal length with no bitmaps produces a byte-identical battery → stale fingerprints against the old episode; wrong exact_count/sha16 corrupt duplicate verdicts and disagreement grouping. `build_row_bitmap` (evidence_consolidation.py:178-179) does it correctly with carrier+episode+evaluator digests — copy it.

**F4 — id()-keyed Galois memo can violate "never changes a winner" (latent, env-gated).**
`spec_abduction.py:1032-1040`: `_FP_MEMO` keys on `(id(tr), id(spec))`; spec dicts are created/discarded by the thousands and CPython recycles addresses → a new spec can hit the old spec's footprint → over-tight lower bound in `_galois_footprint_lower_bound` → would-be winner pruned. Live only under `ZTARE_GALOIS_PRUNE=1` (default off). `_GWC_TARGET_CACHE` (892-906) same pattern but targets are context-retained, safe in practice.

**F5 — Warm-verify memo identity too weak.**
`spec_abduction.py:1001-1009`: `_log_fingerprint` = (length, first row, last row). Episode-rewrite machinery exists (`rebind_identity_sidecar`, level_transfer_repair); a mid-log rewrite preserving length/endpoints returns a stale `_WARM_VERIFY_MEMO` verdict at :1197 → a refuted prior returned as "warm: prior replay-consistent".

**F6 — Enumerator variants can become the next champion.**
`population_enumerator.py:333-338` persists wrapper variants into `workspace/submissions/version_space_hypothesis_*.py`; `_load_champion_path` (78-93) falls back to `sorted(glob("*.py"), reverse=True)[0]` when test_model.py is absent — "version_space_hypothesis_…" sorts last → a deliberately wrong-on-unwitnessed-states wrapper adopted as champion base on the next run of a project without test_model.py.

**F7 — Behavioral-fingerprint collision in dedup: resolved, two residues.** The uncommitted version_space rewrite correctly pivots identity to source content (docstring documents the real prior collision on arc3_ls20_gov). Residues: (a) `load()` dedup key mismatch — legacy rows fall back to 16-hex `candidate_sha`, new rows full 64-hex `hypothesis_id` → same source admitted pre/post-migration yields two survivors; (b) legacy fingerprint-only prune rows still erase source-distinct future survivors sharing a battery fingerprint (`_load_prunes`, kept deliberately).

**F8 — MDL undercounts memorized payloads.**
`spec_catalog.py:899-905`: `_rule_dl` counts `len(v)` top-level only — a `content_states` machine of k glyphs × area A costs k; `writes` cost #colors not #cells. A memorizing region_event can beat a parametric rule in the DL tie-break. Bounded today (region events enter via strict-improvement passes), but this is the metric advertised as the shared MDL.

**Guard-learner monotonicity: verified clean.** Every refine pass internally re-lowers and accepts only on strict wrong-cell improvement over the same `env_frame_indices` scope; `run_refinement_ladder` compounds `spec_cur` across rungs (refinements accumulate, never reset). Delta-scorers only fed base-consistent incumbents; the new `_UNDEFINED_OPERATION_IMAGE` sentinel confined to the executor; standalone semantics byte-identical to HEAD. One tie-accepting pass (`_bare_superseded_writes`, `<=`) is a no-op unless `ZTARE_BARE_SUPERSEDED_FULL_FALLBACK=1` — meaning the documented "bare superseded exit-writes" step silently doesn't run by default (spec_abduction.py:3266-3268).

## 2. Catalog reusability (tu93 prospects)

Catalog core genuinely game-neutral: `spec_catalog.py` operators take all colors/rects/offsets/rates as learned parameters; miners derive every constant from evidence (Chebyshev gap=3, segment≥200 are substrate tuning, not game facts). Game constants live at the edges: distinguishing_play probe block (F1); `operator_implement.py:39-54,131-161` planted-synthetic defaults (parameterized via leaf artifact, palette-only); `population_enumerator.py:286` `known_colors`.

The honest blocker is self-admitted: `closure_audit.py:68-72` marks `interface:coordinate_actions` UNCLOSED — abduce_spec quotients on opaque int action ids (`_transition_class_key`, spec_abduction.py:867-885), so a click game's (x,y) actions collapse into one class and per-action assembly is meaningless. **tu93 verdict: plausible with work, blocked on the coordinate-action interface.** Noise deferral was calibrated on tu93 bootstrap (spec_abduction.py:1669: "72% of tu93 bootstrap signatures are singletons") — predicting most tu93 frames get deferred; the mining path needs that interface plus probably new effect families before it closes anything there.

## 3. Dead/unwired organs (no non-test importer)

- `fiber_lift.py` (0 importers), `effect_compiler.py` (0 — **yet modified Jul 15: actively edited while unreachable**; sibling `causal_compiler_adapter.py` deleted in working tree, good), `scene_grammar.py` (0), `batch_transition.py` (0; both referenced only by tests/test_worldmodel_p0.py).
- Default-off dead paths: `_bare_superseded_writes`, non-last-rule region-write pruning (`ZTARE_PRUNE_REGION_FULL_FALLBACK`), grammar_reflex structural bridge (`ZTARE_REFLEX_STRUCTURAL_BRIDGE`).
- Thin-thread organs (exactly 1 importer): `cycle_enumeration`, `challenger_portfolio`, `candidate_pool`, `symmetry`, `lean_equivalence`, `spec_lean`.

## 4. Complexity iatrogenics

- **refinement_ladder.py (whole module):** every `_wrap_refine` rung bypasses the ladder's own before/after scoring (`_self_scored_rung`) — the ladder is a scheduler over functions that already self-gate and no-op when they can't improve; `extract_residual_signature` (~120 lines) exists to predict whether to call functions whose failure mode is "return unchanged". A second copy of residual analytics bought for call-ordering.
- **grammar_reflex.py:354-380 `_backfill_empty_evidence_cards`:** appends an `unbound_no_evidence_matcher` disposition row per permanently-open closure card on every reflex entry — machinery managing the evidence-less cards closure_audit pre-registers; ledger grows forever, zero state change.
- **version_space fingerprint apparatus post-pivot:** fingerprints now explicitly non-authoritative, yet the battery snapshot, top-20 prediction serialization, on-disk fp cache, and `n_distinct_fingerprints` reporting all remain — a compensating layer for the retired design.
- **operator_implement.py:290-308:** Branch A measures "does the coupling refine help" by running two full abductions under process-global env-var mutation (`ZTARE_REFINE_LADDER=0`).
- Perf: `spec_abduction.py:1342` writes one full-grid nogood row per refuted candidate replay and `_clauses_by_sig` reloads the whole file per abduction (quadratic ledger growth — the live ledger is 8.3 MB); `population_enumerator` re-parses the full version_space ledger via `vs_load()` once per generated candidate.

## Top 3 structural remediations

1. **Make experiment selection holdout-blind by construction.** Delete the episode_002-derived constants from distinguishing_play.py; probe detectors must arrive as data in `version_space_disagreements.jsonl` rows with a provenance field, and an `assert_visible`-style admissibility check rejects any probe target whose provenance cites the holdout. Closes F1 and removes ls20 hardcoding in one stroke.
2. **One identity rule for every cache/ledger key:** full content digests of (candidate bytes, episode bytes, evaluator version) — what `build_row_bitmap` already does — applied to `version_space_fp_cache`, `_WARM_VERIFY_MEMO`, and replacing the two `id()`-keyed memos. Fixes F3/F4/F5 under a single convention.
3. **Land the coordinate-action interface before any tu93 claim** (thread (action_id, coords) through Transition, `_transition_class_key`, per-action option building), and in the same pass delete or wire the four cold organs — effect_compiler in particular is accumulating uncommitted edits with no caller, which is how the next "built-but-unwired orphan" RCA starts. Cheap add-on: the one-line per-transition fix for F2.
