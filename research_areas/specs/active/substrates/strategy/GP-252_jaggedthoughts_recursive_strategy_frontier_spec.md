# GP-252 JaggedThoughts Recursive Strategy Frontier Specification

## Status

Active - operational compiler, mechanism version space, contingent-policy
synthesizer, guarded probe loop, broad public-market scout, scheduled broad and
deep investment discovery, company-choice lowering, and reporting workflow
implemented through 2026-08-12; scientific-positioning and falsifiable
publication contracts, matched activation questions, and closed-book historical
strategy forecasting updated 2026-08-22; source-bound constraint acquisition and
activation-owned question execution updated 2026-08-25

## Seam

`research_areas/seams/substrates/strategy/GP-252_jaggedthoughts_recursive_strategy_frontier_seam.md`

## Concept

`docs/concepts/jaggedthoughts_autonomous_strategy.md`

## Scope

This specification governs the JaggedThoughts decision system:

- a versioned typed operator grammar;
- bounded recursive program enumeration;
- exact candidate and scope identity;
- external, internal, and dynamic burden-of-proof claims;
- evidence-conditioned feasibility;
- source-byte-bound evidence manifests;
- automatic scenario and interaction-factor evaluation;
- exact SMT enumeration of compatible nonempty option sets and canonical typed
  representatives for associative/commutative choice bundles;
- exact behavioral quotienting;
- Pareto frontier and declared-neighborhood local peaks;
- exact rational objective-priority regions, reversal witnesses, and excluding
  unsat cores over the nonnegative unit simplex;
- witnessed frontier partitioning;
- frozen-grammar scope closure;
- representation-audited decision closure;
- source-bound strategic state/action/response traces;
- replay-pruned executable mechanism committees;
- endogenous actor-response rules;
- recursive contingent-policy rollout under mechanism uncertainty;
- authority-bounded registered evidence adapters;
- outcome updates, yield-calibration edges, and optional matched temporal credit;
- replayable JSON artifacts and named Markdown decision reports.
- a point-in-time investment discovery run that enumerates configured public
  equities and funds, compiles type-specific valuation surfaces, ranks candidate
  leaves, and exposes every activation boundary;
- a candidate-leaf-to-research-dossier skill seam whose output may create an
  inactive equity draft but cannot activate paper capital.
- a broad public-market catalog and typed research-intent compiler whose output
  is an enrichment queue rather than an underwriting candidate;
- an investment company-strategy lowering from sourced industry pressures and
  response options to recursive choice systems, compatibility witnesses,
  scenario consequences, global frontiers, and local peaks.
- a strategy-learning population distinct from the capital-admission
  population, plus an expanding-window tournament that selects phenotype
  programs before opening each later operating-outcome block.

The core strategy compiler does not call a language model, browse, or claim
globally optimal strategy. The investment adapter adds public-source ingestion,
a graphical workbench, and a repo-scoped research skill while preserving those
boundaries: source adapters bind bytes and availability, the skill returns a
typed dossier, and only deterministic kernel transitions change workspace
state. Probabilistic dominance remains unimplemented.

## Decision

Implement JaggedThoughts as a strategy-local typed operator-program grammar, a
source-bound scenario/factor evaluator, and a separate frontier-closure
compiler. Enumeration produces programs. The profile supplies claims,
evidence, scenario factors, neighborhood rules, and a representation audit; the
evaluator scores every enumerated target program. Externally computed table
evaluations remain available as an explicit alternate mode. The compiler may
certify exhaustion only inside an exact scope identity. Decision closure
additionally requires an affirmative representation audit.

## Problem

Integrated strategic choices form a rugged performance surface because their
internal, external, and temporal consequences interact. A local optimum is
therefore relative to a move grammar, industry-response model, horizon,
objective vector, and evidence epoch.

Current strategy methods provide useful option generation and analysis but no
mechanical answer to:

```text
Which option programs were generable under the declared language?
Which were considered?
Which were removed, and by what witness?
Which remain unresolved?
Which local peaks depend on the declared neighborhood?
Did the grammar omit a strategic distinction that could change the answer?
```

Without these distinctions, a search-budget stop can be mistaken for closure,
and a local optimum can be reported without naming the neighborhood that makes
it local.

## Why It Matters

JaggedThoughts turns options-led strategy into an inspectable compiler:

```text
typed strategic language
-> recursively enumerated programs
-> integrated option candidates
-> burdens of proof
-> evaluation and equivalence
-> local peaks plus Pareto frontier
-> witnessed closure or exact residual
```

This extends options-led strategy-integrated options, burdens of proof,
targeted analysis, choice-with explicit search-space identity and residual
accounting.
It also connects the repository's fixed-point coverage, frontier-query, version
space, and behavioral-quotient machinery to an out-of-distribution strategy
substrate without changing those existing modules.

## Constraints

1. **Identity before score.** A program identity binds grammar ID, grammar
   version, operator IDs, terminal IDs, and tree structure. Evaluation fields
   cannot redefine identity.
2. **Scope-bound language.** Every certificate binds target type, maximum depth,
   maximum program count, evaluation model, evidence epoch, objectives, and
   neighborhood identity.
3. **Typed construction.** The enumerator applies an operator only to programs
   whose output types exactly match its ordered input signature.
4. **Deterministic enumeration.** The same grammar and bounds produce the same
   ordered program IDs and enumeration digest.
5. **Finite execution.** Recursive operators are permitted only under explicit
   depth and program bounds.
6. **No implicit world closure.** Grammar exhaustion can set `scope_closed`.
   Only a passed representation audit can set `decision_closed`.
7. **Witnessed elimination.** Infeasible, equivalent, and dominated programs
   carry witnesses. Missing evaluation or evidence becomes a residual.
8. **Exact quotient.** Behavioral equivalence uses an exact declared
   signature. Approximate equivalence is deferred.
9. **Neighborhood-relative peaks.** A local peak certificate names an explicit
   neighborhood graph. No default semantic neighborhood is inferred.
10. **Substrate-local first.** Do not promote an operator-grammar abstraction to
    `ztare.common` until billing and strategy lowerings demonstrate the same
    invariant-owning interface.
11. **Jaggedness is measured.** Interdependence does not mechanically imply a
    large number of peaks. The compiler reports peaks induced by the declared
    evaluation model and neighborhood; the name JaggedThoughts is not evidence
    that a profile is rugged.
12. **Landscape lifecycle is explicit.** A frontier scope declares
    `landscape_mode=fixed|endogenous_transition`. State-transforming strategy
    programs require their transition semantics and horizon inside the
    evaluation-model identity.
13. **No silent unitary actor.** Stakeholder utilities remain separate objective
    coordinates unless the profile declares and identifies an aggregation
    rule.
14. **Solver authority is geometric.** The QF_LRA certificate may establish
    whether a frontier program can win for some declared objective weights,
    whether a rival can reverse it, and which inequalities exclude it. It may
    not estimate scenario consequences, probabilities, or returns.
15. **Quotient before recursive expansion when semantics permit.** A declared
    associative/commutative choice-system operator is enumerated as compatible
    option sets in QF_LIA+Bool, then lowered to one canonical typed AST per set.
    Ordered, contingent, and non-associative operators remain tree-enumerated.

## Options

### Option A - Choice-axis Cartesian product

**Description**

Represent every option as one choice per fixed strategic axis.

**Pros**

- transparent candidate count;
- easy compatibility checks;
- suitable baseline for morphological analysis.

**Cons**

- weak representation for contingent or state-transforming strategies;
- bakes the decomposition into one fixed product;
- cannot naturally reuse the principal's operator-algebra pattern.

**Verdict**

Keep as a grammar profile and experimental baseline.

### Option B - Generic typed operator grammar in `ztare.common`

**Description**

Create a reusable cross-substrate grammar kernel immediately.

**Pros**

- maximizes reuse;
- matches the billing precedent conceptually.

**Cons**

- the billing source is not yet available in this repository for an exact
  interface comparison;
- premature extraction could encode strategy-specific assumptions as generic
  invariants.

**Verdict**

Defer extraction; keep the interface extraction-ready.

### Option C - Strategy-local typed operator grammar

**Description**

Build the typed grammar and enumerator under `ztare.strategy`, then test both a
flat integrated-choice grammar and at least one recursive state-transforming
operator.

**Pros**

- expresses both morphological bundles and operator programs;
- bounded recursion is explicit;
- permits later comparison with the billing grammar.

**Cons**

- duplicates a small amount of type-grammar machinery pending a demonstrated
  cross-substrate invariant;
- lowering quality remains case-specific.

**Verdict**

Recommended.

## Recommendation

Ship Option C as the operational kernel. Treat options-led analysis as the
strategy lowering discipline:

- integrated options become target-typed programs;
- “what would have to be true?” becomes claim compilation over program nodes;
- targeted analyses become evidence updates and boundary probes;
- choice occurs over frontier members after residuals are visible.

Industry analysis supplies scenario and response-model inputs. It does not own
the enumerator, equivalence relation, or closure transition.

## Investment discovery binding

### Governing identities

| Object | Job | Owner | Epoch | Compatibility |
|---|---|---|---|---|
| `public_market_catalog` | Bind broad listed equity and ETF identities for cheap screening | universe adapter | retrieval time + provider hashes | one security kind and symbol identity |
| `market_research_intent` | Lower operator language into explicit scope and requested measurements | intent compiler | query + compiler version | visible entity, capitalization, theme, style, and limit fields |
| `market_scout_run` | Evaluate the complete catalog against coarse filters | scout compiler | catalog hash + intent hash | research-queue authority only |
| `market_scout_policy` | Hold editable recurring research mandates | operator configuration | policy content hash | typed query plus optional open terms/objectives |
| `market_scout_cycle` | Execute every enabled saved mandate at one due time | scout scheduler | policy hash + catalog epoch + run identities | enrichment-queue authority only |
| `enrichment_cycle` | Select a diverse, budget-feasible public-data batch | acquisition policy | scout set + policy hash | source-call, time, type, and concentration budgets |
| `enrichment_job` | Acquire evidence for one selected security | durable lease queue | cycle + job hash | exact security and unexpired worker lease |
| `discovery_policy` | Declare cadence, universes, gates, and assumption grids | operator configuration | policy hash | one workspace schema |
| `source_run` | Cache and normalize one public evidence epoch | source kernel | retrieval/as-of epoch | availability-time admissibility |
| `discovery_run` | Enumerate and rank the declared finite universe | discovery kernel | source-run hash + policy hash | exact universe identities |
| `discovery_candidate` | Preserve one type-specific analytical result | discovery kernel | candidate payload hash | equity entity, or fund entity plus watchlist analysis identity, at one source epoch |
| `agent_research_request` | Bind one completed acquisition to a research skill | investment kernel | request hash | exact job, candidate leaf, and source epoch |
| `candidate_research_dossier` | Add strategy, industry, rival, and falsifier evidence | agent or operator | dossier hash | exact request and candidate identity |
| `company_strategy_frontier` | Enumerate evidence-bound industry response systems and local peaks | investment strategy adapter | industry profile + evidence epoch | exact pressure, option, scenario, and grammar identities |
| `investment_profile_draft` | Compile dossier and quantitative evidence into a review object | investment compiler | current source epoch | qualified equity candidate or explicit operator seed |
| `active_paper_profile` | Enter paper monitoring and portfolio assembly | operator | activation time | exact confirmation and paper authority |

### Automatic transaction

```text
broad catalog refresh
  -> read editable saved intents
  -> convenience parser or agent-authored typed override
  -> evaluate all catalog rows per intent
  -> emit bounded, immutable enrichment queues
  -> compile marginal acquisition priority and diversity
  -> admit only a budget-feasible equity/fund batch
  -> lease jobs and batch-enroll selected securities
  -> selectively refresh core, selected-entity, and active-profile sources

due(policy, latest_run, now)
  -> consume_public_sources
  -> build quality reports and fund watchlists
  -> enumerate enrolled SEC equities + compiled fund candidates
  -> equity: recursive valuation grammar + quality gates
  -> fund: factor decomposition + aggregate expectations proxy + valuation gates
  -> rank within one declared normalized objective
  -> write run/candidate leaves and selects/derived_from edges
  -> emit exact candidate-leaf research requests or typed job blocks
```

`frontier_closure.scope_closed` is true only when every identity in the
configured finite universe produced a candidate disposition and no analyzer
failed. It says nothing about un-enrolled tickers, omitted funds, missing
strategy distinctions, or future evidence.

Scout closure and deep-discovery closure are distinct. Scout closure covers
catalog identity and declared coarse filters. Deep-discovery closure covers
the enrolled universe and its configured analyzers. Neither supports an
open-world opportunity claim.

The intent compiler is not a closed thematic ontology. It recognizes a small
set of common aliases for direct operator use and accepts arbitrary
`theme_terms` and ranking objectives from an operator or research agent.
Explicit typed terms take precedence over inferred aliases. This keeps
semantic expansion in the research layer while the kernel remains responsible
for deterministic population filtering, rejection accounting, and closure.

### Company strategy lowering

```text
industry boundary + customer need
  -> source-bound pressures from customers, suppliers, rivals, entrants,
     substitutes, complements, and change
  -> sourced response-option terminals
  -> combine_reinforcing_choices(ChoiceSystem, ChoiceSystem)
  -> recursive bounded programs
  -> repeated/incompatible/bundle-size/prerequisite/resource constraints
  -> scenario-worst earnings durability, growth, capital efficiency,
     downside resilience, and pressure coverage
  -> Pareto frontier + single-choice local peaks
  -> representation residual or decision certificate
```

The adapter cannot derive consequence deltas from option prose. Every option,
pressure, scenario, and interaction must bind evidence. `scope_closed` covers
the declared grammar and adapter constraints. `decision_closed` still requires
a passed representation audit. The compiled result MUST preserve a
content-addressed interaction catalog and MUST bind each evaluated program to
the exact interaction hashes that changed its scores. Downstream strategy-law
programs MUST execute their typed predicate AST against the target move,
environment, and focal comparison; emitting an AST without executing it does
not satisfy the transfer contract.

The static company-choice contract MAY declare prerequisite implications and
linear resource limits. Every resource names a unit, nonnegative limit,
option-specific nonnegative uses, and source references. Z3 MUST exclude a
bundle whose selected option lacks a declared prerequisite or whose selected
uses exceed a limit. The certificate MUST retain the normalized constraint hash
and authored evidence references. This establishes consistency with the frozen
model, not the accuracy of its quantities.

The choice-space certificate MUST expose the constraint language it actually
lowered, not rely on a UI-maintained list. Each predicate row binds its identity,
typed signature, Boolean solver lowering, and active constraint count. The current
finite language is `cardinality_ge`, `cardinality_le`, `not_all_selected`,
`implies_all_selected`, and `linear_sum_le`.
Every bounded rejected bundle MUST retain the exact compiled predicate identifiers
that exclude it; an aggregate count alone is insufficient for inspection or
successor-language learning.

### Strategy measurement successor contract

An outcome-contract acquisition MUST bind one supported move that is an exact
member of a verified current move library, its exact option and frontier hashes,
an `exact_adoption_event`, and the parent profile bytes and path. Only the latest
admissible frontier per entity is eligible; at most one acquisition may fork
from a parent. Moves with absent or interval-censored implementation timing are
ineligible. The research result MUST be either
`contract_found`, `metric_or_threshold_gap`, or `source_gap` and MUST bind opened
primary public documents.

A subscription-acquired contract MUST name metric, source locator, unit,
direction, `pre_move_baseline`, outcome role, measurement start, horizon,
economic coordinate, economic-bridge rationale, evidence references, and a
frozen minimum-effect basis. Its sources are filings or issuer documents acquired
at or after request freeze and explicitly locate the metric, clock, and any
threshold they support. Acquisition mode is
`subscription_primary_document`; the basis is `directional_zero` or
`source_disclosed`. A source-disclosed threshold MUST bind its source, while
directional zero MUST equal zero. The measurement clock begins no earlier than
request freeze and must remain unsettled at assessment.

`contract_found` MUST create an immutable successor profile. It may advance the
evidence epoch, append source and request/result lineage, and add contracts only
to the exact target option. The parent remains unchanged, and the successor MUST
compile before materialization. A typed gap creates no frontier. Neither result
grants causal, rank, portfolio, brokerage, or capital authority.
Gap results require concrete residuals; metric gaps require an opened-source
search and may retry after ninety days. Unsettled requests are rehydrated.
Successors retain append-only measurement lineage, and workers recheck current
parent identity before browsing and again before compiling.

### Two-stage contingent feasibility

The next company-strategy object MUST separate commitments made now from
actions retained as recourse:

```text
irreversible now-option IDs
  + observable typed triggers
  + recourse bundle IDs
  + prerequisite and resource constraints
  -> total, deterministic policy regions
  -> per-region feasibility certificate or counterexample
  -> scenario evaluation outside the solver
```

An observable trigger MUST bind a typed state coordinate, comparison, threshold,
availability epoch, and source identity. It may use only information available
before its recourse action. A recourse leaf MUST reference an immutable bundle
from the compatible choice-space certificate; it may not inline or revise the
bundle. Prerequisites and resource uses MUST bind option IDs, units, coefficients,
bounds, evidence references, and an assumption status. Resources include capital,
capacity, and management bandwidth without treating those categories as a closed
ontology.

The policy-region compiler MUST prove that the declared trigger domain is total
and deterministic. For every reachable region, Z3 MUST check the union of the
now-options and referenced recourse bundle against compatibility, prerequisites,
cardinality, and linear resource bounds. SAT returns a concrete region and
allocation witness. UNSAT returns the region plus a tracked blocking-constraint
core. A contingent policy may enter scenario evaluation only when every reachable
region has one feasible action. The certificate MUST bind the trigger-domain,
choice-space, resource-model, policy-program, and evidence-epoch hashes and MUST
carry `capital_authority=false`.

Solver authority ends at declared syntax and feasibility. It MAY establish
totality, determinism, non-anticipation, compatibility, and arithmetic satisfaction
of frozen constraints. It MUST NOT validate trigger relevance, thresholds,
resource estimates, scenario probabilities, consequence deltas, causal effects,
profitability, security value, or alpha. Those remain source-bound empirical
claims and are evaluated or settled outside Z3. A solver counterexample diagnoses
the declared policy model; it is not evidence about the business.

The bounded v14 adapter implements the first operational subset of this
contract. It resolves commitment and recourse IDs to exact programs in the
same Z3-certified static choice space, builds recursive `branch` programs with
the shared strategy grammar, and invokes the shared policy-region prover for
coverage, overlap, reachability, and state witnesses. It rejects time travel,
unused conditions, a single-leaf pseudo-policy, commitment reversal, and any
leaf absent from the frozen choice space. The executable reference profile has
three recourse leaves and a complete, deterministic QF_LRA region certificate.
Each trigger threshold MUST carry `threshold_basis` and
`threshold_rationale`; subscription-authored profiles admit only
`source_disclosed` or explicitly labelled `analyst_hypothesis`, while
`reference_fixture` is confined to executable examples.

The residual before a live company policy can influence operating research is
empirical, not syntactic: each trigger needs a source-located measurement
contract, an availability-safe observation, a justified threshold, and later
outcome settlement. The v14 receipt therefore remains
`operating_strategy_proposal_only` with `capital_authority=false`. Per-region
resource re-optimization is unnecessary while leaves are immutable members of
one static choice-space certificate; it becomes necessary only if a later
policy language permits state-dependent resource bounds or inline recourse.

The operational selector MUST resolve the exact current company frontier and
policy identity, accept only the policy's complete typed observation set, and
emit a content-addressed selection receipt naming its Z3 region witness and
final static bundle. Workspace activation MUST append the frozen policy and
selection as distinct golden leaves with a lineage edge; it MUST retain
`capital_authority=false`.

### Activation contract

1. Enabling cadence is an operator configuration action.
2. Source refresh, screening, valuation enumeration, ranking, and persistence
   are automatic when a run is due.
3. An addressable deep candidate may receive an immutable research request;
   `blocked` and `stale_evidence` candidates retain a typed block.
4. `submit-dossier` binds any request-bound equity or fund dossier into golden
   lineage and advances the job to `researched` without changing screen status.
5. `draft-candidate` accepts an exact current-epoch qualified public-equity
   leaf and a schema-valid dossier; monitor, blocked, stale, and fund leaves are
   rejected.
6. Draft activation remains the existing exact operator-confirmation
   transition.
7. Brokerage execution is absent.

### Implemented surfaces

```text
src/ztare/investment/discovery.py
src/ztare/investment/research_jobs.py            # budgets, leases, requests, dossier transition
src/ztare/investment/universe_catalog.py         # broad catalog + intent/scout
src/ztare/investment/sources.py                 # issuer and ETF-profile adapters
src/ztare/investment/watchlist.py               # fund expectations proxy
src/ztare/investment/strategy_options.py        # company-choice lowering
src/ztare/investment/strategy_walk_forward.py   # immutable historical forecast folds
src/ztare/investment/golden_store.py            # run and candidate leaves
src/ztare/investment/workspace.py               # due cycle, enrichment, dossier, leaf-to-draft
.agents/skills/jaggedthoughts-capital-research/ # qualitative SOP
forensic-workbench/src/workspaces/investment.jsx
```

### Acceptance

- a forced cycle consumes public sources and returns `source_run_ok=true`;
- a catalog refresh records provider hashes and at least one equity and fund
  identity without per-security API calls;
- a scout run evaluates every catalog row, exposes its compiled intent and
  rejection counts, and never labels a catalog row qualified;
- a scheduled scout cycle executes every enabled editable mandate, preserves
  each run identity, and does not overwrite the latest manual scout;
- the enrichment compiler freezes every score component, marginal diversity,
  cost, selection reason, and budget total before any source call;
- jobs require leases, recover typed evidence blocks at a later source epoch,
  and issue exact candidate-leaf research requests;
- agent-supplied open theme terms narrow the catalog without adding a
  domain-specific kernel branch and take precedence over parser aliases;
- equity enrollment succeeds with the built-in SEC application identity when
  `ZTARE_SEC_USER_AGENT` is absent;
- fund enrollment adds a price series and factor-watchlist identity while
  withholding valuation when issuer or holdings evidence is absent;
- a company-strategy fixture exhausts its declared program scope, emits
  constraint witnesses, global frontier members, local peaks, and a
  representation residual;
- adding a later strategy-outcome block leaves every earlier fold identity,
  selected program, and prediction unchanged;
- a typed phenotype program receives no policy credit unless its expanding-time
  forecast error beats the frozen untyped incumbent under the declared gate;
- any failed adapter is named in `evidence_refresh`; candidates depending on it
  become `stale_evidence` and cannot qualify even when older admissible rows exist;
- the complete workspace build returns `build_ok=true`;
- the declared scope is closed with no analyzer failure;
- each candidate has a stable hash, rank, status, failed gates, next activation,
  and golden leaf;
- a second service check before cadence expiry returns `not_due`;
- the UI exposes schedule state, service heartbeat, run closure, ranked
  candidates, valuation artifact links, and activation owners;
- the golden store verifies after recording the run and its lineage edges;
- dossier submission rejects request or candidate identity mismatch, records a
  content-addressed leaf, and never promotes a monitor or fund to draft;
- a monitor-company strategy-learning request requires an exact dated move and
  measurable outcome contract, binds the current candidate leaf, remains
  excluded from capital-candidate policy learning, and cannot create a proposal;
- every new outcome contract binds its metric direction to the mechanism's
  objective coordinate; settlement emits an immutable scenario-calibration
  receipt, and a challenged invariant direction queues at most one successor
  frontier request bound to the parent frontier and exact receipt hashes;
- mixed, flat, mismatched, or legacy-unbound direction hypotheses remain
  inconclusive, and no metric magnitude is converted into an ordinal scenario
  score;
- the focused investment suite and production UI build pass.

The expanded 2026-08-09 slice cataloged 11,990 identities: 6,730 equities and
5,260 funds. The saved-intent cycle represented 911 mid-cap value companies
and 17 mid-cap value funds, returning bounded queues of 50 and 17. The latest
autonomous cycle scored 67 deduplicated identities, selected three equities and
two funds within 21 estimated source calls and 170 research minutes, produced
five evidence-ready requests, retained two typed blocks, and repaired two prior
blocked jobs. A source-bound SARO strategy profile enumerated 109 programs,
emitted two global-frontier bundles and a capacity-heavy local-only peak,
closed its grammar scope, retained a representation residual, and left the
monitor disposition unchanged. Its dossier was bound to the exact request and
candidate leaves through `submit-dossier`; no draft was created. GP-254 owns
the autonomous acquisition and handoff details.

## Implementation Sketch

### Package layout

```text
src/ztare/strategy/
  __init__.py
  autonomy.py
  autonomous_cli.py
  autonomous_report.py
  evidence.py
  evaluation.py
  jaggedthoughts.py
  mechanisms.py
  policies.py
  probes.py
  profile.py
  representation.py
  report.py
  transitions.py
  cli.py
examples/jaggedthoughts/
  README.md
  autonomous_service_strategy.yaml
  integrated_option_demo.yaml
  observations/high_pressure_partner.json
  sources/autonomous_service_strategy.md
  sources/demo_assumptions.md
tests/strategy/
  test_jaggedthoughts.py
  test_jaggedthoughts_autonomy.py
```

### Grammar objects

```python
TypedTerminal(
    terminal_id: str,
    output_type: str,
    claim_ids: tuple[str, ...],
)

TypedOperator(
    operator_id: str,
    input_types: tuple[str, ...],
    output_type: str,
    claim_ids: tuple[str, ...],
    commutative: bool,
)

OperatorGrammar(
    grammar_id: str,
    version: str,
    terminals: tuple[TypedTerminal, ...],
    operators: tuple[TypedOperator, ...],
)

Program(
    program_id: str,
    output_type: str,
    terminal_id: str | None,
    operator_id: str | None,
    children: tuple[Program, ...],
    depth: int,
)
```

One useful strategy profile can encode terminals such as arenas, value
propositions, channels, activities, capabilities, commitments, and scenario
states. Operators such as `integrate`, `sequence`, `condition`, `respond`, and
`reposition` build higher-order option or policy programs.

### Operator-language design surface

The AWS billing precedent is an operator table over typed objects. The
corresponding JaggedThoughts profile should be codified in the same form, while
the kernel remains open to different operator sets:

| Operator | Type shape | Job |
|---|---|---|
| `observe` | `Source -> Observation` | Read a scoped, epoch-bound strategic source. |
| `diff` | `State x State -> StateDelta` | Compare industry, firm, or response states. |
| `decompose` | `StateDelta -> ChoiceAnatomy` | Expose which strategic entities and commitments moved. |
| `integrate` | `Choice... -> StrategyOption` | Build one internally connected option program. |
| `condition` | `StrategyOption x Scenario -> ContingentStrategy` | Bind an option to a declared contingency. |
| `replay` | `StrategyProgram x State -> OutcomeTrace` | Execute a declared transition or simulation model. |
| `baseline` | `Comparator -> Baseline` | Name the counterfactual used for evaluation. |
| `residual` | `OutcomeTrace x Baseline -> StrategicResidual` | Isolate what the option failed to explain or achieve. |
| `burden` | `StrategyProgram -> ClaimSet` | Compile external, internal, and dynamic obligations. |
| `quotient` | `StrategyProgram... -> EquivalenceClass...` | Merge programs with the same declared behavior. |
| `neighbor` | `StrategyProgram x RewriteRule -> StrategyProgram` | Define the move relation that owns local optimality. |
| `frontier` | `Evaluation... -> StrategyFrontier` | Retain non-dominated representatives and local peaks. |
| `probe` | `ClaimSet x Evidence -> ClaimDisposition...` | Update burdens with discriminating evidence. |
| `revise` | `Grammar x RepresentationResidual -> Grammar` | Open a new grammar epoch around an omitted distinction. |
| `close` | `Frontier x Coverage x RepresentationAudit -> Certificate` | Emit scoped closure or the exact remaining residual. |

The public reference profile instantiates `integrate` and evaluates its eight
generated options across a base case and a distribution disruption. The kernel
already permits recursive operators; operational semantics for the rest must
arrive through tested profiles rather than hard-coded names.

### Enumeration contract

```python
enumerate_typed_programs(
    grammar,
    max_depth,
    max_programs,
) -> EnumerationResult
```

The enumerator:

1. interns all terminals by exact identity;
2. builds programs bottom-up by depth;
3. applies operators only to type-compatible child tuples;
4. canonicalizes commutative children when declared;
5. deduplicates by content-bound program ID;
6. stops at `max_programs` and emits a budget residual rather than exhaustion;
7. returns an ordered target-neutral population and an enumeration digest.

### Strategic claims

```python
StrategicClaim(
    claim_id: str,
    kind: Literal["external", "internal", "dynamic"],
    text: str,
)

ClaimDisposition(
    claim_id: str,
    status: Literal["supported", "refuted", "unresolved"],
    evidence_ref: str,
)
```

The burden of proof for a program is the stable union of claim IDs attached to
its terminals and operators.

### Evaluation and frontier objects

```python
CandidateEvaluation(
    program_id: str,
    objective_values: tuple[float, ...],
    behavior_signature: tuple[str, ...],
    evidence_refs: tuple[str, ...],
)

FrontierScope(
    scope_id: str,
    target_type: str,
    max_depth: int,
    max_programs: int,
    evaluation_model_id: str,
    landscape_mode: Literal["fixed", "endogenous_transition"],
    evidence_epoch: str,
    objective_names: tuple[str, ...],
    neighborhood_id: str,
)
```

All objectives are maximized. Minimized quantities must be sign-normalized
by the lowering and named accordingly.

### Source binding and automatic scenario evaluation

Every evidence reference used by a claim disposition, scenario, factor, or
representation audit must resolve to a declared excerpt. The compiler loads the
local source, rejects path escape, verifies an optional declared content hash,
and uses the repository's evidence-binding primitive to confirm that the
excerpt occurs in the source bytes. The output carries source, evidence
manifest, enumeration, and certificate digests.

For `evaluation.kind=factor_graph`, a profile declares objectives and scenarios.
Each scenario has base coordinates and typed factors:

```yaml
- id: base.focused-direct-subscription
  requires: [arena.focused, channel.direct, economics.subscription]
  delta: [2, 1]
  evidence_refs: [evidence.base-case-model]
```

A factor applies exactly when its required terminal/operator symbols occur in a
program. This supports main effects and higher-order complementarities without
authoring one row per candidate. `scenario_vector` retains every
scenario/objective coordinate for Pareto comparison; `worst_case` and
`weighted_mean` are explicit alternate aggregations.

### Bounded autonomous exploration

Factors may declare plausible alternative coordinates, an evidence question, a
concrete test, and a relative acquisition cost. `build_exploration_agenda`
reuses the repository's information-yield pricing primitive and:

1. forms single- and pairwise factor probes inside explicit world-count bounds;
2. recompiles global frontiers and neighborhood-relative peaks for every
   declared possibility;
3. measures exact frontier partitions and membership displacement;
4. ranks pivotal probes by identification bits per declared cost;
5. emits one machine-readable next action.

This remains the static-factor acquisition path. The transition path below
compiles probe predictions from surviving mechanism programs and executes only
registered adapters admitted by an explicit authority envelope. Grammar and
scenario proposals may come from language models or domain tools, but they
enter as challenger epochs; they do not mint their own closure. The kernel does
not invent observations, causal effects, or a representation pass.

### Autonomous capability thesis - what would have to be true

The strong JaggedThoughts thesis is that strategy can become policy synthesis
under model uncertainty and endogenous response. Static option bundles are the
bootstrap case. The target object is a contingent program that changes a firm
state, changes other actors' response surface, observes the result, and selects
its next commitment.

The eigenbelief is:

> A decision-useful portion of strategic advantage is compressible into typed,
> reusable transition mechanisms whose predictions can be challenged by
> interventions before the decision window closes.

That belief decomposes into ten capability claims:

| ID | We would have to believe | Existing organ to compose | Kill condition |
|---|---|---|---|
| `JT-A1` | Firm, market, rival, and capability states can be represented at a grain that preserves decision consequences. | typed grammars; worldmodel transition identity; partial action systems | Two histories map to the same encoded state yet react materially differently to the same action. |
| `JT-A2` | Strategic actions and commitments can be expressed as typed operators with executable or observational semantics. | JaggedThoughts programs; worldmodel executable carriers; operator proposal contracts | Important expert options repeatedly require untyped escape hatches or prose-only semantics. |
| `JT-A3` | Longitudinal evidence can be compiled into source-bound `(state, action, response, time)` traces. | evidence binding; episode logs; evidence digests; governed argument graphs | The organization cannot distinguish intervention, exposure, and outcome epochs or recover action provenance. |
| `JT-A4` | A committee of rival mechanism programs can predict observed transitions better than narrative or base-rate controls out of sample. | worldmodel synthesis, gates, version space, behavioral quotienting | Surviving programs fail prospective replay or never outperform cheap baselines. |
| `JT-A5` | Customer, competitor, complementor, regulator, and internal responses can be modeled or bounded well enough for the decision horizon. | scenarios; mechanism effects/protocols; fixed versus endogenous landscape identity | Response uncertainty is so wide that nearly every policy remains non-dominated or rankings reverse after minor omitted reactions. |
| `JT-A6` | Recursive enumeration can recover useful policies within tractable depth and budget. | typed enumeration; factored search; symmetry/equivalence reduction; no-good ledgers | Candidate growth outruns pruning, or withheld expert policies remain absent after grammar challenge. |
| `JT-A7` | Representation failure can be detected before it is mistaken for search completion. | grammar epochs; representation challenge; grammar reflex/extension; residuals | Independent challengers keep finding material new frontier behavior with no stability trend. |
| `JT-A8` | Some affordable action or evidence query separates the live model committee. | information-yield pricing; wager/test agendas; worldmodel policy; JaggedThoughts probes | The best reachable probe has negligible identification yield or arrives after commitment is required. |
| `JT-A9` | Outcome attribution and delayed credit are adequate to update models and policies. | forecast contracts/calibration; temporal decision credit; evidence consolidation | Observations cannot be assigned to the action/model epoch, or feedback is slower than strategic regime change. |
| `JT-A10` | The agent can act inside explicit authority, reversibility, budget, and escalation boundaries. | strategy decision policy; registered gate actions; action receipts | The selected probe has no authorized adapter, exceeds loss limits, or creates an irreversible commitment without review. |

The system earns stronger autonomy only by satisfying this ladder prospectively.
Language fluency supplies candidate proposals; it does not satisfy any row by
itself.

### Composed operating loop

```text
source-bound observations
  -> strategic transition traces (state, action, response, time)
  -> executable mechanism-program version space
  -> typed policy-program enumeration
  -> rollout across mechanism and actor-response committees
  -> robust frontier + local peaks + representation residual
  -> highest-yield authorized probe
  -> observed response + model pruning + grammar revision
  -> repeat or escalate an irreversible commitment
```

This is a dual-control loop: an action can create business value and identify
which world model is operating. The acquisition policy should price both, keep
the coordinates visible, and refuse a single opaque score as decision
authority.

### Implemented autonomous kernel and remaining boundary

The transition path now implements all six bridge components:

1. `StrategicState`, `StrategicAction`, `StrategicTransition`, and
   `StrategicTraceSet` bind decision identity, epoch, coordinates, source bytes,
   and observed boundaries; traces lower into the shared witnessed
   `PartialActionSystem`.
2. `StrategicMechanism` programs replay every observed transition;
   `MechanismVersionSpace` retains every tolerance-consistent candidate and
   exposes an empty committee as a representation failure.
3. mechanism rules execute primary effects followed by state-conditioned,
   actor-owned responses.
4. `StrategicProbe` candidates compile into the shared guarded-protocol pricing
   kernel. `ProbeAuthority` limits adapter IDs, action tiers, primitive cost,
   and irreversibility. Profile data cannot install executable code.
5. `then(Policy, Policy)` and
   `branch(Condition, Policy, Policy)` recursively enumerate contingent
   policies. Each policy is rolled through every surviving mechanism; the
   frontier score for each objective is the worst committee outcome.
6. an observed probe transition recompiles the committee and policy frontier,
   records predicted and observed version-space contraction, and emits a
   `DecisionEligibilityEdge`. Supplied matched outcome chains compile through
   the shared temporal-credit and yield-calibration kernels.
7. `diagnose_autonomous_strategy` compiles transition nonfunctionality,
   mechanism-language exhaustion, probe deadlock, enumeration truncation,
   frontier saturation, declared representation gaps, and yield miscalibration
   into prioritized repair contracts with counterexamples and kill tests.

The built-in `file_transition` adapter reads a scoped, content-hashed readout
produced outside the process. It does not confer authority to make a material
organizational commitment. Stronger adapters must be registered by a host and
remain inside the same authority contract.

The remaining research boundary is empirical: whether a useful state grammar
can be maintained, whether mechanism committees predict concealed future
transitions better than simple controls, whether affordable probes arrive in
time, and whether repeated grammar challenges reduce representation residuals.
The compiler makes these questions measurable; a successful reference run does
not settle them.

### Executable semantics

`ProgramInterpretation` binds terminal values and operator implementations to
one exact grammar digest. `interpret_program` recursively executes a program,
checks every input and output type, memoizes repeated subprograms, and rejects
semantics registered for a different grammar epoch. YAML profiles can enumerate
and automatically evaluate factor graphs without executable semantics;
externally computed tables remain supported. State-transition profiles should
use a Python interpretation and bind its identity into the evaluation model.

### Closure partition

For target programs `S` inside the frozen scope, the compiler emits:

```text
S = F ⊔ D ⊔ I ⊔ E ⊔ R
```

where:

- `F`: supported, evaluated, non-dominated representatives;
- `D`: dominated representatives with a named dominator;
- `I`: claim-refuted programs with claim/evidence witnesses;
- `E`: exact behavioral equivalents with a canonical representative;
- `R`: missing evaluations, unresolved claims, or enumeration residuals.

The certificate also reports neighborhood-relative local peaks among the
eligible representatives. Local peaks and the global Pareto frontier are
different views and must remain separate fields.

### Closure predicates

```python
scope_closed = enumeration.exhausted and not residuals

decision_closed = (
    scope_closed
    and representation_audit.status == "passed"
)
```

`representation_audit.status == "unassessed"` is the default. The kernel does
not manufacture a pass from grammar size, score separation, or lack of
remaining programs.

### Representation audit

```python
RepresentationAudit(
    audit_id: str,
    status: Literal["unassessed", "residual", "passed"],
    residuals: tuple[str, ...],
    evidence_refs: tuple[str, ...],
)
```

Candidate audit methods for later experiments:

- independent option-generation recall;
- withheld-production recovery;
- alternative-decomposition comparison;
- historical option archetype recall with outcomes concealed;
- stakeholder or expert challenge of missing choice dimensions;
- grammar mutation followed by frontier stability analysis.

The implemented `challenge_representation` primitive compares a baseline and
challenger grammar under one exact evaluation surface. Program hashes remain
epoch-local; exact behavior signatures own cross-epoch identity. The primitive
recomputes the Pareto frontier of the union and emits representation debt only
for novel challenger behaviors that survive that combined frontier. A
non-finding remains `unassessed`; a single challenger cannot emit `passed`.

### CLI

Compile a declarative profile:

```bash
PYTHONPATH=src venv/bin/python -m ztare.strategy.cli \
  examples/jaggedthoughts/integrated_option_demo.yaml --summary
```

Write the complete machine artifact and named decision report:

```bash
./venv/bin/python -m ztare.strategy.cli \
  examples/jaggedthoughts/integrated_option_demo.yaml \
  --output decision.json --report decision.md
```

Emit only the next-question agenda:

```bash
./venv/bin/python -m ztare.strategy.cli \
  examples/jaggedthoughts/integrated_option_demo.yaml --agenda
```

Challenge one grammar epoch with another:

```bash
PYTHONPATH=src venv/bin/python -m ztare.strategy.cli BASELINE.yaml \
  --challenge CHALLENGER.yaml --challenge-id <stable-id> --summary
```

Compile the transition/mechanism/policy loop:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.strategy.autonomous_cli compile \
  examples/jaggedthoughts/autonomous_service_strategy.yaml --summary
```

Consume the selected registered readout and write a separate run state:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.strategy.autonomous_cli step \
  examples/jaggedthoughts/autonomous_service_strategy.yaml \
  --run-state-out /tmp/jaggedthoughts-run.json \
  --output /tmp/jaggedthoughts-step.json \
  --report /tmp/jaggedthoughts-step.md
```

## Hard Invariants

- `JT-INV-1`: grammar ID and version participate in every program ID.
- `JT-INV-2`: no ill-typed operator application enters the population.
- `JT-INV-3`: program order and digest are deterministic.
- `JT-INV-4`: a program appears in exactly one closure partition class.
- `JT-INV-5`: every dominated, infeasible, or equivalent program has a witness.
- `JT-INV-6`: budget exhaustion prevents `scope_closed`.
- `JT-INV-7`: missing evaluation or unresolved burden claim prevents
  `scope_closed`.
- `JT-INV-8`: `decision_closed` implies `scope_closed` and a passed
  representation audit.
- `JT-INV-9`: local peaks are computed only from the declared neighborhood.
- `JT-INV-10`: the certificate never contains a global/open-world optimality
  field.
- `JT-INV-11`: source bytes, evidence bindings, claims, dispositions, and the
  evaluation declaration participate in the decision-surface identity.
- `JT-INV-12`: an exploration probe may select only a declared uncertainty and
  declared test; it cannot write an observation or representation pass.
- `JT-INV-13`: joint probe enumeration is bounded and skipped combinations are
  surfaced.
- `JT-INV-14`: a mechanism survives only if its executable transition replay is
  within the declared tolerance on every observed coordinate.
- `JT-INV-15`: primary effects and actor-response effects have distinct owners
  and ordered phases.
- `JT-INV-16`: a policy frontier is evaluated against every surviving mechanism
  and each objective retains the worst committee outcome.
- `JT-INV-17`: a probe without model disagreement cannot be selected, even when
  its context is novel.
- `JT-INV-18`: profile data may select only registered adapters admitted by the
  authority envelope; it cannot inject executable adapter code.
- `JT-INV-19`: information-yield calibration cannot mint downstream task value;
  task credit requires matched terminal outcome chains.
- `JT-INV-20`: a diagnostic label has no repair authority unless it carries a
  concrete counterexample, required refinement, and kill test.
- `JT-INV-21`: an LLM proposal cannot mint type validity, model probability,
  causal identification, scope closure, representation closure, or action
  authority.
- `JT-INV-22`: evidence for a method on another substrate or benchmark cannot
  mint strategy or investment capability; transport requires an explicit
  object mapping, boundary statement, and local discriminator.

## Acceptance Criteria

The implementation is accepted when focused tests and the CLI smoke workflow
demonstrate:

1. deterministic enumeration of a typed integrated-choice grammar;
2. recursive same-type operator expansion stops exactly at the depth bound;
3. ill-typed combinations are absent;
4. exact equivalence, infeasibility, dominance, frontier, and residual classes
   are disjoint and exhaustive over target programs;
5. all eliminations carry witnesses;
6. a program-budget cut emits a residual and blocks scope closure;
7. an unresolved burden claim blocks scope closure;
8. a refuted claim produces an infeasibility witness;
9. changing the declared neighborhood can change the local-peak set without
   changing the global frontier;
10. grammar exhaustion with an unassessed or residual representation audit
    keeps `decision_closed=false`;
11. a passed representation audit plus complete witnessed partition permits
    `decision_closed=true`;
12. source excerpts bind to local source bytes and invalid references fail;
13. a factor graph automatically evaluates every target program across all
    declared scenarios;
14. JSON output contains the evaluation model and generated candidates;
15. the Markdown report names the decision, robust frontier, local peaks,
    burdens, eliminations, representation state, sources, and audit identities;
16. serialization replays the enumeration and certificate digests.
17. single and pairwise uncertainty probes recompile the frontier and emit a
    deterministic next action ranked by information per declared cost.
18. competing mechanisms that fit the same historical transition remain in the
    version space;
19. actor-response rules change high-pressure rollouts without changing the
    low-pressure replay;
20. recursive `then` and `branch` policies exhaust their frozen depth scope and
    compile a committee-robust frontier;
21. the selected registered probe discriminates the live committee inside the
    declared authority bounds;
22. its content-bound observation prunes the contradicted mechanism, recompiles
    the policy frontier, and records predicted versus observed information;
23. once the committee agrees, the same probe is not selected again;
24. the reference workflow emits JSON, run-state, and Markdown artifacts while
    leaving the source profile unchanged.
25. representation failures compile into deterministic diagnostic receipts and
    route the next action without changing the source profile.
26. every evaluation report labels claims as inherited, candidate, or
    established and binds any capability claim to its named comparator,
    concealed outcome, and uncertainty-aware endpoint.
27. an MDA-style Bayesian model-discovery comparator is included when a valid
    simulator or likelihood makes the comparison compatible; otherwise the
    report records which compatibility assumption failed.
28. posterior-predictive information pricing reproduces the existing uniform
    deterministic committee exactly and accepts nonuniform structure weights
    only from a separately identified inference producer.
29. activation research freezes a Cartesian-complete thesis × rival × null by
    frontier-program response matrix in a web-disabled subscription call before
    acquisition; the later source-bound dossier settles the researched program,
    and neither artifact grants queue or capital authority.
30. new activation requests freeze a content-addressed matched assignment to
    either the incumbent frontier program or the matrix-selected program before
    browsing; legacy requests are treated as nonexperimental incumbent cases.
31. the subscription schema, prompt, dossier validator, and settlement bind the
    same assignment and executed program; unchosen program outcomes are not
    imputed.
32. policy learning accepts only complete two-arm pairs, uses source-bound
    realized information yield, requires at least twenty pairs plus a paired
    permutation and sign-stable interval, and cannot make an investment claim.
33. before a winner the assignment is balanced; after a qualifying result the
    preferred research-question policy receives eighty percent of later cases
    while a matched audit lane preserves the remaining twenty percent.
34. the workbench exposes pair count, gate, status, future routing, and the
    immutable policy artifact without granting capital authority.
35. a frontier with at least two exact options and no typed feasibility
    predicate emits a `strategy_constraint_evidence:<frontier-prefix>` research
    atom carrying the exact parent option vocabulary; missing or ambiguous
    source evidence leaves the parent choice space unchanged.
36. when an activation request embeds a research-question frontier, that later
    policy episode owns the sealed response matrix, executed program, browsing
    prompt, and settlement. The older dossier request continues to own candidate
    and research lineage but cannot replace the activation's question identity.

## Scientific-Positioning and Publication-Claim Contract

### Claim classes

Every public research artifact governed by this specification MUST distinguish
three classes:

- `inherited`: a method or result transported from an existing field;
- `candidate_contribution`: a JaggedThoughts composition whose incremental
  value is under test;
- `established_here`: a claim supported by a frozen, replayable experiment that
  met its outcome-blind frozen comparator and endpoint.

Typed grammars, bounded enumeration, SMT solving, CEGIS/CEGAR, Pareto
frontiers, robust control, dual control, Bayesian experimental design, and LLM
hypothesis proposal are inherited. No report may describe their standalone use
as a JaggedThoughts contribution.

The candidate contribution is the typed composition of:

1. source-bound strategic transitions;
2. executable rival mechanisms;
3. exhaustive bounded contingent-policy enumeration;
4. distinct `scope_closed` and representation-audited `decision_closed`
   predicates;
5. counterexample-driven representation repair;
6. authority-bounded probes and actions; and
7. longitudinal settlement across strategic forecasts, operating outcomes,
   valuation revisions, and benchmark-relative returns.

### Model Discovery Agent boundary

[Model Discovery Agent](https://arxiv.org/abs/2608.09696) is the nearest
current systems comparator for M-open mechanism discovery. It uses an LLM to
propose candidate mechanistic structures, sequential Monte Carlo or
simulation-based inference to estimate model and parameter uncertainty,
held-out predictive checks to trigger hypothesis-space expansion, and
value-of-information experiment design. Its claimed benchmark result is
specific to ForceBench, ChemBench, and NeuronBench.

The paper informs two design decisions here:

- the LLM may propose representation repairs, but typed and statistical
  machinery owns validation and belief updates;
- a predictive residual may trigger M-open expansion, and experiment choice
  should be compared with a value-of-information policy.

It does not establish the GP-252 capability. Its reported tasks use synthetic
data with known truth, controlled interventions, bounded experiment budgets,
designed intervention spaces, and an available likelihood, simulator, or
simulation-based approximation. GP-252 must additionally handle strategic
nonstationarity, rival adaptation, sparse
observational histories, delayed and irreversible action, multi-objective
choice, governance, and price-relative investment settlement. The paper does
not test GP-252's policy grammar, closure predicates, neighborhood peaks,
authority membrane, cross-firm transport, or investment outcomes. GP-252's
current version-space and probe-partition calculations MUST NOT be presented as
a Bayesian posterior, model evidence, or causal identification.
The common information-yield primitive may consume posterior weights and
stochastic predictions; it does not infer or calibrate those inputs.

Where an executable simulator or likelihood exists, the exploration program
MUST include an MDA-style arm using the same evidence, intervention menu,
budget, and held-out queries. Where those assumptions fail, the artifact MUST
name the failed compatibility relation rather than omit the comparator
silently.

### Publication gates

A systems-artifact claim requires a frozen grammar, source manifest, evaluator,
and epoch; independent deterministic replay; exhaustive program disposition
inside the bound; and zero unwitnessed eliminations. It does not imply
strategic effectiveness.

A representation-search claim requires later behavior to be concealed during
profile construction, an independent post-freeze grammar challenge, and an
ablation against flat morphology and unconstrained LLM search. The primary
endpoint is false-closure rate or concealed-policy quality. The claim fails if
profile authors encoded the winning behavior or challengers routinely add
frontier-changing behavior after `decision_closed`.

A mechanism-learning claim requires decision-episode-blocked out-of-sample
evaluation against persistence, regularized statistical controls, narrative
LLM, and the compatible MDA-style arm. The primary endpoint MUST be a
outcome-blind frozen uncertainty-aware predictive loss. Its interval MUST exclude no
improvement against the strongest surviving comparator. Predictive fit and
mechanism-form recovery are separate endpoints; a useful forecast cannot by
itself certify the governing mechanism.

A probe-selection claim requires identical probe menus, authority, cost, and
irreversibility budgets across random, LLM-only, and value-of-information
comparators. The primary endpoint is cost-normalized reduction in held-out
predictive loss or mechanism uncertainty. Information gain alone cannot mint
downstream task value.

A strategic-decision claim requires prospective settlement against a frozen
comparator, outcome, and horizon. An investment claim additionally freezes
price, benchmark, factor exposures, transaction costs, and multiplicity policy.
A strategy outcome cannot mint an investment-return claim, and an observational
association cannot mint a causal claim.

Every publication MUST report null and negative results, all named ablations,
data leakage checks, comparator compatibility, and uncertainty. If an MDA-style
arm explains the full gain, the supported claim is strategy-domain adaptation
and governance. If typed closure and representation repair add no predictive or
decision lift, the broader autonomous-strategy claim is rejected for the tested
scope.

## Exploration Program

### Research boundary informing the program

- Casadesus-Masanell, *Industry Analysis* (Core Reading 8101, revised 2022),
  especially pp. 36-48, supplies a six-stage operating sequence-define,
  identify, analyze, test, respond, change-and treats positioning as an
  integrated system of mutually reinforcing choices. It also separates a
  snapshot of industry structure from competition through time, industry
  shaping, scenario construction, and specific rival response. JaggedThoughts
  maps those distinctions to decision/state identity, recursive policy
  composition, observed transition tests, endogenous actor rules, and
  representation residuals. The reading's warning that structural analysis
  does not predict a particular competitor response is why a declared Five
  Forces assessment may seed mechanism candidates but cannot settle their
  version space.
- [Rahmandad, *Interdependence, Complementarity, and Ruggedness of Performance
  Landscapes*](https://doi.org/10.1287/stsc.2019.0090) shows that
  complementarity can reduce rather than multiply local peaks. Peak count is an
  output of a profile, not a premise.
- [Signposts for Problemistic Search](https://doi.org/10.1287/stsc.2023.0072)
  models reference points as an endogenous transformation of the perceived
  landscape. Evaluation-model and evidence-epoch identity therefore own the
  current surface.
- [Searching, Shaping, and the Quest for Superior
  Performance](https://doi.org/10.1287/stsc.2017.0036) separates navigating a
  landscape from changing it. JaggedThoughts binds this distinction through
  `landscape_mode`.
- [Csaszar and Levinthal, *Mental Representation and the Discovery of New
  Strategies*](https://doi.org/10.1002/smj.2440) motivates the separate
  representation audit and grammar-epoch recursion.
- [DEI](https://arxiv.org/abs/2605.27130) and quality-diversity search motivate
  diversity/coverage baselines for proposer systems. Archive coverage remains
  different from witnessed grammar closure.
- [Revisiting the Unitary Actor
  Assumption](https://doi.org/10.1287/stsc.2024.0257) motivates retaining
  stakeholder objectives separately until an aggregation rule is declared.
- [Can AI Do Strategy?](https://doi.org/10.1287/stsc.2026.intro.v11.n1)
  frames strategic AI along causal-reasoning and delegation ladders. The
  JaggedThoughts receipts expose both: mechanism replay measures the causal
  layer, while adapter authority and step status measure delegation.
- [Beyond Black Boxes: Designing and Testing Agentic AI Systems for
  Strategy](https://doi.org/10.1287/stsc.2025.0432) motivates evaluating a
  purpose-built agentic system through its architecture and controlled task
  surface rather than treating fluent output as capability evidence.
- [When Artificial Intelligence Does Strategy](https://doi.org/10.1287/stsc.2025.0448)
  identifies lock-in risks under extensive delegation. Representation residuals,
  multiple mechanism survivors, and grammar challenges are the corresponding
  anti-lock-in surfaces here.
- [Robust Bandit Policies Under Uncertain Causal
  Mechanisms](https://proceedings.mlr.press/v323/avery26a.html) supports keeping
  a causal-mechanism uncertainty set through policy evaluation instead of
  collapsing early to one fitted model.
- [Trajectory Planning for Safe Dual Control with Active
  Exploration](https://arxiv.org/abs/2604.15507) motivates treating a bounded
  action as both a state transition and a model-discriminating observation,
  with safety constraints compiled before selection.

### Stage 0 - Executable reference profile

Use a small integrated-choice grammar with known candidate count, deliberate
incompatibilities, two behaviorally equivalent programs, multiple local peaks,
and one globally non-dominated frontier.

Implemented 2026-08-08. The public example binds eight evidence excerpts,
enumerates eight integrated options, automatically evaluates them under two
source-bound scenarios, finds three one-rewrite local peaks and three robust
Pareto members, writes machine and decision artifacts, closes the frozen scope,
and keeps decision closure false while representation is unassessed.

The autonomous reference case is also implemented. Two mechanisms replay one
low-pressure transition; a depth-two grammar exhaustively enumerates 202
contingent policies; the robust frontier is computed across both models; the
lower-cost one-bit high-pressure probe is selected; its content-bound readout
eliminates the contradicted model; the frontier is recompiled; and the resolved
probe is not repeated. Representation remains residual by declaration.

### Stage 1 - Options-led historical case

Select one historical case with a frozen decision date. Conceal later outcomes
during grammar construction and option generation. Compare:

- human/LLM integrated-option generation;
- flat morphological enumeration;
- typed recursive enumeration;
- typed enumeration plus representation audit and grammar revision.

Measure coherent option recall, distinct peak recall, false closure,
discriminating-test efficiency, and frontier stability under grammar revisions.

### Stage 1b - Isomorphic strategy-search benchmark

The first apparatus slice is implemented as a sealed deterministic landscape:
it compares exhaustive Z3/frontier search with Pareto-improving one-edit hill
climbing and requires the former to escape a local peak through an initially
declining edit path. This establishes apparatus behavior only. The full stage
below remains required for empirical or scientific performance claims.
The same fixed instance MUST include an interaction-blind solver ablation that
uses the identical certified feasible set but additive terminal effects. Its
selection is evaluated on the frozen full landscape to distinguish feasibility
closure from interaction-model value.

Construct sealed business environments with typed actions, prerequisites,
resource limits, positive and negative interactions, several local peaks,
regime changes, observational adoption confounding, and causal motifs hidden
behind randomized industry names. Each system begins at a local peak and has a
fixed budget of twelve outcome queries on each held-out firm.

Compare one-edit NK hill climbing, exact Z3/Pareto search with a fixed additive
score, constrained Bayesian optimization or a combinatorial bandit, doubly
robust policy learning on a fixed action set, an LLM planner without closure,
and JaggedThoughts ablations removing grammar, closure, or mechanism transfer.
The primary endpoint is normalized terminal regret against the simulator's
known feasible optimum after twelve queries. A system-level contribution
requires zero infeasible recommendations, exact feasible-frontier replay on
tractable instances, calibrated frozen outcome predictions, transfer lift that
survives relabeling, and at least twenty percent lower mean regret than the
strongest compatible baseline with a 95 percent interval excluding zero. If
the integrated system or any claimed component fails its ablation, that claim
is rejected while the compiler may remain a useful decision-support product.

### Stage 2 - Billing-to-strategy structural comparison

Obtain the principal's billing grammar source or a redacted signature table.
Compare object identity, operator signature, lifecycle, equality, closure, and
residual semantics. Promote a shared operator-grammar kernel only if the common
interface survives both substrates without billing or strategy terminology.

### Stage 3 - Domain-expert challenge

Prepare a two-page memo and runnable case demonstration. Ask a strategy expert
to attack:

- whether the grammar captures integrated choice systems;
- whether burdens of proof are attached at the right granularity;
- whether the neighborhood models strategic moves plausibly;
- whether the representation audit catches missing peaks;
- which teaching case provides a fair prospective test.

The discussion seeks a discriminator and case design, not endorsement.

## Open Questions

- What evidence threshold should permit `RepresentationAudit(status="passed")`?
- Should uncertain objectives use interval dominance, scenario-wise dominance,
  minimax regret, or separate frontier compilers?
- Which trace volume and tolerance calibration reliably distinguish rival
  response mechanisms without overfitting one episode?
- Can an LLM propose terminals and operators while a deterministic compiler
  owns type checking, enumeration, and closure?
- Which program equivalence is stable under grammar revision?
- Should neighborhood edges be generated by declared rewrite operators once a
  rewrite semantics exists?

## Outcome-bearing control boundary

The recursive strategy grammar selects the exact treatment phenotype; it does
not manufacture the comparator or its outcome. A strict control requires both
a source-bound `no_family_adoption_found` classification and filing-derived
operating history available by the panel cutoff. The investment acquisition
layer may fetch that history after classification, but a source gap remains a
gap. Strategy-law settlement consumes only the resulting typed panel rows.

The compiled one-choice neighborhood MUST be externally inspectable. Every edge
binds a base program, target program, exactly one added option, any interactions
activated by that addition, and the authored objective delta. This is the
contrastive calibration unit for subsequent learning. Until an observed
base-to-target transition, point-in-time outcome contract, and admissible contrast
are bound, the edge remains an authored target with no causal, valuation, return,
rank, portfolio, or capital authority.

The transfer layer MUST preserve an exact one-choice deletion as a distinct control
identity. A target program phenotype `P + option` may be compared with `P` only when
the control program is independently source-classified as integrated, its phenotype
multiset is exactly one constituent smaller with no substituted constituent, and both
arms have the same frozen readout signature and matched environment stratum. This
comparison is an operating association; recursive adjacency alone grants no causal or
security-return credit.

The program-adoption request is a frozen-chain successor and MUST be schedulable
without acquiring the broad-discovery compile lock. A new frontier may therefore
activate its program question on the research-agent maintenance pass even while the
market scanner is hydrating another universe. Candidate-bound frontiers outrank
unbound operator illustrations at the same entity and evidence epoch; among equally
bound compiler artifacts the move-library selector prefers the higher compiler
contract, emitted predicate catalog, and typed neighborhood before using a digest as
a deterministic final tie-break. Digest order alone has no temporal or epistemic
meaning.

The request producer MUST include every exact one-choice base of a candidate
frontier or local-peak target when at least two of that base's constituent events
are source-bound. Eligibility does not depend on the base itself being frontier or
local-peak; otherwise the empirical consumer for `P -> P + option` can never acquire
the `P` classification it requires.

Integrated-program attribution has an additional discrimination gate. When
several feasible programs share a common option spine, a prospective program
readout MUST include at least one constituent that distinguishes the selected
program from those rivals. A metric signature supported only by common-spine
moves may measure the company after adoption, but it MUST NOT settle which
recursive program performed better. The adoption request records
`common_option_ids` and each candidate's `discriminating_option_ids`; the
outcome-plan compiler enforces the gate before freezing a readout.
An exact adoption classification additionally requires one opened joint source
whose structured support set contains `coordinated_program` and
`option:<option_id>` for every selected-program constituent. Separate option
documents plus generic language about the common spine do not satisfy this
relation.

The strict `P:0` question and an active-comparator `P:Q` question MUST use
different schemas and estimands. `family_adoption_only` remains contaminated for
`P:0`; it MAY enter a pre-outcome `P:Q` eligibility frontier only as a declared
relation class to the focal phenotype. Until the source event carries Q's full
typed phenotype, the system MUST NOT name or hash an exact Q phenotype.

The active-comparator frontier MUST bind the cohort plan, projection frontier,
evidence epoch, industry and calendar risk set, one exact-date index event per
firm, washout and crossover rules, pre/post history floors, and independent-firm
floors. It MUST partition ambiguous, bundled, repeated, crossover-contaminated,
and missing-history rows before any effect calculation. Projection selection
cannot use the outcome later used for validation. No `P:Q` artifact may satisfy
the strict law's control floor or grant law, rank, portfolio, or capital credit.

### Additive constraint-challenge successor

An additive constraint-challenge request MUST bind an intact parent frontier,
choice-space certificate, feasibility-predicate hash, evidence epoch, and source set.
Its admitted and excluded bundle examples MUST belong to the parent-feasible set.
Candidate predicates MUST be new, source-bound incompatibility, prerequisite, or
typed resource-limit rows; a request may contain at most twelve. Deterministic replay
MUST test every candidate-predicate subset across the complete parent-feasible set.
Only one inclusion-minimal satisfying subset is successor-eligible. Zero such subsets
MUST return `insufficient`; more than one MUST return `ambiguous`.

An eligible successor MUST preserve the parent bytes, append only the selected
predicates, bind request and result hashes, advance the evidence epoch no earlier
than the challenge evidence, and run through the existing frontier compiler. The
challenge MUST NOT remove or revise a parent predicate, infer a causal effect, or
grant rank, portfolio, order, or capital authority. Those transitions require a
separate falsification or regime-change contract.

The recurring research-question compiler MUST activate this challenge surface
when the current source-bound frontier has at least two options and zero typed
feasibility predicates. The selected question MUST carry exact prior option ids
and descriptions, and the browsing role MUST either return a supported candidate
plus admitted/excluded or implication examples or return empty typed arrays. The
role may not rename the options or turn qualitative scarcity into a numeric
resource predicate. Admission remains the deterministic subset replay above.
