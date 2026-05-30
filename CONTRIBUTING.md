# Contributing to ZTARE

Thanks for considering a contribution. ZTARE is a single-operator research apparatus with the bar set at "does it preserve the falsification discipline" rather than "is it clever." Read this before opening a PR.

## TL;DR

1. Open an issue first for anything beyond a typo or a one-line bug fix.
2. Every claim that gets shipped needs a deterministic gate that catches its violation. New primitives ship with their gates in the same PR.
3. Run the gates before pushing: `make gates` (publish-safety +
   docs-freshness) plus the smoke tests. `make install-hooks` wires the
   same checks into a local pre-push hook; CI re-runs them on every PR
   (`.github/workflows/gates.yml`). The gates dogfood themselves, they
   refuse to run if they cannot prove they fire.
4. Don't commit to `main` directly. PRs only.
5. If your PR demotes a prior claim, the demotion goes in the **same artifact** as the original claim, not a separate erratum.
6. By submitting a PR you agree your contribution is under MIT (see `LICENSE`).

## What kind of contributions are welcome

| Kind | Likely to be merged |
|---|---|
| Bug fix with a regression test | yes |
| New gate, anti-pattern catalog entry, or catch-ledger row | yes |
| New substrate adapter following the existing pattern (`projects/<substrate>/`) | yes |
| Spec clarifications in `docs/concepts/` with a test that pins the new wording | yes |
| Cross-primitive integration tests | yes |
| Independent replication on a second operator / second apparatus stack | **especially yes**, see "honest scope" below |
| Performance fix backed by a benchmark | yes |
| New primitive that re-implements something already shipped | no, discuss in an issue first |
| Refactor without a behavior-preserving test | no |
| "Make the LLM smarter" PRs | no, the kernel is substrate-agnostic by design |
| Anything that breaks the invariants below | no |

## Invariants that must hold

These are not stylistic preferences, they are the contracts the apparatus's epistemic claims publicly commit to. Breaking any of them is a regression even if tests pass.

### Mutator and judge come from different model families

The substrate-mutator-judge loop relies on structural separation. A PR that lets the same model class produce both the candidate form and the score against that form re-introduces the U-Form gradient (P1 in `docs/concepts/epistemic_principles.md`). Multi-model cold-shot diversity (Gemini / GPT / Claude) is a structural defense, not an aesthetic preference.

### Pre-registration before any discriminating test

Every substantive claim requires a pre-registered prediction or acceptance threshold authored before the result that confirms or refutes it is seen. PRs that introduce a claim without a corresponding pre-registration commit (or pre-registration line in the seam) are regressions per P15 / P17.

### Self-demotion in the same artifact

When an apparatus output does not survive its own subsequent audit, the demotion is documented **in the same artifact as the original claim**, not in a separate erratum. PRs that move a refuted claim to a quiet correction file violate P17. Preserve the original; add a `## Self-demotion` section in place.

### Deterministic gates run independently of LLM calls

The gate stack (R1-R26 anti-pattern gates, structural checks, fit harness) must be deterministic. A PR that introduces an "let an LLM judge whether the gate fires" path in any deterministic-gate location is a regression. LLMs propose; gates decide; the operator authorizes promotion.

### Charter contamination rule

Mutator-visible context must not contain the ground-truth form, parameters, or derivation of the substrate's true law. PRs that pipe GT into the charter, the seam, or the prompt-render path violate the charter contamination rule (`feedback_charter_contamination`). The catch ledger has rows for past violations of this rule; it is a recurring failure mode.

### Catch-ledger discipline

Any caught self-overclaim, by an automated detector, a reviewer agent, or a human reader, gets a row in `analytics/public/ledgers/catch/catch_ledger.jsonl` (see [LEDGERS.md](LEDGERS.md)) with timestamp, rule violated, and demotion artifact path. The ledger is governed by a concurring-agent gate: one agent scores, a second ratifies. PRs that bypass this gate dilute the ledger.

## Seams and specs are public when closed

Seams and specs default private until they close, and become public once closed and safe to share. The visibility rule is in `AGENTS.md §4a`. If your PR closes a seam, also promote it to the public tree in the same PR.

## Workflow

### 1. Open an issue first

Describe the problem, the proposed fix, and which invariant the fix relates to. For new primitives, link the relevant concept doc in `docs/concepts/`. For bug fixes, link a reproducer.

### 2. Branch

```bash
git checkout -b fix/<short-name>            # for fixes
git checkout -b primitive/<short-name>      # for new primitives
git checkout -b substrate/<short-name>      # for new substrate adapters
git checkout -b docs/<short-name>           # for spec/doc changes
git checkout -b catch/<short-name>          # for catch-ledger entries
```

### 3. Implement + test

Tests live in `tests/`, mirror the source path. Substrate adapters get a smoke test that runs one real iteration end-to-end against archived data (not synthetic). New primitives ship with the deterministic gate that detects their failure mode in the same PR.

### 4. Run preflight

```bash
make smoke              # smoke tests across substrates
make gate-harness       # deterministic gate stack
make typecheck          # static checks where applicable
```

### 5. Update docs

If you changed an apparatus surface, update `docs/concepts/architecture.md`. If you elevated a postmortem pattern to a transferable principle, add it to `docs/concepts/epistemic_principles.md` (currently v0.3, P1-P19). If you closed a seam, promote it to the public seams tree in the same PR.

### 6. Open the PR

Title: `<area>: <one-line>` (e.g. `gate: add R27 silent-default detector`, `substrate: add OEIS A002865`, `catch: row #25 vocabulary-laundering`).

Body: link the issue, describe what changed, list which gates and tests cover the change, note any invariant impact, and link the demotion artifact if your PR refutes a prior claim.

## Coding conventions

- **Python**: type hints on all new public functions; no `print` in primitive code (use `logging`).
- **No comments that say what code says.** Add a comment only when the *why* is non-obvious, a hidden constraint, a workaround, an invariant.
- **No backwards-compatibility shims** unless explicitly requested. Delete the old code; tests are the rollback plan.
- **License headers are not required on new files.** MIT applies to the whole repo via the top-level `LICENSE` + `NOTICE.md`.

## Independent replication is the highest-value contribution

The single largest open question about this apparatus is whether the falsification discipline produces results under a *different operator on a different substrate*. The current evidence base is N=1: one principal, one apparatus stack, four substrates. If you reproduce the apparatus on your own infrastructure and run a scientific substrate of your choice, successfully or not, please open an issue with the result. Failed reproductions are at least as valuable as successful ones; both update the project's confidence in the methodology generalization.

## Security

For security-sensitive issues, please file an issue with the title `SECURITY: <one-line>` and the maintainer will rotate it through a private channel until the project lands a `MAINTAINERS` file.

## Scope

- The kernel scope is **adversarial validation of scientific claims** under a single-operator discipline. PRs that add multi-tenant orchestration, agent-runtime infrastructure, or chat UIs are out of scope, those layers belong in the sibling [cognitive-firm](https://github.com/sparckix/cognitive-firm) repo.
- The kernel scope does **not** include training models, building autonomous agents, or implementing inference. The apparatus orchestrates LLMs as workers; it does not provide them.
- Substrate-specific content (NS Track B Lean files, gravity sandbox PDE solver, neural-scaling W&B fetchers) lives under `projects/<substrate>/` and is welcome but reviewed against the substrate-prober question framework: *what is this substrate's binding constraint?*

## License agreement

By submitting a contribution you agree:

1. The contribution is your original work, or you have the right to submit it under MIT.
2. Your contribution is licensed to the project under MIT (see `LICENSE`).
3. You preserve the copyright notice in derivative works.

There is no separate CLA. The MIT license is the agreement.

## Questions

Open an issue with the `question` label, or read `docs/concepts/architecture.md` and `docs/sprint_60day_journey.md` first, most architectural questions have already been answered there.
