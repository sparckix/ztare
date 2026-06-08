# Changelog

All notable changes to ZTARE are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This changelog begins at the first tagged release (`0.1.0`). Earlier development
is preserved in the git history and narrated in `docs/sprint_70day_journey.md`;
it is intentionally not backfilled here entry-by-entry.

## [Unreleased]

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
  and seam / spec-format forcing gates — each dogfooded so it cannot silently rot.
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

[Unreleased]: https://github.com/sparckix/ztare/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sparckix/ztare/releases/tag/v0.1.0
