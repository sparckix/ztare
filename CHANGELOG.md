# Changelog

All notable changes to ZTARE are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This changelog begins at the first tagged release (`0.1.0`). Earlier development
is preserved in the git history and narrated in `docs/sprint_70day_journey.md`;
it is intentionally not backfilled here entry-by-entry.

## [Unreleased]

### Added
- Public first-run and release-stewardship surfaces: `make hello`, a public
  smoke workflow, and a release checklist that separates governance evidence,
  benchmark evidence, paper evidence, and maintainer-only planning evidence.
- Evaluator-hardening frozen-suite checks and review packets for the bounded
  constraint-memory proof point. The ordinary-review arm remains explicit
  future work until imported rows are promotion-ready.
- Public gaming-behavior catalog packaging and audit checks that keep the
  original-nine paper lineage separate from later mined engineering rows.
- Project-intake userland: create, validate, falsify, enqueue, and prep-ledger
  resolve-next paths for bounded project claims before in-loop autoresearch use.
- Local forensic-workbench prototype: a React/Vite project browser for intake,
  source/evidence state, run readiness, report blockers, review decisions, and
  CLI-applied review files.

### Changed
- README, quickstart, CLI docs, public roadmap, claim register, and evidence
  atlas now lead with the local claim-governance path before deeper
  architecture.
- Canonical package imports were normalized across runtime modules and tests so
  package identity matches the installed `ztare` namespace instead of
  `src.ztare`.
- Autoresearch routing docs and CLI help now distinguish out-of-loop RD agent
  execution from in-loop kernel validation, project intake, and source/evidence
  readiness.
- Report generation is treated as a support-contract surface: stale or
  unsupported reports stay blocked until source/evidence, trace, and report
  bindings are current.
- Public positioning now frames chat agents, coding agents, proof tools, and
  observability platforms as adjacent systems that can feed or inspect a local
  claim lifecycle.

### Fixed
- Public evidence pack caveats now reflect the current full-suite result
  instead of the resolved canonical-import guard failure.
- Release-slice audit now classifies the canonical import cleanup as a separate
  review group while keeping papers, LeanMill source, proof-audit files, and
  generated experiment state as holdbacks.
- Action-intelligence recommendation IDs no longer churn when only
  materialization timestamps change.
- Kernel-health source warnings now surface distinct source-health issues
  instead of duplicated rows.

### Claim boundaries
- The evaluator-hardening packet supports a bounded claim about deterministic
  gates and evaluator primitives on the frozen constraint-memory benchmark. It
  is not a global autonomous-research benchmark.
- The forensic workbench is a narrow local prototype over existing CLI and
  read-model surfaces, not a hosted product or a replacement for filesystem
  evidence.
- Action-intelligence and kernel-health rows remain advisory unless source
  freshness, consumption, and decision-use evidence justify stronger authority.
- LeanMill post-`v0.2.0` work remains split by evidence class: governance
  checks, axiom/statement-integrity audits, witness-transport corrections, and
  benchmark-floor samples are not measured proof-search lift without a matched
  baseline.
- The gaming-behavior catalog is an observed mechanism and hardening catalog,
  not a completeness claim about all model gaming behavior.

## [0.2.0] - 2026-06-14

Second tagged public release. This release refreshed the public dashboard and
calibration exports while widening the public evidence surface around
LeanMill, autoresearch, forecast-pool routing, and non-math faithfulness.

### Added
- Dashboard views and public data bundles for solver-lane telemetry,
  recursive-gain summaries, trajectory views, and methodology status.
- Forecast-pool bridge fixtures and public calibration exports for LeanMill
  close plumbing and router health.
- Architecture-index and primitive-atlas refreshes so public capability
  discovery follows the current source tree.
- Early non-math firewall and cognitive-firm handoff demonstrations, kept as
  bounded faithfulness/governance evidence rather than broad domain-accuracy
  claims.

### Changed
- LeanMill governance and proof-search records became more explicit about axiom
  status, statement identity, transport edges, timeout behavior, and typed
  exits.
- Autoresearch orchestrator, validator, and pattern/action contract surfaces
  were refreshed so state projection and action obligations were easier to
  inspect.
- Public dashboard bundles and calibration summaries were regenerated from the
  current ledgers.

### Fixed
- Kernel-parity, solver-lane, forecast-router, and prompt-evolution exports
  were refreshed so public dashboards no longer pointed at stale summaries.
- Non-math wedge evidence was separated from theorem/proof-search claims.

## [0.1.0] - 2026-06-07

First tagged public release. ZTARE is a zero-trust research engine: neural
*proposers* are kept strictly separate from deterministic *verifiers, gates, and
append-only ledgers*, so the model cannot self-certify. The discipline is the
product — it improves research rigor; it does not guarantee truth.

### Added
- **leanmill — governed Lean proof-search engine.** A governed DAG search over a
  typed move algebra (native / warm / cold leaves; conjecture, specialize,
  generalize, falsify, tactic-step, witness-transport, cache-reuse) behind a
  single anti-laundering kernel (axiom allowlist + statement-integrity + MNC) and
  composite decomposition→closure ratification. The solver proposes; governance
  ratifies. Environment lift is measured, not assumed (status: lift-pending).
- **Autoresearch law-discovery factory** (`discover → compress → prove`): an LLM
  mutator and a symbolic-regression compressor feeding a Lean prover, with the
  fitter, holdout tests, and the kernel as the only arbiters.
- **Shared `common/` libraries**: sandboxed-Python execution, symbolic-witness /
  SymPy compute (linear systems, linear recurrences, Pell / diophantine),
  constraint isomorphism, inversion, a kernel-hardener, and an LLM-runtime shim —
  reused by both leanmill and autoresearch.
- **Primitive registry + atlas**: a full-coverage, AST-scanned primitive index
  with an embedding atlas and an amnesia precheck (`primitive_amnesia`) that
  surfaces existing capabilities before new ones are built.
- **Deterministic publish-safety and anti-gaming gates**: a leak-gated dashboard
  build, an external-review publish-safety gate, a mined gaming-behavior catalog,
  and seam / spec-format forcing gates, each exercised so it cannot silently rot.
- **Public analytics dashboard** (GitHub Pages): a single self-contained,
  leak-masked view of volume / taste / compounding metrics.

### Changed
- Documentation (capabilities, module map, leanmill architecture) refreshed to
  describe the current governed DAG solver and its honest, lift-pending status.
- Autoresearch validators migrated onto the shared sandboxed-execution path
  (one executor, used by both lanes).

### Fixed
- VPS deploy hardening (toolchain / PATH, solver subtree, post-deploy
  verification) and solver telemetry / return-shape defects surfaced by cold
  review.

[Unreleased]: https://github.com/sparckix/ztare/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sparckix/ztare/releases/tag/v0.2.0
[0.1.0]: https://github.com/sparckix/ztare/releases/tag/v0.1.0
