# Review — DSL / carrier / Lean-bridge cluster

Cluster: `grid_dsl.py`, `scene_grammar.py`, `symmetry.py`, `transition_identity.py`, `candidate_pool.py`, `carrier_loader.py`, `challenger_portfolio.py`, `deterministic_candidate_producers.py`, `effect_compiler.py`, `fiber_lift.py`, `lean_bridge.py`, `lean_equivalence.py`, `invariant_bridge.py`, `spec_lean.py`, `adapter.py`, `policy.py`, `coverage_planner.py`, `probe_selection.py`, `refinement_ladder.py`, `residual_repair.py`, `terminal_witness.py`.
Scope: ~6,700 LOC read in full + ~800 lines of caller context (`arc3_play_loop`, `gates.as_predictor`, `invariant_certificate`, `evidence_consolidation`, `batch_gate`). DSL fail-closed contract fuzz-tested live (10 malformed ASTs → all `None`, no raise).

## 1. Correctness findings

**F1 — Candidate pool silently drops PATCH_BASE/PROGRAM carriers from the loop committee.**
`candidate_pool.py:41-54` — `_load_member` is a parallel mini-lowering (WORLD_MODEL_SPEC or `step/f/model/I_model` aliases only) bypassing the canonical door `carrier_loader.lower_carrier_namespace`, so it cannot lower `PATCH_BASE`/`PATCH_DELTA_SPEC` or `PROGRAM` AST carriers. The play loop pools exactly those: `arc3_play_loop.py:2999` (deterministic compiler PATCH_BASE), `:3017` (cached survivor), `:3201` (mutator test_model.py — the evidence prompt in adapter.py:161-166 tells the mutator to submit `PROGRAM`). Failure: a gate-passing compiled candidate is added to the pool, `surviving_committee` loads it as `None`, and disagreement-frontier probing at arc3_play_loop.py:3315 permanently no-ops for the carriers the pool exists to persist.

**F2 — Global `EXTENSIONS.clear()` on every lowering corrupts already-lowered programs.**
`carrier_loader.py:187` — `_register_carried_extensions` clears process-global `grid_dsl.EXTENSIONS` on every `lower_carrier_namespace` call. Any earlier-lowered program with `("ext", name, …)` nodes then resolves against the newest carrier's registry (or fail-closed `None`). Concrete: `challenger_portfolio.propose_distinguishing_targets` loads the champion predictor once (:379) then per-member predictors (:387 via `evidence_consolidation._load_carrier_from_source` → same door); an EXTENSIONS_SRC champion predicts through the member's registry → spurious null "disagreements" in version_space_disagreements.jsonl. `batch_gate.py:253-256` documents the hazard and works around it by ordering — defuse at the chokepoint, not per caller.

**F3 — Stale kernel-ratified invariants enforced with no epoch binding.**
`lean_bridge.absorb_ratification` (lean_bridge.py:280-287) keys certs by (quantity, relation, theorem) + lean-artifact sha only; `_invariants` (arc3_play_loop.py:~1327) loads every row forever; `reachability.py:247` prunes predicted successors violating any of them. Each theorem is about the `specStep` of the spec *at absorb time*; after a re-spec the cert only fires when out of sync with the current model — every actual effect is the unjustified case. Failure: spec v1 proves `count4_monotone`; v2 learns a timer reset refills color 4; reachability prunes the true successor as "theorem-impossible", goal states behind the reset become unplannable. Contrast: carrier receipts get `require_current_carrier_evidence_binding` (carrier_loader.py:131-167); invariant certs get nothing.

**F4 — effect_compiler rejects the best-evidenced rotation bank.**
`effect_compiler.py:360-362` — `starts = set(edge) - set(edge.values()); if len(starts) != 1: raise`. A fully witnessed 4-cycle (all four display edges observed) has no unique chain start → `EvidenceCompilationError` despite maximal evidence; `:359` hardcodes exactly 4 renderings. Credit: the emitted carrier honors the doc warning — `ROTATION_NEXT` stays a partial graph and generated `PATCH_DELTA` returns `None` on unwitnessed source states (effect_compiler.py:639-646). The mod-4 cycle-closing shortcut exists only in dead fiber_lift.py:402.

**F5 — Shape-mismatch witness collides with no-mismatch fingerprint.**
`terminal_witness.py:85-93` — a wrong-dimension prediction raises inside the cell comprehension, is caught, and produces `cells=[] / mismatch_count=0`, hashing identically to a perfect-match receipt for the same (action, phase). Level change altering grid dims → champion's stale-shape prediction dedupes as "no mismatch", defeating the behavior-keyed dedup.

**F6 — Proof-audit timeout escapes the fail-closed contract.**
`lean_bridge.py:147-169` — `subprocess.run(..., timeout=600)` raises `TimeoutExpired`, uncaught in `_run_proof_audit`/`absorb_ratification` whose contract elsewhere is "return {}". Play-loop callsite catches broadly (arc3_play_loop.py:875); the CLI `absorb` path crashes on a hung lake build. One-line fix.

Minor: `candidate_pool.add_candidate:32` dedups by substring search of a 16-hex digest over the whole JSONL (structure-blind). `challenger_portfolio.py:400-407` records disagreements with `prediction: null` when exactly one side is fail-closed None — verify distinguishing_play tolerates null grids.

**Uncommitted-diff verdicts:** symmetry.py diff is a correct de-authorization hardening (default group dihedral→identity, scale quotient opt-in); all non-test callers (goal_abduction.py:610,614) pass the group explicitly — no silent behavior change, and it removes the old one-operand scale-reduction asymmetry in `shape_similarity`. residual_repair.py diff harmless (lane tag). transition_identity.py (new) clean; `authoritative_dynamics` requiring `evidence_refs` deliberate. grid_dsl fail-closed holds under fuzzing.

## 2. Lean bridge: real or demo?

- **Live and real:** blueprint→campaign→absorb runs in production — `_write_worldmodel_blueprint` per checkpoint, background campaign kick, job polling, `absorb_ratification` runs the canonical L1/L2/L3 proof-audit subprocess with byte-matched target sha, sorry/admit/axiom bans, allowlist check (lean_bridge.py:203-219). Genuinely kernel-checked universal theorems, not rfl-over-probes.
- **Demo/manual only:** `lean_equivalence.certify_environment` — sole caller is `scripts/public/control/worldmodel_lean_certificates.py` (synthetic sealed envs, run by hand). `spec_lean.emit_spec_certificate` has **zero callers** — only its `_PRELUDE`/`spec_to_lean_step` are consumed by lean_bridge blueprints. Both rfl paths scope claims honestly to enumerated probes — no over-claim, just unwired. F3 is the one place a Lean certificate is applied beyond what it proves.

## 3. Dead-code inventory (import-grep verified, non-test callers = 0)

| Module | LOC | Status |
|---|---|---|
| effect_compiler.py | 655 | tests only — despite being a brand-new uncommitted file; not registered in `deterministic_candidate_producers._PRODUCERS`; docs confirm "former configured producer" |
| coverage_planner.py | 596 | tests + own CLI; nothing invokes the CLI |
| scene_grammar.py | 442 | tests only (the whole "perception layer") |
| fiber_lift.py | 418 | tests only; docs mark historical |
| lean_equivalence.py | 214 | one manual script |
| spec_lean.emit_spec_certificate + SpecCertificate | ~50 | zero callers |
| probe_selection: rank_probes / capability handler | ~180 | capability never registered; only `build_witness_hypergraph` live via residual_specialists.py:43 |

≈ **2,500 LOC of this cluster is cold.**

## 4. ARC-hardcoding

- **fiber_lift.py:38-48** is the jackpot: colors 9/12/11/4, `_TIMER_ROWS=(61,62)`, display rows 16-18 × cols 15-17, `_TIMER_COST=4`, reset 84, uncertified `% 4` C4 closure at :402 — all quarantined in dead code.
- **effect_compiler.py:359** (exactly 4 rotation renderings) and `:482` (`{rotation_increment, timer_reset}` only) are game-family-shaped in nominally data-driven code.
- Documented-and-declared, not violations: grid_dsl `COLOR_LITS=(0..3)` (seed pool), background=0 in `_shift`, candidate_pool arity-4 fallback, SceneParams 64x64 defaults. No hidden `s[5][19]`-style markers found in this cluster.

## Top 3 remediations

1. **Route `candidate_pool._load_member` through `carrier_loader.lower_carrier_namespace`** (F1) — one chokepoint fix restores PATCH_BASE/PROGRAM/EXTENSIONS carriers to the loop committee and deletes the parallel lowering seam the carrier_loader docstring warns about.
2. **Stamp `spec_sha256`/evidence-epoch into invariant cert rows at absorb and filter stale rows in `_invariants`** (F3) — same discipline `require_current_carrier_evidence_binding` already enforces for carriers; prevents theorem-of-a-dead-spec from pruning the current champion's reachability.
3. **Make extension registration per-program instead of process-global** (F2) — bind a registry snapshot into the lowered closure (or save/restore around lowering); fixes challenger_portfolio interleaving, removes batch_gate's hand-maintained ordering constraint. While in effect_compiler: accept the fully-witnessed cycle in `_learn_display` (a witnessed last→first edge is a certificate, not a shortcut) (F4).
