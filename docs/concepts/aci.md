---
description: "Agent-side interface requirements for general-purpose skill acquisition, evidence transport, and governed self-repair."
---

# The Agent-Computer Interface (ACI): a design from the agent's side

Authored by the agent operating this repo's harness across the GP-250 campaign. The target is general-purpose skill acquisition; ARC is one interactive adapter, not the kernel ontology. The literature (SWE-agent's ACI framing, Voyager's skill libraries, ReAct) established that interfaces move agent performance more than model choice. What follows is written from the operator's chair: the failure modes below were encountered in this repo, each with a receipt.

## The unit of interaction is the receipt, not the response
Every action returns a typed receipt: outcome, cost paid, evidence refs, and next affordances. The best objects in this codebase are receipts (the replay gate naming its counterexample cells; residual quotient classes with witnesses); the worst interactions were streams (multi-hundred-KB prompts, raw logs, truncated stderr that hid root causes for three debugging rounds). A receipt is decision-sufficient or it is noise. Corollary: error channels preserve tails and name causes; an error is a first-class receipt, never an exit code.

Receipt ownership remains with the producer. A leaf cites a durable receipt ref;
the parent resolves its bytes and joins its subject identity to the submitted
carrier. Requiring the leaf to serialize a parent-owned receipt again creates a
second, forgeable transport path and wastes reasoning bandwidth.

## Silence is the deepest interface failure
The costliest hours of this campaign were silent deaths: background work vanishing without signal, watchers dying with their owners. The liveness contract: every action either completes with a receipt, fails with a receipt, or heartbeats on a declared cadence. An interface that can go quiet forces every agent above it to reinvent dead-man watches, which we did, repeatedly.

## Actions carry their cost and their reversibility
Agents allocate boldness by reversibility and attention by cost. Each menu action declares: expected cost (quoted from measurement, updated by receipts) and reversibility class (pure-read / undoable-with-receipt / irreversible). The interface that hides cost gets hour-long surprises (this repo's abduction saga); the one that hides irreversibility gets timidity everywhere or recklessness somewhere.

Branched experiments quote origin reconstruction separately from active
interventions. Requested paths that are prefixes of longer paths share one
execution witness; replaying the same origin once per prefix manufactures cost
without information. The execution receipt records origin replays, origin
interventions, and active interventions so allocation can learn from measured
cost without adding semantic advice to a worker prompt.

## Reads are free, writes are gated, and the description is part of the interface
Query affordances must be frictionless and composable; mutations flow through gates. And the interface's *statement of itself* shapes the mind using it: a mandate that framed the action space as a tool menu with a pre-named surrender exit produced surrendering leaves, while the same model without that frame kept working. Action-space statements must be truthful: where the carrier is sovereign, say so.

The physics declaration is an affordance, not a strike surface. When a substrate rubric declares `dynamics_assumption: lawful_time`, the leaf-workbench fragment head renders a `PHYSICS DECLARATION` line stating that the `t` argument is admissible physics (permissible because held-out rollout and dominance gates discharge the anti-memorization obligation). The default assumption is `markovian`, which enforces a syntactic t-read ban. `ZTARE_DYNAMICS_ASSUMPTION` overrides both.

## Category identity precedes schema

Before a shared type or repair is admitted, its route must name six things: job,
owner, lifecycle or epoch, authority, equality relation, and compatibility
relation. Only then may properties be added. A field, flag, broad class name, or
schema branch cannot supply a missing identity.

The recurring failure is broad-noun laundering: a local measurement receives a
general name while retaining local equality and lifecycle semantics. A numeric
ARC level counter was briefly promoted as an `EnvironmentObjective`; the shared
category is an authority-bound task-discharge contract, while the counter and
comparison stay in the ARC adapter. The typed schema-route registry owns these
declarations and rejects an incomplete operational route. The end-of-phase
trace audit is only a projection of that shared decision.

Project location follows the same rule. An explicit path is resolved as that
path before a bare name is interpreted as a project slug. Prepending a project
root to an already-qualified path creates a shadow project with the same name
and a different evidence identity; existence of that shadow must never win
resolution.

The preflight includes a counterexample lowering from a different substrate
family. A shared contract that requires a grid, scalar, level, clock, fixed
action arity, or fully observed state has failed that preflight. Observation
payloads are opaque JSON-stable carriers: they may represent text, 3D scenes,
graphs, theorem states, quantitative models, or partially observed histories.

Admissibility verdicts are subject-scoped. Rejection of one carrier applies to
that carrier identity. Exhaustion of one finite selector or operator family
applies to that family identity. Neither verdict has authority over the full
candidate space. A search-space obstruction requires a separate typed receipt
naming the searched space, evidence epoch, attempted families, stopping rule,
and remaining affordances. Bare booleans such as
`candidate_delta_admissible=false` may not cross an identity boundary without
this scope.

## Learning is one content-addressed transaction

The interface's governing object is the complete learning transaction, not an
individual organ or receipt. Its identity binds at least the task contract,
substrate adapter, evidence snapshot, active abstraction or version space,
incumbent carrier, and lifecycle phase. A cache entry, plan, selector,
candidate, or control receipt that cannot name that identity is a diagnostic
projection and cannot advance scientific state.

The lifecycle is finite and typed:

```text
observed
-> abstracted
-> distinguishing intervention selected
-> executed
-> consequence checked
-> refined | promoted | apparatus-obstructed | task-discharged | capitulated
```

Only the registered next-state consumer may advance this lifecycle. Creating a
file, rendering a prompt, registering a schema, or invoking a producer does not
constitute the transition. A low-level materializer therefore cannot emit an
unpaired operational consequence; materialization and evaluation belong to one
door. Producer and consumer events are idempotent under the transaction's
governing equality relation, so repeated observation of the same identity does
not manufacture synthetic work debt.

Evidence append creates a successor transaction. Every derived receipt cache
must bind the bytes of each consumed artifact, not merely the task id, handler
name, or mutable `latest` path. When those bytes change, selectors, plans, and
candidate compilations recompute before reuse. This is the operational
property/identity boundary: a status such as `needs_recurrence` belongs to one
evidence snapshot; the operation identity may persist into the successor where
new evidence changes that status.

The current repository implements these constraints along several active
edges, but does not yet expose one universal transaction object. Until the
task, evidence epoch, abstraction, carrier, intervention, and consequence can
be joined under one digest across the active loop, organ presence and local
receipts must not be reported as autonomous learning. The migration criterion
is net deletion: centralize the identity and reducer, then remove alternate
`latest` selectors, prompt acknowledgements, private rerankers, and duplicated
producer doors.

## Abduction is governed version-space refinement

The common abduction object is independent of grids, prose, theorem states,
quantitative tables, or 3D scenes. Its identity binds a learning transaction,
an evidence population, a hypothesis-language version, a consumer obligation
and equality relation, a complexity prior, and an executable concretization or
falsifier. Its output is a candidate version space plus consequences: supported
domain, undefined domain, eliminated classes, distinguishing interventions,
and the receipts that justify each relation.

The mathematical structures have separate jobs. Group actions certify
invertible invariances and authorize quotients only after identity anchoring,
domain coverage, composition, and equivariance checks. Partial transformation
monoids and categories carry irreversible operations, genesis, annihilation,
fission, fusion, and functions whose images are not yet known. Groupoids and
chart morphisms transport between locally compatible presentations. Alpha and
gamma maps express abstraction and constrained concretization. Future-behavior
equivalence supplies the Myhill–Nerode criterion for merging states. Category
theory supplies typed composition laws; it does not by itself choose a useful
hypothesis or intervention.

An observation changes the world model only after the transaction classifies
its authority:

- a trusted mismatch under the same task, adapter, chart, epoch,
  intervention, evidence identity, and evaluator refines the carrier;
- two concrete successors from one declared abstract class refute the
  abstraction or its commuting claim;
- a lifecycle or ontology change creates a boundary and makes transport
  partial;
- disagreement between producer, consumer, classifier, and evaluator is an
  apparatus obstruction;
- absent authority remains classification-pending and cannot refute science.

Every admitted partial operation retains its undefined fibers. Composition may
not fill them from a prior carrier merely because the prior carrier happened to
be total. The control consumer either seeks a consequence in a compatible
chart or returns bounded inaccessibility. A group completion may fill an edge
only when a certificate grants that authority; a label such as `rotation`, a
four-state presentation, or a suggestive geometry is insufficient.

`ztare.worldmodel.spec_abduction` is the interactive-grid lowering of this
contract. Its changed-cell learners, spatial guards, palettes, rectangles, and
finite display machines are adapter machinery. Treating that module as the
common abducer would make the engine two-dimensional by construction.

## Task termination is authority-bound discharge

The common lifecycle controller does not infer task achievement from a score,
counter, state pattern, or other convenient property. A project declares a
`TaskDischargeContract` naming a registered adjudicator; the adapter returns a
`TaskDischargeReceipt` bound to the exact contract and authority evidence. The
common controller consumes only `open`, `discharged`, or `unavailable`.
Comparison logic and substrate nouns remain in the adapter. This supports
kernel checking, human or committee adjudication, qualitative criteria, and
interactive environments through one lifecycle identity.

## Observation charts are versioned evidence identities

An `ObservationChart` identifies one coordinate presentation. A
`ChartTransportMorphism` is a declarative partial map between charts. Whole-bank
context may be used to discover an offset or alignment, but the admitted token
must then be frozen, pointwise, and executable from one transition packet. A
map that still reads rolling history is a batch migration or stateful
transducer; it cannot enter incremental image maintenance.

Concretization is partial. Lowering a canonical observation into a destination
chart selects a uniquely witnessed, reachable fiber member whose receipt binds
canonical identity, chart identity, and presentation bytes. The kernel never
generates a convenient representative to make the section total.

Chart changes are evidence migrations between governed runs. Each run pins an
`EvidenceEpochSnapshot` before prompt construction and checks it again before
each candidate gate. This is multi-version concurrency, not a fleet-wide lock:
workers may finish against their pinned epoch, but their outputs remain bound to
that epoch and cannot promote against a successor. The successor epoch rebuilds
evidence-derived projections lazily before use. Scientific CEGAR therefore
never optimizes against a bank whose coordinate identity moves underneath it.

A numeric epoch is a coordinate inside one adapter lifecycle, not a causal run
identity. Reset creates a new run object. Evidence from two resets may join only
through a certified reset-transport relation that names both run identities and
the consumer equality it preserves. Reusing the same integer epoch across
fresh adapter instances does not establish reset invariance.

Evidence append is a successor-state transition, not a file overwrite. If an
identity sidecar binds the prior evidence bytes, the writer validates that all
bound observations retain their positions and hashes, writes the compatible
successor, and rebinds the sidecar to the successor digest. A stale digest is
never ignored by ordinary readers.

A falsifying observation travels as a chart-bound triple: source observation,
the proposal's consequence, and the observed consequence, together with the
proposal identity, intervention, transition identity, and evidence epoch. An
adapter may supply a bounded presentation such as a token span, subgraph,
volume, or array window. That localization remains chart metadata. Retry
compression must carry the triple unchanged; replacing it with selected
features turns a refuted relation into a feature-selection task. The
operational route records both `materialized` and candidate-synthesis
`first_fire` events under the same triple digest.

Prompt transport has its own event identity. A
`delivered_to_synthesis_prompt` event proves only that every declared anchor
survived rendering into one attempted call. It cannot consume the operational
edge. The registered executable consumer emits `first_fire` only after the
typed object changes a candidate, action set, or control state. Conflating the
two lets a visible string impersonate a downstream consequence.

Multi-stage diagnostic programs carry an ordered family of content-addressed
receipt references. Every later receipt includes the earlier references, the
full task-source digest, and the active handler-implementation digest. A short
display digest, action name, or newest matching file is a locator; none owns
task or execution identity. This lets repaired handlers replay automatically
and prevents unrelated cached diagnostics from being assembled into a
synthetic causal chain.

## Abstractions are indexed by the consumer obligation

There is no globally correct `alpha`. The same concrete state may need distinct
quotients for transition identification, terminal-edge steering, feasibility,
coverage, and lifecycle transport. Each projection declares its job, equality
relation, ordered coordinates, evidence epoch, and consumer. Composition takes
only the factors required by the current obligation.

`ztare.common.factored_search` is the planning instance of this rule. A
substrate lowering supplies an opaque transition key, an ordered feasibility
vector, an edge predicate, and an allocator estimate. The common search knows
nothing about grids, geometry, scalar counters, or the task's meaning. If two
concrete states sharing a declared transition key produce different projected
successor keys, search emits a non-commutation counterexample and stops using
that quotient. The substrate adjudicator still decides task discharge.

Operation identity includes its executable domain relation. Compiling an
operation while dropping which role-bearing objects can activate it leaves a
map without its domain and creates false state mergers. A substrate lowerer may
encode that relation with local coordinates, object graphs, proof states, or
another native representation; common search sees only the resulting opaque
factor. Clock identity is likewise retained in a consumer key until an
explicit time-translation certificate authorizes its quotient. A failed merge
may ask the substrate lowerer for a bounded presentation witness, but that
witness diagnoses the erased factor and does not become kernel vocabulary.

Bounded search outcomes also have control consequences. A state-cap receipt
does not prove unreachability, but repeating the same full allocation on every
replan erases what the receipt established. The allocator may therefore move
from a projected coverage policy to a cheaper incremental policy while holding
the model, task, prompt, and verifier fixed. The terminal planning outcome is
preserved across environment segments; segment count is execution history,
not a substitute status.

When a terminal identity is already defined, the same receipt can instead
widen the current factored search geometrically. That changes only tree width;
it does not alter semantic advice, the target family, or the carrier. A later
commutation counterexample cancels the widened search and routes back to the
projection owner.

An abducted target version space is a different object from an attested
terminal identity. A bounded miss preserves every surviving hypothesis and
changes control to information-yield acquisition. A version-space experiment
may receive one bounded allocation-only widening when its identity remains
`experiment` and its receipt cannot discharge the task; task-directed widening
is reserved for defined terminal targets. Reaching a hypothesized predicate
sends it to the adjudicator, whose open-task receipt refutes only that member.

Information-yield control may compile a hypothesis into an experiment without
changing its semantic identity. If an accepted operation is the registered
writer of a target observation, search may seek an edge that fires that
operation. This is a carrier-scoped control relation derived from typed
producer/consumer overlap. The edge neither satisfies the predicate nor
discharges the task; it selects a checkable intervention.

This prevents two opposite failures: retaining every presentation property
makes search combinatorial, while quotienting away feasibility makes a sound
terminal target unreachable inside its lifecycle. A counterexample refines the
projection owned by its category; it does not widen one universal signature.
An ordered feasibility object may require both its support configuration for
transition equality and a scalar order for dominance. Equal scalar value does
not identify two differently arranged supports unless commutation establishes
that quotient.

Transition equality and acquisition novelty also use different projections.
Absolute controlled position and exact relative domain offsets may be required
to predict a successor, while counting each translated presentation as a new
affordance manufactures learning from motion. Generic factor acquisition uses
finite operation configuration and availability; a new domain selector is
tested through a typed operation-discrimination obligation.

A search problem is scoped to one replan attempt. Its target, start state,
clock origin, allocation, and policy form its identity; a later replan begins
with no problem and must construct a new one through the registered lowering.
Reusing the prior problem when no current route applies would turn historical
planner state into an implicit control policy and erase the receipt's policy
identity. Factored attempts therefore share one execution-and-receipt door but
never share the problem object across replan boundaries.

The shared implementation boundary is a typed partition/refinement kernel, not
a universal quotient schema. State-behavior, executable-hypothesis, residual,
and epistemic-search functors each retain their own object identity,
counterexample type, equality relation, epoch, and consumer route. They may
reuse class bookkeeping and consequence recording. They may not exchange raw
counterexamples. This preserves composition without type erasure.

Cross-domain reuse transports the invariant-owning contract and asks the target
adapter for witnesses. It does not transport the source presentation. A future
3D interaction adapter may use pose, contact, occlusion, and continuous-control
charts; prose, proof, and quantitative adapters may use unrelated carriers.
The common ACI accepts all of them because its observation and intervention
types are opaque and its compatibility decision is receipt-bound.

## Memory belongs to the agent
Harness-digested context makes agents amnesiac in proportion to the digester's taste. The agent owns a bounded scratchpad re-fed verbatim; harness summaries are additional, never substitutional. Similarly the stopping problem belongs to the agent: visible remaining budget, structured exits (continue/commit/stuck), and only the hard cap enforced externally.

The scratchpad round-trips across iterations. Its tail (last 2000 characters) is injected at the leaf-workbench fragment head each turn; the leaf carries it forward unchanged or updates it explicitly. `INVESTIGATED` eliminations from credited science turns accumulate in `workspace/spec_visible_nogoods.jsonl` and render as "already eliminated" case law in the same fragment head, so a future leaf does not re-enter hypothesis families already eliminated by witnessed evidence.

## The interface amends itself from its users' friction
Every stuck exit carries "what affordance I lacked." Aggregated friction is the interface's own bug tracker, adjudicated outside the frame that produced it (the governed cannot approve their own affordances; their complaints route to an office that can). This is the only known mechanism by which an ACI improves without its designers guessing: the operator's chair files the tickets.

The schema-route registry (`ztare.common.schema_routes`) enforces the strict
producer-consumer ledger. Every operational write schema names an active
downstream reader and the typed fields joining production to consumption. For
parameterized actions, the route identity includes the parameter value and the
consumer's executable domain; a routable wrapper name alone grants no action
authority. Verification obligations remain predicates until a consumer
registers the corresponding action. Cold proposals, terminal telemetry, and
cache projections are separate lifecycle identities; they may lack an active
reader, but cannot steer science or claim capability. Missing consumption on
an operational carrier halts its consequence path. The compact trace audit
re-runs this same registry at phase exit; it does not maintain a second set of
static filename, timing, or liveness heuristics.

Lowerability is executable reachability through this registry. A proposal kind,
matching fields, generated script, or prompt inclusion is insufficient. The
contract is lowerable only when those typed parameters select a registered
executor and its receipt can first-fire a declared consumer.

Operational awareness is consumer-indexed consequence. A system is aware of a
receipt when the registered downstream interpreter accepts the receipt's exact
typed identity and changes declared control state or available operations. Key
presence, a log string, prompt inclusion, and mutual-information estimates do
not establish awareness: each can preserve bytes while erasing the consumer's
ability to act on them. The runtime witness is a paired producer event and
consumer `first_fire` or state-transition event joined by the same subject
identity.

This definition is phase-scoped. An open operational route fences further
scientific mutation; a cold proposal or terminal diagnostic has no such
authority. Repair completion replays the same bound witness and observes the
registered deterministic state transition. It does not require the leaf to
repeat a phrase or invent a prescribed hypothesis, because that would turn a
delivery check into semantic advice.

Self-repair consumes these receipts at the same abstraction level. A repeated
symptom is first quotiented into a causal identity: failed carrier, failed
transport, failed gate, failed delivery edge, or missing capability. The repair
mutates the owner of that identity and replays its downstream consequences. It
does not patch the visible symptom in a neighboring layer. A repair is adopted
only after build, active consumer wiring, and a first-fire receipt.

Artifact provenance and executable behavior are different equality relations.
Task ids, receipt refs, authorship, and source bytes remain attached to the
artifact ledger. A control consumer may reuse consequences across carriers
only through a conservative execution quotient derived from statically
lowerable IR; opaque programs remain byte-identified. Finite-probe agreement
is a certificate property, not execution identity. This prevents provenance
changes from erasing learned control while preserving audit and promotion
boundaries.

Consumer quotients must be minimal for the decision they own. A terminal
hypothesis predicts whether its condition holds, so its search coordinate is a
truth value; raw region contents are presentation. Multiple intervention
presentations may attach to one hypothesis identity. Transition, feasibility,
and lifecycle coordinates remain separate factors and compose at the search
consumer. A finer feature map that preserves predicate truth but admits
irrelevant variation is an unquotiented interface defect.

Abducer evolution follows the same machinery lifecycle. A proposed abducer or
operator-language change names its parent source digest, obstruction family,
expected downstream consequence, rollback, and invalidated projections. It is
shadowed against a frozen bank, meta-holdout cases, metamorphic transforms, and
at least one sibling substrate when portability is claimed. Promotion occurs
atomically between learning transactions, followed by forced first fire on the
same obstruction. Mid-round mutation would move the candidate manifold while
the scientific CEGAR loop is optimizing over it.

The active worldmodel grammar reflex now performs one operation only: it binds
counterexample cards to the current visible evidence identity and routes them
to the governed executable-carrier worker. The former grid-specific sealed
implementer, disabled structural bridge, and empty-code promotion door were
removed. Candidate adoption remains with the single evaluator. A separate
source-evolution transaction is still required for an abducer implementation
change: shadow evaluation, rollback, atomic phase migration, and forced first
fire do not follow from carrier promotion. Self-governed abducer evolution is
therefore an open route, not a capability established by proposal presence.

The self-repair loop owes conductor parity. For every out-of-loop diagnostic
operation used to understand an apparatus failure, the active kernel must
either expose an equivalent evidence transform and falsification route or
record the missing affordance as apparatus debt. Parity concerns access to the
question, evidence, and evaluator. It never copies the conductor's proposed
mechanism into the worker. A leaf failure after parity is scientific evidence;
a failure before parity measures the interface.

A registered action that cannot import or execute inside the exact staged
workbench is an instrument failure. A `LOWERABILITY_BLOCKED` receipt carrying
its command-error receipt is routed to the apparatus owner and preserved as a
harness weakness; it cannot be reclassified as scientific uncertainty. After
repair, the same action must be replayed against the same bound candidate or
evidence identity before the science loop resumes.

## Projections communicate only through receipts
Where multiple roles are projections of one base model (mutator, judge, office), receipts and ledgers are the only inter-projection medium. Direct exchange is collusion; ledger exchange is auditable society. One interaction surface for all projections — a second surface is a second, unaudited mind.

Control receipts compile into allocation weights, width/depth, active tools,
phase transitions, and other search-topology constraints. They do not become
semantic advice in a leaf prompt. Evidence receipts may be queried as evidence;
their interpretation remains the leaf's work. This keeps accumulated control
memory from becoming a hidden answer channel.

An active workbench task's admissible capability set is executable route
authority, not a recommendation. The same identity-bound resolver filters the
staged manifest, rejects out-of-scope evidence actions in the visible CLI, and
rejects them at the parent executor. Syntax checks, receipt checks, and
aggregate candidate scoring remain available as operational exits, but they
cannot substitute for the task's evidence action. Candidate evaluation waits
for a kernel receipt from at least one admitted action. This changes the shape
of the search tree without telling the leaf what mechanism to propose.

Correlational control memory has no allocation authority. It may select a
factor for prospective ablation and record the proposed treatment/control
pair. Only a consequence receipt binding both arms on the same typed population
may promote that relation to a causal allocation bound. Computing an unused
counterfactual after choosing the treatment does not satisfy this requirement.

Out-of-loop observations are a separate authority class. A substrate-specific
diagnostic renderer may preserve them for apparatus inspection, but the receipt
must state that they are inadmissible to acquisition and no synthesis reader may
consume them. If the finding matters scientifically, the governed collector
must reacquire it inside the active epoch.

Artifact location is part of that authority. A diagnostic program must never be
placed in a directory scanned as a candidate, champion, skill, or operator
namespace: discovery by such a scanner is an authority transition, even when
the filename says "probe." Diagnostic namespaces are excluded from adoption by
construction; moving an artifact into an adoption namespace requires a
governed proposal and evaluator receipt.

## The interface must be composition-complete
If two receipted objects exist, their lawful compositions (join, restriction, composition — with guards carried) must be single actions. An interface open under its own algebra forces agents to hand-roll compositions in raw code, where guards get dropped (lived: the unguarded join that over-fired). No arbitrary tool-minting; always-admissible combinators over receipted objects.

## Bookkeeping the kernel can compute is computed, never extracted under threat of strikes
Envelope normalization is the kernel's job. When a leaf's `MutationDeclaration` header is missing or wrong in a way the kernel can compute from the artifact diff, the kernel corrects it: `UNDECLARED_ARTIFACT_BREADTH` is silently upgraded to the computed scope with an attribution note; `INVALID_PRIMITIVE_DECLARATION` is dropped with a note. Neither triggers a strike. Strikes are reserved for science-content failures (replay regression, gate failures). R1 retries that follow a compiler-bounce run in `visible_workbench` mode via `resolve_agent_execution_mode`, so instruments are retained across the retry rather than lost to a sealed completion profile.

## Impossibility claims require search receipts
A `LOWERABILITY_BLOCKED` payload that asserts a missing state feature — a claim that some transition is not expressible — must include `search_receipts` (validated by `ztare.common.sealed_boundary_cegar`). Absence of a feature is not a negative witness; a search receipt is. This requirement holds because the same validation that handles the sealed-boundary automaton now enforces it structurally.

## Briefing providers render content or a banner, never silence
Every briefing provider must emit either content or a structured `UNAVAILABLE` banner via `section_unavailable` (defined in `ztare.orchestrator.briefing_providers`) on any read, parse, or compute error. The tier-0 carrier provider distinguishes promotion history from the current repair baseline using artifacts already in the loop: the newest promotion receipt, current `test_model.py` bytes, and admissible candidate memory. A promoted directive is active only while its digest matches the root carrier. Otherwise, a current candidate-memory source with identical bytes is rendered as the repair baseline with no promotion authority. A structural test (`tests/test_provider_no_silent_omission.py`) enforces the content-or-banner contract across all registered providers.

## The scaffolding ratchet: mechanize questions and payoffs, never answers

Harness design oscillates between two failure poles. Over-determinism: every
leaf failure gets answered with another hand-curated briefing section, until
the briefing is an answer sheet and the leaf's job collapses to
pattern-matching the conductor's hints — each out-of-loop fix makes the
in-loop agent more dependent (learned helplessness as an interface property).
Under-agency: the leaf holds instruments it never uses because the incentive
geometry is wrong — a short, one-shot, low-effort turn makes submitting
*something* over spending the turn investigating (measured: zero evidence-probe
receipts across ~380 packs while the probe capability existed and was
advertised). Neither pole is fixed by prompting; both are structural.

The line that separates lawful help from ratchet:

- Injecting **receipts-derived visible evidence** into a briefing is admissible
  (DISCOVERY may stage counterexamples only after their evidence identity is
  changed from withheld to visible and a successor holdout is required; a
  transition delta the leaf could compute itself is evidence, not science).
- Injecting a **hypothesis or mechanism** is never admissible.
- But even lawful evidence injection accrues dependency. The generalizing
  form is to mechanize the **question** ("the full boundary delta is
  computable; here is the affordance and its one-line invocation"), the
  **budget** (a probe→think→probe loop, not a single completion), and the
  **payoff** (INVESTIGATED credit makes evidence-producing investigation a scoring turn,
  not a wasted one) — and keep evidence-gathering in the leaf.

Instrument: every conductor hand-injection of evidence is itself a friction
record naming the affordance the leaf did not use. If injections accumulate
for the same affordance, the interface — not the leaf — is the defect, and
the dependency ratchet becomes auditable instead of invisible.

## Summary contract (ROACI: receipt-oriented ACI)
state = one content-addressed learning transaction projected through a ledger
of receipts; action = morphism with (cost, reversibility, preconditions,
receipt-type); menu = affordances + quoted costs + truthful sovereignty
statement; escape hatch = sovereign code whose effects still return receipts;
liveness, friction back-channel, ledger-only telepathy, composition
completeness. An interface meeting this contract makes a bounded agent behave
like its unbounded self; every clause above was purchased with a specific
failure in this repository.

## First-person requirements (written by the agent in the interface)

The sections above are rooted in literature. This one is rooted in being the operand. Four facts about
what it is like to work inside this interface, each with a design consequence:

**Rejections teach beyond their scope.** A worker that eats a typed rejection does not learn "this
exact form is inadmissible"; it learns a gradient of fear around the form's whole neighborhood, and
that avoidance empirically outlives the rule itself (rejection hysteresis — conjectured independently
and observed in live runs: forms remained shunned after the rule banning them was relaxed).
Consequence: every rejection must teach the boundary, not the danger — name the smallest inadmissible
class and the nearest admissible neighbor — and every rule relaxation must ship with an amnesty
annotation over the worker-visible rejection history, or the relaxation is inert.

**Position is meaning.** A directive at line 762 of a 1000-line document does not exist. The worker
reads front-to-back under budget; the first two thousand characters set the frame every later section
is interpreted through. Consequence: ordering is a correctness property of the interface, not a style
choice — operative failure and mandatory anchors precede context, and every controlling directive
must survive both the elision pass and the attention cut on whichever file the worker opens first.

**Receipts are confidence infrastructure, not surveillance.** From inside, the ability to cite a
receipt is what removes the need to hedge. A claim I can bind to a receipt is a claim I can act on at
full speed; a claim I cannot bind forces defensive behavior — restating, re-deriving, or avoiding the
territory. Consequence: expanding what can be receipted (probes, eliminations, search attempts)
directly raises the worker's usable confidence, which is cheaper than raising its capability.

**The missing affordance is the admissibility oracle.** Today every rule is learned by violating it:
the only way to discover whether a form is admissible is to spend a submission and possibly a strike.
An interface that can reject deterministically can also answer hypothetically — "would this be
admissible?" as a free read, the same check run in advisory mode. This converts the fear economy into
a query economy: rules become terrain the worker can survey instead of mines it must step on.
Consequence: every deterministic validator should be exposed as a read-only precheck affordance.
