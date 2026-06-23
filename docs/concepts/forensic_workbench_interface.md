---
description: "Interface contract for the first ZTARE forensic workbench prototype: users, boundaries, controller surfaces, and acceptance tests."
---

# Forensic Workbench Interface

> **Up:** [`docs/concepts/README.md`](README.md)

This page is the public interface-positioning contract for the first local
ZTARE workbench prototype. It is narrower than the full architecture and more
concrete than a product pitch. Its job is to prevent a future UI from becoming
a generic chat surface or dashboard.

The first prototype is allowed only if it preserves the review boundary:
bounded claim, local sources, evidence state, run readiness, trace, preflight,
verdict or demotion, next falsifier, and exportable review artifact.

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

This is the first prototype's benchmark. A pretty screen that cannot complete
this path is not progress.

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

The prototype should consume existing CLI/read-model surfaces before adding new
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

The prototype is local-first. It should read repository files and launch local
commands. It should not require private cloud state to render truth. If a row
uses unavailable private data, the row must say so and show the missing path or
receipt rather than filling the gap with a model-written explanation.

## Project List Model

The v0.4 D4 prototype consumes explicit read models, not raw browser access to
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

GET /api/snapshot?project=<project>&rubric=<rubric>&intake=<intake>
-> fresh single-project workbench snapshot bound to the selected intake

GET /api/health?project=<project>&rubric=<rubric>&intake=<intake>
-> kernel-health summary plus action-intelligence source-health warnings

GET /api/file?path=<repo-relative-path>
-> read-only bounded text preview for a selected file/evidence path

GET /api/receipts?project=<project>
-> recent review, row-action, and intake-edit receipts from project ledgers

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
report contract, latest-review receipt, latest saved row action, bounded-claim
status, source/evidence readiness, recent receipt history, and report/export
state before the user opens a case.

The index must include both first-run demos:

- `demo_claims`, backed by
  `examples/project_packets/ready_demo_claims_intake.json`;
- `ops_root_cause_diagnosis_demo`, backed by its project-local intake.

If a project has no materialized report-support context, the case still opens.
The report/export row should be blocked with `report_support_unavailable`
instead of failing the whole workbench. A missing report is a reviewable state,
not a reason to hide the project.

Writes should stay explicit. Static mode saves a review or row-action file,
applies it through the CLI, then refreshes the snapshot. Live mode may call a
local API to write the same receipt directly. Either way, the visible trail is
file or API payload, receipt ledger, receipt history, latest receipt row, and
refreshed snapshot.

File inspection is read-only. The browser may request one repository-relative
path from the local API and display a bounded text preview. It must not crawl
the filesystem, infer hidden project state, or turn a preview into a write.

Case export should also be explicit. A browser-generated case packet may package
the current snapshot, row evidence refs, and recent receipt paths for download
or copy, but it must not write project files or imply that a blocked case is
reviewed.

Health and action rows are read-only in D4. They may tell the reviewer that a
project has kernel-health attention, provider-runtime risk, stale source-health
inputs, or advisory action-intelligence warnings. They do not make release
claims stronger and do not become hidden control authority.

## Acceptance Tests

Any prototype must pass these before it is treated as release-relevant:

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

The prototype can be incomplete and still useful. It may not be opaque.
