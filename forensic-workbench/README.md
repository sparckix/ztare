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
make forensic-workbench-api
npm --prefix forensic-workbench run dev
```

Vite proxies `/api/projects`, `/api/snapshot`, `/api/health`, `/api/review`,
and `/api/row-action` to the local API. The browser still does not scan
`projects/` directly. It asks the local API for a project index and a fresh
snapshot for the selected project, using the intake and rubric discovered by
the index. The app shows the backing project directory, intake, report contract,
latest review receipt, and latest saved row action before the main case file.
When the local API is running, the Apply button writes the same review receipt
that the CLI writes, then refreshes the same selected project/intake snapshot.
The Save action button writes a row-action receipt through the same explicit
API/ledger path. The Refresh button reloads the current case from local project
files. If the API is not running at startup, the app falls back to
`public/workbench_snapshot.json`; if a live project refresh fails after the API
is detected, the app keeps the current case and shows the error instead of
swapping in stale static data.

Live mode also fetches `/api/health` for the selected project. That endpoint
summarizes kernel-health attention components and action-intelligence source
health issues so the workbench can show advisory blockers without promoting
them into control authority.

That keeps every visible state tied to a file, command, receipt, or warning.
The project index includes project-local intakes and public example intakes, so
the first two cases are `demo_claims` and `ops_root_cause_diagnosis_demo`. If a
case has no report-support context yet, it still opens with a blocked
`report_support_unavailable` export row.

Run locally:

```bash
npm --prefix forensic-workbench run dev
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
- first-screen stage rail for sources, evidence, run readiness, and export state
- first-five-minute path: open the case, inspect the claim, check evidence,
  run preflight, resolve the blocker, and apply the review
- first-screen bounded claim, export decision, non-claim count, and next falsifier
- status metrics for run readiness, export state, evidence rows, and attention rows
- blocker panel showing the current blocking row, blocker reasons, and a direct
  review action
- health and actions panel showing live kernel-health status,
  action-intelligence source-health warnings, and copyable next commands
- current-action rail with the next command or provenance target
- artifact coverage strip showing rows with artifacts, commands, receipts, and
  review files
- latest-review receipt row that reads the CLI-applied receipt when present and
  otherwise shows an explicit no-receipt state
- review queue strip showing selected row, decision, evidence count, and receipt readiness
- review workspace for marking a row reviewed, deferred, or blocking export
- saved-action workspace for writing the next row action to a project ledger
- review note field plus downloadable/copyable
  `ztare-forensic-workbench-review-v1` review file
- review JSON preview before download or CLI handoff
- searchable audit table plus inspector panel for row-level evidence

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

This prototype is intentionally separate from Orbit. Orbit is the organizational
overlay; this app is the individual claim-review workbench.
