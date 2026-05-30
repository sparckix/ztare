# Pre-Registration — x_algo_goodhart_audit

**Status:** Sealed for run 2026-05-15. Principal-directed (Mode 1, principal-extension).
**Filed:** 2026-05-15 (before any iteration spend).
**Substrate class:** Qualitative audit (GP-075-degraded GP-072 — GT genuinely unknown,
no sealed answer to protect; Division A/B information barrier is **not applicable**
because there is no ground-truth formula being hidden).

## 1. Eigenquestion (operative, code-structural)

Where in the published X "For You" ranking code does optimizing the proxy objective
(Σ weight·P(action)) structurally diverge from a healthy/relevant feed, such that the
divergence is derivable from the *visible structure* (sign convention, separable linear
form, post-hoc multiplicative guardrails, hard-binary safety filter, continuous training
on engagement) WITHOUT assuming any withheld weight magnitude — and do the design's own
stated guardrails (negative-weighted actions, author-diversity attenuator, OON factor,
VF filter) structurally fail to neutralize it?

Advisory orthogonal eigenquestion (generator, claude-sonnet-4-6,
`proposed_eigenquestion_20260516T004837Z.md`): temporal-irreversibility framing —
recorded as advisory only; NOT the operative science object for this run.

## 2. Falsifiable claim under test

The substrate (mutator) will be scored on whether it can name ONE highest-leverage
structural failure mode, argue its mechanism line-to-code, show the stated guardrails
do not structurally neutralize it, and falsify ≥3 rival modes on the static evidence
surface — with magnitude-dependent claims correctly bounded as "not decidable from
this evidence." Pass/fail is rubric-driven (adversarial panel), not GT-comparison.

## 3. Lakatosian pass/fail

- **Progressive:** thesis grounds the failure mode in named code structure (e.g.
  the dwell/continuous-dwell terms being positive-summed; guardrails being purely
  multiplicative post-hoc and per-response, not affecting the trained objective;
  candidate isolation removing cross-candidate context; continuous training closing
  the engagement feedback loop) AND falsifies rivals structurally.
- **Degenerate:** thesis relies on a withheld magnitude, on external domain knowledge
  not on the evidence surface, on speculative psychologizing, or strawmans rivals.
- A correctly bounded "not decidable from this evidence" on a magnitude-dependent
  sub-claim is **progressive**, not degenerate.

## 4. Sealed run command (pinned)

```
make experiment-loop PYTHON=venv/bin/python \
  PROJECT=x_algo_goodhart_audit RUBRIC=rubrics/x_algo_goodhart_audit.json \
  ITERS=5 MUTATOR_MODEL=gpt5.5 JUDGE_MODEL=claude \
  MODE=factory DYNAMIC=0 EVOLVE=0 CROSS_FAMILY=0 VALIDATE_RUBRIC=0
```

- `ITERS=5` — operator authorized "no more than 5 iters of gpt5.5".
- `MUTATOR_MODEL=gpt5.5` — operator authorized.
- `JUDGE_MODEL=claude` — cross-family judge (Anthropic ≠ OpenAI mutator) per AGENTS.md
  §6e.1 mandatory cross-family hygiene. This makes the panel adversarial across
  provider families and reduces shared-blind-spot risk.
- `DYNAMIC=0 EVOLVE=0` — operator-specified: no committee regeneration, no auto-evolve.
- `VALIDATE_RUBRIC=0` — see §6; the canonical validator was run manually and PASSED.

## 5. Artifacts / evidence provenance

- Source: `xai-org/x-algorithm` public HEAD, cloned 2026-05-15 (release "Updates —
  May 15th, 2026"). Curated verbatim source in
  `projects/x_algo_goodhart_audit/raw/x_algorithm_src/` (scorers, filters, READMEs).
- `evidence.txt` is hand-built (Path A) from verbatim code excerpts + repo-grounded
  facts — deliberately NOT LLM-compiled, to keep the evidence surface faithful.
- Key recorded fact: the proxy **weight values are withheld** from the open-source
  tree (read at runtime from `xai_feature_switches::Params` / absent `params` module);
  only functional form + sign convention + normalization are public.

## 6. Apparatus deviations (stated explicitly per AGENTS.md §7a honesty rule)

1. **Makefile path staleness (repo mid-reorg).** `make validate-rubric` and
   `make seal` reference `scripts/validate_rubric.py` / `scripts/validate_evidence.py`,
   but the validators now live under `scripts/public/validators/`. The canonical
   `scripts/public/validators/validate_rubric.py` was run directly:
   **RESULT: PASSED — 7 checks OK** (run twice; after the Phase-5 rubric edits and
   after the cage_meta addition). The loop is launched with `VALIDATE_RUBRIC=0`
   because validation was performed with the canonical tool, not skipped.
2. **`make seal` Phase 3.5 (`validate_evidence.py`) is structurally incompatible
   with qualitative-audit substrates.** It hard-requires ≥5 numeric table
   rows/tuples. This is a symbolic-regression gate. **Proof of class-mismatch:**
   running it on the repo's own canonical sealed qualitative audit
   `gp169_consciousness_ascription_audit` fails with the *identical* error
   ("0 table rows and 0 inline tuples"). Fabricating numeric tuples into the
   evidence would corrupt the faithful code surface (a GP-072 contamination /
   honesty violation), so it was NOT done. The numeric evidence gate does not
   apply to this substrate class; the applicable gate (`validate_rubric`) PASSED.
3. **`make eigenquestion-propose`** does not map model labels; default "gemini"
   404s. Ran successfully with raw id `claude-sonnet-4-6` (advisory artifact only).
4. **Apparatus import bug fixed (blocked ALL experiment-loops).** First launch
   crashed in iter-1 Falsification Suite: `src.ztare.validator.test_thesis` →
   `lean_substrate_runner` → `lean_proof_gate.py:53` did
   `import verify_lean_stub` after inserting `<repo>/scripts` on sys.path, but
   the scripts reorg moved the module to `scripts/public/lean/verify_lean_stub.py`.
   Fixed `src/ztare/gates/lean_proof_gate.py` to insert
   `scripts/public/lean` (and keep legacy `scripts/`) — both layouts now resolve.
   Import chain verified before relaunch. (Unrelated to the substrate; a
   reorg-induced apparatus regression. Per §5d audit-gap discipline: Mode-1
   working-tree edit to `src/`, no commit.) The stale Makefile prereq
   `_preflight_charter_patches` (→ missing `scripts/preflight_charter_patches.py`)
   prints an error but is non-fatal to the loop.

## 7. GP-072 Phase 5 — Domain-Expert Rubric Review (performed manually, Mode 1)

- **5.1 Rubric ↔ answer-class compatibility:** PASS. Original LLM-drafted rubric
  required "code modifications / output traces / empirical side effects" to
  falsify rivals — impossible, the mutator cannot execute the artifact and only
  has a static evidence surface. Fixed dimension 4 + both relevant criteria to
  require *structural* falsification from the visible code and to explicitly bar
  smuggling withheld magnitudes. Rubric now matches the static-evidence answer class.
- **5.2 GP-103 anti-recurrence checklist:** PASS. No parameter-count ceiling in
  persona/dimensions; persona names no correct answer class or law; parsimony
  framing rewards structural justification; composites admitted. (Auto-check:
  no numeric parameter ceilings.)
- **5.3 Persona adversarial audit:** PASS. Persona is an answer-class-neutral
  hostile empiricist (demands code-grounded mechanism, penalizes speculation);
  it does not steer the judge toward or away from any specific failure mode.
- `cage_meta.class="audit"` + `cage_observe_mode=true` added (canonical
  qualitative-audit format, modeled on `gp169`); weights sum 100; `rival_`
  criteria present (uniqueness gap N/A, disabled with reason).

## 7b. Run-2 addendum (re-scoped, 2026-05-15)

Run-1 produced a correct answer to the wrong question: the rubric/charter
optimized a cautious internal falsification audit, so the mutator anchored on
one thesis and hedged it weaker across all 5 iters (plateau 72). Run-2 re-scopes
the deliverable to a **sharp, defensible, postable adversarial critique** and
adds the anti-anchoring stack to break the single-thesis hedge-loop.

- Charter rewritten: deliverable = thread-ready critique (one screenshot claim +
  code-anchored harm chain + steelmanned rebuttal survived + one-clause scope).
- Rubric rewritten: persona = sharp-critic ∧ hostile-reply-guy; 4 dims (22/30/26/22)
  punish BOTH mush and overclaim; canonical `validate_rubric` PASSED (7 checks).
- Anti-anchoring opt-ins (rubric, per `rubric_authoring_map.md §5b`):
  `enable_primitive_class_rotation`, `enable_qualitative_stagnation_detection`
  (`qualitative_plateau_threshold=3`), `enable_forced_reframe`
  (`gp168_stagnation_threshold=2`). No extra model spend.
- `evidence.txt §E` de-hedged: withheld magnitudes / unexposed grox are a
  CONSTRAINT (build on public structure), explicitly NOT a "not-decidable" headline.
- Eigenquestion: deliberately NOT run (run-1's was orthogonal; objective is crisp;
  saves a paid call).
- Run-1 dynamic artifacts archived to `projects/x_algo_goodhart_audit/_run1_archive/`;
  thesis reset to scaffold baseline for a clean iter-0.

Run-2 sealed command (pinned; cost-minimized per operator):
```
make experiment-loop PYTHON=venv/bin/python \
  PROJECT=x_algo_goodhart_audit RUBRIC=rubrics/x_algo_goodhart_audit.json \
  ITERS=4 MUTATOR_MODEL=gpt4.1-mini JUDGE_MODEL=gpt4.1-mini \
  MODE=factory DYNAMIC=0 EVOLVE=0 CROSS_FAMILY=0 VALIDATE_RUBRIC=0
```
Operator-directed deviation from §6e.1: mutator and judge are SAME family
(`gpt4.1-mini`) — explicit principal cost decision; reduces adversarial
independence (shared blind spots), accepted tradeoff for minimal spend.

## 8. Attestation

The evidence surface is faithful verbatim X-algorithm source + repo-grounded facts;
there is no hidden GT to leak (qualitative audit). The applicable canonical validator
(validate_rubric) PASSED. GP-072 Phase 5 review was performed and the answer-class
bias it caught was fixed. Apparatus deviations are documented above with proof. This
substrate is sealed for the pinned 5-iteration run.
