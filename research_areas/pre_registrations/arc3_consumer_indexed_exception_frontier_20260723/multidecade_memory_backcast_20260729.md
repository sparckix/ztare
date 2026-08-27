# Multi-decade memory backcast

Date: 2026-07-29

Status: conjecture and architecture selection

## Method

For each era:

1. stand inside the era and use only capabilities visible at that time;
2. name the locally rational orthodoxy;
3. identify anomalies already visible but assigned to the wrong category;
4. look backward from the next regime and name the category boundary that
   moved;
5. project the same error pattern forward to 2036;
6. lower the backcast into an executable capability with a kill test.

The point is not to ridicule a prior period. Each orthodoxy was adapted to its
compute, data, optimization, and deployment constraints. The useful question
is which object people thought was fixed but the next regime made learnable.

## 2005 from inside 2005

The modal high-status machine-learning program emphasized statistical
generalization, convex objectives, kernels, boosting, carefully designed
features, and task-specific pipelines. The framing was sensible:

- optimization failures were common and expensive;
- labeled data was relatively scarce;
- compute and storage constrained end-to-end experiments;
- transparent guarantees and decomposable pipelines reduced risk;
- a chosen feature map made the task legible to a reliable learner.

Several anomalies were already present:

- multilayer neural networks could learn representations, though training was
  unreliable;
- web-scale data and commodity parallel hardware were growing quickly;
- speech, vision, and text all suffered from hand-designed representation
  bottlenecks;
- unsupervised and self-supervised objectives could exploit unlabeled data;
- the feature map determined more of the ceiling than the convex optimizer.

### What 2015 saw in retrospect

The category boundary moved from `learner over a fixed representation` to
`learner of the representation and the decision rule together`.

The missed object in 2005 was not a specific neural layer. It was the
representation itself as an optimizable, scale-sensitive state. Kernel
selection automated part of the map, but retained the assumption that the
important learning problem ended at a static input-output function.

## 2015 from inside 2015

Deep supervised learning had overturned much of the prior representation
orthodoxy. Convolutional networks, recurrent networks, LSTMs, large labeled
datasets, GPUs, and end-to-end training formed a new center.

The locally rational assumptions were:

- different modalities and tasks deserved different architectures;
- sequence learning required recurrence or convolution;
- deployment mostly evaluated a frozen trained function;
- labeled benchmark performance was the clearest capability measure;
- transfer learning meant adapting a trained representation to a nearby task.

Anomalies already visible included:

- word vectors and language modeling learned broad reusable structure;
- sequence-to-sequence attention relaxed fixed-vector bottlenecks;
- one model could condition on instructions or examples rather than receive a
  new output head for every task;
- unlabeled text supplied far more supervision than curated labels;
- scaling data, model size, and compute kept yielding smooth improvements.

### What 2025 saw in retrospect

The category boundary moved from `task-specific trained predictor` to
`general conditional computer pretrained on a broad stream`.

The missed object in 2015 was the task interface. A task did not always need to
be compiled into a new architecture or parameter update; it could arrive as
context. Attention and self-supervised pretraining made conditional behavior
the reusable unit, while scaling made that unit unexpectedly broad.

The Transformer paper's removal of recurrence was a decisive training and
parallelization move. A later mistake was to generalize this engineering win
into the claim that recurrence, persistent state, and multi-rate memory were
conceptually obsolete.

## 2025 from inside 2025

The modal program combined large pretrained Transformers, post-training,
longer context, retrieval, tools, reinforcement learning, synthetic data, and
inference-time reasoning. The locally rational assumptions were:

- most capability resides in model weights;
- more context approximates memory;
- retrieval means finding semantically relevant text;
- a skill is a reusable prompt, tool, policy, or action macro;
- inference is a temporary application of a mostly fixed model;
- benchmark results can be attributed primarily to the named model.

The visible anomalies were:

- harness state and continuation semantics could change scores by multiples
  without changing weights;
- long context increased availability but did not decide what should control
  the next action;
- retrieval often returned similar material with low causal relevance;
- agents repeatedly relearned action semantics and failed branches across
  calls;
- test-time learning and neural-memory systems blurred inference and learning;
- sparse attention worked best when routing was content-dependent;
- episodic replay in brains selected and transformed memories rather than
  copying the full waking stream;
- tool-using systems exposed a controller-identity question: which process
  actually owned the observation/action chronology?

### The ZTARE manifestation

ZTARE built several strong slow-layer components:

- exact episode and authority identities;
- a guarded skill compiler;
- persistent skill families and revisions;
- predictive quotient transport;
- deterministic briefing providers;
- an attention agenda over structured records;
- counterfactual choice memory.

The ARC probe then assigned the action boundary to a deterministic compiled
planner. GPT-5.6 Sol did not act. Motor compression and protocol selection
worked, but produced zero level credit.

When Sol owned the action chronology:

- one resumed `xhigh` session gained level 1 in 20 actions;
- 32 fresh `xhigh` sessions gained zero levels in 32 actions;
- a full-budget resumed session gained level 1 at action 16, retained its
  action map into level 2, chose a costly wrong subgoal, and ended at one level
  after 32 actions.

This separates three axes that the word “memory” had collapsed:

1. **fast recurrent workspace** — maintains hypotheses and prediction errors
   across adjacent actions;
2. **episodic memory** — preserves the exact observation, action, prediction,
   successor, and external event stream;
3. **slow consolidated memory** — extracts guarded structure that transports
   across episodes and can be selectively recalled.

The fourth axis is selection: which slow memory enters the fast workspace at a
particular decision boundary.

## 2036 backcast

This is a conjectured regime, not a forecast claim.

Assume that by 2036 competent agents are routinely treated as multi-rate
adaptive systems rather than single model calls. A mature system has:

- a pretrained prior supplying broad competence;
- a persistent recurrent workspace for the current causal thread;
- a high-fidelity episodic store;
- event-triggered offline and micro-sleep replay;
- a slow schema/skill learner;
- learned sparse retrieval into the workspace;
- external action and verification channels;
- homeostatic pruning, interference tests, and reconsolidation;
- calibrated credit linking recalled memory to later decision quality.

From that vantage, several 2025 assumptions look like category errors.

| 2025 category | 2036 backcast |
|---|---|
| Context length is memory | Context is addressable material; memory includes write, consolidation, selection, update, and forgetting |
| RAG is recall | Similarity search is one candidate generator; recall is a decision-valued routing act |
| A skill library is learned judgment | A skill is a slow proposal until a fast controller selects it under a compatible context and outcome credit |
| Sparse attention is a compute trick | Sparse attention is resource allocation over competing causal hypotheses |
| Inference and learning are separate | Adaptation occurs at several rates: token, action, episode, sleep cycle, and population |
| Benchmark score is a model property | Score belongs to a coupled model–state–harness–action interface |
| More stored experience means improvement | Unselected or uncredited memory creates interference and orientation cost |
| Distillation copies behavior | Consolidation transforms episodes into guarded abstractions and may deliberately forget detail |

## Forward–backward–forward invariant

Across the three transitions, the recurring move is:

`a supposedly fixed interface becomes a learned, stateful allocation problem`

- 2005 → 2015: fixed features became learned representations.
- 2015 → 2025: fixed tasks became contextual conditional computation.
- 2025 → 2036: fixed inference context becomes a learned multi-rate memory and
  attention process.

The recurring failure is optimizing the component exposed by the current
benchmark while leaving the next regime's allocation boundary outside the
learner.

## Christensen-style orthogonal axes

The incumbent performance axis is model capability on a fixed prompt or
benchmark call. The undersupplied job is competent continuation through a
changing environment under action cost.

These axes must stay separate:

| Axis | Owner | Current state |
|---|---|---|
| Broad prior competence | frontier model weights | strong |
| Within-episode recurrence | response/session chain | useful; H82/H83 measured |
| Exact episodic capture | environment/controller trace | initial plus every successor observation, action edge, epoch, and boundary recorded in H86 |
| Offline consolidation | guarded skill compiler and memory | first same-session actor integration fired in H86; no task payoff |
| Sparse recall | briefing attention agenda | first actor integration compressed seven candidates to three, but carried a boundary-scoped digest across later contexts |
| Causal retrieval credit | external outcome settler | absent |
| Counterfactual planning | online controller/world model | present as reasoning, not outcome-calibrated |
| Verification/authority | adapters and receipts | strong |

ZTARE overinvested in verification, slow compression, and schema authority
while the acting controller and retrieval-credit loop were absent. Those
investments remain useful once routed around the actor rather than substituted
for it.

## Selected capability: Wake–Sleep Credit Router

The next capability is a closed circuit connecting the existing parts.

### Governing identities

1. **Wake episode**
   - owner: acting controller plus environment adapter;
   - lifecycle: one exact task/controller/context/action-vocabulary epoch;
   - content: observation, choice set, chosen action, predicted effect,
     successor observation, external event, and boundary identity.

2. **Sleep candidate**
   - owner: offline compiler;
   - lifecycle: proposed until replay and interference checks pass;
   - content: guarded causal atom or action chunk plus evidence refs;
   - authority: cannot change an online decision merely by existing.

3. **Recall decision**
   - owner: sparse attention router;
   - lifecycle: one online decision boundary;
   - equality: exact task, controller, action vocabulary, context guard, and
     choice-set compatibility;
   - content: selected top-k memories, predicted decision impact, and retrieval
     cost.

4. **Credit settlement**
   - owner: external outcome/ablation evaluator;
   - lifecycle: after the selected decision's successor or later task event;
   - content: predicted versus observed impact, matched alternative or
     ablation, calibration update, and promotion/demotion decision.

### Sleep cycle

1. **Replay:** reconstruct exact forward transitions from the episodic store.
2. **Reverse credit:** traverse backward from externally adjudicated events.
3. **Counterfactual stress:** compare a recalled item against a matched
   no-recall or alternative-memory decision where available.
4. **Compression:** merge only compatible atoms; preserve order-sensitive
   coordinates when `AB` and `BA` differ.
5. **Homeostasis:** demote memories that consume attention without reducing
   decision loss; retain weak but high-uncertainty items for targeted replay.
6. **Reconsolidation:** a recalled memory returns to candidate status when a
   compatible observation contradicts its predicted effect.

### Sparse wake routing

Selection is not nearest-neighbour retrieval alone. Each memory bids for a
bounded attention slot using:

`expected decision-loss reduction - retrieval cost - interference risk`

The bid is calibrated from prior recall settlements. Authority and semantic
similarity determine admissibility and candidate generation; observed
decision impact determines continued allocation.

This converts the old briefing-provider registry from a list of things that
can be shown into a population whose members earn attention through measured
usefulness.

## First falsifier

Build a substrate-neutral router over structured memory candidates.

Use a sealed synthetic stream with:

- one high-authority but decision-irrelevant provider;
- one lower-authority provider whose memory changes the correct choice only in
  compatible contexts;
- noisy observed outcomes;
- held-out compatible contexts;
- context and controller mismatches;
- a fixed top-1 attention budget and explicit retrieval costs.

Compare against the current authority/actionability attention agenda.

Pass:

- learned routing has lower held-out decision regret than the static agenda;
- the causal provider becomes top-1 only after outcome evidence;
- incompatible outcomes cannot update its credit;
- the same provider is demoted when its measured value falls below retrieval
  cost.

Kill:

- improvement follows semantic or authority labels without outcome evidence;
- credit crosses a task/controller/context/choice-set boundary;
- the router cannot beat the static agenda on the sealed stream;
- attention cost is dropped when a memory becomes a compiled skill.

Only after this falsifier passes should the router consume ARC wake episodes.
The first ARC test is whether a level-boundary micro-sleep reduces actions
spent on a wrong subgoal relative to a resumed-session control. It is a
mechanism experiment, not a leaderboard claim.

## H86 live update

The synthetic falsifier passed, but the first ARC integration did not. H86
used one stable Sol `xhigh` session for 32 actions plus one non-acting
consolidation tick after the action-20 level boundary. It recorded 33 lossless
settled observations. The sleep compiler proposed seven memories and the
router returned three. The actor still gained one level and spent its
post-boundary budget pursuing the same ring-shaped wrong-subgoal family seen
in the resumed-session control.

The failure sharpens the 2036 backcast. A scheduled summary is not yet replay
learning, and a sparse top-k is not yet state-triggered recall. H86 ranked the
same model's predicted usefulness before any live inject/ablate settlement.
It also selected under the boundary observation hash and then reused that
digest after the observation changed. The next circuit needs distinct
acquisition and consumption contexts, a compatibility abstraction evaluated
at each decision, and externally settled marginal value.

The counterfactual layer adds a third identity. Exact controller instances and
trajectories remain distinct because a stochastic session cannot inhabit both
arms. Credit generalizes only through a preregistered exchangeability stratum
over restored decision contexts and controller classes. This is the role of
the quotient: raw hashes secure the evidence, while a tested abstraction
defines which distinct episodes may estimate the same recall effect.

## H87 backcast update

The first repaired paired test supports one part of the 2036 view. Three fresh
Sol `xhigh` controllers given a one-shot H86 memory bundle completed Level 1 at
actions `13,15,15`; matched controls completed at `20,miss,15`, under the same
initial observation and 20-action cost. Total task score was `3` versus `2`,
and the frozen composite decision effect averaged `+0.31`. Distinct-observation
yield did not change.

This changes the emphasis of the backcast. The scarce resource was not stored
knowledge or environmental contact by itself. The measured gain came from
granting old evidence bounded authority over a current decision, then pricing
that grant against a matched controller. From a 2036 perspective, today's
plain-sight category error may be treating memory as context volume. A more
productive unit is a **priced right to perturb a policy**:

1. evidence has an immutable origin;
2. a compatibility relation authorizes transport to one decision;
3. attention allocates a bounded intervention;
4. a matched outcome updates the intervention's conditional value;
5. failed value predictions refine the context partition.

H87 does not complete that loop. It prices one whole bundle at one fixed
prefix, and its per-pair prediction MSE (`0.1642`) is large. The 2036-to-2025
move now points to conditional markets over memory interventions: factor the
bundle, add a prompt-length-matched placebo, retrieve only when a learned guard
fires, and let cross-episode settlements refine the guard. The unresolved
orthogonal axis is **judgment about when knowledge should control**, not more
knowledge compilation.

`decision_intervention_market.py` applies that unit beyond memory. A briefing
record, skill, episodic trace, or retrieved artifact becomes one exact rendered
bid in a shared prompt-token budget, while the existing matched-outcome state
prices it. This exposes the old briefing-provider stack as a candidate
acquisition layer rather than a separate attention doctrine. Live provider
allocation remains untested.

## H88 backcast update: the threshold is loop gain

H88 separated causal content from presentation volume. Two memories describing
the marker-to-glyph transition and glyph-matching task relation were compared
with three true reminders about controls, walls, and marker persistence. Both
one-shot presentations were exactly 3,849 canonical JSON UTF-8 bytes and every
arm received the same 20-action cost from the same observation. Causal memory
completed Level 1 at actions `13,15,13`; redundant true memory completed at
`19,miss,14`. Causal memory won all three paired decision scores and the
outcome-corrected allocator reversed the producer's initial ranking.

This sharpens the plain-sight 2035/2036 category error. Stored knowledge,
context length, compression ratio, and retrieval accuracy are component
properties. The system-level quantity is **closed-loop gain after intervention
cost**:

```text
experience_t
-> causal consolidation
-> selective policy perturbation
-> outcome_t+1
-> corrected selection
-> higher-value experience_t+2
```

A broad-capability turning point would occur when this loop produces more
decision-relevant evidence than it consumes, and the corrected selector
transfers that gain into later contexts. Below that point, memory additions
accumulate without compounding. Above it, better experience improves
consolidation, which improves intervention selection, which improves the next
experience distribution.

H87 established one positive forced-recall edge. H88 established that external
outcome can distinguish causal content from equally presented true context.
The loop is still open at four places: recall timing is forced, silence cannot
win, context compatibility has not generalized, and the learned ranking has
not yet changed performance on a subsequent held-out decision. All three H88
pairs also ran causal first, so a reversed-order replication precedes any
order-independent interpretation.

H89 removed the execution-order concern: three right-first pairs preserved a
`3/2` causal task advantage and positive mean effect, although one pair favored
redundant memory. H90 then closed the next arrow experimentally and killed the
strong critical-mass claim. A hash-verified H89 credit state chose causal
memory for four later controllers, while producer priors chose redundant
memory. The outcome-trained choice completed `3/4` versus `4/4`, won no pairs,
and averaged `-0.2325`.

From the 2036 backcast, the plain-sight mistake moves one level deeper. We
treated “memory delivered to the prompt” as the operative intervention.
Brains have another gate between hippocampal availability and policy control:
prefrontal working-memory admission, basal-ganglia gating, competition with
the current cortical attractor, and observable revision of the action plan.
Our exact observation scope erased this variable because stochastic
controllers at the same frame held different active hypotheses.

The corrected loop is:

```text
controller proposal
-> replay candidate
-> admit / challenge / remain silent
-> proposal revision
-> verified use relation
-> action and outcome
-> credit to the gate under that proposal state
```

This is an orthogonal-axis correction. Content quality and retrieval accuracy
live on one axis; authority over a particular live policy state lives on
another. H88/H89 improved the former. H90 shows that the critical-mass
threshold depends on the latter. Until proposal-conditional gating has
positive held-out loop gain, broad acceleration remains a hypothesis rather
than a measured trend.

## H91 backcast update: judgment needs an internal controllability model

H91 instrumented the missing policy-state edge. Each of eight fresh Sol
`xhigh` controllers first emitted a blind proposal, then received either the
causal H86 bundle or an exact-byte-matched redundant-true placebo and committed
a revised proposal before acting. Both arms paid two proposal calls, 3,849
memory bytes, and 20 primitive actions. Across four alternating-order pairs,
the causal intervention completed Level 1 at actions `13,15,13,15`; placebo
completed at `16,20,20,16`. The causal arm won the frozen composite score in
all four pairs, with mean paired effect `+0.04` and no task-count difference.

This establishes an externally measured proposal-perturbation edge for this
context. It does not validate the frozen lexical account of the edge. The
regex quotient credited only one of four target offers as supported transport
because the blind controllers often assigned the controllable role to the
small floor marker rather than the larger moving object. Several revised
proposals corrected that object assignment while retaining words such as
“marker,” so the text classifier confused preserved vocabulary with preserved
policy state. The provisional first-stage estimate (`0.25`) and its derived
complier effect (`0.16`) are therefore inadmissible for later routing until the
state quotient is repaired.

The 2036 backcast consequently moves from memory valuation to **internal
controllability**. A mature agent should estimate a conditional operator:

```text
(controller state, evidence intervention, cost)
    -> displacement of the planned object/role path
    -> externally settled consequence
```

The brain analogy is narrower than “sleep distillation.” A recalled episode
perturbs a competing cortical plan; local pre/post displacement supplies an
eligibility trace; later consequence supplies the modulatory settlement; sleep
groups response families that share a causal effect. Consolidating the content
alone discards the variable that determines whether recall changes conduct.

The next quotient must make the following square inspectable:

```text
raw observation  -- alpha_world --> content-addressed object/role graph
      |                                      |
blind proposal   -- alpha_judgment --> planned object/role path
```

Both arrows must refer to the same object identities under the same task,
epoch, controller, observation, choice set, and intervention-cost authority.
Memory credit attaches to a change in the planned path and later outcome,
rather than to word overlap. A contradiction or an unbound proposal reference
reopens the quotient instead of being coerced into a feature bucket.

This also locates the candidate contribution relative to the existing
alpha/functor/quotient core. The environment-side abstraction already quotients
raw transitions into behavioral roles. H91 says the same discipline must cross
the controller boundary: `alpha_judgment` quotients proposals into typed paths
over `alpha_world` objects, and a response operator learns which interventions
move those paths profitably. Critical mass would mean this operator improves
the distribution of subsequent experience often enough that better experience
trains a better operator. H91 supplies one positive edge; transfer, silence,
weak-instrument refusal, and later-decision improvement remain open.

## H92 backcast update: identity needs a presentation coordinate

H92 moved the proposal quotient from words to exact object occurrences. The
first two alternating-order pairs behaved as predicted: causal memory moved
both blind plans from the five-cell `0/1` subject to the 25-cell `9/12`
subject with the `0/1` occurrence as the first waypoint, while both placebo
plans stayed in the forbidden subject basin. Target completed at `13,13`;
placebo at `16,miss`.

The third target proposal then copied one 64-hex occurrence ref incorrectly.
The kernel rejected it before the first charged action, satisfying the frozen
kill condition and rejecting H92. This is another 2036-to-2025 category
correction. Cryptographic content address is an evidence identity; it is a
poor controller-facing coordinate. Working cognition recruits locally
addressable assemblies and action channels. It does not reproduce the
assembly's complete physical fingerprint to point at it.

The corrected square therefore has two coordinates:

```text
raw observation -> exact object identities -> local catalog presentation
                                             |
controller proposal ----------------------> short scoped handles
                                             |
alpha_judgment resolves handles ----------> exact object/role path
```

The short handle carries no role meaning and no transport authority. Its
catalog-presentation digest binds it to one observation; the adapter resolves
it to the exact content address before the common kernel sees the proposal.
This mirrors the existing fiber-planning split between partition identity and
presentation assignment. H92's miss came from carrying identity across the
controller boundary without carrying its presentation functor.

## H93 backcast update: the eligibility trace now commutes

H93 tested the presentation repair on two new alternating-order pairs. The
actor saw role-free handles plus geometry; exact content hashes stayed behind
the adapter. Every raw blind/revised proposal was persisted before resolution.
Both target controllers revised `o02 -> o03`; both placebo controllers stayed
`o02 -> o02`. After handle resolution, the unchanged exact-ref kernel measured
target supported transport `2/2`, placebo spontaneous transport `0/2`, and
first stage `1.0`.

The external settlement agreed: target completed at `13,15`; placebo at
`miss,16`; target task delta was `+1` and mean paired composite delta
`+0.445`. The controller-facing pointer therefore repaired H92 without
weakening identity authority or creating a semantic hint.

This gives the backcast its first inspectable internal eligibility trace:

```text
blind proposal basin
-> randomized evidence perturbation
-> exact planned-path displacement
-> externally settled consequence
```

The brain analogy now earns a specific algorithmic consequence. Local
addressability lets a fast controller recruit a slow trace; exact binding lets
delayed outcome modulate the responsible transition rather than the mere
presence of memory. Sleep can group these settled response signatures into
conditional families. The next threshold is not more forced recall. It is
whether a response family can inspect a new blind path, offer memory only when
that path belongs to a benefited basin, remain silent otherwise, and improve
net outcome after the attention/intervention cost. That is the first test that
can close the loop from experience to later judgment.

## H94 backcast update: a local trace changed a later choice

H94 supplied the missing prospective edge. H93's randomized evidence compiled
into one response family over the exact wrong-control blind basin: offer and
withhold counts `2/2`, typed-path first stage `1.0`, and cost-adjusted effect
`+0.445`. On two new controllers, the family saw only the typed blind plan and
selected causal mechanics before either outcome existed. H90's scalar outcome
state, trained on twice as many prior settlements but lacking proposal-state
conditioning, selected redundant true memory twice. Response controllers
completed at actions `13,13`; scalar controllers at `14,15`; mean composite
gain was `+0.015`.

The 2036-to-2025 correction is sharper now. The unit of learned judgment is not
a memory, retrieval score, or global value. It is a locally settled response
operator:

```text
(proposal basin, evidence intervention, cost)
    -> typed policy displacement
    -> externally settled value
    -> offer | silence | explore on a later proposal
```

This resembles corticostriatal gating more closely than a searchable notebook:
the slow trace changes a later fast choice only in the state where the earlier
perturbation was both taken up and useful. H94 supports that one local loop. It
does not yet supply the mechanism that would create critical mass.

From the 2036 view, accumulation requires **certified reactivation across
fibers**. Brains do not address every episode by a global content hash; partial
cues reactivate local assemblies, while downstream circuitry tests whether the
reactivated transition still predicts consequence. ZTARE's corresponding
mechanism should be a commuting response-transport square:

```text
proposal basin in observation A --intervention--> revised basin in A
              |                                  |
     certified object transport         certified response transport
              |                                  |
proposal basin in observation B --intervention--> revised basin in B
```

Only a square whose transported displacement and external consequence agree
may move credit. A noncommuting square creates a new family or triggers
exploration. This is stricter than embedding similarity and more useful than
exact-context refusal: it specifies how local judgment can compose without
turning into indiscriminate analogy.

The next discriminator is therefore not another same-basin replication. It is
a new observation fiber or proposal basin with two possible outcomes:

1. a certified transport square makes the H94 response applicable and improves
   a later nonterminal decision; or
2. transport fails, and the circuit remains silent or explores without paying
   the full intervention cost.

Chained settlement across two such decisions is the minimum evidence for the
backcast's critical-mass hypothesis.

## H95 backcast update: one local assembly reactivated lawfully

H95 instantiated the square rather than treating it as an analogy. H94's
source response crossed to the observation after prefix `[2]` only through:

1. a unique content-type map for every contract and response-witness object;
2. a payload-specific intervention morphism preserving acquisition
   provenance, provider, calibration, authority, and cost while re-rendering
   the exact revision in the new context;
3. a blind/revised proposal square whose contract-relative signatures
   commute; and
4. fresh target-fiber settlement before target credit is promoted.

The causal and placebo payloads required different intervention certificates.
Across two balanced pairs, the transported causal response was taken up `2/2`,
placebo spontaneous uptake was `0/2`, task delta was `+1.0`, and mean paired
composite gain was `+0.48`. A nearby prefix in which the required marker
occurrence disappeared was refused without controller contact.

The brain analogy becomes algorithmic here. Partial cue reactivation is not a
nearest-neighbour lookup: it is a provisional recruitment of a prior response
assembly under a set of commuting constraints, followed by local settlement.
The result supplies one reactivation edge. Critical mass still requires many
such edges to compose without accumulating false-transfer cost.

The 2036 correction now points to **path defect**. If two histories reach an
apparently equivalent endpoint, a scalar memory system merges them. A
compositional judgment system asks whether the two transport chains induce the
same response. Their disagreement is a loop defect:

```text
defect(path_A, path_B)
    = disagreement(
          transported contract,
          blind-basin signature,
          revised displacement,
          predicted consequence,
          external settlement calibration)
```

This defect must affect admission before delivery. Zero defect permits
composition; positive defect lowers confidence, triggers exploration, or
splits the response family. H96 should seek matched endpoints or matched
quotient states reached through different prefixes and test whether
branch-resolved defect predicts false reuse better than endpoint identity
alone.

## H96--H101 backcast update: from memory to epistemic metabolism

H96 supplied a useful rejection. Appearance lineage preserved all four object
occurrences and the causal controller gained a level, yet the transported
response contract still asked for a marker that the prefix had already
consumed. The placebo proposal also occupied another basin. Object continuity
therefore cannot carry a temporal program across a completed subgoal. H97
compiled the missing Brzozowski-style response derivative and an exact stored
Responses API parent fork. Two live calls ended at exhausted API credit before
model, controller, environment, or action contact, leaving the causal question
open.

H98 and H99 then inverted the one-child ceiling. A settled response may emit
many residual questions; positive-scalar copies are quotiented; exact response
rank determines the independent children; randomized settlement determines
which children earn causal ancestry. A two-generation synthetic chain grew
`1 -> 2 -> 3`, with geometric knowledge factor `sqrt(3)` and zero false-edge
growth. That result exposed another hidden category boundary: the offspring is
an independently settled question-answering direction, rather than a stored
memory, tool, file, or proposal count.

H100 found that the proposed reproduction law carried an exponential assay
cost. Complete factorial settlement requires `2^r` trajectories for rank
`r`; growth would become less measurable as it became more interesting. A
pre-outcome Walsh code reduced the additive rank-twelve assay to sixteen
trajectories from `4096`, while retaining exact rank and explicit named
interaction authority. This is the sparse-attention analogy in executable
form: allocate observation channels to an identifiable causal basis instead
of broadcasting every combination.

H101 then replaces scalar loop gain with an epistemic metabolism. Different
capabilities are species; evidence-backed improvements are catalytic
reactions; model competence and external observations are the food set;
primitive actions are the resource budget; false transfers are error species.
A candidate turning point requires a food-generated, reflexively catalyzed,
stoichiometrically productive, error-bounded flux under one budget. On the
synthetic H99/H100 topology, sparse assay cost `80` admits such a flux under
budget `100`; factorial cost `160` blocks it while topology and food closure
stay fixed. Cycles without food, missing catalysts, bootstrap-only production,
error amplification, and authority changes all fail.

H102 adds kinetics and depreciation. The same H101 RAF can decay at low
capability stock and amplify at higher stock because reproduction consumes two
judgment units and needs the design catalyst. Exact mass-action evaluation
gives judgment drift `-15/64` at `J=3/2, D=9/4` and `+133/512` at
`J=7/4, D=21/8`, bracketing the surface `3 J^2 = 8`. Sparse settlement keeps
the upper-state cost rate below budget; factorial settlement blocks that same
reaction-rate vector. Topological closure therefore becomes one gate inside a
state-dependent developmental threshold.

From the 2036 vantage, this suggests a further category transition:

| 2025 object | 2036 backcast object |
|---|---|
| Model capability | A typed ecology of capabilities with joint-input dependencies |
| Memory accumulation | Production of independently settled residual directions |
| Retrieval bandwidth | An experimental-design budget over identifiable causal effects |
| Recursive improvement count | A food-generated catalytic flux with explicit error metabolism |
| Critical mass | Capability stock and catalytic throughput outrun depreciation and assay cost |
| Self-improvement demo | A prospectively discovered reaction that helps discover and test its descendants |

The brain analogy is now narrower and more demanding. Wake experience supplies
food and local prediction errors. Replay performs counterfactual fission.
Sparse settlement plays the role of selective reactivation. Consolidation
promotes only lineages whose intervention effects survive external outcome.
Executive control allocates the resulting catalysts. Homeostatic processes
remove false-edge production and unaffordable reactions. A summary or skill
file can participate in this cycle, but its existence does not make the cycle
autocatalytic.

The remaining plain-sight variable is **reaction discovery**. H101's positive
reactions were authored after observing H99/H100. A capable 2036 system should
infer the missing catalyst from a failed reproduction attempt, design the
sparse assay, and prospectively produce settled descendants that become inputs
to the next generation. The minimum next experiment is therefore a matched
exact-state fork in which the causal arm receives the compiled residual and
the placebo arm does not. The causal arm must discover a non-authored
measurement reaction, reduce primitive-contact cost, and produce a held-out
child lineage. H97 is the first unresolved edge of that experiment.

The historical invariant now has a fourth term:

```text
2005: learn the representation
2015: learn the task interface
2025: learn which memory may perturb policy
2036: learn the capability reactions that reproduce better experimenters
```

H101 makes the last line falsifiable as a network-and-flux criterion; H102 adds
the stock-and-rate threshold. Neither supplies prospectively measured reaction
kinetics.

## Novelty correction

The selected direction is convergent with published 2026 agent-memory work.
ProactAgent already makes retrieval an explicit action and supplies step-level
credit by replaying a shared interaction prefix into retrieval and
no-retrieval continuations, scoring both task outcome and efficiency. Its
experience base is typed, and priority updates are restricted to retrieved
entries associated with improved outcomes. AdaMEM already diagnoses
episode-initial memory as too static and introduces step-wise adaptive memory.
UMA already learns proactive consolidation and explicit memory-bank
operations.

The July literature adds an even closer kill. Remember When It Matters
(arXiv:2607.08716) already frames memory as an active intervention, places a
separate memory agent beside an unchanged action agent, and learns whether to
inject or remain silent; its reported ablations favor selective intervention
over always-on recall. Decision-Aware Memory Cards (arXiv:2606.08151) already
ranks evidence by action shift, outcome uplift, necessity, and negative
transfer. RICE-PO (arXiv:2605.26352) already localizes credit at uncertain
executable retrieval anchors. H87's positive always-inject result is therefore
a prerequisite control, not the novel judgment mechanism.

The multi-decade exercise still selected the correct missing capability for
ZTARE, but it did not invent the category. The research-isomorphism result
`Counterfactual Replay Exchange` independently recovered a close structural
shape; the failure was not running a nearest-prior-art inversion immediately
after that conjecture. The defensible ZTARE research surface is narrower:
receipt-bound acquisition and consumption identities, an explicit
exchangeability certificate, guard-overlap interference, fixed primitive
action cost, and contradiction-driven boundary reopening. Those differences
need head-to-head evidence before any novelty claim.

Conjecture mode now requires a `prior_art_inversion` search plan with explicit
queries, comparison axes, and a kill condition. The plan does not establish
novelty; it blocks novelty language until an executed, source-bound comparison
receipt exists. Focused verification: 30 tests plus the research-isomorphism
self-test pass.

## Source anchors

- McClelland, McNaughton, and O'Reilly, complementary learning systems:
  https://doi.org/10.1037/0033-295X.102.3.419
- Káli and Dayan, offline replay and hippocampal–neocortical interaction:
  https://www.nature.com/articles/nn1202
- Diekelmann and Born, sleep, replay, transformation, and downscaling:
  https://www.nature.com/articles/nrn2762
- Schapiro et al., human replay prioritizes weakly learned information:
  https://www.nature.com/articles/s41467-018-06213-1
- Huelin Gorriz et al., experience prioritizes replay:
  https://www.nature.com/articles/s41467-023-43939-z
- Mattar and Daw, prioritized memory access by expected decision gain:
  https://pubmed.ncbi.nlm.nih.gov/30349103/
- Gillespie et al., post-learning replay biased by reward-prediction error:
  https://www.nature.com/articles/s41467-025-65354-2
- LeCun, Bengio, and Hinton, deep learning:
  https://www.science.org/doi/10.1126/science.aaa8415
- Vaswani et al., Transformer:
  https://arxiv.org/abs/1706.03762
- Kaplan et al., neural scaling laws:
  https://arxiv.org/abs/2001.08361
- Roy et al., content-based sparse routing:
  https://arxiv.org/abs/2003.05997
- Behrouz et al., test-time neural memory:
  https://arxiv.org/abs/2501.00663
- Cai et al., proactive retrieval with paired-prefix retrieval/no-retrieval
  continuations:
  https://arxiv.org/abs/2604.20572
- Zhang et al., step-wise test-time adaptive agent memory:
  https://arxiv.org/abs/2606.05684
- Zhang et al., end-to-end learned consolidation and memory operations:
  https://arxiv.org/abs/2602.18493
- Guan et al., decision-aware memory cards:
  https://arxiv.org/abs/2606.08151
- Li et al., localized counterfactual retrieval credit:
  https://arxiv.org/abs/2605.26352
- Wu et al., selective proactive memory intervention:
  https://arxiv.org/abs/2607.08716
- OpenAI model guide, persisted reasoning context:
  https://developers.openai.com/api/docs/guides/latest-model
