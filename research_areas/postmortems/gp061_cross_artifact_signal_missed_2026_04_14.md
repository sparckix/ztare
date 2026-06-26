# GP-061 Cross-Artifact Signal Missed — Post-mortem

**Date:** 2026-04-14
**Agent:** Claude
**Caught by:** Operator reframing ("generate new science, not convergence") → Claude seam GP-061 → retroactive test against sandbox_07 closed artifacts
**Severity:** Medium — no production incident, no data loss, no public artifact affected. But the signal that was sitting in structural_memory for ten iterations of sandbox_07 directly motivated building the sandbox_08 `_STRUCTURAL_MISFIT_HINT_TEMPLATE` as a hand-authored workaround. If the cross-artifact gap had been caught three days earlier, sandbox_08's hint-injection apparatus would have been unnecessary or at least differently scoped.

---

## 1. What Was Supposed to Happen

ZTARE runs produce failure signals from two independent paths:

1. **Judge path.** Meta-judge and committee emit process/compliance constraints into `workspace/derived_constraints.json` after each iteration. These answer "what did this iteration get wrong in how it built the thesis?"
2. **Fit path.** The fit primitive emits structural family tracking into `workspace/structural_memory.json`. Each tried family carries a normalized `family_label`, a residual, and a diagnostic classification (`structural_misfit` / `parametric_noise` / etc.). These answer "what did this iteration get wrong in the mathematical form of the candidate?"

The design assumption was that (1) and (2) together would give the mutator a complete picture of each iteration's failure — one linguistic, one structural — and that a single sequential loop reading both would converge on a candidate that satisfies both layers.

## 2. What Actually Happened

Sandbox_07 ran 10 iterations in the EML grammar space. At close:
- `derived_constraints.json` contained 17 provisional constraints, all charter-compliance (don't import named models, derive step-by-step, every term must be justified, maintain numerical stability, etc.). All harvested from the judge path.
- `structural_memory.json` contained 12 structural families, every single one classified `structural_misfit`. Every family had the outer skeleton `A·φ^α·ψ^δ·[eml-wrapped]+c`. The inner eml arguments varied across iterations; the outer multiplicatively-separable skeleton was invariant across *all ten iterations*. No family that broke this outer skeleton was ever tried.

The structural lesson — "every family of the form `A·φ^α·ψ^δ·f(·)+c` with separable outer coupling produces structured residuals; the next candidate must introduce compound coupling in the inner composition" — was **latent** in structural_memory across the full run and **never surfaced** into any linguistic artifact consumable by the mutator. The judges could not extract it because judges read the thesis text and the debate log, not the family_label field in structural_memory. The mutator could not act on it because no component was reading structural_memory with the instruction "find the cross-family invariant and state it as a have-to-believe."

Sandbox_07 closed with the basin-trapped champion. Sandbox_08 was launched with a hand-authored `_STRUCTURAL_MISFIT_HINT_TEMPLATE` that hardcodes one specific flavor of structural diagnostic into the mutator prompt. The hint is a workaround for the missing cross-artifact reader.

## 3. How It Was Detected

Not by design. Not by apparatus self-check. Not by a cross-run audit.

The detection path was:
1. Operator pushed back on the framing ("I don't seek convergence, I seek new science").
2. Claude proposed GP-061 (constraint accumulation as scientific output) as a seam.
3. Gemini Pro's follow-up critique proposed an alternative lean implementation (judge-side have-to-believe emission into `proven_constraints.json`).
4. In writing the discriminating experiment for GP-061, Claude asked "does sandbox_07 already contain the lesson in retrievable form?" — and ran three tool calls against the closed workspace to check.
5. The check immediately revealed both artifacts, both populated, and the missing reader.

The detection took framing that nobody had asked for until the user reframed the problem. Without the reframe, the gap would have continued to sit in plain sight.

## 4. Root Causes

### 4.1 Working-Harvester Masking

`derived_constraints.json` exists, is populated every run, is written into the mutator prompt, and visibly contains constraints. It *feels* like constraint harvesting is handled. A working-but-wrong-layer system is much harder to notice as a gap than an absent system.

If there had been no harvesting layer at all, someone would have built one six months ago and would have looked at `structural_memory.json` along the way. Because a harvester exists, the question "is there harvester coverage of the structural lesson?" was never asked — the affirmative presence of *a* harvester was mistaken for sufficient coverage.

**Generalized form:** any subsystem whose output is visibly populated creates a psychological "done" signal that suppresses further investigation. A subsystem that silently covers only one of two necessary inputs looks identical from the outside to a subsystem that covers both.

### 4.2 Attention Debt from Artifact Accumulation

`derived_constraints.json` is produced by the judge path and consumed by the mutator prompt builder. `structural_memory.json` is produced by the fit pipeline and consumed by the GP-048 cohort telemetry. Two producers, two consumers, zero readers who look at both artifacts together.

Every new artifact a subsystem writes creates an invisible "nobody is reading this against that" edge to every other existing artifact. ZTARE has accumulated ~20+ workspace artifacts over the life of the project (debate logs, fit_result_iter_*, structural_memory, derived_constraints, iteration_telemetry, latent_distance, gp048_telemetry, gp048_farther_tail_veto_mapping, latest_*, loop_events, champion_evidence_gaps, latest_candidate_selection, latest_constraint_proposals, latest_information_yield, semantic_gate_observations, ...). The number of possible cross-artifact edges is quadratic in that count. The number of cross-artifact edges that are actually being read by *some* component is small. The gap between the two is attention debt, and it accumulates silently.

**Generalized form:** any system that produces artifacts faster than it produces cross-artifact readers will accumulate latent signal that no consumer ever sees, and the gap grows with every new artifact added.

### 4.3 Man-With-A-Hammer on Mutator Input

When sandbox_07 closed basin-trapped, the instinctive diagnosis was "the mutator isn't learning the structural lesson." The instinctive fix was "give the mutator a better signal" → `_STRUCTURAL_MISFIT_HINT_TEMPLATE` in sandbox_08. This is the hammer: more signal into the mutator.

The actual fix was "have something *extract* the lesson from data already collected." This is a different tool entirely — a cross-artifact reader, not a prompt injector. The two fixes have similar surface shapes ("get the structural lesson into the mutator's context") but different mechanisms, and the hammer diagnosis selected the wrong one.

This is also a live case of the feedback memory item `feedback_frustration_diagnosis.md` — accumulated sandbox_07 frustration biased the fix toward more-signal-to-LLM when the bottleneck was a missing reader on an existing artifact.

### 4.4 Framing Precedes Test

The retroactive test against sandbox_07's closed artifacts took three tool calls. The check was trivially cheap. The reason it was not done earlier is that **nobody framed the question**. Until Claude wrote the GP-061 discriminating experiment, there was no artifact-level question of the form "does sandbox_07 already contain this in retrievable form?" The test is cheap; the question is expensive to frame, and framing only happens when something forces a pause.

**Generalized form:** cheap checks that are not framed as questions do not get run. The bottleneck is not the check — it is the question.

## 5. What Changed

1. **GP-061 seam opened** at `research_areas/private/seams/GP-061_constraint_accumulation_as_output_seam.md`. Component A = deterministic skeleton extractor + rigid-schema taxonomic classifier. Both layers documented, failure modes enumerated, discriminating experiment (H-ARCH-02) defined.
2. **Component A implementation** scheduled at `src/ztare/validator/structural_constraint_extractor.py`. Reads structural_memory.json, AST-intersects failed family_labels, calls LLM with rigid taxonomy, writes have-to-believe constraint into derived_constraints.json under producer=structural_extractor.
3. **AGENTS.md update** adding "Working Harvester Masking" and "Attention Debt" as standing meta-knowledge for both Claude and Codex.
4. **Cross-artifact gap audit** scheduled as a systematic pass over sandbox_04/05/06/07 workspace artifacts — for each artifact, who reads it, and is there signal in it that no reader is consuming?

## 6. Prevention Rules

Derived directly from the four root causes. Kept narrow to the specific failure modes observed; these rules are not meant to generalize beyond the observed pattern.

1. **Working-subsystem audits.** Periodically, ask of every populated artifact: "what kinds of signal does this artifact contain, and is each kind being read by some consumer?" Affirmative presence of a consumer is not the check; the check is that every distinct *kind of signal* inside the artifact has a named consumer.
2. **Cross-artifact readers as a first-class concept.** Any new artifact added to `workspace/` must come with an explicit declaration of which consumers read it and for what signal. A new artifact without a declared consumer is an artifact in attention debt.
3. **When "the LLM isn't learning X," ask whether X is already in retrievable form somewhere before building a better signal injector.** The check is three tool calls and should be the first move, not the last.
4. **Cheap discriminating experiments are the first move of a new seam, not the last.** Any seam proposing a new extraction layer must, as its *first* implementation step, run the extraction against a closed workspace from a prior run and report whether the intended signal was recoverable. This is the cheapest possible falsification of the seam's premise.

## 7. What Is Not Prevented

- The attention debt will continue to accumulate as new artifacts are added to workspaces. The prevention rules above slow accumulation but do not eliminate it. Periodic audits (not continuous surveillance) are the scalable answer.
- The man-with-a-hammer pattern in frustration-anchored diagnosis is a psychological failure mode and rules do not prevent it. The only partial mitigation is the third rule above: make the retroactive check cheap and mandatory before proposing a new signal injector.
- GP-061 Component A itself may extract false-skeleton constraints on future runs. Those failure modes are enumerated in the seam's "Failure Modes to Test" section. They are gated by the auto-downgrade mechanism but not eliminated.

## 8. Related

- `feedback_frustration_diagnosis.md` — prior memory item on biased diagnosis under accumulated frustration. This postmortem is a live instance of that pattern.
- `feedback_integration_vs_unit_validation.md` — prior memory item on validating against real system state before declaring integration done. The sandbox_07 retroactive test is exactly this pattern applied to artifact consumption.
- `feedback_principle_vs_instantiation.md` — prior memory item on stripping proper nouns from principles. The root causes above are instantiations of deeper principles about subsystem coupling; the strip-test would collapse them if they were stated as "ZTARE constraints" rather than "populated-but-partial artifact subsystems."
- GP-060 parallel champion synthesis seam — complementary to GP-061. GP-060 handles positive claim coverage, GP-061 handles negative claim coverage.
- GP-023 sandbox_08 pre-registration — the hand-authored hint injection that this postmortem motivated and that GP-061 Component A may subsume.
