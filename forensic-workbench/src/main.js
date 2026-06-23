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
    return `/api/snapshot?project=${encodeURIComponent(snapshot.project)}`;
  }
  return "/workbench_snapshot.json";
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

function parseReviewFile(value) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
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
  const suffix = project.intake_source ? ` · ${displayText(project.intake_source)}` : "";
  return `${project.project}${suffix}`;
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

function EvidenceBlock({ item }) {
  return h(
    "div",
    { className: `evidence-block ${item.type}` },
    h("div", { className: "evidence-block-head" }, h(EvidenceType, { type: item.type }), h("span", null, item.label)),
    h("code", null, item.value),
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

function Inspector({ row, snapshot }) {
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
      items.length ? items.map((item) => h(EvidenceBlock, { key: item.label, item })) : h("p", null, "No evidence recorded.")
    )
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
  const [projects, setProjects] = useState([]);
  const [liveMode, setLiveMode] = useState(false);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [reviewStates, setReviewStates] = useState({});
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");

  const installSnapshot = (payload) => {
    setSnapshot(payload);
    setReviewMessage("");
    const rows = payload.rows || [];
    const firstAttention = rows.find((row) => row.kind === "attention");
    setSelectedLabel((firstAttention && firstAttention.label) || (rows[0] && rows[0].label) || "");
  };

  const loadSnapshot = (project, useLiveApi, options = {}) => {
    const allowStaticFallback = options.allowStaticFallback === true;
    setLoadingSnapshot(true);
    setError("");
    const url = useLiveApi && project ? `/api/snapshot?project=${encodeURIComponent(project)}` : "/workbench_snapshot.json";
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
        return loadSnapshot(preferred.project, true, { allowStaticFallback: true });
      })
      .catch(() =>
        loadSnapshot("", false).catch((err) => setError(String(err.message || err)))
      );
  }, []);

  const handleProjectChange = (event) => {
    const project = event.target.value;
    if (!project || !liveMode) return;
    loadSnapshot(project, true).catch((err) =>
      setModeMessage(`Could not load live project snapshot for ${project}: ${err.message || err}`)
    );
  };

  const refreshCurrentProject = () => {
    if (!snapshot || !liveMode) return;
    loadSnapshot(snapshot.project, true).catch((err) =>
      setModeMessage(`Could not refresh live project snapshot for ${snapshot.project}: ${err.message || err}`)
    );
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

  const selectedReviewState = (selectedRow && reviewStates[selectedRow.label]) || { decision: "", note: "" };
  const setSelectedReviewState = (label, nextState) => {
    setReviewStates((current) => ({ ...current, [label]: nextState }));
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
                  { value: snapshot.project, onChange: handleProjectChange, disabled: loadingSnapshot },
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
      h(NextMovePanel, { snapshot, selectedRow, setSelectedLabel, liveMode }),
      h(CaseDocket, { snapshot, selectedRow }),
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
      h(Toolbar, { filter, query, setFilter, setQuery }),
      h(
        "section",
        { className: "main-grid" },
        filteredRows.length
          ? h(WorkbenchTable, { rows: filteredRows, selectedLabel: selectedRow && selectedRow.label, setSelectedLabel })
          : h(EmptyState),
        h(Inspector, { row: selectedRow, snapshot })
      )
    )
  );
}

createRoot(document.getElementById("root")).render(h(App));
