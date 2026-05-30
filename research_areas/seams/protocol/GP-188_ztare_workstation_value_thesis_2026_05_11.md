# GP-188 ZTARE Workstation Value Thesis

> **Seam metadata** · `seam_id:` GP-188 · `track:` protocol · `status:` pre-registered / no-spend validation plan · `last_updated:` 2026-05-11


**Status:** pre-registered / no-spend validation plan  
**Created:** 2026-05-11  
**Owner:** principal + Research Director / Codex as principal-extension  
**Related:** `GP-188_research_director_primitive_compilation_boundary_seam.md`,
`ztare_mission_hypothesis_ledger_seam.md`

## Thesis

ZTARE remains valuable only if it changes the Director's search trajectory in
ways that are visible in durable artifacts: sharper hypotheses, fewer repeated
mistakes, better next-test selection, cleaner closure, and faster conversion of
negative results into named mechanisms.

The full `autoresearch_loop` is not the only form of ZTARE value. The extracted
primitive bench is also ZTARE: graph/workmap queries, primitive-surface
prechecks, Lean/CAS/dimensional gates, motion/Jaccard diagnostics, BIC-shaped
coverage checks, pattern chains, and typed endpoint queues. The heavy loop is
reserved for stable adversarial experiments. The primitive bench is the default
workstation for live theorem and frontier-method work.

The value claim is falsifiable:

- `RD + extracted ZTARE primitives` should beat `RD-only local reasoning` on
  frontier search tasks where graph/workmap/proof-gate state matters.
- `RD + full autoresearch loop` should beat `RD + extracted primitives` only
  when the candidate has a stable substrate, an independent falsification axis,
  and iteration telemetry is expected to expose frame changes that local checks
  cannot.
- If extracted primitives do not improve routing or artifact quality, they are
  ceremony. If the full loop does not beat extracted primitives on stable
  candidates, the loop boundary is too broad or the loop needs recalibration.

## Eigenquestion

When does using ZTARE as an active workstation change the Director's next move
relative to ordinary out-of-loop RD reasoning, and when is the full
`autoresearch_loop` worth its cost over the extracted primitive bench?

## Arms

### Arm A: RD-only out-of-loop

The Director may use normal repo reads, local reasoning, and direct edits. The
Director may not run the primitive-surface precheck, graph/workmap ranking,
motion/Jaccard/BIC primitives, or proof-gate queues except as ad hoc manual
inspection.

This arm estimates the baseline of smart local work without ZTARE as a
workstation.

### Arm B: RD + extracted primitive bench

The Director starts each substantial tick with the workstation precheck and uses
the relevant primitives before deciding on edits or outside prompts:

```bash
./venv/bin/python scripts/public/control/primitive_tick_surface.py --scope ns
./venv/bin/python scripts/public/projects/ns/ns_l3a_workmap.py --top 12
./venv/bin/python scripts/public/projects/ns/ns_graph.py jsonl --sink sharpTarget --top 32 --strip-plumbing
```

Other applicable local primitives may be added: Lean gates, CAS/dimensional
checks, pattern-chain audits, motion/Jaccard diagnostics, BIC-shaped
coverage/complexity checks, and source-witness checks.

This arm estimates ZTARE as a low-latency workstation assistant.

### Arm C: RD + full autoresearch loop

This arm is not authorized by this thesis. It can be run only after explicit
principal approval for a concrete substrate, command, model tier, budget cap,
iteration cap, launch window, and closure owner.

When approved, this arm estimates the value of mutator/judge iteration,
rotation telemetry, champion/revert history, and closure rows over the extracted
primitive bench.

## Matched Task Set

Use 6 to 12 matched frontier microtasks. The initial packet for each task must
be frozen before scoring. Candidate task families:

1. Identify the next theorem surface after an external proof-search answer.
2. Convert a negative GPT-5.5 response into typed missing primitives and guards.
3. Decide whether the next move should be local work, a cold-shot prompt, or a
   full loop packet.
4. Rerank an NS/L3A workmap after new theorem declarations or countermodels.
5. Produce a 100x theory-building prompt with anti-tautology and
   same-carrier guards.
6. Close a small proof-search episode into prediction rows, seam updates, and
   next-action state.

The first pass should be retrospective and no-spend: replay recent NS/L3A
segments from saved artifacts and chat-derived notes, then ask what each arm
would have done at the same point.

## Primary Metrics

Score each arm on:

1. **Next-action quality:** did the chosen next move attack the actual exposed
   obstruction?
2. **Primitive yield:** number and quality of named missing primitives, illegal
   inferences, countermodels, typed declarations, or local gates produced.
3. **Rework reduction:** did it avoid repeated prompt families, already-killed
   branches, or locally answerable questions?
4. **Artifact density:** durable files changed or created with a cold-reader
   trail: seam note, workmap delta, theorem packet, prompt packet, ledger row,
   or proof-gate result.
5. **Decision latency:** time from new evidence to a justified next move.
6. **Anti-tautology performance:** did it catch route-binding, circular
   potential, post-hoc matching, signed-to-absolute, or graph-adjacency
   smuggling before spend?
7. **Closure discipline:** was the result recorded where a cold agent can find
   it?

Use blinded panel scoring where possible: reviewers see task packet, arm output,
and artifact pointers, not which arm produced it.

## Success Criteria

The extracted primitive bench is validated if, on matched tasks, it achieves at
least one of:

- 30 percent higher next-action/artifact-quality score than RD-only at similar
  time budget;
- 30 percent lower rework rate or duplicate prompt recurrence;
- at least two cases where it finds a materially different next move that later
  survives review;
- at least two cases where it prevents a full-loop or cold-shot spend by
  resolving the question locally.

The full loop is validated only on approved stable candidates if it produces
information the extracted bench could not reasonably produce: discovered frame
changes, adversarial counterexamples, champion/revert telemetry, or closure rows
that change what to build next.

## Kill Conditions

Kill or demote the thesis if:

- extracted primitives mostly reproduce RD-only conclusions without improving
  timing, artifact quality, or error avoidance;
- graph/workmap outputs are consulted but do not affect next actions;
- the full loop wins only by consuming more time/money without producing
  durable new failure mechanisms;
- evaluation rewards longer prose or more files instead of better decisions;
- the same-arm scorer knows the arm identity and outcome preferences dominate;
- retrospective replay is contaminated by knowing what later happened and no
  fresh prospective task confirms the effect.

## NS Arc Reflection

The NS/L3A arc is the first calibration sample.

What worked:

- Narrow external prompts produced high-value negative information when they
  targeted one primitive and asked for proof or obstruction.
- The prediction ledger improved calibration by forcing explicit expected
  outcomes before answers returned.
- Typed Lean-facing declarations and graph/workmap rankings kept the frontier
  from becoming pure route narration.
- The local primitive patch to damp closed algebra facts in the L3A workmap
  made the open PDE obligations visible again.

Blindspots observed:

- I leaned too long on external GPT-5.5 answers before converting them into
  local typed primitives, guards, workmap deltas, and ledger rows.
- I treated "local work" and "autoresearch loop" too much as a binary. The
  correct intermediate object is ZTARE as a callable workstation.
- I used the graph as a map, but too late as a preflight invariant. The graph
  should have been part of every substantial tick from the start.
- I sometimes generated cold-shot candidates before writing a primitive
  insufficiency receipt.
- Swarm/debate was useful for pressure, but it risks becoming substitute labor
  unless every panel output is bound to a patch, guard, prompt, or theorem
  packet.
- I underused the already-extracted ZTARE primitives because I was acting like a
  standalone proof-search agent rather than a Director operating a workstation.

## Immediate No-Spend Validation

1. Run a retrospective NS/L3A segment audit on 6 recent decision points.
2. For each point, classify the arm that actually dominated the decision:
   RD-only, extracted primitive bench, or outside cold-shot.
3. Record what primitive precheck would have surfaced at that point.
4. Mark whether the primitive would have changed the next move.
5. Count avoidable delays, repeated prompt families, and missed local updates.
6. If the audit supports the thesis, convert the precheck into a default RD tick
   habit. If not, repair or demote the extracted primitive bench.

No `make experiment-loop` or raw `make loop` is authorized by this thesis.

## Initial Retrospective Sample: NS/L3A Arc

**Status:** preliminary, qualitative. This is not the final validation audit.
It identifies candidate decision points to replay with a frozen packet later.

| Decision point | Actual dominant mode | Primitive bench likely effect | Preliminary read |
|---|---|---|---|
| Signed DR / raw Mobius bridge response | Outside cold-shot then local discussion | Workmap + typed endpoint queue would have forced immediate separation between signed projected flux and absolute p=3 mass | Would reduce delay from answer to local theorem declarations |
| Raw local-energy carrier vs DR commutator response | Outside cold-shot | PDE estimate-craft + source-witness check would have made `mollified DR carrier` the local object earlier | Would reduce repeated attempts to project from unmollified `K(F)` |
| Normalized CKN excess to codim-four packing response | Outside cold-shot | L3A workmap would have surfaced `CKNExcessCarlesonPacking` and `RadiusChargingBadScaleMeasure` as open PDE nodes | Would help rerank, not solve |
| Radius charging / excess-drop responses | Outside cold-shot plus local graph work | Primitive bench would have caught the `r^2` vs `r` mass-renormalization trap as a recurring guard | Would reduce prompt repetition across equivalent no-go variants |
| De Giorgi production lane responses | Outside cold-shot | Dimensional endpoint gate would have flagged the `q > 5/2` threshold before more broad production prompts | Would likely prevent one redundant cold-shot family |
| Eventized beta / same-tree incidence response | Outside cold-shot plus local workmap patch | Graph/workmap tick plus anti-tautology pattern would have separated algebraic adapter from same-carrier incidence theorem earlier | Strong positive sample for extracted primitive value |

Preliminary diagnosis:

- The external cold shots were useful because they attacked narrow PDE
  primitives and returned sharp no-go mechanisms.
- The delay came after the answers: conversion into local graph/workmap state,
  typed missing primitives, prediction-ledger rows, and prompt guards was not
  automatic enough.
- The extracted primitive bench appears most valuable as a **post-answer
  compressor** and **pre-cold-shot filter**, not as a replacement for every
  outside theory-building prompt.
- The full autoresearch loop still has a role, but this NS arc has not yet
  produced a stable spend-bearing substrate. The current objects are theorem
  surfaces and prompt packets, so the primitive bench is the right default.

The next validation step is to replay these six points with frozen evidence
packets and score Arm A vs Arm B. Arm C remains approval-gated.
