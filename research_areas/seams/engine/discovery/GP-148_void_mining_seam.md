# GP-148 — Mining the Void (Seam)

> **Seam metadata** · `seam_id:` GP-148 · `track:` engine · `status:` draft (debate open; Stage 1 extractor delegated to backgroun · `last_updated:` 2026-05-09


**Status:** draft (debate open; Stage 1 extractor delegated to background Agent 2026-04-24)
**Owner:** analytics-infrastructure
**Depends on:** GP-053 (seam-spec invariant), GP-086 (cage/kernel hardening — derived_constraints as a feedback ledger), GP-104 (qualitative rubric / M-form alignment), INV-10
**Triggered by:** 2026-04-24 operator observation — the corpus of ~thousands of iteration-level debate logs + telemetry across gp023/gp060/gp061/gp072–gp085/gp088/gp100–gp147/ztare_on_ztare/sandbox_XX/mlh_* constitutes a proprietary dataset of high-dimensional LLM reasoning failures. Gemini-Pro synthesis: "you are sitting on the loss landscape of frontier LLMs attempting to conduct pure science."
**Visibility:** private (first-mover IP: the pattern catalog itself may be novel contribution)

---

## 1. Problem statement

Every iteration in every ZTARE project produces (score, weakest-point text, rationale text, failed-gate list, stagnation count, token usage). These are written to per-project artifacts and otherwise not aggregated. We traverse them iter-by-iter without ever looking across the corpus.

The user's insight: score fluctuations (17 → 65 → 25 → 78 → 28 → 63 → 88 typical pattern) are not noise. They are an algorithmic gradient. The highest-value signal lives in the catastrophic failures — iterations where the mutator was certain it had a breakthrough and the judge annihilated it. By focusing only on champions we succumb to survivorship bias.

## 2. Three assets hiding in the void (Gemini-Pro taxonomy)

### 2.1 Falsification Dictionary

A precise mapping from "mathematical intuitions frontier LLMs consistently hallucinate" to "judge verdict that kills them." Hypothetical finding: *logarithmic offset kills score in 80% of continuous-data runs.* If the corpus reveals specific mutations that systematically fail, they become hard algorithmic priors we can block in Phase A, saving hundreds of iters of compute.

### 2.2 Stagnation Signature

The exact sequence of score-deltas + token-deltas that PRECEDES a multi-iteration plateau. Allows us to predict and pre-empt stagnation before burning compute. Downstream: an early-warning hook that fires on detected stagnation signature, forces a charter-rotation or mutator-swap.

### 2.3 Judge Exploits

Edge cases where the judge's rubric can be Goodharted — where a structurally-deficient thesis scored high because it satisfied rubric dimensions without satisfying the underlying scientific question. Reveals which existing gates are doing decisive work vs. which are decorative.

## 3. Three uncomfortable truths (must be designed into the seam)

### 3.1 Oracle Illusion

Any pattern we mine is a pattern of "LLM-mutator behavior against LLM-judge rubric," not against physical reality. If we feed mined insights back into rubric design, we risk overfitting the entire architecture to the specific aesthetic preferences of (whatever model family is currently judging). Mitigation: cross-judge validation. For every candidate pattern, check whether it holds under judges from DIFFERENT model families (o3 + gpt-4.1 + gemini-pro at minimum). Patterns that hold only under one judge family are judge-specific, not structural.

### 3.2 Cost vs Yield

Running a heavy LLM over thousands of debate logs is expensive. ROI is positive ONLY if insights feed back into live constraint-shaping (derived_constraints.json ledger per GP-086), not static PDF reports. If Stage 3 produces insights that never reach the mutator prompt, it is wasted compute.

### 3.3 Lollapalooza Convergence

Hypothesis: 90+ scores correlate with 3+ orthogonal constraints satisfied simultaneously, not single-variable mutations. Mining should either confirm this (and inform mutator prompts to prefer multi-constraint satisfaction) or refute it (and change how we understand breakthroughs). This is TESTABLE from the corpus — check if champion theses at ≥90 share structural signatures distinct from iters at 70-80.

## 4. Simulated multi-turn expert panel debate

### Round 1 — opening positions

**Data Archaeologist (DA):** extraction first, analysis second. The corpus is siloed across `projects/*/debate_log_iter_*.md` and `projects/*/workspace/iteration_telemetry.jsonl`. Stage 1 is a recursive aggregator producing one canonical JSONL archive. Stage 2 is deterministic queries over that archive. Stage 3 is selective LLM meta-analysis ONLY on isolated inflection points (≥30-point score jumps/drops). Do not skip Stage 1 and let an LLM eat the whole corpus — that is a token-fire and produces low-signal output.

**Kernel Architect (KA):** GP-086 says cage/kernel gates live in `src/ztare/gates/`. Mining outputs that feed back into derived_constraints.json ledger count as kernel modifications and should be gated. Specifically: no pattern from mining should land in an active project's derived_constraints.json without a precision-bounded audit (e.g., N≥10 supporting iterations, cross-judge-validated per Oracle Illusion mitigation).

**Epistemic Auditor (EA, Munger role):** invert — how do we guarantee this mining exercise produces false confidence? Three ways. (a) Mine only champions, miss the 90% of data in failures. (b) Mine only one project, call it a pattern. (c) Feed patterns back into rubric without testing if they generalize to a held-out project. Architecture must do the opposite of all three: mine failures explicitly, cross-project validate any claimed pattern (≥3 projects), hold out at least one project as validation set when patterns are tested.

**Lean Contract Auditor (LCA):** whatever mining outputs become derived constraints, those constraints become part of the mutator prompt context. If the mutator trains on patterns extracted from the judge's historical behavior, the pipeline becomes a closed loop where the judge and the mutator coordinate through the derived-constraints layer. That is circularity. Mitigation: mined patterns are tagged `producer: "void_mining_gp148"` and auditable separately. Operators can disable them per-project if circularity is suspected.

**Operator (OP):** I want actionable output. A Falsification Dictionary is useful if I can read it and say "mutator will not propose this pattern again in gp145 SAW." A Stagnation Signature is useful if it triggers a loop-control escalation. Either the mined data lands as a specific, overrideable, date-stamped artifact, or it is decoration.

**Cost Controller (CC):** Stage 3 LLM analysis over N=5000 iterations at $0.05 per token-heavy analysis call = $250 per full sweep. Acceptable once per week; not acceptable continuously. Build with batched periodic runs, not live.

### Round 2 — response and counter-response

**DA → LCA:** circularity is real but not fatal if we separate extraction from prescription. Stage 1 extraction observes. Stage 2 analysis reports. Stage 3 LLM meta-analysis proposes. The operator decides what (if any) proposal reaches derived_constraints.json. Machine-in-the-loop, not machine-closes-the-loop.

**EA → KA:** agree on "no auto-injection into derived_constraints.json." Every mined pattern passes through an OPERATOR AUDIT GATE before it can affect mutator prompts. The audit gate is: (i) minimum iteration count (N≥10 supporting observations); (ii) cross-project evidence (≥3 projects exhibit the pattern); (iii) cross-judge validation (pattern holds under ≥2 judge model families); (iv) operator review with explicit accept / reject / defer. Reject = pattern discarded. Defer = pattern stays in a watch-list, re-evaluated after more data.

**OP → CC:** batched weekly is fine for Stage 3. Stage 2 should run after every significant gp140/gp145/gp147 iter (not continuously, but on demand when we want a fresh view). Stage 1 should run daily (cron or on-loop-completion hook).

**KA → LCA:** tag proposal. Mined patterns that pass the audit gate get `producer: "void_mining_gp148"` + `mined_from_projects: [<slug list>]` + `cross_judge_validated: [<judge list>]` + `audit_date: <YYYY-MM-DD>` + `audit_operator: <name>`. Derived-constraints ledger already supports producer tagging per GP-086.

### Round 3 — convergence points

- Three-stage pipeline: Stage 1 (deterministic extractor, delegated), Stage 2 (analytical queries, deterministic), Stage 3 (LLM meta-analysis on isolated inflection points).
- No auto-injection into derived_constraints.json. Operator audit gate mandatory between mining output and constraint ledger.
- Cross-judge validation required for any claimed pattern (Oracle Illusion mitigation).
- Cross-project validation required (≥3 projects) for any claimed pattern (pattern vs. substrate-artifact discrimination).
- Tag all mined constraints with producer + mined_from_projects + cross_judge_validated + audit_date + audit_operator.
- Test Lollapalooza hypothesis as a first-class analysis output of Stage 2 (structural signature of 90+ iterations vs. 70-80 iterations).

### Round 4 — residual disagreement: do we test on a held-out project?

**EA:** yes. Pick one active project (candidate: gp145 SAW, which hasn't launched yet) and keep it as validation. Test mined patterns there BEFORE injecting into any active-run derived constraints.

**DA:** this increases latency (we can't use a mined pattern on gp145 until it has enough iterations to serve as validation). Tradeoff between caution and speed.

**Resolution:** tiered validation. Patterns with very strong evidence (N≥50 supporting iterations, ≥5 projects, ≥3 judge families) bypass held-out test — the evidence is overwhelming. Patterns with weaker evidence (10 ≤ N < 50, 3 ≤ projects < 5) require held-out validation. Patterns below thresholds stay in watch-list only.

## 5. Design converged from debate

### 5.1 Three-stage pipeline

**Per-iteration record schema (operator additions 2026-04-24):** the extractor must ALSO capture fields that let Stage 2 prove which constraints are acting as walls for current frontier models, AND let us disambiguate stochastic score drift from structural score change. Added fields:

- `active_constraints`: list of constraint/invariant IDs that were in effect at this iter (e.g., `["INV-3_layer3_exclusive", "pslq_bit_budget", "GP-133-R4-newton-mode", ...]`). Extracted from the rubric, the charter, and any derived_constraints.json snapshot available for the iter. Decisive for `mine_score_ceilings.py` to mathematically prove "constraint X was active for every iter that pinned at ceiling Y."
- `diff_delta_bytes`: signed integer — net byte delta of `thesis.md` + `test_model.py` between iter-1 and this iter. Negative = compression; positive = expansion; near-zero = stagnation. Feeds Stage 2 stagnation signature detection.
- `run_session_id`: heuristic identifier of the continuous run this iter belongs to (gap > 1 hour between consecutive iters in same project → new session). Disambiguates stochastic re-runs of the same charter/rubric/mutator/judge setup. Same (project, charter_hash, rubric_version, mutator_model_id, judge_model_id) in different run_sessions = stochastic drift comparison data.
- `charter_hash`: SHA-256 of `project_charter.md` content at iter time (best-effort: if git history is available, reconstruct the version at the iter's timestamp; else, hash the current-state charter and flag `charter_hash_approximate: true`).
- `rubric_hash`: SHA-256 of `rubrics/<project>.json` at iter time (same git-vs-current-state logic).

These enable the Stage 2 analyses required by the seam's Popper pre-registrations (§9):

- P1 Lollapalooza: need thesis structural features across runs.
- P2 judge-family dispersion: need (mutator_model_id, judge_model_id) tuples AND run_session_id to distinguish "same setup different stochastic run" from "same setup same run."
- P3 stagnation signature: need diff_delta_bytes sequence, not just score sequence.
- Constraint-wall analysis: need active_constraints.

```
Stage 1 — EXTRACTION (deterministic)
   scripts/public/mine_trajectories.py (DELEGATED to background Agent, in flight)
   → analytics/public/ledgers/trajectory/trajectory_archive.jsonl (canonical per-iteration records)

   NOTE 2026-04-24: the delegated Agent was briefed on the base schema
   WITHOUT active_constraints, diff_delta_bytes, run_session_id,
   charter_hash, rubric_hash. When Agent 1 completes, apply a Stage 1.5
   enrichment pass (scripts/public/mine_trajectories_enrich.py) that reads the
   existing archive and appends those fields in a second JSONL in place.
   Rationale: avoids restarting Agent 1 partway; keeps the base schema
   stable; lets us iterate on enrichment without rebuilding the core
   extractor.

Stage 2 — ANALYTICAL QUERIES (deterministic, interactive)
   scripts/public/mine_weakest_link_taxonomy.py
   scripts/public/mine_score_ceilings.py
   scripts/public/mine_primitive_reuse.py
   scripts/public/mine_climb_triggers.py
   scripts/public/mine_judge_bias.py
   scripts/public/mine_lollapalooza_hypothesis.py  (tests Gemini's 3+ orthogonal-constraint claim)
   → analytics/public/queries/<query>_<YYYY-MM-DD>.json

Stage 3 — LLM META-ANALYSIS (batched, selective)
   scripts/public/mine_reasoning_trajectory.py (input: inflection-point slices from Stage 2)
   → analytics/public/reasoning_analysis/<slice_id>_<YYYY-MM-DD>.md

Stage 4 — OPERATOR AUDIT GATE (human-in-the-loop)
   Reviewed proposals at analytics/public/proposals/ → accept/reject/defer
   Accepted proposals tagged and injected into specific projects' derived_constraints.json
```

### 5.2 Stage 2 query catalog (non-exhaustive)

- **weakest_link_taxonomy**: cluster weakest-point strings by TF-IDF or keyword-bag. Expected clusters: "unproven bound," "empirically tuned threshold," "circular gate," "coordinate-dependent," "over-claim exhaustiveness." Each cluster = entry in the Falsification Dictionary.
- **score_ceilings**: per (project, rubric_version, mutator, judge), compute max-score, time-to-ceiling, ceiling-class (weakest-link cluster pinning the ceiling). Reveals which rubric shapes plateau where.
- **primitive_reuse**: grep named primitives across all `current_iteration.md` / `thesis.md`. Which crossed ≥2 projects? Which crossed ≥5? Candidates: pMDL, Tracy-Widom, Noether, Wasserstein-persistence, LLL, LATTICE variants, weak-form SINDy.
- **climb_triggers**: isolate (iter_t, iter_t+1) pairs where Δscore ≥ +10. Correlate with charter-diff / rubric-diff / mutator-swap events.
- **judge_bias**: score distributions by (mutator_family, judge_family). Same-family pairs → agreement bias if distributions are shifted upward vs. mixed-family pairs.
- **lollapalooza_hypothesis**: structural signatures of ≥90-score iterations. Count distinct rubric-dimension-related terms in thesis-text. Null hypothesis: 90+ iters have same term-count distribution as 70-80 iters. Refute = Lollapalooza confirmed.
- **stagnation_signature**: for each multi-iter plateau (≥3 iters within ±5 score), extract the score-delta + token-usage-delta + weakest-link-category sequence immediately prior. Cluster sequences; emergent signatures are the early-warning patterns.

- **pivot_effectiveness** (added 2026-04-24 post gp140 87-score observation): join the enriched archive with each project's `workspace/loop_events.jsonl`; for each `topological_pivot_profile_injected` and `topological_pivot_emergency` event, measure score delta over the next 3 iters. Bucket by weakest-link-class of the pre-pivot iter. Report per-class effectiveness (p(climb ≥+10), p(regress ≤-10), p(no-change |Δ|<10). Emergent hypothesis from gp140 single observation: "unverified coercivity" class → basis-change pivot effective; "exhaustiveness / completeness" class → pivot ineffective (mutator needs empirical-retreat, not topology swap). Validate against ≥3 projects before proposing new `pivot_effectiveness_routing` heuristic. Anti-overfitting discipline: single-project observation stays in watch-list, does not propose codification.

### 5.3 Stage 3 LLM meta-analysis prompt (adopted from Gemini-Pro)

For each inflection-point slice (≥30-point jump/drop):

```
You are evaluating a REASONING TRAJECTORY, not grading physics.

Here is a sequence of N iterations from the ZTARE scientific discovery
engine running on project {project_slug}. The trajectory shows a
{pattern_type}: {description of the jump/drop}.

Iteration-by-iteration:
[iter_index] [score] [weakest_point] [proposed_primitive_names]

Your task:
1. Identify the specific conceptual blindspot the mutator was trapped
   in during the low-score phase.
2. Identify the exact epistemic pivot (if any) that allowed it to escape
   (or, in a drop case, caused the collapse).
3. Output a candidate derived constraint in the schema:
     constraint: <string, ≤ 200 chars>
     applies_to: <string, "champion thesis" or "any proposal">
     failure_family: <slug>
     severity: enriching | degrading | critical
     supporting_iterations: <list of (project, iter_timestamp) tuples>
     cross_judge_validation_needed: true/false

Do NOT grade the physics. Do NOT propose a better thesis. Only output
the structural error and the structural fix as a candidate constraint.
```

### 5.4 Audit gate specification

Any Stage 3 proposal before injection into `workspace/derived_constraints.json`:

```
Required audit fields:
  - supporting_iterations: N >= 10 (or N >= 50 for auto-accept tier)
  - cross_project_count: >= 3 (or >= 5 for auto-accept tier)
  - cross_judge_families: >= 2 (or >= 3 for auto-accept tier)
  - audit_date: YYYY-MM-DD
  - audit_operator: <name>
  - audit_decision: accept | reject | defer
  - held_out_validation: <project_slug or null>  (required if below auto-accept tier)

On accept:
  Inject into target project's derived_constraints.json with:
    producer: "void_mining_gp148"
    mined_from_projects: [<slug list>]
    cross_judge_validated: [<judge_family list>]
    audit_date, audit_operator (as above)
    status: "provisional"  (subject to normal 2-sighting confirmation rule)
```

## 6. Open questions deferred to spec

- **OQ-1:** exact weakest-link-taxonomy clustering method (TF-IDF + k-means? keyword-list + regex? small LLM classifier?). Spec picks one with criteria.
- **OQ-2:** Stage 3 batching cadence (weekly? on-demand? triggered by inflection-point count threshold?).
- **OQ-3:** UI for operator audit gate (CLI prompt? markdown-file-based review queue? lightweight web form?).
- **OQ-4:** held-out project rotation — if gp145 serves as held-out for the current quarter, when does it rotate to an active-injection project and a different project takes the held-out slot?
- **OQ-5:** storage format for analytics/public/ — JSONL per analysis, or a SQLite DB the scripts populate?

## 7. Scope boundary

GP-148 does NOT include:
- Changes to the autoresearch_loop.py mutator prompt format
- Changes to the judge's rubric-loading path
- Live auto-injection of any constraint into any project
- Any analysis of projects outside `projects/*/` (e.g., papers/, docs/)

GP-148 IS:
- An aggregation + analysis + proposal pipeline feeding an audit gate
- Read-only against all existing project state
- Write-only to `analytics/public/` (new top-level directory)

## 8. Implementation handoff (for next Claude / operator / cloud agent)

Implementation order per INV-10:
1. Seam converges (this document, currently draft)
2. Spec lands at `research_areas/private/specs/active/GP-148_void_mining_spec.md`
3. Stage 1 extractor (DELEGATED, in flight via background Agent 2026-04-24)
4. Stage 2 query scripts (one at a time, each merged after review)
5. Stage 3 LLM meta-analysis script (batched runs only)
6. Operator audit gate tooling (likely markdown-review-queue first cut)
7. First full mining sweep on current corpus; held-out validation on gp145 SAW (when launched)

The next Claude / cloud agent picking this up should:
- Confirm Stage 1 extractor completed and archive is populated
- Read the seam (this document) + spec (when written) to align on convergence points
- Implement Stage 2 scripts in the order listed in §5.1 above (each as a standalone module that reads the Stage 1 archive)
- Defer Stage 3 LLM scripts until Stage 2 has produced at least one concrete inflection-point slice to test against

Do NOT implement auto-injection into derived_constraints.json. The audit gate is decisive and must stay operator-gated.

## 9. Testable claims (Popper pre-registration)

Before mining runs at scale, pre-register these as specific falsifiable predictions:

- **P1 (Lollapalooza hypothesis):** iterations scoring ≥ 90 have structurally different thesis-term distributions from iterations at 70-80 (multi-constraint coverage). Falsifier: if the distributions are statistically indistinguishable (KS-test p > 0.05 across 100+ samples each), Lollapalooza is false.
- **P2 (single-judge overfit risk):** same thesis structure scored by different judge families shows score dispersion > 15 points for ≥ 20% of theses. Falsifier: if dispersion < 15 for ≥ 95% of theses, judges agree and single-judge bias is not a concern.
- **P3 (Stagnation signature detectability):** at least one cluster of stagnation pre-sequences has in-cluster variance < 0.5 (tight signature) with 3+ member sequences. Falsifier: all stagnation pre-sequences are inter-project heterogeneous → no predictable signature.

## 9b. Findings & interventions — deferred to companion seam

First mining pass + LLM classifier + four operator backtests produced a findings corpus + a seven-item intervention catalog. That material lives in the companion seam to keep GP-148 focused on infrastructure:

**→ `research_areas/private/seams/engine/GP-149_mining_findings_and_interventions_seam.md`**

GP-148 (this seam) stays stable: extractor, enrichment, query specs, Popper pre-registrations for the infrastructure. GP-149 evolves: findings update with each mining pass; interventions are debated, implemented, telemetry-evaluated, and either promoted to kernel or rolled back.

Cross-reference established 2026-04-24.

## 10. What this seam is NOT

- Not a substrate for ZTARE to iterate on.
- Not a change to the mutator prompt or judge rubric.
- Not an auto-injection pipeline.
- Not a visualization / dashboard project.

It IS: a systematic extraction + analysis + operator-gated proposal pipeline that converts the iteration-exhaust corpus into queryable knowledge, with the explicit discipline of not overfitting to mined patterns.
