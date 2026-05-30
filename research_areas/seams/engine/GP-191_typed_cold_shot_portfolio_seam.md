# GP-191 — Typed Cold-Shot Portfolio and Deterministic Router

> **Seam metadata** · `seam_id:` GP-191 · `track:` engine · `status:` implemented / verify · `last_updated:` 2026-05-09


**Status:** implemented / verify  
**Opened:** 2026-05-01 00:21:00 EDT  
**Owner:** principal + Codex/operator-supervisor  
**Related:** `GP-169_cold_llm_synthetic_erdos_seam.md`, `GP-190_post_run_discriminator_daemon_seam.md`, `src/ztare/orchestrator/cold_shot_seed.py`, `src/ztare/orchestrator/cold_shot_discriminator.py`, `src/ztare/orchestrator/frontier_script_scaffold.py`

---

## Eigenquestion

How should ZTARE mechanize the meta-finding that frontier cold-shots can
produce better structural priors than iterative mutator search, without
collapsing discovery into prompt leakage, domain-specific ontology injection,
or a single prompt-soup primitive?

## Observed Meta-Finding

The `gp163d` run produced a durable methodological signal:

1. A low-context, problem-specific GPT-5.5 cold-shot produced a structurally
   cleaner chameleon-like family than the iterative mutator.
2. The cold-shot was not empirically dominant after fitting; ZTARE's iterative
   apparatus still improved several class fits through parameter adaptation.
3. The synthesis hypothesis is therefore:

   ```text
   frontier cold-shot proposes structural family
   -> ZTARE promotes hardcoded constants to fitted parameters
   -> ZTARE gates, fits, falsifies, and records the result
   ```

This is distinct from GP-169's Erdős seed. GP-169 is deliberately
domain-blind and cross-domain. The successful `gp163d` cold-shot was
problem-specific and structural.

## Panel Result — 2026-05-01 00:21:00 EDT

Three independent reviewers converged on the same architecture:

1. **Do not build one general-purpose cold-shot prompt.** It will become prompt
   soup: seed generation, discriminator selection, cross-domain transfer, and
   script scaffolding need different context rules, schemas, validators, and
   promotion licenses.
2. **Do not make an LLM meta-router authoritative.** A model deciding which
   cold-shot family to run becomes an opaque judgment layer. It can run in
   observe mode to suggest missing families, but routing must be deterministic.
3. **Implement a typed cold-shot family registry.** Cold-shot families should be
   plugins with declared lifecycle, context policy, artifact schema,
   validator, cache key, briefing tier, and consumption acknowledgment.
4. **Separate claim classes.** A deanchored cold-shot can support a stronger
   "cold discovery" claim than a problem-specific structural seed. A
   domain/Lagrangian seed is valuable, but should be labeled as expert-assisted
   mechanism search unless kept gate-side.

## Cold-Shot Families

| Family | Lifecycle | Purpose | Mutator-visible? | Claim class |
|---|---|---|---|---|
| `de_anchor_seed` | pre-iter-1 | Cross-domain/Erdős seed from anonymized fingerprint | yes, low-tier briefing | strongest cold-discovery evidence |
| `structural_seed` | pre-iter-1 | Problem-specific structural family under gates, not physics by default | yes, T1 if enabled | architecture-guided discovery |
| `physics_lagrangian_seed` | pre-iter-1 | Domain/action-principle seed when dimensional or variational substrate warrants it | yes only when explicitly routed | expert-assisted mechanism search |
| `discriminator` | post-run | Next-test / kill-shot proposal after champion, null, or anomaly | no direct candidate injection | promotion support only after closure |
| `frontier_script_scaffold` | frontier planning | Scaffold scripts/public/checklists for expensive GPU/API tests | no direct execution | instrument repair / launch hygiene |

## Deterministic Router

The router reads rubric/substrate metadata and returns a set of selected
families. It does not call an LLM.

Inputs:

- `rubric.enable_cold_llm_erdos_seed`
- `rubric.enable_cold_shot_seed`
- `rubric.enable_lagrangian_derivation`
- `rubric.rubric_mode` / `rubric.rubric_modes`
- `rubric.cage_meta.class`
- explicit policy block:

  ```json
  {
    "cold_shot": {
      "mode": "observe",
      "force_families": [],
      "disabled_families": [],
      "budget": {"max_calls_per_run": 3, "max_cost_usd": 1.0}
    }
  }
  ```

Outputs:

- `workspace/cold_shot_policy.json`
- append-only `workspace/cold_shot_runs.jsonl`
- per-family artifacts remain separate, e.g. `cold_llm_seed_iter0.json`,
  `cold_shot_seed.json`, `next_discriminator_queue.jsonl`.

## Anti-Contamination Rules

1. Families do not overwrite each other's candidates.
2. The router selects families; validators decide whether artifacts are
   admissible; promotion guards decide whether closed tests support F/INS rows.
3. Domain/Lagrangian routing is not the default for non-physics substrates.
4. Canonical constants and hidden holdout labels stay gate-side unless the run
   is explicitly labeled expert-assisted.
5. Two-stage generation is required before any cold-shot artifact can trigger
   expensive GPU runs, public/promotable claims, or generated code execution.

## Implementation Slice

Phase 1 ships:

- `src/ztare/orchestrator/cold_shot_policy.py`
- deterministic family registry and router
- `workspace/cold_shot_policy.json`
- `workspace/cold_shot_runs.jsonl` observability rows
- pre-iter-1 dispatch integration for GP-169
- policy-aware GP-184 fire/no-fire guard
- contract prompt correction: import-safety defaults must not be encoded as
  hardcoded numeric defaults inside `PARAMETRIC_FORM`.

## Phase 1 Implementation Note — 2026-05-01 00:29:00 EDT

Implemented:

- `src/ztare/orchestrator/cold_shot_policy.py`
- `src/ztare/orchestrator/cold_shot_policy_fixture_regression.py`
- pre-iter-1 dispatch integration in
  `src/ztare/orchestrator/pre_iter1_dispatch.py`
- policy guard around the existing GP-184 Lagrangian seed in
  `src/ztare/validator/autoresearch_loop.py`
- contract briefing correction in
  `src/ztare/orchestrator/briefing_providers/contract_rules.py`
- R1 diagnostic correction in `src/ztare/fit/mutation_suite_guard.py`

Validation run:

```text
./venv/bin/python3 -m src.ztare.orchestrator.cold_shot_policy_fixture_regression
./venv/bin/python3 -m py_compile src/ztare/orchestrator/cold_shot_policy.py src/ztare/orchestrator/pre_iter1_dispatch.py src/ztare/validator/autoresearch_loop.py src/ztare/orchestrator/briefing_providers/contract_rules.py src/ztare/fit/mutation_suite_guard.py
```

Both passed.

Important scope boundary: Phase 1 registers `structural_seed` but does not yet
implement the generator. This is intentional. The current GP154 Erdos-only
baseline should finish first. The next clean A/B is:

```text
Arm A: de_anchor_seed only
Arm B: structural_seed + same gates / same iteration budget
```

Only if Arm B shows a real variational/free-energy seam should a domain or
Lagrangian family be routed for neural scaling.

Phase 1 does not yet implement the full `structural_seed` generator. That
family is registered and routable, but firing it remains opt-in via future
implementation. This avoids overfitting the architecture to GP154 while the
current Erdos-only baseline is still running.

## Phase 1b Instrument Repair — 2026-05-01 00:09:00 EDT

During the GP154 baseline, iter 3 produced a clean declared-parameter form
with a fitted categorical offset:

```text
params['pC'] if features['fit_convention'] == 'chinchilla_parametric' else 0.0
```

R20/R21 correctly found no hidden constants (`effective_k == declared_k`), but
R22/RH-17 still flagged the expression as a lookup table because its regex
treated any categorical branch with a numeric zero baseline as a hardcoded
class return. That is detector imprecision, not a discovery result: a declared
optimizer-visible offset with neutral zero baseline is different from
`1.23 if class == X else 0.98`.

General repair shipped:

- RH-17 now flags literal class lookup branches.
- RH-17 no longer flags declared-parameter categorical offsets with neutral
  zero baselines.
- R21/R24 remain responsible for counting and policing branch complexity.
- Regression fixture added at
  `src/ztare/gates/structural_anti_pattern_gates_fixture_regression.py`.

Validation run:

```text
./venv/bin/python3 -m src.ztare.gates.structural_anti_pattern_gates_fixture_regression
./venv/bin/python3 -m py_compile src/ztare/gates/structural_anti_pattern_gates.py src/ztare/gates/structural_anti_pattern_gates_fixture_regression.py
```

Both passed. Replaying the iter 3 `PARAMETRIC_FORM` through the repaired R22
detector returns no RH-17 match.

## Phase 1c Cross-Substrate Decontamination — 2026-05-01 00:46:00 EDT

GP154 normalized exposed a serious kernel bug: the GP-184 cold-shot path still
contained GP163D/gravity-specific priors as global defaults. The iter-0 seed
was useful structurally (quartic latent field, `m2*q + lambda*q^3 = J`), but
the concrete prompt and briefing imported a non-existent `sigma` feature and
gravity-specific screening language into a neural-scaling substrate. That is
instrument contamination, not a failed neural-scaling hypothesis.

General repair shipped:

- `cage_meta` for `gp154_scaling_law_normalized` now includes the required
  generic cage metadata (`min_rows_per_category`, `near_miss_factor`) so the
  authoritative gate stack engages.
- GP-184 prompt generation now includes an explicit feature-license rule:
  `BACKGROUND` and `PARAMETRIC_FORM` row variables must be drawn from the
  active substrate's exposed `features.py` keys.
- GP-184 cache version bumped to `prompt_template_version=2`, so stale
  gravity-shaped cold-shot prompts do not silently replay for new runs.
- Cold-shot seed artifacts now persist `substrate_feature_keys`; the briefing
  provider also reconstructs feature keys from `features.py` for old artifacts.
- Hardcoded mandatory `sigma` coupling was removed from the generic primitive.
  Domain-specific mandatory couplings must now be declared explicitly through
  rubric field `cold_shot_required_feature_couplings`.
- The GP-180 worked-example provider was generalized away from gp163d/MOND
  examples toward domain-neutral latent-field examples.
- The blitz candidate scorer no longer gives any global bonus for
  domain-specific vocabulary; adoption of a cold-shot family must be judged by
  validators, not by last-project keywords.
- GP154 normalized evidence records the quartic latent-field crossover as a
  bounded prior while explicitly rejecting cross-substrate feature imports.

Validation run:

```text
./venv/bin/python3 -m py_compile src/ztare/orchestrator/cold_shot_seed.py src/ztare/orchestrator/briefing_providers/cold_shot_seed.py src/ztare/orchestrator/briefing_providers/lagrangian_worked_example.py src/ztare/orchestrator/blitz_dispatch.py
./venv/bin/python3 scripts/public/validators/validate_rubric.py gp154_scaling_law_normalized
./venv/bin/python3 scripts/public/validators/validate_evidence.py gp154_scaling_law_normalized --rubric rubrics/gp154_scaling_law_normalized.json
```

All passed. `validate_evidence` still emits the existing soft import warning
for `test_model.py` when run outside the project sys.path, but exits PASS.

## Success Criterion

A cold agent can inspect a run workspace and answer:

1. which cold-shot families were eligible;
2. which families were selected;
3. why each selected family fired or did not fire;
4. which artifact each family wrote;
5. whether downstream code consumed it.

If the answer requires reading chat history, the implementation is incomplete.
