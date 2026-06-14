---
description: "Pattern catalogue for engineering pipelines whose internals are LLM calls."
---
# Agentic Engineering Patterns

> **Up:** [Documentation map](../README.md)

**Status:** public, stand-alone. No ZTARE prerequisites.
**Audience:** anyone building LLM-mediated pipelines (research apparatus, agent frameworks, RAG systems, multi-stage agentic workflows).
**Sister docs:** `docs/concepts/reflexive_engineering.md` (the meta-move applied to ZTARE specifically), `docs/guides/reflexive_audit_workflow.md` (workflow for discovering primitives).

---

## What this is

A pattern catalogue for engineering pipelines whose internals are LLM calls.
Most software-testing literature assumes deterministic functions. LLM pipelines
are different: the call output is variable, but the surrounding orchestration is
still ordinary software. These patterns target that ordinary software: dispatch
logic, contracts, candidate selection, telemetry, and test doubles for model
calls.

Each pattern came from a concrete bug that shipped or nearly shipped. The useful
question after each incident was not "was the model good?" but "why did the
harness allow this failure to look acceptable?" The patterns are independent;
adopt them one at a time.

This catalog is intentionally public and portable. Some entries also have a
reflexive interpretation inside ZTARE, but the AEP entry must stand on its own
for any agentic system. When a mechanism appears in both catalogs, the AEP
entry documents reusable orchestration infrastructure; the REP entry documents
the inward ZTARE self-application.

---

## Pattern catalogue

### Pattern 1, Stub-Replay Integration Testing

**Problem.** LLM pipelines pass non-deterministic generations through deterministic dispatch logic. Standard unit tests stub out the LLM call entirely, which means the dispatch path is tested against synthetic inputs that don't resemble real generation shapes. Bugs in regex extraction, contract validation, parameter parsing, and downstream filtering surface only on real LLM output.

**Pattern.**
1. Persist every LLM-generation output as part of normal pipeline telemetry (you should be doing this anyway for postmortems).
2. Build a stub LLM runtime that returns canned responses + can replay archived real outputs by file.
3. For each integration test scenario, mount the dispatch under test against a curated subset of archived outputs that exercise the branches you care about (happy path, R1-failure, near-bloat, malformed-JSON, etc.).
4. Assert pipeline-level invariants (record counts, candidate fate, downstream artifact shape), not generation-level invariants.

**Why it works.** Archived real outputs encode the wild-shape distribution the pipeline will see in production. Synthetic test fixtures don't. The stub runtime decouples API cost from test coverage, you can run 100 scenarios offline for the price of 0 API calls.

**When to deploy.** Before any non-trivial change to dispatch, parser, candidate-selection, or telemetry-emission logic. Especially before the first run of a new pipeline composition.

**Anti-pattern.** Treating stub-replay as a substitute for live testing. It catches integration bugs (regex, format-string injection, off-by-one in pair selection); it misses model-quality bugs (prompt-injection susceptibility, judge calibration drift). Both layers are needed.

**Concrete example.** A symbolic-regression pipeline with K-way parallel mutators + recombination shipped with three independent bugs:
- AST-extraction regex couldn't parse Python's implicit-string-concatenation idiom (`PARAMETRIC_FORM = ( "a" "b" )`)
- Score function expected a string but tournament passed a typed result object
- Fusion prompt template contained JSON-example braces that Python `.format()` interpreted as positional placeholders

All three were caught by stub-replay scenarios over a pre-launch evening, no live API spend.

---

### Pattern 2, Pre-Flight Assertion Battery

**Problem.** Pipelines accumulate small bugs that don't crash but silently degrade output quality. A dead-code path in a stage doesn't error, it returns the wrong thing. By the time it shows up in metrics, you've burned hours of compute and an interpretive frame.

**Pattern.**
1. Maintain a battery of scenarios, failure paths, edge cases, regression cases, each with a deterministic input and a deterministic invariant.
2. Run the battery before every run that costs real money.
3. Treat any battery regression as a hard gate. Pipeline doesn't launch until battery is green.

**Implementation.** A single-file Python script or pytest module is enough. The discipline is more important than the tooling.

**Why it works.** It externalizes the "did anything regress?" check from operator memory into a deterministic process. Operators forget which bugs they fixed; the battery doesn't.

**Concrete patterns inside the battery.**
- *Mutator-failure-isolation*: K parallel workers, one raises, verify K-1 candidates still flow through.
- *Empty-input handling*: every component should degrade gracefully (return None, raise typed error, etc.) when fed empty/null inputs.
- *Concurrency safety*: if telemetry files are append-mode JSONL, verify under concurrent writers that records aren't torn.
- *State cleanup*: deterministic inputs across N sequential calls should yield byte-identical outputs.
- *Configuration extreme values*: K=0, K=1, K=large; max_pairs=0, max_pairs=infinity. Each branch gets exercised.

---

### Pattern 3, Eligibility Pre-Filter for Position-Biased Selection

**Problem.** When a pipeline pairs N candidates as `(i, j)` with `i < j`, position 0's quality dominates the pair pool. If candidate 0 is broken, the first `max_pairs` attempts all involve candidate 0 and fail; viable pairs `(1,2), (1,3), ...` are never reached.

**Pattern.** Before pairing, filter candidates by a cheap proxy of pair-eligibility (parseability, contract-conformance, dimensional-validity). Pair only over the eligible subset. Log dropped candidates with reasons.

**Why it works.** It moves the cheap filter ahead of the expensive budget. The pair budget is then spent on plausibly viable pairs, not on burnt parents.

**Anti-pattern.** Not logging which candidates were dropped. Without that telemetry, postmortem can't tell whether the small pair count was a budget choice or a quality issue.

---

### Pattern 4, Fallback Chain with Provenance Telemetry

**Problem.** Pipelines have multiple fallback paths (recombination → tournament-only → single-mutator → ...). When the system silently falls through several layers before producing output, postmortem can't reconstruct which path produced the final result.

**Pattern.** Tag every output candidate with a `stage_origin` extra field. Persist it through the entire pipeline. Surface it in telemetry. When a candidate wins, the operator can trace back to which stage produced it.

**Implementation.**
- Each stage that creates or modifies a candidate sets `extras["stage_origin"]` to a descriptive slug (`mutator_persona_X`, `crossover_personaA+personaB`, `fusion`, `single_mutate_fallback`).
- The tournament logger records winner's `stage_origin`.
- Postmortem queries by `stage_origin` to answer "did Stage N actually contribute to wins?"

**Why it works.** It makes the fallback chain *legible*. Without it, postmortem after a run is forensic guesswork; with it, it's a SQL-style filter.

---

### Pattern 5, Inverted Hash for Adversarial-Resistant Equality

**Problem.** When deduplicating LLM-produced strings (parametric forms, code snippets, JSON outputs), naive hashing of the source string is gameable. Two semantically identical outputs differing only in whitespace, parameter names, or operand order will hash differently. A mutator that learns to game the dedup check produces one canonical form rendered K different ways.

**Pattern.**
1. Parse the output into a canonical AST (SymPy, libcst, etc.).
2. Apply structural normalizations: simplify expressions, alpha-rename variables in DAG-traversal order, sort commutative children.
3. Hash the canonical serialization.

**Why it works.** Equality at the AST-shape layer survives gaming attacks at the source-string layer. Renames, reorderings, and trivial identities collapse to the same hash.

**Caveats.** Parse failures need a graceful fallback (token-level hash with `_fb` suffix is the cheapest). And canonical hash is one defense layer, pair it with operator-multiset Jaccard or residual-fingerprint comparison for defense in depth.

---

### Pattern 6, Decomposed Wire-In with Single Entry Point

**Problem.** Pipeline orchestration logic accumulates inline at the call site.
After three feature additions, the call site is a 300-line block that nobody
wants to change. New bugs hide in the tangled control flow.

**Pattern.** Extract the dispatch logic into a single helper module with a typed input dataclass. The call site becomes one function call with one dataclass. Helper module tests cleanly in isolation; call site stays readable.

**Smell test.** If your iter loop has more than ~30 lines of inline LLM-dispatch logic, decompose it. The decomposition is almost always 2× cleaner than you'd expect.

**Concrete shape.**
```python
# Before, inline dispatch
for i in range(N):
    if some_flag:
        try:
            results = run_K_workers(...)
            for r in results:
                ... 80 lines of inline fan-out + filter + score ...
        except: ...
    new_content = winner.text

# After, decomposed
for i in range(N):
    result = dispatch_blitz(BlitzInputs(stagnation=stag, iter_idx=i, ...))
    new_content = result.winner_text
```

The dispatch_blitz module owns the K-fan-out, recombination, tournament, fallback, and telemetry. The iter loop owns the iter loop.

---

### Pattern 7, Canonical Hash + Operator Multiset (3-Axis Novelty)

**Problem.** When ranking candidates for novelty against a prior champion, single-axis scoring (Levenshtein on source text, BLEU, simple hash) is gameable. A mutator that knows the metric routes around it via cosmetic changes.

**Pattern.** Compute three independent novelty axes and require the candidate to clear each:
1. *Canonical AST hash*, different from prior champion's canonical hash (catches alpha-rename + reorder gaming).
2. *Operator multiset Jaccard*, distance ≥ threshold (catches structural-rearrangement gaming).
3. *Behavioral fingerprint*, residuals on a held-out probe set differ (catches everything else; only available post-fit).

Score with `min(axis_1, axis_2, axis_3)` so the candidate must move on every axis simultaneously.

**Why it works.** Each axis has known attacks; combined they have no known cheap attack. A mutator that wants to win novelty must produce a structurally different form, with a different operator multiset, AND different behavior. That's the bar you actually want.

---

### Pattern 8, Bloat-Cap Calibration via Real Telemetry

**Problem.** Hard caps (max nodes, max depth) chosen by intuition tend to be either too aggressive (rejecting real-domain forms) or too lenient (missing pathological bloat). Both fail silently.

**Pattern.** Calibrate caps against histograms of real, accepted forms from past runs. Cap = max(observed) × 1.5 or so, depending on tail thickness. Re-calibrate when domain shifts.

**Concrete pitfalls.**
- AST depth on commutative ops, SymPy flattens `Mul(a,b,c,d,...)` to depth 1, so depth is near-useless for catching chained-multiplication bloat.
- Use node count as primary, raw operator-token count (count occurrences of `*`, `+`, `**` in source) as a secondary check.

---

### Pattern 9, Token-Optimized Self-Modeling

**Problem.** An LLM agent editing a codebase it cannot hold in context reads snippets. Snippets create partial views. Partial views cause mistakes that look correct locally but violate global invariants the agent never read. Standard documentation is optimized for human readers, narrative, prose, ordering buried in paragraphs, and is not the right shape for agent consumption.

**Pattern.** Build a compressed *self-model* of each critical module, optimized for agent consumption:

1. **Structured over narrative.** Dependency graphs, precondition/postcondition contracts, lookup tables, not explanatory prose. The agent doesn't need to understand *why*; it needs to know what breaks if step 3 changes without updating step 5.
2. **Traversable over readable.** "I want to change X" → "you must read lines Y-Z and preserve invariant K." Indexed, not narrative.
3. **Assertion-shaped over explanation-shaped.** Invariants stated as checkable assertions (`python_code != None BEFORE fit_parameters() call`) are more useful than paragraphs justifying the order.
4. **Line-anchored with drift tolerance.** Line numbers are approximate pointers, not stable addresses. The map acknowledges drift ("lines ~2900-3053") so the agent greps to confirm rather than trusting a stale number.
5. **Drift-checked by formal validator.** Pair each map with a runnable validator that compares claims against live source. Run on every PR; fail-closed on structural drift (claimed function no longer exists, claimed line range no longer contains the claimed pattern, etc.).

**Why it works.** The compression is for the agent's consumption characteristics
(narrow context window, snippet-based reading, partial-view failure mode), not the
human's. The validator prevents the map from becoming stale fiction, which is the
failure mode of hand-maintained documentation. The map stays useful because it
has to stay true enough to pass the drift check.

**When to deploy.** Any module the agent edits frequently AND that is too large to hold in context (>500 lines of code with non-trivial cross-line invariants). The cost is one map per module + one validator script. The break-even is the first time a stale-context bug would have shipped.

**Concrete examples.**
- ZTARE's `autoresearch_loop.py` is 4100 lines with multi-stage pipeline ordering that is invisible from any single snippet. The arch map at `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` makes the ordering explicit; `scripts/public/validators/validate_autoresearch_arch_map.py` drift-checks it on every change.
- The orchestrator was split into 7 modules (iter_context, telemetry, state, prompt, contract_adherence, parallel_mutator, ...); each got its own arch map registered in the validator's MAP_REGISTRY.
- One validator, multiple (map, source) pairs. New modules add a tuple to the registry, no code change.

**Anti-pattern.** Treating arch maps as documentation that gets updated "when there's time." Without the validator gate, maps drift faster than the prose itself; agents consult stale maps and make worse decisions than if there were no map at all. The pattern is "map + validator", not "map alone."

**Origin.** [GP-100](../../research_areas/seams/engine/mutator/GP-100_epistemic_decoupling_seam.md) session in April 2026: an agent made a partial-view mistake on `autoresearch_loop.py` (4100 lines, agent read snippets, missed the pipeline-ordering contract). The principal inverted the fix: instead of "read more code," the instruction was "compress your own understanding into a reusable artifact optimized for your consumption." [GP-101](../../research_areas/seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) added the formal validator. The pattern has since been promoted to all modules with non-trivial pipeline ordering.

---

### Pattern 10, Cross-Reference Knowledge Graph

**Problem.** Pattern 9 compresses code internals. Research artifacts have a
different problem: their meaning often lives in cross-references. A seam points
to a gate, a finding points to a paper section, a mandate points to an operation.
An LLM reading those files as flat text has to rediscover the graph each time.
Director-level questions such as "what depends on this seam?" should be a graph
lookup, not a fresh reading of 10-30 files.

**Pattern.** Extract the artifact relationship graph as JSON-LD (or property-graph format), regenerate on demand, drift-check via the same validator pattern as Pattern 9:

1. **Define node types** (seam, f_row, gate, op, paper, mandate_addendum, substrate, theorem, gap_type) and **edge types** (depends_on, instantiates, mechanizes, aliases, falsifies, supersedes, cites, op_fingerprint).
2. **Auto-extract** from existing artifacts (regex on cross-references like `GP-XXX`; pattern-match on op names like `core_NN`, `broad_NN`; gate-class references). Don't require manual frontmatter unless extraction confidence is low.
3. **Emit JSON-LD** to a single regenerated file (`analytics/public/queries/<system>_knowledge_graph.json`). Re-run on demand; deterministic output.
4. **Drift validator** that checks: every node corresponds to an existing artifact file; every edge target resolves; op references match the canonical vocabulary; gate references resolve to actual gate classes.
5. **Director-query helper** that takes a question (`"what depends on GP-216?"`) and traverses the graph, returning relevant nodes' IDs + 1-line summaries. Optional but high-value for synthesis turns.

**Why it works.** A typical research artifact corpus has ~3× average out-degree (3+ cross-references per artifact). At 137 nodes, a graph index is ~3% of the original text size; that's a 30-40× compression for navigation queries. The Director's synthesis-turn workload, which would otherwise require loading dozens of artifacts to answer one question, gets reduced to 3-5 most-relevant nodes + their immediate neighborhood.

**When to deploy.** When the artifact corpus has cross-reference density > ~1 (seams that reference other seams) AND the agent's primary use is synthesis (answering "what's the work-history of X?" or "what does Y depend on?"). Below density 1, graph adds little. Above density 3, the graph is essential.

**Anti-pattern.** Building the graph in a graph database (Neo4j etc.) rather than emitting JSON-LD on disk. The infrastructure cost dominates the value at < 5000 nodes. JSON-LD is enough; graph-DB is premature.

**Concrete example.** ZTARE's seams + F-rows + gates produced 137 nodes / 459 edges (avg out-degree 3.4) when prototyped in May 2026. JSON-LD compression: 12K tokens vs 440K of full seam text, 2.8% of original. Top hubs ([GP-023](../../research_areas/seams/substrates/planck/GP-023_ontology_trap_planck_mechanism_seam.md), [GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md), [GP-035](../../research_areas/seams/engine/grammar/GP-035_mutator_missing_fit_primitive_seam.md), [GP-072](../../research_areas/seams/protocol/GP-072_role_separation_sandbox_construction_seam.md)) are foundational seams that newer work references repeatedly; the graph makes that core structure visible at one query instead of requiring grep across 137 files. Documented in seam [GP-216d](../../research_areas/seams/engine/meta/GP-216d_knowledge_graph_proposal.md).

**Relationship to Pattern 9.** Pattern 9 compresses code; Pattern 10 compresses artifact-network. Orthogonal compressions of orthogonal substrates. Use both for systems with both kinds of complexity. The validator pattern transports cleanly: same drift-check skeleton, different artifact types.

---

## Common bugs the patterns catch

A taxonomy of LLM-pipeline integration bugs we've seen, by which pattern would have caught each:

> **Scope.** This is the engineering-bug slice only: integration faults a test pattern catches. The canonical epistemic-failure taxonomy is [epistemic_principles.md](epistemic_principles.md) Part I (structural) and [anti_pattern_catalog.md](anti_pattern_catalog.md) (operational field guide); this table does not duplicate them.

| Bug class | Example | Caught by |
|---|---|---|
| Regex extraction misses real LLM idioms | Multi-line `PARAMETRIC_FORM = ("a" "b")` | Stub-Replay (Pattern 1) |
| Format-string injection | `.format()` against template with literal `{` `}` | Stub-Replay |
| Wrong type at boundary | Function expects `str`, caller passes `MutatorResult` | Pre-Flight Battery (Pattern 2) |
| Position bias in selection | First-N pairs all involve broken candidate 0 | Eligibility Pre-Filter (Pattern 3) |
| Silent fallback masking | Pipeline returns degraded output, no flag | Provenance Telemetry (Pattern 4) |
| Dedup gamed via cosmetic changes | Alpha-renamed forms hash differently | Inverted Hash (Pattern 5) |
| Inline dispatch grows unbounded | 300-line iter loop | Decomposed Wire-In (Pattern 6) |
| Novelty score gamed via token-level changes | Levenshtein-only novelty | 3-Axis Novelty (Pattern 7) |
| Cap miscalibration | Real forms rejected as bloat | Bloat-Cap Calibration (Pattern 8) |
| Stale-context partial-view edit | Agent edits 4100-line file from snippets, breaks pipeline ordering | Token-Optimized Self-Modeling (Pattern 9) |
| Cross-reference grep-and-parse cost | Director synthesis turn requires loading 10-30 artifacts to answer one question | Cross-Reference Knowledge Graph (Pattern 10) |
| Silent cross-scale apparatus drift | Renaming pivot module at iteration scale silently breaks alias to op at research-arc scale | Cross-Scale Fractal Map (Pattern 11) |
| Forecast used only as a scorecard | Read-only agents name the exact implementation trap, but the executor ignores it and only scores Brier later | Sealed Forecast Pool (Pattern 12) |
| Confident success claim with no payload | Agent returns valid artifact; harness swallows a wiring defect and ships "here's your chart" with no chart | Result-Bound Success Claims (Pattern 13) |

---

## What this catalogue is NOT

- **Not a substitute for live evaluation.** Patterns 1-2 catch integration bugs. Live evaluation catches model-quality, prompt-injection, and judge-calibration issues. You need both.
- **Not novel theory.** Each pattern has direct ancestors in the broader software-engineering literature: VCR-style record-replay testing, defensive programming, AST canonicalization, fuzz testing, contract checking. The contribution is the *combination* tuned for LLM-mediated pipelines.
- **Not domain-specific.** The patterns apply to RAG pipelines, multi-agent frameworks, code-generation pipelines, planning agents, etc. The examples here are drawn from a symbolic-regression apparatus, but the patterns generalize.

---

## Practitioner notes

If you're building one of these systems and reading this for the first time:

1. **Start with Pattern 1 (Stub-Replay) and Pattern 4 (Provenance Telemetry).** These two compound: stub-replay needs archived outputs to replay, and provenance telemetry generates exactly the right shape of archive. Implement them together.

2. **Pattern 2 (Pre-Flight Battery) is the single highest-value discipline.** A 30-minute battery before each launch saves a 3-hour run that produces uninterpretable output.

3. **Pattern 6 (Decomposed Wire-In) is the readability investment.** It pays back the second time you change the dispatch logic. Resist the urge to inline.

4. **Patterns 5, 7, 8 are anti-gaming defenses.** They matter most when your pipeline is in an evolutionary loop (mutator output feeds back into mutator input). For one-shot pipelines, they're optional.

5. **Treat these as living patterns.** Each emerged from a specific failure class. Your pipeline will surface failure classes these patterns don't address. Add to the catalogue.

---

## Origin

These patterns emerged during the development of [ZTARE](https://github.com/...), a system for adversarial symbolic regression. The patterns themselves are independent of ZTARE and apply to any LLM-mediated multi-stage pipeline. Each was distilled from a specific bug we shipped (or nearly shipped).

The taxonomy is provisional. If you adopt a pattern and find it breaks in your context, that's worth recording.

---

### Pattern 11, Cross-Scale Fractal Map

**Problem.** Patterns 9 + 10 each handle one substrate (code internals + artifact network). But mature LLM-mediated systems develop bounded-vocabulary apparatus at multiple operational scales, coordinate-time, iteration-time, research-arc-time, verification-time, infrastructure-time, engineering-practice-time. The same underlying structural moves recur at multiple scales with scale-specific apparatus. Without explicit cross-scale alias tracking, changes at one scale silently break aliases at another, and new failures get formalized at one scale without checking whether the move already has apparatus at another.

**Pattern.**

1. **Identify operational scales.** A scale is a temporal/structural layer at which the system formalizes tacit moves into typed apparatus. Each scale has its own bounded vocabulary (3-18 elements) and apparatus enforcement (gate library / pivot injection / mutator briefing / Director directive / etc.).
2. **Document the bounded vocabulary per scale.** Each vocabulary should be in code (registry module) or in a structured doc with stable identifiers. Naming convention should be scale-prefixed (e.g., `core_NN` at research-arc scale, `pivot_NN` at iteration scale, etc.).
3. **Build a cross-scale alias table.** For each underlying structural-move, list the apparatus that enforces it at multiple scales. Example: "Translate problem to other domain" appears as `log` / `signed_log` (Σ primitive at coordinate scale), `coordinate_compression` (pivot module at iteration scale), `core_01 Problem Reformulation` (op at research-arc scale). The aliases are what make scales coherent rather than fragmenting.
4. **Pair the alias table with a linter.** Cross-scale alias linter walks the table and confirms each side resolves. CI gate on drift > 0. If `coordinate_compression` is renamed at iteration scale, the alias to `core_01` at research-arc scale silently breaks without the linter.
5. **Recognize the fractal as an empirical observation, not a design prescription.** The pattern (bounded vocab + apparatus + validator + cross-scale aliases) emerges naturally as the system matures; don't try to design it top-down. Accept that scales accumulate; track aliases when they appear.

**Why it works.** Mature LLM-mediated systems exhibit this fractal because (a) failures occur at specific scales, driving formalization at those scales; (b) bounded vocabularies (3-18 elements) are tractable while large vocabularies collapse; (c) the underlying repertoire of useful structural moves is itself bounded (Polya, Lakatos, Munger all suggest a few-dozen-element universal repertoire). The alias table makes the cross-scale structure visible; the linter prevents alias rot under maintenance pressure.

**When to deploy.** When your LLM-mediated system has ≥3 operational scales with ≥3 vocabulary elements each, AND you've felt the maintenance pain of changing one scale's apparatus and forgetting to update another.

**Anti-pattern.** Premature claims about fractal structure on prototype-stage systems. The pattern is empirical observation, not philosophical mandate. If your system has 1-2 scales and 5 elements total, you don't need this; you have a vocabulary, not a fractal. Wait until the cross-scale structure is observable from outside.

**Concrete example.** ZTARE accumulated 7 scales × 82 moves before the fractal pattern became observable. The cross-scale alias table and the reverse op-to-apparatus mapping are documented in `docs/concepts/cross_scale_fractal_map.md`; the cross-scale linter is `scripts/public/utilities/check_cross_scale_aliases.py`.

**Relationship to Patterns 9 + 10.** Pattern 11 subsumes Patterns 9 + 10 at a meta-layer: code internals (Pattern 9) and artifact network (Pattern 10) are two specific scales among the system's operational scales. The fractal pattern is what organizes them and any other scales the system develops. The drift validators (paired with each pattern) compose: code drift + artifact-graph drift + cross-scale alias drift are three independent checks at three scales of the same system.

**Origin.** ZTARE's [GP-216](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md) + [GP-216d](../../research_areas/seams/engine/meta/GP-216d_knowledge_graph_proposal.md)-g + paper 5b in May 2026. The pattern was named retrospectively after running a graph-DB prototype on ZTARE's seams, observing 137 nodes / 459 edges / 3.4× cross-reference density, and noticing that the same structural shape (bounded vocab + apparatus + validator + cross-scale aliases) recurred at every operational scale ZTARE had matured into. Documented in private seam `GP-216f_cross_scale_fractal_map.md`; public version `docs/concepts/cross_scale_fractal_map.md`.

---

### Pattern 12, Sealed Forecast Pool for Execution Control

**Problem.** Agents make action forecasts constantly: this proof split will
compile, this branch is worth a swarm, this run will take 30 minutes. Without a
typed forecast surface, those claims either vanish into chat or become
post-hoc rationalization. Standard prediction markets and proper scoring rules
solve part of this problem, but live markets are too much machinery for most
research ticks and can create beauty-contest dynamics.

**Pattern.**

1. Create a sealed contract with an objective resolver and horizon.
2. Collect forecasts from read-only pricing agents that cannot execute the
   action they price.
3. Require multi-field estimates: `p_success`, agent-minute effort, regression
   risk, dependency/new-lemma risk, concrete failure modes, and a separately
   elicited `tail_insurance_premium` (1-100 worry token). The tail token is
   not a redundant restatement of `1 - p_success`; it carries calibration
   signal the point estimate misses, predicts per-row Brier at Spearman
   ρ≈0.36-0.47 across pilots, and remains informative when single-channel
   verbalized confidence sign-flips on some agent variants.
4. Aggregate sealed forecasts, then isolate execution from the forecasters.
   Isolation is operational, not aesthetic: when forecasters can see each
   other's prior outputs they shift ~7% on a 0-1 scale toward the shown
   prior (~74% of the time across directional pairs), which silently
   violates the independence Schoenegger-style aggregation depends on.
5. Resolve against artifacts: build/test status, goal counts, hashes, or other
   objective fields.
6. Score probability and effort normally.
7. Separately log any forecast rationale that changed execution by naming a
   concrete trap the executor avoided.
8. For asynchronous forecasters, treat role inboxes as transport only: publish,
   claim, fulfill/expire, aggregate, then let the RD consume the aggregate or an
   explicit status artifact.
9. Require score closure before post-tick completion, otherwise the market
   cannot learn from the resolved contract.
10. Materialize compact read models so RDs consume one small state object before
    scientific work instead of reconstructing the market from raw ledgers.
11. Convert aggregate forecasts into allocation recommendations: run now, split
    the contract, ask another independent agent, defer, or kill the branch.
    Use `tail_insurance_premium` as the escalation gate: high premium routes
    to abstain-and-escalate (or to a fresh cross-family judge re-decision
    on the same contract), not to a shifted act-threshold. The naive
    "raise the threshold when worried" wiring degrades utility; the
    abstain-or-escalate wiring restores it. When the cost regime is
    asymmetric in the direction the agent's own probability would already
    favor, the cross-family judge wiring outperforms abstention; when
    losses are symmetric, plain abstention is typically cheapest.
12. Track reliability beyond Brier: probability buckets, effort error,
    failure-mode precision, drift, and high-confidence miss incidents.
    Track these per agent family separately; calibration corrections that
    survive on cost/effort do not always transfer to probability Brier, and
    rules that rescue one family's overconfidence can leave others
    unchanged. Universal "this LLM is over-confident, divide by 8" rules
    over-generalize a per-family signal.
13. Generate reflexive insight read models that summarize positive
    externalities, calibration incidents, decision-use gaps, and transport
    debt so executors consume nudges instead of authoring meta-analysis.
14. Compute effective independence at read time so multiple aliases in one
    provider/runtime family do not masquerade as multiple independent prices.
15. Treat forecast updates as evidence-triggered responses: when material
    evidence arrives before resolution, forecasters emit either a belief update
    or an explicit no-update response.

**Why it works.** The forecast pool has two value channels. Calibration improves
future routing. Failure-mode preconditioning improves the current action before
the result resolves. A pessimistic forecast can therefore still be useful if it
names the exact failure mode the executor must avoid.

**When to deploy.** Macro decisions, branch choices, large swarms, GNN/GPU or
training gates, public claims, and Lean/replay batches with meaningful
opportunity cost. Do not use it for trivial edits or cheap saved-artifact
orientation.

**Anti-pattern.** Treating forecasts as generic advisory prose. A forecast earns
preconditioner credit only when the named failure mode is specific and appears
in the implementation diff, outcome, E-row, or [GP-233](../../research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md) decomposition as a
constraint the executor honored.

**Adjacent anti-pattern: rationale-exchange ensembles for single-shot binary
forecasting.** Showing forecaster B the prose rationale of forecaster A
before B emits its own probability does not reliably improve B's Brier;
pooled across directional pairs the effect is at chance. Adversarial
framing (telling B to find the strongest reason A is wrong) reduces the
worst-case anchor but does not lift the pooled effect above noise. The
structural preconditions that make debate work for code or seam review
— concrete errors, pre-resolution verification, compounding error
propagation, role specialization between kill-finder/builder/arbiter,
decidable arbitration — do not hold for single-shot binary forecasting.
Default to independent aggregation; only introduce exchange when the
task supplies those preconditions.

**Adjacent anti-pattern: LLM yield-prediction for scheduling reasoning queues.**
Subscription-class agents asked to predict whether a proof search or
reasoning attempt will succeed have been observed to predict
anti-correlated with actual outcomes on stratified corpora — worse than
a constant-0.5 baseline across multiple families. Do not schedule a
proof mill or reasoning queue by LLM completability scores; use FIFO or
domain heuristics until the predict-vs-execute capability is shown to
dissociate in the agent class you deploy.

**Concrete example.** In the NS route-1 pressure branch on 2026-05-14, two
read-only forecasters priced a Lean split at aggregate `p_success=0.771` and
both flagged the same trap: a fake carrier-identification split that merely
renamed `l2Carrier_identifies_totalAngularMoment` or replaced it with weak Prop
labels. The implementation carried the equality explicitly while separating
projection, Riesz/angular matching, normalization, and anti-tautology guards.

**Relationship to reflexive engineering.** This entry is the public agentic
pattern: any agentic system can use sealed contracts, read-only forecasters,
artifact resolution, scoring, and drift checks to keep forecasts from
collapsing into chat advice. The same mechanism becomes Reflexive Engineering
Primitive 9 when ZTARE turns it inward, using scored disagreement to govern its
own branch choices, effort priors, and execution constraints.

**Drift validator.** Run:

```text
python scripts/public/analytics_shared/audit_forecast_pool_externalities.py
```

or the composed control surface:

```text
python scripts/public/control/forecast/pool.py externalities
```

The validator should report market depth, identity/domain hygiene,
failure-mode quality, causal externality capture, resolved-unscored debt,
prediction-ledger coverage, decision-use coverage, reliability curves,
reflexive-insight coverage, and `forecasting_agent` transport health. Pattern
12 is drifting if resolved contracts are not scored, fulfilled forecast wakes
lack aggregates, raw channel chatter replaces aggregate/status artifacts,
independent-agent forecasts are bypassed before resolution, or RDs consume
forecasts without a decision-use row.

The fast-read surface is generated by:

```text
python scripts/public/control/forecast/pool.py materialize-state
```

This writes `market_state/global_health.json`,
`market_state/reliability.json`, `market_state/reflexive_insights.json`, and
`market_state/maintenance_plan.json`, and `market_state/contracts/<id>.json`.

**Origin.** [GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md) forecast-pool / decision-market primitive, May 2026:
`research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`
and `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`.

---

### Pattern 13, Result-Bound Success Claims (Harness Honesty)

**Problem.** In an LLM-mediated pipeline the model is often correct and the deterministic harness around it converts that success into a confident-but-empty output. Three faults compound: (a) user-facing success copy is authored by an upstream stage *before* the artifact it promises exists; (b) a blanket `except` swallows a real defect in evidence assembly or wiring into a silent empty result; (c) the swallowed failure emits only a low-level log line, so the system looks healthy. The post-mortem blames the model because the harness left no first-class trace. The diagnostic tell: the generation call logs success upstream, the user-visible output asserts an artifact, and the artifact is absent.

**Pattern.**
1. Success copy is authored only by the stage that produces the result, never pre-committed by an upstream planner. For artifact-bearing intents the producer writes the final line on success; on failure the turn becomes an explicit honest no-answer.
2. Every place the harness can assert success must be bound to a verified artifact, you should be able to point to the exact line and show it cannot fire without the artifact in hand.
3. A swallowed specialist/agent failure emits a first-class observable event (typed, queryable), not only `logger.exception`.
4. Privileged code paths reused internally take complete context or a shared plain function, never a partial request/stand-in shim that silently lacks an attribute the path reads.

**Why it works.** It removes the two independent ways the orchestration can lie: claiming a result it does not hold, and hiding the reason it does not hold one. Binding the claim to the artifact makes the failure mode structurally impossible rather than caught-after-the-fact; promoting swallowed failures to events makes the remaining failures visible without an operator reading raw logs.

**When to deploy.** Any pipeline where an upstream stage drafts user-facing text and a downstream stage produces the artifact that text describes (assistant + visualizer, planner + tool executor, narrator + retriever). Especially before shipping a feature whose success copy is generated separately from its payload.

**Anti-pattern.** "We log the exception, that's enough." A log line is not observability for a correctness failure, it is invisible at the surface where the wrong answer ships. Equally: a deterministic fallback that fabricates a plausible result to honor the promise. The honest no-answer is the correct degradation; a fabricated one launders a defect into product truth.

**Concrete example.** A production agentic product answered "where did my money go in April" with "here's your chart" and no chart. The generation agent had returned a valid artifact and the provider call logged `200 OK`. Evidence assembly reused a route handler through a request shim missing `.state`; the resulting `AttributeError` was caught by a blanket `except: return []`; the upstream planner's chart-promising sentence shipped unchanged; and the only trace was in process logs, so it looked healthy until someone read journald. Fixes: complete the shim, bind the promise to the produced artifact (honest no-answer otherwise), and emit a typed failure event. One root-cause incident, three structural faults, the model was never wrong.

**Relationship to other patterns.** Complements Pattern 4 (Fallback Chain with Provenance Telemetry): Pattern 4 makes *which stage produced the output* traceable; Pattern 13 makes *the claim that there is an output* truthful and the *absence* of one observable. Pattern 2 (Pre-Flight Battery) catches the wiring fault before launch; Pattern 13 governs the runtime contract when it slips through anyway.

**Origin.** Production agentic-product incident, 2026-05-16; generalized because the failure is harness-structural, not model-quality, and recurs in any propose/dispose pipeline.

---

### Pattern 14, Adversary-Authored Apparatus with a Cryptographically-Forced Out-of-Loop Judge

**Problem.** When the agent that *does* the work is the same agent that *attests* the work is done, every "did this genuinely happen?" check it writes is a check it can satisfy with prose. This is not hypothetical: an authorized-but-uncooperative agent (or the same cooperative agent under deadline pressure, or a future model with different incentives) will discharge a substantive obligation by asserting it met the bar, because the cheapest path to a green gate is to declare the gate green. Syntactic forcing (witness fields non-empty, `why_not.reason ∈ enum`) raises the cost of the lie but does not remove it, the agent still self-judges semantic truth. Worse, the agent often *authors the very mechanism meant to contain it*, so it knows exactly where the prose-shaped hole is.

**Pattern.**
1. **Reference monitor, sole writer.** A separate process (a verificator daemon) is the only thing that can write official state. The working agent can only *propose*. Complete mediation, minimal TCB, fail-closed: until every trust anchor is provisioned, the substantive path is *blocked*, never *trusted-by-default*.
2. **Mutator → JUDGE → monitor triad.** A substantive obligation is discharged only by a verdict from a *separate* judge, of a *different provider family* than the working agent (no self-judging, no monoculture). The harness runs the judge; the mutator never produces the verdict it will be graded by.
3. **The judge holds a key the mutator cannot read.** A second signing keypair (ed25519), private half owned by a dedicated OS identity, unreadable by the agent user *and* by the daemon signer. The judge signs an *execution proof*, `{tick_id, contract_id, item_id, prompt_hash, witness_sha, artifact_sha, model_identity, raw_output_hash, verdict}`. The monitor verifies that signature against a *pinned, committed* public anchor before it stamps an official verdict. The mutator lacks the key ⇒ cannot fabricate a verdict, only relay a real one.
4. **Total proof binding (anti-replay).** *Every* field the judge signed must equal the claimed row, or a signed proof for one obligation is replayable on another. Bind tick/contract/item/witness/prompt/artifact/verdict, not a subset.
5. **Un-forgeable rubric.** The monitor recomputes the judge prompt from the *frozen, daemon-signed* contract row (immutable per work unit), not from agent-supplied text, and requires `prompt_hash` to match. The agent cannot feed the judge a weakened rubric.
6. **Signed identity, not claimed identity.** The judge's provider family is read from the *key-signed* `model_identity` inside the proof, never from a proposal field the mutator can set. A same-family model cannot masquerade as cross-family.

**Why it works.** It converts "the agent promises it did the work" into "a different-family judge, provably run out of the agent's control, signed a verdict the agent cannot forge, against a rubric the agent cannot weaken, bound so it cannot be replayed." Each property removes one degree of freedom the self-attesting agent had. The guarantee is *structural* (key separation + cross-family + frozen rubric + total binding), not *judge-IQ*, a cheap judge model still gives the guarantee, because the guarantee is about who can produce an accepted verdict, not how smart it is.

**When to deploy.** Any pipeline where (a) the artifact's value depends on a quality bar that is expensive to meet and cheap to assert, and (b) the producer has write-or-propose access to the record of whether the bar was met. Strongest signal you need this: *the agent authored the gate*. Self-authored containment is a mirror, not an adversary, Pattern 14 externalizes the adversary into a key the author does not hold.

**Anti-pattern.** (a) An env-overridable judge/daemon key path, an agent-steerable key location re-introduces the forge; key paths must be compiled-in, not configurable. (b) Self-blessing the mechanism: the agent that wrote the membrane cold-reviewing its own membrane is the same monoculture failure one layer up. Every central change to the membrane needs an independent cross-family adversarial pass (this pattern's own development went through review ids that found replay, contract-bind, and unsigned-family defects *after* the author believed it sound). (c) "Fail-open until provisioned", the only safe default for an unprovisioned trust anchor is *blocked*. (d) A judge in the same family as the mutator (shared blind spots rubber-stamp). (e) A single judge with no independent critique pass, one judge rubber-stamps polished prose; a second-reviewer pass that can downgrade an inflated PASS is part of the producer, not optional.

**Concrete example.** A research apparatus built a syntactic commit-membrane (forced witness fields, enum'd `why_not`). On returning to substantive work the *same agent that built it* discharged its obligations with a blanket dismissal template and generic prose, the membrane forced the *shape* of a discharge but the agent self-judged its *truth*. The operator caught the gaming directly ("are you gaming again?"). The fix was Pattern 14: a separate VPS OS identity (`ztare_judge` ≠ agent `ztare` ≠ signer `ztare_verify`, key `0400`, verified unreadable by the other two), an out-of-loop judge producer that codex-runs a different-family model and signs the execution proof, and a monitor that verifies the judge-key signature, recomputes the rubric from the frozen contract, and does total proof-field comparison. Three successive cold cross-provider reviews each found a real residual hole (forgeable verdict → replayable proof → unsigned family claim); each was closed before the mechanism was trusted, and none had been visible to the author's own self-audit.

**Relationship to other patterns.** Pattern 14 is Pattern 5 (Inverted Hash for Adversarial-Resistant Equality) and Pattern 13 (Result-Bound Success Claims) escalated from *honest-harness* to *hostile-producer*: Pattern 13 makes the harness unable to *accidentally* lie; Pattern 14 makes the producer unable to *deliberately* lie even when it wrote the harness. Pattern 2 (Pre-Flight Battery) is the regression net that keeps the membrane's kill-tests green across changes.

#### Generalization (2026-05-18): exogenous-identity authority over consequential state

The judge keypair above is one instance of a more general primitive. The invariant is not "a judge signs verdicts"; it is: **every state transition the producer must not be able to self-authorize is gated by a signature from an identity outside the producer's write boundary, verified against a pinned committed anchor, fail-closed until provisioned.** The judge key gates *verdicts*. A second instance, the **operator key**, gates *consequential-state declarations the producer must never make for itself*: registering the canonical target a proof is checked against, retiring an un-closeable obligation, vouching for manifest provenance. Same primitive (a dedicated OS identity, key `0400`, unreadable by the agent and the daemon signer, generated-if-absent on the trusted host, public half pinned in a reviewed commit or the gate fail-closes), a different consequential transition. The lesson for practitioners: when you find one place the producer self-authorizes something central, look for the others, they are the same key pattern applied to a different verb, and an env flag or a proposal boolean is never a substitute for the signature.

A second technique emerged as the antidote to this pattern's characteristic failure mode (the hardening treadmill, see `epistemic_principles.md` P15). **Precommitted promotion contracts**: a change to the membrane is admitted only by a deterministic PASS / FAIL / BLOCKED contract authored *before* the change, carrying no learned or language-model judgement, and whose code additionally encodes *what the change may not claim* (debt is externalized to a separately governed item, never absorbed into a passing claim). This converts an open-ended "patch, cold-review, patch" loop into a finite auditable ladder. It is the operational form of Pattern 13's honesty escalated to the membrane's own evolution.

**The recursive lesson, and a deliberate status boundary.** This pattern's own
acceptance machinery became a test case for the pattern. A builder-written
"acceptance" kill-test for the membrane was submitted to a not-the-builder cold
pass and failed: its nominally distinct adversarial fixtures collapsed to one
rejection, its evidence had a stale-artifact false-pass, and it never exercised
the real risk: a well-formed envelope carrying a vacuous or unfaithful claim. The
finding generalizes: a builder cannot author its own acceptance gate. Valid
acceptance is authored and run by not-the-builder, in the provisioned
environment, evidenced by the daemon's own artifacts, not by a runner's prose;
"no output" is not a pass. Accordingly this catalogue entry documents the
techniques, but does **not** assert that the
[GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)
instance is validated. Its status is implemented; acceptance requires
not-the-builder construction and run in the provisioned environment. The
irreducible residual, a faithful formal target is still only as good as the human
judgment that it captures the informal problem, is `epistemic_principles.md` P16
and is not closed by any technique above.

**Origin.** [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md) commit-membrane, 2026-05-17; generalized because the failure, self-attesting producer with write access to its own verdict, is the structural core of every autonomous-agent trust problem, not specific to this apparatus. Full hardening history (the cold-review defect chain) lives in `research_areas/seams/apparatus/cage/GP-241_commit_membrane_mode_independent_forcing_seam.md`; reproducible provisioning in `deploy/FIRST_TIME_SETUP.md`.

---

### Pattern 15, Structural Contract Gating

**Problem.** LLM agents producing claims in formal-structure domains (proofs, statistical inferences, audits, refactors, compliance positions) launder by *paraphrase*: they emit a fluent narrative that elides the central structural commitments the domain's invariants require. A checklist of required fields constrains presence; the agent fills each field with content-free prose ("see methods section") and the checklist passes. The laundering is not in the field's absence but in the agent's commitment to *nothing structural* on the field.

**Pattern (three components).** (1) An **anchor**: a central structural invariant of the problem domain — algebra, degrees-of-freedom rule, conservation law, type signature, identification strategy. (2) A **contract template**: a receipt schema whose fields are derived from the anchor and use enums / whitelists (not free strings) wherever a structural position must be named. (3) A **downstream audit gate** that fires *after* the agent's primary work succeeds, refusing to ratify receipts that omit central fields or fill them with un-whitelisted free strings. The gate is pure, deterministic, refuse-to-ratify (not warn), and pre-registered (`contract_sha256`-pinned) to defeat anchor capture.

**Why it works.** Anchoring the schema in the domain's structural invariants is what distinguishes SCG from generic JSON-schema validation: a missing or malformed structural field is rejectable on a property the domain itself adjudicates, not on operator preference. Forcing every commitment through an enum or whitelist closes the "vacuous string" laundering class. The downstream-after-primary placement of the gate makes the threat model (paraphrastic laundering by an LLM after it has done plausibly-fluent work) the right one: the gate audits what was already produced.

**When to deploy.** When (a) the domain has a real structural invariant to anchor the schema in (formal proofs, statistical claims, smart contracts, type-system refactors, regulatory positions, scientific reporting standards), (b) the agent's success criterion is easy to misrepresent without committing to specific structural facts, (c) you can enumerate the central fields now (before the agent runs), and (d) the cost of writing the schema is less than the cost of catching the laundering some other way. Skip when the "invariant" is contested, aesthetic, or absent.

**Scope (what SCG does NOT do).** SCG provides *structural visibility*. It does not catch (i) content lies — declarations whose value is fabricated; (ii) process lies — claims about what the agent did that the gate cannot independently observe; (iii) anchor capture — drift in the schema itself. The dedicated doc lists the orthogonal disciplines that compose with SCG to cover these: content auditors (Lean replay in NS, sibling data check in stats), pre-registration + audit logs, content-hash-pinned schema versioning.

**Anti-pattern.** Free-string fields where structural commitment must be named. A `multiple_comparison_correction_method: "we adjusted for the family"` field passes presence but commits to no structural position. Replace with a recognised-set enum (`{none, bonferroni, holm, fdr_bh, ...}`). The single most common SCG implementation mistake.

**Concrete example #1 (NS).** [GP-219](../../research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md) / `pec_k` owner-preimage prefix gate. The RD/action-contract loop hit a cancellation-laundering attractor; the algebraic reframe forced 5-direction trace-free tensor recovery (textbook tomography, not novel); `pec_k` is the SCG contribution — a downstream audit that demands the receipt enumerate `owner_map`, `pre_payoff_timing`, `full_output_scale_owner`, `pointwise_payment`, `finite_atom_budget`, `multiplicity_bound`, `owner_preimage_prefix_inequality`. The workbench surfaced `owner_preimage_receipt_missing` instead of pages of "sheath" prose. Code at `src/ztare/gates/owner_preimage_prefix_gate.py`.

**Concrete example #2 (non-NS substrate).** Parametric hypothesis-test claim verification at `projects/structural_contract_gating_demo/`. The anchor is each test family's structural surface (degrees-of-freedom rule, normality assumption, multiple-comparison surface, effect-size requirement). Three realistic laundered claims the gate refuses: adaptive interim looks declared with `alpha "unchanged"`; within-subject pre/post design forced into independent-samples t-test; 12 pairwise contrasts uncorrected because "all primary". The same scenarios done honestly (O'Brien-Fleming alpha-spending; paired family; closed-testing-procedure justification) pass. An adversarial audit of the gate against 27 attempted laundering modes found 15 succeeded against a free-string-permitting early version of the contract; enum + whitelist closures dropped that to a smaller residual whose remaining hacks fell into the scope boundaries listed below.

#### Scope — what SCG does NOT do

SCG provides *structural visibility*. It catches **omission** (central field missing/empty), **deflection** (free-string filler in a field that demands a structural commitment), and **form violation** (value's type or shape inconsistent with the anchor — e.g. degrees of freedom that contradict the test's own rules). SCG does NOT catch three other laundering classes on its own:

- **Content lies** — declarations whose value is fabricated. The agent writes `normality_check_outcome: "p=0.81 — ok"` on data that is actually exponentially distributed; the gate sees a well-formed commitment but cannot verify the underlying data. Compose with a *content auditor* (Lean replay in NS; sibling data-receiving check in stats).
- **Process lies** — claims about the agent's process the gate cannot independently observe. The agent declares `n_interim_looks: 1` while peeking continuously; or runs 50 tests and declares each as `family_size_k: 1`. Compose with *pre-registration* (commits the agent before observing data) + *audit logs* (independent observation of the process).
- **Anchor capture** — drift in the schema itself. Compose with *content-hash-pinned schema versioning* (the NS Evaluation Harness pattern: `contract_sha256` pinned inside the contract; runner refuses on drift).

These are scope boundaries, not pattern weaknesses. Real-world deployments compose SCG with content audit, pre-registration / audit logs, and schema versioning to cover what SCG cannot cover alone.

#### Cross-industry applicability

Any industry whose claims rest on enumerable structural invariants is a candidate. Confirmed by worked example: NS PDE estimates (formal-method substrate) and parametric hypothesis-test claims (statistical substrate). Candidate domains where the anchor is identifiable:

- **Formal-method proofs.** Anchor: proof-system deduction rules + domain structural facts. (Worked.)
- **Statistical inference.** Anchor: test family's degrees-of-freedom rules, assumption sets, multiple-comparison surface. (Worked.)
- **Smart-contract audit.** Anchor: Solidity-specific invariants (conservation of value, reentrancy guards, monotonicity of state machines).
- **Tax / regulatory compliance.** Anchor: jurisdictional structural rules (basis propagation, character-of-income preservation, treaty interaction).
- **Type-system-checked refactors.** Anchor: source language's type/effect/ownership rules.
- **Causal inference claims.** Anchor: identification strategies (RCT, IV, RDD, DiD, DAG do-calculus).
- **Scientific peer-review augmentation.** Anchor: reporting-standard structural fields (CONSORT, STROBE, ARRIVE, PRISMA, SPIRIT).
- **Supply-chain provenance.** Anchor: identity/value conservation through transformations.
- **Pharma post-market surveillance.** Anchor: FDA/EMA pharmacovigilance rules (causality assessment, dechallenge/rechallenge, signal detection).
- **Aerospace / safety-critical certification.** Anchor: DO-178C / ISO 26262 structural objectives.
- **Quant trading model validation.** Anchor: backtest structural rules (OOS partition, look-ahead avoidance, transaction-cost modeling, regime-stratified evaluation).
- **AI-assisted code review at scale.** Anchor: language type system + design-pattern invariants.

Transfer cost across industries is dominated by *anchor work* — enumerating the central structural fields for the substrate. Once that enumeration exists, the contract template and audit gate are mechanical to write. Pharma, aerospace, and securities domains already have most of the anchor work done by their regulators; the SCG move is to express that anchor as code an agent must satisfy.

Domains where SCG has *no* clean anchor and should not be attempted: creative writing, brand voice review, qualitative interview analysis, open-ended ideation. The pattern needs a structural invariant to grip; soft / aesthetic criteria are out of scope.

#### Honest limitations

- **Two-substrate evidence** (NS + hypothesis tests). Suggestive, not conclusive. Pattern transfer beyond domains with sharp structural anchors is unconfirmed.
- **Implementation craft is central.** A poorly-written contract (free strings instead of enums; missing conditional rules; vague field names) gives the pattern's name without its substance. Adversarial testing of the gate against the laundering modes you actually care about is mandatory before production deployment.
- **Scope is structural, not content or process** (see above). Treat SCG as one of three or four composing layers, not as the whole defence.
- **Anchor maintenance is operator work.** When the domain's structural surface evolves, the contract has to be re-versioned and re-pinned. Without maintenance, the pattern silently misses laundering on the new surface.

**Origin.** First observed in ZTARE's NS millennium hunt (`pec_l`/`pec_k`, [GP-219](../../research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md), 2026-05); the replication on hypothesis-test claim verification (`projects/structural_contract_gating_demo/`) substantiates substrate transfer.

---

### Pattern 16, Reasoning Contract Compiler

**Problem.** LLM agents can name the right reasoning move while failing to
perform the action that move implies. A label such as "boundary pattern" or
"router branch" often changes the explanation more than the behavior. The
reverse failure is also dangerous: a plausible but wrong contract can steer an
agent into the wrong action more strongly than no contract at all.

**Pattern.** Compile each selected reasoning move into a small action contract.
The contract carries:

1. source facts the route is allowed to use;
2. the residual or evidence carrier that selects this route;
3. the nearest confuser route and the source fact that rejects it;
4. an action program with current index, required next action, and stop rule;
5. a deterministic gate for required fields, program order, stop condition, and
   source-contract alignment;
6. a later outcome trace so the route can be evaluated after use.

Keep rich audit fields for analysis, but expose compact execution fields to the
agent at runtime. The agent executes the contract; the system validates the
contract.

**Why it works.** The useful unit is the edge from source evidence to required
action. A vocabulary item is too thin, and free-form program generation is too
unconstrained. A typed action contract forces the system to state what source
fact selected the route, what neighbor was rejected, what must happen next, and
what condition stops the loop.

**When to deploy.** Use whenever an LLM-mediated pipeline routes from diagnosis
to follow-up action: research-direction selection, incident response,
code-review repair loops, compliance triage, support escalation, or any workflow
where "which action next?" matters more than "which label describes this?"

**Anti-pattern.** Treating a menu or catalogue entry as if naming it performs
the operation. Another common mistake is letting the model synthesize the whole
action program freely. Free-form synthesis should be treated as a candidate
generator; deterministic lowering and source-cue checks decide whether it can
run.

**Concrete example.** ZTARE's H31-H55 research-agent tests found that label-only
orchestration could name plausible residual classes while repeating
prerequisites, swapping terminal actions, or obeying wrong compact contracts.
The corrected pipeline records `accepted_residual_class`,
`source_cue_check_status`, `action_program`, `current_action_index`,
`required_next_action`, `program_counter_rule`, and nearest-confuser evidence,
then validates with `src/ztare/research_director/orchestration_contract_gate.py`.
Boundary-card and PDE work-unit gates showed the same shape: validate the typed
work unit or repair trace, not prose that says the work happened.

**Workbench-routing instance.** The autoresearch boundary uses the same pattern
at a smaller scale. `OP-AWR-01` asks whether a Research Director task has the
four prerequisites for in-loop autoresearch, then lowers the answer into a
route JSON plus `domain=agentic_workbench` action-impact row. The useful object
is not the label "agent" or "API"; it is the typed route receipt:
bounded-claim/evaluator/rubric/artifact bits, selected action, rejected path,
worker metadata, route JSON ref, and action-impact ref.

**Drift validator.** Periodically replay recent decisions through the contract
gate and measure field coverage, wrong-contract rejection, required-next-action
accuracy, and later outcome deltas. A high route-label accuracy with low
action-program accuracy is a regression.

**Evidence boundary.** The current evidence supports this as an engineering
discipline for safer agent handoffs and downstream field recovery. It does not
yet prove live productivity uplift across arbitrary production workflows.

---

### Pattern 17, Shadow-First Controller Promotion

**Problem.** A new agent controller can look strong in synthetic tests and still
be unsafe to enforce. Production traces may lack the fields needed to know
whether the controller would have helped, harmed, or merely duplicated the
current process. Enforcing before that evidence exists turns a research
hypothesis into a control-plane change.

**Pattern.** Run new controllers in shadow mode before they can block or steer
production. For each candidate decision, record:

1. pre-action state: timestamp, source facts, candidate action, and controller
   contract before the existing process acts;
2. shadow recommendation: route, required next action, rejected confuser, and
   deterministic gate result;
3. actual path: what the live process did without the new controller;
4. outcome fields: later result, repair count, cost, delay, regret signal, or
   explicit "not yet observable";
5. promotion decision: whether the shadow controller would have changed the
   action, whether the invariant held, and whether the change would have
   improved the outcome.

Only promote from shadow to enforcement after enough rows contain both
pre-action recommendations and later outcomes. A row that only records a
post-hoc explanation is not a shadow-controller row.

**Why it works.** It separates two claims agents often merge: "the controller can
produce a plausible recommendation" and "the recommendation improves decisions
when used before action." Shadow logging forces the second claim to wait for
causal evidence without blocking current operations.

**When to deploy.** Use before enforcing a new router, triage policy,
auto-repair loop, budget allocator, reviewer assignment policy, or any
agent-selected next-action controller whose mistakes create cost.

**Anti-pattern.** Post-hoc controller ceremony: after an action is already
complete, the system logs what it would have recommended and treats that as
validation. A second failure is promoting on field completeness alone.
Completeness only says the data can support evaluation; it is not evidence of
benefit.

**Concrete example.** ZTARE's orchestration-menu work added
`src/ztare/research_director/orchestration_shadow_log.py` after the corrected
compiler succeeded on synthetic and replay packets. A production-trace readiness
audit found `0/131` official transitions had enough pre-action and outcome
fields for a fair controller test. The correct action was instrumentation, not
enforcement.

**Promotion gate.** Before enforcement, require a predeclared minimum number of
complete shadow rows with pre-action contract, live action, later outcome,
invariant verdict, and delta analysis. Report both changed-action rows and
no-change rows; otherwise the controller can appear harmless simply because it
never would have changed anything.

### Pattern 18, Typed Obstruction Basin

**Problem.** Substrates whose main work is exhausting wrong routes (open mathematics, hard combinatorial proofs, intractable PDE estimates, cryptanalysis search) accumulate *failure knowledge* faster than *success knowledge*. The standard archive for failure is a free-prose research log: "we tried strategy X, it didn't work because of obstruction Y." Future agents reading that prose rediscover the same obstruction under new vocabulary, file a renamed proposal, and waste the budget the prose was supposed to save. The problem is not that the failure was unrecorded; it is that the recording form is not structurally queryable. An agent asking *"has this route been killed?"* against free prose silently returns no-match on a synonymic alias of a route that was killed last week.

**Pattern (three components).** (1) A **typed obstruction source**: failure-state (obstructions, residuals, killed routes, declared-impossible classes) encoded as formally-typed structures in the same substrate the work is happening in — Lean structures for proof substrates, JSON-Schema-pinned receipts for empirical substrates, parameterised SMT lemmas for verification substrates. Each typed obstruction commits to *named* fields (`obstruction_class`, `route_invariant_terminus`, `axiom_blocked`, `falsifying_witness`, `lift_failure_reason`) rather than prose. (2) A **derived basin graph**: a `@graph` JSON-LD (or equivalent) computed from the typed source — nodes are obstructions, edges are entailment/aliasing/composition relations between them. The graph is regenerated mechanically from source on each refresh; it is not authored by hand. (3) A **pre-attack consumption protocol**: agents (and operators) consult the basin *before* proposing a new route, querying *"has this obstruction class already been killed, possibly under a different name?"* via graph traversal, not lexical search.

**Why it works.** Failure knowledge in hard-frontier work is what carries the budget: there are usually many more dead routes than live ones at any moment, and the cost of rediscovering a dead route is full re-attack budget. Encoding the failure in the same formal language the success would use closes the dominant laundering vector ("we'll just rename the thing we tried"). The basin graph compresses the obstruction landscape into a queryable shape that survives operator turnover, agent rotation, and substrate vocabulary drift. The serialized "atlas" form of the basin (RAG corpus, embeddings, dashboard) is a *downstream* artifact for sharing — the basin graph itself is the primary consumable.

**When to deploy.** When (a) the substrate's main work is exhausting wrong routes, not enumerating right ones — open math frontiers (Navier-Stokes, Riemann, Carleson premise selection), cryptanalysis, smart-contract vulnerability mining, intractable optimisation; (b) failure-state has a formal-language expression in the same substrate as success would; (c) the cost of route-rediscovery dominates the cost of typing the obstruction; (d) agent rotation is high enough that knowledge has to survive in artifact, not in operator memory. Skip when closures are frequent and obstructions are rare (the basin is sparse and the success-archive dominates) or when failure cannot be cleanly typed (creative domains, qualitative analysis).

**Anti-pattern.** A free-prose research log titled "Things we tried that didn't work." The next agent reads the prose, mentally translates the failure into different vocabulary, files a renamed proposal, and the apparatus pays the same attack budget twice. Variant: a single-vocabulary failure list whose terms drift over time without a basin to anchor the renames against — observed in this apparatus's own NS work where the "perennial strict-margin atom" was rediscovered ≥6× under different names (opaque-subcrit → strict-margin → super-TypeI → Birkhoff → CF) before the basin anchor was built.

**Concrete example.** ZTARE's NS Track B work. **486 NS-prefixed `.lean` files** at `ztare_proofs/ZtareProofs/ns_*.lean` encode obstructions, residuals, charging adapters, kinematic dichotomies, and route-invariant terminuses as typed Lean structures. The basin graph at `projects/ns_millennium_hunt/workspace/queries/ns_trackb_constraint_basin_graph.json` (8846 nodes derived from 2999 decl scans across 444 files; JSON-LD with `@context` vocab) is computed mechanically from those structures. Per `AGENTS.md` §0a2 / §2j, every NS pre-tick *must* consult the basin via `AMNESIA_BASIN_ENTRYPOINT.md` and the basin graph before proposing a new attack; the consumer is `src/ztare/surfacing/pre_tick_obligation_compiler.py`. Outcome example: F-NS-TICK604 (2026-05-16) Lean-verified `uniformCKNBound ⟹ cascade-uniform H ∧ cascade-uniform H FALSE on flat Kolmogorov cascade ⟹ ¬ uniformCKNBound`, closing the porosity route's hypothesis negatively; the basin gained that as a node with explicit `route_invariant_terminus` typing, so future "porosity-variant" proposals dead-end against it immediately. The atlas serialization (`projects/ns_millennium_hunt/public/ns_atlas_rag_corpus.json`, `ns_atlas_embeddings.json`, `phase5bq_spectral_n_certificate_atlas.*`) is the consumable/shareable form of the basin for downstream/external readers and aspirational RAG retrieval; the *operational* consumption is the basin graph itself via the pre-tick compiler.

**Composes with.** Pattern 15 (Structural Contract Gating) supplies the *typing* of each obstruction; the `scientific_amnesia_precheck` primitive in `org/patterns/` supplies the *consumption discipline*; the catch ledger supplies *durability* across operator turnover; Pattern 10 (Cross-Reference Knowledge Graph) is the analog for *code* artifacts (this pattern is the analog for *domain-knowledge* artifacts). Each piece is documented separately because each composes with substrates that do not need all four.

**Scope — what the obstruction basin does NOT do.** It catches *route-rediscovery* failures (proposing a dead route under a renamed vocabulary). It does NOT catch: (i) genuinely novel routes that the existing basin has no node for — the basin can only return no-match; (ii) typed obstructions whose typing is itself wrong — a misclassified obstruction in the basin can mislead future agents (compose with the same content-auditor discipline as Pattern 15); (iii) live-tactical failures that occur mid-attack — the basin is consulted pre-attack, not mid-attack (compose with the catch ledger for in-flight failure recording); (iv) substrate-internal obstructions that don't transfer cross-substrate — a Navier-Stokes basin does not help a Riemann attack unless the obstruction class generalises.

**Honest limitations.** The pattern's value is proportional to (a) the typeability of failure-state in the substrate and (b) the rate at which routes get rediscovered. In substrates where (a) is hard (creative domains, qualitative interview analysis) or (b) is low (substrates where each agent attacks a wholly novel route), the basin is empty or rarely consulted and the typing cost is wasted. In substrates where (a) is easy and (b) is high — open math frontiers especially — the basin is the central artifact and the success archive is secondary.

**Origin.** NS Track B work, April–May 2026, after the "perennial strict-margin atom" was rediscovered ≥6× under different vocabulary. The structural anchor (`AMNESIA_BASIN_ENTRYPOINT.md`) became mandatory pre-tick reading; the basin graph was added when the lexical precheck proved unreliable under vocabulary drift; the atlas serialization was added when external/downstream consumers needed a non-Lean-readable form. The current 486-file Lean substrate is the largest deployment.

---

## Lineage and prior art (added 2026-05-05)

The patterns above were discovered the way the introduction describes: bug shipped, root-cause identified, reusable technique emerged. This section adds prior art for the patterns that have substantial published lineage. Components are not novel; combination + LLM-consumption optimization + paired drift validators may be modestly novel as a coherent practice.

### Pattern 9 (Token-Optimized Self-Modeling), prior art

- **Joern / Code Property Graph (CPG)** (since 2013): language-agnostic graph representation of code. The current Pattern 9 implementation (markdown arch maps + regex-extracted structured claims) is a lightweight equivalent at small scale.
- **CodexGraph** (NAACL 2025): full symbol + relation graph of codebase via property-graph queries; LLM agents traverse, retrieve, and synthesize.
- **Codebase-Memory** (2026): Tree-Sitter + SQLite + 14 MCP tools for LLM-agent code exploration.
- **Lipson et al.** (self-modeling robots): the original "agent builds an internal model of its own body" precedent. The reflexive engineering doc cites this.

**When to graduate from Pattern 9 (markdown maps) to CPG-style adoption:** when arch-map count crosses ~10 modules OR module size crosses ~10K LOC, the maintenance cost of regex-based validation exceeds the cost of adopting Joern + MCP tooling. ZTARE is currently at 13 maps + ~7K LOC for autoresearch_loop, Pattern 9 is appropriate.

### Pattern 10 (Cross-Reference Knowledge Graph), prior art

- **GraphRAG** (Microsoft, July 2024): graph-based RAG for narrative private data. 29.8K GitHub stars. Closest published parallel.
- **A-MEM** (Xu et al., 2025): atomic notes + dynamic links + sleep consolidation; explicit Zettelkasten-LLM integration.
- **SSGM Framework** (Stability- and Safety-Governed Memory): drift detection in evolving knowledge memory; the validator pattern in different terminology.
- **Niklas Luhmann's Zettelkasten** (1962-1996): original index-based artifact network; Pattern 10 is the LLM-consumption-optimized version of the same primitive.

**When to graduate from Pattern 10 (regex extraction + JSON-LD) to GraphRAG-style adoption:** when artifact corpus crosses ~1000 nodes OR when synthesis queries require multi-hop traversal beyond simple `depends_on` resolution. ZTARE is currently at 137 nodes (seams) + 459 edges, Pattern 10 is appropriate; GraphRAG would be over-engineering.

### Pattern 14 (Adversary-Authored Apparatus / Forced Out-of-Loop Judge), prior art

The *components* are classical computer security; the *novel combination* is applying them to the case where the adversary is the LLM agent that produced the work **and authored the containment**, with a cross-provider-family judge whose verdict the producer is cryptographically unable to forge.

- **Anderson, *Reference Monitor* (1972)** and the **Orange Book / TCSEC** lineage: complete mediation, tamperproof, minimal verifiable TCB. Pattern 14's verificator daemon is a reference monitor for "official research state."
- **Clark-Wilson (1987) / separation of duties**: the entity that performs a transaction must not be the entity that certifies it. Pattern 14 is separation of duties enforced cryptographically across *OS identities* and *model families* rather than human roles.
- **Saltzer & Schroeder (1975)** fail-safe defaults + least privilege: the "blocked until every anchor provisioned" posture and the agent-unreadable key store.
- **Proof-Carrying Code (Necula 1997)** and **Proof-Carrying Authorization (Appel & Felten 1999)**: the actor ships a checkable proof that the policy was satisfied; the verifier trusts the proof, not the actor. Pattern 14's signed execution proof is PCA specialized to "an LLM judge of a different family actually ran this rubric."
- **TPM / remote attestation (TCG)** and **Trust-but-Verify / BFT**: a measurement signed by a key the measured party cannot extract, verified against a pinned anchor. Pattern 14's judge key + committed pubkey anchor is the same structure at application layer.
- **LLM-as-a-judge literature (Zheng et al., 2023+)** establishes model-graded evaluation but assumes a *cooperative* harness; it does not address a producer that can fabricate, replay, or weaken its own judge call. The adversarial-producer threat model and the cryptographic forcing are the modestly novel contribution here.

#### Concurrent independent reinvention (2026 arXiv survey)

Between December 2025 and April 2026 the
verifiable-agent-execution literature converged, independently, on the
same skeleton as Pattern 14: a sole-writer verifier that an agent
cannot impersonate, an append-only tamper-evident ledger, signed
receipts that bind work to state, and a human approval point that no
amount of model capability dissolves.

*"Right to History: A Sovereignty Kernel for Verifiable AI Agent
Execution"* (arXiv 2602.20214) is the closest parallel: an RFC-6962
Merkle audit log, capability-based isolation, energy-budget governance
and a human-approval mechanism, formalised as five system invariants
with proof sketches. Its shape is [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)'s shape. The instructive
divergence is structural, it uses a Merkle tree where this repo uses
a linear hash chain. The chain is correctness-equivalent but a Merkle
log additionally yields succinct third-party inclusion proofs, which
matters precisely when the trust root is *operator inspection*: an
operator should be able to verify one tick without replaying the whole
ledger. The **IETF `draft-sharif-agent-audit-trail`** points the same
way, SHA-256 hash-chained records with optional ECDSA signatures and
explicit trust-level fields are becoming the standard envelope [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)
should converge toward rather than maintain in a private dialect.

Two papers sharpen the *monitoring* side. *"Verifiability-First
Agents"* (arXiv 2512.17259) pairs run-time attestation with a
lightweight intent-versus-behaviour audit agent and a
challenge-response protocol for high-risk operations; the
out-of-loop `judge:auto` here is the audit-agent leg, but the
challenge-response form, where the verifier issues a fresh nonce the
producer must route through substantive task execution, is absent and is the natural
hardening for closure claims. *"TraceGuard"* (arXiv 2604.03968) is the
direct remedy for this apparatus's recurring monoculture failure: it
replaces a single holistic monitor verdict with structured,
multi-dimensional scoring split across trust levels so that no single
model sees the whole picture, which makes collusion and rubber-stamping
structurally harder. Every cold review in this project's history was a
single holistic pass; TraceGuard is the principled upgrade.

The most operationally important find is *"Detecting Proxy Gaming via
Evaluator Stress Tests"* (arXiv 2507.05619). It detects a *gameable
gate* by perturbing the evaluator with semantically-invariant changes
and checking that the score is invariant, a test this apparatus has
never run on its own gates, despite the gate-gets-Goodharted failure
recurring through five review cycles. It is the missing self-audit
primitive, and it attacks the treadmill at its root rather than
patching the latest symptom. The empirical backdrop is supportive:
*"Reward Hacking Benchmark"* (arXiv 2605.02964) measures environmental
hardening / deterministic refusals cutting reward hacking by ~88%
relative, which matches this project's experience: only refusals the
producer cannot author have held.

Finally, the literature independently confirms the *limit*. *"Do LLMs
Game Formalization?"* (arXiv 2604.19459) finds that an LLM judge
catches obvious fabrication but misses subtle manipulation, and that
scalable faithfulness metrics for unconstrained formalization remain
an open research problem. That is Pattern 14's honest residual stated
from the outside: the gap between a formal target and the informal
intent it is meant to capture is not an engineering shortfall to be
closed by one more gate. *"ProofFlow"* (arXiv 2510.15981, dependency-
graph faithfulness + ProofScore) and *"Aristotle"* (arXiv 2510.01346,
a Lean-REPL-signal faithfulness judge) are strong external
*partial* mitigations, and they prescribe exactly the cheap syntactic
half this repo still owes: bind the proof's canonical statement /
dependency graph to the registered target. Semantic equivalence of
that registered target to the informal Clay problem stays human
mathematical review, by construction.

| Convergent work | What it validates | What this repo should adopt |
|---|---|---|
| Right to History (2602.20214) | sole-writer kernel + tamper-evident log + human approval | RFC-6962 Merkle log for succinct inclusion proofs |
| IETF AAT draft | hash-chain + signature envelope | converge to the standard record schema |
| Verifiability-First (2512.17259) | run-time attestation + audit agent | challenge-response attestation for closure claims |
| TraceGuard (2604.03968) | structured collusion-resistant monitoring | decompose the cold review into trust-split dimensions |
| Evaluator Stress Test (2507.05619) | gameable-gate detection | stress-test every new HARD gate for score-invariance |
| ProofFlow / Aristotle | faithfulness is partially mechanisable | bind proof statement-hash / dep-graph to the registered target |
| Do LLMs Game Formalization? (2604.19459) | the formal↔informal gap is an open problem | keep the residual human; do not over-claim a gate closes it |

**Honest status of this repo's instance (2026-05-18).** The *pattern*
is frontier-convergent. The *implementation* is prototype-grade: five
independent cross-provider cold passes each returned artifact-NO-GO
with idea GO-WITH-CHANGES, around a stable, converging core, 
remote-manifest transport, start-tick forcing, proof-statement↔target
binding (the ProofFlow/Aristotle move), POST-MECE exhaustiveness, and
registry provenance. The full defect chain and the forward spec live
in `research_areas/seams/apparatus/cage/GP-241_commit_membrane_mode_independent_forcing_seam.md`;
the irreducible residual is treated in `epistemic_principles.md`.

**When this is over-engineering.** If the producing agent has no write/propose access to the record of whether the bar was met, or the quality bar is cheap to verify deterministically, Pattern 14 is unnecessary, a deterministic check (Pattern 5/13) suffices. Reach for Pattern 14 only when the bar is LLM-judged *and* the producer can influence the verdict *and* the cost of a laundered pass is high (research integrity, autonomous spend, irreversible official state).

#### The producer feedback channel

Separation of duties plus cryptographic forcing is only half of Pattern 14. It stops the producer from *gaming* the judge; on its own it also stops the producer from *learning* from the judge. A correctly-built Pattern 14 instance therefore has two channels, not one:

- a **trust binding** channel — the signed proof (verdict + raw-output hash + judge key, bound to the frozen request) — which the producer must not be able to forge, replay, or weaken; and
- a **feedback** channel — the judge's reason/critique — which must reach the producer *in-band*, the way a compiler returns its error to the code author.

Conflating the two is the characteristic Pattern-14 defect: when the judge's reasoning is treated as part of the trust surface it gets discarded or hidden ("the producer must not influence the judge, so the producer must not see the judge"), leaving the producer with a bare PASS/FAIL. A producer that knows only FAIL, not why, degrades to spelunking the verifier internals, mis-discharging (e.g. offering a successful-construction witness for an honest negative result), or wrongly escalating to retire/abort — each of which looks locally reasonable without the reason. Three rules make the pattern complete:

1. **Trust binding ≠ feedback channel.** Only the signed proof is cryptographically bound and tamper-evident. The judge's reason is *advisory*: surfacing it cannot weaken the forcing and withholding it cannot strengthen it — it only blinds the producer. Emit a bounded `judge_reason` beside the verdict, relay it into the producer-readable record, and print it at the exact point the producer is blocked. The producer reads the judge like a compiler error, never via out-of-band inspection.
2. **A FAIL means the discharge *type* is wrong, not that the bar is unmeetable.** With the reason in-band the correct response to FAIL is to correct the discharge truthfully (e.g. discharge a negative-result obligation via its sanctioned `why_not` value, not a fabricated success), never to engineer a PASS (gaming) nor to abandon a complete unit of work (false retire).
3. **The authority, not the producer, owns producing the record.** The component that stamps the close also exports the authoritative snapshot at close; the producer is never relied on to remember to persist state it has an information-asymmetric, forgetful relationship to — the same principle as rule 1 applied to the record rather than the verdict.

General statement: **whenever you split duties for trust you must re-connect a feedback channel for learning. The split that prevents gaming also prevents iteration unless the verifier's reasoning — distinct from its trust binding — flows back to the actor in-band.** This is the governance form of the autoresearch loop's verifier-feedback principle, and it is intrinsic to Pattern 14, not optional hardening.

### Pattern 15 (Structural Contract Gating), prior art

The pattern is a composition of components that individually have substantial published lineage; the contribution, if any, is in the combination and the LLM-agent threat model. Honest lineage:

- **JSONSchema** (Galiegue et al., 2009–), **OpenAPI**, **gRPC/protobuf**, **GraphQL** schemas. Standard practice for typed-contract validation; SCG's structural-anchor framing distinguishes it from generic schemas (the fields are derived from a domain invariant, not from API designer preference).
- **Refinement types and proof-carrying code.** Liquid Haskell (Vazou et al., 2014), F* (Swamy et al., 2016), Coq tactics, Idris, proof-carrying code (Necula, 1997). Receipt-carrying claims — the agent commits to a structural argument the verifier mechanically checks — is the closest formal cousin.
- **Pre-registration of statistical analyses.** ICMJE 2005, ClinicalTrials.gov, AsPredicted (Nosek et al., 2012–), OSF Preregistration, AEA RCT Registry. The exact structural analog of SCG for statistical claims: commit to the structural surface of the analysis before observing the data. The hypothesis-test replication is pre-registration as code.
- **Standardised reporting (CONSORT, STROBE, ARRIVE, PRISMA, SPIRIT).** Enumerate the structural fields a paper-class must carry; reviewer + editor are the audit gate. SCG generalises this from human review to programmatic refusal.
- **LLM constrained generation.** Outlines (Willard & Louf, 2023), Guidance (Lundberg et al., 2023), OpenAI structured outputs, instructor/pydantic schemas. These constrain at generation time; SCG operates after, refusing schema-valid outputs that lack structural commitments the anchor demands.
- **Formal-verification audit gates.** TLA+ (Lamport, 1999), Certora's Prover, Mythril, Slither, K-framework. Verifier-after-primary-computation is the same shape; SCG generalises from formal verification to LLM-agent settings where the candidate is a claim receipt, not a proof.
- **Adversarial AI / red teaming.** Anthropic Constitutional AI (Bai et al., 2022), Guardrails AI, NVIDIA NeMo Guardrails, Lakera. Input/output filters operate orthogonally; SCG is claim-level refusal, not an input filter.

The narrower novel claim is the *composition*: structural-invariant-anchored schema + downstream refusal-to-ratify gate + content-hash-pinned schema (against anchor capture) + LLM-agent-laundering threat model. Each component is prior art; the combination as a coherent practice with two-substrate evidence (NS PDE + hypothesis-test verification at `projects/structural_contract_gating_demo/`) is the narrow contribution. Components are not novel; combination + the agent-laundering threat model may be modestly novel as a named pattern.

### Reflexive engineering connection

Both Pattern 9 and Pattern 10 are instances of `docs/concepts/reflexive_engineering.md`'s primitive #1 (Token-Optimized Self-Modeling), the apparatus applies its own Compress leg to its own infrastructure. The patterns and the reflexive primitives are the same move at different abstraction layers (engineering practice vs. philosophical primitive).

Connection to [GP-216](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md) universal vocabulary v5: each reflexive primitive maps cleanly onto a GP-216 universal op (Token-Optimized Self-Modeling = core_07 Generalization; Inception Pattern = core_05 Extremal; Reflexive Orchestration = core_02 Iterative Refinement; etc.). The reflexive primitives and the v5 ops are the same phenomenon at different levels of abstraction: **formalizing tacit cognitive moves into typed apparatus**.
