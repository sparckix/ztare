# GP-251 — AxiomPack Frontier Exploration Inlet Seam

> **Seam metadata** · `seam_id:` GP-251 · `track:` engine/lean · `status:` ACTIVE (theory-program and isolated-lineage kernel implemented; consequential campaign pending) · `last_updated:` 2026-07-09
>
> Opened 2026-07-09 · Owner: user + LeanMill engine

Canonical spec:
`research_areas/specs/active/engine/lean/GP-251_axiompack_frontier_exploration_inlet_spec.md`.

## Problem

AxiomPack had two strong but disconnected halves:

1. an older candidate-template blueprint/proof-gap path;
2. a new exact formula–model theory cartographer and anonymous navigator design.

The second design specified the internal campaign engine but left the public
research inlet implicit. During implementation, the first two-law magma
campaign began to look like the way a user would specify a domain:
family-specific Python constructed the signature, grammar, model universe, and
packet. That is acceptable for a reproducible plugin experiment and wrong as
the product boundary.

Without a unified inlet:

- a user cannot simply give AxiomPack a research direction;
- autonomous domain scouting has no typed handoff;
- the solver/navigator invocation point is unclear;
- family-specific adapters can leak into the kernel;
- the legacy candidate-template blueprint can be mistaken for frontier
  discovery;
- “deanchored” risks meaning “hardcoded by a Python author instead of a prompt
  author.”

## Decision

Introduce a sibling of autoformalization:

```text
direction/evidence
  → FrontierExplorationBrief
  → reviewed FrontierTheoryBlueprint
  → signed campaign packet
  → deterministic context construction
  → anonymous interactive navigator
  → boundary verification and context revision
```

The public orchestration function is `explore_axiom_space`. Human directions,
LeanMill residuals, autonomous scout proposals, and structure-first typed
inputs all enter through it.

The blueprint describes an exploration environment. In cold mode it contains
no candidate axioms. Magma becomes a registered optimized adapter and first
campaign, not an entrypoint.

The later category correction is now explicit: a compact pack and finite
equation--model geometry are instruments, not AxiomPack's identity. The
governing object is an agent-authored `TheoryProgram` with a lineage,
hypotheses, predictions, representation moves, counterexamples, and verifier
receipts. `compact_axiom_pack` preserves the calibrated minimal-basis profile;
`theory_program` does not inherit its independence, joint-only, or size-two
gates.

## Why this boundary

The user must be able to choose the region of mathematics without
choosing the answer. Primitive semantics and verification cannot be anonymous
to the compiler; candidate laws and interpretation labels can be anonymous to
the navigator.

This creates a testable deanchoring boundary:

- named direction permitted before freeze;
- typed semantics and resource bounds frozen;
- candidate-law leakage rejected;
- names removed from the cold navigator view;
- post-freeze interpretation kept separate.

It also controls cost: deterministic enumeration maps the affordable local
space; model calls are reserved for blueprint compilation, navigation, and
representation expansion.

## Relationship to existing surfaces

### Reuse

- `solver/autoformalize.py`: dispatch and independent faithfulness pattern;
- `theory_ir.py`: typed first-order signature/formulas;
- `finite_model.py`: executable finite semantics;
- `common/finite_incidence_context.py`: substrate-neutral theory geometry;
- `common/abstraction_functor.py`: alpha/gamma lowering discipline, inherited
  directly by `TheorySubstrateAdapter`;
- `common/cegis_membrane.py`: consumed counterexample accounting;
- `common/leaf_workbench_*`: interactive action/receipt boundary;
- `common/subscription_agent_runtime.py`: agent process/session runtime;
- `contracts/work_items.py`: conditional frontier consequences as ordinary
  theorem work;
- `solver/solver_core.py`: the single governed proof entry, including proof
  cache, premise retrieval, no-good memory, and banked-library reuse;
- `axiom_authority.py`: replay and promotion authority;
- `axiom_yield.py` and `research_signals.py`: matched attribution and query
  pricing.
- `common/information_yield_pricing.py`: named-baseline residual pricing shared
  with ARC probe selection.

### Preserve but relabel

`leanmill.axiom_pack_blueprint.v1` remains a warm compatibility inlet because
it requires candidate axiom templates. It cannot satisfy the cold frontier
blueprint schema.

### Adapter-only

`magma_law_universe.py`, magma isomorphism canonicalization, and the magma SMT
encoding serve the initial ETP-adjacent campaign. Generic kernel code must not
depend on them.

## Hard invariants

1. One public exploration inlet; no domain-specific CLI is the product API.
2. Cold frontier blueprints contain no candidate axioms or named axiom lists.
3. Natural language may author a proposal but never supplies executable
   semantics by itself.
4. Every primitive symbol lowers through a registered/tested adapter.
5. Context exactness is conditional on a complete signed census.
6. Names and sealed rows do not enter the cold navigator briefing.
7. Model calls propose or navigate; deterministic/independent verifiers decide.
8. Magma imports do not cross into generic context, journal, workbench, or
   orchestration interfaces.
9. The same role cannot compile, review, and ratify a blueprint.
10. Existing AxiomPack/LeanMill promotion authority remains the only promotion
    route.
11. A missing adapter becomes an `AdapterGap` and agent coding task; the agent
    cannot mutate the live registry or certify its own exactness.
12. Budget is an immutable composite contract with host-owned reservations and
    append-only usage/stop receipts; no model-authored message can raise a cap.
13. Wall time is a user cap, not a cross-run scientific comparison metric.
14. Navigation cannot spend resources reserved for boundary verification.
15. Budget and runtime policy belong to the frozen campaign definition; named
    profiles share the LeanMill campaign profile vocabulary.
16. Workbench UI state is projected from CLI actions and campaign/journal read
    models; the frontend does not create a second campaign state machine.
17. A conditional Lean consequence receives proof credit only through
    `solve_adhoc`; matched attribution may remove credit but cannot create it.
18. Boundary spend is permitted only for consequences surviving a named cheap
    baseline; conjunction-only closure alone is insufficient.
19. A no-candidate exit is host-receipted and bounded by the shared
    investigated-turn stagnation pressure; the navigator cannot self-certify
    refusal.
20. A named theory is blueprint data. Equation generation, finite isomorphism
    quotient, countermodel search, and source lookup are adapter properties;
    none creates a theory-named adapter identity.
21. New campaign packets bind the full reviewed blueprint as well as the
    context; boundary policy cannot drift beside signed context bytes.
22. A deterministic compact-pack control cannot silently navigate a
    `theory_program` campaign.
23. Formula expansion accepts full typed first-order formulas and conservative
    derived operations. A new primitive or abstraction requires a reviewed
    successor language; it cannot enter a frozen context as a formula.
24. Host-isolated lineages share frozen inputs and hard caps but no sibling
    candidate trace before freeze. Late synthesis is proposal-only and must
    replay in a fresh context.
25. Pack dependency, program prediction, representation lift, and knowledge
    alignment remain separate evidence coordinates.

## Implementation state at seam opening

Built and focused-test passing before this correction:

- substrate-neutral finite incidence context;
- canonical 410-law magma grammar through operation order three;
- complete size-2/3 magma census and isomorphism quotient;
- exact formula profiles, theory nodes, minimal bases, synergy, and witnesses;
- self-contained context snapshots;
- append-only campaign journal and materialized views;
- AxiomPack workbench environment and static environment resolver;
- witnessed context-aware conflict ledger;
- information-priced boundary query policy;
- targeted Z3 finite-table countermodels;
- conditional Lean consequence tasks and matched attribution;
- conservative definition and landscape-morphism prototypes;
- finite-protocol evidence-induced adapter;
- owned process-group timeout behavior;
- durable/idempotent calibration replay.

Deterministic full-context build observed locally:

- 410 canonical formulas;
- 19,699 labeled size-2/3 magma tables;
- 3,340 canonical model classes;
- 133 finite semantic formula profiles;
- 733 distinct theory nodes generated by presentations of size at most two;
- 83,845 unordered formula pairs;
- zero provider calls.

This is apparatus evidence only. It is not a discovery result.

## First frontier execution — 2026-07-10

The prepared campaign ran on the Hetzner Lean node from the canonical Markdown
inlet. The anonymous navigator froze a two-law presentation and a joint-only
consequence without seeing interpretation labels. The revealed equations were:

```text
x = x * ((x * x) * x)
x * x = (x * x) * x
target: x = x * (x * x)
```

No fixed-size countermodel was found at carrier sizes four or five. Lean proved
the unrestricted implication by rewriting the first premise with the second.
The full proof compiled; the same proof failed with no premises and with either
premise removed. Recheck receipt:
`6b2c9120f7dd677bd8392468ba6957ce753978b4afd4d54f77be6348f260189f`.

Post-freeze interpretation identified the premises as Equational Theories
Project Equations 99 and 359 and the target as Equation 8. Equation 359 rewrites
one subterm of Equation 99 to Equation 8 in one step. Interpretation receipt:
`5fc23935e44bc7aeb17674f71f8057a9295ef318a0160da4c7b4eb1c99b253c9`.

The execution path succeeded, but the selection objective failed: it rewarded
joint-only closure without pricing what a cheap deductive baseline already
explained, and the leaf contract required a finalist. The corrected host gate
now uses `leanmill.direct_equational_deduction.v2`; replaying the same frozen
context leaves this candidate with zero residual consequences and zero residual
bits.
The leaf may now return a receipted `reject_all`; three consecutive receipted
no-candidate attempts under the same frozen campaign/context surface stagnation
pressure, and a finalist resets the sequence.

The next residual-selection smoke froze `(x*x)*y = x*y` as a singleton because
the old scorer counted its generator and the direct instance
`(x*x)*x = x*x`. No boundary call ran. The v2 baseline removes generators,
receipts substitution instances, and requires deterministic residual replay at
the boundary. The frozen row is therefore a harness counterexample rather than
a mathematical finalist.

## Implemented correction

The generic universe protocol, typed brief/blueprint, static adapter registry,
compiler/review boundary, AdapterForge quarantine, unified
`explore_axiom_space` inlet, shared campaign CLI, and interactive navigator are
implemented. The 2026-07-10 interpretation added the missing scientific
boundary: residual information after a named cheap baseline, receipted
no-candidate termination, and residual-only boundary queries. The remaining
product projection is the Workbench frontend over existing CLI actions.

The portability slice now also generates complete bounded universal-equation
languages from typed total-operation signatures, quotients generic finite
structures under sort-preserving isomorphism while retaining multiplicity,
and runs signature-generic fixed-size SMT with host witness replay. A
non-magma unary/binary campaign exercises these paths and immutable snapshot
reuse without a family module. A fully conditioned inverse-semigroup preflight
collapsed to seven small isomorphism classes and was killed before navigation.
The viability-gated successor explores regular unary semigroups over the same
adapter; the domain remains campaign data, not a new identity.

## Build slices

### Slice A — typed inlet

- strict brief and blueprint dataclasses/schemas;
- cold-mode no-candidate-law validator;
- deterministic structure-first compiler;
- injected LLM compiler callback;
- independent review and executable preflight receipts.

### Slice B — adapter inversion

- generic universe/model-record protocols;
- generic context builder;
- static adapter registry;
- magma and protocol adapter registration;
- dependency test preventing generic→magma imports.

### Slice C — orchestration

- `explore_axiom_space` lifecycle and immutable attempt directory;
- compiler/reviewer/navigator dispatch injection;
- journal and packet wiring;
- legacy warm route explicit and separate;
- status/replay/cancel projection.

### Slice D — first campaign through the inlet

- freeze the magma direction/blueprint via the public path;
- reproduce the exact context;
- deterministic-control navigator parity;
- interactive anonymous navigator run;
- explicit R1/R2 two-formula presentations;
- larger-model and Lean boundary checks;
- post-freeze interpretation.

### Slice E — autonomous source

- scout emits a brief ranked by checkability/scarcity/information economics;
- same compiler and authority path;
- no scout-authored trust root or bypass.

## Update triggers

Update this seam on any change to:

- the public `explore_axiom_space` signature;
- budget schema, presets, phase reserves, or stop-receipt semantics;
- campaign-definition YAML or LeanMill named-profile semantics;
- Workbench server/CLI-action/frontend projection;
- brief or frontier-blueprint schema;
- adapter registry or extension authority;
- cold-view contamination policy;
- navigator invocation/session policy;
- exact-context claim boundary;
- legacy warm-route separation;
- first-campaign interpretation status;
- presentation-size bounds and verified-theory interpretation schema;
- any scientific result from the frontier campaign.

## Kill conditions

Revisit the architecture if:

- the blueprint compiler repeatedly cannot specify primitive semantics without
  hand-written adapters;
- the generic FOL adapter covers too little to avoid family-specific code;
- name stripping destroys the distinctions needed for productive navigation;
- deterministic theory maps do not improve query selection over direct agent
  conjecturing;
- the navigator’s choices add no information per verification cost over the
  frozen control;
- the same inlet cannot support both a mathematical and evidence-induced
  substrate without semantic coercion.

## Claim boundary

GP-251 may support a claim that AxiomPack implements a typed, replayable,
interactive frontier-theory exploration architecture. Novel mathematical
discovery, superior navigator performance, and general cross-domain efficacy
remain unproven until separate campaigns close.

## Implementation checkpoint — 2026-07-09

Completed in this build:

- `FrontierExplorationBrief`, strict `FrontierTheoryBlueprint`, cold manifest,
  compiler/reviewer separation, and executable adapter preflight;
- `explore_axiom_space` as the single campaign inlet, including structure-first,
  injected NL compiler, immutable replay, warm-legacy routing, and
  `blocked_adapter_gap`;
- generic finite-model-universe protocols and many-sorted labeled FOL adapter;
- magma inversion behind the static registry, with the reproducibility CLI now
  calling the public inlet;
- typed AdapterGap and AdapterForge quarantine flow; the coding agent uses the
  same durable subscription role surface and cannot update the registry;
- top-level `ztare.leanmill.prompts` for cross-LeanMill compiler, reviewer,
  navigator, AdapterForge, and AxiomPack prompts; solver prompt imports remain
  compatible;
- subscription compiler/reviewer/navigator bindings with durable response
  replay;
- paginated anonymous node/formula workbench and bounded interactive navigator;
- generic typed postfix frontier-formula codec;
- persistent owned-dispatch receipts and guarded calibration status/cancel;
- content-keyed pair-node materialization cache.

Verification:

- 124 focused tests pass;
- full order-three size-2/3 build through `explore_axiom_space` reproduced
  context `d22e5a390f117cbcbd4f1972dfb93d88b0e10db2bb5eaef1cf7b59c1f3e87206`;
- independent process replay matched the navigation digest
  `c6389b7fdf4a179618ec18d81863859ca973af107dae66f0fda3a1a621d964da`;
- both build and replay used zero provider calls.

Artifact:
`/private/tmp/axiompack_gp251_public_inlet/attempt-8ec6c294f93a41e3a694615a214f4c23`.

Open at the 2026-07-09 checkpoint:

- wire finite-protocol/evidence-induced construction through the public
  campaign builder rather than only the shared incidence protocol;
- add the main `ztare` CLI projection over `explore_axiom_space`;
- exercise AdapterForge on a missing semantics-rich substrate and pass actual
  code-review/registry authority;
- run a paid anonymous navigator only under an explicit campaign decision;
- execute selected size-4/5 and conditional Lean boundary queries;
- perform post-freeze ETP/literature interpretation and close the scientific
  outcome.

## Implementation checkpoint — 2026-07-10

The remaining engine slices above are now implemented:

- one inspectable Markdown campaign binds its research body to shared YAML
  frontmatter for lane, evidence, runtime, budget, and scientific stop rules;
  named profiles are shared with the autoformalization launcher;
- the authoring form may omit detailed caps and use only a named profile;
  preparation materializes the full contract, and unused completed-phase
  allocation rolls forward without consuming protected boundary reserve. The
  allocation policy is explicit in the campaign digest;
- host-owned reservations cover compilation, context construction, navigation,
  expansion, and boundary work, with durable stop receipts;
- the brittle compact budget-override string was removed; overrides use YAML,
  while a named profile remains a one-word convenience;
- formal-model and evidence-induced campaigns share `TheoryLandscapeContext`;
  the generic finite-evidence adapter exercises the latter through the public
  inlet;
- AdapterForge resumes a typed adapter gap, runs host conformance plus
  independent review, and emits only a quarantined proposal;
- larger-model/raw boundaries, context-epoch proposals, lifecycle actions, and
  public CLI actions are wired and replayable;
- a fresh campaign can reuse a complete prior context by digest after checking
  its signature, base theory, adapter, formula universe, and model strata;
- context snapshots now persist materialized incidence bitsets, so a reused
  modern snapshot does not reevaluate every formula/model cell;
- conditional Lean work now enters `WorkItem(kind="theorem_goal")` and the
  canonical `solve_adhoc` pipeline. The separate AxiomPack proof prompt/role was
  removed. Full/empty/leave-one-out replay begins only after a governed full-arm
  closure;
- a scoped hook on the existing subscription runtime meters every nested
  `solve_adhoc` dispatch against the same campaign ledger before launch; the
  prepared role explicitly disables proposer-pool fanout and subscription
  failover;
- exact in-context navigation stays on incidence bitsets. Semantic premise
  retrieval, proof cache, faithfulness/no-good memory, and family-library
  compounding activate at the ordinary Lean solver boundary;
- the completed calibration batch was recovered from signed historical bytes:
  ten proposed rows, one pre-check duplicate, nine signed checked rows, zero new
  provider calls.

Verification:

- 181 focused unit/integration/E2E tests pass;
- the bounded public-inlet smoke at
  `/private/tmp/axiompack_gp251_smoke_20260709/attempt-94ac307788cb4c4697eddffddd8bbb67`
  froze 3 finalists and 4 common-action boundary queries with zero provider
  calls;
- the earlier complete order-three context artifact remains reusable at
  `/private/tmp/axiompack_gp251_public_inlet/attempt-8ec6c294f93a41e3a694615a214f4c23`;
- recovered calibration rows are at
  `/private/tmp/leanmill_axiom_pack_band_review/prepared-40a1d740621546f0/row_recovery.json`.
- the zero-provider execution preflight for the held campaign passed against
  the typed blueprint and materialized 410-formula/3,340-model context; its
  frozen campaign, context, contract, and receipt are under
  `research_areas/pre_registrations/axiompack_gp251_smoke_20260710/`;
- bounded `deploy/vps_run.sh leanmill-*` actions project the canonical campaign
  lifecycle onto the Hetzner Lean node. Inputs must be in the curated sync
  manifest; attempt output stays on the node outside that manifest.

Open implementation work is now limited to the Workbench frontend projection
and any migration/import convenience for older context snapshots. Open
scientific work is the approved anonymous navigator campaign, selected size-4/5
and governed Lean queries, and post-freeze interpretation.

## Continuation — residual attempts and interpretation

The held campaign has now run through navigation, fixed-size Z3, governed Lean,
matched premise attribution, governance recheck, and post-freeze source review.
No discovery claim survives:

- attempt 1 selected a one-contextual-rewrite consequence; residual baseline
  replay removes it;
- attempt 2 selected a premise and its direct substitution instance; v2
  substitution receipts remove it before boundary spend;
- attempt 3 selected `x = x ◇ ((x ◇ y) ◇ x)` implying
  `x = x ◇ (x ◇ x)`, passed size-four/five Z3 and governed Lean attribution,
  then mapped post-freeze to the catalogued ETP Equation 101 → Equation 8
  implication.

Attempt 3 exposed that `pack_arity: 2` was only an upper cap. A campaign can now
freeze `navigator_contract.presentation_size` minimum/maximum bounds. The cold
manifest, interactive freeze, journal recovery, signed packet, and
interpretation replay enforce them; old attempts default to one-through-cap and
retain their digests. The next two-law campaign must bind `{minimum: 2,
maximum: 2}`.

LeanMill now has `theory_interpretation.py`, a post-verification composer. It
binds operational and bounded-model facts, governed proof attribution,
source-based alignment, and the human gloss. The post-freeze schema additionally
asks for the key idea: premise roles, the useful recombination, and the crossed
invariant or obstruction. Mechanism evidence references must occur in the
frozen verifier packet. The mechanism projects to the shared
`ConstraintFingerprint`/`research_isomorphism` input shape, but any transported
analogy remains advisory until a destination-side discriminator replay passes.

The next scientific slice is therefore not another single-law pass over a
completed implication graph. It is either an exact-two magma campaign with a
post-freeze external-knowledge residual, or a user-supplied executable
constraint substrate entering through an existing adapter/AdapterForge and the
shared SMT/raw/Lean boundaries. The Workbench frontend projection remains
product work.

## Portable finite kernel and regular-unary smoke — 2026-07-10

The finite equational path now compiles from a typed signature rather than a
named family module. `generic_fol_finite.v1` provides complete bounded equation
generation, sort-wise isomorphism quotienting with labeled multiplicity,
generic finite SMT, immutable replay, and exact-context singleton ablation.
Adapter capabilities remain properties; family names and base equations remain
campaign data.

The fully conditioned inverse-semigroup gate was killed provider-free at seven
canonical size-two/three models. Its regular-unary successor passed at 47
canonical models and 71 formulas. The anonymous navigator froze a local
recovery law plus constant selector; exact singleton countermodels and governed
Lean verified that the pair forces right projection. Post-freeze interpretation
therefore classified it as selector collapse to a right-zero structure.

This exposed a portable baseline gap. `finite_structure_baseline.py` now
recognizes constant/projection/full/empty finite templates, conditions residual
entropy on their joint support, and subtracts their closure. Repricing the
frozen context moves all ten prior residual consequences to baseline with zero
provider calls. All remaining positive exact-two residuals force unary
identity, and none clears the existing campaign information-per-cost threshold.
The operation-order-two context should not be rerun.

Preflight and execution also share `compile_campaign_brief`, eliminating a
blueprint-ID mismatch caused by execution-only budget-preference bytes. Focused
kernel and E2E tests pass; the Workbench frontend projection remains separate.

## Cycle-structure outcome and contrastive refinement — 2026-07-10

The 88-model cycle-structure campaign completed through Sol 5.6 medium
navigation, size-six/seven Z3, Isabelle, governed Lean, exact singleton
ablation, and governance replay. Sol authored associativity, whose size-five
profile duplicated an existing formula profile. The frozen winner reduced to a
common permutation, and its first target was the corresponding involution law.
Disposition: routine reconstruction; no theorem-novelty claim. Canonical
result: `research_areas/pre_registrations/axiompack_cycle_structure_frontier_20260710/sol_medium_result.md`.

The discriminating failure was representation access. The cold workbench
exposed separation IDs but no anonymous structures from a class conflated by
the current formula language. `FiniteIncidenceContext` now computes
language-relative observational object classes. A single generic workbench
action pages same-stratum anonymous pairs for both formal and evidence
contexts. A pair-bound typed formula enters a new context epoch only after
exact host evaluation separates the pair; this finite-profile witness carries
no proof, external-knowledge, or promotion authority.

Provider accounting now excludes three recognized CLI rejections that occur
before inference and conservatively charges unfamiliar failures. Campaign
status projects the exact outstanding phase/action reservation, replacing
process inspection as the sparse-output progress surface. Cross-domain
`research_isomorphism` feedback stays disabled until a matched destination-
selection experiment shows higher destination-side discriminator yield than a
cold arm.

The Sol-high contrastive successor exercised the new action. From an anonymous
pair agreeing on all 210 seed formulas, it authored
`op2(op0(x,y)) = op0(op2(x),op2(y))`; exact evaluation certified a new finite
profile. The explicit successor transition produced a 211-formula, 12-profile,
20-node epoch. Exhaustive host pairing found no conjunction-only consequence
with any seed formula, so the coordinate has zero residual exact-two use and no
boundary stage is due. Canonical result:
`research_areas/pre_registrations/axiompack_cycle_structure_frontier_20260710/sol_high_contrastive_result.md`.

The transition established the runtime identity boundary. Source finalists stay
archived under their source context and epoch; `continue-epoch` consumes the
outbound formula request and begins a clean navigator trace. Exact prompt bytes
are now durable provider-input artifacts. Historical result-only traces replay
through the deterministic workbench and idempotent journal. Candidate-free
budget exhaustion materializes `budget_stopped` without acquiring
`reject_all` authority.
