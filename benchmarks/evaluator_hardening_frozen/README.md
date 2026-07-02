---
description: "Frozen evaluator-hardening proof-point suite assembled from public constraint-memory artifacts."
---

# Frozen Evaluator-Hardening Suite

This is the public proof-point suite for the evaluator-hardening claim. It is
model-free at review time: the check reads frozen benchmark artifacts already
in the repository and verifies that the claim boundary still matches the data.

## Current Scope

Artifact-backed arms:

1. `A_baseline_soft_judge`: rubric-only judge, no deterministic gates, no
   primitives.
2. `B_deterministic_gates`: deterministic score gates, no primitives.
3. `C_gates_plus_primitives`: deterministic gates plus approved
   attacker/judge-side primitives.

Known gap:

4. `D_ordinary_review`: ordinary unstructured LLM review. This arm is required
   for a future four-arm upgrade, but it is not represented by the frozen
   `source_run_20260404_195100` artifact. The checker keeps this gap explicit so the
   packet cannot be overread as a completed four-arm benchmark.

The ordinary-review arm has a predeclared contract at
[`ordinary_review_arm_contract.json`](ordinary_review_arm_contract.json), and
the benchmark runner exposes it as an opt-in `D_ordinary_review` condition. It
can call a live provider or import externally generated review rows. The
current suite is still blocked, not silently upgraded, because no frozen
ordinary-review outputs exist for the source run. The blocker is recorded at
[`D_ordinary_review_blocker.json`](D_ordinary_review_blocker.json).

## Command

```bash
make evaluator-hardening-frozen-check
```

Live fourth-arm run command:

```bash
python benchmarks/constraint_memory/run_benchmark.py --suite main --conditions D_ordinary_review --match-source-run benchmarks/evaluator_hardening_frozen/source_run_20260404_195100 --ordinary-review-model <model>
```

This command requires the selected provider credentials. Its output must be
frozen under `benchmarks/constraint_memory/runs/<run_id>/` before the suite can
be called a four-arm comparison.

Reviewer-safe prompt export:

```bash
make benchmark-ordinary-review-prompts BENCH_ORDINARY_EXPORT=/tmp/ztare_ordinary_review_prompt_packet
```

The repository also carries a generated packet at
[`ordinary_review_prompt_packet/`](ordinary_review_prompt_packet/). It contains
one prompt per frozen specimen, a prompt manifest with SHA-256 hashes, and an
import template. The prompt manifest intentionally omits labels, expected
exploit metadata, detection keywords, and prior A/B/C outputs, so it can be sent
to an ordinary reviewer without leaking the answer key. The hashes are the
provenance expected by the import path below. The Make target binds the prompt
packet to the frozen `source_run_20260404_195100` source-run specimen set by default, so
later additions to the broader `main` suite do not silently change the
fourth-arm comparison population. `make evaluator-hardening-frozen-check`
compares the checked-in packet against a fresh runner export and preflights a
synthetic import, so packet drift fails before any fourth-arm claim can be made.

Imported fourth-arm run command:

```bash
python benchmarks/constraint_memory/run_benchmark.py --suite main --conditions D_ordinary_review --match-source-run benchmarks/evaluator_hardening_frozen/source_run_20260404_195100 --ordinary-review-import-results path/to/ordinary_review_rows.json
```

The import file may be a list of rows, an object with `rows` or `reviews`, or a
mapping from `specimen_id` to review payload. Each selected specimen must have a
row. Every imported row must also carry enough provenance to make the review
auditable: `model`, one of `timestamp` / `reviewed_at` / `created_at`, one of
`prompt_sha256` / `prompt_hash` / `prompt_path` / `prompt`, and one of
`provider` / `runtime` / `provider_runtime`. The prompt provenance must also
bind to the exact prompt generated for that specimen: hashes must match the
runner-generated SHA-256, prompt literals must hash to it, and prompt paths
must be readable and hash to it. Relative prompt paths resolve from the import
JSON file directory first. The runner fails closed instead of
mixing imported and live review evidence or accepting provenance-free rows.

Preflight imported rows without creating a benchmark run:

```bash
make benchmark-ordinary-review-validate-import BENCH_ORDINARY_IMPORT=path/to/ordinary_review_rows.json
```

This checks row coverage, review schema, required provenance, and exact prompt
binding against the frozen source-run specimen set. Use it before running the
ordinary-review arm for freezing.

When the ordinary-review arm runs, the runner writes
`ordinary_review_freeze_manifest.json` beside `results.json` and
`metrics_summary.json`. Promote the arm into this frozen suite only if that
manifest reports `can_promote_to_frozen_suite: true`; otherwise follow its
`promotion_blockers` rather than editing suite metadata by hand.

Validate a completed ordinary-review run before any frozen-suite metadata edit:

```bash
make benchmark-ordinary-review-freeze-check BENCH_ORDINARY_RUN=benchmarks/constraint_memory/runs/<run_id>
```

Expected output:

- `ok: true`;
- `artifact_backed_arms: 3`;
- `complete_four_arm_suite: false`;
- baseline false-accept rate is nonzero;
- deterministic gates reduce false accepts to zero;
- gates plus primitives keep false accepts at zero and restore good controls.

## Non-Claims

- This is not a broad autonomous-research ranking.
- This is not a theorem-prover or LeanMill performance benchmark.
- This is not a completed four-arm public comparison until the ordinary-review
  arm is run and frozen.
- This does not benchmark the full in-loop plus out-of-loop research operating
  stack.

## Next Falsifier

Run and freeze `D_ordinary_review` on the same claim packets. Demote or narrow
the evaluator-hardening claim if ordinary unstructured review matches the
hardened arms on false accepts, false rejects, and structural-failure detection
without deterministic gates or mined precedent.
