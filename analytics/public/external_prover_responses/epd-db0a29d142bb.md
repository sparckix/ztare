# External-prover dispatch epd-db0a29d142bb

**Model**: gpt-5.5-2026-04-23
**Substrate**: NS-Track-B
**Dispatched**: 2026-05-18T02:10:06.329384+00:00
**Cost**: $0.0000
**Tokens**: 1158 in / 15187 out

## Question

# Eigenquestion: two non-probative "decisive" experiments — is this a treadmill, and what is the minimal design that actually discriminates?

You are a cold, adversarial reviewer with deep Lean/Mathlib/ATP + experiment-design expertise and NO stake in our prior choices. Be blunt. Tell us if we are treadmilling. Give the single minimal design that would actually answer the question — or tell us the question is wrong.

## The question we've been chasing
Does tactic-by-tactic search over LIVE proof states beat whole-proof compose-then-compile, at equal wall-clock, on real multi-step theorems? (Origin: a prior "kernel-grounded rerank" idea was killed using a substrate that exposed no proof state; an earlier cold pass said that kill was a substrate artifact and ranked "proof-state stepping" the #1 missing primitive, prior = "experiment will be positive".)

## What we built (durable, works)
- Persistent leanprover-community/repl (import amortized ~40s once, ~0.07s/tactic).
- A leak-tight Mathlib benchmark extractor (cold-validated algorithm: in-place `sorry` in the target's real source file → repl File mode → true module context, target NOT registered → genuine pre-command proof state). 40 rows kept, gold-multi-step 3–39 tactic steps, single-`exact?` rejected.
- A beam searcher over proof states + a controlled whole-proof baseline (SAME tactic portfolio, same governance, same budget — isolates only the proof-state variable).

## The evidence — TWO non-probative runs, opposite failure modes
1. **v30 corpus (27 rows):** stateful 4 vs baseline 5 governed closures. But EVERY closure in BOTH arms was a ONE-SHOT tactic (`positivity`/`norm_num`/`simp_all`); the corpus was all one-shot arithmetic → CEILING: no room for proof-state to matter. Non-probative.
2. **Leak-tight corpus (40 hard multi-step rows), 25s/goal, unguided portfolio:** stateful **0** vs baseline **0**. Nothing closed at all → FLOOR: a fixed tactic-portfolio beam (no LLM tactic-generator conditioned on the goal, no learned policy, no retrieval) is too weak to close ANY genuinely hard multi-step Mathlib theorem in 25s. Non-probative.

Common root we now see: the *prover* (fixed portfolio) is the binding constraint, not proof-state-vs-blind. We never established base-rate > 0 for the portfolio on multi-step theorems before spending the run (a self-inflicted discipline miss).

## Questions — be blunt
1. **Are we treadmilling?** Two non-probative runs chasing "proof-state vs blind". Is this question still worth answering, or is it the wrong object — should effort go elsewhere (e.g. premise retrieval, a real generator, or abandoning the comparison)? Say so plainly if yes.
2. If the question IS worth answering, what is the **single minimal design** that discriminates? Specifically adjudicate: (a) graded-difficulty corpus (include 2–4-step theorems where a portfolio has nonzero base-rate, so there's discrimination room) vs (b) a real goal-conditioned LLM tactic-generator (the actual "stateful agent") vs whole-proof generation by the SAME model — which is the true minimal test, and what budget / base-rate gate / N?
3. What is the **cheap base-rate pre-check** we should have run, and should every future "decisive" run be gated on base-rate ∈ (0,1) on the chosen corpus?
4. Is the leak-tight benchmark itself still valuable independent of this question (e.g. as a contamination-free eval other provers can use), or is it over-engineered for what we need?
5. Given a just-occurred operator-machine crash from parallel heavy local Lean runs (now: heavy/long runs go on a slower VPS, serialized, checkpointed), factor compute-resilience into the recommended design.

Give: (i) treadmill verdict (yes/no + why), (ii) the ONE design to run next end-to-end with its base-rate gate, (iii) what to STOP doing.


## Response

## (i) Treadmill verdict

**Yes, partially.** You are treadmilling **if you keep running fixed-tactic-portfolio A/Bs** and calling them tests of “proof-state stepping.” Those runs test only:

\[
\text{weak proposal distribution} \times \text{chosen corpus difficulty} \times \text{budget},
\]

not the live-state variable.

Your two failures are exactly the two non-identifiability regimes:

| run | missing precondition | actual quantifier scope | valid conclusion |
|---|---|---|---|
| v30 | multi-step goals where state can matter; non-ceiling base rate | one-shot arithmetic/automation goals | “both arms mostly measure one-shot tactic coverage” |
| 40 hard leak-tight | prover has nonzero solve rate at budget | fixed portfolio on hard Mathlib at 25s | “this portfolio is too weak here” |

So: **the question is not wrong, but your current prover is the wrong instrument.** Proof state is an information channel. A fixed portfolio with no goal-conditioned proposal policy cannot exploit much of that information.

This is consistent with the direction of the literature: successful neural ATP/proof-assistant systems usually combine a learned proposal model with checker/search/feedback, not a blind fixed tactic list; see GPT-f, arXiv:2009.03393; Thor, arXiv:2205.10893; LeanDojo/ReProver, arXiv:2306.15626. Whole-proof generation/repair is a different baseline; see Baldur, arXiv:2303.04910.

---

## (ii) The one design to run next

Run **one paired, base-rate-gated LLM-vs-LLM experiment**:

> **Stateful LLM next-tactic search over live Lean states**  
> versus  
> **same LLM generating whole proof scripts from the initial theorem context only**,  
> equal wall-clock, same static context/retrieval, same Lean checker, same benchmark distribution.

This is the minimal load-bearing test. A graded corpus is necessary calibration material, but **not sufficient**. Merely adding 2–4-step theorems to a fixed portfolio test answers only a toy question: “can a hand tactic list exploit pruning?” It does not answer the real question.

### Formal hypothesis

For theorem distribution \(D\), model \(M\), context policy \(C\), and wall-clock budget \(T\):

\[
Y_i^S = 1 \iff \text{stateful tactic agent proves theorem } i \text{ within } T,
\]
\[
Y_i^W = 1 \iff \text{whole-proof generator proves theorem } i \text{ within } T.
\]

Primary hypothesis:

\[
\Pr_D[Y^S=1] > \Pr_D[Y^W=1].
\]

Without fixing \(D,M,C,T\), the question is undefined.

---

### Corpus

Use the leak-tight extractor, but make a **graded pool**, not only hard rows.

Required:

- true source-file context;
- target theorem not registered;
- final success rechecked by fresh Lean/kernel run;
- exclude rows closed by a single allowed one-shot tactic at initial state;
- gold proof length mostly 2–12 tactics;
- stratify roughly:
  - 40%: 2–4 gold tactics,
  - 40%: 5–8,
  - 20%: 9–12/15.

Do **not** select final test rows based on the two arms’ success. Use a disjoint calibration set.

---

### Arms

#### Stateful arm \(S\)

- Same LLM \(M\).
- Prompt includes current Lean proof state, theorem statement, local context, same static retrieved premises if any.
- Generate \(k\) next-tactic candidates per node.
- Execute candidates in REPL.
- Beam search over live states.
- Suggested caps:
  - beam \(B=8\),
  - candidates per expansion \(k=4\) or \(8\),
  - max depth 12–16,
  - wall-clock \(T=60\)s/goal/arm to start.
- No manual patching.
- Ban `sorry`, `admit`, new imports, new declarations, unsafe environment mutation.

#### Whole-proof arm \(W\)

- Same LLM \(M\).
- Same theorem statement, imports, local context, same static retrieved premises.
- Generates complete proof scripts only.
- Verification by Lean after whole script generation.
- **No intermediate proof states or compiler-diagnostic repair.**

If you allow compile-error repair, that is a third arm, not the “blind whole-proof” baseline. Lean error messages often leak goal-state information.

---

### Budget

Start with:

\[
T = 60\text{s per theorem per arm}.
\]

If the calibration gate fails low, first try \(T=120\)s or easier strata. If it still fails, stop the comparison and work on the generator/retrieval. If it fails high, harden the corpus or reduce \(T\).

Primary result should be at **equal wall-clock**, but also log:

- model calls,
- generated tokens,
- Lean tactic checks,
- verifier time,
- timeouts,
- crashes/restarts.

---

### Base-rate gate

Calibration set: **30 theorems**, disjoint from final test.

Run both arms at intended \(T\).

Let

\[
U = \#\{i : Y_i^S = 1 \lor Y_i^W = 1\},
\]
\[
D = \#\{i : Y_i^S \neq Y_i^W\}.
\]

Proceed only if:

- \(6 \le U \le 24\), i.e. union solve rate between 20% and 80%;
- initial one-shot solve rate \(\le 20\%\);
- preferably \(D \ge 4\) on the pilot.

Do **not** require both arms individually nonzero. If stateful solves 8/30 and whole-proof solves 0/30, that is not a floor; that is a potentially large effect. The fatal case is both zero or both saturated.

---

### Main \(N\)

Use **N = 100 paired theorems** minimum.

N=40 is only a smoke test unless the effect is huge.

Primary analysis: paired McNemar/sign test on discordant pairs.

Let:

\[
n_{10} = \#\{Y^S=1,Y^W=0\},
\]
\[
n_{01} = \#\{Y^S=0,Y^W=1\}.
\]

Estimator:

\[
\hat{\Delta} = \frac{n_{10}-n_{01}}{N}.
\]

One-sided exact test:

\[
n_{10} \sim \operatorname{Binomial}(n_{10}+n_{01}, 1/2)
\]

under the null of no stateful advantage.

Call it positive only if:

- \(\hat{\Delta} \ge 0.10\), and
- one-sided exact McNemar/sign-test \(p \le 0.05\).

Otherwise report inconclusive/negative honestly.

---

## (iii) Cheap base-rate pre-check you should have run

For the fixed-portfolio experiments, before any “decisive” run:

1. Sample 20–30 goals from the intended corpus.
2. Run every portfolio tactic one-shot at the initial state.
   - If many close: ceiling; corpus is bad.
3. Run the intended stateful beam with the same fixed portfolio at the intended budget.
   - If 0/20 or 0/30 close: floor; prover is too weak.
4. Only then run the paired A/B.

Yes: **every future decisive run should be gated on non-extreme base rate.** More precisely, gate on union solve rate and discordance, not merely literal \(p \in (0,1)\).

---

## Benchmark value

The leak-tight benchmark is still valuable, but be precise about what it guarantees.

It is valuable as:

- a true pre-command proof-state extractor;
- a target-unregistered Lean evaluation substrate;
- a way to avoid `exact?`/environment leakage;
- a reusable hard/stress benchmark.

But it is **not automatically LLM-contamination-free** if the theorems/proofs come from public Mathlib that may be in model pretraining. It is kernel/environment leak-tight, not internet-pretraining leak-tight. For contamination-free LLM eval, use post-cutoff/private/new theorems or withheld proofs.

For your immediate experiment: do not over-engineer more benchmark machinery before fixing the prover. Expand/stratify enough to get \(N=100\), but the bottleneck is the proposal model.

---

## Compute-resilience requirements

Given the crash: no more heavy local parallel runs.

Run serialized/checkpointed jobs on the VPS:

- unit of work: theorem × arm × seed;
- checkpoint after every model call and every Lean node expansion;
- store full transcript in SQLite/JSONL:
  - prompt,
  - completions,
  - tactic result,
  - proof state hash,
  - time,
  - memory,
  - errors;
- deterministic job IDs;
- resume idempotently;
- watchdog memory/time limits;
- restart REPL periodically or on memory threshold;
- randomize/interleave arm order by theorem to avoid API/model/time drift;
- final successful proofs rechecked in a fresh Lean process.

With \(N=100\), two arms, \(T=60\)s, the hard upper bound is about 3.3 wall-clock hours plus overhead if serialized; on a slow VPS, call it overnight. That is acceptable. Crashing your operator machine is not.

---

## What to STOP doing

Stop:

1. Calling zero-zero or one-shot-saturated runs “decisive.”
2. Running fixed tactic portfolios on hard Mathlib and treating failure as evidence about proof-state search.
3. Using all-hard corpora without a base-rate pilot.
4. Using one-shot arithmetic corpora for a multi-step-state question.
5. Tuning corpus/budget after seeing final outcomes.
6. Letting whole-proof baselines see compiler/proof-state repair feedback while calling them “blind.”
7. Treating public-Mathlib leak-tightness as LLM contamination-freeness.
8. Running heavy parallel Lean jobs on the local operator machine.

**VERDICT: partially — the scientific question is still worth one properly gated LLM-vs-LLM paired test, but continuing fixed-portfolio A/Bs is treadmill behavior.**
