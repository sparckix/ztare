# GP-246 — Governed DAG Proof-Search (ex-ante typed contract + best-first + deferral)

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
