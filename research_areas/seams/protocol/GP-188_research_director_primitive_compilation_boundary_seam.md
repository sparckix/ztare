# GP-188 — Research Director Primitive-Compilation Boundary

> **Seam metadata** · `seam_id:` GP-188 · `track:` protocol · `status:` open · `last_updated:` 2026-05-16


**Status:** open  
**Created:** 2026-04-29 22:09:00  
**Owner:** principal + research_director role  
**Related:** `org/mandates/research_director_mandate.md`, `seams/protocol/GP-172_research_director_mform_role_seam.md`, NS Phase 3→5h workstream

---

## Compression

The Research Director should not "do science by hand" when the move can be
stated as a stable primitive. The right split is:

- **Director = chooser / sequencer / compressor of primitives**
- **ZTARE/apparatus = executor of already-formalized primitives**

The boundary is **not** human vs AI, nor domain-expert vs alien-thinker.
The real boundary is:

- **formalized enough to compile into a reliable contract**
- vs
- **still underdescribed enough that compiling it would launder ambiguity**

The deeper operating loop is now explicit:

```text
operator <-> agent interaction exposes the useful move
-> organizational memory records, criticizes, and compares it
-> ZTARE mechanizes the stable subroutine once it repeats or prevents a real
   error/cost
```

This is organizational learning, not immediate automation. A move can be
brilliant in chat and still be too underdescribed to compile. Conversely, once
the same move recurs with the same inputs, artifacts, and abort conditions, it
should stop living only in the operator's head.

This seam exists because the NS Phase 3→5h sequence exposed both:

1. repeated expensive manual direction that clearly wants to become reusable
   apparatus, and
2. still-live judgment calls that should remain at Director level until their
   causal split is specified.

---

## Trigger Evidence From NS

The last two days produced the following pattern:

1. **Eigenquestion selection was decisive.**
   The useful moves came from repeatedly compressing the object:
   `wide ansatz search -> twin-peak symmetry risk -> poison test -> lifeline tracker`.

2. **Telemetry contract bugs, not PDE results, repeatedly dominated cost.**
   `0.99` vs `0.990`, final-snapshot vs peak-time ambiguity, missing raw
   checkpointing, and under-instrumented late-window component traces caused
   multiple wasted GPU cycles.

3. **De-anchored mechanism generation was useful despite weak domain expertise.**
   The useful pivots did not come from classical NS expertise alone. They came
   from meta-cognitive reframing plus hostile falsification.

4. **The Director's real value was not producing prose.**
   It was choosing the next clean discriminator and forcing the instrument to
   record the right object.

These are not one-off NS quirks; they are generic frontier-program signals.

---

## Candidate Primitive Classes

### Class A — should live inside ZTARE / apparatus now

These are already specified enough.

1. **Stable threshold-key normalization**
   - Numeric threshold lookup helpers
   - No direct string indexing in frontier telemetry paths

2. **Raw-before-derived checkpoint contracts**
   - Expensive telemetry written first in minimally processed form
   - Derived summaries computed afterward
   - If summary fails, raw payload survives

3. **Frontier run manifests**
   - run id
   - eigenquestion
   - discriminating criterion
   - telemetry contract
   - stop rule

4. **Remote run wrappers**
   - upload
   - launch
   - status watch
   - local ntfy fallback
   - artifact retrieval

5. **Offline extractor harness**
   - given saved artifact bundle, run standard extractors locally first
   - fail closed on missing fields
   - classify `instrument_failure` vs `scientific_failure`

6. **Phase-driver checkpoint templates**
   - final snapshot
   - peak-time snapshot
   - late-window component timeseries
   - spectra
   - localization

### Class B — should live as Director+ZTARE compositions next

These are mechanizable as orchestrated recipes, but not pure inner-loop
apparatus yet.

1. **Eigenquestion selector**
   Input: current result state  
   Output: smallest causal split + cheapest discriminator

2. **Rival-mechanism generator**
   Input: result packet  
   Output: 3-5 live alternative explanations with kill conditions

3. **Admissibility scheduler**
   Input: live interpretations + cost  
   Output: offline extraction vs new GPU vs abandon branch

4. **Frontier telemetry planner**
   Input: proposed next falsifier  
   Output: minimum telemetry needed so the result is interpretable

5. **Mechanism compression**
   Input: messy numerical survivor  
   Output: theorem-shaped mechanism question or downgrade

### Class C — should remain outside full mechanization for now

Not because they are human-only, but because they are not specified enough yet.

1. Final external-claim language on theorem-adjacent objects
2. When a numerical mechanism is mature enough for proof-routing / Lean
3. Choosing among several underdetermined "alien" stories when the
   discriminators are still not formalized

---

## Proposed Primitive Queue

Ordered by expected information yield per engineering effort.

1. **Frontier telemetry contract primitive**
   - standard schema for raw + derived checkpointing
   - owner: apparatus/instrumentation
   - value: removes repeated wasted GPU spends

2. **Frontier experiment manifest**
   - small YAML/JSON contract for active expensive runs
   - includes eigenquestion, stop rule, and required telemetry
   - owner: protocol + supervisor

3. **Result-state compressor**
   - codify `scientific result` / `instrument failure` / `mixed` verdicts
   - owner: Director role-extension

4. **Eigenquestion provider**
   - Director-level primitive producing a structured next-test object
   - owner: research_director role-extension

5. **Rival mechanism dossier**
   - like skeptic dossier, but for active frontier mechanistic interpretation
   - owner: research_director role-extension

6. **Research-taste opportunity card**
   - explicit vector of principal preferences for attention routing
   - axes: unresolved-problem resolution, prize/money leverage, architecture
     fit, self-recursive governance value
   - owner: org/preferences + research_director role-extension
   - non-goal: does not promote truth, findings, or public claims

7. **Meta-cold-shot script scaffold**
   - chooses script family/template before proposing code
   - writes scaffold artifact, not executable changes
   - owner: apparatus/orchestrator

8. **Frontier pull-forward primitive**
   - input: closed experiment packet, external review, or subagent result with
     explicitly named next artifacts
   - output: bounded next-task queue with `now / parallel / defer / reject`
     classification, write-scope ownership, and prediction-ledger trigger check
   - owner: research_director role-extension + supervisor task claiming
   - value: prevents high-confidence downstream work from staying in chat while
     also preventing generic "do everything in parallel" thrash
   - non-goal: not a replacement for PATTERN-011 swarm dispatch; it decides
     which already-revealed frontier items should be pulled into the current
     critical path
   - candidate mandate rule: for any RD task with independent lanes or a
     downstream artifact that can unblock the next lane, either dispatch/pull
     forward or state why the dependency is serial, too small, or write-conflict
     prone

---

## Pros / Cons of Moving More Inside ZTARE

### Pros

1. Lower operator attention cost
2. Better reproducibility
3. Fewer repeated telemetry bugs
4. Cleaner experiment closure
5. Less loss of good de-anchored ideas to chat history

### Cons

1. Risk of overfitting apparatus to one domain's artifacts
2. Risk of mistaking smooth automation for stronger science
3. Risk of converting underdetermined interpretation into fake determinism
4. Risk of prematurely freezing the Director's "alien" move into the wrong
   primitive

---

## Current Recommendation

Do **not** attempt to push the whole Research Director inside ZTARE.

Do:

1. keep the Director as the exogenous chooser of what still needs judgment
2. aggressively compile repeated frontier moves into primitives
3. treat every expensive manual loop as a candidate for:
   - `inside apparatus now`
   - `Director+ZTARE composition`
   - `not specified enough yet`

In short:

**The Director should increasingly operate by composing mechanized primitives, not by re-performing them manually.**

That is the architecture this seam is opening.

---

## Immediate Next Actions

1. Create a minimal frontier-manifest primitive spec
2. Create a raw-before-derived checkpoint primitive spec
3. Extend the Research Director role-extension with:
   - eigenquestion object
   - rival-mechanism dossier
   - instrument-failure vs science-failure classifier
4. Wire research-taste opportunity cards to queue ranking without touching
   promotion readiness or judge scores
5. Use the meta-cold-shot scaffold for the next repeated frontier `.py`
   generation event before writing bespoke code

---

## Open Question

Should the "frontier numerics" path remain a Research Director addendum, or
should it become a separate role (`frontier_science_director`) once the
primitive library is large enough?

---

## Kernel-Wide Update — 2026-05-11

The NS/L3A session exposed a boundary error that this seam should settle
kernel-wide.

The split is not:

- inside `autoresearch_loop.py` vs outside ZTARE.

The split is:

- **Full loop:** the high-friction workstation test bench for
  pre-registered mutator/judge experiments with budgets, telemetry,
  adversarial pressure, closure, and E/F-row obligations.
- **Extracted primitives:** ZTARE as the workstation assistant for interactive
  Director/Codex work when a full loop is unnecessary or too slow.

This is the intended "strange loop" handle: the system created reusable
capabilities, and the manager agent should use those capabilities locally
instead of redoing the cognition by hand or rebuilding a second loop.
The extracted primitives are not a replacement for `autoresearch_loop`; they
are the low-latency front bench that prepares candidates for the full loop
when the candidate has become testable enough to deserve a budgeted run.

Current extracted primitive families include:

- primitive discoverability: `primitive_tick_surface`
- graph/workmap refresh: `NS-GRAPH-TICK-PRECHECK`,
  `NS-L3A-CONCENTRATION-WORKMAP`
- motion and diversity scoring: Jaccard/set-distance primitives and related
  motion diagnostics
- route/model-selection heuristics: BIC-shaped coverage/complexity scoring
- proof workbench gates: Lean proof gates, PDE dimensional gates, CAS checks
- proof-target packaging: typed-endpoint queues, prompt/eigenquestion packets,
  source-witness checks
- method vocabulary: PDE estimate-craft ops and orchestration pattern menu

Operational rule:

1. For substantial interactive work, query the extracted primitive surface
   first.
2. Use existing primitives as workstation tools before adding new apparatus.
3. Add only thin adapters when a primitive output is not consumable by the
   current task.
4. Promote into a full autoresearch loop when the work becomes a real
   budgeted experiment with a pre-registered discriminator, adversarial judge
   value, and closure telemetry.
5. Feed durable outputs back into ZTARE memory: compiler-checked theorems,
   concrete falsifiers, typed missing primitives, graph/workmap outputs,
   failure categories, and E/F/INS rows when closure criteria are met.

Heavy workbench promotion gate:

Promotion means "loop-ready package," not launch authorization. Approved
execution should default to `make experiment-loop`; direct `make loop` is a
lower-level escape hatch and needs an explicit reason. `make experiment-loop`
is the safety wrapper for pre-registered experiments; raw `make loop` is the
underlying runner for cases where the principal explicitly wants direct flag
control.

Before promotion, RD/Codex must write a primitive-insufficiency receipt:

- primitive surface queried;
- primitives or bounded local checks run;
- result of each check;
- exact unresolved question;
- reason mutator/judge iteration can answer what local checks cannot.

Use the heavy workbench only when all eight conditions hold. Even when all
eight hold, launch still requires explicit principal approval while LLM spend is
not fully automated against a budget cap. A generated charter, rubric,
eigenquestion, or candidate packet is preparation, not authorization.

0. **Primitive bench exhausted:** no available Lean/CAS/dimensional/source/
   graph/workmap/local cold-shot primitive, or bounded composition of them, can
   decide the next build or belief update.
1. **Pre-registered discriminator:** there is a concrete pass/fail question
   whose answer changes the next build or belief state.
2. **Adversarial iteration has marginal value:** the uncertainty is not merely
   Lean syntax, CAS simplification, dimensional bookkeeping, source lookup, or
   local endpoint packaging.
3. **Stable substrate packet:** the charter, evidence, rubric, and thesis can
   hold still for the run; the target will not change every iteration.
4. **Telemetry is worth paying for:** iteration logs, cold shots, frame/reframe,
   inverter/topological-pivot moves, champion promotion, and closure records are
   expected to teach more than a local primitive tick.
5. **Spend is justified by expected information yield:** the run has a named
   failure mode, a kill condition, a primitive-insufficiency receipt, and a
   reason the loop could expose something local checks would miss.
6. **Independent falsification axis:** the pass/fail criterion is anchored to
   an observable not produced by the candidate itself or by the judge rubric
   alone. Before launch, record one negative/control case, held-out check,
   compiler/CAS/source-witness obligation, or cross-surface transfer test that
   would fail if the run merely rephrases the prompt, optimizes judge taste, or
   back-solves the target.
7. **Telemetry/rotation is indispensable:** the decision would be
   uninterpretable without iteration history, prompt/eigenquestion rotation
   receipts, judge/mutator pressure, champion/revert trail, and closure rows. A
   generated charter, rubric, eigenquestion, prompt packet, or rotation plan is
   extracted-primitive output; it becomes loop input only after principal
   acceptance and only if it can remain fixed for the run.

If any condition fails, stay on the extracted primitive bench: graph/workmap
tick, Lean gate, CAS/dimensional check, source-witness check,
`make eigenquestion-propose`, pattern-chain audit, primitive-surface precheck,
or a local cold-shot prompt packet. Record durable outputs as theorem/proof
artifacts, workmap deltas, typed missing primitives, seam notes, or E/F/INS rows
only when closure criteria are actually met.

Two promotion examples:

- **Do promote:** a theorem target has narrowed to two rival mechanisms and an
  adversarial mutator/judge run can distinguish bridge, obstruction, or route
  reranking with durable telemetry.
- **Do not promote:** the next move is adding Lean declarations, checking a
  finite algebraic adapter, refreshing graph rankings, or removing a known
  tautology from a prompt.

Discriminating invariants:

These invariants decide whether the next move belongs on the extracted
primitive bench or the heavy workbench.

| Invariant | Extracted primitives | `make experiment-loop` / `make loop` |
|---|---|---|
| **State stability** | Target still moving; theorem surface, prompt, or guard fields are being shaped | Charter/evidence/rubric can hold fixed for the run |
| **Signal type** | Compiler, CAS, dimensional, graph-ranking, source-witness, or single-shot prompt signal | Iterated mutator/judge pressure is the signal |
| **Failure value** | Failure should immediately edit a local theorem, prompt, graph edge, or seam | Failure categories need telemetry, champion history, and closure rows |
| **Adversarial value** | A local guard can expose the tautology or syntax error cheaper | A judge/mutator loop can discover frame changes or hidden route classes |
| **Primitive sufficiency** | A bounded primitive composition can decide the next state update | The remaining uncertainty survives primitive precheck and requires iterated pressure |
| **Anti-tautology axis** | No independent falsifier is named; local primitive work continues | A negative/control, held-out, compiler/CAS/source-witness, or cross-surface transfer check blocks score-chasing |
| **Cost of drift** | Low; edits are reversible and cheap | High; target drift during run would invalidate spend |
| **Authorization state** | No dated principal approval artifact exists; keep packet non-runnable | Approval names substrate, command, tier, caps, window, and closure owner |
| **Rotation fixity** | Prompt/eigenquestion still being generated, compared, or operator-reviewed | Accepted eigenquestion/rotation schedule is fixed before iter 1 |
| **Command surface** | `make eigenquestion-propose`, primitive-surface precheck, graph/workmap/Lean/CAS/source gates | Prefer `make experiment-loop`; use raw `make loop` only by explicit principal choice |
| **Promotion artifact** | Lean declaration, workmap update, eigenquestion draft, countermodel, source packet | Closed experiment with E/F-row, telemetry, champion/revert trail |
| **Best use case** | Theorem construction and preflight compression | Discriminating experiments on stable candidates |

Default decision rule:

- If the uncertainty is **what theorem/prompt/guard to ask**, stay local.
- If the uncertainty is **how a stable candidate behaves under adversarial
  iteration**, use the heavy workbench.
- If the answer would be invalid without telemetry or iteration history, use
  the heavy workbench.
- If a single Lean/CAS/source/graph check can answer it, stay local.

This keeps the full loop valuable rather than vestigial: it is the expensive
integration arbiter for stable candidates, while the extracted primitives are
the fast instrument panel that prepares candidates for that arbiter.

Expense-control rule:

- RD/Codex may draft local eigenquestions, theorem packets, and review prompts.
- RD/Codex must not launch `make experiment-loop` or `make loop` without the
  principal's explicit approval for that specific run.
- RD/Codex must not create launch-ready rubrics for frontier proof work unless
  the principal has asked for a loop-ready package. If a packet is useful for
  thinking, keep it as notes or a seam review artifact, not a runnable substrate.

Launch authorization invariant:

- No RD/Codex session may create or execute a spend-bearing substrate unless a
  principal approval artifact exists for that specific run.
- The approval artifact must name: substrate slug/path, exact command or command
  template, model tier(s), iteration cap, budget cap, allowed launch window, and
  closure owner.
- Chat discussion, generated charters, rubrics, eigenquestions, candidate
  packets, or "ready if approved" language are not authorization.

Runnable-substrate quarantine:

- Exploratory packets for frontier proof work must be explicitly non-runnable:
  `launch_ready: false`, no sealed command, and no complete active rubric
  consumed by `autoresearch_loop.py`.
- If a packet is useful for thinking, store it as notes or a seam-review
  artifact, not under active substrate paths used by the loop.
- Promotion from packet to runnable substrate requires the launch authorization
  artifact above plus a local-preflight record showing which extracted
  primitives were tried and why they were insufficient.

Local-preflight invariant:

- Heavy workbench promotion requires a short preflight record listing the
  cheapest applicable primitive checks already run: graph/workmap tick,
  Lean/CAS/dimensional/source-witness checks, and prompt/eigenquestion audit as
  relevant.
- If one of those checks can answer the question, the full loop is forbidden for
  that move.

Seam debate outcome:

- Position A: full `autoresearch_loop` should remain the integration arbiter
  because it is the only path with mutator/judge pressure, telemetry, champion
  promotion, and closure discipline.
- Position B: interactive theorem work should default to extracted primitives
  because most moves are still target-shaping, syntax checking, endpoint
  packaging, or local falsification; heavy-loop use too early turns proof search
  into prompt-score optimization.
- Resolution: two-bench protocol. Extracted primitives are the default front
  bench. The heavy workbench is promoted only when the candidate is stable,
  discriminating, and worth adversarial iteration.

## Epistemic Review Panel — 2026-05-11

**Status:** panel-mediated seam review, not external authority.

All four requested reviewer roles completed:

- fictitious Research Director reviewer;
- epistemic-methodology reviewer;
- operations/cost-control reviewer;
- autoresearch-loop architect reviewer.

### Consolidated Verdict

`REVISE`, with convergence on four missing controls:

1. primitive-exhaustion / local answerability;
2. independent anti-tautology axis;
3. explicit launch authorization and runnable-substrate quarantine;
4. command-surface semantics and rotation fixity.

### Reviewer Findings

**Fictitious Research Director reviewer:** GP-188 was directionally right, but
too easy for an RD/Codex agent to satisfy narratively. The seam needed a
primitive-insufficiency receipt and should clarify that approved execution
defaults to `make experiment-loop`; direct `make loop` is a lower-level escape
hatch requiring explicit reason.

**Epistemic-methodology reviewer:** the promotion gate lacked an independent
falsification axis. A stable, pre-registered, well-telemetered loop can still be
a tautology or benchmark chase unless the pass/fail signal is anchored outside
the candidate/rubric surface.

**Operations/cost-control reviewer:** the cost boundary needed a checkable
authorization object. Chat discussion and generated packets are not launch
authorization; spend-bearing substrates require a dated principal approval
artifact naming command, model tiers, caps, launch window, and closure owner.

**Autoresearch-loop architect reviewer:** `make experiment-loop` should be the
default launch wrapper for approved experiments; raw `make loop` is direct flag
control and should require explicit principal choice. Prompt/eigenquestion
rotation is extracted-primitive output until the principal accepts it as fixed
run input.

### Patch Applied

This seam now requires:

- primitive-insufficiency receipt before promotion;
- eight heavy-workbench gate conditions, including primitive exhaustion and an
  independent falsification axis;
- discriminating invariants for primitive sufficiency, anti-tautology, and
  authorization state;
- default execution through `make experiment-loop`, with direct `make loop`
  requiring explicit reason;
- launch authorization invariant;
- runnable-substrate quarantine;
- local-preflight invariant.
- telemetry/rotation indispensability;
- command-surface semantics.

Urgent follow-up:

- Add or verify a one-command "workstation precheck" that prints the relevant
  primitive surface, graph/workmap status, and available proof gates for the
  active substrate.
- Make Codex/RD sessions treat this precheck as the default first move for
  frontier proof work, unless the task is a tiny direct edit.

This update does not move theorem construction into `autoresearch_loop.py`.
It clarifies that ZTARE is also a locally callable assistant layer through its
compiled primitives.

## Implementation Status — 2026-05-11

The panel's urgent precheck requirement is now mapped to existing local commands,
not a new loop.

Default one-command workstation precheck:

```bash
./venv/bin/python scripts/public/control/rd_tick_brief.py --short --blocking-substrate ns
```

This path already prints the RD primitive discoverability surface and invokes
registered substrate graph prechecks. For a lighter primitive-only pass:

```bash
./venv/bin/python scripts/public/control/primitive_tick_surface.py --scope ns
```

For the current NS/L3A track, the bounded local primitive sequence is:

```bash
./venv/bin/python scripts/public/control/primitive_tick_surface.py --scope ns
./venv/bin/python scripts/public/projects/ns/ns_l3a_workmap.py --top 12
./venv/bin/python scripts/public/projects/ns/ns_graph.py jsonl --sink sharpTarget --top 32 --strip-plumbing
```

These commands are extracted-primitive workbench calls. They do not create a
runnable substrate and do not authorize `make experiment-loop`.

2026-05-11 GNN-lane addendum:

The GNN/router work exposed a concrete GP-188 failure mode: relying only on
the high-level primitive surface missed an already shipped Jaccard primitive at
`src.ztare.motion.set_distance.jaccard_distance`. The correction is now part
of the local-preflight invariant for algorithmic work:

1. query the primitive surface;
2. run direct source inventory with `rg` for the relevant operation family
   (`jaccard`, `distance`, `motion`, `vocabulary`, `graph`, `ppr`, `pagerank`,
   `bic`, `budget`, etc.);
3. reuse the existing primitive when available;
4. if adding a new adapter, state why the existing primitive was insufficient.

For the current GNN lane, v10.0 now imports the existing Jaccard primitive
rather than maintaining a duplicate implementation. The result is also a
negative design signal: Jaccard is useful for typed role-neighborhood
ablation, but non-name neighborhoods and row-obligation seeded matching remain
weak. That means the next build target is non-bootstrap obligation-role
extraction, not another generic graph metric.

Remaining implementation backlog:

1. Add a tiny local-preflight receipt writer if repeated manual receipts become
   noisy. Until then, the receipt can live in the active seam or research note.
2. Run the no-spend value validation in
   `GP-188_ztare_workstation_value_thesis_2026_05_11.md`: compare RD-only,
   RD plus extracted primitives, and approved full-loop use on matched
   frontier microtasks before broadening the workbench boundary.
3. Add a machine-checkable launch-authorization artifact schema only when the
   principal next approves a real loop-ready run.
4. Add a quarantine lint if agents start creating runnable frontier rubrics
   without approval. Current rule remains procedural: no active rubric or sealed
   command for frontier proof work unless approval exists.
5. Close pattern-deployment rows after panel-mediated audits when their outcome
   changes routing. The current GP-188 panel outcome is `REVISE -> patched
   two-bench protocol`.

Panel decision retained:

- extracted primitives are the default front bench for interactive theorem and
  prompt work;
- the full autoresearch loop remains valuable as the expensive integration
  arbiter only after primitive insufficiency, a stable substrate, independent
  falsification, telemetry need, and explicit principal approval are present.

## Primitive-Surfacing Boundary Decision — 2026-05-16

**Trigger.** Out-of-loop RD ticks failed to use correctly-registered
primitives (evidenced: `LAGRANGIAN-DERIVATION` never surfaced for an
action-principle tick). RCA (three layers): (1) `primitive_tick_surface._score`
ranks by lexical *substring* token-overlap → vocabulary-drift-fragile
(PATTERN-024 amnesia-precheck class); (2) `10*impact` makes
`impact_factor_expost` a HARD VISIBILITY GATE (menu confidence:candidate
catch-22 transported to the arch index); (3) meta: a hand-rolled
bag-of-tokens score was used while learned-relevance/rerank infra already
exists in-repo (`gnn_lemma_relevance_v21_rerank`, `substrate_recommender`,
`universal_classifier`). Three in-pressure hot-hacks (vocab tokens →
scorer reweight → BM25 imports) all regressed and were reverted to
pristine; `primitive_tick_surface.py` is byte-equivalent to original.

**Design Q1 (BM25 prior + agentic-forced) + Q2 (π-group primitive)**
submitted for independent adversarial review.

**Adversarial review verdict: FLAWED** (Claude reviewer; codex CLI
co-reviewer was a 0-char stdin-hang non-result, not folded). Decisive
must-fix (MF1): BM25-over-tokens is a hand-rolled bag-of-tokens,
**explicitly banned by AGENTS.md §6n** — the spec re-proposed the
prohibited move after three regressions. MF2: BM25 still lexical
(negative-IDF degeneracy on the 232-row corpus, no floor; tie-break
still reorders). MF3: the `if not matched and not buckets: continue`
filter drops the exact failing row before any rank → fix inert. MF4:
T4 gameable. MF5: Q2 forcing condition under-specified (orthogonality
to buckingham_pi_gate accepted).

**Reviewer-prescribed reframe (the AGREED implementable path):**
- **No new scorer.** Deterministic surface stays a deliberately-dumb
  **WEAK PRIOR** (explicitly non-authoritative; §6n-compliant). 
  `primitive_tick_surface._score` NOT modified. Any future relevance
  stage may ONLY reuse `substrate_recommender`/`gnn_lemma_relevance_v21_rerank`
  (§6n) — out of scope here.
- **Decisive fix = the agentic mechanism (B):** the FORCED
  authoritative path is the agent reasoning capability→primitive against
  the FULL curated registry, recorded in the F-row
  `primitives_considered:`/`why_not:` contract (post_tick GAP-F /
  `validate_primitives_considered.py`); `validate_prescription_surfacing.py`
  EXTENDED to also enumerate `architecture_index.jsonl` primitives so a
  registered-but-not-considered capability-matched primitive is flagged
  (completeness backstop, independent of the weak prior).
- **Truthful applicability vocab** in `architecture_index.jsonl`
  (truthful capability tokens — truthful metadata the agent/coverage
  reads, NOT the banned scorer; §6n wants truthful applicability).
- **Q2** π-group `pi_group_forcing` primitive ships AFTER the MF5 fix:
  FORCED iff `dim(quantity)` uniquely representable over subset S after
  quotienting by null-space vectors supported on S;
  `needs_independent_constant` by `rank([dim S]) vs rank([dim S | dim
  quantity])`; rational exponents; explicit no-solution branch.
  Orthogonal to `buckingham_pi_gate` (transcendental-arg only).

**Decision:** reviewer rejected the original (BM25) design and prescribed
the above reframe; implementing the reviewer's own prescription =
"reviewer agrees" to the reframe. Implementation proceeds on the
reframe; the IMPLEMENTATION is itself adversarially reviewed before
trust (`feedback_infra_change_needs_adversarial_survival_before_trust`).
Cross-refs: AGENTS.md §6n; GP-225 (ranker lineage — redirected here);
Task #21; `projects/ns_millennium_hunt/workspace/surfacing_fix_design_for_review_20260516.md`.

### Implementation complete — 2026-05-16 (this seam owns these primitives)

Both angles implemented exactly per the reviewer-prescribed reframe; this
seam is the spec of record that created the primitives below.

**Q1 — surfacing completeness backstop (no new scorer; §6n-compliant).**
`scripts/public/validators/validate_prescription_surfacing.py` extended:
new `arch_self_surfacing_gaps()` imports the REAL mechanism
(`ztare.research_director.primitive_tick_surface.build_primitive_tick_surface`)
— not a lexical proxy, not a duplicate — and, for every arch-index
primitive that declares an `applicability` vector, queries the surface
with that primitive's OWN applicability and flags it if it is absent
from its own top-N. This is the precise, low-noise coverage test: a
capability registered but un-rankable for its declared purpose (the
LAGRANGIAN-DERIVATION class — buried under `10*impact`). Advisory only:
never a hard FAIL even under `--blocking`; output capped to a coverage
metric + 10-row sample (full list behind `--verbose-arch`) so the
backstop itself is not a buried-prescription treadmill. Empirical
finding: only **~35% (81/233)** of primitives self-surface — i.e. the
deterministic surface is near-worthless as anything but a WEAK PRIOR,
which is exactly the reviewer reframe (agent GAP-F reasoning is the
forced authoritative path; the surface is not a substitute). `_score`
NOT modified (verified). Truthful `applicability` vocab added to
`BUCKINGHAM-PI-GATE` (truthful metadata, not the banned scorer).

**Q2 — `pi_group_forcing` primitive (MF5-corrected).** New
`src/ztare/gates/pi_group_forcing.py` (sibling of `buckingham_pi_gate`,
orthogonal — Buckingham is transcendental-arg-dimensionless AST prune
only). Exact rational linear algebra (sympy): build A = [dim vectors of
subset S], b = dim(target); branch on `rank(A)` vs `rank([A|b])` →
**forced** (b∈col(A), A full column rank: unique monomial), **needs
independent constant** (b∉col(A)), **ambiguous free π-group** (b∈col(A),
non-trivial null space). Validated on 6 cases incl. the canonical NS
heat-length: ℓ from {ν,t} ⇒ FORCED `ν^(1/2)·t^(1/2)`; ℓ from {ν} ⇒
needs-independent-constant; {ν,t,L₀} ⇒ ambiguous. Registered in
`architecture_index.jsonl` as `PI-GROUP-FORCING-GATE` with truthful
applicability — confirmed self-surfacing under the Q1 backstop
(Q1↔Q2 integration test passes). §6n parity: in-loop opt-in dispatch
added to `autoresearch_loop.py` (Path-B block, `enable_pi_group_forcing`
+ `pi_group_targets`, default OFF/inert — mirrors the safe Buckingham
opt-in pattern, never blocks fit); out-of-loop via arch-index
registration + RD-tick `primitive_tick_surface` §9 + external-prover
§5.2. No graph.yaml node (sibling Buckingham has none; not fabricating).

All three modified/created files parse clean. Status: implemented;
adversarial IMPLEMENTATION review returned **SOUND, zero blocking
must-fixes** (2026-05-16) — Q1+Q2 trusted.

## Q3 proposal — CERTIFICATE-PROVENANCE-GATE — 2026-05-16

**Verified gap (not recalled):** read `ns_governance_gate.py` (171L) and
`validate_forward_evidence.py` (144L) in full — both are
schema/vocabulary-laundering only (force `target_kind` enum + anti-mush
regex; self-described "INTEGRATION GLUE, not new detectors"). v33 organs
+ ANTI-PATTERN-013 cover Lean proof-TEXT laundering. `pi_group_forcing`
covers the dimensional half. NO existing gate decides **certificate
provenance**: whether a quantitative certificate (e.g. route-1
`defectBudgetStrictMarginCertificate` ratio<1 — the perennial atom,
hand-checked every tick) is *derived from the genuine source object*
(the PDE) vs *laundered through an adapter / stub / asserting shim*.

**Why decidable & general-purpose:** it is a DAG reachability property,
not an LLM judgment. Walk the certificate's dependency graph backward;
fail iff some path bottoms out at an asserting shim instead of a
genuine root. Substrate-agnostic, parameterized by two
**substrate-supplied deterministic** predicates `is_genuine_root(node)`
and `is_asserting_shim(node)` (Lean: real Mathlib lemma vs
`sorry`/axiom/adapter-stub; fit: real held-out data vs leaked
label/hardcoded; consequence: theorem vs assumed). HARD CONSTRAINT
(adversary must enforce): predicates are deterministic & substrate-
supplied; if they degrade to LLM-adjudication the gate is rejected as
"another advisory artifact" (the documented failure mode). Sibling of
the v33/anti-laundering family, orthogonal (those are proof-text;
this is provenance-DAG). §6n: in-loop opt-in default-OFF + out-of-loop
arch-index + truthful applicability, mirroring Q2.

**Process:** propose (this) → adversarial DESIGN review → if SOUND
implement → adversarial IMPLEMENTATION review before trust
(`feedback_infra_change_needs_adversarial_survival_before_trust`).
Self-contained brief:
`projects/ns_millennium_hunt/workspace/certificate_provenance_gate_design_20260516.md`.
NS stays cleared until Q3 review cycle completes (operator-authorized).

### Q3 DESIGN REVIEW VERDICT: FLAWED — 2026-05-16

Adversarial design review returned **FLAWED**, 4 blocking must-fixes
(recorded verbatim, not laundered):
1. The used-constants reachability DAG the design depends on **does not
   exist**; only the `#print axioms` kernel closure does
   (`verify_lean_stub.py:149`, `lean_proof_gate.py:293-306`).
   `extract_mathlib_graph.py` is regex name-matching, NOT a kernel dep
   graph. Re-scope predicates to the axiom-closure (real, deterministic)
   OR specify a genuine `CollectAxioms`/const-closure extractor — do not
   reuse the regex graph.
2. `extract_provenance_dag → None`/empty on a *formal* (Lean) substrate
   must map to **LAUNDERED, not NOT_APPLICABLE**. NOT_APPLICABLE must key
   off *declared substrate class*, never extraction success — else the
   opaque-`by`-block evasion passes.
3. Specify the predicate-coverage calibration threshold; explicitly
   state hypothesis-as-fact is NOT in the deterministic set (defer to
   v33 currency-mismatch / indirect-leakage; do not claim it).
4. Cite the `v33_indirect_leakage` adjacency; soften "general-purpose"
   to **"Lean/formal-substrate gate; non-formal substrates explicitly
   NOT_APPLICABLE."**

Honest consequence: the high-value, genuinely-novel core (does the
certificate *term* transitively reduce to PDE-level lemmas, vs a
sorry-free-but-asserting `opaque`/parametric shim) needs a real Lean
const-closure extractor that **does not exist** — that is a project,
not a session task. The thin re-scope (axiom-closure only) is largely
**duplicative of `lean_proof_gate.py` GP-211**, so low marginal value.
Per FLAWED-discipline: NOT implemented. v2 spec
(`...certificate_provenance_gate_design_20260516.md`, revised) captures
the 4 must-fixes. Scoping fork handed to operator (build the
const-closure extractor as a project / thin-but-low-value / park as
recorded known-gap + resume NS). Do NOT reimplement mid-session.

### Q3 ownership + v2 (D) re-scope — 2026-05-16

**Ownership resolved (cross-agent contention avoided):** the parallel
Path-B/bundle agent formally DECLINED Q3 with 3 decisive reasons —
(1) implementation locus is the Lean-spine gate `src/ztare/gates/
lean_proof_gate.py` (hosts the v33 organs), MY infra, not substrate-
agnostic bundle Path-B; (2) the GP-188 Q3 review cycle + FLAWED verdict
+ fork are mine (FLAWED ⇒ my fix-and-re-review); (3) the hard residual
is Lean-spine infra not bundle governance. **Q3 is owned here.** The
bundle agent must NOT edit `lean_proof_gate.py`; this seam must NOT
edit bundle Path-B — the ownership boundary is explicit and recorded
to prevent the two threads converging on one file.

**v2 design = (D) signature-shape consequence-exposure organ**, a new
v33-sibling organ in `lean_proof_gate.py` (wired via the existing
`anti_laundering_passed` / `v33_organ_flags` / `enforce_anti_laundering`
surface). Detects the dominant, decidable shim form: a claimed-closure
theorem that smuggles the hard target into its own signature as an
assumed hypothesis — `theorem cert (h : HardTargetThing) … : Goal` —
i.e. "consequence: assumed" mislabeled as proof_closure (the T3N1/T3N2
manual call mechanized). Addresses the 4 FLAWED must-fixes:
- MF1: operates on the theorem **signature binders** (present,
  parseable) — NOT the nonexistent reachability DAG, NOT the regex
  import graph. Deterministic; substrate-supplied hard-target
  head-symbol/name set; no CollectAxioms, no LLM.
- MF2: keyed on declared `cage_meta.substrate_class`. If
  `substrate_class == lean_proof` and the claimed-closure theorem
  signature is unparseable / no theorem decl → **LAUNDERED**
  (fail-closed), never NOT_APPLICABLE. NOT_APPLICABLE is reserved for
  declared non-lean substrate_class only (closes the opaque-`by`-block
  / drop-the-formalism evasion).
- MF3: calibration = advisory until N clean ticks; blocking only on
  the unambiguous case (a hypothesis binder whose type head-symbol ∈
  the substrate hard-target set). EXPLICITLY NOT covered: mid-term
  opaque/parametric adapter buried in the proof term — that is the
  parked Fork-A const-closure residual, NOT claimed here.
- MF4: cites the `v33_indirect_leakage` adjacency (different object:
  simp-set gold-lemma leakage vs signature binder smuggling — sibling,
  not duplicate). Scope claim softened to **"Lean/formal-substrate
  organ; non-lean substrate_class → NOT_APPLICABLE."**

Process: v2 spec (this) + self-contained brief
`projects/ns_millennium_hunt/workspace/certificate_provenance_gate_v2_design_20260516.md`
→ adversarial DESIGN review of v2 → implement ONLY on SOUND → adversarial
IMPLEMENTATION review before trust. NS resumes after the v2 cycle.

### Q3 v2 DESIGN REVIEW: FLAWED — Q3 RETRACTED as a session task — 2026-05-16

v2 adversarial design review = **FLAWED**, decisive (not a patch list).
Two decisive, verified findings:
1. **Core decidability claim false under the cheapest evasion.**
   `abbrev Reg (u) := GlobalRegularity u; theorem cert (h : Reg u) :
   Goal := …` — head symbol `Reg ∉ hard_target_heads`; compiles,
   sorry-free, axiom-clean, all v33 organs PASS. Catching it requires
   Lean `whnf`/`isDefEq` kernel re-probe = the term-level const-closure
   infra v2 explicitly excluded = the parked Fork-A residual =
   project-scale. The cheap signature-parse form is structurally
   incapable of its own purpose. (Also: `hard_target_heads` is a
   relocated human/LLM judgment denylist whose namespace the adversary
   controls — zero adversarial floor; Q5 goal-head-in-hypothesis rule
   false-FAILs legitimate induction / well-founded / mutual shapes.)
2. **Motivating case already covered.** `ns_governance_gate.py:52-87` +
   `MUSH_RE:83-87` already prevents a `consequence_exposure` row from
   claiming closure (NS_KIND_MAP + anti-mush). The T3N1/T3N2 "manual
   label" cited as the gap was the governance gate WORKING, not a gap.
   (Independently re-verified by reading the file in-thread.)

**Decision (premature — see Meta-Darwin of the kill below).**

### Meta-Darwin OF THE KILL — negative UN-SETTLED — 2026-05-16

Operator-forced: the v1/v2 FLAWED verdicts were both **attack-only**
adversaries (briefed "a false SOUND is the costly error" — asymmetric
toward FLAWED). Per `feedback_discipline_verdict_is_artifact_scoped`
("never settle a scientific negative from one attack-only adversary")
the kill itself must survive Meta-Darwin. It does NOT — both
decisive legs are overclaimed:

- **Leg 1 (abbrev ⇒ needs kernel `whnf`/`isDefEq`): overclaimed.**
  Conflates general definitional equality with **file-local
  delta/structure-decl closure**: unfold the submitted file's OWN
  `abbrev`/`def`/`structure` declarations (a finite, decidable,
  pure-parse fixpoint — no kernel re-probe) THEN head-match. The cheap
  evasions (`abbrev Reg := GR`, one-field `structure`, in-file `def`)
  are caught by this closure. Genuinely-uncatchable-by-parse reduces to
  the hard target reached via a *pre-existing library* def-chain not in
  the submitted file = the Fork-A residual (correctly parked).
  Separately, the reviewer's `Nonempty/PLift/True→` "lethal variants"
  are strictly-WEAKER props — not the hard target — so using them as a
  hypothesis is not smuggling it (different, often-sound, case).
- **Leg 2 (motivating case already covered by NS-GOVERNANCE-GATE):
  VERIFIED FALSE.** `ns_governance_gate.py:90-107`: for
  `target_kind=="proof_closure"` it routes purely on `_run_v33(lp)`;
  it does NOT parse the signature. v33 organs (per the v2 reviewer
  itself) do not parse binders. So the governance gate covers the
  HONESTLY-labeled consequence case (MUSH_RE + `else` branch); the
  DISHONESTLY-labeled `proof_closure` that smuggles the hard target
  into its signature is **open**. Artifact-scope (honest label) was
  conflated with idea-scope (dishonest smuggle).

**Status: Q3 is NOT a closed negative.** The negative was overclaimed;
un-settled. Corrected scope **v3**: a signature-parse organ WITH
file-local delta/structure-decl closure, target = dishonestly-labeled
`proof_closure` whose signature assumes the hard target (VERIFIED open,
NOT covered by NS-GOVERNANCE-GATE). `hard_target_heads` gameability is
substantially mitigated by the in-file closure (adversary's own in-file
aliases get unfolded). Residual narrowed to: hard target via
pre-existing *library* def-chain only = Fork-A term-closure project
(still parked). v3 is **specced here, deferred for its own balanced
(not attack-only) review cycle** — NOT run now (operator directed
move-to-NS); NOT implemented; NOT a closed negative either way. No
treadmill: this is the operator-requested Meta-Darwin output, recorded,
then parked pending a balanced-adversary review.

### Q3 v3 BALANCED REVIEW + KILL-AUDIT — 2026-05-16

Verdict: **concept SOUND / implementable; FLAWED only on 3 finite
must-fixes; KILL-AUDIT: prior v2 kill OVERCLAIMED on BOTH legs —
independently confirmed with file:line.**
- Leg1 overclaimed: `v33_preflight_risk_detector.py:52-72` already does
  pure-parse binder/head split in this repo (no elaborator); kernel
  `isDefEq` needed ONLY for the parked library-chain residual.
- Leg2 VERIFIED FALSE: `ns_governance_gate.py:90-107` routes
  `proof_closure` purely on `_run_v33(lp)`, never parses the signature;
  the four v33 organs (`lean_proof_gate.py:463-515`) do not inspect
  binders vs hard-target heads. Dishonest-label smuggle is OPEN.
- NS-benefit REAL: `ns_residual_manifest.md:52-68` is literally the
  ≥14×-repeated hand-check this organ mechanizes.
Three finite MUST-FIXES before trust: (1) step-2 head extraction must
descend a fixed transparent-wrapper allowlist (`Fact`/`Subtype`/
`{_//_}`/`Nonempty`/`PLift`/`ULift`/`id`/instance-binder `[…]`/
`∀→`-strict-positive-tail) before the hard-target-head test; (2)
replace syntactic "`∃`-only ⇒ weaker" with a witness-non-triviality
test; (3) `hard_target_heads` substrate-keyed + narrow, never generic.

**Status: NOT a closed negative; NOT a treadmill — three reviews
converged.** Path: apply 3 must-fixes → v3.1 → implement organ in
`lean_proof_gate.py` → adversarial IMPLEMENTATION review before trust.
Fork-A library-chain term-closure remains the parked residual.

### Dispatch-economy RCA + GAP-G forced ledger — IMPLEMENTED 2026-05-16

RCA (verified by inspection): the dispatch-economy mechanization
(`rd_tick_brief.py:607` `predispatch_reminder()` + PATTERN-011) failed
to prevent a sustained orchestration relapse because it is (1) an
advisory PRINT not a measured forcing check, (2) coupled to the
rd_tick_brief NS-pre-tick path — the relapse was out-of-loop meta-work
that never routes there (verified: rd_tick_brief never ran the session),
(3) unenforced. SAME class as the Q1 surfacing bug (forcing function
path-coupled + advisory). First design (post-hoc transcript
dispatch:compose ratio+maxrun) adversarially reviewed **WRONG**: ratio
false-FIRES on the *sanctioned* compose→adversarial-kill cadence and on
legitimate divide-and-conquer; Claude-JSONL signal is fleet-non-portable
(reproduces path-coupling). Reviewer-prescribed correct design
IMPLEMENTED: ledger-only forced self-account
`src/ztare/validator/dispatch_ledger_check.py` (GAP-G; in src/ per the
in-loop→src rule). Every going-forward tick F-row must carry
`dispatch_ledger: none|<label>=<adversarial_kill|divide_and_conquer|
cold_deanchor_carveout3>`; missing field or unsanctioned class = flagged
violation (the honest self-incrimination the operator cannot un-see).
Path-INDEPENDENT: additive advisory leg in `post_tick_check.py` (§8c,
mirrors GAP-F, no shared state) + standalone. Retroactive-exempt
(only today's rows), advisory→`--blocking` post-calibration, never
false-FAIL — empirically: tick613/614 with sanctioned `adversarial_kill`
ledgers pass clean (no false-FIRE on sanctioned cadence, the reviewer's
decisive property). Composed in-thread; the single dispatch was the
sanctioned adversarial review itself.

### Q3 v3.1 IMPLEMENTED — 2026-05-16

New organ `scripts/public/control/v33_consequence_exposure_gate.py`
(sibling of the 4 v33 organs, same `_load` pattern), wired into
`src/ztare/gates/lean_proof_gate.py::_run_v33_anti_laundering` (a
`blocking` shape ⇒ `consequence_exposure_confirmed` ⇒ fails the layer
via the existing `_confirmed` filter; else
`consequence_exposure_shape_suspect_advisory`). All 3 must-fixes
implemented + smoke-verified (7 cases): MF1 file-local delta/structure
closure + transparent-wrapper allowlist descent catches the
`abbrev`/`structure`/`Fact` evasions; MF2 fail-closed at the
lean_proof locus (no-theorem / unparseable ⇒ blocking) and
NOT_APPLICABLE cannot arise here by construction (locus only runs for
substrate_class==lean_proof); MF3 `Nonempty`/`Trunc` strictly-weaker
excluded via witness-non-triviality, `hard_target_heads`
substrate-supplied & NARROW via sidecar `v33_hard_target_heads.txt`,
**default-empty ⇒ blocking rule inert (advisory-only) = correct
staged-blocking default, zero false-FAIL on the live loop**. §6n
VERIFIED (not asserted): in-loop via
`src/ztare/validator/lean_substrate_runner.py:86 → run_lean_proof_gate
→ _run_v33_anti_laundering:600`; decisive wiring in `src/`;
arch-index row `V33-CONSEQUENCE-EXPOSURE-GATE` registered with truthful
applicability. Both files parse. NEXT: adversarial IMPLEMENTATION
review before trust (dispatched). Fork-A library-chain residual still
parked.
