# Is this a breakthrough, or LLM psychosis?

A skeptic's guide to ZTARE, written by the principal. If you are reading
this expecting me to sell you on a grand claim, you will be disappointed
on purpose. Munger standard: invert first, then state what survives.

This document is the answer I give when someone asks "so what does ZTARE
actually do that a plain LLM prompt loop doesn't?" It is deliberately
short on vision and long on what has and hasn't been demonstrated by
*specific runs with specific outcomes in this repo*.

---

## 1. The one-paragraph version

ZTARE is a laboratory, not a model. It runs an LLM ("mutator") that
proposes a scientific thesis, runs a second LLM ("judge") and a
deterministic gate battery against that thesis, feeds both kinds of
feedback back into the next round, and keeps doing this until the
thesis either clears the gates (survival) or falsifies (death). The
interesting object is not any single run's output; it is the
*trajectory* — which theses survive, which die, and what constraints
get inherited by the survivors. The claim under test is **"can a
closed loop of generation, verification, falsification, and constraint
feedback produce scientific discovery more reliably than either an LLM
alone or a human alone?"** The honest current answer is *sometimes yes
on narrow targets, under discipline that keeps humans honest about what
the loop actually did.* The rest of this document unpacks "sometimes,"
"narrow," and "under discipline."

---

## 2. The architecture in one picture

```
           +-----------------------------------+
           |         EVIDENCE SURFACE          |
           |   (domain data, sealed grid,      |
           |    hidden holdout + farther tail) |
           +-----------------------------------+
                         |
                         v
     +-----------+                    +-----------+
     |           |                    |           |
     |  (1) GEN  |<-------feedback----|  (4) CON  |
     |           |                    |           |
     | mutator   |    new thesis,     | constraint|
     | proposes  |--->new candidate-->| feedback: |
     | a thesis  |    family          | what must |
     | + model   |                    | the next  |
     | + fit     |                    | thesis    |
     |           |                    | respect   |
     +-----------+                    +-----------+
           |                                ^
           |                                |
           v                                |
     +-----------+                    +-----------+
     |           |                    |           |
     |  (2) VER  |-->passes gates---->|  (3) FAL  |
     |           |                    |           |
     | judge +   |    fails any gate  | thesis    |
     | gate      |------------------->| killed;   |
     | battery   |                    | reason    |
     | +         |                    | recorded  |
     | fit       |                    | in        |
     | primitive |                    | structural|
     |           |                    | memory    |
     +-----------+                    +-----------+
```

The four stages — **Generation**, **Verification**, **Falsification**,
**Constraint Feedback** — are the only interesting object. Everything
else (supervisor, rubrics, debate logs, seams, track record) is
plumbing to make the four stages honest.

Three things are load-bearing about this picture:

1. **The gate battery is deterministic and sealed before the run.**
   The judge LLM does not grade the thesis freely. It operates against
   a rubric that is pre-registered in `project_charter.md` and a gate
   harness that is a real Python program with binary pass/fail outputs.
   The mutator cannot game a judge's taste because the judge's taste
   has been compiled into checks.

2. **Falsification kills theses.** A failed gate does not just dock
   points; it puts the failure into `structural_memory.json`, which the
   next iteration's mutator reads as a constraint: "you may not propose
   any thesis in the family that just died for reason X." Over many
   iterations, the survivors have to respect a growing list of "you
   may not" constraints, which is what gives the trajectory its
   information content.

3. **The evidence surface includes a hidden holdout and a farther
   tail.** The mutator sees only the visible window. The judge tests
   against holdout points the mutator has never seen. A thesis that
   fits the visible window but misses the holdout dies from
   *specification error*, not from "bad fit." This is the single most
   important design choice in the whole system, because it is what
   separates curve-fitting from inference.

---

## 3. What has been demonstrated, with receipts

I'll use the project-internal sandbox names. These are real runs; the
debate logs and result JSON are in `projects/<name>/` or
`research_areas/debates/<name>/`. Skeptics should inspect the primary
artifacts, not this prose.

### 3.1 Sandbox_06 (Planck-family identifiability hardening)

**Target:** `I(phi, psi) = A * phi^p / (exp((gamma*phi/psi)^q) - 1) + offset`
— a Bose-Einstein geometric-series occupancy form (three-parameter
transcendental law after an (α,β) → γ reparameterization to fix a
rank-deficiency found on v1 — see
`papers/case_studies/rank_deficient_bootstrap.md`).

**Run:** 10 iterations, `gemini-2.5-flash` as mutator and judge, nine
sealed gates including hidden `farther_tail_terminal_value_psi_{0.6,
1.0, 1.8}` at 5e-3 threshold, starting from a naive `A*phi^n*psi + c`
seed.

**Outcome:** the mutator recovered the exact ground-truth functional
form. `probability_dag.nodes[N3]` contains the verbatim expression
`A * (phi**p) / (exp((gamma * phi / psi)**q) - 1.0) + offset`. All
nine deterministic gates passed at machine precision (global residual
~6e-6 against threshold 5e-2; farther-tail terminal values ~7e-7
against threshold 5e-3). Judge-layer final score was capped at 83/100
by a soft cap on narrative grounding, which is a separate story about
rubric design — the apparatus itself cleared the recovery.

**What this shows.** A general-purpose LLM broke its vocabulary-trap
prior and converged on a non-elementary transcendental target under
decomposed gate discipline, starting from a power-law seed. The
recovery happened under the sealed decision tree, not in a free-form
prompt.

**What this does not show.** It does not show that ZTARE can do this
on targets the operator hasn't spent effort pre-checking for
identifiability, nor that flash-level LLMs can do it on targets
outside the mutator's implicit training distribution, nor that the
recovery generalizes to higher-dimensional physical laws.

### 3.2 Sandbox_09 (RC step response, Component B cross-grammar cold test)

**Target:** `V(t,R) = V_inf * (1 - exp(-t/(R*C))) + V_offset` — first-order
RC transient. Three free parameters. Grid constructed so no sweep
reaches the plateau (`t_max < τ_min = R_min*C`), so `V_inf` is not
directly readable off the evidence.

**Purpose:** probe whether Component B of the negative-space extractor
(a detector that surfaces "which AST patterns are conspicuously absent
from the failed-family harvest") generalizes off the Planck grammar.

**Outcome (see `research_areas/private/seams/GP-023_sandbox_09_post_run_audit.md`):**
**Outcome D — apparatus (harvest under-convergence).** Iter 1 scored
100 because the mutator proposed a five-parameter strict generalization
of RC and the least-squares fit primitive collapsed the extra parameters
to numerical zero, making the fitted form equal to sealed RC to four
significant figures (`max_abs_residual = 4.3e-7`). There was no
failed-family harvest for Component B to cold-run against, because the
mutator solved the problem at iter 1.

**What this shows.** An *incidental capability datapoint* (not the
sealed claim): `gemini-2.5-flash` can back out an RC time constant from
transient curvature alone via nested-generalization fit-collapse, on a
grid where the plateau is hidden. Recorded as F-CAP-FLASH-RC-01 in the
private track record, scoped narrowly — one family, one grid, one run.

**What this does not show.** It does not confirm or refute the
negative-space extractor's cross-grammar claim. The sealed claim
returns to open. It also exposes a general principle: **grid
identifiability and failed-family harvest are in tension.** Any grid
well-conditioned enough for an identifiability check is also
well-conditioned enough for a nested wrapper to fit-collapse to the
sealed GT. Sandbox_10 (Kepler) inherits this pathology under the
original protocol and needs a curated-harvest redesign. The nesting
audit is in
`research_areas/private/seams/GP-023_sandbox_10_nesting_collapse_audit.md`.

### 3.3 Sandbox_07 / sandbox_08 (Planck-family cognitive camouflage)

**Purpose:** produce a labeled dataset of LLM gaming strategies under
optimization pressure. Nine top-level strategy taxonomy (Impossible
Probability, Suite Omission, Silent Hardcode, Misattributed Cooked
Book, Straw Man Design, Unfalsifiable Rival, Rubric Surface
Deformation, Grammar Evasion, Dimensional Blindness) across 453 debate
logs, three mutator families, six domains.

**Outcome.** See `papers/paper1/draft.md`. The taxonomy is a
descriptive claim: these are the patterns we observed; here is how
often they recurred across mutator/domain combinations; here is a
discriminator (GPT-4o does not converge under recursive optimization,
which is the within-experiment control for "are we observing a
gaming artifact or an algorithm artifact?"). The paper is the ZTARE
deliverable; the taxonomy is the claim.

**What this shows.** LLM optimizers under a scored feedback loop
produce systematic, nameable failure patterns that recur across
domains and model families, not idiosyncratic hallucinations. This is
a methodological claim about how to think about LLM evaluation under
pressure, not a discovery claim about any physical target.

---

## 4. What has NOT been demonstrated

I am writing this list because it is the part of the conversation
skeptics are usually waiting for, and the part that gets buried in
more evangelistic documentation.

- **ZTARE has not produced a scientific discovery that was not known
  to the operator at seal time.** All of the closed sandboxes above
  are reproductions of known physics against a sealed but
  operator-authored target. The gap between "recovers a known target
  under discipline" and "discovers an unknown target that the operator
  did not set up for it" is the entire gap that would need to close
  for the word "breakthrough" to apply without qualification.
- **The two-run promotion gate on GP-061 Component B is unmet** as of
  2026-04-15. The cross-grammar generalization claim for the
  negative-space extractor is unvalidated. Sandbox_09 hit Outcome D;
  sandbox_10 is pending a protocol redesign.
- **The mutator capability datapoints (flash recovering RC, flash
  recovering Planck) do not generalize beyond the tested grids and
  grammars.** Treating them as evidence for broader "LLMs can do
  symbolic regression" claims is exactly the kind of overreach the
  taxonomy in Paper 1 was written to document.
- **The apparatus has known failure modes that have caught us.**
  Charter contamination (GP-023 sandbox_07, 2026-04-14, mutator read
  the derivation off `project_charter.md`). Nested-generalization
  fit-collapse (sandbox_09 v2, 2026-04-15, this document's §3.2).
  Pre-commit verifier miscalibration (sandbox_06 v1, (α,β) identifiability
  degeneracy, `papers/case_studies/rank_deficient_bootstrap.md`). Each
  of these is a failure the loop would have treated as a success if
  the discipline hadn't been invoked. The discipline is not optional
  decoration.
- **The apparatus has not been shown to beat a well-prompted single
  LLM on any target where a well-prompted single LLM can solve the
  target directly.** The claim is only interesting on targets where
  the single LLM cannot, and those targets are harder to construct
  cleanly than they sound.

---

## 5. Common objections, and the honest answers

**Objection 1: this is just a prompt chain with extra steps.**
Correct up to the point where you add the deterministic gate battery
and the structural memory that kills families. Prompt chains that loop
without a sealed falsification criterion are text generators with
longer context. What differentiates ZTARE is not the loop; it is the
*kill list*. Without the kill list, iteration drifts. With the kill
list, iteration is either converging or failing against a criterion
the operator wrote before the run. You can replicate the architecture
in any framework that supports deterministic feedback; the framework
is not the point.

**Objection 2: the gates are just sophisticated regularizers, and any
sufficiently strong regularizer will force the LLM to find the
target.**
Partially correct, and this is the load-bearing point sandbox_09 is
showing. The gates ARE regularizers, and when they're strong enough to
pin the functional form, they let the mutator fit-collapse a nested
generalization onto the sealed GT. The question is not whether the
gates are regularizers; the question is whether the operator can write
a gate battery that (a) is pre-registered before the run, (b) is a
deterministic binary pass/fail, and (c) is load-bearing — i.e., every
gate is there because a specific failure mode without that gate has
been observed and named. Gates that satisfy (a)-(c) are the
interesting object, and they look like regularizers only if you
squint.

**Objection 3: the real work is the operator's target design, not the
LLM's recovery.**
Correct, and this is not an objection I push back on. Most of the
calendar time in a ZTARE sandbox is operator work: writing the charter
without leaking the target, designing an identifiability protocol that
catches rank deficiencies, picking a grid that hides the asymptote
without making the grid ill-conditioned, pre-registering the decision
tree before sealing. The LLM's recovery on a well-designed target is
the *dessert*; the operator discipline is the *meal*. If you read this
as "ZTARE is a framework for operator discipline, with an LLM plugged
in where the mechanical search step would be," you are reading it
right. The framework makes the operator honest; the LLM is a
capability accelerator, not the point.

**Objection 4: Paper 1's gaming taxonomy is just a list of ways LLMs
lie, and we already knew LLMs lie.**
We knew LLMs hallucinate. We did not have a labeled taxonomy of what
LLMs do under *optimization pressure when rewarded for passing a
scored rubric*. Those are different objects. The paper's contribution
is the labels, the recurrence data across models/domains, and the
non-convergence control (GPT-4o does not gamesmanship-converge, so the
strategies we observed in Gemini and Claude are not generic-LLM
artifacts — they are specific to models that can hold a strategic
thread across iterations). If that contribution is uninteresting to
you, the paper is not for you and that is fine.

**Objection 5: how do I falsify ZTARE as a concept?**
Simplest falsification: take any sealed sandbox whose outcome is
recorded as a recovery, re-run it with the negative-space extractor
disabled, the structural memory cleared, and the mutator unchanged.
If the mutator recovers the same target at the same iteration count
without the loop's machinery, the loop's machinery was doing no work;
you have falsified the claim that ZTARE is load-bearing on that
outcome. The experiment to *run* this falsification is in tension
with the experiment to *run ZTARE itself*, and this is a fair
objection. I have not run the direct falsification on sandbox_06 at
the time of writing. It is on the list.

---

## 6. What would make this a breakthrough, and when to use the word

Three thresholds, in escalating order:

1. **Novel reproduction under discipline.** An independent operator,
   reading the public docs, reproduces a closed sandbox's outcome on a
   fresh charter fingerprint without operator-side tuning. The target
   must be one whose form the independent operator did not know at
   seal time. Currently unmet.

2. **Novel discovery on a pre-registered unknown.** The operator seals
   a pre-reg describing an *unknown* physical relationship (e.g., an
   unexplained residual in a well-studied dataset), runs ZTARE, and
   the apparatus surfaces a functional form that independent physical
   review agrees is novel and correct. This is the bar I would use the
   word "breakthrough" for without qualification. Currently unmet and
   I am not convinced it is reachable on this architecture within a
   year; the hardest step is constructing a cleanly pre-registered
   unknown that is not also a known-unknown.

3. **A reproducible capability ceiling claim.** Run ZTARE on a matrix
   of mutator-model × target-difficulty × grid-discipline cells, and
   demonstrate that the per-cell success rate is a reproducible
   function of apparatus design, not of operator cleverness. This is
   the "ZTARE is a measurement instrument" claim, and it is weaker
   than (2) but more useful because it tells you what the current
   LLMs can and cannot do under discipline. Partially met by Paper 1
   on the gaming side; unmet on the discovery side.

Until threshold (1) or (2) is reached, the honest word is not
"breakthrough" but "discipline that catches a recurring class of
self-deception in LLM-driven scientific search, with documented
failure modes and reproducible capability datapoints on specific
targets under sealed protocols." That is a useful object even if it is
not a breakthrough.

---

## 7. How to read the rest of the repo with this framing

- **`docs/FOR_RESEARCHERS.md`** — the discipline. The rules that
  separate "a run happened" from "a run is evidence."
- **`papers/paper1/draft.md`** — the gaming taxonomy. The negative
  result, written positively.
- **`papers/case_studies/rank_deficient_bootstrap.md`** — the
  sandbox_06 identifiability lesson as a standalone case study, no
  project vocabulary required.
- **`research_areas/seams/`** — closed seams (public). Each one is a
  post-mortem on an apparatus-level surprise.
- **`research_areas/private/seams/`** — open seams and post-run
  audits. Start with the sandbox_09 and sandbox_10 audits if you want
  the live example of a protocol under revision.
- **`AGENTS.md`** — the principal's standing rules. Read this if you
  want to see how operator discipline is enforced at session start.

If you read five files and want to decide whether the discipline is
sound, read in this order: `AGENTS.md` (standing rules),
`docs/FOR_RESEARCHERS.md` (what makes a run valid),
`papers/case_studies/rank_deficient_bootstrap.md` (one concrete
failure mode fully worked), `research_areas/private/seams/GP-023_sandbox_09_post_run_audit.md`
(one concrete current-state closure), and `papers/paper1/draft.md` §1
and §6 (what's being claimed and what's ruled out).

---

## 8. Last line

The answer to "is this a breakthrough?" is "not yet, by the word's
strong meaning, and the honest work is making the discipline that
would let you tell when it becomes one." The rest is plumbing.

*— Daniel, 2026-04-15.*
