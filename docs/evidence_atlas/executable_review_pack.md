---
description: "Small command set for reviewing ZTARE evidence without traversing the whole repository."
---
# Executable Review Pack

> **Up:** [Evidence Atlas](README.md)

This is the smallest command set a skeptical reviewer should run before
reading the full corpus. It is intentionally not a complete test suite.

## Checkout Caveats

Current maintainer check on 2026-06-19:

- `make gates` passed.
- `make docs-check`, `make smoke-public`, and the public terminology audit
  passed.
- `python -m pytest tests -q` completed successfully: 1787 passed, 6 skipped,
  2 xfailed, 14 warnings.

Interpretation: the public evidence pack is supported by the explicit
model-free review commands below, by `make gates`, and by the current full test
suite. A green suite is a repo-health and reproducibility fact; it is not
evidence that every historical or frontier research claim is true.

## Tier 1: Model-Free Evidence

```bash
make first-run
make hello
make evaluator-hardening-frozen-check
make gaming-catalog-audit
make scope-boundary-audit
make demo
make benchmark-evidence
python scripts/public/control/evidence_packet_check.py
```

Expected purpose:

- `make first-run` runs the full offline public review path used by CI:
  hello, gaming-catalog audit, benchmark-evidence check, frozen
  evaluator-hardening check, claim-boundary audit, terminology audit, public
  smoke, and docs checks.
- `make hello` runs the smallest current claim-discipline demo:
  overclaim in, demotion plus missing evidence out.
- `make evaluator-hardening-frozen-check` can be run separately to inspect the
  proof point. It verifies the three artifact-backed
  evaluator-hardening arms and keeps the ordinary-review fourth arm blocked
  until real frozen outputs exist.
- `make gaming-catalog-audit` verifies that the public gaming catalog, live
  registry, promotion evidence, and hardening map keep the original-nine paper
  lineage separate from later engineering rows.
- `make scope-boundary-audit` checks that broad public claim phrases appear
  only with nearby boundaries, demotions, or no-upgrade notes.
- `make demo` runs the small model-free evaluation-failure demonstrations in
  `papers/case_studies/`.
- `make benchmark-evidence` checks the conservative benchmark evidence stated
  in [benchmark evidence](../../benchmarks/benchmark_evidence.md) and validates
  reviewer-facing review packets.
- `evidence_packet_check.py` can be run directly to inspect packet field and
  link failures.

## Tier 2: Public Runtime Smoke

```bash
make smoke-public
python scripts/public/control/forecast/pool.py smoke
```

Expected purpose:

- verifies public runtime wiring without relying on private infrastructure;
- verifies forecast-pool isolation in a temporary root;
- exercises forecast/action-intelligence smoke surfaces.

## Tier 3: Reflexive Self-Report Critic

```bash
python scripts/public/control/self_report_epistemology_critic.py
```

Expected purpose:

- checks whether self-reported time series are statistically trustworthy enough
  to support aggregate trend claims;
- currently flags per-iteration champion-score non-i.i.d. behavior and too few
  reflexive metric snapshots.

Interpretation caveat: the catch-ledger window is small. If the script prints
an "i.i.d. OK" line after skipping baseline diagnostics for small N, do not
turn that into a strong independence claim.

## Tier 3b: Autoresearch State And Source Preflight

Reference: [Autoresearch State Carrier](../reference/autoresearch_state_carrier.md).

```bash
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/test_hypothesis_projection.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/reports/test_autoresearch_trace.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/research_director/test_autoresearch_workbench_router.py tests/scripts/test_action_intelligence.py -q
ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json --json
PROJECT=$(find projects -path '*/workspace/eval_history.jsonl' -print -quit | sed 's#^projects/##; s#/workspace/eval_history.jsonl$##')
ztare autoresearch trace --project "$PROJECT" --json
ztare autoresearch projection --project "$PROJECT" --out ztare_projection_smoke.json
```

Expected purpose:

- checks the autoresearch trace for raw/source, evidence/provenance,
  projection, health, missing-surface, and recovery-command state;
- checks the fixed `demo_claims` packet reaches first-run readiness before any
  loop history exists;
- checks the projection carrier for admitted/pruned nodes, transport metadata,
  failure signatures, artifact refs, and
  action-intelligence linkage;
- checks fail-closed route/rubric source-contract boundaries before a task is
  treated as workbench-ready.

Interpretation caveat: these commands prove inspectability and preflight
coverage. They do not prove that autoresearch improved the underlying research
result or that one worker transport outperforms another.

Forkability boundary: these commands exercise reusable kernel/read-model
surfaces over files present in the checkout. They do not require private
maintainer state, the ZTARE tenant overlay in `org/`, or live membrane
operations.

## Tier 4: Formal And Lean Surfaces

```bash
lake build
```

Expected purpose:

- checks the Lean workspace compiles under the current local toolchain.

Interpretation caveat: a successful build is not a proof-value claim. For
LeanMill claims, read the governance/audit docs and the relevant proof-specific
receipts.

## Tier 5: Full Repo Health

```bash
python -m pytest tests -q
make gates
```

Expected purpose:

- `pytest` should eventually be green or intentionally scoped.
- `make gates` is the benchmark-evidence, public-smoke, external-review
  publish-safety, docs-freshness, and seam/spec-format boundary.

Current `make gates` status is green in this checkout. Before a lab review,
the stale full-test collection imports should still be resolved or the full
test target should be intentionally scoped.

## Reviewer Reading Order After Commands

1. [Public claim register](../public_claim_register.md)
2. [Claim cards](claim_cards.md)
3. [Primitive evidence matrix](primitive_evidence_matrix.md)
4. [Benchmark evidence](../../benchmarks/benchmark_evidence.md)
5. Project-specific `public/CLAIM_SUMMARY.md` files for the claims you care
   about.
