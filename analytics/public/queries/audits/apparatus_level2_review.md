# Apparatus Level 2 Review — claim × falsifier-test backlog

Generated: 2026-05-06T18:29:06.227407+00:00

## Frame

This document is the strange-loop / Level 2 layer applying invert/compress/disagree to ZTARE's claims about ITSELF. Every row below is a concrete claim the apparatus makes plus a falsifier-test Codex can run. **A claim without a runnable falsifier is suppressed.**

## Auxiliary data summary

- failure_log_entries: 9
- codex_panel_rows: 22
- last_known_novelty_rate: 0.0
- missing_primitives_backlog_size: 5696
- v3_checkpoint_size_kb: 2177.3
- deidentified_retry_outputs: 0

## Backlog (10 apparatus claims)

### 1. claim_typed_endpoint_helps

**Claim:** The typed-endpoint pack increases the verified-patch rate vs. cold LLM nomination.

**Falsifier design:**

> Take the last 20 closure attempts. Split by whether they used typed-endpoint pack. Compare VERIFIED-rate. If typed-endpoint-rate ≤ cold-LLM-rate (within 1 SE), claim is false.

**Data required:**
  - typed_endpoint_failure_log.jsonl
  - Codex-marked panel CSV (pre-typed-endpoint era)

**Predicted outcome if claim is TRUE:** typed-endpoint VERIFIED-rate ≥ 2x cold-LLM

**Predicted outcome if claim is FALSE:** rates within noise; typed-endpoint is theater

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 2. claim_lemma_scout_helps

**Claim:** The mathlib_lemma_scout's PDE-shape index (SOBOLEV / HOLDER / etc.) actually surfaces lemmas Codex would have missed.

**Falsifier design:**

> Sample 10 verified patches Codex shipped this week. For each, ask: did the scout surface the actual lemma used? If hit-rate ≤ 20%, the index is too coarse to be useful.

**Data required:**
  - list of mathlib lemmas surfaced via scout in last N runs
  - Codex's pre-scout vocabulary (which lemmas he'd cite spontaneously)

**Predicted outcome if claim is TRUE:** scout hit-rate ≥ 50% on real verifications

**Predicted outcome if claim is FALSE:** hit-rate ≤ 20%; scout is decorative

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 3. claim_v3_gnn_predicts_real

**Claim:** The v3 GNN lemma-relevance ranker (hit@10 = 0.379 on spine-only test set) generalizes to mathlib lemmas Codex actually uses in production.

**Falsifier design:**

> Take the last 20 verified-patch lemma references. For each, see if the v3 ranker would have surfaced it in top-10. If hit-rate < 0.20 (vs claimed 0.38), there's a spine→production distribution shift that invalidates the metric.

**Data required:**
  - v3 ranker checkpoint
  - list of lemmas used in last N Codex-shipped patches

**Predicted outcome if claim is TRUE:** production hit@10 ≥ 0.30 (mild degradation)

**Predicted outcome if claim is FALSE:** production hit@10 ≤ 0.10; spine eval was overfit

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 4. claim_idea_feliz_better_than_novelty

**Claim:** Idea-feliz produces actionable insights at a higher rate than the deprecated novelty-nomination prompt (0/22).

**Falsifier design:**

> Score Codex's idea-feliz panel using the same vocabulary as the novelty panel (already_have | novel_plausible | wrong | trivial). If idea-feliz novelty_rate ≤ 5% (matching novelty-prompt floor), claim is false; the apparatus shifted the slogan, not the substance.

**Data required:**
  - Codex-marked CSV with idea-feliz verdicts
  - the 0/22 baseline from novelty-nomination Codex panel

**Predicted outcome if claim is TRUE:** idea-feliz novelty_rate ≥ 30%

**Predicted outcome if claim is FALSE:** novelty_rate < 5% — same theater, new costume

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 5. claim_failure_log_compounds

**Claim:** Stage 4 failure-category accumulator changes apparatus behavior over time (later runs avoid earlier failure modes).

**Falsifier design:**

> Bin failures by week. Check if the SAME (target, field, patch_class) triple's failure category SHIFTS over weeks. If the same triple keeps failing in the same category, the accumulator does NOT compound — it's just a write-only log.

**Data required:**
  - typed_endpoint_failure_log.jsonl with timestamps

**Predicted outcome if claim is TRUE:** failure-category distribution shifts week-over-week

**Predicted outcome if claim is FALSE:** static distribution; log is bookkeeping not learning

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 6. claim_constraint_basin_is_accountant

**Claim:** The constraint-basin graph diagnostics are 5-10x as a proof-spine accountant per Codex's 2026-05-05 verdict.

**Falsifier design:**

> List every belief update Codex attributed to constraint-basin diagnostics in advisor_channel.md / F-rows. Count: how many led to a CONCRETE downstream action (Lean patch / rubric edit / scoping decision)? If <30%, the diagnostics are scout-only (1-2x), not accountant (5-10x).

**Data required:**
  - Codex's stated belief updates from constraint-basin runs
  - concrete actions taken on those updates (Lean patches, rubric edits)

**Predicted outcome if claim is TRUE:** ≥30% of belief updates produce concrete actions

**Predicted outcome if claim is FALSE:** scout signal that doesn't compound to action

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 7. claim_negative_prompting_expands_method_space

**Claim:** negative_prompting_wrapper.py surfaces genuinely different methods after typed-endpoint / gap-typed attempts stall.

**Falsifier design:**

> Sample the last 10 negative-prompting runs. Mark every method as already_considered | distinct_but_unusable | distinct_and_used. If <20% of runs produce at least one distinct_and_used method, the wrapper is not a closure tool; it is just brainstorming.

**Data required:**
  - analytics/queries/negative_prompting_runs/*.json
  - Codex verdicts on whether each method was already considered
  - downstream typed-endpoint / Lean / falsifier attempts spawned by those methods

**Predicted outcome if claim is TRUE:** ≥20% of runs spawn a concrete typed attempt or falsifier

**Predicted outcome if claim is FALSE:** methods are paraphrases or too vague to translate

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 8. claim_context_deidentifier_reduces_refusal

**Claim:** context_deidentifier.py's auto-retry inside typed_endpoint_pack reduces open-problem/conjecture refusal failures without changing the mathematical content.

**Falsifier design:**

> For every auto-deidentified retry, check whether the first response was an open-problem refusal and the retry produced a parseable Lean block or sharper CANNOT PATCH diagnosis. If success-rate ≤10% or the diff strips load-bearing assumptions, the tool is not useful for closure work.

**Data required:**
  - typed_endpoint_failure_log.jsonl refusal entries
  - typed_endpoint_runs/*_deidentified_response.md
  - audit diff from context_deidentifier.py for each retry

**Predicted outcome if claim is TRUE:** refusal-to-actionable rate ≥25% with no assumption loss

**Predicted outcome if claim is FALSE:** retry keeps refusing or deidentification corrupts context

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 9. claim_theory_builder_pivot_beats_estimate_chaining

**Claim:** When PDE estimate chaining stalls, a theory-builder pivot (new object / relaxed carrier / falsifier-first reframing) produces more closure progress than adding another local inequality adapter.

**Falsifier design:**

> Compare the next 10 stalled PDE targets after the pivot rule is in the mandate. If theory-builder turns do not produce either a typed source object, a new Lean constructor, or a concrete falsifier at a higher rate than estimate-adapter turns, demote the pivot rule to advisory rhetoric.

**Data required:**
  - closure attempts tagged ps_06 estimate-chaining vs. tb_01/tb_08 object-redefinition
  - Lean patches or explicit falsifiers produced after each tag
  - graph/workmap delta after the attempt

**Predicted outcome if claim is TRUE:** object/falsifier turns produce ≥2x actionable artifacts

**Predicted outcome if claim is FALSE:** no artifact-rate lift; pivot language is theater

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

### 10. claim_pde_preflight_cuts_lean_debug_time

**Claim:** Deterministic PDE estimate preflight (dimensional/endpoint gate + SymPy/asymptotic algebra + small Fourier/numeric falsifier when relevant) catches bad estimate narratives before Lean and improves time-to-useful signal.

**Falsifier design:**

> For the next 10 PDE-estimate attempts, tag whether preflight ran before Lean. Count (a) narratives killed by failed units/asymptotics, (b) Lean failures avoided, and (c) verified/source-constructor patches reached. If preflight does not kill at least one bad narrative or reduce repeated Lean-debug failures, demote it to an optional sanity check.

**Data required:**
  - analytics/queries/pde_workbench/*.json
  - research_areas/EXPERIMENT_TRACK_RECORD.md E/F rows tagged PDE preflight
  - Lean compile/failure logs for estimates attempted with vs without preflight

**Predicted outcome if claim is TRUE:** ≥1 bad narrative killed and fewer repeated Lean-debug failures

**Predicted outcome if claim is FALSE:** preflight adds delay without changing patch/falsifier outcomes

**Codex action:** mark this claim with one of:
  - `not_yet_tested` — falsifier not yet run
  - `confirmed` — falsifier ran, claim survived
  - `refuted` — falsifier ran, claim failed; remove from mandate
  - `untestable` — claim too vague to run as written; rephrase

---

## Honest scope of THIS document

- These are SCAFFOLDS. None of these falsifiers has been run yet by this script.
- The strange-loop recursion ends here: we don't ship Level 3 (apparatus testing the apparatus testing the apparatus).
- This file should be regenerated whenever the mandate adds a new apparatus claim (e.g. via `research_director_mandate.md` v1.2x updates).