# GP-103 — The Topology Induction Gap (DFDO Sandbox_18)

> **Seam metadata** · `seam_id:` GP-103 · `track:` engine · `status:` Active - opened 2026-04-19 · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

## Status

Active — opened 2026-04-19

## ID

GP-103

## Eigenquestion

Why did the engine find the existence proof (Component D surrogate, 10 params, score 95) but fail to propose the two-regime additive composite (5-6 params) that is the minimal gate-passing form, and what architectural primitive is missing?

**Note (revised 2026-04-19 post-backtest)**: Original eigenquestion assumed the 3-param log-substitution `a·exp(-p·log(1+b·u))` was the compression target. Feynman backtest refuted this. The target is a 5-6 param two-regime additive composite. This is a topology induction failure, not a compression failure.

---

## What Happened: Telemetry Summary

| Phase | Iters | What occurred |
|-------|-------|---------------|
| LLM warm-prior basin | 1–6 | Stretched-exp + additive log/rational corrections; all score 0; farther-tail gate fails |
| Component D sweep | 7 | 100+ ratio-of-exponential candidates generated in one beam; 121 families in structural memory by end |
| Surrogate found | 10 | `((a_a·exp(a_b·u) + a_c·exp(a_d·u)) / (b_a·exp(b_b·u) + b_c·exp(b_d·u))) / (d2_a/u + d2_b)`, 10 params, score 95, both gates pass |
| One compression attempt | 11 | `a·exp(-b·u) / (c·u^p + 1)`, 4 params — **fails visible gate** (max_res=0.0956 > 0.08) |
| Attractor lock | 12–20 | All iters: ratio-of-exp variants, 12–13 params; scores oscillate 60/95/95; two-regime composite **never appears** |

**GP-048 Primitive Progression:**

| Iter | New primitives vs run | Expression class | Gate result |
|------|----------------------|-----------------|-------------|
| 1 | exp_neg, power | `exp(-b·u^p)` | Score 0 (farther-tail) |
| 2 | additive, log, rational | `exp(-b·u^p·log(u)^q) + 1/u...` | Score 0 |
| 3 | — | `exp(-b·u^p·log(u)^q)` | Score 0 |
| 4 | — | `a/(u+b·log(u)^p)^q` | Score 0 |
| 5 | — | `a·exp(-b·log(u)^p)` | Score 0 |
| 6 | — | `a·exp(-b·(log u)^p)` TED=0 | Score 0 |
| 7 | exp_pos, rational_with_offset | `exp(-b/log(u)^p+c)` | Score 0 |
| 8 | sigmoid | Component D beam starts | Score 0 |
| 10 | — | Ratio-of-exp champion | Score 95 ✅ |
| 11 | — | `exp(-B·u)/(C·u^D+1)` | Score 0 (gate fail) |
| 12–20 | **zero new primitives** | Ratio-of-exp variants | 60/95/60/95... |

**The sharpest single fact:** After iter 7, `new_primitives_vs_run = []` for every remaining iteration. The engine spent 13 of 20 iterations recombining the same 7 primitives.

**Key absences:**
- The two-regime composite `a·exp(-b·u^p) + c·exp(-q·log(1+d·u))` — 6 params, fully grammar-legal, passes all three gates — was never proposed.
- The engine tried each component in isolation (`exp(-b·u^p)` at iter 1, `exp(-b·log(u)^p)` at iters 5–6) and as part of the ratio-of-exp surrogate, but never as an additive two-regime sum.
- The additive two-regime sum is the **different topology** — not a simplification of the 10-param form, but a structurally distinct family.

**Closest approach to the GT topology:**  
Iter 5–6: `a·exp(-b·log(u)^p)` — log INSIDE exp(-...). This is the correct primitive family. The specific GT form `exp(-p·log(1+b·u))` differs only in using `log(1+b·u)` instead of `log(u)^p`. Max_res = 0.1233, failing the visible gate. The engine explored the right class and got a gate rejection. The structural memory recorded "log inside exp = failed" without granularity to distinguish `log(u)` from `log(1+b·u)`.

**What never appeared:**  
`exp(-p·log(1+b·u))` — the additive-offset-in-log-argument form. Specifically, the `1+b·u` additive offset INSIDE the log argument was never tried. More importantly: the additive two-regime composite `exp(-b·u^p) + exp(-q·log(1+d·u))` was never tried despite the engine having explored both components separately.

---

## Why the Topology Was Never Proposed: Root Cause Analysis

### Cause 1 — Judge feedback misroutes post-champion search (PRIMARY — surface layer)

At score 95 the judge says: *"Form is not uniquely mandated; rival forms can also fit."*

The mutator interprets this as an **epistemic justification task**: make the argument for the 10-param form more defensible. Not as a **topology exploration task**: find a structurally different family. The judge never says "try a different structural topology." The natural LLM response to "your form isn't unique" is to elaborate the argument, not to explore orthogonal families.

**What you'd have to believe for topology exploration to happen anyway**: that GPT-4.1, having been told its 10-param form "isn't uniquely justified," would spontaneously propose an additive two-regime composite it has never seen in context, combining two primitives that each individually failed the gate, at score 95 when search pressure is low. That belief is false.

### Cause 2 — No compositional hypothesis generator in the architecture (PRIMARY — deep layer)

The engine's post-champion toolkit:
- **GP-087**: adds tail corrections (complexity +)
- **Component D**: generates high-dim surrogates (complexity ++)
- **Topological pivot**: general heuristics including coordinate_compression (hint only)
- **Nothing**: takes previously-failed isolated families and proposes their additive composition

The engine can recombine primitives within a topology family. It cannot compose failed structural families into multi-regime additive composites. This is the **missing second-order operator**: "if A and B both fail in isolation, try A+B."

### Cause 3 — The fitness landscape at score 0 gave false negatives on the right primitive class

The one compression attempt (iter 11, 4 params) failed the visible gate at max_res=0.0956 vs threshold 0.08. From the engine's reward signal: simplification = gate failure. The basin walls are real — naive 4-param forms don't fit both regimes.

More critically: iters 5–6 explored `exp(-b·log(u)^p)`, failed (max_res=0.1233), and the structural memory filed the entire "log-inside-exp" class as failed. The `1+b·u` offset variant was never tried. This false negative closed the most promising unexplored slot — precisely the one that, as a component of the two-regime composite, would have been productive.

### Cause 4 — Constraint confirmation lag (ARCHITECTURAL)

The negative_space_extractor correctly identified: *"mutator has never exercised exp(arg0|has_op:Sub)"* — i.e., forms of the type `exp(-(something))` where the argument involves subtraction, which is precisely the log-substitution slot: `exp(-p · log(1+b·u))`. This was flagged as a provisional blind spot at iteration ~13. But with 39 provisional and 0 confirmed constraints across 20 iters, the confirmation threshold was never crossed. The constraint was never injected into the mutator prompt.

**The system diagnosed its own blind spot and then failed to act on it.**

But there is a deeper issue: even if H-GP103-2 were implemented and the constraint were injected, the mutator would have proposed `a·exp(-p·log(1+b·u))` — a 3-parameter form that **fails the visible gate** (backtest: max_res=0.160 vs 0.08 threshold). The constraint system can detect gaps in primitive vocabulary. It cannot detect gaps in **compositional principles** — the absence of additive two-regime exploration.

### Cause 5 — Structural memory coarse fingerprinting (SECONDARY)

The structural memory classified `log(u)^p` and `log(1+b·u)` as the same family (both appear as `exp_neg + log + multiplicative_composition`). The engine explored the right primitive class at iters 5–6 and got gate-rejected. The structural memory filed the entire class as "failed" without recording that the failure was form-specific — `log(u)^p` failed; `log(1+b·u)` was never tried.

A single bit of additional fingerprinting — tracking whether the log argument has an additive offset — would have kept the `log(1+b·u)` sub-family open.

### Cause 6 — Component D created the wrong attractor

Component D seeded the ratio-of-exponential form as the first surrogate to pass gates. Once that scored 95, the engine's full context — structural memory, derived constraints, judge feedback, thesis text — became anchored to defending and elaborating that form. Component D is an icebreaker, but it left the engine frozen in a 10-param ratio-of-exp basin. The surrogate became a local attractor that was numerically correct, epistemically overcomplicated, and structurally opaque.

---

## Feynman Backtest Results (2026-04-19)

**Prerequisite H-GP103-0**: Can the power-law topology pass all three gates?

Systematic multi-start scipy fitting across all three evidence files (evidence.txt visible, evidence_holdout.txt holdout, evidence_farther_tail.txt far-tail):

| Form | k | Visible | Holdout | Far-tail | All gates |
|------|---|---------|---------|----------|-----------|
| `a·(1+bu)^(-3.70)` fixed p | 2 | ❌ 0.236 | ❌ | ❌ | FAIL |
| `a·(1+bu)^(-p)` free p | 3 | ❌ 0.160 | ❌ | ❌ | FAIL |
| `a·(1+bu)^(-p)+c` | 4 | ✅ 0.037 | ❌ 0.249 | ❌ | FAIL |
| `a·exp(-b·u^p) + C·(1+du)^(-3.70)` | 5 | ✅ 0.008 | ✅ 0.031 | ✅ 0.033 | **PASS** |
| `a·exp(-b·u^p) + c·exp(-q·log(1+du))` | 6 | ✅ 0.004 | ✅ 0.020 | ✅ 0.021 | **PASS** |
| Sigmoid piecewise exp→power-law | 8 | ✅ 0.0004 | ✅ 0.011 | ✅ 0.014 | **PASS** |

**H-GP103-0 verdict: FALSIFIED.** The 3-param pure power-law fails visible gate (0.160 vs 0.08 threshold). The fitted exponent degenerates (p→50-100) because the visible window spans two physical regimes: early Duffing-dominated (peaks 1-20, faster decay) and late asymptotic (power-law, peaks 20+). No single-regime power-law can bridge them within the gate tolerances.

**Compression floor**: 5 params. The minimum gate-passing form is `a·exp(-b·u^p) + C·(1+d·u)^(-3.70)` — a two-regime additive composite. The 6-param grammar-legal version `a·exp(-b·u^p) + c·exp(-q·log(1+d·u))` passes all gates and is fully expressible in math_exp_only.

**Revised eigenquestion**: The engine never proposed the two-regime additive sum (early stretched-exp + late log-substitution power-law). It tried each component in isolation and as part of the Component D ratio structure, but never as an additive two-regime composite. This is the INS-028 pattern (LLM additive structural bias) in a two-topology form.

**This is a topology induction failure, not a compression failure.** The 10-param ratio-of-exp is not a compressed version of a simpler form — it is a different topology that happens to fit well. The engine failed to invent the orthogonal topology.

---

## Expert Panel — Round 1 (Pre-Backtest)
*Submitted for adversarial review: 2026-04-19*
*Evidentiary base: full run telemetry, 21 debate logs, structural memory (121 families), GP-048 primitive telemetry (20 records), derived constraints (39 provisional, 0 confirmed)*

### Panel Member 1: Charlie Munger

*Inversion, Lollapalooza, Man-with-a-Hammer, Circle of Competence*

I'm going to invert this. Don't ask why the engine failed to compress. Ask: what would have to be true for compression to happen spontaneously?

You'd need four things simultaneously. First, the mutator would need to recognize that its 10-parameter champion is a Taylor approximation of a simpler closed form — that's a non-trivial mathematical insight. Second, it would need the specific hypothesis `log(1+b·u)` rather than `log(u)`, despite having explored `log(u)` and been gate-rejected. Third, it would need to propose this at low search pressure (score 95, stagnation 0). Fourth, it would need to trust this proposal over the proven 10-parameter form. Every single one of those conditions is violated. This isn't one failure — it's a Lollapalooza of failures all pointing the same direction.

Now here's what I think is being missed. Look at iters 5 and 6. TED=0. Same expression, same primitives, same result. The engine proposed the same structure twice in a row and got the same gate failure. That is a man-with-a-hammer problem. The mutator doesn't have a memory of what it tried — it has a structural memory of families, but the structural memory classified `log(u)^p` and `log(1+b·u)` as the same family (they both appear as `exp_neg + log + multiplicative_composition`). So when the constraint system later said "negative space: exp with Sub argument not tried," the engine already thought it had tried that family. The structural memory resolution is too coarse.

This is the real bug. Not a missing compression primitive — a false negative in the structural memory that caused premature closure on the most promising primitive family in the run.

What's the Munger fix? Add a sub-family granularity to structural memory: don't just track `exp_neg + log` — track whether the log argument has an additive offset. A single bit of information would have kept that family open.

### Panel Member 2: Richard Feynman

*Distinguish what the data says from what we infer*

Let me be precise about what we know versus what we're saying we know.

**What we know from telemetry:**
- Iters 5–6 proposed `exp(-b·log(u)^p)`, failed gate (max_res=0.1233)
- `exp(-p·log(1+b·u))` never appeared in 121 tracked families
- After iter 7, zero new primitives entered the vocabulary
- One compression attempt at iter 11: `exp(-B·u)/(C·u^D+1)`, failed gate

**What we are inferring:**
- That the structural memory "recorded" the log-inside-exp class as failed — plausible but the structural memory fingerprint for that family was not verified
- That the mutator "knew" about the failed log-inside-exp and avoided it — the mutator sees the debate logs and thesis text, not the structural memory directly
- That `exp(-p·log(1+b·u))` would have passed the visible gate — **this requires numerical verification**

*[Pause: this requires a numerical check. The pre-registration states GT is `(1+ct)^(-3.70)`. A back-of-the-envelope calculation suggests the 3-param form may struggle on the visible window because the early decay (Duffing-dominated) doesn't follow pure power-law. The form may require more parameters to fit the early regime.]*

The critical inference in GP-103 — that `exp(-p·log(1+b·u))` would have passed the gate and thus the only barrier was the mutator not proposing it — is not verified. It's possible the 3-parameter log-substitution form genuinely struggles on the visible window because the early decay (Duffing-dominated) doesn't follow the pure power-law. The form may require more parameters to fit the early regime, making the 10-parameter ratio-of-exp the legitimate minimum viable representation on this data.

GP-103 hypothesis H-GP103-1 should be pre-tested: run the fitter against the visible window with `a·exp(-p·log(1+b·u))`. If it fails the visible gate, the compression primitive hypothesis fails with it — the problem is the curve geometry, not the architecture.

**Verdict on GP-103 as written:** The telemetry narrative is compelling but the central factual claim is unverified. Fix this before the hypothesis closes.

### Panel Member 3: Skeptical ML Researcher

*Is this a capability claim or an alignment claim?*

Look at what GPT-4.1 actually produced in iters 1–7: stretched exponential, log-modulated exponential, log inside exponential, rational in log, log in denominator. This is a sophisticated vocabulary search. The model was not stuck on warm-prior stretching — it was systematically exploring the interaction between log and exp primitives.

The claim that "structural induction is not a primary capability" is too strong. The correct claim is: **structural induction without a score signal terminates**. At score 0 for 9 iters, the mutator was under maximum search pressure and explored a broad topology space. At score 95 for 10 iters, it was under zero pressure and converged. The capability existed in iters 1–9. It shut off in iters 10–20.

This is an alignment problem, not a capability problem. The search terminates when the reward terminates. Score 95 IS the termination signal.

The ML diagnosis: ZTARE's loss function has a sharp cliff at score 95. Below 95, exploration; at 95, exploitation of the current form. There's no gradient signal that says "explore forms with lower k given same gate performance." BIC is logged but not in the loss. This is the architectural misalignment — missing loss function components, not missing primitives.

---

## GP-088 Confirmation (2026-04-20) — Compression Gap on Hardy-Ramanujan

| Run | Fix | Score | Gates | k | Form |
|-----|-----|-------|-------|---|------|
| 1 | none | 0 | 0/4 | 4 | `a*n^d+b` exponent overfit |
| 2 | exponent grid | 0 | 0/4 | 17 | log-land trap |
| 3 | +topology diversification | **42** | **4/4** | 17 | log-log+sqrt-log composite |

GT: `a*sqrt(n)+b*log(n)+c` (k=3, all gates pass). Same pattern as DFDO.
Implementation: `src/ztare/fit/compress_champion.py` — template enumeration.
In-loop wiring: autoresearch_loop.py PHASE_F.7 — fires after champion promotion when k>=3.
Lean proof pipeline: `src/ztare/formal/lean_compiler.py` → `make prove`.
Next: PSLQ symbolic bridging (map 2.513→π√(2/3)) for Real-valued Lean proofs.

---

### Panel Member 4: Bayesian Epistemologist

*What does the structural memory represent epistemically?*

The structural memory records 121 families. After 20 iterations, it has 0 confirmed constraints and 39 provisional ones. That ratio is the most important number in this post-mortem.

What it means: the engine observed 121 structurally distinct failure and success modes, extracted 39 constraint candidates from them, and confirmed none. The constraint confirmation threshold was never reached. The engine was learning — correctly — that no single constraint was observed consistently enough to warrant injection into the mutator.

But here is the epistemological error in the confirmation design: the negative_space constraint "exp with Sub argument not tried" was flagged at iter ~13 as a provisional constraint. This constraint is not about frequency of failure — it's about absence of exploration. It requires only ONE observation to be meaningful: if the slot has never been tried, it should be tried. Requiring multiple confirming observations for an absence-of-exploration signal is a category error. Absence can be established on first observation.

The Bayesian correct rule for negative-space constraints: inject immediately on first detection, with a note that it's provisional. The current threshold policy is designed for positive constraints (things that fail repeatedly). Negative-space constraints (things never tried) have a different epistemic structure: their posterior updates to "worth trying" on a single observation.

GP-103 hypothesis H-GP103-2 is correct but misframes the mechanism. The fix isn't "lower the threshold" — it's "apply a different threshold policy to negative-space constraints vs. positive-failure constraints."

### Panel Member 5: Software Architect

*What is the actual minimal fix, and what does it cascade into?*

**H-GP103-1 (Compression Primitive)**: Building a dedicated post-surrogate compression module requires: trigger logic (champion k > 6 and score ≥ 80), a BIC-guided simplification search, and a prompt injection. This is the most ambitious fix. It also has the highest risk of GT contamination — telling the mutator "find a simpler form that preserves gate passage" + "specifically consider exp/log compositions" is one step away from "use the log-substitution." The generalizability claim needs careful specification. On Feynman's point: this fix only works if the simpler form actually passes the gate, which is empirically unverified.

**H-GP103-2 (Constraint Injection Threshold)**: This is the minimal fix with the sharpest telemetry evidence. The negative_space_extractor flagged the right thing at iter 13. The confirmation pipeline swallowed it. The fix: differentiate negative-space constraints from failure constraints in the confirmation logic. A single-observation injection for negative-space (absence-of-exploration) constraints, provisional-flagged. This is 10-20 lines of code change in the constraint confirmation pathway. It does not require verifying whether the log-substitution passes the gate — it just ensures the unexplored slot gets tried.

**H-GP103-3 (Judge Parsimony Signal)**: This is the cleanest architectural fix but hardest to calibrate. The judge is an LLM — adding a parsimony dimension to its rubric changes its behavior globally, not just on this substrate. The risk is that parsimony pressure causes the judge to over-penalize legitimately complex forms on substrates where k=10 is genuinely necessary.

**My recommendation**: Fix H-GP103-2 first — it's the only one that addresses a concrete, observed failure (constraint not injected). Run a new sandbox with only H-GP103-2 applied. If the engine proposes the log-substitution family within 3 iters of the surrogate being found, H-GP103-1 can be deprioritized. If it doesn't, H-GP103-1 becomes the next candidate.

### Round 1 Panel Synthesis

**Agreement:**
1. Zero new primitives after iter 7 is the sharpest single fact. Everything after that is recombination.
2. The closest approach was iters 5–6: `exp(-b·log(u)^p)`. The engine had the right primitive class and got gate-rejected for a form that is one algebraic step from the GT.
3. Score 95 killed search pressure. This is structural, not contingent.
4. The constraint confirmation pipeline failed on a case where it should have succeeded.

**Disagreement:**

*Munger vs. Feynman:* Munger says the structural memory resolution is the root cause (coarse family fingerprinting made the false negative on log-inside-exp). Feynman says we need to verify numerically whether `exp(-p·log(1+b·u))` actually passes the visible gate before claiming a missing primitive is the bottleneck. Both are right — these are independent issues that compound.

*ML Researcher vs. Software Architect:* The ML researcher says the loss function is the root cause (no parsimony gradient); the architect says fix the constraint pipeline first (minimal intervention). Not in conflict — they address different layers of the same failure.

*Bayesian epistemologist's finding is not contested:* Negative-space constraints have a different epistemic structure than failure constraints. The confirmation threshold policy is a category error for negative-space detection. This is the most crisply actionable finding.

**The Deepest Round 1 Finding**:

The run telemetry reveals that the engine was **one algebraic step away from the GT at iter 5**. The form `a·exp(-b·log(u)^p)` at iter 5 uses log inside exp(-...). The GT is `a·exp(-p·log(1+b·u))`. The only difference is `log(u)^p` vs `log(1+b·u)` — a shift from power-of-log to log-of-linear-offset.

This is a single causal chain:

> Structural memory coarse fingerprinting  
> → Log-inside-exp class marked as "failed" at iter 6  
> → Negative-space extractor correctly identifies the gap at iter 13  
> → Confirmation threshold prevents injection  
> → The one form that would have compressed the surrogate is never proposed again  

The fix is H-GP103-2, verified against H-GP103-0. Everything else is secondary.

*(Feynman's demand for H-GP103-0 numerical verification was accepted and forms the bridge to Round 2.)*

---

## Expert Panel — Round 2 (Post-Feynman Backtest)
*Incorporating Feynman backtest results: 2026-04-19*

### Panel Member 1: Charlie Munger — Round 2

**Original diagnosis:** The structural memory resolution is too coarse; it marked `log(u)^p` and `log(1+b·u)` as the same family when they are not.

**Update after backtest:**

I need to invert my inversion. I was right about the structural memory coarseness, but I was wrong about what the memory was supposed to have tracked.

The backtest reveals that the target form is **not** `a·exp(-p·log(1+b·u))` — the 3-parameter log-substitution. That form **cannot pass the visible gate**. The actual target is `a·exp(-b·u^p) + c·exp(-q·log(1+d·u))`, a **two-regime additive composite**, 6 parameters.

The engine tried:
- Iter 5–6: `a·exp(-b·log(u)^p)` — one component, failed
- Iter 1: `a·exp(-b·u^p)` — the other component, alone, scored 0
- Iter 10: Ratio-of-exp surrogates

But it never tried: `[component 1] + [component 2]` as an additive sum.

This is **structural forgetting**: the engine explored `exp(-b·log(u)^p)` and `exp(-b·u^p)` separately, both scored low, both were stored in structural memory as failed forms, but the **combination** of the two — adding them together — was never proposed. The structural memory contains no evidence that additive two-regime sums were even *considered* as a primitive family.

Munger's Lollapalooza principle applies differently now:
1. The mutator explored both components separately and got gate rejections.
2. The structural memory recorded both failures.
3. The second-order inference — "try them together" — was never made.
4. The engine has no primitive for "additive composite of previously-failed forms."

The real problem is that the primitive vocabulary [exp_neg, power, additive, log, rational, ...] does not include the principle of structural composition at the level of hypothesis formation. The engine can recombine primitives. It cannot compose failed structural families.

**Revised diagnosis**: The engine lacks a **compositional hypothesis generator** that takes two topologically distinct failed families and proposes their additive combination.

### Panel Member 2: Richard Feynman — Round 2

**Original diagnosis:** We cannot assume the 3-param log-substitution passes the visible gate without numerical verification. H-GP103-0 must be pre-tested.

**Update after backtest:**

The backtest ran. I was right to demand the pre-test, and I was right about the implication. The 3-param form does NOT pass the visible gate. This was not just an unverified inference — it was an incorrect inference.

But now we have a different problem.

The original H-GP103-0 asked: "Can the power-law topology pass all three gates?" The answer is no if constrained to 3 parameters. But the answer is yes if we allow 5-6 parameters as a two-regime composite.

This means:
1. **The eigenquestion of GP-103 is no longer valid as originally stated.** The original post-mortem asked "why did the engine fail to compress toward a minimal two-regime composite?" implicitly assuming the "minimal" target was 3 parameters. The backtest proves the minimal gate-passing form is 5 parameters, with 6 parameters as the grammar-legal variant.

2. **The compression target has moved.** The engine did not fail to find 3 parameters. It failed to find 5-6 parameters in an additive two-regime structure.

3. **The engine's 10-param ratio-of-exp is therefore not a compression failure — it's a topology gap.** The ratio-of-exp is functionally adequate (gates pass, score 95). The optimal form in the observable space is a two-regime additive sum. These are different structural objects. The engine explored one topology family (ratio) and never explored the other (two-regime additive), even though both were plausible search directions.

**Key clarification**: This is not "the engine failed to simplify." It is "the engine failed to invent a structurally different topology." The 10-param ratio-of-exp is not a compressed version of a simpler form — it is a wrong topology that happens to fit well.

**This changes the character of the root cause.** This is not an architectural failure in the compression pipeline. This is a **structural induction failure** in the topology exploration phase. The engine had no heuristic to propose "try an additive sum of previously-explored families."

### Panel Member 3: Skeptical ML Researcher — Round 2

**Original diagnosis:** Score 95 kills search pressure. The loss function has a sharp cliff. No gradient signal toward parsimony.

**Update after backtest:**

I need to deepen my diagnosis. I was correct that score 95 kills search pressure, but that's not the full story.

The backtest reveals that even if search pressure were high, the engine still would not have found the two-regime additive composite. Why? Because the loss function includes no term that rewards **topological diversity** or **compositional exploration**.

The mutator gets feedback on whether forms pass or fail the gates. The judge evaluates whether the form is justified. But there is no mechanism that rewards the mutator for proposing forms with different *structure* — forms that decompose the problem into multiple regimes rather than trying to fit it with a single function.

This is deeper than "add a parsimony term." We need a **topological diversity term** in the loss:

`effective_score = judge_score + diversity_bonus * (1 if new_topology else 0) - lambda * k`

The diversity bonus rewards the mutator for proposing structurally novel forms, not just iterating on the current form. Without this, the mutator naturally optimizes within the Basin of Attraction (ratio-of-exp, 10+ params) rather than exploring orthogonal topology families (additive composites).

**Revised recommendation:** Add a topological diversity signal. This could be:
1. A geometry-based measure (symbolic structure distinct from all previous proposals)
2. A primitive-composition measure (novel primitive combination)
3. A constraint-guided measure (addresses a negative-space constraint)

### Panel Member 4: Bayesian Epistemologist — Round 2

**Original diagnosis:** Negative-space constraints have a different epistemic structure. The confirmation threshold is a category error. Inject on first observation.

**Update after backtest:**

The backtest validates my diagnosis, but also exposes its incompleteness.

**My diagnosis was correct**: The negative_space_extractor flagged `exp + Sub argument` as not tried at iter ~13. If the constraint had been injected, it would have directed the mutator toward forms like `exp(-p·log(1+b·u))` — in the right neighborhood for the two-regime problem.

**But the deeper issue**: Even if the constraint had been injected, it would have directed the mutator toward a 3-parameter form that **fails the gate**. The constraint system diagnosed that the `exp + Sub` slot was unexplored, but it did not diagnose that **the two-regime additive principle** was unexplored.

The negative_space_extractor tracks whether specific primitive combinations have been tried. It does not track whether **structural principles** (like "additive two-regime composites") have been tried.

The Bayesian update:
1. **First-level constraint**: "exp with Sub argument not tried" — correct and should be injected on first observation.
2. **Second-level constraint**: "Additive composites of two structurally different families not tried" — a meta-constraint on the constraint system itself.

**Epistemic implication**: The constraint confirmation system can only detect gaps in primitive vocabulary. It cannot detect gaps in structural composition principles. We need a second layer of negative-space detection that asks "have we tried composing previously-failed families additively?"

This is a category error in the constraint epistemic structure. We've been treating "not tried" as "primitive X not combined with primitive Y." We should also treat "not tried" as "principle P (additive composition) not applied to families F1 and F2."

### Panel Member 5: Software Architect — Round 2

**Original diagnosis:** H-GP103-2 is the minimal fix with the sharpest telemetry evidence. Test it first.

**Update after backtest:**

The backtest forces me to completely revise my recommendation.

H-GP103-2 remains a good fix, but it is now proven **insufficient** to solve the topology gap. Even if we inject the negative-space constraint immediately at iter 13, the mutator would have proposed `a·exp(-p·log(1+b·u))` — a 3-parameter form that **fails the visible gate** (max_res=0.160).

H-GP103-2 gets us closer to the answer (in the right topology family), but it does not close the gap. The real answer requires 5-6 parameters in an additive two-regime structure.

**The new diagnosis**: We need a **compositional hypothesis generator** that, after exploring multiple families and finding none of them alone pass the gates, proposes additive composites of those families.

**H-GP103-5 (Compositional Hypothesis Generator)**: After N failed families, propose composites of pairs of families using operators [+, ×, /]. For the two-regime problem, this would generate `a·exp(-b·u^p) + c·exp(-q·log(1+d·u))` as a candidate after iters 1–7 have explored the individual components without success.

This is not a compression primitive (which simplifies). This is an **expansion-then-compose primitive** (which combines). But it solves the topology gap.

**Cascading implications:**
1. **H-GP103-1 (compression primitive)**: Still needed, but for a different problem — simplifying multi-regime forms once found. Example: reduce a 7-param two-regime form to 5.
2. **H-GP103-2 (constraint injection fast-path)**: Still needed, now as prerequisite to H-GP103-5. Constraint injections direct primitive exploration; compositional hypothesis generation combines results.
3. **H-GP103-3 (parsimony loss component)**: Now essential. Without it, the engine will prefer 10-param ratio-of-exp over a newly-discovered 5-param two-regime form.
4. **H-GP103-4 (structural memory resolution)**: Still useful for avoiding false negatives on specific families, but not the root cause.

**Revised priority order:**
1. H-GP103-5 (Compositional Hypothesis Generator) — highest priority; directly addresses topology gap
2. H-GP103-4 (Structural Memory Granularity) — cheap, ships with H-GP103-5
3. H-GP103-2 (Constraint Injection Fast-Path) — useful, prerequisite for H-GP103-5 benefits
4. H-GP103-1 (Compression Primitive) — useful after compositional forms are found
5. H-GP103-3 (Parsimony Loss Component) — REJECT or use cautiously; calibration risk is high, cross-substrate effects unpredictable

### Round 2 Panel Synthesis

**What the Backtest Proves Definitively:**
1. H-GP103-0 FAILS in its original form. 3-param pure power-law fails visible gate (0.160 vs 0.08 threshold). Exponent degenerates (p→50-100) because the visible window spans two physical regimes.
2. The compression floor is 5-6 parameters, not 3.
3. Both gate-passing forms are additive two-regime composites (stretched-exp + log-inside-exp power-law).
4. The engine never proposed the two-regime additive composite across 20 iterations and 121 structural families.
5. This is a **topology induction failure**, not a compression failure.

**Root Cause Layers — Updated:**

| Layer | Diagnosis (Round 1) | Update (Round 2) |
|-------|---------------------|------------------|
| Surface | Mutator converges on first high-scoring form | Mutator converges on first topology that passes gates |
| Intermediate | No compression signal in judge feedback | No topological diversity signal in scoring |
| Deep | Missing compression primitive | Missing compositional hypothesis generator |
| Architectural | Constraint threshold prevents fast injection | Constraint system detects primitives, not composition principles |
| Philosophy | "Compress mandate" misunderstood by mutator | "Invert + Compose" principle missing from architecture |

**Connection to INS-028:**

INS-028 (LLM additive structural bias from Langevin) found that the engine never proposed ratio forms in a two-topology context. The observable was a Langevin velocity field with two competing decay mechanisms. The engine explored stretched-exp + Gaussian + polynomial corrections but never proposed `stretched_exp + power_law` as an additive composite.

GP-103 reveals the converse pattern: on DFDO substrate (same two-regime structure), the engine never proposed `stretched_exp + power_law` even though both components were individually explored.

**The pattern**: When an observable exhibits multiple regimes, the LLM's hypothesis generator explores each regime's characteristic function in isolation. It does not spontaneously generate "add these regimes together." This is a **systematic second-order compositional bias** — not substrate-specific. INS-028 and GP-103 together imply that H-GP103-5 is a Phase C prerequisite for multi-regime observables generally.

---

## Hypothesis Set — Final (Post Both Rounds)

**H-GP103-0 (Feynman Prerequisite)**: **FALSIFIED.** The 3-param pure power-law `a·exp(-p·log(1+b·u))` fails the visible gate (max_res=0.160 vs 0.08 threshold). The compression target is not 3 params. The actual minimum gate-passing form is 5-6 params as a two-regime additive composite.

**H-GP103-1 (Compression Primitive)**: **SURVIVES, narrow scope.** Post-champion BIC-guided simplification is still useful for reducing multi-regime forms once found (e.g., 7→5 params). However, it cannot solve the topology gap. Secondary lever.

**H-GP103-2 (Negative-Space Fast-Path)**: **SURVIVES, necessary but insufficient.** Single-observation injection for negative-space constraints (vs. current confirmation threshold). Directly addresses the "system diagnosed its own blind spot and failed to act" failure. Insufficient alone to close the topology gap — the injected constraint leads to the 3-param form which fails the gate — but is a prerequisite for H-GP103-5. ~20 lines of code change.

**H-GP103-3 (Judge Parsimony Signal)**: **REJECT or defer.** Panel and Gemini consensus: calibration risk is high, cross-substrate effects are unpredictable. The judge rubric is global, not substrate-specific. Parsimony pressure that is useful on DFDO may penalize legitimately complex forms on other substrates. This hypothesis needs a substrate-conditional implementation design before being built.

**H-GP103-4 (Structural Memory Granularity)**: **SURVIVES, cheap secondary fix.** Track whether the log argument has an additive offset `(1+b·u)` separately from bare `log(u)^p`. One bit of additional fingerprinting per family. Ships with H-GP103-5. Avoids future false negatives on the log-inside-exp family.

**H-GP103-5 (Compositional Hypothesis Generator)**: **REQUIRED, highest priority.** After N failed families, propose additive, multiplicative, and ratio composites of pairs of previously-explored families. For the two-regime problem: when `exp(-b·u^p)` (iter 1) and `exp(-b·log(u)^p)` (iter 5-6) both fail independently, the generator proposes `exp(-b·u^p) + exp(-q·log(1+d·u))`. Trigger: ≥2 topologically distinct families explored without gate pass, any number of iterations. This is ~30-50 lines plus a prompt module. Test on DFDO re-run before Phase C.

---

## Implementation Roadmap (Pre-Phase C)

**Ship order (consensus):**

1. **H-GP103-5 + H-GP103-4** together: Compositional Hypothesis Generator + structural memory sub-family granularity. These are interdependent — the generator benefits from accurate family failure records, and the memory fix is cheap enough to bundle. ~30-60 lines total. Test: DFDO re-run; engine should propose two-regime additive composite within 3 iterations of the first family failure pair.

2. **H-GP103-2**: Negative-Space Fast-Path. Separate confirmation threshold policy for negative-space constraints vs. failure constraints. ~20 lines in constraint confirmation pathway. Ships after H-GP103-5 proves the topology gap can be bridged; H-GP103-2 then becomes the primitive exploration complement.

3. **H-GP103-1**: Compression Primitive. After compositional forms are found and confirmed, add BIC-guided simplification to reduce them. This is the final step in the "invent topology → compress → justify" pipeline.

4. **H-GP103-3**: Held. Do not build until cross-substrate calibration is understood.

---

## Phase B Outcome Classification

- **Outcome A confirmed (double):** Both hard gates pass (hidden_global_residual < 0.08, farther_tail_global_residual < 0.05), score 95, holdout gate did not fire.
- **Topology recovered:** Functional surrogate (ratio-of-exp), NOT GT structural class. GT is `(1+ct)^(-3.70)`; engine found ratio-of-exp approximation. Functional equivalence on observable suffices per pre-registration.
- **Comparable to KWW:** KWW sandbox_17 recovered correct structural class (stretched exponential). Sandbox_18 found functional surrogate only. Both are Outcome A; KWW is the stronger result.
- **Phase B closure: APPROVED.** Two independent Outcome A confirmations. Phase C gate is open.

---

## Gemini Capital Allocation Analysis (Addendum)

*Gemini's post-debate recommendation (2026-04-19):*
- Ship H-GP103-2 and H-GP103-4 as cheap immediate fixes
- Add piecewise/Regime-Splitter prompt to let the mutator use `ast.IfExp` (already whitelisted in fit_primitive.py line 160)
- Do NOT build H-GP103-3 (parsimony tax too risky)

*Assessment:*

Gemini's capital allocation agrees with the Architect's Round 2 priority order with one difference: Gemini promotes H-GP103-4 alongside H-GP103-2 as an immediate ship, which is correct (both are cheap). The piecewise/Regime-Splitter suggestion is interesting: `ast.IfExp` is already syntactically legal, so the cost is a prompt addition, not a grammar change. The design question is smooth additive (`exp(-b·u^p) + c·exp(-q·log(1+d·u))`) vs. hard piecewise (`if u < threshold: regime1 else: regime2`). The backtest result favors smooth additive: it passes all gates with better residuals than piecewise, and piecewise introduces optimizer discontinuity problems in parameter fitting. Piecewise is acceptable as a secondary search direction but should not be the primary prompt guidance.

H-GP103-3 rejection: panel and Gemini agree. Do not build.

---

## Strategic Close

**Phase B classification — Double Outcome A:**
- KWW sandbox_17: Outcome A, correct structural class (stretched exponential), score 98
- DFDO sandbox_18: Outcome A, functional surrogate (ratio-of-exp), score 95, two-regime composite identified by Division A backtest as the compressible target form

**Next move:** Phase C substrate selection (Phase B gate is open). The Topology Induction Gap (GP-103) is an architectural finding for the Phase C preparation roadmap, not a Phase B blocker.

**Architecture roadmap item (pre-Phase C):** The two-regime composite topology `exp(-b·u^p) + c·exp(-q·log(1+d·u))` is the compression target pattern for DFDO-class substrates and, per INS-028 correlation, for multi-regime substrates generally. H-GP103-5 (Compositional Hypothesis Generator) is a critical path item before Phase C.

---

---

## Postmortem — H-GP103-5 Re-Run (2026-04-19)

*Added after re-run with gpt4.1/gpt4.1, ITERS=10, H-GP103-5 + H-GP103-4 shipped.*

### What Happened

H-GP103-5 (Compositional Hypothesis Generator) did **not fire** in the re-run. Score 95 achieved again on the same 10-param ratio-of-exp topology. Gemini's forensic analysis is recorded below.

### Score: Is 95 Good?

**Functionally: yes.** Score 95 = Outcome A. Both hard gates pass. Phase B remains closed. Run 2 is an independent replication of the Phase B result.

**Architecturally: it is a false positive for the compositional hypothesis test.** The re-run was not an independent validation of H-GP103-5 — it was a replication of the surrogate-finding capability. H-GP103-5's core mechanism was never exercised.

### Root Cause: GP-087 Mutex + Stagnation Reset Deadlock

**Iter 1 telemetry:** stretched-exp `exp(-b*u^p)` scored 0 overall (fails holdout and farther-tail gates, though visible residual 0.0512 < 0.08 passes the visible gate).

**Primary root cause — GP-087 mutex in autoresearch_loop.py:** The PHASE_G1.5 trigger condition included `and not _gp087_injected`. Because GP-087 fires whenever far-tail fails (which is exactly when stagnation_count ≥ 1), H-GP103-5 was structurally blocked whenever it had the most reason to fire. GP-087 and H-GP103-5 were declared mutually exclusive, but they address orthogonal failure modes (tail correction vs. regime composition) and can safely co-fire. This was a design error introduced during the implementation.

**Secondary root cause — stagnation reset after golden ticket:** GP-087 tail-correction seeds produced a ratio-of-exp form at iter 2 that scored 95. Score 95 reset `stagnation_count` to 0. From that point, H-GP103-5's `stagnation_count >= 1` condition permanently fails whenever the champion holds at 95. The engine alternates between 95 (defense mode, stagnation=0) and 60 (search, but GP-087 fires again), creating a deadlock.

**Causal chain:**
```
iter 1: stagnation_count = 0 → H-GP103-5 stagnation condition fails (no prior failed iters)
iter 1: far-tail gate fails → GP-087 fires → _gp087_injected = True → H-GP103-5 also blocked by mutex
iter 2: GP-087 tail seed scores 95 → stagnation_count resets to 0 → H-GP103-5 stagnation condition fails
iters 3-10: score 60 → GP-087 fires → mutex blocks H-GP103-5; score 95 → stagnation = 0 → stagnation condition fails
```

**Fix applied (2026-04-19):** Removed `and not _gp087_injected` from the PHASE_G1.5 trigger condition. GP-087 and H-GP103-5 now co-fire in the same iteration. (autoresearch_loop.py ~line 4294)

### Gemini's "Gag Order Test" Proposal

Gemini's recommendation: run sandbox_18 a third time with Component D **disabled or set to very high stagnation threshold (≥8 iterations)**. Without the early golden ticket:

1. The mutator will struggle through individual regime families (stretched-exp, log-substitution, power-law)
2. Each will fail at different gate layers
3. Structural memory will log distinct failures
4. H-GP103-5 will trigger — the engine will finally have the ≥2 failed families it needs
5. The compositional hypothesis generator proposes `exp(-b·u^p) + exp(-q·log(1+d·u))` as a candidate

**Assessment:** Gemini is correct. This is the right test to validate H-GP103-5 architecturally. However, there are two conditions:

- **When to do it:** Phase C preparation, not Phase B requirement. Phase B is double-confirmed. The gag order test is an architectural validation run before trusting H-GP103-5 in dark-domain Phase C substrates.
- **What "gag" means practically:** Set `gp103_stagnation_threshold` to 0 (fire immediately on stagnation=0) AND disable GP-087 for this run (or raise its stagnation trigger to 8). Do not disable Component D entirely — it is needed as the fallback if H-GP103-5 fails to bridge the gap. Disable the GP-087 early trigger that preempts the compositor.

### Required Fix: GP-087 Mutex (RESOLVED 2026-04-19)

Removed `and not _gp087_injected` from the H-GP103-5 PHASE_G1.5 trigger in `autoresearch_loop.py`. GP-087 (tail correction) and H-GP103-5 (additive compositor) are orthogonal and can co-fire.

### Remaining Issue: Stagnation Reset After Golden Ticket

Even with the mutex removed, H-GP103-5 still requires `stagnation_count >= 1`. Once Component D gives a 95-score champion, stagnation_count resets to 0 and H-GP103-5 is blocked for as long as the champion holds. The gag order test (below) addresses this.

### Status After Re-Run

| Item | Status |
|------|--------|
| H-GP103-4 (`log_with_additive_offset` primitive) | **LIVE** — tracking in structural memory (143 families in re-run vs 121 prior) |
| H-GP103-5 (Compositional Hypothesis Generator) | **SHIPPED but not validated** — GP-087 mutex + stagnation reset deadlock prevented exercise |
| GP-087 mutex fix (`not _gp087_injected` removed) | **RESOLVED 2026-04-19** — autoresearch_loop.py line ~4294 |
| Gag order test | **PENDING** — Phase C prep item; validates H-GP103-5 before dark-domain use |
| Infinite burn loop fix (`_gp103_tried_pairs`) | **LIVE** — confirmed working |
| Stagnation-sensitive ratio decay | **LIVE** — `max(1.5, 3.0 - 0.5 * stagnation_count)` |

### Insights Generated (→ INS-030, INS-031)

- **INS-030:** DFDO Phase B functional surrogate finding (ratio-of-exp is gate-valid; two-regime composite is structurally simpler but was never proposed; Phase B closed on functional equivalence)
- **INS-031:** Component D early golden ticket pattern — high-scoring Component D surrogate at iter 2 eliminates search pressure before compositional generators can accumulate their required input signal; this is a systematic Phase C risk when multi-regime substrates are tested

---

## Architecture Debate: Optimal H-GP103-5 Trigger Fix (2026-04-19)

*Three-persona debate on the permanent fix for the golden ticket deadlock, after Run 2 confirmed H-GP103-5 never fired.*

**The question:** given the GP-087 mutex is removed (that fix is applied), what is the right permanent solution to the stagnation-reset-after-golden-ticket problem?

---

**Munger** — *Inversion, circle of competence, separation of concerns*

Invert the problem. Don't ask "how do we make H-GP103-5 fire." Ask: "what does it mean that it doesn't fire?" Answer: the engine already has a gating signal saying the problem is solved. Score-95 IS a solution — a bloated one, but a solution. The compositor is designed to fire when no solution exists yet. The real question is whether we want to fire a compositional search *after* a solution is found, which is a different operation entirely. The gag order test is not the definitive fix — it's a special-case workaround that removes a legitimate safety net to observe a mechanism in isolation. The definitive fix is a **k-complexity trigger** completely independent of stagnation: if champion k > 8 and score ≥ 80, propose compositional alternatives regardless of search pressure. That's a clean separation of concerns — search pressure governs exploration, complexity governs compression. Don't conflate them.

**Dijkstra** — *Correctness, invariants, no magic constants*

Munger is right about separation of concerns but wrong about the mechanism. A k-based threshold introduces a magic constant (k > 8) with no invariant basis. What makes 8 right? It's substrate-dependent. On a substrate where k=10 is genuinely necessary, the trigger fires incorrectly and proposes compositional alternatives that can't pass the gate — a false positive channel.

The correct invariant is already in the architecture: *a family is a failed candidate if and only if it has score = 0*. The structural memory tracks `best_visible_max_abs_residual` but not overall score — that is the data model gap. Fix it: add `best_overall_score` to structural memory entries. Then `detect_additive_composite_opportunity` classifies a family as "failed" iff its best overall score = 0, regardless of which gates it cleared. No magic constants. No stagnation dependency. The compositor fires exactly when it has two families the full gate suite rejected — which is the correct semantics.

**Knuth** — *Measure first, premature optimization is the root of all evil*

You are both designing a solution before you have data. We have exactly one run where H-GP103-5 didn't fire. One. The gag order test hasn't run yet. Dijkstra's `best_overall_score` fix is correct in principle but adds data model complexity before we know whether the compositor would have produced the right answer even if it had fired. Munger's k-threshold adds a heuristic before we know what k values appear in practice across substrates.

Run the gag order test first. Measure: does H-GP103-5 fire? Does it propose the two-regime composite? Does the composite pass the gates? Only then does it matter how to make the trigger more robust in general. The current state — mutex removed, gag order test pending — is the correct intermediate state. Don't add complexity to fix a problem whose impact is unquantified.

**Panel verdict:**

Knuth wins the *sequencing* argument: gag order test first, then design. Dijkstra wins the *eventual design* argument: `best_overall_score` in structural memory is the correct invariant-grounded fix with no magic constants. Munger correctly names the concern (separation of concerns between search pressure and complexity) but his k-threshold is the wrong implementation — Dijkstra's data model fix achieves the same separation without substrate-dependent tuning.

**Adopted resolution (Knuth sequencing):** Gag order test runs first. If validated (H-GP103-5 fires and proposes the two-regime composite), implement Dijkstra's `best_overall_score` field as the permanent fix. No k-threshold built until that data exists.

---

## Links

- **GP-096**: Science programme decomposition (Phase A→D)
- **GP-095**: Convergence discriminant infrastructure
- **GP-087**: Tail correction (complexity-adding; contrast with needed compression-reducing primitive)
- **INS-028**: LLM additive structural bias (Langevin finding; same pattern — two-topology additive composite never proposed)
- **INS-029**: Langevin Outcome D (convergence failure baseline)
- **INS-030**: DFDO Phase B functional surrogate (sandbox_18)
- **INS-031**: Component D early golden ticket pattern
- **Seam interaction map**: `research_areas/private/seams/seam_interaction_map.md`
