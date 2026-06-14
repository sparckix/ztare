---
description: "Small command set for reviewing ZTARE evidence without traversing the whole repository."
---
# Executable Review Pack

> **Up:** [Evidence Atlas](README.md)

This is the smallest command set a skeptical reviewer should run before
reading the full corpus. It is intentionally not a complete test suite.

## Current Checkout Caveats

Observed in this checkout on 2026-05-31:

- `make demo` passed.
- `make smoke-public` passed.
- `python -m pytest tests -q` failed during collection because some tests still
  import moved root-level scripts, including
  `scripts/public/control/agent_daemon.py`, `scripts/validate_evidence.py`, and
  `scripts/public/analytics_shared/export_layered_knowledge_graph.py`.
- `make gates` passed after recalibrating publish-safety to the explicit
  external-review surface and fixing one seam metadata header.

These are repo-health issues. They do not erase the apparatus evidence, but
they matter for external trust and should be fixed before sending the repo as a
polished public artifact.

## Tier 1: Model-Free Evidence

```bash
make demo
make benchmark-evidence
python scripts/public/control/evidence_packet_check.py
```

Expected purpose:

- `make demo` runs the small model-free evaluation-failure demonstrations in
  `papers/case_studies/`.
- `make benchmark-evidence` checks the conservative benchmark evidence stated
  in [benchmark evidence](../../benchmarks/benchmark_evidence.md) and validates
  reviewer-facing evidence packets.
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
