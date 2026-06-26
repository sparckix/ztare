---
description: "Interface contract for the D4 ZTARE project workbench: users, boundaries, controller surfaces, and acceptance tests."
---

# Project workbench interface

> Up: [`docs/concepts/README.md`](README.md)

This page is the public interface contract for the D4 local ZTARE Project
Workbench. It is narrower than the full architecture and more concrete than a
product pitch. Its job is to keep the UI centered on a local project: the
thesis, the assumptions, the files behind each project check, the runs and
scores, the review trail, and the report or project file that records the
result.

D4 is useful only if a reviewer can tell what the project says, why it says it,
what is not supported, what still needs work, and which file or receipt records
each step.

## First user

The first user is a technical reviewer with local files and a question that
would be harmed by a plausible but unsupported answer: researcher, founder,
analyst, engineer, diligence reviewer, or policy/strategy reviewer.

The buying or adoption context is a high-stakes local project review. The user
already has files, sources, logs, notes, or reports. They want to know what can
be said, what should not be said, and what evidence would change the answer.

Ignored for v1:

- casual chat users
- team task-management buyers
- hosted notebook users who need cloud collaboration first
- supervisors routing background agents across many programs
- users who want an answer without inspecting evidence

## Job to be done

Turn a messy local project folder into a reviewable thesis:

```text
project -> working diagnosis -> source and evidence files
-> run check -> score/verdict -> what would change it -> report or project file
```

The UI is successful only when a user can identify the current weakest link and
open the file, command details, receipt, or review file behind every visible state.
Common work should run through the local workbench server. Command details are
visible for inspection and audit.

## First use path

The first-use outcome should be:

1. open `demo_claims` or `ops_root_cause_diagnosis_demo`
2. see the working diagnosis and ruled-out alternatives
3. see source/evidence files and any report issue
4. run preflight from the app, or inspect the command details behind the check
5. inspect the receipt or report support issue
6. save a check-level review or next step through the app when a project check is open
7. refresh the project and inspect the stamped receipt
8. leave knowing what evidence would change the answer

This is D4's first-use benchmark. A polished screen that cannot complete this
path is not release-ready.

## First screen

First screen opens directly to a project workbench. It should show:

- project and scoring-guide identity
- working diagnosis and ruled-out alternatives
- intake state
- source/evidence state
- run-check state
- latest preflight or run receipt
- latest next step
- review/report state when present
- exact next step, with command details available for audit

Current-project home should put the next project step before the workflow
guide. The five-step guide can stay available as a disclosure, but the first
scan should answer: what is this project, what should I do now, and which files
or receipts support that state?

Every visible check must carry one of:

- file path
- command details
- receipt hash or status
- review file link
- explicit no-receipt warning

First viewport should behave like a project file.
Above the table, show one dominant next move with this grammar:

```text
status -> why it matters -> evidence -> next step -> review choices
```

Charts, counts, and stage rails are secondary unless they explain that next
move. A user should not have to interpret the system before knowing what to
inspect or do.

Web surface should route the first user through plain work steps:
choose a project, inspect the thesis, prepare evidence, run checks, review the
open project check, and save the project.
Detailed traces, receipts, warnings, and backing JSON belong behind those work
steps, one level down from the first scan.
Current-project home should render that path as a visible **Use this
project** rail: choose project, read thesis, check support, run locally, and
record the review trail. The all-project entry point should say that it browses
the inventory loaded from `projects/` and must not imply that all projects
open at once.
Opening project view should lead with the current diagnosis, the dominant
next step, and the few support states needed to choose that step. The full path
through project selection, file prep, preflight, run, review, and save can stay
available behind a focused detail view.
Top-level navigation and submenus should move between project areas without
immediately covering the screen. Action buttons can open focused panels when
the user chooses a specific task.
Each selected area should also render its active work panel in the page body, so
the user can use Evidence, Runs, Review, Report, and the full project inventory
as normal app pages.
Secondary pages should use a compact page header and let the selected work panel
be the main content, keeping the full project home off every task page.
Area changes belong in the main navigation. Inside an area, use compact tabs for
that area's subviews, scoped to the subviews alone.
Page headers should summarize the active area: Evidence
headers show file/intake state, Runs headers show run readiness, Review headers
show review/next-step state, and Report headers show support/save state.

## Controller surfaces

Workbench should consume existing CLI/read-model surfaces before adding new
backend abstractions:

| UI need | Existing surface |
|---|---|
| Validate bounded intake | `ztare project intake validate --path <intake.json> --json` |
| Show what would change the diagnosis | `ztare project intake falsify --path <intake.json> ...` |
| Check source files | `ztare project source-check --project <project> --json` |
| Refresh source receipts | `ztare project source-index --project <project> --json` |
| Check evidence files | `ztare project evidence-replay --project <project> --json` |
| Summarize the support audit | `ztare project claim-support --project <project> --json` (compatibility CLI) |
| Inspect the run plan | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json` |
| Run cheapest launch check | `ztare autoresearch run ... --preflight-only` |
| Start project run after preflight | `ztare autoresearch run ... --iters <n>` |
| Block stale report promotion | `make synth-contract PROJECT=<project> RENDERER=<renderer>` |
| Apply a saved project-check review | `ztare forensic-workbench apply-review --project <project> --project-check <project_check_slug> --from <review.json>` |
| Refresh the local project data | `make forensic-workbench-data WORKBENCH_PROJECT=<project>` |

For v0.4 the product coverage target is the normal project job, scoped short of
the full autoresearch command surface. D4 should cover:

- choose or create a project
- add or edit the intake
- add, edit, type, preview, and check source files
- refresh file index receipts
- check evidence connection and replay state
- inspect support-audit issues and report-support reasons
- inspect the run plan and project-run readiness
- run preflight
- start a project run only after an explicit confirmation
- inspect latest score, weakest point, evidence gaps, and run history
- record a review or next step against a project check
- save a project file with the same receipts and file-change boundary the user
  saw in the app

Advanced autoresearch commands stay outside the first product path unless their
results become ordinary project state: route decision recording, projection
exports, carrier-replay batches, hillclimb/consequence/rubric audits, dispatch
canaries, subscription outcomes, and parity reports. Those can remain command
details, advisory panels, or later workbench lanes.

The CLI accepts `--project-check` as the preferred flag. `--item` and `--row`
remain accepted for old CLI commands and receipts. The workbench should expose
`project_check_label` and `project_check_slug` in product-facing payloads.

UI must render these outputs as evidence-backed state. It must not infer a
ready state from prose or hide an unsafe launch behind a green label.
An incomplete intake disables launch and names the missing surface.

## Boundaries

ZTARE owns the individual thesis/evidence workbench. It does not own the
organizational control plane.

In scope:

- local project browser
- thesis and intake inspector
- source/evidence readiness
- trace and run-readiness console
- preflight/run launch state
- run history and verdict/demotion view
- report/review-file state

Out of scope:

- accounts, billing, hosting, sharing, or cloud storage
- supervisor or multi-role cockpit
- background-agent task routing
- general chat history
- team dashboards
- generic notebook replacement

If a control is motivated by org governance beyond the in-loop
thesis/evidence lifecycle, it belongs outside v1.

## Local data boundary

Workbench is local-first. It reads repository files and launches local
actions through the workbench server, without requiring private cloud state to render truth. If a review
point uses unavailable private data, it must say so and show the missing path or
receipt, leaving the gap explicit for the user to resolve.

## Project list model

V0.4 D4 workbench consumes explicit read models built from the repository.
Offline snapshot mode renders one generated project-data file:

```text
selected project slug
-> make forensic-workbench-data WORKBENCH_PROJECT=<project>
-> forensic-workbench/public/workbench_snapshot.json
-> local React project file
```

Live read mode wraps the same builder in a workbench server:

```text
GET /api/status
-> server, built app, project-data file, and project-index readiness

GET /api/projects
-> project index from project-local intakes and public example intakes,
   with `ready_count`, `folder_count`, and `pending_folder_count` so the UI can
   distinguish openable projects from project folders that still need an intake.
   `intake_ready_projects`/`projects` are the entries that can open immediately;
   `all_project_folders` is the rich inventory for every folder under
   `projects/`; `project_folders` is a compact compatibility list with the same
   project ordering and `openable` status.

GET /api/workflow
-> six-step project steps plus server-owned summary and next-step fields, so the
   first screen can show the next local action without rebuilding priority only
   in the browser. Each step also carries the workbench destination and local
   action label the UI should open.

POST /api/project-create
-> create a local source project and project intake, then return action results,
   created paths, write boundary, refreshed project index, and first project data
   when available; partial source-initialization writes must be reported even if
   intake creation fails

POST /api/source-import
-> write one new validated source file, refuse existing filenames, update
   source_type_map, append a source-import receipt, run source-check, and return
   refreshed state; the UI may stage the returned source path in the intake
   draft, but the intake write still requires Save intake

GET /api/sources?project=<project>
-> list typed source files using the same source-check read model

GET /api/source-file?project=<project>&relative=<relative_raw_path>
-> read one bounded source file for editing, including source type and body

POST /api/source-edit
-> update one existing source file only when body or type changed, update
   source_type_map, append a source-edit receipt, run source-check, and return
   refreshed state

GET /api/snapshot?project=<project>&rubric=<rubric>&intake=<intake>
-> fresh single-project workbench data bound to the selected intake

GET /api/health?project=<project>&rubric=<rubric>&intake=<intake>
-> run-health summary plus action-guidance source warnings,
   advisory recommendations, report-hold rules, counts, and evidence links

GET /api/trace?project=<project>&rubric=<rubric>&intake=<intake>
-> run-plan summary: readiness checks, preflight receipt state, plan,
   graph summaries, and command details

POST /api/preflight
-> run the `ztare autoresearch run ... --preflight-only` check and
   return command details, exit code, preflight receipt state, and refreshed project data

POST /api/run
-> start the selected `ztare autoresearch run ... --iters <n>` command
   after preflight has accepted the project, then return output tails, refreshed
   trace, run history, and project state. The React app must ask for a second
   in-app confirmation before it sends `confirmed: true`; opening the Run panel
   or clicking the first run button must not launch a model-backed run. The
   first click should request a no-write server preview and show the server's
   command details plus files that may change.

POST /api/source-action
-> run one allowlisted source/evidence action (`source_check`, `source_index`,
   `evidence_bind`, or `evidence_replay`) and return command details, exit code,
   output tail, parsed data when available, refreshed project data, and a D4
   source-action receipt for write-producing actions

GET /api/report-contract?project=<project>&renderer=<renderer>
-> report status, support reasons, synthesis input binding, previewable backing files, and command detail

A stale or unsupported report stays in needs-support state when the support
contract is missing, stale, or disconnected from the current project.

GET /api/file?path=<repo-relative-path>
-> read-only bounded text preview for a selected workbench-safe repo path;
   allowed roots are project files, docs, examples, public analytics, workbench
   artifacts, rubrics, and selected root docs. Papers, absolute paths,
   parent-directory escapes, repo metadata, internal planning, and private
   research paths must be rejected before any file read.

GET /api/receipts?project=<project>
-> recent review, next-step, intake-edit, source-import, source-edit,
   source-action, and project-file receipts from project ledgers

GET /api/run-history?project=<project>
-> latest and recent run scores, weakest points, evidence gaps, synthesis
   patterns, and backing run-history paths

GET /api/evidence-support?project=<project>
-> support-audit status, weak/unsourced counts, source-context status, missing
   evidence-file errors, previewable source paths, and copyable support-audit command

POST /api/project-file
-> write the current project file into the project workspace, append a
   project-file receipt, and return the saved file path plus receipt paths

POST /api/review
-> append project-check receipt and refresh project data

POST /api/next-step
-> append project-check next-step receipt and refresh project data

POST /api/item-action
-> compatibility alias for old next-step clients and receipt tooling

POST /api/row-action
-> compatibility alias for old next-step clients and receipt tooling

POST /api/case-file
-> compatibility alias for old project-file clients and receipt tooling

GET /api/claim-support?project=<project>
-> compatibility alias for old support-audit clients and receipt tooling
```

React app calls `/api/status` before treating the workbench as live.
`api_ready` is the live-editing gate: it means the server can serve project
state and write through the explicit API. `app_built` and `snapshot_available`
are separate serving/offline-snapshot checks, because Vite dev mode can still be live
when the built React app is absent. Projects / Files view shows the same
status so the user can inspect which mode they are using and which default
project the server sees.
Status payload should list preferred routes under `api.endpoints` and
legacy aliases under `api.compatibility_endpoints`, so compatibility does not
look like the main integration path.

Review and next-step POST bodies should send `project_check_slug`. `item_slug`
and `row_slug` remain accepted for old clients and receipt tooling. Saved review
and next-step files and stamped receipts should include product-facing
`project_check_label` and `project_check_slug`, plus `item_label` and
`item_slug` aliases, while keeping `row` and `row_slug` for CLI compatibility.
Snapshot responses and browser project files should expose `project_checks` and
`project_check_count`. `items`/`item_count` and `rows`/`row_count` remain
compatibility aliases. Receipt history should expose `next_step` and
`project_check` path aliases for the saved next-step ledger, while keeping
`item_action` as the old path alias. Project files should expose `audit_commands`.
`command_queue` remains a compatibility alias for existing consumers.
Visible product copy should say check, review, and next step. Terms such as
`row_action`, `source_action`, and `action` belong in API, schema, command details, and
ledger compatibility surfaces, staying out of the first-path labels. Checklist details and
inspector summaries should normalize those legacy terms before display.

If the server is absent at startup, the app may fall back to the last generated
offline project data. Once the server is detected, project-specific data or
review-refresh failure must stay visible to the user, with any stale offline
data held back until the user acts on the failure.

That is deliberate. Browser-side filesystem discovery would hide which project
state was inspected and which command produced it. For this reason, the project browser should
keep using generated or API-served read models built from `projects/*`
and example intakes. It should show the selected project directory, intake,
report contract, live trace console, latest-review receipt, latest saved next step,
latest project-file write, a left-rail all-project inventory, and a project
switchboard that also shows project folders with no workbench intake. Every
folder under `projects/` should stay searchable and available. Intake-ready,
human-named, and file-backed projects should sort first so the first scan is
usable without hiding historical folders. Intake-ready projects should be keyed
by project plus intake with intake mode, source-ref coverage, report-contract
presence, recent receipt paths, and any per-project intake load error before
the user switches projects. It should use
the same new-project form to add an intake to an existing folder only when that
folder has no intake yet, with write paths previewed before the server writes.
Folders under `projects/` should be marked by the server with project status,
intake readiness, source-folder state, and receipt paths. Intake-ready is one
status a project folder may carry; every folder under `projects/` is a project.
`/api/projects` and `/api/status`
should expose `project_inventory_scope: all_projects_directory`,
`inventory_root: projects/`, and `inventory_includes_all_project_folders: true`
so the browser can prove it is not showing only intake-ready projects.
Left rail should summarize all projects and intake-ready projects in plain
counts, with an All projects button that opens the full project view. Full
project view should keep every project searchable and available while sorting
intake-ready, human-named, and file-backed projects before generated folders.
Current-project home should make the same inventory reachable with a
plain-language Browse all projects action and show the live folder count from
the server.
Break the layout into primary project areas with focused submenus in the left rail:
Projects / Current project, All projects, Add intake, Files; Thesis / Status,
Diagnosis, Evidence; Files / File check, Intake, Add source, Edit source; Runs /
Plan, Preflight, Start run, Results, Advisories; Review / Open issues, Save
review, Save next step, Receipts; Report / Support check, Report inputs, Project
file.
Clicking a primary project area should open that area's first focused panel, not
only change a highlighted label.
When the left rail collapses on smaller screens, the same submenu should appear
as a compact in-page menu.
First screen should answer what project is open, what thesis is under
review, what evidence is attached, what the latest run says, what needs
support, and what the next step is. It should present a compact project-facts
strip, a Next steps queue ordered from the live project state, and compact
project-area navigation for the common moves: open a project, inspect the
thesis, prepare evidence, run checks, review, and save. Primary action
should come from project state (unresolved file or support issues first, then
ready preflight or project run, then the next useful inspect/save task), not
from whichever check is currently selected.
Project-area navigation should stay subordinate to that queue. It exists so a
first user can open focused detail views without having to interpret the whole system
model before acting.
Dense tables, editors, traces, receipts, report details, and selected check
inspection should open as focused detail views so they do not crowd the first viewport.
Next action queue should still give a direct path to the current report
issue or selected project step, so a reviewer can move without interpreting the
whole project model first.
Working diagnosis should also be visible on the first screen with ruled-out
alternatives and change-test status, plus direct actions to inspect or edit the
intake. A first user should know what project they are reviewing before opening a
detail view.
After a server-backed write, the first screen should show the latest write kind,
target, and refresh status before the user opens receipt details.
Project checklist and inspector belong under focused check views, so the user
can inspect evidence and decide an action without scrolling through every
edit/report tool. Each relevant project area should also surface working-diagnosis status,
source/evidence readiness, recent receipt history, run history/verdict state,
and report state.
Support-audit panel should show whether the compiled support evidence file is
present, how many support issues or source gaps remain, which local sources were
verified, and the exact command details that rebuild the audit.
Source/evidence readiness panel should show file-index status, evidence
connection status, replay status, source/evidence files, and the command details
that rebuild those checks.
Add source should let the user stage the new source path into source or evidence files
without writing the intake file until Save intake records the edit receipt.
Source-file editor should show pending body/type changes and refuse no-op
saves, so source-edit receipts correspond to actual file or metadata changes.
Project switches, full refreshes, intake reloads, and opening a source from
disk should use an in-app confirmation dialog before replacing pending intake
or source-file edits.
First viewport should also show an unsaved-edits strip when a local intake,
source, or source-import draft is dirty. That strip should link directly to the
related editor so the user can save or clear the draft before changing projects.
Intake editor should preview the intake file plus intake-edit ledger/latest
receipt paths before Save intake is enabled.
Report panel should show the support reasons, synthesis input-binding
status, contract file path, and exact support command.
Manual-commands panel should collect selected check, trace, report, health, and
next-step commands into one list for inspection and copy. The browser must not run
arbitrary shell commands. App buttons call fixed workbench-server endpoints for
the supported actions: project creation, intake edits, add source/edit source,
source checks, evidence connection/replay, preflight, review/next-step receipts, and
project-file saves.

Index must include both first-run demos:

- `demo_claims`, backed by the public ready demo intake
- `ops_root_cause_diagnosis_demo`, backed by its project-local intake

If a project has no materialized report-support context, the project still opens.
Report support project check should show `report_support_unavailable` and keep
the rest of the workbench working. A missing report is a reviewable state that
keeps the project visible.

Writes should stay explicit. Live mode calls the workbench server to persist
review or next-step file under the project workspace folder before writing the
receipt. Offline snapshot mode may save a review or next-step file for a CLI handoff.
Either way, the visible trail is file, receipt ledger,
receipt history, latest receipt, and refreshed project data.
Any panel that can write project files should show a visible write boundary
before the action buttons: what the server-backed button writes, and which
download/copy/preview actions stay browser-only. Creation, add source,
source edit, preflight, fixed source/evidence action, review, next-step, and
project-file panels should also preview the exact or server-patterned payload,
metadata, ledger, and latest-receipt paths that can change before the write
runs. Preflight writes its launch-check receipt to the project telemetry ledger
at `projects/<project>/workspace/iteration_telemetry.jsonl`.
`/api/status` should advertise the same behavior contract the UI uses: every
primary action has `writes_project_files`, `browser_writes`,
`requires_confirmation`, `behavior`, and `write_path_templates` fields. The
status payload also exposes `action_summary` plus the lower-level
`write_contract` counts: `action_count`, `write_action_count`,
`write_without_confirmation_count`, `confirmation_required_count`, and
`read_only_action_count`. The current D4 surface has 17 primary actions: 10
write files or receipts immediately, 1 asks first, and 6 are read-only.
`write_action_count` includes the ask-first action. UI should display the
clearer split from `file_change_summary`, while `action_summary` remains as a
compatibility field: `10 write / 1 ask first / 6 read-only`.
Project-run panel is stricter: it requests a no-write `/api/run` preview,
shows the server-provided command detail and files that may change, then opens a
confirmation dialog before the server may receive `confirmed: true`.
Project-file panel should preview the exact project file before save/download/copy, so
the user can inspect the bundle without creating a browser download or server
write. Saved bundle should include `live_context.project_file_write_plan`
with the same project-file paths, no-hidden-browser-write boundary, and
preview/download/copy actions shown before Save.
Before saving, the project-file panel should also show an Included now checklist:
project checks, source files, project steps, report support, receipts, run
history, and the support audit. Each item should be clearly marked present in the
bundle or missing/unavailable.
Preview should use product names: `project_check_count`, `action_details`,
`evidence_support`, and `evidence_support_file_path`. Compatibility aliases may
remain in the saved JSON for old scripts. A first user should be able to read the
project file without decoding legacy schema aliases.
After project creation, preflight, live review, saved next step, intake-edit,
add-source/edit-source, source/evidence write, or project-file save, the app
should show the stamped receipt schema, target, project context, changed fields or
change summary, ledger path, latest path, source path, and hash before the user
has to inspect the full history. Ledger, latest-receipt, and saved-file paths
should be previewable when they point to repository files. Source/evidence write receipts
should stamp the produced output file hash when the underlying command exposes
one. Affected live panels should
refresh together: trace, report contract, health, support audit, receipt
history, intake editor, project index, and source list when sources changed.
If the intake editor has unsaved local edits, the refresh should preserve the
draft and report the skipped intake refresh, leaving those edits intact.
UI should name the panels that refreshed and separately name any panel whose
refresh failed, so a saved receipt is never mistaken for a fully refreshed project.
Opening a different project, refreshing the current project, or falling back to
offline project data should clear prior run/write activity from the screen. A
new-project write is the exception: after the reset into the new project, the created
paths and write receipt should remain visible so the user can verify what just
changed.
When a check is selected, the review strip should also show the latest saved
review and next-step state for that same check from the receipt history, so a
reviewer does not overwrite or duplicate a review blindly.
Review and next-step save panels should show the selected project check before
the write action: status, evidence-link count, first evidence path, and latest
review state. A reviewer should know exactly what they are saving against before
the server writes a receipt.

File inspection is read-only. The browser may request one repository-relative
path from the workbench server and display a bounded text preview. It must not crawl
the filesystem, infer hidden project state, or turn a preview into a write.

Project-file creation should also be explicit. A browser-generated project file may package
the current project data, project directory/intake/receipt context, project-check evidence
links, project-path next-step context, live trace/report/health context,
workbench status/action summary/write contract/file-preview boundary, latest
preflight result, source-file inventory, latest add-source/edit-source receipts
and hashes, advisory action-guidance recommendations, command detail list, latest
visible write receipt, latest write-refresh result, pending intake draft edits,
and recent receipt paths for download or copy, but it must not write project
files or imply that a project needing support has been reviewed.
When a selected project is intake-scoped, UI panels and saved project files
should show `Project key` and `Intake` as separate facts. The combined
project-plus-intake key is not the intake path. Labeling it that way makes the
project model hard to inspect.
New project-file fields should use product names such as `display_label`,
`project_check_label`, `project_check_count`, `project_checks`,
`latest_project_check`, `readiness_checks`, `graph_summaries`,
`preflight_receipt`, `evidence_support`, and `evidence_support_file_path`.
Older schema names may remain as compatibility aliases while old receipts and
scripts still consume them. The browser preview should hide or rename those
aliases when a product-named field is available.

Advisories and suggested next steps are advisory in D4. They may tell the reviewer that a
project has run-health attention, provider-runtime risk, stale source-warning
inputs, or action-guidance warnings. A reviewer may stage one of those
warnings as a next move on the affected check. Saving that note uses the
same explicit next-step receipt path as any manual next-step note. A warning
does not make release claims stronger and does not become hidden control
authority. Health view should show advisory provenance: recommendation
source path, generated-at time, and source-warning backing file when present.

## Acceptance tests

Any D4 release candidate must pass these checks:

1. A user can open `demo_claims` or `ops_root_cause_diagnosis_demo`.
2. An intake with missing inputs disables launch and names what is missing.
3. A ready intake can run preflight and show a visible receipt.
4. Source-ready, evidence-ready, and loop-ready are visually distinct.
5. Generated material and judgment/demotion material are visually distinct.
6. A stale or unsupported report remains in needs-support state when the support
   contract says it is not ready.
7. Every visible check has provenance or an explicit no-file/receipt warning.
8. A saved review can be applied through the CLI, and the refreshed project data
   shows the latest review receipt.
9. A saved project file carries the same read/write/ask-first action split and
   no-hidden-browser-write boundary that the UI showed before save.
10. The offline snapshot and `workbench_snapshot.json` use product-facing
    display labels for the first path: working diagnosis, source files, evidence
    files, run check, report support, latest review, and latest next step.
11. Intake-scoped panels and saved project-file context display `Project key`
    separately from the intake path.
12. The current-project home shows the five-step work rail and a Browse all
    projects action backed by the live `projects/` inventory count.
13. Review and next-step save panels show selected-project-check context before
    saving. Project-file panel shows the Included now checklist before saving.
14. Supervisor, multi-role, multi-user, hosted, billing, and background-agent
   controls are absent.

D4 can grow incrementally. It may not be opaque.
