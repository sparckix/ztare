# ZTARE Public Roadmap

**Last refreshed:** 2026-07-16
**Planning horizon:** next 4-6 weeks
**Audience:** public readers, contributors, and future maintainers

ZTARE is a local reasoning system for turning high-stakes work into durable,
inspectable state. It helps a person turn sources, code, proofs, data, model
outputs, reports, and bounded claims into records they can inspect: what was
being decided, what passed, what failed, what was demoted, what changed, and
what should be checked next.

The long-term direction is a general-purpose compiler for reasoning. The next
release keeps that ambition narrow: make the local project-to-thesis path easier
to run, easier to inspect, and harder to overread.
Any broader compiler language should stay tied to inspectable repo evidence:
inputs, checks or transforms, outputs, evidence level, and a next falsifier.
Each public capability must also name the Workbench obligation and the
user-visible proof: what the interface must show, and what file, saved history,
or command lets a reader check it.

One concrete design rule is primitive composition: when a project declares a
small vocabulary, ZTARE should check that the work actually stays inside that
vocabulary before treating a score or fit as valid. The EML sandboxes are the
current example: declare the allowed primitive, compose inside it, reject
vocabulary escapes, and record whether the target was reachable.

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

That means a small saved-history entry, replay check, or report readiness check can
outrank a larger visible feature when it prevents a user from overreading a
claim.

Terminology rule for release work: call the whole repo/system **ZTARE**, the
local app the **Project Workbench**, the trusted checks and contracts the
**kernel**, runnable subsystems **engines**, and historical experiment setups
**apparatus**.

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
| Project-to-thesis path | 5 | 5 | 4 | 4 | Shipped in v1.2: thesis, sources, evidence, checks, report readiness, saved history, and next falsifier agree across CLI, Workbench, and saved project files. |
| Project brief and evidence readiness | 4 | 5 | 4 | 3 | Treat as the main review-entry path inside the project-to-thesis lane. |
| Core validator reliability | 4 | 5 | 4 | 3 | Keep malformed work out before model calls. |
| Claim-safe public positioning | 5 | 4 | 5 | 2 | Keep front-door language narrow and inspectable. |
| Landmark public-doc rewrites | 5 | 4 | 4 | 3 | Rewrite README, principles, Cognitive Gym, reflexive/agentic, and validation docs as decision-first evidence memos. |
| Report readiness and project files | 3 | 4 | 4 | 3 | Promote only when the report matches the current project files. |
| Reflexive learning and action intelligence | 3 | 4 | 3 | 4 | Keep advisory until decision-use evidence exists. |
| Reusable research moves | 2 | 3 | 3 | 4 | Promote only when tied to typed saved history. |
| Project Workbench app | 4 | 4 | 4 | 3 | v1.2 adds the public allowlist, release boundary, responsive decision views, plugins, evidence receipts, and broader governed project flows. |

## Product Test

A new reviewer should be able to:

1. clone the repo;
2. run one offline command;
3. see an overclaim demoted or a deterministic check fail;
4. inspect the files behind the verdict;
5. understand what evidence would change the answer without learning the whole
   internal system.

The public path is:

```text
project brief -> source files and evidence check -> run readiness
-> readiness check or project run -> review / demotion / report readiness / project file
```

ChatGPT, Claude, Codex, observability tools, and proof tools are useful inputs
or companions. ZTARE's differentiator is the durable decision trail after those
systems act: bind outputs to local sources, run checks, save records, and
decide what a project can safely support after review.

## Recent Context

- `v0.1.0` established the public zero-trust research workbench: proposers,
  verifiers, review files, deterministic checks, LeanMill, autoresearch, primitive
  discovery, and public dashboards.
- `v0.2.0` refreshed dashboards and calibration exports, then follow-on commits
  hardened proof-search governance, witness transport, axiom audits, and public
  claim boundaries.
- `v1.0.0` shipped the Project Workbench release path: local project
  inventory, source-file and evidence checks, readiness and confirmed run controls,
  saved review history, saved project files, public docs, and release checks.
- `v1.1.0` added pressure-test and drafting surfaces over the Workbench.
- `v1.2.0` ships the production disclosure boundary, deeper project-to-thesis
  flows, governed AxiomPack campaigns, and the ARC-AGI harness as WIP.
- The post-v1.2 planning path should turn these broader surfaces into smaller,
  independently reviewable user workflows with explicit evidence levels.

## Current Release Path

The current release path starts from the shipped project workbench and asks a
larger question:

```text
Can a serious user move from a messy local project to a supported claim,
demotion, support issue, or next falsifier without learning every subsystem
first?
```

The Project Workbench is the first adoption path. The release work underneath
it is broader: project brief, source-file and evidence readiness, trace and run
admission, report readiness, saved review history, evaluator-hardening evidence,
guidance warnings, and public claim language must agree.

This path should answer one practical question:

```text
What can this project safely support right now, what is missing, and what check
or repair should happen next?
```

Built or prepared:

- `make hello` is the smallest value path: no model keys, no persistent
  state, overclaim in, demotion plus missing evidence out;
- `make first-run` is the aggregate offline path: hello, benchmark
  evidence, claim-boundary audit, terminology audit, public smoke, adversarial
  smoke, and docs checks;
- the Project Workbench can list local projects, distinguish connected projects
  from folders that need a project brief, inspect project files, run source and evidence
  checks, check run readiness, start confirmed project runs, save reviews and next
  steps, and save project files with saved history;
- README, quickstart, first-30-minutes guide, and CLI guide are centered
  on the project-brief validation path;
- the operational-diagnosis fixture shows how local organization
  sources become bounded claims, evidence state, trace readiness, and a
  ready-to-check run, with report-support next actions tied to previewable
  backing files;
- at least one historical project folder can be recovered into a project-brief-backed
  project, held on evidence readiness when appropriate, and advanced through
  readiness/run only after those holds are visible;
- source-file and evidence readiness now includes source typing, source-index records,
  evidence-output binding, evidence-gap action records, evidence-support
  summaries, replay manifests, and trace/run-readiness issues;
- report generation has a deterministic support contract that can block stale
  or unsupported reports before model QA promotes them;
- guidance and kernel-health read models keep advisory records
  diagnostic unless source freshness, consumption, and decision-use evidence
  justify stronger authority;
- public release grouping separates on-ramp, evaluator hardening, public CI,
  agentic/reflexive contracts, evidence-atlas hygiene, compatibility shims,
  import cleanup, and release hygiene from explicit holdbacks.

Still to verify before a release cut:

- the workbench, CLI, read models, saved project files, and docs should keep
  agreeing on the live project object as release edits continue: thesis,
  assumptions, sources, evidence, runs, report readiness, saved history, and next
  check;
- warnings should stay clear about repair versus advisory status, and
  should keep pointing to backing files or saved history rather than dense raw
  status lists;
- keep `make first-run`, docs checks, public smoke, scope-boundary, terminology,
  and publish checks green after roadmap/docs edits;
- do not cite stale reports as current when the report readiness contract blocks
  them;
- keep broad autonomy, theorem-prover performance, and paper-level claims out
  of the first screen unless backed by review files and non-claims.

## P0: First-Run Value

**User problem.** A cold reader should not need to understand the full research
institution before seeing value.

**Built state.**

- `make hello` and `make first-run` exist as the public entry path.
- Public docs point readers toward runnable commands before deeper architecture.
- Public CI and smoke checks are scoped to deterministic, credential-free
  checks.
- The gaming behavior catalog is visible as a concrete field guide, not a
  buried taxonomy.

**Next.**

- Keep this path green while release groups are separated.
- Do not let later subsystem work push broad architecture back onto the first
  screen.

**Done when.** A reader can run the public path and explain what ZTARE caught,
what it did not prove, and where the evidence lives.

## P0: Project Brief And Evidence Files

**User problem.** Real users bring messy local sources, not clean benchmark
fixtures.

**Built state.**

- The project brief is the boundary object before an in-loop run.
- Source files, evidence binding, evidence gaps, claim support, and
  run checks are visible in one place.
- No-spend recovery commands are explicit: bind existing evidence when honest,
  justify gaps only against current hash-bound gap entries, and fetch public
  evidence only from explicit recovery contracts.
- The operational-diagnosis demo is the public customer-shaped example.
- Historical folders that are not yet projects can be shown as "needs
  project brief" instead of disappearing from the workbench.

**Next.**

- Keep the serious-project and historical-recovery paths honest as release
  changes continue: no run until source, evidence, scoring, trace, and readiness
  state can be inspected.
- Keep `evidence-bind` and evidence-gap justification as explicit saved work, not
  hidden compiler side effects.

**Done when.** A user can prepare a small project and see whether it is ready
for review, held on source-file or evidence quality, or waiting for a project run.

## P0: Core Validator Reliability

**User problem.** A model should not spend tokens on malformed contracts,
stale evidence, or untyped claims.

**Built state.**

- Malformed project briefs, rubrics, source records, and launcher contracts fail before
  model calls.
- Provider fallback is opt-in for in-loop runs, and provider telemetry is
  shown.
- Deterministic checks cover claim discipline, gaming behavior, and
  unsupported-report detection.
- Undefined-name and publish-safety checks are in the release path.

**Next.**

- Treat provider/runtime failures as runtime evidence, not as substantive
  project verdicts.
- Keep the bounded operational-diagnosis run cheap and traceable.

**Done when.** A reviewer can distinguish model failure, source-contract
failure, project setup failure, provider/runtime failure, and harness failure
from the saved files.

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
  and the exact review files being shipped.
- Rewrite landmark docs so each page starts with the reader's decision,
  concrete example, evidence boundary, non-claim, and next step. First
  targets: `README.md`, `PRINCIPLES.md`,
  `docs/multi_substrate_validation.md`, `docs/concepts/cognitive_gym.md`, and
  the reflexive/agentic pattern docs.

**Done when.** A reader can say what ZTARE helps them inspect, what it does not
prove, and how other agents fit into the project workflow.

## P1: Report Support And Project Files

**User problem.** A run is not useful if the saved report invents support or
hides unresolved evidence.

**Built state.**

- Report generation is bound to source and evidence records, trace state, run
  history, graph/evidence-gap records, non-claims, and next steps.
- Deterministic support contracts have higher authority than model QA.
- The operational-diagnosis report path correctly blocks stale or unsupported
  report promotion when the support contract is not current.

**Next.**

- Regenerate synthesis only after deciding to spend provider calls.
- Keep candidate reports separate from final review files until the support
  contract allows promotion.

**Done when.** A report can be read as a review file, not a narrative
summary of whatever the model said.

## P1: Reflexive Learning And Action Intelligence

**User problem.** The system should learn from repeated failures without
turning metrics into reward hacking.

**Built state.**

- Repeated catch categories can become candidate checks, contracts, or explicit
  non-checks.
- Guidance recommendation IDs are stable across rematerialization.
- Observed correlations are separated from promoted control authority.
- Source warnings preserve stale run-history archives, weak evidence-ledger
  linkage (historical provenance:
  [research-yield decomposition evidence ledger](research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md)),
  and missing work-log consumption.

**Next.**

- Promote only warnings that have source freshness, consumption, and
  decision-use evidence.
- Keep advisory records from becoming reward signals by accident.

**Done when.** The system can show which repeated failures changed behavior,
which stayed diagnostic, and which are still waiting on evidence.

## P1: Reusable Research Moves

**User problem.** A useful primitive should be reusable, discoverable, and hard
to duplicate accidentally.

**Built state.**

- Primitive-amnesia and move-card routing are part of the release path.
- A primitive is promoted only when it prevents a concrete failure or improves a
  check or saved file.
- Graph records, forecast records, and pattern/action contracts are tied to
  typed decisions, not free-floating prose.

**Next.**

- Keep graph carriers focused on typed saved-file slots, next checks, and
  decision records.
- Keep forecasts measured before they steer work.

**Done when.** A new primitive has a duplicate check, a saved-history view, a
validator or audit, and an ex-post usage criterion.

## P1: Project Workbench Design Lane

**User problem.** The CLI is powerful but not the final adoption path for
people inspecting local theses and evidence.

**Built state.** A React/Vite local workbench now runs against a small local
server. It can list projects, open a project, show the current support issue, inspect
source, evidence, run, and report state, preview backing files, edit project brief and source
files through explicit write boundaries, check run readiness, start a confirmed project
run, save review status, save next steps, and save a project file with
saved history plus the workbench read/write/ask-first contract. The first screen is a
project guide with clear next steps; heavier trace, saved-history, report, and source
editing views open through focused menus. CLI-compatible saved-history paths remain
intact for existing users. The public
[`forensic_workbench_interface.md`](docs/concepts/forensic_workbench_interface.md)
contract defines the first user, first five-minute outcome, consumed
CLI/read-model interfaces, boundaries, and acceptance tests before any UI code is
treated as release-relevant.

**Direction.** The interface should be a specialized project workbench.

Early constraints:

- primary persona: independent technical reviewers, researchers, founders, and
  analysts who produce high-stakes working theses from local files;
- primary mode: project browser, thesis/project-brief inspector, source and evidence state,
  trace and run-readiness console, readiness/run launch, run history, verdict,
  report readiness, and saved project files;
- no persistent chat pane as the main interaction model;
- every displayed judgment should link back to the file, saved history, command, or
  ledger that owns it;
- ZTARE stays the individual thesis/evidence workbench; the org runtime remains
  the coordination and governance overlay.

**Next.**

- Polish the operational-diagnosis fixture until the first screen answers:
  what project is open, what needs attention, what action comes next, and where the
  backing files live.
- Keep the app path primary: project switching, project-brief/source edits, readiness checks,
  confirmed project runs, review status, saved next steps, saved history, and project-file
  saves should work through the local server without requiring terminal
  commands.
- Keep file inspection job-based and read-only: thesis, source material,
  evidence and gaps, run outputs, report readiness, saved history, and assumptions
  should open through focused previews instead of one crowded file list.
- Keep every write explicit: the user should see what file changed, what saved history
  was saved, and which panels refreshed.

**Done when.** A reviewer can open the local webserver, switch projects,
understand the current support issue, record review status, save the next
action, start the next allowed project run when confirmed, and save a project file
without losing file or saved-history provenance.

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
  operational-diagnosis demo?
- Which guidance warnings should become hard release holds, and
  which should stay advisory?
- Which report format is most useful for outside reviewers: decision
  brief, research note, review file, or all three with different checks?
- After project index, live snapshot, and review-apply, what is the next
  smallest backend bridge that reduces first-use friction without rebuilding
  the whole CLI in a browser?
