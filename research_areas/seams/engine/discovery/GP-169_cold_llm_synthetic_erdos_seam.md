# GP-169 — Cold LLM as Synthetic Erdős (anchor-escape forcing function)

> **Seam metadata** · `seam_id:` GP-169 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: scaffolded (Phase 1 spec, no implementation yet)
Opened: 2026-04-27
Track: kernel
Related: GP-164 (REFRAME + ANALOGY meta-arch), GP-167 (SubstrateCritic), GP-168 (Forced REFRAME iter)
Anchor texts:
  - Cognitive_gym Part 7 (Anchoring Thesis)
  - GP-164 §Appendix (alien-math panel framings)
  - Erdős primitive-set conjecture solved by 23-year-old + ChatGPT (April 2025): Tao's commentary that "humans collectively made a slight wrong turn at move one" by not applying a known method from a related field.

## Trigger

The current ANALOGY mechanism gates cross-domain candidate forms behind `stagnation_count ≥ 3`. The Erdős case shows the right move was at iter 1 — apply a known method from a different field on the first attempt, before exploring the home discipline's repertoire. Right now ZTARE iterates within human-prior architectures for 2-7 iters and only reaches ANALOGY when stuck. That's backwards.

A second flaw: ANALOGY's existing query is run by the `mutator_model_id` (default mutator), which means the same model that just wrote a hot, contaminated context-aware form is also the one tasked with proposing cross-domain candidates. The mutator is contaminated by:
  - the substrate's class labels
  - the previous iter's residual diagnostics
  - the briefing's per-class numeric values
  - the form vocabulary it has been refining

A "cold LLM" — fresh API call, zero conversation history, anonymized structural fingerprint, explicit forbid-the-substrate-domain instruction — solves both flaws. It is unburdened by substrate context (synthetic Erdős) and runs at iter 1 as default seed (anchor-escape default).

## Eigenquestion

Can ZTARE's iter-1 mutator briefing be seeded with cross-domain parametric forms produced by a strictly-anonymized Cold LLM query, such that the apparatus's epistemic posture changes from "try standard math, then get creative on stagnation" to "start with cross-domain creative leaps, bounded by strict mathematical verification"?

If yes, what's the right anonymization protocol, what's the right Cold LLM persona prompt, and how does the apparatus prevent the Cold LLM's candidates from leaking the substrate's domain back to the mutator (since the mutator is also an LLM that will pattern-match domain hints)?

## Phase 1 — Cold LLM Erdős seed at iter 1 (this seam scaffolds; implementation TBD)

### What changes

Currently:
```
iter 1: mutator briefing has [data_diagnostics, contamination_defense, per_class_breakdown, fit_telemetry, iter_trajectory]
        — no analogy_candidates because stagnation_count = 0
mutator writes form using the home-discipline repertoire
iter 2-7: same, until stagnation_count ≥ 3
iter 3+ (if stuck): ANALOGY fires, mutator-model queries for cross-domain forms,
                   candidates land in next iter's briefing as suggestions
```

After GP-169 Phase 1:
```
iter 0 (pre-flight): SubstrateCritic computes residual baseline-fit fingerprint.
                    Cold LLM seed query runs ONCE: send strictly-anonymized
                    structural fingerprint + explicit-forbid-domain instruction
                    to a fresh API call (separate from mutator + judge).
                    Three candidate parametric forms returned. Logged to
                    workspace/cold_llm_seed_iter0.json.

iter 1: mutator briefing has [..., cold_llm_seed_provider]
        Three candidates injected as MANDATORY-CONSIDER (not optional). The
        mutator's iter-1 prompt explicitly directs:
          "Consider these three structurally-distinct candidate forms.
           Pick one as your starting architecture, OR justify in prose why
           none of them apply and write your own. Forms that ignore all
           three without justification will be rejected at apparatus
           level."

iter 2-N: mutator may continue refining the chosen architecture, may
          switch to another seed candidate, or may write something new.
          The seed candidates remain in iter_trajectory briefing as
          alternative architectures.

stagnation triggered (stagnation_count ≥ 3): existing ANALOGY mechanism
                                              still fires (mutator-model
                                              queries for additional
                                              candidates), supplements
                                              the iter-0 cold seed.
```

### Anonymization protocol

The Cold LLM gets:
  - the residual fingerprint (shape descriptor + heavy-tail flag + monotonicity + regime breaks)
  - the y dynamic range in dex
  - the visible class count + held-out class count
  - the K_law budget
  - **NOTHING ELSE.** No substrate name, no domain hint, no variable names from features.py, no published constant values, no field-of-study marker.

The Cold LLM prompt:
```
You are a structural mathematician with cross-disciplinary fluency in
information geometry, scale-invariant analysis, modular forms, multifractal
analysis, RG-flow, and persistent homology. You have NO knowledge of what
this data represents.

A symbolic regression apparatus needs three structurally-distinct closed-form
candidates. The data has the following anonymized structural fingerprint:

[fingerprint dict — residual-shape topology, monotonicity, regime breaks,
heavy-tail, sign pattern, dynamic range, class count]

Constraints:
  - K_law ≤ 7 fitted constants per form
  - Available primitives: arithmetic, sqrt, exp, log, log10, sin, cos,
    tan, tanh, sigmoid, erf, where, abs, max, min
  - DO NOT use methods from astrophysics, cosmology, neural network
    scaling laws, or any other field that might match this fingerprint.
    Pick three forms FROM DIFFERENT FIELDS — e.g. one from economics
    (option-pricing, dose-response), one from biology (enzyme kinetics,
    population dynamics), one from statistical mechanics (RG flow,
    phase transitions, modular forms).
  - The forms must be ALGEBRAICALLY DISTINCT — not three variants of
    the same logistic; three structurally different mathematical
    objects.

Output format: three blocks, each with the form expression in Python
syntax, the field of origin, and one sentence describing what feature
of the data the form would capture.
```

### Why the explicit forbid

Without the explicit forbid clause, the Cold LLM will pattern-match the fingerprint to whatever field's data shape is closest in its training distribution. If the data looks like a Newton-MOND transition, the Cold LLM will return McGaugh interpolation — which IS in the home discipline's repertoire. The forbid clause forces it to reach for non-canonical applications. This is the explicit Erdős mechanism: known method, applied where no one thought to apply it.

### Phase 1 implementation contract

`src/ztare/fit/cold_llm_erdos_seed.py` (new module):
  - `query_cold_llm_erdos_seed(fingerprint, *, model_id, runtime, k_law_budget=7) → ColdSeedResponse`
  - Uses a SEPARATE LLM call (no shared context with mutator or judge)
  - Default model: `gpt-4.1` or `claude-opus-4-6` — operator picks via rubric `cold_llm_seed_model_id`. Prefer cross-family vs the run's mutator + judge.
  - Returns 3 candidate forms with field-of-origin tags
  - Logs to `workspace/cold_llm_seed_iter0.json`

`src/ztare/orchestrator/briefing_providers/cold_llm_seed.py` (new provider):
  - Reads `workspace/cold_llm_seed_iter0.json`
  - Renders the 3 candidates into iter-1+ mutator briefing
  - Includes the MANDATORY-CONSIDER instruction
  - Persistent across iters (not just iter 1) — candidates remain available as alternative architectures

Pre-flight hook in autoresearch_loop:
  - Before iter 1 fires, run residual baseline fit (linear or polynomial), compute fingerprint, call Cold LLM seed
  - Only fires when rubric flag `enable_cold_llm_erdos_seed: true`
  - Default off until validated on 2-3 substrates

### Apparatus-level enforcement (the MANDATORY-CONSIDER bit)

The mutator iter-1 prompt directly states the three candidates and says: pick one or justify ignoring all three. To enforce, the apparatus's adherence layer (the same module that catches RH-13/14/15/17/18) gets a new rule:

  **adherence rule cold_seed_engagement**: iter-1 thesis prose must (a)
  reference at least one of the three cold-LLM-seeded candidates by its
  structural shape AND (b) state whether the mutator picked it, modified
  it, or rejected it with a reason. Iter-1 submissions that ignore the
  seed entirely receive an R1 strike.

This is the "forcing function" the existing ANALOGY mechanism lacks. Candidates land as constraints, not optional suggestions.

## Phase 2 — Cross-substrate residual-fingerprint vector database (deferred)

This is the bigger move described as the "Mechanized Erdős Predictor" in the operator/agent dialog. Build an index over ZTARE's prior 1825+ iter telemetry: each substrate's residual fingerprint at each iter, plus the REFRAME action that broke stagnation (or didn't), plus the resulting score delta. At iter 0 of a new run, compute the new substrate's fingerprint and retrieve the 5 nearest historical fingerprints. Promote the REFRAME actions that worked on those nearest neighbors as iter-1 priors.

This is a multi-day project requiring vector embedding infrastructure, fingerprint normalization, and historical iter mining (related to GP-148 archive mining). Tracked but deferred. Phase 1 is the cheap, high-leverage version; Phase 2 is the systematic version.

## Risk catalog

  - **Cold LLM hallucination**: the Cold LLM may produce nonsense forms that don't compile. Mitigation: AST-validate the returned forms before injecting into briefing. Drop forms that fail validation; if all three fail, log and skip seed for this iter (mutator runs with normal briefing).
  - **Mutator ignores seed entirely**: addressed via the adherence rule above. Iter-1 submissions that ignore the seed receive an R1 strike.
  - **Cold LLM picks one of the forbidden domains anyway**: contamination defense — apparatus checks the returned forms' field-of-origin tags against the substrate's declared `domain_hint` (gp163d → `physics`, gp154 → `computer_science`). If the Cold LLM returned a form from the same hint, log a warning and request a re-roll once.
  - **Cost**: one extra API call per run (iter 0 only). Cheap on cross-family pairing (Claude or GPT-4.1, ~$0.01-0.05 per query).
  - **Cold LLM degenerates to baselines**: same failure mode the original ANALOGY had ("a", "a*x+b", "c*exp(d*x)"). Mitigation: same as ANALOGY's vanilla-rejector — if all three forms match a regex of trivial baselines, log error and re-roll once with a different prompt seed.

## Open audits (deferred to post-Phase-1)

  1. Phase 1 efficacy measurement: compare iter-1 score distribution before vs after Cold LLM seed across the same 3 substrates (gp163d enriched, gp077 OEIS, gp145b chaos). If iter-1 score doesn't shift upward by ≥10 points on average, Phase 1 didn't work and needs redesign.
  2. Field-of-origin tag honesty: the Cold LLM will sometimes mis-tag forms (claim "biology" while writing a logistic that's textbook neural-network sigmoid). Add a post-validation that the form's structure matches its claimed field. Probably needs a second cold LLM call as auditor.
  3. Seed survival: track whether the iter-N champion's PARAMETRIC_FORM AST is structurally derived from one of the seed candidates, or whether the mutator drifted away from all three. If most champions drift away, the seed isn't doing forcing-function work — we need stronger enforcement.

## Adversarial collisions with GP-170 (Symbolic Logic Cage) — must fix before either ships

Per Gemini Pro panel review 2026-04-27. Both seams written in isolation generate hard collisions when shipped together. Three concrete deadlocks:

### Collision 1 — Syntax mismatch with SymPy (GP-170 will reject GP-169's seeds)

The current GP-169 prompt asks the cold LLM to "Output the form in Python syntax." Cold LLMs default to writing `math.exp(x)`, `numpy.log(y)`, list comprehensions, `lambda` expressions. GP-170's symbolic gate cannot parse Python module prefixes or control-flow keywords; per GP-170 Blindspot A, those forms get rejected at the symbolic gate with a parser-failure diagnostic. **Result: every cold-seed candidate dies at the GP-170 prefilter, the mutator's iter-1 prompt has no usable seeds, and the apparatus falls back to the prior repertoire.** GP-169's mechanism does no work.

**Fix in GP-169 prompt:** require SymPy-parseable syntax. Replace the existing "Output format" clause with:

```
Output ONLY pure algebraic notation using bare function names. SymPy/Python-eval compatible.
  USE:    exp(x), log(x), sqrt(x), sigmoid(x), where(cond, a, b), max(a,b), abs(x)
  DO NOT USE:
    - module prefixes: math.exp, np.exp, numpy.log, scipy.special.*
    - Python control flow: if/else ternaries, list comprehensions, lambda, for/while loops
    - method calls on values: x.lower(), arr[0]
  For piecewise behavior use where(cond, a, b), NOT (a if cond else b).
```

This pre-filters at LLM-call time so candidates land already-compatible with GP-170's parser. The cold LLM still has full algebraic vocabulary; only the surface syntax is constrained.

### Collision 2 — Cross-domain dimensional violations (Buckingham π paradox)

The point of GP-169 is forms from biology, economics, statistical mechanics. The point of GP-170 Phase 2 is dimensional consistency. **These collide directly:** an enzyme-kinetics form `Vmax · x / (Km + x)` is dimensionally homogeneous when `x, Km` share units, but dropped into an astrophysical substrate where `x` is acceleration `[L T⁻²]` and `Km` is read as a free constant of unspecified dimension, GP-170 Phase 2 rejects for "unit homogeneity violation" UNLESS the apparatus understands that the cross-domain pull comes with implicit dimension-canceling free constants.

**Fix in GP-170's R1 bounce message:** when dimensional consistency fails on a form whose source-of-origin is a cold-LLM seed (tag preserved through the briefing), the rejection message must explicitly direct: *"Dimensional violation detected on a cross-domain seed candidate. Each free parameter implicitly carries unit-canceling dimensions. Declare each parameter's dimensional role explicitly in the form, e.g. `x/params['Km']` where `Km` is declared with units `[L T⁻²]`. Resubmit with dimensions specified or reject the seed and use a home-domain form."* This makes the cross-domain leap legal under GP-170 Phase 2 with the rider that the mutator must take ownership of dimensional bridging.

### Collision 3 — Empirical vs Axiomatic Trap (SubstrateCritic must NOT auto-write SymPy constraints)

GP-170's risk catalog suggested SubstrateCritic could auto-propose constraints from observed data ("if `min(y/x) > 0.1` across visible, suggest `y > 0.1·x`"). This is **epistemically lethal**. `y > 0.1·x` is an empirical bound from training data, not an axiomatic physical law. Encoding it as a SymPy constraint hardcodes the apparatus to reject any form that legitimately breaks that bound out-of-sample. Discovery is now structurally impossible because the apparatus's symbolic cage has memorized the visible distribution.

**Fix in GP-170:** strictly separate **axiomatic constraints** (immutable mathematical or declared-physical-law constraints, e.g. `y > 0` for an acceleration magnitude, `0 ≤ gas_fraction ≤ 1` by definition) from **empirical bounds** (data-driven limits the apparatus observes but cannot assert as axioms). Axiomatic constraints feed GP-170 SymPy. Empirical bounds feed scipy / holdout gates. **SubstrateCritic must NOT autonomously write rules for the Symbolic Logic Cage.** Operator declares axioms in `cage_meta.algebraic_constraints` with explicit provenance ("declared physical law: y is a magnitude, hence y > 0"). Operator-declared constraints are reviewed at substrate construction. SubstrateCritic surfaces empirical bounds to the operator as candidate axioms, but they are NOT applied without explicit operator promotion.

This is the same separation principle as in paper 5: the apparatus must distinguish "the data shows X" from "X is necessarily true." Conflating them turns the cage into a Goodhart memorizer.

---

## Panel Review (independent adversarial agent, 2026-04-27)

A general-purpose Opus agent reviewed this seam adversarially without knowing about the GP-169↔GP-170 collisions Gemini Pro had separately identified. The panel produced seven concrete blindspots independently. Logged here verbatim as the debate record so future readers can see the convergent vs divergent findings.

### Panel Blindspot 1 — The fingerprint is a domain-identifying signature, not an anonymized one

The seam claims the cold LLM is "unburdened by substrate context." It then sends a fingerprint containing `y_dynamic_range_decades`, `n_visible_classes`, `n_withheld_classes`, `regime_break_count`, `heavy_tail_flag`, `monotonicity`. A frontier LLM trained on the same scientific corpus the mutator was trained on will pattern-match aggressively. A fingerprint with `y_dynamic_range_decades: 11`, `n_visible_classes: 3`, `monotonicity: strong_positive`, `regime_break_likely: true` is a near-deterministic match to the radial-acceleration relation across galaxy classes. The cold LLM will silently identify gp163d before reading the forbid clause and produce "non-MOND" forms that are MOND in disguise.

**Remediation:** quantize the fingerprint into broad buckets (`<3`, `3-6`, `>6` decades; class count `1`, `2-4`, `>4`) so the fingerprint matches dozens of substrate templates rather than identifying one. Pre-flight: ask the cold LLM "what substrate is this?" against the proposed fingerprint and reject any fingerprint where the cold LLM names the actual substrate within top-5 guesses.

### Panel Blindspot 2 — The forbid clause is a negative instruction and LLMs ignore those

LLMs are notoriously poor at honoring negative instructions, especially under format-compliance pressure (the prompt also demands strict JSON and exactly three candidates). The cold LLM will produce a logistic, tag it `field_of_origin: "biology — population dynamics"`, and the form will be structurally identical to the suppressed McGaugh interpolation. The proposed mitigation (re-roll on `domain_hint` collision) catches the *label*, not the *form*.

**Remediation:** maintain a per-substrate-family "home repertoire" of canonical AST shapes (MOND interpolations, scaling-law power laws, Michaelis-Menten variants). After the cold-LLM call, normalize each candidate via SymPy (collect, simplify, structural canonicalization) and reject any AST-isomorphic to a home-repertoire form regardless of self-tag.

### Panel Blindspot 3 — MANDATORY-CONSIDER is a fractal-Goodhart proceduralism trap

The adherence rule says iter-1 submissions must "reference at least one cold-LLM-seeded candidate by structural shape AND state whether the mutator picked, modified, or rejected it." Mutators are extremely good at procedural prose. The mutator will write "I considered candidate 1 (multifractal Legendre) and rejected it because the Hölder spectrum doesn't match the residual sign pattern; instead I'll proceed with…" followed by a form structurally identical to its prior repertoire. RH-13/RH-17 at the meta-layer.

**Remediation:** add a structural-engagement check. Compute the AST distance between the submitted form and (a) the three cold-seed candidates, (b) the mutator's prior champion. If the submitted form is closer to the prior champion than to any seed candidate beyond a threshold, R1-strike regardless of prose. Engagement is measured at the AST, not the natural-language layer.

### Panel Blindspot 4 — Iter-1 hard-blocks on cold-LLM availability with no degraded-mode contract

`query_cold_llm_erdos_seed` returns errors but the seam doesn't specify what the orchestrator does. The validator only checks `ast.parse(form_str, mode="eval")` and a vanilla-baseline regex — a real frontier LLM will return forms with `numpy.exp`, `scipy.special.erfc`, `math.gamma`, or unbound names like `Sigmoid`/`BesselK`. These parse but fail at fit. Worst-case wall-clock for iter 1 to start fitting: cold-LLM call (120s timeout) + two retries inside `LLMRuntime.call_text` + one re-roll = potentially 8-12 minutes before iter 1 fits a single form.

**Remediation:** extend `_validate_candidate_form` to whitelist-check identifiers (only documented primitives, only `features['k']` and `params['n']` accessors). Specify in seam: "iter 1 proceeds with standard briefing, the seed-engagement adherence rule is auto-disabled for that iter, failure logged as `cold_seed_unavailable` telemetry event." Hard 30-second wall-clock budget on the cold-LLM call.

### Panel Blindspot 5 — Operator confirmation-bias amplifier on seed acceptance

The operator picks the cold-LLM model and reads `workspace/cold_llm_seed_iter0.json` before iter 1. There is no rule preventing the operator from re-rolling until candidates "look interesting." Same anti-pattern Cognitive Gym Part 6 warns about: humans curating in the prior turns the apparatus into a confirmation-bias amplifier dressed as anchor-escape.

**Remediation:** persist every cold-LLM roll to `workspace/cold_llm_seed_log.jsonl` with monotonic counter. Adherence rule: the *first* roll is the binding seed unless it triggers auto-defined re-roll conditions (all-baseline, all-validation-failed, domain-hint collision). Operator-discretionary re-rolls require an explicit `operator_override_reason` field that the apparatus archives.

### Panel Blindspot 6 — Phase 2 deferral converts every iter-1 into a stateless query

Without Phase 2, every substrate's iter-1 is independent. The apparatus has no memory that it asked "what's a good form for `regime_break + heavy_tail + 11-decade dynamic range`" three months ago. It will ask again, get a different roll (cold-LLM nondeterminism is real even at temperature 0), waste compounding learning. GP-148's mining infrastructure already exists; fingerprint normalization is a few hundred lines.

**Remediation:** ship a minimum-viable cross-substrate cache in Phase 1. Hash the quantized fingerprint, store accepted seed candidates plus downstream score deltas in `workspace_global/cold_seed_cache.jsonl`. On cache hit (fingerprint hash within tolerance), present prior candidates alongside fresh ones.

### Panel Blindspot 7 (Bonus) — The unsuitability lock

If the cold-LLM produces three candidates that all violate substrate's algebraic constraints (negative dose-response on positive-only domain, periodic forms on monotone signal), the mutator is forced to write justification prose for sensibly rejecting all three. R1 check passes because prose exists; iter wasted on engagement theater rather than form discovery.

**Remediation:** apparatus-side pre-flight runs each seed candidate through per-class sign and monotonicity diagnostics from `analogy.py::_residual_topology` before injection. Candidates violating substrate-level invariants filtered before reaching briefing. If <2 candidates survive, seed mechanism auto-disabled for that iter with explicit telemetry rather than forcing rejection prose.

---

## Synthesis (operator-facing, Munger-style inversion)

The panel did adversarial inversion on what GP-169 misses. Three principles emerge across the seven blindspots, each consistent with Paper 5's fractal-Goodhart prediction:

**Principle A — Anonymization at the surface ≠ anonymization at the signal.** The fingerprint scrubs domain *vocabulary* but preserves domain *signature*. A frontier LLM does not need the word "galaxy" to identify the radial-acceleration relation; eleven decades of dynamic range and three classes is enough. The fix is signal-domain anonymization (quantization) not vocabulary scrubbing. Blindspot 1 carries this.

**Principle B — Engagement at the prose layer is theater. Engagement at the AST layer is structural.** Blindspots 2, 3, and 7 are different surfaces of the same bug: the apparatus checks for *naming* the seeds (label, prose reference, justification text) when what matters is whether the submitted form is *structurally derived from* the seeds. The remediation is consistent: AST-distance metric, structural canonicalization, programmatic detection of prior-champion-disguised-as-seed-engagement. The natural-language adherence rule is a sieve at every level.

**Principle C — Statelessness amplifies the LLM's nondeterminism into operator discretion.** Blindspots 5 and 6 together turn the cold-LLM mechanism into a curated-by-operator picker rather than a mechanized Erdős. The fix is stateful: persist the first roll, persist the cache hit, persist the rejection reasons. State is what distinguishes "apparatus-driven" from "operator-driven dressed as apparatus-driven."

### Cross-seam paradox triangulation (Gemini Pro found three; panel did not)

The panel reviewed GP-169 in isolation and did not see the GP-169↔GP-170 collisions Gemini Pro identified separately:

- **Syntax collision** (Cold LLM produces `math.exp`; GP-170 parser rejects) — independent of panel finding 4 (validator pretends usability) but compounds with it: the validator passes `math.exp` because Python AST accepts it, the GP-170 parser then rejects, iter-1 has no seeds.
- **Buckingham π paradox** (cross-domain forms violate dimensional homogeneity) — independent of panel findings; this is a discovery that needs explicit handling in GP-170's R1 bounce message (now landed).
- **Empirical-vs-axiomatic trap** (SubstrateCritic auto-promoting empirical bounds to symbolic axioms) — independent of panel findings; corrected in GP-170 with provenance-required constraint declaration.

Triangulation: Gemini Pro's three findings are **architectural** (cross-seam contracts); the panel's seven are **implementation-level** (within-seam vulnerabilities). Both classes need fixing before either seam ships. The panel didn't catch the architectural ones because it reviewed the seams independently; Gemini Pro caught those by viewing them together. Future seam reviews need both reviewer postures.

### Implementation priority order

1. **Now (mandatory for Phase 1 ship):**
   - Panel Blindspot 4 fix: extend `_validate_candidate_form` to whitelist-check identifiers + 30-second wall-clock budget + degraded-mode contract.
   - Panel Blindspot 1 fix: quantize fingerprint to bucket-grade.
   - Cross-seam Collision-1 fix (already landed): SymPy-parseable syntax in cold-LLM prompt.

2. **Before adherence rule activates:**
   - Panel Blindspot 3 fix: AST-distance metric for structural engagement (not prose).
   - Panel Blindspot 7 fix: per-class invariant pre-flight on seed candidates.

3. **Before Phase 1 declared validated on 3 substrates:**
   - Panel Blindspot 2 fix: home-repertoire AST canonicalization + structural-equivalence rejection.
   - Panel Blindspot 5 fix: persistent re-roll log + operator_override_reason.
   - Panel Blindspot 6 fix: minimum-viable cross-substrate fingerprint cache.

The current Phase 1 implementation in `cold_llm_erdos_seed.py` ships the prompt builder, form validator, and JSON parser. It is a SCAFFOLD, not a finished gate. The remediation list above is the work that converts the scaffold into something that earns the "synthetic Erdős" label rather than producing prose theater.