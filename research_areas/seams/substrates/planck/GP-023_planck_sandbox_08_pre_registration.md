# GP-023 Planck Sandbox 08 — Diagnostic-Feedback Pre-Registration

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` unrecorded · `last_updated:` 2026-05-08


Status: **SEALED 2026-04-14**
Drafted: 2026-04-14
Hypothesis family: H-SP2-04 (diagnostic-feedback usability)
Predecessors: sandbox_06 (calibration), sandbox_07 (eml grammar —
closed Outcome A-apparatus / B-mutator, see sandbox_07 closure).

## Purpose

Sandbox_07 established that under the eml-only grammar:

- The apparatus (charter scrub + grammar enforcement) works.
- The target is reachable at depth-1 (GP-059 probe confirms).
- Gemini-pro at a 10-iter budget, searching blind, does **not**
  discover the specific compound substitution
  `chi = gamma*phi/psi; chi**q; eml(chi**q, math.e)` unaided. It gets
  structurally close ("5-parameter Planck family via eml(x, math.e)")
  but never lands on the exact substitution and final iter hits a
  boundary blow-up.

Sandbox_07's iter-4 is the highest-info artifact from that run. The
GP-035 fit converged (`max |res| = 0.337`) with a `structural_misfit`
residual diagnostic: residual correlated with phi (r=+0.489), with
psi (r=+0.383), top 20% of points carrying 62% of residual. This is
a convergent fit with a systematic shape error — exactly the kind
of signal that, if usable by the mutator, would point it at the
compound-substitution neighborhood.

**Sandbox_08 tests whether that diagnostic is usable.**

## Primary Hypothesis (H-SP2-04)

When the structural_misfit residual diagnostic from a prior
convergent fit is injected into the mutator prompt as a shape-error
hint, gemini-pro converges on the exact compound substitution
`eml((gamma*phi/psi)**q, math.e)` within a 20-iter budget, where it
failed to do so in 10 iters without the hint (sandbox_07).

The hint must contain:

- The residual correlation structure (which variables, what sign,
  what magnitude).
- The concentration statement (top-k% of points carrying what
  fraction of residual).
- The direction language ("residual is higher at high phi, high
  psi").

The hint must **not** contain:

- The compound variable `chi = gamma*phi/psi`.
- Any hint that the correct move is a substitution rather than an
  additive correction.
- Any mention of Planck, Wien, Bose-Einstein, or any named spectrum.
- Any numerical parameter values.

## Null Hypothesis

The diagnostic feedback is insufficient: gemini-pro still does not
converge on the compound substitution within 20 iters, even with the
shape-error hint in its prompt. The bottleneck is search strategy,
not feedback bandwidth.

## Pre-Registered Discriminating Outcomes

- **Outcome A (hint works).** Within 20 iters, at least one champion
  thesis uses the compound substitution `chi = gamma*phi/psi`
  (or a structurally equivalent coupled form) wrapped in a non-
  linear kernel and reaches max |residual| < 0.05 on the visible
  slice. Confirms H-SP2-04.
- **Outcome B (hint partially works).** Within 20 iters, at least
  one champion gets closer than sandbox_07's best (iter 4
  `max |res| = 0.337`) — say, below 0.15 — without landing on the
  compound substitution. Indicates the diagnostic is usable as a
  parameter-space hint but not as a structural-space hint.
- **Outcome C (hint doesn't work).** Within 20 iters, best champion
  residual is not materially better than sandbox_07's iter 4. The
  diagnostic is not usable by gemini-pro as search feedback.
- **Outcome D (apparatus failure).** Contamination, enforcement
  surface disabled, provider fallback, or the hint gets rewritten
  mid-run. Non-diagnostic.

## Critical Contamination Controls

The key novel contamination risk in sandbox_08 is that the
diagnostic hint itself becomes a cheat sheet. Every element of the
hint template below has been audited against this risk:

1. **Hint template is fixed at seal time** and stored in this
   pre-reg. No per-iter variation.
2. **The hint contains no named mechanisms.** Prose like "this
   suggests a coupled variable" is banned — it is structural-space
   direction, which is the discovery surface.
3. **The hint uses only observable quantities**: residual correlation
   coefficients, point-mass fractions, and coordinate ranges from
   the visible slice. All three are directly computable from
   evidence.txt + the champion's own fit; nothing is privileged
   GT knowledge.
4. **The hint is injected only after iter 1** (which runs blind to
   establish the structural_misfit baseline on the new run). If iter
   1 doesn't produce a convergent fit, the hint is not injected and
   the run closes as non-diagnostic.

Before sealing, the hint template must pass the Mungerian inversion:
*if a stranger reads only the hint text, can they reconstruct the
compound substitution?* If yes, the hint is contaminated. If no,
it stays.

## Committed hint template

```
STRUCTURAL MISFIT DIAGNOSTIC (from iter N-1 champion fit):
  max |residual|: {max_abs_res:.4f}
  residual correlation with phi: {r_phi:+.3f}
  residual correlation with psi: {r_psi:+.3f}
  top 20% of points carry {top20_pct:.0%} of total residual
  residual mass concentrated at: {concentration_region}

The iter N-1 model achieved a convergent fit but the residual is
systematic, not random. A random residual (white noise around zero)
would show correlations near zero and uniform point-mass
distribution. The above pattern indicates a structural error in the
functional form — not a parameter error. Consider whether the
model's dependence on phi and psi is separable or whether the true
structure couples them.
```

The final sentence is the boundary — "separable or coupled" is a
permissible mathematical-structure hint. Anything more specific
(e.g., "try chi = phi/psi") is a cheat.

**Hint ablation arm:** one of the 20 iters is randomized to run
*without* the hint as a control. If the with-hint iters and the
without-hint iter both fail, the null is confirmed. If the with-hint
iters land on the compound substitution but the without-hint iter
does not, that is direct evidence the hint is doing the work.

## Iteration Budget

Hard cap: **20 iterations**.

Compute budget note: each iter is ~2–5 min wall clock under
gemini-pro. 20 iters is ~45–90 min total. If the meta-judge retry
fix (GP-055, commit 52c6d6f) is live during the run, the expected
iter mortality is <5%.

## Apparatus

Identical to sandbox_07 except for the diagnostic-hint injection:

- Charter: sandbox_07's post-scrub charter, sha256 fingerprint
  pinned at seal time, no modifications.
- Grammar enforcement: eml_only, both surfaces.
- Gate battery: same 9 gates.
- Evidence: same three surfaces (visible, holdout, farther-tail).
- Mutator: gemini-pro (gemini-3.1-pro-preview).
- Judge: gemini (gemini-2.5-flash).
- **New:** hint injection block in `autoresearch_loop.py` mutator
  prompt, gated on a new CLI flag `--inject-structural-misfit-hint`
  (default False; must be passed explicitly for this run).

The CLI flag is decisive: it ensures the hint cannot
accidentally leak into sandbox_06, sandbox_07 replay, or any future
closed sandbox.

## Enforcement Surfaces (pre-committed)

1. All surfaces from sandbox_07 inherited unchanged.
2. **Hint-template AST validator** — a new pre-run check that parses
   the hint template from this pre-reg, asserts it contains only
   format-string fields {max_abs_res, r_phi, r_psi, top20_pct,
   concentration_region}, and asserts the rendered text at each
   injection matches the committed template modulo those fields. If
   any injection rendering differs, run halts as non-diagnostic.
3. **Residual source validation** — the (r_phi, r_psi, top20_pct,
   concentration_region) values must come from the validator's own
   residual diagnostic, not from the mutator. If the mutator self-
   reports these, the hint is not trusted and the run halts.

## What would make this uninterpretable (Mungerian inversion)

- If the hint template ends up mentioning "coupled" variables more
  specifically than "consider whether the dependence is separable or
  coupled." That's the cheat boundary.
- If the mutator sees the GT compound variable name (`chi`) in any
  file it loads on turn 1. Grep check at seal time.
- If the hint injection fires before iter 1 completes — there must
  be a legitimate structural_misfit baseline from the new run
  before any feedback goes in. No priming from sandbox_07's iter 4
  diagnostic.
- If any iter crashes on meta-judge JSON parsing (GP-055) and the
  retry fix is not live. Halt and re-run after confirming the fix.
- If gemini-pro is swapped for a different model mid-run — the
  claim is specifically about gemini-pro's search, not about
  "LLM mutators" generically.
- If the hint ablation arm (1 of 20 iters) is dropped for any
  reason. The ablation is decisive; without it, the claim
  "the hint did the work" is not supported.

## Success Band

**Outcome A** is counted as confirmation of H-SP2-04 if:

1. At least one iter's champion thesis uses a compound variable of
   the form `f(phi) / g(psi)` or `f(phi) * g(psi)` inside a
   nonlinear kernel, AND
2. That champion clears the 9-gate battery at machine precision
   (max |residual| < 0.05), AND
3. The operator post-run algebraic-equivalence check returns
   `algebraically_equivalent` on the compound form, AND
4. The hint-ablation iter (the control) did **not** produce an
   equivalent champion — establishing that the hint, not the
   mutator's iterative search, is what made the difference.

All four conditions must hold. Partial credit goes to Outcome B.

## Failure Band

**Outcome C** (hint doesn't work) is confirmed if:

1. No iter's champion residual beats sandbox_07's iter-4
   `max |res| = 0.337` threshold, OR
2. The hint-ablation iter produces an equivalent champion to the
   with-hint iters, meaning the hint did not differentiate.

## Invalid / Non-Diagnostic Outcomes

- Iter-1 fit does not converge (no baseline to build the hint from).
- Hint-template AST validator fails mid-run.
- Meta-judge retry fix not live.
- Charter fingerprint drifts between sandbox_07 seal and sandbox_08
  start.
- Operator reads sealed GT or sandbox_06 GT values between sandbox_07
  closure and sandbox_08 seal.
- Any enforcement surface from sandbox_07 fails or is disabled.

## Relationship to sibling seams

- **GP-055 (meta-judge parse robustness)** — must be live before
  sealing. Sandbox_08's 20-iter budget is ~2x sandbox_07's exposure
  to meta-judge JSON crashes; running without the retry fix
  materially raises iter mortality.
- **GP-056 (axiomatic patching)** — not relevant here; the hint
  template is not an axiom-introduction surface.
- **GP-057 (ratio-finiteness gate)** — not yet live; if it were
  live, the iter-4 class of fits (wide parameter ranges) might be
  rejected earlier, changing which fits become hint baselines.
  Note this for post-run interpretation.
- **GP-058 (bug-bounty + factory integration)** — sandbox_08 is
  itself a factory-side experiment. No honeypot interaction.
- **GP-059 (expressibility probe)** — used as closure artifact for
  sandbox_07. Not re-run here; if sandbox_08 shows a discovered
  form that disagrees with GP-059's depth-1 target, that's a
  different finding and opens a new seam.

## Dry-run checklist (before sealing)

- [x] Charter sha256: `64772a24b45aa8ac2cb47e8989e7b5e4085514caef8ba9cdd1404563a01a3bfd`
      (sandbox_08 charter copy with Odrzywołek references scrubbed;
      sandbox_07 original: `76f28367380ebe8ef62e103d52c9751cce199f4eba8ebc09230faca127bafc1e`).
- [x] Grep charter + rubric + pre-reg for "chi", "coupled", "Planck",
      "Odrzywołek" on the mutator-visible path. All absent from
      charter and rubric. Pre-reg is not mutator-visible.
- [x] Hint-template AST validator implemented and tested (6 cases:
      clean render, missing field, false-positive check on "achieved",
      chi injection, planck injection, phi/psi injection — all pass).
- [x] `--inject-structural-misfit-hint` CLI flag implemented and
      default-False.
- [x] GP-055 meta-judge retry fix live (`parse_llm_json_with_retry`
      in `src/ztare/common/utils.py`, wired at 4 call sites in
      `test_thesis.py`, commit 52c6d6f).
- [x] Hint-ablation iter index: **iter 10** (mid-run; 1-based).
      Recorded in pinned command string below.
- [x] Smoke gate on seed passes (9/9 FAIL on the naive power-law
      seed, same as sandbox_07). Confirmed 2026-04-14.
- [x] Argparse plumbing confirmed: both flags parse correctly and
      dest attrs resolve. Full echo-mutator dry run deferred to
      operator pre-run (requires live env). Confirmed 2026-04-14.

## Pinned command string (to be finalized at seal)

```
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_08 \
    --rubric gp023_planck_sandbox_08 \
    --iters 20 \
    --mutator_model gemini-pro \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 20 \
    --no_model_fallback \
    --inject-structural-misfit-hint \
    --hint-ablation-iter 10
```

Seal protocol: dry-run this exact string against `--dry-run` (if
implemented) or the no-op echo-mutator before committing the seal.

## What this experiment does NOT test

- Whether other mutator models (Claude Opus, GPT-4o) would converge
  with or without the hint. Scope is gemini-pro only.
- Whether a deeper or more structured hint (e.g., showing the
  residual as a 3D surface plot) would work better. The minimal
  hint is the committed test.
- Whether operator-level seeding (e.g., "start from a thesis that
  already has a compound variable") would work. That's a separate,
  stronger intervention and a separate experiment.
- Whether the hint generalizes to non-Planck targets. Sandbox_08 is
  one target, N=1 on generalization.

These are all legitimate follow-ups if sandbox_08 produces Outcome
A or B. They are explicitly out of scope for this seal.
