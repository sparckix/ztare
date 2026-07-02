---
description: "Interface contract for the ZTARE Project Workbench: users, boundaries, controller interfaces, and acceptance tests."
---

# Project workbench interface

> Up: [`docs/concepts/README.md`](README.md)

The public interface contract for the local ZTARE Project Workbench. It
keeps the UI centered on a local project: the thesis, the assumptions, the
run-learned axioms and constraints, the files behind each open issue, the runs
and scores, the review trail, and the report or project file that records the
result.

The Project Workbench is useful only if a reviewer can tell what the project
says, why it says it, what is not supported, what still needs work, and which
file or saved work explains each step.

## First users

The first users are people doing source-backed work where a plausible but
unsupported answer would cause damage: researchers, founders, analysts,
engineers, diligence reviewers, lawyers, policy teams, product teams, security
reviewers, and anyone reviewing AI-assisted work before it becomes a
deliverable.

The adoption context is a local project review. The user already has files,
sources, logs, notes, reports, code, datasets, proof notes, or formal fragments.
They want to know what can be said, what should not be said, and what evidence
would change the answer. Profession-level examples live in
[`ztare_use_cases.md`](../guides/ztare_use_cases.md).

Ignored for v1:

- casual chat users
- team task-management buyers
- hosted notebook users who need cloud collaboration first
- supervisors routing background agents across many programs
- users who want an answer without inspecting evidence

## Job to be done

Turn a messy local project folder into a reviewable thesis:

```text
project -> thesis -> source and evidence files
-> run readiness -> score/verdict -> what would change it -> report or project file
```

For investigative projects, the same path should read in plainer terms:

```text
project -> working diagnosis -> source and evidence files
```

The UI is successful only when a user can identify the current weakest link and
open the file, command, saved work, or review file behind every
visible state.
Common work should run through the local workbench server. Commands are
visible for inspection and audit.
Before the readiness check or a confirmed project run, the page should show the
target files, history path, and no-change boundary. The exact path list can sit
behind disclosure, but the user should know what will change before clicking.
File contents should open in a focused viewer when the user asks to preview a
thesis, source, evidence file, report input, saved history item, or saved
project file.
The viewer should give a short role-specific guide before raw text, so the user
knows whether they are reading a thesis, evidence file, original source, report
input, or saved work.
It should also offer three modes: Read for the short guide and skim view,
Structure for the file-specific outline, and Raw for the exact server-limited
text. Use Structure for saved project files, saved history, source indexes, source
notes, evidence bundles, evidence gaps, run outputs, report readiness, scoring
guides, and launch previews. Use Read for prose and small summaries. Use Raw
only when exact text matters.
The quick read should cover common file shapes: Markdown sections, JSON fields
and referenced paths, CSV columns and first data row, then the raw text.
Referenced repo paths should be clickable inside the viewer when they are safe
to preview. A saved work should lead to the files it changed; an evidence or
report file should lead back to the sources or evidence files it names.
When report readiness names an internal authority field as the source of a next
action, the workbench should attach previewable project files that make the
action inspectable instead of showing the internal field name as the main
evidence.
The main project pages should not try to visualize every file inline. They
should group files by the user's job and open the focused viewer when the user
needs the contents.

## Working With Coding Agents

Many users will already use Codex, Claude Code, notebooks, search tools, or
domain scripts. The Project Workbench should not replace those sessions. It
should give them a project home.

A good session can explore freely, write notes, run code, make plots, draft
proof steps, summarize sources, or produce a memo. ZTARE becomes useful when
the user wants to know what survived that session:

```text
outside tool session -> project files -> research map
-> source/evidence check -> run or repair -> report/readiness decision
```

So the workbench should support three levels:

- **Explore:** add or edit project files without claiming they are evidence yet.
- **Organize:** map the thesis, support, tensions, branches, and useful files.
- **Check:** run ZTARE checks only when a thesis, report, or proof target needs
  support.

This keeps the system useful for high-taste research scaffolds. The model or
coding agent can remain creative. The project decides what is source material,
what is evidence, what is still open, and what should be checked next.
Advanced agents working inside this repository may also use Research Director
utilities for capability recall, route choice, gap typing, graph actions, and
pattern contracts. The Project Workbench should surface the project files and
state those utilities affect, not every advanced control.

Project Home should show a compact file inventory before the evidence map:
project brief, thesis, raw sources, evidence, active gaps, run outputs, report
support, saved project files, saved history, and run-learned backing files. The
default slice should make the important files previewable without turning the
first screen into a file dump. When a project has a saved project file, the
inventory should expose direct preview buttons for the saved file, latest
saved work, and history ledger before the grouped file list.
The inventory should be grouped by the user's job: understand the thesis, inspect
sources, check evidence, review runs, inspect the report, inspect saved history,
or inspect assumptions and constraints. A flat list of file paths is allowed
only as an expanded detail.
Inline previews are useful for small recovery cards, but the main pages should
not become document readers.

## First use path

The first-use outcome should be:

1. open `demo_claims` or `ops_root_cause_diagnosis_demo`
2. see the thesis and ruled-out alternatives
3. see the working diagnosis and ruled-out alternatives when the project is a
   diagnosis or investigation
4. see project files, evidence summary, and any report issue
5. check run readiness from the app, or inspect the command behind the check
6. inspect the saved work or report readiness issue
7. save a review or next step through the app when an issue is open
8. refresh the project and inspect the saved work
9. leave knowing what evidence would change the answer

This is the Project Workbench's first-use benchmark. A polished screen that
cannot complete this path is not release-ready.
For a historical folder with files but no project brief, the benchmark is
similar: the user should select the folder, see the files used to draft the
brief, preview those files, inspect the `Connect project` write paths, and save
the brief without leaving the workbench. Recovery notes should list the folder,
files to review, file/evidence counts, and next checks; long source passages
should stay in Preview, not in editable project-brief notes by default.

## First screen

First screen opens directly to a project workbench. It should show:

- project and scoring-guide identity
- thesis and ruled-out alternatives
- run-learned axioms and derived constraints when prior iterations produced them
- project-brief state
- file/evidence state
- run-readiness state
- latest readiness-check or run record
- latest next step
- review/report state when present
- exact next step, with commands available for audit

Current-project home should put the next project step before the workflow
guide. The five-step guide can stay available as a disclosure, but the first
scan should answer: what is this project, what should I do now, and which files
or saved works support that state?
When the next step can write, the first-screen card should name the first write
target and latest history paths, not only a count of possible file changes.
It should also show the last saved review and last saved next step from the
project history ledgers, so a returning user can see what changed without first
opening raw saved history.
If no separate assumptions file exists but the intake has `non_claims`, the
first screen should show those as scope limits instead of saying assumptions are
not loaded. If `latest_eval_results.json`, `verified_axioms.json`, or
`workspace/derived_constraints.json` exists, the first screen should show the
axiom/constraint counts and each backing file.

Every visible check must carry one of:

- file path
- commands
- saved work status
- review file link
- explicit no-record warning

First viewport should behave like a project file.
Above the table, show one dominant next move with this grammar:

```text
status -> why it matters -> evidence -> next step -> review choices
```

Charts, counts, and stage rails are secondary unless they explain that next
move. A user should not have to interpret the system before knowing what to
inspect or do.

Web interface should route the first user through plain work steps:
choose a project, inspect the thesis, prepare evidence, decide whether it can run, review the
open issue, and save the project.
Detailed traces, saved history, warnings, and backing JSON belong behind those work
steps, one level down from the first scan.
Current-project home should render that path as a visible **Use this
project** rail: choose project, read thesis, check support, run locally, and
record the review trail. The all-project entry point should say that it browses
the inventory loaded from `projects/` and must not imply that all projects
open at once.
File recovery and evidence preparation are separate states. A recovered project
with indexed source files but no compiled evidence file, compile provenance,
or replay manifest should say `Prepare evidence`, list the missing files,
and show the history paths that will prove the repair. It should not call the
evidence usable just because source files are listed.
Run readiness should also show scoring-guide holds in plain language. If the
scoring guide lacks the current dimensions list, the workbench should show
`Fix scoring guide`, point to the scoring-guide file, and show the validation
command before any run action appears ready.
When the first blocker is an active evidence gap, the next action should open
the panel that can actually resolve it: fetch evidence or save a justification.
Do not route that blocker to a generic file-prep page if the gap controls live
with run results and evidence support.
The blocked-run preview should follow the same rule: name the in-app recovery
step first, include the workspace/subsection destination, and keep the backing
shell command as audit detail rather than the main instruction.
The selected evidence gap should render as a human-readable brief before the
write controls: target, severity, missing evidence, recovery path, public-fetch
availability, the question to answer, and why the gap matters. Raw schema fields
can remain available in Preview, but the default task panel should tell the user
which decision they are making.
Help belongs inside the project flow. The selected ZTARE project should
include a Help view with short question-and-answer cards for the project brief,
source files, scoring guides, evidence prep, evidence gaps, run readiness,
report readiness, and saved history.
Each card should name the backing repo doc or command, so help text stays a
translation of current documentation rather than a separate source of truth.
Help cards should also use the selected project's live state: project-brief
path, source/evidence state, scoring-guide file, active gap file, report readiness
state, run-readiness issue, first recovery command, or saved-history count. The user
should see what applies to this project before reading the general answer.
Opening project view should lead with the current thesis, the dominant
next step, and the few support states needed to choose that step. The full path
through project selection, file prep, readiness check, run, review, and save can stay
available behind a focused detail view.
The Evidence map should show thesis-support points as claim cards with the
source files that support each point. The user should be able to preview every
cited source from the card before opening raw compiled evidence.
Top-level navigation should have product lanes, not project internals:
ZTARE Projects and LeanMill. After a ZTARE project is selected, the project task
menu should expose Project, Thesis, Files, Run, Review, Report, Saved history,
and Settings. The project inventory lives under ZTARE Projects / Projects, not
inside the selected-project task list. Thesis is not a peer of Projects; it is
something the user inspects inside a selected project. Run is the user-facing
name for the plan/readiness/run-results area; avoid using `Checks` as a
top-level or primary task label.
Task changes should move between project work areas without immediately covering
the screen. Action buttons can open focused panels when the user chooses a
specific task. Each selected task should render its active work panel in the page
body, so the user can use Files, Run, Review, Report, and the full
project inventory as normal app pages.
Secondary pages should use a compact page header and let the selected work panel
be the main content, keeping the full project home off every task page.
Page headers should summarize the active task: Files headers show
project-brief, project-file, and evidence state; Run headers show run readiness;
Review headers show review/next-step state; and Report headers show
support/save state.

## Controller Interfaces

Workbench should consume existing CLI/read-model interfaces before adding new
backend abstractions:

| UI need | Existing interface |
|---|---|
| Create or refresh project charter | `ztare project charter scaffold --project <project> --mode <mode>` |
| Validate project brief | `ztare project intake validate --path <intake.json> --json` |
| Show what would change the thesis | `ztare project intake falsify --path <intake.json> ...` |
| Check project files | `ztare project source-check --project <project> --json` |
| Refresh file-check records | `ztare project source-index --project <project> --json` |
| Inspect evidence readiness | `ztare project evidence-replay --project <project> --json` |
| List active evidence gaps | `ztare project evidence-gap list --project <project> --json` |
| Justify an evidence gap | `ztare project evidence-gap justify --project <project> --source active ... --json` |
| Summarize the support audit | `ztare project claim-support --project <project> --json` (compatibility CLI) |
| Inspect the readiness command | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json` |
| Check readiness before model work | `ztare autoresearch run ... --preflight-only` |
| Start project run after readiness is accepted | `ztare autoresearch run ... --iters <n>` |
| Check report readiness | `ztare forensic-workbench report-action --project <project> --action check_readiness --renderer <renderer> --confirmed --json` |
| Apply a saved project-check review | `ztare forensic-workbench apply-review --project <project> --project-check <project_check_slug> --from <review.json>` |
| Refresh the local project data | `make forensic-workbench-data WORKBENCH_PROJECT=<project>` |
| Check the live project path | `make forensic-workbench-state WORKBENCH_PROJECT=<project>` |

The product coverage target is the normal project job, scoped short of the full
autoresearch command set. The Project Workbench should cover:

- choose or create a project
- add or edit the project charter: the human mandate for the question, thesis,
  scope limits, change test, and run boundary
- add or edit the project brief
- add, edit, type, preview, and check source files
- refresh saved file-index records
- prepare evidence, refresh saved file-index records, and check evidence connection
  and replay state
- list and justify active evidence gaps with a saved work
- inspect support-audit issues and report readiness reasons
- inspect the readiness command and project-run readiness
- inspect run readiness: whether the project may start the next loop,
  which prep blockers remain, which command clears the first blocker, and where
  model spend begins
- check readiness before model work
- start a project run only after an explicit confirmation
- inspect latest score, weakest point, evidence gaps, and run history
- record a review or next step against an issue
- save a project file with the same saved works and file-change boundary the user
  saw in the app

Advanced autoresearch commands stay outside the first product path unless their
results become ordinary project state: route decision recording, projection
exports, carrier-replay batches, hillclimb/consequence/rubric audits, dispatch
canaries, subscription outcomes, and parity reports. Those can remain command
details, suggested-fix panels, or later workbench lanes.

LeanMill belongs beside the ZTARE project path, not inside the project run area.
The first LeanMill Workbench lane can inspect curated formalizations,
saved targets, typed exits, public saved works, and the current proof-credit boundary.
It can also save a formalization target plus research notes into the curated
formalization tree with public saved history. Notes-to-autoformalize launch, ad hoc solve launch, and
proof-governance handoff stay disabled until the server can show target paths,
job ids, output paths, typed exits, and saved governance records before any
distributed job starts.

The CLI accepts `--project-check` as the preferred flag. `--item` and `--row`
remain accepted for old CLI commands and saved works. The UI should call this an
issue or selected issue. Payloads may still expose `project_check_label` and
`project_check_slug` for stable CLI/API compatibility.

UI must render these outputs as evidence-backed state. It must not infer a
ready state from prose or hide an unsafe launch behind a green label.
An incomplete intake disables launch and names the missing evidence.

## Boundaries

ZTARE owns the individual thesis/evidence workbench. It does not own the
organizational control plane.

In scope:

- local project browser
- thesis and intake inspector
- source/evidence readiness
- trace and run-readiness console
- readiness/run launch state
- run history and verdict/demotion view
- report/review-file state
- separate LeanMill proof-search section with target-and-notes drafting

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
saved work, leaving the gap explicit for the user to resolve.

The server owns a small storage boundary. Today that boundary is a file-backed
project store rooted in the repository: intake edits, source edits, saved
project files, settings, and saved works write to local paths and return those
paths to the UI. The UI should treat the server as the writer and should not
invent browser-only project state. Later storage can move behind the same
boundary, but v1 keeps the product local-first and inspectable.

## Project list model

The Project Workbench consumes explicit read models built from the repository.
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
-> server, built app, project-data file, project-index readiness, and active
   storage backend. v1 should report the file-backed local store.

GET /api/projects
-> project index from project-local briefs and public example briefs,
   with `ready_count`, `folder_count`, and `pending_folder_count` so the UI can
   distinguish openable projects from project folders that still need a project
   brief.
   `intake_ready_projects`/`projects` are the entries that can open immediately;
   `all_project_folders` is the rich inventory for every folder under
   `projects/`; `project_folders` is a compact compatibility list with the same
   project ordering and `openable` status.

GET /api/project-recovery-draft?project=<project>
-> read an existing project folder with no project brief and draft the
   `Connect project` form
   from local thesis, evidence, root, workspace, and raw files. This is
   read-only: it returns candidate bounded claim text, source files, evidence
   files, scope limits, and a read-only draft boundary. It also returns
   `add_intake_action` and `add_intake_write_boundary`, so the UI can show the
   rule, target path, history path, and no-change boundary for the explicit
   project-create/connect-project save action. The project-brief file is never
   written by loading the draft.

GET /api/workflow
-> six-step project steps plus server-owned summary and next-step fields, so the
   first screen can show the next local action without rebuilding priority only
   in the browser. Each step also carries the workbench destination and local
   action label the UI should open.

POST /api/project-create
-> create a local source project, project charter, and project brief, then return action results,
   created paths, saved-history paths, write boundary, refreshed project index, and first project data
   when available; partial source-initialization writes must be reported even if
   project-brief creation fails

GET /api/charter?project=<project>
-> read the project charter, return editable Markdown text, validation status,
   and the file-backed write boundary for saving it. The charter is the
   human-editable project mandate. It is not the structured project brief.

POST /api/charter
-> update `projects/<project>/project_charter.md`, append the charter saved-history
   record, and return refreshed charter/project state. The endpoint refuses
   empty text and no-op saves.

POST /api/source-import
-> write one new validated source file, refuse existing filenames, update
   source_type_map, append a source-import saved work, run source-check, and return
   refreshed state; the UI may stage the returned source path in the project
   brief draft, but the brief write still requires Save project brief. Optional
   `artifact_kind` and `created_by` metadata let Codex, Claude Code, notebook,
   search, proof, and report outputs land as project work without changing the
   evidence filter controlled by `source_type`.

GET /api/sources?project=<project>
-> list typed source files using the same source-check read model

GET /api/source-file?project=<project>&relative=<relative_raw_path>
-> read one bounded source file for editing, including source type,
   project-work kind, creator label, and body

POST /api/source-edit
-> update one existing source file only when body, source type, project-work
   kind, or creator label changed; update source_type_map, append a source-edit
   saved work, run source-check, and return refreshed state. Metadata-only
   edits are valid because they change how external notes, searches,
   computations, proof work, and report drafts appear in the research map.

GET /api/snapshot?project=<project>&rubric=<rubric>&intake=<intake>
-> fresh single-project workbench data bound to the selected intake

GET /api/health?project=<project>&rubric=<rubric>&intake=<intake>
-> run-health summary plus action guidance source warnings,
   guidance recommendations, report-hold rules, counts, and evidence links

GET /api/trace?project=<project>&rubric=<rubric>&intake=<intake>
-> run-plan summary: whether the selected project can continue, what local
   input blocks it, the next local command when one exists, readiness saved-history
   state, plan, graph summaries, and commands. The Run -> Ready to run
   screen should render the decision first: can this project run, what blocks
   it, and what should the user do next. Commands, structural checks,
   and graph summaries belong behind an advanced disclosure.

GET /api/research-map?project=<project>&rubric=<rubric>&intake=<intake>
-> project orientation map for GitHub/Obsidian and D4. It reads the current
   thesis, change test, ruled-out alternatives, raw-file project-work metadata,
   support points, compiled evidence contradictions, candidate claims, open
   unknowns, derived constraints, report limits, graph summaries, formal-work
   state, and saved history. The map should add interpretation: tensions,
   branches to test, and the next useful move. It should not repeat the
   dashboard.

POST /api/research-map
-> write only `projects/<project>/workspace/research_map.md`,
   `research_map.json`, and research-map saved history. It does not generate
   contradictions; those come from evidence preparation and workspace update,
   then survive source-type filtering into `compiled_evidence_packet.json`.

GET /api/settings
-> non-secret workbench defaults loaded from `.env`, plus provider-key
   present/missing flags with values hidden. Editable defaults include
   evidence model/search settings, run draft/review/stress-test models,
   timeout, retries, and fallback mode.

GET /api/capabilities
-> read the public capability map and audit summary. The response is read-only
   and project-independent. Help uses it to show what each project test reads,
   how it checks, what it produces, when not to trust it yet, the research
   lessons behind it, the ZTARE implication, source titles, a runnable command,
   and the proof a user can inspect. The payload keeps internal ids for
   provenance, but also returns readable research labels for the UI.

POST /api/settings
-> save allowlisted workbench defaults to `.env`; this never displays or
   rewrites provider-key values

The Settings page is the model and run-control page for the Project
Workbench. A project should not require source-code edits to change models. The
local server reads and writes only these non-secret `.env` keys:
Model fields should render as dropdowns from the runtime aliases in
[`docs/reference/model_aliases.md`](../reference/model_aliases.md); blank means
use the runtime default.

| Setting | What it controls |
|---|---|
| `ZTARE_WORKBENCH_MODEL` | Default model label passed as `MODEL` for evidence preparation and evidence fetch auto-compile. |
| `ZTARE_EVIDENCE_SEARCH_BACKEND` | Public evidence-search backend for fetch: `auto`, `openai`, or `anthropic`. |
| `ZTARE_WORKBENCH_REPORT_MODEL` | Optional report-synthesis model; blank means use the evidence model or synthesis runtime default. |
| `ZTARE_WORKBENCH_FETCH_SEVERITY` | Which evidence gaps the fetch action targets first: `degrading`, `enriching`, or `blocking`. |
| `ZTARE_WORKBENCH_MAX_FETCHES` | Maximum active evidence gaps fetched in one confirmed action. |
| `ZTARE_WORKBENCH_AUTO_COMPILE` | Whether a confirmed fetch also runs source check, workspace update, and evidence compile. |
| `ZTARE_WORKBENCH_RUN_MUTATOR_MODEL` | Draft model used to propose candidate project updates during a run. |
| `ZTARE_WORKBENCH_RUN_JUDGE_MODEL` | Review model used to score and critique candidate updates during a run. |
| `ZTARE_WORKBENCH_RUN_INVERTER_MODEL` | Optional stress-test model used to look for objections, missing evidence, and failure modes. |
| `ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT` | Per-call timeout for bounded project runs. |
| `ZTARE_WORKBENCH_AUTORESEARCH_LLM_RETRIES` | Retry count for bounded project runs. |
| `ZTARE_WORKBENCH_EVIDENCE_LLM_TIMEOUT` | Timeout for evidence workspace-update and evidence compile calls. |
| `ZTARE_WORKBENCH_EVIDENCE_LLM_RETRIES` | Retry count for evidence workspace-update and evidence compile calls. |
| `ZTARE_WORKBENCH_MODEL_FALLBACK` | `0` keeps calls on the configured family; `1` allows runtime fallback when supported. |

Provider keys such as `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`,
`GEMINI_API_KEY`, and `GOOGLE_API_KEY` are editable from Settings. The
Project Workbench should never display existing secret values. A blank key field
means leave that provider unchanged; a non-empty value writes or replaces that
key in `.env`.
If a model setting is blank, generic workbench commands should omit the model
argument and let the lower-level environment choose. The UI should not bake a
provider into project, evidence, or run actions.

POST /api/preflight
-> run the `ztare autoresearch run ... --preflight-only` check and
   return command, exit code, readiness saved-history state, and refreshed project data

POST /api/run
-> start the selected `ztare autoresearch run ... --iters <n>` command
   after readiness has been accepted, then return output tails, refreshed
   trace, run history, and project state. The React app must ask for a second
   in-app confirmation before it sends `confirmed: true`; opening the Run panel
   or clicking the first run button must not launch a model-backed run. The
   first click should request a no-write server preview and show the server's
   command plus files that may change. The workbench applies Settings
   page run defaults to the previewed command before confirmation: draft model,
   review model, optional stress-test model, `--llm-timeout-seconds`, `--llm-retries`,
   and `--allow-model-fallback` when enabled. The Start run panel and
   confirmation dialog must show the effective draft, review, optional
   stress-test models, timeout, retries, fallback mode, command, and write paths
   before the confirmed request can start.

POST /api/source-action
-> run one allowlisted source/evidence action (`source_check`, `source_index`,
   `evidence_prepare`, `evidence_bind`, or `evidence_replay`) and return command
   details, exit code, output tail, parsed data when available, refreshed
   project data, and a Project Workbench source-action saved work for
   write-producing actions.
   `evidence_prepare` is model-backed through the Settings page's configured
   evidence model, timeout, retries, and fallback mode. The first request must
   be a no-write preview and the React app must ask for confirmation before
   sending `confirmed: true`. Run-readiness and recovery commands and action-card
   commands must use the same Settings-normalized evidence-prepare command, so
   stale trace text cannot disagree with the action the user is about to run.

GET /api/evidence-gaps?project=<project>
-> active evidence gaps, backing gap file, and the current fetch command when
   missing sources still need recovery. Active gaps must match
   `ztare project evidence-gap list`, including hash-bound resolution saved works
   that make a prior gap inactive. The payload should include human-facing
   `status`, `gap_count`, `active_gap_count`, `active_gaps`, source path,
   fetch history paths, justification history paths, full possible write paths,
   and fetch command so the Evidence page and project actions do not disagree.
   The combined `Fetch or justify evidence gaps` action has two branches:
   confirmed fetch may write raw evidence, evidence text, compiled evidence,
   fetch manifest, and workbench fetch saved works; justification writes only
   the hash-bound evidence-gap resolution/action/brief saved works.

POST /api/evidence-fetch
-> no-write preview, then confirmed public evidence fetch using Settings page
   defaults for evidence model, search backend, severity, max fetches,
   auto-compile, and fallback mode. A confirmed run writes the upstream fetch
   manifest/raw evidence outputs plus a workbench evidence-fetch saved work.

POST /api/evidence-gap-justify
-> write a hash-bound evidence-gap resolution saved work through the existing CLI
   writer, then refresh active gaps and project data

GET /api/report-contract?project=<project>&renderer=<renderer>
-> read the current report readiness contract from local project files; return
   report status, support reasons, synthesis input binding, previewable backing
   files, command, and a no-write boundary
   Support issues should keep their machine-readable reason while also showing
   the actual risk, why it matters, what to check, and when the issue is done.

POST /api/report-contract
-> no-write preview, then confirmed run of
   `ztare forensic-workbench report-action --action check_readiness` to refresh
   the local report readiness contract and write a Workbench saved work. This
   action does not call a model, but it can write project files, so the React
   app must ask before sending `confirmed: true`.

A stale or unsupported report stays in needs-support state when the support
contract is missing, stale, or disconnected from the current project.

GET /api/file?path=<repo-relative-path>
-> read-only bounded text preview for a selected workbench-safe repo path;
   allowed roots are project files, docs, examples, public analytics, workbench
   outputs, rubrics, and selected root docs. Papers, absolute paths,
   parent-directory escapes, repo metadata, internal planning, and private
   research paths must be rejected before any file read. Response includes file
   kind, display kind, format, bytes, hash, line counts, truncation state, and
   previewable referenced repo paths.

GET /api/receipts?project=<project>
-> recent review, next-step, intake-edit, source-import, source-edit,
   source-action, evidence-gap, and project-file saved works from project files,
   plus `ztare-forensic-workbench-receipt-history-summary-v1` with four
   plain-language entries: latest review, latest next step, latest source or
   evidence change, and latest project file. The Saved history page should render
   that summary before the raw ledger entries.

GET /api/run-history?project=<project>
-> latest and recent run scores, weakest points, evidence gaps, synthesis
   patterns, and backing run-history paths

GET /api/evidence-support?project=<project>
-> support-audit status, weak/unsourced counts, source-context status, missing
   evidence-file errors, previewable source paths, and copyable support-audit command

GET /api/principles
-> short Workbench principle lines for the topbar, sourced from
   `docs/evidence_atlas/workbench_principles.json`; `surface=leanmill` keeps
   LeanMill-specific lines available without adding another panel.

GET /api/leanmill
-> LeanMill section state: curated formalization counts, saved-target counts,
   public history paths, target-save history paths, solver-lane
   guidance status, typed exits, and disabled proof-launch actions with the
   missing job/saved-history boundary named

POST /api/leanmill/target
-> preview or save a LeanMill target plus research notes under
   `ztare_proofs/leanmill-formalizations/blueprints/`, append a public
   target-save history record, and return the target path, history path,
   latest history path, hashes, and no-change status. `confirmed: false`
   must not write files.
   `POST /api/leanmill/blueprint` remains accepted for older clients, but new
   browser and CLI surfaces should describe this as a target-and-notes save.

POST /api/project-file
-> write the current project file into the project workspace, append a
   project-file saved work, and return the saved file path plus saved-history
   paths.
   New saved files use `ztare-forensic-workbench-project-file-v1`; new save
   saved works use `ztare-forensic-workbench-project-file-write-receipt-v1`.
   Older `case-file` schemas remain compatibility inputs.
   The response should also compare the new project-file hash with the previous
   saved file and report whether the handoff file content changed.

POST /api/review
-> append project-check saved work and refresh project data

POST /api/next-step
-> append project-check next-step saved work and refresh project data

POST /api/item-action
-> compatibility alias for old next-step clients and saved-history tooling

POST /api/row-action
-> compatibility alias for old next-step clients and saved-history tooling

POST /api/case-file
-> compatibility alias for old project-file clients and saved-history tooling

GET /api/claim-support?project=<project>
-> compatibility alias for old support-audit clients and saved-history tooling
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
and `row_slug` remain accepted for old clients and saved-history tooling. Saved review
and next-step files and stamped saved works should include product-facing
`project_check_label` and `project_check_slug`, plus `item_label` and
`item_slug` aliases, while keeping `row` and `row_slug` for CLI compatibility.
Snapshot responses and browser project files should expose `project_checks` and
`project_check_count`. `items`/`item_count` and `rows`/`row_count` remain
compatibility aliases. Saved history should expose `next_step` and
`project_check` path aliases for the saved next-step ledger, while keeping
`item_action` as the old path alias. Project files should expose `audit_commands`.
`command_queue` remains a compatibility alias for existing consumers.
Visible product copy should say check, review, and next step. Terms such as
`row_action`, `source_action`, and `action` belong in API, schema, commands, and
ledger compatibility fields, staying out of the first-path labels. Checklist details and
inspector summaries should normalize those legacy terms before display.

`ztare forensic-workbench project-state --project <project> --json` should print
the same live project-state object used by `/api/workflow`. Its top-level `ok`
must follow the project-object contract, not merely the fact that JSON was
rendered. The payload should expose compact `failed_checks` and
`first_failed_check` fields, so CLI, UI, and saved project files can name the
first route or state problem in plain language. `--strict` exits non-zero when
that shared project object is incoherent.

If the server is absent at startup, the app may fall back to the last generated
offline project data. Once the server is detected, project-specific data or
review-refresh failure must stay visible to the user, with any stale offline
data held back until the user acts on the failure.

That is deliberate. Browser-side filesystem discovery would hide which project
state was inspected and which command produced it. For this reason, the project browser should
keep using generated or API-served read models built from `projects/*`
and example project briefs. It should show the selected project directory, project brief,
report contract, live readiness console, latest saved review, latest saved next step,
latest project-file write, a left-rail all-project inventory, and a project
switchboard that also shows project folders with no workbench project brief. Every
folder under `projects/` should stay searchable and available. Project-brief-ready,
human-named, and file-backed projects should sort first so the first scan is
usable without hiding historical folders. Connected projects should be keyed by
project plus project brief with brief mode, source-ref coverage, report-contract
presence, recent history paths, and any per-project brief load error before
the user switches projects. It should use
the same new-project form to connect an existing folder only when that
folder has no project brief yet, with write paths previewed before the server
writes.
Pending project tiles should show the same decision rule, first write target,
history path, and no-change boundary as ordinary project actions, so recovery
does not feel like a separate hidden workflow.
Folders under `projects/` should be marked by the server with project status,
project-brief readiness, source-folder state, and history paths. Ready is one
status a project folder may carry; every folder under `projects/` is a project.
`/api/projects` and `/api/status`
should expose `project_inventory_scope: all_projects_directory`,
`inventory_root: projects/`, and `inventory_includes_all_project_folders: true`
so the browser can prove it is not showing only intake-ready projects.
Left rail is navigation, not a project browser. It should expose only the
product lane and the current task menu. Project counts, folder recovery, search,
and current-project status belong in the main page, where labels and counts
have enough room to be readable. Full project view
should keep every project searchable and available while sorting intake-ready,
human-named, and file-backed projects before generated folders.
Current-project home should make the same inventory reachable with a
plain-language Browse all projects action and show the live folder count from
the server.
Break the layout into two top-level lanes. Keep the left rail to product lanes
and the selected project's focused actions:
ZTARE Projects / Project library, Current project, Connect project, Settings;
current project / Overview, Project brief, Files, Run, Review, Report, Saved
history; LeanMill / Start, Draft target, Proof files, History. LeanMill work
items come from saved targets, formalization files, outcome files, and LeanMill
analytics state, not from the ordinary project-library list.
Clicking a project task should open that task's first useful panel, not only
change a highlighted label.
When the left rail collapses on smaller screens, the same submenu should appear
as a compact in-page menu.
First screen should answer what project is open, what thesis is under
review, what evidence is attached, what the latest run says, what needs
support, and what the next step is. It should present a compact project-facts
strip, a Next steps queue ordered from the live project state, and compact
project-area navigation for the common moves: open a project, inspect the
thesis, prepare evidence, decide whether it can run, review, and save. Primary action
should come from project state (unresolved file or support issues first, then
the readiness check or project run, then the next useful inspect/save task), not
from whichever check is currently selected.
Project-area navigation should stay subordinate to that queue. It exists so a
first user can open focused detail views without having to interpret the whole system
model before acting.
The current-project home should also expose four plain job cards: open or
recover a project, prepare evidence, do the next allowed step, and save what changed.
Those cards should route to the same project-state-backed destinations as the
deeper menus.
Dense tables, editors, traces, saved history, report details, and selected check
inspection should open as focused detail views so they do not crowd the first viewport.
Next action queue should still give a direct path to the current report
issue or selected project step, so a reviewer can move without interpreting the
whole project model first.
The thesis should also be visible on the first screen with ruled-out
alternatives and change-test status, plus direct actions to inspect or edit the
intake. A first user should know what project they are reviewing before opening a
detail view.
After a server-backed write, the first screen should show the latest write kind,
target, and refresh status before the user opens saved-history details.
The detailed saved-history panel should use the same concrete write-target wording as
the action and next-step cards. Evidence fetches, evidence-gap justifications,
and report readiness refreshes should be labeled by user action rather than raw
schema or route names.
The first-screen next-action card should also show its target path, saved-history
path, latest saved work, and no-change boundary when the live workflow provides
them, so the user can decide whether to continue before opening another panel.
Project inspector views belong under focused review screens, so the user
can inspect evidence and decide an action without scrolling through every
edit/report tool. Each relevant project area should also show thesis status,
source/evidence readiness, recent saved history, run history/verdict state,
and report state.
Report-readiness panel should show whether the compiled evidence file is
present, how many evidence issues or source gaps remain, which local sources were
verified, and the exact commands that rebuild the audit.
When report readiness is blocked, the panel should make the next action explicit:
save any allowed report action as a next step, copy the note, preview the
backing file, or rerun the support check after inputs change.
Source/evidence readiness panel should show file-index status, evidence
connection status, replay status, source/evidence files, and the commands
that rebuild those checks.
Add file should let the user stage the new file path into source or evidence
files without writing the project brief until Save project brief records the
edit saved work.
Add file should also ask what kind of work the file is: project note, agent
session notes, source summary, computation output, script/code, report draft,
proof note, search summary, or raw evidence. This is separate from whether the
file is evidence.
Source-file editor should show pending body/type changes and refuse no-op
saves, so source-edit saved works correspond to actual file or metadata changes.
Project switches, full refreshes, project-brief reloads, and opening a source
from disk should use an in-app confirmation dialog before replacing pending
project-brief or source-file edits.
First viewport should also show an unsaved-edits strip when a local project
charter, project brief, source, or source-import draft is dirty. That strip should link directly to the
related editor so the user can save or clear the draft before changing projects.
Project charter editor should preview the charter file plus saved-history paths
before Save charter is enabled.
Project brief editor should preview the project-brief file plus edit
ledger/latest history paths before Save project brief is enabled.
Report panel should show the support reasons, synthesis input-binding
status, contract file path, exact support command, and the allowed next report
actions from the support contract. The first screen should not merely say the
report is blocked; it should tell the user which report readiness action is safe
to take next.
Manual-commands panel should collect selected check, trace, report, health, and
next-step commands into one list for inspection and copy. The browser must not run
arbitrary shell commands. App buttons call fixed workbench-server endpoints for
the supported actions: project creation, intake edits, add source/edit source,
source readiness review, evidence connection/replay, readiness check, review/next-step saved works, and
project-file saves.

Index must include both first-run demos:

- `demo_claims`, backed by the public ready demo intake
- `ops_root_cause_diagnosis_demo`, backed by its project-local intake

If a project has no materialized report-readiness context, the project still opens.
Report readiness should show `report_support_unavailable` and keep
the rest of the workbench working. A missing report is a reviewable state that
keeps the project visible.

Writes should stay explicit. Live mode calls the workbench server to persist
review or next-step file under the project workspace folder before writing the
saved work. Offline snapshot mode may save a review or next-step file for a CLI handoff.
Either way, the visible trail is file, saved-history ledger,
saved history, latest saved work, and refreshed project data.
Any panel that can write project files should show a visible write boundary
before the action buttons: what the server-backed button writes, and which
download/copy/preview actions stay browser-only. Creation, add source,
source edit, readiness check, fixed source/evidence action, evidence-gap
justification, review, next-step, and project-file panels should also preview
the exact or server-patterned payload, metadata, history, and latest saved work
paths that can change before the write runs. The readiness check writes its launch-check
saved work to the project telemetry ledger at
`projects/<project>/workspace/iteration_telemetry.jsonl`.
Each write boundary should also carry the active storage contract. In v1 that
means the local file-backed project store; future storage can move behind the
same server contract without changing browser write semantics.
`/api/status` should advertise the same behavior contract the UI uses: every
primary action has `writes_project_files`, `browser_writes`,
`requires_confirmation`, `behavior`, and `write_path_templates` fields. The
status payload also exposes `action_summary` plus the lower-level
`write_contract` counts: `action_count`, `write_action_count`,
`write_without_confirmation_count`, `confirmation_required_count`, and
`read_only_action_count`. The current Project Workbench action set includes
project actions plus the LeanMill target-and-notes action: 12 write files or saved works
immediately, 5 ask first, and 9 are read-only.
`write_action_count` includes the ask-first action. UI should display the
clearer split from `file_change_summary`, while `action_summary` remains as a
compatibility field: `12 write / 5 ask first / 9 read-only`.
Readiness-check and project-run panels should not describe writes only as a path
count. They should show the first write target, history path, latest saved work
when present, and no-change boundary before the user clicks. Project-run panel
is stricter: it requests a no-write `/api/run` preview, shows the
server-provided command and files that may change, then opens a
confirmation dialog before the server may receive `confirmed: true`.
Run history should read the local run files and the project telemetry ledger in
both full and fast modes. If scored runs exist, the project home should show the
latest score and run count first. If no scored run exists but a readiness-check
saved work exists in `projects/<project>/workspace/iteration_telemetry.jsonl`, the
home state should say that readiness was accepted and show the telemetry file as
the backing saved work.
Run history should also carry compact compression-progress advice when the run
emits BIC, MDL, proof-length, or comparable lower-is-better complexity values.
The UI should explain whether the latest loop made the explanation simpler to
defend, whether it should narrow or pivot, and whether that advice agrees with
the recorded run controller.
Project-file panel should preview the exact project file before save/download/copy, so
the user can inspect the bundle without creating a browser download or server
write. Saved bundle should include `live_context.project_file_write_plan`
with the same project-file paths, no-hidden-browser-write boundary, and
preview/download/copy actions shown before Save. Before hashing and writing,
the server should stamp `live_context.project_state` plus a compact
`live_context.workflow` from the current project state, plus
`live_context.project_object_contract`. The contract says whether project,
intake, thesis support, recent changes, next action, destination, report readiness repair action,
evidence repair action, workflow-step write boundaries, project-action write boundaries, and save paths
agree across `/api/workflow`, `ztare forensic-workbench project-state`, and the
saved project file. The UI can then show Project object: coherent / needs
review without making the user inspect raw JSON. The contract should also carry
a compact `failed_checks` list with `id`, `label`, and `detail`, so a broken
route or stale project-state field appears as a human-readable repair target.
Before saving, the project-file panel should also show an Included now checklist:
open issues, source files, project steps, report readiness, saved history, run
history, run-learned axioms/constraints, and the support audit. Each item should
be clearly marked present in the bundle or missing/unavailable.
After saving, the response should be understandable without opening JSON: saved
path, history path, stamped project-state schema, next action, issue
count, recent saved-history count, project-action count, and the files that changed.
The saved project file should also carry a top-level `project_summary` with the
thesis, change test, next action, source/evidence/run-readiness/run/report readiness
states, action count, saved-history count, proof paths, and project-object state. This
gives the file a readable first page before the deeper `live_context`
details. A saved project file should carry `project_object_ok`,
`project_object_failed_count`, and `project_object_failed_checks` in that
summary, and the file viewer should show the coherent/needs-review state in both
Read and Structure modes.
That summary should also include `project_to_thesis_audit`: the reader-facing
check for thesis, source/evidence state, file warnings, run state, report
readiness, next action, repair actions, write boundaries, latest change, files,
and recovery path when present. The saved-file viewer should render this as a
short Project path section with counts and failed checks, not only as
raw JSON.
It should also name the latest saved review and latest saved next
step when those saved works exist, so the handoff file says what decision was
recorded without forcing the reader into the saved-history ledger first.
It should also carry a compact recent-changes section: latest history path,
latest review, latest next step, latest source/evidence change, and latest
project-file save. This lets a reader recover what changed without scanning
multiple saved-history ledgers.
The summary should preserve `open_project_repair_count`,
`open_project_inspect_count`, and `open_advisory_count`, and its `proof_paths`
should include source-warning backing ledgers as well as saved works and
report/evidence files. A saved project file must not erase the evidence trail
just because an action is only guidance.
The Project file panel should preview those proof paths before save, so the
reader can inspect the backing files without first writing the handoff file.
Project-action cards should also show the path that will prove or explain the
next move: a report readiness file, evidence-bind saved work, source-action saved work,
review ledger, or next-step ledger, depending on the action.
When an action can write files or saved works, the card should show the first
concrete write target and a compact count for additional paths. It should not
hide write scope behind a generic path count.
Each project action should also carry a short `rule` field: why this action is
allowed now, what state blocks stronger claims, or why the card is inspect-only.
The UI should render that rule before history paths and commands, so a user
does not have to infer the decision logic from raw paths.
Project-state actions are returned as a full list. The UI may show a short
default slice for readability, but the user must be able to expand the list
without losing any action. `live_context.project_state.action_summary` reports
`total_count`, `project_repair_count`, `project_inspect_count`,
`advisory_count`, `area_counts`, and `action_type_counts` so the project can
distinguish file-changing repairs, read-only inspections, and suggestions.
Source-warning guidance should say it is not a project blocker and should
carry backing ledger/source paths in `evidence_refs`, not `receipt_paths` or
write targets. The UI labels those paths as `Backing evidence`;
project-written saved works remain `Saved work path`, and ordinary source/report
files remain `Backing file`.
Preview should use product names: `project_check_count`, `action_details`,
`evidence_support`, and `evidence_support_file_path`. Compatibility aliases may
remain in the saved JSON for old scripts. A first user should be able to read the
project file without decoding legacy schema aliases.
After project creation, readiness check, live review, saved next step, intake-edit,
add-source/edit-source, source/evidence write, or project-file save, the app
should show the saved-history schema, target, project context, changed fields or
change summary, history path, latest path, source path, and hash before the user
has to inspect the full history. History, latest saved work, and saved-file paths
should be previewable when they point to repository files. Source/evidence write saved works
should stamp the produced output file hash when the underlying command exposes
one. Affected live panels should
refresh together: trace, report contract, health, support audit, saved
history, intake editor, project index, and source list when sources changed.
If the intake editor has unsaved local edits, the refresh should preserve the
draft and report the skipped intake refresh, leaving those edits intact.
UI should name the panels that refreshed and separately name any panel whose
refresh failed, so a saved work is never mistaken for a fully refreshed project.
Opening a different project, refreshing the current project, or falling back to
offline project data should clear prior run/write activity from the screen. A
new-project write is the exception: after the reset into the new project, the created
paths and saved write record should remain visible so the user can verify what just
changed.
When an issue is selected, the review strip should also show the latest saved
review and next-step state for that same issue from the saved history, so a
reviewer does not overwrite or duplicate a review blindly.
Review and next-step save panels should show the selected issue before
the write action: status, evidence-link count, first evidence path, and latest
review state. A reviewer should know exactly what they are saving against before
the server writes a saved work.

File inspection is read-only. The browser may request one repository-relative
path from the workbench server and display a bounded text preview. It must not crawl
the filesystem, infer hidden project state, or turn a preview into a write.
The file view should be grouped by the user's job before it shows individual
files: understand the thesis, inspect source material, check evidence and gaps,
review runs, inspect report readiness, inspect saved works, or review assumptions.
The compact preview is for scanning. The focused viewer is for reading, with
separate Read, Structure, and Raw modes so Markdown, JSON, JSON lines, CSV, and
plain text can expose their useful structure without crowding the project home.
The viewer should be opened from thesis, evidence, source, run, report, warning,
suggested-next-move, and history paths wherever those paths appear. Use the mode
that fits the file: Read for prose and short summaries, Structure for
project files, source-warning files, suggested-next-move files, saved works,
evidence manifests, run output, and nested JSON, and Raw when the user needs the
exact text. Large or referenced files should stay in the viewer rather than
being expanded inline on the main page.

Project-file creation should also be explicit. A browser-generated project file may package
the current project data, project directory/project-brief/saved-history context, project-check evidence
links, project-path next-step context, live trace/report/health context,
workbench status/action summary/write contract/file-preview boundary, latest
readiness-check result, project-file inventory, latest add-source/edit-source saved works
and hashes, action guidance recommendations, command-preview list, latest
visible write record, latest write-refresh result, pending project-brief draft edits,
and recent history paths for download or copy, but it must not write project
files or imply that a project needing support has been reviewed.
When a selected project is project-brief-scoped, UI panels and saved project
files should display `Project key` and `Project brief` as separate facts. The
combined project-plus-brief key is not the brief path. Labeling it that way
makes the project model hard to inspect.
New project-file fields should use product names such as `display_label`,
`project_check_label`, `project_check_count`, `project_checks`,
`latest_project_check`, `readiness_checks`, `graph_summaries`,
`preflight_receipt`, `evidence_support`, and `evidence_support_file_path`.
The `preflight_receipt` field name is a compatibility name; visible UI should
say readiness check.
Older schema names may remain as compatibility aliases while old saved works and
scripts still consume them. The browser preview should hide or rename those
aliases when a product-named field is available.

Suggested fixes and next steps are guidance in the Project Workbench. They may
tell the reviewer that a project has run-health attention, provider-runtime
risk, stale source-warning inputs, or action guidance warnings. A reviewer may stage one of those
warnings as a next move on the affected issue. Saving that note uses the
same explicit next-step history path as any manual next-step note. A warning
does not make release claims stronger and does not become hidden control
authority. Suggested-fixes view should show provenance: recommendation
source path, generated-at time, and source-warning backing file when present.

## Acceptance tests

Any Project Workbench release candidate must pass these checks:

1. A user can open `demo_claims` or `ops_root_cause_diagnosis_demo`.
2. A project brief with missing inputs disables launch and names what is missing.
3. A ready project brief can run the readiness check and show a visible saved work.
4. Source-ready, evidence-ready, and loop-ready are visually distinct.
5. Generated material and judgment/demotion material are visually distinct.
6. A stale or unsupported report remains in needs-support state when the support
   contract says it is not ready.
7. Every visible check has provenance or an explicit no-file/saved-history warning.
8. A saved review can be applied through the CLI, and the refreshed project data
   shows the latest saved review.
9. A saved project file carries the same read/write/ask-first action split and
   no-hidden-browser-write boundary that the UI showed before save.
10. The offline snapshot and `workbench_snapshot.json` use product-facing
    display labels for the first path: thesis, source files, evidence
    files, run readiness, report readiness, latest review, and latest next step.
11. Project-brief-scoped panels and saved project-file context display
    `Project key` separately from the project-brief path.
12. The current-project home shows the five-step work rail and a Browse all
    projects action backed by the live `projects/` inventory count.
13. Review and next-step save panels show selected-project-check context before
    saving. Project-file panel shows the Included now checklist before saving.
14. Project state and saved project files show run-learned axioms/constraints
    with counts and backing files when prior iterations produced them.
15. The Start run path proves the two-step boundary: readiness can be checked and
    inspected without model spend; a bounded run first returns a no-write
    preview showing effective model settings and output paths; only a confirmed
    request can start the model-backed run.
16. Workbench navigation is deep-linkable by workspace and section, and browser
    Back/Forward restores the visible task. The clean first-start route supports
    `day0=1`, and `start=files` opens the project-create upload path rather
    than dropping the user into an undirected form.
17. LeanMill appears as its own top-level Workbench lane with formalizations,
    target-and-notes drafting, saved history, typed exits, and disabled
    proof-launch actions. It is not a dense subsection of a ZTARE project run
    area.
18. `/api/workflow`, `ztare forensic-workbench project-state`, and saved project
    files carry a `ztare-project-object-contract-v1` audit showing whether the
    live project object is coherent, plus a compact first failed check when it
    is not.
19. Supervisor, multi-role, multi-user, hosted, billing, and background-agent
   controls are absent.

The Project Workbench can grow incrementally. It may not be opaque.
