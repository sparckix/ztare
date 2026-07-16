# Release Checklist

This checklist records the minimum invariants for a public push. It is not a
substitute for code review; it prevents packaging and documentation failures
from drowning out the repo's actual contribution.

## Tree Hygiene

- [ ] `git status --short` has only intentional release changes.
- [ ] No generated dependency trees are tracked: `node_modules/`, `orbit/node_modules/`.
- [ ] No local logs or caches are tracked: `nohup.out`, `.lake/`, `.pytest_cache/`, `__pycache__/`.
- [ ] Lean source under `ztare_proofs/` is intentionally public; generated
      Lean build state under `ztare_proofs/.lake/` is not tracked.
- [ ] No OS/editor artifacts are tracked: `.DS_Store`, `*.bak`, `*.pre_audit_*`.
- [ ] No model checkpoints or large generated artifacts are tracked unless they
      are deliberate release assets with provenance and checksums.
- [ ] `git ls-files` has no paths under `[internal-ref]` or other
      private-state folders. `org/mandates/` and `org/preferences/` may track
      only README/template files; real local mandate/preference files remain
      ignored.

## Secrets And Privacy

- [ ] No API keys, tokens, private keys, private endpoints, personal contact
      details, or unpublished third-party material are tracked.
- [ ] Public/private mirror relationships in `MIRROR.md` have been checked for
      drift when public docs are edited.
- [ ] Private paths are either absent from the public branch or represented by
      sanitized README stubs only.

## Documentation

- [ ] `README.md` is the public entry point.
- [ ] `docs/README.md` maps docs by layer and maturity.
- [ ] `papers/README.md` is authoritative for what papers are public, draft,
      released, superseded, or intentionally excluded.
- [ ] Case studies and science tracks state their maturity and prohibited claims.
- [ ] Internal docs are labeled as internal/audit support, not first-read paths.
- [ ] `CHANGELOG.md`, `priority_roadmap.md`, and
      `docs/public_claim_register.md` agree on the latest tag and the
      post-tag release slice.
- [ ] Public review packets linked from release notes contain a claim,
      evidence pointer, command or inspection path, non-claims, and next
      falsifier.

## Claim-Class Membrane

- [ ] Governance evidence is described as governance evidence: axiom/status
      audits, statement-integrity checks, certificate checks, policy gates, or
      anti-laundering receipts.
- [ ] Benchmark evidence names the benchmark, sample size or fixture count,
      comparator, timeout/cost boundary, and whether the result is a floor,
      lift claim, or negative result.
- [ ] Paper evidence names the paper packet and distinguishes corpus evidence,
      replay/synthetic evidence, methodology claims, and future validation.
- [ ] Maintainer-only planning evidence stays out of public release notes unless
      it has been promoted into a public packet or claim-register entry.
- [ ] LeanMill proof-search results are not upgraded into measured lift unless
      a matched baseline and discriminating proof slice are present.
- [ ] Forecasting results are not upgraded into market/human superiority claims
      unless source timing, label timing, comparator information, and row
      validity are checked.
- [ ] Public release notes include explicit non-claims for any result that could
      be overread.

## Runtime Reality

- [ ] At least one documented smoke path has been run in a clean environment or
      explicitly marked as requiring private credentials/state.
- [ ] Clean-checkout org bootstrap has a public template path:
      `python scripts/org_first_run_setup.py --init-private --skip-smoke`.
- [ ] Quickstart commands use verified Make/script parameters, not remembered
      aliases.
- [ ] Known limitations are documented near the command that triggers them.
- [ ] `make gates` has passed before commit and before push.
- [ ] `make docs-check` has passed after any public-doc or review-packet edit.

## Project Workbench Release Boundary

- [ ] The operator followed `docs/guides/workbench-release.md`; local, public-scope, and remote-tunnel
      commands in the guide still match the supported runtime.
- [ ] `forensic-workbench/public-projects.json` is tracked, intentional, and contains only projects safe to disclose.
- [ ] `make forensic-workbench-release-check` passes after the production frontend build.
- [ ] `make forensic-workbench-docker-build` passes with Buildx and uses the Workbench-specific build context.
- [ ] The `workbench-release-boundary` CI job passes on the public checkout.
- [ ] The public-scope inventory equals the manifest; an unlisted project read, file preview, and write are refused.
- [ ] The built frontend and API share one loopback origin. Port 8765 is not exposed directly on a remote host.
- [ ] A remote demo uses an SSH tunnel and `public` or explicit `allowlist` project scope.
- [ ] `make workbench-interaction-smoke` passes against the release server without model-backed writes.
- [ ] The new-project, returning-project, pressure-test, decision-test, document, plugin, Activity, and LeanMill routes render without an error boundary.

## Current Release Notes

- 2026-05-02: release-readiness audit found the conceptual architecture strong
  but tree hygiene not push-ready. Immediate repairs: unstage all prior partial
  staging, delete local `.DS_Store` files, delete root `nohup.out`, add docs
  map, add this checklist, and remove one tracked pre-audit snapshot.
- 2026-06-19: release stewardship now requires explicit claim-class separation
  for governance, benchmark, paper, and maintainer-planning evidence. This keeps
  post-tag LeanMill, forecasting, and evaluator-hardening work from being
  overread as broader system-performance claims.
- 2026-06-22: the next public release slice is the local claim-governance
  workbench path: first-run, project intake, source/evidence readiness,
  autoresearch trace, report/export support contracts, action-intelligence and
  kernel-health read models, release-slice audit, public positioning, and the
  narrow forensic-workbench prototype. LeanMill source, paper/submission churn,
  proof-audit artifacts, forecasting-program churn, HBR/roadshow work, and
  neuralese-writing rubric work remain holdbacks unless directly needed for
  that path.
