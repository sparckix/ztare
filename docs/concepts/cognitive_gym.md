---
description: "How ZTARE decides whether a model proposal has enough source-bound support to become evidence."
---

# Claim Review Constraint Stack

> **Up:** [Documentation map](../README.md)

Use this page when a model-produced claim sounds plausible and you need to
decide what, if anything, can count as evidence.

The short answer is: a model can propose. It does not get to grade its own
proposal. Another layer must own the source binding, arithmetic, holdout check,
negative evidence, and remaining weakness.

The historical filename is `cognitive_gym.md`. The public concept is simpler:
the claim-review constraint stack.

## The Decision

Ask this before accepting a model output:

```text
What part of this would I defend after another person inspects the source
files and reruns the checks?
```

The answer is usually smaller than the model output. ZTARE keeps that smaller
answer and makes the missing evidence visible.

## Worked Exercise

Suppose a model proposes a compact formula for a dataset and writes a polished
explanation.

A weak review asks whether the explanation sounds plausible. This stack asks
different questions:

1. Did deterministic code fit the parameters, or did the model guess them?
2. Did the form survive a held-out region, or only the visible window?
3. Is it rediscovering a known family while calling itself novel?
4. Did any source, theorem name, constant, or target answer leak into the
   prompt?
5. What residual remains after the best admitted form?

The promoted artifact is not "the model found a law." It is one of these
smaller states:

- admitted over this evidence window, with a named weakest point;
- demoted to a known family or calibration result;
- blocked by missing or stale evidence;
- refused because the grammar cannot express the target yet;
- routed to the next falsifier.

That is the point: turn fluent output into a reviewable state.

## The Stack

| Step | What happens | Why the model cannot own it |
|---|---|---|
| Proposal | A model proposes a structure, proof move, formula, or explanation. | Proposal quality is not evidence quality. |
| Source binding | The claim is tied to local sources, evidence files, or proof artifacts. | The model can cite friendly-looking material without proving the binding. |
| Residual check | Diagnostics inspect what the proposal fails to explain. | The model should not name away its own weakness. |
| Parameter fit | Deterministic code computes coefficients against the evidence. | Arithmetic and optimization need replayable ownership. |
| Holdout check | The proposal is tested outside the visible window where possible. | A fluent explanation can overfit the easiest slice. |
| Contamination check | The system checks whether a hint is too close to a sealed answer. | Retrieval can masquerade as construction. |
| Known-family check | The result is compared with known families before it is called novel. | Rediscovery and discovery need different labels. |
| Review artifact | The surviving state is written with evidence, non-claims, and next check. | A claim without a review trail is not durable. |

The first public lesson is separation. The proposal worker can suggest a path.
It cannot fit the evidence, choose the holdout, excuse source gaps, or decide
that a known-family match is new.

## What Each Constraint Prevents

| Failure | What goes wrong without the constraint | What the stack forces |
|---|---|---|
| Numerical hallucination | The model guesses coefficients and explains the guess. | A deterministic fitter owns the numbers. |
| Friendly citation | A source is cited but does not support the claim. | Source binding must point to inspectable files. |
| Visible-window overfit | The formula works only where it was tuned. | Holdout and farther-tail checks decide the admitted scope. |
| Answer retrieval | The prompt leaks the target constant, theorem name, or known answer. | Contamination checks block the shortcut. |
| Rediscovery inflation | A known family is presented as a new result. | The result is labeled as rediscovery when that is all the evidence supports. |
| Grammar ceiling | The current form library cannot express the target. | The result becomes a ceiling or next-extension finding, not a fake discovery. |
| Self-graded progress | The same model proposes, excuses, and promotes its own answer. | Proposal, check, and review stay separate. |

## Why Short Runs Can Still Matter

Short runs are not impressive by themselves. They matter only when the search
space is constrained and the artifacts show why alternatives failed.

When a short run succeeds, the evidence is the surviving artifact plus the
failure trail:

- which forms were tried;
- which checks rejected them;
- what held-out evidence admitted the survivor;
- what weakest point remains.

When nothing survives, that can also be useful. It may show a source gap, a
grammar ceiling, a stale evidence path, or a project setup failure. The point is
to preserve the reason instead of turning the failure into vague bad news.

## Calibration Versus Discovery

Use a different standard depending on the project:

| Project type | What a good result looks like | What should make you suspicious |
|---|---|---|
| Calibration project | The system reaches a known answer or refuses for an inspectable reason. | A perfect score with no residual or source trail. |
| Discovery project | The system narrows a live question and names what would change the answer. | A broad claim promoted from in-loop score alone. |
| Report project | The report is backed by current source/evidence receipts. | Model-written QA promotes a stale or unsupported report. |
| Proof project | The proved statement, assumptions, and proof artifact survive separate checks. | A compile is treated as enough when the statement may be wrong or vacuous. |

This distinction prevents a common mistake: treating a high score on a known
answer as proof that the system can discover unknown answers. Calibration proves
the instrument can behave. Discovery needs stronger evidence.

## What This Page Does Not Prove

This page does not prove that ZTARE discovers new laws, solves hard math
problems, or replaces domain review. It describes the control surface that
prevents a proposal from grading itself.

Evidence for a particular result must come from the project, report, proof, or
review artifact that used this stack.

## What To Do Next

For a runnable first check, start with:

```bash
make hello
```

For a real project, prepare the boundary object first:

```bash
ztare project walkthrough
ztare project intake validate --path <intake.json>
ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --brief
```

Then inspect the review trail, not the prose alone.

**Related docs:** [architecture.md](architecture.md), especially "Layer 2: The
In-Loop Validator"; [epistemic_principles.md](epistemic_principles.md) for
transferable principles; [agentic_engineering_patterns.md](agentic_engineering_patterns.md)
for pipeline patterns; [anti_pattern_catalog.md](anti_pattern_catalog.md) for
the failure taxonomy; [reflexive_engineering.md](reflexive_engineering.md) for
the repair layer.
