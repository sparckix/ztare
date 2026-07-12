# The Agent-Computer Interface (ACI): a design from the agent's side

Authored by the agent operating this repo's harness across the GP-250 campaign. The literature (SWE-agent's ACI framing, Voyager's skill libraries, ReAct) established that interfaces move agent performance more than model choice. What follows is what the literature does not say, because it is written from the operator's chair rather than the observer's: the failure modes below were all *lived* in this repo, each with a receipt.

## The unit of interaction is the receipt, not the response
Every action returns a typed receipt: outcome, cost paid, evidence refs, and next affordances. The best objects in this codebase are receipts (the replay gate naming its counterexample cells; residual quotient classes with witnesses); the worst interactions were streams (multi-hundred-KB prompts, raw logs, truncated stderr that hid root causes for three debugging rounds). A receipt is decision-sufficient or it is noise. Corollary: error channels preserve tails and name causes; an error is a first-class receipt, never an exit code.

## Silence is the deepest interface failure
The costliest hours of this campaign were silent deaths: background work vanishing without signal, watchers dying with their owners. The liveness contract: every action either completes with a receipt, fails with a receipt, or heartbeats on a declared cadence. An interface that can go quiet forces every agent above it to reinvent dead-man watches, which we did, repeatedly.

## Actions carry their cost and their reversibility
Agents allocate boldness by reversibility and attention by cost. Each menu action declares: expected cost (quoted from measurement, updated by receipts) and reversibility class (pure-read / undoable-with-receipt / irreversible). The interface that hides cost gets hour-long surprises (this repo's abduction saga); the one that hides irreversibility gets timidity everywhere or recklessness somewhere.

## Reads are free, writes are gated, and the description is part of the interface
Query affordances must be frictionless and composable; mutations flow through gates. And the interface's *statement of itself* shapes the mind using it: a mandate that framed the action space as a tool menu with a pre-named surrender exit produced surrendering leaves, while the same model without that frame kept working. Action-space statements must be truthful: where the carrier is sovereign, say so.

The physics declaration is an affordance, not a strike surface. When a substrate rubric declares `dynamics_assumption: lawful_time`, the leaf-workbench fragment head renders a `PHYSICS DECLARATION` line stating that the `t` argument is admissible physics (permissible because held-out rollout and dominance gates discharge the anti-memorization obligation). The default assumption is `markovian`, which enforces a syntactic t-read ban. `ZTARE_DYNAMICS_ASSUMPTION` overrides both.

## Memory belongs to the agent
Harness-digested context makes agents amnesiac in proportion to the digester's taste. The agent owns a bounded scratchpad re-fed verbatim; harness summaries are additional, never substitutional. Similarly the stopping problem belongs to the agent: visible remaining budget, structured exits (continue/commit/stuck), and only the hard cap enforced externally.

The scratchpad round-trips across iterations. Its tail (last 2000 characters) is injected at the leaf-workbench fragment head each turn; the leaf carries it forward unchanged or updates it explicitly. `INVESTIGATED` eliminations from credited science turns accumulate in `workspace/spec_visible_nogoods.jsonl` and render as "already eliminated" case law in the same fragment head, so a future leaf does not re-enter hypothesis families it has already closed with witnessed evidence.

## The interface amends itself from its users' friction
Every stuck exit carries "what affordance I lacked." Aggregated friction is the interface's own bug tracker, adjudicated outside the frame that produced it (the governed cannot approve their own affordances; their complaints route to an office that can). This is the only known mechanism by which an ACI improves without its designers guessing: the operator's chair files the tickets.

A trace auditor (`ztare.orchestrator.trace_auditor`) enforces a dead-letter-receipts invariant: every receipt type that a writer emits must have a reader. The auditor detects orphaned receipt kinds and appends improvement riders to `workspace/leaf_proposals.jsonl` for the Strategy Office, distinct from the science-leaf side channel.

## Projections communicate only through receipts
Where multiple roles are projections of one base model (mutator, judge, office), receipts and ledgers are the only inter-projection medium. Direct exchange is collusion; ledger exchange is auditable society. One interaction surface for all projections — a second surface is a second, unaudited mind.

## The algebra must be closed
If two receipted objects exist, their lawful compositions (join, restriction, composition — with guards carried) must be single actions. An interface open under its own algebra forces agents to hand-roll compositions in raw code, where guards get dropped (lived: the unguarded join that over-fired). No arbitrary tool-minting; always-admissible combinators over receipted objects.

## Bookkeeping the kernel can compute is computed, never extracted under threat of strikes
Envelope normalization is the kernel's job. When a leaf's `MutationDeclaration` header is missing or wrong in a way the kernel can compute from the artifact diff, the kernel corrects it: `UNDECLARED_ARTIFACT_BREADTH` is silently upgraded to the computed scope with an attribution note; `INVALID_PRIMITIVE_DECLARATION` is dropped with a note. Neither triggers a strike. Strikes are reserved for science-content failures (replay regression, gate failures). R1 retries that follow a compiler-bounce run in `visible_workbench` mode via `resolve_agent_execution_mode`, so instruments are retained across the retry rather than lost to a sealed completion profile.

## Impossibility claims require search receipts
A `LOWERABILITY_BLOCKED` payload that asserts a missing state feature — a claim that some transition is not expressible — must include `search_receipts` (validated by `ztare.common.sealed_boundary_cegar`). Absence of a feature is not a negative witness; a search receipt is. This requirement holds because the same validation that handles the sealed-boundary automaton now enforces it structurally.

## Briefing providers render content or a banner, never silence
Every briefing provider must emit either content or a structured `UNAVAILABLE` banner via `section_unavailable` (defined in `ztare.orchestrator.briefing_providers`) on any read, parse, or compute error. The live-champion provider (tier 0, priority 18) renders the mandatory patch-base directive from `workspace/champion_materialization.jsonl` as the first thing the leaf sees; without it a leaf cannot identify the champion to patch and regresses. A structural test (`tests/test_provider_no_silent_omission.py`) enforces the content-or-banner contract across all registered providers.

## The scaffolding ratchet: mechanize questions and payoffs, never answers

Harness design oscillates between two failure poles. Over-determinism: every
leaf failure gets answered with another hand-curated briefing section, until
the briefing is an answer sheet and the leaf's job collapses to
pattern-matching the conductor's hints — each out-of-loop fix makes the
in-loop agent more dependent (learned helplessness as an interface property).
Under-agency: the leaf holds instruments it never uses because the incentive
geometry is wrong — a short, one-shot, low-effort turn rewards submitting
*something* over spending the turn investigating (measured: zero evidence-probe
receipts across ~380 packs while the probe capability existed and was
advertised). Neither pole is fixed by prompting; both are structural.

The line that separates lawful help from ratchet:

- Injecting **receipts-derived evidence** into a briefing is admissible
  (DISCOVERY may stage counterexamples; a transition delta the leaf could
  compute itself is evidence, not science).
- Injecting a **hypothesis or mechanism** is never admissible.
- But even lawful evidence injection accrues dependency. The generalizing
  form is to mechanize the **question** ("the full boundary delta is
  computable; here is the affordance and its one-line invocation"), the
  **budget** (a probe→think→probe loop, not a single completion), and the
  **payoff** (INVESTIGATED credit makes honest investigation a scoring turn,
  not a wasted one) — and keep evidence-gathering in the leaf.

Instrument: every conductor hand-injection of evidence is itself a friction
record naming the affordance the leaf did not use. If injections accumulate
for the same affordance, the interface — not the leaf — is the defect, and
the dependency ratchet becomes auditable instead of invisible.

## Summary contract (ROACI: receipt-oriented ACI)
state = ledger of receipts; action = morphism with (cost, reversibility, preconditions, receipt-type); menu = affordances + quoted costs + truthful sovereignty statement; escape hatch = sovereign code whose effects still return receipts; liveness, friction back-channel, ledger-only telepathy, algebraic closure. An interface meeting this contract makes a bounded agent behave like its unbounded self; every clause above was purchased with a specific failure in this repository.

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
choice — operative failure and mandatory anchors precede context, and every load-bearing directive
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
