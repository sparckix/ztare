# Changelog

All notable changes to ZTARE are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This changelog begins at the first tagged release (`0.1.0`). Earlier development
is preserved in the git history and narrated in `docs/sprint_70day_journey.md`;
it is intentionally not backfilled here entry-by-entry.

## [Unreleased]

No unreleased changes.

## [1.2.4] - 2026-07-16

### Changed
- The base PyPI install now includes SymPy and `z3-solver`, matching the
  deterministic symbolic and SMT capabilities advertised by the package.
- Z3 is constrained to the broadly compatible 4.x wheel line, avoiding the
  malformed macOS platform tag in the upstream 5.0.0.0 wheel.
- Added capability-based `lean`, `ui`, and `full` extras while retaining the
  broader `research` and model-specific provider extras.
- The public install guide now separates Python extras from the external Lean
  4/Mathlib toolchain and names the source-checkout requirement for
  repository-backed commands.

## [1.2.3] - 2026-07-16

### Fixed
- Public command-example validation now checks repository module paths without
  importing their parent packages, so optional scenario dependencies do not
  enter the provider-free first-run path.
- New ARC/world-model and gate report formatters now parse on every supported
  Python version instead of relying on Python 3.12+ f-string grammar.
- The syntax gate now prefers Python 3.11 when it is available, matching the
  minimum supported interpreter and the public clean-install workflow.
- Contract-coherence tests now classify `PATCH_DELTA_SPEC` as a carrier format
  instead of a control-receipt type.

## [1.2.2] - 2026-07-16

### Fixed
- Public CLI smoke checks now derive their expected version from project
  metadata instead of retaining a release-specific literal.
- Checkout-mode version reporting now prefers `pyproject.toml`, avoiding stale
  editable-install metadata after a version bump.

## [1.2.1] - 2026-07-16

### Fixed
- The provider-free constraint-memory export path now defers Google, Anthropic,
  and OpenAI SDK imports until a corresponding model is selected, restoring the
  clean base-install first-run check.
- A standard-library-only regression test now exercises the offline prompt
  export without access to optional site packages.

## [1.2.0] - 2026-07-16

This release deepens the Project Workbench, advances AxiomPack from a compact
pack builder into governed theory-program campaigns, and publishes the current
ARC-AGI harness as work in progress.

### Added
- A production Workbench release boundary: explicit public-project allowlist,
  one-origin frontend/API serving, hidden-project refusal checks, CI coverage,
  Docker build context, interaction smoke, and a documented release runbook.
- Workbench evidence-fetch receipts, plugin management, project scenarios,
  saved decision visits, model briefs, report readiness, and responsive Verdict
  and LeanMill views.
- AxiomPack campaign closure, formal-task boundaries, external-science
  admission, language advancement, compound implication sieves, resumable VPS
  actions, campaign receipts, and kernel-checked Lean artifacts.
- ARC-AGI/world-model workbench contracts for transition identity, observation
  charts, equivariance certificates, factored search, schema routes, compiled
  planning, and deterministic candidate production.

### Changed
- AxiomPack campaigns now treat an agent-authored theory program and its lineage
  as the governed object; compact packs remain one calibrated profile.
- World-model utilities were consolidated around typed identities and shared
  primitives, with superseded adapter, causal-compiler, k-line, scene-grammar,
  and duplicate planning surfaces removed.
- Provider SDKs and research dependencies moved into optional package extras;
  the base installation retains the offline public path.
- Public documentation, architecture indexes, sample-project receipts, and
  Workbench copy now distinguish mapped files from verified claim support.

### Fixed
- Report-readiness checks refuse stale synthesis bindings while continuing to
  surface provider and trace risks.
- Workbench project inventory reports visible and total rows correctly under
  filtering and pagination.
- Public artifacts and tests no longer embed maintainer-specific filesystem
  paths.
- Undefined-name, seam-metadata, terminology, and responsive-layout failures
  found by the release gates were repaired.

### Claim boundaries
- ARC-AGI remains WIP. This release publishes harness code and typed contracts;
  it makes no benchmark, solve-rate, or leaderboard claim.
- AxiomPack campaign and Lean artifacts demonstrate governed execution and
  bounded formal results; they do not establish general theorem-discovery lift.
- The Project Workbench remains local-first and filesystem-backed. The public
  boundary is a disclosure and serving contract, not a hosted multi-user
  service.

## [1.1.0] - 2026-07-02

The Project Workbench became a first-party local capability with rubric review,
research-map queries, single-claim falsification, document drafting, sample
projects, a one-container deployment path, and refreshed public evidence.

## [1.0.0] - 2026-06-25

The initial Project Workbench release added a local React/server app for opening
projects, inspecting backing files, running checks, recording review status,
saving next steps, and preserving receipt provenance. It also refreshed public
roadmap, documentation, terminology gates, and evidence/read-model artifacts.

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

[Unreleased]: https://github.com/sparckix/ztare/compare/v1.2.4...HEAD
[1.2.4]: https://github.com/sparckix/ztare/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/sparckix/ztare/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/sparckix/ztare/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/sparckix/ztare/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/sparckix/ztare/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/sparckix/ztare/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/sparckix/ztare/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/sparckix/ztare/releases/tag/v0.2.0
[0.1.0]: https://github.com/sparckix/ztare/releases/tag/v0.1.0
