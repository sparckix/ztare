# Continual skill semantic-authority result

Date: 2026-07-29

Status: motor compression and fast recurrent-state value confirmed;
outcome-priced recall and Level 3 remain open

This result combines the frozen H63 history audit with three bounded
active-epoch planner runs. The frozen audit made no environment call. Every
active run restored the established seed through Level 2 and retained the
external level-count adjudicator as task authority.

## Measured result

- Four guarded motor programs losslessly compressed 825 primitive operations
  to description length 297, a gain of 528.
- On seven held-out trajectory segments, the same library encoded 187
  primitive operations as 49 control tokens. All seven segments compiled.
- Environment interventions saved by that compression: 0.
- Reindexing the four motor programs by witnessed effects now produces 21
  effect-schema parents containing 48 guarded context variants. The identity
  repair collapsed the prior 48 context-bound leaves without discarding any
  initiation or terminal-context guard.
- All four motor programs are context-gated; none has one invariant effect.
- After the active runs, persistent memory contains four motor families, eight
  revisions, 24 intrinsic learning signals, two whole-run task experiences,
  three controller-decision experiences, zero task-credit witnesses, and zero
  transported families.
- The only retained earlier `+1` level report,
  `workspace/latest_self_play_probe.json`, preserves a 45-operation word and
  an adapter authority statement but no task-discharge receipt or
  effect-aligned transition stream. Its action word is absent from the raw
  episode slices, so it cannot be migrated into option credit without
  inventing the missing state/effect alignment.
- All 21 effect schemas are uncredited for active task contract
  `2bf705da...`; decision pricing admits zero skill invocations.
- The bounded active replay had budget 9. Every available protocol required
  more than 9 primitive interventions, so the planner returned
  `mechanism_protocol_budget_exhausted` and executed zero active actions.
- The live planner reconstructed 21 effect schemas and all 48 context
  variants, emitted no completed choice window, grew no evidence, and left the
  external task-discharge receipt open.
- With budget 17, the first active experiment selected
  `predictive_compatibility_support`, executed 11 interventions, grew evidence
  by one, gained zero levels, and persisted one open decision from a canonical
  two-protocol choice set.
- On the next budget-17 run, exact-context counterfactual completion assigned
  priority 1 to the untried `observed_partial_action_frontier` family. It
  overrode the higher information-density support family for the first leg,
  executed 16 interventions, and left the task open. A witnessed within-epoch
  context transition then created a different choice context; the one
  remaining intervention sampled predictive support there. The run grew
  evidence by one and gained zero levels.
- The two initial-state protocol families therefore have a matched open/open
  comparison. It produces no enabling or hazard witness because neither
  externally discharged the task.

The clearest counterexample is `predictive_compatibility_support`. Its
ten-operation preparation compiles to two safe motor tokens for execution.
Decision pricing retains all ten units because neither motor invocation has
earned task value. The other execution/decision token counts are `6/16`,
`16/65`, and `6/16`.

## Architectural verdict

The engine has acquired reusable motor chunks and now performs one useful form
of internal judgment: it notices an unresolved controller choice and tests the
untried alternative under the same task, external state, controller, budget,
and canonical option set. That behavior changed the live protocol selection.
It has not acquired positive task value, and Level 3 remains open.

The corrected planner keeps three authorities separate:

1. the primitive intervention budget governs whether a protocol may touch the
   environment;
2. guarded motor evidence governs whether a known sequence may execute as a
   chunk;
3. predicted information yield ranks uncalibrated experiments;
4. matched external outcome contrasts may rerank controller-level options
   without changing primitive intervention cost.

This separation prevented the budget-9 replay from spending interventions on
an eleven-intervention protocol. Counterfactual completion then changed the
next live choice from predictive support to the observed frontier. Neither
choice improved Level 3.

Choice-local episodic memory is attached to the controller decision boundary,
not to the motor chunks used to execute its preparation. A choice event
records the task contract, exact external choice context,
controller/continuation context, full feasible protocol-family set, chosen
family and route variant, and the external outcome. Credit is derived only
from attained/open contrasts with the same complete scope. Synthetic tests
confirm that changing the controller context blocks both credit and
counterfactual priority.

## Missing learning object

The current persistent object is close to a motor habit:

`exact initiation identities -> fixed operation word -> witnessed local effect`

The retained hierarchy now has six separately governed parts:

1. an effect-schema identity shared across compatible contexts;
2. context-specific initiation and termination variants;
3. one or more motor implementations;
4. a controller-level experiment family and route variant;
5. an externally grounded task-value distribution scoped to one complete
   choice surface;
6. uncertainty plus evidence provenance used to choose the next contrast.

The 48-to-21 collapse now occurs in the identity model rather than only in the
analysis. Controller choices now persist and affect exploration. The missing
learning object is distal task credit: both tested experiments left the
terminal task open, yet either may enable a later experiment. The memory has
no transition-value model that propagates a later external discharge backward
through earlier epistemic decisions.

The current system also predicts information yield but does not persist a
calibrated predicted-versus-observed information-gain error for each protocol
variant. It can choose a diverse contrast, but it cannot yet learn that one
kind of experiment systematically improves or fails to improve the next
decision state. The unreplayable earlier success remains an episodic-recording
failure: its terminal summary discarded the aligned intermediate choices
needed for temporal credit.

## Next discriminating experiment

Add one step of externally anchored temporal credit without treating evidence
growth as task success. Each controller decision must retain its predicted
information yield, observed response, resulting decision-state identity, and
eventual task discharge. Replay can then test whether an earlier experiment
reliably enables a later credited choice.

- Pass: a protocol family earns distal credit only when its witnessed
  successor decision state lies on multiple externally discharged chains; the
  credit changes ranking in a compatible held-out context while primitive
  cost remains unchanged.
- Kill: the apparent credit reduces to raw evidence growth, fails under a
  matched alternative, crosses a context boundary, or leaves decision ranking
  unchanged.

More motor replay and more immediate open/open choices cannot answer this
question.

## Frontier actor and wake-sleep continuation

The later H82--H86 sequence corrected the acting-controller identity and then
tested a first memory bridge.

- H82 gave all actions to one resumed GPT-5.6 Sol `xhigh` session. It gained
  one level at action 20.
- H83 reset the model session at every action while preserving the game,
  observation encoding, instructions, and budget. It gained zero levels in 32
  actions. Fast recurrent reasoning state therefore has measured value on this
  task.
- H84 let one resumed actor spend all 32 actions. It gained one level at
  action 16, then spent its remaining budget on a wrong subgoal.
- H85 established the substrate-neutral mechanics of matched inject/ablate
  credit, guard-overlap competition, exact-scope rejection, and
  probation-before-demotion on a sealed synthetic stream.
- H86 inserted one same-session consolidation inference after the first level
  boundary. It recorded 32 actions, 33 observations, one stable session, and
  one sleep tick. Three of seven proposed memories re-entered the actor. The
  result remained one level; the post-boundary trajectory again pursued an
  untested ring.

H86 shows that wake-sleep scheduling plus compression is insufficient. The
selected memories were ranked by the same model's uncalibrated predicted
decision delta, so consolidation mostly rehearsed already available beliefs.
The top memory was the cardinal control map, a high-confidence fact already
resident in the resumed session. No external decision effect had yet priced
any candidate.

The first live bridge also conflated two contexts. Each memory correctly cited
its acquisition episode, and the router selected under the boundary
observation. The selected digest then persisted across subsequent observation
changes without a fresh compatibility decision. Acquisition provenance and
consumption scope must be separate identities. The next live discriminator
must retrieve at each decision from a slower store, settle randomized
inject/ablate effects on an exact decision surface, and leave primitive
environment-action cost unchanged.

This next discriminator should be treated as a ZTARE reproduction and
extension of ProactAgent's paired-prefix retrieval/no-retrieval method
(arXiv:2604.20572), not as an architecture-novelty test. The comparative
question is whether exact receipt identities, certified experimental strata,
guard-overlap pricing, and contradiction provenance add measurable value over
that closer baseline.

H87 executed the paired-prefix discriminator after separating acquisition,
one-shot consumption, and experimental-stratum identities. Three randomized
pairs restored the same initial `ls20` observation, used fresh Sol `xhigh`
sessions, and charged 20 actions to each arm. Inject received the H86
three-memory bundle once at the prefix. It completed Level 1 at actions
`13,15,15`; controls completed at `20,miss,15`. Total task score was `3/2`;
paired `0.8 task + 0.2 efficiency` deltas were `0.07,0.86,0.00`, for a mean
`0.31` against predicted `0.20`. The preregistered exploratory criterion
passed.

This is bundle-level, same-game evidence. Direct observation-novelty yield
delta was `0.00`, per-pair prediction MSE was `0.1642`, and treatment carried
extra prompt tokens. The next comparison should factor mechanic memory from
the redundant control map, add a length-matched placebo, and learn when to
retrieve across fresh episodes rather than replaying the whole bundle at a
fixed prefix.

H88 performed the first factorization. It compared two H86-supported causal
memories against three H86-supported but redundant true memories. Both
conditions rendered to exactly 3,849 canonical JSON UTF-8 bytes, were consumed
once at decision zero, restored the same initial observation, and spent 20
actions. Causal mechanics completed Level 1 at `13,15,13`; redundant true
memory completed at `19,miss,14`. Total task score was `3/2`; paired composite
deltas were `+0.06,+0.86,+0.01`; mean observed delta was `+0.31` against
predicted `+0.15`. The outcome-corrected allocator selected the causal revision
despite its lower producer rating.

The effect was early search control. Redundant-memory arms could infer the
marker/glyph mechanism online, but they first spent actions on a direct
terminal hypothesis or later orientation repairs. Distinct-observation yield
remained unchanged. The causal bundle therefore changed which supported
hypothesis controlled action, rather than expanding visible contact or
providing a complete route.

All H88 pairs executed causal first because the frozen randomizer produced the
same order three times. A right-first replication is owed before the ranking
can be treated as order-independent. Even a successful replication would
leave the principal judgment question open: selecting or withholding the
intervention from the live state rather than forcing both conditions at the
initial prefix.

H89 ran all three pairs in the reverse order. Causal mechanics completed at
`13,20,20`; redundant true memory completed at `16,miss,13`. The causal
intervention retained a `3/2` task advantage, won two of three composite
comparisons, and averaged `+0.2567`. Combined H88+H89 evidence has three pairs
per order, `6/6` causal completions versus `4/6` redundant completions, and one
negative-transfer pair.

H90 tested the first temporal-credit use. The H89 result and embedded credit
state rehydrated under exact hashes. That state autonomously chose causal
mechanics, while the producer-prior allocator chose redundant memory. Four
fresh paired controllers used balanced order and the same presentation and
action costs. The trained choice completed at `19,20,13,miss`; the prior
choice at `14,20,13,13`. Trained allocation won no pairs, had task delta `-1`,
and averaged `-0.2325`. The compounding hypothesis was rejected.

The missing conditioning variable is the controller proposal before recall.
All H90 arms shared the same observation, but some spontaneously chose the
marker-first hypothesis and others chose direct terminal entry. Delivery of
causal memory did not reliably alter that proposal. A delivery receipt
therefore cannot authorize decision-use credit. The next circuit needs a
draft, inject/challenge/silence gate, revised draft, explicit use relation, and
external settlement attached to the gate decision.

H91 instrumented that missing transition. Four alternating pairs gave every
controller a blind proposal and a same-observation commitment after either
causal mechanics or an exact-byte redundant-true placebo. Both arms used
3,849 canonical UTF-8 bytes, two inference calls before action, and 20
primitive actions. Target memory completed at `13,15,13,15`; placebo at
`16,20,20,16`. Target won all four composite comparisons and averaged
`+0.04`.

Only one target arm was credited with a newly supported proposal transport,
versus zero placebo arms. The first stage was `+0.25`; the instrumented
estimate was identified with provisional complier effect `+0.16`. Three
successful target runs received no supported-uptake credit. This repairs
H90's delivery-equals-use error.

The frozen text adapter then exposed a deeper identity boundary. Several
blind controllers called the floor object the moving “marker,” so lexical
matching mistook a wrong-object plan for a precondition-first plan. The next
continual object is not another content score. It is a response family over a
shared world/proposal quotient: content-addressed world objects and roles,
planned object-role paths, exact intervention transport, and external
settlement. Held-out admission remains blocked until that object bridge
replaces lexical proposal features.

H92 compiled that bridge and immediately exposed an interface error. The
content-addressed objects were unique and the first two target/placebo pairs
produced exact path contrasts, but a later controller copied one 64-hex
occurrence ref incorrectly. The fail-closed kernel rejected it. Exact hashes
remain the evidence identity; they should not be the controller's working
pointer.

H93 introduced a deterministic catalog presentation. Role-free handles
`o00...` are scoped by an immutable digest of the observation, catalog, and
complete handle-to-ref map. Raw handle proposals persist before resolution;
the adapter resolves them; the common kernel still receives exact refs. On two
fresh balanced-order pairs, targets revised `o02 -> o03` and placebos stayed
`o02 -> o02`. Exact supported transport was `2/2` versus `0/2`, first stage
`1.0`; target boundaries were `13,15` versus `miss,16`; mean composite delta
was `+0.445`.

H94 compiled those four H93 settlements into one admissible response family
over the exact blind proposal basin. The family required offer/withhold counts
`2/2`, first stage `1.0`, and positive cost-adjusted value `+0.445`. It then
selected causal mechanics for two new controllers from their typed blind plans
before either outcome was known. H90's rehydrated scalar credit state selected
redundant true memory twice. Response controllers completed at `13,13` versus
`14,15`, with task delta `0`, two composite wins, and mean gain `+0.015`.

The continual object is now executable local judgment:

```text
(exact proposal basin, settled response family, intervention cost)
    -> offer | silence | explore
```

This is prospective credit reuse, but only inside one observation and one
trained basin. The next missing edge is certified transport between decision
fibers. A family response may cross an observation or proposal-basin boundary
only if the object transport, proposal quotient, intervention displacement, and
external consequence form a commuting square. Without that certificate, the
correct action is silence or exploration. Chained temporal credit and
accelerating improvement remain open.

H95 supplied one such edge. It transported H94's source response to the
observation after prefix `[2]` through a unique-type object map and a separate
intervention revision morphism. The latter preserves invariant payload,
acquisition provenance, provider, calibration, authority, and primitive cost
while allowing the exact rendered revision to change with consumption
context. Causal and placebo payloads require different certificates; only the
causal target revision enters the response contract.

Across two alternating-order target-fiber pairs, causal supported transport
was `2/2` and placebo spontaneous transport was `0/2`. Causal mechanics
completed at `12,12`; placebo at `miss,19`; task delta was `+1.0` and mean
paired composite gain was `+0.48`. A nearby six-action prefix removed a
required contract object, and the transport compiler refused without calling
a controller. H95 then promoted one target-fiber family from the four new
settlements.

The continual object now supports one certified reactivation:

```text
source response family
    + partial object correspondence
    + payload-preserving intervention re-rendering
    + commuting blind/revised proposal square
    -> explore in target fiber
    -> randomized target settlement
    -> target response family
```

The next missing edge is composition. Individually transportable one-hop maps
may disagree around a loop even when their endpoints look equivalent. The
next compiler must expose that path defect and make it consequential for
admission before claiming chained temporal credit.

## Evidence

- `continual_skill_memory_audit_result.json`
  (`0948c02ce1f138640194be86bcf213d872338a807ea54f953b614dd8c773d236`)
- `continual_skill_budget9_live_replay_result.json`
  (`6a23d32daaac5cf17af8e10be0ed26210e1f605b88f7d68aefde714dd58c5cb4`)
- `continual_skill_budget17_support_result.json`
  (`bd409220497d6f12a1dd8de92e2f19cb1d2795d9fee8bfd047b5958061388577`)
- `continual_skill_budget17_counterfactual_result.json`
  (`ba29bf1c8e98d45637a3fb5a965195787819eaf4e2998ce7f98e10a8285edbac`)
- `projects/arc3_ls20_gov/workspace/continual_skill_memory.json`
  (`182135ceb6ad89eee63bf2ec4b0141bc7272a45225f82276fc837db2fb9d1229`)
- `h82_persistent_subscription_actor_result.json`
  (`b79aa3229ce3570f429cdd381aa8fb13bae58b3b32a0c2951736af644359751d`)
- `h83_fresh_subscription_actor_result.json`
  (`b215a630b851eb53c433f1953a2fddd54f74e1f6394218fa696e0f94908f21cb`)
- `h84_full_budget_resumed_actor_result.json`
  (`b27106f1d08b3f73b40c8b16f03d1519a9abf2ee394f6d5c148ea6b805152ca7`)
- `h85_wake_sleep_credit_router_result.json`
  (`029597d8abd0b99fb04998ce9a13ffab04b26c532887481c0616bae86a920069`)
- `h86_level_boundary_microsleep_result.json`
  (`50ad60cf9bd5738ad556ed37f364d62f7626b554f15b98ead1a16c4b47b1f482`)
- `h87_paired_one_shot_recall/result.json`
  (`ebbc2209ce1b684e804d7751236d7c1a236c4309362ce906580b14bd3f12228a`)
- `h88_pairwise_memory_content/result.json`
  (`9dc9e7fdce2b4479896926c09019da9c896a8ae7e0b9ad6e209cfadadc1de2d7`)
- `h89_pairwise_memory_content_reverse/result.json`
  (`2093a1c1a12b7bc3362ef4e66f684f38fab8e545635b62f5f7d3ef6a06479fcc`)
- `h90_heldout_outcome_trained_selector/result.json`
  (`3b0d070afed8526ba84210b6e60b557aed753949247bf37c296a32beaa437f2b`)
- `h91_instrumented_proposal_plasticity/result.json`
  (`8608e4b95f0f4e30da7c354d04595fe15b289843532ad160542dee280343f395`)
- `h92_object_linked_judgment_quotient/result.json`
  (`60bacd9d859d05bafb37d6f7df59758ce9ce33f16559109174ae00f5dc379e79`)
- `h93_catalog_scoped_pointer_judgment/result.json`
  (embedded result
  `09f424c2bf4079d543de8ea08b591873bd7aee51605903dbfd13c18b622ba0b0`;
  file
  `c3f9121fedd5639294ea78afdd002d7fe604bc83df213d86a78e1080e81c1a4a`)
- `h94_prospective_response_family_admission/result.json`
  (embedded result
  `21d66a4a6ddd6ba48f0a1bbe3faa0d98ef78453eacbe6aead26cc3d963f36a7d`;
  file
  `67865c448988bcbf9afb4141efb738258d2ed1426f34bd76072702e9df6183c2`)
- `h95_response_transport_square/result.json`
  (embedded result
  `ec5c63057dcdd7ba18b1ceb29fa75ffe883b5548eee2ac6ee9ce30e8b1f15bf9`;
  file
  `6fd1cb577eb0fed0799622e02f0da35120ca58988defda2e622baf242cdebbea`)
- earlier cumulative focused verification: `274 passed`
- H90 identity/harness verification: `23 passed`
- H91 proposal-plasticity verification: `37 passed`
- H93 pointer-bridge focused verification: `29 passed`
- H94 response-family focused verification: `19 passed`
- H95 response-transport focused verification: `32 passed`
