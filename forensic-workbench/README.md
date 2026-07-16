# ZTARE Project Workbench

Local React/Vite workbench for reviewing and editing repo-backed ZTARE
projects. Open a project, inspect its thesis, check the files behind
it, run local checks, save review/next-step history, and save an inspectable
project file.

The implementation still uses `forensic-workbench` in package names, CLI commands,
and legacy schemas. Treat that as compatibility naming. The product is Project
Workbench.

## Start It

### Requirements

Choose one supported path:

- **Container:** Docker Engine or Docker Desktop with Compose and Buildx. No host Python or Node runtime is
  needed after the image is built.
- **Source:** the repository Python environment from the root quickstart plus Node 20+ and npm. The launcher
  installs the locked frontend dependencies with `npm ci` on first use.

The service is a trusted-local-user tool. It has filesystem-backed write actions but no accounts, sessions,
or tenant authorization. Keep it on loopback; use an SSH tunnel for a remote machine.

Run the live workbench:

```bash
make forensic-workbench-live
```

The launcher starts the local API at `http://127.0.0.1:8765` and the Vite app at
`http://127.0.0.1:5174`, and installs the app's locked web dependencies on the first
run. It assumes the repository's Python environment is already installed. If the API is already
running, the launcher reuses it. If the Vite port is already taken, it exits
instead of silently moving the app.

For separate debugging:

```bash
make forensic-workbench-api
make forensic-workbench-dev
```

This app declares its own dependencies (`react`, `react-dom`, `vite`). The live
launcher installs them automatically; to install them by hand (e.g. in CI):

```bash
make forensic-workbench-install
```

To build the React app and serve it from the API server:

```bash
make forensic-workbench-build
make forensic-workbench-api
```

Then open `http://127.0.0.1:8765/`.

Before a shared demo or release, run the release boundary smoke:

```bash
make forensic-workbench-release-check
```

It builds the app, starts an isolated public-scope server, verifies that the tracked public-project
manifest is the entire visible inventory, refuses an unlisted project read/file preview/write, checks the
local-only browser origin, and confirms the built frontend is served from the API's one-port origin.

Build the same one-port artifact an adopter will run:

```bash
make forensic-workbench-docker-build
```

`docker buildx version` is an intentional preflight: Buildx honors
`deploy/Dockerfile.workbench.dockerignore`, which prevents private projects, research trees, solver corpora,
and local artifacts from entering the release build context. Start the image with
`make forensic-workbench-docker` and open `http://127.0.0.1:8765`.

See the [Workbench release guide](../docs/guides/workbench-release.md) for visibility modes, remote access,
the clean release procedure, expected results, and known deployment limits.

Offline snapshot mode is for audit or review without live edits:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=<project>
```

That materializes `forensic-workbench/public/workbench_snapshot.json`; the app
can render it without live edits. The generated snapshot uses the same public
labels as the live app: thesis, ruled-out alternatives, source files,
evidence files, run readiness, report support, latest review, and latest next step.

## What You Can Do

The first path is:

1. Open a project from `projects/`.
2. Read the thesis, ruled-out alternatives, and what would change it.
3. Check source and evidence files.
4. Check run readiness before heavier work, with the history path visible first.
5. Review the report/support issue or save a next step.
6. Save the project file with saved history and backing paths.

The project home's **Do next** card shows the current next action plus the
target path, history path, latest saved work, and no-change boundary when those are
available from the live workflow.

The current-project home makes that path explicit in the **Use this project**
rail: choose project, read thesis, check support, run locally, and save the
review trail. The next project step is shown before the workflow guide; the guide
stays available behind **Show workflow guide** so the first scan stays focused.
**Browse N folders** opens the searchable inventory loaded from `projects/`;
it does not try to open every project at once.
Any source, evidence, thesis, report, saved work, or project file preview opens in
a focused file viewer with path, type, format, size, line counts, role-specific
reading guidance, quick-read cards for common structures, referenced repo paths,
copy-text, and copy-path controls. Referenced repo paths inside the viewer can
be opened directly, so saved history can lead to the files it changed and an
evidence file can lead back to cited project files.
The current-project home also shows a compact **Project files** inventory:
project brief, thesis, raw sources, evidence, active gaps, run outputs, report support,
saved history, and run-learned backing files. The inventory is grouped by the work a
user is doing: understand the question, inspect source material, check evidence
and gaps, review runs and lessons, inspect report support, inspect saved history, or
review assumptions. Open the small grouped list first; expand only when you need
the full file set.
Inline previews remain available where they help a small recovery card.

The main areas are:

- **Projects:** open any folder under `projects/`, or connect an older folder
  by saving the missing project brief. When a folder has files but no brief, the
  Connect project flow drafts from existing thesis/source/evidence files, shows
  the files it found, keeps draft notes concise, and previews the exact brief
  and history paths before saving.
- **Thesis:** inspect the thesis, assumptions, caveats, charter, and research map. The
  evidence map shows support points with the cited source files for each point.
  Run-learned axioms and constraints show their backing files when prior runs
  produced them.
- **Evidence:** edit the project brief, add project files, edit existing files,
  and prepare the evidence summary.
- **Pressure-test the thesis:** inspect readiness, check readiness, start a confirmed project run,
  and review scores/warnings. Active evidence gaps open here too, because this
  is where the user can fetch evidence or save a hash-bound justification. The
  selected gap is shown as a brief: what is missing, why it matters, whether
  public fetch is available, the question to answer, and the file or evidence
  state it will update.
  If a run is blocked, the run preview names the in-app recovery step first and
  can open the recovery panel instead of leaving the user with only a copied
  shell command. Readiness-check and confirmed-run panels show what files can change
  before the action runs.
- **Open points:** record review status, save next steps, and inspect saved history.
  The saved-history view also leads with a "worth another pass?" read — whether
  the program is still compressing its explanation or into diminishing returns
  (advisory, computed from run history, not the judge score).
- **Verdict:** check report readiness and save the project file, see the
  trust verdict and where to verify, and export the verified research graph to an
  Obsidian vault (one linked note per claim, evidence, and falsifier, with the
  weak spots marked) to write an article from.
  Report readiness gives a direct next-action block: save any allowed report
  action as the next step, preview the backing file, copy the note, or rerun the
  local readiness check.

The app discovers project folders through the local server. The project index
reports total, intake-ready, file-backed, and background/generated counts, with
intake-ready projects sorted first and generated/background folders hidden until
you ask to show them.
In that payload, `intake_ready_projects` and the older `projects` field are the
entries that can open immediately. `all_project_folders` is the rich browser
inventory for every folder under `projects/`; the older `project_folders` field
is a compact compatibility list with the same projects and `openable` status.

## Scenario and Plugin Surfaces

The sidebar is a stable JTBD map. Scenarios compose rubric, run, evidence,
renderer, solver, recheck, gate, deliverable, and optional panel capabilities;
they do not add navigation items.

The Plugins screen creates or edits scenario/rubric data and reloads Python
capability plugins. Frontend panels are authored modules under
`src/scenario-panels/` and are discovered during the Vite build. A scenario
selects one with `workbench_panels: [results:<panel-id>]`. The panel author owns
the UI and any bounded API route it needs. Use the shared `ModalPortal` and
`useModalBehavior` helpers for dialogs rather than rendering a fixed overlay
inside a host panel.

Scenario selection is stored in the `scenario` URL parameter, so Pressure-test links
survive refresh and browser Back/Forward navigation.

## Live Data

The browser does not scan the repository directly. It asks the local API for
bounded read models:

- `/api/status` for server, app, and project-index readiness.
- `/api/capabilities` for the project checks and research lessons.
- `/api/projects` for the full project folder inventory.
- `/api/snapshot` for the selected project data.
- `/api/workflow` for the six-step project steps, summary counts, UI
  destinations, and the server-chosen next step.
- `/api/intake`, `/api/sources`, and `/api/source-file` for editable project
  files.
- `/api/trace`, `/api/run-history`, `/api/report-contract`, `/api/health`, and
  `/api/evidence-support` for run, score, report, guidance, and support-audit
  state.
- `/api/receipts` and `/api/file` for saved history and bounded file preview.

`/api/file` previews only workbench-safe repo paths: project files, docs,
examples, public analytics, workbench outputs, rubrics, and selected root
docs. It returns file kind, format, hash, line counts, and safe referenced repo
paths with the bounded text preview. It rejects papers, absolute paths,
parent-directory escapes, repo metadata, internal planning, and private research
paths before reading a file.

The UI shows human labels first. Raw schema names, route names, and legacy keys
are compatibility details, not the primary product language.

## Writes

Every server-backed write returns a write boundary. The UI shows the files that
may change before the write and the files that changed after it.

Write endpoints:

- `/api/project-create` creates the project folder, source folders, source
  metadata, and project-brief path, or adds the missing brief to an existing
  project folder.
- `/api/intake` edits the selected project-brief JSON.
- `/api/source-import` adds one new `.md` or `.txt` source under `raw/`.
- `/api/source-edit` edits one existing source file or source type.
- `/api/source-action` runs one allowlisted file or evidence check.
- `/api/preflight` runs the local readiness check. The route name is kept for
  CLI/API compatibility.
- `/api/run` first returns a no-write preview; only a confirmed request starts
  the selected project run.
- `/api/review` saves review status for a selected issue.
- `/api/next-step` saves the next step for a selected issue.
- `/api/project-file` writes the current project file plus saved-history paths.

Browser-only actions remain browser-only: preview, download, copy. Failed writes
return an explicit no-write boundary with `browser_writes=false` and no changed
project paths.

The live status contract groups actions into three buckets: read-only, writes
files or saved history now, and asks before writing. `/api/status` exposes the
product-facing `file_change_summary`, keeps `action_summary` for compatibility,
and includes the per-action `behavior` contract so the UI can show the plain
split without guessing from route names or booleans. The payload reports the
current counts; documentation does not pin them because plugin and workflow
capabilities can change the action set. `browser_writes=false` across the set.

Review and next-step save panels show the selected issue before saving:
status, evidence-link count, first evidence path, and latest review state. That
keeps the save action tied to the project file the user is inspecting.

## Project Files

Saving a project file writes an inspectable JSON bundle under the selected
project workspace. New saved files use
`ztare-forensic-workbench-project-file-v1`; the saved-history compatibility
schema is `ztare-forensic-workbench-project-file-write-receipt-v1`. It includes:

- current project data and project context;
- project steps and next-step destination, trace, report, health, support audit,
  and run-history context;
- workbench status, action summary, write contract, file-preview boundary, and
  project inventory counts from the local server;
- `project_file_write_plan`, which records the project-file paths, no-hidden-
  browser-write boundary, and preview/download/copy actions shown before save;
- file inventory and latest file checks;
- recent review, next-step, project-brief, file, and project-file saved history;
- `project_key` and `intake` as separate facts in live context and recent
  saved history, while keeping older compatibility fields for existing scripts;
- server-stamped `live_context.project_state` and a compact
  `live_context.workflow`, so the saved file matches `/api/workflow` and
  `ztare forensic-workbench project-state` even if the browser had stale state;
- product-named support-audit paths such as `evidence_support_file_path`;
- local step plans and paths needed to audit the visible state;
- unsaved project-brief/file edits when a draft exists.

Before saving, the Project file panel shows what is included now: open issues,
source files, project steps, report support, saved history, run history, and support
audit. The preview uses product names such as action details, open issues,
support audit, and previewable proof paths even when the saved JSON keeps older
compatibility aliases.
Save stays disabled until enough live context is loaded; preview, download, and
copy remain browser-only. After Save, the panel shows the saved path, history
path, stamped project state, next action, issue count, recent saved-history count,
and project-action count.

The saved project file does not say the project is finished. It records what
the workbench currently knows, what still needs support, and which files back
that state.

## Command Compatibility

Live mode writes through the API. Offline snapshot mode can still hand off
review files to the CLI:

```bash
ztare forensic-workbench apply-review --project <project> --intake <intake> --project-check <project_check> --from <project>_<intake>_<project_check>_review.json
```

Saved next steps use the same shape:

```bash
ztare forensic-workbench save-next-step --project <project> --intake <intake> --project-check <project_check> --from <project>_<intake>_<project_check>_action.json
```

Review and next-step files carry `project_check_label` and
`project_check_slug` for the product UI, plus `item_*` and `row_*` fields
for existing scripts.

`--intake` is optional for old files, but safer for selected live projects
because it rejects mismatched payloads. `--item`, `--row`, and `save-action`
remain accepted for older scripts.

After a CLI write, refresh offline project data:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=<project>
```

## Compatibility

These names are still present for old saved history and clients:

- package and directory name: `forensic-workbench`;
- older `case-file` saved project schemas and saved-history schemas;
- legacy fields such as `rows`, `row_count`, `row_slug`, and `case_key`;
- legacy routes `/api/case-file`, `/api/item-action`, and `/api/row-action`.
- legacy route `/api/claim-support`.

New UI copy and new API callers should use project-first language:

- selected issue;
- project file;
- review status;
- report support;
- source and support-audit state.
- `project_key` for selected-project identity when a specific intake is loaded.
