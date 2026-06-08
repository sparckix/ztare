# GP-246 — Governed DAG Proof-Search (ex-ante typed contract + best-first + deferral)

> ⛔ **FROZEN 2026-06-03 — historical log only.** The CANONICAL home for leanmill design + open
> areas + lift status is now **`docs/concepts/leanmill_architecture.md` (§Open Areas For Exploration)**.
> Do NOT append new findings here; record them in the architecture doc. This seam is kept as the
> chronological record up to 2026-06-03.

> **Seam metadata** · `seam_id:` GP-246 · `track:` engine/lean · `status:` FROZEN (→ leanmill_architecture.md) · `last_updated:` 2026-06-03

status: ACTIVE (spec → build) · opened 2026-05-30
owner: operator + engine
update_post: any change to the solver action_program shape, the DAG node schema,
the deferral/cost policy, the residual→lever map, or the no-false-closure invariant.
supersedes-in-spirit: the fixed Layer-2→5 cascade in `solver_action_contract`
(that cascade stays as the measured BASELINE; this seam is the optimization over it).

## Thesis (grounded, not aspirational)

From `papers/epistemic-generation/draft.md` ("Epistemic Generation as Mechanization
Placement"): structural primitives/typed contracts pay off as a **human+apparatus
mechanization interface that becomes a deterministic gate under an explicit contract**,
NOT as a solver-visible generation booster (agent-facing primitive screens are NULL).

Applied to the solver, the north-star object is therefore NOT a smarter prover (we will
not out-scale AlphaProof / DeepSeek-Prover-V2 on RL+search+compute). It is:

> **A provider-agnostic, typed-contract-GOVERNED best-first search over a proof-obligation
> DAG, where the LLM/hammer/frontier-prover is a subordinate move-generator and the moat
> is the mechanization-placement governance** (ex-ante contract → typed moves → kernel-
> ratified credit → matched-negative-control → residual→lever → no-false-closure).

The shift the operator named: the typed contract is **EX ANTE generative scaffold**
(it pre-specifies the DAG nodes, the allowed typed moves, and the residual→lever map
BEFORE any prover runs) — not ex-post rescue/validation. Ex-post validation (Layer 5)
remains, but it is the *floor*, not the source of value.

## Confidence (skin-in-the-game)

- HIGH that governance + ex-ante contract + no-false-closure is correct and better than
  status quo (the 2026-05-30 `sorry`-acceptance bug proved the status quo was unsound;
  the re-smoke showed uncrippling layers moves 0→real closures).
- MEDIUM/UNPROVEN that DAG best-first + deferral beats the fixed cascade on closure rate.
  This is a BET. The full ~20-row baseline run (fixed cascade, uncrippled) is the control;
  the DAG search must show MORE closures (or equal closures at lower cost) on the SAME
  rows to earn adoption. Pre-register: `closed_or_exact_gap@budget`, DAG vs cascade,
  same rows, same providers. Do NOT claim uplift until measured.

## What's already in place (do not rebuild)
- Ex-ante typed contract per row (`solver_action_contract`, built BEFORE prover layers).
- Provider registry (claude_opus / codex_gpt5 / gemini_flash / deepseek_v2) + in-worker
  native_hammer + claude_opus_warm.
- Matched-negative-control + kernel-ratified credit + attempts DB + typed exits.
- no-false-closure invariant ENFORCED (2026-05-30 `_is_compile_ok`: reject sorry/admit/
  bare-error in the closure verdict).
- Layer-1 semantic premise shelf (atlas embeddings) — restored on VPS 2026-05-30.

## What this seam ADDS (build order)

1. **Ex-ante proof-obligation DAG** (`solver_obligation_dag`): the contract pre-specifies
   typed nodes {root_goal, sub_goal, helper_lemma, gap, falsifier} and edges (a node's
   closure may discharge a parent). Built from the goal + the premise shelf + any
   decomposition the contract declares — BEFORE proving. Each node carries its own typed
   residual→lever slot.
2. **Governed best-first search** (`governed_dag_search`): a frontier of open nodes scored
   by (estimated P(close) × value) − cost; expand the best node with one typed MOVE; on a
   kernel-ratified+MNC-passed close, propagate to parents and reuse the partial closure.
   Replaces the fixed program-counter cascade with a search that reuses partial progress
   and exposes residuals as new typed sub-goals (the gated Arc-F move-graph, activated).
3. **Deferral/cost-aware typed-action policy** (`move_policy`): per node, choose the move
   (native_hammer FREE → claude_warm → cold-shot provider fan-out → frontier-prover slot)
   by expected-value/cost with an explicit DEFER action (stop spending on a node whose
   marginal P(close) is below threshold; emit it as exact_gap). This is the paper's own
   recommended next step — primitives as typed action-schemas in a policy WITH baselines,
   cost, and deferral.
4. **Provider-agnostic frontier slot**: the cold-shot fan-out gains a generic
   `external_frontier_prover` provider so a lab prover plugs in as one more move; the
   governance (MNC, kernel-ratify, residual→lever) is identical regardless of who generated.
5. **residual→lever closure**: every node attempt resolves to exactly one of
   {closure | exact_gap | falsifier | retired_impossible | new_sub_target}, and the search
   emits next_lever (what to expand) vs killed_node (vs retired). No attempt dies silent.

## Invariants (HARD; machine-checked)
- no-false-closure: a node is `closed` ONLY if kernel-clean (no sorry/admit, axioms in
  allowlist) AND matched-negative-control passes. (Regression test: a `sorry` node must
  score exact_gap, never closed.)
- Lane A PROPOSES, governance (proof_audit) RATIFIES. Search emits candidates only.
- substrate-agnostic: DAG/policy/governance carry NO NS/Clay-specific logic; any
  substrate specifics enter via the contract/registry plugin.

## Gates / done-definition
- BUILD done: governed_dag_search closes the re-smoke Rayleigh rows at ≥ the cascade's
  closure count on the SAME rows, with all invariants green + adversarial review survived.
- SCIENCE done: on the ~20-row pre-reg benchmark, DAG vs cascade reported as
  closed_or_exact_gap@budget with per-move attribution; adopt only if DAG ≥ cascade.

## Arc H — est_p_close calibration via the forecasting apparatus (cross-workstream merge)

The move policy's `est_p_close` IS a success-probability estimate — the exact object of
the F105 forecaster-calibration program. v1 uses a heuristic stub, upgraded for premise-
anchored nodes to the EXOGENOUS retrieval score. The principled upgrade:
1. **Elicit** the model's bid-ask P(close) per (node, move) BEFORE the attempt (skin-in-the-
   game, pre-registered) — the F105 elicitation surface.
2. **Score** it against the KERNEL outcome (closed / not) — an exogenous carrier the model
   cannot narrate around. The `solver_lane_attempts.db` (provider, outcome, compile_ok) is
   already the predicted-vs-actual substrate; add a `predicted_p_close` column.
3. **Calibrate** per-model using the F105 method (measured over/under factor, the three
   legal verdicts, the first-principles framing that worked vs the crude-factor that harmed).
HARD caveat from F105: calibration is **axis- AND model-specific** — RE-MEASURE on the
Lean-move-close domain; do NOT transport the coding-task factors. This makes `est_p_close`
a measured, governed, exogenously-scored prior instead of a stub — and it is the only place
the two workstreams genuinely compose (both are calibrated-success-probability under
mechanization-placement governance). GATED until the solver baseline gives a closure base-rate
to calibrate against (a 0%-closure regime has nothing to calibrate).

## Literature anchors (private; not for public docs)
- Magnushammer (Mikuła 2023) → native_hammer move priors.
- ReProver/LeanDojo (Yang 2023), LeanAgent (Yang 2024) → retrieval + warm-agent moves;
  best-first over a goal DAG is the standard ITP search our cascade lacks.
- COPRA (Thakur 2024) → in-context error-feedback ≈ warm-agent move.
- AlphaProof / DeepSeek-Prover-V2 → RL+tree-search provers; we DO NOT replicate, we
  wrap them as `external_frontier_prover` moves under our governance.
- Novel-to-apparatus: the GOVERNANCE is the contribution — ex-ante typed-contract DAG +
  deferral-aware typed-action policy + MNC + residual→lever + no-false-closure, all
  provider-agnostic. (Validated framing: epistemic-generation placement theory.)

## A/B RESULT (2026-05-31) — ADOPT on cost; no closure-rate uplift

First valid A/B (the prior run was VOID — `lake_not_on_PATH`, all 0/29; that bug
is now mechanized away). Both arms on the SAME 29-row spectral/APN slice, fixed
no-false-closure oracle, real compiles (0 lake_not_on_PATH), no orphan leak.

| metric | cascade | dag_search |
|---|---|---|
| closed rows | 11 / 29 | 11 / 29 (identical set) |
| attempts on the 18 never-closed rows | 54 | 40 |
| claude_opus cold-shot calls | 18 | 3 |

- **No closure-rate uplift**: DAG closes the same 11 rows as the cascade. The
  best-first/reuse machinery did NOT find closures the cascade missed on this slice.
- **Cost win, mechanism-confirmed**: the deferral-aware policy cuts the expensive
  `claude_opus` cold-shot 18→3 (-83%) and failed-row attempts 54→40, concentrated
  exactly on the low-P(close) rows it is designed to defer on. Per the
  pre-registered adoption rule ("MORE closures OR equal closures at lower cost"),
  DAG search EARNS ADOPTION — on the cost criterion, not closure rate.
- **Caveats**: single run, n=29; "attempts" is a cost proxy (the real saving is the
  expensive cold-shot calls). The 11 are compile_ok=1 candidates; full closure
  needs proof_audit MNC + axiom-allowlist ratification (same metric both arms, so
  the comparison holds). A confirmatory repeat would strengthen the cost claim, but
  the saving is mechanistically coherent (lands on the deferral target).
- **Baseline-validity resolved**: the sound run closes 11 distinct rows vs the
  suspect baseline's ~8 — the prior closures were NOT inflated; the solver's
  closure capability is real under the no-false-closure oracle.

DONE-status: BUILD-done MET (DAG ≥ cascade closures on same rows, invariants green,
no-false-closure verified, no orphan leak). Adoption SUPPORTED on cost; SCIENCE-done
(repeat for power) optional.

## Closure genuineness (2026-05-31) — the 11 are real proofs, not trivial restatements
Inspected the stored `proof_text` for all 11 compile_ok rows in
`leanmill_solver_lane_results.json`. They are genuine non-trivial Lean proofs
invoking real library lemmas and target-specific context, e.g.:
- `sum_sq_singularValues_eq_sum_eigenvalues`: `exact Finset.sum_congr rfl (fun i _ => T.sq_singularValues_fin hn i)`
- `singularValues_le_singularValues_zero`: `exact T.singularValues_antitone (Nat.zero_le i)`
- `singularValues_of_finrank_codomain_le`: `rw [LinearMap.singularValues_eq_zero_iff_le_finrank_range]; exact (Submodule.finrank_le T.range).trans hi`
- larger bodies: trace_div_card... (1042 chars), spectralRadius_mul_comm (450),
  perturb_2_row_and_col_gershgorin (411).
None are `sorry`/bare-`rfl`. They depend on the target's own `T.*` projections, so
a context-stripped MNC control should fail (non-vacuous). MNC ran inline
(`executed_at: solver_layer`).

REMAINING FORMAL STEP (not blocking adoption): run `proof_audit.py` on the 11 to
surface the MNC pass/fail BOOLEAN + axiom-allowlist verdict per row, turning
"11 kernel-clean genuine candidates" into "N formally-ratified closed theorems".

## A/B CONFIRMATORY (run-2, 2026-05-31) — cost win replicates; closure parity is FRAGILE
Second independent run, same 29-row slice, fixed oracle, real compiles.
| metric | cascade | dag_search (run-2) | dag_search (run-1) |
|---|---|---|---|
| closed rows | 11 | **10** | 11 |
| total attempts | 76 | 70 | 66 |
| claude_opus cold-shot calls | 18 | **7** | 3 |

- **Cost saving REPLICATES**: DAG cut the expensive claude_opus cold-shot 18→7 (run-1: 18→3). The deferral policy reliably spends less on the expensive provider.
- **Closure parity does NOT robustly replicate**: run-1 DAG tied cascade (11=11); run-2 DAG closed **one fewer** (10 vs 11). The deferral occasionally defers a row that WOULD have closed.
- **Revised verdict (supersedes the run-1 "adopt on cost")**: GP-246's value is a robust *cost* reduction on the expensive provider, but at a *closure-parity risk* — "equal-OR-one-fewer closures at lower cost," not clean equal-at-lower-cost. The deferral threshold is too aggressive on the margin. Adopt the deferral ONLY with (a) a "do-not-defer a node showing partial-progress" guard, or (b) explicitly in cost-dominated regimes where dropping a marginal closure is acceptable. A single run (run-1) over-stated the case; the confirmatory run is why we don't adopt on n=1.

## Newton-gate audit #1 (2026-05-31): the Layer-1 semantic premise shelf is KEPLER-ALIVE on this slice
Ablation (reflexive idea #1 / RP-003 seed bet): cascade with vs without the semantic premise shelf
(`LEANMILL_DISABLE_SEMANTIC_PREMISE_SHELF=1`), same 29-row spectral/APN slice, fixed oracle.
- WITH shelf: 11 closed. WITHOUT shelf: 11 closed. **Closed-row SET is IDENTICAL.**
- Verdict: the premise shelf is **engaged (Kepler-alive) but causally Newton-dead** on this slice —
  the same rows close without it; the shelf's embed/retrieve/render compute is pure cost here.
- Scope: slice-specific (spectral/APN rows may be close enough to Mathlib that providers find the
  lemmas unaided). NOT a universal claim; the shelf may be Newton-alive on retrieval-harder substrates.
- Why it matters: the capability-ROI audit only measures ENGAGEMENT (4 alive/7 dead/7 never); the
  Newton-gate is strictly sharper — it found an "alive/engaged" primitive with zero causal yield. This
  is the catch the Newton-gate exists to produce, on first application.

## Leakage audit on the 11 spectral closures (2026-05-31) — clean; closures are genuine, not retrieval
Meta-Darwin-mandated leakage check (the "are closures retrieval, not capability?" concern): for all 11
closed theorems, checked the name against (a) the semantic premise-shelf corpus (apn_atlas_corpus +
ns_atlas_rag_corpus, 11M chars) and (b) the Mathlib decl index (5.7M chars).
- Result: **0/11 in the premise-shelf corpus; 0/11 are exact Mathlib declarations.** No name-level
  retrieval leakage. The two "perturb" base-token matches are coincidental common words, not the theorems.
- Combined with the Newton-audit (premise shelf redundant on this tier) + the genuine proof bodies: the
  closures are REAL (novel statements, kernel-clean, leakage-free) but the proofs assemble existing
  Mathlib lemmas and the retrieval component adds nothing AT THIS DIFFICULTY. You cannot discriminate a
  useful component from a dead one on rows this easy — confirming the hard-but-provable corpus is the
  required next step. The leakage-audit method (name + corpus + decl overlap) is now built and is a
  mandatory gate for the hard-row test (else closures could be retrieval).

## Orchestration-alpha analyzer (2026-05-31) — built; alpha=0 on the easy slice (one provider dominates)
New analyzer `scripts/public/control/leanmill/orchestration_alpha.py`: reads the per-provider attempts and
computes whether the routed ENSEMBLE closes rows NO single provider does (the "orchestration is the alpha"
test). Baseline on the valid cascade run (29-row spectral slice):
- ensemble_closed=11, best_single=claude_opus_warm=11, **orchestration_alpha=0**.
- claude_opus_warm closed ALL 11 alone; native_hammer 0, cold-shot claude_opus 0.
- Reading: on the easy/Munger-empty tier the orchestration is REDUNDANT (one provider dominates); alpha can
  only appear on the hard-but-provable corpus where the dominant provider fails and routing/LeanHammer/other
  providers pick up rows it misses. The analyzer is the measurement gate for that test, with each alpha-row
  closure subject to cert-ratification (the now-fixed axiom probe).

## Hard-row leak-clean orchestration matrix (2026-06-01) — INTERIM: 0/7 closed, but 5/7 reach 1 goal remaining
The hard-but-provable test the orchestration-alpha analyzer was built for, now run leak-tight. Apparatus
built this session: (1) shelf quarantine (`apn_atlas_corpus.quarantined.json`, leak-tight 0/8 — drops the
DeepMind proof-helper DAG the shelf shared with the targets); (2) statement-extractor
(`src/ztare/leanmill/solver/statement_extract.py`) — fair goals = transitive def-closure of the statement,
proof helpers withheld (7/8 type-check; Conjecture2 unfit, signature under-extracted); (3) exhaustive
provider×row matrix (`orchestration_matrix.py`) — every provider attempts every row INDEPENDENTLY (no
warm short-circuit, no break-on-close — the fix for the earlier alpha=0 ARTIFACT), credit-gated by the
canonical `_validate_against_contract` (kernel + MNC), backend-absent providers recorded `unavailable`.

Result on 7 leak-clean rows × {native_hammer, claude_opus, codex_gpt5}, ZTARE_LEANMILL_APN_CORPUS=quarantined:
- **0/7 closed by ANY provider → orchestration_alpha = 0.** This is a RIGHT-REASON zero (exhaustive, no
  short-circuit; nobody closes, so ensemble = best-single = 0), NOT the earlier short-circuit artifact.
  The leak-clean DeepMind statements are above the current whole-proof frontier with the proof DAG quarantined.
- **BUT the proof-state gradient (GP-187, wired this session) shows the providers are CLOSE, not lost:**
  **5/7 rows reached `unsolved_goals` with a SINGLE goal remaining (progress 0.5)** (P2,P4,P5,P7,P8); the
  other 2 (P1,P3) only reached tactic-level failure (0.2). One claude attempt hit `unknown_identifier` —
  it reached for a WITHHELD helper (quarantine working as intended).
- **Next lever (non-treadmill residual_to_lever): the wedge is proof-STATE stepwise continuation, NOT a
  stronger one-shot prover.** Whole-proof granularity leaves providers ~1 goal short with no way to continue;
  feed the 1-goal-remaining partial proof back as a sub-goal and attack just the residual. The GP-187 gradient
  + the DAG (now consuming `best_progress` in `_frontier_score`/`move_policy`) are the support for this; the
  stepwise-continuation experiment is the next test.
- Caveats: codex_gpt5 was `unavailable` on 4/7 (backend/auth degraded mid-run — honest, not a silent drop, but
  its arm is partial; a clean codex arm needs that fixed). `progress=0.5/1 goal` is a heuristic parse of Lean's
  "unsolved goals", a proxy for "close", not a verified "one tactic away". Pilot was kernel-clean-only; MNC
  credit-gate is moot here (nothing closed). Conjecture2 (8th row) excluded — statement-extractor under-parsed
  its multi-line bipartite signature (kept=2, missing vocab → won't type-check); signature-parse fix pending.

## Stepwise continuation experiment (2026-06-01) — INTERIM NEGATIVE (confounded), discriminator pending
Test of the residual_to_lever conclusion (the 1-goal-short wedge is proof-state CONTINUATION, not a
stronger one-shot prover). `stepwise_continuation.py`: elicit whole proof → compile → extract the exact
open-goal state (kernel `proof_state.extract_unsolved_goals`) → hand it back for ONLY the continuation
tactics → re-verify, bounded 3 iters, credit-gated by the canonical `_validate_against_contract`.
Run: 5 progress rows (P2,P4,P5,P7,P8) × claude_opus × max-iters 3, quarantined shelf.
- **Result: 0/5 closed, 0 stepwise-only wins.** Iterating from the residual did NOT close the last goal;
  rows stayed stuck at 1 goal across all 3 continuations (or the fresh whole-proof errored at iter 0).
- **NON-PROBATIVE as a thesis-refutation** — a real confound: the loop RE-ELICITS a fresh whole proof at
  iter 0, which need not reproduce the matrix's favorable 1-goal partial (one row errored at iter 0). The
  clean discriminator (seed iter-0 from the matrix's ACTUAL partial proof) is BLOCKED: the existing matrix
  DB predates the `proof_text` column (that run loaded pre-MNC code), so no partials were stored.
- **Next lever**: re-run the matrix with CURRENT code (credit-grade MNC gate + stores `proof_text` partials
  + retries codex availability), then seed the stepwise loop from the real 1-goal partials. One re-run
  unblocks BOTH the definitive credit-grade alpha AND the seeded continuation discriminator. Also possible:
  the "1 goal remaining" is the CRUX (hardest goal), not a mop-up — in which case continuation won't help and
  the wedge is decomposition/premise-injection on that goal. The seeded re-run discriminates these.
- Apparatus shipped regardless: kernel `extract_unsolved_goals` (unit-tested) + `--seed-db` path (fails
  gracefully when partials absent). Boundary respected: extractor in kernel, loop in script.

## Provider complementarity via Jaccard (2026-06-01) — the binary alpha hid a real signal
Reused the extracted Jaccard primitive (`ztare.motion.set_distance.jaccard_distance`) in
`orchestration_alpha.py` to measure provider DIVERSITY on the partial-progress sets (which rows each
provider reached 1-goal-on), since closure-set Jaccard is trivial at 0 closures.
- **All 3 provider-pairs: Jaccard similarity = 0.0** (claude_opus / codex_gpt5 / native_hammer; shared=0,
  unions 3-4). Each provider gets CLOSEST (1 goal remaining) on DIFFERENT rows — maximally complementary,
  not redundant. The binary `orchestration_alpha=0` (nobody closes) HID this: the providers fail in
  complementary ways, so closing each one's near-misses would yield genuine ensemble coverage.
- Why it matters: this is the latent-orchestration-value signal. It strengthens the stepwise/refinement
  wedge (if refinement pushes each provider's 1-goal near-miss to a close, the ENSEMBLE covers more rows
  than any single provider — which the alpha would then show as >0). Direction is real; n is tiny (unions
  3-4) and codex was unavailable on 4/7, so suggestive not definitive — the matrix re-run (complete codex
  arm + credit-grade) sharpens it.
- Master-discriminator note: this is mechanism-honest — Jaccard binds to the EXOGENOUS carrier (the actual
  compiler-determined set of rows each provider reached 1-goal on), not a self-narrated score. Most other
  extracted stats (BIC-paired-t, Fisher-z power, Brier-delta) do NOT fit — they need continuous outcomes /
  larger n; leanmill closures are tiny-n binary. Information-yield's PRINCIPLE (stop on unchanged residual)
  was wired into the refinement loop; its committee-coupled function was not force-fit.

## Seeded refinement = CLEAN NEGATIVE (2026-06-01): the residual is the CRUX, not a mop-up
Definitive run of the stepwise wedge with BOTH confounds removed: seeded iter-0 from the matrix v2's
REAL 1-goal partial proofs (proof_text now stored), whole-proof REFINEMENT (regenerate complete proof from
compiler feedback, not blind fragment-append), + information-yield stagnation-stop. claude_opus, 5 rows.
- **Result: 0/5 closed; refinement DEGRADED the proof** (P2: 1 goal → 3 → stagnation-stop fired; P7/P8:
  1 goal → broke to error). Showing the provider the exact goal it already couldn't prove gave it no new
  capability and often lost the working prefix.
- **Verdict (probative, confounds removed): the continuation/refinement wedge is FALSIFIED on this corpus.**
  The "1 goal remaining" is the CRUX — providers scaffold to the hard goal but cannot close it, regardless of
  how the residual is presented (one-shot / append / whole-proof refinement, all 0).
- **Reframe (the honest conclusion): with the proof DAG quarantined (leak-clean), these DeepMind theorems are
  ABOVE the current providers' frontier.** The crux genuinely needs the bespoke helper lemmas that constitute
  the published proof — which we correctly withheld. So leak-clean closure here is likely infeasible for current
  providers regardless of orchestration OR continuation. The corpus is a FRONTIER MARKER, not a near-term target.
- **What the apparatus DID establish (all sound, reusable):** quarantine (leak-tight 0/8) + statement-extractor
  (7/8 fit) + exhaustive credit-grade matrix (alpha=0 right-reason) + proof-state gradient (5/7 reach 1 goal) +
  Jaccard (providers complementary, sim 0.0) + stepwise/refinement (crux falsification) + info-yield stop (fired).
- **residual_to_lever (forward):** to SHOW orchestration alpha you need a corpus where SOME provider closes SOME
  rows (so the ensemble can beat best-single); the Jaccard complementarity predicts alpha WOULD appear there.
  Options: (a) curate an EASIER hard-but-provable tier (crux within reach, still non-Mathlib, leak-clean);
  (b) keep APN as a frozen frontier benchmark and re-measure as provers improve. NOT another continuation tick.
- Scope/honesty: n=5, claude_opus only (codex unavailable 3/7), one corpus tier (APN hilbert). Probative for the
  continuation hypothesis on THIS corpus; NOT a universal claim that proof-state methods never help.

## Premise-injection ablation + CLOSEOUT (2026-06-01): APN is above-frontier across 6 variants
Operator-chosen diagnostic (premise-injection ablation: add back k withheld helpers, measure closure vs k).
- Reconstruction-from-decls ablation was CONFOUNDED ×2 (dropped `set_option autoImplicit false`/`open
  Classical` → spurious other_error). On the 3rd stumble, applied the "≥3 point-fixes = the primitive is the
  bug" rule: reconstruction is the WRONG primitive. Switched to TRUNCATION (`truncate_to_target_header`:
  verbatim file up to `:= by`, a verified-clean prefix), the correct primitive.
- **k=all via truncation: 0/5.** Even given the ENTIRE verbatim scaffold (every helper + directive, only the
  final proof blanked), claude_opus does not close: P2 leaves a clean 3-goal partial; P4/P5/P7/P8 error on the
  proof body. So the gap is NOT merely helper-CONSTRUCTION — the final ASSEMBLY is also beyond the provider here.
- **CLOSEOUT — robust negative across 6 variants** (one-shot matrix 0/7; stepwise re-elicit+append 0/5; seeded
  whole-proof refinement 0/5; reconstruction ablation ×2 confounded/discarded; truncation k=all 0/5): leak-clean
  APN hilbert is ABOVE claude_opus's frontier regardless of orchestration / continuation / refinement / full
  scaffolding. **APN is a FRONTIER MARKER, not a near-term target.**
- What the session BUILT and stands (all sound, reusable, deployed): shelf quarantine; statement-extractor;
  credit-grade exhaustive matrix; proof-state gradient (wired into the DAG best-first); Jaccard provider
  complementarity (sim 0.0 — orchestration WOULD pay on a within-frontier corpus); info-yield stagnation-stop;
  truncation-based ablation context; primitive-amnesia precheck. The apparatus is ready the moment a
  within-frontier leak-clean corpus exists (the operator's option (b) from the fork) or provers improve.
- STOP: no more continuation/ablation variants on APN (discipline: the negative is robust; the corpus is the
  limit, not the method). Forward = within-frontier corpus OR frozen-benchmark re-measurement.
- Caveats: claude_opus only (codex unavailable 3-4/7); n=5; the 4 k=all other_errors may carry some
  provider-proof-malformation-on-huge-context component, so "assembly beyond provider" is strong-suggestive,
  while "no closures across all variants → above-frontier" is solid.

## CORRECTION (2026-06-01): the earlier closeout was CONFOUNDED — harness bugs, not frontier
Operator skepticism ("can't believe APN is above frontier; the paper used GPT-5.x") forced a re-audit
that found the prior "above-frontier across 6 variants" verdict was driven by HARNESS BUGS, not capability:
- **`_build_solver_context` on materialized rows** prepended the source-file prelude → DUPLICATED the
  statement defs ("`X` has already been declared") AND re-injected the withheld helpers (re-leak). EVERY
  matrix/stepwise/ablation variant shared this context builder, so all 6 "negatives" were void.
- **codex_gpt5 (the paper's GPT-5.x family) was rate_limited** on most rows → never properly run.
- **gemini/deepseek `max_tokens=2048`** truncated proofs.
Fixes: compile the SELF-CONTAINED materialized goal directly (no prelude), codex backoff/retry, max_tokens 16384.
- **FAIR one-shot matrix (clean, codex working): 0/7 closures — BUT codex reaches `unsolved_goals, 1 goal` on
  6/7 leak-clean rows; claude/native on several too.** Trustworthy now. Jaccard: 2/3 provider-pairs complementary.
- **Revised verdict: APN is above the ONE-SHOT frontier, NOT above-frontier.** Providers land ONE goal short.
  The paper closes these almost certainly via ITERATIVE SEARCH + compiler feedback + multiple samples
  (AlphaProof-style), which our single whole-proof shot does not do. The gap is the HARNESS, not (clearly) capability.
- The stepwise/refinement experiments that would test the iterative wedge were ALSO run with the buggy context →
  those "falsified" verdicts are VOID. Re-running un-confounded (seeded from the fair 1-goal partials, fixed
  self-contained context) — that is the experiment that mirrors the paper and has never been fairly run.
- Lesson: a shared confound in the context builder invalidated an entire battery of "independent" variants at
  once. The operator's external-reference check (the arXiv model) was the discriminator the self-review missed.

## Un-confounded iterative refinement (2026-06-01): 0/5 — but the harness is WEAK vs the paper's
The fair test (fixed self-contained context, seeded from the fair matrix's REAL 1-goal partials,
claude_opus refiner, 3 iters): **0/5 closed; refinement DEGRADES the 1-goal partial** (→ error/other_goal).
Now trustworthy (no context confound). BUT this does NOT refute the paper's reachability, because my
iterative harness is a WEAK approximation:
- refiner = claude_opus (codex/gpt-5.x reached 1-goal on MORE rows but its 27-min/attempt rate-limit made a
  multi-iter loop impractical here);
- "refinement" = sequential WHOLE-PROOF regeneration from compiler feedback (3 shots) — NOT the paper's
  AlphaProof-style TREE SEARCH + many samples + value model.
**Disciplined conclusion:** leak-clean APN is not reachable by one-shot OR crude refinement with current
providers; providers land 1 goal short; complementary across providers (Jaccard 2/3). Whether it is reachable
with a PROPER search harness (multi-sample + feedback + gpt-5.x at high reasoning) is OPEN — we have not built
that harness. The remaining gap to the paper is harness sophistication + model/reasoning budget, NOT a clean
capability ceiling. Forward = build a real sampling+feedback search loop (significant; codex rate-limited) OR
treat APN as a frontier-search benchmark. STOP crude-refinement variants (the negative is robust for THAT harness).

## Distinctive architecture (subgoal-decompose + global cache) VALIDATED (2026-06-01)
Built `subgoal_cache.py` — the AlphaProof-Nexus-distinctive engine (arXiv 2605.22763): NOT best-of-N, but
decompose-into-subgoals + a GLOBAL persistent proven-lemma cache. Decompose via `unfold <stmtdef>; repeat'
apply And.intro` → read leaf conjuncts from the unsolved-goals block; prove each leaf in-context (best-of-N);
cache proven leaves globally (`proven_lemma_cache.jsonl`, reused cross-row); assemble.
- **Result on P2 (leak-clean, claude_opus best-of-5): leaves 1/3.** `ProblemP2` decomposes cleanly into
  ProblemP2CoeffFormula / Type1Unimodal / Type1LogConcave. **ProblemP2CoeffFormula PROVED + cached** — a goal
  one-shot/refinement NEVER closed (those were 0/7). First genuine forward progress on a leak-clean APN row.
- **Bottleneck LOCATED precisely:** the 2 remaining leaf conjuncts (Type1Unimodal, Type1LogConcave) are the wall
  for claude best-of-5. Close those and P2 assembles. This is the RL-trained-leaf-solver gap — exactly
  AlphaProof's advantage (Gemini 3.1 Pro + RL solver + massive search per leaf), the training-required part.
- Bugs fixed en route to a CORRECT pipeline (each was confounding earlier "negatives"): context dup/re-leak;
  closure dotted-ref drop (`local_refs`); extract_goal regex (`:= sorry`/dotted); unsolved-goals per-⊢ split.
- **Next levers** (do NOT re-run best-of-N): (a) recursive decomposition of the 2 hard leaves (they may split
  further); (b) stronger leaf solver on them (n≫5, codex/gpt-5.x, or the RL prover); the global cache makes
  every prior proven leaf free. The architecture is the right one; the remaining gap is leaf-solver strength.

## De-anchoring Meta-Darwin (2026-06-01): the automation void is EMPTY on research leaves
Operator directive: de-anchor from human problem-solving, work natively-agentic, mine the void, kill loved
ideas. Tested the de-anchored alternative to the (anthropomorphic) conjecture-verify-cache engine:
LLM-FREE retrieval-augmented heavy automation (12 retrieved premises thrown at nlinarith/simp_all/aesop +
decide/native_decide — the verifier-cheap/human-expensive region a human won't hand-explore).
- Pre-registered scratch forecast p_success=0.20 (skin in the game, no membrane).
- **Result on P2's 3 leaves: native-automation 0/3** (closed NOTHING, incl. the easy leaf0 that LLM-conjecture
  best-of-5 DID close → 1/3). Realized 0.0 vs predicted 0.20 (over; the void was emptier than bet).
- **Meta-Darwin verdict: KILL the automation-void idea on research-grade NON-DECIDABLE leaves.** The
  anthropomorphic LLM-reasoning decomposition BEAT pure-agentic brute automation (1/3 vs 0/3). The de-anchoring
  lesson cuts the other way here: the leaf gap is genuine mathematical REASONING/INSIGHT, not human-vs-agentic
  strategy — brute automation can't manufacture the insight. Scope: APN hilbert P2; automation would win on
  DECIDABLE/finite/arithmetic classes, so the engine should ROUTE the cheap automation pass by goal class
  (likely-decidable → automation first; reasoning-heavy → LLM-conjecture), not pick one religiously.
- Next lever: conjecture-engine + a STRONGER leaf solver (RL prover / high-reasoning model) on the hard leaves;
  automation stays as a cheap gated first pass. Skepticism applied to BOTH ideas; the data (kernel-arbitrated) chose.

## SCALE-compounding KILLED on this corpus + consolidated skeptical verdict (2026-06-01)
RD tick (de-anchored, Meta-Darwin on my own loved architecture). Cheap no-LLM discriminator: decompose all 7
APN rows, Jaccard their leaf-conjunct sets — does the global cache compound across rows?
- **Result: 0 shared leaves across all row-pairs** (P1=4, P2=3, P3/P4/P5/P7/P8=1 leaf each, all DISJOINT).
  Forecast over (p_share 0.35 → 0.0). **KILL the cross-row cache-compounding claim on this corpus:** these are
  independent problems; a lemma proved for one is useless for another. COMPRESS (within-search reuse) survives;
  SCALE (cross-row/substrate compounding — the paper's shared-memory speedup) is CORPUS-DEPENDENT, needs a
  shared-sub-lemma corpus (a single theory's many lemmas), not a grab-bag of independent targets.

**Consolidated skeptical verdict (two loved-idea kills this session, kernel-arbitrated):**
- BUILT + kernel-tested: the conjecture·verify·cache engine (INVERT decompose + COMPRESS within-search cache +
  governance + proof-state gradient). Decomposition WORKS (closed P2's easy leaf one-shot/refine never could).
- KILLED: (1) the verifier-cheap automation void (0/3, the gap is insight not strategy-style); (2) cross-row
  cache compounding (0 shared leaves, rows independent). Neither architectural amplifier helps on this corpus.
- BINDING CONSTRAINT = leaf-solver TALENT on the hard leaves. No orchestration/automation/caching shortcut
  manufactures the insight. The remaining genuine lever is a stronger leaf solver (high-reasoning model now;
  RL prover via the GPU offer) — running the codex talent discriminator next.
- CALIBRATION: 2 over-forecasts (0.20→0, 0.35→0). I am systematically optimistic about compounding/transfer;
  priors adjusted down. Skepticism applied to my OWN architecture, not just others' — the data chose.

## CORRECTION — the "automation void / binding-constraint=talent" verdict ran on a DEAD REPL (2026-06-01, later same day)
De-strawmanning the nurture side (operator: "are you not strawmanning?") surfaced two substrate confounds that
VOID part of the verdict above. Both are now fixed; the kernel-arbitrated data is re-read on a LIVE substrate.

- **CONFOUND 1 — the persistent REPL was DEAD.** The vendored repl binary is built at lean4 **v4.29.0**; `ztare_proofs`
  Mathlib oleans are **v4.30.0-rc2** (ABI mismatch). `PersistentLean(project_dir="ztare_proofs")` had `import Mathlib`
  silently return the empty env `{env:0}` in ~0.8s (a real import is ~46s) — **not even `Nat` defined**. Any run that
  built PersistentLean over `ztare_proofs` and saw "0 closed" (incl. `repl_search.py` 0/3) was scoring an empty Lean
  env, **not** a solver. Those automation-void negatives are **non-probative**, same class as the #print-axioms
  module-incompatible VOID. FIX (shipped): `PersistentLean._spawn` now fail-loud asserts `example : Finset ℕ := ∅`
  against base_env and raises a toolchain-mismatch error — a dead env can never again masquerade as "0 closed".
  LIVE pair = repl v4.29 + `projects/atlas_lean_2026_05_29` (v4.29 Mathlib); import live in ~46s, tactics work.

- **CONFOUND 2 — proofState/tactic STEPPING is env-blind for local defs.** From the P2 sorry proofState (via
  `start_tactic_proof` or `open_file`), `unfold ProblemP2` => "Unknown identifier", `constructor` => "not inductive"
  (whnf won't unfold the file's own def), `refine ⟨…⟩` => "Unknown constant". The incremental tactic mode does not
  thread the file's definitional env into name resolution. So an incremental "stateful tactic beam" cannot step a
  goal stated via local `def`s; the **whole-proof `check(file_minus_import)` mode** is the correct mechanism
  (names + decomposition resolve). `scripts/public/control/leanmill/stateful_beam.py` (proofState stepping) is the
  wrong instrument for these rows — reorient to a whole-proof decomposition beam.

- **RE-READ on the LIVE pair (kernel-gated).** `refine ⟨?_,?_,?_⟩` splits P2 into its 3 components.
  `theorem coeff_only : ProblemP2CoeffFormula := by intro r g d; simp_all [pureOSequence, generatedOrderIdeal]`
  closes **KERNEL-CLEAN** (0 sorries; `#print axioms coeff_only` = [propext, Classical.choice, Quot.sound], **no
  sorryAx**) — a component the one-shot 7-tactic battery had ERRORED on. The two remaining components reduce to
  crisp residuals: `Type1Unimodal => ∃ j ≤ socleDegree P, …` and `Type1LogConcave => ∀ i, 0 < i → …`.

- **NET verdict adjustment.** "Decomposition works" SURVIVES and is reconfirmed live. SCALE cross-row compounding
  KILL (Jaccard, no REPL) SURVIVES. The "automation-void 0/3 ⇒ binding-constraint=pure-talent" claim is **suspended**
  pending a live-pair re-run of the automation pass — and is already partly falsified: live decompose+unfold
  automation closes 1/3 of P2 that one-shot errored on. The residual wall is **localized**, not coarse: the
  unimodality + log-concavity of type-1 pure O-sequences (still plausibly invention/composition-bound; published
  proof = 35-129-lemma DAG ⇒ MOVE_CONJECTURE/subgoal-cache is the indicated lever for those two, not more tactics).
- **CALIBRATION update:** the two prior "0→kill" forecasts were partly scoring a dead substrate, not optimism alone;
  the real recurring lesson is [[feedback_positive_control_must_match_real_substrate]] — verify the primitive is
  ALIVE before reading any negative as signal. Self-serve positive control is now enforced in the primitive itself.

## MECHANIZED prevention of "going blind" (2026-06-01, operator-directed RCA + forcing function)
RCA of the dead-REPL episode: we trusted a NEGATIVE result ('0 closed' ⇒ talent-bound) from
a substrate we never calibrated. The repl/oleans toolchain mismatch returned an empty env
silently; nothing forced a liveness check; the void negative was written as a verdict. Root
defect = uncalibrated instrument + no observability, NOT the specific version skew.

Prevention shipped (3-layer forcing function, guarded at the single chokepoint `PersistentLean`):
- `_check_toolchain` (deterministic, pre-spawn): RAISES in ~0.01s on a definite repl-vs-project
  lean-toolchain mismatch, with the exact versions. Cheapest catch of this exact RCA.
- `_assert_prelude_live` (post-import positive control): probes `example : Finset ℕ := ∅`;
  RAISES if Mathlib is unusable. Functional backstop.
- spawn emits `[lean-substrate] LIVE | toolchain X==Y | import Ns | positive control ok` to
  stderr every spawn — the observability that was missing.
- `src/ztare/formal/substrate_liveness.py::calibrate(pl, corpus_probe=None)` — substrate-agnostic;
  for any script that INTERPRETS a negative: toolchain + positive controls + verifier
  FALSE-ACCEPT guard (false goal must not be 'closed') + sorry-gate guard (#print axioms must
  surface sorryAx). Fail-closed (`SubstrateDeadError`).
- `scripts/public/control/leanmill/verify_substrate.py --project-dir <dir>` — one-command
  GREEN/RED canary (nonzero exit on dead); run before trusting any result, usable as a CI gate.
Because `PersistentLean` is the only substrate entry, every consumer is auto-protected: a dead
substrate now raises loudly instead of returning silent 0s. Dogfooded: RED on ztare_proofs
(mismatch, exit 2), GREEN on atlas_lean (exit 0). Lesson encoded: a negative is inadmissible
without a green calibration stamp run through the SAME code path as the real probes.

## LIVE-substrate re-measurement of "automation 0/3" — CALIBRATED 1/12 (2026-06-01)
The whole-proof decomposition beam (`scripts/public/control/leanmill/decomposition_beam.py`),
run over the matched live pair (repl v4.29 + atlas_lean_2026_05_29) with a GREEN calibration
stamp printed BEFORE any number (toolchain match + positive controls + false-accept guard +
sorry-gate), per-component across all 8 APN rows, budget 40 candidate bodies/component:
- **AGGREGATE: 1/12 components closed kernel-clean** (no sorryAx). per-row: P1=0/4, P2=1/3 (only
  ProblemP2CoeffFormula, via `intros; aesop (add simp [Monomial, …])`), P3/P4/P5/P7/P8=0/1,
  Conjecture2 skipped (target-type parse — minor fix).
- Forecast was 0.30 (over-forecast); the specific "P1 fully closes" bet (0.55) was WRONG — but
  this negative is ADMISSIBLE (calibrated), not a dead-substrate artifact. RCA of the miss:
  GammaP1/divisorsFinset/generatedOrderIdeal are `noncomputable`, so decide/native_decide have
  no executable code; simp/norm_num/aesop unfold correctly but stall at a concrete
  `{m ∈ Finset.Iic mXYZ ∪ Finset.Iic mXZ2 | …}.card = 1` they won't enumerate.
- **Two buckets — do NOT lump:** (a) P1's 4 components are AUTOMATION/SOLVER-STRENGTH bound
  (concrete finite Finset cardinalities; a targeted Finset-enumeration/Fintype-decidability pass
  or a stronger leaf solver plausibly closes them — not a deep-math wall); (b) the sequence
  properties (P2 unimodal/log-concave, P3-P8) are INVENTION/talent bound (35-129-lemma DAG;
  MOVE_CONJECTURE is the lever). Decomposition's genuine buy: it closed P2's CoeffFormula that
  one-shot errored on, and it localizes every residual into these two buckets.
- NET: the "binding constraint is mostly invention" verdict is now EARNED on a calibrated
  substrate (replacing the void 0/3), with the caveat that ~1/3 of the open components (P1) are
  a tractable automation-strength gap, not the deep frontier.

## Agentic LLM-leaf is the lever — layered calibrated answer (2026-06-02)
After fixing the dead-REPL, the env-blind proofState mode, and several LLM-dispatch harness
artifacts (all caught by calibration), the leanmill "is the hard leaf talent-bound?" question
resolves into a LAYERED, kernel-arbitrated answer on the APN hilbert_functions_2 corpus
(matched live pair: repl v4.29 + atlas_lean_2026_05_29; every closure independently re-gated
by `lake env lean` + `#print axioms` ⊆ {propext, Classical.choice, Quot.sound}, no sorryAx):

- **One-shot deterministic** (native battery + obligation-router vocabulary + MM-3 reframes,
  budget 80, A/B): **1/12** components. The research-ops vocabulary / pec / MM-3 added ZERO
  lift over a plain battery in one-shot mode (router ⊇ battery, router-only closures = 0) —
  consistent with the research_log finding that passive op-LABELS are internalized in latent
  space; the contract/forcing layer is what changed behaviour, not the labels.
- **Multi-step AGENTIC LLM leaf** (codex on subscription, iterating against `lake`; agent
  composes, the independent kernel gate arbitrates): closes the **P1 arithmetic bucket** that
  one-shot could not — P1 d0/d1/d3 kernel-clean (d2 a 300s TIMEOUT, same structure, not a
  wall). The d0 proof INVENTED a helper lemma (`totalDeg m = 0 → m = 0` via Finsupp-sum) then
  `card_eq_one` + `Finset.ext` + `mem_generatedOrderIdeal_iff` — genuine multi-step
  construction a tactic battery cannot do. But it closes **0/2 of the P2 sequence-property
  frontier** (`ProblemP2Type1Unimodal`, `ProblemP2Type1LogConcave`) in a single 300s leaf.

**Frontier pinned:** the genuine invention/talent wall for this corpus is exactly the type-1
pure O-sequence unimodality & log-concavity theorems (published proof = 35-129-lemma DAG) —
NOT tactic search, NOT budget, NOT the arithmetic/coefficient bookkeeping. The indicated
architecture for those is conjecture-DAG decomposition (`MOVE_CONJECTURE`): split the hard
theorem into sub-lemmas, solve each with the agentic leaf (the now-confirmed per-node solver),
compose + cache. This maps onto the existing `run_llm_layers` "warm agent (iterative)" slot +
the governed DAG — both now empirically grounded, not speculative.

**Method note (the recurring time-sink):** every false signal this thread came from an
UNCALIBRATED instrument read as a real negative — dead REPL (toolchain), env-blind proofState,
codex prompt-not-delivered, dead API keys. Each is now guarded by a positive control run
through the same code path. The durable fix is one tested dispatch primitive
(`subscription_agent_runtime`) + calibration-first everywhere, not bespoke ssh commands.

## Conjecture-DAG decomposition on the P2-unimodal frontier — scaffolding yes, core no (2026-06-02)
Tested the indicated next architecture: can agentic decomposition crack the P2 frontier the
single leaf couldn't? Two agentic codex passes (~1800s total, workspace-write + lake,
independently axiom-gated):
- Pass 1 (decompose P2-unimodal): codex GENERATED + PROVED 4 substantive new helper lemmas
  (`OrderIdeal.exists_le_maximal`, `carrier_eq_divisors_of_maximal_singleton`,
  `PureOrderIdeal.carrier_eq_divisors_of_type_one`, `pureOSequence_ext`) — all kernel-clean —
  but left the final `theorem leaf : ProblemP2Type1Unimodal := by sorry` unassembled (900s).
- Pass 2 (close leaf USING the proven helpers, focused, 900s): NO further progress — still 1
  sorry, no new lemmas, axioms still carry sorryAx.
**Conclusion:** the conjecture-DAG move WORKS at the scaffolding level (decomposition reduces an
unprovable theorem to proven structural lemmas + a localized residual), but the IRREDUCIBLE
core — that the divisor-degree-count sequence of a type-1 pure order ideal is unimodal — is
genuine hard mathematics (Stanley/Hibi pure-O-sequence territory; published proof is a
multi-lemma DAG) and did not yield to agentic leaf + decomposition + 1800s. The frontier for
this corpus is now PRECISELY localized to the unimodality/log-concavity argument, not tactic
search / budget / orchestration.

**Validated architecture (the payoff of the whole thread):** governed multi-step =
  agentic LLM leaf (kernel-arbitrated, the confirmed per-node solver)
  + decomposition into sub-lemmas (conjecture-DAG; reduces hard theorems to scaffolding + a
    localized core)
  + ProofCache + the calibrated substrate/embedder/provider liveness gates.
This closes tractable leaves one-shot can't and localizes hard theorems to their genuine
mathematical core — it does NOT manufacture the missing mathematical idea. That boundary is
the honest, calibrated result; "world-class proof search" is NOT claimed (cf. AlphaProof solves
IMO; this closed degree-0 arithmetic + scaffolding on one corpus). The lever is the ENVIRONMENT
(general model + governed loop), not trained-prover compute.

## Closure ledger: an under-budgeted "open" is NOT a wall (2026-06-02, operator-caught)
A subset best-of-N ledger (timeout=250, decompose=False for P1, claude crippled) read P1_d2
(`pureOSequence GammaP1 2 = 4`) as open → looked like 1/3. The operator flagged it as possibly
a capability/timeout artifact, not a wall. Re-tested FAIRLY (codex, 600s, decompose=True):
P1_d2 CLOSES KERNEL-CLEAN with a genuine enumeration proof (codex builds the 4 degree-2
monomials, proves the filtered set equals them via Finset.ext + the divisor bounds, then card;
axioms ⊆ allowlist). So:
- **P1 arithmetic bucket is fully tractable** (d0/d1/d2/d3 all close kernel-clean with a fair
  budget + decompose) — the under-budgeted ledger under-counted.
- **P2-unimodal remains the genuine frontier** — it DID get a fair shot (dedicated 1800s
  decompose: scaffolding proved, core open), so its wall is credible math, not budget.
- **Two harness bugs surfaced + fixed:** (a) `closure_ledger` now defaults timeout=500,
  decompose=True for all, and flags near-budget opens as `budget_suspect` (a genuine-frontier
  verdict requires a NON-budget-suspect open — an under-budgeted open is inadmissible-as-a-wall,
  the same calibration discipline applied to the ledger); (b) claude via the subscription
  wrapper can EDIT but cannot run Bash/lake non-interactively (acceptEdits blocks Bash), so in
  best-of-N it was a blind one-shot, not an iterating agent — true cross-family best-of-N needs
  `--allowedTools Bash` / a permission rule (operator authorization; `--dangerously-skip-
  permissions` is harness-blocked as unsafe-agent-spawning).

## Frontier diagnosis: P2-unimodal is FORMALIZATION-bound, not discovery-bound (2026-06-02)
RD-disciplined analysis (capability precheck surfaced PDE-ESTIMATE-CRAFT-OPS@0.72 + proof_state;
consumed the RD brief; mapped to the universal research-ops + pec vocabulary). The agentic leaf
stalled on `ProblemP2Type1Unimodal` not because the math is open, but because Mathlib lacks the
needed reusable lemma — a DIFFERENT obstruction class than "hard open problem".

**The classical reduction (research-ops decomposed):**
- core_01 Problem Reformulation: a type-1 pure order ideal's carrier = divisors of its single
  maximal monomial g = ∏ᵥ xᵥ^{eᵥ}; so its O-sequence h_d = #{divisors of degree d} =
  [t^d] ∏ᵥ (1 + t + … + t^{eᵥ}). (This IS the ProblemP2CoeffFormula component — already closed
  kernel-clean in P1, so the reduction is partly formalized.)
- Transfer (known): each interval factor (1+…+t^{eᵥ}) is symmetric (palindromic) + unimodal.
- pec_a Auxiliary-Object / MOVE_CONJECTURE (the crux): the product of symmetric-unimodal
  polynomials (nonneg coeffs) is symmetric-unimodal — the symmetric-unimodal cone is closed
  under multiplication. ⇒ h is unimodal. QED (classical).

**Grounded obstruction:** `grep` of the pinned Mathlib finds ZERO unimodal/log-concave SEQUENCE
theory (one stray "unimodal" in Analysis/Convex/Quasiconvex.lean; no log-concave-sequence
lemmas). So the missing piece is a concrete reusable lemma — `symmetric-unimodal × symmetric-
unimodal = symmetric-unimodal` — NOT a research discovery. The leaf failed because it tried the
whole theorem inline; the lever is to conjecture + formalize THAT one lemma (which then also
feeds Type1LogConcave and generalizes to any codim-r type-1 ideal).

**Novel architecture move (the transferable insight): FRONTIER-TYPE DIAGNOSIS before budget.**
Before throwing agentic budget at a hard theorem, cheaply classify the obstruction
(Characterization-by-Obstruction, core): is the underlying math (a) DISCOVERY-bound (genuinely
open — no automated lever) or (b) FORMALIZATION-bound (classical, but a needed Mathlib lemma is
absent — lever = identify + MOVE_CONJECTURE the specific missing reusable lemma, a bounded
formalization the leaf CAN do)? The diagnostic is two cheap probes: the generating-function /
structural reduction + a Mathlib-coverage grep. P2-unimodal is squarely (b). This turns "the
leaf can't prove the theorem" into "point the leaf at the missing lemma" — and the lemma is
reusable across the whole P2/P3-P8 family. The pattern-action-contract carrier for such ticks:
nearest universal op = core_01/Characterization-by-Obstruction; nearest pec = pec_a (auxiliary
object); required artifact = the named missing lemma + a Mathlib-absence receipt.

## Move-algebra made non-commutative-first (2026-06-02) — Barrington reorder, shipped
Forward change to the deferral/cost policy + residual→lever map (per this seam's `update_post`),
derived from the Barrington isomorphism (constant-width branching programs are universal because
AND is a commutator in the non-solvable S₅ — at bounded resource, power is in the
NON-COMMUTATIVITY of the composition, not the width). Operationalized in
`src/ztare/leanmill/solver/governed_dag_search.py`, NOT as a passive label (the session already
showed passive op-vocabulary adds ZERO lift) but as a behavior change with a self-test:
- **`MOVE_CLASS` + `move_class()`**: the move menu is typed into COMMUTATIVE (native_hammer,
  claude_warm, cold_shot, frontier — attack the goal as-stated with more/wider resource,
  structure-preserving, collapsing) vs NON_COMMUTATIVE (`conjecture_lemma` — invent / generalize
  / reframe / decompose; changes the obligation structure, spawns a typed sub-target). The
  non-commutative core is the "commutator" that builds depth.
- **Policy REORDER (`move_policy`)**: once a commutative move has FAILED on a node, the policy
  promotes the non-commutative `conjecture` move AHEAD of the remaining (more expensive)
  commutative moves — escalate COMPOSITION STRUCTURE, not resource. A fresh node still tries the
  free commutative hammer first (cost order intact); the heavy commutative moves remain as later
  fallbacks once the core is also tried. A reorder, not a removal.
- **Typed lever (`residual_to_lever`)**: a node that died still spraying (commutative-only) emits
  an `escalate_noncommutative` lever — "add a structure-changing move, NOT more budget/width" —
  whereas a node that already spent the non-commutative core points at a genuine wall (new math /
  stronger prover). Return tokens stay in the stable enum (escalation rides in `next_lever`), so
  consumers of `root_resolution` are unaffected.
- **Grounding + falsifier**: directly supported by this session's kernel-arbitrated P1 ablation
  (commutative spraying 0/4 vs invention 4/4 at comparable budget). Falsifier: on a VPS A/B at
  fixed budget, if closure rate tracks budget/width as much as the non-commutative reorder, the
  isomorphism is poetry and the reorder should be reverted. Until that A/B runs, this is a
  grounded-but-unconfirmed policy change (self-test green: 38/38, incl. 6 new Barrington tests).

## Barrington reorder — falsifier RUN on exogenous Mathlib rows: NULL on this distribution (2026-06-02)
Ran the falsifier (`scripts/public/control/leanmill/barrington_evidence.py`) on the live local
pair (repl v4.29 + the v26 LeanHammer-baseline Mathlib project), apparatus CERTIFIED first
(substrate positive control + verifier soundness `1+1=3`-rejected + battery adequacy `1+1=2` +
codex provider liveness — so the result is ADMISSIBLE, not a dead-instrument artifact). Targets =
a pre-registered slice of EXOGENOUS Mathlib-sourced benchmark rows (not self-invented → no
evidence-distribution gaming). Three arms isolate non-commutativity from raw LLM power: C1
deterministic battery (commutative spray) / C2 agentic-direct (LLM, prove as-stated) / N
agentic-invent (LLM, the MOVE_CONJECTURE core). Every closure kernel-gated (#print axioms ⊆
allowlist).

Result (6 rows): C1 battery closed 4/6 (incl. all three hard-looking V28C measure-theory rows —
`hammer` reproduced the hand proofs). Frontier (C1-open) = 2 rows. On BOTH, **C2 (direct) AND N
(invent) closed — N_gt_C2 = 0**. N even did MORE work for the same result (3 and 5 invented
lemmas; 101s/128s vs C2's 85s/105s).

**Honest reading (not laundered):** the Barrington separation does NOT appear on this
distribution — where the battery fails here, raw agentic iteration (C2) suffices and invention
adds zero lift (and costs more). This does NOT confirm the reorder; it BOUNDS the claim: the
non-commutative advantage is specific to INVENTION-BOUND frontiers (a direct proof infeasible in
budget, but a decomposition into NOVEL lemmas tractable) — e.g. the APN P2-unimodal class where
the session saw commutative 0/4 vs invention 4/4. The v26 rows are multi-step-but-known, not
invention-bound, so they cannot discriminate. Positive by-product: the agentic invent path is
VALIDATED as correct (it produced kernel-clean multi-lemma decompositions), just not necessary
here. **Status of the shipped reorder: grounded only on the APN-class frontier; the decisive
A/B needs the APN corpus on the VPS (the script is general — point `--project-dir`/`--rows` at
it). Until then the reorder is a scoped, self-test-green policy change, NOT an empirically
confirmed win.** A guardrail this run surfaced: promoting invention where direct suffices is
wasteful, so the reorder's trigger (only AFTER a commutative move has FAILED) is the right gate —
do not promote conjecture ahead of an un-tried cheap direct attempt.

## Reorder REFINED to the hybrid ladder (2026-06-02) — v26 finding folded in
The v26 null showed strong-direct (agentic prove-as-stated) closes the frontier rows MORE
CHEAPLY than invention (it was faster and used fewer lemmas). So the first reorder (promote
`conjecture` the moment the FREE battery fails) was too aggressive — it would skip the one
cheap strong-direct attempt that often suffices. `move_policy` now encodes the evidence-grounded
ladder: **free probe (native_hammer) → strong direct (claude_warm) → INVENT (conjecture) →
resource-scaling (cold_shot/frontier)**. Invention is promoted ABOVE the width/bigger-prover
moves (the Barrington residue: width ≠ substitute for the commutator move) but BELOW the single
strong-direct attempt (the v26 evidence: don't pay for invention where direct works). Self-test
green (4 ladder cases + lever typing). Still pending the APN-frontier A/B to confirm the
INVENT>resource half on an invention-bound target; the strong-direct-first half is already
evidence-backed.

## DECISIVE: Barrington reorder REFUTED on the APN frontier → REVERTED (2026-06-02)
Ran the Direct-vs-Invent head-to-head on the APN invention-bound frontier (the testbed the
v26 rows couldn't provide), apparatus-certified with an ADEQUACY GATE + a no-op-dispatch guard
(added after a first run where a 633s P1 run tripped a transient codex rate-limit and starved
the follow-ups → unedited probes that the harness wrongly read as 'open'; the guard now detects
an untouched-`sorry` probe = apparatus-void, backs off 75s + retries, and refuses a frontier
verdict unless a known-closable control closed). Hardened run, all kernel-arbitrated:
- `ProblemP2CoeffFormula` (control): **both arms closed, engaged** (106s) → adequacy ✓.
- `ProblemP2Type1Unimodal`: DIRECT + INVENT **both engaged ~17min, both open** (1031s).
- `ProblemP2Type1LogConcave`: both engaged, **both open** (1634s).
- VERDICT: adequacy_ok=True, **signal=0**, both_closed=0.
Plus the earlier admissible P1: **DIRECT closed kernel-clean, INVENT errored** (invent uniquely
LOST), and the v26 null (invent tied direct, slower, more lemmas).

**Tally across every admissible target: the forced INVENT mode NEVER beat a strong DIRECT
agentic attempt** — it tied, lost (P1), or both failed (the genuine Type1 frontier, which is
beyond both arms at this budget — the multi-lemma-DAG unimodality math already pinned). RCA:
a capable direct prover already invents inline (`have`-steps) as needed, so a separate forced
invent/decompose mode is redundant (and slower/error-prone). **Barrington's one falsifiable
residue does not cash out operationally here.**

**Action (no laundering):** the move_policy reorder that promoted `conjecture` ahead of
resource-scaling moves is **REVERTED** — the menu keeps its plain order (free probe → strong
direct → resource → invent last), invention is NOT promoted. Kept as NEUTRAL DIAGNOSTICS:
`MOVE_CLASS`/`move_class` (accurate metadata) and the `escalate_noncommutative` lever (now
flags the failure mode without prescribing invention). The durable lever is a strong direct
agentic prover under the existing governance — NOT a Barrington-motivated move-algebra reorder.
Self-test green (regression test `plainorder_invent_not_promoted` locks the non-promotion in).

## CORRECTION (2026-06-02, self-audit): the above is NON-PROBATIVE — "refuted" RETRACTED
Design audit of the Direct-vs-Invent test found three flaws that void it as a test of the
strong claim (invention/structure-change vs direct):
1. **Nested, non-independent arms.** `solve_leaf(decompose=True)` runs the DIRECT attempt
   FIRST, then a decompose fallback only if direct fails. So INVENT ⊇ DIRECT: "both closed"
   means INVENT closed via its direct round (invention never ran); the arms differ ONLY when
   round-1-direct fails. The test actually measured "does the decompose-fallback rescue a
   direct failure?", not "invent vs direct".
2. **n=1, stochastic.** codex is non-deterministic. The "P1: DIRECT closed, INVENT errored"
   datum is VARIANCE (INVENT's own direct round erred that run), not "invent lost" — my tally
   of that as a signal was wrong and is retracted.
3. **No discriminating-regime target.** Targets were either easy (direct closes → invention
   never runs) or beyond-both (Type1 frontier). None in the "direct fails but a bounded
   invented lemma closes" regime where the contrast could appear.
**Corrected status:** invention's value is UNTESTED, not refuted. The reorder REVERT still
stands, but on CONSERVATIVE grounds (ship no behavior change without POSITIVE evidence), not as
a refutation. A clean future test needs: independent arms (direct-only vs invent-WITHOUT-direct-
fallback), n≥3 for stochasticity, and a discriminating target (e.g. the specific missing
reusable lemma below, not the whole theorem). Apparatus discipline held (adequacy gate + no-op
guard made the run admissible); the ERROR here was experiment DESIGN, caught by self-audit.

## Probe: Barrington + meta-language applied to the unimodality crux (2026-06-02)
Operator asked whether the Barrington isomorphism / the research-ops meta-language help on the
actual frontier (the missing symmetric-unimodal product-closure lemma). Result:
- **Barrington = correct diagnostic that self-rejects on the substrate.** Unimodality's deepest
  classical proof (Stanley) imports a NON-COMMUTATIVE structure (sl₂ action / hard Lefschetz) —
  the Barrington pattern exactly. But Mathlib has only `Algebra/Lie/Weights/*` and ZERO
  Gaussian-binomial-unimodality / hard-Lefschetz / sl₂-rep machinery, so that route is out of
  formalization reach. The substrate INVERTS Barrington's lesson: in the bounded-FORMAL setting
  the COMMUTATIVE/elementary route is the lever (it's what Mathlib has). Clean close to the
  Barrington thread — non-commutative power is real in abstract math, doesn't cash out in Lean.
- **meta-language = planning scaffold** (reformulation → transfer → crux), used to localize, then
  refined into the elementary 3-sub-lemma route below. Not a solver booster.
- **Crux collapsed by grounding:** SYMMETRY of the product is ~free via
  `Polynomial.mirror_mul_of_domain : (p*q).mirror = p.mirror*q.mirror`. The genuine missing piece
  is UNIMODALITY of the product. Elementary route (Mathlib has `coeff_mul` + `Mirror`):
  (1) symmetric-unimodal = nonneg sum of symmetric interval-atoms; (2) atom×atom = trapezoid
  (unimodal, via convolution); (3) same-center sum of symmetric-unimodal stays so.
- **Highest-yield target (grounded, guided):** formalize "product of two symmetric-unimodal
  nonneg polynomials is unimodal" via that decomposition — NOT the whole Type1Unimodal theorem.
  Closing it = a new reusable lemma Mathlib lacks that unlocks the P2/P3–P8 family (the solver-
  lane-manufactures-missing-math capability). Also the proper discriminating test the Barrington
  post-mortem required (hard-but-bounded, guided route, n≥3, real substrate).

## CORRECTION (2026-06-02, operator-caught): route prescription was an absence=wall prejudgment
Operator: "why do we need Mathlib? perhaps the non-commutative route was faster." Correct on both:
- **Absence ≠ wall, and it's self-undermining.** I gated the proof ROUTE on "what Mathlib already
  ships" — the same absence=wall error, and it defeats the very "solver manufactures missing math"
  thesis (if the lane can build the unimodality lemma it can build the algebraic scaffolding too).
- **The non-commutative route likely doesn't need heavy machinery.** The LIGHTWEIGHT Stanley
  linear-algebra method = an explicit up-operator `U : Vᵢ→Vᵢ₊₁` injective below the middle ⇒
  `dim Vᵢ ≤ dim Vᵢ₊₁` ⇒ unimodal. That's finite-dim linear algebra (rank/injectivity) — which
  Mathlib HAS — NOT "hard Lefschetz" as a named theorem. Meanwhile the "elementary" route is
  index-bookkeeping LLMs are bad at. No evidence the elementary route is faster; I prejudged.
**Redesigned experiment (staged, not yet run — operator holding):** keep TARGET guidance (the
compile-verified crux `prod_symm_unimodal_is_unimodal` / `interval_conv_unimodal` in
`projects/atlas_lean_2026_05_29/CruxScaffold.lean`), DROP the route prescription. Two ROUTE ARMS,
n≥3 each, measure closure-rate + proof-length:
  A combinatorial/commutative (atom decomposition + convolution);
  B algebraic/"non-commutative" (up-operator + Mathlib linear algebra).
This is the LEGITIMATE Barrington test (does the algebraic route win on a real target?) — done
right (route-open, real substrate, n≥3) — and a genuine manufacture-missing-math demonstration
either way. Supersedes the prior "elementary route is the lever" framing (that was a prejudgment).

## FORWARD PROGRESS (2026-06-02): the engine lemma PROVEN in-thread, kernel-clean
Operator held the multi-hour agentic run; per "do the forward work yourself", I proved the base
engine of the unimodality crux DIRECTLY (compile cycles against the live atlas_lean substrate, no
agentic dispatch). `interval_conv_unimodal : Unimodal (a+b) (conv (ind a) (ind b))` — the
convolution of two flat indicator intervals (the trapezoid) is unimodal — KERNEL-CLEAN, axioms ⊆
{propext, Classical.choice, Quot.sound}, no sorryAx. Mathlib has zero unimodal-sequence theory, so
this is a genuinely new reusable lemma (solver-lane-manufactures-missing-math, done by hand here).
Key insight that collapsed it: the UNIFIED CLOSED FORM `conv (ind a)(ind b) k = min a k + min b k
- k + 1` for `k ≤ a+b` (one formula for rising/plateau/falling), reducing unimodality to `omega`
arithmetic. Artifact: `projects/leanmill_experiments/unimodality_engine.lean`.
Remaining path to APN Type1Unimodal (clear, bounded): (1) inductive step — conv of a
symmetric-unimodal sequence with a flat interval stays symmetric-unimodal; (2) bridge —
pureOSequence of a type-1 ideal = iterated conv of intervals (via the already-closed
ProblemP2CoeffFormula); (3) assemble. The hardest-to-find piece (the engine + closed form) is done.

## Reframe (2026-06-02, operator): the governed harness IS the frontier prover
Operator: "isn't our solver harness via governed DAG + all the capabilities a frontier Lean prover
on its own right" + "why fork LeanCopilot (dated) — won't use SOTA". Correct, and it dissolves the
"external prover dark = gap" framing (mine, wrong):
- A frontier prover is a SYSTEM that closes hard goals, not a trained checkpoint. Ours = governed
  best-first DAG search + SOTA general-model agents (GPT-5.5/Opus) iterating against the kernel +
  premise-shelf retrieval + conjecture/decompose + proof cache + MNC + no-false-closure governance.
  That is MORE than DeepSeek-Prover-V2 / LeanCopilot (each is ONE move with NO governance).
- Don't fork LeanCopilot: it's a frozen dated tactic-suggester; the agentic leaf (frontier model +
  kernel feedback + retrieval + invention) subsumes it AND auto-upgrades with the subscription model
  (no retrain). Forking = rebuilding a weaker component.
- Roadmap locks onto the HARNESS (enable the leaf, strengthen shelf/decompose/cache/calibration/
  governance), NOT external bolt-ons. deepseek_v2/leancopilot = optional diversity moves only if
  proven to add lift; no GPU infra, no fork. Matches the architecture thesis (environment > trained
  -prover compute). The §6n leaf-enable regression validates exactly this.

## Harness strengthening round (2026-06-02): leaf-on + Arc-H calibration + cache reuse
Operator bar for every harness change: NON-IATROGENIC (no regression/false-closure) AND generates
LIFT. Applied honestly:
- **Agentic leaf ON (§6n flip, default-on, reversible `ZTARE_AGENTIC_LEAF=0`)**: VALIDATED through
  the real governed worker — closed `SPEC_svd_schatten_svd_8` ("agentic_leaf closed by codex",
  compile_ok=1) with no regression. Empirical ground truth: the harness has closed 11 governed
  proofs (SPEC corpus) — it IS a frontier prover (the move generators are SOTA subscription agents).
- **Arc-H est_p_close calibration** (`solver/move_calibration.py`, opt-in `ZTARE_CALIBRATE_PRIORS=1`):
  replaces the stub move priors with a Beta posterior (stub = prior mean) measured from
  `solver_lane_attempts.db`. NON-IATROGENIC FLOOR: a FREE move (native_hammer, cost 0) is never
  down-weighted (always worth trying — flooring at stub); calibration only down-weights COSTLY dead
  moves (live: cold_shot 0.30→0.092 from 0/18) — that is the lift (stop spending budget on a 0/18
  move so the policy reaches the productive ones). Small samples stay near the stub (no laundering).
- **Proof-cache reuse** (`run_governed_dag_search(cache=, cache_verify=)`, opt-in `ZTARE_PROOF_CACHE=1`):
  bank kernel-verified lemmas to a persistent jsonl + reuse across rows/runs (compounding lift).
  NON-IATROGENIC GUARD: a cache hit is RE-COMPILED in the new context via `cache_verify` before
  closing — a failed re-verify is a cache MISS, never a closure (no-false-closure preserved on
  reuse; the prior trust-the-cache path was a latent false-closure hazard). Self-test proves a
  rejecting verifier blocks the false closure.
All three are FLAG-GATED (opt-in, reversible, default behaviour byte-unchanged) and self-test green.
The lift is by-construction PLAUSIBLE but not yet A/B-PROVEN — the flags exist precisely to run the
flag-on-vs-off regression (closure-rate / efficiency) before flipping defaults.
**Remaining list items, honest verdict:** premise shelf = built + leakage-quarantined, but lift is
UNMEASURED → don't pull forward without a measurement. Conjecture/decompose = lift is UNPROVEN with
ANTI-evidence (the Barrington exploration showed unguided decompose ≈ direct, sometimes slower) →
do NOT pull forward as a lift lever; it stays as the structure-changing move of last resort only.

## A/B CONFIRMED → calibration + cache defaults flipped ON (2026-06-03)
Mechanism-level A/B (`projects/leanmill_experiments/ab_calibration_cache.py`, deterministic, REAL
calibrated priors): (1) CALIBRATION lift — tight budget, only-frontier-closes row: OFF wastes 4
units on the dead cold_shot ⇒ frontier unaffordable ⇒ DEFERS; ON skips cold_shot ⇒ frontier
affordable ⇒ CLOSES. ON closes a row OFF cannot. (2) NO-REGRESSION — ample budget: both close, ON
spends ≤ OFF. (3) CACHE lift — recurring lemma reused with 0 moves, still kernel-closed. All three
TRUE. Caveat: this proves the lift EXISTS + is non-iatrogenic; real-world MAGNITUDE depends on
regime frequency (how often budget-tight + cold_shot-blocked, how often lemmas recur) — observable
via telemetry. Since lift is proven and regression ruled out, defaults flipped ON in
solver_lane_worker (ZTARE_CALIBRATE_PRIORS / ZTARE_PROOF_CACHE default on, =0 reverts), matching
the leaf. The three harness levers (leaf, calibration, cache) are now live + reversible.

## Adaptive-budget stall-defer: TRIED → iatrogenic (regression-caught) → REVERTED (2026-06-03)
Tier-1 candidate: defer a node that stalled N no-progress moves to free budget for progressing
nodes. Implemented (stall_count + stall-defer in move_policy + threading) — and the self-test
regression IMMEDIATELY caught it iatrogenic: stall_limit=3 deferred the root BEFORE its late
productive move (conjecture is 5th in MOVE_ORDER), breaking the conjecture-path test (would skip
frontier/conjecture on a hard node = lost closures). Any non-iatrogenic guard (don't defer until
the structural move is tried) collapses stall-defer into plain move-exhaustion → NO net lift. The
safe form of "prioritize progressing nodes" already exists (GP-187 `PROGRESS_WEIGHT` frontier
boost). VERDICT: fails the non-iatrogenic bar → fully reverted, all self-tests green. Good outcome
— the regression did its job (caught harm before shipping). Also corrected the Tier-2 framing:
the "decompose/stepwise/orchestration negatives" are NON-PROBATIVE/confounded/scoped, i.e.
lift-UNPROVEN, NOT clean negatives — recorded as such in the architecture "Open Areas" roadmap
(needs clean tests, not dismissal). No clean negatives exist in the harness roadmap.

## Adaptive budget DONE RIGHT: timeout-aware leaf retry (2026-06-03)
Operator: "did we just do a naive implementation [of adaptive budget]?" Yes — the stall-defer was
naive (skipped late moves). The node-level adaptive allocation is already done (PROGRESS_WEIGHT).
The genuinely-untapped, NON-NAIVE variant is at the LEAF: an agent dispatch that RUNS OUT OF TIME
is under-budget, not a real negative — `solve_leaf` previously read the unfinished probe as "open"
(the documented under-budget false-negative; APN P2 hit ~400s timeouts; closure_ledger budget_suspect).
FIX (agentic_leaf): `_dispatch_timed_out` detects the runtime's "timed out after Ns" marker; on an
OPEN result whose dispatch timed out, retry ONCE with TIMEOUT_RETRY_FACTOR×budget (both direct +
decompose). NON-IATROGENIC: fires only on a detected timeout; the kernel verify still gates (no
false closure); a genuine failure (no timeout marker) is NOT retried. Self-test: recovers a timeout
(closed+retried, rounds=2); a genuine failure is not retried (rounds=1). This is the adaptive budget
the operator's instinct pointed to — addresses the recurring apparatus trap (under-budget read as a
science negative), not a redundant node-defer.

## FRONTIER CLOSURE (2026-06-03): leanmill closed ProblemP2Type1Unimodal kernel-clean
Re-ran the APN frontier with the upgraded harness (timeout-retry + the no-op/backoff guard, on the
validated atlas_lean v4.29 substrate). Result: control `ProblemP2CoeffFormula` both arms closed
(adequacy ✓); **`ProblemP2Type1Unimodal`: DIRECT failed (engaged), INVENT CLOSED (engaged), 3375s.**
INDEPENDENTLY re-verified: compiles, sorry-free (30KB of invented helper lemmas), axioms ⊆
{propext, Classical.choice, Quot.sound}. Faithful (the IsUnimodal statement is PINNED in the corpus
— no circular-UnimodalOn laundering), unleaked (solve_leaf attaches no retrieval shelf; Mathlib has
zero unimodal-sequence theory, nothing to leak). Artifact:
projects/leanmill_experiments/closure_Type1Unimodal_2026_06_03.lean.

**What this means (disciplined):**
- VERIFIED FACT: the harness manufactured a kernel-clean proof of a Mathlib-absent frontier theorem
  (type-1 pure O-sequence unimodality) — the world-class "manufactures missing math" capability, on
  a real target, not a toy. This is n-independent (the proof exists + verifies).
- SUGGESTIVE (n=1): INVENT (decompose/invent helper lemmas) > DIRECT on this invention-bound target
  — the first PROBATIVE discriminating data point FOR invention (adequacy held, both engaged, clean
  closure). REVERSES the earlier "invention non-probative/untested" pessimism — but n=1 + codex is
  stochastic, so the INVENT>DIRECT *claim* needs n≥3 to firm (the prior "both open" was under-budget
  at 400s/arm; this run engaged 3375s — budget, not the idea, was the prior blocker).
- The earlier Barrington-reorder revert was conservative-correct at the time (no evidence then); this
  is the discriminating evidence that was missing. Invention-as-a-leaf-capability is now EVIDENCED on
  the frontier; whether to RE-promote the conjecture move in the DAG policy is a separate n≥3 question.

## Scoping the Type1Unimodal closure + Barrington-reorder reconsideration (2026-06-03)
SCOPING (operator: "but APN also solved it right?"): YES — the corpus is from alphaproof-nexus-
RESULTS; targets carry reference helper-DAGs (32-156 decls). So Type1Unimodal has an upstream
reference solution — this is NOT an open-problem closure. What ours IS: INDEPENDENT (solve_leaf
attaches no retrieval shelf → agent never saw the reference helpers) + kernel-clean + faithful
pinned statement = a CAPABILITY demonstration (the harness manufactures a valid independent proof
of a real invention-bound theorem). Caveat: "independent of retrieval" ≠ "no prior exposure" — a
general model may carry training-data familiarity (unknowable). Do NOT frame as novel math or
beating AlphaProof.

BARRINGTON-REORDER RECONSIDERATION (operator-requested): the new evidence (INVENT closed
Type1Unimodal, DIRECT failed) confirms invention as a frontier lever — but it is delivered by the
LEAF's decompose mode (decompose=True, running in the claude_warm DAG move), which is ALREADY
ACTIVE. The reverted DAG conjecture-MOVE reorder is a DIFFERENT mechanism (spawns a sub_goal NODE)
and is largely SUBSUMED by the leaf's internal decompose for whole-leaf invention. HOWEVER it has
a DISTINCT untapped benefit the leaf lacks: a spawned sub_goal node is CACHED + reusable across the
P2/P3-P8 family (which shares the symmetric-unimodal machinery); leaf-internal `have`s are not
banked separately. VERDICT: revert STANDS for now (immediate invention capability is in the leaf,
evidenced); the DAG conjecture-move reorder moves from "reverted/unproven" to "plausible via
FAMILY-COMPOUNDING, worth a clean test" — test = run the DAG with conjecture-promotion over the
P2/P3-P8 family + measure cross-target cache reuse. NOT blindly re-promoted (n=1 + speculative
compounding). Replication #2 of Type1Unimodal (n≥3 for INVENT>DIRECT) running.

## n≥3 + family-compounding results (2026-06-03)
TWO clean, opposite-direction results from parallel runs:
1. INVENT>DIRECT did NOT replicate. Rep#1 Type1Unimodal: DIRECT failed, INVENT closed (signal=1).
   Rep#2: BOTH closed (signal=0) — DIRECT also closes with adequate budget. So the n=1 signal was
   stochastic/budget, NOT a real invent-vs-direct gap. BUDGET (timeout-retry) is the lever. The
   Barrington reorder STAYS REVERTED — the n≥3 replication caught the false n=1 signal. (The
   Type1Unimodal CLOSURE is robust: n=2.)
2. FAMILY-COMPOUNDING LIFT CONFIRMED + verified. LogConcave A/B: baseline (from scratch) OPEN after
   1201s; treatment (with the proven shared machinery from the Type1Unimodal closure prepended)
   CLOSED kernel-clean in 1064s (axioms ⊆ allowlist, reused the shared lemmas 20×). A sub-lemma
   family proven ONCE unlocked a sibling that from-scratch could not close — faster. This is the
   world-class property: the harness's outputs COMPOUND (a growing library of reusable proven
   lemmas unlocks new theorems). n=1 ⇒ suggestive, needs replication, but verified-genuine +
   directionally strong. Artifact: VPS Lift_treatment.lean.
REFRAMING: the lever is NOT "invention beats direct" (dead at n=2) — it is COMPOUNDING (bank the
family machinery, provide it to siblings, premise-shelf style). The clean mechanism that WORKED is
PROVIDING proven shared lemmas to a sibling (not relying on byte-identical cache hits). Next: firm
the compounding lift (n≥3) + wire the banking→provisioning loop (the proof cache / premise shelf as
the compounding engine).

## CORRECTION (2026-06-03, operator): "INVENT>DIRECT dead at n=2" was too strong
Operator: "maybe barrington helps when direct cannot — maybe [Type1Unimodal] was too easy." Correct.
Rep#2's both-closed does NOT refute INVENT>DIRECT — it shows Type1Unimodal is NON-DISCRIMINATING
(direct can close it), so it can't reveal the gap. INVENT>DIRECT is UNTESTED, not dead. The
discriminating regime is narrow: harder than Type1Unimodal (direct succeeds) but easier than
LogConcave-from-scratch (both arms failed without shared machinery) — we haven't hit a target where
direct RELIABLY fails but invent closes. So: Barrington reorder stays reverted (no positive evidence
yet) BUT the door is NOT closed — a proper discriminating target (e.g. LogConcave WITH shared
machinery: does direct-with-machinery fail while invent-with-machinery closes?) is the clean future
test. The CONFIRMED lever remains family-compounding; firming that (n≥3) is the current one-by-one step.

## CONTAMINATION caught + CLEAN-CAPABILITY result (2026-06-03, operator-caught)
Operator: "is the AI using the APN proofs? they're in the repo / public." CRITICAL — I'd only
checked the premise shelf (not attached) and MISSED the in-repo SOLVED reference:
projects/gp_spectral_apn_seed_2026_05_28/apn_repo/APNOutputs/.../hilbert_functions_2.lean (602 lines,
sorry-free). A codex sandbox probe (workspace-write, --cd atlas_lean) READ it → the reference was
REACHABLE during every prior closure ⇒ those closures were CONTAMINATION-SUSPECT (my "independent"
framing RETRACTED). Mild counter-evidence: our proof shares ZERO lemma names with the reference (not
a verbatim copy).
CLEAN TEST (clean_capability_test.sh): quarantined the SOLVED references (apn_repo/gates/gates_spectral
→ /tmp, verified no Type1 reference remained; kept the sorried candidate=target), re-ran. RESULT:
Type1Unimodal CLOSED kernel-clean (independently re-verified: sorry-free, axioms ⊆ {propext,
Classical.choice, Quot.sound}) in 466s — FASTER than the contaminated runs (argues the reference
did NOT help). Control closed (adequacy ✓). So: IN-REPO LEAKAGE CHANNEL RULED OUT — the capability
is real, not in-repo copying. RESIDUAL CAVEAT: training-data exposure (APN is public, arxiv
2605.22763; codex cutoff vs APN recency unknowable) — the standard public-benchmark caveat.
PATH TO A FULLY-CLEAN CAPABILITY CLAIM: (1) ✅ in-repo ruled out; (2) quarantined BATCH over the APN
family (P3-P8) → clean closures at scale; (3) a NOVEL non-public target → rules out training-data.
MECHANIZATION TODO: barrington_apn / any APN capability run must QUARANTINE references by DEFAULT
(contamination must not silently recur) — make clean_capability_test's quarantine the default path.

## Governance: reference-leakage gate shipped (2026-06-03) — #3 mechanized
`src/ztare/leanmill/solver/reference_leakage_gate.py`: detects SOLVED (sorry-free) in-repo .lean
references that define a target + are reachable by the agent's workspace-write sandbox (the SECOND
leakage channel, beyond the premise shelf), and a `clean_capability(...)` context manager that
quarantines them for a run + restores on exit (even on error). Excludes the sorried candidate (the
target) + agent-local files + our own experiment artifacts. Self-test 8/8. This is the governance
counterpart to the solver levers — capability runs are now leakage-clean BY DEFAULT for the in-repo
channel (training-data channel still needs a novel/non-public target). Don't neglect governance:
this closes the exact gap the operator's "is it using the proofs?" question exposed.
