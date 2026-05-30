---
id: PATTERN-014
name: cold_shot_dispatch
version: 1
status: active
discovered: 2026-05-09
discovered_reason: |
  Pre-existed as kernel primitive at `src/ztare/fit/cold_llm_erdos_seed.py`
  and as project-side cold-shot scripts and `cold_shot_policy.json`
  workspace files since approximately 2026-05-02.
  Operator catch (2026-05-09 evening): this cold-shot pattern had already
  been implemented in ZTARE (the Erdős cold-LLM seed) roughly a week
  earlier, and the operator had explicitly asked for such primitives to
  be extracted; the catalog was minted without exhaustively ingesting
  existing kernel primitives despite a patterns graph already existing.
  Pattern-extraction failure: minted org/patterns/INDEX.md
  catalog without exhaustive ingestion of existing ZTARE kernel primitives.
  Catch C-2026-05-09-60.
triggers:
  lexical: [
    "treat as the book", "Erdős-style", "Erdős style", "alien-math",
    "alien math tradition", "no prior context", "de-anchor", "de_anchor",
    "ignore the literature", "fresh attempt"
  ]
  structural:
    - load_bearing_eigenquestion_with_anchored_failure_modes
    - same_family_LLM_dispatches_have_converged_on_a_dead_route
    - need_to_break_anchoring_on_canonical_literature
    - cross_vocabulary_audit_flagged_anchoring_risk
  problem_classes:
    - hard_mathematical_residual
    - vocabulary_drift_risk
    - pre_category_emergence
    - load_bearing_falsifiable_proposition
spawn:
  mode: cold_shot
  variants:
    - mode: kernel_library
      description: |
        Existing ZTARE kernel primitive. Used during ZTARE iter loop
        pre_iter_1 advisory phase. Multi-family cold-shot family policy
        (de_anchor_seed / structural_seed / physics_lagrangian_seed /
        qualitative_evidence_seed) selected per substrate class.
      module: src.ztare.fit.cold_llm_erdos_seed
      project_examples:
        - projects/*/workspace/cold_shot_policy.json
        - projects/gp210_consciousness_theory/workspace/cold_shot_policy.json
        - projects/ns_spike_lifecycle_discriminator/workspace/cold_shot_policy.json
    - mode: rd_direct_external_prover
      description: |
        Research-Director-direct cross-family LLM cold-shot via OpenAI/
        Anthropic/Google API. Used when (a) no ZTARE iter loop is active
        on the substrate, or (b) the central question is at the
        meta-architecture layer (e.g. "is this Lean encoding faithful?").
        Operator-authorized 2026-05-09 with $10 hard cap.
      tools: [bash]
      scripts:
        - scripts/public/control/dispatch_external_prover.py  # this dispatcher
      kill_criteria:
        - cumulative_session_spend_USD: 10.0
        - per_dispatch_cap_USD: 5.0
output_schema: cold_shot_response_v1
fallback: PATTERN-011  # if cold-shot reveals the question needs N parallel attacks, escalate to swarm
preconditions:
  - eigenquestion_shape_validated: yes  # see PATTERN-015
  - anchored_failure_modes_explicit: yes  # the cold-shot prompt MUST list "do not anchor on [X / Y / Z]"
chain_position: pre_iter | post_demolition  # before main iter, OR after a route is demolished and we need a fresh attempt
related_patterns:
  - id: PATTERN-005
    relation: child  # falsifiable_asymmetry, cold-shot prompts demand a falsifiable verdict
  - id: PATTERN-009
    relation: sibling  # both are cross-validation; PATTERN-009 is CAS, PATTERN-014 is LLM
  - id: PATTERN-011
    relation: parent  # swarm_dispatch is N-parallel; cold-shot is 1-shot deep
  - id: PATTERN-015
    relation: required  # cold-shot is only as good as its eigenquestion phrasing
references:
  - existing kernel: src/ztare/fit/cold_llm_erdos_seed.py
  - cold-shot policy schema: projects/*/workspace/cold_shot_policy.json
  - ANTI-PATTERN-006 (cross_agent_monoculture), cold-shot is the cross-family answer
falsifiable_test: |
  Over N>=15 cold-shot dispatches in a campaign window, at least 30% must produce a
  verdict that either contradicts a same-family verdict the RD previously relied on
  OR names a structural defect the RD missed (measured against the catch ledger).
  If the contradiction/net-new-defect rate across any 15 cold-shots falls below 30%
  — i.e. cold-shots only confirm internal verdicts — the cross-family-lift
  hypothesis is empirically false and the pattern demotes.
  metric_source: external_prover_ledger.jsonl (cold-shot verdicts) joined to the
  catch ledger for external_via_operator-sourced catches; dispatch counts from
  pattern_deployment_ledger.jsonl primary_pattern=PATTERN-014.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-014, Cold-Shot Dispatch

## What this pattern is

A **single-dispatch, cross-family, no-prior-context, de-anchored, alien-
math-discipline** prompt to an LLM (today: GPT-5.5 / Gemini-Pro), used
to attack a central eigenquestion when same-family agents have
converged on a dead route or the question lives at the meta-architecture
layer that internal Claude swarms can't reach without bias.

Distinct from:
* **PATTERN-009 (independent_cas_verification)**: SymPy/numpy CAS check,
  not an LLM dispatch.
* **PATTERN-011 (swarm_dispatch)**: N parallel workers (agent-based or
  PY-LLM-based). Cold-shot is **1 deep dispatch**, not N parallel.
* **PATTERN-002 (darwin_idea_killer)**: same-family adversarial attack.
  Cold-shot is **cross-family** with explicit de-anchoring.

## The 5-bullet cold-shot discipline

Every cold-shot prompt MUST contain (verbatim or close paraphrase):

1. **No prior context**: "You are receiving this with no prior
   conversation context."
2. **The book framing**: "Treat the data as a problem from 'the book', 
   attack it on its merits, not on the canonical framings the
   literature has already tried."
3. **Explicit de-anchoring**: "Do not anchor on [LIST: papers/ techniques
   the failing route used] even though those are cited below."
4. **Drop non-central frames**: "If a frame is not central for
   the problem, drop it."
5. **Alien-math tradition swap**: "Alien-math discipline: assume you are
   a mathematician from a different tradition than [the tradition that
   produced the failing route], what would such a tradition reach for
   first?"

Plus the standard problem-statement structure:
* THE PROBLEM (eigenquestion in ≤200 words).
* EMPIRICAL DATA / WHAT IS KNOWN (≤500 words, including counterexamples
  that ruled out earlier routes).
* WHAT'S BEEN TRIED AND REFUTED (named with arXiv ids + verdicts).
* FALSIFIABLE OUTPUT FORMAT (per PATTERN-005): demand a verdict line
  ending in "[yes / no / partially / unknown, one-sentence rationale]".

Without these bullets, the dispatch is a generic LLM call and reverts
to single-family bias.

## When to deploy

* **Pre-iter advisory** (kernel mode): before launching a ZTARE iter on
  a new substrate, fire the cold-shot family policy to seed the iter
  with diverse non-self-derived starting points.
* **Post-demolition** (RD-direct mode): after an internal Claude swarm
  has converged on a route that an external cross-vocabulary audit or
  external prover demolished, re-attack with cold-shot from a different
  tradition. Tonight's two operator-relayed GPT-5.5 dispatches (Q1 on
  BKGSW+NC, Q2 on Lerner-port faithfulness) are canonical examples.
* **Central meta-architecture question**: when the question is
  about how the apparatus is itself thinking ("is this Lean encoding
  faithful to the published theorem"), internal-Claude has bias.
  Cold-shot is the cross-family answer.

## When NOT to deploy

* When the question is tractable for an internal swarm and same-family
  bias is a feature (e.g. closing a Lean sorry on a proof the dispatcher
  is already in the middle of). PATTERN-001 (friction_debate) or
  PATTERN-011 (swarm_dispatch) is cheaper and adequate.
* When the eigenquestion has not yet been validated under PATTERN-015
  (eigenquestion_phrasing_discipline), a poorly-phrased cold-shot
  wastes paid cross-family capacity.

## Cost discipline

* `scripts/public/control/dispatch_external_prover.py` enforces a hard $10 session cap
  (operator-authorized 2026-05-09).
* Per-dispatch cap default $5; override via `--max-cost-usd`.
* Every dispatch logs a row to `analytics/public/ledgers/external_prover/external_prover_ledger.jsonl`
  AND a row to `analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl` tagged
  PATTERN-014.

## Falsifiable-asymmetry test (per PATTERN-005)

Cold-shot is "working" iff: there exists at least one cold-shot dispatch
in the campaign window whose verdict (a) contradicted a same-family
verdict the RD had previously relied on, or (b) named a structural
defect the RD missed. Tonight's C-58 + C-59 are two such instances
(operator-relayed cold-shots). The pattern is **falsified** if cold-
shots only ever confirm existing internal verdicts, that would mean
the cross-family-lift hypothesis is empirically wrong.

## Theory-building vs falsification mode (added 2026-05-09 ~19:30 UTC; sharpened by Codex swarm 2026-05-09)

Empirical finding: the apparatus has been deploying cold-shots in
~80% FALSIFICATION mode ("is X faithful?", "is Y over-strengthened?",
"what's our Lord Kelvin?") and ~20% THEORY-BUILDING mode. Operator
catch verbatim 2026-05-09 ~19:25 UTC: "instead of falsifying attempt
theory building and problem solving in the cold shot with the 1800s
framing... we need to select the right problemsolving/theory building
questions for cold shots, not only falsification attempts. though
falsification is the hallmark of darwin and our apparatus, i know that."

Cold-shots have TWO orthogonal modes:

* **FALSIFICATION mode**: dispatch asks GPT-5 to AUDIT/CRITIQUE/TEST
  an existing claim, approach, or artifact. Output is a verdict
  (yes/no/partial), counterexample, or named obstruction. Pattern:
  PATTERN-005 falsifiable_asymmetry deployed. Examples tonight:
  PL-070 Lerner port faithfulness, PL-082 plancherel axiom verification,
  PL-088 axioms #1/#3 over-strengthening, PL-090 Clay timeline, PL-091
  X post expert critique, PL-093 Lord Kelvin diagnosis, PL-098
  Caccioppoli charter target validity.

* **THEORY-BUILDING mode**: dispatch asks GPT-5 to PRODUCE a
  construction, candidate definition, missing abstraction, or new
  lemma. Output is mathematical content, not a verdict. Pattern:
  Gowers methodology, give the model a relatively-new framework
  and ask DIRECTLY for the proof/construction. Examples tonight:
  PL-094 NS-arc projection (produced 6-week pivot plan), PL-099
  μ[u] candidate construction (in flight as of writing).

The 1880s/2080s benchmark framing is a THEORY-BUILDING tool, not a
falsification one. Riemann pre-Selberg had rich pattern recognition;
the BENCHMARK (Selberg trace formula 90 years later) tells us the
missing piece was a STRUCTURAL OBJECT linking zeta to spectral
theory. Projecting forward: the NS Clay missing piece is candidate
defect-calculus per C-93. Cold-shot should ASK FOR THE CONSTRUCTION,
not audit whether existing approaches are faithful.

### Submode: retrospective_failure_benchmark

This is the reusable form of the operator's "1880s / what will look
obvious in 50-100 years?" instruction. It remains inside PATTERN-014
rather than receiving a new pattern id as of 2026-05-09, because the
catalog already covers it as a theory-building cold-shot submode and
the independent catalog explorer recommended extension over minting.

Required output shape:

1. Name the historical failure class (e.g. wrong carrier, wrong
   topology, missing invariant, missing compactness principle).
2. Map it to a present artifact: file, theorem, prediction row, catch,
   or cold-shot packet.
3. Produce or repair the theorem/construction first.
4. Only then fill verification forks, three-leg checks, or retrospective
   verdicts.
5. State the exact next artifact to change.

Anti-capture rule: if the prompt's first requested deliverable is only
an audit/fork/verdict, rewrite before dispatch. PL-111 was superseded
for this reason; PL-112 was proof-attempt-first and produced the L3A
concentration-carrier repair.

Gowers protocol connection: the 2026-05-08 Gowers report is relevant
not because it is an authority, but because its workflow asks for
construction/proof writeup first, then human checking and preferably
formalization. Use forks and checks as guardrails around proof work,
not substitutes for proof work.

Mix going forward: roughly 50% falsification + 50% theory-building.
Theory-building for genuinely Clay-relevant constructions (where
the missing-abstraction projection points). Falsification for any
apparatus-shipped artifact before downstream commitment.

## Reasoning-effort preference (added 2026-05-09 per operator directive ~16:35 UTC)

Empirical finding from tonight's batch: `reasoning-effort=high` is the
right default for Tier-1 cold-shot dispatches. Specifically for:

* Strategic eigenquestions (substrate-target pair selection,
  Clay-timeline tests, methodology audits).
* Multi-step proof-rigor verifications (e.g. Bochner-Fejér limit
  passages, Plancherel identities).
* Cross-vocabulary translation audits.

`reasoning-effort=medium` is acceptable for:
* Tactical refactor-execution (e.g. axiom rewrites, citation
  updates).
* Verification of already-known classical identities.
* Quick pivot-residual scoping where speed matters more than depth.

The cost differential (medium vs high) is typically $0.20-0.50 per
dispatch, small relative to the strategic value of high-quality
Tier-1 verdicts. Default to high for genuinely Tier-1 work; only
drop to medium for tactical verification.

The dispatcher script `scripts/public/control/dispatch_external_prover.py` already
defaults to `high` in its argparse; explicit `--reasoning-effort
medium` overrides should be reserved for tactical-only dispatches.

## Citation-verification rule (added 2026-05-09 per catch C-70)

**Mandatory abstract-first-sentence-quote requirement.** Empirical 2026-05-09:
single GPT-5 cold-shot dispatch returned 3 of 3 PHANTOM arXiv identifiers
(IDs resolved to statistics / judo / info-science papers, not the cited NS
results). The conceptual content was roughly correct (backward DSS Liouville
IS open; Seregin DOES work on stationary Liouville) but the IDENTIFIER LAYER
is hallucinated.

Calibration: GPT-5 cold-shot arXiv-ID hallucination prior is empirically
~0.50, not the ~0.05 the RD initially estimated.

**Every cold-shot prompt that asks for citations MUST require:**

> For each arXiv ID you cite, quote the ABSTRACT'S FIRST SENTENCE
> alongside the ID. This is a verification anchor; it lets a downstream
> internal verification agent cross-check the ID without fetching the
> paper.

**Mandatory post-dispatch step**: PATTERN-009 (independent_cas_verification,
internal-Claude-with-WebFetch variant) is REQUIRED on any cold-shot output
containing arXiv IDs BEFORE the IDs propagate to any downstream artifact
(catch ledger, paper draft, X post, journey doc, task description).

**Failure-mode note**: the conceptual content of cold-shot output is
typically reliable (the 5 of 5 cold-shots tonight all returned mathematically
sound conceptual analysis). The hallucination surface is the **identifier
layer**, author names roughly right, theorem statements roughly right, but
arXiv IDs / journal volumes / page numbers fabricated. The verification
protocol bridges this gap.

## Cold-shot-before-encoding rule (added 2026-05-09 per catch C-61)

When an external prover (cold-shot or operator-relay) proposes a
**next-campaign target** (a new theorem statement, a new analytic
framework, a new replacement route after a previous demolition), the
target MUST itself be cold-shot tested via PATTERN-014 BEFORE any
internal Lean encoding consumes agent-hours.

**Canonical evidence**: catch C-2026-05-09-61. The same GPT-5.5
framework that derived the height-filtered Leray-skew commutator
framework as the next-campaign target (after demolishing the additive-
combinatorics route) demolished its own proposal 4 hours later via
GPT-5 cold-shot (height-scale collapse for Liouville ω). The internal
Lean encoding `ns_trackb_W6_NEW_3_LeraySkewCommutator.lean` (~250 LoC,
~12 wall-clock minutes of agent time) was shipped IN BETWEEN, and is
now retroactively tagged with the demolition.

**Mitigation**: every next-campaign-target proposition gets a $0.30-
$0.60 cold-shot test before it gets a Lean file. Costs $0.50, saves
$5-10 of agent-time + the catch-ledger churn of having to demolish
in-flight encoding.

## Anti-laundering catches

* **ANTI-PATTERN-006 (cross_agent_monoculture)**: cold-shot's whole
  point is to defeat single-family laundering. If the "cold-shot"
  is actually an internal Claude agent dispatched without the 5-bullet
  discipline, the pattern is misapplied.
* **Catch C-60 (this pattern's minting catch)**: when the pattern was
  initially missing, the existing kernel `cold_llm_erdos_seed.py`
  primitive was rediscovered ad-hoc as "PATTERN-009 deployment." The
  fix is this pattern doc + the explicit kernel cross-references above.
