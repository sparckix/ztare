# Contributing to ZTARE

Thanks for considering a contribution. ZTARE is an open research kernel for
generating, stress-testing, governing, and auditing claims from agentic work.
The bar for a contribution is not whether it sounds clever; it is whether it
preserves the evidence discipline: separate proposal from verification, keep
claims bounded, and make failures visible.

## TL;DR

1. Open an issue first for anything beyond a typo or a one-line bug fix.
2. Every shipped claim needs an evidence path: artifact, gate or verifier,
   non-claim, and next falsifier. New primitives ship with their tests or
   gates in the same PR.
3. Run the gates before pushing: `make gates` (publish-safety +
   docs-freshness) plus the smoke tests. `make install-hooks` wires the
   same checks into a local pre-push hook; the public smoke workflow re-runs
   the deterministic public subset on every PR
   (`.github/workflows/public-smoke.yml`). The gates test their own failure
   modes; they refuse to run if they cannot prove they fire.
4. Don't commit to `main` directly. PRs only.
5. If your PR demotes a prior claim, the demotion goes in the **same artifact** as the original claim, not a separate erratum.
6. By submitting a PR you agree your contribution is under MIT (see `LICENSE`).

## What kind of contributions are welcome

| Kind | Likely to be merged |
|---|---|
| Bug fix with a regression test | yes |
| New gate, gaming-behavior catalog entry, or catch-ledger row | yes |
| New substrate adapter following the existing pattern (`projects/<substrate>/`) | yes |
| New first-run recipe, review packet, or reproducible project packet | yes |
| Spec clarifications in `docs/concepts/` with a test that pins the new wording | yes |
| Cross-primitive integration tests | yes |
| Independent replication by a second maintainer on a second deployment | **especially yes**, see "honest scope" below |
| Performance fix backed by a benchmark | yes |
| New primitive that re-implements something already shipped | no, discuss in an issue first |
| Refactor without a behavior-preserving test | no |
| "Make the LLM smarter" PRs | no, the kernel is substrate-agnostic by design |
| Anything that breaks the invariants below | no |

## Invariants that must hold

These are not stylistic preferences, they are the contracts ZTARE's epistemic claims publicly commit to. Breaking any of them is a regression even if tests pass.

### Mutator and judge come from different model families

The substrate-mutator-judge loop relies on structural separation. A PR that lets the same model class produce both the candidate form and the score against that form re-introduces the U-Form gradient (P1 in `docs/concepts/epistemic_principles.md`). Multi-model cold-shot diversity (Gemini / GPT / Claude) is a structural defense, not an aesthetic preference.

### Pre-registration before any discriminating test

Every substantive claim requires a pre-registered prediction or acceptance threshold authored before the result that confirms or refutes it is seen. PRs that introduce a claim without a corresponding pre-registration commit (or pre-registration line in the seam) are regressions per P15 / P17.

### Self-demotion in the same artifact

When a ZTARE output does not survive its own subsequent audit, the demotion is documented **in the same artifact as the original claim**, not in a separate erratum. PRs that move a refuted claim to a quiet correction file violate P17. Preserve the original; add a `## Self-demotion` section in place.

### Deterministic gates run independently of LLM calls

The gate stack (R1-R26 anti-pattern gates, structural checks, fit harness) must be deterministic. A PR that introduces an "let an LLM judge whether the gate fires" path in any deterministic-gate location is a regression. LLMs propose; gates decide; a human reviewer authorizes promotion.

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
make first-run          # offline public value demo, catalog audit, smoke, docs
make gates              # publish-safety, docs freshness, parser/seam checks
```

For narrow code changes, also run the closest `pytest` target for the files you
touched. For release-facing changes, `make gates` is mandatory before commit or
push.

### 5. Update docs

If you changed a public workbench surface, update `docs/concepts/architecture.md`.
If you elevated a postmortem pattern to a transferable principle, add it to
`docs/concepts/epistemic_principles.md` (currently v0.3, P1-P16). If you
closed a seam, promote it to the public seams tree in the same PR.

### 6. Open the PR

Title: `<area>: <one-line>` (e.g. `gate: add R27 silent-default detector`, `substrate: add OEIS A002865`, `catch: row #25 vocabulary-laundering`).

Body: link the issue, describe what changed, list which gates and tests cover the change, note any invariant impact, and link the demotion artifact if your PR refutes a prior claim.

## Coding conventions

- **Python**: type hints on all new public functions; no `print` in primitive code (use `logging`).
- **No comments that say what code says.** Add a comment only when the *why* is non-obvious, a hidden constraint, a workaround, an invariant.
- **No backwards-compatibility shims** unless explicitly requested. Delete the old code; tests are the rollback plan.
- **License headers are not required on new files.** MIT applies to the whole repo via the top-level `LICENSE` + `NOTICE.md`.

## Independent replication is the highest-value contribution

The single largest open question is whether the falsification discipline produces results for a *different maintainer on a different project*. The current evidence base is N=1: one principal, one deployment, four substrates. If you reproduce ZTARE on your own infrastructure and run a scientific substrate of your choice, successfully or not, please open an issue with the result. Failed reproductions are at least as valuable as successful ones; both update the project's confidence in the methodology generalization.

## Security

For security-sensitive issues, do not open a public issue. Use the reporting
channel in [SECURITY.md](SECURITY.md).

## Scope

- The kernel scope is **claim generation, adversarial validation, proof/project
  governance, and evidence discipline** for bounded research or project work.
  PRs that add multi-tenant orchestration, agent-runtime infrastructure, or
  chat UIs are out of scope; those layers belong in the sibling
  [cognitive-firm](https://github.com/sparckix/cognitive-firm) repo.
- The kernel scope does **not** include training models, building a general
  autonomous-agent framework, or implementing inference. ZTARE can orchestrate
  model workers; the claim surface is the typed artifact and verifier output,
  not the model call.
- Substrate-specific content (proof-search campaigns, policy/compliance
  packets, forecasting calibration, project reproductions, PDE workbenches)
  lives under `projects/<substrate>/` and is welcome when it answers the
  project-packet readiness question: *what is this project's binding
  constraint, and what evidence would change the next action?*

## License agreement

By submitting a contribution you agree:

1. The contribution is your original work, or you have the right to submit it under MIT.
2. Your contribution is licensed to the project under MIT (see `LICENSE`).
3. You preserve the copyright notice in derivative works.

There is no separate CLA. The MIT license is the agreement.

## Questions

Open an issue with the `question` label, or read
`docs/concepts/architecture.md`, `docs/guides/first-30-minutes.md`, and
`docs/sprint_70day_journey.md` first. Most architectural questions already
have a public answer there.
