---
description: "Interface contract for the D4 ZTARE forensic workbench: users, boundaries, controller surfaces, and acceptance tests."
---

# Forensic Workbench Interface

> **Up:** [`docs/concepts/README.md`](README.md)

This page is the public interface-positioning contract for the D4 local ZTARE
workbench. It is narrower than the full architecture and more concrete than a
product pitch. Its job is to keep the UI centered on local claim review instead
of generic chat or dashboards.

D4 is useful only if it preserves the review boundary: bounded claim, local
sources, evidence state, run readiness, trace, preflight, verdict or demotion,
next falsifier, and exportable review artifact.

## First User

The first user is a technical reviewer with local artifacts and a decision that
would be harmed by a plausible but unsupported answer: researcher, founder,
analyst, engineer, diligence reviewer, or policy/strategy reviewer.

The buying or adoption context is a high-stakes local claim review. The user
already has files, sources, logs, notes, or reports. They want to know what can
be said, what must be demoted, and what evidence would change the verdict.

Ignored for v1:

- casual chat users;
- team task-management buyers;
- hosted notebook users who need cloud collaboration first;
- supervisors routing background agents across many programs;
- users who want an answer without inspecting evidence.

## Job To Be Done

Turn a messy local claim-and-evidence bundle into an auditable claim state:

```text
project -> bounded claim -> sources/evidence -> readiness
-> trace/preflight -> verdict or demotion -> next falsifier -> export
```

The UI is successful only when a user can identify the current weakest link and
open the file, command, receipt, or review artifact behind every visible state.

## First Five Minutes

The first five-minute outcome should be:

1. open `demo_claims` or `ops_root_cause_diagnosis_demo`;
2. see the bounded claim and non-claims;
3. see source/evidence readiness and any blocker;
4. run or inspect a preflight-only command;
5. inspect the receipt or blocked-export reason;
6. save a row-level review file when a decision is needed;
7. apply the review file through the CLI and refresh the snapshot;
8. leave knowing the next falsifier or missing surface.

This is D4's first-use benchmark. A polished screen that cannot complete this
path is not release-ready.

## First Screen

The first screen is a project workbench, not a blank prompt. It should show:

- project and rubric identity;
- bounded claim and non-claims;
- intake state;
- source/evidence state;
- trace and run-readiness state;
- latest preflight or run receipt;
- verdict/demotion/export state when present;
- exact next command or explicit blocked action.

Every row must carry one of:

- file path;
- command;
- receipt hash or status;
- review artifact link;
- explicit no-receipt warning.

The first viewport should behave like a case file, not a passive dashboard.
Above the table, show one dominant next move with this grammar:

```text
status -> why it matters -> evidence -> primary action -> review choices
```

Charts, counts, and stage rails are secondary unless they explain that next
move. A user should not have to interpret the system before knowing what to
inspect or do.

## Controller Surfaces

The workbench should consume existing CLI/read-model surfaces before adding new
backend abstractions:

| UI need | Existing surface |
|---|---|
| Validate bounded intake | `ztare project intake validate --path <intake.json> --json` |
| Show falsifier behavior | `ztare project intake falsify --path <intake.json> ...` |
| Check typed source readiness | `ztare project source-check --project <project> --json` |
| Refresh source receipts | `ztare project source-index --project <project> --json` |
| Check evidence replay | `ztare project evidence-replay --project <project> --json` |
| Summarize claim support | `ztare project claim-support --project <project> --json` |
| Read run-readiness trace | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json` |
| Run cheapest launch check | `ztare autoresearch run ... --preflight-only` |
| Block stale report promotion | `make synth-contract PROJECT=<project> RENDERER=<renderer>` |
| Apply a saved row review | `ztare forensic-workbench apply-review --project <project> --row <row_slug> --from <review.json>` |
| Refresh the local workbench snapshot | `make forensic-workbench-data WORKBENCH_PROJECT=<project>` |

The UI must render these outputs as evidence-backed state. It must not infer a
ready state from prose or hide an unsafe launch behind a green label.

## Boundaries

ZTARE owns the individual claim/evidence workbench. It does not own the
organizational control plane.

In scope:

- local project browser;
- claim and intake inspector;
- source/evidence readiness;
- trace and run-readiness console;
- preflight/run launch state;
- run history and verdict/demotion view;
- export/review-artifact state.

Out of scope:

- accounts, billing, hosting, sharing, or cloud storage;
- supervisor or multi-role cockpit;
- background-agent task routing;
- general chat history;
- team dashboards;
- generic notebook replacement.

If a control is motivated by org governance rather than the in-loop
claim/evidence lifecycle, it belongs outside v1.

## Local Data Boundary

The workbench is local-first. It should read repository files and launch local
commands. It should not require private cloud state to render truth. If a row
uses unavailable private data, the row must say so and show the missing path or
receipt rather than filling the gap with a model-written explanation.

## Project List Model

The v0.4 D4 workbench consumes explicit read models, not raw browser access to
the repository. Static mode renders one generated project snapshot:

```text
selected project slug
-> make forensic-workbench-data WORKBENCH_PROJECT=<project>
-> forensic-workbench/public/workbench_snapshot.json
-> local React case file
```

Live read mode wraps the same builder in a local API:

```text
GET /api/projects
-> project index from project-local intakes and public example intakes

POST /api/project-create
-> create a local source project and project intake, then return command results,
   refreshed project index, and a first snapshot when available

POST /api/source-import
-> write one new validated raw source file, refuse existing filenames, update
   source_type_map, append a source-import receipt, run source-check, and return
   refreshed state

GET /api/sources?project=<project>
-> list typed raw sources using the same source-check read model

GET /api/source-file?project=<project>&relative=<relative_raw_path>
-> read one bounded raw source file for editing, including source type and body

POST /api/source-edit
-> update one existing raw source file only when body or type changed, update
   source_type_map, append a source-edit receipt, run source-check, and return
   refreshed state

GET /api/snapshot?project=<project>&rubric=<rubric>&intake=<intake>
-> fresh single-project workbench snapshot bound to the selected intake

GET /api/health?project=<project>&rubric=<rubric>&intake=<intake>
-> kernel-health summary plus action-intelligence source-health warnings,
   advisory recommendations, blocking rules, counts, and evidence refs

GET /api/trace?project=<project>&rubric=<rubric>&intake=<intake>
-> autoresearch trace summary: carrier chain, run gate, plan, graph, and commands

POST /api/preflight
-> run the bounded `ztare autoresearch run ... --preflight-only` check and
   return the command, exit code, loop-admission trace, and refreshed snapshot

POST /api/source-action
-> run one allowlisted source/evidence action (`source_check`, `source_index`,
   `evidence_bind`, or `evidence_replay`) and return the command, exit code,
   output tail, parsed JSON when available, refreshed snapshot, and a D4
   source-action receipt for write-producing actions

GET /api/report-contract?project=<project>&renderer=<renderer>
-> report/export status, blocker reasons, synthesis input binding, contract path, and command

GET /api/file?path=<repo-relative-path>
-> read-only bounded text preview for a selected file/evidence path

GET /api/receipts?project=<project>
-> recent review, row-action, intake-edit, source-import, source-edit,
   source-action, and case-file receipts from project ledgers

GET /api/run-history?project=<project>
-> latest and recent run scores, weakest points, evidence gaps, synthesis
   patterns, and backing run-history paths

GET /api/claim-support?project=<project>
-> claim-support status, weak/unsourced counts, source-context status, missing
   evidence-file errors, previewable source paths, and copyable support-audit command

POST /api/case-file
-> write the current case-file JSON into the project workspace, append a
   case-file receipt, and return the saved artifact path plus receipt paths

POST /api/review
-> append row-level review receipt and refresh snapshot

POST /api/row-action
-> append row-level action receipt and refresh snapshot
```

If the API is absent at startup, the app may fall back to the last generated
static snapshot. Once the API is detected, a project-specific snapshot or
review-refresh failure must stay visible to the user instead of silently
swapping in stale static data.

That is deliberate. Browser-side filesystem discovery would hide which project
state was inspected and which command produced it. The project browser should
therefore keep using generated or API-served read models built from `projects/*`
and example intakes. It should show the selected project directory, intake,
report contract, live trace console, latest-review receipt, latest saved row action,
latest case-file write, and a project switchboard with intake mode,
source-ref coverage, report-contract presence, and recent receipt paths before
the user switches cases. It should
also show bounded-claim status, source/evidence readiness, recent receipt
history, run history/verdict state, and report/export state before the user
opens a case.
The claim-support panel should show whether the compiled claim-support evidence file is
present, how many claims are weak or unsourced, which local sources were
verified, and the exact command that rebuilds the audit.
The source/evidence readiness panel should show source-index status, evidence
binding, output binding, replay status, source/evidence files, and the commands
that rebuild those checks.
The raw-source editor should show pending body/type changes and refuse no-op
saves, so source-edit receipts correspond to actual file or metadata changes.
The report/export panel should show the blocker reasons, synthesis input-binding
status, contract file path, and exact support command.
The command cockpit should collect selected-row, trace, report, health, and row
commands into one queue for inspection and copy. The browser should not run
arbitrary shell commands; the only live launch action in D4 is the dedicated
preflight panel, which calls the local API to run the bounded preflight-only
command surfaced by the trace.

The index must include both first-run demos:

- `demo_claims`, backed by
  `examples/project_packets/ready_demo_claims_intake.json`;
- `ops_root_cause_diagnosis_demo`, backed by its project-local intake.

If a project has no materialized report-support context, the case still opens.
The report/export row should be blocked with `report_support_unavailable`
instead of failing the whole workbench. A missing report is a reviewable state,
not a reason to hide the project.

Writes should stay explicit. Static mode saves a review or row-action file,
then the user can apply it through the CLI. Live mode calls the local API to
persist the same review or row-action JSON under the project workspace before
writing the receipt. Either way, the visible trail is file, receipt ledger,
receipt history, latest receipt row, and refreshed snapshot.
After a live review, row-action, intake-edit, source import/edit,
source/evidence write action, or case-file save, the app should show the
stamped receipt schema, target, ledger path, latest path, source path, and hash
before the user has to inspect the full history. Ledger, latest-receipt, and
written-artifact paths should be previewable when they point to repository
files. Source/evidence write receipts should stamp the produced artifact hash
when the underlying command exposes one. The affected live panels should
refresh together: trace, report/export contract, health, claim support, receipt
history, project index, and source list when sources changed.
The UI should name the panels that refreshed and separately name any panel whose
refresh failed, so a saved receipt is never mistaken for a fully refreshed case.
When a row is selected, the review strip should also show the latest saved
review and row-action state for that same row from the receipt history, so a
reviewer does not overwrite or duplicate a decision blindly.

File inspection is read-only. The browser may request one repository-relative
path from the local API and display a bounded text preview. It must not crawl
the filesystem, infer hidden project state, or turn a preview into a write.

Case export should also be explicit. A browser-generated case file may package
the current snapshot, project directory/intake/receipt context, row evidence
refs, live trace/report/health context, latest preflight result, raw-source
inventory, advisory action-intelligence recommendations, command queue, latest
visible write receipt, latest write-refresh result, and recent receipt paths
for download or copy, but it must not write project files or imply that a
blocked case is reviewed.

Health and action rows are read-only in D4. They may tell the reviewer that a
project has kernel-health attention, provider-runtime risk, stale source-health
inputs, or advisory action-intelligence warnings. They do not make release
claims stronger and do not become hidden control authority.

## Acceptance Tests

Any D4 release candidate must pass these checks:

1. A user can open `demo_claims` or `ops_root_cause_diagnosis_demo`.
2. A blocked intake disables launch and names the missing surface.
3. A ready intake can run preflight and show a visible receipt.
4. Source-ready, evidence-ready, and loop-ready are visually distinct.
5. Generated material and judgment/demotion material are visually distinct.
6. A stale or unsupported report remains blocked when the support contract
   blocks it.
7. Every visible row has provenance or an explicit no-receipt warning.
8. A saved row review can be applied through the CLI, and the refreshed
   snapshot shows a latest-review receipt row.
9. Supervisor, multi-role, multi-user, hosted, billing, and background-agent
   controls are absent.

D4 can grow incrementally. It may not be opaque.
