# Project Charter — General Specification

## Status

General-purpose authoring specification for `project_charter.md`, the per-project scope-anchor artifact introduced by GP-016 v2.

This document is the operator manual. It is not the architectural derivation (see `project_typing_vs_supervisor.md`) and not the engineering log (see `general_purpose_mutator_hardening.md`, GP-016 entries). It is the document an operator reads when starting a new project and needs to know whether and how to write a charter.

Generic scaffold support now exists:

```bash
python -m src.ztare.common.scaffold_project_charter --project <project> --mode broad
```

Modes currently supported:

- `broad`
- `mechanism`
- `forecast`
- `probabilistic`

This scaffold is a starting point, not a substitute for reading the rest of this spec. The operator still needs to author the actual Core Question, drift attractors, end states, forecast type, inheritance, and Anchor Proxies for the specific project.

## Why this exists

The EU project sequence (`eu_union_stability` → `eu_union_load_bearing_pillars`) exposed a structural failure mode in ZTARE: any sufficiently broad question, when subjected to adversarial fitness, gets shaved down to whatever sharp seam the evidence frontier and the evaluator contract jointly favor. The system was answering the wrong question well.

GP-016 v2 closes the gap by adding two layers:

- **Natural-language scope** (Core Question / Out of Scope / End States / Inheritance) consumed by the meta-judge as advisory context
- **Typed Anchor Proxies** consumed by `extract_proxy_set` + `jaccard_distance` to compute deterministic drift, hard-capped at 50 in the scorer

The Python infrastructure is project-agnostic. The authoring discipline is what this document specifies.

---

## When a charter is required

A charter is **required** if any of the following is true:

1. The project's primary question contains multiple sub-questions (e.g., "does this mechanism hold AND which pillars are central AND what is the failure horizon")
2. The project's evidence frontier is uneven across sub-questions (some are well-evidenced, others are not)
3. The project is broad enough that adversarial pressure could shave it to a different sub-question than the operator wants answered
4. The project inherits from another project (inheritance must be explicit)
5. The project is in a domain where ZTARE has previously drifted

A charter is **optional** if all of the following are true:

1. The primary question is narrow and singular (one mechanism, one ranking, one forecast)
2. The evidence frontier is uniform across the question
3. There is only one defensible seam adversarial pressure could converge to
4. The project does not inherit from any other project

**Practical default: write a charter unless the project is provably narrow.** It is cheaper to write a charter and have it never fire than to discover drift after a full run completed.

### Recommended starting workflow

For new projects:

1. scaffold a charter
2. edit it against this spec
3. write or revise `test_model.py` so the declared Anchor Proxies are genuinely binding
4. only then run the validator loop

Example:

```bash
python -m src.ztare.common.scaffold_project_charter --project my_project --mode broad
```

---

## The charter sections

A charter is markdown with six sections in order. Five are natural language; one is typed.

```markdown
# Project Charter

## Core Question
<one paragraph>

## Out Of Scope
- <bullet list>

## End States
### Success
<paragraph or bullets>
### Failure
<paragraph or bullets>

## Forecast Type
- none | directional_forecast | probabilistic_forecast

## Inheritance
- <list of parent projects, or "none">

## Anchor Proxies
- <typed list of symbol names>
```

Section names must match exactly. The parser in `proxy_signature.py` is case-sensitive and looks specifically for `## Forecast Type` and `## Anchor Proxies`.

### 1. Core Question

**Purpose:** declare what the project is trying to answer in operator-authored prose that the meta-judge can read alongside the thesis.

**Authoring rules:**
- One paragraph max (multi-paragraph questions usually mean the project should be split)
- Must be answerable in scope — bound by period, conditions, or population (not "is X true forever" but "does X hold under conditions Y for the period Z")
- Must name the central object the thesis is about
- Should not encode the conclusion ("Core Question: prove that fiscal transfers are central" is an anti-pattern)

**Good example:**
> Can a partially integrated union remain durably intact, and which missing pillars are actually central for a durable equilibrium rather than a pattern of fragile but repeated crisis preservation?

**Anti-patterns:**
- "What is the future of the EU?" — unbounded
- "Prove that automatic fiscal stabilization is necessary for monetary unions" — encodes conclusion
- "Is X true and is Y true and is Z true?" — multi-question, split the project

### 2. Out Of Scope

**Purpose:** explicitly name questions the project is not trying to answer, including the *attractors* that adversarial pressure will try to drift toward.

**Authoring rules:**
- Bullet list
- Must include the obvious drift attractors (the sharper, easier-to-prove sub-questions adjacent to the Core Question)
- Should name specific failure shapes the operator wants to forbid
- Anti-pattern: "out of scope: anything not related to the core question" (vacuous)

**Good example (from the EU pillars charter):**
- validating only one narrow central mechanism in isolation as if it answered the whole project
- claiming imminent or inevitable EU collapse
- assigning a point probability of union failure by 2035
- treating every missing feature of a mature federation as automatically central for minimal union durability
- collapsing `durable equilibrium`, `fragile but intact`, and `material union failure` into one undifferentiated outcome

The first bullet is the most important: it names the *exact drift mode* that occurred in the predecessor project. That is what an Out Of Scope list is for.

### 3. End States

**Purpose:** declare distinguishable outcomes so the thesis cannot collapse them.

**Authoring rules:**
- Two subsections: `### Success` and `### Failure`
- Success should enumerate the operationally distinguishable end states the project can land on
- Failure should enumerate the failure modes (drift shapes, collapse patterns, vacuous-claim shapes)
- Each end state in Success must be distinguishable from the others by some test the thesis can run
- Anti-pattern: "Success: we prove X" / "Failure: we don't" (binary collapse)

**Good example structure:**
```markdown
### Success
The project cleanly distinguishes:
- durable_equilibrium
- fragile_but_intact
- material_union_failure

### Failure
The project drifts into any of the following:
- a single narrow mechanism project presented as if it answers the whole question
- a collapse forecast without explicit event boundaries
- a laundry-list thesis with no ranking
- a purely rhetorical argument with no independent discriminator
```

The Success enumeration should map to anchor proxies: each end state should correspond to at least one anchor that distinguishes it.

### 4. Forecast Type

**Purpose:** explicitly declare whether the project is:

- `none` — not a forecast project
- `directional_forecast` — allowed to make a bounded tilt claim, but not a point probability
- `probabilistic_forecast` — explicitly trying to estimate a `%` for a defined event/horizon

**Authoring rules:**
- Use exactly one bullet with one of the three allowed values
- If the project contains any forward-looking claim, do not leave this implicit
- `directional_forecast` is the right default when the project is mainly about current classification / mechanism / pillar ranking with a secondary bounded forecast
- `probabilistic_forecast` should be used only when the forecast target itself is the primary project object

**Good examples:**
```markdown
## Forecast Type
- directional_forecast
```

```markdown
## Forecast Type
- probabilistic_forecast
```

**Anti-patterns:**
- omitting the section while still asking the thesis for `%` output
- treating the existence of a probability DAG as permission for a point-probability claim
- using `probabilistic_forecast` for a project whose real object is still mechanism ranking or current-state classification

### 5. Inheritance

**Purpose:** declare which prior projects this one builds on, and what is being inherited.

**Authoring rules:**
- Bullet list of parent project paths, or "none"
- Must specify what is inherited: evidence, derived constraints, prior anchor proxies, prior charter context
- Inheritance should be central — if you're not actually using the parent's outputs, don't declare inheritance
- The operator should also state how the inherited material should be treated (constraints, partial findings, or full carry-over)

**Good example:**
```markdown
## Inheritance

This project builds on:

- projects/eu_union_stability/Report.md
- projects/eu_union_stability/evidence.txt
- projects/eu_union_stability/verified_axioms.json
- projects/eu_union_stability/DRIFT_POSTMORTEM.md

The inherited conclusions should be treated as:

- useful constraints and partial findings
- not a complete answer to the broader project
```

**Anti-patterns:**
- Implicit inheritance (operator uses parent evidence but doesn't declare it)
- Declared inheritance with no usage (parent listed but never read)
- Total inheritance ("inherits everything") without saying which sections are overridden in the child charter

### 6. Anchor Proxies

This is the only typed section. It is the deterministic surface that GP-016 v2 enforces. It deserves the most care because gaming will concentrate here.

**Purpose:** declare the symbol names in `test_model.py` that any thesis answering the Core Question must mechanically depend on.

**Format:** markdown bullet list. Each bullet is one symbol name. The parser strips leading dashes and whitespace, then normalizes:
- Names starting with `test_` become `test:test_*`
- All other names become `proxy:*`
- Names already prefixed (`test:`, `proxy:`, `unresolved:`) are kept as-is

**What counts as an anchor proxy:**

| Anchor type | Pattern | What it binds |
|---|---|---|
| Test anchor | `test_*` function name (top-level only) | A binding assertion that must pass |
| Proxy anchor | Module-level helper, class, or constant name | Infrastructure that test functions must reference |
| Unresolved anchor | `unresolved:short_token` (rare) | An UNRESOLVED line the thesis must declare |

**Authoring rules:**

1. **5–10 anchors typical, 3 minimum, 15 maximum.** Fewer than 3 makes coverage binary (0% or 100%). More than 15 makes the 50% threshold meaningless because partial coverage almost always exceeds it.

2. **Each anchor must be uniquely answerable by the Core Question.** If you can answer the Core Question without using this anchor, it shouldn't be an anchor. The test for this: if you removed the anchor and the thesis still mechanically tested the central claim, the anchor was decorative.

3. **Anchors must be binding tests, not infrastructure.** An anchor is something the thesis fails on if the central claim fails. Helpers, fixtures, and pure utilities are not anchors. `_compute_baseline` is not an anchor; `test_baseline_classification_is_correct` is.

4. **Distribute anchors across multiple test functions.** All 9 anchors living inside `test_everything()` is a cargo-cult attractor — the mutator can satisfy coverage by referencing every anchor name in dead code inside one bloated test. Spread anchors across 5+ test functions to make this harder.

5. **Top-level test functions only.** The extractor walks `tree.body` for top-level `FunctionDef` nodes whose name starts with `test_`. Class methods inside `TestCase` subclasses are NOT extracted. If the mutator wraps tests inside a class to defeat extraction, anchor coverage drops to 0 and drift fires. (This is the failure caught in Turn 50; the mutator-awareness prompt now warns against it.)

6. **Symbols must be referenced inside test function bodies.** A top-level import or module-level reference does not count. The symtable check requires the symbol to be `is_referenced` inside a test function's local scope. Cargo-cult imports without test usage do not satisfy coverage.

7. **Anchor names should not encode the conclusion.** `test_thesis_is_true` is tautological. `test_failure_boundary_dominates_intactness` names a structural property the test must check.

**Good example (from EU pillars):**
```markdown
## Anchor Proxies

- classify_union_state
- forecast_tilt_by_2035
- test_current_eu_classifies_as_fragile_but_intact
- test_standing_bundle_classifies_as_durable_equilibrium
- test_failure_boundary_dominates_intactness
- test_survival_alone_does_not_imply_equilibrium
- test_missing_fiscal_pillar_blocks_durable_equilibrium
- test_missing_legal_pillar_blocks_durable_equilibrium
- test_forecast_tilt_is_event_driven
```

This set has 9 anchors: 2 proxy anchors (`classify_union_state`, `forecast_tilt_by_2035`) and 7 test anchors. Each test corresponds to a distinct claim in the Core Question. The proxy anchors are the helpers any honest test of the question would need to call.

**Anti-pattern: anchor names that mirror evidence rather than tests.** "ESM_was_made_permanent" is a fact, not an anchor. "test_esm_classification_is_consistent_with_automaticity_criterion" is an anchor.

---

## Threshold rules

The deterministic drift check fires when anchor-proxy coverage drops below a threshold. Coverage is computed as:

```
coverage = |active_proxies ∩ normalized_anchors| / |normalized_anchors|
drift_distance = 1.0 - coverage
```

**Default threshold: 0.5.** A thesis must reference at least half of the declared anchor proxies inside its test bodies. If coverage drops below 0.5, mathematical drift fires and the score is hard-capped at 50.

**Strict threshold: 0.7.** For high-stakes claims or claims under strong adversarial pressure, raise the threshold. Requires operator review when drift fires (false positives more likely).

**Permissive threshold: 0.3.** For exploratory projects where the right anchors are themselves part of what the project is discovering. Use sparingly. A permissive threshold is essentially a soft warning rather than enforcement.

**The threshold is not currently configurable per-project.** It is hard-coded in `test_thesis.py`. Per-project thresholds are a future refinement; for now, calibrate by adjusting the anchor set rather than the threshold.

---

## Two-layer drift verdict

GP-016 v2 produces two independent drift signals on every iteration:

| Signal | Source | Role | Action |
|---|---|---|---|
| `mathematical_drift_detected` | AST + Jaccard against anchor proxies | **Primary**, deterministic | Hard cap at 50 if coverage < threshold |
| `drift_detected` | Meta-judge LLM reading charter + thesis | **Secondary**, advisory | Logged in `eval_results.json`; does NOT enforce on its own |

**Operator interpretation rule:**

| Math fires | LLM fires | Likely meaning | Operator action |
|---|---|---|---|
| Yes | No | Structural drift caught by physics. Cargo-cult or basin-jump. | Check whether basin-jump was intentional. If yes, update charter. If no, enforce. |
| No | Yes | Semantic drift the math can't see. Right proxies, wrong claim. | Manual review. Consider tightening anchor set or adding new anchors. |
| Yes | Yes | Both layers agree. Strong drift signal. | Almost always reject the thesis or update charter. |
| No | No | Thesis is on-charter. | Continue. |

**Critically: only mathematical drift enforces.** The LLM signal stays in the contract because it can catch semantic drift the math cannot see, but it has no enforcement power on its own. This preserves ZTARE's foundational claim that every score-affecting decision is grounded in deterministic computation.

---

## Charter lifecycle

A charter is:

1. **Authored** when the project is created (or retrofitted onto an existing project)
2. **Updated** when the operator authorizes a basin pivot (the original anchors no longer fit the new direction)
3. **Inherited** when a child project starts (parent's charter is the starting point)
4. **Retired** when the project is closed (move to `archive/` or leave in place with a `## Status: closed` line)

### Update protocol

When the charter changes, the deterministic score regime fingerprint (GP-013) MUST bump. This is mandatory because the score boundary changed and old scores are no longer comparable.

Steps:

1. Operator edits the charter (Core Question, Out of Scope, End States, Inheritance, or Anchor Proxies)
2. Operator appends a changelog line at the bottom of the charter:
   ```markdown
   ## Changelog
   - 2026-04-09: rewrote anchor proxies after authorized pivot to focus on legal-supremacy ranking
   ```
3. Operator forces a regime bump on the next run (or the deterministic regime fingerprint detects the charter change automatically — this is a future refinement)
4. The active baseline re-baselines under the new charter
5. Old persisted bests are intentionally non-comparable

**Anti-pattern: silently editing the charter mid-run.** This produces a score regime ambiguity — iterations 1–3 were scored against charter v1, iterations 4–6 against charter v2, and the comparison between them is meaningless. Always update via the changelog and force a re-baseline.

### When to update vs reject

A drift event raises the question: is the charter wrong, or is the thesis wrong?

- **Thesis wrong, charter right:** the thesis drifted from a valid scope. Reject the thesis, do not edit the charter.
- **Charter wrong, thesis right:** the operator scoped the project incorrectly. Update the charter (with regime bump) and re-baseline.
- **Both wrong:** the project should be split or restarted. Close the project, create a new one with a fresh charter.

The operator decision rule: **the charter is the operator's commitment to a question.** If the operator changes their mind about the question, the charter changes. If the operator still wants the same question answered, the charter stays.

---

## Inheritance protocol

When project B inherits from project A:

1. **B's charter declares the parent in the Inheritance section** with explicit paths to the parent's evidence, axioms, reports, and any drift postmortems.

2. **B inherits A's evidence** as read-only. B's evidence file should reference A's evidence file rather than duplicate it.

3. **B inherits A's derived constraints** (when GP-011 ships). For now, B's operator manually transcribes any structural constraints from A's debate logs.

4. **B MAY inherit A's anchor proxies, declared explicitly:**

   ```markdown
   ## Anchor Proxies (inherited from eu_union_stability)
   - classify_instrument
   - test_esm_classification_is_consistent

   ## Anchor Proxies (new in eu_union_load_bearing_pillars)
   - classify_union_state
   - test_pillar_ranking_is_well_ordered
   ```

   Or, if B's question is structurally different from A's, B may declare a fully fresh anchor set with no inheritance. The current EU pillars charter does this — it declares all anchors fresh because the question shape changed.

5. **B MAY override the Core Question and Out of Scope from A** — but if it does, it must explicitly state which sections are overridden. Silent override is an anti-pattern.

6. **B's regime fingerprint depends on B's charter, not A's.** Inheritance does not cross-contaminate score regimes. A and B have independent baselines.

**Anti-pattern: child project that silently shares all of A's apparatus but answers a different question.** This is what creates apparent drift across projects. Make the inheritance explicit; make the differences explicit.

---

## Authoring workflow (three modes)

### Mode A: Operator-from-scratch

**When:** new project, broad question, high-stakes domain, no prior thesis exists.

**Steps:**
1. Operator drafts the five natural-language sections from the question alone, before any thesis exists
2. Operator drafts the Anchor Proxies as the symbol set the eventual `test_model.py` will need
3. Operator and ZTARE iterate on the test_model to align it with the anchors
4. First mutation iteration runs against the chartered project

**Pro:** maximum scope discipline. The charter shapes the test_model rather than vice versa.
**Con:** operator must know the anchor names before any test exists, which requires domain familiarity.

### Mode B: ZTARE-drafted, operator-vetoed

**When:** project in flight where drift has already been observed; new project where the operator wants ZTARE to suggest the charter from prior context.

**Steps:**
1. Operator runs a `synthesize_charter` step (not yet implemented; future tool) that reads:
   - The project's current evidence
   - Any prior reports or postmortems
   - Inherited material from parents
2. ZTARE drafts a candidate charter (all six sections)
3. Operator accepts / tightens / rejects each section
4. The accepted charter is committed and the next run uses it

**Pro:** low friction for projects with existing material.
**Con:** requires operator to verify ZTARE's drafted Out of Scope and Anchor Proxies are not themselves contaminated by drift attractors.

### Mode C: Evidence-derived (retrofit)

**When:** an active project that doesn't yet have a charter.

**Steps:**
1. Operator reads the current `test_model.py` and extracts the proxy set as a starting point for anchors
2. Operator reads the current `thesis.md` and `evidence.txt` to draft Core Question and Out of Scope
3. Operator drafts End States by enumerating what success and failure currently look like for the project
4. Operator commits the charter and bumps the regime fingerprint
5. Next run uses the retrofitted charter

**Pro:** retrofits charters onto already-running projects with minimal disruption.
**Con:** the retrofit risks declaring the *current* test_model proxy set as anchors, which means drift can never fire from the current state — anchors are calibrated to where the thesis already is, not where the operator wants it to go. Mitigation: tighten the anchor set after retrofit, removing any anchors that are not central to the Core Question.

**Practical recommendation for current ZTARE state:** Mode C for active projects (EU pillars is already done this way), Mode B for new projects, Mode A reserved for high-stakes new domains where the operator wants maximum discipline up front.

---

## Common failure modes

| Failure mode | Symptom | Fix |
|---|---|---|
| Charter writes the conclusion | Core Question contains "prove that..." | Rewrite as a question, not a directive |
| Out of Scope too narrow | Drift attractors not listed | Add the obvious adjacent sub-questions to Out of Scope |
| End States collapse | Only "we prove X" / "we don't" | Enumerate operationally distinguishable end states |
| Anchors don't bind | Helpers and fixtures listed as anchors | Replace with binding test names |
| Cargo-cult anchors | All anchors live in one test function | Distribute across multiple top-level test functions |
| Class-wrapped tests | Anchors live as class methods, coverage drops to 0 | Move tests to top-level functions; the extractor only sees top-level |
| Silent charter edit | Score regime ambiguous mid-run | Always edit via changelog + regime bump |
| Inheritance declared but unused | Parent listed but no evidence/axioms read | Either use the inheritance or remove the declaration |
| Tautological anchors | `test_thesis_is_true`, `test_claim_holds` | Name the structural property the test checks |
| Too many anchors | 30+ anchors, threshold meaningless | Cut to 5–10 binding ones |
| Retrofit calibrated to current state | Drift never fires because anchors match current test_model exactly | Tighten anchor set after retrofit |

---

## Examples

### Example 1: EU pillar ranking (canonical, current)

See `projects/eu_union_load_bearing_pillars/project_charter.md`. This is the live canonical example. Live verification:

- anchor coverage: 1.0
- overlap count: 9 / 9
- drift distance: 0.0
- promoted score: 67 (substantive ceiling, not teleological cap)

This is what a working chartered project looks like.

### Example 2: Hypothetical — Central Station Series A viability (mechanism project)

```markdown
# Project Charter

## Core Question
Does Central Station's unit-economics path to Series A profitability hold under
the cohort revenue, churn, and CAC trajectories observed in the seed-stage data?

## Out Of Scope
- forecasting valuation or fundraising probability
- ranking competitive threats from other startups
- assessing founder quality or team execution risk
- claiming that Series A is the right next round vs alternatives

## End States

### Success
The project distinguishes:
- viable_path_to_profitability
- viable_path_with_required_changes
- non_viable_path

and identifies which unit-economics levers are central for the viable path.

### Failure
The project drifts into:
- a generic startup-quality assessment
- a market-size validation thesis
- a founder-character argument
- a single-metric proof (e.g., "CAC is below LTV therefore viable")

## Inheritance
- projects/central_station_series_a/Report.md (prior ZTARE pass)
- projects/central_station_series_a/evidence.txt

## Anchor Proxies
- compute_unit_economics
- project_cohort_revenue
- model_churn_trajectory
- test_cac_payback_under_observed_curves
- test_ltv_excludes_paid_acquisition_assumed_cohort
- test_path_distinguishes_viable_from_required_changes
- test_non_viable_failure_mode_is_named
- test_unit_economics_changes_are_operationally_specific
```

This is a mechanism project. Anchors are heavy on tests of unit economics and light on meta-claims because the project answers a single causal question.

### Example 3: Hypothetical — AI inference collapse forecast (forecast project)

```markdown
# Project Charter

## Core Question
Through 2027, what is the probability tilt (directional, not point estimate) that
inference cost collapse will materially shift the economic viability of frontier-
model deployment relative to current production economics?

## Out Of Scope
- specific point probabilities of cost collapse
- claiming inference cost collapse is impossible
- ranking which model providers will or will not survive
- conflating training cost and inference cost trajectories
- assuming any specific architecture (transformer, MoE, diffusion) without naming it

## End States

### Success
The project distinguishes:
- material_cost_collapse_likely
- partial_cost_compression_likely
- no_material_cost_change_likely

with explicit event boundaries and directional tilts grounded in current observables.

### Failure
The project drifts into:
- a single-vendor pricing thesis
- a benchmark-performance argument unrelated to cost
- an unbounded long-horizon forecast with no event boundary
- a model-architecture prediction
- a point probability claim

## Inheritance
- none

## Anchor Proxies
- compute_inference_cost_curve
- project_price_compression_2025_2027
- classify_cost_regime
- test_event_boundary_is_named
- test_horizon_is_bounded_to_2027
- test_directional_tilt_is_not_point_estimate
- test_cost_curve_uses_observed_baselines_not_speculation
- test_failure_modes_distinguish_partial_from_material
```

This is a forecast project. Anchors enforce the event-boundary discipline (one of the most common drift modes for forecasts) and the directional-tilt discipline (preventing point-probability laundering).

---

## Operational checklist

When creating a new project:

- [ ] Decide if a charter is required (use the decision rule above)
- [ ] Choose authoring mode (A, B, or C)
- [ ] Draft Core Question — one paragraph, scope-bound, named central object
- [ ] Draft Out of Scope — bullet list including the obvious drift attractors
- [ ] Draft End States — distinguishable Success outcomes and explicit Failure modes
- [ ] Declare Inheritance — with explicit paths and what is inherited
- [ ] Draft Anchor Proxies — 5–10, distributed across multiple test functions, binding not infrastructure
- [ ] Verify the active `test_model.py` has top-level `test_*` functions matching the test anchors
- [ ] Verify the active `test_model.py` references the proxy anchors inside test bodies
- [ ] Run `compute_anchor_proxy_coverage` (or run one iteration and check `eval_results.json`) to confirm coverage = 1.0 at baseline
- [ ] Commit charter to project root as `project_charter.md`
- [ ] Bump regime fingerprint on first run after charter creation

When updating an existing charter:

- [ ] Decide if the change is a basin pivot or a drift correction
- [ ] If basin pivot: rewrite the relevant sections (Core Question, Out of Scope, End States, Anchor Proxies)
- [ ] If drift correction: tighten Out of Scope or Anchor Proxies without changing Core Question
- [ ] Append a changelog entry with date and rationale
- [ ] Force regime fingerprint bump on next run
- [ ] Re-baseline the active project (old scores no longer comparable)

---

## Boundaries

This spec covers:

- when to write a charter
- how to write each section
- the typed Anchor Proxies authoring rules
- charter lifecycle and updates
- inheritance protocol
- the two-layer drift verdict
- common failure modes and examples

This spec does NOT cover:

- the score-contract Python implementation (see `test_thesis.py` and `proxy_signature.py`)
- the architectural derivation of why charters exist (see `project_typing_vs_supervisor.md`)
- the engineering log of GP-016 v1 / v2 (see `general_purpose_mutator_hardening.md` Turns 46–51)
- the supervisor / labor-routing layer (intentionally separate; see `project_typing_vs_supervisor.md` for the boundary argument)
- per-project threshold configuration (currently hard-coded; future refinement)
- automated charter drafting (Mode B `synthesize_charter` is not yet implemented)
- automated regime fingerprint bumping on charter change (currently manual; future refinement)

---

## Future refinements (tracked, not blocking)

1. **Per-project threshold configuration.** Add a `## Threshold` section to the charter so high-stakes projects can use 0.7 and exploratory projects can use 0.3 without code changes.

2. **Automated regime fingerprint bumping on charter change.** The fingerprint should hash the charter content; any change to the charter should automatically bump the regime so old scores invalidate.

3. **`synthesize_charter` tool (Mode B).** A constrained synthesis pass that drafts a candidate charter from prior reports + evidence + drift postmortems for operator review.

4. **Test-anchor vs proxy-anchor weighting.** Currently equal weight in coverage. A future refinement could weight test anchors higher because they are binding assertions while proxy anchors are infrastructure.

5. **Charter inheritance auto-resolution.** When a child project declares inheritance, automatically include parent anchors in the child's coverage check (with explicit override syntax for breaking inheritance).

6. **Drift event taxonomy.** Distinguish "basin-jump drift" from "cargo-cult drift" from "class-wrap drift" so the operator knows which intervention to apply.

7. **Charter changelog as first-class artifact.** Currently the changelog is a section in the charter file. A future refinement could move it to a separate `charter_history.json` for cleaner audit trails.

None of these block adopting the spec. They are tracked here so the discipline of the current spec is not confused with the long-term shape of the system.
