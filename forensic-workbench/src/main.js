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
const REPORT_CONTRACT_SCHEMA = "ztare-forensic-workbench-report-contract-v1";
const CASE_FILE_WRITE_SCHEMA = "ztare-forensic-workbench-case-file-write-receipt-v1";
const SOURCE_TYPES = ["source_evidence", "seed_hypothesis", "research_question", "collection_todo", "untyped"];
const PROJECT_SLUG_RE = /^[A-Za-z0-9_.-]+$/;
const SOURCE_IMPORT_FILENAME_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(md|txt)$/;

function emptySourceImportDraft() {
  return { filename: "", source_type: "source_evidence", body: "" };
}

function emptySourceEditDraft() {
  return { relative_raw_path: "", source_type: "source_evidence", body: "" };
}

const STAGES = [
  { id: "sources", label: "Sources", rowLabel: "Source readiness" },
  { id: "evidence", label: "Evidence", rowLabel: "Evidence readiness" },
  { id: "run", label: "Run", rowLabel: "Run readiness" },
  { id: "export", label: "Export", rowLabel: "Report/export" }
];

const DISPLAY_OVERRIDES = {
  valid_packet: "valid intake",
  missing_packet: "missing evidence file",
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

function displayMessage(value) {
  return String(value || "")
    .replace(/\bcompiled evidence packet\b/gi, "compiled evidence file")
    .replace(/\bevidence packet\b/gi, "evidence file")
    .replace(/\bpacket boundary\b/gi, "intake boundary");
}

function snapshotRefreshMessage(base, payload) {
  const snapshotError = displayMessage(payload && payload.snapshot_error);
  if (snapshotError) return `${base}. Snapshot refresh failed: ${snapshotError}`;
  if (payload && payload.snapshot) return `${base} and refreshed the case.`;
  return `${base}. Refresh status was not recorded.`;
}

function shortDigest(value) {
  const raw = String(value || "");
  if (!raw) return "none";
  return raw.length > 16 ? `${raw.slice(0, 12)}...${raw.slice(-4)}` : raw;
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

function safeFilePart(value) {
  return String(value || "")
    .trim()
    .replace(/[^A-Za-z0-9_.-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80) || "case";
}

function caseFileDownloadName(snapshot) {
  const project = safeFilePart((snapshot && snapshot.project) || "ztare");
  const intake = safeFilePart((snapshot && snapshot.intake) || "case");
  return `${project}_${intake}_case_file.json`;
}

function caseScopedDownloadName(snapshot, rowKey, suffix) {
  const project = safeFilePart((snapshot && snapshot.project) || "ztare");
  const intake = safeFilePart((snapshot && snapshot.intake) || "case");
  const row = safeFilePart(rowKey || "row");
  return `${project}_${intake}_${row}_${suffix}.json`;
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

function rawSourceRelative(row) {
  const direct = String((row && row.relative_raw_path) || "");
  if (direct) return direct;
  const path = String((row && row.path) || "");
  const marker = "/raw/";
  const markerIndex = path.indexOf(marker);
  return markerIndex === -1 ? path : path.slice(markerIndex + marker.length);
}

function sourceBasename(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const parts = raw.split(/[\\/]/);
  return parts[parts.length - 1] || "";
}

function sourceFilenameExists(sourceList, filename) {
  const target = sourceBasename(filename);
  if (!target) return false;
  const sources = (sourceList && sourceList.sources) || [];
  return sources.some((row) => sourceBasename(rawSourceRelative(row) || row.path) === target);
}

function projectSlugExists(projects, slug) {
  const target = String(slug || "").trim();
  if (!target) return false;
  return (projects || []).some((row) => row.project === target);
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

function receiptMatchesCase(receipt, context) {
  if (!receipt || !context) return true;
  const project = String(context.project || "").trim();
  const intake = String(context.intake || "").trim();
  const caseKey = projectEntryKey(context);
  if (receipt.project && project && receipt.project !== project) return false;
  if (receipt.case_key) return receipt.case_key === caseKey;
  if (receipt.intake && intake) return receipt.intake === intake;
  return true;
}

function latestReceiptForRow(receiptHistory, row, kind, context) {
  if (!row) return null;
  const slug = rowSlug(row.label);
  return ((receiptHistory && receiptHistory.receipts) || []).find((receipt) => {
    if (receipt.kind !== kind) return false;
    if (!receiptMatchesCase(receipt, context)) return false;
    if (receipt.row_slug === slug) return true;
    return rowSlug(receipt.row || "") === slug;
  }) || null;
}

function receiptArtifactPath(receipt) {
  if (!receipt) return "";
  return receipt.review_file_path || receipt.action_file_path || receipt.case_file_path || receipt.source_path || receipt.intake_path || "";
}

function receiptChangeSummary(receipt, kind = "") {
  if (!receipt) return "";
  const parts = [];
  const fields = (receipt.updated_fields || []).map(displayFieldName).filter(Boolean);
  if (fields.length) parts.push(`fields: ${fields.join(", ")}`);
  if (receipt.decision) parts.push(`decision: ${displayText(receipt.decision)}`);
  if (receipt.action) parts.push(`action: ${displayText(receipt.action)}`);
  if (receipt.source_type) parts.push(`source type: ${displayText(receipt.source_type)}`);
  if (receipt.binding_mode) parts.push(`binding: ${displayText(receipt.binding_mode)}`);
  if (receipt.row_count !== undefined || receipt.command_count !== undefined || receipt.receipt_count !== undefined) {
    parts.push(`case: ${receipt.row_count || 0} rows, ${receipt.command_count || 0} commands, ${receipt.receipt_count || 0} receipts`);
  }
  if (!parts.length && kind) parts.push(displayText(kind));
  return parts.join(" / ");
}

function receiptCaseSummary(receipt) {
  if (!receipt) return "";
  const parts = [];
  if (receipt.case_key) parts.push(`case ${receipt.case_key}`);
  else if (receipt.project) parts.push(`project ${receipt.project}`);
  if (receipt.intake) parts.push(`intake ${receipt.intake}`);
  if (receipt.rubric && receipt.rubric !== receipt.project) parts.push(`rubric ${receipt.rubric}`);
  return parts.join(" / ");
}

function actionIntelligenceNote(row, fallback = "Inspect action-intelligence row") {
  if (!row) return fallback;
  const refs = Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean) : [];
  const parts = [
    row.recommended_action || row.issue_type || fallback,
    row.blocking_rule ? `rule: ${row.blocking_rule}` : "",
    row.scope ? `scope: ${row.scope}` : "",
    row.domain ? `domain: ${row.domain}` : "",
    row.rationale ? `rationale: ${row.rationale}` : "",
    refs.length ? `evidence: ${refs.slice(0, 4).join(", ")}` : ""
  ].filter(Boolean);
  return parts.join(" | ");
}

function actionIntelligenceAction(row) {
  const text = `${(row && row.recommended_action) || ""} ${(row && row.issue_type) || ""}`.toLowerCase();
  if (/source|ledger|archive|surfacing|evidence/.test(text)) return "needs_source";
  if (/block|export/.test(text)) return "export_blocker";
  if (/ready|run/.test(text)) return "ready_to_run";
  return "next_step";
}

function rowForActionNote(rows, action, selectedRow) {
  if (action === "needs_source") {
    return rowByLabel(rows, "Source readiness") || rowByLabel(rows, "Evidence readiness") || selectedRow;
  }
  if (action === "export_blocker") return rowByLabel(rows, "Report/export") || activeBlocker(rows) || selectedRow;
  if (action === "ready_to_run") return rowByLabel(rows, "Run readiness") || rowByLabel(rows, "Preflight") || selectedRow;
  return selectedRow || activeBlocker(rows) || rowByLabel(rows, "Report/export") || rowByLabel(rows, "Run readiness") || rows[0] || null;
}

function repoPathCandidate(value) {
  return String(value || "").trim().split("#")[0].trim();
}

function isPreviewableRepoPath(value) {
  const raw = repoPathCandidate(value);
  if (!raw || raw.startsWith("/") || raw.includes("..")) return false;
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(raw)) return false;
  return true;
}

function previewableRepoPath(value) {
  const path = repoPathCandidate(value);
  return isPreviewableRepoPath(path) ? path : "";
}

function previewFileTitle(liveMode, previewable, readyTitle = "Preview the written artifact") {
  if (!liveMode) return "Start the local API to preview files";
  if (!previewable) return "Written artifact is not a repository file";
  return readyTitle;
}

function buildReviewFile(snapshot, row, reviewState) {
  if (!row) return "";
  const payload = {
    schema: "ztare-forensic-workbench-review-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    intake: snapshot.intake || "",
    case_key: projectEntryKey(snapshot),
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
    intake: snapshot.intake || "",
    case_key: projectEntryKey(snapshot),
    row: row.label,
    row_status: displayText(row.status),
    action: actionState.action || "next_step",
    note: actionState.note || "",
    evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
  };
  return JSON.stringify(payload, null, 2);
}

function sourceActionReceiptEvent(payload) {
  if (!payload || !payload.writes) return null;
  const parsed = payload.parsed_output || {};
  const receiptPath = payload.receipt_path || parsed.receipt_path || parsed.path || parsed.source_index_receipt || "";
  const latestPath = payload.latest || receiptPath;
  const sourcePath = parsed.source_index || parsed.workspace_meta || parsed.provenance_path || parsed.path || "";
  const receipt = payload.receipt || parsed.receipt || {
    schema: "ztare-forensic-workbench-source-action-receipt-v1",
    project: parsed.project || payload.project || "",
    action: payload.action || "",
    status: parsed.status || parsed.merge_status || (payload.accepted ? "accepted" : "attention"),
    accepted: Boolean(payload.accepted),
    returncode: payload.returncode,
    source_path: sourcePath,
    source_receipt_path: parsed.source_index_receipt || parsed.receipt_path || parsed.path || "",
    source_sha256: parsed.source_sha256 || parsed.sha256 || "",
    source_receipt_sha256: parsed.source_receipt_sha256 || "",
    source_count: parsed.source_count
  };
  return {
    kind: "source_action",
    row: payload.label || displayText(payload.action || "source action"),
    result: {
      ...payload,
      receipt,
      receipt_path: receiptPath,
      latest: latestPath
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function sourceCheckDetail(payload) {
  const check = (payload && payload.source_check) || {};
  return {
    accepted: Boolean(check.accepted),
    command: check.command || "",
    returncode: check.returncode,
    error: displayMessage(check.error || ""),
    stdout_tail: displayMessage(check.stdout_tail || ""),
    stderr_tail: displayMessage(check.stderr_tail || "")
  };
}

function SourceCheckDetail({ event }) {
  if (!event || !event.source_check) return null;
  const detail = sourceCheckDetail(event);
  const output = detail.error || detail.stderr_tail || detail.stdout_tail || "";
  return h(
    "div",
    { className: `source-check-detail ${detail.accepted ? "ready" : "attention"}` },
    h("span", null, detail.accepted ? "Source check accepted" : "Source check needs attention"),
    detail.command ? h("code", null, detail.command) : null,
    output ? h("p", null, output) : null,
    detail.returncode === null || detail.returncode === undefined
      ? null
      : h("small", null, `exit ${detail.returncode}`)
  );
}

function buildCaseFile(snapshot, receiptHistory, context = {}) {
  const rows = (snapshot && snapshot.rows) || [];
  const receipts = ((receiptHistory && receiptHistory.receipts) || []).slice(0, 8);
  const trace = context.traceContext || {};
  const report = context.reportContext || {};
  const health = context.healthContext || {};
  const preflight = context.preflightEvent || null;
  const runHistory = context.runHistoryContext || {};
  const claimSupport = context.claimSupportContext || {};
  const sourceList = context.sourceListContext || {};
  const sourceAction = context.sourceActionEvent || null;
  const sourceImport = context.sourceImportEvent || null;
  const sourceEdit = context.sourceEditEvent || null;
  const latestWrite = context.writeReceiptEvent || null;
  const latestRefreshResults = Array.isArray(context.refreshResults) ? context.refreshResults.filter(Boolean) : [];
  const projectEntry = context.projectEntry || {};
  const intakeDraft = context.intakeDraft || null;
  const sourceImportDraft = context.sourceImportDraft || null;
  const sourceEditDraft = context.sourceEditDraft || null;
  const pendingIntakeFields = intakeChangedFields(intakeDraft);
  const sourceImportStarted = Boolean(
    sourceImportDraft &&
      (String(sourceImportDraft.filename || "").trim() ||
        String(sourceImportDraft.body || "").trim())
  );
  const pendingSourceEditFields = sourceChangedFields(sourceEditDraft);
  const intakeRefSummary = projectEntry.intake_ref_summary || {};
  const commandQueue = commandCockpitItems({
    snapshot,
    selectedRow: context.selectedRow || null,
    traceContext: trace,
    reportContext: report,
    healthContext: health,
    claimSupportContext: claimSupport
  }).map((item) => ({
    label: item.label,
    source: item.source || "",
    row_label: item.rowLabel || "",
    command: item.command
  }));
  return {
    schema: "ztare-forensic-workbench-case-file-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    intake: snapshot.intake,
    case_key: projectEntryKey(snapshot),
    readiness: snapshot.readiness,
    report_status: snapshot.report_status,
    status_reasons: snapshot.status_reasons || [],
    generated_from: snapshot.served_from === "local_api" ? "local_api_snapshot" : "static_snapshot",
    project_context: {
      project_dir: projectEntry.project_dir || snapshot.project_source || "",
      intake_source: projectEntry.intake_source || snapshot.intake_source || "",
      intake_editable: projectEntry.intake_editable !== false,
      intake_error: projectEntry.intake_error || "",
      intake_ref_summary: {
        total: intakeRefSummary.total || 0,
        present: intakeRefSummary.present || 0,
        missing: intakeRefSummary.missing || 0,
        unsafe: intakeRefSummary.unsafe || 0,
        external: intakeRefSummary.external || 0
      },
      report_contract: projectEntry.report_contract || "",
      latest_review: projectEntry.latest_review || snapshot.latest_review_artifact || "",
      latest_row_action: projectEntry.latest_row_action || snapshot.latest_row_action_artifact || "",
      latest_intake_edit: projectEntry.latest_intake_edit || snapshot.latest_intake_edit_artifact || "",
      latest_source_import: projectEntry.latest_source_import || "",
      latest_source_edit: projectEntry.latest_source_edit || "",
      latest_source_action: projectEntry.latest_source_action || "",
      latest_case_file_write: projectEntry.latest_case_file_write || ""
    },
    live_context: {
      trace: {
        schema: trace.schema || "",
        readiness: trace.readiness || "",
        trace_command: trace.trace_command || "",
        next_commands: (trace.next_commands || []).slice(0, 6),
        carrier_chain: (trace.carrier_chain || []).slice(0, 8),
        plan_preview: {
          schema: (trace.plan_preview || {}).schema || "",
          status: (trace.plan_preview || {}).status || "",
          recommended_first_command: (trace.plan_preview || {}).recommended_first_command || "",
          model_calls_before_confirmation: (trace.plan_preview || {}).model_calls_before_confirmation
        }
      },
      report_contract: {
        schema: report.schema || "",
        report_scope: report.report_scope || "",
        intake: report.intake || "",
        case_key: report.case_key || "",
        status: report.status || "",
        status_reasons: report.status_reasons || [],
        report_support_contract: report.report_support_contract || "",
        command: report.command || "",
        synthesis_input_binding: {
          schema: (report.synthesis_input_binding || {}).schema || "",
          status: (report.synthesis_input_binding || {}).status || "",
          reason: (report.synthesis_input_binding || {}).reason || "",
          artifact_count: (report.synthesis_input_binding || {}).artifact_count
        }
      },
      health: {
        schema: health.schema || "",
        kernel: {
          summary: ((health.kernel || {}).summary) || {},
          attention_components: ((health.kernel || {}).attention_components || []).slice(0, 8)
        },
        action_intelligence: {
          counts: ((health.action_intelligence || {}).counts) || {},
          issues: ((health.action_intelligence || {}).issues || []).slice(0, 8),
          recommendations: ((health.action_intelligence || {}).recommendations || []).slice(0, 8),
          recommendation_counts: ((health.action_intelligence || {}).recommendation_counts) || {},
          recommendations_generated_at: ((health.action_intelligence || {}).recommendations_generated_at) || "",
          recommendations_source_path: ((health.action_intelligence || {}).recommendations_source_path) || "",
          source_paths: ((health.action_intelligence || {}).source_paths) || {}
        }
      },
      preflight_result: preflight
        ? {
            schema: preflight.schema || "",
            command: preflight.command || "",
            returncode: preflight.returncode,
            accepted: Boolean(preflight.accepted),
            stdout_tail: displayMessage(preflight.stdout_tail || ""),
            stderr_tail: displayMessage(preflight.stderr_tail || ""),
            loop_admission: ((preflight.trace || {}).loop_admission) || {},
            snapshot_error: displayMessage(preflight.snapshot_error || ""),
            trace_error: displayMessage(preflight.trace_error || "")
        }
        : null,
      run_history: {
        schema: runHistory.schema || "",
        run_scope: runHistory.run_scope || "",
        intake: runHistory.intake || "",
        case_key: runHistory.case_key || "",
        summary: runHistory.summary || {},
        paths: runHistory.paths || {},
        latest_eval: runHistory.latest_eval || {},
        champion_eval: runHistory.champion_eval || {},
        recent_runs: (runHistory.recent_runs || []).slice(-8),
        synthesis_history: runHistory.synthesis_history || {}
      },
      claim_support: {
        schema: claimSupport.schema || "",
        status: claimSupport.status || "",
        accepted: Boolean(claimSupport.accepted),
        support_scope: claimSupport.support_scope || "",
        intake: claimSupport.intake || "",
        case_key: claimSupport.case_key || "",
        command: claimSupport.command || "",
        claim_count: claimSupport.claim_count || 0,
        weak_or_unsourced_count: claimSupport.weak_or_unsourced_count || 0,
        source_context_blocked_count: claimSupport.source_context_blocked_count || 0,
        errors: (claimSupport.errors || []).slice(0, 8).map(displayMessage),
        evidence_file_path: claimSupport.evidence_file_path || claimSupport.packet_path || "",
        source_index_path: claimSupport.source_index_path || "",
        source_context: (claimSupport.source_context || []).slice(0, 12)
      },
      sources: {
        schema: sourceList.schema || "",
        accepted: Boolean(sourceList.accepted),
        raw_dir: sourceList.raw_dir || "",
        source_count: ((sourceList.sources || []).length),
        sources: (sourceList.sources || []).slice(0, 16).map((source) => ({
          path: source.path || "",
          relative_raw_path: rawSourceRelative(source),
          source_type: source.source_type || "",
          chars: source.chars,
          sha256: source.sha256 || ""
        }))
      },
      latest_source_action: sourceAction
        ? {
            schema: sourceAction.schema || "",
            action: sourceAction.action || "",
            label: sourceAction.label || "",
            writes: Boolean(sourceAction.writes),
            command: sourceAction.command || "",
            returncode: sourceAction.returncode,
            accepted: Boolean(sourceAction.accepted),
            receipt_path: sourceAction.receipt_path || "",
            latest: sourceAction.latest || "",
            receipt: sourceAction.receipt || {},
            stdout_tail: displayMessage(sourceAction.stdout_tail || ""),
            stderr_tail: displayMessage(sourceAction.stderr_tail || "")
          }
        : null,
      latest_source_import: sourceImport
        ? {
            schema: sourceImport.schema || "",
            source_path: sourceImport.source_path || "",
            source_type: sourceImport.source_type || "",
            source_type_map: sourceImport.source_type_map || "",
            receipt_path: sourceImport.receipt_path || "",
            latest: sourceImport.latest || "",
            sha256: (sourceImport.receipt || {}).sha256 || "",
            receipt: sourceImport.receipt || {},
            source_check_accepted: Boolean(sourceImport.source_check && sourceImport.source_check.accepted),
            source_check: sourceCheckDetail(sourceImport)
          }
        : null,
      latest_source_edit: sourceEdit
        ? {
            schema: sourceEdit.schema || "",
            source_path: sourceEdit.source_path || "",
            relative_raw_path: sourceEdit.relative_raw_path || "",
            source_type: sourceEdit.source_type || "",
            receipt_path: sourceEdit.receipt_path || "",
            latest: sourceEdit.latest || "",
            sha256: (sourceEdit.receipt || {}).sha256 || "",
            receipt: sourceEdit.receipt || {},
            source_check_accepted: Boolean(sourceEdit.source_check && sourceEdit.source_check.accepted),
            source_check: sourceCheckDetail(sourceEdit)
          }
        : null,
      latest_write_receipt: latestWrite
        ? {
            kind: latestWrite.kind,
            row: latestWrite.row,
            snapshot_error: latestWrite.snapshotError || "",
            ledger: (latestWrite.result || {}).ledger || "",
            latest: (latestWrite.result || {}).latest || "",
            receipt: (latestWrite.result || {}).receipt || {},
            refresh_results: latestRefreshResults.map((row) => ({
              label: row.label || "",
              ok: row.ok !== false,
              error: row.error || ""
            }))
          }
        : null,
      pending_intake_edit: intakeDraft
        ? {
            path: intakeDraft.path || "",
            editable: intakeDraft.editable !== false,
            status: pendingIntakeFields.length ? "pending_unsaved" : "clean",
            changed_fields: pendingIntakeFields,
            bounded_claim: intakeDraft.bounded_claim || "",
            next_falsifier: intakeDraft.next_falsifier || "",
            notes: intakeDraft.notes || "",
            non_claims: linesFromText(intakeDraft.non_claims_text),
            source_refs: linesFromText(intakeDraft.source_refs_text),
            evidence_refs: linesFromText(intakeDraft.evidence_refs_text),
            loaded_reference_status: intakeDraft.reference_status || null
          }
        : null,
      pending_source_import: sourceImportStarted
        ? {
            status: "pending_unsaved",
            filename: sourceImportDraft.filename || "",
            source_type: sourceImportDraft.source_type || "",
            body_chars: String(sourceImportDraft.body || "").length
          }
        : null,
      pending_source_edit: sourceEditDraft && sourceEditDraft.relative_raw_path
        ? {
            status: pendingSourceEditFields.length ? "pending_unsaved" : "clean",
            changed_fields: pendingSourceEditFields,
            relative_raw_path: sourceEditDraft.relative_raw_path || "",
            source_type: sourceEditDraft.source_type || "",
            body_chars: String(sourceEditDraft.body || "").length
          }
        : null
    },
    command_queue: commandQueue,
    rows: rows.map((row) => ({
      label: row.label,
      status: displayText(row.status),
      kind: row.kind || "neutral",
      detail: row.detail || "",
      evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
    })),
    recent_receipts: receipts.map((receipt) => ({
      kind: receipt.kind,
      applied_at: receipt.applied_at,
      summary: receipt.summary,
      path: receipt.path,
      line: receipt.line,
      project: receipt.project || "",
      rubric: receipt.rubric || "",
      intake: receipt.intake || "",
      case_key: receipt.case_key || "",
      row: receipt.row || "",
      source_path: receipt.source_path || "",
      source_type: receipt.source_type || "",
      decision: receipt.decision || "",
      action: receipt.action || "",
      updated_fields: receipt.updated_fields || []
    }))
  };
}

function caseFileSummary(snapshot, receiptHistory, caseFile) {
  const blocker = activeBlocker((snapshot && snapshot.rows) || []);
  const receipts = ((receiptHistory && receiptHistory.receipts) || []).length;
  return [
    `Project: ${snapshot.project}`,
    `Readiness: ${displayText(snapshot.readiness)}`,
    `Export: ${displayText(snapshot.report_status)}`,
    `Current blocker: ${blocker ? blocker.label : "none"}`,
    `Recent receipts: ${receipts}`,
    `Command queue: ${caseFile ? caseFile.command_queue.length : 0}`,
    `Intake: ${snapshot.intake || "not recorded"}`
  ].join("\n");
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
  if (!["file", "source", "evidence", "receipt", "review"].includes(item.type)) return false;
  const value = String(item.value || "");
  if (!isPreviewableRepoPath(value) || !value.includes("/")) return false;
  const filename = value.split("/").pop() || "";
  return filename.includes(".");
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

function PendingEditsStrip({ items }) {
  if (!items || !items.length) return null;
  return h(
    "section",
    { className: "pending-edits-strip", "aria-label": "Unsaved edits" },
    h(
      "div",
      { className: "pending-edits-copy" },
      h("span", null, "Unsaved edits"),
      h("strong", null, `${items.length} pending`)
    ),
    h(
      "div",
      { className: "pending-edits-list" },
      items.map((item) => h("span", { key: item }, item))
    ),
    h("p", null, "Save the related editor before switching projects, refreshing, or reloading from disk.")
  );
}

function projectOptionLabel(project) {
  const intakeName = sourceBasename(project.intake || "");
  const parts = [intakeName ? `${project.project} / ${intakeName}` : project.project];
  if (project.intake_source) parts.push(displayText(project.intake_source));
  const refSummary = project.intake_ref_summary || {};
  if (refSummary.total) parts.push(`refs ${refSummary.present || 0}/${refSummary.total}`);
  return parts.join(" / ");
}

function projectEntryKey(entry) {
  if (!entry) return "";
  const project = String(entry.project || "").trim();
  const intake = String(entry.intake || "").trim();
  return intake ? `${project}::${intake}` : project;
}

function projectLoadParams(entryOrSnapshot) {
  if (!entryOrSnapshot) return {};
  return {
    project: entryOrSnapshot.project,
    rubric: entryOrSnapshot.rubric || entryOrSnapshot.project,
    intake: entryOrSnapshot.intake || ""
  };
}

function ProjectContextPanel({ projectEntry, snapshot, liveMode, onPreview }) {
  const intake = (projectEntry && projectEntry.intake) || snapshot.intake || "";
  const projectDir = (projectEntry && projectEntry.project_dir) || snapshot.project_source || "";
  const reportContract = (projectEntry && projectEntry.report_contract) || "";
  const latestReview = (projectEntry && projectEntry.latest_review) || snapshot.latest_review_artifact || "";
  const latestAction = (projectEntry && projectEntry.latest_row_action) || snapshot.latest_row_action_artifact || "";
  const latestIntakeEdit = (projectEntry && projectEntry.latest_intake_edit) || snapshot.latest_intake_edit_artifact || "";
  const latestSourceImport = (projectEntry && projectEntry.latest_source_import) || "";
  const latestSourceEdit = (projectEntry && projectEntry.latest_source_edit) || "";
  const latestSourceAction = (projectEntry && projectEntry.latest_source_action) || "";
  const latestCaseFileWrite = (projectEntry && projectEntry.latest_case_file_write) || "";
  const refSummary = (projectEntry && projectEntry.intake_ref_summary) || {};
  const intakeError = (projectEntry && projectEntry.intake_error) || "";
  const intakeMode = projectEntry && projectEntry.intake_editable === false ? "read-only" : "editable";
  const pathRows = [
    { label: "Intake", value: intake },
    { label: "Report contract", value: reportContract },
    { label: "Latest review", value: latestReview },
    { label: "Latest action", value: latestAction },
    { label: "Latest intake edit", value: latestIntakeEdit },
    { label: "Latest source import", value: latestSourceImport },
    { label: "Latest source edit", value: latestSourceEdit },
    { label: "Latest source action", value: latestSourceAction },
    { label: "Latest case file", value: latestCaseFileWrite }
  ];
  const renderPathRow = (item) =>
    h(
      "div",
      { className: "project-context-path", key: item.label },
      h("span", null, item.label),
      h("code", null, item.value || "none"),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          disabled: !liveMode || !item.value,
          onClick: () => onPreview && onPreview({ type: "file", value: item.value }),
          title: liveMode ? `Preview ${item.label.toLowerCase()}` : "Start the local API to preview project files"
        },
        "Preview"
      )
    );
  return h(
    "section",
    { className: "project-context-panel", "aria-label": "Project files" },
    h("div", null, h("span", null, "Project files"), h("strong", null, projectDir || "not discovered")),
    h("div", null, h("span", null, "Intake refs"), h("strong", null, refSummary.total ? `${refSummary.present || 0}/${refSummary.total} present` : "not counted")),
    h("div", { className: intakeError ? "project-context-attention" : "" }, h("span", null, "Intake check"), h("strong", null, intakeError ? displayMessage(intakeError) : "checked")),
    h("div", null, h("span", null, "Edit mode"), h("strong", null, intakeMode)),
    pathRows.map(renderPathRow)
  );
}

function ProjectSwitchboard({ projects, selectedProjectKey, snapshot, liveMode, loading, onSelect }) {
  if (!liveMode || !projects.length) return null;
  const activeKey = selectedProjectKey || projectEntryKey(snapshot);
  return h(
    "section",
    { className: "project-switchboard", "aria-label": "Local cases" },
    h(
      "div",
      { className: "project-switchboard-head" },
      h("span", { className: "eyebrow" }, "Local cases"),
      h("h2", null, "Open workbench state"),
      h("p", null, "Inspect available project folders before switching.")
    ),
    h(
      "div",
      { className: "project-switchboard-grid" },
      projects.map((project) => {
        const caseKey = projectEntryKey(project);
        const refSummary = project.intake_ref_summary || {};
        const intakeError = project.intake_error || "";
        const active = caseKey === activeKey;
        const intakeMode = intakeError ? "intake attention" : project.intake_editable === false ? "read-only intake" : "editable intake";
        const receiptCount = [
          project.latest_review,
          project.latest_row_action,
          project.latest_intake_edit,
          project.latest_source_import,
          project.latest_source_edit,
          project.latest_source_action,
          project.latest_case_file_write
        ].filter(Boolean).length;
        return h(
          "article",
          { key: caseKey, className: `project-tile ${active ? "active" : ""}` },
          h(
            "div",
            { className: "project-tile-main" },
            h("strong", null, project.project),
            h("small", null, project.intake || project.project_dir || "intake pending")
          ),
          h(
            "div",
            { className: "project-tile-facts" },
            h("span", null, displayText(project.intake_source || "unknown_intake_source")),
            h("span", { className: intakeError ? "attention" : "" }, intakeMode),
            h("span", null, refSummary.total ? `${refSummary.present || 0}/${refSummary.total} refs` : "refs not counted"),
            h("span", null, project.report_contract ? "report contract" : "no report contract"),
            h("span", null, receiptCount ? `${receiptCount} receipt paths` : "no recent receipts")
          ),
          intakeError ? h("p", { className: "project-tile-error" }, displayMessage(intakeError)) : null,
          h(
            "button",
            {
              type: "button",
              className: active ? "copy-button" : "copy-button primary",
              disabled: loading || active,
              onClick: () => onSelect(caseKey),
              title: active ? "This case is open" : `Open ${project.project} / ${sourceBasename(project.intake || "") || "case"}`
            },
            active ? "Open" : "Switch"
          )
        );
      })
    )
  );
}

function ProjectCreatePanel({ draft, setDraft, message, creating, liveMode, projects, onCreate }) {
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const project = String(draft.project || "").trim();
  const validProject = Boolean(project && PROJECT_SLUG_RE.test(project));
  const duplicateProject = projectSlugExists(projects, project);
  const hasRequiredFields = Boolean(
    String(draft.task || "").trim()
      && String(draft.bounded_claim || "").trim()
      && String(draft.next_falsifier || "").trim()
  );
  const canCreate = Boolean(liveMode && !creating && validProject && !duplicateProject && hasRequiredFields);
  const createTitle = !liveMode
    ? "Start the local API to create a project"
    : duplicateProject
      ? "This project already exists. Open it from Local cases."
      : !validProject
        ? "Use letters, numbers, dot, dash, or underscore"
        : !hasRequiredFields
          ? "Enter task, bounded claim, and next falsifier"
          : "Create local project and intake";
  const projectNote = duplicateProject
    ? "Existing case. Open it from Local cases."
    : project && !validProject
      ? "Use letters, numbers, dot, dash, or underscore."
      : "";
  return h(
    "section",
    { className: "project-create-panel", "aria-label": "Create case" },
    h(
      "div",
      { className: "project-create-head" },
      h("span", { className: "eyebrow" }, "New case"),
      h("h2", null, "Create a bounded project"),
      h("p", null, message || "Create local project folders and an intake before running checks.")
    ),
    h(
      "div",
      { className: "project-create-grid" },
      h(
        "label",
        null,
        h("span", null, "Project slug"),
        h("input", { value: draft.project, onInput: (event) => setField("project", event.target.value), placeholder: "my_project" }),
        projectNote ? h("small", { className: "project-create-note" }, projectNote) : null
      ),
      h("label", null, h("span", null, "Task"), h("input", { value: draft.task, onInput: (event) => setField("task", event.target.value), placeholder: "Check whether..." })),
      h("label", null, h("span", null, "Bounded claim"), h("textarea", { value: draft.bounded_claim, onInput: (event) => setField("bounded_claim", event.target.value), rows: 2 })),
      h("label", null, h("span", null, "Next falsifier"), h("textarea", { value: draft.next_falsifier, onInput: (event) => setField("next_falsifier", event.target.value), rows: 2 })),
      h("label", null, h("span", null, "Notes"), h("textarea", { value: draft.notes, onInput: (event) => setField("notes", event.target.value), rows: 2, placeholder: "optional context" })),
      h("label", null, h("span", null, "Source refs"), h("textarea", { value: draft.source_refs_text, onInput: (event) => setField("source_refs_text", event.target.value), rows: 2, placeholder: "one path per line" })),
      h("label", null, h("span", null, "Evidence refs"), h("textarea", { value: draft.evidence_refs_text, onInput: (event) => setField("evidence_refs_text", event.target.value), rows: 2, placeholder: "one path per line" })),
      h("label", null, h("span", null, "Non-claims"), h("textarea", { value: draft.non_claims_text, onInput: (event) => setField("non_claims_text", event.target.value), rows: 2, placeholder: "one caveat per line" }))
    ),
    h(
      "div",
      { className: "project-create-actions" },
      h(
        "button",
        {
          type: "button",
          className: "snapshot-link",
          disabled: !canCreate,
          onClick: onCreate,
          title: createTitle
        },
        creating ? "Creating" : "Create case"
      )
    )
  );
}

function SourceImportPanel({ draft, setDraft, message, importing, event, liveMode, sourceList, onImport, onPreview, onAddToIntake }) {
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const filename = String(draft.filename || "").trim();
  const hasBody = Boolean(String(draft.body || "").trim());
  const validFilename = Boolean(filename && SOURCE_IMPORT_FILENAME_RE.test(filename));
  const duplicateFilename = sourceFilenameExists(sourceList, filename);
  const canImport = Boolean(liveMode && !importing && validFilename && hasBody && !duplicateFilename);
  const importTitle = !liveMode
    ? "Start the local API to import a source"
    : duplicateFilename
      ? "This filename already exists. Open it in Raw sources to edit."
      : !validFilename
        ? "Use a flat .md or .txt filename"
        : !hasBody
        ? "Enter a filename and source text"
        : "Write source file and receipt";
  const filenameNote = duplicateFilename
    ? "Existing source. Open it in Raw sources to edit."
    : filename && !validFilename
      ? "Use a flat .md or .txt filename."
      : "";
  return h(
    "section",
    { className: "source-import-panel", "aria-label": "Import source" },
    h(
      "div",
      { className: "source-import-head" },
      h("span", { className: "eyebrow" }, "Source import"),
      h("h2", null, "Add a raw source"),
      h("p", null, message || "Write one source file into this project, record a receipt, then check source readiness.")
    ),
    h(
      "div",
      { className: "source-import-grid" },
      h(
        "label",
        null,
        h("span", null, "Filename"),
        h("input", { value: draft.filename, onInput: (inputEvent) => setField("filename", inputEvent.target.value), placeholder: "source_note.md" }),
        filenameNote ? h("small", { className: "source-import-note" }, filenameNote) : null
      ),
      h(
        "label",
        null,
        h("span", null, "Source type"),
        h(
          "select",
          { value: draft.source_type, onChange: (inputEvent) => setField("source_type", inputEvent.target.value) },
          SOURCE_TYPES.map((value) =>
            h("option", { key: value, value }, displayText(value))
          )
        )
      ),
      h("label", { className: "source-import-body" }, h("span", null, "Text"), h("textarea", { value: draft.body, onInput: (inputEvent) => setField("body", inputEvent.target.value), rows: 5 }))
    ),
    h(
      "div",
      { className: "source-import-actions" },
      h(
        "button",
        {
          type: "button",
          className: "snapshot-link",
          disabled: !canImport,
          onClick: onImport,
          title: importTitle
        },
        importing ? "Importing" : "Import source"
      ),
      event
        ? h(
            "div",
            { className: "source-import-result" },
            h("strong", null, event.source_path || "source imported"),
            h("small", null, `${displayText(event.source_type || "source")} / ${(event.source_check && event.source_check.accepted) ? "check accepted" : "check attention"}`),
            h(SourceCheckDetail, { event }),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode || !event.source_path,
                onClick: () => onPreview && onPreview({ type: "file", value: event.source_path }),
                title: "Preview imported source"
              },
              "Preview"
            ),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode || !event.source_path,
                onClick: () => onAddToIntake && onAddToIntake(event.source_path),
                title: "Stage this source path in the intake draft"
              },
              "Add to intake draft"
            )
          )
        : null
    )
  );
}

function RawSourceManagerPanel({ sourceList, draft, setDraft, message, editing, event, liveMode, onOpenSource, onSave, onReload, onPreview }) {
  const sources = (sourceList && sourceList.sources) || [];
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const changedFields = sourceChangedFields(draft);
  const hasLoadedSource = Boolean(draft && draft.original && draft.relative_raw_path);
  const canSave = Boolean(liveMode && hasLoadedSource && changedFields.length && draft.body && draft.body.trim() && !editing);
  return h(
    "section",
    { className: "raw-source-manager", "aria-label": "Raw sources" },
    h(
      "div",
      { className: "raw-source-head" },
      h("span", { className: "eyebrow" }, "Raw sources"),
      h("h2", null, "Inspect and edit sources"),
      h("p", null, message || "Open a project source, edit the text or type, then save a receipt-backed file change.")
    ),
    h(
      "div",
      { className: "raw-source-list" },
      h(
        "div",
        { className: "raw-source-list-head" },
        h("span", null, `${sources.length} files`),
        h(
          "button",
          {
            type: "button",
            className: "copy-button",
            disabled: !liveMode,
            onClick: onReload,
            title: liveMode ? "Reload source list" : "Start the local API to load raw sources"
          },
          "Reload"
        )
      ),
      sources.length
        ? sources.slice(0, 12).map((row) =>
            h(
              "div",
              { className: "raw-source-row", key: rawSourceRelative(row) || row.path },
              h("div", null, h("strong", null, rawSourceRelative(row) || row.path || "source"), h("small", null, `${displayText(row.source_type || "untyped")} / ${row.chars || 0} chars`)),
              h(
                "div",
                { className: "raw-source-row-actions" },
                h(
                  "button",
                  {
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode || !rawSourceRelative(row),
                    onClick: () => onOpenSource(rawSourceRelative(row)),
                    title: "Open source for editing"
                  },
                  "Edit"
                ),
                h(
                  "button",
                  {
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode || !row.path,
                    onClick: () => onPreview && onPreview({ type: "file", value: row.path }),
                    title: "Preview source file"
                  },
                  "Preview"
                )
              )
            )
          )
        : h("p", null, liveMode ? "No raw sources loaded yet." : "Start the local API to inspect raw sources.")
    ),
    h(
      "div",
      { className: "raw-source-editor" },
      h(
        "div",
        { className: "raw-source-editor-fields" },
        h(
          "label",
          null,
          h("span", null, "File"),
          h("input", {
            value: draft.relative_raw_path,
            disabled: true,
            placeholder: "Open a source from the list",
            title: "Source paths are selected from the list. Use Source import to add a new file."
          })
        ),
        h(
          "label",
          null,
          h("span", null, "Source type"),
          h(
            "select",
            { value: draft.source_type, onChange: (inputEvent) => setField("source_type", inputEvent.target.value) },
            SOURCE_TYPES.map((value) => h("option", { key: value, value }, displayText(value)))
          )
        ),
        h("label", { className: "raw-source-body" }, h("span", null, "Text"), h("textarea", { value: draft.body, onInput: (inputEvent) => setField("body", inputEvent.target.value), rows: 8, placeholder: "Open a source to edit it here." }))
      ),
      h(
        "section",
        { className: `raw-source-pending ${changedFields.length ? "changed" : ""}`, "aria-label": "Pending source write" },
        h("span", null, "Pending write"),
        h("strong", null, changedFields.length ? `${changedFields.length} changed field${changedFields.length === 1 ? "" : "s"}` : "No changes"),
        h("p", null, changedFields.length ? changedFields.map(displayFieldName).join(", ") : "Open a source and edit text or type before writing a receipt."),
        h("code", null, draft.relative_raw_path ? `target=${draft.relative_raw_path}` : "target=none")
      ),
      h(
        "div",
        { className: "raw-source-save" },
        h(
          "button",
          {
            type: "button",
            className: "snapshot-link",
            disabled: !canSave,
            onClick: onSave,
            title: canSave ? "Save source file and write a receipt" : "Open a source and make a change before saving"
          },
          editing ? "Saving" : "Save source"
        ),
        event
          ? h(
              "div",
              { className: "raw-source-result" },
              h("strong", null, event.source_path || "source edited"),
              h("small", null, `${displayText(event.source_type || "source")} / ${(event.source_check && event.source_check.accepted) ? "check accepted" : "check attention"}`),
              h(SourceCheckDetail, { event })
            )
          : null
      )
    )
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

function sourceDraftFields(draft) {
  if (!draft) return {};
  return {
    source_type: draft.source_type || "",
    body: draft.body || ""
  };
}

function sourceChangedFields(draft) {
  if (!draft || !draft.original) return [];
  const current = sourceDraftFields(draft);
  const original = sourceDraftFields(draft.original);
  return Object.keys(current).filter((key) => current[key] !== original[key]);
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

function ReceiptHistoryPanel({ history, message, liveMode, onPreview }) {
  const receipts = (history && history.receipts) || [];
  const latest = receipts[0] && receipts[0].applied_at ? receipts[0].applied_at : "none";
  const paths = (history && history.paths) || {};
  const ledgerCount = Object.values(paths).filter(Boolean).length;

  return h(
    "section",
    { className: "receipt-history", "aria-label": "Receipt history" },
    h(
      "div",
      { className: "receipt-history-head" },
      h("span", { className: "eyebrow" }, "Receipts"),
      h("h2", null, "Receipt history"),
      h("p", null, message || (liveMode ? "Recent project writes from the local receipt ledgers." : "Start the local API to read receipt ledgers."))
    ),
    h(
      "div",
      { className: "receipt-history-stats" },
      h("div", null, h("span", null, "Recent"), h("strong", null, String(receipts.length))),
      h("div", null, h("span", null, "Latest"), h("strong", null, displayText(latest))),
      h("div", null, h("span", null, "Ledgers"), h("strong", null, String(ledgerCount)))
    ),
    h(
      "div",
      { className: "receipt-history-list" },
      receipts.length
        ? receipts.map((item) => {
            const artifactPath = receiptArtifactPath(item);
            const previewableArtifact = isPreviewableRepoPath(artifactPath);
            const changedSummary = receiptChangeSummary(item, item.kind);
            const caseSummary = receiptCaseSummary(item);
            return h(
              "article",
              { className: `receipt-history-row ${item.kind || "receipt"}`, key: `${item.kind}:${item.path}:${item.line}` },
              h(
                "div",
                { className: "receipt-row-main" },
                h("strong", null, displayText(item.kind || "receipt")),
                h("small", null, item.applied_at || `line ${item.line || "?"}`),
                h("p", null, item.summary || "Receipt recorded.")
              ),
              h(
                "div",
                { className: "receipt-row-meta" },
                item.row ? h("span", null, item.row) : null,
                caseSummary ? h("span", null, caseSummary) : null,
                changedSummary ? h("span", null, changedSummary) : null,
                artifactPath ? h("span", null, artifactPath) : null
              ),
              h(
                "div",
                { className: "receipt-row-actions" },
                h("code", null, `${item.path || "no ledger"}${item.line ? `:${item.line}` : ""}`),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !liveMode || !item.path,
                    onClick: () => onPreview && onPreview({ type: "receipt", value: item.path }),
                    title: liveMode ? "Preview the receipt ledger" : "Start the local API to preview ledgers"
                  },
                  "Preview ledger"
                ),
                h(
                  "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !previewableArtifact,
                      onClick: () => onPreview && onPreview({ type: "file", value: artifactPath }),
                      title: previewFileTitle(liveMode, previewableArtifact)
                    },
                    "Preview file"
                  ),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !item.path,
                    onClick: () => copyText(item.path),
                    title: "Copy ledger path"
                  },
                  "Copy path"
                )
              )
            );
          })
        : h("p", null, liveMode ? "No receipt rows found for this project." : "Receipt history is available in live mode.")
    )
  );
}

function TraceConsolePanel({ traceContext, message, liveMode, onPreviewSource }) {
  const kernel = (traceContext && traceContext.kernel_entry) || {};
  const plan = (traceContext && traceContext.plan_preview) || {};
  const surfaces = (traceContext && traceContext.surfaces) || {};
  const carrierRows = (traceContext && traceContext.carrier_chain) || [];
  const planRows = plan.dependency_order || [];
  const graphRows = (traceContext && traceContext.graph_carriers) || [];
  const nextCommands = (traceContext && traceContext.next_commands) || [];
  const sourcePaths = [
    surfaces.source_index_receipt_path ? { label: "Source receipt", value: surfaces.source_index_receipt_path } : null,
    surfaces.compile_provenance_path ? { label: "Compile provenance", value: surfaces.compile_provenance_path } : null
  ].filter(Boolean);
  const status = (traceContext && traceContext.readiness) || "loading";

  return h(
    "section",
    { className: `trace-console ${kernel.can_enter_kernel ? "ready" : "attention"}`, "aria-label": "Autoresearch trace console" },
    h(
      "div",
      { className: "trace-summary" },
      h("span", { className: "eyebrow" }, "Trace"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Live autoresearch trace for this project, summarized from the local CLI."
            : "Start the local API to inspect the live autoresearch trace.")
      )
    ),
    h(
      "div",
      { className: "trace-metrics" },
      h("div", null, h("span", null, "Run check"), h("strong", null, displayText(kernel.status || "unknown"))),
      h("div", null, h("span", null, "Can run"), h("strong", null, kernel.can_enter_kernel ? "yes" : "no")),
      h("div", null, h("span", null, "Evidence"), h("strong", null, displayText(surfaces.evidence_status || "unknown"))),
      h("div", null, h("span", null, "Plan"), h("strong", null, displayText(plan.status || "unknown")))
    ),
    h(
      "div",
      { className: "trace-body" },
      h(
        "div",
        { className: "trace-section trace-commands" },
        h("span", null, "Commands"),
        h("code", null, (traceContext && traceContext.trace_command) || "No trace command loaded."),
        nextCommands.length
          ? nextCommands.slice(0, 3).map((command, index) =>
              h(
                "button",
                {
                  className: "copy-button",
                  type: "button",
                  key: `${index}:${command}`,
                  onClick: () => copyText(command),
                  title: "Copy trace next command"
                },
                index === 0 ? "Copy first command" : `Copy command ${index + 1}`
              )
            )
          : h("p", null, "No next commands surfaced.")
      ),
      h(
        "div",
        { className: "trace-section" },
        h("span", null, "Plan steps"),
        planRows.length
          ? planRows.map((row) =>
              h(
                "div",
                { className: `trace-plan-row ${row.model_calls ? "model" : "local"}`, key: row.id || row.description },
                h("strong", null, displayText(row.id || "step")),
                h("small", null, row.model_calls ? "model call" : "local"),
                h("p", null, row.description || displayText(row.status || "pending")),
                row.command
                  ? h(
                      "button",
                      {
                        className: "copy-button",
                        type: "button",
                        onClick: () => copyText(row.command),
                        title: "Copy plan command"
                      },
                      "Copy"
                    )
                  : null
              )
            )
          : h("p", null, "No plan steps surfaced.")
      ),
      h(
        "div",
        { className: "trace-section trace-carriers" },
        h("span", null, "Carrier chain"),
        carrierRows.length
          ? carrierRows.slice(0, 8).map((row) =>
              h(
                "div",
                { className: `trace-carrier-row ${row.blocking ? "attention" : "ready"}`, key: row.surface },
                h("strong", null, displayText(row.surface || "surface")),
                h("small", null, displayText(row.status || "unknown")),
                row.next_command
                  ? h(
                      "button",
                      {
                        className: "copy-button",
                        type: "button",
                        onClick: () => copyText(row.next_command),
                        title: "Copy carrier next command"
                      },
                      "Copy"
                    )
                  : null
              )
            )
          : h("p", null, "No carrier chain loaded.")
      ),
      h(
        "div",
        { className: "trace-section" },
        h("span", null, "Trace files"),
        sourcePaths.length
          ? sourcePaths.map((item) =>
              h(
                "div",
                { className: "trace-file-row", key: item.label },
                h("strong", null, item.label),
                h("code", null, item.value),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !liveMode,
                    onClick: () => onPreviewSource && onPreviewSource({ type: "file", value: item.value }),
                    title: liveMode ? "Preview trace source file" : "Start the local API to preview files"
                  },
                  "Preview"
                )
              )
            )
          : h("p", null, "No source file paths surfaced.")
      ),
      h(
        "div",
        { className: "trace-section trace-graphs" },
        h("span", null, "Graphs"),
        graphRows.length
          ? graphRows.map((row) =>
              h(
                "div",
                { className: "trace-graph-row", key: row.graph_id || row.graph_kind },
                h("strong", null, displayText(row.graph_kind || "graph")),
                h("small", null, `${row.node_count || 0} nodes / ${row.edge_count || 0} edges`),
                (row.source_artifacts || []).slice(0, 1).map((path) => h("code", { key: path }, path))
              )
            )
          : h("p", null, "No graph carriers surfaced.")
      )
    )
  );
}

function PreflightRunPanel({ traceContext, event, message, running, liveMode, onRun }) {
  const kernel = (traceContext && traceContext.kernel_entry) || {};
  const loop = (event && event.trace && event.trace.loop_admission) || (traceContext && traceContext.loop_admission) || {};
  const command = kernel.preflight_command || (event && event.command) || "";
  const canRun = Boolean(liveMode && command && !running);
  const accepted = event && event.accepted;
  const status = running ? "running" : event ? (accepted ? "accepted" : "blocked") : command ? "ready" : "missing";
  const outputTail = event ? displayMessage(event.stderr_tail || event.stdout_tail || "").trim() : "";
  const snapshotNote = event && event.snapshot_error ? `Snapshot refresh failed: ${displayMessage(event.snapshot_error)}` : "";
  const traceNote = event && event.trace_error ? `Trace refresh failed: ${displayMessage(event.trace_error)}` : "";

  return h(
    "section",
    { className: `preflight-run-panel ${accepted ? "ready" : event ? "attention" : ""}`, "aria-label": "Preflight action" },
    h(
      "div",
      { className: "preflight-run-summary" },
      h("span", { className: "eyebrow" }, "Preflight"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Run the local preflight only. This checks launch inputs and writes the normal loop-admission receipt; it does not start a model run."
            : "Start the local API to run preflight from the workbench.")
      )
    ),
    h(
      "div",
      { className: "preflight-run-command" },
      h("span", null, "Command"),
      h("code", null, command || "No preflight command surfaced for this case."),
      h(
        "div",
        { className: "preflight-run-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            disabled: !canRun,
            onClick: onRun,
            title: canRun ? "Run local preflight only" : "Preflight requires live mode and a surfaced command"
          },
          running ? "Running" : "Run preflight"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !command,
            onClick: () => command && copyText(command),
            title: "Copy preflight command"
          },
          "Copy"
        )
      )
    ),
    h(
      "div",
      { className: "preflight-run-facts" },
      h("div", null, h("span", null, "Exit"), h("strong", null, event ? String(event.returncode) : "not run")),
      h("div", null, h("span", null, "Accepted"), h("strong", null, event ? (accepted ? "yes" : "no") : "not run")),
      h("div", null, h("span", null, "Receipts"), h("strong", null, String(loop.receipt_count ?? 0))),
      h("div", null, h("span", null, "Hash check"), h("strong", null, loop.intake_hash_verified === undefined ? "unknown" : loop.intake_hash_verified ? "verified" : "not verified"))
    ),
    outputTail || snapshotNote || traceNote
      ? h(
          "div",
          { className: "preflight-run-output" },
          h("span", null, "Result"),
          snapshotNote ? h("p", null, snapshotNote) : null,
          traceNote ? h("p", null, traceNote) : null,
          outputTail ? h("pre", null, outputTail) : null
        )
      : null
  );
}

function RunHistoryPanel({ runHistory, message, liveMode, onPreview }) {
  const summary = (runHistory && runHistory.summary) || {};
  const latest = (runHistory && runHistory.latest_eval) || {};
  const synthesis = (runHistory && runHistory.synthesis_history) || {};
  const paths = (runHistory && runHistory.paths) || {};
  const recentRuns = (runHistory && runHistory.recent_runs) || [];
  const runScope = displayText((runHistory && runHistory.run_scope) || "project_run_history");
  const selectedCase = (runHistory && (runHistory.case_key || runHistory.intake)) || "";
  const gaps = latest.evidence_gaps || [];
  const patterns = [
    ...(synthesis.recurring_failures || []).map((text) => ({ label: "Failure", text })),
    ...(synthesis.major_pivots || []).map((text) => ({ label: "Pivot", text })),
    ...(synthesis.cross_run_patterns || []).map((text) => ({ label: "Pattern", text }))
  ].slice(0, 6);

  return h(
    "section",
    { className: "run-history-panel", "aria-label": "Run history and verdict" },
    h(
      "div",
      { className: "run-history-summary" },
      h("span", { className: "eyebrow" }, "Run history"),
      h("h2", null, summary.latest_score === undefined || summary.latest_score === null ? "No scored run" : `Score ${summary.latest_score}`),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Latest verdict state from project run history and evaluation files."
            : "Start the local API to inspect run history.")
      )
    ),
    h(
      "div",
      { className: "run-history-facts" },
      h("div", null, h("span", null, "Rows"), h("strong", null, String(summary.run_rows || 0))),
      h("div", null, h("span", null, "Best"), h("strong", null, summary.best_score === undefined || summary.best_score === null ? "none" : String(summary.best_score))),
      h("div", null, h("span", null, "Gaps"), h("strong", null, String(summary.latest_evidence_gap_count || 0))),
      h("div", null, h("span", null, "Run"), h("strong", null, summary.latest_run_id ? `${summary.latest_run_id}/${summary.latest_iteration ?? 0}` : "none")),
      h("div", null, h("span", null, "Scope"), h("strong", null, runScope)),
      h("div", null, h("span", null, "Selected case"), h("strong", null, selectedCase || "not bound"))
    ),
    h(
      "div",
      { className: "run-history-verdict" },
      h("span", null, "Weakest point"),
      h("p", null, latest.weakest_point || summary.latest_weakest_point || "No latest weakest point recorded."),
      h(
        "div",
        { className: "run-history-paths" },
        ["eval_history", "latest_eval", "champion_eval", "synthesis_history"].map((key) =>
          h(
            "button",
            {
              key,
              type: "button",
              className: "copy-button",
              disabled: !liveMode || !paths[key],
              onClick: () => paths[key] && onPreview && onPreview({ type: "file", value: paths[key] }),
              title: paths[key] ? `Preview ${paths[key]}` : "No backing file recorded"
            },
            displayText(key)
          )
        )
      )
    ),
    h(
      "div",
      { className: "run-history-runs" },
      h("span", null, "Recent runs"),
      recentRuns.length
        ? recentRuns.slice(-5).reverse().map((row) =>
            h(
              "div",
              { className: "run-history-row", key: `${row.run_id}:${row.iteration}:${row.timestamp}` },
              h("strong", null, `Score ${row.score ?? "none"}`),
              h("small", null, `${row.run_id || "run"} / iter ${row.iteration ?? 0}`),
              h("p", null, row.weakest_point || "No weakest point recorded."),
              (row.artifact_refs || []).slice(0, 2).map((path) =>
                h(
                  "button",
                  {
                    key: path,
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode,
                    onClick: () => onPreview && onPreview({ type: "file", value: path }),
                    title: `Preview ${path}`
                  },
                  "Artifact"
                )
              )
            )
          )
        : h("p", null, "No run-history rows found for this project.")
    ),
    h(
      "div",
      { className: "run-history-patterns" },
      h("span", null, "Verdict pressure"),
      gaps.length
        ? gaps.slice(0, 3).map((gap) =>
            h(
              "div",
              { className: "run-history-gap", key: `${gap.target}:${gap.severity}` },
              h("strong", null, gap.target || "Evidence gap"),
              h("small", null, displayText(gap.severity || "gap")),
              h("p", null, gap.description || gap.required_surface || "No gap detail recorded.")
            )
          )
        : patterns.length
          ? patterns.map((item) =>
              h(
                "div",
                { className: "run-history-gap", key: `${item.label}:${item.text}` },
                h("strong", null, item.label),
                h("p", null, item.text)
              )
            )
          : h("p", null, "No evidence gaps or synthesis patterns surfaced.")
    )
  );
}

function ClaimSupportPanel({ claimSupport, message, liveMode, onPreview }) {
  const status = (claimSupport && claimSupport.status) || "loading";
  const errors = (claimSupport && claimSupport.errors) || [];
  const sources = (claimSupport && claimSupport.source_context) || [];
  const rows = (claimSupport && claimSupport.rows) || [];
  const command = (claimSupport && claimSupport.command) || "";
  const evidenceFilePath = (claimSupport && (claimSupport.evidence_file_path || claimSupport.packet_path)) || "";
  const sourceIndexPath = (claimSupport && claimSupport.source_index_path) || "";
  const supportScope = displayText((claimSupport && claimSupport.support_scope) || "project_compiled_evidence");
  const selectedCase = (claimSupport && (claimSupport.case_key || claimSupport.intake)) || "";
  const attention = errors.length > 0 || (claimSupport && claimSupport.accepted === false);

  return h(
    "section",
    { className: `claim-support-panel run-history-panel ${attention ? "attention" : "ready"}`, "aria-label": "Claim support audit" },
    h(
      "div",
      { className: "run-history-summary" },
      h("span", { className: "eyebrow" }, "Claim support"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Support summary loaded from the local project claim-support audit."
            : "Start the local API to inspect claim-support state.")
      )
    ),
    h(
      "div",
      { className: "run-history-facts" },
      h("div", null, h("span", null, "Claims"), h("strong", null, String((claimSupport && claimSupport.claim_count) || 0))),
      h("div", null, h("span", null, "Weak/unsourced"), h("strong", null, String((claimSupport && claimSupport.weak_or_unsourced_count) || 0))),
      h("div", null, h("span", null, "Source blockers"), h("strong", null, String((claimSupport && claimSupport.source_context_blocked_count) || 0))),
      h("div", null, h("span", null, "Sources"), h("strong", null, String(sources.length))),
      h("div", null, h("span", null, "Scope"), h("strong", null, supportScope)),
      h("div", null, h("span", null, "Selected case"), h("strong", null, selectedCase || "not bound"))
    ),
    h(
      "div",
      { className: "run-history-verdict" },
      h("span", null, "Audit result"),
      errors.length
        ? errors.slice(0, 4).map((error) => h("p", { key: error }, displayMessage(error)))
        : h("p", null, rows.length ? `${rows.length} support rows loaded.` : "No weak or unsourced support rows surfaced."),
      h(
        "div",
        { className: "run-history-paths" },
        [
          { label: "Evidence file", path: evidenceFilePath },
          { label: "Source index", path: sourceIndexPath }
        ].map((item) =>
          h(
            "button",
            {
              key: item.label,
              type: "button",
              className: "copy-button",
              disabled: !liveMode || !item.path,
              onClick: () => item.path && onPreview && onPreview({ type: "file", value: item.path }),
              title: item.path ? `Preview ${item.path}` : "No backing file recorded"
            },
            item.label
          )
        )
      )
    ),
    h(
      "div",
      { className: "run-history-runs" },
      h("span", null, "Source context"),
      sources.length
        ? sources.slice(0, 5).map((source) =>
            h(
              "div",
              { className: "run-history-row", key: source.source_id || source.path },
              h("strong", null, source.source_id || source.relative_raw_path || "source"),
              h("small", null, `${displayText(source.status || "unknown")} / ${displayText(source.source_type || "untyped")}`),
              h("p", null, ((source.preview || {}).text) || source.path || "No source preview recorded."),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  disabled: !liveMode || !source.path,
                  onClick: () => source.path && onPreview && onPreview({ type: "file", value: source.path }),
                  title: source.path ? `Preview ${source.path}` : "No source file recorded"
                },
                "Preview"
              )
            )
          )
        : h("p", null, "No source context loaded.")
    ),
    h(
      "div",
      { className: "run-history-patterns" },
      h("span", null, "Command"),
      h("code", null, command || "No claim-support command loaded."),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          disabled: !command,
          onClick: () => copyText(command),
          title: "Copy claim-support command"
        },
        "Copy command"
      )
    )
  );
}

function ReportContractPanel({ reportContext, message, liveMode, onPreview }) {
  const binding = (reportContext && reportContext.synthesis_input_binding) || {};
  const reasons = (reportContext && reportContext.status_reasons) || [];
  const contractPath = (reportContext && reportContext.report_support_contract) || "";
  const command = (reportContext && reportContext.command) || "";
  const schema = (reportContext && reportContext.schema) || REPORT_CONTRACT_SCHEMA;
  const status = (reportContext && reportContext.status) || "loading";
  const reportScope = displayText((reportContext && reportContext.report_scope) || "project_report_support");
  const selectedCase = (reportContext && (reportContext.case_key || reportContext.intake)) || "";
  const isBlocked = status === "blocked" || reasons.length > 0 || binding.status === "unbound";

  return h(
    "section",
    { className: `report-contract-panel ${isBlocked ? "attention" : "ready"}`, "aria-label": "Report/export contract" },
    h(
      "div",
      { className: "report-contract-summary" },
      h("span", { className: "eyebrow" }, "Report/export"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Report support contract loaded from the local API."
            : "Start the local API to inspect the report support contract.")
      )
    ),
    h(
      "div",
      { className: "report-contract-metrics" },
      h("div", null, h("span", null, "Binding"), h("strong", null, displayText(binding.status || "unknown"))),
      h("div", null, h("span", null, "Artifacts"), h("strong", null, String(binding.artifact_count ?? "none"))),
      h("div", null, h("span", null, "Current digest"), h("strong", null, shortDigest(binding.current_digest))),
      h("div", null, h("span", null, "Ledger digest"), h("strong", null, shortDigest(binding.ledger_digest))),
      h("div", null, h("span", null, "Scope"), h("strong", null, reportScope)),
      h("div", null, h("span", null, "Selected case"), h("strong", null, selectedCase || "not bound"))
    ),
    h(
      "div",
      { className: "report-contract-body" },
      h(
        "div",
        { className: "report-contract-section" },
        h("span", null, "Blockers"),
        reasons.length
          ? reasons.map((reason) => h("strong", { key: reason }, displayText(reason)))
          : h("p", null, "No report blockers surfaced.")
      ),
      h(
        "div",
        { className: "report-contract-section" },
        h("span", null, "Input binding"),
        h("p", null, binding.reason || "No binding reason loaded."),
        binding.schema ? h("code", null, binding.schema) : null
      ),
      h(
        "div",
        { className: "report-contract-section report-contract-file" },
        h("span", null, "Contract file"),
        h("code", null, contractPath || "No report contract path loaded."),
        h(
          "div",
          { className: "report-contract-actions" },
          h(
            "button",
            {
              className: "copy-button",
              type: "button",
              disabled: !liveMode || !contractPath,
              onClick: () => onPreview && onPreview({ type: "report", value: contractPath }),
              title: liveMode ? "Preview the report contract JSON" : "Start the local API to preview files"
            },
            "Preview"
          ),
          h(
            "button",
            {
              className: "copy-button",
              type: "button",
              disabled: !contractPath,
              onClick: () => copyText(contractPath),
              title: "Copy report contract path"
            },
            "Copy path"
          )
        )
      ),
      h(
        "div",
        { className: "report-contract-section report-contract-command" },
        h("span", null, "Command"),
        h("code", null, schema),
        h("code", null, command || "No report command loaded."),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !command,
            onClick: () => copyText(command),
            title: "Copy report contract command"
          },
          "Copy command"
        )
      )
    )
  );
}

function CaseExportPanel({ snapshot, receiptHistory, projectEntry, intakeDraft, sourceImportDraft, sourceEditDraft, traceContext, reportContext, healthContext, preflightEvent, sourceListContext, sourceActionEvent, sourceImportEvent, sourceEditEvent, runHistoryContext, claimSupportContext, writeReceiptEvent, refreshResults, selectedRow, liveMode, saving, saveEvent, onSave }) {
  const caseFile = buildCaseFile(snapshot, receiptHistory, {
    projectEntry,
    intakeDraft,
    sourceImportDraft,
    sourceEditDraft,
    traceContext,
    reportContext,
    healthContext,
    preflightEvent,
    sourceListContext,
    sourceActionEvent,
    sourceImportEvent,
    sourceEditEvent,
    runHistoryContext,
    claimSupportContext,
    writeReceiptEvent,
    refreshResults,
    selectedRow
  });
  const caseFileJson = JSON.stringify(caseFile, null, 2);
  const summary = caseFileSummary(snapshot, receiptHistory, caseFile);
  const rowsWithEvidence = caseFile.rows.filter((row) => row.evidence_refs.length).length;
  const writeRefreshRows = (((caseFile.live_context.latest_write_receipt || {}).refresh_results) || []).filter(Boolean);
  const writeRefreshOk = writeRefreshRows.filter((row) => row.ok !== false).length;
  const pendingIntake = caseFile.live_context.pending_intake_edit;
  const pendingSourceImport = caseFile.live_context.pending_source_import;
  const pendingSourceEdit = caseFile.live_context.pending_source_edit;
  const liveContextCount = [
    caseFile.live_context.trace.schema ||
      caseFile.live_context.trace.readiness ||
      caseFile.live_context.trace.trace_command ||
      caseFile.live_context.trace.next_commands.length ||
      caseFile.live_context.trace.carrier_chain.length,
    caseFile.live_context.report_contract.schema ||
      caseFile.live_context.report_contract.status ||
      caseFile.live_context.report_contract.report_support_contract ||
      caseFile.live_context.report_contract.command,
    caseFile.live_context.health.schema ||
      Object.keys(caseFile.live_context.health.kernel.summary || {}).length ||
      caseFile.live_context.health.kernel.attention_components.length ||
      Object.keys(caseFile.live_context.health.action_intelligence.counts || {}).length ||
      caseFile.live_context.health.action_intelligence.issues.length ||
      caseFile.live_context.health.action_intelligence.recommendations.length,
    caseFile.live_context.preflight_result,
    caseFile.live_context.sources.schema ||
      caseFile.live_context.sources.source_count ||
      caseFile.live_context.sources.raw_dir,
    caseFile.live_context.latest_source_action,
    caseFile.live_context.latest_source_import,
    caseFile.live_context.latest_source_edit,
    caseFile.live_context.latest_write_receipt,
    pendingIntake,
    pendingSourceImport,
    pendingSourceEdit,
    caseFile.live_context.run_history.schema || Object.keys(caseFile.live_context.run_history.summary || {}).length,
    caseFile.live_context.claim_support.schema || caseFile.live_context.claim_support.status
  ].filter(Boolean).length;
  const filename = caseFileDownloadName(snapshot);

  return h(
    "section",
    { className: "case-export-panel", "aria-label": "Case file export" },
    h(
      "div",
      { className: "case-export-copy" },
      h("span", { className: "eyebrow" }, "Export"),
      h("h2", null, "Case file"),
      h("p", null, "Download, copy, or save the current case file to the project workspace when the local API is running.")
    ),
    h(
      "div",
      { className: "case-export-facts" },
      h("div", null, h("span", null, "Rows"), h("strong", null, String(caseFile.rows.length))),
      h("div", null, h("span", null, "Rows with evidence"), h("strong", null, String(rowsWithEvidence))),
      h("div", null, h("span", null, "Receipts"), h("strong", null, String(caseFile.recent_receipts.length))),
      h("div", null, h("span", null, "Commands"), h("strong", null, String(caseFile.command_queue.length))),
      h("div", null, h("span", null, "Project files"), h("strong", null, caseFile.project_context.project_dir ? "included" : "not recorded")),
      h("div", null, h("span", null, "Intake mode"), h("strong", null, caseFile.project_context.intake_editable ? "editable" : "read only")),
      h("div", null, h("span", null, "Pending intake"), h("strong", null, pendingIntake ? (pendingIntake.changed_fields.length ? `${pendingIntake.changed_fields.length} fields` : "clean") : "not loaded")),
      h("div", null, h("span", null, "Pending import"), h("strong", null, pendingSourceImport ? (pendingSourceImport.status === "pending_unsaved" ? "draft" : "clean") : "not started")),
      h("div", null, h("span", null, "Pending source edit"), h("strong", null, pendingSourceEdit ? (pendingSourceEdit.changed_fields.length ? `${pendingSourceEdit.changed_fields.length} fields` : "clean") : "not loaded")),
      h("div", null, h("span", null, "Preflight"), h("strong", null, caseFile.live_context.preflight_result ? displayText(caseFile.live_context.preflight_result.accepted ? "accepted" : "blocked") : "not run")),
      h("div", null, h("span", null, "Raw sources"), h("strong", null, String(caseFile.live_context.sources.source_count || 0))),
      h("div", null, h("span", null, "Source action"), h("strong", null, caseFile.live_context.latest_source_action ? displayText(caseFile.live_context.latest_source_action.action) : "not run")),
      h("div", null, h("span", null, "Source import"), h("strong", null, caseFile.live_context.latest_source_import ? displayText(caseFile.live_context.latest_source_import.source_type) : "none")),
      h("div", null, h("span", null, "Source edit"), h("strong", null, caseFile.live_context.latest_source_edit ? displayText(caseFile.live_context.latest_source_edit.source_type) : "none")),
      h("div", null, h("span", null, "Write refresh"), h("strong", null, writeRefreshRows.length ? `${writeRefreshOk}/${writeRefreshRows.length} panels` : "not run")),
      h("div", null, h("span", null, "Run score"), h("strong", null, caseFile.live_context.run_history.summary.latest_score === undefined || caseFile.live_context.run_history.summary.latest_score === null ? "none" : String(caseFile.live_context.run_history.summary.latest_score))),
      h("div", null, h("span", null, "Claim support"), h("strong", null, displayText(caseFile.live_context.claim_support.status || "not loaded"))),
      h("div", null, h("span", null, "Advisory rows"), h("strong", null, String(caseFile.live_context.health.action_intelligence.recommendations.length || 0))),
      h("div", null, h("span", null, "Live context"), h("strong", null, String(liveContextCount))),
      h("div", null, h("span", null, "Schema"), h("strong", null, caseFile.schema)),
      h("div", null, h("span", null, "Save receipt"), h("strong", null, CASE_FILE_WRITE_SCHEMA))
    ),
    h(
      "div",
      { className: "case-export-actions" },
      h("code", null, filename),
      h("small", { className: "case-export-boundary" }, liveMode ? "Save writes the case file and receipt through the local API. Download and copy only export browser JSON." : "Start the local API to write the case file and receipt; download and copy stay in the browser."),
      h(
        "button",
        {
          className: "copy-button primary",
          type: "button",
          disabled: !liveMode || saving,
          onClick: () => onSave && onSave(caseFile),
          title: liveMode ? "Save the current case file to the project workspace" : "Start the local API to save case files"
        },
        saving ? "Saving" : "Save to workspace"
      ),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: () => downloadText(filename, caseFileJson),
          title: "Download the current case file JSON"
        },
        "Download case file"
      ),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: () => copyText(caseFileJson),
          title: "Copy case file JSON"
        },
        "Copy JSON"
      ),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: () => copyText(summary),
          title: "Copy a short case summary"
        },
        "Copy summary"
      ),
      saveEvent
        ? h(
            "small",
            { className: `case-export-save-note ${saveEvent.error ? "attention" : "ready"}` },
            saveEvent.error
              ? `Save failed: ${saveEvent.error}`
              : `Saved ${saveEvent.path || "case file"}; receipt ${saveEvent.latest || saveEvent.receipt_path || "recorded"}.`
          )
        : null
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

function SourceEvidencePanel({ snapshot, traceContext, liveMode, onPreview, setSelectedLabel, sourceActionEvent, sourceActionMessage, sourceActionRunning, onRunSourceAction }) {
  const rows = snapshot.rows || [];
  const sourceRow = rowByLabel(rows, "Source readiness") || {};
  const evidenceRow = rowByLabel(rows, "Evidence readiness") || {};
  const surfaces = (traceContext && traceContext.surfaces) || {};
  const sourceStatus = surfaces.source_index_status || sourceRow.status || "unknown";
  const evidenceStatus = surfaces.evidence_status || evidenceRow.status || "unknown";
  const outputBinding = surfaces.output_binding_status || "unknown";
  const replayStatus = surfaces.replay_status || "unknown";
  const attention = sourceRow.kind === "attention" || evidenceRow.kind === "attention";
  const files = [
    surfaces.source_index_receipt_path ? { label: "Source receipt", value: surfaces.source_index_receipt_path } : null,
    surfaces.compile_provenance_path ? { label: "Compile provenance", value: surfaces.compile_provenance_path } : null
  ].filter(Boolean);
  const commands = [
    sourceRow.command ? { label: "Source command", value: sourceRow.command, row: "Source readiness" } : null,
    evidenceRow.command ? { label: "Evidence command", value: evidenceRow.command, row: "Evidence readiness" } : null
  ].filter(Boolean);
  const readinessRows = [sourceRow, evidenceRow].filter((row) => row.label);
  const project = (snapshot && snapshot.project) || "<project>";
  const actionButtons = [
    {
      action: "source_check",
      label: "Check sources",
      command: `ztare project source-check --project ${project} --json`,
      writes: false
    },
    {
      action: "source_index",
      label: "Refresh index",
      command: `ztare project source-index --project ${project} --index-only --json`,
      writes: true
    },
    {
      action: "evidence_bind",
      label: "Bind outputs",
      command: `ztare project evidence-bind --project ${project} --json`,
      writes: true
    },
    {
      action: "evidence_replay",
      label: "Check replay",
      command: `ztare project evidence-replay --project ${project} --json`,
      writes: false
    }
  ];

  return h(
    "section",
    { className: `source-evidence-panel ${attention ? "attention" : "ready"}`, "aria-label": "Source and evidence readiness" },
    h(
      "div",
      { className: "source-evidence-summary" },
      h("span", { className: "eyebrow" }, "Sources and evidence"),
      h("h2", null, `${displayText(sourceStatus)} / ${displayText(evidenceStatus)}`),
      h("p", null, "Inspect source indexing, evidence binding, replay state, and the files behind them.")
    ),
    h(
      "div",
      { className: "source-evidence-metrics" },
      h("div", null, h("span", null, "Source index"), h("strong", null, displayText(sourceStatus))),
      h("div", null, h("span", null, "Evidence"), h("strong", null, displayText(evidenceStatus))),
      h("div", null, h("span", null, "Output binding"), h("strong", null, displayText(outputBinding))),
      h("div", null, h("span", null, "Replay"), h("strong", null, displayText(replayStatus)))
    ),
    h(
      "div",
      { className: "source-evidence-body" },
      h(
        "div",
        { className: "source-evidence-section" },
        h("span", null, "Rows"),
        readinessRows.length
          ? readinessRows.map((row) =>
              h(
                "button",
                {
                  key: row.label,
                  type: "button",
                  className: `source-evidence-row ${row.kind === "attention" ? "attention" : "ready"}`,
                  onClick: () => setSelectedLabel(row.label),
                  title: `Inspect ${row.label}`
                },
                h("strong", null, row.label),
                h("small", null, row.detail || displayText(row.status))
              )
            )
          : h("p", null, "No source/evidence rows loaded yet.")
      ),
      h(
        "div",
        { className: "source-evidence-section" },
        h("span", null, "Files"),
        files.length
          ? files.map((item) =>
              h(
                "div",
                { className: "source-evidence-file", key: item.label },
                h("strong", null, item.label),
                h("code", null, item.value),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !liveMode,
                    onClick: () => onPreview && onPreview({ type: "file", value: item.value }),
                    title: liveMode ? "Preview source/evidence file" : "Start the local API to preview files"
                  },
                  "Preview"
                )
              )
            )
          : h("p", null, "No source/evidence files loaded yet.")
      ),
      h(
        "div",
        { className: "source-evidence-section source-evidence-commands" },
        h("span", null, "Commands"),
        commands.length
          ? commands.map((item) =>
              h(
                "div",
                { className: "source-evidence-command", key: item.label },
                h("strong", null, item.label),
                h("code", null, item.value),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    onClick: () => copyText(item.value),
                    title: "Copy readiness command"
                  },
                  "Copy"
                )
              )
            )
          : h("p", null, "No source/evidence commands surfaced.")
      ),
      h(
        "div",
        { className: "source-evidence-section source-evidence-actions" },
        h("span", null, "Actions"),
        h(
          "div",
          { className: "source-evidence-action-buttons" },
          actionButtons.map((item) =>
            h(
              "div",
              { className: `source-evidence-action-card ${item.writes ? "writes" : ""}`, key: item.action },
              h(
                "button",
                {
                  className: "copy-button",
                  type: "button",
                  disabled: !liveMode || sourceActionRunning,
                  onClick: () => onRunSourceAction && onRunSourceAction(item.action),
                  title: liveMode ? item.command : "Start the local API to run source actions"
                },
                sourceActionRunning && sourceActionEvent && sourceActionEvent.action === item.action ? "Running" : item.label
              ),
              h("small", null, item.writes ? "Writes project receipt" : "Read-only check"),
              h("code", null, item.command)
            )
          )
        ),
        h("p", null, sourceActionMessage || "Run a fixed local check or source-index refresh; the command and result stay visible."),
        sourceActionEvent
          ? h(
              "div",
              { className: `source-evidence-action-result ${sourceActionEvent.accepted ? "ready" : "attention"}` },
              h("strong", null, `${sourceActionEvent.label || displayText(sourceActionEvent.action)}: ${sourceActionEvent.accepted ? "accepted" : "attention"}`),
              h("code", null, sourceActionEvent.command || "No command recorded."),
              sourceActionEvent.stdout_tail ? h("pre", null, displayMessage(sourceActionEvent.stdout_tail)) : null,
              sourceActionEvent.stderr_tail ? h("pre", null, displayMessage(sourceActionEvent.stderr_tail)) : null
            )
          : null
      )
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
  const isCommand = item.type === "command";
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
    h(
      "button",
      {
        className: "copy-button",
        type: "button",
        title: isCommand ? "Copy command" : "Copy evidence value",
        onClick: () => copyText(item.value)
      },
      isCommand ? "Copy" : "Copy value"
    )
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

function commandCockpitItems({ snapshot, selectedRow, traceContext, reportContext, healthContext, claimSupportContext }) {
  const items = [];
  const seen = new Set();
  const add = ({ label, command, source, rowLabel, priority = 50 }) => {
    const value = String(command || "").trim();
    if (!value || seen.has(value)) return;
    seen.add(value);
    items.push({ label, command: value, source, rowLabel, priority });
  };
  const rows = (snapshot && snapshot.rows) || [];
  const blocker = activeBlocker(rows);
  if (blocker) add({ label: "Current blocker", command: blocker.command, source: blocker.label, rowLabel: blocker.label, priority: 5 });
  if (selectedRow) add({ label: "Selected row", command: selectedRow.command, source: selectedRow.label, rowLabel: selectedRow.label, priority: 10 });
  const plan = (traceContext && traceContext.plan_preview) || {};
  add({ label: "Recommended first command", command: plan.recommended_first_command, source: "Trace plan", rowLabel: "Run readiness", priority: 15 });
  ((traceContext && traceContext.next_commands) || []).slice(0, 4).forEach((command, index) =>
    add({ label: index === 0 ? "Trace next command" : `Trace command ${index + 1}`, command, source: "Autoresearch trace", rowLabel: "Run readiness", priority: 20 + index })
  );
  add({ label: "Report support", command: reportContext && reportContext.command, source: "Report/export contract", rowLabel: "Report/export", priority: 30 });
  add({ label: "Claim support", command: claimSupportContext && claimSupportContext.command, source: "Claim support audit", rowLabel: "Evidence readiness", priority: 35 });
  (((healthContext && healthContext.kernel) || {}).attention_components || []).forEach((row, index) =>
    add({ label: "Run-health command", command: row.next_command, source: row.component || "Run health", rowLabel: "Run health", priority: 40 + index })
  );
  rows.forEach((row, index) => add({ label: "Row command", command: row.command, source: row.label, rowLabel: row.label, priority: 60 + index }));
  return items.sort((left, right) => left.priority - right.priority).slice(0, 8);
}

function CommandCockpit({ snapshot, selectedRow, traceContext, reportContext, healthContext, claimSupportContext, setSelectedLabel }) {
  const commands = commandCockpitItems({ snapshot, selectedRow, traceContext, reportContext, healthContext, claimSupportContext });
  const firstCommand = commands[0] || null;
  return h(
    "section",
    { className: "command-cockpit", "aria-label": "Command cockpit" },
    h(
      "div",
      { className: "command-cockpit-summary" },
      h("span", { className: "eyebrow" }, "Command cockpit"),
      h("h2", null, firstCommand ? firstCommand.label : "No command loaded"),
      h("p", null, "Copy commands from the case context. The browser never runs shell commands.")
    ),
    h(
      "div",
      { className: "command-cockpit-primary" },
      h("span", null, "Primary command"),
      h("code", null, firstCommand ? firstCommand.command : "No command surfaced for this case."),
      h(
        "div",
        { className: "command-cockpit-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            disabled: !firstCommand,
            onClick: () => firstCommand && copyText(firstCommand.command),
            title: "Copy primary command"
          },
          "Copy primary"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !firstCommand || !firstCommand.rowLabel,
            onClick: () => firstCommand && firstCommand.rowLabel && setSelectedLabel(firstCommand.rowLabel),
            title: "Inspect the row behind this command"
          },
          "Inspect row"
        )
      )
    ),
    h(
      "div",
      { className: "command-cockpit-list" },
      h("span", null, "Command queue"),
      commands.length
        ? commands.map((item) =>
            h(
              "div",
              { className: "command-cockpit-row", key: item.command },
              h("strong", null, item.label),
              h("small", null, item.source || "case context"),
              h("code", null, item.command),
              h(
                "button",
                {
                  className: "copy-button",
                  type: "button",
                  onClick: () => copyText(item.command),
                  title: "Copy command"
                },
                "Copy"
              )
            )
          )
        : h("p", null, "No command surfaced. Inspect evidence and receipt paths instead.")
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

function ReviewQueue({ row, reviewState, receiptHistory, snapshot, liveMode, onPreview }) {
  const decision = reviewState.decision || "unreviewed";
  const decisionLabel = (REVIEW_ACTIONS.find((action) => action.id === decision) || { label: "Unreviewed" }).label;
  const evidenceCount = row ? evidenceItems(row).length : 0;
  const lastReview = latestReceiptForRow(receiptHistory, row, "review", snapshot);
  const lastAction = latestReceiptForRow(receiptHistory, row, "row_action", snapshot);
  const lastReviewPath = receiptArtifactPath(lastReview);
  const lastActionPath = receiptArtifactPath(lastAction);
  const receiptState = row && decision !== "unreviewed" ? (liveMode ? "ready to apply" : "file ready") : "decision needed";
  const renderReceiptCell = (label, receipt, path, stateText) =>
    h(
      "div",
      { className: "review-queue-receipt" },
      h("span", null, label),
      h("strong", null, receipt ? displayText(stateText || "recorded") : "none"),
      h("code", null, path || "no artifact path"),
      h(
        "div",
        { className: "review-queue-actions" },
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !path,
            onClick: () => copyText(path),
            title: path ? `Copy ${label.toLowerCase()} artifact path` : "No artifact path recorded"
          },
          "Copy path"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !liveMode || !path,
            onClick: () => onPreview && onPreview({ type: "file", value: path }),
            title: liveMode && path ? `Preview ${label.toLowerCase()} artifact` : "Start the local API to preview artifact files"
          },
          "Preview"
        )
      )
    );
  return h(
    "section",
    { className: `review-queue ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Review queue" },
    h("div", null, h("span", null, "Selected"), h("strong", null, row ? row.label : "No row")),
    h("div", null, h("span", null, "Decision"), h("strong", null, decisionLabel)),
    h("div", null, h("span", null, "Evidence"), h("strong", null, String(evidenceCount))),
    h("div", null, h("span", null, "Receipt"), h("strong", null, receiptState)),
    renderReceiptCell("Last review", lastReview, lastReviewPath, lastReview && lastReview.decision),
    renderReceiptCell("Last action", lastAction, lastActionPath, lastAction && lastAction.action)
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

function HealthActionsPanel({ healthContext, healthMessage, liveMode, onPreviewSource, onUseActionNote }) {
  const kernel = (healthContext && healthContext.kernel) || {};
  const kernelSummary = kernel.summary || {};
  const action = (healthContext && healthContext.action_intelligence) || {};
  const actionCounts = action.counts || {};
  const attention = kernel.attention_components || [];
  const issues = action.issues || [];
  const recommendations = action.recommendations || [];
  const sourcePaths = action.source_paths || {};
  const status = kernelSummary.overall_status || (liveMode ? "loading" : "static mode");
  const previewableSourcePaths = Object.entries(sourcePaths).filter(([_key, value]) => value);
  const renderEvidenceRefs = (evidenceRefs) =>
    evidenceRefs.length
      ? h(
          "div",
          { className: "health-evidence-refs" },
          evidenceRefs.map((ref) =>
            h(
              "div",
              { className: "health-evidence-ref", key: ref },
              h("code", null, ref),
              h(
                "div",
                { className: "health-source-actions" },
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    onClick: () => copyText(ref),
                    title: "Copy evidence ref"
                  },
                  "Copy"
                ),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !liveMode || !isPreviewableRepoPath(ref),
                    onClick: () => onPreviewSource && onPreviewSource({ type: "file", value: ref }),
                    title:
                      liveMode && isPreviewableRepoPath(ref)
                        ? "Preview evidence ref"
                        : "Start the local API to preview repository files"
                  },
                  "Preview"
                )
              )
            )
          )
        )
      : null;

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
            ? "Live run health and action recommendations for this project."
            : "Start the local API to inspect live run health and action recommendations.")
      )
    ),
    h(
      "div",
      { className: "health-metrics" },
      h("div", null, h("span", null, "Run health"), h("strong", null, displayText(kernelSummary.component_status || status))),
      h("div", null, h("span", null, "Attention"), h("strong", null, String((kernelSummary.component_counts || {}).attention || attention.length || 0))),
      h("div", null, h("span", null, "Action issues"), h("strong", null, String(actionCounts.issues || issues.length || 0))),
      h("div", null, h("span", null, "Recommendations"), h("strong", null, String(recommendations.length || 0))),
      h("div", null, h("span", null, "Warnings"), h("strong", null, String(actionCounts.warning || 0)))
    ),
    h(
      "div",
      { className: "health-findings" },
      h(HealthFindingList, {
        title: "Run findings",
        emptyText: "Run health has no active attention component.",
        rows: attention,
        renderRow: (row, index) =>
          h(
            "div",
            { className: "health-finding-row kernel", key: `${row.component || "kernel"}:${index}` },
            h("strong", null, row.component || "run component"),
            h("small", null, displayText(row.status || "attention")),
            h("p", null, row.action || "Inspect component."),
            row.next_command
              ? h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    onClick: () => copyText(row.next_command),
                    title: "Copy run-health next command"
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
        renderRow: (row, index) => {
          const evidenceRefs = Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean) : [];
          const affectedDomains = Array.isArray(row.affected_domains) ? row.affected_domains.filter(Boolean) : [];
          const countText =
            row.observed_count !== undefined && row.expected_count !== undefined
              ? `${row.observed_count}/${row.expected_count}`
              : "";
          const actionNote = actionIntelligenceNote(row, "Inspect source-health issue");
          return h(
            "div",
            { className: "health-finding-row action", key: `${row.issue_id || row.issue_type || "issue"}:${row.scope || index}` },
            h("strong", null, displayText(row.issue_type || "source-health issue")),
            h("small", null, [displayText(row.severity || "warning"), row.scope ? displayText(row.scope) : "", countText].filter(Boolean).join(" | ")),
            h("p", null, displayText(row.blocking_rule || row.recommended_action || "Inspect source health.")),
            row.recommended_action
              ? h("p", { className: "health-action-next" }, `Next: ${displayText(row.recommended_action)}`)
              : null,
            affectedDomains.length
              ? h("p", { className: "health-action-domains" }, `Affects: ${affectedDomains.map(displayText).join(", ")}`)
              : null,
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => onUseActionNote && onUseActionNote(actionNote, actionIntelligenceAction(row)),
                title: "Stage this issue in the row-action editor"
              },
              "Use as action"
            ),
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => copyText(actionNote),
                title: "Copy this issue as a row-action note"
              },
              "Copy action note"
            ),
            renderEvidenceRefs(evidenceRefs)
          );
        }
      }),
      h(HealthFindingList, {
        title: "Advisory recommendations",
        emptyText: "No action-intelligence recommendations surfaced.",
        rows: recommendations,
        renderRow: (row, index) => {
          const evidenceRefs = Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean).slice(0, 3) : [];
          const pSuccess = typeof row.p_success === "number" ? `p ${Math.round(row.p_success * 100)}%` : "";
          const cost = typeof row.expected_cost_agent_minutes === "number" ? `${row.expected_cost_agent_minutes} min` : "";
          const actionNote = actionIntelligenceNote(row, "Inspect advisory recommendation");
          return h(
            "div",
            { className: "health-finding-row recommendation", key: `${row.recommendation_id || "recommendation"}:${index}` },
            h("strong", null, displayText(row.recommended_action || "recommendation")),
            h(
              "small",
              null,
              [row.domain ? displayText(row.domain) : "", row.confidence ? displayText(row.confidence) : "", row.execution_authority ? displayText(row.execution_authority) : ""]
                .filter(Boolean)
                .join(" | ")
            ),
            h("p", null, row.rationale || "Inspect the backing recommendation before acting."),
            pSuccess || cost || row.effective_n
              ? h("p", { className: "health-action-domains" }, [pSuccess, cost, row.effective_n ? `n ${row.effective_n}` : ""].filter(Boolean).join(" | "))
              : null,
            row.decision_id ? h("code", null, row.decision_id) : null,
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => onUseActionNote && onUseActionNote(actionNote, actionIntelligenceAction(row)),
                title: "Stage this recommendation in the row-action editor"
              },
              "Use as action"
            ),
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => copyText(actionNote),
                title: "Copy this recommendation as a row-action note"
              },
              "Copy action note"
            ),
            renderEvidenceRefs(evidenceRefs)
          );
        }
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
  const reviewFilename = row ? caseScopedDownloadName(snapshot, rowKey, "review") : "review.json";
  const intakeArg = snapshot.intake ? ` --intake ${snapshot.intake}` : "";
  const command = row
    ? `ztare forensic-workbench apply-review --project ${snapshot.project}${intakeArg} --row ${rowKey} --from ${reviewFilename}`
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
      h("p", null, liveMode ? "Apply writes the review receipt through the local API. Download and copy only export the JSON." : "Start the local API to write the review receipt; download and copy stay in the browser."),
      h(
        "div",
        { className: "handoff-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
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
  const actionFilename = row ? caseScopedDownloadName(snapshot, rowKey, "action") : "row_action.json";
  const intakeArg = snapshot.intake ? ` --intake ${snapshot.intake}` : "";
  const command = row
    ? `ztare forensic-workbench save-action --project ${snapshot.project}${intakeArg} --row ${rowKey} --from ${actionFilename}`
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
      h("p", null, liveMode ? "Save action writes the row-action receipt through the local API. Download and copy only export the JSON." : "Start the local API to write the row-action receipt; download and copy stay in the browser."),
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

function WriteReceiptPanel({ receiptEvent, refreshResults, liveMode, onPreview }) {
  if (!receiptEvent) return null;
  const result = receiptEvent.result || {};
  const receipt = result.receipt || {};
  const refreshRows = Array.isArray(refreshResults) ? refreshResults.filter(Boolean) : [];
  const refreshFailures = refreshRows.filter((row) => row.ok === false);
  const refreshSuccesses = refreshRows.length - refreshFailures.length;
  const receiptSummary = receiptEvent.snapshotError
    ? `Receipt written. Snapshot refresh failed: ${receiptEvent.snapshotError}`
    : refreshFailures.length
      ? `Receipt written. Refreshed ${refreshSuccesses}/${refreshRows.length} panels; ${refreshFailures.length} need attention.`
      : refreshRows.length
        ? `Receipt written. Refreshed ${refreshRows.length} live panels.`
        : "Receipt written. Refresh status was not recorded.";
  const kindLabels = {
    intake_edit: "Intake edit",
    case_file: "Case file",
    row_action: "Row action",
    source_action: "Source action",
    source_import: "Source import",
    source_edit: "Source edit",
    review: "Review"
  };
  const kindLabel = kindLabels[receiptEvent.kind] || displayText(receiptEvent.kind || "write");
  const editedFields = (receipt.updated_fields || []).map(displayFieldName).join(", ");
  const actionLabel = receipt.action || receipt.decision || receipt.status || receipt.binding_mode || receipt.source_type || editedFields || "written";
  const hash =
    receipt.review_file_sha256 ||
    receipt.action_file_sha256 ||
    receipt.after_sha256 ||
    receipt.source_sha256 ||
    receipt.source_receipt_sha256 ||
    receipt.case_file_sha256 ||
    receipt.sha256 ||
    "";
  const sourcePath = receipt.review_file_path || receipt.action_file_path || receipt.intake_path || receipt.source_path || receipt.case_file_path || receipt.path || receipt.provenance_path || "";
  const previewableSourcePath = isPreviewableRepoPath(sourcePath);
  const ledgerPath = result.ledger || result.receipt_path || "";
  const latestPath = result.latest || "";
  const changedSummary = receiptChangeSummary(receipt, receiptEvent.kind);
  const caseContext = [
    receipt.project ? `project ${receipt.project}` : "",
    receipt.intake ? `intake ${receipt.intake}` : "",
    receipt.case_key ? `case ${receipt.case_key}` : ""
  ].filter(Boolean).join(" / ");
  const receiptJson = JSON.stringify(receipt, null, 2);

  return h(
    "section",
    { className: "write-receipt-panel", "aria-label": "Last write receipt" },
    h(
      "div",
      { className: "write-receipt-summary" },
      h("span", { className: "eyebrow" }, "Last write receipt"),
      h("h2", null, `${kindLabel}: ${displayText(actionLabel)}`),
      h("p", null, receiptSummary)
    ),
    h(
      "div",
      { className: "write-receipt-facts" },
      h("div", null, h("span", null, "Target"), h("strong", null, receipt.row || receipt.relative_raw_path || receipt.intake_path || receipt.case_file_path || receiptEvent.row || "none")),
      h("div", null, h("span", null, "Case"), h("strong", null, caseContext || receipt.project || "not recorded")),
      h("div", null, h("span", null, "Schema"), h("strong", null, receipt.schema || "none")),
      h("div", null, h("span", null, "Applied"), h("strong", null, receipt.applied_at || "none")),
      h("div", null, h("span", null, "Changed"), h("strong", null, changedSummary || "not recorded")),
      h("div", null, h("span", null, "Hash"), h("strong", null, shortDigest(hash))),
      h("div", null, h("span", null, "Refresh"), h("strong", null, refreshRows.length ? `${refreshSuccesses}/${refreshRows.length} panels` : "not run"))
    ),
    refreshRows.length
      ? h(
          "div",
          { className: "write-refresh-strip" },
          refreshRows.map((row) =>
            h(
              "span",
              { key: row.label, className: row.ok === false ? "attention" : "ready", title: row.error || row.label },
              row.label
            )
          )
        )
      : null,
    h(
      "div",
      { className: "write-receipt-paths" },
      h("div", null, h("span", null, "Ledger"), h("code", null, ledgerPath || "no ledger path")),
      h("div", null, h("span", null, "Latest"), h("code", null, latestPath || "no latest path")),
      h("div", null, h("span", null, "Source"), h("code", null, sourcePath || "no source path")),
      h(
        "div",
        { className: "write-receipt-actions" },
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !liveMode || !ledgerPath,
            onClick: () => onPreview && onPreview({ type: "receipt", value: ledgerPath }),
            title: liveMode ? "Preview the receipt ledger" : "Start the local API to preview files"
          },
          "Preview ledger"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !liveMode || !latestPath,
            onClick: () => onPreview && onPreview({ type: "receipt", value: latestPath }),
            title: liveMode ? "Preview the latest receipt file" : "Start the local API to preview files"
          },
          "Preview latest"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !liveMode || !previewableSourcePath,
            onClick: () => onPreview && onPreview({ type: "file", value: sourcePath }),
            title: previewFileTitle(liveMode, previewableSourcePath)
          },
          "Preview file"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !receipt.schema,
            onClick: () => copyText(receiptJson),
            title: "Copy stamped receipt JSON"
          },
          "Copy receipt"
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
  const [traceContext, setTraceContext] = useState(null);
  const [traceMessage, setTraceMessage] = useState("");
  const [preflightEvent, setPreflightEvent] = useState(null);
  const [preflightMessage, setPreflightMessage] = useState("");
  const [preflightRunning, setPreflightRunning] = useState(false);
  const [sourceActionEvent, setSourceActionEvent] = useState(null);
  const [sourceActionMessage, setSourceActionMessage] = useState("");
  const [sourceActionRunning, setSourceActionRunning] = useState(false);
  const [runHistoryContext, setRunHistoryContext] = useState(null);
  const [runHistoryMessage, setRunHistoryMessage] = useState("");
  const [claimSupportContext, setClaimSupportContext] = useState(null);
  const [claimSupportMessage, setClaimSupportMessage] = useState("");
  const [healthContext, setHealthContext] = useState(null);
  const [healthMessage, setHealthMessage] = useState("");
  const [reportContractContext, setReportContractContext] = useState(null);
  const [reportContractMessage, setReportContractMessage] = useState("");
  const [projects, setProjects] = useState([]);
  const [selectedProjectKey, setSelectedProjectKey] = useState("");
  const [projectCreateDraft, setProjectCreateDraft] = useState({
    project: "",
    task: "",
    bounded_claim: "",
    next_falsifier: "",
    notes: "",
    source_refs_text: "",
    evidence_refs_text: "",
    non_claims_text: ""
  });
  const [projectCreateMessage, setProjectCreateMessage] = useState("");
  const [projectCreating, setProjectCreating] = useState(false);
  const [sourceImportDraft, setSourceImportDraft] = useState(emptySourceImportDraft());
  const [sourceImportMessage, setSourceImportMessage] = useState("");
  const [sourceImportEvent, setSourceImportEvent] = useState(null);
  const [sourceImporting, setSourceImporting] = useState(false);
  const [sourceListContext, setSourceListContext] = useState(null);
  const [sourceListMessage, setSourceListMessage] = useState("");
  const [sourceEditDraft, setSourceEditDraft] = useState(emptySourceEditDraft());
  const [sourceEditMessage, setSourceEditMessage] = useState("");
  const [sourceEditEvent, setSourceEditEvent] = useState(null);
  const [sourceEditing, setSourceEditing] = useState(false);
  const [liveMode, setLiveMode] = useState(false);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [writeReceiptEvent, setWriteReceiptEvent] = useState(null);
  const [lastRefreshResults, setLastRefreshResults] = useState([]);
  const [caseFileSaveEvent, setCaseFileSaveEvent] = useState(null);
  const [caseFileSaving, setCaseFileSaving] = useState(false);
  const [intakeDraft, setIntakeDraft] = useState(null);
  const [intakeMessage, setIntakeMessage] = useState("");
  const [receiptHistory, setReceiptHistory] = useState(null);
  const [receiptHistoryMessage, setReceiptHistoryMessage] = useState("");
  const [filePreview, setFilePreview] = useState(null);
  const [filePreviewMessage, setFilePreviewMessage] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [reviewStates, setReviewStates] = useState({});
  const [actionStates, setActionStates] = useState({});
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");

  const defaultSnapshotLabel = (rows) => {
    const firstAttention = rows.find((row) => row.kind === "attention");
    return (firstAttention && firstAttention.label) || (rows[0] && rows[0].label) || "";
  };

  const installSnapshot = (payload, options = {}) => {
    setSnapshot(payload);
    setReviewMessage("");
    setActionMessage("");
    const rows = payload.rows || [];
    const labels = new Set(rows.map((row) => row.label));
    setSelectedLabel((currentLabel) => {
      if (options.preferredLabel && labels.has(options.preferredLabel)) return options.preferredLabel;
      if (options.preserveSelection && currentLabel && labels.has(currentLabel)) return currentLabel;
      return defaultSnapshotLabel(rows);
    });
  };

  const resetCaseSessionState = () => {
    setTraceContext(null);
    setTraceMessage("");
    setPreflightEvent(null);
    setPreflightMessage("");
    setSourceActionEvent(null);
    setSourceActionMessage("");
    setRunHistoryContext(null);
    setRunHistoryMessage("");
    setClaimSupportContext(null);
    setClaimSupportMessage("");
    setHealthContext(null);
    setHealthMessage("");
    setReportContractContext(null);
    setReportContractMessage("");
    setSourceImportEvent(null);
    setSourceImportMessage("");
    setSourceImportDraft(emptySourceImportDraft());
    setSourceListContext(null);
    setSourceListMessage("");
    setSourceEditEvent(null);
    setSourceEditMessage("");
    setSourceEditDraft(emptySourceEditDraft());
    setWriteReceiptEvent(null);
    setLastRefreshResults([]);
    setCaseFileSaveEvent(null);
    setIntakeDraft(null);
    setIntakeMessage("");
    setReceiptHistory(null);
    setReceiptHistoryMessage("");
    setFilePreview(null);
    setFilePreviewMessage("");
    setReviewMessage("");
    setActionMessage("");
    setReviewStates({});
    setActionStates({});
  };

  const refreshResult = (label, ok, error = "") => ({ label, ok, error: error ? String(error) : "" });

  const refreshProjectIndex = (activeProject) =>
    fetch("/api/projects", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`project index fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        const projectRows = payload.projects || [];
        if (!projectRows.length) throw new Error("project index is empty");
        setProjects(projectRows);
        const activeRow = projectRows.find((row) => projectEntryKey(row) === activeProject) || projectRows.find((row) => row.project === activeProject);
        if (activeRow) {
          setSelectedProjectKey(projectEntryKey(activeRow));
        }
        return refreshResult("project index", true);
      })
      .catch((err) => {
        setModeMessage(`Project index refresh failed: ${err.message || err}`);
        return refreshResult("project index", false, err.message || err);
      });

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
        return refreshResult("health", true);
      })
      .catch((err) => {
        setHealthContext(null);
        setHealthMessage(`Live health context unavailable: ${err.message || err}`);
        return refreshResult("health", false, err.message || err);
      });
  };

  const loadTraceContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setTraceMessage("Loading autoresearch trace.");
    return fetch(endpointUrl("/api/trace", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`trace fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "trace fetch failed");
        setTraceContext(payload);
        setTraceMessage("Live autoresearch trace loaded from the local API.");
        return refreshResult("trace", true);
      })
      .catch((err) => {
        setTraceContext(null);
        setTraceMessage(`Live autoresearch trace unavailable: ${err.message || err}`);
        return refreshResult("trace", false, err.message || err);
      });
  };

  const loadReportContractContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setReportContractMessage("Loading report support contract.");
    return fetch(endpointUrl("/api/report-contract", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`report contract fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false && !payload.status) throw new Error(payload.error || "report contract fetch failed");
        setReportContractContext(payload);
        setReportContractMessage("Report support contract loaded from the local API.");
        return refreshResult("report", true);
      })
      .catch((err) => {
        setReportContractContext(null);
        setReportContractMessage(`Report support contract unavailable: ${err.message || err}`);
        return refreshResult("report", false, err.message || err);
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
        return refreshResult("intake", true);
      })
      .catch((err) => {
        setIntakeDraft(null);
        setIntakeMessage(`Live intake unavailable: ${err.message || err}`);
        return refreshResult("intake", false, err.message || err);
      });
  };

  const loadReceiptHistory = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setReceiptHistoryMessage("Loading receipt history.");
    return fetch(endpointUrl("/api/receipts", { project: projectParams.project, intake: projectParams.intake, limit: 12 }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`receipt history fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "receipt history fetch failed");
        setReceiptHistory(payload);
        setReceiptHistoryMessage(`${payload.receipt_count || 0} receipt rows found in project ledgers.`);
        return refreshResult("receipts", true);
      })
      .catch((err) => {
        setReceiptHistory(null);
        setReceiptHistoryMessage(`Receipt history unavailable: ${err.message || err}`);
        return refreshResult("receipts", false, err.message || err);
      });
  };

  const loadRunHistoryContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setRunHistoryMessage("Loading run history.");
    return fetch(endpointUrl("/api/run-history", { ...projectParams, limit: 8 }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`run history fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "run history fetch failed");
        setRunHistoryContext(payload);
        setRunHistoryMessage(`${(payload.summary || {}).run_rows || 0} run-history rows loaded from project files.`);
        return refreshResult("run history", true);
      })
      .catch((err) => {
        setRunHistoryContext(null);
        setRunHistoryMessage(`Run history unavailable: ${err.message || err}`);
        return refreshResult("run history", false, err.message || err);
      });
  };

  const loadClaimSupportContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setClaimSupportMessage("Loading claim support.");
    return fetch(endpointUrl("/api/claim-support", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`claim support fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false && !payload.status) throw new Error(payload.error || "claim support fetch failed");
        setClaimSupportContext(payload);
        setClaimSupportMessage(
          payload.accepted
            ? `${payload.claim_count || 0} claim-support rows loaded from project files.`
            : `Claim support needs attention: ${payload.status || "attention"}.`
        );
        return refreshResult("claim support", true);
      })
      .catch((err) => {
        setClaimSupportContext(null);
        setClaimSupportMessage(`Claim support unavailable: ${err.message || err}`);
        return refreshResult("claim support", false, err.message || err);
      });
  };

  const loadSourceListContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setSourceListMessage("Loading raw sources.");
    return fetch(endpointUrl("/api/sources", { project: projectParams.project }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`source list fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "source list fetch failed");
        setSourceListContext(payload);
        setSourceListMessage(`${(payload.sources || []).length} raw sources loaded from ${payload.raw_dir || "project raw"}.`);
        return refreshResult("sources", true);
      })
      .catch((err) => {
        setSourceListContext(null);
        setSourceListMessage(`Raw sources unavailable: ${err.message || err}`);
        return refreshResult("sources", false, err.message || err);
      });
  };

  const liveProjectParams = () => ({
    project: snapshot.project,
    rubric: (currentProjectEntry && currentProjectEntry.rubric) || snapshot.rubric,
    intake: (currentProjectEntry && currentProjectEntry.intake) || snapshot.intake
  });

  const pendingEditorWarnings = (options = {}) => {
    const warnings = [];
    if (options.intake !== false) {
      const fields = intakeChangedFields(intakeDraft);
      if (fields.length) warnings.push(`intake draft (${fields.map(displayFieldName).join(", ")})`);
    }
    if (options.sourceEdit !== false) {
      const fields = sourceChangedFields(sourceEditDraft);
      if (fields.length) {
        warnings.push(`raw source ${sourceEditDraft.relative_raw_path || "draft"} (${fields.map(displayFieldName).join(", ")})`);
      }
    }
    if (options.sourceImport === true) {
      const hasImportDraft = Boolean(String(sourceImportDraft.filename || "").trim() || String(sourceImportDraft.body || "").trim());
      if (hasImportDraft) warnings.push("source import draft");
    }
    return warnings;
  };

  const confirmDiscardPendingEditors = (action, options = {}) => {
    const warnings = pendingEditorWarnings(options);
    if (!warnings.length) return true;
    const message = `${action} will discard unsaved ${warnings.join(" and ")}. Save first, or continue to discard.`;
    if (window.confirm(message)) return true;
    setModeMessage(`Kept current case. Save or discard unsaved edits before ${action.toLowerCase()}.`);
    return false;
  };

  const refreshLiveContextAfterWrite = (projectParams, options = {}) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    const refreshIntakeAfterWrite = () => {
      if (options.intake === false) return null;
      if (intakeChangedFields(intakeDraft).length) {
        return Promise.resolve(refreshResult("intake", false, "unsaved intake draft preserved"));
      }
      return loadIntakeDraft(projectParams);
    };
    const tasks = [
      loadTraceContext(projectParams),
      loadReportContractContext(projectParams),
      loadHealthContext(projectParams),
      refreshIntakeAfterWrite(),
      loadReceiptHistory(projectParams),
      loadClaimSupportContext(projectParams),
      refreshProjectIndex(projectEntryKey(projectParams))
    ].filter(Boolean);
    if (options.sources) tasks.push(loadSourceListContext(projectParams));
    if (options.runHistory) tasks.push(loadRunHistoryContext(projectParams));
    return Promise.all(tasks).then((results) => {
      const compactResults = results.filter(Boolean);
      setLastRefreshResults(compactResults);
      const failed = compactResults.filter((item) => item.ok === false);
      const refreshed = compactResults.filter((item) => item.ok !== false).map((item) => item.label);
      if (failed.length) {
        setModeMessage(
          `Write saved. Refreshed ${refreshed.length} live panels; ${failed.length} need attention: ${failed
            .map((item) => item.label)
            .join(", ")}.`
        );
      } else {
        setModeMessage(`Write saved. Refreshed live panels: ${refreshed.join(", ")}.`);
      }
      return results;
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
        installSnapshot(payload, {
          preserveSelection: options.preserveSelection === true,
          preferredLabel: options.preferredLabel || ""
        });
        setModeMessage(
          useLiveApi
            ? `Live project snapshot loaded from the local API: ${payload.project}.`
            : `Static snapshot loaded from ${payload.html_output || "workbench_snapshot.json"}.`
        );
        if (useLiveApi) {
          const liveParams = { ...loadParams, project: payload.project, rubric: payload.rubric || loadParams.rubric, intake: payload.intake || loadParams.intake };
          setSelectedProjectKey(projectEntryKey(liveParams));
          return Promise.allSettled([
            loadTraceContext(liveParams),
            loadReportContractContext(liveParams),
            loadHealthContext(liveParams),
            loadIntakeDraft(liveParams),
            loadReceiptHistory(liveParams),
            loadRunHistoryContext(liveParams),
            loadClaimSupportContext(liveParams),
            loadSourceListContext(liveParams)
          ]);
        }
        setTraceContext(null);
        setTraceMessage("Static mode uses the last generated snapshot only.");
        setPreflightEvent(null);
        setPreflightMessage("Static mode cannot run live preflight.");
        setSourceActionEvent(null);
        setSourceActionMessage("Static mode cannot run live source/evidence actions.");
        setReportContractContext(null);
        setReportContractMessage("Static mode uses the report/export row from the last generated snapshot only.");
        setHealthContext(null);
        setHealthMessage("Static mode uses the last generated snapshot only.");
        setIntakeDraft(null);
        setIntakeMessage("Static mode cannot edit the project intake.");
        setReceiptHistory(null);
        setReceiptHistoryMessage("Static mode uses the latest generated snapshot only.");
        setRunHistoryContext(null);
        setRunHistoryMessage("Static mode uses the run-history row from the last generated snapshot only.");
        setClaimSupportContext(null);
        setClaimSupportMessage("Static mode uses the source/evidence rows from the last generated snapshot only.");
        setSourceListContext(null);
        setSourceListMessage("Static mode cannot inspect raw sources.");
        setSourceEditEvent(null);
        setSourceEditMessage("Static mode cannot edit raw sources.");
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
        setSelectedProjectKey(projectEntryKey(preferred));
        return loadSnapshot(preferred, true, { allowStaticFallback: true });
      })
      .catch(() =>
        loadSnapshot("", false).catch((err) => setError(String(err.message || err)))
      );
  }, []);

  const openProject = (caseKey) => {
    if (!caseKey || !liveMode) return;
    const entry = projects.find((row) => projectEntryKey(row) === caseKey) || projects.find((row) => row.project === caseKey) || { project: caseKey, rubric: caseKey };
    if (!confirmDiscardPendingEditors(`Opening ${entry.project}`, { sourceImport: true })) return;
    resetCaseSessionState();
    setModeMessage(`Opening ${entry.project} from local project files.`);
    loadSnapshot(entry, true).catch((err) =>
      setModeMessage(`Could not load live project snapshot for ${entry.project}: ${err.message || err}`)
    );
  };

  const handleProjectChange = (event) => openProject(event.target.value);

  const refreshCurrentProject = () => {
    if (!snapshot || !liveMode) return;
    const sourceDraftWasDirty = sourceChangedFields(sourceEditDraft).length > 0;
    if (!confirmDiscardPendingEditors("Refreshing this project")) return;
    if (sourceDraftWasDirty) {
      setSourceEditDraft(emptySourceEditDraft());
      setSourceEditMessage("Raw source draft cleared by refresh.");
    }
    const entry = currentProjectEntry || snapshot;
    loadSnapshot(entry, true, { preserveSelection: true }).catch((err) =>
      setModeMessage(`Could not refresh live project snapshot for ${snapshot.project}: ${err.message || err}`)
    );
  };

  const refreshCurrentIntake = () => {
    if (!snapshot || !liveMode) return;
    if (!confirmDiscardPendingEditors("Reloading the intake", { sourceEdit: false })) return;
    const entry = currentProjectEntry || snapshot;
    loadIntakeDraft(projectLoadParams(entry));
  };

  const createProjectLive = () => {
    if (!liveMode || projectCreating) return;
    setProjectCreating(true);
    setProjectCreateMessage("Creating local project and intake.");
    fetch("/api/project-create", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: projectCreateDraft.project,
        rubric: projectCreateDraft.project,
        task: projectCreateDraft.task,
        bounded_claim: projectCreateDraft.bounded_claim,
        next_falsifier: projectCreateDraft.next_falsifier,
        notes: projectCreateDraft.notes,
        source_refs: linesFromText(projectCreateDraft.source_refs_text),
        evidence_refs: linesFromText(projectCreateDraft.evidence_refs_text),
        non_claims: linesFromText(projectCreateDraft.non_claims_text),
        renderer: "decision_brief"
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok || payload.ok === false) {
            throw new Error(payload.error || `project create failed: ${response.status}`);
          }
          return payload;
        })
      )
      .then((payload) => {
        if (!payload.accepted) {
          setProjectCreateMessage("Create command finished with attention; inspect the server response.");
          return;
        }
        const projectRows = (payload.project_index && payload.project_index.projects) || [];
        if (projectRows.length) setProjects(projectRows);
        setSelectedProjectKey(projectEntryKey(payload));
        resetCaseSessionState();
        if (payload.snapshot) installSnapshot(payload.snapshot);
        setLiveMode(true);
        loadSnapshot({ project: payload.project, rubric: payload.rubric, intake: payload.intake }, true).catch((err) =>
          setProjectCreateMessage(`Created ${payload.project}, but live reload failed: ${err.message || err}`)
        );
        setProjectCreateDraft({
          project: "",
          task: "",
          bounded_claim: "",
          next_falsifier: "",
          notes: "",
          source_refs_text: "",
          evidence_refs_text: "",
          non_claims_text: ""
        });
        setProjectCreateMessage(`Created ${payload.project} and opened the live case.`);
      })
      .catch((err) => setProjectCreateMessage(String(err.message || err)))
      .finally(() => setProjectCreating(false));
  };

  const importSourceLive = () => {
    if (!snapshot || !liveMode || sourceImporting) return;
    const params = liveProjectParams();
    setSourceImporting(true);
    setSourceImportMessage("Importing source file.");
    setSourceImportEvent(null);
    fetch("/api/source-import", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        renderer: "decision_brief",
        filename: sourceImportDraft.filename,
        source_type: sourceImportDraft.source_type,
        body: sourceImportDraft.body
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok || payload.ok === false) {
            throw new Error(payload.error || `source import failed: ${response.status}`);
          }
          return payload;
        })
      )
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Source readiness" });
        if (payload.trace) setTraceContext(payload.trace);
        setSourceImportEvent(payload);
        setSourceImportDraft({ filename: "", source_type: "source_evidence", body: "" });
        setSourceImportMessage(`Imported ${payload.source_path}. Source check ${payload.source_check && payload.source_check.accepted ? "accepted" : "needs attention"}.`);
        setWriteReceiptEvent({
          kind: "source_import",
          row: payload.relative_raw_path || payload.source_path,
          result: payload,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { sources: true });
      })
      .catch((err) => setSourceImportMessage(String(err.message || err)))
      .finally(() => setSourceImporting(false));
  };

  const addImportedSourceToIntakeDraft = (sourcePath) => {
    const path = String(sourcePath || "").trim();
    if (!path) return;
    if (!intakeDraft) {
      setSourceImportMessage("Load a live intake before staging source refs.");
      return;
    }
    if (intakeDraft.editable === false) {
      setSourceImportMessage("This intake is read-only; the source path was not staged.");
      return;
    }
    const refs = linesFromText(intakeDraft.source_refs_text);
    if (refs.includes(path)) {
      setSourceImportMessage(`${path} is already in the intake draft.`);
      return;
    }
    const nextRefs = [...refs, path].join("\n");
    setIntakeDraft({ ...intakeDraft, source_refs_text: nextRefs });
    setSourceImportMessage(`Staged ${path} in source refs. Save intake to write the receipt.`);
    setIntakeMessage(`Staged ${path} in source refs. Save intake to write the receipt.`);
  };

  const reloadSourceList = () => {
    if (!snapshot || !liveMode) return;
    loadSourceListContext({ project: snapshot.project });
  };

  const openRawSourceForEdit = (relativePath) => {
    if (!snapshot || !liveMode || !relativePath) return;
    if (sourceEditDraft.relative_raw_path && sourceChangedFields(sourceEditDraft).length) {
      if (!confirmDiscardPendingEditors(`Opening ${relativePath}`, { intake: false, sourceImport: false })) return;
    }
    setSourceEditMessage(`Opening ${relativePath}.`);
    fetch(endpointUrl("/api/source-file", { project: snapshot.project, relative: relativePath }), { headers: { Accept: "application/json" } })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok || payload.ok === false) {
            throw new Error(payload.error || `source file fetch failed: ${response.status}`);
          }
          return payload;
        })
      )
      .then((payload) => {
        const nextDraft = {
          relative_raw_path: payload.relative_raw_path || relativePath,
          source_type: payload.source_type || "untyped",
          body: payload.body || ""
        };
        setSourceEditDraft({
          ...nextDraft,
          original: { ...nextDraft }
        });
        setSourceEditMessage(`Opened ${payload.relative_raw_path || relativePath}.`);
      })
      .catch((err) => setSourceEditMessage(String(err.message || err)));
  };

  const saveRawSourceEdit = () => {
    if (!snapshot || !liveMode || sourceEditing) return;
    const params = liveProjectParams();
    setSourceEditing(true);
    setSourceEditMessage(`Saving ${sourceEditDraft.relative_raw_path || "source"}.`);
    setSourceEditEvent(null);
    fetch("/api/source-edit", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        renderer: "decision_brief",
        relative_raw_path: sourceEditDraft.relative_raw_path,
        source_type: sourceEditDraft.source_type,
        body: sourceEditDraft.body
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok || payload.ok === false) {
            throw new Error(payload.error || `source edit failed: ${response.status}`);
          }
          return payload;
        })
      )
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Source readiness", preserveSelection: true });
        if (payload.trace) setTraceContext(payload.trace);
        setSourceEditEvent(payload);
        const nextDraft = {
          relative_raw_path: payload.relative_raw_path || sourceEditDraft.relative_raw_path,
          source_type: payload.source_type || sourceEditDraft.source_type,
          body: sourceEditDraft.body
        };
        setSourceEditDraft({ ...nextDraft, original: { ...sourceDraftFields(nextDraft) } });
        setSourceEditMessage(`Saved ${payload.source_path}. Source check ${payload.source_check && payload.source_check.accepted ? "accepted" : "needs attention"}.`);
        setWriteReceiptEvent({
          kind: "source_edit",
          row: payload.relative_raw_path || payload.source_path,
          result: payload,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { sources: true });
      })
      .catch((err) => setSourceEditMessage(String(err.message || err)))
      .finally(() => setSourceEditing(false));
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
    const snapshotKey = projectEntryKey(snapshot);
    return (
      projects.find((row) => projectEntryKey(row) === selectedProjectKey) ||
      projects.find((row) => projectEntryKey(row) === snapshotKey) ||
      projects.find((row) => row.project === snapshot.project) ||
      null
    );
  }, [projects, selectedProjectKey, snapshot]);

  const reportPanelContext = useMemo(() => {
    if (reportContractContext) return reportContractContext;
    const rows = (snapshot && snapshot.rows) || [];
    const reportRow = rowByLabel(rows, "Report/export") || {};
    return {
      schema: REPORT_CONTRACT_SCHEMA,
      status: (snapshot && snapshot.report_status) || reportRow.status || "unknown",
      status_reasons: (snapshot && snapshot.status_reasons) || [],
      report_support_contract: (currentProjectEntry && currentProjectEntry.report_contract) || reportRow.file || reportRow.evidence || "",
      command: reportRow.command || "",
      synthesis_input_binding: {
        status: liveMode ? "loading" : "snapshot",
        reason: liveMode
          ? "The live report support contract is still loading."
          : "Static mode shows the report/export row from the last generated snapshot."
      }
    };
  }, [currentProjectEntry, liveMode, reportContractContext, snapshot]);

  const pendingEditorItems = pendingEditorWarnings({ sourceImport: true });
  const selectedReviewState = (selectedRow && reviewStates[selectedRow.label]) || { decision: "", note: "" };
  const setSelectedReviewState = (label, nextState) => {
    setReviewStates((current) => ({ ...current, [label]: nextState }));
  };
  const selectedActionState = (selectedRow && actionStates[selectedRow.label]) || { action: "next_step", note: "" };
  const setSelectedActionState = (label, nextState) => {
    setActionStates((current) => ({ ...current, [label]: nextState }));
  };
  const useHealthActionNote = (note, action = "next_step") => {
    if (!snapshot || !note) return;
    const rows = snapshot.rows || [];
    const target = rowForActionNote(rows, action, selectedRow);
    if (!target) return;
    setSelectedLabel(target.label);
    setActionStates((current) => ({ ...current, [target.label]: { action, note } }));
    setActionMessage(`Staged health action on ${target.label}. Review and save the row action.`);
  };

  const applyReviewLive = (rowSlugValue, reviewPayload) => {
    if (!snapshot || !liveMode || !rowSlugValue || !reviewPayload) return;
    const params = liveProjectParams();
    setReviewMessage("Applying review.");
    setWriteReceiptEvent(null);
    fetch("/api/review", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
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
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: reviewPayload.row, preserveSelection: true });
        setReviewMessage(
          payload.snapshot_error
            ? `Applied review for ${reviewPayload.row}. Snapshot refresh failed: ${payload.snapshot_error}`
            : `Applied review for ${reviewPayload.row}.`
        );
        setWriteReceiptEvent({
          kind: "review",
          row: reviewPayload.row,
          result: payload.review,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params);
      })
      .catch((err) => setReviewMessage(String(err.message || err)));
  };

  const applyRowActionLive = (rowSlugValue, actionPayload) => {
    if (!snapshot || !liveMode || !rowSlugValue || !actionPayload) return;
    const params = liveProjectParams();
    setActionMessage("Saving row action.");
    setWriteReceiptEvent(null);
    fetch("/api/row-action", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
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
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: actionPayload.row, preserveSelection: true });
        setActionMessage(
          payload.snapshot_error
            ? `Saved action for ${actionPayload.row}. Snapshot refresh failed: ${payload.snapshot_error}`
            : `Saved action for ${actionPayload.row}.`
        );
        setWriteReceiptEvent({
          kind: "row_action",
          row: actionPayload.row,
          result: payload.action,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params);
      })
      .catch((err) => setActionMessage(String(err.message || err)));
  };

  const saveIntakeDraft = () => {
    if (!snapshot || !liveMode || !intakeDraft) return;
    const params = liveProjectParams();
    if (intakeDraft.editable === false) {
      setIntakeMessage("This intake is read-only in the local workbench.");
      return;
    }
    if (!intakeChangedFields(intakeDraft).length) {
      setIntakeMessage("No changed intake fields to write.");
      return;
    }
    setIntakeMessage("Saving intake edit.");
    setWriteReceiptEvent(null);
    fetch("/api/intake", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
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
        if (payload.snapshot) installSnapshot(payload.snapshot, { preserveSelection: true });
        setIntakeMessage(
          payload.snapshot_error
            ? `Saved intake edit. Snapshot refresh failed: ${payload.snapshot_error}`
            : `Saved intake edit receipt: ${(payload.edit && payload.edit.latest) || "recorded"}.`
        );
        setWriteReceiptEvent({
          kind: "intake_edit",
          row: "Project intake",
          result: payload.edit,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { intake: false });
      })
      .catch((err) => setIntakeMessage(String(err.message || err)));
  };

  const runPreflightLive = () => {
    if (!snapshot || !liveMode || preflightRunning) return;
    setPreflightRunning(true);
    setPreflightMessage("Running local preflight.");
    setPreflightEvent(null);
    fetch("/api/preflight", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: snapshot.project,
        rubric: (currentProjectEntry && currentProjectEntry.rubric) || snapshot.rubric,
        intake: (currentProjectEntry && currentProjectEntry.intake) || snapshot.intake,
        renderer: "decision_brief"
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok) {
            const error = new Error(payload.error || payload.stderr_tail || payload.stdout_tail || `preflight failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Run readiness", preserveSelection: true });
        if (payload.trace) setTraceContext(payload.trace);
        setPreflightEvent(payload);
        setPreflightMessage(
          payload.accepted
            ? snapshotRefreshMessage("Preflight accepted", payload)
            : "Preflight finished without an acceptance marker."
        );
      })
      .catch((err) => {
        if (err.payload) {
          setPreflightEvent(err.payload);
          if (err.payload.trace) setTraceContext(err.payload.trace);
          if (err.payload.snapshot) installSnapshot(err.payload.snapshot, { preferredLabel: "Run readiness", preserveSelection: true });
        }
        setPreflightMessage(String(err.message || err));
      })
      .finally(() => setPreflightRunning(false));
  };

  const sourceActionTargetLabel = (action) =>
    action === "evidence_bind" || action === "evidence_replay" ? "Evidence readiness" : "Source readiness";

  const runSourceActionLive = (action) => {
    if (!snapshot || !liveMode || sourceActionRunning) return;
    const params = liveProjectParams();
    setSourceActionRunning(true);
    setSourceActionMessage(`Running ${displayText(action)}.`);
    setSourceActionEvent({ action });
    fetch("/api/source-action", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        renderer: "decision_brief",
        action
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok) {
            const error = new Error(payload.error || payload.stderr_tail || payload.stdout_tail || `source action failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: sourceActionTargetLabel(action), preserveSelection: true });
        if (payload.trace) setTraceContext(payload.trace);
        setSourceActionEvent(payload);
        const writeEvent = sourceActionReceiptEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        if (payload.writes) {
          refreshLiveContextAfterWrite(params, { sources: true });
        } else {
          loadSourceListContext(params);
          loadClaimSupportContext(params);
        }
        setSourceActionMessage(
          payload.accepted
            ? snapshotRefreshMessage(`${payload.label || displayText(payload.action)} finished`, payload)
            : `${payload.label || displayText(payload.action)} finished with attention; inspect the command output.`
        );
      })
      .catch((err) => {
        if (err.payload) {
          setSourceActionEvent(err.payload);
          if (err.payload.trace) setTraceContext(err.payload.trace);
          if (err.payload.snapshot) installSnapshot(err.payload.snapshot, { preferredLabel: sourceActionTargetLabel(action), preserveSelection: true });
          const writeEvent = sourceActionReceiptEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
          if (err.payload.writes) {
            refreshLiveContextAfterWrite(params, { sources: true });
          } else {
            loadSourceListContext(params);
            loadClaimSupportContext(params);
          }
        }
        setSourceActionMessage(String(err.message || err));
      })
      .finally(() => setSourceActionRunning(false));
  };

  const saveCaseFileLive = (caseFile) => {
    if (!snapshot || !liveMode || caseFileSaving) return;
    const params = liveProjectParams();
    setCaseFileSaving(true);
    fetch("/api/case-file", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        case_file: caseFile
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok || payload.ok === false) {
            throw new Error(payload.error || `case file save failed: ${response.status}`);
          }
          return payload;
        })
      )
      .then((payload) => {
        setCaseFileSaveEvent(payload);
        setWriteReceiptEvent({
          kind: "case_file",
          row: payload.path || "case file",
          result: payload,
          snapshotError: ""
        });
        return refreshLiveContextAfterWrite(params);
      })
      .catch((err) => {
        const error = String(err.message || err);
        setCaseFileSaveEvent({ error });
        setLastRefreshResults([]);
        setWriteReceiptEvent({
          kind: "case_file",
          row: "case file",
          result: {
            receipt: {
              schema: CASE_FILE_WRITE_SCHEMA,
              status: "save_failed",
              error
            }
          },
          snapshotError: error
        });
      })
      .finally(() => setCaseFileSaving(false));
  };

  const loadFilePreview = (item) => {
    const previewPath = item && previewableRepoPath(item.value);
    if (!liveMode) {
      setFilePreview(null);
      setFilePreviewMessage("Start the local API to preview repository files.");
      return;
    }
    if (!previewPath) {
      setFilePreview(null);
      setFilePreviewMessage("Selected ref is not a previewable repository file.");
      return;
    }
    setFilePreview(null);
    setFilePreviewMessage(`Loading ${previewPath}.`);
    fetch(endpointUrl("/api/file", { path: previewPath }), { headers: { Accept: "application/json" } })
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
                  { value: selectedProjectKey || projectEntryKey(snapshot), onChange: handleProjectChange, disabled: loadingSnapshot },
                  projects.map((project) => {
                    const caseKey = projectEntryKey(project);
                    return h("option", { key: caseKey, value: caseKey }, projectOptionLabel(project));
                  })
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
      actionMessage ? h("div", { className: `mode-banner ${liveMode ? "live" : "static"}` }, actionMessage) : null,
      h(PendingEditsStrip, { items: pendingEditorItems }),
      h(NextMovePanel, { snapshot, selectedRow, setSelectedLabel, liveMode }),
      h(CaseDocket, { snapshot, selectedRow }),
      h(StageRail, { snapshot, setSelectedLabel }),
      h(Toolbar, { filter, query, setFilter, setQuery }),
      h(
        "section",
        { className: "main-grid" },
        filteredRows.length
          ? h(WorkbenchTable, { rows: filteredRows, selectedLabel: selectedRow && selectedRow.label, setSelectedLabel })
          : h(EmptyState),
        h(Inspector, { row: selectedRow, snapshot, liveMode, loadFilePreview, filePreview, filePreviewMessage })
      ),
      h(SourceEvidencePanel, {
        snapshot,
        traceContext,
        liveMode,
        onPreview: loadFilePreview,
        setSelectedLabel,
        sourceActionEvent,
        sourceActionMessage,
        sourceActionRunning,
        onRunSourceAction: runSourceActionLive
      }),
      h(
        "section",
        { className: "metrics", "aria-label": "Snapshot status" },
        h(Metric, { label: "Run readiness", value: snapshot.readiness, tone: "ready" }),
        h(Metric, { label: "Export", value: snapshot.report_status, tone: snapshot.report_status === "blocked" ? "attention" : "ready" }),
        h(Metric, { label: "Evidence rows", value: String(counts.total) }),
        h(Metric, { label: "Needs review", value: String(counts.attention), tone: counts.attention ? "attention" : "ready" })
      ),
      h(FirstFiveMinutePath, { snapshot, setSelectedLabel }),
      h(ClaimSummary, { snapshot }),
      h(CommandCockpit, { snapshot, selectedRow, traceContext, reportContext: reportPanelContext, healthContext, claimSupportContext, setSelectedLabel }),
      h(ProjectContextPanel, { projectEntry: currentProjectEntry, snapshot, liveMode, onPreview: loadFilePreview }),
      h(ProjectSwitchboard, { projects, selectedProjectKey, snapshot, liveMode, loading: loadingSnapshot, onSelect: openProject }),
      h(ProjectCreatePanel, {
        draft: projectCreateDraft,
        setDraft: setProjectCreateDraft,
        message: projectCreateMessage,
        creating: projectCreating,
        liveMode,
        projects,
        onCreate: createProjectLive
      }),
      h(SourceImportPanel, {
        draft: sourceImportDraft,
        setDraft: setSourceImportDraft,
        message: sourceImportMessage,
        importing: sourceImporting,
        event: sourceImportEvent,
        liveMode,
        sourceList: sourceListContext,
        onImport: importSourceLive,
        onPreview: loadFilePreview,
        onAddToIntake: addImportedSourceToIntakeDraft
      }),
      h(RawSourceManagerPanel, {
        sourceList: sourceListContext,
        draft: sourceEditDraft,
        setDraft: setSourceEditDraft,
        message: sourceEditMessage || sourceListMessage,
        editing: sourceEditing,
        event: sourceEditEvent,
        liveMode,
        onOpenSource: openRawSourceForEdit,
        onSave: saveRawSourceEdit,
        onReload: reloadSourceList,
        onPreview: loadFilePreview
      }),
      h(IntakeEditor, {
        draft: intakeDraft,
        setDraft: setIntakeDraft,
        liveMode,
        message: intakeMessage,
        onSave: saveIntakeDraft,
        onReload: refreshCurrentIntake,
        onPreviewRef: loadFilePreview
      }),
      h(TraceConsolePanel, { traceContext, message: traceMessage, liveMode, onPreviewSource: loadFilePreview }),
      h(PreflightRunPanel, { traceContext, event: preflightEvent, message: preflightMessage, running: preflightRunning, liveMode, onRun: runPreflightLive }),
      h(RunHistoryPanel, { runHistory: runHistoryContext, message: runHistoryMessage, liveMode, onPreview: loadFilePreview }),
      h(ClaimSupportPanel, { claimSupport: claimSupportContext, message: claimSupportMessage, liveMode, onPreview: loadFilePreview }),
      h(ReportContractPanel, { reportContext: reportPanelContext, message: reportContractMessage, liveMode, onPreview: loadFilePreview }),
      h(HealthActionsPanel, { healthContext, healthMessage, liveMode, onPreviewSource: loadFilePreview, onUseActionNote: useHealthActionNote }),
      h(BlockerPanel, { snapshot, setSelectedLabel }),
      h(CommandRail, { snapshot, selectedRow }),
      h(ProvenanceStrip, { rows: snapshot.rows || [] }),
      h(ReceiptHistoryPanel, { history: receiptHistory, message: receiptHistoryMessage, liveMode, onPreview: loadFilePreview }),
      h(CaseExportPanel, {
        snapshot,
        receiptHistory,
        projectEntry: currentProjectEntry,
        intakeDraft,
        sourceImportDraft,
        sourceEditDraft,
        traceContext,
        reportContext: reportPanelContext,
        healthContext,
        preflightEvent,
        sourceListContext,
        sourceActionEvent,
        sourceImportEvent,
        sourceEditEvent,
        runHistoryContext,
        claimSupportContext,
        writeReceiptEvent,
        refreshResults: lastRefreshResults,
        selectedRow,
        liveMode,
        saving: caseFileSaving,
        saveEvent: caseFileSaveEvent,
        onSave: saveCaseFileLive
      }),
      h(ReviewQueue, { row: selectedRow, reviewState: selectedReviewState, receiptHistory, snapshot, liveMode, onPreview: loadFilePreview }),
      reviewMessage ? h("div", { className: "review-message" }, reviewMessage) : null,
      h(ReviewWorkspace, { snapshot, row: selectedRow, reviewState: selectedReviewState, setReviewState: setSelectedReviewState, liveMode, applyReviewLive }),
      h(WriteReceiptPanel, { receiptEvent: writeReceiptEvent, refreshResults: lastRefreshResults, liveMode, onPreview: loadFilePreview }),
      h(RowActionWorkspace, {
        snapshot,
        row: selectedRow,
        actionState: selectedActionState,
        setActionState: setSelectedActionState,
        liveMode,
        applyRowActionLive
      })
    )
  );
}

createRoot(document.getElementById("root")).render(h(App));
