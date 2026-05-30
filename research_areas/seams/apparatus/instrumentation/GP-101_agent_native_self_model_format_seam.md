# GP-101 — Agent-Native Self-Model Format: What Representation Minimizes Agent Error Rate?

> **Seam metadata** · `seam_id:` GP-101 · `track:` apparatus · `status:` open - opened 2026-04-19 · `last_updated:` 2026-05-09


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-04-19

## ID

GP-101

## Eigenquestion

What representation format for token-optimized self-models minimizes agent error rate per token of self-model consumed, and how do we measure that?

## Problem Statement

GP-100 produced the first token-optimized self-model (`autoresearch_loop_architectural_map.md`). The v1 map was rewritten to be more agent-native (structured blocks, dependency chains, edit-intent lookup tables, assertion-shaped invariants) but the optimal format is not settled.

The tension: human-readable prose is wasteful (narrative structure, explanatory paragraphs the agent doesn't need) but structured formats (pure YAML/JSON) may lose relational information that prose encodes implicitly (e.g., "this trap exists BECAUSE of this historical incident"). The agent needs to know what breaks — it doesn't need to know why the system was designed this way, UNLESS the "why" predicts which edits are dangerous.

### Candidate formats

1. **Structured blocks** (current v2): markdown with code-fenced pseudo-schemas. Pipeline as typed dependency chain. Invariants as assert/check/why/trap blocks. Edit lookup table.
2. **Pure YAML/JSON schema**: machine-parseable, zero prose, maximum information density per token. Risk: loses relational/causal links between components.
3. **Precondition/postcondition contracts**: each phase defined as `{pre: [...], post: [...], side_effects: [...]}`. Closest to formal verification.
4. **Hybrid prose+schema**: short prose summaries with embedded structured data. May be worst of both — partial narrative overhead without full structure.
5. **Executable assertions**: a test file that imports the module and asserts structural properties (function exists, signature matches, etc.). Self-verifying against drift.

### Why this matters

If token-optimized self-modeling is a real methodological primitive (see `research_areas/private/philosophy/token_optimized_self_modeling.md`), the format question becomes decisive. A wrong format choice either wastes tokens (too verbose) or causes errors (too compressed, loses critical relationships). The first instance (autoresearch_loop) is the test case — if the format doesn't prevent the class of errors that motivated it (partial-view pipeline ordering mistakes), it failed.

## Scope

**Covers:**
- Format comparison: prose vs structured vs YAML vs contracts vs executable
- How to measure "agent error rate per token consumed"
- Whether the optimal format differs by file type (pipeline file vs library vs config)
- Whether causal/historical context ("why this exists") has measurable value for error prevention
- Maintenance cost: which format drifts least as the source file evolves

**Does not cover:**
- Whether to build self-models (decided: yes, see philosophy doc)
- Which files need self-models (criteria in philosophy doc)
- Content of specific self-models (per-file decision)

## Debaters

- **Munger** (Charlie Munger persona): Inversion, anti-complexity, "what would make this harmful?"
- **Dijkstra** (Edsger Dijkstra persona): Formal methods, precondition/postcondition, "can the machine verify this?"
- **Knuth** (Donald Knuth persona): Literate programming, documentation as literature, "the human and the machine read the same artifact"
- **Norvig** (Peter Norvig persona): Pragmatic AI, empirical testing, "measure it, don't argue about it"

## Open Questions for Debate

**Q1: Does causal context prevent errors or waste tokens?**
The "why" line in each invariant block (e.g., "python_code is scaffold for substitute_fitted_params; GP-035 runs AFTER") — does an agent that reads this make fewer errors than one that reads only the assertion? Or does the causal context consume tokens that could be spent reading more of the actual source?

**Q2: Should the format be self-verifying?**
An executable test file (`test_self_model.py`) could import `autoresearch_loop` and assert structural properties (function signatures, pipeline ordering via AST analysis). This catches drift automatically. But it's a second artifact to maintain.

**Q3: Is the edit-intent lookup table the highest-value section?**
The "I want to change X → read Y first" table directly maps to the failure mode (agent edits X without reading Y). If this section prevents 80% of errors, perhaps the rest of the self-model is low-value overhead.

**Q4: Does the optimal format differ by file type?**
A pipeline file (autoresearch_loop) has ordering contracts. A library file (fit_primitive.py) has API contracts. A config file (rubric JSON) has flag-to-behavior mappings. Should each have a different self-model format?

**Q5: How do we measure success?**
The only honest metric is "did the agent make a partial-view mistake after reading the self-model?" This requires either (a) tracking errors across future sessions, or (b) synthetic testing — give an agent a change task on the file, with and without the self-model, and compare error rates. Is synthetic testing valid or does it just measure the synthetic task?

---

## Debate

### Turn 1 — 2026-04-19

#### Munger

Start by inverting the question: what would make a self-model actively harmful? Two things. First, staleness — the agent trusts the map over the territory and introduces a bug the map said was impossible. Second, complexity creep — the self-model becomes a second codebase that requires its own self-model, and now you have infinite recursion of bureaucracy. Both pathologies point toward the same answer: pick the simplest format that prevents the demonstrated failure class and nothing more.

On Q1, causal context is a luxury. The agent does not need to know that INV-1 exists "because GP-035 runs after." It needs to know: do not delete the python block before fit runs. The "why" line is a nice-to-have that costs tokens on every single read. If you must keep it, make it one clause, not a sentence.

On Q3, the edit-intent lookup table is the 80/20 section. Look at the actual failure that motivated this entire exercise: agent edited X without reading Y. The lookup table is a direct patch for that exact failure. Everything else — the region index, the state variables, the rubric flags table — is supplementary. If I had to ship one section and throw away the rest, it would be the lookup table plus the invariants list. Two sections. Done.

On Q5, do not build an elaborate measurement apparatus. Count the mistakes. You already have a track record of sessions where agents broke things. Compare the rate before the self-model to the rate after. If you cannot count, the problem is not important enough to solve.

#### Dijkstra

The question of format is, at its core, a question of verifiability. A representation is good if and only if its correctness can be mechanically checked. Prose fails this test categorically — no machine can verify that a prose description accurately reflects the program it describes. YAML fails for a different reason: it encodes structure but not contracts. What remains are precondition/postcondition specifications and executable assertions.

On Q2, the self-model MUST be self-verifying. A non-verified self-model is a comment, and we know what happens to comments — they rot. The `test_self_model.py` approach is not overhead; it is the minimum viable integrity guarantee. Without it, you are asking future agents to trust an artifact that has no obligation to remain truthful. The "second artifact to maintain" objection is specious: the test IS the self-model. The markdown version is the human-readable rendering of it. If you can only have one, keep the test.

On Q1, the causal "why" line is precisely the kind of informal annotation that drifts. Replace it with a formal dependency declaration: `substitute_fitted_params REQUIRES python_code != None`. This is checkable. "GP-035 runs AFTER" is a historical note that tells you nothing a dependency graph does not already encode. Remove it.

On Q4, the format should NOT differ by file type. The contract language — preconditions, postconditions, side effects — is universal. A pipeline file has ordering preconditions. A library file has signature preconditions. A config file has value-range preconditions. The vocabulary is identical. Different formats per file type is an invitation to ad hoc inconsistency.

#### Knuth

I must object to both of my colleagues' implicit assumption that the machine is the only reader. The `autoresearch_loop_architectural_map.md` will be read by the principal, by future collaborators, and by the agent. If the format is pure YAML or a test file, the human must reverse-engineer intent from structure. This is the literate programming objection: the artifact should be readable as a document AND executable as a specification. They are not in tension if you design the format correctly.

On Q1, the "why" line is not luxury — it is the decisive pedagogical link. Consider INV-3: "deterministic f() is the Odrzywolek Inversion contract." Without that clause, an agent or human who encounters the assertion knows WHAT is forbidden but not WHY it is forbidden, and therefore cannot reason about edge cases the assertion does not cover. The causal context is how you generalize from specific invariants to the design philosophy. Strip it and you get a checklist that handles known cases but cannot handle novel ones.

On Q3, the edit-intent lookup table is high-value but not sufficient. It answers "where to look" but not "what to preserve." The invariants section answers the latter. They are complementary, not ranked. The table without invariants is a map without a legend.

On Q4, I agree with Dijkstra that the contract vocabulary is universal, but the PRESENTATION should differ. A pipeline file's self-model reads as a sequential narrative of phases. A library file's self-model reads as an API reference. Forcing both into the same visual layout sacrifices comprehension for consistency. The underlying logic (pre/post/side-effects) can be uniform while the rendering adapts.

#### Norvig

Everyone is arguing philosophy. Let me propose an experiment. Take the five candidate formats from the seam. For each, produce a self-model of `autoresearch_loop.py`. Then construct 10 change-tasks that historically caused partial-view errors (you have the git history — mine it). Give each self-model + the change-task to an agent in a fresh session with no prior context. Measure: (a) did the agent read the right regions before editing, (b) did the edit preserve invariants, (c) token cost of the self-model. Plot error rate against token cost. Pick the Pareto-optimal format. This is Q5 answered directly.

On Q1, this is empirically testable. Run the same 10 tasks with the "why" lines and without. If the error rate is statistically indistinguishable, strip them. If the "why" lines prevent even one novel error the assertions alone missed, keep them. My prior: the "why" lines help on novel tasks but not on tasks the assertions directly cover. This means the answer depends on your task distribution — are future edits mostly known-pattern or novel? If mostly known-pattern, strip for token savings. If novel, keep.

On Q2, a `test_self_model.py` is valuable but solves a different problem — drift detection, not error prevention. The self-model prevents agent mistakes; the test prevents self-model rot. Both are needed but they are separate interventions. Do not conflate them.

On Q5, synthetic testing IS valid if the synthetic tasks are drawn from the real error distribution. If you make up tasks, you measure the made-up distribution. If you replay actual historical mistakes (with the fix reverted), you measure the real thing. The experiment design matters more than the philosophy of measurement. Use historical replay, not synthetic invention.

---

### Turn 2 — 2026-04-19

#### Munger

Knuth says the "why" line helps the agent generalize to novel cases. I will concede a narrow version of this: if the why-clause is one predicate — "BECAUSE fit runs after extraction" — it earns its tokens. If it is a history lesson — "this was introduced in GP-035 when we discovered that the Odrzywolek Inversion required deterministic parameters" — it does not. The test is: does the clause change what the agent does on the next edit? If yes, keep it. If it only changes what the agent understands, cut it. Understanding without action is overhead in a token-constrained system.

Norvig's experiment is the right answer to Q5. I endorse it with one caveat: do not wait for statistical significance across 50 runs. You have maybe 5-10 real historical mistakes. Run those. If the lookup table alone catches 8 of 10, you know what the high-value section is. Perfect is the enemy of good, and statistical rigor is the enemy of shipping.

On Dijkstra's point about the test being the self-model: this is elegant but impractical. A test file that asserts `substitute_fitted_params` requires `python_code != None` tells the agent the precondition but not where in the 4100-line file to find the relevant code. The self-model's value is partly spatial — "lines 3070-3175" — which a test file does not encode. You need both the map and the verifier. Two artifacts, minimal each.

#### Dijkstra

I accept Munger's correction on spatial information — a test file does not encode "where to look," and this is decisive for an agent that navigates by line number. The self-model therefore has two irreducible components: a structural map (regions, line ranges) and a contract specification (pre/post/invariants). The test file verifies the contracts have not drifted. Three artifacts, not two: map, contracts, test. But each is minimal and formally scoped.

On Q1, I will meet Knuth halfway. The causal clause is acceptable if it is formalized as a dependency edge, not prose. "INV-3 DEPENDS_ON: Odrzywolek Inversion contract (fit_primitive.py)" is a typed link. "This is the Odrzywolek Inversion contract" is a comment. The former can be traversed programmatically. The latter cannot. If we agree that all causal context must be expressible as typed dependency edges, I withdraw my objection to including it.

On Q4, I maintain format uniformity. Knuth wants different "presentations" with uniform "logic." But presentation IS the format under debate. If the rendering differs, agents consuming the self-model encounter different structures per file type and must learn multiple parsing strategies. This is precisely the ad hoc inconsistency I warned about. One format. One parser. One verification strategy.

#### Knuth

Dijkstra's typed-dependency-edge proposal is a reasonable compromise on Q1. I accept that "INV-3 DEPENDS_ON: odrzywolek_inversion_contract" is superior to a prose sentence, provided the dependency target is itself a readable artifact. If the edge points to a node that has its own description, the pedagogical chain is preserved without inline prose. This is, in fact, the literate programming solution: the text is woven from typed references, each of which can be followed to its definition.

On Q4, I will concede to Dijkstra on format uniformity with one condition: the single format must include a "topology" field that declares whether the file's primary structure is sequential (pipeline), hierarchical (library), or tabular (config). This is metadata about the self-model, not a different format. The agent reads the topology field and knows whether to interpret the dependency chain as "must execute in order" or "may call in any combination." Without this, a uniform format loses information that the separate presentations encoded implicitly.

On Q5, I support Norvig's historical-replay experiment. I add one requirement: the experiment must also test whether the agent can UPDATE the self-model correctly after making a change. A format that prevents read-errors but causes write-errors (the agent cannot maintain it) will rot faster than the code it describes. Maintenance cost is the hidden variable.

#### Norvig

Good convergence. Let me synthesize. On Q1, the panel has converged on: keep causal context, but formalize it as typed dependency edges rather than prose. Measurable via the historical-replay experiment — run with and without the edges and compare error rates. On Q2, consensus that drift-detection (test file) and error-prevention (self-model) are separate but both needed. On Q3, the lookup table is highest-value but insufficient alone — invariants are the necessary complement. On Q4, single format with a topology metadata field. On Q5, historical-replay experiment using real git-history mistakes, not synthetic tasks.

The one remaining disagreement is Munger's "ship with 5 data points" versus my preference for a structured experiment. I will concede practically: run the 5-10 historical replays first. If the signal is overwhelming (8/10 errors prevented by lookup table + invariants alone), ship that format and iterate. If the signal is ambiguous, expand the test set with carefully constructed synthetic tasks that match the real error distribution. This is sequential testing, not premature rigor.

The maintenance-cost variable Knuth raised is important and undertested. Add it to the experiment: after each change-task, ask the agent to update the self-model. Measure how often the update introduces a factual error into the model itself. Format A might prevent code-editing errors but generate self-model-editing errors. The format that minimizes the sum of both is the winner.

---

### Convergence Summary — 2026-04-19

**Points of agreement:**

1. **Q1 resolved:** Causal context should be kept but formalized as typed dependency edges (`DEPENDS_ON: <target>`), not prose sentences. Edges are traversable, verifiable, and token-efficient. Prose "why" lines should be converted to this format.

2. **Q2 resolved:** The self-model (error prevention) and a test file (drift detection) are complementary, not competing. Both are needed. The test file verifies that contracts in the self-model still match the source code.

3. **Q3 resolved:** The edit-intent lookup table is the highest-value single section, but invariants are the necessary complement. The minimum viable self-model is: lookup table + invariant contracts. Region index and state variables are supplementary.

4. **Q5 resolved:** Historical-replay experiment using real mistakes from git history. Sequential testing: run 5-10 replays first; expand if signal is ambiguous. Maintenance cost (agent's ability to correctly update the self-model) must be measured alongside read-error prevention.

**Remaining disagreements:**

1. **Q4 unresolved:** Dijkstra wants strict format uniformity across all file types. Knuth accepts uniformity but requires a `topology` metadata field (sequential / hierarchical / tabular) to preserve structural semantics. Munger is indifferent — he would ship whichever version passes the 5-case test. Norvig would A/B test both approaches. **Resolution path:** include the topology field in v2 and measure whether agents use it. If they ignore it, remove it.

2. **Artifact count:** Dijkstra wants three artifacts (map, contracts, test). Munger wants two (map with inline contracts, test). Knuth wants one (literate document that is both map and contracts, plus a test). **Resolution path:** start with Munger's two-artifact version (lowest maintenance cost), add the test file, measure drift rate. If contracts need to separate from the map for verification reasons, split then.

---

## 2026-04-23 Continuation — Executable Validator (Option 5 shipped)

**Triggering event:** principal observed (correctly) that today's autoresearch_loop edits (GP-133 R4 rubric-preflight gates) were NOT checked against `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` ex-ante nor ex-post. The map drifts silently when edits happen without validator enforcement — the exact failure mode Option 5 was scoped to prevent.

**Ask:** introduce formal validator code that (a) agents must run before editing `autoresearch_loop.py`, (b) verifies the edit didn't break the map ex-post. Continuation of this seam.

### What ships

**`scripts/public/validators/validate_autoresearch_arch_map.py`** (see Task #38) — executable validator that reads `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` and asserts claims against live source. Two modes:

1. `ex-ante` — read the map before starting an edit. Confirms claimed regions, functions, exits still exist at claimed line ranges. Output: drifted claims to read first.
2. `ex-post` — after edit. Pass iff (a) no new drift OR (b) editor also updated the map. Drift = map claims region at line X-Y but source no longer matches.

### Assertions codified

- Region line ranges (±30 tolerance, matches map's self-stated drift disclaimer)
- Named functions exist at approximate line numbers
- Exit taxonomy — each claimed exit (R1_*, R3_*, subprocess_crash, UNDERIDENTIFIED, budget_exhausted, GP133_R4_gate) has matching `raise`/`break` site
- Invariants INV-N — each has associated source-side assertion or tagged comment

### Enforcement

- Pre-commit git hook runs `ex-post` on commits touching `autoresearch_loop.py`. Drift > threshold blocks commit.
- AGENTS.md rule added: before any edit to autoresearch_loop.py, run `ex-ante`; after, run `ex-post` and update map if drift introduced.

### Known limitations

- Syntactic only; cannot detect semantic drift (region at right line with different behavior). Semantic validation requires per-region smoke tests — deferred.
- Historical-replay corpus (Knuth Round 1) still deferred.

### Status

Continuation → ACTIVE. Seam remains OPEN until validator runs in CI and has prevented ≥1 drift-commit.
