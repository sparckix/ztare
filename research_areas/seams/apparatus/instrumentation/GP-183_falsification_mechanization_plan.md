# GP-183 — Mechanizing the Research Director's falsification tests

> **Seam metadata** · `seam_id:` GP-183 · `track:` apparatus · `status:` active · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

**Opened:** 2026-04-28 afternoon, post-run-1777381378 audit
**Author:** Research Director (planning seam)
**Trigger:** iter 2 of run 1777381378 produced a Pareto-class form
that an adjacent reviewing LLM characterized as a new law of gravity.
Three Research-Director-driven adversarial tests falsified the
"new-law" claim within 30 minutes:
  1. The Lagrangian declaration collapsed to `q = single_background_var`
     (cosmetic substitution; no derivation content).
  2. Per-cluster radial MRE pattern was wrong-sign for chameleon
     screening (inner > outer rather than inner < outer).
  3. Ablation of `rho_local_log10` showed it contributed only ~10%
     of the fit improvement; mass + radius did most of the work.

Each of these is a deterministic test on artifacts the apparatus
already produces. The cost of running them by hand was 30 min of
Research Director time per candidate champion. The cost of running
them as a per-promotion gate is one Python call. **Mechanizing them
makes the Research Director redundant on these specific patterns**,
which frees the role for novel falsifications the gates cannot
anticipate.

## Phases (in shipping order)

### Phase A — Per-iter telemetry persistence (instrumentation foundation)

The falsification tests need per-iter history. Currently the apparatus
writes single-file `_latest.json` artifacts that overwrite per iter,
which makes post-run forensics expensive. Fix this first; everything
in Phase B and C reads these files.

| Task | What | Effort | Risk |
|---|---|---|---|
| A1 | `lagrangian_derivation_iter_NNN.json` per iter, plus `_latest` copy for backward compat | 15 min | low |
| A2 | `noether_nondegeneracy_iter_NNN.json` same | 15 min | low |
| A3 | `gp180_telemetry_iter_NNN.json` same | 10 min | low |
| A4 | `per_class_fit_audit_iter_NNN.json` (NEW — fits each free param per class, computes spread) | 60 min | medium |
| A5 | `cap_kind_iter_NNN.json` (persist the existing cap_kind classifier output) | 20 min | low |

### Phase B — Mechanize the falsification tests as cage gates

Each gate is a deterministic check that fires after fit completes and
flags a structural pathology. They do not compute new science; they
read artifacts Phase A produces.

| Task | Gate ID | What it catches | Effort |
|---|---|---|---|
| B1 | `G-LAGRANGIAN-NONTRIVIAL` | static E-L of declared L collapses to `q = single_background_var` (the iter-2 cosmetic-Lagrangian failure) | 90 min |
| B2 | `G-SCREEN-SIGN` | inner-cluster MRE > outer-cluster MRE (wrong-sign chameleon claim) | 60 min |
| B3 | `G-FEATURE-CONTRIB` | per-feature ablation: each feature's ΔMRE contribution must exceed a rubric-declared threshold (default 0.05); features below threshold are flagged as cosmetic | 90 min |
| B4 | `G-CROSS-CLASS-DEGEN` | per-class refit log_c spread > rubric-declared threshold (default 1 dex for K=1, 3 dex for K=4) | 60 min |

Each gate emits a structured verdict to `workspace/<gate_id>_iter_NNN.json`
and returns a `pass | warn | fail` status. The fit pipeline reads these
verdicts and applies cap rules:
- B1 fails → cap at 60 with reason `lagrangian_trivially_substituted`
- B2 fails → cap at 70 with reason `screen_sign_inverted`
- B3 fails → annotate cosmetic features, no cap (informational)
- B4 fails → cap at 75 with reason `cross_class_param_drift`

### Phase C — DSL tightening (preventive layer)

Phase B catches the patterns post-hoc. Phase C tightens the upstream
DSL so the mutator is less likely to produce them in the first place.

| Task | What | Effort |
|---|---|---|
| C1 | Rubric flag `require_nontrivial_lagrangian: true` activates B1 as a hard gate (skip-fit if L is trivial) | 30 min |
| C2 | Lagrangian worked-example briefing addition: explicit "DO NOT use harmonic-oscillator-around-feature pattern; the static E-L must have a non-trivial algebraic solution that is not a single-background substitution" | 20 min |
| C3 | GP-180 return code `lagrangian_trivially_substituted` when steady_state is `{q: <single background symbol>}` | 30 min |

### Phase D — Inversion-based research questions (philosophy + rubric mode)

The falsification framing generalizes. Instead of "find a form that
fits," ask "find what would falsify the planted baseline." This is a
new rubric mode.

| Task | What | Effort |
|---|---|---|
| D1 | Paper 7 §11.14 "Mechanizing the inversion: from find-a-fit to break-the-baseline" | 90 min |
| D2 | Rubric mode `falsification_search`: rather than searching for a form that beats the baseline on aggregate MRE, search for a form (or a substrate enrichment proposal) that *invalidates* the planted baseline on a specific gate. Mutator's job becomes attack, not synthesis. | 4-6 hours |
| D3 | Periodic Research Director "novel falsification" prompt: a separate role-agent run after every ~10 iters that tries to identify a pattern the existing gates do NOT catch | 2 hours |

### Phase E — Documentation + stand-up

| Task | What | Effort |
|---|---|---|
| E1 | Update `paper 7 §11.13` (already shipped) — covered | done |
| E2 | Annotate `test_model_baseline.py` as "Phenomenological Bridge v1" — covered | done |
| E3 | Update Research Director mandate (`org/mandates/research_director_mandate.md`) with the new gate catalog and the operator-authorization-override clause from today's planting | 30 min |
| E4 | Memory entry: feedback_falsification_mechanization | 15 min |

## What this plan accomplishes

After Phase B ships, the Research Director's role narrows to:
- Patterns the gates do NOT catch (novel falsifications)
- Cross-substrate replication (does this pattern hold on a different rubric?)
- Literature triangulation (anchor-set proposal, not anchor-set evaluation)

The gates become the apparatus's standing immune system. If a future
champion passes B1 + B2 + B3 + B4 + the existing R20-R24 + per-class
farther-tail thresholds, the *probability that it is a clever
phenomenology rather than a real law* drops substantially. Not to
zero — never to zero on a single substrate — but to a level where the
next adversarial test is cross-substrate generalization, not within-
substrate phenomenology detection.

## Cost-benefit

Phase A: ~2 hours, immediately useful for post-run forensics on every
future run. ROI begins on the next run.

Phase B: ~5 hours, catches the iter-2 false-positive class plus
related patterns automatically. ROI begins when the next run produces
a Pareto-class candidate.

Phase C: ~80 min, reduces the rate at which Phase B fires by making
the mutator avoid the patterns Phase B catches.

Phase D: ~6-8 hours, opens the inversion-search rubric mode and gives
the operator a way to direct the apparatus toward attacking the
baseline rather than synthesizing past it.

Total: 13-17 hours of focused work to mechanize the entire Research
Director-style falsification surface that today required manual
intervention.

## What this plan does NOT do

It does not eliminate the substrate-bottleneck. Iter 2 capping at
50 was rubric-correct on a substrate with cluster gas at single radii
only. No gate or DSL fix will make that substrate produce a real
chameleon-screening discovery. The plan above is about apparatus
hygiene; substrate enrichment is its own seam.

It does not eliminate the Research Director role. The gates catch
known patterns; novel ones still require the role. But the cadence
shifts from "after every promotion candidate" to "after every ~10
iters or when a structural anomaly surfaces."
