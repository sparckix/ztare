# GP-251 — AxiomPack Frontier Exploration Inlet and Theory Inventor

## Status

Active implementation spec · updated 2026-07-12.

The portable semantic and verification kernel is implemented. The initial
compact-pack profile, formula epochs, boundary attribution, interpretation,
and explicit successor transition remain available. The active slice removes
the first calibration campaign's accidental ceiling: the navigator can now
author full first-order formulas, introduce conservative derived operations,
request a new executable theory language, and select theory programs without a
joint-only or size-two requirement. The host-isolated lineage kernel is also
implemented, including campaign routing, durable resume, late comparison,
sibling-local scientific stopping, and proposal-only synthesis into a fresh
context epoch. Exact and sampled contexts share the packet inlet while
retaining distinct claim scopes. A deterministic proposal-only policy now
profiles frozen programs against one another, excludes silence and vacuity,
and routes explicit hold/refute disagreements through the ordinary full-program
boundary executor. The remaining scientific bar is a
consequential campaign that compounds at least two authored coordinates and
lifts a discriminating prediction beyond the seed chart. M6 remains a later
Workbench projection.

The adaptive representation/search join is now active. Late synthesis receives
a receipt-bound portfolio built from semantic wave-image growth and the shared
residual-information coordinates. It chooses a typed continuation mode rather
than receiving a host-selected winner; that mode enters the next isolated wave,
whose first consequence is receipted as followed, diversified, leaf-revised,
or unconsumed. This closes the prior descriptive-only edge from information/QD
measurement to search behavior without turning finite geometry into the
campaign controller.

The first adaptive compositional campaign exercised that join on the exact
23-model size-four context. Two admitted leaf-authored coordinates increased
the panel from 210 to 212 formulas and from 10 to 12 semantic profiles. The
strongest tested composition was premise-sensitive but had zero residual yield
beyond the declared cheap baseline. Late synthesis therefore selected another
current-context wave; its contrast diagnostic executed, and the dependent
GPT-5.5 turn timed out before returning a typed formula. The campaign retired
unresolved with no finalist and no novelty claim. This exposed one lifecycle
gap: a leaf transport failure could unwind before materializing the trace.
Navigator calls now close that outcome with a typed failure receipt, preserve
all prior action receipts, and feed them into the adaptive consequence record.

The size-five prototype preflight passed provider-free on 2026-07-11 with
`88` canonical models and `11` semantic profiles. The executable compositional
campaign subsequently separated a size-four orientation stratum (`23` models,
`10` profiles) from withheld size-five/six boundary strata; the typed blueprint
is the sole owner of those carrier sizes.

The first compositional execution revealed that its prose objective had not
entered the typed blueprint: the cold manifest still carried the earlier
exact-two eigenquestion, and finalist coverage could emit `target_reached`
without an authored coordinate. The kernel now separates inner program
validity from outer campaign success. A delegated
`late_lineage_objective_review` is visible anonymously to the navigator; the
late synthesis leaf must bind frozen program IDs and either authorize boundary
spend or return a next discriminator. The latter automatically opens another
host-isolated wave under the same context and campaign ledger. Each wave owns a
fresh durable call namespace, preventing a continuation from replaying the
prior wave's decisions. This is a hybrid
boundary: the leaf judges research sufficiency, while the host validates
identities, admissions, receipts, and caps.

This is the canonical implementation specification for frontier AxiomPack.
It supersedes the scratch design at
`/private/tmp/axiompack_frontier_theory_discovery_spec.md` while preserving its
finite formula–model context, semantic theory-node, interactive navigator, and
boundary-verification design.

Paired seam:
`research_areas/seams/engine/lean/GP-251_axiompack_frontier_exploration_inlet_seam.md`.

## 0. Decision

AxiomPack has one public research inlet:

```python
explore_axiom_space(
    direction: str | FrontierExplorationBrief,
    *,
    evidence_refs: Sequence[str] = (),
    source_mode: str = "human_directed",
    compiler: FrontierBlueprintCompiler,
    navigator: TheoryNavigator | None = None,
) -> FrontierExplorationRun
```

A user, a LeanMill residual router, or an autonomous domain scout
supplies a research direction. A blueprint compiler lowers that direction into
a typed and reviewable exploration environment. The host then constructs the
declared formula–model context and invokes an iterative navigator over an
anonymous view of the resulting theory landscape.

The direction specifies where and how to search. In the cold frontier mode it
does not supply candidate axioms.

### 0.1 User job and campaign lifecycle

The interaction is campaign-shaped, matching LeanMill autoformalization:

1. write one campaign Markdown body describing a mathematical region,
   phenomenon, examples, and exclusions;
2. optionally add `leanmill.campaign.v1` frontmatter with `lane: axiompack`, a
   named profile, and any budget/stop/runtime overrides;
3. launch through `leanmill campaign campaign.md`;
4. inspect live context coverage, actions, costs, finalists, counterexamples,
   proof status, and stop reason;
5. approve or decline costly boundary work through `leanmill verify`;
6. replay, compare, continue in a new epoch, promote, or retire the campaign.

The Markdown body is the mathematical payload. YAML frontmatter is the shared
LeanMill control envelope: lane, evidence refs, budget/stop, and runtime role
overrides. The same named profiles and ledger serve autoformalization and the
frontier lane. Runtime overrides dispatch through `subscription_agent_runtime`.
Existing frontmatter-free autoformalization blueprints keep their established
CLI/kernel behavior.

Autoformalization and AxiomPack are sibling compilation pipelines:

- autoformalization compiles natural language into one theorem target;
- AxiomPack compiles natural language into a theory-search environment.

They reuse dispatch, structured-output, faithfulness, authority, and LeanMill
verification infrastructure. They do not share an output schema. A conditional
Lean consequence becomes the existing `WorkItem(kind="theorem_goal")` and
enters `solver_core.solve_adhoc`; AxiomPack has no private prover lane.

## 1. North star

The governing object is an autonomous theory inventor. It enters an
underexplored domain, invents or revises representations and hypotheses without
being handed the familiar theory, uses counterexamples and formal systems to
evolve them, and returns ideas that change what can be derived or tested.

An AxiomPack is one crystallized presentation produced by that process. It is
not the process's identity. A finite formula--model context is one adjudication
instrument. It is not the hypothesis horizon.

AxiomPack should let a user say, for example:

> Explore compact axiom systems for finite reversible update structures with
> two composable operations. Prefer theories whose consequences arise jointly.
> Do not seed the search with named textbook axiom lists.

The compiler may use the named direction to establish primitive semantics and
verification. Once the campaign freezes, the cold navigator sees anonymous
symbols, typed formula structure, models, countermodels, closures, costs, and
receipts—not literature labels or established axiom-system names.

The autonomous form uses the same inlet. A scout proposes a direction; it does
not gain a separate authority path.

### 1.1 Theory programs and evidence coordinates

The navigator evolves a `TheoryProgram`:

```text
lineage identity
+ ordered theory-language moves
+ current hypothesis presentation
+ explicit discriminating predictions or experiments
+ counterexamples and verifier receipts
```

The system keeps four coordinates separate:

1. **representation lift** — a formula, definition, observable, quotient, or
   abstraction distinguishes cases the prior language aliased;
2. **deductive lift** — the program entails a prediction beyond its declared
   cheap baseline;
3. **consequential lift** — the prediction survives a withheld regime or
   changes a proof/experiment frontier;
4. **knowledge alignment** — post-freeze review classifies recovery,
   recombination of recorded components, or an unmapped candidate.

No scalar collapses these coordinates. A new finite profile does not imply a
useful theory; a proved implication does not imply a new idea; an unsuccessful
literature search does not imply novelty.

### 1.2 Goldilocks boundary

The leaf chooses representations, hypotheses, theory size, experiments,
lineage strategy, and when to request a language change. The host owns typing,
deterministic lowering, context/lineage identity, exact or declared sampled
evaluation, counterexample replay, budgets, and formal verification.

Interaction is a durable role-local loop rather than a sequence of unrelated
completions. A lineage keeps one subscription session across search waves;
lineages and attempts never share sessions. Each host action returns a typed
receipt into that session. A budget edge can stop the next turn but cannot
erase the preceding completed decision, and recovery binds any synthesis only
to the exact frozen input digest it reviewed.

`compact_axiom_pack` remains an explicit selection profile for questions about
small jointly necessary bases. `theory_program` is the default for new frontier
directions. Compact-pack independence, exact-two, and joint-only gates cannot
govern theory-program campaigns.

## 2. Architectural correction

The earlier scratch spec correctly identified the exact semantic context as
the missing center, but left the product entrypoint implicit. That ambiguity
made the first magma experiment look like the way users specify mathematics.

The corrected layers are:

| Layer | Responsibility |
|---|---|
| research direction | human, residual router, or scout says where to explore |
| blueprint compiler | NL/evidence → typed exploration environment |
| substrate adapter | executable semantics for a signature or evidence surface |
| exact/sampled context kernel | one replaceable object × hypothesis adjudication chart |
| navigator | evolves theory programs and chooses consequential boundary questions |
| expansion author | proposes formulas, definitions, language changes, or adapter refinements |
| lineage layer | isolates independent theory genealogies and permits only receipted late comparison |
| verifiers | finite census, SMT, Lean, or raw-domain checker |
| authority | freeze, replay, promotion, and context-epoch transitions |

Magma is the first campaign plugin. It is not a kernel interface and it is not
the public entrypoint.

## 3. Sources of research direction

All sources compile through `explore_axiom_space`.

### 3.1 Human-directed

A user supplies a domain, phenomenon, structural question, examples,
or desired observation boundary. Candidate laws are optional only in explicitly
warm/domain-conditioned mode.

### 3.2 Residual-directed

LeanMill converts recurring proof gaps, failed abstractions, or counterexample
families into a direction. The existing proof-gap inlet becomes one source of
campaign pressure, not the definition of AxiomPack eligibility.

### 3.3 Scout-directed

An autonomous scout ranks domains by:

- checkability and available raw verifiers;
- scarcity of systematic exploration;
- finite or otherwise executable local semantics;
- representation headroom;
- expected information per verification cost;
- contamination risk and available cold-view transformation.

The scout emits a `FrontierExplorationBrief`. It cannot freeze its own blueprint
or verify its own proposals.

### 3.4 Structure-first

A campaign author may provide a typed signature and grammar directly with no natural
language domain name. This is the cleanest anonymous census route.

## 4. FrontierExplorationBrief

The permissive human-facing input is:

```text
schema: leanmill.frontier_exploration_brief.v1
brief_id
direction
source_mode: human_directed | residual_directed | scout_directed | structure_first
evidence_refs[]
requested_mode?: anonymous_signature_census | evidence_induced |
                 domain_conditioned | proof_gap_conditioned
deanchoring_intent
resource_envelope?
forbidden_shortcuts[]
created_by
```

Only `direction`, `source_mode`, and provenance are mandatory at this surface.
The brief makes no exactness or promotion claim.

## 5. FrontierTheoryBlueprint

The strict compiler output is:

```text
schema: leanmill.frontier_theory_blueprint.v1
blueprint_id
brief_digest
mode
eigenquestion
signature
primitive_semantics
base_axioms[]
base_theory_status
adapter_id
adapter_config
formula_grammar
model_or_observation_strata
pack_arity
collapse_controls[]
visible_evidence_manifest
sealed_evidence_manifest_digest
deanchoring_policy
navigator_contract
query_budget
stop_rule
verification_plan
codec_versions
authority_refs[]
compiler_receipt
semantic_review_receipt
executable_preflight_receipt
frozen: true
```

Hard invariants:

1. `candidate_axioms`, `candidate_axiom_templates`, named axiom lists, and
   hidden targets are forbidden in `anonymous_signature_census`.
2. Primitive operations and relations require executable semantics. A symbol
   described only in prose cannot enter a census.
3. The adapter must come from the static registry or carry a separately tested
   adapter-extension receipt.
4. Exact contexts require a complete census receipt. Sampled panels cannot be
   relabeled exact after the fact.
5. The visible manifest cannot contain sealed bytes, literature labels, or
   interpretation attachments.
6. The same role cannot author the blueprint and supply its semantic/executable
   trust root.
7. A compiler failure produces a typed blocked result, not a guessed campaign.
8. `pack_arity` is the representable maximum. If the direction requires a
   minimum or exact number of interacting formulas,
   `navigator_contract.presentation_size` freezes integer `minimum`/`maximum`
   bounds within that cap. Navigation, recovery, the signed packet, and
   interpretation enforce the same bounds.
9. `formula_grammar` defines the deterministic seed chart for an exact
   context. It is not the campaign's global hypothesis horizon. A cold
   navigator may submit one signature-bound first-order formula through the
   typed postfix codec, optionally using derived operations that expand into
   the prior signature. Admission mints a new immutable context epoch and
   recomputes every truth profile and theory node before navigation resumes.
   A needed primitive, observable, quotient, or abstraction becomes an
   outbound theory-language request for a newly reviewed blueprint. No formula
   or language change is spliced into a frozen context in place.
10. Object classes induced by the current formula truth vectors are
    language-relative observational classes. They never replace the adapter's
    declared object identity or isomorphism policy. A formula proposed against
    an anonymous same-stratum pair enters a new epoch only when exact host
    evaluation separates the pair.

The older `leanmill.axiom_pack_blueprint.v1` requires candidate templates and
remains the legacy warm/proof-gap compatibility route. It must never be silently
treated as a frontier blueprint.

## 6. Blueprint compilation lifecycle

The lifecycle mirrors autoformalization’s useful boundaries:

1. **Acquire direction.** Freeze the brief and referenced evidence digests.
2. **Compile.** A capable LLM or deterministic parser proposes a typed
   `FrontierTheoryBlueprint`.
3. **Semantic review.** An independent role checks whether the typed signature,
   primitive semantics, and observation surface preserve the user’s
   direction without inserting candidate laws.
4. **Executable preflight.** The host validates types, adapter availability,
   grammar finiteness, model counts, bounds, codecs, and raw checkers.
5. **Cold-view transform.** Remove names and interpretation attachments; bind
   anonymous IDs to the reviewed blueprint.
6. **Freeze and sign.** Mint the campaign packet before model or navigator work.
7. **Construct context.** Deterministic host work precedes agent navigation.

This is a compilation pipeline, not a conversation in which the model’s prose
becomes semantics.

## 7. Campaign mode router

### 7.1 `anonymous_signature_census`

Use when a finite typed signature, grammar, and complete local model census are
available. There is no hidden true theory. Search possible theories.

### 7.2 `evidence_induced`

Use when raw observations and executable hypotheses are available. The context
is observation × hypothesis. Exact closure is allowed only when both the
observation universe and the hypothesis language are complete under the frozen
declaration.

### 7.3 `domain_conditioned`

Use when a named mathematical or nonmathematical interpretation matters.
Semantic-fidelity review remains visible in the authority record. The navigator
may still receive a cold projection after compilation.

### 7.4 `proof_gap_conditioned`

Use the existing registered-gap machinery to form a direction and evidence
manifest. It compiles into the same frontier contracts.

The router is deterministic after the brief is typed. Ambiguity returns a
compiler question or blocked receipt.

## 8. Adapter architecture

Evidence-induced substrates consume `TheorySubstrateAdapter`, which now
inherits the shared `AbstractionFunctor` alpha/gamma contract, and lower into
the finite-incidence interface. Typed formal substrates already begin after
alpha: their signature, formulas, and models are kernel IR, so their registered
backend supplies formula/model construction and verifier capabilities directly
rather than inventing a ceremonial raw-state lowering. Both paths converge on
`TheoryLandscapeContext`. Neither imports a family name.

Minimum adapter responsibilities:

```python
abstract(raw_evidence) -> AbstractState
signature(state) -> TheorySignature
base_axioms(state) -> Sequence[AxiomFormula]
build_context(state, bounds) -> FiniteIncidenceContext
lower(theory, raw_state) -> prediction
check_raw(prediction, observation) -> receipt
```

This boundary keeps abduction and transport separate. ARC-style spec abduction
induces executable transition programs from observations; AxiomPack induces
small theory presentations from a formula-model landscape. They share the
observation-by-hypothesis incidence algebra, information pricing,
counterexample receipts, and raw-disposal rule, but not a substrate-specific
candidate generator. `FiniteProtocolTheoryAdapter` is the existing executable
bridge between those orientations.

The group-action parallel is also explicit but not prematurely unified. ARC
shape identity is an orbit under a declared geometric group such as `D4` plus
translation/scale normalization. Finite-structure identity is an orbit under a
product of carrier symmetric groups acting on typed tables. Both quotient
nuisance labels before scoring, but their action and normalization semantics
differ; extracting a common transform loop now would hide more than it shares.

Registry policy:

- `generic_fol_finite`: default for finite many-sorted first-order signatures;
- `finite_protocol`: evidence-induced executable transition programs;
- `magma_equational`: optimized first-campaign plugin;
- later cycle-set/Yang–Baxter and other semantics-rich adapters;
- `adapter_extension`: workbench proposal that must compile, self-test, and pass
  independent review before registry inclusion.

Most algebraic domains should be data/configuration over the generic adapter.
A new Python module is justified only by new executable semantics,
canonicalization, or verification—not by a new theory name.

Adapter identity and adapter properties are separate. A named theory such as
an inverse semigroup is a signature plus frozen base equations in a campaign,
not an adapter. Host-enumerable equation grammar, sort-wise isomorphism
quotient, fixed-size countermodel search, and source-relation lookup are
capabilities of an adapter. Requesting a missing property creates a
capability-shaped gap while preserving the substrate identity.

For finite total-operation signatures, the default cold path is
`generic_fol_finite.v1` plus
`leanmill.universal_equation_grammar.v1`. The host exhaustively generates the
declared operation-order band, quotients variable renaming and equation-side
exchange, validates every formula against `theory_ir`, and fails rather than
truncate when `max_formulas` is exceeded. The same adapter canonically
quotients finite structures under one carrier permutation per sort and retains
labeled multiplicity in its completeness receipt. A campaign may explicitly
request labeled models when labels have semantics; a theory name never selects
that policy.

### 8.1 AdapterForge: missing adapters are solver tasks

A missing adapter is not automatically a human implementation task. The
blueprint compiler first attempts to express the requested substrate through
the existing generic adapters. If no registered adapter can lower the declared
semantics, compilation stops with:

```text
AdapterGap
  gap_id
  brief_digest
  proposed_adapter_id
  primitive_semantics_contract
  raw_fixture_refs[]
  required_context_kind: exact | sampled
  required_operations[]
  required_receipts[]
  forbidden_authorities[]
  acceptance_tests[]
```

The orchestrator may then dispatch an `AdapterForge` coding agent, analogous to
a Lean solver working against a typed target and compiler:

1. stage the adapter protocol, frozen fixtures, and acceptance tests in a
   bounded workspace;
2. give the agent tools to implement and run the adapter locally;
3. require structured source, manifest, self-test, and fixture receipts;
4. run host-owned conformance, completeness/claim-boundary, determinism,
   serialization, and adversarial tests;
5. send the implementation and the original direction to an independent
   semantic reviewer;
6. place a passing adapter in the registry-proposal quarantine;
7. admit it only through code review/authority, then begin a new immutable
   blueprint attempt using the registered adapter.

The agent may write code, tests, codecs, canonicalizers, and raw-checker
bindings. It may not mark its adapter complete, declare a census exact, add its
own trust root, or mutate the live registry. A proposal that only restates the
domain in Python without executable lowering fails.

For a theory-language coordinate capability, the manifest also declares one to
four scalar `observable_paths`. Only those values enter formula–model geometry
and information-yield pricing. Raw profiles, operation tables, model IDs,
induced tables, and counterexample details remain audit witnesses. This
observable/witness split prevents a capability from earning apparent yield by
returning a near-serialization of each model. Host conformance checks exact
object coverage and deterministic replay; independent review receives the
source/test bytes and hashes, not filenames or self-test prose alone.

This is a first-class branch of `explore_axiom_space`, surfaced as
`blocked_adapter_gap` until the adapter is independently admitted. Human
implementation remains an override, not the default architecture.

Theory-language continuation has one compiler-first state machine. Navigation
only freezes the typed request against its exact source context and epoch. The
continuation tries registered adapter capabilities before AdapterForge and
consumes a closed outcome algebra: `compiled` admits a successor epoch,
`rejected` returns content-bound feedback to search, and `unavailable` creates
the typed gap. A reviewed campaign-local finite-model functor must map every
source object exactly and cannot mutate the global registry. Its image context
is exact relative to the frozen source only; fixed-size target-model generation
is withheld until a separately reviewed generative/roundtrip semantics exists.
That semantics is a content-addressed materialization of the shared
`AbstractionFunctor` relation plus generated model pairs, not a substrate family
in the host. AdapterForge stages the data; LeanMill imports no generated Python.
Admission binds the frozen request/context, checks exact source coverage,
raw→alpha→gamma roundtrip up to declared sortwise isomorphism, every raw base
law, canonical generated abstract models, and an independent review of the
exact host receipt. A witnessed countermodel may enter larger-model search, but
batch exhaustion returns `unknown`; generator completeness remains a separate
mathematical proof obligation. A fitted alpha image or unreviewed materialized
relation returns a typed unavailable outcome.
Direct and forged compilation, CLI continuous mode, Workbench callers, and the
named VPS launcher all use this state machine.

### 8.2 Executable abstraction inlet

A user may bring a Rust enumerator, functional constraint program, SMT
encoding, CAS script, transition checker, or other executable semantics rather
than a finished formal theory. That artifact supplies adapter evidence; it does
not require another AxiomPack engine. The compiler first maps it onto a
registered adapter. If that fails, AdapterForge binds the artifact and frozen
fixtures to `TheorySubstrateAdapter` and proposes the missing codec/checker.

The resulting campaign reuses LeanMill's existing boundaries: exact or sampled
incidence, SMT countermodels and decidability routing, replay against the raw
checker, conditional `solve_adhoc` work, premise attribution, and post-freeze
interpretation. Substrate code owns executable semantics and efficient
enumeration. AxiomPack owns theory identity, residual selection, experiment
choice, receipts, and promotion. A new domain-specific Python family is not the
user interaction model.

## 9. Formula–model context kernel

Freeze a finite hypothesis/formula universe `F`, object/model universe `M`,
base mask `B`, and incidence relation `m ⊨ f`.

For a presentation `P ⊆ F`:

```text
Ext(P) = {m in B : m satisfies every f in P}
Cl(P)  = {f in F : every m in Ext(P) satisfies f}
```

A semantic theory node is identified by:

```text
hash(context_hash, extent_bits)
```

An AxiomPack is a minimal presentation of a theory node, not the node itself.
The context computes implication, bounded equivalence, redundancy,
independence witnesses, separation objects, minimal generators, and joint-only
consequences by bitset operations.

Do not materialize the full concept lattice by default. Materialize nodes
generated under the frozen pack-arity bound and compute other closures lazily.

### 9.1 Exactness boundary

Exact finite means complete enumeration under the signed declaration. It does
not mean universal mathematics.

| Surface | Permitted claim |
|---|---|
| complete finite context | exact bounded closure/equivalence |
| sampled panel | behavioral routing/fingerprints only |
| targeted model finder | concrete refutation; search failure may be unknown |
| kernel-checked proof | unrestricted implication for the rendered statement |

These statuses remain separate in every archive and UI.

### 9.2 Context epochs

Adding a model or formula mints a new context hash and epoch. Old receipts stay
replayable under the old hash and never silently validate in the new epoch.

## 10. LLM and agent invocation

The system spends model calls only where agency can change the search.

### 10.1 Blueprint compiler

One structured compilation task, with optional clarification/refinement. It
sees the named direction and relevant source evidence.

### 10.2 Independent blueprint reviewer

Checks semantic preservation, candidate-law leakage, executable primitive
meaning, and suitability of the proposed cold transform.

### 10.3 Theory navigator

A bounded, optionally warm agent session receives the anonymous context
briefing and shared LeafWorkbench environment. It repeatedly inspects nodes,
countermodels, closures, and query costs before freezing finalists. A freeze
includes an ordered, nonempty subset of the previewed residual consequences as
`boundary_target_ids`; this is the navigator's choice of which expensive
questions deserve spend. The host validates that every nominated target is a
residual consequence, then preserves the order.

This follows LeanMill's move-selection split. Mechanical context construction
surfaces the choices, the navigator selects the presentation and boundary
question, and deterministic executors validate and aggregate the resulting
receipts. Countermodel-first ordering and kernel acceptance remain host-owned
because they define cost control and evidence authority rather than research
strategy.

When the current formula language conflates distinct objects, the navigator
may inspect a bounded anonymous same-stratum pair from one observational class
and author a coordinate intended to separate it. The host evaluates that
coordinate exactly. Pair separation proves only that its finite truth profile
is absent from the current panel; description cost, deductive residual,
cross-stratum persistence, formal proof, and knowledge status remain separate
questions.

### 10.4 Expansion author

Invoked only when the current grammar cannot express a useful distinction. It
may propose:

- one typed frontier formula;
- one conservative definition;
- an abstraction refinement;
- a typed structural transport;
- an adapter-extension proposal.

### 10.5 Verifiers

The host, SMT solver, Lean kernel, Isabelle kernel, or raw-domain oracle
verifies proposals. Provider output never supplies its own trust root.

Lean verification uses the ordinary solver leaf and therefore inherits the
proof cache, semantic premise shelf, no-good/refutation memory, banked lemma
library, statement-integrity checks, matched negative control, and governance
kernel. The AxiomPack boundary owns only conditional task construction and
matched premise attribution.

For a typed first-order finalist, the existing Isabelle/Sledgehammer service
may run as an optional formal peer before the Lean call. The translation starts
from `TheorySignature` and `Formula`, not from parsed Lean text: sorts become
HOL type variables and signature symbols are universally quantified. A
Sledgehammer suggestion is `unresolved` until the complete theory rebuilds in
Isabelle without skipped-proof tokens. Isabelle evidence can prioritize or
corroborate a target, but cannot mint Lean proof credit or AxiomPack promotion.
The shared `cross_substrate_consensus` surface records agreement or an explicit
kernel disagreement; unavailable and unresolved attempts never enter that
reconciliation as negative mathematical votes.

### 10.6 AdapterForge agent

Invoked only from a typed `AdapterGap`. It receives the shared adapter protocol,
frozen raw fixtures, exactness target, and executable acceptance suite. Its
deliverable is an adapter implementation proposal, not candidate axioms. The
subscription-agent runtime supplies the coding/tool loop; host tests and an
independent reviewer own admission.

### 10.7 Verified-theory interpretation

`theory_interpretation.py` is a LeanMill-wide post-verification surface, with
AxiomPack as its first complete caller. It must explain the candidate's key
idea (the useful recombination), not merely paraphrase the conclusion. Its
typed receipt composes:

- operational model/observation profile and bounded countermodel receipts;
- full/empty/leave-one-out premise dependency;
- a proposed key idea, premise roles, recombination, and crossed
  invariant/obstruction, each bound to verifier receipt hashes;
- source-bound external alignment and its limitations;
- a human-facing gloss;
- a domain-stripped `ConstraintFingerprint` compatible with the shared
  constraint/research-isomorphism engine.

The model may propose the key idea and analogy. It may not upgrade either into
a theorem or novelty claim. Unknown evidence references fail. An isomorphism
transport remains `advisory_pending_destination_replay` until its typed
morphism and destination discriminator pass. If no familiar concept is found,
the status is `mechanically_characterized_unmapped`; the system does not invent
a name or interpretation.

For an outer objective that remains open, a grounded mechanism continues into
search. The host projects only its domain-stripped constraint, premise roles,
verifier references, and claim boundary into a fresh search wave; source matches
and literature labels stay outside the navigator view. The navigator then chooses
an existing-coordinate experiment, authors a typed formula, requests a reviewed
theory-language successor, or stops. The projection grants none of those moves
admission authority. A producer/first-fire route receipt binds the interpretation
SHA and source context before the next wave may consume it.

## 11. Navigator workbench

Required actions include:

- inspect/compare theory nodes;
- show minimal generators and joint-only consequences;
- show separation models or observations;
- show anonymous same-stratum objects that agree on every current formula;
- add/drop existing formula IDs;
- select a theory presentation;
- rank/request a boundary countermodel;
- render/request a conditional Lean consequence;
- propose a formula or conservative definition;
- request an abstraction refinement or structural transport;
- freeze a candidate presentation.

Formula profile IDs are the ordinary wire representation. A frontier formula
uses a bounded typed postfix/stack codec preserving arbitrary bracketing.
An optional `contrast_object_ids` pair binds a proposal to the displayed
observational blind spot. A non-separating proposal receives no epoch; a
separating proposal carries an exact finite-profile witness into the normal
context-epoch path. Before finalist freeze it may be admitted inline. After
freeze it is an outbound request: the source finalist remains bound to its
source context and `continue-epoch` archives that source state before admitting
the formula into a fresh navigator trace.

Workbench receipts bind context hash, node/presentation IDs, input hashes,
outputs, and authority. Sealed rows and interpretation labels never enter the
cold briefing or call journal.

## 12. Reciprocal state and campaign journal

One append-only journal coordinates subsystems. Core event types:

- context/formula/model additions;
- theory presentations and bounded closures;
- countermodels and proof attempts;
- learned conflicts;
- abstraction refinements;
- definition proposals/retentions;
- structural transports;
- finalist freeze;
- sealed evaluation;
- next-epoch evidence promotion.

Materialized views include current context, theory archive, proof panel,
conflict memory, definition library, navigator briefing, and sealed ledger.
Subsystems exchange events and content references rather than importing every
other subsystem.

## 13. Selection and query policy

Hard-reject every presentation that is ill typed, empty under declared
controls, contaminated by a visible target, or supported by an overclaimed
exactness receipt. Minimality, internal independence, and joint-only
consequence are additional requirements only for `compact_axiom_pack`.
`theory_program` retains redundancy and premise-ablation as inspectable cost
and dependency coordinates; they do not define admissibility.

Principal signal: deductive description length—minimum basis cost plus retained
definitions/lemmas versus bounded and kernel-checked consequences gained.

Archive by semantic phenotype rather than one universal scalar. Use semantic
extent, consequence profile, larger-model/proof status, and proof-cost profile
as diversity coordinates.

Information yield chooses the next expensive query. Truth cells already known
from a complete census are not experiments.

The current formula language also induces a partition of objects by truth
vector. Non-singleton classes are representation blind spots. The host may
surface anonymous representatives, while the leaf chooses the distinguishing
formula. This partition is recomputed after each admitted formula and has no
authority over substrate identity, named interpretation, or isomorphism.

### 13.1 Residual information and receipted refusal

Apparent consequence count is not a discovery signal. For each proposed
presentation the host must declare a cheap baseline, subtract every consequence
that baseline explains, and expose a vector rather than a universal score:

```text
candidate consequence IDs
cheap-baseline consequence IDs + baseline_ref
residual consequence IDs
exact residual identification bits over frozen objects
presentation description units
verification cost units
```

The substrate supplies the baseline semantics; the common kernel performs only
set subtraction and exact partition entropy. Finite equational contexts use
`leanmill.bidirectional_equational_deduction.v5`. It removes the proposed
premises, direct substitution instances, targets obtained by one contextual
rewrite, and targets whose two sides meet within eight deterministic rewrite
steps. The bounded term graph reuses intermediate equalities without taking
the product of both rewrite frontiers; contractions and smaller expansions are
prioritized under a 4,096-state-per-side cap. Size-increasing rewrites are
limited to the root or a direct child; contractions and size-preserving
rewrites remain contextual. Frozen base equations are available premises. Each
classification carries replayable steps, the state cap, and explored-state
counts; these bounds are the cheap-baseline cost boundary, not a proof or
theory identity.

A search that reaches either state cap without a join returns
`cheap_baseline_inconclusive`. It is removed from priced residual coordinates,
cannot justify a finalist, and cannot be stored as a zero-residual conflict.
The navigator may pivot, expand the grammar, or spend a separately declared
stronger-deduction tier; saturation is never novelty evidence.

Finite structures add a second, signature-generic baseline before residual
entropy is priced. The host recognizes only primitive table templates:
constant operations, argument projections (including unary identity), and
empty/full relations. If a presentation forces one or more templates in the
exact context, residual entropy is conditioned on the models satisfying their
joint template. Candidate consequences in the template closure are subtracted.
The receipt exposes the anonymous symbol/argument indices, support counts,
conditioning extent, and finite-context claim boundary. This is an MDL
baseline, not a blacklist of named theories: a template is an adapter-neutral
property, never adapter or campaign identity. A later campaign may explicitly
explore the induced slice by adding the property to its base data; it does not
create another Python adapter.

Later bounded rewrite, completion, or proof-search baselines may extend this
stack, but each must have a versioned identity and receipt. A stronger baseline
changes the coordinates and therefore requires replay, not mutation of old
evidence.

Novelty has two separate coordinates:

1. **Endogenous residual** is computed before freeze against the declared cheap
   deduction baseline. It steers anonymous search without theory names or
   human salience.
2. **External-knowledge residual** is computed only after freeze against a
   source-bound theorem or literature graph when one exists. It prevents an
   unfamiliar but catalogued result from being promoted as new. Missing
   external coverage is `unavailable`, never evidence for novelty.

The external coordinate may stop expensive boundary work in a discovery
campaign; a preregistered validation/control may continue with that label.
External names never flow back into the cold navigator, and the two coordinates
are not blended into a universal score.

The system must also keep four frontier categories distinct:

1. **domain frontier** — the research direction concerns an under-explored
   area;
2. **semantic frontier** — the formula separates the frozen finite objects
   after the declared structural baseline;
3. **deductive frontier** — the consequence survives the declared bounded
   deduction/proof-description tiers;
4. **knowledge frontier** — the result is not catalogued or readily recoverable
   from public sources or model priors.

Crossing one category never certifies another. Anonymous generation receipts
source blindness, not independence from training memory. Post-freeze knowledge
status is one of `catalogued_recovery`, `routine_reconstruction`,
`discovery_candidate`, or `unresolved`; the engine itself never upgrades
`discovery_candidate` to a public discovery claim. An exact source match forces
recovery. Missing source coverage and a failed closed-book probe leave status
unresolved. A quick independent recognition or derivation is evidence of high
recoverability, while elapsed campaign time alone is not a gate.

Freeze is a provisional boundary nomination. Before expensive work, the host
surfaces the cheap part of a replayable vector: semantic residual, bounded
deduction disposition, and primitive structural-collapse class. The navigator,
not a deterministic ranking formula, chooses among formula expansion, region
change, receipted refusal, and nomination from that vector. It uses the existing
presentation-preview action; no parallel quality tool is introduced. The
navigator cannot self-attest any coordinate. Cross-size/stratum persistence,
exact premise necessity, post-freeze recoverability, and downstream lift fill
lazily only after the candidate survives the preceding tier. Zero deductive
residual rejects a discovery candidate; a validation campaign may continue
under an explicit recovery label.

The cold navigator manifest includes every frozen base formula in anonymous
typed IR. It removes axiom names and replaces signature names with positional
`sort_N`, `op_N`, and `rel_N` symbols. Base mathematics is therefore visible
while theory labels and literature remain sealed. Hiding base equations would
make the residual scorer an oracle and prevent the navigator from detecting a
short derivation itself.

The navigator may return `reject_all`, and the prompt must name this as a
legitimate outcome. The host accepts it only after at least one attempted
nomination has a deterministic selection receipt with a named baseline, no
residual consequence, and zero residual bits. Invisible or self-attested
rejections do not count. Rejected presentations become journal events. The
shared `INVESTIGATED_STAGNATION_K` value bounds the escape surface: sibling
attempts under one frozen campaign/context reduce to a sequence receipt, and
three consecutive receipted no-candidate outcomes surface stagnation pressure.
A finalist resets the sequence. The next attempt must then change region,
representation, or campaign direction rather than repeat refusal indefinitely.
A receipted no-candidate run has status
`frontier_no_candidate` and performs no boundary query.

The navigator prompt exposes exact remaining navigation calls and turns. This
is horizon information, not a host search procedure: budget exhaustion never
promotes a preview. Under the roll-forward policy, an AdapterForge agent slice
is unreachable when the frozen forge-attempt cap is zero, and boundary call
capacity beyond the declared Lean-attempt count can roll into navigation while
the declared Lean and interpretation calls remain protected.

### 13.2 Exploration budget and stopping contract

The inspectable campaign contract is `leanmill.campaign.v1` YAML frontmatter in
the same Markdown file as the research direction. A campaign author may write
it directly or state the preference in ordinary language; a budget-compiler
role using the existing subscription runtime emits the same fields. The host
validates and materializes the complete typed contract before construction. A
user does not need to enumerate internal resource kinds. Example:

```yaml
---
schema: leanmill.campaign.v1
lane: axiompack
source_mode: human_directed
profile: standard
budget:
  wall_clock: 20m
  metered_api_usd: "0"
stop:
  low_yield_patience: 3
  when: three structurally distinct finalists survive the size-five boundary
---

Explore anonymous finite reversible update theories.
```

The typed object is authoritative after YAML validation. An NL compiler may map
preferences into fields but cannot execute them. A domain-specific scientific
stop clause is preserved verbatim in `stop.when`; the existing blueprint
compiler must lower it to a condition over host-observable receipts, and the
independent semantic reviewer must approve the alignment. An ambiguous clause
cannot silently weaken an operational cap.

Hard ceilings may cover:

- elapsed wall time;
- provider calls and agent turns;
- reported input/output tokens and metered spend;
- deterministic workbench actions;
- adapter-forge attempts;
- finite-context models and truth cells;
- boundary queries, SMT calls/seconds, formal-peer attempts/seconds, and Lean
  attempts/seconds.

Wall time is the default user-facing outer cap because it bounds latency and is
easy to understand. It is not a comparison metric: machine speed, queueing, and
verifier latency vary. Spend aligns with procurement but may be unknown for a
subscription call; tokens are observable but not equivalent across models;
call counts are replayable but calls have unequal scope. Therefore a campaign
always retains at least one nonmonetary provider ceiling when metered cost is
used.

The host divides the envelope into compilation, context, navigation, expansion,
boundary, and interpretation phases. A phase reserves resources before acting,
commits measured usage afterward, and releases unused reservation. The agent
cannot edit caps, ledger events, or phase reserves. Early navigation cannot
consume the boundary-verification reserve. Unused capacity from completed
phases rolls forward, so the internal partition does not strand budget or
force a user to predict the campaign's control flow. The allocation
policy is an explicit digest-bound campaign field; older strict-phase budgets
retain their original semantics on replay.

Model execution continues through `common/subscription_agent_runtime.py`; the
budget code is admission/accounting around that runtime, not a provider
transport. Boundary queries and other proposed next moves project to
`common/kernel_action_schema.py`. `theory_ir.py` remains the formula/model IR and
does not absorb orchestration actions.

Scientific stopping is a second layer inside the hard envelope. The campaign
continues only when an admissible next action either:

1. is required to leave the attempt in a replayable state; or
2. has estimated marginal information per normalized cost at or above the
   frozen threshold.

The soft rule also freezes `max_finalists`, a low-yield patience count, and any
coverage/diversity target. It may stop early on target attainment or repeated
low-yield actions. It cannot authorize an action beyond a hard ceiling.

For agentic theory programs, marginal yield is classified over a shared
pointwise image rather than lexical novelty. Per search wave, the host records
the new conjecture identities and their structural residual/ablation outcome
carriers. New conjectures with no new outcome carrier are `alpha_blind`; no new
conjectures are `exhausted`; a new outcome carrier is `expanding`. The receipt
is visible to late synthesis but grants no routing authority. In particular,
the host cannot manufacture a richer grammar: an `alpha_blind` successor must
be authored by a leaf as a theory-language/functor request or end unresolved.

Every terminal path emits a `BudgetStopReceipt` distinguishing at least:

- `target_reached`;
- `marginal_yield_below_threshold`;
- `hard_cap_reached:<resource>`;
- `user_stop`;
- `campaign_finished`;
- `blocked_before_action:<resource>`.

The receipt binds the immutable budget digest, total and per-phase usage,
outstanding reservations, elapsed time, last information estimate, and the
attempt/context identity. A wall-clock expiry must end only owned descendant
process groups through the runtime contract in §17; it must not signal the
calling session.

## 14. Counterexamples, CEGIS, and abstraction

Only witnessed conflicts enter `TheoryConflictLedger`. A context-relative
failure must replay before reuse in a later epoch.

Visible holdout counterexamples become consumed evidence through the existing
CEGIS membrane and cannot certify clean transfer in the same epoch.

In evidence-induced mode, two raw states with one abstract role but differing
checked behavior identify an abstraction alias. A counterexample without an
alias is a law failure. This is the disciplined bridge to ARC-style abduction:
the outer evidence/program incidence and counterexample membrane are shared;
the substrate’s raw semantics remain adapter-owned.

Contrastive formula authorship is the corresponding language-refinement loop
inside one frozen object universe: find an observational class, display a
bounded anonymous pair, propose a typed predicate, and rebuild the incidence
context only after exact separation. Formal adapters render typed tables;
evidence adapters render declared anonymous observations. Predicate authoring
and lowering remain adapter-owned when the common typed formula codec does not
apply.

## 15. Boundary lifting and authority

For frozen finalists:

1. search larger finite carriers or observations;
2. render sparse conditional consequences;
3. submit conditional Lean consequences as normal `WorkItem` theorem goals to
   `solve_adhoc`, or execute the raw verifier under the same campaign budget;
4. record proved, refuted, and unresolved separately;
5. replay full/empty/leave-one-out attribution;
6. reveal interpretation/literature only after cold freeze;
7. route any promotion through existing AxiomPack/LeanMill authority.

The full-arm proof must be a governed `solve_adhoc` closure before attribution
can begin. Empty and leave-one-out arms replay the identical proof bytes; they
can disqualify attribution but cannot create proof credit.

The campaign installs a scoped budget hook around the existing subscription
runtime while `solve_adhoc` runs. Every logical subscription dispatch reserves
one provider call and agent turn before launch and commits it afterward. The
hook changes no command or transport. The AxiomPack boundary defaults the
multi-provider proposer pool and cross-subscription failover off unless the
campaign envelope explicitly budgets and enables them; all ordinary solver memory,
moves, retrieval, and governance remain active.

Absence of a finite countermodel never becomes `kernel_proven`. A failed proof
attempt remains unresolved.

## 16. Definitions and landscape transport

A conservative definition must expand deterministically into the prior
signature, be total and typed, and either reduce total description length or
open a separated consequence class. Retention creates a new grammar/context
epoch. An unconstrained new primitive starts a new signature campaign.

Every context may emit an anonymous landscape fingerprint over formula
profiles, generated extents, materialized covers, minimal bases, synergy
motifs, model strata, and proof/refutation motifs. Structural matches may
nominate a `ConstraintMorphism`; the target context must compile and test the
actual formula/definition/query mapping. Similarity alone has no axiom
authority.

`research_isomorphism` remains a post-freeze optional move. Its first admission
test is matched: equal source artifact, destination-choice count, and budget;
one arm receives transported destination suggestions and one chooses cold.
Destination-side discriminator information yield is the outcome. Automatic
feedback into future campaigns requires measured lift on that test.

## 17. Runtime and durability

Every provider call runs in a new session/process group with an `OwnedDispatch`
receipt. Cancellation signals only a recorded group after proving
`leader_pid == pgid == sid` and separation from the parent group. Ambiguous
ownership signals nothing.

Attempts are immutable and resumable:

- completed result → zero new calls;
- completed compiler/proposer bytes → replay them after downstream interruption;
- exact prompt bytes are persisted beside each call receipt; prompt identity,
  result identity, and host scientific state are distinct;
- checker progress is journaled;
- stdout, stderr, and structured output bytes are fsynced before parsing;
- a stochastic redraw requires a new attempt directory;
- batch preflight precedes paid per-row review.

An explicit budget extension is not a stochastic redraw. It appends authority,
reason, and additional caps to the same ledger, preserves cumulative usage and
search-wave images, and resumes the pending edge in the same attempt. Exhaustion
at run N therefore remains evidence at run N+1; additional budget cannot reset
the stopping state or mint a rejection.

Campaign accounting distinguishes transport attempts from provider inference.
Known local CLI rejections before inference consume no provider-call or agent-
turn allowance; unfamiliar failures conservatively consume one. Historical
receipts without the charge field retain the one-call interpretation. Status
projects every outstanding reservation as its phase, action ID, resources, and
reservation time, so a sparse-output verifier is observable without process
scanning.

A campaign may bind a prior complete context by path, context hash, and snapshot
digest. Reuse replays the snapshot and checks signature, base theory, adapter,
formula/hypothesis universe, and model strata against the new blueprint before
navigation. It writes a reuse receipt into a fresh attempt; it never mutates the
older attempt or reruns the census. Current snapshots persist materialized truth
bitsets and load them directly; the loader remains backward-compatible with
older formula+model snapshots that require one deterministic incidence replay.

The 2026-07-09 parent-session termination incident is the regression target for
this contract.

The 2026-07-10 successor run adds two regression targets. Durable historical
calls without prompt bytes replay their digest-bound result bytes through the
deterministic workbench and an idempotent journal. A capped epoch with no
finalist and no receipted rejection materializes `budget_stopped`; it cannot be
coerced into `reject_all`. Provider-free campaign replay binds the active run
digest, context hash, and epoch; a cached source replay is archived at an epoch
transition and cannot answer for its successor.

## 18. First campaign plugin

The first scientific campaign remains anonymous two-law magma theories because
it offers a compact, open, exactly enumerable frontier adjacent to the
Equational Theories Project’s stated compound-implication direction.

Its plugin declares:

- one anonymous sort and one anonymous binary operation;
- 410 canonical equations through total operation order three;
- every size-2 and size-3 operation table;
- pack arity two;
- complete incidence and isomorphism quotient;
- larger size-4/5 SMT countermodels;
- sparse conditional Lean implications;
- interpretation only after freeze.

`magma_law_universe.py` and `finite_model_census.py` magma canonicalization are
optimized plugin internals. Fixed-size SMT lowering is signature-generic and
host-replays every witness. The public caller submits a brief or typed
blueprint, never a Python family name.

## 19. Implementation map

### Generic kernel/current shared surfaces

- `src/ztare/common/finite_incidence_context.py`
- `src/ztare/common/information_yield_pricing.py`
- `src/ztare/common/constraint_isomorphism.py`
- `src/ztare/common/theory_substrate_adapter.py`
- `src/ztare/common/leaf_workbench_environment.py`
- `src/ztare/common/subscription_agent_runtime.py`
- `src/ztare/leanmill/finite_theory_context.py`
- `src/ztare/leanmill/equational_formula_universe.py`
- `src/ztare/leanmill/theory_campaign_journal.py`
- `src/ztare/leanmill/theory_conflict_ledger.py`
- `src/ztare/leanmill/theory_query_policy.py`
- `src/ztare/leanmill/theory_landscape_morphism.py`
- `src/ztare/leanmill/theory_interpretation.py`
- `src/ztare/leanmill/frontier_interpretation.py`
- `src/ztare/leanmill/exploration_budget.py`
- `src/ztare/leanmill/context_epoch.py`
- `src/ztare/leanmill/typed_axiom_proposal.py`
- `src/ztare/leanmill/typed_postfix_codec.py`
- `src/ztare/leanmill/campaign_manifest.py`
- `src/ztare/leanmill/campaign_profile.py`
- `src/ztare/leanmill/frontier_campaign_definition.py`
- `src/ztare/leanmill/frontier_campaign.py`
- `src/ztare/leanmill/axiompack_leaf_workbench.py`
- `src/ztare/research_signals.py`

### Blueprint/control-plane additions required by GP-251

- `src/ztare/leanmill/frontier_blueprint.py`
- `src/ztare/leanmill/frontier_blueprint_compiler.py`
- `src/ztare/leanmill/theory_adapter_registry.py`
- `src/ztare/leanmill/adapter_forge.py`
- `src/ztare/leanmill/explore_axiom_space.py`
- prompt/schema additions under canonical LeanMill prompt/contracts homes;
- CLI projection through `ztare` and a public control script.
- bounded Hetzner projection through the named `leanmill-*` actions in
  `deploy/vps_run.sh`; campaign inputs cross only through
  `deploy/vps_sync_files.txt`.

### Plugin and boundary surfaces

- `src/ztare/leanmill/adapters/generic_fol_finite.py`
- `src/ztare/leanmill/adapters/magma_equational.py`
- existing magma law/census modules behind that adapter;
- `src/ztare/leanmill/equational_baseline.py`
- `src/ztare/leanmill/finite_context_ablation.py`
- `src/ztare/leanmill/finite_structure_baseline.py`
- `src/ztare/leanmill/theory_interest.py`
- `src/ztare/leanmill/finite_table_model_finder.py`
- `src/ztare/leanmill/lean_consequence_bridge.py`
- `src/ztare/leanmill/theory_conflict_ledger.py`
- existing `src/ztare/leanmill/solver/sledgehammer.py` Isabelle transport and
  checker;
- `src/ztare/leanmill/contracts/work_items.py`
- `src/ztare/leanmill/solver/solver_core.py`
- existing proof-cache, premise-shelf, no-good, faithfulness, and banked-library
  stores reached through `solve_adhoc`;
- `src/ztare/leanmill/conservative_definition.py`
- `src/ztare/leanmill/theory_landscape_morphism.py`

## 20. Build order

### M0 — preservation and runtime repair

- preserve the prior implementation and recovered calibration bytes;
- process ownership, durable output, immutable attempts, status/cancel/replay;
- generic versus band-specific codec separation;
- batch preflight before checker spend.

### M1 — generic semantic context

- substrate-neutral incidence kernel;
- generic finite-model-universe protocol;
- persistent context snapshots and context epochs;
- exact closures, minimal bases, synergy, and witnesses.

### M2 — public inlet

- `FrontierExplorationBrief` and `FrontierTheoryBlueprint`;
- NL/typed compiler plus independent semantic/executable review;
- deterministic mode router and adapter registry;
- `explore_axiom_space` orchestration entrypoint;
- legacy blueprint explicitly routed warm.
- typed `AdapterGap` and AdapterForge dispatch/admission boundary.

### M3 — navigator and boundary verification

- shared workbench environment and anonymous briefing;
- persistent navigator session and query budget;
- agent-authored first-order formulas and conservative derived operations
  through `propose_frontier_formula`, followed by host typechecking, expansion
  to the prior signature, and immutable context rebuild;
- SMT/raw countermodels and conditional Lean tasks;
- optional typed Theory-IR-to-Isabelle peer proof before model-mediated Lean
  work, under its own boundary cap;
- conditional work-item routing through `solve_adhoc`;
- matched attribution, journal reduction, conflict replay.
- generic logical premise ablation before proof spend. An exact formal context
  reuses its concrete singleton countermodels and host-replays base, premise,
  and target. Formula-to-source mapping remains an optional adapter capability
  and external cross-check; a missing capability extends the existing adapter
  rather than creating a source-named adapter identity.

### M4 — first campaign

- freeze the magma blueprint through the public inlet;
- build and replay the complete context;
- run the anonymous navigator and freeze diverse R1/R2 presentations;
- run larger-model and Lean checks;
- reveal ETP/literature after freeze;
- report positive, negative, or partial mechanism outcome.

Executed on the Hetzner Lean node on 2026-07-10. The anonymous navigator froze
one independent two-law presentation and one joint-only target. Fixed-size Z3
checks found no countermodel on carriers four or five. Lean then proved the
unrestricted conditional consequence. A premise-aware governance replay passed
the full arm and failed the empty and both leave-one-out arms under identical
proof bytes. The original generic `rejected_banned_axiom` result was a harness
classification mismatch: candidate laws are local typeclass fields, not global
axiom declarations. The immutable recheck receipt is
`6b2c9120f7dd677bd8392468ba6957ce753978b4afd4d54f77be6348f260189f`.

The frozen equations, revealed only after verification, are:

```text
x = x * ((x * x) * x)
x * x = (x * x) * x
therefore x = x * (x * x)
```

Post-freeze interpretation identified the premises as Equational Theories
Project Equations 99 and 359 and the target as Equation 8. The implication is
one contextual rewrite: Equation 359 rewrites a subterm in Equation 99 to
Equation 8. Interpretation receipt:
`5fc23935e44bc7aeb17674f71f8057a9295ef318a0160da4c7b4eb1c99b253c9`.

The run therefore separates two conclusions. The orchestration, larger-model,
Lean, and causal-attribution path worked. The scientific ranking did not: it
rewarded conjunction-only closure without subtracting a cheap deduction
baseline, and the prompt forced a finalist. Replaying the frozen context under
`leanmill.direct_equational_rewrite.v1` classifies the sole target as baseline
explained, leaving zero residual consequences and zero residual bits without
another provider call. This is the motivating regression for §13.1.

A second low-effort navigation attempt exposed the next baseline omission
before any size-4/5 or proof spend. It froze the singleton equation
`(x*x)*y = x*y` because the finite closure reported both the premise itself and
`(x*x)*x = x*x` as residual consequences. The latter is the direct instance
`y := x`; neither is frontier information. The v2 baseline excludes the
presentation and receipts direct substitution instances. Boundary execution
also replays the frozen selection receipt and residual coordinates before any
countermodel or solver call, so the stale finalist now fails closed.

A third low-effort attempt passed the v2 endogenous baseline and froze the
singleton `x = x ◇ ((x ◇ y) ◇ x)`, targeting `x = x ◇ (x ◇ x)`. Size-four/five
Z3 found no countermodel; Lean proved the implication using two premise
instantiations; full/empty/leave-one-out replay attributed the proof to the
premise. Post-freeze comparison identified Equational Theories Project
Equation 101 implying Equation 8, already present as an implicit-true edge in
the project's completed single-equation graph. This is a catalogued-result
rediscovery. It also exposed the arity bug: `pack_arity: 2` meant at most two
and did not encode the requested two-law interaction. Frozen
`navigator_contract.presentation_size` bounds now distinguish exact-two
campaigns while preserving old attempt replay.

The exact-two successor froze E8 + E151 and proved E99. The official source
relation explicitly refutes both singleton implications, so the result earns
`proved_exact_two_synergy` rather than only saved-proof attribution. The proof
derives E359 by self-instantiating E8 and contracting with E151, then rewrites
E8 to E99. This clears the three earlier harness confounders but remains a
small compound implication with no novelty claim. Source artifact:
`research_areas/pre_registrations/axiompack_gp251_smoke_20260710/exact_two_source_interpretation.md`.

### M5 — expansion and portability

- conservative definitions;
- landscape fingerprints and tested transports;
- generic many-sorted adapter coverage;
- a semantics-rich finite mathematical campaign through the generic adapter;
- one evidence-induced/nonmath adapter;
- scout-directed brief generation through the same inlet.
- one user-supplied executable constraint substrate compiled through an
  existing adapter or AdapterForge, then tested through shared SMT/raw/Lean
  boundaries;
- a typed interpretation ladder from operational profile and premise
  attribution to the key recombination, source alignment, and a
  domain-stripped isomorphism fingerprint.

The finite equational portability slice is implemented. A non-magma
unary/binary signature now enters through `generic_fol_finite.v1` with no
family module: the host generates 71 canonical equations through operation
order two, quotients the size-two structures by sort-preserving isomorphism,
builds the exact incidence context, freezes finalists, invokes the generic
fixed-size SMT capability, and reuses the exact snapshot without enumeration.
SMT receipts bind signature, base theory, premise pack, target, size vector,
solver, and host replay; an unsatisfiable premise pack is reported separately
from absence of a countermodel. Campaign packet v3 binds the full reviewed
blueprint so later boundary policy cannot drift beside the signed context.

Base-constrained exact enumeration is also implemented as a property of
`generic_fol_finite.v1`. `exhaustive_tables` keeps direct iteration for small
unconstrained spaces. `smt_exact` reuses the generic finite SMT lowering,
blocks the full sort-preserving orbit of each returned model, and constructs an
exact universe only after a final `UNSAT` for every declared stratum. Orbit
size supplies labeled multiplicity; the canonical representative supplies
model identity. Model-cap, wall-bound, and solver-unknown exits carry
incomplete receipts and fail context construction. Preflight reserves the
declared solver/orbit work bound rather than the raw table count, while still
reporting that raw count. No named algebraic family enters the adapter
registry.

The fully conditioned inverse-semigroup preflight produced only seven
isomorphism classes across sizes two and three, so it was killed before a
navigator call. The successor moves one level outward to regular unary
semigroups: associativity plus a selected inverse witness, with no involution,
product-reversal, commuting-idempotent, or inverse-semigroup characterization
seeded. This remains campaign data (`mul`, `inv`, reviewed base equations,
grammar, strata), not a new adapter. A provider-free Hetzner viability gate
requires at least 25 canonical models before launch. Any optimized enumerator
or external identity catalog must enter as an independently tested capability.

The successor gate passed with 47 canonical models and 71 formulas. Its cold
navigator froze `op1(x)*x=x` plus `op1(x)=op1(y)` and selected
`(x*y)*y=y`. Finite singleton countermodels certified exact-two
nonimplication; size-four/five SMT found no countermodel; Lean proved and
independently rechecked the pair implication. The proof derives the stronger
right-projection law `a*b=b`, while the unary premise makes `op1` constant.
Post-freeze review therefore classified the mechanism as selector collapse to
a standard right-zero structure, not a discovery result.

That outcome motivated the finite-structure baseline above. Repricing the same
frozen context with no provider call moves all ten apparent consequences into
the constant/projection baseline and reduces residual bits from `0.88785309`
to zero. Exhaustive repricing of all 2,485 exact-two presentations leaves 24
positive conditional residuals, all inside the unary-identity slice, and none
clears the campaign's existing `0.05` information-per-cost threshold. The
short operation-order-two campaign is therefore exhausted outside primitive
operation collapse; no paid rerun is warranted.

The Sol-medium successor after bounded equational replay rejected one
zero-residual presentation, then froze commutativity with `op1(x)*x=x` and
ranked `x*x=op1(x)` first. Size-four/five Z3, Isabelle, ordinary LeanMill, and
the provider-free attribution recheck all supported the implication; concrete
singleton countermodels established exact-two dependence. The proof collapses
the selected inverse to the identity and then forces idempotence, placing the
result in familiar semilattice territory. It is a valid theory-induction result
with no theorem-novelty claim. The result artifact and receipt references are
in `sol_dynamic_30m_result.md` beside the campaign.

Provider-free post-run repricing with the generic eight-step v5 replay derives
both ranked targets and all other joint consequences. The residual set and
identification bits are zero. The apparatus receipts remain useful regression
evidence; the mathematical disposition is routine recovery. The AAR in the
result artifact records the stopping failure: a positive finite-semantic
residual under an arbitrary four-step cap was treated as boundary-worthy before
the deductive and knowledge-frontier coordinates were surfaced.

The formula-authorship eigenquestion remains untested because the false
residual made the seed chart appear sufficient. The next same-substrate action,
if run, is a zero-boundary-spend apparatus discriminator for formula authorship
or receipted refusal. It is not itself a mathematical-novelty campaign.

The successor frontier campaign now changes substrate rather than repeating
the regular-unary chart. A definitional equational expansion of finite
nondegenerate cycle sets uses an anonymous binary operation, its rowwise
inverse, and the inverse of its diagonal map. The generic solver census
reproduces the published isomorphism counts `2, 5, 23, 88` at sizes two
through five. The size-five launch context is final-UNSAT exact with 88
canonical models, 2,640 accepted labeled models, 210 order-two seed formulas,
11 semantic profiles, and 15 generated nodes. The published counts are an
encoding checksum, not a candidate result.

This campaign directly tests the open formula-authorship discriminator. The
cold Sol-medium navigator sees the anonymous base equations and shallow chart,
but no domain name, sources, named subclasses, or target identity. It must add
a typed formula when the chart only offers routine regions, use the new profile
in a residual exact-two pack, or return a host-receipted null. Larger size-six
and size-seven countermodels and conditional Isabelle/Lean work remain lazy
post-freeze boundaries. Sol medium is the first source-backed interpreter;
Fable is reserved for a sparse second opinion after a consequential unresolved
ambiguity. The frozen campaign and experiment contract are in
`research_areas/pre_registrations/axiompack_cycle_structure_frontier_20260710/`.
Laptop and Hetzner provider-free preflights agree on the frozen blueprint,
context, universe receipt, and all counts with zero provider calls.

The same run exposed two apparatus bugs now covered by regression tests:
optional peer exhaustion stopped the second ranked target, and the literature
packet hid the base formulas behind hashes. Optional verifier exhaustion now
skips only that stage, and post-freeze packet v3 supplies the ambient theory to
the interpretation layer without weakening the cold-search membrane.

Preflight and execution now share `compile_campaign_brief`, so the preflight
blueprint identity is byte-identical to the blueprint later bound into the
signed packet. Previously the preflight omitted the compiled budget-preference
receipt and reported a different blueprint ID despite building the same
context.

The cycle-structure campaign completed with ten Sol 5.6 medium navigator
turns. Sol used formula authorship once, proposing associativity, but exact host
evaluation showed that its size-five truth profile duplicated an existing
profile. The frozen two-formula presentation reduced to a common permutation;
its first target was the involution law in that encoding. Size-six/seven Z3,
Isabelle, governed Lean, singleton countermodels, attribution, and governance
replay supported the implication. The disposition is routine reconstruction,
with no theorem-novelty claim. The result and receipt references are in
`research_areas/pre_registrations/axiompack_cycle_structure_frontier_20260710/sol_medium_result.md`.

The contrastive Sol-high successor then passed the representation discriminator
and failed the compositional one. The leaf authored the anonymous
endomorphism-shaped equation
`op2(op0(x,y)) = op0(op2(x),op2(y))`; a displayed object pair witnessed a new
finite profile. Explicit `continue-epoch` admission produced a 211-formula,
12-profile, 20-node context. Exhaustive provider-free pairing against all 210
seed formulas found no conjunction-only consequence and therefore no residual
exact-two presentation containing the new coordinate. Outcome class:
representation lift without theory-selection lift. No SMT, Isabelle, Lean, or
literature stage is licensed. Receipt map:
`research_areas/pre_registrations/axiompack_cycle_structure_frontier_20260710/sol_high_contrastive_result.md`.

The zero-pair result is scoped to the seed chart. It rules out every pairing of
the authored coordinate with one of 210 seed formulas, while leaving open an
interaction between two future authored coordinates. The engine already admits
repeated pre-freeze formula epochs. The next scientific discriminator is that
recursive language-learning regime, under a fresh contract with enough
navigation allowance to inspect each rebuilt context before nomination.

That run identified the representation bottleneck: formula authorship received
no inspectable structures that the shallow language conflated. The common
incidence kernel now computes observational object classes. The shared
workbench pages anonymous same-stratum pairs for formal and evidence contexts;
an optional pair-bound formula proposal is admitted only when exact host
evaluation separates the pair. The witness certifies a new profile relative to
the current finite panel and carries no broader proof or novelty authority.

Post-correction verification on 2026-07-10 passed 191 scoped integration tests,
documentation freshness, Markdown links, and knowledge-graph drift checks.
Hetzner provider-free preflight replayed the 47-model/71-formula context with
zero provider calls and reported the same execution blueprint
`blueprint:e35db4047e4f039d4324fcf7306aa9b81fbe3bc315f9512ac8b903e00723aa18`.

### M5b — theory-program invention

Implemented kernel surfaces:

- `theory_program` selection prices every residual prediction of a presentation
  and does not require minimality, independence, joint-only consequence, or a
  two-formula presentation;
- `typed_postfix_codec` accepts typed relations, equality, Boolean connectives,
  and quantifiers, while compact equations retain replay compatibility;
- conservative derived operations expand deterministically into the prior
  Theory IR and cannot add theory strength;
- theory-language changes are proposal-only requests for a new reviewed
  blueprint or adapter capability;
- one compiler-first continuation consumes every language request as compiled,
  rejected, or unavailable; total campaign-local functor images may create a
  successor epoch without granting global registry or larger-model authority;
- reviewed, content-addressed alpha/gamma materializations may add fixed
  abstract search batches only after source roundtrip, raw-law replay,
  canonicality, and independent-review receipts; alpha-only images cannot claim
  extrapolation, and batch exhaustion cannot claim a finite-size theorem;
- a `TheoryProgram` binds campaign, lineage, context epoch, hypotheses,
  predictions, and the host selection receipt;
- host-isolated lineages receive the same frozen context without sibling traces,
  then compare only frozen programs. Shared resource ceilings remain global,
  while one lineage's soft target cannot terminate its siblings;
- the no-provider navigator is explicitly a compact-pack control and cannot
  silently select a theory program;
- post-freeze interpretation distinguishes pack-dependency evidence from a
  verified theory-program prediction;
- `theory_program_disagreement_policy` prices frozen-program hold/refute
  disagreements with the shared information-yield policy and feeds the
  selected full-program lifts into the ordinary boundary executor. Silence,
  vacuity, and unanimous seed predictions remain explicit exclusions.

Remaining scientific integration:

- execute a consequential recursive-language campaign whose withheld
  prediction tests more than a short implication inside the seed chart.

The 2026-07-12 compositional successor supplied three new finite semantic
coordinates, then exposed four lifecycle/category defects before yielding a
frontier result: an action receipt could lose its dependent leaf turn; synthesis
received program IDs without prediction evidence; navigation coverage stopped
the boundary phase; and a seed-refuted prediction could freeze. The kernel now
keeps host actions pending through the leaf disposition, carries prediction
profiles and residual evidence into synthesis, scopes coverage stops to
navigation, and returns refuted/vacuous programs to counterexample-guided
search. Prediction receipts also include leave-one-premise-out witnesses.

The compound-dependency workbench now projects exact minimal presentations and
joint-only consequences from the incidence chart; the 410-formula control has
1,687 such dependency rows. A subscription probe used this projection and
surfaced the next identity boundary: `forall …, p and q` is a product of two
prediction coordinates. The host now receipts that normal form, identifies
consecutive same-kind quantifier groups through an additive logical-coordinate
hash, and lowers an executable product into its existing atom IDs before any
boundary spend. Historical formula IDs remain unchanged. In the probe, both
atoms passed exact seed support and leave-one-premise-out checks, then failed on
host-replayed size-four countermodels; the two implication no-goods persist for
successor attempts. Outcome: useful representation/search feedback, no
frontier theorem.

The first frozen compound campaign is
`research_areas/pre_registrations/axiompack_compound_implication_frontier_20260712/campaign.md`.
It targets the Equational Theories Project's deferred compound-implication
frontier with the existing magma adapter and exact context. Its discriminator
is an irreducible two-to-four-premise prediction supported in the seed chart,
refuted after every premise ablation, absent from the single-premise baseline,
and tested on larger carriers.

The normalized successor is
`campaign_observation_algebra_successor.md` in the same directory. It retains
the frozen scientific stop instruction, uses GPT-5.5 medium through the shared
subscription runtime, and consumes the witnessed no-good ledger rather than
repeating the two killed implications.

### M6 — Workbench product projection

- register an AxiomPack lane in the existing LeanMill Workbench server;
- reuse `src/ztare/leanmill/cli.py`, `frontier_campaign_actions.py`, and
  `scripts/public/control/forensic_workbench_server.py` as the only action
  bridge; the frontend owns no campaign transitions;
- project `prepare`, `approve/run`, `status`, `inspect`, `boundary-approve`,
  `replay`, `continue-epoch`, `stop`, and `retire` through the existing CLI
  action bridge;
- stream campaign-journal and budget-ledger read models rather than inventing a
  frontend-only state store;
- show the cold anonymous view before finalist freeze and interpretation only
  after the authority event;
- keep provider/runtime configuration in the campaign definition and execute
  it through the shared subscription runtime.

The engine and CLI action schemas ship before the frontend lane. Frontend work
is a later projection of those stable actions.

## 21. Required tests

### Entry and compilation

1. NL brief compiles to a typed frontier blueprint with no candidate laws.
2. named candidate axioms are rejected in cold mode.
3. semantic review cannot sign its own trust root.
4. unknown primitive semantics or adapter fail closed.
5. structure-first typed input requires no LLM call.
6. legacy `AxiomPackBlueprint` routes only to the warm inlet.
7. human, residual, and scout directions reach the same frozen packet schema.

### Genericity

8. the context kernel imports no magma adapter.
9. a generic finite signature and a finite protocol both instantiate the
   incidence interface.
10. adding a theory name requires no Python module when generic semantics fit.
11. adapter extensions require compile/self-test/review receipts.
12. an unknown substrate produces `blocked_adapter_gap`, then an admitted
    adapter can resume only in a new attempt.
13. AdapterForge cannot write the live registry or certify exactness.
13a. requesting a missing adapter property yields a capability gap while
preserving the adapter identity.
13b. a unary/binary algebra uses the generic host equation grammar and generic
fixed-size SMT capability without a family-named Python module.
13c. generic finite models quotient sort-preserving relabelings while retaining
labeled multiplicity; opting out is an adapter property, not another adapter.
13d. a base-constrained generic census blocks complete isomorphism orbits and
emits an exact universe only after final solver exhaustion.

### Exact context

14. complete census counts, formula counts, and ordered hashes replay.
15. sampled panels cannot emit exact closure.
16. equivalent presentations share a node ID.
17. independence and separation return concrete witnesses.
18. synergy excludes singleton consequences.
19. model/formula additions mint a new context epoch.
19a. a seed-exhausted navigator can author a typed first-order formula outside
the seed grammar, and its admitted epoch recomputes the exact formula-model
incidence before any candidate is selected.
19b. a formula whose bounded truth profile duplicates an existing profile
receives no residual-information credit merely because its syntax is new.
19c. model-cap, wall-bound, and solver-unknown enumeration exits cannot build
an exact formal context.
19d. observational object classes group objects only by the current truth
vector; an admitted formula refines that partition in a new epoch without
changing object identity.
19e. a conservative derived operation expands into the prior signature before
evaluation, while a request for a new primitive or abstraction can only produce
an outbound blueprint request.

### Navigator and membrane

20. every advertised action has one executable route.
21. receipts bind context and node/presentation IDs.
22. cold briefings contain no interpretation names or sealed rows.
23. formula-ID presentations need no semantic checker.
24. authored frontier formulas require a signature-bound typed proposal and
host rebuild. Context admission grants no proof, novelty, intent-fidelity, or
promotion authority; a separately signed semantic review is required only
when natural-language intent is later used for lowering or promotion.
25. consumed holdouts cannot certify the same epoch.
25a. a current navigator freeze ranks an explicit nonempty subset of previewed
residual consequences; the host rejects an invented or duplicate target and
executes valid nominations in navigator order. Legacy frozen artifacts without
the field retain replay compatibility by exposing every residual consequence.
25b. the navigator can request an anonymous same-stratum pair from a
non-singleton observational class and bind a typed formula proposal to that
pair. The host rejects a non-separating proposal and receipts a separating one
as a new finite semantic profile before rebuilding the context.
25c. `theory_program` admits a bounded nonempty presentation with residual
predictions even when it is redundant or has no joint-only consequence; the
compact profile retains its independence and synergy gates.
25d. a blueprint breadth of three reaches the workbench and navigator without a
hidden size-two default.
25e. host-isolated lineages receive no sibling trace or candidate bytes before
freeze, share hard campaign caps, use sibling-local soft-stop windows, and
cross-pollinate only as a proposal requiring fresh replay.

### Boundary and authority

26. fixed-size SMT countermodels host-replay.
27. SMT unknown remains unknown.
28. bounded closure never becomes a kernel proof by absence of a countermodel.
29. Lean implications are conditional and introduce no global axiom.
30. failed Lean attempts remain unresolved.
31. matched full/empty/leave-one-out arms reuse identical proof bytes.
32. structural similarity cannot enter axiom authority without a compiled
    target mapping and signed obligations.
33. a conditional Lean boundary reaches `solve_adhoc` and carries its governed
    closure receipt before AxiomPack can emit `proved_attributed`.
34. every subscription dispatch nested under that solve reserves campaign
    budget before launch; exhaustion prevents the next dispatch.
34a. saved-proof leave-one-out failure cannot emit logical pack synergy; an
exact-two synergy status requires concrete host-replayed or source-bound
refutation of both singleton implications.
34b. a source-known singleton implication is classified before SMT or Lean
budget is reserved; this invalidates compact-pack synergy credit without
changing the identity of a theory program.
34c. a persisted zero-residual presentation or finite-countermodel implication
suppresses a later attempt only after the original witness replays in the
current exact context; sealed witness payloads never enter the navigator view.
34d. an Isabelle peer result is `proved` only after the returned proof rebuilds
as a complete theory for the exact typed implication. Unavailable transport or
an unverified proof remains non-substantive, and the peer consumes its separate
campaign cap rather than a Lean or model-call allowance.
34e. exhausting an optional formal-peer or Lean allowance marks that stage
`skipped_budget_exhausted` for the affected target; it does not stop remaining
admissible targets. Global wall/user/stop-rule and boundary-query limits retain
campaign stopping authority.
34f. post-freeze interpretation receives the frozen base formulas, signature,
primitive semantics, and eigenquestion. These bytes are unavailable to the
cold navigator and cannot alter candidate selection.

### Runtime and replay

35. timeout kills owned leader and descendant while parent survives.
36. ambiguous/current-group cancellation fails closed.
37. completed attempts make zero provider calls.
38. downstream interruption resumes from durable upstream bytes.
39. the deterministic campaign replays from its snapshot and journal.
40. a digest-bound compatible context snapshot skips enumeration, while any
    signature/formula/strata mismatch fails before navigation.
40a. a new campaign packet binds the full reviewed blueprint and boundary
execution rejects any later blueprint drift.
41. navigation returns an already-frozen finalist when the next agent-turn
    reservation hits the cap.
42. a saved conditional proof can be re-governed without another model call;
    the overlay is digest-bound and leaves the boundary artifact immutable.
43. post-freeze literature interpretation uses a strict result schema, an
    explicit native-web capability, and a new immutable attempt after an
    inconclusive capability failure.
44. `low | medium | high` effort is normalized in `common/llm_runtime.py` and
    lowered for both API and subscription transports.
45. the exact first-science presentation is rejected by the direct-rewrite
    baseline with zero residual formulas and bits.
46. `reject_all` fails without host selection receipts and succeeds only over
    named-baseline zero-residual receipts.
47. three consecutive receipted no-candidate campaign outcomes surface the
    shared investigated-turn stagnation pressure, while a finalist resets it.
48. a no-candidate result exits the public inlet as `frontier_no_candidate`
    and `verify` performs no SMT or Lean call.
49. an exact-two campaign rejects a singleton freeze in navigation, recovery,
    signed-packet validation, and interpretation.
50. the interpretation composer rejects premise-role or evidence references
    outside the frozen packet.
51. a grounded key-idea receipt projects to the shared
    `ConstraintFingerprint`/research-isomorphism input shape.
52. a transported interpretation remains advisory until a destination replay
    receipt verifies its discriminator.
53. interpretation exposes proof-dependency-only status and withholds its
    isomorphism fingerprint when logical premise ablation is absent.
54. a presentation forcing a constant/projection/full/empty finite template
    receives a content-bound structural-baseline receipt, and residual entropy
    is conditioned on the joint template support.
55. the regular-unary right-zero collapse reprices from ten residual formulas
    to zero without provider calls.
56. campaign preflight and execution compile the same blueprint identity.
57. the direct equational baseline can receipt a one-step consequence that uses
    one frozen base equation and one candidate equation.
58. an executable theory adapter satisfies both `AbstractionFunctor` and
`TheorySubstrateAdapter` through one inherited alpha/gamma contract.
59. known pre-inference CLI rejections consume zero provider calls, unknown
transport failures consume one, and campaign status names each outstanding
phase/action reservation.
60. a `research_isomorphism` transport cannot enter routine campaign feedback
without a matched destination-selection test and a destination-side
discriminator receipt.
61. topology-map width is frozen separately from candidate-presentation width;
the map is lazy, while any allowed wider presentation keeps an exact extent-
derived node identity.

## 22. Non-goals

- a universal interestingness scalar;
- one Python adapter per named mathematical family;
- unrestricted natural-language semantics at the trust boundary;
- claiming decontamination from model pretraining;
- treating bounded regularity as unrestricted truth;
- broad literature interpretation before candidate freeze;
- replacing LeanMill’s proof or promotion authorities;
- asking an LLM to enumerate a finite space the host can exhaust exactly.

## 23. Done definition

Build completion requires:

1. a natural-language and a structure-first direction both reach
   `explore_axiom_space` and freeze valid packets;
2. the same generic kernel runs the magma and finite-protocol adapters;
3. the full magma context replays with zero provider calls;
4. a compact-pack campaign either freezes a presentation satisfying its frozen
   minimality/dependency bounds or emits a receipted no-candidate result; a
   theory-program campaign freezes explicit residual predictions without
   inheriting those compact-pack gates;
5. at least one larger-model or Lean outcome is recorded with the correct
   status boundary;
6. no family-specific module is reachable as the public research inlet;
7. focused regressions and repository gates pass.
8. a verified candidate emits an evidence-bound interpretation receipt with a
   key-idea mechanism and optional isomorphism fingerprint; prose alone cannot
   change proof or novelty status.
9. one non-magma total-operation signature reaches formula generation, exact
   isomorphism-quotiented context, snapshot replay, generic SMT, and generic
   post-freeze formula rendering without a family module.
10. one base-constrained semantics-rich signature reaches an exact
    solver-enumerated context through the same adapter and reproduces an
    external small-model checksum before any navigator call.
11. the same anonymous object-contrast action works over formal and
    evidence-induced contexts, and a separating typed proposal produces a
    replayable context epoch while a failed contrast does not.
12. post-freeze formula authorship freezes a successor request, preserves the
    source finalist identity, and `continue-epoch` starts with no carried
    finalist.
13. exact prompt bytes replay across prompt-version and budget-state drift;
    legacy result-only traces remain host-replayable, and a candidate-free
    budget stop cannot acquire refusal authority.
14. relations, connectives, quantifiers, conservative definitions, and outbound
    theory-language requests traverse the same typed navigator seam.
15. at least two host-isolated lineages freeze context-bound programs and are
    compared only after freeze; the comparison has no union-theory authority.
16. deterministic navigation cannot silently substitute compact-pack selection
    for a theory-program campaign.
17. blueprint compilation and independent review preserve an invention or
    evolving-language direction in the eigenquestion; the initial grammar may
    orient search but cannot become the campaign identity by compilation drift.
18. leaf-visible trace projection obeys its policy byte ceiling even for one
    deeply nested receipt; complete receipts remain durable, and boundary/sieve
    feedback survives budget stops and resume waves.
19. mixed boundary outcomes preserve every prediction status, including live
    siblings of a refuted target, and subscription dispatch reads the same
    receipted extended wall-clock cap as ledger admission.
20. a language request reaches one compiler-first continuation door; direct and
    AdapterForge-assisted compilation admit the same successor shape, rejection
    returns replayable search feedback, unavailability alone opens a gap, and a
    functor-image successor cannot claim held-out fixed-size semantics.

Scientific claims remain separate. The first campaign may yield a positive,
negative, or partial mathematical result; apparatus completion does not imply
discovery.
