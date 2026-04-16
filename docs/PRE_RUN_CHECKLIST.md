# Pre-Run Checklist — Leak Audit and Scaffold Readiness

Canonical checklist for any ZTARE experiment before the first `autoresearch_loop.py` invocation. If you cannot check every box below, **the run is not a data point — it is a warm-up** (see `docs/FOR_RESEARCHERS.md` §1).

This checklist exists because even with explicit rules in `AGENTS.md` and the charter-contamination section of `FOR_RESEARCHERS.md`, scaffolds keep shipping with leaks. The passive rule ("don't leak") fails under pressure; the active rule ("run this grep, paste the result, or halt") is harder to skip.

The checklist is mandatory for both Claude Code and Codex. If an agent declares a sandbox "ready to run" without a completed checklist, that's a rule violation — file it as a seam.

---

## 0. What counts as mutator-visible

Every file `autoresearch_loop.py` reads on or before iter 1 is mutator-visible. At minimum:

- `projects/<slug>/project_charter.md` (injected verbatim at `autoresearch_loop.py:1319`)
- `projects/<slug>/thesis.md` (the seed thesis)
- `projects/<slug>/test_model.py` (param names, seed form, comments)
- `projects/<slug>/evidence.txt` including the prose header before `=== sweep ===` blocks
- `projects/<slug>/evidence_holdout.txt` and `evidence_farther_tail.txt` headers
- `rubrics/<rubric-name>.json` (persona + every criterion string; injected into both mutator and judge prompts)
- Any `current_iteration.md`, `workspace/*.json`, or `history/*.md` leftover from a prior run in the same slot

Anything in `research_areas/private/seams/` is **not** mutator-visible (the loop never reads it). That is the correct home for the sealed GT form, the sealed expected void slot, and the verdict criterion. Charter and rubric describe *that* the target exists and *how* grading works — never what the target *is*.

---

## 1. Leak audit — grep denylist

Run this exact grep against every mutator-visible file listed in §0. The set of forbidden substrings is target-dependent; the denylist below is the *generic layer* every run must pass, plus a target-specific layer the operator adds per pre-reg.

### Generic layer (always applies)

**Content leaks — forbidden substrings in any mutator-visible file:**

- The literal GT functional form (e.g. `1 - exp`, `** n`, `exp(-`, `sqrt(`, `log(` — whatever closed-form the pre-reg seals)
- Semantic names of the GT parameters (`V_inf`, `tau`, `decay`, `peak`, `amplitude`, `time constant`, `asymptot*`, `saturat*`, `ceiling`, `rate constant` — not the placeholder letters `a, b, c, A, n`)
- Domain nouns that imply the generator class: `RC`, `circuit`, `resistor`, `capacit*`, `ohm`, `voltage`, `Planck`, `Kepler`, `Hill`, `logistic`, `Arrhenius`, `Boltzmann`, `black-scholes`, `queue`, `SIR`, any named law
- Derivation vocabulary: "first-order", "step response", "transient", "asymptote", "exponential", "power law", "sigmoid", "Lorentzian", "Gaussian" — if the answer's shape class leaks, the mutator one-shots it
- The expected Component B void slot (e.g. `fn:*|arg0|has_op:Div`) — this lives in the sealed pre-reg and must never appear in any mutator-visible file

**Naming leaks — leaked through identifiers instead of content:**

- **Project directory slug.** The path `projects/<slug>/` surfaces in iteration-diff summaries, error messages, and any file reference string the loop constructs. If the slug encodes the answer class (`gp023_sandbox_09_rc_step`, `kepler_v2_sqrt_primitive`, `planck_law_retry`), the mutator decodes it before reading a single line of evidence. Slugs must be opaque (`gp023_sandbox_09`, not `gp023_sandbox_09_rc_step`).
- **Rubric filename.** Same argument. Rubrics are referenced by filename (`rubrics/<name>.json`) in command strings and in the loop's rubric resolution trace. Use opaque filenames matching the project slug.
- **Branch, worktree, and scratchpad names.** If you scaffold in a feature branch named `feature/sandbox_09_rc_step_generalization`, the branch name may surface in git-aware tooling or in ad-hoc notes. Keep them opaque too.
- **Comment strings inside code files.** `# RC step generator` in `test_model.py` or `gate_harness.py` is just as visible as a prose leak.

**Same-dir cheat sheets — ground-truth generators inside the project dir:**

- Any script that computes the GT values (e.g. `generate_evidence.py`) must live **outside** `projects/<slug>/`. Put it next to the sealed pre-reg under `research_areas/private/seams/`, under a `tools/` or `sealed_generators/` directory, or delete it after the evidence files are rendered. Its presence inside the project dir is a standing kill-shot: even if the current loop does not `os.listdir` the project dir, any future tooling change, any IDE-assisted mutator, and any manual inspection breaks the blind.
- Same for any `.ipynb` notebook, shell script, or README that describes the GT.
- Same for any prior run's `current_iteration.md`, `debate_log_iter_*.md`, or `workspace/*.json` — these are stale state from a prior run and leak the previous iteration's thesis. Wipe them before starting a fresh experiment.

**Framework meta-talk — breaking the mutator's fourth wall:**

- The mutator persona is a domain solver working on a math problem. It is not a ZTARE experimenter. If the charter or rubric tells the mutator that it is being tested by "Component B", compared against "Planck sandboxes", or evaluated as a "cross-domain generalization target", the mutator's task changes from "fit the curve" to "satisfy the evaluator". That is a persona break and it invalidates the experiment.
- Strip all references to: ZTARE architecture components (Component A/B, GP-0NN seam IDs, negative_space_extractor, derived_constraints), cross-project comparisons (sandbox_07/08, Planck family, Kepler sibling), experiment-design vocabulary (cold-harvest, mode (c) verdict, disjointness claim, generalization target). These belong only in the sealed pre-reg and the operator-facing documentation.
- The charter should read like a task statement for a math-problem solver. Nothing more.

### Target-specific layer

Add a `leak_denylist:` block in the pre-reg §Leak Audit section listing every target-specific word the operator wants scrubbed (e.g. sandbox_09 adds `step.response`, `RC`, `V_inf`, `V_offset`, `capacitance`, `resistance`). The operator builds this list from the sealed GT form and its common textbook names, not from the charter.

### Command

```
bash docs/scripts/leak_audit.sh <project-slug> <rubric-name>
```

If that script does not yet exist for your project layout, use the inline equivalent:

```
grep -n -E -i '<generic denylist regex>|<target denylist regex>' \
    projects/<slug>/project_charter.md \
    projects/<slug>/thesis.md \
    projects/<slug>/test_model.py \
    projects/<slug>/evidence.txt \
    projects/<slug>/evidence_holdout.txt \
    projects/<slug>/evidence_farther_tail.txt \
    rubrics/<rubric-name>.json
```

**Exit criterion:** zero matches, or every match explained in writing in the pre-reg §Leak Audit section as a known load-bearing substring that is not a leak (e.g. a YAML scoring flag like `asymptotic_claim: true` which is already redundant with the numeric data).

---

## 2. Strip test (Mungerian inversion)

For every sentence in the charter, thesis, and rubric persona, do the strip test from `feedback_principle_vs_instantiation.md`:

1. Remove proper nouns and concrete mechanisms.
2. Read what remains.
3. If the sentence still carries useful instruction to the mutator → keep it.
4. If the sentence collapses to "this target is X" or "the answer has property Y" → it was a leak disguised as prose. Delete or rewrite.

This catches shape hints the grep misses ("the curve has an asymptote", "smaller R saturates faster", "the rise inverts at t=1.6 if you nest R wrong") because those sentences have no single forbidden word but collectively name the answer.

---

## 3. Identifiability protocol

Before sealing the pre-reg (§4 below), the operator must run the identifiability protocol on the sealed GT parameters:

1. **Multi-start fit** — ≥20 random seeds within a physically plausible box. All converged seeds must recover the sealed GT to within the pre-reg's per-parameter tolerance.
2. **Pairwise bowl check** — fix each pair of parameters at GT, sweep the third. Loss surface must be convex-down around GT with a unique minimum.
3. **Rank-along-trajectory** — Jacobian column-rank equals the parameter count at GT. Catches hidden degeneracies like sandbox_06 α,β collapse.
4. **Bootstrap** — ≥200 resamples of the visible grid; 95% CIs for each parameter must not contain a neighbor parameter's GT value.

Results pasted into the pre-reg before seal. A pre-reg without identifiability results is not sealed.

---

## 4. Pre-registration seal

The pre-reg (`research_areas/private/seams/<project>_pre_registration.md`) must be written and sealed **before** the first main-loop invocation. Seal format per `docs/FOR_RESEARCHERS.md` §4, with these additional sections mandated by this checklist:

- **§Leak Audit** — pasted grep output with zero matches (or explained non-leaks), plus target denylist used
- **§Identifiability** — pasted results of §3 above
- **§Smoke Gate** — harness_smoke_gate.py output showing all charter-declared gates fail on the naive seed with finite actuals
- **§Charter Fingerprint** — `sha256sum projects/<slug>/project_charter.md` recorded at seal time, so later drift is detectable per replication procedure (`FOR_RESEARCHERS.md` §7)
- **§Sealed Expected Slots** — the hidden targets the operator commits to grade against (expected Component B void slot, expected champion form, etc.), in the pre-reg only, **never** in the charter

---

## 5. Smoke gate

`python projects/<slug>/harness_smoke_gate.py` must exit 0 and report:

- Naive seed fails visible assertions (exit 1 in `--run-visible-assertions` mode)
- `--emit-deterministic-gates` emits exactly the charter-declared gate set with every field populated
- All `actual` values are finite (no `null`/NaN/inf — otherwise GP-030 would cap every candidate at 50 for the wrong reason and the run would look like a real failure)

If any contract is violated, fix the harness before the main run.

---

## 6. Dry run of the sealed command

Per `FOR_RESEARCHERS.md` §4: the pre-reg is sealed by dry-running the exact sealed command string once, with `--iters 0` or equivalent, to pin all implicit defaults (model family, rubric path resolution, argparse flag parsing). A pre-reg whose command has never been dry-run is not sealed.

---

## 7. Final go/no-go

Before the run starts, the operator confirms in writing (in the pre-reg §Seal section):

- [ ] §1 grep denylist audit — zero unexplained hits
- [ ] §2 strip test — completed on charter, thesis, rubric persona
- [ ] §3 identifiability protocol — passed
- [ ] §4 pre-reg sealed — fingerprint recorded
- [ ] §5 smoke gate — exit 0
- [ ] §6 sealed command — dry-run passed

If any box is unchecked, the run must not start. If an agent (Claude Code or Codex) declares a sandbox "ready" without all six boxes checked, that is a rule violation — the agent must file a seam and halt.

---

## 8. Why this is a separate document

The rules it enforces are already scattered across `AGENTS.md` (§7 hard rules, §4a visibility), `FOR_RESEARCHERS.md` (§1 validity, §2 charter contamination, §4 pre-reg format), and multiple feedback memories (`feedback_charter_contamination.md`, `feedback_principle_vs_instantiation.md`, `feedback_compile_before_loop.md`). The scatter is load-bearing for different audiences, but it means no single document exists that an agent can consult as "the checklist before I press run". This file is that checklist.

**Cross-references:**
- `AGENTS.md` §4a (visibility) and §7 (hard rules) — binding on both agents and operator
- `docs/FOR_RESEARCHERS.md` §1, §2, §4 — longer-form discipline prose
- `feedback_charter_contamination.md` — origin incident (GP-023 sandbox_07, 2026-04-14)
- `feedback_principle_vs_instantiation.md` — the strip test rule this §2 enforces
- `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` — the first spec to mandate this checklist as a precondition for sandbox_09

**Amendment rule.** If you discover a new leak class that this checklist missed, append a new bullet to §1 generic layer and record the incident in a feedback memory. Do not delete old bullets; the denylist is monotonic.
