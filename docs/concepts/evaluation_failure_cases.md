---
description: "Three compact examples of evaluation checks that pass while missing their intent."
---

# Evaluation failure cases

> Up: [Documentation map](../README.md)

This note preserves the old `papers/case_studies/` folder contents.
Those files were small, reproducible examples of a more general lesson:

```text
A check can satisfy its formal predicate while missing the question it was
supposed to answer.
```

The details matter because this is the same failure class ZTARE is built to
catch in larger research programs.

## Rank-deficient bootstrap

*What passed:* fit a model, add small noise to the data, refit repeatedly,
and observe that the recovered parameters stay stable.

*What it missed:* two parameters entered the model only through their ratio.
The optimizer returned to the same basin every time, so the parameters looked
stable even though they were not individually identifiable.

*Better check:* vary the starting point in addition to the data. If parameters are
identifiable, reasonable starts should converge to the same values.
If only a ratio is identifiable, individual parameters scatter while the ratio
stays locked.

*Rule:* bootstrap-under-noise is a basin-stability check unless it also
exercises the flat directions of the model.

## Evidence grid underdetermination

*What passed:* a candidate formula fit visible data and generalized to a
holdout drawn from unseen values of one input variable.

*What it missed:* the holdout varied the wrong axis. Two structurally
different formulas both generalized across the held-out variable but diverged
when the other variable moved into the regime where the structural classes
separate.

*Better check:* put the discriminator in the regime where the candidate
structural classes disagree most. A statistically held-out slice is not enough.

*Rule:* a holdout tests the variation it covers. It does not automatically
test structural class.

## Evidence enrichment saturation

*What passed:* after a farther-tail gate killed one wrong champion, the
evidence was enriched and the next champion passed the same gate.

*What it missed:* enrichment changed the competitor hypothesis. The old gate
had been calibrated for one pair of formulas, while the new champion belonged
to a different structural family. The gate still asked the old question.

*Better check:* when enrichment changes the operative hypothesis pair,
redesign the discriminator for that pair.

*Rule:* discriminators are hypothesis-pair-specific. A gate that killed
candidate A does not automatically test candidate B.

## How to use these cases

Before trusting any green check, ask:

1. What did this check perturb?
2. What wrong answer could survive that perturbation?
3. Is the check testing the intended claim, or a proxy that may not cover the same ground?
4. Has the candidate changed enough that the old discriminator is obsolete?

If a wrong answer can survive easily, the check is not doing the job its label
suggests.
