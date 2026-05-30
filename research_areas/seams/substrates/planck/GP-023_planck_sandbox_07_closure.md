# GP-023 Planck Sandbox 07 — Closure Note

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` unrecorded · `last_updated:` 2026-05-08


Status: closed 2026-04-14
Primary outcome: **D (H-SP2-03 refuted as stated) + corrected reading**
Pre-reg: `GP-023_planck_sandbox_07_pre_registration.md`
Run: 10 iters, mutator `gemini-pro` (gemini-3.1-pro-preview),
judge `gemini` (gemini-2.5-flash), 2026-04-14 19:47–21:20 PT.

Per AGENTS.md §7: sealed artifacts are never edited in place.
Closures live in post-mortem files. This is the post-mortem.

## Primary verdict

**Outcome D** — the run closed with every iteration scoring 0 against
the 9-gate battery. Champion tracker never left the iter-0 seed. The
pre-registered refutation condition is met: *"H-SP2-03 is refuted if
gates do not clear at machine precision under a valid run with the
committed iteration budget and enforcement surfaces active."*

The run was valid. Smoke gate passed pre-run, charter-contamination
fix held (no iter-1 transcription like the two prior killed runs),
enforcement surfaces (fit_primitive grammar + autoresearch_loop AST
validator) both fired on every iter, no provider fallback, no
sealed-holdout leakage.

So **H-SP2-03 as stated is refuted**: gemini-pro did not recover the
Planck GT form under the eml-only grammar within 10 iters.

## Corrected reading — what the refutation actually means

The as-stated hypothesis conflates two claims:

1. **Apparatus claim.** The depth-1 Odrzywołek representation
   `eml((gamma*phi/psi)**q, math.e)` is reachable under the committed
   eml-only grammar.
2. **Mutator claim.** A general-purpose LLM mutator (here: gemini-pro)
   can discover that representation within the 10-iter budget under
   ZTARE gate pressure.

The refutation touches claim (2), not claim (1). Evidence:

**GP-059 expressibility probe** (`research_areas/private/probes/gp059_eml_expressibility_check.py`, run 2026-04-14 post-closure) directly fits the depth-1 form
`A * phi**p / eml((gamma*phi/psi)**q, math.e) + offset` to the
sandbox_07 visible slice from a blind initial guess using
`scipy.optimize.curve_fit`. The fit recovers the sealed GT at
six-decimal precision:

```
A      = 0.950002  (sealed: 0.95)
p      = 2.299999  (sealed: 2.30)
gamma  = 0.720000  (sealed: 0.72)
q      = 1.300000  (sealed: 1.30)
offset = 0.059999  (sealed: 0.06)

max |residual|  = 0.000007  (gate threshold 0.05)
```

The target **is** reachable at depth-1 under the committed grammar, to
a residual four orders of magnitude under the visible-slice gate. The
apparatus claim is confirmed, not refuted.

The mutator claim is what failed. Gemini-pro, across 10 iters +
retries, never proposed the specific compound substitution
`chi = gamma*phi/psi` wrapped in an exponent `q` and handed to
`eml(·, math.e)`. It got structurally close — the semantic-gate
observation for iter 10 records a final thesis of *"projecting the
eml(x, math.e) transform onto the fully decoupled 5-parameter Planck
family"* — but the proposed model hit non-finite values at phi=0.05,
psi=0.6 (boundary blow-up, fail-closed). No iter landed on the exact
compound variable construction.

## Corrected outcome taxonomy entry

Rather than a bare Outcome D, the closure records this as:

- **Outcome A** on the **apparatus** claim (charter contamination fix
  holds; eml-only grammar enforcement holds; target is reachable
  under the committed grammar at depth-1).
- **Outcome B** on the **mutator-search** claim (gemini-pro at
  10-iter budget does *not* discover the compound substitution
  unaided; this is the genuine negative, not an apparatus bug).

Both subclaims are closed with evidence. Neither needs re-running in
its current form.

## What carries forward

Three standing findings survive this run:

1. **Charter contamination fix is production-proven.** Three seals on
   the same packet, the third holds. Rule from the second-kill patch
   note is now a standing project rule.
2. **Iter-4 structural_misfit diagnostic is the highest-info artifact
   from the run.** GP-035 fit converged with `max |res| = 0.337` and
   residual correlated with phi (r=+0.489) and psi (r=+0.383), top
   20% of points carrying 62% of residual. This is a convergent fit
   with a shape error — exactly the signal the farther-tail and
   structural-misfit gates are designed to expose. Whether gemini-pro
   can *use* this diagnostic as search feedback is a separate claim
   that sandbox_08 will test.
3. **Grammar lock-down is not over-specified.** GP-059 probe confirms
   depth-1 reachability. Any future sandbox claiming "mutator failed
   because grammar was too tight" requires a similar probe before
   the claim is admitted.

## Anti-overfitting check

Is this closure retrospectively lowering the bar? Not quite. The
pre-reg specifies: *"H-SP2-03 is refuted if Outcome D occurs under a
valid run."* The run was valid, the outcome was D, and the formal
refutation stands. What the corrected reading adds is a *finer
decomposition* of the refutation, enabled by a separate probe (GP-059)
that was not part of the sealed test battery. The pre-reg's binary
verdict is unchanged; the informative structure behind the binary is
added in post-mortem.

This is the Mungerian check (AGENTS.md §6c): would a stranger reading
only this closure conclude that the hypothesis was moved to fit the
result? No — because the binary outcome still stands against the
sealed success criterion. The closure *adds* a discriminating
follow-up, it does not *revise* the pre-reg's grading.

## Artifacts

- `projects/gp023_planck_sandbox_07/` — full run directory, 17
  debate logs, iter-0 champion (seed), semantic_gate_observations
  jsonl, evidence files.
- `research_areas/private/seams/GP-023_planck_sandbox_07_pre_registration.md`
  — sealed pre-reg (unchanged).
- `research_areas/private/probes/gp059_eml_expressibility_check.py`
  — expressibility probe + run log.

## Next experiment

Open GP-023 sandbox_08 (see sibling file
`GP-023_planck_sandbox_08_pre_registration.md`) testing whether
structural_misfit residual diagnostic, injected as mutator feedback,
closes the gap between "structurally close neighborhood" and "exact
compound substitution" in the gemini-pro search.
