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
- [ ] `git ls-files` has no paths under `research_areas/private/` or other
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

## Runtime Reality

- [ ] At least one documented smoke path has been run in a clean environment or
      explicitly marked as requiring private credentials/state.
- [ ] Clean-checkout org bootstrap has a public template path:
      `python scripts/org_first_run_setup.py --init-private --skip-smoke`.
- [ ] Quickstart commands use verified Make/script parameters, not remembered
      aliases.
- [ ] Known limitations are documented near the command that triggers them.

## Current Release Notes

- 2026-05-02: release-readiness audit found the conceptual architecture strong
  but tree hygiene not push-ready. Immediate repairs: unstage all prior partial
  staging, delete local `.DS_Store` files, delete root `nohup.out`, add docs
  map, add this checklist, and remove one tracked pre-audit snapshot.
