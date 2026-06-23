# ZTARE Public Roadmap

**Last refreshed:** 2026-06-22
**Planning horizon:** next 4-6 weeks
**Audience:** public readers, contributors, and future maintainers

ZTARE is a local workbench for checking high-stakes reasoning before it becomes
a claim. It helps a person turn sources, code, proofs, data, model outputs,
reports, and bounded claims into states they can inspect: what passed, what
failed, what was demoted, and what should be checked next.

The long-term direction is a general-purpose compiler for reasoning. This
release keeps that ambition narrow: make the first local claim/evidence path
easy to run, easy to inspect, and hard to overread.

This public roadmap is intentionally short. The detailed implementation backlog
stays in maintainer planning docs; this page tells outside readers what will
make the next release easier to try, inspect, and challenge.

## Planning Rule

The roadmap is ordered by dependency-first trust, not by raw feature count.
Reach is still uncertain, and several items are foundational correctness work,
so the release asks:

```text
what most improves trust, leverage, and product legibility per unit effort?
```

That means a small receipt, replay check, or blocked-report contract can outrank
a larger visible feature when it prevents a user from overreading a claim.

Terminology rule for release work: call the user-facing product the
**workbench**, the trusted checks and contracts the **kernel**, runnable
subsystems **engines**, and historical experiment setups **apparatus**.

## Priority Snapshot

Scores use a RICE-style 1-5 scale:

- **Reach:** how much of the first public user path the lane affects.
- **Impact:** how much the lane improves claim safety or reviewer value.
- **Confidence:** how much current runnable evidence supports the lane.
- **Effort:** implementation and review cost, where 5 is highest cost.

The current call favors high reach, high impact, high confidence, and low
effort, while respecting dependency order.

| Lane | Reach | Impact | Confidence | Effort | Current call |
|---|---:|---:|---:|---:|---|
| First-run value | 5 | 5 | 5 | 2 | Keep green through release. |
| Project intake and evidence readiness | 4 | 5 | 4 | 3 | Treat as the main review-entry path. |
| Core validator reliability | 4 | 5 | 4 | 3 | Keep malformed work out before model calls. |
| Claim-safe public positioning | 5 | 4 | 5 | 2 | Keep front-door language narrow and inspectable. |
| Landmark public-doc rewrites | 5 | 4 | 4 | 3 | Rewrite README, principles, Cognitive Gym, reflexive/agentic, and validation docs as decision-first evidence memos. |
| Report generation and export | 3 | 4 | 4 | 3 | Promote only when support contracts pass. |
| Reflexive learning and action intelligence | 3 | 4 | 3 | 4 | Keep advisory until decision-use evidence exists. |
| Reusable research moves | 2 | 3 | 3 | 4 | Promote only when tied to typed receipts. |
| Forensic workbench design lane | 3 | 4 | 4 | 4 | Narrow React prototype exists with static snapshots, live local project reads, and explicit review-receipt apply. Keep source/evidence/review trails inspectable. |

## Product Test

A new reviewer should be able to:

1. clone the repo;
2. run one offline command;
3. see an overclaim demoted or a gate fire;
4. inspect the files behind the verdict;
5. understand the next falsifier without learning the whole internal system.

The public path is:

```text
project intake -> source/evidence check -> trace readiness
-> preflight or bounded run -> verdict / demotion / export
```

ZTARE should not compete with ChatGPT, Claude, Codex, or observability tools as
a general interface. Those systems can generate, edit, code, trace, or review.
ZTARE's job is narrower: bind outputs to local sources and decide what a claim
is allowed to mean after checks, gates, and review.

## Recent Context

- `v0.1.0` established the public zero-trust research workbench: proposers,
  verifiers, review artifacts, gates, LeanMill, autoresearch, primitive
  discovery, and public dashboards.
- `v0.2.0` refreshed dashboards and calibration exports, then follow-on commits
  hardened proof-search governance, witness transport, axiom audits, and public
  claim boundaries.
- The current release slice should make the system simpler to enter and harder
  to overread. Version labels after `v0.2.0` are planning labels until tagged.

## Current Unreleased Slice

The current unreleased slice already contains much of the entry-path work. The
release task is to verify it, keep the claim boundaries sharp, and split it into
reviewable commits without pulling in paper, forecasting, proof-audit, or
LeanMill holdbacks.

This slice should answer one question:

```text
Can a serious user stand behind a bounded claim without manually re-verifying
every source, artifact, and model-produced sentence?
```

Built or prepared in the current slice:

- `make hello` is the smallest value path: no model keys, no persistent
  state, overclaim in, demotion plus missing evidence out;
- `make first-run` is the aggregate offline path: hello, benchmark
  evidence, claim-boundary audit, terminology audit, public smoke, adversarial
  smoke, and docs checks;
- README, quickstart, first-30-minutes guide, and CLI guide are centered
  on the intake-backed validation path;
- the operational-diagnosis fixture shows how local organization
  sources become bounded claims, evidence state, trace readiness, and a
  preflightable run;
- source/evidence readiness now includes source typing, source-index receipts,
  evidence-output binding, evidence-gap action rows, claim-support summaries,
  replay manifests, and trace/run-readiness blockers;
- report generation has a deterministic support contract that can block stale
  or unsupported reports before model QA promotes them;
- action-intelligence and kernel-health read models keep advisory rows
  diagnostic unless source freshness, consumption, and decision-use evidence
  justify stronger authority;
- public release slicing separates on-ramp, evaluator hardening, public CI,
  agentic/reflexive contracts, evidence-atlas hygiene, compatibility shims,
  import cleanup, and release hygiene from explicit holdbacks.

Still to prove before release:

- run the release-slice audit cleanly enough that every dirty path is
  classified as a release group, internal planning, or holdback;
- keep `make first-run`, docs checks, public smoke, scope-boundary, terminology,
  and publish gates green after the final roadmap/docs edits;
- do not cite stale reports as current when the report support contract blocks
  them;
- keep broad autonomy, theorem-prover performance, and paper-level claims out
  of the first screen unless backed by review artifacts and non-claims.

## P0: First-Run Value

**User problem.** A cold reader should not need to understand the full research
institution before seeing value.

**Built state.**

- `make hello` and `make first-run` exist as the public entry path.
- Public docs point readers toward runnable commands before deeper architecture.
- Public CI and smoke surfaces are scoped to deterministic, credential-free
  checks.
- The gaming behavior catalog is visible as a concrete field guide, not a
  buried taxonomy.

**Next.**

- Keep this path green while release groups are separated.
- Do not let later subsystem work push broad architecture back onto the first
  screen.

**Done when.** A reader can run the public path and explain what ZTARE caught,
what it did not prove, and where the evidence lives.

## P0: Project Intake And Evidence Readiness

**User problem.** Real users bring messy local sources, not clean benchmark
fixtures.

**Built state.**

- Project intake is the boundary object before an in-loop run.
- Source freshness, evidence binding, evidence gaps, claim support, and
  run readiness are visible in one trace.
- No-spend recovery commands are explicit: bind existing evidence when honest,
  justify gaps only against current hash-bound gap rows, and fetch public
  evidence only from explicit recovery contracts.
- The operational-diagnosis demo is the public customer-shaped example.

**Next.**

- Run one more real non-LeanMill project pass only when the semantics are
  honest.
- Keep `evidence-bind` and evidence-gap justification as explicit receipts, not
  hidden compiler side effects.

**Done when.** A user can prepare a small project and see whether it is ready
for review, blocked on source/evidence quality, or waiting for a bounded run.

## P0: Core Validator Reliability

**User problem.** A model should not spend tokens on malformed contracts,
stale evidence, or untyped claims.

**Built state.**

- Malformed intake, rubrics, source rows, and launcher contracts fail before
  model calls.
- Provider fallback is opt-in for in-loop runs, and provider telemetry is
  surfaced.
- Deterministic gates cover claim discipline, gaming behavior, and
  unsupported-report detection.
- Undefined-name and publish-safety gates are in the release path.

**Next.**

- Treat provider/runtime failures as runtime evidence, not as substantive
  project verdicts.
- Keep the bounded operational-diagnosis run cheap and traceable.

**Done when.** A reviewer can distinguish model failure, source-contract
failure, project setup failure, provider/runtime failure, and harness failure
from emitted artifacts.

## P0: Claim-Safe Public Positioning

**User problem.** The repo can look like a sprawling research archive unless
the public boundary is sharp.

**Built state.**

- Public language is centered on bounded claims, evidence, demotion, and next
  falsifiers.
- Plain capability names lead; historical seam ids are provenance, not
  product names.
- LeanMill, forecasting, papers, org runtime, and hard-problem campaigns stay
  as evidence tracks unless they directly improve first-run trust.
- `docs/concepts/system_position_and_module_map.md` now explains what
  ZTARE is and is not relative to chat agents, coding agents, proof assistants,
  and observability platforms.

**Next.**

- Keep release notes and public docs aligned with the current tagged version
  and the exact review artifacts being shipped.
- Rewrite landmark docs so each page starts with the reader's decision,
  concrete example, evidence boundary, non-claim, and next action. First
  targets: `README.md`, `PRINCIPLES.md`, `docs/multi_substrate_validation.md`,
  `docs/concepts/cognitive_gym.md`, and the reflexive/agentic pattern docs.

**Done when.** A reader can say: ZTARE is the claim-governance workbench; other
agents are workers, sources, or judges inside that lifecycle.

## P1: Report Generation And Export

**User problem.** A run is not useful if the exported report invents support or
hides unresolved evidence.

**Built state.**

- Report generation is bound to source/evidence receipts, trace state, run
  history, graph/evidence-gap actions, non-claims, and next actions.
- Deterministic support contracts have higher authority than model QA.
- The operational-diagnosis report path correctly blocks stale or unsupported
  report promotion when the support contract is not current.

**Next.**

- Regenerate synthesis only after deciding to spend provider calls.
- Keep candidate reports separate from final review artifacts until the support
  contract allows promotion.

**Done when.** A report can be read as a review artifact, not a narrative
summary of whatever the model said.

## P1: Reflexive Learning And Action Intelligence

**User problem.** The system should learn from repeated failures without
turning metrics into reward hacking.

**Built state.**

- Repeated catch categories can become candidate gates, contracts, or explicit
  non-gates.
- Action-intelligence recommendation IDs are stable across rematerialization.
- Observed correlations are separated from promoted control authority.
- Source-health warnings preserve stale trajectories, weak research-yield
  ledger linkage (historical provenance: the
  [research-yield decomposition seam](research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md)),
  and missing surfacing-event consumption.

**Next.**

- Promote only warnings that have source freshness, consumption, and
  decision-use evidence.
- Keep advisory rows from becoming reward signals by accident.

**Done when.** The system can show which repeated failures changed behavior,
which stayed diagnostic, and which are still waiting on evidence.

## P1: Reusable Research Moves

**User problem.** A useful primitive should be reusable, discoverable, and hard
to duplicate accidentally.

**Built state.**

- Primitive-amnesia and move-card routing are part of the release surface.
- A primitive is promoted only when it prevents a concrete failure or improves an
  artifact/check.
- Graph records, forecast rows, and pattern/action contracts are tied to
  typed decisions, not free-floating prose.

**Next.**

- Keep graph carriers focused on typed artifact slots, next checks, and
  decision receipts.
- Keep forecasts measured before they steer work.

**Done when.** A new primitive has a duplicate check, a receipt surface, a
validator or audit, and an ex-post usage criterion.

## P1: Forensic Workbench Design Lane

**User problem.** The CLI is powerful but not the final adoption surface for
people inspecting local claims and evidence.

**Built state.** The design brief names the first persona, value proposition,
object model, first controller/screen contract, and the non-chat interaction
constraints. A narrow React/Vite prototype now consumes the workbench snapshot,
shows intake, evidence, run readiness, and report rows, separates source paths,
compiled evidence paths, commands, receipts, and review artifacts, blocks
review-file export until a decision is selected, previews the review JSON before
handoff, shows artifact coverage across rows, can switch projects through a
local live-read API during dev, applies row-level review decisions through an
explicit local API, and keeps the saved review file path compatible with
`ztare forensic-workbench apply-review`. The public
[`forensic_workbench_interface.md`](docs/concepts/forensic_workbench_interface.md)
contract defines the first user, first five-minute outcome, consumed
CLI/read-model surfaces, boundaries, and acceptance tests before any UI code is
treated as release-relevant.

**Direction.** The interface should be a specialized forensic workbench.

Early constraints:

- primary persona: independent technical reviewers, researchers, founders, and
  analysts who produce high-stakes bounded claims from local files;
- primary mode: project browser, claim/intake inspector, source/evidence state,
  trace and run-readiness console, preflight/run launch, run history, verdict,
  and export;
- no persistent chat pane as the main interaction model;
- every displayed judgment should link back to the file, receipt, command, or
  ledger that owns it;
- ZTARE stays the individual claim/evidence workbench; the org runtime remains
  the coordination and governance overlay.

**Next.**

- Polish the narrow first use case against the operational-diagnosis fixture:
  inspect intake, source paths, compiled evidence, blockers, review decisions,
  saved review files, and receipts. The current prototype covers this as a
  React/Vite shell with live local project switching, explicit local API review
  apply, explicit row-action save, health finding to row-action staging,
  static review/action-file download/copy fallback, and refreshed receipt
  visibility. Live mode opens the live snapshot JSON for the selected project;
  static mode remains the fallback when the local API is absent. Focused
  regressions cover the downloaded review file -> CLI apply path and the local
  API -> receipt path.
- Every visible row must expose a file path, source path, evidence path,
  command, receipt, review file, or explicit no-receipt warning.
- Keep backend writes explicit: local API calls must write the same file-backed
  receipt shape as the CLI and refresh the snapshot when possible.

**Done when.** A reviewer can open the local webserver, understand the current
blocker, make a row-level review decision, and apply the saved review file
without losing the file/command provenance.

## Explicit Non-Priorities

- Do not broaden first-run docs into a tour of every subsystem.
- Do not claim general autonomous research performance.
- Do not promote LeanMill search lift without benchmark evidence and claim
  boundaries.
- Do not treat observability metrics, graph diagnostics, forecasts, or action
  recommendations as control authority without separate validation.
- Do not stage release groups broadly while holdbacks remain in the dirty tree.

## Open Questions

- Which real project should be the next public non-demo run after the
  operational-diagnosis surface?
- Which action-intelligence warnings should become hard release blockers, and
  which should stay advisory?
- Which report/export format is most useful for outside reviewers: decision
  brief, research note, review artifact, or all three with different gates?
- After project index, live snapshot, and review-apply, what is the next
  smallest backend bridge that reduces first-use friction without rebuilding
  the whole CLI in a browser?
