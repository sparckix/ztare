---
description: "Pattern: using a graph diagnostic to force an agent belief update."
---
# Pattern: Graph Diagnostic → Agent Belief Update → Strategy Change

> **Up:** [Documentation map](../README.md)

**Status:** documented 2026-05-05 from one validated instance (NS Track B closure).
**Correction note, 2026-05-05:** the first robustness-extension pass used an
extractor that did not see theorem-level equality conclusions. After the
equality parser fix, equality bridges such as
`leraySelfTaxLimitPrice = continuumGlobalSelfTaxTarget` enter the graph
directly, and any earlier robustness percentages should be read as
graph-version-scoped rather than canonical.
**One-liner:** Run independent graph-theoretic diagnostics on the same artifact, hand the output to a domain-expert agent, ask it which beliefs it actually changed. The diagnostics earn their keep iff the agent's strategy changes.

Canonical graph-record fields, decision receipts, and the registry of current
graph families live
in [`graph_interfaces.md`](graph_interfaces.md).

---

## What this pattern is

A specific agentic engineering pattern for using mechanically-derived structural diagnostics to update the prior beliefs of a downstream agent (LLM, human, or both) about where to spend effort on a complex artifact (proof spine, codebase, dependency graph, etc.).

The shape:

1. **Construct a structural graph** from the artifact mechanically (no domain interpretation injected).
2. **Run a suite of independent diagnostics** that surface different aspects of the graph (not one number, multiple, complementary methods).
3. **Strip plumbing / nuisance variation** so the diagnostics aren't dominated by extraction noise.
4. **Hand the output to a domain-expert agent** along with the question: *which of these findings, if any, change your prior strategy?*
5. **Log only the belief updates**, discard anything the agent already knew or anything that left their strategy unchanged.

The pattern is descriptive, not prescriptive: it does not tell the agent what to do. It produces structural facts; the agent decides which facts are central for the current attempt.

---

## Why this differs from "running diagnostics"

Standard diagnostic workflow: produce metrics, hand them to a reviewer, reviewer reads them, reviewer decides whether they're useful. The metrics' value is asserted by the metric author.

This pattern: produce metrics, hand them to a reviewer, **the metrics' value is conditioned on whether the reviewer's strategy changes after reading them**. Metrics that surface only "things the reviewer already knew" are scored as zero-information. Metrics that surface artifacts of extraction noise are scored as negative-information (they actively misled).

The empirical question shifts from *"is this metric statistically meaningful?"* to *"did this metric move a competent reviewer's prior?"*, which is the question that matters for resource allocation.

---

## Validated instance (NS Track B, 2026-05-05)

**Setup:** 580-node / 4275-edge constraint-basin graph extracted from the NS Track B Lean proof spine. Ten diagnostics shipped: min-cut, components, feedback-arc-set, edge betweenness, Louvain communities, PageRank, HITS, Fiedler bisection, k-core, k-shortest paths. Plumbing-stripping flag (`--strip-plumbing`) removes generic-named binders before computing.

**Belief updates the agent (Codex, with NS Track B domain context) reported after reading the output:**

1. *"The old `residual → sharpTarget` bottleneck disappears after plumbing stripping. The prior 'C / raw residual chokepoint' read was partly an artifact of local binder names, not a real proof-spine signal."*, Belief change: **prior structural finding partially retracted**.

2. *"The real brittle edge is `S.payoffLimit → leraySelfTaxLimitPrice → sharpTarget`, with min-cut value 1. That puts the critical pressure on the self-tax profile LSC receipt and branch coordinate identities, not on generic residual scaling."*, Belief change: **review priority redirected from one subsystem to another**.

3. *"`nu → sharpTarget` and `residual → sharpTarget` have no directed path in the stripped graph. Viscosity / transport are not feeding the threshold wall directly. If we force them into sharpTarget, we risk creating a fake proof edge."*, Belief change: **a candidate proof move is reclassified as risky** based on graph orientation.

**Strategic outcome:** the agent reported *"I'm acting on this by tightening the self-tax/profile-to-threshold bridge, not chasing the old raw residual path."*, a concrete strategy change attributable to the diagnostic output.

---

## What the validated instance teaches

1. **Plumbing-stripping is central.** Two of the three belief updates were caused by signals that were invisible until generic binder names were filtered. A diagnostic suite without a noise filter would have produced a strictly worse result, possibly an actively misleading one.

2. **Multi-method convergence beats any single method.** The brittle bridge through `leraySelfTaxLimitPrice` was independently flagged by k-core, edge betweenness, and k-shortest paths. A single-method run would not have differentiated this from a coincidence.

3. **Negative findings are findings.** The "no directed path from `nu` to `sharpTarget`" result is an absence, not a presence, and it changed strategy. Apparatus designed only for positive findings would have missed this.

4. **The agent must be domain-competent.** A novice reading the same output would not have known that "no path from viscosity to the threshold wall" was a structural integrity signal rather than a bug. The pattern surfaces structure to a competent reader; it does not interpret.

---

## Generalization

The pattern transfers to any artifact admitting a meaningful structural graph and a competent reviewer agent:

| Artifact | Graph | Reviewer | What "belief update" looks like |
|---|---|---|---|
| Lean proof spine (this instance) | quantity × inequality | proof author / Codex | strategy change on which obligation to close next |
| Software dependency tree | module × imports | maintainer / refactor agent | strategy change on which module to refactor |
| Research paper bibliography | claim × citation | author / reviewer | strategy change on which counterargument to address |
| Knowledge graph completion | entity × relation | domain-expert agent | strategy change on which fact to verify next |

The substrate-specific work is the graph extraction and the plumbing filter. The diagnostic suite, the multi-method convergence test, and the belief-update protocol are substrate-agnostic.

---

## When NOT to apply

- When the agent has no prior strategy to update (e.g., greenfield work), there's nothing for diagnostics to move.
- When the artifact is small enough to be reviewed exhaustively. Diagnostics are a cheaper proxy for full review; if full review is cheap, skip the proxy.
- When extraction noise dominates structure. If plumbing-stripping doesn't have a principled basis for the substrate, the noise floor will produce phantom belief updates that don't survive scrutiny.

---

## Anti-patterns to avoid

- **Reporting findings without asking whether they changed strategy.** A diagnostic suite that produces 200 lines of output and zero strategy changes was negative-information.
- **Single-method reliance.** Any one centrality measure can be artifact-driven; only convergence across independent methods is robust evidence.
- **Treating diagnostics as proof.** Min-cut is not a regularity proof. Centrality is not a central argument. The pattern produces *orientation*, never *evidence*.
- **Hiding the plumbing filter from the reviewer.** Reviewer must know what was stripped, why, and on what basis, otherwise belief updates are uninspectable.

---

## Extension: from descriptive to predictive / comparative / interventional

The base pattern is descriptive, it produces a snapshot ranking and asks the agent to update beliefs from it. The following extensions add orthogonal capabilities that compose with the base. Each maps to a v5 universal-vocabulary core op as the operational instantiation:

| Extension | Frame shift | core op | Validated finding (NS Track B, 2026-05-05) |
|---|---|---|---|
| **Composite central score** | 10 rankings → 1 fused ranking | core_04 (Local-to-Global Assembly) | Single explainable rank with per-method contributions; surfaces `C, cap, grade, residual, E` as fused-top quantities |
| **Robustness ensemble** (random edge dropout) | observation → invariance test | core_05 (Canonical Form & Invariance) | **Graph-version-scoped retraction:** the first raw/passive graph downgraded `S.payoffLimit`, but the post-equality-parser graph changes that stability profile. Treat robustness output as a belief-update trigger, not as a static theorem about one node. |
| **Counterfactual edge perturbation** | observation → intervention | core_02 (Iterative Refinement Loop) | All top-betweenness edges produce identical 0.33 top-5 shift, they're functionally redundant for top-K stability, all pointing at the same structural fragility |
| **Link prediction** (Adamic-Adar baseline) | descriptive → predictive | core_06 (External Framework Importation) | Top candidate missing inequality: `radialPowerWeight ↔ calderonCommutatorResidualDecouple` (AA=5.49, 15 common neighbors). Both PDE-mathematical, same neighborhood, no current bridge |
| **Structural-role clustering** (k-means on feature vector) | rankings → typology | core_03 (Decomposition & Recomposition) | 580 nodes resolve into 6 roles. The 10-member central core (k_core=1.0, balanced hub+auth) is one cluster; the architectural-seam group (`R.bernsteinConstant`, `Low*Receipt`) is another; this typology generalizes across substrates |
| **F-row mention trajectory** | static graph → comparative-across-time | core_03 + core_06 | **Meta-diagnostic:** 16 of 25 top-composite quantities are NEVER mentioned in 267 F-rows. Either F-rows use different aliases, or this is a "silent ledger" zone, central in the proof, invisible in the experimental log |
| **Workmap-graph linkage** | diagnostic → recommendation | core_06 (Cross-Domain Translation) | The `S.payoffLimit / S.priceLimit` chokepoint is the closure target for three open obligations (`LeraySelfTaxProfilePriceStream`, `CountablePricingStream`, `LPBeatBackscatterChargeStream`), but it's only 50%-robust per ensemble, so workmap recommendations are pegged to a noise-sensitive chokepoint |

Each extension is independent CPU-feasible work; together they extend the apparatus from "describe what's there" to "describe + validate + predict + recommend + retract."

---

## What the extensions teach beyond the base pattern

5. **Robustness ensembles retroactively retract findings.** Without random-edge-dropout testing, the base pattern's belief updates are conditional on the extracted graph being noise-free, which it isn't. A robustness pass either confirms a finding (≥90% appearance across runs) or strips its central claim. This is the canonical-form (core_05) test applied to the apparatus's own outputs.

6. **Link prediction adds falsifiable predictions to the descriptive output.** The Adamic-Adar baseline produces predictions ("there should be an inequality between X and Y") at zero GPU cost. Each prediction is testable by the proof author. Win-rate is a direct measure of utility that the descriptive methods do not expose. Example: `leraySelfTaxLimitPrice ↔ continuumGlobalSelfTaxTarget` was predicted as missing, promoted to an explicit theorem-level bridge, and then disappeared from the missing-edge list after graph regeneration.

7. **Role typology generalizes; rankings don't.** A list of 580 numbered nodes is substrate-specific. Six role labels (central core, ledger transit, peripheral fringe, architectural seam, etc.) transfer to any constraint-basin graph. The typology IS the universal vocabulary instantiation at the structural-role level.

8. **F-row trajectory exposes apparatus blind spots.** When the graph elevates quantities the experimental log never names, one of two things is true: the log is using outdated terminology (calibration problem) or the apparatus and the agent have genuinely diverged on what matters (epistemic problem). Both are findings; the static graph alone hides them.

9. **The apparatus corrects its own claims under further testing.** The pattern produced a brittle-bridge claim, then produced its own correction under robustness testing and parser hardening. An apparatus that only produces affirmations is suspect; one that also retracts under further testing is more credible.

---

## Validated extension: LLM-as-graph-analyst as pattern-recognizer, not theorem-writer

**Validated 2026-05-05 (NS Track B, Codex feedback):**

Bundled the structural diagnostics (composite, link prediction, role clusters, robustness, hypergraph) into a focused prompt for Gemini 3 Pro. Asked for 3 specific Lean theorem nominations.

**Result:** Gemini surfaced one genuinely novel structural observation, the 6 components `branchA, branchB, mixedC, crossAB, crossAC, crossBC` have *identical* graph metrics (composite 0.2833, pagerank 0.033, k_core 0.167, degree 0.083), implying an algebraic-expansion pattern matching `(A+B+C)²`. Pure centrality methods can't surface this.

**Codex correction:** the structural pattern claim was right. The proposed theorem was *false as written*, the real object needs `positivePart cross*`, not raw `cross*`; negative cross terms break the claimed upper bound.

**Honest framing:**
- LLM-graph-analyst is **5-10x as a pattern-recognizer + falsifier-director, not 100x as a theorem-writer**.
- Strong: spotting structural symmetries (the polynomial-expansion observation), naming central algebraic objects, surfacing patterns the centralities miss.
- Weak: writing correct theorem signatures without domain ground-truth. Cannot be trusted to ship the actual claim.
- Correct workflow: LLM produces a pattern claim + nominal signature → domain-expert agent corrects to the actual provable form → apparatus records both versions for future calibration.

**Anti-pattern flagged:** treating LLM nominations as ready-to-prove. The signature must be reviewed by the domain-expert agent and corrected. Treat the apparatus as a falsifier/director, not a theorem-generation oracle.

---

## Final calibration (Codex, end of 2026-05-05 session)

Two-tier honest assessment after a full day of apparatus + GPU experiments:

| Component | Calibrated leverage | Why |
|---|---|---|
| **Graph / constraint-basin scripts** | **5-10x as a proof-spine accountant / falsifier** | Iteratively useful for direction and audit. Surfaced concrete things in this session: the unrestricted `∀ B, QuarticSurvivalProjectionReceipt B` vacuity risk; the decorative-branch issue in `TrackBProfileDecompositionObligation`; the updated workmap ordering after parser fixes. **Treat as accounting, not theorem truth.** |
| **LLM-as-graph-analyst (Gemini 3 Pro)** | **5-10x as pattern-recognizer + falsifier-director, not 100x as theorem-writer** | Surfaces structural patterns metrics can't (the polynomial-expansion symmetry observation). Cannot be trusted to write correct theorem signatures (the `cross*` → `positivePart cross*` correction). |
| **GNN link prediction (RGCN-lite v1)** | **0x, refuted by inductive holdout (2026-05-05)** | Bootstrap MRR 0.875 was transductive memorization. Inductive holdout: MRR = 0.0476 ≡ random baseline. The +103% bootstrap claim was REFUTED for actually-novel inequality prediction. |
| **GNN link prediction v2** (feature-aware GraphSAGE, name embeddings + struct features) | **2.6x AA inductive** (MRR 0.123 vs 0.048) | Real but modest generalization. Decision-grade as tiebreaker only. |
| **GNN link prediction v3** (asymmetric scoring + hard negatives + edge-type-aware RGCN) | **9.1x AA inductive** (MRR 0.4327, hit@10 0.90), but **practically null for closure** | Architecture changes genuinely matter. Inductive MRR 0.43 means the model ranks held-out edges in top-1.x on average. **CRITICAL CODEX FINDING (2026-05-06): v3 rediscovers REAL spine edges already covered by existing theorems** (e.g. the v3 phase-latency nomination `gramianConstant ↔ controlBudget` is already in `ns_phase_latency_control_receipt` and the GP216 flat-torus capacity field). **The useful lesson is negative: v3 is good at predicting structurally-likely edges, but the structurally-likely edges in NS are already proven. The closure bottleneck is not "what edges should exist" but "how do I prove the specific obligation", a different problem the GNN doesn't solve.** |
| **Closed-loop theorem-writer pipeline** | **Pre-validated; live leverage TBD by Codex testing** | Stage 1 typed filter + Stage 3 lake-build verifier + Stage 4 learning summary work end-to-end on synthetic input. Real leverage = ratio of (verified theorems Codex would have missed) / (Codex's review time on UNVERIFIABLE log). |

**Sharper frame after v3 → closure-utility test (2026-05-06):** the apparatus is good at *rediscovering structurally-likely edges*, but in a near-finished proof spine those edges are already proven. **Predictive accuracy ≠ closure utility.** The GNN's top-K novel predictions tend to be either (a) plumbing/under-resolved quantities with AA=0 (apparatus filter bug per Codex's regex fix), or (b) real spine edges already covered by existing theorems. Neither generates a missing closure theorem. Codex's redirect to direct profile/Lipschitz obligation hardening is the right response.

**Closure-utility verdict locked in (2026-05-06, Codex panel marking, n=22):** the LLM novelty probe produced different *slogans* (0% theorem-name overlap with standard prompt) but **0% novelty rate** when type-checked against the actual Lean spine. Every novelty-prompted nomination either restated existing theorems with new names, referenced under-resolved/wrong-typed identifiers, or proposed dimensionally-incoherent bounds. **Aggregate novelty rate: 0/22.** The novelty-prompt layer falsifies the LLM/GNN apparatus's surprise claims; it does not produce proof progress. The apparatus surfaces what the spine already contains; it does not generate missing closure theorems. **For theorem discovery this batch was 0-1x, not 10-100x.** The closure-utility ceiling at this graph scale, with this LLM/GNN pipeline, is descriptive; Codex's manual obligation hardening remains the central path.

**Sharper failure-mode diagnosis (Codex, 2026-05-06):** "Zero overlap" only means the prompt changed the *slogans*; it does not mean the prompt found usable math. The concrete failure modes:

  1. **Invent non-existent Lean objects.** Nominations referenced `Profile`, `ShellRegime`, `sharpTarget R`, `B.gamma` as a free namespace, none of which resolve to actual declarations in the spine.
  2. **Ignore endpoint exposure.** Nominations proposed bounds between quantities without checking whether the type-system makes them comparable in the operative module.
  3. **Propose scalar shortcuts already ruled out.** Direct scalar bounds the existing counterexample guards already rule out, the apparatus didn't read the falsifier corpus.

**The route to 10x is NOT "more surprising slogans."** It is: **typed nominations that resolve to current structures and produce lake-checkable source/falsifier patches.** The reference standard is the beat/backscatter guard pattern, a typed candidate that either patches a current theorem or builds a Lean falsifier, both compiler-verifiable.

**Apparatus redesign implied:**
- Reverse the order: instead of LLM proposes theorem → typed-filter rejects, do **typed-filter proposes feasible candidates → LLM selects + refines among them**.
- Output target shifts from "novel theorem signature" to "lake-checkable patch to existing source / Lean falsifier".
- Resolve every identifier to a current decl/structure/field BEFORE the LLM sees the nomination prompt; reject the un-typed ideation upstream rather than downstream.
- Existing primitives that already do this work: `lean_decl_index.py` (Stage 1 typed filter), `llm_theorem_closed_loop.py` (lake-build verifier with revision loop). The architectural fix is making typed-resolution the GENERATOR, not just the gate.

**Idea-feliz approach (2026-05-06, the correct division of labor):** the deeper insight from the day's experiments is that asking LLMs to produce typed Lean is the wrong question. The right question: ask LLM only for the COMPRESSED MATHEMATICAL INSIGHT ("idea feliz"), and let Codex own the typed-Lean translation. `scripts/public/analytics_shared/idea_feliz_generator.py` ships this. Each output insight has: structural pattern (citing graph diagnostic + node names), mathematical hypothesis in plain English (NOT Lean), suggested next move, falsifier criterion. Verdict vocabulary: `worth_translating | already_have | wrong_diagnosis | right_pattern_wrong_move`. Codex's promotion criterion: "use the generator as a SCOUT, but only promote outputs that resolve to typed Lean fields or concrete falsifier criteria." `right_pattern_wrong_move` is a valid finding, it confirms the apparatus surfaces a real co-occurrence seam even when the proposed move is dimensionally suspect. The first idea-feliz brief on NS Track B (2026-05-06) produced 4 insights; Codex's verdict on the nu ↔ shell insight: "right_pattern_wrong_move, graph sees real co-occurrence seam around viscosity and shell-scale pricing, but a direct inequality `shell ≤ nu` or `nu ≤ shell` is dimensionally suspect unless the Lean object is a nondimensionalized shell-viscosity reserve parameter." The structural seam is real; the form of the move is the apparatus's blind spot. The right division: apparatus surfaces seams, Codex names the dimensionally-coherent form.

**The unifying frame Codex articulated:** *"proof-spine accountant / falsifier, not theorem truth."* The apparatus surfaces structural anomalies (vacuous quantifiers, decorative branches, missing transitive bridges, brittle bottlenecks) and proposes nominations to investigate. The domain-expert agent decides which findings are mathematically meaningful and writes the actual proofs. Conflating accountant signals with theorem evidence is the central error class to avoid.

**The two unmet conditions for higher leverage:**
1. **Inductive / temporal GNN holdout**, train on graph state at time T excluding some nodes/files; test on edges added after T. Until run, GNN MRR is uninformative for "predict the next lemma Codex needs."
2. **Closed-loop verified theorem yield**, track over the next 10 closure attempts: how many VERIFIED nominations get added to the spine vs. how many UNVERIFIABLE ones surface real calibration findings. Until measured, pipeline value is unverified.

---

## Updated anti-patterns to avoid

- **Reporting any single-method ranking as "robust" without ensemble testing.** Treat any centrality finding as provisional until it survives ≥10 random-perturbation runs at the top-K level.
- **Predictive output without a baseline.** Before any GNN claim, the Adamic-Adar / common-neighbors baseline must be established as the floor. GNN value = improvement over baseline, not absolute prediction quality.
- **Hand-curating the role taxonomy.** Roles must emerge from k-means or equivalent on the feature vector, not from intuition. The taxonomy's value comes from being mechanically derivable.
- **Treating F-row absence as bug.** If the graph elevates quantities the log doesn't mention, the FIRST hypothesis is calibration drift, not apparatus error. Fix the calibration before declaring the apparatus wrong.

---

## Files / call-sites for the validated instance

- Diagnostic suite: `scripts/public/projects/ns/ns_constraint_basin_graph.py` (10 base methods + 5 extensions, `--strip-plumbing` default-on, `--all-analytics` runs the base 10)
  - Extension flags: `--composite N`, `--robustness N`, `--counterfactual N`, `--workmap PATH`, `--frow-temporal`, `--link-prediction N`, `--role-clustering K`
- Unified entry: `scripts/public/projects/ns/ns_graphs.py all` (wraps artifact + constraint extractors)
- Architecture-map entry: Cage v5 super-architecture map, §Standalone Gate-Pipeline Harness
- Director duty: `org/mandates/research_director_mandate.md` §Per-closure-attempt review (graph-derived, advisory)

---

## What the 100x target would require

The remaining unimplemented extension is **GNN-based link prediction** trained on the F-row trajectory of constraint-graph snapshots. Adamic-Adar gives a baseline; a graph neural network conditioned on the temporal evolution would in principle exceed it because it can learn substrate-specific structural priors. This requires:
- GPU compute (single A10 / equivalent)
- A sequence of constraint-graph snapshots (currently blocked by sparse git history; F-row-derived snapshots are the workaround)
- A held-out evaluation on Lean theorems added after some training cutoff

This is the untested high-leverage bet. The 10x extensions in this document are CPU-feasible scaffolding for it: they establish the baseline (Adamic-Adar), the validation protocol (robustness ensemble), and the typology (role clustering) that any GNN approach must improve upon. The pattern is GPU-optional at the 10x level; all four shipped extensions ran in under five CPU-minutes total on the validated NS instance.
