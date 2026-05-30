---
description: "Worked end-to-end case studies of the apparatus on real research substrates."
---

# Case Studies

This folder contains short, self-contained demonstrations of evaluation
failures, cases where a test passed when it should have failed, and why.

Each case study has two files: a narrative (`.md`) that explains what
happened and what it means, and a reproducer (`.py`) that you can run
yourself in under a minute with only numpy and scipy.

---

## Why this exists

When you use a language model to propose a mathematical formula, a
scientific law, or a structured answer, you need some way to check
whether the answer is actually right. The obvious checks, does it
fit the data, does it generalize to a held-out set, are necessary
but not always sufficient. Each case study here shows a specific way
a reasonable-looking check can pass while the answer is structurally
wrong, and what a better check looks like.

The findings come from experiments where language models were asked to
recover unknown mathematical laws from data, under sustained adversarial
evaluation. The failures that looked most instructive and most general
were written up here as standalone examples, independent of the
experimental framework that produced them.

---

## Case studies

### 1. `rank_deficient_bootstrap.md`

**The check:** fit a model, add small noise to the data, refit 30 times,
assert the recovered parameters are stable.

**What it misses:** if two parameters enter the model only through their
ratio, the optimizer lands in the same basin every time, even though
either parameter alone is completely unconstrained. The parameters look
stable but are not identifiable.

**The fix:** vary the starting point, not the data. Parameters that are
genuinely identifiable will converge from any reasonable start.
Parameters that are not will scatter, while their identifiable combination
stays locked.

**One-line rule:** if your identifiability check does not vary the
starting point, it is a basin stability check, not an identifiability
check.

```
python rank_deficient_reproducer.py
```

---

### 2. `evidence_grid_underdetermination.md`

**The check:** fit a model to visible data, evaluate RMSE on a held-out
set drawn from unseen values of one of the input variables.

**What it misses:** two structurally different formulas can both pass
the visible fit and the holdout, if the holdout only extends the range
of one variable. The formulas may diverge sharply when the other
variable is pushed into a new regime, one that the holdout grid never
reached.

**The fix:** probe the regime where the candidate structural classes
actually disagree. For the specific case here, that means extending the
first input variable well past the training range, not just varying the
second.

**One-line rule:** if your holdout only varies what you left out of the
visible set, it tests generalization within the structural family the
data is consistent with, not whether that family is the correct one.

```
python evidence_grid_underdetermination_reproducer.py
```

---

### 3. `evidence_enrichment_saturation.md`

**The check:** after a farther-tail gate eliminates a wrong champion form,
enrich the evidence and re-run. The new champion passes the same gate.

**What it misses:** the gate was calibrated for the original hypothesis pair
(Wien vs Planck). Evidence enrichment changed the champion's structural family
(from Wien to a stretched-exponential form), changing the operative hypothesis
pair. The existing gate, designed to catch tail overestimation by Wien, does
not catch tail underestimation by the new form. The gate passes a form that is
still structurally distinct from the ground truth.

**The fix:** after any enrichment that changes the champion's structural family,
re-examine whether the existing discriminator is calibrated for the new hypothesis
pair. A discriminator for pair A is not automatically a discriminator for pair B.

**One-line rule:** when evidence enrichment changes the competitor hypothesis,
redesign the discriminator for the new pair, don't assume the old gate still
asks the right question.

```
python evidence_enrichment_saturation_reproducer.py
```

---

## The shared pattern

All three case studies have the same structure: a check satisfies the
*form* of a correctness test, it passes, the number is within threshold,
the verdict is green, while missing the *intent*. The form is "are the
results consistent under this perturbation?" The intent is "have we
actually found the right answer?"

The gap between form and intent is the thing to look for when designing
evaluation batteries. A useful diagnostic question for any check you are
about to run: *what exactly am I perturbing, and what would have to be
true for a wrong answer to survive this perturbation?*

If a wrong answer can survive easily, the check is not doing what you
think it is.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Documents**

- [When the discriminator gets outrun: evidence enrichment and hypothesis-pair specificity](evidence_enrichment_saturation.md)
- [evidence_enrichment_saturation_reproducer.py](evidence_enrichment_saturation_reproducer.py)
- [When holdout generalisation cannot discriminate structural class](evidence_grid_underdetermination.md)
- [evidence_grid_underdetermination_reproducer.py](evidence_grid_underdetermination_reproducer.py)
- [When a bootstrap-under-noise identifiability check lies to you](rank_deficient_bootstrap.md)
- [rank_deficient_reproducer.py](rank_deficient_reproducer.py)
- [validity_horizon_generalization.json](validity_horizon_generalization.json)
- [wolf_method_comparison.json](wolf_method_comparison.json)

<sub>0 sub-folder(s), 8 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
