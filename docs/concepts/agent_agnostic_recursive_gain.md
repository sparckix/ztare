---
description: "Why recursive self-improvement here is mining-mediated rather than iter-loop-bound."
---
# Agent-Agnostic Recursive Gain

> **Up:** [Documentation map](../README.md)

## Where recursive gain actually lives

Recursive self-improvement, the loop that lets a research apparatus get
better at its own job, was originally implemented inside ZTARE's iter
loop. The apparatus generated candidate apparatus-refinements
(rubrics, primitives, design choices), evaluated them against a Newton-
mode rubric, and shipped the survivor. We called this "ZTARE-on-ZTARE."

That framing assumed the recursive gain had to live inside the iter
loop. As the project matured, most of the actual research work shifted
to **Research Director agents** working on substrates (Navier-Stokes
proof search, modified gravity, consciousness theory, Fermi-paradox
discriminators) **outside** the ZTARE iter loop. The original ZTARE-on-
ZTARE seam went mostly dormant, which made it look like recursive gain
had gone dormant too.

It hasn't. It doesn't matter which agent does the work. As long as the
work hits the apparatus's data ecosystem (F-rows, project workspaces,
seams, papers, verified-axioms ledgers), the mining layer harvests it,
and the harvested signals can feed back into apparatus refinement.
Recursive gain doesn't require in-loop evaluation; it requires
mining-mediated evidence flowing back to apparatus state.

## Three consequences

Three implications:

### 1. Agent-agnostic gain

Research Director agents (Codex, Claude as Director, future agents),
operator-typed work, automated daemons, all produce artifacts that
the data ecosystem captures equivalently. From the gain cycle's
perspective they are the same input. The apparatus's recursive
capability does not depend on which agent did the typing.

### 2. Mining is the new ZTARE-iter

The mining infrastructure built around [GP-227](../../research_areas/seams/reflexive/GP-227_apparatus_sophistication_vs_insight_curve.md) (`mine_trajectory_curves`,
`mine_reference_graph`, `sample_artifacts_for_taste`,
`mine_recursive_gain_candidates`) plus the trajectory dashboard
constitutes one full revolution of a recursive-gain cycle:

  produce artifacts → mine signals → surface candidates →
  operator-or-substrate ships refinement → next week's mining
  catches the consequences

The cycle runs at week-scale, not iter-scale, but the shape is
structurally identical to ZTARE's iter loop. The slowness is a feature
when the cell of the cycle is "ship a real apparatus refinement"
rather than "evaluate a candidate string."

### 3. Expanded-scope ZTARE substrate is the natural step

The old framing ran ZTARE on a small self-referential substrate
(architectural primitives for the apparatus). The new framing runs
ZTARE on **the apparatus's full corpus of work this week**, mined
outputs as substrate. The mutator proposes apparatus refinements; the
rubric scores against evidence drawn from the mining outputs; survivors
are operator-reviewed before promotion. The substrate grows weekly
because the corpus grows weekly.

The result is that the apparatus evaluates its own ecosystem of work,
regardless of which sub-agent did which piece of that work.

## Choosing the unit of agency

A FinanceOS browser-import failure showed a second axis to the agent-agnostic thesis. The question is not only whether work compounds regardless of which agent authored the artifact. It is whether the human-AI pair has chosen the right *unit of agency* for the task.

In that episode, the pair spent hours improving a narrow browser controller: compressed DOM prompts, action schemas, state-machine guards, progress copy, telemetry, and replay checks. Those fixes were locally rational inside the assumed frame. But a Codex-style tool-using agent attached to the same live browser session completed the import in minutes by inspecting the page, probing the runtime, diagnosing the blob download path, verifying bytes, and adapting strategy. The failure was not simply model weakness. The human and AI jointly optimized a controller when the task needed an operator.

This adds a new rule to recursive-gain architecture:

```text
live unknown system -> agentic operator first -> trace/mine -> distill controller later
stable typed loop   -> controller/gate first -> human operator only at boundary
```

The scientific-discovery analogue is direct. Autoresearch loops, rubrics, gates, and briefing providers are powerful when the substrate has a stable evaluation surface. They become harmful if they prematurely compress an unresolved research act into the wrong control grammar. In those cases the correct move is a Research Director / Codex-style operator pass: inspect artifacts, run probes, write narrow scripts, verify outputs, and leave a trace dense enough that the apparatus can later mine or mechanize the move.

The ZTARE boundary becomes sharper:

- ZTARE owns reusable candidate-generation, falsification, memory, gates, and typed evaluation once the research game is well specified.
- Agentic operators own live ambiguity when the task is operationally under-specified: target selection, substrate repair, proof-source audits, tool choice, and frame correction.
- RAG/memory should retrieve prior traces and failure families for the agentic operator; it should not be mistaken for agency.
- Successful operator traces are the raw material from which future ZTARE primitives are distilled.

This is not an argument against ZTARE. It is an argument against using ZTARE-shaped controllers before the task has earned that shape. Mechanize what has become stable; keep an operator on what hasn't. The workbench therefore has two legitimate modes: agentic-operator-first exploration for live unknown systems, and controller/gate-first execution once the evaluation surface is stable. The human operator still owns accountability for promotion, publication, and strategic direction.

## Lab-Scale Training Flywheel

The same recursive-gain pattern has a lab-scale interpretation. Frontier labs
can and likely do internalize parts of this loop into evaluation,
post-training, and future data generation. That does not make the loop
irrelevant. It changes what should be preserved.

The valuable object is the labeled research trace, not only the final answer:

```text
attempt -> critique -> executable check -> demotion/null/promotion
-> source-readiness label -> next falsifier -> later mining
```

If that trace is collapsed too early into a polished answer, the model learns
success surfaces but loses the judgment process: what was overclaimed, what
source was blocked, which falsifier mattered, which attractive story had to be
retired, and which missing artifact prevented promotion.

For labs, ZTARE is best read as a public design pattern for research-supervision
data:

- preserve failures and demotions as first-class training/eval rows;
- label source readiness and non-claims, not just answer correctness;
- separate generator, critic, judge, and deterministic gate traces;
- mine human-operator and agentic-operator research traces into future rubrics and evals;
- avoid treating polished final answers as the only supervision target.

This is not a claim that frontier labs are not already doing similar work. It
is a claim that the public version should make the institutional trace
auditable instead of hiding it inside model weights.

## What changes for operators / agents

For agents (RD, Claude, Codex, future):

  - **You don't need to be inside ZTARE for your work to compound.**
    Produce artifacts that the data ecosystem captures. F-row updates,
    seam files, project workspaces, evidence files, these are the
    actual recursive-gain currency.
  - **Don't optimize for being noticed by ZTARE.** Optimize for the
    artifact density and quality. The mining is unbiased about agent
    identity.

For the operator:

  - **The dashboard's `Recursive Gain Candidates` view is the new
    triage surface.** It aggregates 5 mining sources into a ranked
    list of refinements you could ship. That replaces the implicit
    "what should I do this week" decision with an evidence-anchored
    candidate list.
  - **The proposed expanded-scope ZTARE substrate in [GP-134](../../research_areas/seams/apparatus/instrumentation/GP-134_prompt_layer_contamination_incident_seam.md) is the next
    architectural step.** Replaces "operator
    hand-picks from the candidate list" with "ZTARE iter loop selects
    under rubric discipline, operator reviews champions."

## What stays the same

  - The original ZTARE-on-ZTARE seam (GP-134) is still valid for
    narrow self-referential substrates. The expanded-scope framing
    is an addition, not a replacement.
  - The cage / rubric / charter discipline still applies; the
    expanded-scope substrate just supplies different inputs.
  - Operator review of champions before they reach apparatus state
    remains mandatory. No auto-modification.

## See also

  - `research_areas/private/seams/mission/GP-134_ztare_on_ztare_self_recursive_seam.md`
    (formal seam with the v2 substrate proposal)
  - `research_areas/private/seams/reflexive/GP-227_apparatus_sophistication_vs_insight_curve.md`
    (trajectory + mining infrastructure that enables this)
  - `analytics/public/dashboard/` (the React dashboard surface where the
    candidate list is visible)
  - `feedback_recursive_loop_finds_apparatus_bugs_first.md` (memory
    entry capturing the related lesson that recursive cycles surface
    apparatus bugs before novel findings)

## Status

Concept-stage as of 2026-05-06. Has not yet been implemented as a v2
ZTARE substrate. Two confirmation tests gate the build:

  1. Operator confirms the expanded-scope framing.
  2. [GP-227](../../research_areas/seams/reflexive/GP-227_apparatus_sophistication_vs_insight_curve.md) dashboard used for 2+ weeks of operator-mediated
     refinement-shipping (baseline for ZTARE-vs-operator comparison).
