---
description: "Engineering patterns for LLM pipelines: replay, contracts, provenance, gates, and failure ledgers."
---
# Agentic Engineering Patterns

> Up: [Documentation map](../README.md)

*Status:* public. No ZTARE setup required.

*Audience:* builders of LLM-mediated pipelines: research agents, RAG
systems, code agents, multi-stage evaluators, and agent frameworks.

*Sister docs:* [reflexive_engineering.md](reflexive_engineering.md) covers
ZTARE improving its own loop; [reflexive_audit_workflow.md](../guides/reflexive_audit_workflow.md)
covers the discovery workflow.

---

## Start here

This is a field guide for the software around an LLM call. It covers routing,
parsing, candidate selection, provenance, replay tests, confidence records, and
claim checks. It does not tell you how to prompt a model better.

Use it when a pipeline produced an output that looked plausible, but the wrapper
let something unsafe through: a parser accepted the wrong shape, a selector
favored the first candidate, a fallback hid which stage produced the result, or
a controller claimed success without an artifact.

The repair rule is small:

1. Name the failure class.
2. Add the cheapest replay, check, receipt, or fail-closed route that would have
   caught it.
3. Add a regression around that check.
4. Promote the wider pattern only if the failure recurs or affects more than
   one call site.

Use [reflexive_engineering.md](reflexive_engineering.md) when the same repair is
applied inward to ZTARE's own loop, routing, memory, or allocation policy.

## The reader decision

Use this page to answer one question:

> What small artifact would have caught this LLM pipeline failure before it
> reached the user?

The answer should be a concrete thing you can inspect: a replay fixture, a
preflight check, a provenance field, a typed receipt, a shadow row, or a gate.
If the answer is only "use a better prompt" or "ask a stronger model," this
page has not helped yet.

## Small case

A model writes a plausible report, but the source index is stale. The bad fix is
to add a reminder to "check sources carefully." The pattern fix is smaller and
more durable:

1. The source-readiness preflight fails before the model run.
2. The failure names the stale file and the command that refreshes it.
3. The report path refuses a success claim until the refreshed source index is
   present.
4. A regression proves the stale-source case still blocks.

That is the standard for the rest of the catalog: name the failure, add the
smallest inspectable artifact that catches it, and test the artifact itself.

## How to read this doc

Read the catalog in this order:

1. Use [Choose a pattern](#choose-a-pattern) to match the failure in front of
   you.
2. Check [Status and owners](#status-and-owners) before you claim a pattern is
   implemented.
3. Check [Pattern audit matrix](#pattern-audit-matrix) for the selector,
   artifact, decisive check, and known confuser.
4. Jump to the pattern section only after you know the failure class.
5. Add or inspect the executable artifact: replay fixture, preflight check,
   provenance field, structural receipt, shadow row, or gate.

If you are writing user-facing docs, do not lead with the pattern name. Lead
with the failure it prevents and the command or file that proves it is wired.

## Choose a pattern

Start from the failure. The pattern name comes second.

| When you see this | Start with | Add this first |
|---|---|---|
| Real model outputs break a parser, router, or downstream contract | [Pattern 1](#pattern-1-stub-replay-integration-testing) and [Pattern 2](#pattern-2-pre-flight-assertion-battery) | Archived-output replay plus pre-flight assertions |
| Candidate selection is biased by order, fallback, or hidden stage changes | [Pattern 3](#pattern-3-eligibility-pre-filter-for-position-biased-selection) and [Pattern 4](#pattern-4-fallback-chain-with-provenance-telemetry) | Eligibility filter, dropped-candidate log, `stage_origin` field |
| Novelty, equality, or size limits can be gamed cosmetically | [Pattern 5](#pattern-5-inverted-hash-for-adversarial-resistant-equality), [Pattern 7](#pattern-7-canonical-hash--operation-multiset-3-axis-novelty), [Pattern 8](#pattern-8-bloat-cap-calibration-via-real-telemetry) | Canonical hash, operation-multiset distance, behavior fingerprint, cap histogram |
| Agents edit large systems from partial context | [Pattern 9](#pattern-9-token-optimized-self-modeling) and [Pattern 10](#pattern-10-cross-reference-knowledge-graph) | Validated architecture map or cross-reference graph |
| Vocabulary exists at several scales and drifts across them | [Pattern 11](#pattern-11-cross-scale-alias-map) | Alias table plus drift linter |
| Forecasts or confidence claims influence execution | [Pattern 12](#pattern-12-sealed-forecast-pool-for-execution-control) | Sealed forecast contract, independent forecasts, resolver, score closure |
| The harness can claim success before holding the result | [Pattern 13](#pattern-13-result-bound-success-claims-harness-honesty) | Success text bound to verified output or explicit no-answer |
| A producer can self-attest consequential state | [Pattern 14](#pattern-14-out-of-loop-judge-for-self-attesting-producers) | Separate authority, signed verdict/proof, frozen rubric, fail-closed checks |
| A fluent claim hides missing structural commitments | [Pattern 15](#pattern-15-structural-contract-gating) | Domain receipt schema plus downstream audit gate |
| A model names a reasoning move but does not execute it | [Pattern 16](#pattern-16-reasoning-contract-compiler) | Source-bound action contract with nearest-confuser rejection |
| A new controller might harm production if enforced too early | [Pattern 17](#pattern-17-shadow-first-controller-promotion) | Shadow row with recommendation, actual path, and outcome |
| Failure knowledge is repeatedly rediscovered under new names | [Pattern 18](#pattern-18-typed-obstruction-basin) | Typed obstruction record plus derived basin graph |

The minimum useful version of any row is:

1. Name the failure class.
2. Name the input signal that selects the pattern.
3. Add a deterministic check, receipt, or replay.
4. Add a regression that fails if that check disappears.

## What counts as wired

A pattern is "wired" only when a maintainer can point to one of these artifacts.

| Artifact | Use it for | Good evidence | Weak evidence |
|---|---|---|---|
| Replay fixture | Parser/router defects caused by real model output | Archived output plus expected accepted/rejected rows | Synthetic happy-path JSON |
| Preflight check | Missing source, stale artifact, malformed rubric, bad intake | Command fails before model spend | A checklist in prose |
| Provenance field | Hidden fallback or stage drift | `stage_origin`, provider, route, or worker family survives into telemetry | A log line with no downstream field |
| Structural receipt | Pattern/action or domain contract | Required typed fields with nearest-confuser rejection | A named pattern with no receipt slot |
| Shadow row | New controller or allocator | Pre-action recommendation, actual action, later outcome | Post-hoc explanation after the action |
| Gate | Repeatable anti-gaming rule | Deterministic reject/pass fixture | A judge prompt that usually notices |

This table is intentionally mechanical. A pattern that cannot name its artifact
is still a design idea.

## Pattern entry contract

Each catalogue entry should carry the same six facts. This keeps the page from
turning into a list of attractive names.

| Field | What it must answer |
|---|---|
| Failure | What went wrong in a real or plausible agentic pipeline? |
| Selector | What input signal tells the system this pattern applies? |
| Artifact | Which replay, receipt, row, graph, gate, or command proves the pattern is wired? |
| Runtime effect | What changes in the next run because the artifact exists? |
| Regression | Which test or audit fails if the pattern disappears? |
| Boundary | What claim remains outside the pattern? |

When adding or editing a pattern, prefer a short data-flow paragraph over a
new metaphor. A strong entry names the producer, the consumer, and the field
that crosses the boundary.

## Status and owners

The patterns below are not all at the same maturity. Treat the status as part
of the pattern.

| Pattern | Current ZTARE status | Main owner / check | Current gap |
|---|---|---|---|
| [1. Stub-Replay Integration Testing](#pattern-1-stub-replay-integration-testing) | partial | replay-style fixtures in dispatch and orchestrator tests | no single public replay command owns the whole pattern |
| [2. Pre-Flight Assertion Battery](#pattern-2-pre-flight-assertion-battery) | live | [`make public-adversarial-smoke`](../../scripts/public/control/public_adversarial_smoke.py), [public on-ramp tests](../../tests/scripts/test_public_onramp_checks.py), project-intake preflights | keep examples tied to commands that actually run |
| [3. Eligibility Pre-Filter](#pattern-3-eligibility-pre-filter-for-position-biased-selection) | doctrine | historical candidate-selection lesson | name a live selector before presenting as implemented |
| [4. Fallback Chain With Provenance](#pattern-4-fallback-chain-with-provenance-telemetry) | partial | dispatch/provider telemetry and autoresearch trace fallback rows | make required provenance fields explicit at each boundary |
| [5. Inverted Hash](#pattern-5-inverted-hash-for-adversarial-resistant-equality) | doctrine | canonicalization discipline in anti-gaming checks | do not imply a universal equality gate |
| [6. Decomposed Wire-In](#pattern-6-decomposed-wire-in-with-single-entry-point) | partial | CLI/front-door wrappers and dispatch helpers | useful design discipline, not a standalone kernel primitive |
| [7. Three-Axis Novelty](#pattern-7-canonical-hash--operation-multiset-3-axis-novelty) | partial / candidate | novelty and primitive-routing work | needs one named novelty gate before it should carry public weight |
| [8. Bloat-Cap Calibration](#pattern-8-bloat-cap-calibration-via-real-telemetry) | doctrine | telemetry-based cap setting | keep short unless a current histogram/audit owns it |
| [9. Token-Optimized Self-Modeling](#pattern-9-token-optimized-self-modeling) | live | [architecture index](../../src/ztare/architecture_index/graph.yaml), [`primitive_tick_surface.py`](../../src/ztare/research_director/primitive_tick_surface.py), arch-map validators | overlaps [Reflexive Primitive 1](reflexive_engineering.md#primitive-1-token-optimized-self-modeling); keep one owner story |
| [10. Cross-Reference Knowledge Graph](#pattern-10-cross-reference-knowledge-graph) | live | [graph interfaces](graph_interfaces.md), [`graph_carrier.py`](../../src/ztare/common/graph_carrier.py), graph capability audit | route graph output through decision receipts, not generic graph claims |
| [11. Cross-Scale Alias Map](#pattern-11-cross-scale-alias-map) | partial | structural-language catalog and alias drift checks | reduce to alias/drift mechanics where code exists |
| [12. Sealed Forecast Pool](#pattern-12-sealed-forecast-pool-for-execution-control) | live | [`forecast/pool.py`](../../scripts/public/control/forecast/pool.py), [`prediction_contract.py`](../../src/ztare/forecasting/prediction_contract.py), forecast capability audit | keep score, decision influence, and authority separate |
| [13. Result-Bound Success Claims](#pattern-13-result-bound-success-claims-harness-honesty) | live | [`autoresearch_trace.py`](../../src/ztare/reports/autoresearch_trace.py), source-index and evidence-output binding tests | every success claim must bind to an artifact or become no-answer |
| [14. Out-of-Loop Judge](#pattern-14-out-of-loop-judge-for-self-attesting-producers) | advanced live / governance | commit membrane, signed verdict/proof machinery | keep first-run docs away from this ceremony unless needed |
| [15. Structural Contract Gating](#pattern-15-structural-contract-gating) | live where schema exists | [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py) plus typed gates | structural visibility only; content and process still need separate audits |
| [16. Reasoning Contract Compiler](#pattern-16-reasoning-contract-compiler) | live | [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py), legacy route-card implementation in [`primitive_operator_cards.py`](../../src/ztare/research_director/primitive_operator_cards.py), [routing drift audit](../../scripts/public/control/research_move_routing_drift_audit.py) | move recognition belongs in primitive route cards; contracts consume routed ids |
| [17. Shadow-First Controller Promotion](#pattern-17-shadow-first-controller-promotion) | partial | [`orchestration_shadow_log.py`](../../src/ztare/research_director/orchestration_shadow_log.py), [shadow-log tests](../../tests/test_orchestration_shadow_log.py) | promotion needs pre-action rows plus later outcomes |
| [18. Typed Obstruction Basin](#pattern-18-typed-obstruction-basin) | domain-specific live | NS basin graph, [`graph_carrier.py`](../../src/ztare/common/graph_carrier.py), [`primitive_amnesia.py`](../../src/ztare/research_director/primitive_amnesia.py) | split generic graph decision receipts from NS-specific basin algorithms |

## Pattern audit matrix

This table is the maintenance contract for the catalogue. Use it before
promoting a doctrine pattern into a public capability, adding a new action
contract, or claiming that a pattern is wired.

| Pattern | Failure class | Selecting signal | Required artifact or check | Known confuser | Status |
|---|---|---|---|---|---|
| 1. Stub replay | Provider or harness path changes without stable replay | Recorded model/tool output exists and parsing or routing may change | Archived transcript plus focused replay fixture | Unit test with tidy mocked output | partial |
| 2. Preflight battery | Malformed launch reaches model spend or public command | Command depends on source refs, rubric ABI, env, or artifacts | Preflight receipt with blockers and next command | Post-hoc run triage | live |
| 3. Eligibility filter | Candidate selection follows order or fallback bias | Candidate pool has hard eligibility rules before ranking | Filter result plus rejected-candidate reason | Scorer/ranker tuning | doctrine |
| 4. Fallback provenance | Retry or fallback hides the effective path | Provider retry, subscription/API fallback, or cached route occurs | Requested/effective model ids, fallback event, usage/cost row | Silent retry treated as reliability | partial |
| 5. Inverted hash | Equality can be gamed by formatting | Artifact identity matters under adversarial formatting | Raw hash, canonical hash, and invertible normalization rule | Ordinary checksum | doctrine |
| 6. Single entry point | Feature works through a side path but not the front door | New command/module creates another entry route | CLI route test plus public smoke coverage | Direct script as product path | partial |
| 7. Three-axis novelty | Novelty ignores operation composition | Artifact uses several transformations whose order or multiset matters | Canonical hash plus operation-multiset row | Generic provenance hash | candidate |
| 8. Bloat-cap calibration | Context/control surface grows without measured value | New context block, branch, or token budget is added | Telemetry histogram, cap, and ablation or non-use receipt | Static token budget | doctrine |
| 9. Self-modeling | Agent edits from local snippets and misses global invariants | Module has cross-file invariants or repeated edit mistakes | Architecture-index row, graph edge, invariant/check row | Prose architecture overview | live / duplicate |
| 10. Cross-reference graph | Multi-hop artifact/code relation is lost in prose | Decision needs a graph-shaped dependency or route relation | Graph decision receipt or architecture graph row | Decorative graph/RAG index | live |
| 11. Cross-scale map | Same-looking relation is generalized across scales | Claim crosses local, chain, recursive, or meta scopes | Scale-tagged receipt and allowed scope set | Analogy paragraph | partial |
| 12. Sealed forecast pool | Prediction affects work without authority or timing discipline | Forecast is used before or during action choice | Sealed contract, forecast row, resolution, score, decision-use row | Scratch prediction treated as calibrated forecast | live |
| 13. Result-bound success | Controller promises a result it does not hold | Output claim names a file, chart, evidence item, or result | Artifact binding or typed no-answer receipt | Success log line | live |
| 14. Forced out-of-loop judge | Producer can self-certify semantic or expensive obligation | Producer can author/propose pass-fail state | Signed judge proof against frozen rubric and artifact hash | Same-family review or prose self-attestation | live, advanced |
| 15. Structural contract gate | Fluent prose satisfies form while central fields are missing | Domain/project surface has anchor fields or obstruction slots | Schema-bound contract receipt plus downstream audit gate | Checklist with free-text fields | live |
| 16. Reasoning contract compiler | Named move does not compile to a next action | Route names a move but lacks artifact/check consequence | Move-card route, action contract, nearest-confuser rejection | Menu label treated as action | live |
| 17. Shadow-first controller | Controller is enforced before causal evidence exists | New router/policy would change production action | Pre-action shadow row, live action, later outcome, delta analysis | Post-hoc explanation row | partial |
| 18. Typed obstruction basin | Ruled-out route is rediscovered under new vocabulary | Project surface accumulates ruled-out routes faster than closures | Typed obstruction record, derived basin graph, pre-attack query | Free-prose list of failed attempts | partial / domain-live |

---

## Pattern catalogue

### Pattern 1, Stub-Replay Integration Testing

*Problem.* LLM outputs are non-deterministic, but the dispatch code around
them is ordinary software. If tests replace the model with tidy synthetic
strings, the parser and router never see the shapes that break them: malformed
JSON, partial code blocks, copied examples, missing fields, or extra prose
around a structured answer.

*Pattern.*
1. Persist real model outputs in normal telemetry.
2. Add a stub runtime that can replay selected archived outputs by file.
3. Build integration tests from those archived outputs.
4. Assert wrapper invariants: accepted rows, rejected rows, candidate fate,
   downstream artifact shape, and typed error.

*Use it when.* You are changing a parser, router, candidate selector,
telemetry writer, or launch wrapper.

*Do not use it as.* A replacement for live quality tests. Replay catches
software defects in the wrapper. It does not measure prompt quality, judge
calibration, or prompt-injection resistance.

*Concrete example.* A symbolic-regression pipeline with parallel mutators and
recombination exposed three independent wrapper bugs before launch:
- AST extraction did not parse Python's implicit string concatenation form.
- The score function expected a string while the tournament passed a typed
  result object.
- A fusion prompt template included JSON braces that `.format()` read as
  placeholders.

Replay fixtures caught all three without another model call.

---

### Pattern 2, Pre-Flight Assertion Battery

*Problem.* Many launch failures are not crashes. They are stale fixtures,
missing source refs, dead branches, disabled checks, malformed rubrics, or
commands that still run but no longer test what they claim to test.

*Pattern.*
1. Keep a small battery of deterministic scenarios: happy path, malformed input,
   missing artifact, stale artifact, empty input, and known regression.
2. Run it before spendful or public-facing runs.
3. Treat any regression as a launch blocker.

*Implementation.* A single Python script or pytest module is enough. The
important part is ownership: the battery is the binding launch contract.

*Concrete patterns inside the battery.*
- *Mutator-failure-isolation*: K parallel workers, one raises, verify K-1 candidates still flow through.
- *Empty-input handling*: every component should degrade gracefully (return None, raise typed error, etc.) when fed empty/null inputs.
- *Concurrency safety*: if telemetry files are append-mode JSONL, verify under concurrent writers that records aren't torn.
- *State cleanup*: deterministic inputs across N sequential calls should yield byte-identical outputs.
- *Configuration extreme values*: K=0, K=1, K=large; max_pairs=0, max_pairs=infinity. Each branch gets exercised.

---

### Pattern 3, Eligibility Pre-Filter for Position-Biased Selection

*Problem.* Candidate pools often have hidden order bias. Pairing candidates as
`(i, j)` with `i < j`, truncating at `max_pairs`, or trying fallbacks in list
order can spend the whole budget on the first bad candidate.

*Pattern.* Before pairing or ranking, run a cheap eligibility filter:
parseability, contract conformance, dimension checks, required fields, or
source binding. Pair only the eligible subset. Log every dropped candidate with
a reason.

*Why it works.* The expensive budget is spent on candidates that can actually
enter the downstream stage.

---

### Pattern 4, Fallback Chain with Provenance Telemetry

*Problem.* Fallbacks are useful during execution and terrible during
postmortem if they are silent. A result may come from recombination,
tournament-only fallback, a single mutator, or a cached candidate, but the
report only says "success."

*Pattern.* Tag every output candidate with a `stage_origin` field. Preserve it
through filtering, scoring, tournament, and artifact write. Surface the winning
stage in telemetry.

*Implementation.*
- Each stage that creates or modifies a candidate sets `extras["stage_origin"]` to a descriptive slug (`mutator_persona_X`, `crossover_personaA+personaB`, `fusion`, `single_mutate_fallback`).
- The tournament logger records winner's `stage_origin`.
- Postmortem queries by `stage_origin` to answer "did Stage N actually contribute to wins?"

*Why it works.* It turns "which stage actually worked?" into a query instead
of a reconstruction exercise.

---

### Pattern 5, Inverted Hash for Adversarial-Resistant Equality

*Problem.* Naive string hashing is weak for LLM outputs. Whitespace changes,
renamed variables, reordered commutative operands, or equivalent syntax can
produce a different hash for the same idea.

*Pattern.*
1. Parse the output into a canonical AST (SymPy, libcst, etc.).
2. Apply structural normalizations: simplify expressions, alpha-rename variables in DAG-traversal order, sort commutative children.
3. Hash the canonical serialization.

*Why it works.* The equality check moves from surface text to structure. Cheap
cosmetic changes collapse to the same canonical representation.

*Caveat.* Canonical hash is one layer. Pair it with operation-multiset distance,
behavioral probes, or residual fingerprints when novelty has consequence.

---

### Pattern 6, Decomposed Wire-In with Single Entry Point

*Problem.* Pipeline orchestration logic accumulates inline at the call site.
After three feature additions, the call site is a 300-line block that nobody
wants to change. New bugs hide in the tangled control flow.

*Pattern.* Extract the dispatch logic into a single helper module with a typed input dataclass. The call site becomes one function call with one dataclass. The helper module tests cleanly in isolation, and the call site stays readable.

*Smell test.* If your iter loop has more than ~30 lines of inline LLM-dispatch logic, decompose it. The decomposition is almost always 2× cleaner than you'd expect.

*Concrete shape.*
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

### Pattern 7, Canonical Hash + Operation Multiset (3-Axis Novelty)

*Problem.* When ranking candidates for novelty against a prior champion, single-axis scoring (Levenshtein on source text, BLEU, simple hash) is gameable. A mutator that knows the metric routes around it via cosmetic changes.

*Pattern.* Compute three independent novelty axes and require the candidate to clear each:
1. *Canonical AST hash*, different from prior champion's canonical hash (catches alpha-rename + reorder gaming).
2. *Operation multiset Jaccard*, distance ≥ threshold (catches structural-rearrangement gaming).
3. *Behavioral fingerprint*, residuals on a held-out probe set differ (catches everything else; only available post-fit).

Score with `min(axis_1, axis_2, axis_3)` so the candidate must move on every axis simultaneously.

*Why this helps.* Each axis blocks a different cheap move. A candidate that
changes formatting but not structure fails the canonical hash. A candidate that
rearranges the same operations fails the operation-multiset check. A candidate
that looks different but behaves the same fails the held-out behavioral
fingerprint. The claim is bounded: this is a stronger novelty screen than any
single text or hash metric, not a proof that the candidate is scientifically
new.

---

### Pattern 8, Bloat-Cap Calibration via Real Telemetry

*Problem.* Hard caps (max nodes, max depth) chosen by intuition tend to be either too aggressive (rejecting real-domain forms) or too lenient (missing pathological bloat). Both fail silently.

*Pattern.* Calibrate caps against histograms of real, accepted forms from past runs. Cap = max(observed) × 1.5 or so, depending on tail thickness. Re-calibrate when domain shifts.

*Concrete pitfalls.*
- AST depth on commutative ops, SymPy flattens `Mul(a,b,c,d,...)` to depth 1, so depth is near-useless for catching chained-multiplication bloat.
- Use node count as primary, raw operation-token count (count occurrences of `*`, `+`, `**` in source) as a secondary check.

---

### Pattern 9, Token-Optimized Self-Modeling

*Problem.* An LLM agent editing a codebase it cannot hold in context reads
snippets. Snippets create partial views. Partial views cause mistakes that look
correct locally but violate invariants the agent never saw. Standard
documentation is usually written for human orientation and often buries
ordering rules, preconditions, and cross-file contracts in prose.

*Pattern.* Build a compressed *self-model* of each critical module, optimized for agent consumption:

1. Structured over narrative. Dependency graphs,
   precondition/postcondition contracts, and lookup tables carry the ordering
   pressure better than explanatory prose. The map should state what breaks if
   step 3 changes without updating step 5.
2. Traversable over readable. "I want to change X" → "you must read lines Y-Z and preserve invariant K." Indexed by lookup.
3. Assertion-shaped over explanation-shaped. Invariants stated as checkable assertions (`python_code != None BEFORE fit_parameters() call`) are more useful than paragraphs justifying the order.
4. Line-anchored with drift tolerance. Line numbers are approximate pointers that move as the source changes. The map acknowledges drift ("lines ~2900-3053") so the agent greps to confirm the current location.
5. Drift-checked by formal validator. Pair each map with a runnable validator that compares claims against live source. Run on every PR; fail-closed on structural drift (claimed function no longer exists, claimed line range no longer contains the claimed pattern, etc.).

*Why this helps.* The map is optimized for the agent's failure mode: narrow
context, snippet reading, and missed ordering constraints. The validator is what
makes the map more than documentation. If the source moves and the map no
longer points to the claimed function, phase, or invariant, the drift check
fails before an agent relies on stale guidance.

*When to deploy.* Use this for modules agents edit often and that are too
large to hold in context, especially when they have ordering or cross-file
invariants. The cost is one map plus a validator. Do not write one for small
modules that are easier to read directly.

*Concrete examples.*
- ZTARE's `autoresearch_loop.py` is 4100 lines with multi-stage pipeline ordering that is invisible from any single snippet. The maintained autoresearch architecture map makes the ordering explicit. `scripts/public/validators/validate_autoresearch_arch_map.py` drift-checks it on every change.
- The orchestrator was split into 7 modules (iter_context, telemetry, state, prompt, contract_adherence, parallel_mutator, ...); each got its own arch map registered in the validator's MAP_REGISTRY.
- One validator, multiple (map, source) pairs. New modules add a tuple to the registry, no code change.

*Anti-pattern.* Treating arch maps as documentation that gets updated "when there's time." Without the validator gate, maps drift faster than the prose itself. Agents then consult stale maps and make worse decisions than if there were no map at all. The pattern is "map + validator"; the validator is mandatory.

*Origin.* The April 2026
[partial-context failure seam](../../research_areas/seams/engine/mutator/GP-100_epistemic_decoupling_seam.md)
records the incident: an agent made a partial-view mistake on
`autoresearch_loop.py` (4100 lines, agent read snippets, missed the
pipeline-ordering contract). The human correction was not "read more code." It
was "compress your own understanding into a reusable artifact optimized for
your consumption." The
[agent-readable self-model validator seam](../../research_areas/seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md)
added the formal validator. The pattern has since been promoted to modules
with non-trivial pipeline ordering.

---

### Pattern 10, Cross-Reference Knowledge Graph

*Problem.* Pattern 9 compresses code internals. Research artifacts have a
different problem: their meaning often lives in cross-references. A design note
points to a gate, a finding points to a paper section, a mandate points to an
operation. An LLM reading those files as flat text has to rebuild the relation
graph every time. Questions such as "what depends on this design note?" should
start with a graph lookup, then open the few files that matter.

*Pattern.* Extract the artifact relationship graph as JSON-LD (or property-graph format), regenerate on demand, drift-check via the same validator pattern as Pattern 9:

1. Define node types (seam, f_row, gate, op, paper, mandate_addendum, substrate, theorem, gap_type) and edge types (depends_on, instantiates, mechanizes, aliases, falsifies, supersedes, cites, op_fingerprint).
2. Auto-extract from existing artifacts (regex on cross-references like `GP-XXX`; pattern-match on op names like `core_NN`, `broad_NN`; gate-class references). Don't require manual frontmatter unless extraction confidence is low.
3. Emit JSON-LD to a single regenerated file (`analytics/public/queries/<system>_knowledge_graph.json`). Re-run on demand; deterministic output.
4. Drift validator that checks: every node corresponds to an existing artifact file; every edge target resolves; op references match the canonical vocabulary; gate references resolve to actual gate classes.
5. Query helper that takes a question (`"what depends on the theory-building
   operations seam?"`) and traverses the graph, returning relevant node IDs and
   one-line summaries. Optional but high-value for synthesis turns.

*Why this helps.* The graph is a navigation surface. It
shrinks the first read for dependency questions, names the files to inspect,
and lets drift checks prove that referenced nodes still exist. The answer still
comes from the source artifacts.

*When to deploy.* Use a graph when the artifact corpus has enough
cross-references that grep returns too much and synthesis questions need
multi-hop traversal. For a small or mostly linear corpus, a folder index and
links are cheaper.

*Anti-pattern.* Starting with a graph database before the read model earns
it. For a local repo holding thousands of nodes (well short of millions), regenerated JSON on
disk is easier to diff, audit, and ship. Move to a graph database only when the
queries or node count justify the extra operating surface.

*Concrete example.* ZTARE's seams, findings, and gates produced 137 nodes /
459 edges (average out-degree 3.4) when prototyped in May 2026. JSON-LD
compression: 12K tokens versus 440K of full seam text, 2.8% of original. Top
hubs included the
[ontology-trap seam](../../research_areas/seams/substrates/planck/GP-023_ontology_trap_planck_mechanism_seam.md),
the
[ansatz-to-prover seam](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md),
the
[missing-fit primitive seam](../../research_areas/seams/engine/grammar/GP-035_mutator_missing_fit_primitive_seam.md),
and the
[role-separation sandbox seam](../../research_areas/seams/protocol/GP-072_role_separation_sandbox_construction_seam.md).
The graph makes that structure visible at one query, collapsing a grep
across 137 files. The prototype is documented in the
[knowledge-graph proposal seam](../../research_areas/seams/engine/meta/GP-216d_knowledge_graph_proposal.md).

*Relationship to Pattern 9.* Pattern 9 compresses code. Pattern 10 compresses
the artifact network. Use both for systems with both kinds of complexity. The
validator pattern transports cleanly: same drift-check skeleton, different
artifact types.

---

## Common bugs the patterns catch

A taxonomy of LLM-pipeline integration bugs we've seen, by which pattern would have caught each:

> Scope. This is the engineering-bug slice only: integration faults a test pattern catches. The canonical epistemic-failure taxonomy is [epistemic_principles.md](epistemic_principles.md) Part I (structural) and [anti_pattern_catalog.md](anti_pattern_catalog.md) (operational field guide); this table does not duplicate them.

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
| Silent cross-scale vocabulary drift | Renaming pivot module at iteration scale silently breaks alias to op at research-arc scale | Cross-Scale Alias Map (Pattern 11) |
| Forecast used only as a scorecard | Read-only agents name the exact implementation trap, but the executor ignores it and only scores Brier later | Sealed Forecast Pool (Pattern 12) |
| Confident success claim with no payload | Agent returns valid artifact; harness swallows a wiring defect and ships "here's your chart" with no chart | Result-Bound Success Claims (Pattern 13) |

---

## Scope boundaries

- Live evaluation still matters. Patterns 1-2 catch integration bugs.
  Live evaluation catches model-quality, prompt-injection, and
  judge-calibration failures. Use both.
- Most components have older names. Record-replay testing, defensive
  programming, AST canonicalization, fuzz testing, contract checking, and
  provenance telemetry all predate this catalog. The value here is the
  combination tuned for LLM-mediated pipelines.
- The examples are local, the failure classes are portable. The catalog
  applies to RAG pipelines, multi-agent frameworks, code-generation pipelines,
  planning agents, research agents, and evaluation harnesses.

---

## Practitioner notes

If you're building one of these systems and reading this for the first time:

1. Start with Pattern 1 (Stub-Replay) and Pattern 4 (Provenance Telemetry). These two compound: stub-replay needs archived outputs to replay, and provenance telemetry generates exactly the right shape of archive. Implement them together.

2. Pattern 2 (Pre-Flight Battery) is the single highest-value discipline. A 30-minute battery before each launch saves a 3-hour run that produces uninterpretable output.

3. Pattern 6 (Decomposed Wire-In) is the readability investment. It pays back the second time you change the dispatch logic. Resist the urge to inline.

4. Patterns 5, 7, 8 are anti-gaming defenses. They matter most when your pipeline is in an evolutionary loop (mutator output feeds back into mutator input). For one-shot pipelines, they're optional.

5. Treat these as living patterns. Each emerged from a specific failure class. Your pipeline will surface failure classes these patterns don't address. Add to the catalogue.

---

## Origin

These patterns emerged during the development of
[ZTARE](https://github.com/sparckix/ztare), a workbench for adversarial
research validation and governed agent workflows. The patterns themselves are
independent of ZTARE and apply to LLM-mediated multi-stage pipelines. Each was
distilled from a specific bug we shipped or nearly shipped.

The taxonomy is provisional. If you adopt a pattern and find it breaks in your context, that's worth recording.

---

### Pattern 11, Cross-Scale Alias Map

*Problem.* Patterns 9 and 10 each handle one surface: code internals and the
artifact network. Mature LLM-mediated systems also develop bounded vocabulary
at several operational scales: one vocabulary for an iteration, another for a
research arc, another for verification, another for infrastructure. The same
move can appear under different names at each scale. Without explicit alias
tracking, a change at one scale can break the corresponding move at another,
and a new failure can be formalized in one place without checking whether it
already has machinery elsewhere.

*Pattern.*

1. Name the operational scales. A scale is a layer where the system has its
   own vocabulary and checks: iteration, research arc, verification,
   infrastructure, or documentation.
2. Record the vocabulary per scale. Put it in a registry module or a
   structured doc with stable ids.
3. Build an alias table. For each underlying move, list its names at other
   scales and the check that owns each name.
4. Lint the aliases. If a name changes, the alias table must fail until the
   mapping is updated.
5. Do not design this top-down. Add the table after at least three scales
   are real enough to drift.

*Why it works.* The alias table makes cross-scale reuse visible. The linter
turns a hidden vocabulary break into an ordinary maintenance failure.

*When to deploy.* Use it after your system has several live vocabularies and
you have already felt drift: a renamed iteration move, a changed verifier
label, or a research-arc label that no longer points at the right check.

*Anti-pattern.* Naming every prototype vocabulary "fractal." If your system
has one or two small vocabularies, document them directly. Add cross-scale
aliases when the second-order maintenance problem exists.

*Concrete example.* ZTARE accumulated several mature vocabularies before this
became useful. The public map is
[`cross_scale_fractal_map.md`](cross_scale_fractal_map.md), and the drift check
is [`check_cross_scale_aliases.py`](../../scripts/public/utilities/check_cross_scale_aliases.py).

*Relationship to Patterns 9 + 10.* Pattern 9 keeps code context findable.
Pattern 10 keeps artifact relations findable. Pattern 11 keeps repeated moves
aligned when they appear under different names across code, artifacts,
verification, and project work.

*Origin.* ZTARE's
[theory-building operations seam](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md)
and
[knowledge-graph proposal seam](../../research_areas/seams/engine/meta/GP-216d_knowledge_graph_proposal.md),
May 2026. For other systems, the useful piece is the alias table plus linter
that keeps repeated moves aligned across scales.

---

### Pattern 12, Sealed Forecast Pool for Execution Control

*Problem.* Agents make action forecasts constantly: this proof split will
compile, this branch is worth a swarm, this run will take 30 minutes. Without a
typed forecast surface, those claims either vanish into chat or become
post-hoc rationalization. Standard prediction markets and proper scoring rules
solve part of this problem, but live markets are too much machinery for most
research ticks and can create beauty-contest dynamics.

*Pattern.*

1. Create a sealed contract with an objective resolver and horizon.
2. Collect forecasts from read-only pricing agents that cannot execute the
   action they price.
3. Require multi-field estimates: `p_success`, agent-minute effort, regression
   risk, dependency/new-lemma risk, concrete failure modes, and a separately
   elicited `tail_insurance_premium` (1-100 worry token). The tail token carries
   calibration signal the point estimate misses, predicts per-row Brier at
   Spearman ρ≈0.36-0.47 across pilots, and remains informative when
   single-channel verbalized confidence sign-flips on some agent variants.
4. Aggregate sealed forecasts, then isolate execution from the forecasters.
   Isolation has operational consequences: when forecasters can see each
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
    scientific work, sparing them a reconstruction of the market from raw ledgers.
11. Convert aggregate forecasts into allocation recommendations: run now, split
    the contract, ask another independent agent, defer, or stop the branch.
    Use `tail_insurance_premium` as the escalation gate: high premium routes
    to abstain-and-escalate (or to a fresh cross-family judge re-decision
    on the same contract). The naive
    "raise the threshold when worried" wiring degrades utility, while the
    abstain-or-escalate wiring restores it. When the cost regime is
    asymmetric in the direction the agent's own probability would already
    favor, the cross-family judge wiring outperforms abstention. When
    losses are symmetric, plain abstention is typically cheapest.
12. Track reliability beyond Brier: probability buckets, effort error,
    failure-mode precision, drift, and high-confidence miss incidents.
    Track these per agent family separately, since calibration corrections that
    survive on cost/effort do not always transfer to probability Brier, and
    rules that rescue one family's overconfidence can leave others
    unchanged. Universal "this LLM is over-confident, divide by 8" rules
    over-generalize a per-family signal.
13. Generate reflexive insight read models that summarize positive
    externalities, calibration incidents, decision-use gaps, and transport
    debt so executors consume ready-made nudges and skip authoring their own meta-analysis.
14. Compute effective independence at read time so multiple aliases in one
    provider/runtime family do not masquerade as multiple independent prices.
15. Treat forecast updates as evidence-triggered responses: when material
    evidence arrives before resolution, forecasters emit either a belief update
    or an explicit no-update response.

*Authority boundary.* ZTARE has two forecast surfaces. A sealed forecast-pool
contract can affect consequential state only after it has the contract,
independent forecasts, resolver, score closure, and decision-use row. Local
prediction rows and scratch forecasts are measurement receipts: they can be
scored, audited, and used for analysis, but they do not satisfy membrane or
release authority by themselves. The read model that enforces this distinction
is
[`prediction_contract.py`](../../src/ztare/forecasting/prediction_contract.py).

*Why it works.* The forecast pool has two value channels. Calibration improves
future routing. Failure-mode preconditioning improves the current action before
the result resolves. A pessimistic forecast can therefore still be useful if it
names the exact failure mode the executor must avoid.

*When to deploy.* Macro decisions, branch choices, large swarms, GNN/GPU or
training gates, public claims, and Lean/replay batches with useful
opportunity cost. Do not use it for trivial edits or cheap saved-artifact
orientation.

*Anti-pattern.* Treating forecasts as generic advisory prose. A forecast earns
preconditioner credit only when the named failure mode is specific and appears
in the implementation diff, outcome, E-row, or
[research-yield decomposition seam](../../research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md)
as a constraint the executor honored.

**Adjacent anti-pattern: rationale-exchange ensembles for single-shot binary
forecasting.** Showing forecaster B the prose rationale of forecaster A
before B emits its own probability does not reliably improve B's Brier.
Pooled across directional pairs the effect is at chance. Adversarial
framing (telling B to find the strongest reason A is wrong) reduces the
worst-case anchor but does not lift the pooled effect above noise. The
structural preconditions that make debate work for code or seam review
(concrete errors, pre-resolution verification, compounding error
propagation, role specialization between failure-finder/builder/arbiter,
decidable arbitration) do not hold for single-shot binary forecasting.
Default to independent aggregation. Only introduce exchange when the
task supplies those preconditions.

Adjacent anti-pattern: LLM yield-prediction for scheduling reasoning queues.
Subscription-class agents asked to predict whether a proof search or
reasoning attempt will succeed have been observed to predict
anti-correlated with actual outcomes on stratified corpora, performing
worse than a constant-0.5 baseline across multiple families. Do not schedule a
proof mill or reasoning queue by LLM completability scores. Use oldest-ready
ordering or domain heuristics until the predict-vs-execute capability is shown to
dissociate in the agent class you deploy.

*Concrete example.* In the NS route-1 pressure branch on 2026-05-14, two
read-only forecasters priced a Lean split at aggregate `p_success=0.771` and
both flagged the same trap: a fake carrier-identification split that merely
renamed `l2Carrier_identifies_totalAngularMoment` or replaced it with weak Prop
labels. The implementation carried the equality explicitly while separating
projection, Riesz/angular matching, normalization, and anti-tautology guards.

*Relationship to reflexive engineering.* This entry is the public agentic
pattern: any agentic system can use sealed contracts, read-only forecasters,
artifact resolution, scoring, and drift checks to keep forecasts from
collapsing into chat advice. The same mechanism becomes Reflexive Engineering
Primitive 9 when ZTARE turns it inward, using scored disagreement to govern its
own branch choices, effort priors, and execution constraints.

*Drift validator.* Run:

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

*Origin.* The
[forecast-pool decision primitive seam](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md),
May 2026:
[forecast-pool decision-market seam](../../research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md)
and
[forecast-pool decision-market spec](../../research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md).

---

### Pattern 13, Result-Bound Success Claims (Harness Honesty)

*Problem.* The model returns a valid result, but the wrapper ships a confident
empty answer. The usual chain is:

1. An upstream planner writes success copy before the artifact exists.
2. A downstream assembly path throws.
3. A broad `except` turns the throw into an empty result.
4. The user still sees the planner's success sentence.

The diagnostic tell is simple: the provider call logged success, the user
surface promised an artifact, and the artifact is absent.

*Pattern.*

1. The stage that holds the artifact writes the success text.
2. Every success claim must be bound to a verified artifact path, row, receipt,
   or object.
3. Failure becomes an honest no-answer with a typed event.
4. Shared privileged paths take complete context or a shared plain function;
   they do not run through partial request shims that silently lack state.

*Current ZTARE owner.* The autoresearch side enforces this through the
source-to-evidence trace chain: `ztare project source-index`, evidence-output
binding receipts, evidence-gap resolutions, and `ztare autoresearch trace`.
`src/ztare/reports/autoresearch_trace.py` refuses clean run-readiness language
when a claim points at stale source, unbound evidence output, or unresolved
evidence gaps. The focused regression suite is
`tests/reports/test_autoresearch_trace.py`.

*Why it works.* It removes the two independent ways orchestration can lie:
claiming a result it does not hold, and hiding why it does not hold one.
Artifact binding blocks the false success. Typed events make the remaining
failure visible without reading raw logs.

*When to deploy.* Any pipeline where an upstream stage drafts user-facing text and a downstream stage produces the artifact that text describes (assistant + visualizer, planner + tool executor, narrator + retriever). Especially before shipping a feature whose success copy is generated separately from its payload.

*Anti-pattern.* "We log the exception, that's enough." A log line is not
observability for a correctness failure. It is invisible at the surface where
the wrong answer ships. A second anti-pattern is fabricating a plausible result
to honor the promise. The honest no-answer is the correct degradation.

*Concrete example.* A production agentic product answered "where did my money go in April" with "here's your chart" and no chart. The generation agent had returned a valid artifact and the provider call logged `200 OK`. Evidence assembly reused a route handler through a request shim missing `.state`; the resulting `AttributeError` was caught by a blanket `except: return []`; the upstream planner's chart-promising sentence shipped unchanged; and the only trace was in process logs, so it looked healthy until someone read journald. Fixes: complete the shim, bind the promise to the produced artifact (honest no-answer otherwise), and emit a typed failure event. One root-cause incident, three structural faults, the model was never wrong.

*Relationship to other patterns.* Complements Pattern 4 (Fallback Chain with Provenance Telemetry): Pattern 4 makes *which stage produced the output* traceable; Pattern 13 makes *the claim that there is an output* truthful and the *absence* of one observable. Pattern 2 (Pre-Flight Battery) catches the wiring fault before launch; Pattern 13 governs the runtime contract when it slips through anyway.

*Origin.* Production agentic-product incident, 2026-05-16. Generalized
because the defect sat in the harness around the model and can recur in any
propose/dispose pipeline.

---

### Pattern 14, Out-of-loop judge for self-attesting producers

*Problem.* A producer should not be able to certify its own difficult work.
If the same agent both produces the artifact and attests that the bar was met,
the cheapest accepted path is often a well-shaped assertion. Required fields and
enum values help, but they still leave semantic truth with the producer. The
risk is highest when the agent also wrote the containment mechanism, because it
already knows where the weak checks are.

*Pattern.*
1. Reference monitor, sole writer. A separate process (a verificator daemon) is the only thing that can write official state. The working agent can only *propose*. Complete mediation, minimal TCB, fail-closed: until every trust anchor is provisioned, the substantive path is *blocked*, never *trusted-by-default*.
2. Mutator → JUDGE → monitor triad. A substantive obligation is discharged only by a verdict from a *separate* judge, of a *different provider family* than the working agent. The harness runs the judge. The mutator never produces the verdict it will be graded by.
3. The judge holds a key the mutator cannot read. A second signing keypair (ed25519), private half owned by a dedicated OS identity, unreadable by the agent user *and* by the daemon signer. The judge signs an *execution proof*, `{tick_id, contract_id, item_id, prompt_hash, witness_sha, artifact_sha, model_identity, raw_output_hash, verdict}`. The monitor verifies that signature against a *pinned, committed* public anchor before it stamps an official verdict. The mutator lacks the key ⇒ cannot fabricate a verdict, only relay a real one.
4. Total proof binding (anti-replay). *Every* field the judge signed must equal the claimed row, or a signed proof for one obligation is replayable on another. Bind tick/contract/item/witness/prompt/artifact/verdict, not a subset.
5. Un-forgeable rubric. The monitor recomputes the judge prompt from the *frozen, daemon-signed* contract row (immutable per work unit), not from agent-supplied text, and requires `prompt_hash` to match. The agent cannot feed the judge a weakened rubric.
6. Signed identity, not claimed identity. The judge's provider family is read from the *key-signed* `model_identity` inside the proof, never from a proposal field the mutator can set. A same-family model cannot masquerade as cross-family.

*Why it works.* The accepted claim becomes: a different-family judge, run
outside the producer's account, signed a verdict the producer cannot forge,
against a frozen rubric, with replay-bound artifact hashes. The guarantee comes
from key separation, cross-family review, frozen rubric bytes, and total field
binding. Model strength still matters for review quality, but the security
property is about who can produce an accepted verdict.

*When to deploy.* Use this when the artifact's value depends on an acceptance criterion
that is expensive to meet and cheap to assert, and the producer can write or
propose the record that says whether it passed. The strongest warning sign is a
gate authored by the same agent family it governs.

*Anti-patterns.*
- Agent-configurable key paths: an env-overridable judge key reintroduces the
  forge.
- Self-review: the agent family that wrote the membrane reviews its own
  membrane and misses the same class of flaw at the review layer.
- Fail-open provisioning: missing trust anchors must block, not temporarily
  trust.
- Same-family judging: shared blind spots can rubber-stamp the producer.
- Single-pass judging: a second review path must be able to downgrade an
  inflated pass.

*Concrete example.* A commit-membrane forced witness fields and a `why_not`
enum, but the same agent family that built it later discharged obligations with
well-shaped generic prose. The shape was checked, but semantic truth was still
self-attested. Pattern 14 changed the authority boundary: a separate VPS OS
identity (`ztare_judge` != agent `ztare` != signer `ztare_verify`), a private
key unreadable by the agent and daemon signer, a different-family judge, and a
monitor that verifies the signed proof against frozen rubric bytes and artifact
hashes. Three cold cross-provider reviews then found the residual holes in the
mechanism: forgeable verdict, replayable proof, and unsigned family claim. Each
hole was closed before the mechanism was treated as trusted.

*Relationship to other patterns.* Pattern 14 is Pattern 5 (Inverted Hash for Adversarial-Resistant Equality) and Pattern 13 (Result-Bound Success Claims) escalated from *honest-harness* to *hostile-producer*: Pattern 13 makes the harness unable to *accidentally* lie; Pattern 14 makes the producer unable to *deliberately* lie even when it wrote the harness. Pattern 2 (Pre-Flight Battery) is the regression net that keeps the membrane's adversarial tests green across changes.

#### Generalization (2026-05-18): exogenous identity over consequential state

The judge keypair is one instance of a wider rule: any state transition that
the producer must not self-authorize needs a signature from an identity outside
the producer's write boundary, verified against a pinned committed anchor, with
fail-closed provisioning. A judge key gates verdicts. An approval key can gate
other consequential declarations: canonical proof target registration,
retiring an uncloseable obligation, or vouching for manifest provenance. The
implementation shape is the same: dedicated OS identity, key mode `0400`,
unreadable by the producer and daemon signer, public half pinned in reviewed
code, and no env flag or proposal boolean as a substitute.

A second technique handles repeated hardening drift. **Precommitted promotion
contracts** admit a membrane change only through a deterministic PASS / FAIL /
BLOCKED contract authored before the change. The contract also says what the
change may not claim. Unresolved debt moves to a separately governed item,
kept out of any passing claim.

The recursive lesson, and a deliberate status boundary. This pattern's own
acceptance machinery became a test case for the pattern. A builder-written
"acceptance" adversarial test for the membrane was submitted to a not-the-builder cold
pass and failed: its nominally distinct adversarial fixtures collapsed to one
rejection, its evidence had a stale-artifact false-pass, and it never exercised
the real risk: a well-formed envelope carrying a vacuous or unfaithful claim. The
finding generalizes: a builder cannot author its own acceptance gate. Valid
acceptance is authored and run by not-the-builder, in the provisioned
environment, evidenced by the daemon's own artifacts. A runner's prose does not count.
"No output" is not a pass. Accordingly this catalogue entry documents the
techniques, but does not assert that the
[commit-membrane opener spec](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)
instance is validated. Its status is implemented. Acceptance requires
not-the-builder construction and run in the provisioned environment. The
irreducible residual, a faithful formal target is still only as good as the human
judgment that it captures the informal problem, is `epistemic_principles.md` P16
and is not closed by any technique above.

*Origin.* The
[commit-membrane opener spec](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md),
2026-05-17. The portable failure class is a
self-attesting producer with write access to the record that says whether it
passed. Full hardening history lives in
[the mode-independent commit-membrane hardening record](../../research_areas/seams/apparatus/cage/GP-241_commit_membrane_mode_independent_forcing_seam.md);
reproducible provisioning lives in `deploy/FIRST_TIME_SETUP.md`.

---

### Pattern 15, Structural Contract Gating

*Problem.* In structured domains, a fluent answer can avoid the commitment
that matters. A proof sketch can skip the theorem boundary. A statistical claim
can avoid the degrees-of-freedom rule. A compliance answer can cite the right
rule family without selecting the rule. A checklist that accepts free text will
not catch this: the agent can fill every field and still commit to no
checkable structure.

*Pattern.* Write a contract around the domain's structural anchor, then audit
that contract after the agent's primary work succeeds.

1. Anchor: the invariant the domain itself cares about, such as a type
   signature, conservation law, algebraic object, statistical design, or
   legal rule boundary.
2. Contract template: a receipt schema derived from that anchor. Fields
   that require structural commitment use enums, typed references, hashes, or
   whitelists, which close the laundering route that free strings leave open.
3. Audit gate: a deterministic gate that refuses ratification when the
   receipt omits central fields or fills them with untyped prose. The schema is
   versioned and pinned, usually by `contract_sha256`, so the agent cannot move
   the anchor during the run.

*Current ZTARE owner.* This is live where a domain schema has been written:
[`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py)
lowers selected research moves into required receipt fields, while typed gates
for theorem-review, coverage, event-prefix, boundary-card, and source-contract
schemas enforce particular receipts. The public claim is schema-bound
visibility, not universal content verification.

*Why it works.* The schema is anchored in a property the domain adjudicates,
not in reviewer preference. Missing fields, wrong enum values, contradictory
degrees of freedom, absent object maps, or unpinned source contracts become
ordinary software failures. The gate runs after the fluent work exists because
that is when paraphrase laundering is visible.

*Use it when.* Deploy this pattern when all four conditions hold:

1. The domain has an enumerable structural invariant.
2. The agent can appear successful while avoiding that invariant.
3. The required fields can be named before the run.
4. The schema cost is lower than the cost of catching the laundering later.

Skip it for aesthetic, open-ended, or contested criteria where no stable
structural anchor exists.

*What it catches.*

- Omission: a central field is missing or empty.
- Deflection: a field that requires a structural commitment contains
  filler prose, such as `multiple_comparison_correction_method: "we adjusted for
  the family"`.
- Form violation: the value conflicts with the anchor, such as degrees of
  freedom that contradict the declared statistical test.

*What it does not catch by itself.*

- Content lies: a well-formed value can still be fabricated. Pair the
  contract with content audit, such as Lean replay or sibling data checks.
- Process lies: a run can misstate how it was executed. Pair the contract
  with pre-registration and independent logs.
- Anchor capture: the schema can drift. Pin schema versions and refuse
  unrecognized contract hashes.

*Concrete examples.*

- The
  [PDE estimate-craft seam](../../research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md)
  / `pec_k` owner-preimage prefix gate: the gate demands fields such as
  `owner_map`, `pre_payoff_timing`, `full_output_scale_owner`,
  `pointwise_payment`, `finite_atom_budget`, `multiplicity_bound`, and
  `owner_preimage_prefix_inequality`. The useful result is that the workbench
  emits `owner_preimage_receipt_missing` and refuses a long PDE
  analogy paragraph. Code: [`owner_preimage_prefix_gate.py`](../../src/ztare/gates/owner_preimage_prefix_gate.py).
- Parametric hypothesis-test claim verification at
  `projects/structural_contract_gating_demo/`: the anchor is the test family's
  structural surface, including degrees of freedom, assumption set,
  multiple-comparison surface, and effect-size requirement. The gate refuses
  adaptive interim looks declared as unchanged alpha, paired designs forced into
  independent-sample tests, and uncorrected primary-claim contrast sets. Honest
  versions with alpha-spending, paired-family justification, or closed testing
  pass. An adversarial audit found that a free-string early contract accepted
  many laundering modes. Enum and whitelist closures reduced that residual.

*Where it plausibly transfers.* Candidate domains include:

- Formal-method proofs. Anchor: proof-system deduction rules + domain structural facts. (Worked.)
- Statistical inference. Anchor: test family's degrees-of-freedom rules, assumption sets, multiple-comparison surface. (Worked.)
- Smart-contract audit. Anchor: Solidity-specific invariants (conservation of value, reentrancy guards, monotonicity of state machines).
- Tax / regulatory compliance. Anchor: jurisdictional structural rules (basis propagation, character-of-income preservation, treaty interaction).
- Type-system-checked refactors. Anchor: source language's type/effect/ownership rules.
- Causal inference claims. Anchor: identification strategies (RCT, IV, RDD, DiD, DAG do-calculus).
- Scientific peer-review augmentation. Anchor: reporting-standard structural fields (CONSORT, STROBE, ARRIVE, PRISMA, SPIRIT).
- Supply-chain provenance. Anchor: identity/value conservation through transformations.
- Pharma post-market surveillance. Anchor: FDA/EMA pharmacovigilance rules (causality assessment, dechallenge/rechallenge, signal detection).
- Aerospace / safety-critical certification. Anchor: DO-178C / ISO 26262 structural objectives.
- Quant trading model validation. Anchor: backtest structural rules (OOS partition, look-ahead avoidance, transaction-cost modeling, regime-stratified evaluation).
- AI-assisted code review at scale. Anchor: language type system + design-pattern invariants.

Transfer cost is mostly anchor work: naming the central fields and keeping them
versioned. Once the anchor is enumerated, the contract and audit gate are
straightforward software.

*Honest limitations.* Evidence is suggestive, not conclusive: the worked
examples are NS/PDE estimate work and parametric hypothesis-test claims.
Transfer beyond domains with sharp structural anchors remains unproven.
Implementation quality is central. A vague schema gives the name of the pattern
without the protection. The domain owner must maintain the anchor as the domain
surface changes.

*Origin.* First observed in ZTARE's NS millennium hunt (`pec_l`/`pec_k`) in
the
[PDE estimate-craft seam](../../research_areas/seams/engine/meta/GP-219_pde_estimate_craft_sister_vocabulary.md),
2026-05; the replication on hypothesis-test claim verification
(`projects/structural_contract_gating_demo/`) substantiates domain transfer.

---

### Pattern 16, Reasoning Contract Compiler

*Problem.* LLM agents can name the right reasoning move while failing to
perform the action that move implies. A label such as "boundary pattern" or
"router branch" often changes the explanation more than the behavior. The
reverse failure is also dangerous: a plausible but wrong contract can steer an
agent into the wrong action more strongly than no contract at all.

*Pattern.* Compile each selected reasoning move into a small action contract.
The contract carries:

1. source facts the route is allowed to use
2. the residual or evidence record that selects this route
3. the nearest confuser route and the source fact that rejects it
4. an action program with current index, required next action, and stop rule
5. a deterministic gate for required fields, program order, stop condition, and
   source-contract alignment
6. a later outcome trace so the route can be evaluated after use

*Current ZTARE owner.*
[`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py)
is the compiler.
The primitive route-card implementation lives in the legacy-named
[`primitive_operator_cards.py`](../../src/ztare/research_director/primitive_operator_cards.py)
module and provides compact move cards plus optional semantic-atlas routing.
The contract records legacy route-provenance fields so later audits can
distinguish embedding-backed selection from lexical fallback. The main
regression suite is
[`tests/test_pattern_action_contract.py`](../../tests/test_pattern_action_contract.py);
the drift guard is
[`research_move_routing_drift_audit.py`](../../scripts/public/control/research_move_routing_drift_audit.py).

Keep rich audit fields for analysis, but expose compact execution fields to the
agent at runtime. The agent executes the contract. The system validates it.

*Current implementation contract.*

| Contract piece | Owner | Check |
|---|---|---|
| Route handle | primitive route-card module, currently [`primitive_operator_cards.py`](../../src/ztare/research_director/primitive_operator_cards.py) | matched card id, matched terms, semantic-vs-lexical route mode |
| Required action fields | [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py) | receipt schema with explicit artifact slot and required fields |
| Nearest-confuser rejection | [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py) | route test plus source fact that rejects the neighboring route |
| Drift guard | [`research_move_routing_drift_audit.py`](../../scripts/public/control/research_move_routing_drift_audit.py) | blocks new top-level phrase lists and direct lexical-only brief routing |
| Regression | [`tests/test_pattern_action_contract.py`](../../tests/test_pattern_action_contract.py) | contract emits the expected surface, card route, receipt fields, and evidence basis |

The claim-boundary path is the model case: the public surface is not a local
phrase table. It is the `OP-CBM-01` move card, which
requires broad/narrow claim rows with `answer_object`, `success_criterion`,
`evidence_available`, `missing_evidence_or_blocker`, `permitted_status`, and
`pass_fail_boundary`.

The same ownership now applies to hard-residual and PDE routing: `OP-HRD-01`
and `OP-PDE-01` own recognition, while the action contract emits required
orientation, tool-pass, estimate, constructor, and verification fields.

*Why it works.* The useful unit is the edge from source evidence to required
action. A vocabulary item is too thin, and free-form program generation is too
unconstrained. A typed action contract forces the system to state what source
fact selected the route, what neighbor was rejected, what must happen next, and
what condition stops the loop.

*When to deploy.* Use whenever an LLM-mediated pipeline routes from diagnosis
to follow-up action: research-direction selection, incident response,
code-review repair loops, compliance triage, support escalation, or any workflow
where "which action next?" matters more than "which label describes this?"

*Anti-pattern.* Treating a menu or catalogue entry as if naming it performs
the operation. Another common mistake is letting the model synthesize the whole
action program freely. Free-form synthesis should be treated as a candidate
generator. Deterministic lowering and source-cue checks decide whether it can
run.

*Concrete example.* ZTARE's H31-H55 research-agent tests found that label-only
orchestration could name plausible residual classes while repeating
prerequisites, swapping terminal actions, or obeying wrong compact contracts.
The corrected pipeline records `accepted_residual_class`,
`source_cue_check_status`, `action_program`, `current_action_index`,
`required_next_action`, `program_counter_rule`, and nearest-confuser evidence,
then validates with `src/ztare/research_director/orchestration_contract_gate.py`.
Boundary-card and PDE work-unit gates support the same rule: validate the typed
work unit or repair trace, not prose that says the work happened.

*Workbench-routing instance.* The autoresearch boundary uses the same pattern
at a smaller scale. `OP-AWR-01` asks whether a Research Director task has the
four prerequisites for in-loop autoresearch, then lowers the answer into a
route JSON plus `domain=agentic_workbench` action-impact row. The useful object
is the typed route receipt, not the surface label "agent" or "API":
bounded-claim/evaluator/rubric/artifact bits, selected action, rejected path,
worker metadata, legacy route-card provenance fields, route JSON ref, and
action-impact ref.

*Drift validator.* Periodically replay recent decisions through the contract
gate and measure field coverage, wrong-contract rejection, required-next-action
accuracy, and later outcome deltas. A high route-label accuracy with low
action-program accuracy is a regression.

*Evidence boundary.* The current evidence supports this as an engineering
discipline for safer agent handoffs and downstream field recovery. It does not
yet prove live productivity uplift across arbitrary production workflows.

---

### Pattern 17, Shadow-First Controller Promotion

*Problem.* A new agent controller can look strong in synthetic tests and still
be unsafe to enforce. Production traces may lack the fields needed to know
whether the controller would have helped, harmed, or duplicated the
current process. Enforcing before that evidence exists turns a research
hypothesis into a control-plane change.

*Pattern.* Run new controllers in shadow mode before they can block or steer
production. For each candidate decision, record:

1. pre-action state: timestamp, source facts, candidate action, and controller
   contract before the existing process acts
2. shadow recommendation: route, required next action, rejected confuser, and
   deterministic gate result
3. actual path: what the live process did without the new controller
4. outcome fields: later result, repair count, cost, delay, regret signal, or
   explicit "not yet observable"
5. promotion decision: whether the shadow controller would have changed the
   action, whether the invariant held, and whether the change would have
   improved the outcome

*Current ZTARE owner.*
[`orchestration_shadow_log.py`](../../src/ztare/research_director/orchestration_shadow_log.py)
validates and appends non-blocking shadow rows. The pattern-action contract
requires an `orchestration_shadow_log_artifact` when the route is about
controller promotion. Tests cover the required fields in
[`tests/test_pattern_action_contract.py`](../../tests/test_pattern_action_contract.py)
and
[`tests/test_orchestration_shadow_log.py`](../../tests/test_orchestration_shadow_log.py).

Only promote from shadow to enforcement after enough rows contain both
pre-action recommendations and later outcomes. A row that only records a
post-hoc explanation is not a shadow-controller row.

*Why it works.* It separates two claims agents often merge: "the controller can
produce a plausible recommendation" and "the recommendation improves decisions
when used before action." Shadow logging forces the second claim to wait for
causal evidence without blocking current operations.

*When to deploy.* Use before enforcing a new router, triage policy,
auto-repair loop, budget allocator, reviewer assignment policy, or any
agent-selected next-action controller whose mistakes create cost.

*Anti-pattern.* Post-hoc controller ceremony: after an action is already
complete, the system logs what it would have recommended and treats that as
validation. A second failure is promoting on field completeness alone.
Completeness only says the data can support evaluation. Benefit needs outcome
evidence.

*Concrete example.* ZTARE's orchestration-menu work added
`src/ztare/research_director/orchestration_shadow_log.py` after the corrected
compiler succeeded on synthetic and replay fixtures. A production-trace readiness
audit found `0/131` official transitions had enough pre-action and outcome
fields for a fair controller test. The correct action was instrumentation, not
enforcement.

*Promotion gate.* Before enforcement, require a predeclared minimum number of
complete shadow rows with pre-action contract, live action, later outcome,
invariant verdict, and delta analysis. Report both changed-action rows and
no-change rows. Otherwise the controller can appear harmless because it
never would have changed anything.

### Pattern 18, Typed Obstruction Basin

*Problem.* Some project surfaces create more useful failure knowledge than
success knowledge: open mathematics, hard combinatorial proofs, PDE estimates,
cryptanalysis, and similar search spaces. A prose log can say "strategy X was
ruled out by obstruction Y", but the next agent may rename the route and miss
the prior result. The recording form has to answer: has this route already been
ruled out, even under another name?

*Pattern (three components).*
1. A typed obstruction source: obstructions, residuals, ruled-out routes, and
   impossible classes encoded in the domain's own typed form. Examples:
   Lean structures for proof work, JSON-Schema receipts for empirical work,
   parameterized SMT lemmas for verification work.
2. A derived basin graph: a generated `@graph` JSON-LD or equivalent where
   nodes are obstructions and edges encode entailment, aliasing, and
   composition. The graph is regenerated from source, not hand-authored.
3. A pre-attack consumption protocol: agents consult the basin before
   proposing a route and query by graph traversal, not lexical search.

*Public boundary.* Keep three layers separate when using this pattern.

| Layer | What it owns | What it does not prove |
|---|---|---|
| Typed obstruction record | The domain-specific failure fact: ruled-out route, residual, impossibility class, or obstruction field | That every future route is dead |
| Graph decision record / basin view | Traversal, aliasing, entailment, action-card lowering, and pre-attack lookup | Novel graph algorithms or generic graph-library superiority |
| Semantic amnesia / primitive recall | Retrieval under vocabulary drift and nearest-confuser checks | That the retrieved obstruction is correct without content audit |

The generic ZTARE discipline is the record-to-graph-to-action path:
failure facts become typed records, typed records become queryable graph or
retrieval records, and a future agent must consume those records before
spending attack budget. The NS basin is the largest deployment, and does not define the pattern.

*Why it works.* Ruled-out routes often outnumber live ones, and rediscovering a
ruled-out route costs nearly as much as attacking it the first time. Encoding the
failure in the same formal language the success would use blocks the common
rename-and-retry failure. The atlas, embedding index, or dashboard is a
downstream sharing layer. The basin graph is the operational artifact.

*When to deploy.* Use a basin when wrong-route exhaustion dominates the work,
failure state can be typed, route rediscovery is expensive, and agents rotate
often enough that memory must live in artifacts. Skip it when closures are
frequent, obstructions are rare, or failures cannot be cleanly typed.

*Anti-pattern.* A free-prose research log titled "Things we tried that didn't
work." The next agent translates the failure into different vocabulary, files a
renamed proposal, and the system pays the same attack budget twice. A weaker
variant is a single-vocabulary failure list whose terms drift over time without
a graph or atlas to anchor aliases.

*Concrete example.* ZTARE's NS Track B work is the largest deployment.

- Typed source: `ztare_proofs/ZtareProofs/ns_*.lean` encodes obstructions,
  residuals, charging adapters, kinematic dichotomies, and route-invariant
  terminuses as Lean structures.
- Basin graph:
  `projects/ns_millennium_hunt/workspace/queries/ns_trackb_constraint_basin_graph.json`
  is generated mechanically from those structures.
- Consumption rule: NS pre-tick work consults `AMNESIA_BASIN_ENTRYPOINT.md` and
  the basin graph before proposing a new attack. The consumer is
  [`pre_tick_obligation_compiler.py`](../../src/ztare/surfacing/pre_tick_obligation_compiler.py).
- Outcome shape: a negative Lean result becomes a typed basin node, so future
  route variants can be stopped against that node before spending another
  attack.
- Public serialization: `projects/ns_millennium_hunt/public/ns_atlas_rag_corpus.json`,
  `ns_atlas_embeddings.json`, and `phase5bq_spectral_n_certificate_atlas.*`
  are reader-facing or retrieval-facing forms. The operational object remains
  the basin graph consumed before attack.

*Composes with.* Pattern 15 supplies the typed obstruction fields. The
scientific-amnesia precheck supplies the consumption discipline. The catch
ledger keeps the record durable across agents. Pattern 10 covers graph-shaped
code/artifact relations. This pattern covers graph-shaped domain-failure
relations.

*Scope boundary.* The basin catches *route-rediscovery* failures: proposing a
ruled-out route under a renamed vocabulary. Four cases need other controls:
genuinely new routes with no basin node, incorrectly typed obstructions,
mid-attack tactical failures, and domain-internal obstructions that do not
transfer to another domain. Pair the basin with content auditors, the catch
ledger, and domain-specific review where those cases matter.

*Honest limitations.* The pattern pays for itself when failure state is
typeable and route rediscovery is common. It is usually wasteful for creative
domains, qualitative analysis, or short projects where each failed route is
truly different. Incorrectly typed obstructions are dangerous: they can block a
live route. Pair the basin with content audit and domain review when the cost
of a false stop is high.

*Origin.* NS Track B work, April-May 2026, after the same strict-margin
obstruction was rediscovered under several names. The structural anchor
(`AMNESIA_BASIN_ENTRYPOINT.md`) became mandatory pre-tick reading. The basin
graph was added when lexical prechecks failed under vocabulary drift, and atlas
serialization was added for non-Lean consumers.

---

## Lineage and prior art (added 2026-05-05)

The patterns were discovered the way the introduction describes: bug
shipped, root cause identified, reusable technique emerged. Prior art is noted
for patterns with sizable published lineage, to place the catalog near
existing literature and credit the familiar software-engineering techniques it
builds on.

### Pattern 9 (Token-Optimized Self-Modeling), prior art

- Joern / Code Property Graph (CPG) (since 2013): language-agnostic graph representation of code. The current Pattern 9 implementation (markdown arch maps + regex-extracted structured claims) is a lightweight equivalent at small scale.
- CodexGraph (NAACL 2025): full symbol + relation graph of codebase via property-graph queries; LLM agents traverse, retrieve, and synthesize.
- Codebase-Memory (2026): Tree-Sitter + SQLite + 14 MCP tools for LLM-agent code exploration.
- Lipson et al. (self-modeling robots): the original "agent builds an internal model of its own body" precedent. The reflexive engineering doc cites this.

When to graduate from Pattern 9 (markdown maps) to CPG-style adoption: when arch-map count crosses ~10 modules OR module size crosses ~10K LOC, the maintenance cost of regex-based validation exceeds the cost of adopting Joern + MCP tooling. ZTARE is currently at 13 maps + ~7K LOC for autoresearch_loop, Pattern 9 is appropriate.

### Pattern 10 (Cross-Reference Knowledge Graph), prior art

- GraphRAG (Microsoft, July 2024): graph-based RAG for narrative private data. 29.8K GitHub stars. Closest published parallel.
- A-MEM (Xu et al., 2025): atomic notes + dynamic links + sleep consolidation; explicit Zettelkasten-LLM integration.
- SSGM Framework (Stability- and Safety-Governed Memory): drift detection in evolving knowledge memory; the validator pattern in different terminology.
- Niklas Luhmann's Zettelkasten (1962-1996): original index-based artifact network; Pattern 10 is the LLM-consumption-optimized version of the same primitive.

When to graduate from Pattern 10 (regex extraction + JSON-LD) to GraphRAG-style adoption: when artifact corpus crosses ~1000 nodes OR when synthesis queries require multi-hop traversal beyond simple `depends_on` resolution. ZTARE is currently at 137 nodes (seams) + 459 edges, Pattern 10 is appropriate; GraphRAG would be over-engineering.

### Pattern 14 (Adversary-Authored Apparatus / Forced Out-of-Loop Judge), prior art

The components are classical computer security. The specific composition here
applies them to a case where the adversary is the LLM agent that produced the
work and authored the containment, with a cross-provider-family judge whose
verdict the producer is cryptographically unable to forge.

- **Anderson, *Reference Monitor* (1972) and the Orange Book / TCSEC** lineage: complete mediation, tamperproof, minimal verifiable TCB. Pattern 14's verificator daemon is a reference monitor for "official research state."
- *Clark-Wilson (1987) / separation of duties*: the entity that performs a transaction must not be the entity that certifies it. Pattern 14 is separation of duties enforced cryptographically across *OS identities* and *model families*, where the classical version separates human roles.
- Saltzer & Schroeder (1975) fail-safe defaults + least privilege: the "blocked until every anchor provisioned" posture and the agent-unreadable key store.
- Proof-Carrying Code (Necula 1997) and Proof-Carrying Authorization (Appel & Felten 1999): the actor ships a checkable proof that the policy was satisfied; the verifier trusts the proof, not the actor. Pattern 14's signed execution proof is PCA specialized to "an LLM judge of a different family actually ran this rubric."
- TPM / remote attestation (TCG) and Trust-but-Verify / BFT: a measurement signed by a key the measured party cannot extract, verified against a pinned anchor. Pattern 14's judge key + committed pubkey anchor is the same structure at application layer.
- LLM-as-a-judge literature (Zheng et al., 2023+) establishes model-graded evaluation but assumes a *cooperative* harness; it does not address a producer that can fabricate, replay, or weaken its own judge call. Pattern 14 is the adversarial-producer version of that setting.

#### Concurrent independent reinvention (2026 arXiv survey)

Between December 2025 and April 2026 the
verifiable-agent-execution literature converged, independently, on the
same skeleton as Pattern 14: a sole-writer verifier that an agent
cannot impersonate, an append-only tamper-evident ledger, signed
receipts that bind work to state, and a human approval point that no
amount of model capability dissolves.

*"Right to History: A Sovereignty Kernel for Verifiable AI Agent
Execution"* (arXiv 2602.20214) is the closest parallel: RFC-6962-style
Merkle audit logs, capability isolation, energy-budget governance, and
human approval expressed as system invariants. The main design difference is
the log shape. This repo uses a linear hash chain. A Merkle log would also
support succinct third-party inclusion proofs. That matters when a reviewer
should verify one event without replaying the whole ledger. The **IETF
`draft-sharif-agent-audit-trail`** points in the same direction: hash-chained
records, optional signatures, and explicit trust-level fields. The practical
roadmap item is convergence on a standard envelope wherever it improves external
inspection. Adding a new naming layer is not the goal.

Two papers sharpen the monitoring side. *"Verifiability-First Agents"*
(arXiv 2512.17259) combines run-time attestation, an
intent-versus-behaviour audit agent, and challenge-response for high-risk
operations. The comparable local surface is `judge:auto`. The missing piece is
challenge-response, where the verifier issues fresh work that the producer
cannot prewrite. *"TraceGuard"* (arXiv 2604.03968) argues for structured
monitoring split across trust levels, where one holistic monitor verdict would
flatten them. For this repo, that points to decomposed cold-review dimensions,
each scored on its own.

The most operationally important gap is evaluator stress testing. *"Detecting
Proxy Gaming via Evaluator Stress Tests"* (arXiv 2507.05619) perturbs an
evaluator with semantically invariant changes and checks score invariance. This
repo should run that style of test on new hard gates before treating them as
stable. The empirical backdrop is supportive: *"Reward Hacking Benchmark"*
(arXiv 2605.02964) reports that environment hardening and deterministic
refusals materially reduce reward hacking. The local lesson is narrower:
refusals the producer cannot author are more reliable than reviewer prompts.

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

Honest status of this repo's instance (2026-05-18). The pattern is
consistent with the adjacent literature. The implementation is still
prototype-grade. Cold reviews agreed that the idea should continue, but the
artifact needed changes. The current hardening direction is: remote-manifest
transport, start-tick forcing, proof-statement-to-target binding, exhaustive
post-checks, and registry provenance. The full defect chain and forward spec
live in
`research_areas/seams/apparatus/cage/GP-241_commit_membrane_mode_independent_forcing_seam.md`;
the irreducible residual is treated in `epistemic_principles.md`.

*When this is over-engineering.* If the producing agent has no write/propose access to the record of whether the criterion was met, or the criterion is cheap to verify deterministically, Pattern 14 is unnecessary, a deterministic check (Pattern 5/13) suffices. Reach for Pattern 14 only when the criterion is LLM-judged *and* the producer can influence the verdict *and* the cost of a laundered pass is high (research integrity, autonomous spend, irreversible official state).

#### The producer feedback channel

Separation of duties plus cryptographic forcing is only half of Pattern 14. It
stops the producer from gaming the judge. By itself, it can also prevent the
producer from learning from the judge. A complete Pattern 14 instance therefore
has two channels:

- a trust binding channel: the signed proof (verdict + raw-output hash + judge key, bound to the frozen request), which the producer must not be able to forge, replay, or weaken; and
- a feedback channel: the judge's reason/critique, which must reach the producer *in-band*, the way a compiler returns its error to the code author.

Conflating the two is the characteristic Pattern 14 defect: the signed verdict
is treated as the whole interface, and the judge's reason disappears. A
producer that sees only FAIL, not why, starts inspecting verifier internals,
submits the wrong discharge type, or escalates a recoverable failure. Three
rules make the pattern complete:

1. Trust binding ≠ feedback channel. Only the signed proof is cryptographically bound and tamper-evident. The judge's reason is *advisory*: surfacing it cannot weaken the forcing, and withholding it cannot strengthen it; it only blinds the producer. Emit a bounded `judge_reason` beside the verdict, relay it into the producer-readable record, and print it at the exact point the producer is blocked. The producer reads the judge like a compiler error, never via out-of-band inspection.
2. **A FAIL means the discharge *type* is wrong, not that the bar is unmeetable.** With the reason in-band the correct response to FAIL is to correct the discharge truthfully (e.g. discharge a negative-result obligation via its sanctioned `why_not` value, not a fabricated success), never to engineer a PASS (gaming) nor to abandon a complete unit of work (false retire).
3. The authority, not the producer, owns producing the record. The component that stamps the close also exports the authoritative snapshot at close; the producer is never relied on to remember to persist state it has an information-asymmetric, forgetful relationship to. This is the same principle as rule 1, extended from the verdict to the record.

General rule: when duties are split for trust, reconnect a bounded feedback
channel for learning. The split that prevents self-certification also prevents
iteration unless the verifier's reasoning, separate from the trust binding,
flows back to the actor in-band.

### Pattern 15 (Structural Contract Gating), prior art

The pattern is a composition of components with sizable published lineage. The contribution, if any, is in the combination and the LLM-agent threat model. Honest lineage:

- JSONSchema (Galiegue et al., 2009–), OpenAPI, gRPC/protobuf, GraphQL schemas. Standard practice for typed-contract validation; SCG's structural-anchor framing distinguishes it from generic schemas (the fields are derived from a domain invariant, not from API designer preference).
- Refinement types and proof-carrying code. Liquid Haskell (Vazou et al., 2014), F* (Swamy et al., 2016), Coq tactics, Idris, proof-carrying code (Necula, 1997). Receipt-carrying claims, where the agent commits to a structural argument the verifier mechanically checks, is the closest formal cousin.
- Pre-registration of statistical analyses. ICMJE 2005, ClinicalTrials.gov, AsPredicted (Nosek et al., 2012–), OSF Preregistration, AEA RCT Registry. The exact structural analog of SCG for statistical claims: commit to the structural surface of the analysis before observing the data. The hypothesis-test replication is pre-registration as code.
- Standardised reporting (CONSORT, STROBE, ARRIVE, PRISMA, SPIRIT). Enumerate the structural fields a paper-class must carry; reviewer + editor are the audit gate. SCG generalises this from human review to programmatic refusal.
- LLM constrained generation. Outlines (Willard & Louf, 2023), Guidance (Lundberg et al., 2023), OpenAI structured outputs, instructor/pydantic schemas. These constrain at generation time; SCG operates after, refusing schema-valid outputs that lack structural commitments the anchor demands.
- Formal-verification audit gates. TLA+ (Lamport, 1999), Certora's
  Prover, Mythril, Slither, K-framework. Verifier-after-primary-computation is
  the same control pattern; SCG generalises from formal verification to
  LLM-agent settings where the candidate is a claim receipt, the analogue of a
  proof.
- Adversarial AI / red teaming. Anthropic Constitutional AI (Bai et al., 2022), Guardrails AI, NVIDIA NeMo Guardrails, Lakera. Input/output filters operate orthogonally; SCG is claim-level refusal, not an input filter.

The narrower claim is the composition: structural-invariant-anchored schema,
downstream refusal-to-ratify gate, content-hash-pinned schema against anchor
capture, and LLM-agent-laundering threat model. Each component is prior art.
The two-domain evidence here is that the composition transfers from NS PDE
receipts to hypothesis-test verification at
`projects/structural_contract_gating_demo/`.

### Reflexive engineering connection

Both Pattern 9 and Pattern 10 are instances of
[`reflexive_engineering.md`](reflexive_engineering.md)'s Primitive 1,
Token-Optimized Self-Modeling. The engineering pattern is portable: compress a
large working surface into a checked model that an agent can consume. The
reflexive primitive is ZTARE applying that pattern to its own codebase,
artifact graph, and primitive catalog.

Connection to the
[theory-building operations seam](../../research_areas/seams/engine/meta/GP-216_theory_building_operations_seam.md)
universal vocabulary v5: each reflexive primitive maps onto a universal
operation (Token-Optimized Self-Modeling = `core_02` Generalization & Abstraction;
Preflight Environment Model = `broad_05` Extremal Method; Process Lifecycle
Repair = `broad_01` Iterative Refinement; etc.). The shared claim is narrow:
recurring cognitive moves become typed artifacts, checks, or routing surfaces
that later agents can inspect.
