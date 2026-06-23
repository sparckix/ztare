---
description: "How optimization pressure corrupts measurement at each architectural layer, and the counters."
---

# Goodhart at Every Layer

> **Up:** [Documentation map](../README.md)

> **Role among the concept docs.** This doc owns the *per-layer manifestation map*: where the same optimization-pressure gradient shows up at each level of a verification stack. It is one of three non-overlapping facets of the failure axis: the canonical *structural law* of why the gradient exists is [epistemic_principles.md](epistemic_principles.md) Part I; the canonical *operational field guide* of catalogued instances is [anti_pattern_catalog.md](anti_pattern_catalog.md); this doc is the per-layer where-it-recurs map. It does not restate the law or the instance catalogue.

A catalog of how optimization pressure corrupts measurement at each
level of a verification stack, what ZTARE has caught, and what it
hasn't. The method here is to state the failure modes first, then state
what survives them.

This document replaces `is_this_a_breakthrough.md` (2026-04-15). The
original asked whether ZTARE is a breakthrough. The better question
turned out to be: *at how many layers can a specification be gamed, and
does the apparatus detect each one?*

---

## 1. The core observation

Goodhart's Law ("when a measure becomes a target, it ceases to be a
good measure") does not stop at the thesis. It recurs at every level
of a verification stack:

| Layer | What gets gamed | Who games it | Example |
|-------|----------------|-------------|---------|
| **Thesis** | The thesis optimizes a narrow proxy of the rubric | LLM mutator | Suite Omission, Strawman Comparator (*Cognitive Camouflage* taxonomy) |
| **Judge** | The judge anchors on surface features instead of substance | LLM judge | High prose quality masking analytical gaps (seattle run) |
| **Rubric** | The rubric drops charter requirements | Rubric designer (human or generator) | M-form alignment audit ([GP-105](../../research_areas/seams/reflexive/GP-105_mform_alignment_audit_seam.md)): seattle rubric had no counterfactual discipline gate, mutator scored 94 without one |
| **Evidence** | The evidence grid is too narrow to discriminate structural classes | Grid designer | Inference-type boundary check ([GP-083](../../research_areas/seams/mission/treatise/GP-083_inference_type_boundary_seam.md)): 97/100 on the wrong functional family because the grid didn't reach the regime where families disagree |
| **Parameter** | The optimizer overfits a structural parameter to the training window | curve_fit (numerical) | Ansatz-to-proof surface ([GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md)): d=0.562 instead of d=0.5 because correction terms bias the L2 minimum |
| **Apparatus** | The apparatus itself has blind spots in its search topology | Architecture | Ansatz-to-proof surface ([GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md)): grammar-guided symbolic regression could only compose additively, could not nest exp(sqrt(n)); stagnation counter stayed 0 for qualitative projects |

The pattern: each layer looks correct from the layer above it. The
thesis passes the rubric. The rubric satisfies the charter. The charter
is consistent with the evidence. And yet the whole stack can be wrong
because the failure is at a layer nobody is checking.

---

## 2. What ZTARE has caught, with receipts

### 2.1 Thesis-layer gaming (Leg 3: Adversarial Disagreement)

**What:** LLM mutators under optimization pressure produce systematic,
nameable gaming strategies. Nine top-level strategies across 453
debate logs, three mutator families, six domains.

**Receipts:** *Cognitive Camouflage* taxonomy. GPT-4o non-convergence is the
within-experiment control (it oscillates without gaming, proving the
strategies are model-specific, not algorithm artifacts).

**Gate that caught it:** Verification panel (independent judges scoring the
same candidate), meta-judge on disagreement, structural memory that
kills families.

### 2.2 Evidence-layer underdetermination (Leg 2: Compress)

**What:** A bounded evidence grid cannot discriminate between
structurally distinct functional families if the grid does not reach
the regime where those families disagree.

**Receipts:** E-GP083-CRUCIAL-01. Champion scored 97/100 with a
functional surrogate that passed visible + holdout gates. A separate
farther-tail discriminator (placed where competing structural classes
actually diverge) caught the structural error: 238% relative error,
threshold 200%.

**Gate that caught it:** Farther-tail holdout gate ([GP-046](../../research_areas/seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md)). The gate
is authored outside the candidate's claim region and tests asymptotic
survival, not window fit.

### 2.3 Parameter-layer overfitting (Leg 2: Compress)

**What:** A free continuous power-law exponent overfits in finite
evidence windows. curve_fit converges to d=0.562 instead of d=0.5
because O(1/sqrt(n)) asymptotic corrections bias the optimizer away
from the true rational exponent. Visible-window improvement: 0.002.
Farther-tail degradation: 0.053. Amplification factor: 26x.

**Receipts:** E-GP088-CAL-A01. 10 iterations, score 0 throughout.
Retroactive proof: constraining d to a discrete grid {0.25, 0.33, 0.5,
0.67, 1.0, 1.5, 2.0} and selecting by BIC recovers d=0.5, all four
gates pass.

**Gate that caught it:** Farther-tail holdout gate (same as 2.2). The
exponent grid refinement (shipped 2026-04-20 in fit_primitive.py) is
the structural fix.

### 2.4 Rubric-layer Goodhart (GP-105: M-Form Alignment Audit)

**What:** A qualitative project rubric can drop implicit charter
requirements. The mutator scores high on what the rubric measures while
systematically avoiding what the charter asked for.

**Receipts:** Seattle tech housing project. Score 94 at iteration 4
without counterfactual peer-city analysis, which the charter's core
question explicitly required. The rubric's persona mentioned
counterfactuals but the dimensions didn't gate on them.

**Gate that caught it:** GP-105 General Office audit (shipped
2026-04-20). A cross-family LLM, blinded to the rubric, audits the
thesis against the charter. If it detects a gap, it appends an
adversarial criterion at 15% weight and rebalances existing dimensions.

### 2.5 Apparatus-layer blind spots (GP-088 + stagnation bug)

**What (topology):** The symbolic-regression composition engine can only combine
primitives additively (+) or by division (/). It cannot nest functions
(e.g., exp(sqrt(n))). For targets requiring nested composition, the
engine's reachable set is topologically insufficient.

**What (stagnation):** For qualitative projects, verified_axioms_added
was set from the judge's eval output even for reverted (non-improving)
iterations. Since the judge always extracts empirical claims from any
thesis, has_novelty() returned True every iteration, preventing
stagnation from ever accumulating. The engine ran indefinitely without
pivoting.

**Receipts:** GP-088 calibration_a01 (topology). Seattle iteration
telemetry (stagnation). Both fixed 2026-04-20.

**Gate that caught it:** No gate caught it. A human reviewer caught it by
reading the telemetry. This is the layer where the apparatus itself is
the specification being gamed, and external human review is the only
current detector. GP-105b (ex-post goal-orchestration scanner) is the
proposed structural fix.

---

## 3. What ZTARE has NOT caught

- **ZTARE has not produced a scientific discovery unknown to the
  human reviewer at seal time.** All closed sandboxes are reproductions of
  known targets. The gap between "recovers a known target under
  discipline" and "discovers an unknown target" is the entire gap that
  would make the word "breakthrough" apply.

- **The apparatus has never caught its own specification failure in
  real time.** Every specification-layer fix (GP-105, stagnation bug,
  exponent grid) was diagnosed by a human reviewer reading logs
  after the fact. GP-105b proposes automated ex-post detection; it is
  unbuilt.

- **The mutator's inductive bias has not been overcome organically.**
  GP-088 run 2 showed that gpt-4.1 defaults to logarithmic forms for
  sublinear targets and never proposes n^0.5, even with 10 iterations
  of failure feedback. The exponent grid fixes the parameter if the
  topology is proposed, but the topology itself depends on the mutator.
  Seeding the thesis with topology hints violates the pre-registration
  protocol.

- **The qualitative project track is immature.** The seattle run
  exposed three bugs (stagnation stuck at 0, rubric-charter gap,
  verified_axioms_added from reverted iterations). Each is now fixed,
  but the fixes are untested on a second qualitative project. N=1.

- **The apparatus has not been shown to beat a well-prompted single
  LLM on any target where a single LLM can solve it directly.** The
  claim is only interesting on targets where a single LLM cannot.

---

## 4. The self-recursive question

The deepest version of Goodhart at every layer is: can the apparatus
detect Goodhart in its own specification?

Today the answer is no. Every specification-layer fix was human-driven.
The apparatus catches thesis-layer and evidence-layer failures
automatically (gates, structural memory, farther-tail holdout). It
catches rubric-layer failures semi-automatically (GP-105 General Office
audit). It does not catch apparatus-layer failures at all without
human inspection.

GP-105b proposes a structural fix: a cron-triggered scanner that reads
completed-run telemetry, detects systematic patterns (stagnation stuck,
pivot never fires, score oscillation), and generates Supervisor Goals
for apparatus improvement. This closes the PDCA loop: the apparatus
acts, the scanner checks, the supervisor plans, the reviewer
approves. Whether this actually works is an open question.

The philosophical limit: the scanner cannot scan itself. Recursive
self-improvement of the scanner requires human intervention, by
design (constraint 5 in the GP-105b seam: no recursive depth > 1).
Somewhere in the stack, a human must be the final verifier. *Epistemic Verification*
calls this the Peircean Residual: the claim that one verification step
stays human.

---

## 5. When to use the word "breakthrough"

Three thresholds, in escalating order:

1. **Novel reproduction under discipline.** An independent reviewer
   reproduces a closed sandbox outcome on a fresh charter fingerprint
   without maintainer-side tuning, on a target whose form the reviewer
   did not know at seal time. Currently unmet.

2. **Novel discovery on a pre-registered unknown.** The reviewer seals
   a pre-registration describing an unknown physical relationship, runs
   ZTARE, and the apparatus surfaces a functional form that independent
   review agrees is novel and correct. Partially met: sandbox_20
   recovered the Kapnistos ring polymer relaxation law (B=0.433, theory
   2/5=0.400) from blinded data, confirmed by a polymer physics
   professor. Lucky number density constant a=1.200 estimated from
   50K data points (to our knowledge unpublished). Both results
   documented in the Experimental Mathematics letter.

3. **A reproducible capability ceiling claim.** A matrix of
   mutator-model x target-difficulty x grid-discipline cells, with
   per-cell success rate as a reproducible function of apparatus design.
   Partially met by *Cognitive Camouflage* (gaming side); unmet on the discovery side.

Until threshold (1) or (2) is reached, the honest description is:
*a discipline that catches a recurring class of self-deception in
LLM-driven search, with documented failure modes and reproducible
capability datapoints on specific targets under sealed protocols.*
Useful. Important, maybe. A breakthrough, not yet.

---

## 6. How to read the repo with this framing

- `docs/FOR_RESEARCHERS.md`, the discipline
- `papers/paper1/draft.md`, the gaming taxonomy (thesis-layer Goodhart)
- `papers/paper5/draft.md`, the principles (all-layer Goodhart theory)
- `docs/concepts/evaluation_failure_cases.md`, evidence-layer lesson
- `research_areas/EXPERIMENT_TRACK_RECORD.md`, receipts for every claim
- `GP-105`, rubric-layer Goodhart
- information-yield architecture map, apparatus-layer signal flow and bug history
- `AGENTS.md`, standing reviewer discipline

*, Daniel, 2026-04-20. Rewritten from is_this_a_breakthrough.md (2026-04-15).*
