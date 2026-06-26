# ZTARE Project Workbench

Local React/Vite workbench for reviewing and editing repo-backed ZTARE
projects. It is the D4 product surface: open a project, inspect its working
diagnosis, check the files behind it, run local checks, record review/next-step
receipts, and save an inspectable project file.

The implementation still uses `forensic-workbench` in package names, CLI commands,
and legacy schemas. Treat that as compatibility naming. The product is Project
Workbench.

## Start It

Run the live workbench:

```bash
make forensic-workbench-live
```

The launcher starts the local API at `http://127.0.0.1:8765` and the Vite app at
`http://127.0.0.1:5174`. If the API is already running, the launcher reuses it.
If the Vite port is already taken, it exits instead of silently moving the app.

For separate debugging:

```bash
make forensic-workbench-api
make forensic-workbench-dev
```

To build the React app and serve it from the API server:

```bash
make forensic-workbench-build
make forensic-workbench-api
```

Then open `http://127.0.0.1:8765/`.

Offline snapshot mode is for audit or review without live edits:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=<project>
```

That materializes `forensic-workbench/public/workbench_snapshot.json`; the app
can render it without live edits. The generated snapshot uses the same public
labels as the live app: working diagnosis, ruled-out alternatives, source files,
evidence files, run check, report support, latest review, and latest next step.

## What You Can Do

The first path is:

1. Open a project from `projects/`.
2. Read the working diagnosis, ruled-out alternatives, and what would change it.
3. Check source and evidence files.
4. Run preflight before heavier work.
5. Review the report/support issue or save a next step.
6. Save the project file with receipts and backing paths.

The current-project home makes that path explicit in the **Use this project**
rail: choose project, read thesis, check support, run locally, and save the
review trail. The next project step is shown before the workflow guide; the guide
stays available behind **Show workflow guide** so the first scan stays focused.
**Browse N folders** opens the searchable inventory loaded from `projects/`;
it does not try to open every project at once.

The main areas are:

- **Projects:** open any folder under `projects/`, or add the missing intake for
  a historical project folder.
- **Thesis:** inspect the diagnosis, assumptions, caveats, and project checks.
- **Evidence:** edit the intake, add source files, edit existing sources, and
  run file checks.
- **Runs:** inspect the run plan, run preflight, start a confirmed project run,
  and review scores/warnings.
- **Review:** record review status, save next steps, and inspect receipts.
- **Report:** inspect report support and save the project file.

The app discovers project folders through the local server. The project index
reports total, intake-ready, file-backed, and background/generated counts, with
intake-ready projects sorted first and generated/background folders hidden until
you ask to show them.
In that payload, `intake_ready_projects` and the older `projects` field are the
entries that can open immediately. `all_project_folders` is the rich browser
inventory for every folder under `projects/`; the older `project_folders` field
is a compact compatibility list with the same projects and `openable` status.

## Live Data

The browser does not scan the repository directly. It asks the local API for
bounded read models:

- `/api/status` for server, app, and project-index readiness.
- `/api/projects` for the full project folder inventory.
- `/api/snapshot` for the selected project data.
- `/api/workflow` for the six-step project steps, summary counts, UI
  destinations, and the server-chosen next step.
- `/api/intake`, `/api/sources`, and `/api/source-file` for editable project
  files.
- `/api/trace`, `/api/run-history`, `/api/report-contract`, `/api/health`, and
  `/api/evidence-support` for run, score, report, advisory, and support-audit
  state.
- `/api/receipts` and `/api/file` for receipt history and bounded file preview.

`/api/file` previews only workbench-safe repo surfaces: project files, docs,
examples, public analytics, workbench artifacts, rubrics, and selected root
docs. It rejects papers, absolute paths, parent-directory escapes, repo
metadata, internal planning, and private research paths before reading a file.

The UI shows human labels first. Raw schema names, route names, and legacy keys
are compatibility details, not the primary product language.

## Writes

Every server-backed write returns a write boundary. The UI shows the files that
may change before the write and the files that changed after it.

Write endpoints:

- `/api/project-create` creates the project folder, source folders, source
  metadata, and intake path, or adds the missing intake to an existing project
  folder.
- `/api/intake` edits the selected intake.
- `/api/source-import` adds one new `.md` or `.txt` source under `raw/`.
- `/api/source-edit` edits one existing source file or source type.
- `/api/source-action` runs one allowlisted source/evidence action.
- `/api/preflight` runs the local preflight-only check.
- `/api/run` first returns a no-write preview; only a confirmed request starts
  the selected project run.
- `/api/review` saves review status for a project check.
- `/api/next-step` saves the next step for a project check.
- `/api/project-file` writes the current project file plus receipt paths.

Browser-only actions remain browser-only: preview, download, copy. Failed writes
return an explicit no-write boundary with `browser_writes=false` and no changed
project paths.

The live status contract groups actions into three buckets: read-only, writes
files or receipts now, and asks before writing. `/api/status` exposes the
product-facing `file_change_summary`, keeps `action_summary` for compatibility,
and includes the per-action `behavior` contract so the UI can show the plain
split without guessing from route names or booleans. The current split is 6
read-only actions, 10 direct file/receipt writes, and 1 ask-first run action;
`browser_writes=false` across the set.

Review and next-step save panels show the selected project check before saving:
status, evidence-link count, first evidence path, and latest review state. That
keeps the save action tied to the project file the user is inspecting.

## Project Files

Saving a project file writes an inspectable JSON bundle under the selected
project workspace. It includes:

- current project data and project context;
- project steps and next-step destination, trace, report, health, support audit,
  and run-history context;
- workbench status, action summary, write contract, file-preview boundary, and
  project inventory counts from the local server;
- `project_file_write_plan`, which records the project-file paths, no-hidden-
  browser-write boundary, and preview/download/copy actions shown before save;
- source-file inventory and latest source actions;
- recent review, next-step, intake, source, and project-file receipts;
- `project_key` and `intake` as separate facts in live context and recent
  receipts, while keeping older compatibility fields for existing scripts;
- product-named support-audit paths such as `evidence_support_file_path`;
- command details and paths needed to audit the visible state;
- unsaved intake/source edits when a draft exists.

Before saving, the Project file panel shows what is included now: project checks,
source files, project steps, report support, receipts, run history, and support
audit. The preview uses product names such as action details, project checks,
and support audit even when the saved JSON keeps older compatibility aliases.
Save stays disabled until enough live context is loaded; preview, download, and
copy remain browser-only.

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
`project_check_slug` for the product surface, plus `item_*` and `row_*` fields
for existing scripts.

`--intake` is optional for old files, but safer for selected live projects
because it rejects mismatched payloads. `--item`, `--row`, and `save-action`
remain accepted for older scripts.

After a CLI write, refresh offline project data:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=<project>
```

## Compatibility

These names are still present for existing receipts and clients:

- package and directory name: `forensic-workbench`;
- schemas such as `ztare-forensic-workbench-*-v1`;
- legacy fields such as `rows`, `row_count`, `row_slug`, and `case_key`;
- legacy routes `/api/case-file`, `/api/item-action`, and `/api/row-action`.
- legacy route `/api/claim-support`.

New UI copy and new API callers should use project-first language:

- project check;
- project file;
- review status;
- report support;
- source and support-audit state.
- `project_key` for selected-project identity when a specific intake is loaded.
