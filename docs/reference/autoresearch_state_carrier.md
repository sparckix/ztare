---
description: "Technical reference for the autoresearch trace, projection read model, and action-intelligence linkage."
---
# Autoresearch Trace State Reference

> **Up:** [Reference](README.md)

## Scope

ZTARE has a read-only autoresearch trace that reports whether a project has a
valid project-intake boundary plus the raw/source, evidence/provenance,
derived-constraint, projection, and health surfaces needed for inspection.
Under that trace, the hypothesis projection read model turns existing
`workspace/eval_history.jsonl` or legacy history records into an inspectable
projection over tried hypotheses, admitted/pruned nodes, branch constraints,
worker transport, artifact references, and downstream action-intelligence
links.

The implementation and CLI still use the historical word `carrier` in literal
field names such as `carrier_chain` and commands such as
`ztare autoresearch carrier-replay`. In reader-facing prose, treat that as a
read-model compatibility term: it means "the ordered state surfaces carried
into, or recovered from, an autoresearch run." It is not a public evidence
packet, not a project-intake file, and not proof that the projected hypothesis
is true.

The projection also exposes `latest_eval_results.json` as a read-only overlay.
If a run writes latest evaluation state without appending an
`eval_history.jsonl` row, the read model reports `latest_eval_without_eval_history`
and leaves projection nodes empty. If the latest evaluation is newer than the
history rows, it reports `latest_eval_not_in_eval_history` so the user does not
mistake stale projection nodes for the current run state. The overlay is not a
synthetic node and does not promote latest-eval state into history.

The loop writer now materializes the baseline evaluation into
`workspace/eval_history.jsonl` before the iteration loop, and iteration rows use
the same append helper. New rows carry artifact refs for latest-eval, graph,
evidence-gap, constraint, thesis/current-iteration, test-model, and submission
snapshot surfaces when available. New rows keep the full weakest-point text;
the projection still recognizes older rows that stored a long prefix only.
Append failures are reported instead of being silently swallowed.

The trace is implemented by `src/ztare/reports/autoresearch_trace.py`. The
projection kind is `ztare_autoresearch_hypothesis_projection_v0`,
implemented by `src/ztare/validator/hypothesis_projection.py`. The read-only
replay audit is `ztare autoresearch carrier-replay`; it runs the same
projection read model over selected projects and reports latest-eval,
artifact-ref, worker provenance, and action-link coverage gaps without running
the loop.

## Reference Status

L1/L2: implemented and exercised on fixed tests plus current repository run
history. This reference is about inspectability of state, not outcome quality
and not public claim strength.

## Primary Sources

- [hypothesis_projection.py](../../src/ztare/validator/hypothesis_projection.py)
- [autoresearch_trace.py](../../src/ztare/reports/autoresearch_trace.py)
- [autoresearch_carrier_replay.py](../../src/ztare/reports/autoresearch_carrier_replay.py)
- [test_hypothesis_projection.py](../../tests/test_hypothesis_projection.py)
- [test_autoresearch_trace.py](../../tests/reports/test_autoresearch_trace.py)
- [test_autoresearch_carrier_replay.py](../../tests/reports/test_autoresearch_carrier_replay.py)
- [test_autoresearch_loop_static_guards.py](../../tests/validator/test_autoresearch_loop_static_guards.py)
- [workflow.md autoresearch route contract](../guides/workflow.md)
- [action impact ledger](../../analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl)

## Runnable Anchors

```bash
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/test_hypothesis_projection.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/reports/test_autoresearch_trace.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/reports/test_autoresearch_carrier_replay.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/validator/test_autoresearch_loop_static_guards.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/test_cli.py tests/test_hypothesis_projection.py tests/reports/test_autoresearch_carrier_replay.py tests/reports/test_autoresearch_trace.py tests/validator/test_autoresearch_loop_static_guards.py -q
PROJECT=$(find projects -path '*/workspace/eval_history.jsonl' -print -quit | sed 's#^projects/##; s#/workspace/eval_history.jsonl$##')
ztare autoresearch trace --project "$PROJECT" --json
ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json --json
ztare autoresearch projection --project "$PROJECT" --out ztare_projection_smoke.json
ztare autoresearch carrier-replay --project "$PROJECT" --json
make synth PROJECT="$PROJECT" MODEL=gemini RENDERER=research_note
rg -n 'projection_kind|action_intelligence_link_count|action_intelligence_refs|worker_archetype|transport|status|artifact_refs|branch_cue|failure_signature' ztare_projection_smoke.json
rg -n 'latest_eval_overlay|latest_eval_without_eval_history|latest_eval_not_in_eval_history' ztare_projection_smoke.json
```

Expected output:

```text
trace status is complete_trace or partial_trace with explicit missing surfaces
```

The smoke trace should report:

- `status` as `complete_trace` or `partial_trace`;
- `readiness`, distinguishing intake-ready candidates from historical traces
  with no intake and traces blocked by missing project/evidence surfaces;
- `readiness_canonical`, preserving current intake-facing status names while
  legacy `readiness` IDs remain readable;
- `blocking_missing` and `history_missing`, so a fresh first-run candidate with
  no `eval_history` is distinguishable from a project missing source,
  evidence, rubric, or intake surfaces;
- `project_intake` when an intake is supplied or discovered, including
  validation errors, source/evidence ref counts, non-claim count, expected
  command, and project/rubric matching. Legacy `project_packet` fields remain
  as compatibility aliases only;
- `synthesis/autoresearch_review_context.json` after `make synth` on a project
  with autoresearch artifacts. This is a compact trace-derived reporting input,
  not a new source of substantive evidence or a thesis-promotion path;
- intake-backed run telemetry records the admitted intake hash and
  run-readiness contract digest, so later trace/health review can bind a run to
  the exact intake and entry state that passed, flag current-intake drift, and
  report whether the current run-readiness contract still matches the admitted
  digest;
- `loop_admission`, a top-level summary of unique admitted receipts, reporting
  intake hash status separately from run-readiness hash status;
- `route_preview`, using the intake's exact `expected_command` when the intake
  validates and marking whether the route/run handoff can execute now;
- `plan_preview`, a deterministic read-before-run view of the dependency order,
  worker roles, spend boundary, fallback policy, expected workspace outputs, and
  largest quality risk before a paid loop starts;
- `missing`, `recovery_actions`, and `next_commands` when required trace
  surfaces are absent;
- `graph_rd_actions`, including out-of-loop public-source recovery actions and
  in-loop focus receipts for local verifier gaps;
- raw/source, evidence/provenance, projection, and health summaries.

Evidence-gap routing in the trace is contract-first. Rows with
`recovery_kind=public_evidence` may drive `out_of_loop_evidence_recovery` and
public-source fetch. Rows with `recovery_kind=local_verification` drive
`in_loop_focus_receipt` and should be resolved by fixture, verifier, code/log,
preflight, receipt, or next-loop discriminator work. The trace treats legacy
rows through compatibility inference, but new producers should emit
`recovery_kind`, `recovery_channel`, `required_surface`, `can_public_fetch`, and
`in_loop_consumable` directly.
Project-intake files may seed these rows with an `evidence_gap_contracts`
list; validation canonicalizes each row and the brief trace renders the
resulting recovery contract. The source-claim graph carrier and graph-focus
mutator briefing also consume those intake gap contracts when workspace gap
rows are absent, so a fresh project can carry its first local-verification
target without waiting for `latest_evidence_gaps.json`. Live autoresearch runs
pass the admitted `--intake` payload into the briefing context, so providers
use the exact launch intake before falling back to conventional project-local
intake or legacy packet filenames.

The smoke projection should include:

- `projection_kind: ztare_autoresearch_hypothesis_projection_v0`;
- `status` rows such as `merged` and `pruned`;
- `worker_archetype`, `transport`, `artifact_refs`, `failure_signature`, and
  `branch_cue` fields on nodes;
- `latest_eval_overlay`, with explicit status when latest evaluation is absent,
  covered by history, present without history, unreadable, or newer than
  history;
- `action_intelligence_link_count` and `action_intelligence_refs` when current
  action rows link to the projected project or artifact references.

The replay audit should include:

- `schema: ztare-autoresearch-carrier-replay-v1`;
- one row per selected project;
- `status` as `ok`, `attention`, or `error`;
- `latest_eval_status`, `missing_carrier_fields`, `attention_reasons`, and
  `next_action` for repairable carrier gaps;
- `current_carrier`, which reports whether the latest materialized projection
  node has artifact refs, worker provenance, transport, and a failure
  signature;
- aggregate counts for attention rows, latest-eval overlay gaps, missing
  artifact refs, unrecorded transport, current complete/missing carrier rows,
  and action-intelligence links.

Recent live trace-smoke results:

- `ztare autoresearch run --project demo_claims --rubric demo_claims --intake
  examples/project_packets/ready_demo_claims_intake.json --iters 1 --mutator
  deepseek --judge deepseek --llm-timeout-seconds 60 --llm-retries 1`
  completed as a live trace smoke.
- Baseline and iteration rows were appended to `workspace/eval_history.jsonl`;
  the attempted mutation scored 72 against the retained champion score of 85
  and was reverted.
- `ztare autoresearch carrier-replay --project demo_claims --json` reports
  `latest_eval_status: covered_by_eval_history` and
  `latest_eval_attention_count: 0`; remaining attention is historical
  pre-fix rows without artifact refs. Current replay output also separates this
  legacy debt from the live row through `current_carrier.status: complete` and
  `next_action: legacy_carrier_backfill_optional_current_rows_ok`.
- A later two-iteration `demo_claims` smoke with Kimi/Moonshot as mutator and
  Grok/xAI as judge exercised the provider path with fallback disabled. The
  trace remained `complete_trace` and did not report provider fallback for that
  run. That result is a provider/userland integration check, not an
  outcome-quality claim.

The smoke command intentionally selects a project from the checkout instead of
naming a favored campaign. The read model is project-agnostic.

## What The Test Covers

The fixed tests verify:

- complete traces distinguish current and legacy evidence/provenance layouts;
- project-intake validation is reported separately from historical trace
  completeness;
- fresh first-run candidates can report `ready_for_first_in_loop_run` even
  though no eval history exists yet;
- route previews use the validated project-intake file's expected command rather
  than a generic task placeholder;
- partial traces emit missing surfaces and recovery commands;
- admitted and pruned nodes are derived from score progression;
- worker archetype, worker capability, worker state, worker identity, and
  transport cannot silently disappear from the read model;
- completed dispatch receipts override policy metadata when transport is
  inferred;
- gate failures can be recovered from iteration telemetry;
- latest evaluation state without a history row is reported as an overlay and
  does not create a synthetic projection node;
- latest evaluation state that is not represented in history marks projection
  nodes as stale;
- latest evaluation state with full weakest-point text can match older
  history rows that carried a long prefix only;
- action-intelligence rows link back to projection nodes through artifact or
  project references.
- replay distinguishes a clean project, a latest-only project, a stale history
  project, and a missing project without mutating the checkout.
- baseline evaluation must append a history row before the iteration loop, and
  iteration rows must include artifact refs through the shared writer.

## Evidence Summary

The trace and projection read model are read-only syntheses over existing
project history. They do not mutate canonical run state. The tests cover
readiness, state-shape fields, and linkage fields, while the smoke commands
prove the CLI can emit the intake-aware trace, projection, and replay audit for
a project already present in the checkout.

## Non-Claims

- No claim that an autoresearch run improved a public scientific result.
- No claim that subscription workers outperform API workers.
- No claim that linked action-intelligence rows prove the projected hypothesis
  is true.
- No claim that valid project intake by itself makes project/evidence
  surfaces complete.
- No claim that every historical project already has complete worker metadata or
  a complete raw-source-to-evidence provenance chain.
- No claim that older `eval_history.jsonl` rows are backfilled automatically.

## Next Falsifier

The read model remains only partial if new autoresearch rows can omit raw/source
provenance, worker transport, artifact refs, failure signatures, or
action-intelligence linkage without a test failure. It also remains partial if
latest-eval-only states accumulate without a typed history append or a review
that explains why history is intentionally absent. A stronger reference fixture
would use a fixed end-to-end autoresearch fixture whose route row, trace
artifact, projection artifact, latest-eval overlay, and action-impact row are
all produced by one command.

## Missing Upgrade

The missing upgrade is an end-to-end fixture that creates a route JSON row,
executes or imports an autoresearch run, emits the trace and projection
artifacts, and records the action-impact row in one bounded command. The current
reference proves the read model, readiness report, and joins, not that the full
lifecycle is atomic.
