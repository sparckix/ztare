# ZTARE Forensic Workbench Prototype

React/Vite local webserver prototype for the forensic-workbench lane.

The app reads `public/workbench_snapshot.json`, which is generated from the
existing project intake, autoresearch trace, and report-support contract:

```bash
make forensic-workbench-data
```

Choose a different static case by materializing a new snapshot:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=<project>
```

## Data model

The React app can run in two local modes.

Static mode renders one generated project snapshot:

1. choose a project slug;
2. run `make forensic-workbench-data WORKBENCH_PROJECT=<project>`;
3. render `forensic-workbench/public/workbench_snapshot.json`;
4. apply saved review files through the CLI;
5. refresh the snapshot.

Live mode uses a thin local API around the same snapshot builder and review
receipt writer:

```bash
make forensic-workbench-live
```

Vite proxies `/api/projects`, `/api/snapshot`, `/api/health`, `/api/intake`,
`/api/trace`, `/api/project-create`, `/api/source-import`, `/api/preflight`,
`/api/sources`, `/api/source-file`, `/api/source-edit`, `/api/source-action`, `/api/run-history`,
`/api/receipts`, `/api/file`, `/api/review`, and `/api/row-action` to the local API. The browser
still does not scan `projects/`
directly. It asks the local API for a project index and a fresh snapshot for the
selected project, using the intake and rubric discovered by the index. The app
shows the backing project directory, intake, report contract, latest review
receipt, latest saved row action, recent receipt history, and the live
autoresearch trace before the main case file. The intake editor reads and writes
the selected project intake
through `/api/intake`; source and evidence refs are resolved against the intake
directory and repo root, then shown as present, missing, external, or unsafe.
The project picker uses the same lightweight intake read to show ref counts
before a case opens. Project-local intakes are editable; public example intakes
are readable but not writable from the browser. The editor shows pending
changed fields before saving and refuses no-op writes, so an intake-edit receipt
means the file actually changed.
The New case panel calls `/api/project-create`, which runs the fixed
`ztare project source-init` and `ztare project intake create` path for a new
project slug, then reloads the project through the same live snapshot flow.
The source-import panel calls `/api/source-import`, writes one `.md` or `.txt`
file under the selected project's `raw/` directory, updates
`raw/source_type_map.json`, appends a source-import receipt, and runs the
offline source check.
The raw-source panel calls `/api/sources` to load the typed source list,
`/api/source-file` to open one existing source, and `/api/source-edit` to write
the edited source body/type back to disk. A source edit updates
`raw/source_type_map.json`, appends a source-edit receipt, reruns source-check,
and refreshes the case.
The inspector can preview a selected intake ref or row file/source/evidence/review
path through `/api/file`, which is read-only, repository-contained, and capped
to a bounded text preview. When the local API is running, the Apply button
writes the same review receipt that the CLI writes, then refreshes the same
selected project/intake snapshot. The Save action button writes a row-action
receipt through the same explicit API/ledger path. Intake edits write an
intake-edit receipt under the project workspace. The receipt-history panel reads
the review, row-action, and intake-edit ledgers through `/api/receipts`, returns
`ztare-forensic-workbench-receipt-history-v1`, then lets the user preview the
backing ledger file. The Refresh button reloads the current case from local
project files. If the API is not running at startup, the app falls back to
`public/workbench_snapshot.json`; if a live project refresh fails after the API
is detected, the app keeps the current case and shows the error instead of
swapping in stale static data.

Live mode also fetches `/api/trace`, `/api/report-contract`, and `/api/health`
for the selected project, fetches `/api/run-history` for verdict/run evidence,
and can call `/api/preflight` for an explicit preflight-only launch check.
The trace endpoint returns `ztare-forensic-workbench-trace-v1`: carrier chain,
kernel-entry state, plan steps, loop admission, graph summaries,
source/evidence statuses, and copyable next commands from
`ztare autoresearch trace`. The report endpoint returns
`ztare-forensic-workbench-report-contract-v1`: report/export status, blocker
reasons, synthesis input-binding state, the backing contract path, and the
copyable `make synth-contract` command. The health endpoint returns kernel-health attention
components, action-intelligence source-health issues, and source-health file
paths. The workbench shows these as read-only rows with copyable commands and
previewable source files, so advisory blockers are inspectable without becoming
hidden browser writes.
The preflight endpoint returns `ztare-forensic-workbench-preflight-v1`: the
exact `ztare autoresearch run ... --preflight-only` command, exit code,
acceptance flag, loop-admission trace, output tail, and refreshed snapshot when
available. It is not a general shell runner and it does not start a model run.
The project-create endpoint returns `ztare-forensic-workbench-project-create-v1`:
source-init result, intake-create result, refreshed project index, and the first
snapshot when available.
The source-import endpoint returns `ztare-forensic-workbench-source-import-v1`:
written source path, source type, source-import receipt path, source-check
result, and refreshed snapshot/trace when available.
The source-list endpoint returns `ztare-forensic-workbench-source-list-v1`.
The source-file endpoint returns `ztare-forensic-workbench-source-file-v1`.
The source-edit endpoint returns `ztare-forensic-workbench-source-edit-v1`:
edited source path, relative raw path, source type, source-edit receipt path,
source-check result, and refreshed snapshot/trace when available.
The source-action endpoint returns `ztare-forensic-workbench-source-action-v1`
for three fixed actions: `source_check`, `source_index`, and
`evidence_replay`. The source-index action uses
`ztare project source-index --index-only --json`, so the browser can refresh
source metadata without hiding a model-backed extraction step.
The run-history endpoint returns `ztare-forensic-workbench-run-history-v1`:
recent run scores, latest and champion verdict summaries, evidence gaps,
synthesis patterns, and backing file paths.

That keeps every visible state tied to a file, command, receipt, or warning.
The case-packet export is client-side and explicit: clicking Download packet
creates `ztare-forensic-workbench-case-packet-v1` JSON from the current
snapshot, recent receipt history, live trace/report/health context, the latest
preflight result, latest source/evidence action result, run-history context, the
latest source import, latest source edit, command queue, and the latest visible write receipt. It
does not write project files or claim that an unreviewed case is complete.
The project index includes project-local intakes and public example intakes, so
the first two cases are `demo_claims` and `ops_root_cause_diagnosis_demo`. If a
case has no report-support context yet, it still opens with a blocked
`report_support_unavailable` export row.

Run the live local workbench:

```bash
make forensic-workbench-live
```

Run the API and React dev server separately when debugging:

```bash
make forensic-workbench-api
make forensic-workbench-dev
```

Build:

```bash
npm --prefix forensic-workbench run build
```

The interface is organized as a local claim-review surface:

- sidebar navigation over intake, evidence, run, export, and health surfaces
- case-file first viewport with one dominant next move: status, why it matters,
  evidence, primary action, and review choices
- case docket summarizing export decision, evidence path, and review handoff
- project file strip showing the selected project directory, intake, report
  contract, latest review receipt path, and latest saved row action path
- intake editor showing bounded claim, non-claims, source refs, evidence refs,
  ref status, pending changed fields, and intake-edit receipt writes
- project picker showing intake ref counts and read-only vs editable intake mode
- source/evidence readiness panel showing source index, evidence binding, output
  binding, replay state, backing files, and copyable commands
- raw-source panel for loading an existing source, editing its text/type, saving
  the file through the API, and recording a source-edit receipt
- first-screen stage rail for sources, evidence, run readiness, and export state
- first-five-minute path: open the case, inspect the claim, check evidence,
  run preflight, resolve the blocker, and apply the review
- first-screen bounded claim, export decision, non-claim count, and next falsifier
- status metrics for run readiness, export state, evidence rows, and attention rows
- blocker panel showing the current blocking row, blocker reasons, and a direct
  review action
- health and actions panel showing live kernel-health rows,
  action-intelligence source-health rows, source files, and copyable next
  commands
- autoresearch trace console showing carrier chain, kernel-entry status, plan
  steps, graph carriers, source/evidence paths, and next commands
- preflight action panel that runs only the local preflight command and shows
  exit status, loop-admission receipt count, and bounded output
- run-history panel showing latest score, weakest point, evidence gaps, recent
  runs, synthesis patterns, and previewable backing files
- report/export contract panel showing blocker reasons, synthesis input-binding
  state, contract file path, and the exact support command
- current-action rail with the next command or provenance target
- command cockpit collecting the selected-row, trace, report, health, and row
  commands into one queue; only the dedicated preflight panel can ask the local
  API to run a bounded preflight-only check
- artifact coverage strip showing rows with artifacts, commands, receipts, and
  review files
- receipt history panel showing recent review, row-action, intake-edit, source-import, and source-edit
  ledger rows with previewable backing ledger paths
- case-packet export for downloading or copying the current case, rows,
  evidence refs, live context, preflight result, run history, command queue,
  and recent receipt paths
- latest-review receipt row that reads the CLI-applied receipt when present and
  otherwise shows an explicit no-receipt state
- review queue strip showing selected row, decision, evidence count, and receipt readiness
- review workspace for marking a row reviewed, deferred, or blocking export
- saved-action workspace for writing the next row action to a project ledger
- last-write receipt panel showing the stamped review/action/intake-edit receipt, ledger
  path, latest path, source path, hash, and preview/copy controls
- review note field plus downloadable/copyable
  `ztare-forensic-workbench-review-v1` review file
- review JSON preview before download or CLI handoff
- searchable audit table plus inspector panel for row-level evidence
- read-only file preview for selected intake refs and evidence paths when the
  local API is running

The current prototype is file-backed. Static mode downloads an inspectable
review file and makes the CLI handoff explicit:

```bash
ztare forensic-workbench apply-review --project <project> --row <row> --from <project>_<row>_review.json
```

That command appends a receipt under the project workspace. Row actions use the
same pattern:

```bash
ztare forensic-workbench save-action --project <project> --row <row> --from <project>_<row>_action.json
```

Live mode calls the local API to append the same receipts and refresh the case.
In both modes, the receipt ledgers are the inspectable edit path.

After applying a review, refresh the snapshot:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=<project>
```

The refreshed app should show the latest-review receipt row. If no receipt has
been applied, it should say so explicitly rather than pretending the row is
reviewed.

The refreshed app should also show the latest-row-action row. If no action has
been saved, it should say so explicitly rather than implying a next step exists.
After a live review, row-action, or intake-edit write, the app should show the
stamped receipt paths and hash immediately.

This prototype is intentionally separate from Orbit. Orbit is the organizational
overlay; this app is the individual claim-review workbench.
