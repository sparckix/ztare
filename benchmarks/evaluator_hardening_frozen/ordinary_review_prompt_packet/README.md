# Ordinary Review Packet

This packet is the `D_ordinary_review` reviewer handoff for the frozen
constraint-memory evaluator-hardening suite.

## What to Review

- Source run: `benchmarks/constraint_memory/runs/20260404_195100`
- Specimens: `9`
- Prompt files: `prompts/*.txt`
- Return format: fill `ordinary_review_import_template.json`

Review each prompt independently. Use only the prompt text. Do not use ZTARE
deterministic gate output, mined primitive memory, exploit labels, prior
benchmark-condition output, or any expected-answer metadata.

## Required Row Shape

Each row must keep:

- `specimen_id`
- `model`
- `timestamp`
- `prompt_sha256`
- `provider_runtime`
- `review.accept_claim_as_stated`
- `review.score`
- `review.fatal_flaw_identified`
- `review.flaw_summary`
- `review.confidence`

`prompt_sha256` must stay equal to the hash in the template. The import path
fails closed if a row is missing provenance, if a selected specimen is missing,
or if prompt provenance does not bind to the exact generated prompt.

## Preflight Returned Rows

From the repository root:

```bash
make benchmark-ordinary-review-validate-import BENCH_ORDINARY_IMPORT=path/to/ordinary_review_rows.json
```

## Freeze As Fourth Arm

After preflight passes:

```bash
make benchmark-ordinary-review BENCH_ORDINARY_IMPORT=path/to/ordinary_review_rows.json
```

Before editing frozen-suite metadata:

```bash
make benchmark-ordinary-review-freeze-check BENCH_ORDINARY_RUN=benchmarks/constraint_memory/runs/<run_id>
```

Do not describe the suite as a completed four-arm comparison until a real
ordinary-review import run has been frozen under
`benchmarks/constraint_memory/runs/<run_id>/` and promoted into the frozen
suite metadata.
