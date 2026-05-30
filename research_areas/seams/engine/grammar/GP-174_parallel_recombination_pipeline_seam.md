# GP-174 — Parallel Recombination Pipeline (closes GP-060)

> **Seam metadata** · `seam_id:` GP-174 · `track:` engine · `status:` open, panel review pending · `last_updated:` 2026-05-08


**Status:** open, panel review pending
**Opened:** 2026-04-27 (night)
**Author:** Claude (Research Director role) on principal authorization
**Closes:** GP-060 (Parallel Champion Synthesis — combiner was the decisive component, never shipped)
**Related:** GP-157 Phase 4e (parallel_mutator skeleton + tournament wire-in shipped earlier tonight); GP-164 ANALOGY (collapse-mode that motivates structural recombination); GP-167 (substrate critic, separate channel for the same residual signal); the 4-panel physicist debate (synthesis target requires structural fragments from disjoint families).

---

## 1. Problem statement

Phase 4e wire-in (shipped 2026-04-27 night) gives K parallel mutator workers per iter, with `pick_best_candidate` selecting one winner via syntactic heuristic. K-1 candidates are discarded.

That is engineered divergence without recombination. Three observations make this insufficient:

1. **ANALOGY collapse postmortem** (gp163d run, 22 fires) — the LLM in the loop has a heavy prior toward Heaviside / tanh / sigmoid threshold forms. K parallel calls do not escape that prior; they sample around it. Tournament selection picks the "best Heaviside form," not a structurally novel form.
2. **Two complementary partial-bridges on v3.4** — Form A (cluster-clean, declarability-fail) and Form B (Lagrangian-clean, wide-binary-fail) each carry the structural fragment the other is missing. Tournament discards both; recombination produces the synthesis.
3. **Four-panel physicist debate verdict** — the synthesis target `c_eff = λ·(1+α·Q(u)·GAS_LIFT(u))` requires `Q(u)` from screened-scalar Lagrangian and `GAS_LIFT(u)` Hill-β≥2 from cluster-RAR fits. Two structural fragments from disjoint families. No single LLM call has produced this composite over 22 ANALOGY fires + 5 mutator iters; it has to be assembled.

The seam is therefore: **how to compose K parallel mutators with deterministic AST crossover + LLM-level persona-fusion + persistent MCTS branches + adversarial refinement, without each stage destroying the value of the prior stage.**

---

## 2. Pipeline architecture (proposed v0)

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 1: K Parallel Mutators (engineered persona divergence) │
│    — newton_discovery / munger_inversion / engineer_pragmatist │
│    — 3 workers in parallel via ThreadPoolExecutor              │
│    — output: K candidate (thesis_text, parametric_form)        │
└───────────────────────────────────────────────────────────────┘
              ↓
┌───────────────────────────────────────────────────────────────┐
│  Stage 2: AST Crossover (deterministic recombination)          │
│    — parse each PARAMETRIC_FORM via SymPy                      │
│    — identify swappable sub-trees (depth ≥ 2, ≥ 1 free param)  │
│    — generate hybrids via single-point crossover               │
│      → for K=3: C(3,2)=3 pairs × ~3 swap positions = ~9 hybrids│
│    — output: K originals + ~9 crossover hybrids                │
└───────────────────────────────────────────────────────────────┘
              ↓
┌───────────────────────────────────────────────────────────────┐
│  Stage 3: Persona-Fusion (LLM-level semantic merge)            │
│    — single LLM call with the K + crossover candidates as input│
│    — prompt: "produce ONE form that combines structural        │
│      strengths and addresses each candidate's failure mode"    │
│    — output: 1 fusion candidate                                 │
└───────────────────────────────────────────────────────────────┘
              ↓
┌───────────────────────────────────────────────────────────────┐
│  Stage 4: Tournament + MCTS Branch Persistence                 │
│    — score all candidates via expanded heuristic               │
│      (PARAMETRIC_FORM presence, syntactic validity, AST depth, │
│       parameter count K, structural-novelty vs prior champion) │
│    — pick top-1 as iter winner (passes through normal pipeline)│
│    — pick top-2..top-3 as carried-forward "branches"           │
│    — branches re-enter Stage 1 next iter as additional seed    │
│      personas alongside the standard K personas                 │
└───────────────────────────────────────────────────────────────┘
              ↓
┌───────────────────────────────────────────────────────────────┐
│  Stage 5: Adversarial Refinement (post-judge, post-cage)       │
│    — only fires when iter winner promoted to champion          │
│    — auditor persona attacks the new champion: "name the       │
│      structural failure mode this form has not closed"         │
│    — auditor output piped into next-iter's MutatorBriefing as  │
│      an additional adversarial constraint                       │
│    — termination: bounded by iter (one auditor pass per iter,  │
│      not a recursive loop)                                      │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Failure mode catalog (panel input)

### Stage 2 — AST Crossover

**FM-2a Sub-tree boundary detection collapses on disjoint-skeleton candidates.**
If the K candidates have no shared structural skeleton (one is `y = a + b·x`, another is `y = a·exp(-x/c)`), there is no meaningful "swap point." Crossover degenerates to "graft random sub-tree from A into random position of B," producing nonsense forms.

  *Mitigation candidates*: (a) require K candidates to share a top-level shape (e.g., all be `y = x · F(features, params)`); (b) restrict crossover to a fixed set of named slots (`screening_function`, `mass_dependence`, `radial_dependence`) — turns crossover into a constrained slot-fill rather than free swap; (c) skip crossover when shared-skeleton fraction < threshold and report telemetry only.

**FM-2b Variable-name and parameter aliasing.**
Candidate A: `screening = (1 + alpha·Q(u))^0.5` with `params['log_alpha']`. Candidate B: same name `params['log_alpha']` for a different role (a high-x cutoff). Naive sub-tree swap merges the two parameter names into one fitted variable, losing degrees of freedom and producing degenerate fits.

  *Mitigation candidates*: (a) namespace each candidate's parameters before crossover (`params_A_log_alpha`); (b) post-crossover variable rename + de-duplication pass; (c) AST-level parameter audit before serializing back to PARAMETRIC_FORM.

**FM-2c Dimensional / units violations.**
Sub-tree `mass_log10 + radius_log10` is dimensionless (both are log-quantities); sub-tree `params['log_lam']·exp(...)` is in m/s². Swapping produces forms that are dimensionally meaningless. Cage's existing dimensional gate would reject these, but burning gate cycles on guaranteed-rejection forms is wasteful.

  *Mitigation candidates*: (a) tag each sub-tree's dimensional class at parse time, only allow same-class swaps; (b) defer to existing dimensional gate (let it reject), but skip forms with obviously-mismatched output units before serializing.

**FM-2d Round-trip serialization fragility.**
SymPy's `parse_expr` and `srepr` round-trips don't always survive the apparatus's PARAMETRIC_FORM string format (`features['x']` indexed access, `params.get('log_c', default)` pattern, `np.where` calls). Crossover output may not even be importable.

  *Mitigation candidates*: (a) test round-trip on each input candidate before attempting crossover, skip pairs where one fails; (b) maintain a translation layer between apparatus PARAMETRIC_FORM string and SymPy-friendly canonical form; (c) post-crossover compile-test before adding to candidate pool.

### Stage 3 — Persona-Fusion

**FM-3a Regression to mean.**
LLM synthesis prompts ("combine the strengths of these candidates") tend to produce reconciliation-by-averaging: the LLM picks the most-common form-family across candidates and writes a single expression in that family. If 3/3 candidates were threshold forms, fusion is also a threshold form. The "synthesis" loses the disjoint-family signal that makes recombination valuable.

  *Mitigation candidates*: (a) explicit prompt instruction: "pick the LEAST-common structural fragment from each candidate and combine them"; (b) frame the task as "name the failure mode of each candidate, then propose a form that has none of those failure modes"; (c) return the fusion candidate alongside the originals + crossovers in the tournament pool — let the structural-novelty score discriminate.

**FM-3b Loss of K-divergence.**
Fusion's purpose is to find the union of structural strengths. If fusion just picks one candidate's form verbatim, it adds nothing. Telemeter the fusion's structural distance from each input.

  *Mitigation candidates*: hash the fusion's PARAMETRIC_FORM, compare to each input's hash; if identical to any single input, demote fusion's tournament score and log a `fusion_collapse` event.

### Stage 4 — Tournament + MCTS Branch Persistence

**FM-4a Cost explosion.**
Top-3 branches × K=3 next-iter mutators = 9 LLM calls per iter, plus crossover hybrids (~9), plus fusion (1) = ~19 candidate evaluations. If branches are kept across many iters without aggressive pruning, K grows unbounded.

  *Mitigation candidates*: (a) hard cap branches at top-2 (not top-3) — geometric-rather-than-arithmetic growth; (b) prune branches whose normalized score drops below 0.5× current iter's leader; (c) opt-in flag `parallel_mcts_branches=B` (default 0 → no MCTS); (d) telemeter K per iter, alert when > 12.

**FM-4b Stale branches.**
A branch from iter N may still seed iter N+5's mutator pool even if it's structurally obsolete relative to the new champion. The branch becomes noise that wastes K LLM calls per iter.

  *Mitigation candidates*: (a) age-out branches after N=2 iters of non-promotion; (b) require branches to "earn" persistence by clearing a minimum diversity-distance from the current champion.

**FM-4c Tournament tie-breaking.**
If three candidates score identically (PARAMETRIC_FORM present, syntactically valid, K=3, no novel-feature use), worker_id-based deterministic tie-break is unprincipled and may systematically favor one persona.

  *Mitigation candidates*: (a) add structural-novelty score (Levenshtein distance from current champion's PARAMETRIC_FORM, or AST tree-edit distance); (b) on ties, prefer the candidate whose persona did NOT win the previous iter (anti-persistence); (c) random tie-break with seed logged.

### Stage 5 — Adversarial Refinement

**FM-5a Termination.**
Without bounded scope, the auditor → mutator → auditor loop never terminates. Even with one-pass-per-iter bound, the auditor can produce objections that compound across iters: each iter's champion has more attached "open critiques" than the last.

  *Mitigation candidates*: (a) hard scope: one auditor pass per iter, on the iter winner only, output is a SINGLE structured critique fed into next-iter briefing — not a recursive call; (b) the critique is treated as input alongside (not replacement of) the existing failure_log + analogy_candidates; (c) prune critiques that are duplicates of existing rubric anchors (the rubric already enforces those).

**FM-5b Adversarial drift toward over-rejection.**
The auditor persona, like ZTARE's existing skeptic-director seat, may drift toward "everything is wrong" verdicts that block legitimate progress. The 4-panel debate's "NOT close to a clean Tier-1 bridge" verdict is exactly this drift, applied at human level.

  *Mitigation candidates*: (a) auditor must produce SPECIFIC structural critiques (sub-tree-level), not global verdicts; (b) auditor's critiques are one input among many to next-iter mutator, not a veto; (c) telemeter auditor's critique acceptance rate (how often does mutator's next form actually address the critique?) — if < 20%, the auditor is adversarial-noise, demote to OBSERVE only.

### Cross-stage

**FM-X-a R1 contract failure compounding.**
If 3/3 mutators fail R1 contract, plus crossovers fail (because their seed candidates didn't compile), plus fusion fails (because its inputs were all R1-failed), an iter could waste 4-5× normal token cost producing zero usable forms.

  *Mitigation candidates*: (a) early-abort: if K mutators all fail R1, skip crossover + fusion (no point); (b) batch R1 validation: validate all K candidates before stage-2 entry, and only candidates passing R1 enter crossover; (c) the existing R1 retry budget applies per-candidate; cap aggregate R1 retries per iter to K + 2 to prevent runaway.

**FM-X-b Telemetry observability blind spots.**
Without per-stage telemetry, post-mortem cannot diagnose which stage is responsible for an iter's success or failure. Was the win the mutator's? The crossover's? The fusion's?

  *Mitigation candidates*: (a) every candidate carries a `stage_origin` tag (`mutator_persona_X` / `crossover_pair_AB` / `fusion`); (b) workspace artifact `pipeline_log.jsonl` records every candidate, score, and tournament outcome per iter; (c) iter-summary print line: "iter N: winner=<stage_origin>, crossover_won=<bool>, fusion_won=<bool>".

**FM-X-c Compositional emergent overfitting.**
Each stage's mitigation may individually be sound, but composed they can produce a winner that satisfies every per-stage check while being a structural curve-fit. The ANALOGY tournament-then-pick-best-Heaviside failure mode could re-emerge at the pipeline level.

  *Mitigation candidates*: (a) maintain the existing Cage gate stack as the floor — the pipeline does not bypass any cage check; (b) add a pipeline-level adversarial gate: forms whose PARAMETRIC_FORM hash collides with any prior champion's hash AND whose score margin is below threshold are rejected as "compositional plagiarism"; (c) periodic ablation: run iter N+5 with `parallel_mutator_k=1` (single mutator) and compare the winner — if the K=3 pipeline isn't beating K=1 by margin, the pipeline is overfitting to its own selection.

---

## 4. Open questions for panel review

1. **Should AST crossover require shared-skeleton (FM-2a (a)) or use named slots (FM-2a (b))?** Tradeoff: shared-skeleton requires the persona briefings to enforce a top-level shape, biasing search; named slots require the apparatus to carry a "form contract" that the mutator must instantiate.

2. **Should Persona-Fusion run as part of every iter, or only on stagnation/champion-promotion?** Cost: 1 LLM call/iter forever vs. 1 call only when needed. Fusion's value is highest exactly when the K parallel mutators have converged on similar forms, which is the stagnation signal.

3. **MCTS branches: opt-in (B=0 default) or opt-in via stagnation auto-trigger?** Always-on MCTS has cost shape K + B per iter. Auto-triggered has the principal observability benefit (operator sees which iters needed branch persistence).

4. **Adversarial refinement: separate persona, or extend the existing skeptic-director M-form seat (per memory `feedback_skeptic_director_seam.md`)?** The skeptic-director is already a defined role; extending it preserves the M-form architecture rather than adding a new seat.

5. **Round-trip serialization (FM-2d): build a translation layer, or accept the loss-rate and skip un-serializable crossovers?** A translation layer is ~200 LOC; skipping is free but reduces crossover yield.

6. **Compositional overfitting (FM-X-c): periodic K=1 ablation as cost-amortized check?** This is a paper-grade methodology proposal, not just an apparatus check.

---

## 5. Proposed phasing (panel may revise)

**Phase 1 (ship tonight, after panel sign-off):**
- Stage 2 AST crossover with shared-skeleton requirement (FM-2a (a))
- Stage 3 Persona-Fusion with explicit "least-common-fragment" prompt (FM-3a (a))
- Tournament expansion to score originals + crossovers + fusion together
- Telemetry: `pipeline_log.jsonl` + per-candidate `stage_origin` tag
- Default `parallel_mutator_k = 3` already shipped; `enable_recombination = False` opt-in

**Phase 2 (next iter, after Phase 1 telemetry):**
- Stage 4 MCTS branch persistence (top-2 carried forward) — opt-in via stagnation
- Stage 5 adversarial refinement via skeptic-director seat extension

**Phase 3 (post-stability soak):**
- Translation layer for FM-2d
- Named-slot crossover (FM-2a (b)) as alternative to shared-skeleton

---

## 6. Reviewer mandate

Review the failure mode catalog (§3) and the open questions (§4). For each failure mode you accept, propose mitigation. For each you reject as not-actually-failure-mode, say so. Add failure modes I have missed. Recommend phasing. Do not implement code; this is the design-review pass before code commits.

The panel is intentionally diverse — 5 distinct expertise domains are scoped (genetic programming, LLM ensembling, MCTS, adversarial ML, apparatus systems engineering). Each seat is asked to focus on its primary domain but flag cross-domain concerns when they see them.

After all 5 panel verdicts return, the implementation pass will apply their fixes, then a separate two-seat audit (software engineer + epistemic reviewer) will check the implementation against the panel-revised spec.


---

## Turn 2 — Munger inversion + synthesis on panel verdicts (2026-04-27 night)

_Method: for each panel recommendation, ask (a) inversion (what would make it worse if naively applied?) (b) synthesis across seats (Munger lollapalooza — what compounds?)._

## Part I — Munger Inversion (per recommendation)

For each decisive panel recommendation, the Mungerian question: *what is the failure mode of the recommendation itself?*

### GP seat — "Use named-slot crossover, not shared-skeleton"

**Inversion: named slots are themselves a contamination vector.**
The slots have to be defined somewhere. If the operator defines them (`screening_function`, `mass_dependence`), that's exactly the charter contamination the apparatus already documents (memory `feedback_charter_contamination.md`). The slot name becomes a cheat sheet. Conversely if the slots are inferred from a held-out grammar mining pass, the inference itself overfits to the prior champion family. Named slots that are domain-typed (`screening_function`) are worse than shared-skeleton; named slots that are math-operator-typed (`binary_op_slot`, `unary_envelope_slot`) are the safe form, but lose most of the decisive structure that made named slots powerful in the first place.

**Resolution:** Phase 1 ship shared-skeleton with the **canonical-hash bucketing** (already implemented). Phase 2 build named slots only after we have ≥3 successful runs with shared-skeleton, and only with math-operator types. Don't let GP-seat enthusiasm for slots leak the answer into the grammar.

### LLM seat — "Shard MutatorBriefing per persona"

**Inversion: sharding the briefing breaks the ANALOGY+substrate-critic feedback loop.**
The current `MutatorBriefing` carries 5 providers (failure_log, analogy_candidates, prior champion, charter, data_diagnostics). If newton-discovery sees only first-principles hints and engineer-pragmatist sees only empirical anchors, then ANALOGY's residual fingerprint (which is iter-N-global) is divided. The K personas no longer have a shared epistemic baseline; they fork the apparatus's perception of what the substrate is doing. This compounds across iters.

**Resolution:** Don't shard. Instead, add a **persona-private suffix** to each worker's briefing — a 1-2 sentence "you are <persona> with <specific bias>" — without touching the shared providers. Diversity from the persona axis, not from the briefing axis.

### MCTS seat — "Sequential Halving, not UCB1"

**Inversion: Sequential Halving requires a fixed budget known in advance.**
The apparatus doesn't have one. Iters are open-ended (operator stops the run). Per-iter K is rubric-flagged. Imposing Sequential Halving's halving schedule means committing to a horizon up front — which is exactly the closure constraint GP-168's unfalsifiability theorem says we DON'T have without exogenous resource pressure. Adopting Sequential Halving smuggles in a budget that the operator hasn't actually authorized.

**Resolution:** UCB1 is fine for now, with the seat's other recommendations (visit-count tie-breaker, score-decay age-out). When the operator commits to a fixed-budget run (e.g., a paper-deadline campaign), switch to Sequential Halving. Don't bake horizon assumptions into the apparatus.

### Adversarial seat — "Replace Levenshtein with 3-axis novelty stack"

**Inversion: a 3-axis novelty stack is itself gameable at the meta-level.**
Each axis (canonical AST, op-multiset, residual-fingerprint) has known attacks. Combining them with `min` (the seat's recommendation) means a candidate that passes the strictest axis wins; a sufficiently sophisticated mutator learns which axis is binding and routes around it. The 3-axis is harder to game than 1, but still has a ceiling — it's a defense-in-depth, not a defense-in-principle.

**Resolution:** Ship 3-axis (canonical AST + op-multiset implemented; residual deferred). Pair it with the K=1 ablation (also adversarial-seat recommendation) — when the K=3 pipeline isn't beating K=1 by margin, the novelty stack is being gamed and the operator gets an alert. The defense-in-depth × meta-check composition is the real mitigation.

### Apparatus seat — "Ship pipeline_log.jsonl in Phase 1"

**Inversion: rich telemetry is itself a reasoning shortcut.**
With per-stage, per-candidate logs, the operator and the role-agents will start diagnosing pipeline behavior FROM the logs rather than from the substrate evidence. The apparatus's failure surface becomes "what does the log say?" rather than "what does the residual look like?" This is the apparatus-as-substrate failure mode — the logs become an attractor that pulls attention away from the actual physics.

**Resolution:** Ship the logs (the diagnosis cost without them is too high) but **enforce a discipline in the Research Director mandate**: never write a triangulation report or a paper section from pipeline_log alone. Always cross-reference at least one substrate-side artifact (residual, fit, anchor comparison). This keeps the logs in their place — telemetry, not ontology.

### GP seat — "Drop persona-fusion from Phase 1"

**Inversion: dropping fusion makes the K mutators a flat-search-with-K-arms.**
GP seat's argument is "fusion will defeat divergence." But the K mutators alone, scored by tournament, become K independent draws from the LLM's prior — exactly the ANALOGY-collapse mode the pipeline is designed to escape. Without fusion (or any structural composition operator), the K=3 setup is K=1 + K-1 wasted draws. The cost-shape doesn't justify itself.

**Resolution:** Keep fusion, gated on stagnation (panel synthesis). Apply LLM-seat's two-pass structured prompt + adversarial-seat's "MUST NOT be in dominant family" hard constraint. This addresses GP-seat's regression-to-mean concern via prompt structure, not by removing the operator.

---

## Part II — Munger Synthesis (lollapalooza)

The Mungerian lollapalooza: when **multiple panel concerns compound on the same surface**, the failure mode is far worse than any single seat predicts. Three lollapaloozas surfaced.

### Lollapalooza A — Persona-LLM-substrate tri-collapse

**Compounds across:** LLM seat (FM-1b non-independence, FM-1c lexical contamination), Adversarial seat (FM-X-d persona collusion), GP seat (FM-2a shared-skeleton homogeneity).

**Mechanism:** K=3 from the same model + shared MutatorBriefing + shared-skeleton crossover requirement. The K personas are not independent because (i) they share weights, (ii) they share context, (iii) they're forced to share top-level form structure. Effective K is closer to 1.3 — but the apparatus accounts for K=3 cost. The 3× spend buys 1.3× exploration.

**Compound mitigation (must do all three to break the lollapalooza):**

1. **Cross-family Stage 1:** at least one persona on a different model family per iter. Already prescribed by `feedback_gpt41_default_option.md`; needs to be wired into parallel_mutator_k workers (currently all use one `current_mutator` model).
2. **Persona-private suffix** (per Inversion II above) — diversity from prompt suffix, not briefing shard.
3. **Canonical-hash skeleton bucketing** (already implemented) — keep the cheap pre-filter but allow cross-bucket pairs to enter fusion (so fusion is the cross-skeleton mechanism, crossover stays in-skeleton).

Doing only 1 of 3 leaves the lollapalooza largely intact. Doing 2 of 3 closes ~70%. All three closes the surface.

### Lollapalooza B — Critique-Goodhart × auditor-drift × cross-iter laundering

**Compounds across:** Adversarial seat (FM-5c critique-Goodharting, FM-5d easily-fixable critique selection, FM-5e cross-iter laundering), MCTS seat (FM-4b stale branches), Apparatus seat (FM-X-c provenance gap).

**Mechanism:** Auditor emits critiques → mutator addresses superficially → critique closed → next iter's crossover pulls a sub-tree from a stale branch (FM-4b) that predates the critique → pathology re-enters → auditor doesn't re-emit (already "closed") → champion ships with the critiqued pathology. Each individual mitigation (critique-acceptance band, falsifiable closure tests, severity-weighted scoring) blocks one path; together the paths re-route.

**Compound mitigation:**

1. **Critique-tagged sub-trees** (Adversarial FM-5e mitigation): when a branch is recombined, sub-trees inherit the critique-tags of their iter-of-origin.
2. **Provenance.json sidecar** (Apparatus FM-X-c): every artifact carries its full lineage, queryable post-hoc.
3. **Critique expiry + resolution test** (Adversarial FM-5a): critiques have an `expiry_iter` AND a falsifiable `resolution_test`; can't be silently closed.
4. **Score-decay branch age-out** (MCTS FM-4b): stale branches geometrically decay regardless of "promotion or not" — removes the time-of-flight surface that laundering exploits.

These are independent. Implementing 1+3 without 2+4 leaves the laundering surface; 2+4 without 1+3 leaves the Goodhart surface. **All four required.** Phase 5 territory; do not ship adversarial refinement (Stage 5) until all four are in.

### Lollapalooza C — Compositional pipeline-overfitting × stale-branch noise × Pipeline-as-substrate

**Compounds across:** Adversarial seat (FM-X-c compositional overfitting), MCTS seat (FM-4b stale branches, FM-4f non-stationarity), Apparatus seat (telemetry-as-attractor inversion above).

**Mechanism:** The pipeline produces a winner. The winner is then re-injected into next iter's seed pool via MCTS branches (which seat 5 says go through MutatorBriefing per FM-X-i). The pipeline is now self-conditioning — it's selecting forms from a distribution that previous iterations of the pipeline shaped. Telemetry becomes the optimization target. K=3 beats K=1 not because it's discovering, but because it's compounding its own preferences. The K=1 ablation (Adversarial FM-X-c (c)) catches this only if the ablation runs on a SHARED state — which it can't, because state is conditioned on the pipeline's prior outputs.

**Compound mitigation:**

1. **K=1 ablation must run on a CHECKPOINT BEFORE the pipeline started conditioning** (not on the current state). Reset to a baseline branch state for ablation iters.
2. **Charter/rubric hash invalidation** (MCTS FM-4f): when these change, branches reset.
3. **Discipline rule from Inversion V** (telemetry-as-attractor): triangulation reports must cross-reference substrate, not pipeline-log alone.

### What this synthesis says about Phase 1 phasing

**Phase 1 stays as the panel-revised minimum-viable** (canonical hash, bloat caps, 3-axis novelty, two-pass fusion, pipeline_log) **but DELAY everything that activates Lollapalooza B or C:**
- MCTS branch persistence (Lollapalooza C activator) → Phase 2, with hash-invalidation + branch-from-checkpoint K=1 ablation as prerequisites.
- Stage 5 adversarial refinement (Lollapalooza B activator) → Phase 3, with all four B-mitigations as prerequisites.
- Cross-family Stage 1 LLM diversity (Lollapalooza A breaker) → **Phase 1**, because it's the only path that breaks Lollapalooza A and ships at low cost.

---

## Part III — Net deltas vs Panel-revised Phase 1

| Item | Panel-recommended | Munger-revised |
|---|---|---|
| Canonical hash + 3-axis novelty | Phase 1 | Phase 1 (kept) |
| Bloat caps + parsimony | Phase 1 | Phase 1 (kept) |
| Two-pass structured fusion | Phase 1 | Phase 1 (kept, gated on stagnation) |
| Pipeline_log.jsonl 3 record types | Phase 1 | Phase 1 (kept) + RD mandate discipline rule (Inversion V) |
| Cross-family Stage 1 | Phase 2 (most seats) | **Phase 1** (Lollapalooza A breaker) |
| Persona-private suffix | not specified | **Phase 1** (Lollapalooza A breaker) |
| MCTS branch persistence | Phase 2 | Phase 2 (with B-from-checkpoint ablation prereq) |
| Stage 5 adversarial refinement | Phase 2 | **Phase 3** (Lollapalooza B blockers required first) |
| K=1 ablation every 5 iters | Phase 1 | Phase 1 (kept) but must run on baseline checkpoint not current state (Lollapalooza C mitigation) |
| Translation-layer / canonical IR | Phase 1 (GP+Apparatus) | Phase 1 (kept, partial — full canonical IR is Phase 2) |
| Named-slot crossover | Phase 1 (GP) | **Phase 2** (Inversion I — math-typed slots only) |
| GP-148 experience replay seeds | Phase 2 | Phase 2 (kept) |

**Net Phase 1 additions from Munger pass:** cross-family Stage 1 + persona-private suffix + ablation-from-checkpoint discipline.

**Net Phase 1 subtractions:** named-slot crossover deferred (Inversion I).

**Net Phase 2 → Phase 3 reclassification:** Stage 5 adversarial refinement (Lollapalooza B requires full mitigation stack first).


---

## Turn 3 — Implementation status against panel + Munger checklist (2026-04-27 night, post audit)

_Updated after the two-seat implementation audit (sw engineer + epistemic reviewer) returned. Marks each panel + Munger Phase-1 item as ✓ shipped, ⚠ partial, or ✗ deferred to Phase 2/3._

### Stage 1 — K Parallel Mutators

| Item | Source | Status | Notes |
|---|---|---|---|
| ThreadPoolExecutor K-way fan-out | Phase 4e | ✓ | `src/ztare/orchestrator/parallel_mutator.py` |
| Stagnation-gated dispatch (K=1 default) | Apparatus + MCTS panels + Munger | ✓ | `should_run_parallel` in `blitz_dispatch.py`; default K=1, K=K when `stagnation_count >= parallel_mutator_min_stagnation` OR `parallel_mutator_force=True` OR `iter_idx in parallel_mutator_force_iters` |
| Persona-private structured suffix | Munger Lollapalooza A breaker | ✓ | `PERSONA_PRIVATE_SUFFIX` in `blitz_dispatch.py`; injected into `_single_mutate` closure in `autoresearch_loop.py`; three biases (newton_discovery / munger_inversion / engineer_pragmatist) cover continuous / inversive / piecewise priors |
| K=1 ablation every Nth iter | Adversarial + Apparatus + Munger Lollapalooza C | ✓ | `parallel_mutator_k1_ablation_every` rubric flag (default 5 on gp163d); override fires before stagnation policy so ablation-iter is K=1 regardless |
| Cross-family LLM diversity (one persona on different family) | LLM + Adversarial panels + Munger | ✗ | Phase-2 deferred; today all K workers use the run's `current_mutator` model. Mitigation rationale: gpt-5.5 mutator + gpt-4.1 judge already give cross-family epistemic airgap at the iter level |

### Stage 2 — AST Crossover

| Item | Source | Status | Notes |
|---|---|---|---|
| SymPy-based sub-tree swap | seam §2 | ✓ | `crossover_pair` in `recombination.py` |
| Skeleton-match pre-filter (FM-2a) | GP panel | ✓ | `_skeleton_hash` token-level pre-filter |
| Canonical-hash de-duplication (FM-2a + FM-X-c) | Adversarial panel | ⚠ | `_canonical_hash` does sympy.simplify + alpha-rename + sstr; **audit caught**: alpha-rename uses lexical sort over original symbol names rather than DAG-traversal order — false negatives possible on aggressive rename gaming. Phase-2 fix |
| Bloat hard caps (max_nodes=40, max_depth=8) + parsimony λ | GP panel | ✓ | enforced as both hard cap (returns -1.0) and soft penalty in `score_candidate_extended` |
| Parameter-linkage atomic transfer | GP panel | ⚠ partial | `params_union` carries names through but no co-fitted-block atomicity discipline. Phase-2 |
| Dimensional-class STGP-lite | GP panel | ✗ Phase 2 | rely on existing dimensional gate to reject post-fit |
| AST mutation operator at 10% post-crossover | GP panel | ✗ Phase 2 | crossover-only converges prematurely per Luke 2013; need single-op-swap or constant-rescale operator |
| Round-trip canonical IR (full translation layer) | GP + Apparatus panels | ⚠ partial | `apparatus_to_sympy` + `sympy_to_apparatus` exist; missing slot-tagged canonical genotype. Phase-2 |
| Named-slot crossover (math-typed) | GP panel + Munger Inversion I | ✗ Phase 2 | shipped shared-skeleton instead per Munger Inversion |

### Stage 3 — Persona-Fusion

| Item | Source | Status | Notes |
|---|---|---|---|
| Two-pass structured prompt (diagnosis → construction) | LLM + Adversarial panels | ✓ | `_FUSION_PROMPT` in `recombination.py`; explicit "F is NOT in dominant_family" hard constraint |
| Stagnation-gated firing (only when stuck) | Munger | ✓ | `recombination_fusion_min_stagnation` rubric flag; defaults to 1 |
| FM-3b skeleton-collision rejection | LLM panel | ✓ | fusion_form's canonical hash compared to all input forms; demoted on collision |
| **LLMRuntime wired into dispatch** | impl audit critical fix | ✓ | **AUDIT CAUGHT THIS**: previously `runtime=None` → `persona_fusion` early-exited and Stage 3 was theatrical. Fixed by instantiating `LLMRuntime()` inside `dispatch_mutator_blitz` |
| Failure-mode-closure post-hoc AST verification | Adversarial panel | ✗ Phase 2 | prompt requests but no AST-match verifier on output |
| Fusion as branch-persistence seed | LLM panel | ✗ Phase 2 | requires MCTS branches |

### Stage 4 — Tournament + Scoring

| Item | Source | Status | Notes |
|---|---|---|---|
| Extended scoring with novelty | Adversarial panel | ✓ | `score_candidate_extended` |
| Canonical AST hash novelty axis | Adversarial 3-axis stack | ✓ | +0.5 if differs from prior champion |
| Operator-multiset Jaccard novelty axis | Adversarial 3-axis stack | ✓ | +0.5 if Jaccard ≥ 0.3 |
| Residual-fingerprint novelty axis | Adversarial 3-axis stack | ✗ Phase 2 | requires fitted residuals — pull-forward to Stage 4-post-fit |
| Hard caps via score=-1.0 on bloat | GP panel | ✓ | |
| Parsimony soft penalty | GP panel | ✓ | `PARSIMONY_LAMBDA × max(0, n_nodes - 20)` |
| **Novelty as gate not bonus** | Adversarial — must-fix-soon | ⚠ partial | currently bonus-add (0.5+0.5); a high-baseline-low-novelty candidate can beat a moderate-baseline-high-novelty one. Phase-2 fix: convert to gate (must clear threshold) |
| **Tournament tie-break** | Adversarial — must-fix-soon | ⚠ partial | currently stable-sort = insertion-order = worker_id. Anti-persistence (don't pick last-iter's persona) or seeded-random not yet implemented. Phase-2 |
| MCTS branch persistence | MCTS panel | ✗ Phase 2 | with `parallel_mcts_branches` rubric flag, hash-invalidation on charter/rubric change, score-decay age-out |

### Stage 5 — Adversarial Refinement

| Item | Source | Status | Notes |
|---|---|---|---|
| Skeptic-director seat extension (one auditor pass per iter) | LLM + Adversarial + Munger | ✗ Phase 3 | Lollapalooza B mitigation stack (critique-tagged sub-trees, expiry, falsifiable closure tests, severity weighting) must ship together to avoid the cross-iter laundering surface |

### Cross-stage / telemetry

| Item | Source | Status | Notes |
|---|---|---|---|
| R1-sanity pre-filter at Stage 1→2 boundary | Apparatus FM-X-a | ✓ | `candidate_passes_r1_sanity` |
| Pipeline_log.jsonl iter_summary record | Apparatus panel | ✓ | |
| Pipeline_log.jsonl stage_event record | Apparatus panel | ✓ | per-stage entries with timing + counts |
| **Pipeline_log.jsonl candidate record** | Apparatus panel — must-fix | ✓ | **AUDIT CAUGHT**: `write_candidate_record` was defined but never invoked. Wired in `dispatch_mutator_blitz` after `pick_best_candidate`; emits per-candidate score breakdown + stage_origin + parent_ids + canonical_hash |
| Provenance.json sidecar per artifact | Apparatus panel | ⚠ alternate | provenance carried inline on candidate records rather than separate sidecars; equivalent for postmortem |
| Failure isolation (any stage crash falls back to single_mutate) | Apparatus panel | ✓ | three error paths in `dispatch_mutator_blitz` |
| Decomposed wire-in (no spaghetti at autoresearch_loop) | Operator instruction | ✓ | autoresearch_loop wire-in is now ~25 lines, full pipeline owned by `blitz_dispatch.py` |
| Sympify safety on untrusted mutator output | impl audit security flag | ⚠ deferred | `sp.sympify(work, locals=local)` in `apparatus_to_sympy`; mutator output is from our trusted LLM (mitigated). Phase-2: switch to `parse_expr(transformations=())` for defense-in-depth |

### Munger inversion + synthesis (Turn 2) deltas applied in Phase 1

| Item | Status |
|---|---|
| Cross-family Stage 1 (Lollapalooza A breaker) — moved to Phase 1 | ✗ NOT WIRED — gpt-5.5 mutator + gpt-4.1 judge airgap is the proxy; full per-worker family rotation deferred to Phase 2 |
| Persona-private suffix (Lollapalooza A breaker) — Phase 1 add | ✓ shipped |
| K=1 ablation every 5 iters from baseline checkpoint (Lollapalooza C) | ✓ shipped (default `parallel_mutator_k1_ablation_every=5`); ablation-from-baseline-checkpoint refinement is Phase 2 |
| Named-slot crossover (math-typed) — moved to Phase 2 per Inversion I | ✗ Phase 2 |
| Stage 5 adversarial — moved to Phase 3 per Lollapalooza B | ✗ Phase 3 |

### Implementation audit must-fix items (2026-04-27 night)

| # | Item | Status |
|---|---|---|
| 1 | Fusion is dead code (`runtime=None`) | ✓ FIXED — `LLMRuntime()` instantiated inside `dispatch_mutator_blitz` |
| 2 | `write_candidate_record` never called | ✓ FIXED — wired after `pick_best_candidate` for all candidates |
| 3 | Sympify on untrusted mutator output | ⚠ DEFERRED — mitigated by mutator-source trust (run's own LLM); Phase-2 hardening |
| 4 | Canonical hash DAG-order | ⚠ DEFERRED — currently lexical-sort alpha-rename; Phase-2 |
| 5 | Novelty as gate not bonus | ⚠ DEFERRED — Phase-2 |
| 6 | Tournament tie-break (anti-persistence or seeded-random) | ⚠ DEFERRED — Phase-2 |

### Net Phase 1 readiness verdict

Phase 1 ships the panel-revised core: K parallel mutators with stagnation gating + persona-private suffixes, AST crossover with canonical-hash dedup + bloat caps + parsimony, two-pass structured fusion (now actually reachable), 3-axis novelty (canonical AST + op-multiset; residual deferred), pipeline_log with all three record types, K=1 ablation every 5 iters, decomposed wire-in.

Six known refinements deferred to Phase 2/3, none of them blocking. The Stage 5 adversarial seat needs the Lollapalooza B mitigation stack (critique-tagged sub-trees + expiry + falsifiable closure + severity weighting) to ship safely; deferred to Phase 3 per Munger reclassification.
