import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const h = React.createElement;

const FILTERS = [
  { id: "all", label: "All rows" },
  { id: "attention", label: "Needs review" },
  { id: "ready", label: "Ready" },
  { id: "neutral", label: "Recorded" }
];

const NAV_SECTIONS = [
  { label: "Intake", row: 0, tone: "intake" },
  { label: "Evidence", row: 3, tone: "evidence" },
  { label: "Run", row: 5, tone: "run" },
  { label: "Export", row: 10, tone: "report" },
  { label: "Health", row: 9, tone: "health" }
];

const REVIEW_ACTIONS = [
  { id: "reviewed", label: "Mark reviewed" },
  { id: "deferred", label: "Defer" },
  { id: "blocked", label: "Block export" }
];

const ROW_ACTIONS = [
  { id: "next_step", label: "Next step" },
  { id: "needs_source", label: "Needs source" },
  { id: "ready_to_run", label: "Ready to run" },
  { id: "export_blocker", label: "Export blocker" }
];

const ROW_ACTION_LABELS = Object.fromEntries(ROW_ACTIONS.map((action) => [action.id, action.label]));

const STAGES = [
  { id: "sources", label: "Sources", rowLabel: "Source readiness" },
  { id: "evidence", label: "Evidence", rowLabel: "Evidence readiness" },
  { id: "run", label: "Run", rowLabel: "Run readiness" },
  { id: "export", label: "Export", rowLabel: "Report/export" }
];

const DISPLAY_OVERRIDES = {
  valid_packet: "valid intake",
  ready_for_in_loop_candidate: "ready for run",
  ready_for_evidence_prepare: "ready for evidence prep",
  report_blockers_present: "report blockers present",
  report_support_unavailable: "report support unavailable",
  synthesis_input_binding_unbound: "input binding unbound",
  runtime_risks_present: "runtime risks present",
  loop_admission: "loop admission",
  "loop admission preflight path": "preflight receipt path",
  public_example_intake: "example intake",
  project_local_intake: "project intake",
  unknown_intake_source: "intake source unknown"
};

function kindLabel(kind) {
  if (kind === "attention") return "Needs review";
  if (kind === "ready") return "Ready";
  return "Recorded";
}

function displayText(value) {
  const raw = String(value || "none");
  return DISPLAY_OVERRIDES[raw] || raw.replace(/_/g, " ");
}

function evidenceItems(row) {
  const seen = new Set();
  const add = (items, label, value, type) => {
    if (!value) return;
    const key = `${type}:${value}`;
    if (seen.has(key)) return;
    seen.add(key);
    items.push({ label, value, type });
  };
  const items = [];
  add(items, "File", row.file, "file");
  add(items, "Source", row.source, "source");
  add(items, "Evidence", row.evidence, "evidence");
  add(items, "Command", row.command, "command");
  add(items, "Receipt", row.receipt, "receipt");
  add(items, "Review artifact", row.review_artifact, "review");
  add(items, "Warning", row.warning, "warning");
  return items;
}

function copyText(value) {
  if (!navigator.clipboard) return;
  navigator.clipboard.writeText(value).catch(() => {});
}

function downloadText(filename, value) {
  const blob = new Blob([value], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function rowSlug(label) {
  return String(label || "row").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "row";
}

function snapshotJsonHref(snapshot, liveMode) {
  if (liveMode && snapshot && snapshot.project) {
    const params = new URLSearchParams({ project: snapshot.project });
    if (snapshot.rubric) params.set("rubric", snapshot.rubric);
    if (snapshot.intake) params.set("intake", snapshot.intake);
    return `/api/snapshot?${params.toString()}`;
  }
  return "/workbench_snapshot.json";
}

function endpointUrl(path, params) {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

function activeBlocker(rows) {
  return rows.find((row) => row.kind === "attention") || rows.find((row) => row.status === "blocked") || null;
}

function rowHasArtifact(row) {
  return evidenceItems(row).length > 0 || Boolean(row.provenance);
}

function coverageSummary(rows) {
  const total = rows.length || 0;
  const rowsWithArtifacts = rows.filter(rowHasArtifact).length;
  const commandRows = rows.filter((row) => row.command).length;
  const receiptRows = rows.filter((row) => row.receipt).length;
  const reviewRows = rows.filter((row) => row.review_artifact).length;
  return { total, rowsWithArtifacts, commandRows, receiptRows, reviewRows };
}

function buildReviewFile(snapshot, row, reviewState) {
  if (!row) return "";
  const payload = {
    schema: "ztare-forensic-workbench-review-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    row: row.label,
    row_status: displayText(row.status),
    decision: reviewState.decision || "unreviewed",
    note: reviewState.note || "",
    evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
  };
  return JSON.stringify(payload, null, 2);
}

function buildRowActionFile(snapshot, row, actionState) {
  if (!row) return "";
  const payload = {
    schema: "ztare-forensic-workbench-row-action-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    row: row.label,
    row_status: displayText(row.status),
    action: actionState.action || "next_step",
    note: actionState.note || "",
    evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
  };
  return JSON.stringify(payload, null, 2);
}

function firstPreviewableEvidence(row) {
  return evidenceItems(row || {}).find(canPreviewEvidence) || null;
}

function firstEvidenceText(row) {
  const item = firstPreviewableEvidence(row) || evidenceItems(row || {})[0];
  return item ? `${item.label}: ${item.value}` : "No evidence file recorded.";
}

function rowActionSuggestion(snapshot, row) {
  if (!row) {
    return {
      action: "next_step",
      title: "Select a row",
      note: "Select a row before saving an action.",
      evidence: "No row selected.",
      command: ""
    };
  }

  const rowName = row.label;
  const status = displayText(row.status);
  const evidence = firstEvidenceText(row);
  const command = row.command || "";
  const warning = row.warning ? ` Warning: ${row.warning}.` : "";
  const reportBlocked = row.label === "Report/export" && snapshot.report_status === "blocked";
  const missingish = /missing|unknown|unavailable|unbound|not discovered|no_action|no_review/i.test(
    `${row.status} ${row.detail} ${row.warning}`
  );

  if (reportBlocked || row.status === "blocked" || row.kind === "attention") {
    return {
      action: "export_blocker",
      title: "Resolve before export",
      note: `Hold export on ${rowName}. Inspect ${evidence}.${warning}${command ? ` Re-run or inspect: ${command}` : ""}`.trim(),
      evidence,
      command
    };
  }

  if (missingish) {
    return {
      action: "needs_source",
      title: "Fill the missing input",
      note: `Update ${rowName} before relying on this case. Inspect ${evidence}.${warning}`.trim(),
      evidence,
      command
    };
  }

  if (row.label === "Run readiness" || row.label === "Preflight" || /ready|available/.test(row.status)) {
    return {
      action: command ? "ready_to_run" : "next_step",
      title: command ? "Run the surfaced command" : "Keep this row as evidence",
      note: command
        ? `Run the surfaced command for ${rowName}: ${command}`
        : `${rowName} is ${status}. Keep ${evidence} attached to the case.`,
      evidence,
      command
    };
  }

  return {
    action: "next_step",
    title: "Record the next move",
    note: `${rowName} is ${status}. Inspect ${evidence} and decide the next project action.`,
    evidence,
    command
  };
}

function parseReviewFile(value) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function linesFromText(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function canPreviewEvidence(item) {
  return ["file", "source", "evidence", "review"].includes(item.type);
}

function Metric({ label, value, tone }) {
  return h(
    "div",
    { className: `metric ${tone || "neutral"}` },
    h("span", null, label),
    h("strong", null, displayText(value))
  );
}

function ProjectIdentity({ snapshot }) {
  const sourceLabel = snapshot.served_from === "local_api" ? "live local API" : snapshot.snapshot_scope || "single project read model";
  return h(
    "div",
    { className: "project-identity", "aria-label": "Project identity" },
    h("span", null, h("em", null, "Project"), h("strong", null, snapshot.project)),
    h("span", null, h("em", null, "Rubric"), h("strong", null, snapshot.rubric)),
    h("span", null, h("em", null, "Intake"), h("strong", null, displayText(snapshot.intake_source || "unknown_intake_source"))),
    h("span", null, h("em", null, "Snapshot"), h("strong", null, displayText(sourceLabel)))
  );
}

function projectOptionLabel(project) {
  const parts = [project.project];
  if (project.intake_source) parts.push(displayText(project.intake_source));
  const refSummary = project.intake_ref_summary || {};
  if (refSummary.total) parts.push(`refs ${refSummary.present || 0}/${refSummary.total}`);
  return parts.join(" / ");
}

function projectLoadParams(entryOrSnapshot) {
  if (!entryOrSnapshot) return {};
  return {
    project: entryOrSnapshot.project,
    rubric: entryOrSnapshot.rubric || entryOrSnapshot.project,
    intake: entryOrSnapshot.intake || ""
  };
}

function ProjectContextPanel({ projectEntry, snapshot }) {
  const intake = (projectEntry && projectEntry.intake) || snapshot.intake || "";
  const projectDir = (projectEntry && projectEntry.project_dir) || snapshot.project_source || "";
  const reportContract = (projectEntry && projectEntry.report_contract) || "";
  const latestReview = (projectEntry && projectEntry.latest_review) || snapshot.latest_review_artifact || "";
  const latestAction = (projectEntry && projectEntry.latest_row_action) || snapshot.latest_row_action_artifact || "";
  const latestIntakeEdit = snapshot.latest_intake_edit_artifact || "";
  const refSummary = (projectEntry && projectEntry.intake_ref_summary) || {};
  const intakeMode = projectEntry && projectEntry.intake_editable === false ? "read-only" : "editable";
  return h(
    "section",
    { className: "project-context-panel", "aria-label": "Project files" },
    h("div", null, h("span", null, "Project files"), h("strong", null, projectDir || "not discovered")),
    h("div", null, h("span", null, "Intake"), h("code", null, intake || "not discovered")),
    h("div", null, h("span", null, "Intake refs"), h("strong", null, refSummary.total ? `${refSummary.present || 0}/${refSummary.total} present` : "not counted")),
    h("div", null, h("span", null, "Edit mode"), h("strong", null, intakeMode)),
    h("div", null, h("span", null, "Report contract"), h("code", null, reportContract || "not generated")),
    h("div", null, h("span", null, "Latest review"), h("code", null, latestReview || "none")),
    h("div", null, h("span", null, "Latest action"), h("code", null, latestAction || "none")),
    h("div", null, h("span", null, "Latest intake edit"), h("code", null, latestIntakeEdit || "none"))
  );
}

function intakeDraftFromPayload(payload) {
  const fields = (payload && payload.editable_fields) || {};
  const draft = {
    path: (payload && payload.path) || "",
    bounded_claim: fields.bounded_claim || "",
    next_falsifier: fields.next_falsifier || "",
    notes: fields.notes || "",
    non_claims_text: (fields.non_claims || []).join("\n"),
    source_refs_text: (fields.source_refs || []).join("\n"),
    evidence_refs_text: (fields.evidence_refs || []).join("\n"),
    editable: payload ? payload.editable !== false : true,
    reference_status: (payload && payload.reference_status) || null
  };
  return { ...draft, original: { ...draft } };
}

function intakeDraftFields(draft) {
  if (!draft) return {};
  return {
    bounded_claim: draft.bounded_claim || "",
    next_falsifier: draft.next_falsifier || "",
    notes: draft.notes || "",
    non_claims_text: draft.non_claims_text || "",
    source_refs_text: draft.source_refs_text || "",
    evidence_refs_text: draft.evidence_refs_text || ""
  };
}

function intakeChangedFields(draft) {
  if (!draft || !draft.original) return [];
  const current = intakeDraftFields(draft);
  const original = intakeDraftFields(draft.original);
  return Object.keys(current).filter((key) => current[key] !== original[key]);
}

function displayFieldName(value) {
  return String(value || "").replace(/_text$/, "").replace(/_/g, " ");
}

function IntakeRefStatus({ draft, liveMode, onPreview }) {
  const status = (draft && draft.reference_status) || {};
  const summary = status.summary || {};
  const groups = [
    { key: "source_refs", label: "Source refs", rows: status.source_refs || [], type: "source" },
    { key: "evidence_refs", label: "Evidence refs", rows: status.evidence_refs || [], type: "evidence" }
  ];

  return h(
    "section",
    { className: "intake-ref-status", "aria-label": "Intake reference status" },
    h(
      "div",
      { className: "intake-ref-summary" },
      h("span", null, "Refs"),
      h("strong", null, `${summary.present || 0}/${summary.total || 0} present`),
      h("small", null, `${summary.external || 0} external / ${summary.missing || 0} missing / ${summary.unsafe || 0} unsafe`)
    ),
    groups.map((group) =>
      h(
        "div",
        { className: "intake-ref-group", key: group.key },
        h("span", null, group.label),
        group.rows.length
          ? group.rows.map((row) =>
              h(
                "div",
                { className: `intake-ref-row ${row.status}`, key: `${group.key}:${row.index}:${row.ref}` },
                h("code", null, row.ref),
                h("strong", null, displayText(row.status)),
                row.previewable
                  ? h(
                      "button",
                      {
                        className: "copy-button",
                        type: "button",
                        disabled: !liveMode,
                        onClick: () => onPreview && onPreview({ type: group.type, value: row.preview_path }),
                        title: liveMode ? "Preview this repository file" : "Start the local API to preview files"
                      },
                      "Preview"
                    )
                  : h(
                      "button",
                      {
                        className: "copy-button",
                        type: "button",
                        onClick: () => copyText(row.ref),
                        title: "Copy reference"
                      },
                      "Copy"
                    )
              )
            )
          : h("p", null, "No refs recorded.")
      )
    )
  );
}

function IntakeEditor({ draft, setDraft, liveMode, message, onSave, onReload, onPreviewRef }) {
  const update = (key) => (event) => {
    setDraft({ ...(draft || {}), [key]: event.target.value });
  };
  const disabled = !liveMode || !draft || draft.editable === false;
  const changedFields = intakeChangedFields(draft);
  const canSave = !disabled && changedFields.length > 0;
  const saveTitle = draft && draft.editable === false ? "Project-local intakes only" : disabled ? "Load a live intake first" : "Write intake edit receipt";
  return h(
    "section",
    { className: "intake-editor", "aria-label": "Project intake editor" },
    h(
      "div",
      { className: "intake-editor-head" },
      h("span", { className: "eyebrow" }, "Project intake"),
      h("h2", null, "Edit intake state"),
      h("p", null, message || (liveMode ? "Live edits write to the project intake and create an intake-edit receipt." : "Start the local API to edit the project intake."))
    ),
    h(
      "div",
      { className: "intake-editor-grid" },
      h(
        "label",
        null,
        h("span", null, "Bounded claim"),
        h("textarea", {
          value: (draft && draft.bounded_claim) || "",
          onChange: update("bounded_claim"),
          disabled,
          "aria-label": "Bounded claim"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Next falsifier"),
        h("textarea", {
          value: (draft && draft.next_falsifier) || "",
          onChange: update("next_falsifier"),
          disabled,
          "aria-label": "Next falsifier"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Notes"),
        h("textarea", {
          value: (draft && draft.notes) || "",
          onChange: update("notes"),
          disabled,
          "aria-label": "Notes"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Non-claims"),
        h("textarea", {
          value: (draft && draft.non_claims_text) || "",
          onChange: update("non_claims_text"),
          disabled,
          "aria-label": "Non-claims"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Source refs"),
        h("textarea", {
          value: (draft && draft.source_refs_text) || "",
          onChange: update("source_refs_text"),
          disabled,
          "aria-label": "Source refs"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Evidence refs"),
        h("textarea", {
          value: (draft && draft.evidence_refs_text) || "",
          onChange: update("evidence_refs_text"),
          disabled,
          "aria-label": "Evidence refs"
        })
      )
    ),
    h(IntakeRefStatus, { draft, liveMode, onPreview: onPreviewRef }),
    h(
      "section",
      { className: `intake-write-preview ${changedFields.length ? "changed" : ""}`, "aria-label": "Pending intake write" },
      h("span", null, "Pending write"),
      h("strong", null, changedFields.length ? `${changedFields.length} changed field${changedFields.length === 1 ? "" : "s"}` : "No changes"),
      h("p", null, changedFields.length ? changedFields.map(displayFieldName).join(", ") : "Edit project-local fields before writing a receipt."),
      h("code", null, draft && draft.path ? `target=${draft.path}` : "target=none")
    ),
    h(
      "div",
      { className: "intake-editor-actions" },
      h("code", null, draft && draft.path ? draft.path : "No live intake loaded."),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: onReload,
          disabled: !liveMode,
          title: liveMode ? "Reload intake from disk" : "Start the local API first"
        },
        "Reload"
      ),
      h(
        "button",
        {
          className: "copy-button primary",
          type: "button",
          onClick: onSave,
          disabled: !canSave,
          title: changedFields.length ? saveTitle : "No changed fields to write"
        },
        "Save intake"
      )
    )
  );
}

function rowByLabel(rows, label) {
  return rows.find((row) => row.label === label) || null;
}

function statusClass(row) {
  if (!row) return "neutral";
  if (row.kind === "attention" || row.status === "blocked") return "attention";
  if (row.kind === "ready" || row.status === "ready" || row.status === "fresh") return "ready";
  return "neutral";
}

function StageRail({ snapshot, setSelectedLabel }) {
  const rows = snapshot.rows || [];
  return h(
    "section",
    { className: "stage-rail", "aria-label": "Case stages" },
    STAGES.map((stage) => {
      const row = rowByLabel(rows, stage.rowLabel);
      const tone = statusClass(row);
      return h(
        "button",
        {
          key: stage.id,
          type: "button",
          className: `stage-card ${tone}`,
          onClick: () => row && setSelectedLabel(row.label),
          disabled: !row
        },
        h("span", { className: "stage-index" }, stage.label),
        h("strong", null, row ? displayText(row.status) : "not recorded"),
        h("small", null, row ? row.detail : "No row in snapshot.")
      );
    })
  );
}

function ClaimSummary({ snapshot }) {
  const rows = snapshot.rows || [];
  const claim = rowByLabel(rows, "Bounded claim");
  const nonClaims = rowByLabel(rows, "Non-claims");
  const falsifier = rowByLabel(rows, "Next falsifier");
  const exportRow = rowByLabel(rows, "Report/export");
  return h(
    "section",
    { className: "case-summary", "aria-label": "Claim review summary" },
    h(
      "div",
      { className: "claim-panel" },
      h("span", { className: "eyebrow" }, "Bounded claim"),
      h("p", null, claim ? claim.detail : "No bounded claim recorded.")
    ),
    h(
      "div",
      { className: "case-facts" },
      h("div", null, h("span", null, "Export"), h("strong", null, displayText(exportRow ? exportRow.status : snapshot.report_status))),
      h("div", null, h("span", null, "Non-claims"), h("strong", null, nonClaims ? displayText(nonClaims.status) : "none")),
      h("div", null, h("span", null, "Next falsifier"), h("strong", null, falsifier ? displayText(falsifier.status) : "not surfaced"))
    )
  );
}

function CaseDocket({ snapshot, selectedRow }) {
  const rows = snapshot.rows || [];
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const reportRow = rowByLabel(rows, "Report/export");
  const reviewRow = rowByLabel(rows, "Latest review receipt");
  const activeRow = activeBlocker(rows) || selectedRow || reportRow || rows[0] || null;
  const sourceStatus = sourceRow ? displayText(sourceRow.status) : "not recorded";
  const evidenceStatus = evidenceRow ? displayText(evidenceRow.status) : "not recorded";
  const reviewStatus = reviewRow ? displayText(reviewRow.status) : "no receipt";
  const activeEvidence = activeRow ? evidenceItems(activeRow) : [];

  return h(
    "section",
    { className: "case-docket", "aria-label": "Case docket" },
    h(
      "div",
      { className: `docket-item ${snapshot.report_status === "blocked" ? "attention" : "ready"}` },
      h("span", null, "Decision"),
      h("strong", null, displayText(snapshot.report_status)),
      h("small", null, reportRow ? reportRow.detail : "No report/export row recorded.")
    ),
    h(
      "div",
      { className: "docket-item ready" },
      h("span", null, "Evidence path"),
      h("strong", null, `${sourceStatus} / ${evidenceStatus}`),
      h("small", null, `${activeEvidence.length} refs on selected row`)
    ),
    h(
      "div",
      { className: reviewRow && reviewRow.kind === "ready" ? "docket-item ready" : "docket-item neutral" },
      h("span", null, "Review handoff"),
      h("strong", null, reviewStatus),
      h("small", null, reviewRow ? reviewRow.detail : "No review receipt recorded.")
    )
  );
}

function rowSignal(row) {
  if (row.kind === "attention") return "Blocker";
  if (row.kind === "ready") return "Ready";
  return "Trace";
}

function rowStatus(rows, label) {
  const row = rowByLabel(rows, label);
  return row ? displayText(row.status) : "not recorded";
}

function workbenchSteps(snapshot) {
  const rows = snapshot.rows || [];
  const blocker = activeBlocker(rows);
  const reviewRow = rowByLabel(rows, "Latest review receipt");
  return [
    {
      label: "Open case",
      detail: "Project loaded",
      state: "ready",
      rowLabel: "Project"
    },
    {
      label: "Inspect claim",
      detail: `Claim ${rowStatus(rows, "Bounded claim")}; ${rowStatus(rows, "Non-claims")}`,
      state: "ready",
      rowLabel: "Bounded claim"
    },
    {
      label: "Check evidence",
      detail: `Sources ${rowStatus(rows, "Source readiness")}; evidence ${rowStatus(rows, "Evidence readiness")}`,
      state: rows.some((row) => row.label === "Source readiness" && row.kind === "attention") ? "attention" : "ready",
      rowLabel: "Evidence readiness"
    },
    {
      label: "Run preflight",
      detail: `Run ${rowStatus(rows, "Run readiness")}`,
      state: rows.some((row) => row.label === "Run readiness" && row.kind === "attention") ? "attention" : "ready",
      rowLabel: "Run readiness"
    },
    {
      label: "Resolve blocker",
      detail: blocker ? `${blocker.label}: ${displayText(blocker.status)}` : "No active blocker",
      state: blocker ? "attention" : "ready",
      rowLabel: blocker ? blocker.label : "Report/export"
    },
    {
      label: "Apply review",
      detail: reviewRow ? displayText(reviewRow.status) : "no review receipt",
      state: reviewRow && reviewRow.kind === "ready" ? "ready" : "neutral",
      rowLabel: "Latest review receipt"
    }
  ];
}

function FirstFiveMinutePath({ snapshot, setSelectedLabel }) {
  return h(
    "section",
    { className: "path-panel", "aria-label": "First five-minute path" },
    h(
      "div",
      { className: "path-heading" },
      h("span", { className: "eyebrow" }, "First five-minute path"),
      h("strong", null, "Inspect the claim, act on the blocker, then refresh the receipt.")
    ),
    h(
      "ol",
      { className: "path-steps" },
      workbenchSteps(snapshot).map((step) =>
        h(
          "li",
          { key: step.label, className: step.state },
          h(
            "button",
            {
              type: "button",
              onClick: () => setSelectedLabel(step.rowLabel),
              title: `Inspect ${step.rowLabel}`
            },
            h("span", null, step.label),
            h("strong", null, step.detail)
          )
        )
      )
    )
  );
}

function EvidenceType({ type }) {
  return h("span", { className: `evidence-type ${type}` }, type);
}

function EvidenceBlock({ item, onPreview, liveMode }) {
  const previewable = canPreviewEvidence(item);
  return h(
    "div",
    { className: `evidence-block ${item.type}` },
    h("div", { className: "evidence-block-head" }, h(EvidenceType, { type: item.type }), h("span", null, item.label)),
    h("code", null, item.value),
    previewable
      ? h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: liveMode ? "Preview file through local API" : "Start local API to preview files",
            onClick: () => onPreview && onPreview(item),
            disabled: !liveMode
          },
          "Preview"
        )
      : null,
    item.type === "command"
      ? h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: "Copy command",
            onClick: () => copyText(item.value)
          },
          "Copy"
        )
      : null
  );
}

function Sidebar({ snapshot, counts }) {
  return h(
    "aside",
    { className: "sidebar" },
    h("div", { className: "brand-lockup" }, h("div", { className: "brand-mark" }, "ZT"), h("div", { className: "side-title" }, h("strong", null, "ZTARE"), h("span", null, "Claim review"))),
    h(
      "nav",
      { className: "side-nav", "aria-label": "Workbench sections" },
      NAV_SECTIONS.map((item, index) =>
        h(
          "a",
          { href: `#row-${item.row}`, key: item.label, className: index === 0 ? "active" : "" },
          h("span", { className: `nav-icon ${item.tone}`, "aria-hidden": "true" }),
          h("span", { className: "nav-label" }, item.label)
        )
      )
    ),
    h(
      "div",
      { className: "side-footer" },
      h("span", null, "Rows"),
      h("strong", null, String(counts.total)),
      h("span", null, "Export"),
      h("strong", null, displayText(snapshot.report_status))
    )
  );
}

function CommandRail({ snapshot, selectedRow }) {
  const rows = snapshot.rows || [];
  const attentionRow = activeBlocker(rows);
  const actionRow = attentionRow || selectedRow || rows.find((row) => row.command) || rows[0] || null;
  const actionCommand = (actionRow && actionRow.command) || "";
  return h(
    "section",
    { className: "command-rail", "aria-label": "Current action" },
    h(
      "div",
      { className: "next-action" },
      h("span", null, "Current action"),
      h("strong", null, actionRow ? `${actionRow.label}: ${displayText(actionRow.status)}` : "No active row"),
      h("p", null, actionRow ? actionRow.detail : "Snapshot has no rows.")
    ),
    h(
      "div",
      { className: "command-card" },
      h("span", null, actionCommand ? "Command" : "Evidence"),
      actionCommand ? h("code", null, actionCommand) : h("code", null, actionRow && actionRow.provenance ? actionRow.provenance : "No command recorded."),
      actionCommand
        ? h(
            "button",
            {
              className: "copy-button",
              type: "button",
              title: "Copy current command",
              onClick: () => copyText(actionCommand)
            },
            "Copy"
          )
        : null
    )
  );
}

function NextMovePanel({ snapshot, selectedRow, setSelectedLabel, liveMode }) {
  const rows = snapshot.rows || [];
  const blocker = activeBlocker(rows);
  const actionRow = blocker || selectedRow || rows[0] || null;
  const actionCommand = (actionRow && actionRow.command) || "";
  const evidence = actionRow ? evidenceItems(actionRow)[0] : null;
  const status = actionRow ? displayText(actionRow.status) : "No row selected";
  const title = blocker ? "Review blocker before export" : "Inspect the current claim state";
  const why = actionRow
    ? actionRow.detail
    : "Snapshot has no rows. Refresh the workbench data before reviewing this case.";
  const evidenceText = evidence ? `${evidence.label}: ${evidence.value}` : "No evidence recorded for this row.";

  return h(
    "section",
    { className: `next-move-panel ${blocker ? "attention" : "ready"}`, "aria-label": "Next move" },
    h(
      "div",
      { className: "next-move-copy" },
      h("span", { className: "eyebrow" }, blocker ? "Needs action" : "Next move"),
      h("h2", null, title),
      h("p", null, why)
    ),
    h(
      "div",
      { className: "next-move-facts" },
      h("div", null, h("span", null, "Status"), h("strong", null, status)),
      h("div", null, h("span", null, "Evidence"), h("code", null, evidenceText))
    ),
    h(
      "div",
      { className: "next-move-actions" },
      h(
        "button",
        {
          type: "button",
          className: "copy-button primary",
          disabled: !actionRow,
          onClick: () => actionRow && setSelectedLabel(actionRow.label)
        },
        blocker ? "Review blocker" : "Inspect row"
      ),
      actionCommand
        ? h(
            "button",
            {
              type: "button",
              className: "copy-button",
              onClick: () => copyText(actionCommand)
            },
            "Copy command"
          )
        : null,
      h("a", { href: snapshotJsonHref(snapshot, liveMode), className: "text-link" }, liveMode ? "Open live JSON" : "Open snapshot")
    )
  );
}

function BlockerPanel({ snapshot, setSelectedLabel }) {
  const rows = snapshot.rows || [];
  const blocker = activeBlocker(rows);
  return h(
    "section",
    { className: `blocker-panel ${blocker ? "attention" : "ready"}`, "aria-label": "Status reasons" },
    h(
      "div",
      null,
      h("span", null, blocker ? "Current blocker" : "Export decision"),
      h("strong", null, blocker ? blocker.label : displayText(snapshot.report_status)),
      h("p", null, blocker ? blocker.detail : "No blocking row is active in this snapshot.")
    ),
    h(
      "div",
      { className: "reason-stack" },
      h(
        "ul",
        null,
        (snapshot.status_reasons || []).map((reason) => h("li", { key: reason }, displayText(reason)))
      ),
      blocker
        ? h(
            "button",
            {
              type: "button",
              className: "copy-button primary",
              onClick: () => setSelectedLabel(blocker.label)
            },
            "Review blocker"
          )
        : null
    )
  );
}

function ProvenanceStrip({ rows }) {
  const coverage = coverageSummary(rows);
  const coverageText = coverage.total ? `${coverage.rowsWithArtifacts}/${coverage.total}` : "0/0";
  return h(
    "section",
    { className: "provenance-strip", "aria-label": "Artifact coverage" },
    h("div", null, h("span", null, "Rows with artifacts"), h("strong", null, coverageText)),
    h("div", null, h("span", null, "Commands"), h("strong", null, String(coverage.commandRows))),
    h("div", null, h("span", null, "Receipts"), h("strong", null, String(coverage.receiptRows))),
    h("div", null, h("span", null, "Review files"), h("strong", null, String(coverage.reviewRows)))
  );
}

function ReviewQueue({ row, reviewState, liveMode }) {
  const decision = reviewState.decision || "unreviewed";
  const decisionLabel = (REVIEW_ACTIONS.find((action) => action.id === decision) || { label: "Unreviewed" }).label;
  const evidenceCount = row ? evidenceItems(row).length : 0;
  const receiptState = row && decision !== "unreviewed" ? (liveMode ? "ready to apply" : "file ready") : "decision needed";
  return h(
    "section",
    { className: `review-queue ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Review queue" },
    h("div", null, h("span", null, "Selected"), h("strong", null, row ? row.label : "No row")),
    h("div", null, h("span", null, "Decision"), h("strong", null, decisionLabel)),
    h("div", null, h("span", null, "Evidence"), h("strong", null, String(evidenceCount))),
    h("div", null, h("span", null, "Receipt"), h("strong", null, receiptState))
  );
}

function HealthFindingList({ title, emptyText, rows, renderRow }) {
  return h(
    "div",
    { className: "health-finding-list" },
    h("span", null, title),
    rows.length
      ? h("div", { className: "health-finding-rows" }, rows.map(renderRow))
      : h("p", null, emptyText)
  );
}

function HealthActionsPanel({ healthContext, healthMessage, liveMode, onPreviewSource }) {
  const kernel = (healthContext && healthContext.kernel) || {};
  const kernelSummary = kernel.summary || {};
  const action = (healthContext && healthContext.action_intelligence) || {};
  const actionCounts = action.counts || {};
  const attention = kernel.attention_components || [];
  const issues = action.issues || [];
  const sourcePaths = action.source_paths || {};
  const status = kernelSummary.overall_status || (liveMode ? "loading" : "static mode");
  const previewableSourcePaths = Object.entries(sourcePaths).filter(([_key, value]) => value);

  return h(
    "section",
    { className: `health-actions-panel ${status === "attention" || issues.length ? "attention" : "ready"}`, "aria-label": "Health and action context" },
    h(
      "div",
      { className: "health-summary" },
      h("span", { className: "eyebrow" }, "Health & actions"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        healthMessage ||
          (liveMode
            ? "Live kernel-health and action-intelligence context for this project."
            : "Start the local API to inspect live kernel-health and action-intelligence context.")
      )
    ),
    h(
      "div",
      { className: "health-metrics" },
      h("div", null, h("span", null, "Kernel"), h("strong", null, displayText(kernelSummary.component_status || status))),
      h("div", null, h("span", null, "Attention"), h("strong", null, String((kernelSummary.component_counts || {}).attention || attention.length || 0))),
      h("div", null, h("span", null, "Action issues"), h("strong", null, String(actionCounts.issues || issues.length || 0))),
      h("div", null, h("span", null, "Warnings"), h("strong", null, String(actionCounts.warning || 0)))
    ),
    h(
      "div",
      { className: "health-findings" },
      h(HealthFindingList, {
        title: "Kernel findings",
        emptyText: "Kernel health has no active attention component.",
        rows: attention,
        renderRow: (row, index) =>
          h(
            "div",
            { className: "health-finding-row kernel", key: `${row.component || "kernel"}:${index}` },
            h("strong", null, row.component || "kernel component"),
            h("small", null, displayText(row.status || "attention")),
            h("p", null, row.action || "Inspect component."),
            row.next_command
              ? h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    onClick: () => copyText(row.next_command),
                    title: "Copy kernel-health next command"
                  },
                  "Copy command"
                )
              : null
          )
      }),
      h(HealthFindingList, {
        title: "Action-intelligence rows",
        emptyText: "Action-intelligence health has no issue rows.",
        rows: issues,
        renderRow: (row, index) =>
          h(
            "div",
            { className: "health-finding-row action", key: `${row.issue_type || "issue"}:${row.scope || index}` },
            h("strong", null, displayText(row.issue_type || "source-health issue")),
            h("small", null, displayText(row.severity || "warning")),
            h("p", null, `${displayText(row.scope || "unknown scope")}: ${displayText(row.recommended_action || "inspect source health")}`)
          )
      }),
      h(
        "div",
        { className: "health-source-list" },
        h("span", null, "Health source files"),
        previewableSourcePaths.length
          ? previewableSourcePaths.map(([key, value]) =>
              h(
                "div",
                { className: "health-source-row", key },
                h("strong", null, displayText(key)),
                h("code", null, value),
                h(
                  "div",
                  { className: "health-source-actions" },
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      onClick: () => copyText(value),
                      title: "Copy source path"
                    },
                    "Copy"
                  ),
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode,
                      onClick: () => onPreviewSource && onPreviewSource({ type: "file", value }),
                      title: liveMode ? "Preview source file" : "Start the local API to preview files"
                    },
                    "Preview"
                  )
                )
              )
            )
          : h("p", null, "No source-health files reported.")
      )
    )
  );
}

function ReviewWorkspace({ snapshot, row, reviewState, setReviewState, liveMode, applyReviewLive }) {
  const decision = reviewState.decision || "unreviewed";
  const reviewFile = buildReviewFile(snapshot, row, reviewState);
  const reviewPayload = parseReviewFile(reviewFile);
  const rowKey = row ? rowSlug(row.label) : "";
  const reviewFilename = row ? `${snapshot.project}_${rowKey}_review.json` : "review.json";
  const command = row
    ? `ztare forensic-workbench apply-review --project ${snapshot.project} --row ${rowKey} --from ${reviewFilename}`
    : "";
  const reviewReady = Boolean(row && REVIEW_ACTIONS.some((action) => action.id === decision));
  const liveReady = Boolean(liveMode && reviewReady && reviewPayload);

  const updateDecision = (nextDecision) => {
    if (!row) return;
    setReviewState(row.label, { ...reviewState, decision: nextDecision });
  };

  const updateNote = (event) => {
    if (!row) return;
    setReviewState(row.label, { ...reviewState, note: event.target.value });
  };

  return h(
    "section",
    { className: `review-workspace ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Review decision" },
    h(
      "div",
      { className: "review-copy" },
      h("span", { className: "eyebrow" }, "Review decision"),
      h("h2", null, row ? row.label : "Select a row"),
      h("p", null, row ? "Decision and note for the selected evidence row." : "No evidence row selected.")
    ),
    h(
      "div",
      { className: "review-actions", role: "group", "aria-label": "Review actions" },
      REVIEW_ACTIONS.map((action) =>
        h(
          "button",
          {
            key: action.id,
            type: "button",
            className: decision === action.id ? "active" : "",
            onClick: () => updateDecision(action.id),
            disabled: !row
          },
          action.label
        )
      )
    ),
    h("textarea", {
      value: reviewState.note || "",
      onChange: updateNote,
      disabled: !row,
      placeholder: "Review note for this row",
      "aria-label": "Review note"
    }),
    h(
      "div",
      { className: "handoff-card" },
      h("div", null, h("span", null, "Review receipt"), h("code", null, command || "No row selected")),
      h(
        "div",
        { className: "handoff-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            title: reviewReady ? "Download review file" : "Choose a review decision first",
            onClick: () => downloadText(reviewFilename, reviewFile),
            disabled: !reviewReady
          },
          "Download file"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: liveReady ? "Apply review through local API" : "Run local API and choose a decision first",
            onClick: () => liveReady && applyReviewLive(rowKey, reviewPayload),
            disabled: !liveReady
          },
          "Apply"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: reviewReady ? "Copy review file JSON" : "Choose a review decision first",
            onClick: () => copyText(reviewFile),
            disabled: !reviewReady
          },
          "Copy JSON"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: row ? "Copy apply-review command" : "Select a row first",
            onClick: () => copyText(command),
            disabled: !row
          },
          "Copy command"
        )
      )
    ),
    h(
      "div",
      { className: "review-preview" },
      h("span", null, "Review JSON preview"),
      h("pre", null, reviewFile || "Select a row and decision to preview the saved review file.")
    )
  );
}

function RowActionWorkspace({ snapshot, row, actionState, setActionState, liveMode, applyRowActionLive }) {
  const suggestion = rowActionSuggestion(snapshot, row);
  const action = actionState.action || "next_step";
  const rowActionFile = buildRowActionFile(snapshot, row, actionState);
  const rowActionPayload = parseReviewFile(rowActionFile);
  const rowKey = row ? rowSlug(row.label) : "";
  const actionFilename = row ? `${snapshot.project}_${rowKey}_action.json` : "row_action.json";
  const command = row
    ? `ztare forensic-workbench save-action --project ${snapshot.project} --row ${rowKey} --from ${actionFilename}`
    : "";
  const actionReady = Boolean(row && actionState.note && actionState.note.trim());
  const liveReady = Boolean(liveMode && actionReady && rowActionPayload);

  const updateAction = (nextAction) => {
    if (!row) return;
    setActionState(row.label, { ...actionState, action: nextAction });
  };

  const updateNote = (event) => {
    if (!row) return;
    setActionState(row.label, { ...actionState, note: event.target.value });
  };

  const useSuggestion = () => {
    if (!row) return;
    setActionState(row.label, { action: suggestion.action, note: suggestion.note });
  };

  return h(
    "section",
    { className: `row-action-workspace ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Row action" },
    h(
      "div",
      { className: "review-copy" },
      h("span", { className: "eyebrow" }, "Saved action"),
      h("h2", null, row ? row.label : "Select a row"),
      h("p", null, row ? "Save the next project-backed action for this row." : "No evidence row selected.")
    ),
    h(
      "div",
      { className: "review-actions", role: "group", "aria-label": "Row actions" },
      ROW_ACTIONS.map((item) =>
        h(
          "button",
          {
            key: item.id,
            type: "button",
            className: action === item.id ? "active" : "",
            onClick: () => updateAction(item.id),
            disabled: !row
          },
          item.label
        )
      )
    ),
    h(
      "div",
      { className: "action-suggestion" },
      h("span", null, "Suggested action"),
      h("strong", null, suggestion.title),
      h("p", null, `${ROW_ACTION_LABELS[suggestion.action] || "Next step"}: ${suggestion.note}`),
      h("code", null, suggestion.evidence),
      h(
        "div",
        { className: "action-suggestion-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            onClick: useSuggestion,
            disabled: !row,
            title: row ? "Use the suggested action and note" : "Select a row first"
          },
          "Use suggestion"
        ),
        suggestion.command
          ? h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => copyText(suggestion.command)
              },
              "Copy command"
            )
          : null
      )
    ),
    h("textarea", {
      value: actionState.note || "",
      onChange: updateNote,
      disabled: !row,
      placeholder: "Concrete next action, source need, or export blocker",
      "aria-label": "Row action note"
    }),
    h(
      "div",
      { className: "handoff-card" },
      h("div", null, h("span", null, "Action receipt"), h("code", null, command || "No row selected")),
      h(
        "div",
        { className: "handoff-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            title: actionReady ? "Apply row action through local API" : "Write an action note first",
            onClick: () => liveReady && applyRowActionLive(rowKey, rowActionPayload),
            disabled: !liveReady
          },
          "Save action"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: actionReady ? "Download row action JSON" : "Write an action note first",
            onClick: () => downloadText(actionFilename, rowActionFile),
            disabled: !actionReady
          },
          "Download file"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: actionReady ? "Copy row action JSON" : "Write an action note first",
            onClick: () => copyText(rowActionFile),
            disabled: !actionReady
          },
          "Copy JSON"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: row ? "Copy save-action command" : "Select a row first",
            onClick: () => copyText(command),
            disabled: !row
          },
          "Copy command"
        )
      )
    )
  );
}

function Toolbar({ filter, query, setFilter, setQuery }) {
  return h(
    "div",
    { className: "toolbar" },
    h(
      "div",
      { className: "filter-tabs", role: "tablist", "aria-label": "Row filter" },
      FILTERS.map((item) =>
        h(
          "button",
          {
            key: item.id,
            type: "button",
            className: filter === item.id ? "active" : "",
            onClick: () => setFilter(item.id)
          },
          item.label
        )
      )
    ),
    h("input", {
      type: "search",
      value: query,
      onChange: (event) => setQuery(event.target.value),
      placeholder: "Filter evidence, commands, warnings",
      "aria-label": "Filter rows"
    })
  );
}

function WorkbenchTable({ rows, selectedLabel, setSelectedLabel }) {
  return h(
    "div",
    { className: "table-shell" },
    h(
      "div",
      { className: "table-head" },
      h("span", null, "Signal"),
      h("span", null, "Step"),
      h("span", null, "Status"),
      h("span", null, "Evidence"),
      h("span", null, "Summary")
    ),
    h(
      "div",
      { className: "table-body" },
      rows.map((row, index) =>
        h(
          "button",
          {
            id: `row-${index}`,
            key: row.label,
            className: `table-row ${row.kind || "neutral"} ${selectedLabel === row.label ? "selected" : ""}`,
            type: "button",
            onClick: () => setSelectedLabel(row.label)
          },
          h("span", { className: `signal-cell ${row.kind || "neutral"}` }, rowSignal(row)),
          h("span", { className: "step-cell" }, h("strong", null, row.label), h("small", null, kindLabel(row.kind))),
          h("span", { className: "status-cell" }, displayText(row.status)),
          h(
            "span",
            { className: "evidence-cell" },
            evidenceItems(row).map((item) => h(EvidenceType, { key: item.label, type: item.type }))
          ),
          h("span", { className: "summary-cell" }, row.detail)
        )
      )
    )
  );
}

function FilePreview({ filePreview, filePreviewMessage }) {
  return h(
    "section",
    { className: "file-preview", "aria-label": "File preview" },
    h("h3", null, "File preview"),
    filePreviewMessage ? h("p", null, filePreviewMessage) : null,
    filePreview
      ? h(
          "div",
          { className: "file-preview-body" },
          h(
            "div",
            { className: "file-preview-meta" },
            h("span", null, filePreview.path),
            h("span", null, `${filePreview.bytes} bytes${filePreview.truncated ? " (truncated)" : ""}`)
          ),
          h("pre", null, filePreview.text || "")
        )
      : null
  );
}

function Inspector({ row, snapshot, liveMode, loadFilePreview, filePreview, filePreviewMessage }) {
  if (!row) {
    return h("aside", { className: "inspector" }, h("p", null, "Select a row to inspect evidence."));
  }

  const items = evidenceItems(row);
  return h(
    "aside",
    { className: `inspector ${row.kind || "neutral"}` },
    h(
      "div",
      { className: "inspector-head" },
      h("span", null, kindLabel(row.kind)),
      h("h2", null, row.label),
      h("p", null, row.detail)
    ),
    h(
      "dl",
      { className: "inspector-facts" },
      h("div", null, h("dt", null, "Status"), h("dd", null, displayText(row.status))),
      h("div", null, h("dt", null, "Project"), h("dd", null, snapshot.project)),
      h("div", null, h("dt", null, "Readiness"), h("dd", null, displayText(snapshot.readiness)))
    ),
    h(
      "section",
      { className: "evidence-stack", "aria-label": "Evidence" },
      h("h3", null, "Evidence"),
      items.length
        ? items.map((item) =>
            h(EvidenceBlock, {
              key: `${item.type}:${item.value}`,
              item,
              onPreview: loadFilePreview,
              liveMode
            })
          )
        : h("p", null, "No evidence recorded.")
    ),
    h(FilePreview, { filePreview, filePreviewMessage })
  );
}

function EmptyState() {
  return h(
    "div",
    { className: "empty-state" },
    h("strong", null, "No rows match the current filter."),
    h("span", null, "Clear the search field or switch to All rows.")
  );
}

function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [modeMessage, setModeMessage] = useState("");
  const [healthContext, setHealthContext] = useState(null);
  const [healthMessage, setHealthMessage] = useState("");
  const [projects, setProjects] = useState([]);
  const [selectedProjectKey, setSelectedProjectKey] = useState("");
  const [liveMode, setLiveMode] = useState(false);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [intakeDraft, setIntakeDraft] = useState(null);
  const [intakeMessage, setIntakeMessage] = useState("");
  const [filePreview, setFilePreview] = useState(null);
  const [filePreviewMessage, setFilePreviewMessage] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [reviewStates, setReviewStates] = useState({});
  const [actionStates, setActionStates] = useState({});
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");

  const installSnapshot = (payload) => {
    setSnapshot(payload);
    setReviewMessage("");
    setActionMessage("");
    const rows = payload.rows || [];
    const firstAttention = rows.find((row) => row.kind === "attention");
    setSelectedLabel((firstAttention && firstAttention.label) || (rows[0] && rows[0].label) || "");
  };

  const loadHealthContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setHealthMessage("Loading live health context.");
    return fetch(endpointUrl("/api/health", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`health fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        setHealthContext(payload);
        setHealthMessage("Live health context loaded from the local API.");
      })
      .catch((err) => {
        setHealthContext(null);
        setHealthMessage(`Live health context unavailable: ${err.message || err}`);
      });
  };

  const loadIntakeDraft = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setIntakeMessage("Loading project intake.");
    return fetch(endpointUrl("/api/intake", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`intake fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "intake fetch failed");
        setIntakeDraft(intakeDraftFromPayload(payload));
        setIntakeMessage(payload.editable === false ? `Loaded read-only intake: ${payload.path}.` : `Loaded ${payload.path}.`);
      })
      .catch((err) => {
        setIntakeDraft(null);
        setIntakeMessage(`Live intake unavailable: ${err.message || err}`);
      });
  };

  const loadSnapshot = (projectInput, useLiveApi, options = {}) => {
    const allowStaticFallback = options.allowStaticFallback === true;
    const loadParams =
      typeof projectInput === "string"
        ? { project: projectInput, rubric: projectInput }
        : projectLoadParams(projectInput);
    setLoadingSnapshot(true);
    setError("");
    const url = useLiveApi && loadParams.project ? endpointUrl("/api/snapshot", loadParams) : "/workbench_snapshot.json";
    return fetch(url, { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`snapshot fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        installSnapshot(payload);
        setModeMessage(
          useLiveApi
            ? `Live project snapshot loaded from the local API: ${payload.project}.`
            : `Static snapshot loaded from ${payload.html_output || "workbench_snapshot.json"}.`
        );
        if (useLiveApi) {
          const liveParams = { ...loadParams, project: payload.project, rubric: payload.rubric || loadParams.rubric, intake: payload.intake || loadParams.intake };
          setSelectedProjectKey(payload.project);
          return Promise.allSettled([loadHealthContext(liveParams), loadIntakeDraft(liveParams)]);
        }
        setHealthContext(null);
        setHealthMessage("Static mode uses the last generated snapshot only.");
        setIntakeDraft(null);
        setIntakeMessage("Static mode cannot edit the project intake.");
        return null;
      })
      .catch((err) => {
        if (useLiveApi && allowStaticFallback) {
          setLiveMode(false);
          setModeMessage("Local API not available. Showing the last generated static snapshot.");
          return loadSnapshot("", false);
        }
        throw err;
      })
      .finally(() => setLoadingSnapshot(false));
  };

  useEffect(() => {
    fetch("/api/projects", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`project index fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        const projectRows = payload.projects || [];
        if (!projectRows.length) throw new Error("project index is empty");
        setProjects(projectRows);
        setLiveMode(true);
        const preferred = projectRows.find((row) => row.project === payload.default_project) || projectRows[0];
        setSelectedProjectKey(preferred.project);
        return loadSnapshot(preferred, true, { allowStaticFallback: true });
      })
      .catch(() =>
        loadSnapshot("", false).catch((err) => setError(String(err.message || err)))
      );
  }, []);

  const handleProjectChange = (event) => {
    const project = event.target.value;
    if (!project || !liveMode) return;
    const entry = projects.find((row) => row.project === project) || { project, rubric: project };
    setSelectedProjectKey(project);
    loadSnapshot(entry, true).catch((err) =>
      setModeMessage(`Could not load live project snapshot for ${project}: ${err.message || err}`)
    );
  };

  const refreshCurrentProject = () => {
    if (!snapshot || !liveMode) return;
    const entry = projects.find((row) => row.project === snapshot.project) || snapshot;
    loadSnapshot(entry, true).catch((err) =>
      setModeMessage(`Could not refresh live project snapshot for ${snapshot.project}: ${err.message || err}`)
    );
  };

  const refreshCurrentIntake = () => {
    if (!snapshot || !liveMode) return;
    const entry = currentProjectEntry || snapshot;
    loadIntakeDraft(projectLoadParams(entry));
  };

  const counts = useMemo(() => {
    const rows = (snapshot && snapshot.rows) || [];
    return {
      total: rows.length,
      attention: rows.filter((row) => row.kind === "attention").length,
      ready: rows.filter((row) => row.kind === "ready").length,
      recorded: rows.filter((row) => !row.kind || row.kind === "neutral").length
    };
  }, [snapshot]);

  const filteredRows = useMemo(() => {
    if (!snapshot) return [];
    const needle = query.trim().toLowerCase();
    return (snapshot.rows || []).filter((row) => {
      const kind = row.kind || "neutral";
      if (filter !== "all" && kind !== filter) return false;
      if (!needle) return true;
      return [
        row.label,
        row.status,
        row.detail,
        row.file,
        row.source,
        row.evidence,
        row.command,
        row.receipt,
        row.review_artifact,
        row.warning,
        row.provenance
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [filter, query, snapshot]);

  const selectedRow = useMemo(() => {
    if (!snapshot) return null;
    const visibleSelected = filteredRows.find((row) => row.label === selectedLabel);
    return visibleSelected || filteredRows[0] || null;
  }, [filteredRows, selectedLabel, snapshot]);

  useEffect(() => {
    setFilePreview(null);
    setFilePreviewMessage("");
  }, [selectedRow && selectedRow.label]);

  const currentProjectEntry = useMemo(() => {
    if (!snapshot) return null;
    return projects.find((row) => row.project === selectedProjectKey) || projects.find((row) => row.project === snapshot.project) || null;
  }, [projects, selectedProjectKey, snapshot]);

  const selectedReviewState = (selectedRow && reviewStates[selectedRow.label]) || { decision: "", note: "" };
  const setSelectedReviewState = (label, nextState) => {
    setReviewStates((current) => ({ ...current, [label]: nextState }));
  };
  const selectedActionState = (selectedRow && actionStates[selectedRow.label]) || { action: "next_step", note: "" };
  const setSelectedActionState = (label, nextState) => {
    setActionStates((current) => ({ ...current, [label]: nextState }));
  };

  const applyReviewLive = (rowSlugValue, reviewPayload) => {
    if (!snapshot || !liveMode || !rowSlugValue || !reviewPayload) return;
    setReviewMessage("Applying review.");
    fetch("/api/review", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: snapshot.project,
        rubric: (currentProjectEntry && currentProjectEntry.rubric) || snapshot.rubric,
        intake: (currentProjectEntry && currentProjectEntry.intake) || snapshot.intake,
        row_slug: rowSlugValue,
        review_file: reviewPayload
      })
    })
      .then((response) => {
        if (!response.ok) throw new Error(`review apply failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "review apply failed");
        if (payload.snapshot) installSnapshot(payload.snapshot);
        setReviewMessage(
          payload.snapshot_error
            ? `Applied review for ${reviewPayload.row}. Snapshot refresh failed: ${payload.snapshot_error}`
            : `Applied review for ${reviewPayload.row}.`
        );
      })
      .catch((err) => setReviewMessage(String(err.message || err)));
  };

  const applyRowActionLive = (rowSlugValue, actionPayload) => {
    if (!snapshot || !liveMode || !rowSlugValue || !actionPayload) return;
    setActionMessage("Saving row action.");
    fetch("/api/row-action", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: snapshot.project,
        rubric: (currentProjectEntry && currentProjectEntry.rubric) || snapshot.rubric,
        intake: (currentProjectEntry && currentProjectEntry.intake) || snapshot.intake,
        row_slug: rowSlugValue,
        action_file: actionPayload
      })
    })
      .then((response) => {
        if (!response.ok) throw new Error(`row action save failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "row action save failed");
        if (payload.snapshot) installSnapshot(payload.snapshot);
        setActionMessage(
          payload.snapshot_error
            ? `Saved action for ${actionPayload.row}. Snapshot refresh failed: ${payload.snapshot_error}`
            : `Saved action for ${actionPayload.row}.`
        );
      })
      .catch((err) => setActionMessage(String(err.message || err)));
  };

  const saveIntakeDraft = () => {
    if (!snapshot || !liveMode || !intakeDraft) return;
    if (intakeDraft.editable === false) {
      setIntakeMessage("This intake is read-only in the local workbench.");
      return;
    }
    if (!intakeChangedFields(intakeDraft).length) {
      setIntakeMessage("No changed intake fields to write.");
      return;
    }
    setIntakeMessage("Saving intake edit.");
    fetch("/api/intake", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: snapshot.project,
        rubric: (currentProjectEntry && currentProjectEntry.rubric) || snapshot.rubric,
        intake: (currentProjectEntry && currentProjectEntry.intake) || snapshot.intake,
        fields: {
          bounded_claim: intakeDraft.bounded_claim,
          next_falsifier: intakeDraft.next_falsifier,
          notes: intakeDraft.notes,
          non_claims: linesFromText(intakeDraft.non_claims_text),
          source_refs: linesFromText(intakeDraft.source_refs_text),
          evidence_refs: linesFromText(intakeDraft.evidence_refs_text)
        }
      })
    })
      .then((response) => {
        if (!response.ok) throw new Error(`intake save failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "intake save failed");
        if (payload.intake) setIntakeDraft(intakeDraftFromPayload(payload.intake));
        if (payload.snapshot) installSnapshot(payload.snapshot);
        setIntakeMessage(
          payload.snapshot_error
            ? `Saved intake edit. Snapshot refresh failed: ${payload.snapshot_error}`
            : `Saved intake edit receipt: ${(payload.edit && payload.edit.latest) || "recorded"}.`
        );
      })
      .catch((err) => setIntakeMessage(String(err.message || err)));
  };

  const loadFilePreview = (item) => {
    if (!liveMode || !item || !item.value) {
      setFilePreview(null);
      setFilePreviewMessage("Start the local API to preview repository files.");
      return;
    }
    setFilePreview(null);
    setFilePreviewMessage(`Loading ${item.value}.`);
    fetch(endpointUrl("/api/file", { path: item.value }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`file preview failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "file preview failed");
        setFilePreview(payload);
        setFilePreviewMessage(payload.truncated ? "Preview truncated to the first 200 KB." : "Preview loaded from the local API.");
      })
      .catch((err) => {
        setFilePreview(null);
        setFilePreviewMessage(String(err.message || err));
      });
  };

  if (error) {
    return h("main", { className: "state-page error" }, h("h1", null, "Forensic Workbench"), h("p", null, error));
  }
  if (!snapshot) {
    return h("main", { className: "state-page loading" }, h("h1", null, "Forensic Workbench"), h("p", null, "Loading snapshot."));
  }

  return h(
    "main",
    { className: "app-shell" },
    h(Sidebar, { snapshot, counts }),
    h(
      "section",
      { className: "workbench" },
      h(
        "header",
        { className: "topbar" },
        h(
          "div",
          { className: "topbar-copy" },
          h("span", { className: "eyebrow" }, "Local case"),
          h("h1", null, "Case File"),
          h(ProjectIdentity, { snapshot })
        ),
        h(
          "div",
          { className: "topbar-actions" },
          liveMode
            ? h(
                "label",
                { className: "project-picker" },
                h("span", null, loadingSnapshot ? "Refreshing" : "Project"),
                h(
                  "select",
                  { value: selectedProjectKey || snapshot.project, onChange: handleProjectChange, disabled: loadingSnapshot },
                  projects.map((project) => h("option", { key: project.project, value: project.project }, projectOptionLabel(project)))
                )
              )
            : null,
          liveMode
            ? h(
                "button",
                {
                  type: "button",
                  className: "snapshot-link",
                  onClick: refreshCurrentProject,
                  disabled: loadingSnapshot,
                  title: "Refresh from local project files"
                },
                loadingSnapshot ? "Refreshing" : "Refresh"
              )
            : null,
          h("a", { href: snapshotJsonHref(snapshot, liveMode), className: "snapshot-link" }, liveMode ? "Live JSON" : "Snapshot JSON")
        )
      ),
      modeMessage ? h("div", { className: `mode-banner ${liveMode ? "live" : "static"}` }, modeMessage) : null,
      h(ProjectContextPanel, { projectEntry: currentProjectEntry, snapshot }),
      h(IntakeEditor, {
        draft: intakeDraft,
        setDraft: setIntakeDraft,
        liveMode,
        message: intakeMessage,
        onSave: saveIntakeDraft,
        onReload: refreshCurrentIntake,
        onPreviewRef: loadFilePreview
      }),
      h(NextMovePanel, { snapshot, selectedRow, setSelectedLabel, liveMode }),
      h(CaseDocket, { snapshot, selectedRow }),
      h(HealthActionsPanel, { healthContext, healthMessage, liveMode, onPreviewSource: loadFilePreview }),
      h(StageRail, { snapshot, setSelectedLabel }),
      h(FirstFiveMinutePath, { snapshot, setSelectedLabel }),
      h(ClaimSummary, { snapshot }),
      h(
        "section",
        { className: "metrics", "aria-label": "Snapshot status" },
        h(Metric, { label: "Run readiness", value: snapshot.readiness, tone: "ready" }),
        h(Metric, { label: "Export", value: snapshot.report_status, tone: snapshot.report_status === "blocked" ? "attention" : "ready" }),
        h(Metric, { label: "Evidence rows", value: String(counts.total) }),
        h(Metric, { label: "Needs review", value: String(counts.attention), tone: counts.attention ? "attention" : "ready" })
      ),
      h(BlockerPanel, { snapshot, setSelectedLabel }),
      h(CommandRail, { snapshot, selectedRow }),
      h(ProvenanceStrip, { rows: snapshot.rows || [] }),
      h(ReviewQueue, { row: selectedRow, reviewState: selectedReviewState, liveMode }),
      reviewMessage ? h("div", { className: "review-message" }, reviewMessage) : null,
      h(ReviewWorkspace, { snapshot, row: selectedRow, reviewState: selectedReviewState, setReviewState: setSelectedReviewState, liveMode, applyReviewLive }),
      actionMessage ? h("div", { className: "review-message" }, actionMessage) : null,
      h(RowActionWorkspace, {
        snapshot,
        row: selectedRow,
        actionState: selectedActionState,
        setActionState: setSelectedActionState,
        liveMode,
        applyRowActionLive
      }),
      h(Toolbar, { filter, query, setFilter, setQuery }),
      h(
        "section",
        { className: "main-grid" },
        filteredRows.length
          ? h(WorkbenchTable, { rows: filteredRows, selectedLabel: selectedRow && selectedRow.label, setSelectedLabel })
          : h(EmptyState),
        h(Inspector, { row: selectedRow, snapshot, liveMode, loadFilePreview, filePreview, filePreviewMessage })
      )
    )
  );
}

createRoot(document.getElementById("root")).render(h(App));
