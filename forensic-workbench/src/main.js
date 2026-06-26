import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const h = React.createElement;
let modalBodyLockCount = 0;

function lockModalBody() {
  modalBodyLockCount += 1;
  document.body.classList.add("modal-open");
  return () => {
    modalBodyLockCount = Math.max(0, modalBodyLockCount - 1);
    if (!modalBodyLockCount) document.body.classList.remove("modal-open");
  };
}

class WorkbenchErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return h(
      "main",
      { className: "state-page error", role: "alert" },
      h("h1", null, "Project Workbench"),
      h("p", null, "The workbench hit a rendering error. Refresh after the fix is applied."),
      h("code", null, String(this.state.error.message || this.state.error))
    );
  }
}

const FILTERS = [
  { id: "all", label: "All project checks" },
  { id: "attention", label: "Needs review" },
  { id: "ready", label: "Ready" },
  { id: "neutral", label: "Recorded" }
];

const WORKSPACE_SECTIONS = [
  { id: "projects", label: "Projects", summary: "Open a project or add an intake", subnav: ["Current project", "All projects", "Add intake", "Files"] },
  { id: "overview", label: "Thesis", summary: "See the thesis, assumptions, evidence, and next test", subnav: ["Status", "Diagnosis", "Evidence"] },
  { id: "sources", label: "Files", summary: "Edit the intake, source files, and evidence files", subnav: ["File check", "Intake", "Add source", "Edit source"] },
  { id: "run", label: "Runs", summary: "Inspect the run plan, preflight, results, and advisories", subnav: ["Plan", "Preflight", "Start run", "Results", "Advisories"] },
  { id: "review", label: "Review", summary: "Save reviews, next steps, and receipts", subnav: ["Open issues", "Save review", "Save next step", "Receipts"] },
  { id: "save", label: "Report", summary: "Check report support and save the project file", subnav: ["Support check", "Report inputs", "Project file"] }
];

const WORKSPACE_DETAIL_COPY = {
  "overview:Status": {
    title: "Project Status",
    body: "See the thesis, evidence state, run readiness, and what needs review."
  },
  "overview:Diagnosis": {
    title: "Diagnosis",
    body: "Read the current thesis, assumptions, ruled-out alternatives, and what would change it."
  },
  "overview:Evidence": {
    title: "Evidence Files",
    body: "Find missing, stale, or disconnected inputs."
  },
  "sources:File check": {
    title: "File Check",
    body: "See whether the current inputs can support the project."
  },
  "sources:Intake": {
    title: "Edit Intake",
    body: "Edit the diagnosis, challenge, files, notes, and caveats."
  },
  "sources:Add source": {
    title: "Add Source",
    body: "Add a local source and stage it for the intake."
  },
  "sources:Edit source": {
    title: "Edit Source File",
    body: "Open and revise an existing source file."
  },
  "run:Plan": {
    title: "Run Plan",
    body: "Inspect the next local step and keep the command details visible when you need it."
  },
  "run:Preflight": {
    title: "Preflight",
    body: "Run the cheapest check before heavier work."
  },
  "run:Start run": {
    title: "Start Run",
    body: "Start the next project run after preflight accepts the inputs."
  },
  "run:Results": {
    title: "Run Results",
    body: "Compare recent scores, weak points, evidence gaps, and support state."
  },
  "run:Advisories": {
    title: "Advisories",
    body: "Turn health findings and suggested next steps into saved project work."
  },
  "save:Support check": {
    title: "Support Check",
    body: "See what the report still needs before you rely on it."
  },
  "save:Report inputs": {
    title: "Report Inputs",
    body: "Inspect support, provenance, and input binding."
  },
  "save:Project file": {
    title: "Save Project File",
    body: "Save the current receipts and file paths."
  },
  "review:Open issues": {
    title: "Open Issues",
    body: "Choose the evidence, run, or report issue to inspect."
  },
  "review:Save review": {
    title: "Save Review",
    body: "Save whether this project check is reviewed, deferred, or holding the report."
  },
  "review:Save next step": {
    title: "Save Next Step",
    body: "Record what should happen next."
  },
  "review:Receipts": {
    title: "Receipts",
    body: "Check what changed and what refreshed."
  },
  "projects:Current project": {
    title: "Current Project",
    body: "Review the open project, next step, and support state."
  },
  "projects:All projects": {
    title: "All Projects",
    body: "Open a ready project or find a project folder that still needs an intake."
  },
  "projects:Add intake": {
    title: "Add Project Intake",
    body: "Create a project, or add the intake that makes an existing folder editable."
  },
  "projects:Files": {
    title: "Project Files",
    body: "Inspect where this project lives in the repository."
  }
};

const REVIEW_ACTIONS = [
  { id: "reviewed", label: "Mark reviewed" },
  { id: "deferred", label: "Defer" },
  { id: "blocked", label: "Hold for support" }
];

const ITEM_ACTIONS = [
  { id: "next_step", label: "Next step" },
  { id: "needs_source", label: "Needs source" },
  { id: "ready_to_run", label: "Run checks" },
  { id: "export_blocker", label: "Fix report support" }
];

const ITEM_ACTION_LABELS = Object.fromEntries(ITEM_ACTIONS.map((action) => [action.id, action.label]));
const REPORT_CONTRACT_SCHEMA = "ztare-forensic-workbench-report-contract-v1";
const CASE_FILE_WRITE_SCHEMA = "ztare-forensic-workbench-case-file-write-receipt-v1";
const SOURCE_TYPES = ["source_evidence", "seed_hypothesis", "research_question", "collection_todo", "untyped"];
const SOURCE_TYPE_LABELS = {
  source_evidence: "Evidence file",
  seed_hypothesis: "Starting note",
  research_question: "Research question",
  collection_todo: "To collect",
  untyped: "Other"
};

const SOURCE_TYPE_HELP = {
  source_evidence: "Use this file as support for the diagnosis.",
  seed_hypothesis: "Use this file as an early project note.",
  research_question: "Use this file to capture an open question.",
  collection_todo: "Use this file as something to collect or verify later.",
  untyped: "Keep this file in the project without assigning a specific role."
};
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
  { id: "save", label: "Report", rowLabel: "Report support" }
];

const DISPLAY_OVERRIDES = {
  valid_packet: "valid intake",
  missing_packet: "missing evidence file",
  ready_for_in_loop_candidate: "ready for run",
  ready_for_evidence_prepare: "ready for evidence prep",
  report_blockers_present: "report needs support",
  report_support_unavailable: "report support unavailable",
  synthesis_input_binding_unbound: "report input is not connected",
  runtime_risks_present: "runtime risks present",
  loop_admission: "run receipt",
  "loop admission preflight path": "preflight receipt path",
  "Loop admission": "Preflight receipt",
  "Bounded claim": "Working diagnosis",
  "Non-claims": "Ruled-out alternatives",
  "Assumptions and constraints": "Assumptions and constraints",
  "Source readiness": "Source files",
  "Evidence readiness": "Evidence files",
  "Run readiness": "Run check",
  "Next falsifier": "What would change it",
  "Latest review receipt": "Latest review",
  "Latest intake edit": "Latest intake change",
  "Report/export": "Report support",
  report_export: "Report support",
  report_support: "Report support",
  blocked: "needs attention",
  "Latest item action": "Latest next step",
  "latest item action": "latest next step",
  item_action: "saved next step",
  latest_item_action: "latest saved next step",
  row_action: "saved next step",
  latest_row_action: "latest saved next step",
  no_action_saved: "no next step saved",
  no_intake_edit_saved: "no saved intake change",
  next_step: "next step",
  needs_source: "needs source",
  ready_to_run: "run checks",
  export_blocker: "fix report support",
  public_example_intake: "example intake",
  project_local_intake: "project intake",
  project_compiled_evidence: "project evidence file",
  project_run_history: "project run history",
  project_report_support: "project report support",
  unknown_intake_source: "intake source unknown",
  carrier_chain: "run checks",
  graph_carriers: "graph summaries",
  kernel_entry: "run readiness",
  weak_gp233_linkage: "evidence links need repair",
  stale_trajectory_output: "run-history archive is stale",
  unconsumed_surface: "work log is missing",
  repair_source_emitter: "repair source logs"
};

function kindLabel(kind) {
  if (kind === "attention") return "Needs review";
  if (kind === "ready") return "Ready";
  return "Recorded";
}

function displayText(value) {
  const raw = String(value || "none");
  return (DISPLAY_OVERRIDES[raw] || raw)
    .replace(/_/g, " ")
    .replace(/^Reject or demote the claim if\s+/i, "Revise the diagnosis if ")
    .replace(/\bsource-health\b/gi, "source warning")
    .replace(/\baction-intelligence\b/gi, "advisory guidance")
    .replace(/\bkernel\b/gi, "run")
    .replace(/\bcarrier chain\b/gi, "run checks")
    .replace(/\bgraph carriers\b/gi, "graph summaries")
    .replace(/\bGP-?233\b/gi, "evidence ledger")
    .replace(/\bGP-?230\b/gi, "forecast record")
    .replace(/\bGP-(\d+)\b/g, "research record GP-$1");
}

function sourceTypeLabel(value) {
  return SOURCE_TYPE_LABELS[value] || displayText(value || "source");
}

function itemLabel(rowOrLabel) {
  if (rowOrLabel && typeof rowOrLabel === "object" && rowOrLabel.display_label) return String(rowOrLabel.display_label);
  const label = typeof rowOrLabel === "string" ? rowOrLabel : (rowOrLabel && rowOrLabel.label) || "";
  return displayText(label || "project check");
}

function itemStatus(row) {
  if (row && row.display_status) return String(row.display_status);
  return displayText(row && row.status);
}

function itemDetail(row) {
  if (row && row.display_detail) return String(row.display_detail);
  return displayMessage(row && row.detail);
}

function itemDestination(row, fallback = ["overview", "Diagnosis"]) {
  const label = String((row && row.label) || "");
  if (!label) return fallback;
  if (label === "Source readiness" || label === "Evidence readiness") return ["sources", "File check"];
  if (label === "Project intake" || label === "Bounded claim" || label === "Non-claims" || label === "Next falsifier") return ["sources", "Intake"];
  if (label === "Assumptions and constraints") return ["overview", "Diagnosis"];
  if (label === "Preflight" || label === "Run readiness") return ["run", "Preflight"];
  if (label === "Report support") return ["save", "Support check"];
  if (label === "Latest review receipt") return ["review", "Receipts"];
  return fallback;
}

function itemActionLabel(row, fallback = "Inspect") {
  const [workspace, subsection] = itemDestination(row, ["overview", "Diagnosis"]);
  if (workspace === "sources" && subsection === "File check") return row && row.kind === "attention" ? "Fix inputs" : "Inspect inputs";
  if (workspace === "sources" && subsection === "Intake") return "Edit intake";
  if (workspace === "run") return "Run preflight";
  if (workspace === "save") return "Review report support";
  if (workspace === "review" && subsection === "Receipts") return "Open receipts";
  return fallback;
}

function openItemDestination(row, onOpenDetail, fallback = ["overview", "Diagnosis"]) {
  const [workspace, subsection] = itemDestination(row, fallback);
  if (onOpenDetail) onOpenDetail(workspace, subsection);
}

function targetLabel(value) {
  const raw = String(value || "");
  if (!raw) return "";
  return displayText(raw);
}

function compactWhitespace(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function shortText(value, maxLength = 180) {
  const text = compactWhitespace(value);
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
}

function firstSentence(value) {
  const text = compactWhitespace(value);
  if (!text) return "";
  const match = text.match(/^(.+?[.!?])(?:\s|$)/);
  return match ? match[1] : text;
}

function titleFromSlug(value) {
  const text = compactWhitespace(String(value || "").replace(/[_-]+/g, " ").replace(/\bdemo\b/gi, ""));
  if (!text) return "Local project";
  return text.replace(/\b\w/g, (char) => char.toUpperCase());
}

function projectFolderSuggestion(...values) {
  const source = values.map(compactWhitespace).find(Boolean) || "new_project";
  const claimSubject = source.match(/best-supported explanation for (?:the )?(.+?) is /i);
  const withoutLead = source
    .replace(/^(check|verify|test|investigate|diagnose|review)\s+(whether|if|why|how|the)?\s*/i, "")
    .replace(/^(a|an|the)\s+/i, "")
    .replace(/\bbest-supported explanation\b/gi, "diagnosis");
  const candidate = claimSubject ? `${claimSubject[1]} diagnosis` : withoutLead;
  const slug = candidate
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48)
    .replace(/_+$/g, "");
  return slug || "new_project";
}

function cleanProjectSubject(value) {
  return compactWhitespace(String(value || "").replace(/-/g, " ").replace(/\bspike\b/gi, ""));
}

function humanProjectTitle(snapshot, claimRow) {
  const claim = compactWhitespace((claimRow && claimRow.detail) || "");
  const match = claim.match(/best-supported explanation for (?:the )?(.+?) is /i);
  if (match) {
    const subject = cleanProjectSubject(match[1]);
    if (subject) return `${subject} diagnosis`;
  }
  return titleFromSlug((snapshot && snapshot.project) || "Local project");
}

function diagnosisLead(value) {
  const text = compactWhitespace(value);
  const match = text.match(/best-supported explanation for (?:the )?(.+?) is (.+?);/i);
  if (match) return `Best-supported cause for ${cleanProjectSubject(match[1])}: ${shortText(match[2], 140)}.`;
  return shortText(firstSentence(text) || text, 220);
}

function falsifierLead(value) {
  const text = compactWhitespace(value).replace(/^Reject or demote the claim if\s+/i, "");
  return shortText(text, 155);
}

function projectStatusSentence(snapshot, counts, sourceRow, evidenceRow) {
  const inputReady = sourceRow && sourceRow.kind !== "attention" && evidenceRow && evidenceRow.kind !== "attention";
  const inputText = inputReady ? "Inputs are attached" : "Inputs need review";
  const reviewText = counts.attention ? `${counts.attention} project check${counts.attention === 1 ? "" : "s"} needs review` : "no pending project checks";
  const reportText = `report ${reportStatusLabel(snapshot.report_status, snapshot.display_report_status).toLowerCase()}`;
  return `${inputText}; ${reviewText}; ${reportText}.`;
}

function formatWorkbenchTemplate(template, values = {}) {
  return String(template || "").replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key) => String(values[key] || ""));
}

function formatWriteTemplateItems(contract, values = {}, fallbackTemplates = []) {
  const displayTemplates = Array.isArray(contract && contract.display_write_path_templates)
    ? contract.display_write_path_templates
    : [];
  if (displayTemplates.length) {
    return displayTemplates
      .map((item) => ({
        label: item.label || writePathLabel(item.path_template || item.path || item.template),
        path: formatWorkbenchTemplate(item.path_template || item.path || item.template, values)
      }))
      .filter((item) => item.path);
  }
  return fallbackTemplates
    .map((template) => formatWorkbenchTemplate(template, values))
    .filter(Boolean)
    .map((path) => ({ label: writePathLabel(path), path }));
}

function displayMessage(value) {
  return String(value || "")
    .replace(/\bReport\/export\b/g, "Report support")
    .replace(/\bready_for_run=True\b/g, "ready for run: yes")
    .replace(/\bready_for_run=False\b/g, "ready for run: no")
    .replace(/\bready_for_in_loop_candidate\b/g, "ready for run")
    .replace(/\bready_for_evidence_prepare\b/g, "ready for evidence prep")
    .replace(/\bintake_hash_verified=True\b/g, "intake hash verified: yes")
    .replace(/\bintake_hash_verified=False\b/g, "intake hash verified: no")
    .replace(/\breceipt_count=/g, "receipts: ")
    .replace(/\beval_history_rows=/g, "run records: ")
    .replace(/\blatest_exit=/g, "latest exit: ")
    .replace(/\bsource_index=/g, "file index: ")
    .replace(/\bsource index:/gi, "file index:")
    .replace(/\boutput_binding=/g, "evidence connection: ")
    .replace(/\boutput binding:/gi, "evidence connection:")
    .replace(/\breplay=/g, "replay: ")
    .replace(/\breadiness=/g, "readiness: ")
    .replace(/\bevidence_refs\[(\d+)\]/g, "evidence file $1")
    .replace(/\bevidence_refs=/g, "evidence refs: ")
    .replace(/\bsha256=/g, "hash: ")
    .replace(/\bsaved item action\b/gi, "saved next step")
    .replace(/\bitem action\b/gi, "next step")
    .replace(/\bitem-action\b/gi, "next-step")
    .replace(/\blatest item action\b/gi, "latest next step")
    .replace(/\brow action\b/gi, "next step")
    .replace(/\brow-action\b/gi, "next-step")
    .replace(/\bblocked\b/gi, "needs attention")
    .replace(/\bblockers\b/gi, "issues")
    .replace(/\bblocker\b/gi, "issue")
    .replace(/\bcompiled evidence packet\b/gi, "compiled evidence file")
    .replace(/\bevidence packet\b/gi, "evidence file")
    .replace(/\bpacket boundary\b/gi, "intake boundary")
    .replace(/\bsource-health\b/gi, "source warning")
    .replace(/\baction-intelligence\b/gi, "advisory guidance")
    .replace(/\bkernel\b/gi, "run")
    .replace(/\bcarrier chain\b/gi, "run checks")
    .replace(/\bgraph carriers\b/gi, "graph summaries");
}

function jsonResponseOrError(response, fallbackMessage) {
  return response.json().catch(() => ({})).then((payload) => {
    if (!response.ok || payload.ok === false) {
      const error = new Error(payload.error || fallbackMessage || `request failed: ${response.status}`);
      error.payload = payload;
      throw error;
    }
    return payload;
  });
}

function refusedWriteEvent(kind, row, err) {
  const payload = err && err.payload;
  const writeBoundary = payload && payload.write_boundary;
  if (!writeBoundary || writeBoundary.writes_project_files) return null;
  return {
    kind,
    row: row || "write",
    noWrite: true,
    result: {
      ok: false,
      error: payload.error || "The server did not save this change.",
      write_boundary: writeBoundary,
      receipt: {
        schema: "ztare-forensic-workbench-refused-write-v1",
        status: "not_saved",
        error: payload.error || "The server did not save this change."
      }
    },
    snapshotError: ""
  };
}

function preflightWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  return {
    kind: "preflight",
    row: "Preflight",
    result: {
      ...payload,
      receipt: {
        schema: payload.schema || "ztare-forensic-workbench-preflight-v1",
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        command: payload.command || "",
        returncode: payload.returncode,
        stdout_tail: payload.stdout_tail || "",
        stderr_tail: payload.stderr_tail || ""
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function boundedRunWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  return {
    kind: "bounded_run",
    row: "Run",
    result: {
      ...payload,
      receipt: {
        schema: payload.schema || "ztare-forensic-workbench-bounded-run-v1",
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        command: payload.command || "",
        returncode: payload.returncode,
        stdout_tail: payload.stdout_tail || "",
        stderr_tail: payload.stderr_tail || ""
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function projectCreateWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  const createdPaths = Array.isArray(payload.created_paths) ? payload.created_paths.filter(Boolean) : [];
  return {
    kind: "project_create",
    row: payload.project || "Project setup",
    result: {
      ...payload,
      receipt: {
        schema: payload.schema || "ztare-forensic-workbench-project-create-v1",
        status: payload.accepted ? "accepted" : createdPaths.length ? "partial" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        path: payload.project ? `projects/${payload.project}` : "",
        created_paths: createdPaths,
        action: payload.accepted ? "created project" : createdPaths.length ? "partial create" : "create attention"
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function guidanceText(value) {
  return displayText(value)
    .replace(/\bGP-?233\b/gi, "evidence ledger")
    .replace(/\bgp233\b/gi, "evidence ledger")
    .replace(/\bGP-?230\b/gi, "forecast record")
    .replace(/\bgp230\b/gi, "forecast record")
    .replace(/\bmarkdown-only\b/gi, "doc-only")
    .replace(/\bsurfacing-event ledger\b/gi, "work ledger")
    .replace(/\bsurfacing event ledger\b/gi, "work ledger")
    .replace(/\btrajectory archive\b/gi, "run-history archive");
}

const GUIDANCE_LABELS = {
  weak_gp233_linkage: "Evidence links need repair",
  stale_trajectory_output: "Run-history archive is stale",
  unconsumed_surface: "Work log is missing",
  source_compilation_defect: "Source compilation needs repair",
  repair_source_emitter: "Repair source logs",
  split_contract: "Split into a smaller question",
  ask_another_independent_agent: "Ask for another independent check",
  defer: "Defer",
  surface_trajectory_cluster: "Review related run history",
  diagnostic_only: "Diagnostic only",
  none_advisory_only: "Advisory only",
  gp230_read_model: "forecast record summary"
};

function guidanceLabel(value) {
  const raw = String(value || "");
  const mapped = GUIDANCE_LABELS[raw] || raw;
  return guidanceText(mapped).replace(/_/g, " ");
}

function warningCountText(row) {
  if (row && row.observed_count !== undefined && row.expected_count !== undefined) {
    return `${row.observed_count}/${row.expected_count}`;
  }
  return "";
}

function recommendationMeta(row) {
  return [
    row.display_domain || (row.domain ? guidanceLabel(row.domain) : ""),
    row.display_confidence || (row.confidence ? guidanceLabel(row.confidence) : ""),
    row.display_execution_authority || (row.execution_authority ? guidanceLabel(row.execution_authority) : ""),
    row.display_source || (row.source ? guidanceLabel(row.source) : "advisory")
  ]
    .filter(Boolean)
    .join(" | ");
}

function recommendationBoundary(row) {
  const authority = row.display_execution_authority || (row.execution_authority ? guidanceLabel(row.execution_authority) : "Advisory only");
  const confidence = row.display_confidence || (row.confidence ? guidanceLabel(row.confidence) : "");
  const checks = Array.isArray(row.display_blocking_checks) && row.display_blocking_checks.length
    ? row.display_blocking_checks.join(", ")
    : "";
  return [
    authority,
    confidence,
    checks ? `requires: ${checks}` : ""
  ].filter(Boolean).join(" / ");
}

function recommendationEstimate(row) {
  return [
    typeof row.p_success === "number" ? `estimated success ${Math.round(row.p_success * 100)}%` : "",
    typeof row.expected_cost_agent_minutes === "number" ? `expected effort ${row.expected_cost_agent_minutes} min` : ""
  ]
    .filter(Boolean)
    .join(" | ");
}

function reportStatusLabel(status, displayStatus = "") {
  if (displayStatus) {
    const rendered = String(displayStatus);
    return rendered.charAt(0).toUpperCase() + rendered.slice(1);
  }
  if (String(status || "") === "blocked") return "Needs support";
  const text = displayText(status || "unknown");
  if (text === "available") return "Available";
  if (text === "ready") return "Ready";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function snapshotRefreshMessage(base, payload) {
  const snapshotError = displayMessage(payload && payload.snapshot_error);
  if (snapshotError) return `${base}. Project refresh failed: ${snapshotError}`;
  if (payload && payload.snapshot) return `${base} and refreshed the project.`;
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
  add(items, "Command detail", row.command, "command");
  add(items, "Receipt", row.receipt, "receipt");
  add(items, "Review file", row.review_artifact, "review");
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
    .slice(0, 80) || "project";
}

function caseFileDownloadName(snapshot) {
  const project = safeFilePart((snapshot && snapshot.project) || "ztare");
  const intake = safeFilePart((snapshot && snapshot.intake) || "project");
  return `${project}_${intake}_project_file.json`;
}

function caseScopedDownloadName(snapshot, rowKey, suffix) {
  const project = safeFilePart((snapshot && snapshot.project) || "ztare");
  const intake = safeFilePart((snapshot && snapshot.intake) || "project");
  const item = safeFilePart(rowKey || "item");
  return `${project}_${intake}_${item}_${suffix}.json`;
}

function caseKey(snapshot) {
  const project = String((snapshot && snapshot.project) || "").trim();
  const intake = String((snapshot && snapshot.intake) || "").trim();
  return intake ? `${project}::${intake}` : project;
}

function useSha256Hex(value) {
  const [digest, setDigest] = useState("");
  useEffect(() => {
    let cancelled = false;
    const text = String(value || "");
    if (!text || !window.crypto || !window.crypto.subtle) {
      setDigest("");
      return () => {
        cancelled = true;
      };
    }
    window.crypto.subtle
      .digest("SHA-256", new TextEncoder().encode(text))
      .then((buffer) => {
        if (cancelled) return;
        const bytes = Array.from(new Uint8Array(buffer));
        setDigest(bytes.map((byte) => byte.toString(16).padStart(2, "0")).join(""));
      })
      .catch(() => {
        if (!cancelled) setDigest("");
      });
    return () => {
      cancelled = true;
    };
  }, [value]);
  return digest;
}

function rowSlug(label) {
  return String(label || "item").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "item";
}

function checkSlugMatches(actual, expected) {
  if (actual === expected) return true;
  const reportAliases = new Set(["report_export", "report_support"]);
  return reportAliases.has(actual) && reportAliases.has(expected);
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

function emptyProjectCreateDraft() {
  return {
    project: "",
    task: "",
    bounded_claim: "",
    next_falsifier: "",
    notes: "",
    source_refs_text: "",
    evidence_refs_text: "",
    non_claims_text: ""
  };
}

function uniqueLines(values) {
  const seen = new Set();
  const lines = [];
  (values || []).forEach((value) => {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) return;
    seen.add(text);
    lines.push(text);
  });
  return lines;
}

function projectCreateDraftFromFolder(projectOrFolder, currentDraft = emptyProjectCreateDraft()) {
  if (!projectOrFolder) return currentDraft;
  const folder = typeof projectOrFolder === "string" ? { project: projectOrFolder } : projectOrFolder;
  const project = String(folder.project || "").trim();
  if (!project) return currentDraft;

  const projectChanged = String(currentDraft.project || "").trim() !== project;
  const sourceRefs = uniqueLines(folder.raw_preview_files || []);
  const workspaceRefs = uniqueLines(folder.workspace_preview_files || []);
  const notes = [
    folder.project_dir ? `Existing folder: ${folder.project_dir}` : `Existing folder: projects/${project}`,
    workspaceRefs.length ? `Workspace samples:\n${workspaceRefs.join("\n")}` : ""
  ].filter(Boolean).join("\n\n");

  return {
    ...currentDraft,
    project,
    task: projectChanged || !String(currentDraft.task || "").trim()
      ? `Review ${titleFromSlug(project)}`
      : currentDraft.task,
    notes: projectChanged || !String(currentDraft.notes || "").trim()
      ? notes
      : currentDraft.notes,
    source_refs_text: projectChanged || !String(currentDraft.source_refs_text || "").trim()
      ? sourceRefs.join("\n")
      : currentDraft.source_refs_text
  };
}

function backgroundProjectFolder(project) {
  const text = String(project || "");
  return (
    text.startsWith("_") ||
    text.startsWith("backtest_") ||
    text.startsWith("recursive_bayesian_") ||
    text.startsWith("simulation_god_") ||
    text.startsWith("tsmc_fragility_")
  );
}

function folderHiddenByDefault(folder) {
  if (!folder) return false;
  if (typeof folder.hidden_by_default === "boolean") return folder.hidden_by_default;
  return backgroundProjectFolder(folder.project);
}

function folderHasCaseMaterial(folder) {
  if (!folder) return false;
  if (typeof folder.has_project_files === "boolean") return folder.has_project_files;
  if (typeof folder.has_case_material === "boolean") return folder.has_case_material;
  return Boolean(
    folder.raw_file_count
    || folder.raw_source_file_count
    || folder.workspace_file_count
    || folder.raw_exists
    || folder.workspace_exists
    || folder.source_type_map_exists
    || folder.intake_count
  );
}

function cappedCountText(count, capped) {
  const value = Number(count || 0);
  return capped ? `${value}+` : String(value);
}

function projectInventoryFileSummary(project, refSummary = {}) {
  if (refSummary.total) return `${refSummary.present || 0}/${refSummary.total} intake files`;
  const sourceCount = Number(project.raw_source_file_count ?? project.raw_file_count ?? 0);
  const workspaceCount = Number(project.workspace_file_count ?? 0);
  const sourceText = sourceCount
    ? `${cappedCountText(sourceCount, project.raw_source_file_count_capped || project.raw_file_count_capped)} source`
    : "";
  const workspaceText = workspaceCount
    ? `${cappedCountText(workspaceCount, project.workspace_file_count_capped)} workspace`
    : "";
  const parts = [sourceText, workspaceText].filter(Boolean);
  if (parts.length) return parts.join(" / ");
  if (project.has_project_files || project.has_case_material) return "project files present";
  return "empty folder";
}

function projectInventorySort(a, b) {
  const aOpen = a && (a.openable || a.intake) ? 1 : 0;
  const bOpen = b && (b.openable || b.intake) ? 1 : 0;
  if (aOpen !== bOpen) return bOpen - aOpen;
  const aHidden = folderHiddenByDefault(a) ? 1 : 0;
  const bHidden = folderHiddenByDefault(b) ? 1 : 0;
  if (aHidden !== bHidden) return aHidden - bHidden;
  const aFiles = folderHasCaseMaterial(a) ? 1 : 0;
  const bFiles = folderHasCaseMaterial(b) ? 1 : 0;
  if (aFiles !== bFiles) return bFiles - aFiles;
  return String((a && a.project) || "").localeCompare(String((b && b.project) || ""));
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
  if (receipt.project_key) return receipt.project_key === caseKey;
  if (receipt.case_key) return receipt.case_key === caseKey;
  if (receipt.intake && intake) return receipt.intake === intake;
  return true;
}

function latestReceiptForRow(receiptHistory, row, kind, context) {
  if (!row) return null;
  const slug = rowSlug(row.label);
  const acceptedKinds = kind === "next_step" ? new Set(["next_step", "row_action"]) : new Set([kind]);
  return ((receiptHistory && receiptHistory.receipts) || []).find((receipt) => {
    if (!acceptedKinds.has(receipt.kind)) return false;
    if (!receiptMatchesCase(receipt, context)) return false;
    if (checkSlugMatches(receipt.project_check_slug, slug)) return true;
    if (checkSlugMatches(receipt.item_slug, slug)) return true;
    if (checkSlugMatches(receipt.row_slug, slug)) return true;
    if (checkSlugMatches(rowSlug(receipt.project_check_label || receipt.check_label || receipt.display_label || receipt.item_label || ""), slug)) return true;
    return checkSlugMatches(rowSlug(receipt.row || ""), slug);
  }) || null;
}

function receiptTargetLabel(receipt, receiptEvent = {}) {
  if (!receipt && !receiptEvent) return "";
  return targetLabel(
    (receipt && (receipt.project_check_label || receipt.check_label || receipt.display_label || receipt.item_label || receipt.project_check_slug || receipt.item_slug || receipt.row || receipt.relative_raw_path || receipt.intake_path || receipt.project_file_path || receipt.case_file_path)) ||
      receiptEvent.project_check_label ||
      receiptEvent.item_label ||
      receiptEvent.row ||
      ""
  );
}

function receiptArtifactPath(receipt) {
  if (!receipt) return "";
  const createdPaths = Array.isArray(receipt.created_paths) ? receipt.created_paths.filter(Boolean) : [];
  return receipt.review_file_path || receipt.action_file_path || receipt.project_file_path || receipt.case_file_path || receipt.source_path || receipt.intake_path || createdPaths[0] || "";
}

function receiptChangeSummary(receipt, kind = "") {
  if (!receipt) return "";
  const parts = [];
  const fields = (receipt.updated_fields || []).map(displayFieldName).filter(Boolean);
  const createdPaths = Array.isArray(receipt.created_paths) ? receipt.created_paths.filter(Boolean) : [];
  if (fields.length) parts.push(`fields: ${fields.join(", ")}`);
  if (createdPaths.length) parts.push(`created: ${createdPaths.length} path${createdPaths.length === 1 ? "" : "s"}`);
  if (receipt.decision) parts.push(`review status: ${displayText(receipt.decision)}`);
  if (receipt.action) parts.push(`next step: ${displayText(receipt.action)}`);
  if (receipt.source_type) parts.push(`source type: ${sourceTypeLabel(receipt.source_type)}`);
  if (receipt.binding_mode) parts.push(`binding: ${displayText(receipt.binding_mode)}`);
  if (receipt.project_check_count !== undefined || receipt.item_count !== undefined || receipt.row_count !== undefined || receipt.command_count !== undefined || receipt.receipt_count !== undefined) {
    parts.push(`project file: ${receipt.project_check_count ?? receipt.item_count ?? receipt.row_count ?? 0} project checks, ${receipt.command_count || 0} command details, ${receipt.receipt_count || 0} receipts`);
  }
  if (!parts.length && kind) parts.push(displayText(kind));
  return parts.join(" / ");
}

function receiptCaseSummary(receipt) {
  if (!receipt) return "";
  const parts = [];
  if (receipt.project) parts.push(`project ${receipt.project}`);
  else if (receipt.project_key) parts.push(`project ${receipt.project_key}`);
  else if (receipt.case_key) parts.push(`project ${receipt.case_key}`);
  if (receipt.intake) parts.push(`intake ${receipt.intake}`);
  if (receipt.rubric && receipt.rubric !== receipt.project) parts.push(`rubric ${receipt.rubric}`);
  return parts.join(" / ");
}

function actionIntelligenceNote(row, fallback = "Inspect guidance") {
  if (!row) return fallback;
  const refs = evidenceRefDisplayItems(row).map((item) => `${item.label}: ${item.path}`);
  const issue = row.display_issue_type || (row.issue_type ? guidanceLabel(row.issue_type) : "");
  const why = row.display_blocking_rule || (row.blocking_rule ? guidanceText(row.blocking_rule) : "");
  const scope = row.display_scope || (row.scope ? guidanceLabel(row.scope) : "");
  const area = row.display_domain || (row.domain ? guidanceLabel(row.domain) : "");
  const reason = row.display_rationale || (row.rationale ? guidanceText(row.rationale) : "");
  const parts = [
    row.display_recommended_action || guidanceLabel(row.recommended_action || row.issue_type || fallback),
    issue ? `issue: ${issue}` : "",
    why ? `why: ${why}` : "",
    scope ? `scope: ${scope}` : "",
    area ? `area: ${area}` : "",
    reason ? `reason: ${reason}` : "",
    refs.length ? `evidence: ${refs.slice(0, 4).join(", ")}` : ""
  ].filter(Boolean);
  return parts.join(" | ");
}

function evidenceRefDisplayItems(row) {
  if (!row) return [];
  const displayRefs = Array.isArray(row.display_evidence_refs) ? row.display_evidence_refs.filter(Boolean) : [];
  if (displayRefs.length) {
    return displayRefs
      .map((item) => {
        if (typeof item === "string") return { label: "Evidence file", path: item };
        return {
          label: item.label || "Evidence file",
          path: item.path || item.value || ""
        };
      })
      .filter((item) => item.path);
  }
  const refs = Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean) : [];
  return refs.map((path) => ({ label: "Evidence file", path }));
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
  if (action === "export_blocker") return rowByLabel(rows, "Report support") || activeBlocker(rows) || selectedRow;
  if (action === "ready_to_run") return rowByLabel(rows, "Run readiness") || rowByLabel(rows, "Preflight") || selectedRow;
  return selectedRow || activeBlocker(rows) || rowByLabel(rows, "Report support") || rowByLabel(rows, "Run readiness") || rows[0] || null;
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

function previewFileTitle(liveMode, previewable, readyTitle = "Preview the saved file") {
  if (!liveMode) return "Start the workbench server to preview files";
  if (!previewable) return "Saved file is not a repository file";
  return readyTitle;
}

function uniqueBackingFiles(items) {
  const seen = new Set();
  return (items || [])
    .map((item) => ({
      label: displayText(item && item.label ? item.label : "File"),
      path: repoPathCandidate(item && (item.path || item.value))
    }))
    .filter((item) => {
      if (!item.path || seen.has(item.path)) return false;
      seen.add(item.path);
      return true;
    })
    .sort(projectInventorySort);
}

function buildReviewFile(snapshot, row, reviewState) {
  if (!row) return "";
  const itemSlug = rowSlug(row.label);
  const payload = {
    schema: "ztare-forensic-workbench-review-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    intake: snapshot.intake || "",
    project_key: projectEntryKey(snapshot),
    case_key: projectEntryKey(snapshot),
    project_check_label: itemLabel(row),
    project_check_slug: itemSlug,
    item_label: itemLabel(row),
    item_slug: itemSlug,
    row: row.label,
    row_slug: itemSlug,
    row_status: itemStatus(row),
    decision: reviewState.decision || "unreviewed",
    note: reviewState.note || "",
    evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
  };
  return JSON.stringify(payload, null, 2);
}

function buildRowActionFile(snapshot, row, actionState) {
  if (!row) return "";
  const itemSlug = rowSlug(row.label);
  const payload = {
    schema: "ztare-forensic-workbench-row-action-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    intake: snapshot.intake || "",
    project_key: projectEntryKey(snapshot),
    case_key: projectEntryKey(snapshot),
    project_check_label: itemLabel(row),
    project_check_slug: itemSlug,
    item_label: itemLabel(row),
    item_slug: itemSlug,
    row: row.label,
    row_slug: itemSlug,
    row_status: itemStatus(row),
    action: actionState.action || "next_step",
    note: actionState.note || "",
    evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
  };
  return JSON.stringify(payload, null, 2);
}

function sourceActionReceiptEvent(payload) {
  if (!payload || !payload.writes) return null;
  const parsed = payload.parsed_output || {};
  const payloadReceipt = payload.receipt || {};
  const receiptPath = payload.receipt_path || parsed.receipt_path || parsed.path || parsed.source_index_receipt || "";
  const latestPath = payload.latest || receiptPath;
  const sourcePath = payloadReceipt.source_path || parsed.source_index || parsed.workspace_meta || parsed.provenance_path || parsed.path || "";
  const receipt = payloadReceipt.schema ? payloadReceipt : parsed.receipt || {
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
    row: payload.label || displayText(payload.action || "source check"),
    result: {
      ...payload,
      receipt,
      receipt_path: receiptPath,
      latest: latestPath
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function nestedReceiptResult(payload, key) {
  const nested = (payload && payload[key]) || {};
  return {
    ...nested,
    receipt: nested.receipt || {},
    ledger: nested.ledger || "",
    latest: nested.latest || "",
    receipt_path: nested.ledger || "",
    write_boundary: (payload && payload.write_boundary) || {}
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
    h("span", null, detail.accepted ? "File check passed" : "File check needs attention"),
    detail.command ? h("code", null, detail.command) : null,
    output ? h("p", null, output) : null,
    detail.returncode === null || detail.returncode === undefined
      ? null
      : h("small", null, `exit ${detail.returncode}`)
  );
}

function buildCaseFile(snapshot, receiptHistory, context = {}) {
  const rows = (snapshot && snapshot.rows) || [];
  const items = rows.map((row) => ({
    label: row.label,
    display_label: itemLabel(row),
    status: itemStatus(row),
    raw_status: row.status || "",
    kind: row.kind || "neutral",
    detail: itemDetail(row),
    raw_detail: row.detail || "",
    evidence_refs: evidenceItems(row).map((item) => ({ type: item.type, value: item.value }))
  }));
  const receipts = ((receiptHistory && receiptHistory.receipts) || []).slice(0, 8);
  const trace = context.traceContext || {};
  const workflow = context.workflowContext || {};
  const report = context.reportContext || {};
  const health = context.healthContext || {};
  const preflight = context.preflightEvent || null;
  const runHistory = context.runHistoryContext || {};
  const claimSupport = context.claimSupportContext || {};
  const sourceList = context.sourceListContext || {};
  const sourceAction = context.sourceActionEvent || null;
  const sourceImport = context.sourceImportEvent || null;
  const sourceEdit = context.sourceEditEvent || null;
  const serverStatus = context.serverStatus || {};
  const latestWrite = context.writeReceiptEvent || null;
  const latestRefreshResults = Array.isArray(context.refreshResults) ? context.refreshResults.filter(Boolean) : [];
  const projectEntry = context.projectEntry || {};
  const intakeDraft = context.intakeDraft || null;
  const sourceImportDraft = context.sourceImportDraft || null;
  const sourceEditDraft = context.sourceEditDraft || null;
  const readinessChecks = (trace.readiness_checks || trace.carrier_chain || []).slice(0, 8);
  const graphSummaries = (trace.graph_summaries || trace.graph_carriers || []).slice(0, 8);
  const preflightReceipt = trace.preflight_receipt || trace.loop_admission || {};
  const pendingIntakeFields = intakeChangedFields(intakeDraft);
  const sourceImportStarted = Boolean(
    sourceImportDraft &&
      (String(sourceImportDraft.filename || "").trim() ||
        String(sourceImportDraft.body || "").trim())
  );
  const pendingSourceEditFields = sourceChangedFields(sourceEditDraft);
  const intakeRefSummary = projectEntry.intake_ref_summary || {};
  const auditCommands = commandCockpitItems({
    snapshot,
    selectedRow: context.selectedRow || null,
    traceContext: trace,
    reportContext: report,
    healthContext: health,
    claimSupportContext: claimSupport
  }).map((item) => ({
    label: item.label,
    source: item.source || "",
    item_label: itemLabel(item.rowLabel || ""),
    row_label: item.rowLabel || "",
    command: item.command
  }));
  const evidenceFilePath =
    claimSupport.evidence_support_file_path || claimSupport.evidence_file_path || claimSupport.packet_path || "";
  const evidenceSupportBundle = {
    schema: claimSupport.schema || "",
    status: claimSupport.status || "",
    accepted: Boolean(claimSupport.accepted),
    support_scope: claimSupport.support_scope || "",
    intake: claimSupport.intake || "",
    project_key: claimSupport.project_key || claimSupport.case_key || "",
    case_key: claimSupport.case_key || claimSupport.project_key || "",
    command: claimSupport.command || "",
    claim_count: claimSupport.claim_count || 0,
    weak_or_unsourced_count: claimSupport.weak_or_unsourced_count || 0,
    source_context_blocked_count: claimSupport.source_context_blocked_count || 0,
    errors: (claimSupport.errors || []).slice(0, 8).map(displayMessage),
    evidence_support_file_path: evidenceFilePath,
    evidence_file_path: evidenceFilePath,
    packet_path: evidenceFilePath,
    source_index_path: claimSupport.source_index_path || "",
    source_context: (claimSupport.source_context || []).slice(0, 12)
  };
  const serverApi = serverStatus.api || {};
  const serverProjects = serverStatus.projects || {};
  const serverChecks = serverStatus.checks || {};
  const serverInfo = serverStatus.server || {};
  return {
    schema: "ztare-forensic-workbench-case-file-v1",
    project: snapshot.project,
    rubric: snapshot.rubric,
    intake: snapshot.intake,
    project_key: projectEntryKey(snapshot),
    case_key: projectEntryKey(snapshot),
    readiness: snapshot.readiness,
    report_status: snapshot.report_status,
    status_reasons: snapshot.status_reasons || [],
    support_issues: (report.support_issues || []).map((issue) => ({
      id: issue.id || "",
      status: issue.status || "",
      display_status: issue.display_status || "",
      reason: issue.reason || "",
      display_reason: issue.display_reason || ""
    })),
    generated_from: snapshot.served_from === "local_api" ? "local_api_snapshot" : "static_snapshot",
    project_check_count: items.length,
    item_count: items.length,
    row_count: items.length,
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
      latest_project_check:
        projectEntry.latest_project_check ||
        projectEntry.latest_item_action ||
        projectEntry.latest_row_action ||
        snapshot.latest_project_check_artifact ||
        snapshot.latest_item_action_artifact ||
        snapshot.latest_row_action_artifact ||
        "",
      latest_item_action: projectEntry.latest_item_action || projectEntry.latest_row_action || snapshot.latest_item_action_artifact || snapshot.latest_row_action_artifact || "",
      latest_row_action: projectEntry.latest_row_action || projectEntry.latest_item_action || snapshot.latest_row_action_artifact || snapshot.latest_item_action_artifact || "",
      latest_intake_edit: projectEntry.latest_intake_edit || snapshot.latest_intake_edit_artifact || "",
      latest_source_import: projectEntry.latest_source_import || "",
      latest_source_edit: projectEntry.latest_source_edit || "",
      latest_source_action: projectEntry.latest_source_action || "",
      latest_project_file_write: projectEntry.latest_project_file_write || projectEntry.latest_case_file_write || "",
      latest_case_file_write: projectEntry.latest_case_file_write || projectEntry.latest_project_file_write || ""
    },
    live_context: {
      trace: {
        schema: trace.schema || "",
        readiness: trace.readiness || "",
        trace_command: trace.trace_command || "",
        next_commands: (trace.next_commands || []).slice(0, 6),
        readiness_checks: readinessChecks,
        carrier_chain: readinessChecks,
        graph_summaries: graphSummaries,
        graph_carriers: graphSummaries,
        preflight_receipt: preflightReceipt,
        loop_admission: preflightReceipt,
        plan_preview: {
          schema: (trace.plan_preview || {}).schema || "",
          status: (trace.plan_preview || {}).status || "",
          recommended_first_command: (trace.plan_preview || {}).recommended_first_command || "",
          model_calls_before_confirmation: (trace.plan_preview || {}).model_calls_before_confirmation
        }
      },
      workflow: {
        schema: workflow.schema || "",
        mode: workflow.mode || "",
        summary: workflow.summary || {},
        step_count: workflow.step_count ?? (workflow.summary || {}).step_count,
        ready_count: workflow.ready_count ?? (workflow.summary || {}).ready_count,
        attention_count: workflow.attention_count ?? (workflow.summary || {}).attention_count,
        next_step_id: workflow.next_step_id || (workflow.summary || {}).next_step_id || "",
        next_step_label: workflow.next_step_label || (workflow.summary || {}).next_step_label || "",
        next_step_status: workflow.next_step_status || (workflow.summary || {}).next_step_status || "",
        next_step_display_status: workflow.next_step_display_status || (workflow.summary || {}).next_step_display_status || "",
        next_step_detail: workflow.next_step_detail || (workflow.summary || {}).next_step_detail || "",
        next_step_local_step: workflow.next_step_local_step || (workflow.summary || {}).next_step_local_step || "",
        next_step_local_action: workflow.next_step_local_action || (workflow.summary || {}).next_step_local_action || "",
        next_step_ui_destination: workflow.next_step_ui_destination || (workflow.summary || {}).next_step_ui_destination || {},
        next_step_write_path_count: workflow.next_step_write_path_count ?? (workflow.summary || {}).next_step_write_path_count,
        can_start_run: Boolean(workflow.can_start_run ?? (workflow.summary || {}).can_start_run),
        project_file_saved: Boolean(workflow.project_file_saved ?? (workflow.summary || {}).project_file_saved),
        next_step: workflow.next_step || {},
        steps: (workflow.steps || []).slice(0, 8).map((step) => ({
          id: step.id || "",
          label: step.label || "",
          status: step.status || "",
          display_status: step.display_status || "",
          detail: step.detail || "",
          local_step: step.local_step || step.local_action || "",
          local_action: step.local_action || "",
          ui_destination: step.ui_destination || {},
          write_boundary: step.write_boundary || {}
        })),
        errors: (workflow.errors || []).slice(0, 8).map(displayMessage)
      },
      report_contract: {
        schema: report.schema || "",
        report_scope: report.report_scope || "",
        intake: report.intake || "",
        project_key: report.project_key || report.case_key || "",
        case_key: report.case_key || report.project_key || "",
        status: report.status || "",
        display_status: report.display_status || "",
        status_reasons: report.status_reasons || [],
        display_status_reasons: report.display_status_reasons || [],
        support_issues: (report.support_issues || []).map((issue) => ({
          id: issue.id || "",
          status: issue.status || "",
          display_status: issue.display_status || "",
          reason: issue.reason || "",
          display_reason: issue.display_reason || ""
        })),
        report_support_contract: report.report_support_contract || "",
        backing_files: uniqueBackingFiles(report.backing_files || []),
        command: report.command || "",
        synthesis_input_binding: {
          schema: (report.synthesis_input_binding || {}).schema || "",
          status: (report.synthesis_input_binding || {}).status || "",
          reason: (report.synthesis_input_binding || {}).reason || "",
          artifact_count: (report.synthesis_input_binding || {}).artifact_count
        }
      },
      workbench_status: {
        schema: serverStatus.schema || "",
        server_name: serverInfo.name || "Project Workbench",
        api_ready: Boolean(serverStatus.api_ready || serverChecks.api_ready),
        action_summary: serverApi.action_summary || {},
        file_change_summary: serverApi.file_change_summary || {},
        write_contract: serverApi.write_contract || {},
        file_preview: serverApi.file_preview || {},
        primary_route_count: serverApi.primary_route_count || 0,
        compatibility_route_count: serverApi.compatibility_route_count || 0,
        project_count: serverProjects.project_count ?? serverProjects.folder_count ?? 0,
        intake_ready_count: serverProjects.ready_count ?? serverProjects.count ?? 0,
        pending_folder_count: serverProjects.pending_folder_count ?? 0
      },
      health: {
        schema: health.schema || "",
        kernel: {
          summary: ((health.kernel || {}).summary) || {},
          attention_components: ((health.kernel || {}).attention_components || []).slice(0, 8)
        },
        action_guidance: {
          counts: ((health.action_guidance || health.action_intelligence || {}).counts) || {},
          issues: ((health.action_guidance || health.action_intelligence || {}).issues || []).slice(0, 8),
          recommendations: ((health.action_guidance || health.action_intelligence || {}).recommendations || []).slice(0, 8),
          recommendation_counts: ((health.action_guidance || health.action_intelligence || {}).recommendation_counts) || {},
          recommendations_generated_at: ((health.action_guidance || health.action_intelligence || {}).recommendations_generated_at) || "",
          recommendations_source_path: ((health.action_guidance || health.action_intelligence || {}).recommendations_source_path) || "",
          source_paths: ((health.action_guidance || health.action_intelligence || {}).source_paths) || {}
        },
        action_intelligence: {
          counts: ((health.action_guidance || health.action_intelligence || {}).counts) || {},
          issues: ((health.action_guidance || health.action_intelligence || {}).issues || []).slice(0, 8),
          recommendations: ((health.action_guidance || health.action_intelligence || {}).recommendations || []).slice(0, 8),
          recommendation_counts: ((health.action_guidance || health.action_intelligence || {}).recommendation_counts) || {},
          recommendations_generated_at: ((health.action_guidance || health.action_intelligence || {}).recommendations_generated_at) || "",
          recommendations_source_path: ((health.action_guidance || health.action_intelligence || {}).recommendations_source_path) || "",
          source_paths: ((health.action_guidance || health.action_intelligence || {}).source_paths) || {}
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
        project_key: runHistory.project_key || runHistory.case_key || "",
        case_key: runHistory.case_key || runHistory.project_key || "",
        summary: runHistory.summary || {},
        paths: runHistory.paths || {},
        latest_eval: runHistory.latest_eval || {},
        champion_eval: runHistory.champion_eval || {},
        recent_runs: (runHistory.recent_runs || []).slice(-8),
        synthesis_history: runHistory.synthesis_history || {}
      },
      evidence_support: evidenceSupportBundle,
      claim_support: evidenceSupportBundle,
      sources: {
        schema: sourceList.schema || "",
        accepted: Boolean(sourceList.accepted),
        raw_dir: sourceList.raw_dir || "",
        source_count: Number(sourceList.source_count || (sourceList.sources || []).length || 0),
        source_type_counts: sourceList.source_type_counts || {},
        untyped_source_count: Number(sourceList.untyped_source_count || 0),
        invalid_source_type_count: Number(sourceList.invalid_source_type_count || 0),
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
            item_label: targetLabel(latestWrite.row || ""),
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
    audit_commands: auditCommands,
    command_queue: auditCommands,
    project_checks: items,
    items,
    rows: items,
    recent_receipts: receipts.map((receipt) => ({
      kind: receipt.kind,
      display_kind: receipt.display_kind || displayText(receipt.kind || "receipt"),
      applied_at: receipt.applied_at,
      summary: receipt.summary,
      display_summary: receipt.display_summary || receipt.summary || "",
      path: receipt.path,
      line: receipt.line,
      project: receipt.project || "",
      rubric: receipt.rubric || "",
      intake: receipt.intake || "",
      project_key: receipt.project_key || receipt.case_key || "",
      case_key: receipt.case_key || receipt.project_key || "",
      project_check_label: receipt.project_check_label || receipt.check_label || receipt.display_label || receipt.item_label || targetLabel(receipt.row || ""),
      project_check_slug: receipt.project_check_slug || receipt.item_slug || receipt.row_slug || "",
      item_label: receipt.item_label || receipt.project_check_label || targetLabel(receipt.row || ""),
      check_label: receipt.check_label || receipt.display_label || receipt.project_check_label || receipt.item_label || targetLabel(receipt.row || ""),
      item_slug: receipt.item_slug || receipt.project_check_slug || receipt.row_slug || "",
      row: receipt.row || "",
      row_slug: receipt.row_slug || receipt.project_check_slug || receipt.item_slug || "",
      source_path: receipt.source_path || "",
      source_type: receipt.source_type || "",
      decision: receipt.decision || "",
      display_decision: receipt.display_decision || displayText(receipt.decision || ""),
      action: receipt.action || "",
      display_action: receipt.display_action || displayText(receipt.action || ""),
      updated_fields: receipt.updated_fields || []
    }))
  };
}

function caseFileSummary(snapshot, receiptHistory, caseFile) {
  const blocker = activeBlocker((snapshot && snapshot.rows) || []);
  const receipts = ((receiptHistory && receiptHistory.receipts) || []).length;
  const auditCommands = caseFile ? (caseFile.audit_commands || caseFile.command_queue || []) : [];
  return [
    `Project: ${snapshot.project}`,
    `Run check: ${snapshot.display_readiness || displayText(snapshot.readiness)}`,
    `Report: ${reportStatusLabel(snapshot.report_status, snapshot.display_report_status)}`,
    `Current report issue: ${blocker ? itemLabel(blocker) : "none"}`,
    `Recent receipts: ${receipts}`,
    `command details: ${auditCommands.length}`,
    `Intake: ${snapshot.intake || "not recorded"}`
  ].join("\n");
}

function cleanProjectContextPreview(context = {}) {
  return {
    project_dir: context.project_dir || "",
    intake_source: context.intake_source || "",
    intake_editable: context.intake_editable !== false,
    intake_error: context.intake_error || "",
    intake_ref_summary: context.intake_ref_summary || {},
    report_contract: context.report_contract || "",
    latest_review: context.latest_review || "",
    latest_project_check: context.latest_project_check || context.latest_item_action || context.latest_row_action || "",
    latest_intake_edit: context.latest_intake_edit || "",
    latest_source_import: context.latest_source_import || "",
    latest_source_edit: context.latest_source_edit || "",
    latest_source_action: context.latest_source_action || "",
    latest_project_file_write: context.latest_project_file_write || context.latest_case_file_write || ""
  };
}

function cleanEvidenceSupportPreview(bundle = {}) {
  const evidenceFilePath = bundle.evidence_support_file_path || bundle.evidence_file_path || bundle.packet_path || "";
  return {
    schema: bundle.schema || "",
    status: bundle.status || "",
    accepted: Boolean(bundle.accepted),
    support_scope: bundle.support_scope || "",
    intake: bundle.intake || "",
    project_key: bundle.project_key || bundle.case_key || "",
    command_detail: bundle.command || "",
    claim_count: bundle.claim_count || 0,
    weak_or_unsourced_count: bundle.weak_or_unsourced_count || 0,
    source_context_blocked_count: bundle.source_context_blocked_count || 0,
    errors: bundle.errors || [],
    evidence_support_file_path: evidenceFilePath,
    source_index_path: bundle.source_index_path || "",
    source_context: bundle.source_context || []
  };
}

function cleanActionDetailPreview(item = {}) {
  return {
    label: item.label || "",
    source: item.source || "",
    check_label: item.project_check_label || item.item_label || item.check_label || "",
    command_detail: item.command || ""
  };
}

function cleanReceiptPreview(receipt = {}) {
  return {
    kind: receipt.kind || "",
    display_kind: receipt.display_kind || displayText(receipt.kind || "receipt"),
    applied_at: receipt.applied_at || "",
    summary: receipt.display_summary || receipt.summary || "",
    path: receipt.path || "",
    line: receipt.line,
    project: receipt.project || "",
    rubric: receipt.rubric || "",
    intake: receipt.intake || "",
    project_key: receipt.project_key || receipt.case_key || "",
    project_check_label: receipt.project_check_label || receipt.check_label || receipt.display_label || receipt.item_label || targetLabel(receipt.row || ""),
    project_check_slug: receipt.project_check_slug || receipt.item_slug || receipt.row_slug || "",
    check_label: receipt.check_label || receipt.display_label || receipt.project_check_label || receipt.item_label || targetLabel(receipt.row || ""),
    source_path: receipt.source_path || "",
    source_type: receipt.source_type || "",
    display_decision: receipt.display_decision || displayText(receipt.decision || ""),
    display_action: receipt.display_action || displayText(receipt.action || ""),
    updated_fields: receipt.updated_fields || []
  };
}

function cleanCaseFilePreview(caseFile) {
  if (!caseFile) return {};
  const preview = {
    schema: caseFile.schema,
    project: caseFile.project,
    rubric: caseFile.rubric,
    intake: caseFile.intake,
    readiness: caseFile.display_readiness || displayText(caseFile.readiness),
    report_status: reportStatusLabel(caseFile.report_status, caseFile.display_report_status),
    status_reasons: (caseFile.status_reasons || []).map(displayMessage),
    support_issues: (caseFile.support_issues || []).map((issue) => ({
      ...issue,
      display_reason: displayMessage(issue.display_reason || issue.reason || "")
    })),
    project_check_count: caseFile.project_check_count || caseFile.item_count || caseFile.row_count || 0,
    project_context: cleanProjectContextPreview(caseFile.project_context || {}),
    live_context: caseFile.live_context || {},
    action_details: (caseFile.audit_commands || caseFile.command_queue || []).map(cleanActionDetailPreview),
    project_checks: caseFile.project_checks || caseFile.items || [],
    recent_receipts: (caseFile.recent_receipts || []).map(cleanReceiptPreview)
  };
  if (preview.live_context && preview.live_context.trace) {
    preview.live_context = {
      ...preview.live_context,
      trace: {
        ...preview.live_context.trace,
        readiness: displayText(preview.live_context.trace.readiness),
        readiness_checks: preview.live_context.trace.readiness_checks || []
      }
    };
    delete preview.live_context.trace.carrier_chain;
    delete preview.live_context.trace.loop_admission;
  }
  if (preview.live_context && preview.live_context.workflow) {
    preview.live_context = {
      ...preview.live_context,
      workflow: {
        schema: preview.live_context.workflow.schema || "",
        mode: preview.live_context.workflow.mode || "",
        summary: preview.live_context.workflow.summary || {},
        next_step: preview.live_context.workflow.next_step || {},
        steps: preview.live_context.workflow.steps || [],
        errors: preview.live_context.workflow.errors || []
      }
    };
  }
  if (preview.live_context && preview.live_context.evidence_support) {
    preview.live_context = {
      ...preview.live_context,
      evidence_support: cleanEvidenceSupportPreview(preview.live_context.evidence_support)
    };
    delete preview.live_context.claim_support;
  }
  return preview;
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
      title: "Select a project check",
      note: "Select a project check before saving a next step.",
      evidence: "No project check selected.",
      command: ""
    };
  }

  const rowName = itemLabel(row);
  const status = itemStatus(row);
  const evidence = firstEvidenceText(row);
  const command = row.command || "";
  const warning = row.warning ? ` Warning: ${row.warning}.` : "";
  const reportBlocked = row.label === "Report support" && snapshot.report_status === "blocked";
  const inputIssue = row.label === "Source readiness" || row.label === "Evidence readiness" || row.label === "Project intake";
  const missingish = /missing|unknown|unavailable|unbound|not discovered|no_action|no_review/i.test(
    `${row.status} ${row.detail} ${row.warning}`
  );

  if (reportBlocked || row.status === "blocked") {
    return {
      action: "export_blocker",
      title: "Resolve before report",
      note: `Hold the report on ${rowName}. Inspect ${evidence}.${warning}${command ? " Use the Report or Runs area to rerun the related step when ready." : ""}`.trim(),
      evidence,
      command
    };
  }

  if (inputIssue || missingish) {
    return {
      action: "needs_source",
      title: "Fill the missing input",
      note: `Update ${rowName} before relying on this project. Inspect ${evidence}.${warning}`.trim(),
      evidence,
      command
    };
  }

  if (row.kind === "attention") {
    return {
      action: "next_step",
      title: "Resolve this project check",
      note: `Resolve ${rowName} before relying on this project. Inspect ${evidence}.${warning}${command ? " Use the matching project step to rerun when ready." : ""}`.trim(),
      evidence,
      command
    };
  }

  if (row.label === "Run readiness" || row.label === "Preflight" || /ready|available/.test(row.status)) {
    return {
      action: command ? "ready_to_run" : "next_step",
      title: command ? "Run the project step" : "Keep this project check as evidence",
      note: command
        ? `Use the Runs area for ${rowName}; keep the command details available if you need to debug.`
        : `${rowName} is ${status}. Keep ${evidence} attached to the project.`,
      evidence,
      command
    };
  }

  return {
    action: "next_step",
    title: "Record the next move",
    note: `${rowName} is ${status}. Inspect ${evidence} and decide the next project step.`,
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
  const sourceLabel = snapshot.served_from === "local_api" ? "live server" : "saved file";
  const rows = snapshot.rows || [];
  const claimRow = rowByLabel(rows, "Bounded claim");
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const evidenceState = [sourceRow && displayText(sourceRow.status), evidenceRow && displayText(evidenceRow.status)].filter(Boolean).join(" + ") || "not checked";
  return h(
    "div",
    { className: "project-identity", "aria-label": "Project identity" },
    h("span", null, h("em", null, "Project"), h("strong", null, humanProjectTitle(snapshot, claimRow))),
    h("span", null, h("em", null, "Evidence"), h("strong", null, evidenceState)),
    h("span", null, h("em", null, "Intake"), h("strong", null, displayText(snapshot.intake_source || "unknown_intake_source"))),
    h("span", null, h("em", null, "Mode"), h("strong", null, displayText(sourceLabel)))
  );
}

function pendingEditDestination(item) {
  const text = String(item || "").toLowerCase();
  if (text.includes("source import")) return ["sources", "Add source", "Open new source draft"];
  if (text.includes("source file")) return ["sources", "Edit source", "Open source edit"];
  return ["sources", "Intake", "Open intake"];
}

function PendingEditsStrip({ items, onOpenDetail }) {
  if (!items || !items.length) return null;
  const actions = [];
  items.forEach((item) => {
    const [workspace, subsection, label] = pendingEditDestination(item);
    if (!actions.some((action) => action.workspace === workspace && action.subsection === subsection)) {
      actions.push({ workspace, subsection, label });
    }
  });
  return h(
    "section",
    { className: "pending-edits-strip", "aria-label": "Unsaved edits" },
    h(
      "div",
      { className: "pending-edits-copy" },
      h("span", null, "Unsaved edits"),
      h("strong", null, `${items.length} pending edit${items.length === 1 ? "" : "s"}`)
    ),
    h(
      "div",
      { className: "pending-edits-list" },
      items.map((item) => h("span", { key: item }, item))
    ),
    h(
      "div",
      { className: "pending-edits-actions" },
      actions.map((action) =>
        h(
          "button",
          {
            key: `${action.workspace}:${action.subsection}`,
            type: "button",
            className: "copy-button",
            onClick: () => onOpenDetail && onOpenDetail(action.workspace, action.subsection)
          },
          action.label
        )
      )
    )
  );
}

function UnsavedChangesDialog({ prompt, onCancel, onDiscard }) {
  const discardButtonRef = useRef(null);
  useEffect(() => {
    if (!prompt) return undefined;
    const previousActive = document.activeElement;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") onCancel();
    };
    const unlockBody = lockModalBody();
    window.addEventListener("keydown", closeOnEscape);
    window.requestAnimationFrame(() => discardButtonRef.current && discardButtonRef.current.focus());
    return () => {
      unlockBody();
      window.removeEventListener("keydown", closeOnEscape);
      if (previousActive && typeof previousActive.focus === "function") previousActive.focus();
    };
  }, [onCancel, prompt]);
  if (!prompt) return null;
  return h(
    "div",
    { className: "modal-backdrop", role: "presentation", onMouseDown: (event) => event.target === event.currentTarget && onCancel() },
    h(
      "section",
      { className: "discard-dialog", role: "dialog", "aria-modal": "true", "aria-label": "Unsaved edits" },
      h(
        "header",
        { className: "discard-dialog-head" },
        h("span", { className: "eyebrow" }, "Unsaved edits"),
        h("h2", null, "Save or discard before continuing"),
        h("p", null, `${prompt.action} would discard these drafts.`)
      ),
      h(
        "div",
        { className: "discard-dialog-list" },
        (prompt.warnings || []).map((warning) => h("span", { key: warning }, warning))
      ),
      h(
        "div",
        { className: "discard-dialog-actions" },
        h("button", { type: "button", className: "copy-button", onClick: onCancel }, "Keep editing"),
        h("button", { type: "button", ref: discardButtonRef, className: "copy-button danger", onClick: onDiscard }, "Discard and continue")
      )
    )
  );
}

function ProjectRunConfirmDialog({ prompt, onCancel, onConfirm }) {
  const cancelButtonRef = useRef(null);
  const confirmedBoundary = (prompt && prompt.confirmedWriteBoundary) || {};
  const confirmedWritePaths = Array.isArray(confirmedBoundary.write_paths) ? confirmedBoundary.write_paths.filter(Boolean) : [];
  const canConfirm = Boolean(confirmedBoundary.writes_project_files && confirmedWritePaths.length);
  useEffect(() => {
    if (!prompt) return undefined;
    const previousActive = document.activeElement;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") onCancel();
    };
    const unlockBody = lockModalBody();
    window.addEventListener("keydown", closeOnEscape);
    window.requestAnimationFrame(() => cancelButtonRef.current && cancelButtonRef.current.focus());
    return () => {
      unlockBody();
      window.removeEventListener("keydown", closeOnEscape);
      if (previousActive && typeof previousActive.focus === "function") previousActive.focus();
    };
  }, [onCancel, prompt]);
  if (!prompt) return null;
  return h(
    "div",
    { className: "modal-backdrop", role: "presentation", onMouseDown: (event) => event.target === event.currentTarget && onCancel() },
    h(
      "section",
      { className: "case-run-dialog", role: "dialog", "aria-modal": "true", "aria-label": "Confirm project run" },
      h(
        "header",
        { className: "case-run-dialog-head" },
      h("span", { className: "eyebrow" }, "Project run"),
        h("h2", null, "Start this project run?"),
        h("p", null, "This can call configured models and write run files under the selected project.")
      ),
      h(
        "div",
        { className: "case-run-dialog-facts" },
        h("div", null, h("span", null, "Project"), h("strong", null, prompt.project || "not loaded")),
        h("div", null, h("span", null, "Intake"), h("code", null, prompt.intake || "not loaded")),
        h("div", null, h("span", null, "Files after confirm"), h("strong", null, canConfirm ? `${confirmedWritePaths.length} listed paths` : "not available"))
      ),
      h(
        "div",
        { className: "case-run-dialog-paths" },
        h("span", null, "Files that may change"),
        confirmedWritePaths.length
          ? confirmedWritePaths.map((path) => h("code", { key: path }, path))
          : h("p", null, "The server did not return write paths for this preview.")
      ),
      !canConfirm
        ? h(
            "p",
            { className: "case-run-dialog-warning" },
            "Start is disabled until the server returns the exact project files this run would write."
          )
        : null,
      h(
        "div",
        { className: "case-run-dialog-command" },
        h("span", null, "Command detail"),
      h("code", null, prompt.command || "No run command details loaded.")
      ),
      h(
        "div",
        { className: "case-run-dialog-actions" },
        h("button", { type: "button", ref: cancelButtonRef, className: "copy-button", onClick: onCancel }, "Cancel"),
        h(
          "button",
          {
            type: "button",
            className: "copy-button primary",
            disabled: !canConfirm,
            title: canConfirm ? "Start the confirmed project run" : "Files that may change must load before this run can start",
            onClick: onConfirm
          },
          "Start project run"
        )
      )
    )
  );
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
  const latestAction =
    (projectEntry && (projectEntry.latest_project_check || projectEntry.latest_item_action || projectEntry.latest_row_action)) ||
    snapshot.latest_project_check_artifact ||
    snapshot.latest_item_action_artifact ||
    snapshot.latest_row_action_artifact ||
    "";
  const latestIntakeEdit = (projectEntry && projectEntry.latest_intake_edit) || snapshot.latest_intake_edit_artifact || "";
  const latestSourceImport = (projectEntry && projectEntry.latest_source_import) || "";
  const latestSourceEdit = (projectEntry && projectEntry.latest_source_edit) || "";
  const latestSourceAction = (projectEntry && projectEntry.latest_source_action) || "";
  const latestProjectFileWrite = (projectEntry && (projectEntry.latest_project_file_write || projectEntry.latest_case_file_write)) || "";
  const refSummary = (projectEntry && projectEntry.intake_ref_summary) || {};
  const intakeError = (projectEntry && projectEntry.intake_error) || "";
  const intakeMode = projectEntry && projectEntry.intake_editable === false ? "read-only" : "editable";
  const pathRows = [
    { label: "Intake", value: intake },
    { label: "Report support file", value: reportContract },
    { label: "Latest review", value: latestReview },
    { label: "Latest next step", value: latestAction },
    { label: "Latest intake edit", value: latestIntakeEdit },
    { label: "Latest new source", value: latestSourceImport },
    { label: "Latest source edit", value: latestSourceEdit },
    { label: "Latest source check", value: latestSourceAction },
    { label: "Latest project file", value: latestProjectFileWrite }
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
          title: liveMode ? `Preview ${item.label.toLowerCase()}` : "Start the workbench server to preview project files"
        },
        "Preview"
      )
    );
  return h(
    "section",
    { className: "project-context-panel", "aria-label": "Project files" },
    h("div", null, h("span", null, "Project files"), h("strong", null, projectDir || "not discovered")),
    h("div", null, h("span", null, "Intake files"), h("strong", null, refSummary.total ? `${refSummary.present || 0}/${refSummary.total} present` : "not counted")),
    h("div", { className: intakeError ? "project-context-attention" : "" }, h("span", null, "Intake check"), h("strong", null, intakeError ? displayMessage(intakeError) : "checked")),
    h("div", null, h("span", null, "Edit mode"), h("strong", null, intakeMode)),
    pathRows.map(renderPathRow)
  );
}

function ServerStatusPanel({ status, liveMode, message, onRefresh }) {
  const checks = (status && status.checks) || {};
  const projectInfo = (status && status.projects) || {};
  const folderSummary = projectInfo.folder_summary || {};
  const appInfo = (status && status.app) || {};
  const apiInfo = (status && status.api) || {};
  const serverInfo = (status && status.server) || {};
  const snapshotInfo = (status && status.snapshot) || {};
  const primaryLiveRoutes = apiInfo.primary_live_routes || {};
  const actionContracts = apiInfo.action_contracts || {};
  const actionSummary = apiInfo.action_summary || {};
  const fileChangeSummary = apiInfo.file_change_summary || {};
  const writeContract = apiInfo.write_contract || {};
  const filePreviewContract = apiInfo.file_preview || {};
  const liveActionCount = Object.values(actionContracts).filter(Boolean).length || Object.values(primaryLiveRoutes).filter(Boolean).length;
  const pendingFolderCount =
    projectInfo.pending_folder_count !== undefined
      ? projectInfo.pending_folder_count
      : Math.max(0, (projectInfo.folder_count || 0) - (projectInfo.ready_count ?? projectInfo.count ?? 0));
  const readyCount = projectInfo.ready_count ?? projectInfo.count ?? 0;
  const projectCount = projectInfo.project_count ?? projectInfo.folder_count ?? projectInfo.count ?? 0;
  const needsIntakeWithFiles = Number(folderSummary.needs_intake_with_files || 0);
  const needsIntakeEmpty = Number(folderSummary.needs_intake_empty || 0);
  const actionCoverage = liveActionCount ? `${liveActionCount} server actions` : "not loaded";
  const summaryReadCount = fileChangeSummary.read_only_count ?? actionSummary.read_only_count;
  const summaryWriteCount = fileChangeSummary.write_count ?? actionSummary.write_without_confirmation_count;
  const summaryConfirmCount = fileChangeSummary.ask_first_count ?? actionSummary.confirmation_required_count;
  const directWriteCount =
    summaryWriteCount !== undefined
      ? Number(summaryWriteCount || 0)
      : writeContract.write_without_confirmation_count !== undefined
      ? writeContract.write_without_confirmation_count
      : writeContract.write_action_count !== undefined
        ? Math.max(0, Number(writeContract.write_action_count || 0) - Number(writeContract.confirmation_required_count || 0))
        : undefined;
  const writeCoverage =
    summaryWriteCount !== undefined || writeContract.write_action_count !== undefined
      ? `${directWriteCount || 0} write / ${summaryConfirmCount ?? writeContract.confirmation_required_count ?? 0} ask first / ${summaryReadCount ?? writeContract.read_only_action_count ?? 0} read-only`
      : "not loaded";
  const previewRootCount = Array.isArray(filePreviewContract.allowed_roots) ? filePreviewContract.allowed_roots.length : 0;
  const previewCoverage = filePreviewContract.mode
    ? `${displayText(filePreviewContract.mode)} / ${previewRootCount} roots`
    : "not loaded";
  const checkRows = [
    { key: "api_ready", label: "Local server", value: checks.api_ready ? "live" : "not ready", tone: checks.api_ready ? "ready" : "attention" },
    { key: "projects_available", label: "All project folders", value: checks.projects_available ? `${projectCount} total / ${readyCount} ready to open` : "not loaded", tone: checks.projects_available ? "ready" : "attention" },
    { key: "projects_needing_intake", label: "Need intake before opening", value: pendingFolderCount === undefined ? "not counted" : String(pendingFolderCount), tone: pendingFolderCount ? "neutral" : "ready" },
    { key: "folder_split", label: "Folders with files / empty", value: folderSummary.needs_intake_with_files === undefined ? "not counted" : `${needsIntakeWithFiles} / ${needsIntakeEmpty}`, tone: needsIntakeWithFiles ? "neutral" : "ready" },
    { key: "live_routes", label: "Workbench actions", value: actionCoverage, tone: liveActionCount ? "ready" : "attention" },
    { key: "write_boundary", label: "File changes", value: writeCoverage, tone: writeContract.browser_writes ? "attention" : "ready" },
    { key: "file_preview", label: "File preview", value: previewCoverage, tone: filePreviewContract.mode ? "ready" : "attention" },
    { key: "app_built", label: "Web app", value: checks.app_built ? "built" : "dev server only", tone: checks.app_built ? "ready" : "neutral" },
    { key: "snapshot_available", label: "Offline project data", value: checks.snapshot_available ? "available" : "missing", tone: checks.snapshot_available ? "ready" : "neutral" }
  ];
  const actionRows = [
    ["project_inventory", "Projects"],
    ["snapshot", "Project data"],
    ["workflow", "Project steps"],
    ["evidence_support", "Support audit"],
    ["project_create", "Create project or add intake"],
    ["intake_edit", "Intake save"],
    ["source_import", "Add source"],
    ["source_edit", "Save source"],
    ["source_check", "Check source files"],
    ["source_index", "Refresh file index"],
    ["evidence_bind", "Connect evidence files"],
    ["evidence_replay", "Check evidence files"],
    ["preflight", "Preflight"],
    ["run_preview_and_confirm", "Run"],
    ["review", "Save review"],
    ["next_step", "Save next step"],
    ["project_file", "Project file"]
  ]
    .map(([key, fallbackLabel]) => {
      const contract = actionContracts[key] || {};
      const route = primaryLiveRoutes[key] || contract.route || "";
      return {
        key,
        label: contract.label || fallbackLabel,
        route,
        mode: contract.behavior || contract.mode || (route ? "available" : "not loaded"),
        writesProjectFiles: Boolean(contract.writes_project_files),
        requiresConfirmation: Boolean(contract.requires_confirmation),
        browserWrites: Boolean(contract.browser_writes)
      };
    })
    .filter((row) => row.route || row.mode !== "not loaded");
  const readOnlyActions = actionRows.filter((row) => !row.writesProjectFiles && !row.requiresConfirmation);
  const confirmationActions = actionRows.filter((row) => row.requiresConfirmation);
  const writeActions = actionRows.filter((row) => row.writesProjectFiles && !row.requiresConfirmation);
  const readOnlyActionLabels = Array.isArray(fileChangeSummary.read_only_steps)
    ? fileChangeSummary.read_only_steps
    : Array.isArray(actionSummary.read_only_actions)
      ? actionSummary.read_only_actions
      : readOnlyActions.map((row) => row.label);
  const writeActionLabels = Array.isArray(fileChangeSummary.write_steps)
    ? fileChangeSummary.write_steps
    : Array.isArray(actionSummary.write_without_confirmation_actions)
      ? actionSummary.write_without_confirmation_actions
      : writeActions.map((row) => row.label);
  const confirmationActionLabels = Array.isArray(fileChangeSummary.ask_first_steps)
    ? fileChangeSummary.ask_first_steps
    : Array.isArray(actionSummary.confirmation_required_actions)
      ? actionSummary.confirmation_required_actions
      : confirmationActions.map((row) => row.label);
  const actionGroups = [
    {
      key: "read",
      label: "Read-only",
      value: `${summaryReadCount ?? readOnlyActionLabels.length} actions`,
      detail: readOnlyActionLabels.join(", ") || "not loaded",
      tone: "ready"
    },
    {
      key: "write",
      label: "Writes files or receipts",
      value: `${summaryWriteCount ?? writeActionLabels.length} actions`,
      detail: writeActionLabels.join(", ") || "not loaded",
      tone: writeActionLabels.length ? "ready" : "neutral"
    },
    {
      key: "confirm",
      label: "Asks before writing",
      value: confirmationActionLabels.length ? confirmationActionLabels.join(", ") : "none",
      detail: confirmationActionLabels.length ? "Project-run files are shown before the run starts." : "No ask-first action loaded.",
      tone: confirmationActionLabels.length ? "ready" : "neutral"
    }
  ];
  const apiReady = Boolean(status && ((status.checks || {}).api_ready || status.ok));
  const tone = liveMode && apiReady ? "ready" : "attention";
  return h(
    "section",
    { className: `server-status-panel ${tone}`, "aria-label": "Workbench server status" },
    h(
      "div",
      { className: "server-status-copy" },
      h("span", { className: "eyebrow" }, "Workbench readiness"),
      h("h2", null, liveMode && apiReady ? "Live editing is ready" : "Live editing needs attention"),
      h("p", null, message || (liveMode ? "The local server can read project files and save explicit reviews and next steps." : "Start the workbench server to edit project files."))
    ),
    h(
      "div",
      { className: "server-status-checks" },
      checkRows.map((row) =>
        h(
          "div",
          { key: row.key, className: row.tone || (checks[row.key] ? "ready" : "attention") },
          h("span", null, row.label),
          h("strong", null, row.value)
        )
      )
    ),
    h(
      "div",
      { className: "server-status-paths" },
      h("div", null, h("span", null, "Server"), h("strong", null, serverInfo.name ? `${serverInfo.name} ${serverInfo.version || ""}`.trim() : "not loaded")),
      h("div", null, h("span", null, "Web app"), h("strong", null, checks.app_built ? "built" : "not built")),
      h("div", null, h("span", null, "Offline project data"), h("strong", null, checks.snapshot_available ? "available" : "missing")),
      h("div", null, h("span", null, "Default project"), h("strong", null, projectInfo.default_project || "not loaded")),
      h(
        "div",
        { className: "server-status-action-groups", "aria-label": "File-change behavior" },
        actionGroups.map((group) =>
          h(
            "section",
            { key: group.key, className: group.tone },
            h("span", null, group.label),
            h("strong", null, group.value),
            h("small", null, group.detail)
          )
        )
      )
    ),
    h(
      "div",
      { className: "server-status-actions" },
      h(
        "button",
        { className: "copy-button primary", type: "button", onClick: onRefresh, title: "Reload server readiness" },
        "Refresh readiness"
      )
    )
  );
}

function ProjectSwitchboard({ projects, projectFolders, selectedProjectKey, snapshot, liveMode, loading, onSelect, onCreate, onPreview, filePreview, filePreviewMessage }) {
  const [projectQuery, setProjectQuery] = useState("");
  const [pendingFolderLimit, setPendingFolderLimit] = useState(48);
  const [inventoryFilter, setInventoryFilter] = useState("all");
  useEffect(() => setPendingFolderLimit(48), [projectQuery]);
  if (!liveMode || (!projects.length && !projectFolders.length)) {
    const message = liveMode
      ? "Project inventory is loading from projects/."
      : "Start the local workbench server to browse every project folder and edit project files.";
    return h(
      "section",
      { className: "project-switchboard empty", "aria-label": "All projects" },
      h(
        "div",
        { className: "project-switchboard-head" },
        h("span", { className: "eyebrow" }, "Projects"),
        h("h2", null, "All projects"),
        h("p", null, message)
      ),
      liveMode
        ? h("div", { className: "project-switchboard-section-label" }, h("span", null, "Project inventory"), h("strong", null, "Loading"))
        : null
    );
  }
  const activeKey = selectedProjectKey || projectEntryKey(snapshot);
  const normalizedQuery = projectQuery.trim().toLowerCase();
  const entriesByProject = new Map(projects.map((project) => [project.project, project]));
  const inventoryRows = (projectFolders || [])
    .map((folder) => {
      const readyEntry = entriesByProject.get(folder.project);
      return {
        ...folder,
        ...(readyEntry || {}),
        folder_status: folder.status,
        openable: Boolean(readyEntry || folder.openable),
        has_project_files: folderHasCaseMaterial(folder),
        intake_count: folder.intake_count || (readyEntry && readyEntry.intake ? 1 : 0),
        display_label: (readyEntry && readyEntry.display_label) || folder.display_label || titleFromSlug(folder.project || "Project"),
        display_status: readyEntry ? (readyEntry.display_status || "intake ready") : (folder.display_status || "needs intake")
      };
    })
    .filter((row) => {
      if (normalizedQuery) {
        const haystack = [
          row.project,
          row.intake,
          row.project_dir,
          row.intake_source,
          row.report_contract,
          row.display_label,
          row.display_status
        ].join(" ").toLowerCase();
        if (!haystack.includes(normalizedQuery)) return false;
      }
      if (inventoryFilter === "ready") return row.openable;
      if (inventoryFilter === "needs_intake") return !row.openable;
      if (inventoryFilter === "needs_intake_with_files") return !row.openable && row.has_project_files;
      return true;
    })
    .sort(projectInventorySort);
  const readyCount = (projectFolders || []).filter((folder) => entriesByProject.has(folder.project)).length;
  const needsIntakeCount = Math.max(0, (projectFolders || []).length - readyCount);
  const needsIntakeWithFilesCount = (projectFolders || []).filter((folder) => !entriesByProject.has(folder.project) && folderHasCaseMaterial(folder)).length;
  const filterOptions = [
    { id: "all", label: "All projects", count: (projectFolders || []).length },
    { id: "ready", label: "Intake ready", count: readyCount },
    { id: "needs_intake", label: "Needs intake", count: needsIntakeCount },
    { id: "needs_intake_with_files", label: "Files, no intake", count: needsIntakeWithFilesCount }
  ];
  const visibleInventoryRows = inventoryRows.slice(0, pendingFolderLimit);
  const remainingRows = Math.max(inventoryRows.length - visibleInventoryRows.length, 0);
  const filtersActive = Boolean(normalizedQuery || inventoryFilter !== "all");
  const projectSummary = normalizedQuery
    ? `${inventoryRows.length} matching projects`
    : `${(projectFolders || []).length} projects / ${readyCount} intake ready`;
  const visibleSummary = inventoryRows.length
    ? `${visibleInventoryRows.length} visible of ${inventoryRows.length} matching`
    : "No projects match";
  const resetInventoryView = () => {
    setProjectQuery("");
    setInventoryFilter("all");
    setPendingFolderLimit(48);
  };
  return h(
    "section",
    { className: "project-switchboard", "aria-label": "All projects" },
    h(
      "div",
      { className: "project-switchboard-head" },
      h("span", { className: "eyebrow" }, "Projects"),
      h("h2", null, "All projects"),
      h("p", null, "Every folder under projects/ is listed here. Open projects with an intake, or add an intake before running checks.")
    ),
    h(
      "div",
      { className: "project-switchboard-tools" },
      h(
        "label",
        null,
        h("span", null, "Search projects"),
        h("input", {
          value: projectQuery,
          onInput: (event) => setProjectQuery(event.target.value),
          placeholder: "billing, ns, forecast, ops"
        })
      ),
      h("strong", null, projectSummary),
      h(
        "div",
        { className: "project-folder-filter", "aria-label": "Project filter" },
        filterOptions.map((option) =>
          h(
            "button",
            {
              key: option.id,
              type: "button",
              className: inventoryFilter === option.id ? "active" : "",
              "aria-pressed": inventoryFilter === option.id,
              onClick: () => {
                setInventoryFilter(option.id);
                setPendingFolderLimit(48);
              }
            },
            `${option.label} ${option.count}`
          )
        )
      ),
      h(
        "button",
        {
          type: "button",
          className: "copy-button",
          disabled: !filtersActive,
          onClick: resetInventoryView,
          title: filtersActive ? "Clear project search and filters" : "No project filters active"
        },
        "Reset view"
      ),
      h(
        "button",
        { type: "button", className: "copy-button", onClick: () => onCreate && onCreate() },
        "Add intake"
      )
    ),
    filePreviewMessage || filePreview
      ? h("div", { className: "project-switchboard-preview" }, h(FilePreview, { filePreview, filePreviewMessage }))
      : null,
    h(
      "div",
      { className: "project-switchboard-grid" },
      h(
        "div",
        { className: "project-switchboard-section-label" },
        h("span", null, "Project inventory"),
        h("strong", null, visibleSummary)
      ),
      visibleInventoryRows.map((project) => {
        const projectKey = projectEntryKey(project);
        const refSummary = project.intake_ref_summary || {};
        const intakeError = project.intake_error || "";
        const active = projectKey === activeKey;
        const openable = Boolean(project.openable && project.intake);
        const intakeMode = intakeError ? "intake attention" : openable ? (project.intake_editable === false ? "read-only intake" : "editable intake") : "needs intake";
        const fileSummary = projectInventoryFileSummary(project, refSummary);
        const rawPreview = (project.raw_preview_files || []).find(isPreviewableRepoPath) || "";
        const workspacePreview = (project.workspace_preview_files || []).find(isPreviewableRepoPath) || "";
        const receiptCount = [
          project.latest_review,
          project.latest_project_check || project.latest_item_action || project.latest_row_action,
          project.latest_intake_edit,
          project.latest_source_import,
          project.latest_source_edit,
          project.latest_source_action,
          project.latest_case_file_write
        ].filter(Boolean).length;
        return h(
          "article",
          { key: project.project, className: `project-tile ${active ? "active" : ""} ${openable ? "" : "pending"}` },
          h(
            "div",
            { className: "project-tile-main" },
            h("strong", null, project.display_label || titleFromSlug(project.project || "Local project")),
            h("small", null, project.project_dir || `projects/${project.project}`)
          ),
          h(
            "div",
            { className: "project-tile-facts" },
            h("span", { className: openable ? "" : "attention" }, project.display_status || project.status_label || (openable ? "intake ready" : "needs intake")),
            h("span", { className: intakeError ? "attention" : "" }, intakeMode),
            h("span", null, fileSummary),
            h("span", null, project.report_contract ? "report support" : "report not ready"),
            h("span", null, receiptCount ? `${receiptCount} recent changes` : "no recent changes")
          ),
          intakeError ? h("p", { className: "project-tile-error" }, displayMessage(intakeError)) : null,
          !openable ? h("p", { className: "project-tile-error" }, "Add an intake before editing the thesis, evidence, runs, or report support.") : null,
          h(
            "div",
            { className: "project-tile-actions" },
            h(
              "button",
              {
                type: "button",
                className: active ? "copy-button" : "copy-button primary",
                disabled: loading || active,
                onClick: () => {
                  if (openable) onSelect(projectKey);
                  else if (onCreate) onCreate(project);
                },
                title: !openable ? "Add an intake for this project" : active ? "This project is open" : `Open ${project.display_label || titleFromSlug(project.project || "Local project")} / ${sourceBasename(project.intake || "") || "project"}`
              },
              active ? "Current" : openable ? "Open" : "Add intake"
            ),
            rawPreview
              ? h(
                  "button",
                  {
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode,
                    onClick: () => onPreview && onPreview({ type: "file", value: rawPreview }),
                    title: `Preview ${rawPreview}`
                  },
                  "Preview source"
                )
              : null,
            workspacePreview
              ? h(
                  "button",
                  {
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode,
                    onClick: () => onPreview && onPreview({ type: "file", value: workspacePreview }),
                    title: `Preview ${workspacePreview}`
                  },
                  "Preview workspace"
                )
              : null
          )
        );
      }),
      remainingRows
        ? h(
            "div",
            { className: "project-switchboard-more" },
            h(
              "p",
              null,
              normalizedQuery
                ? `${remainingRows} more projects match this search.`
                : `${remainingRows} more projects in this view. Search to narrow the list, or show more here.`
            ),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                onClick: () => setPendingFolderLimit((limit) => limit + 48)
              },
              `Show ${Math.min(48, remainingRows)} more`
            )
          )
        : null
    )
  );
}

function ProjectLandingPicker({ projects, projectFolders, selectedProjectKey, snapshot, liveMode, loading, onSelect, onBrowse, onCreate }) {
  const activeKey = selectedProjectKey || projectEntryKey(snapshot);
  const fallbackProject = { project: snapshot.project, intake: snapshot.intake, rubric: snapshot.rubric, display_label: titleFromSlug(snapshot.project) };
  const entriesByProject = new Map((liveMode && projects.length ? projects : [fallbackProject]).map((project) => [project.project, project]));
  const inventory = liveMode && projectFolders.length
    ? projectFolders.map((folder) => ({ ...folder, ...(entriesByProject.get(folder.project) || {}), openable: entriesByProject.has(folder.project) })).sort(projectInventorySort)
    : [fallbackProject];
  const readyCount = inventory.filter((project) => project.openable || project.intake).length;
  const needsIntakeCount = Math.max(0, inventory.length - readyCount);
  const needsIntakeWithFilesCount = inventory.filter((project) => !(project.openable || project.intake) && folderHasCaseMaterial(project)).length;
  const current = inventory.find((project) => projectEntryKey(project) === activeKey) || inventory.find((project) => project.openable || project.intake) || inventory[0] || null;
  const visibleProjects = [
    ...(current ? [current] : []),
    ...inventory.filter((project) => project !== current)
  ].slice(0, 6);
  const inventorySummary = liveMode
    ? `${inventory.length} project folders loaded from projects/. ${readyCount} can open now; ${needsIntakeCount} need an intake first.`
    : "Offline snapshot mode shows the last generated project. Start the local server to browse projects.";
  const inventoryFacts = liveMode
    ? [
        ["Project folders", String(inventory.length)],
        ["Ready to open", String(readyCount)],
        ["Need intake", String(needsIntakeCount)],
        ["Files, no intake", String(needsIntakeWithFilesCount)]
      ]
    : [
        ["Project folders", "offline"],
        ["Ready to open", current ? "1" : "0"],
        ["Need intake", "server needed"],
        ["Files, no intake", "server needed"]
      ];
  return h(
    "section",
    { className: "case-landing-picker", "aria-label": "Open project" },
    h(
      "div",
      { className: "case-landing-copy" },
      h("span", { className: "eyebrow" }, "Open project"),
      h("h2", null, current ? (current.display_label || titleFromSlug(current.project || snapshot.project)) : "Choose a project"),
      h("p", null, inventorySummary),
      h("small", null, liveMode ? "Open an intake-ready project, or add the intake that makes an older folder editable." : "Live mode is needed for project switching and edits.")
    ),
    h(
      "div",
      { className: "case-landing-actions" },
      h(
        "button",
        {
          type: "button",
          className: "copy-button primary",
          disabled: !liveMode,
          onClick: () => onBrowse && onBrowse(),
          title: liveMode ? "Open the searchable project inventory" : "Start the local server to browse projects"
        },
        liveMode ? `Browse ${inventory.length} folders` : "Browse projects"
      ),
      h(
        "button",
        { type: "button", className: "copy-button", disabled: !liveMode, onClick: () => onCreate && onCreate() },
        "Add intake"
      )
    ),
    h(
      "div",
      { className: "case-landing-metrics", "aria-label": "Project inventory summary" },
      inventoryFacts.map(([label, value]) =>
        h("div", { key: label }, h("span", null, label), h("strong", null, value))
      )
    ),
    h(
      "details",
      { className: "case-landing-list-wrap" },
      h("summary", null, `Project shortcuts (${visibleProjects.length} shown)`),
      h(
        "div",
        { className: "case-landing-list", "aria-label": "Projects" },
        visibleProjects.map((project) => {
          const key = projectEntryKey(project);
          const active = key === activeKey;
          const refSummary = project.intake_ref_summary || {};
          const openable = Boolean(project.openable || project.intake);
          const fileSummary = projectInventoryFileSummary(project, refSummary);
          const status = project.intake_error
            ? "Needs intake"
            : openable && refSummary.total
              ? fileSummary
              : openable
                ? displayText(project.intake_source || "project intake")
                : fileSummary;
          return h(
            "button",
            {
              key: key || project.project,
              type: "button",
              className: active ? "active" : "",
              disabled: loading || !liveMode || active,
              onClick: () => {
                if (openable) onSelect && onSelect(key || project.project);
                else onCreate && onCreate(project);
              },
              title: !openable ? "Add an intake for this project" : active ? "This project is open" : `Open ${titleFromSlug(project.project || "project")}`
            },
            h("strong", null, project.display_label || titleFromSlug(project.project || "Local project")),
            h("span", null, sourceBasename(project.intake || project.project_dir || "") || status),
            h("small", null, status)
          );
        })
      )
    )
  );
}

function projectWorkflowSteps({ snapshot, traceContext, reportContext, runHistory, receiptHistory, liveMode, onOpenDetail }) {
  const rows = (snapshot && snapshot.rows) || [];
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const reportRow = rowByLabel(rows, "Report support");
  const inputReady = sourceRow && evidenceRow && sourceRow.kind !== "attention" && evidenceRow.kind !== "attention";
  const preflightReceipt = (traceContext && (traceContext.preflight_receipt || traceContext.loop_admission)) || {};
  const planStatus = (traceContext && traceContext.plan_preview && traceContext.plan_preview.status) || "";
  const preflightDone = Boolean(preflightReceipt.receipt_count || preflightReceipt.available || planStatus === "ready_for_bounded_run");
  const runSummary = (runHistory && runHistory.summary) || {};
  const runDone = Boolean((runSummary.run_rows || 0) > 0 || runSummary.latest_score !== undefined && runSummary.latest_score !== null);
  const reportStatus = (reportContext && reportContext.status) || snapshot.report_status || "";
  const reportReady = Boolean(reportStatus && reportStatus !== "blocked");
  const receipts = (receiptHistory && receiptHistory.receipts) || [];
  const reviewDone = receipts.some((receipt) => receipt.kind === "review");
  const projectFileDone = receipts.some((receipt) => receipt.kind === "case_file");
  const serverTone = liveMode ? "ready" : "attention";

  return [
    {
      label: "Open project",
      state: liveMode ? "Ready" : "Server needed",
      detail: liveMode ? "Project is loaded from the local API." : "Start live mode to browse and edit projects.",
      tone: serverTone,
      onClick: () => onOpenDetail && onOpenDetail("projects", "All projects")
    },
    {
      label: "Prepare files",
      state: inputReady ? "Ready" : "Needs review",
      detail: inputReady ? "Source and evidence files are usable." : "Check the intake, source files, and evidence connection.",
      tone: inputReady ? "ready" : "attention",
      onClick: () => onOpenDetail && onOpenDetail("sources", inputReady ? "Intake" : "File check")
    },
    {
      label: "Preflight",
      state: preflightDone ? "Accepted" : "Not run",
      detail: preflightDone ? "Run plan can move forward." : "Run the cheap local check before heavier work.",
      tone: preflightDone ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("run", "Preflight")
    },
    {
      label: "Project run",
      state: runDone ? "Scored" : planStatus === "ready_for_bounded_run" ? "Ready" : "Waiting",
      detail: runDone ? "Recent run history is available." : planStatus === "ready_for_bounded_run" ? "Review files that may change before starting." : "Preflight must accept the project first.",
      tone: runDone || planStatus === "ready_for_bounded_run" ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("run", runDone ? "Results" : "Start run")
    },
    {
      label: "Review report",
      state: reportReady ? reviewDone ? "Reviewed" : "Ready" : "Needs support",
      detail: reportReady ? "Report support is usable; record review if needed." : reportRow ? itemDetail(reportRow) : "Inspect report support before relying on it.",
      tone: reportReady ? "ready" : "attention",
      onClick: () => onOpenDetail && onOpenDetail(reportReady && !reviewDone ? "review" : "save", reportReady && !reviewDone ? "Save review" : "Support check")
    },
    {
      label: "Save project",
      state: projectFileDone ? "Saved" : "Not saved",
      detail: projectFileDone ? "A project file receipt is in history." : "Save a project file when the current state is ready to hand off.",
      tone: projectFileDone ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("save", "Project file")
    }
  ];
}

function workflowStepDestination(step) {
  const destination = (step && step.ui_destination) || {};
  const workspaceAliases = { cases: "projects" };
  const subsectionAliases = {
    "Check files": "File check",
    "Project checks": "Open issues",
    Review: "Save review",
    "Next step": "Save next step",
    "Report support": "Support check",
    Report: "Report inputs"
  };
  if (destination.workspace && destination.subsection) {
    return [
      workspaceAliases[destination.workspace] || destination.workspace,
      subsectionAliases[destination.subsection] || destination.subsection
    ];
  }
  const id = String((step && step.id) || "");
  if (id === "open_project") return ["projects", "All projects"];
  if (id === "prepare_files") return ["sources", step.status === "ready" ? "Intake" : "File check"];
  if (id === "preflight") return ["run", "Preflight"];
  if (id === "project_run") return ["run", step.status === "done" ? "Results" : "Start run"];
  if (id === "review_report") return [step.status === "ready" ? "review" : "save", step.status === "ready" ? "Save review" : "Support check"];
  if (id === "save_project") return ["save", "Project file"];
  return ["overview", "Status"];
}

function workflowTone(status) {
  if (["ready", "done", "reviewed"].includes(status)) return "ready";
  if (["needs_attention", "blocked", "failed"].includes(status)) return "attention";
  return "neutral";
}

function workflowServerActionLabel(step) {
  if (step && (step.local_step || step.local_action)) return String(step.local_step || step.local_action);
  const id = String((step && step.id) || "");
  const labels = {
    open_project: "Load project",
    prepare_files: "Edit intake and source files",
    preflight: "Run preflight",
    project_run: "Start or inspect run",
    review_report: "Review report support",
    save_project: "Save project file"
  };
  return labels[id] || "Open project step";
}

function serverWorkflowSteps(workflowContext, onOpenDetail) {
  const steps = (workflowContext && workflowContext.steps) || [];
  if (!Array.isArray(steps) || !steps.length) return [];
  return steps.map((step) => {
    const status = String(step.status || "unknown");
    const [workspace, subsection] = workflowStepDestination(step);
    const writes = (((step.write_boundary || {}).write_paths) || []).filter(Boolean).length;
    const detail = [
      step.detail,
      `Local step: ${workflowServerActionLabel(step)}`,
      writes ? `${writes} possible file change${writes === 1 ? "" : "s"}` : ""
    ].filter(Boolean).join(" / ");
    return {
      label: step.label || displayText(step.id || "Project step"),
      state: step.display_status || displayText(status),
      detail,
      tone: workflowTone(status),
      onClick: () => onOpenDetail && onOpenDetail(workspace, subsection)
    };
  });
}

function ProjectWorkflowStrip({ steps }) {
  return h(
    "section",
    { className: "project-workflow-strip", "aria-label": "Project steps" },
    steps.map((step, index) =>
      h(
        "button",
        {
          key: step.label,
          type: "button",
          className: step.tone || "neutral",
          onClick: step.onClick,
          title: step.detail
        },
        h("span", null, String(index + 1).padStart(2, "0")),
        h("strong", null, step.label),
        h("small", null, step.state)
      )
    )
  );
}

function ProjectWorkflowPanel({ workflowContext, message, liveMode, onOpenDetail }) {
  const steps = Array.isArray(workflowContext && workflowContext.steps) ? workflowContext.steps : [];
  const errors = Array.isArray(workflowContext && workflowContext.errors) ? workflowContext.errors.filter(Boolean) : [];
  const readyCount = steps.filter((step) => ["ready", "done", "reviewed"].includes(String(step.status || ""))).length;
  return h(
    "section",
    { className: `project-workflow-panel ${errors.length ? "attention" : "ready"}`, "aria-label": "Project steps" },
    h(
      "div",
      { className: "project-workflow-head" },
      h("span", { className: "eyebrow" }, "Project steps"),
      h("h2", null, steps.length ? `${readyCount}/${steps.length} steps ready` : "Project steps not loaded"),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Current path from loaded files, receipts, and report support."
            : "Live project state is not connected.")
      )
    ),
    errors.length
      ? h(
          "div",
          { className: "project-workflow-errors" },
          errors.slice(0, 4).map((error) => h("p", { key: error }, displayMessage(error)))
        )
      : null,
    h(
      "div",
      { className: "project-workflow-list" },
      steps.length
        ? steps.map((step, index) => {
            const status = String(step.status || "unknown");
            const boundary = step.write_boundary || {};
            const writePaths = Array.isArray(boundary.write_paths) ? boundary.write_paths.filter(Boolean) : [];
            const [workspace, subsection] = workflowStepDestination(step);
            const serverAction = workflowServerActionLabel(step);
            return h(
              "article",
              { key: step.id || step.label || index, className: `project-workflow-card ${workflowTone(status)}` },
              h(
                "div",
                { className: "project-workflow-card-main" },
                h("span", null, String(index + 1).padStart(2, "0")),
                h("strong", null, step.label || displayText(step.id || "Project step")),
                h("small", null, step.display_status || displayText(status)),
                h("p", null, step.detail || "No detail loaded.")
              ),
              h(
                "div",
                { className: "project-workflow-card-route" },
          h("span", null, "Local step"),
                h("strong", { title: "Handled by the local workbench server" }, serverAction)
              ),
              h(
                "div",
                { className: "project-workflow-card-writes" },
                h("span", null, "File changes"),
                writePaths.length
                  ? writePaths.slice(0, 4).map((path) => h("code", { key: path }, path))
                  : h("small", null, boundary.writes_project_files ? "Paths not listed" : "read-only")
              ),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  onClick: () => onOpenDetail && onOpenDetail(workspace, subsection),
                  title: `Open ${subsection}`
                },
                "Open"
              )
            );
          })
        : h("p", null, "No project steps loaded.")
    )
  );
}

function fallbackNextWorkflowStep(steps) {
  const usable = (steps || []).filter(Boolean);
  return (
    usable.find((step) => step.tone === "attention") ||
    usable.find((step) => step.tone === "neutral") ||
    usable.find((step) => step.tone === "ready") ||
    null
  );
}

function ProjectNextStepPanel({ workflowContext, fallbackSteps, liveMode, onOpenDetail }) {
  const summary = (workflowContext && workflowContext.summary) || {};
  const step = (workflowContext && workflowContext.next_step) || {};
  const stepId = String(step.id || summary.next_step_id || "");
  const fallbackStep = stepId ? null : fallbackNextWorkflowStep(fallbackSteps);
  if (!stepId && !fallbackStep) return null;
  const status = String(step.status || summary.next_step_status || (fallbackStep && fallbackStep.tone) || "");
  const writeBoundary = step.write_boundary || {};
  const writePaths = Array.isArray(writeBoundary.write_paths) ? writeBoundary.write_paths.filter(Boolean) : [];
  const [workspace, subsection] = workflowStepDestination(step);
  const title = step.label || summary.next_step_label || (fallbackStep && fallbackStep.label) || "Next step";
  const detail = step.detail || summary.next_step_detail || (fallbackStep && fallbackStep.detail) || "Open the next project step.";
  const attentionCount = Number(summary.attention_count || 0);
  const tone = stepId ? workflowTone(status) : (fallbackStep && fallbackStep.tone) || "neutral";
  const boundaryLabel = stepId ? "File changes" : "Write boundary";
  const boundaryValue = stepId
    ? writePaths.length ? `${writePaths.length} ${writePaths.length === 1 ? "path" : "paths"}` : writeBoundary.writes_project_files ? "paths not listed" : "read-only"
    : liveMode ? "estimated" : "server needed";
  const openFallback = () => fallbackStep && fallbackStep.onClick && fallbackStep.onClick();
  const openLiveStep = () => onOpenDetail && onOpenDetail(workspace, subsection);
  return h(
    "section",
    { className: `project-next-step ${tone}`, "aria-label": "Next project step" },
    h(
      "div",
      { className: "project-next-step-copy" },
      h("span", { className: "eyebrow" }, "Next step"),
      h("h3", null, title),
      h("p", null, detail),
      h(
        "small",
        null,
        attentionCount
          ? `${attentionCount} project step${attentionCount === 1 ? "" : "s"} need attention.`
          : stepId && liveMode
            ? "Project steps are loaded from local project files."
            : liveMode
              ? "Project steps are estimated from loaded project state."
              : "Static project-data estimate. Start the local server to edit project files."
      )
    ),
    h(
      "div",
      { className: "project-next-step-facts" },
      h("div", null, h("span", null, "State"), h("strong", null, step.display_status || summary.next_step_display_status || (fallbackStep && fallbackStep.state) || displayText(status))),
      h("div", null, h("span", null, boundaryLabel), h("strong", null, boundaryValue))
    ),
    h(
      "button",
      {
        type: "button",
        className: "copy-button primary",
        onClick: stepId ? openLiveStep : openFallback,
        title: stepId ? `Open ${subsection}` : `Open ${title}`
      },
      stepId ? `Open ${subsection}` : "Open step"
    )
  );
}

function ProjectSupportStrip({ sourceRow, evidenceRow, assumptionsRow, runHistory, claimSupport, sourceList, liveMode, onOpenDetail }) {
  const summary = (runHistory && runHistory.summary) || {};
  const latest = (runHistory && runHistory.latest_eval) || {};
  const sources = Array.isArray(sourceList && sourceList.sources) ? sourceList.sources : [];
  const sourceCount = Number((sourceList && sourceList.source_count) || sources.length || 0);
  const weakSupport = Number((claimSupport && claimSupport.weak_or_unsourced_count) || 0);
  const sourceGaps = Number((claimSupport && claimSupport.source_context_blocked_count) || 0);
  const evidenceStatus = (claimSupport && claimSupport.display_status) || (claimSupport && claimSupport.status ? displayText(claimSupport.status) : evidenceRow ? itemStatus(evidenceRow) : "not loaded");
  const latestScore = summary.latest_score === undefined || summary.latest_score === null ? "none" : String(summary.latest_score);
  const iterationText = summary.latest_run_id
    ? `${summary.run_rows || 1} runs / iter ${summary.latest_iteration ?? 0}`
    : "not run";
  const weakestPoint = latest.weakest_point || summary.latest_weakest_point || (evidenceRow ? itemDetail(evidenceRow) : "No weakest point recorded.");
  const facts = [
    {
      label: "Source files",
      value: sourceCount ? `${sourceCount} files` : sourceRow ? itemStatus(sourceRow) : "not loaded",
      detail: sourceRow ? itemDetail(sourceRow) : "No source-file summary loaded.",
      tone: sourceRow && sourceRow.kind === "attention" ? "attention" : "ready",
      action: "Open files",
      onClick: () => onOpenDetail && onOpenDetail("sources", "File check")
    },
    {
      label: "Support audit",
      value: evidenceStatus,
      detail: weakSupport || sourceGaps ? `${weakSupport} support issues / ${sourceGaps} source gaps` : "No support gaps loaded.",
      tone: weakSupport || sourceGaps || (evidenceRow && evidenceRow.kind === "attention") ? "attention" : "ready",
      action: "Open audit",
      onClick: () => onOpenDetail && onOpenDetail("run", "Results")
    },
    {
      label: "Assumptions",
      value: assumptionsRow ? itemStatus(assumptionsRow) : "not loaded",
      detail: assumptionsRow ? itemDetail(assumptionsRow) : "No assumptions or constraints file is loaded.",
      tone: assumptionsRow && assumptionsRow.kind === "attention" ? "attention" : "neutral",
      action: "Open thesis",
      onClick: () => onOpenDetail && onOpenDetail("overview", "Diagnosis")
    },
    {
      label: "Latest score",
      value: latestScore,
      detail: iterationText,
      tone: latestScore === "none" ? "neutral" : "ready",
      action: "Open runs",
      onClick: () => onOpenDetail && onOpenDetail("run", "Results")
    },
    {
      label: "Weakest point",
      value: shortText(weakestPoint, 42),
      detail: "Use this to choose the next review or evidence step.",
      tone: weakestPoint && weakestPoint !== "No weakest point recorded." ? "attention" : "neutral",
      action: "Open issues",
      onClick: () => onOpenDetail && onOpenDetail("review", "Open issues")
    }
  ];
  return h(
    "section",
    { className: "project-support-strip", "aria-label": "Project support" },
    h(
      "div",
      { className: "project-support-head" },
      h("span", { className: "eyebrow" }, "Project support"),
      h("strong", null, "Files, assumptions, run result, and weakest point"),
      h("small", null, liveMode ? "Loaded from local project files and receipts." : "Static project-data view.")
    ),
    h(
      "div",
      { className: "project-support-grid" },
      facts.map((fact) =>
        h(
          "button",
          { key: fact.label, type: "button", className: fact.tone || "neutral", onClick: fact.onClick, title: fact.detail },
          h("span", null, fact.label),
          h("strong", null, fact.value),
          h("small", null, fact.detail),
          h("em", null, fact.action)
        )
      )
    )
  );
}

function ProjectHomeSummary({ snapshot, runHistory, traceContext, workflowContext, reportContext, receiptHistory, claimSupport, sourceList, liveMode, onOpenDetail, onInspectItem }) {
  const rows = (snapshot && snapshot.rows) || [];
  const claimRow = rowByLabel(rows, "Bounded claim");
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const assumptionsRow = rowByLabel(rows, "Assumptions and constraints");
  const runRow = rowByLabel(rows, "Run readiness");
  const reportRow = rowByLabel(rows, "Report support");
  const falsifierRow = rowByLabel(rows, "Next falsifier");
  const summary = (runHistory && runHistory.summary) || {};
  const latest = (runHistory && runHistory.latest_eval) || {};
  const score = summary.latest_score === undefined || summary.latest_score === null ? "none" : String(summary.latest_score);
  const runLabel = summary.latest_run_id ? `${summary.latest_run_id} / ${summary.latest_iteration ?? 0}` : "not run";
  const thesisText = claimRow ? diagnosisLead(claimRow.detail) : "No thesis is recorded in the intake.";
  const changeText = falsifierRow ? falsifierLead(falsifierRow.detail) || itemStatus(falsifierRow) : "No change test recorded.";
  const facts = [
    {
      label: "Diagnosis",
      value: claimRow ? itemStatus(claimRow) : "missing",
      detail: thesisText,
      tone: claimRow ? statusClass(claimRow) : "attention",
      action: "Open diagnosis",
      onClick: () => onOpenDetail && onOpenDetail("overview", "Diagnosis")
    },
    {
      label: "Evidence",
      value: `${sourceRow ? itemStatus(sourceRow) : "source missing"} / ${evidenceRow ? itemStatus(evidenceRow) : "evidence missing"}`,
      detail: evidenceRow ? itemDetail(evidenceRow) : "Attach source and evidence files before relying on the project.",
      tone: (sourceRow && sourceRow.kind === "attention") || (evidenceRow && evidenceRow.kind === "attention") ? "attention" : "ready",
      action: "Open evidence",
      onClick: () => onOpenDetail && onOpenDetail("sources", "File check")
    },
    {
      label: "Assumptions",
      value: assumptionsRow ? itemStatus(assumptionsRow) : "not loaded",
      detail: assumptionsRow ? itemDetail(assumptionsRow) : "No assumptions or constraints file is loaded for this project.",
      tone: assumptionsRow && assumptionsRow.kind === "attention" ? "attention" : "neutral",
      action: "Open constraints",
      onClick: () => {
        if (assumptionsRow && onInspectItem) onInspectItem(assumptionsRow.label);
        else onOpenDetail && onOpenDetail("overview", "Diagnosis");
      }
    },
    {
      label: "Runs",
      value: `Score ${score}`,
      detail: latest.weakest_point || (runRow ? itemDetail(runRow) : runLabel),
      tone: runRow && runRow.kind === "attention" ? "attention" : "neutral",
      action: "Open results",
      onClick: () => onOpenDetail && onOpenDetail("run", "Results")
    },
    {
      label: "Report",
      value: reportRow ? itemStatus(reportRow) : reportStatusLabel(snapshot.report_status, snapshot.display_report_status),
      detail: reportRow ? itemDetail(reportRow) : "Report support has not been loaded.",
      tone: reportRow ? statusClass(reportRow) : snapshot.report_status === "blocked" ? "attention" : "neutral",
      action: "Open report support",
      onClick: () => onOpenDetail && onOpenDetail("save", "Support check")
    }
  ];
  const workflowSteps = serverWorkflowSteps(workflowContext, onOpenDetail);
  const fallbackWorkflowSteps = projectWorkflowSteps({ snapshot, traceContext, reportContext, runHistory, receiptHistory, liveMode, onOpenDetail });
  const activeWorkflowSteps = workflowSteps.length ? workflowSteps : fallbackWorkflowSteps;
  const workRail = [
    {
      label: "1",
      title: "Choose project",
      detail: "Open any project folder with an intake.",
      action: "All projects",
      onClick: () => onOpenDetail && onOpenDetail("projects", "All projects")
    },
    {
      label: "2",
      title: "Read thesis",
      detail: "Check the diagnosis, caveats, and change test.",
      action: "Diagnosis",
      onClick: () => onOpenDetail && onOpenDetail("overview", "Diagnosis")
    },
    {
      label: "3",
      title: "Check support",
      detail: "Inspect source files, evidence files, and assumptions.",
      action: "Files",
      onClick: () => onOpenDetail && onOpenDetail("sources", "File check")
    },
    {
      label: "4",
      title: "Run locally",
      detail: "Use preflight first, then start the project run.",
      action: "Runs",
      onClick: () => onOpenDetail && onOpenDetail("run", "Preflight")
    },
    {
      label: "5",
      title: "Save review",
      detail: "Save the review, next step, and project file.",
      action: "Review",
      onClick: () => onOpenDetail && onOpenDetail("review", "Save review")
    }
  ];
  return h(
    "section",
    { className: "project-home-summary", "aria-label": "Open project summary" },
    h(
      "div",
      { className: "project-home-overview" },
      h(
        "div",
        { className: "project-home-thesis" },
        h("span", { className: "eyebrow" }, "Current project"),
        h("h2", null, humanProjectTitle(snapshot, claimRow)),
        h("p", null, thesisText),
        h("small", null, `Would change if: ${changeText}`)
      ),
      h(
        "div",
        { className: `project-home-thesis-state ${facts[0].tone || "neutral"}` },
        h("span", null, "Diagnosis"),
        h("strong", null, facts[0].value),
        h("button", { type: "button", className: "copy-button", onClick: facts[0].onClick }, facts[0].action)
      )
    ),
    h(
      ProjectNextStepPanel,
      { workflowContext, fallbackSteps: fallbackWorkflowSteps, liveMode, onOpenDetail }
    ),
    h(ProjectSupportStrip, { sourceRow, evidenceRow, assumptionsRow, runHistory, claimSupport, sourceList, liveMode, onOpenDetail }),
    h(
      "details",
      { className: "project-home-work-rail" },
      h("summary", null, "Show workflow guide"),
      h(
        "section",
        { "aria-label": "How to work this project" },
        h(
          "div",
          { className: "project-home-work-rail-head" },
          h("span", { className: "eyebrow" }, "Use this project"),
          h("strong", null, "Inspect the thesis, check support, run locally, then save the review trail.")
        ),
        h(
          "div",
          { className: "project-home-work-rail-steps" },
          workRail.map((step) =>
            h(
              "button",
              { key: step.title, type: "button", onClick: step.onClick, title: step.detail },
              h("span", null, step.label),
              h("strong", null, step.title),
              h("small", null, step.detail),
              h("em", null, step.action)
            )
          )
        )
      )
    ),
    h(
      "details",
      { className: "project-home-workflow" },
      h("summary", null, "Show full project steps"),
      h(ProjectWorkflowStrip, { steps: activeWorkflowSteps })
    )
  );
}

function ProjectCreatePanel({ draft, setDraft, message, creating, liveMode, projects, projectFolders, projectCreateContract, onCreate, onPreview, filePreview, filePreviewMessage }) {
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const project = String(draft.project || "").trim();
  const suggestedProject = projectFolderSuggestion(draft.task, draft.bounded_claim, draft.notes);
  const validProject = Boolean(project && PROJECT_SLUG_RE.test(project));
  const readyProjectExists = projectSlugExists(projects, project);
  const existingFolder = (projectFolders || []).find((folder) => folder.project === project) || null;
  const projectCanReceiveIntake = Boolean(existingFolder && !existingFolder.openable && !existingFolder.intake_count);
  const duplicateProject = readyProjectExists || Boolean(existingFolder && !projectCanReceiveIntake);
  const readySuggestionExists = projectSlugExists(projects, suggestedProject);
  const existingSuggestionFolder = (projectFolders || []).find((folder) => folder.project === suggestedProject) || null;
  const suggestionCanReceiveIntake = Boolean(existingSuggestionFolder && !existingSuggestionFolder.openable && !existingSuggestionFolder.intake_count);
  const duplicateSuggestion = readySuggestionExists || Boolean(existingSuggestionFolder && !suggestionCanReceiveIntake);
  const hasRequiredFields = Boolean(
    String(draft.task || "").trim()
      && String(draft.bounded_claim || "").trim()
      && String(draft.next_falsifier || "").trim()
  );
  const previewProject = project || suggestedProject;
  const previewExistingFolder = (projectFolders || []).find((folder) => folder.project === previewProject) || null;
  const previewCanReceiveIntake = Boolean(previewExistingFolder && !previewExistingFolder.openable && !previewExistingFolder.intake_count);
  const rawPreviewFiles = (previewExistingFolder && previewExistingFolder.raw_preview_files || []).filter(isPreviewableRepoPath);
  const workspacePreviewFiles = (previewExistingFolder && previewExistingFolder.workspace_preview_files || []).filter(isPreviewableRepoPath);
  const contextRows = previewExistingFolder
    ? [
        {
          label: "Source files",
          value: previewExistingFolder.raw_source_file_count || previewExistingFolder.raw_file_count
            ? cappedCountText(
                previewExistingFolder.raw_source_file_count || previewExistingFolder.raw_file_count,
                previewExistingFolder.raw_source_file_count_capped || previewExistingFolder.raw_file_count_capped
              )
            : "0",
          detail: rawPreviewFiles.length ? rawPreviewFiles.join("\n") : "No previewable source sample found."
        },
        {
          label: "Workspace files",
          value: previewExistingFolder.workspace_file_count
            ? cappedCountText(previewExistingFolder.workspace_file_count, previewExistingFolder.workspace_file_count_capped)
            : "0",
          detail: workspacePreviewFiles.length ? workspacePreviewFiles.join("\n") : "No previewable workspace sample found."
        },
        {
          label: "Intake",
          value: previewExistingFolder.intake_count ? String(previewExistingFolder.intake_count) : "missing",
          detail: previewCanReceiveIntake ? "This folder can receive a new intake." : "Pick a folder without an intake."
        }
      ]
    : [];
  const projectCreateTemplates = Array.isArray(projectCreateContract && projectCreateContract.write_path_templates)
    ? projectCreateContract.write_path_templates
    : [];
  const addIntakeMode = Boolean(project && projectCanReceiveIntake);
  const createActionLabel = addIntakeMode ? "Add intake" : "Create project";
  const shouldShowCreatePath = (path) => {
    if (!previewExistingFolder) return true;
    if (!previewCanReceiveIntake) return false;
    if (path === `projects/${previewProject}`) return false;
    if (path === `projects/${previewProject}/raw` && previewExistingFolder.raw_exists) return false;
    if (path === `projects/${previewProject}/workspace` && previewExistingFolder.workspace_exists) return false;
    if (path === `projects/${previewProject}/raw/source_type_map.json` && previewExistingFolder.source_type_map_exists) return false;
    return true;
  };
  const contractCreatePaths = PROJECT_SLUG_RE.test(previewProject) && projectCreateTemplates.length
    ? formatWriteTemplateItems(projectCreateContract, { project: previewProject }, projectCreateTemplates)
        .filter((item) => shouldShowCreatePath(item.path))
    : [];
  const fallbackCreatePaths = PROJECT_SLUG_RE.test(previewProject)
    ? [
        ...(!previewExistingFolder ? [`projects/${previewProject}`] : []),
        ...(previewCanReceiveIntake || !previewExistingFolder
          ? [
              ...(!previewExistingFolder || !previewExistingFolder.raw_exists ? [`projects/${previewProject}/raw`] : []),
              ...(!previewExistingFolder || !previewExistingFolder.workspace_exists ? [`projects/${previewProject}/workspace`] : []),
              ...(!previewExistingFolder || !previewExistingFolder.source_type_map_exists ? [`projects/${previewProject}/raw/source_type_map.json`] : []),
              `projects/${previewProject}/${previewProject}_intake.json`
            ]
          : [])
      ]
    : [];
  const pendingCreatePaths = contractCreatePaths.length ? contractCreatePaths : fallbackCreatePaths;
  const canCreate = Boolean(liveMode && !creating && validProject && !duplicateProject && hasRequiredFields);
  const createTitle = !liveMode
    ? "Start the workbench server to create a project or intake"
    : duplicateProject
      ? "This project already has an intake. Pick another folder."
      : !validProject
        ? "Use letters, numbers, dot, dash, or underscore"
        : !hasRequiredFields
          ? "Enter task, working diagnosis, and what would change it"
          : addIntakeMode
            ? "Add an intake to this existing project folder"
            : "Create local project and intake";
  const projectNote = duplicateProject
    ? "Existing project with intake. Pick another folder."
    : projectCanReceiveIntake
      ? "Existing folder. Add the intake and any missing source folders."
    : project && !validProject
      ? "Use letters, numbers, dot, dash, or underscore."
      : "";
  const suggestionNote = duplicateSuggestion
    ? `${suggestedProject} already has an intake.`
    : suggestionCanReceiveIntake
      ? `Suggested existing folder: ${suggestedProject}`
    : `Suggested: ${suggestedProject}`;
  return h(
    "section",
    { className: "project-create-panel", "aria-label": addIntakeMode ? "Add project intake" : "Create project intake" },
    h(
      "div",
      { className: "project-create-head" },
      h("span", { className: "eyebrow" }, addIntakeMode ? "Existing project" : "New project"),
      h("h2", null, addIntakeMode ? "Add an intake to this project" : "Create a project intake"),
      h("p", null, message || (addIntakeMode ? "Use the files already in this folder, then add the intake needed for editing and runs." : "Create local project folders and an intake before running checks."))
    ),
    h(
      "div",
      { className: "project-create-grid" },
      h(
        "label",
        null,
        h("span", null, "Project folder"),
        h("input", { value: draft.project, onInput: (event) => setField("project", event.target.value), placeholder: "billing_diagnosis" }),
        h(
          "div",
          { className: "case-folder-suggestion" },
          h("small", { className: duplicateSuggestion ? "project-create-note" : "" }, projectNote || suggestionNote),
          h(
            "button",
            {
              type: "button",
              className: "copy-button",
              disabled: duplicateSuggestion || creating,
              onClick: () => setField("project", suggestedProject),
              title: duplicateSuggestion ? "Suggested folder already exists" : "Use the suggested project folder"
            },
            "Use suggestion"
          )
        )
      ),
      h("label", null, h("span", null, "Task"), h("input", { value: draft.task, onInput: (event) => setField("task", event.target.value), placeholder: "Check whether..." })),
      h("label", null, h("span", null, "Working diagnosis"), h("textarea", { value: draft.bounded_claim, onInput: (event) => setField("bounded_claim", event.target.value), rows: 2, placeholder: "What do you currently think is true?" })),
      h("label", null, h("span", null, "What would change it"), h("textarea", { value: draft.next_falsifier, onInput: (event) => setField("next_falsifier", event.target.value), rows: 2, placeholder: "What evidence would make you revise or reject it?" })),
      h("label", null, h("span", null, "Notes"), h("textarea", { value: draft.notes, onInput: (event) => setField("notes", event.target.value), rows: 2, placeholder: "optional context" })),
      h("label", null, h("span", null, "Source files"), h("textarea", { value: draft.source_refs_text, onInput: (event) => setField("source_refs_text", event.target.value), rows: 2, placeholder: "one path per line" })),
      h("label", null, h("span", null, "Evidence files"), h("textarea", { value: draft.evidence_refs_text, onInput: (event) => setField("evidence_refs_text", event.target.value), rows: 2, placeholder: "one path per line" })),
      h("label", null, h("span", null, "Ruled-out alternatives"), h("textarea", { value: draft.non_claims_text, onInput: (event) => setField("non_claims_text", event.target.value), rows: 2, placeholder: "one caveat per line" }))
    ),
    previewExistingFolder
      ? h(
          "section",
          { className: "project-create-context", "aria-label": "Existing project files" },
          h(
            "div",
            { className: "project-create-context-head" },
            h("span", null, "Existing project files"),
            h("strong", null, previewExistingFolder.project_dir || `projects/${previewProject}`)
          ),
          h(
            "div",
            { className: "project-create-context-grid" },
            contextRows.map((row) =>
              h(
                "article",
                { key: row.label },
                h("span", null, row.label),
                h("strong", null, row.value),
                h("p", null, row.detail)
              )
            )
          ),
          rawPreviewFiles.length || workspacePreviewFiles.length
            ? h(
                "div",
                { className: "project-create-context-actions" },
                rawPreviewFiles.slice(0, 2).map((path) =>
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
                    `Preview ${sourceBasename(path)}`
                  )
                ),
                workspacePreviewFiles.slice(0, 2).map((path) =>
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
                    `Preview ${sourceBasename(path)}`
                  )
                )
              )
            : null,
          filePreviewMessage || filePreview
            ? h("div", { className: "project-create-file-preview" }, h(FilePreview, { filePreview, filePreviewMessage }))
            : null
        )
      : null,
    h(
      "section",
      { className: `project-create-preview ${canCreate ? "ready" : ""}`, "aria-label": "Pending project write" },
      h("span", null, addIntakeMode ? "Will add" : "Will create"),
      pendingCreatePaths.length
        ? pendingCreatePaths.map((path) => h("code", { key: path }, path))
        : h("p", null, "Enter a valid project folder to preview the project paths.")
    ),
    h(WriteBoundary, {
      writeLabel: addIntakeMode
        ? "Add intake writes the intake file and any missing source metadata."
        : "Create project writes the project folder, source metadata, and intake file.",
      readLabel: `Suggestions and field edits stay in the browser until ${createActionLabel} runs.`,
      liveMode
    }),
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
        creating ? (addIntakeMode ? "Adding intake" : "Creating") : createActionLabel
      )
    )
  );
}

function sourceWorkspaceDir(sourceList, project = "") {
  const rawDir = String((sourceList && sourceList.raw_dir) || (project ? `projects/${project}/raw` : ""));
  return rawDir.endsWith("/raw") ? rawDir.slice(0, -4) + "/workspace" : "";
}

function writePathLabel(path) {
  const text = String(path || "");
  if (!text) return "Project file path";
  if (text.includes("_intake.json") || /\/[^/]+_intake\.json$/.test(text)) return "Project intake";
  if (text.includes("/raw/source_type_map.json")) return "Source role map";
  if (text.includes("/raw/")) return "Source file";
  if (text.includes("source_index_receipt")) return "File-index receipt";
  if (text.includes("source_index.json")) return "File index";
  if (text.includes("workspace_meta.json")) return "Workspace metadata";
  if (text.includes("evidence_output_binding_receipt")) return "Evidence connection receipt";
  if (text.includes("iteration_telemetry")) return "Run telemetry";
  if (text.includes("latest_eval_results")) return "Latest run result";
  if (text.includes("eval_results")) return "Run result history";
  if (text.includes("forensic_workbench_applied") && text.includes("_review_")) return "Review handoff file";
  if (text.includes("forensic_workbench_reviews")) return "Review ledger";
  if (text.includes("forensic_workbench_latest_review")) return "Latest review receipt";
  if (text.includes("forensic_workbench_applied") && text.includes("_action_")) return "Next-step handoff file";
  if (text.includes("forensic_workbench_row_actions")) return "Next-step ledger";
  if (text.includes("forensic_workbench_latest_row_action")) return "Latest next-step receipt";
  if (text.includes("forensic_workbench_intake_edits")) return "Intake-edit ledger";
  if (text.includes("forensic_workbench_latest_intake_edit")) return "Latest intake-edit receipt";
  if (text.includes("forensic_workbench_source_imports")) return "Source-add ledger";
  if (text.includes("forensic_workbench_latest_source_import")) return "Latest source-add receipt";
  if (text.includes("forensic_workbench_source_edits")) return "Source-edit ledger";
  if (text.includes("forensic_workbench_latest_source_edit")) return "Latest source-edit receipt";
  if (text.includes("forensic_workbench_source_actions")) return "File-check ledger";
  if (text.includes("forensic_workbench_latest_source_action")) return "Latest file-check receipt";
  if (text.includes("forensic_workbench_case_file_")) return "Project file";
  if (text.includes("forensic_workbench_case_files")) return "Project-file ledger";
  if (text.includes("forensic_workbench_latest_case_file_write")) return "Latest project-file receipt";
  if (/^projects\/[^/]+\/workspace$/.test(text)) return "Workspace folder";
  if (/^projects\/[^/]+\/raw$/.test(text)) return "Source folder";
  if (/^projects\/[^/]+$/.test(text)) return "Project folder";
  return "Project file path";
}

function pendingPathPreview(label, paths, emptyText, ready = false) {
  const items = paths.map((item) => {
    if (item && typeof item === "object") return { label: item.label || writePathLabel(item.path || item.value), path: item.path || item.value || "" };
    return { label: writePathLabel(item), path: String(item || "") };
  }).filter((item) => item.path);
  return h(
    "section",
    { className: `pending-path-preview ${ready ? "ready" : ""}`, "aria-label": label },
    h("span", null, label),
    items.length
      ? items.map((item) =>
          h(
            "div",
            { className: "pending-path-row", key: item.path },
            h("strong", null, item.label),
            h("code", null, item.path)
          )
        )
      : h("p", null, emptyText)
  );
}

function SavePathSummary({ title, target, note, paths, ready }) {
  const items = (Array.isArray(paths) ? paths : []).filter((item) => item && item.path);
  return h(
    "section",
    { className: `save-path-summary ${ready ? "ready" : ""}`, "aria-label": title },
    h("div", { className: "save-path-summary-copy" },
      h("span", null, title),
      h("strong", null, target || "Select a project check"),
      h("p", null, note)
    ),
    h(
      "div",
      { className: "save-path-summary-list" },
      items.length
        ? items.slice(0, 3).map((item) =>
            h(
              "div",
              { key: `${item.label}:${item.path}` },
              h("span", null, item.label || writePathLabel(item.path)),
              h("code", null, item.path)
            )
          )
        : h("p", null, "Choose a project check to preview the files that receive this record.")
    )
  );
}

function ReviewPointContextCard({ row }) {
  const evidence = row ? evidenceItems(row) : [];
  const firstEvidence = evidence[0];
  return h(
    "section",
    { className: `review-point-context ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Selected project check" },
    h(
      "div",
      { className: "review-point-context-copy" },
      h("span", { className: "eyebrow" }, "Selected project check"),
      h("strong", null, row ? itemLabel(row) : "No project check selected"),
      h("p", null, row ? itemDetail(row) : "Choose a project check before saving a review or next step.")
    ),
    h(
      "div",
      { className: "review-point-context-facts" },
      h("div", null, h("span", null, "Status"), h("strong", null, row ? itemStatus(row) : "not selected")),
      h("div", null, h("span", null, "Evidence links"), h("strong", null, row ? String(evidence.length) : "0")),
      h("div", null, h("span", null, "First evidence"), h("strong", null, firstEvidence ? shortText(firstEvidence.value, 58) : "none")),
      h("div", null, h("span", null, "Review state"), h("strong", null, row ? kindLabel(row.kind) : "none"))
    )
  );
}

function workspaceDirForProject(project) {
  return project ? `projects/${project}/workspace` : "";
}

function projectSlugFromProjectPath(path) {
  const match = String(path || "").match(/^projects\/([^/]+)\//);
  return match ? match[1] : "";
}

function stampedPayloadPattern(snapshot, rowKey, kind) {
  const workspaceDir = workspaceDirForProject((snapshot && snapshot.project) || "");
  return workspaceDir && rowKey ? `${workspaceDir}/forensic_workbench_applied/<timestamp>_${rowKey}_${kind}_<hash>.json` : "";
}

function SourceImportPanel({ draft, setDraft, message, importing, event, liveMode, project, sourceList, sourceImportContract, onImport, onPreview, onAddToIntake, onOpenIntake }) {
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const filename = String(draft.filename || "").trim();
  const hasBody = Boolean(String(draft.body || "").trim());
  const validFilename = Boolean(filename && SOURCE_IMPORT_FILENAME_RE.test(filename));
  const duplicateFilename = sourceFilenameExists(sourceList, filename);
  const rawDir = String((sourceList && sourceList.raw_dir) || (project ? `projects/${project}/raw` : ""));
  const workspaceDir = sourceWorkspaceDir(sourceList, project);
  const sourceImportTemplates = Array.isArray(sourceImportContract && sourceImportContract.write_path_templates)
    ? sourceImportContract.write_path_templates
    : [];
  const pendingImportPaths = validFilename && rawDir && workspaceDir
    ? formatWriteTemplateItems(
        sourceImportContract,
        { project, filename },
        sourceImportTemplates.length
          ? sourceImportTemplates
          : [
              `${rawDir}/${filename}`,
              `${rawDir}/source_type_map.json`,
              `${workspaceDir}/forensic_workbench_source_imports.jsonl`,
              `${workspaceDir}/forensic_workbench_latest_source_import.json`
            ]
      )
    : [];
  const canImport = Boolean(liveMode && !importing && validFilename && hasBody && !duplicateFilename);
  const importTitle = !liveMode
    ? "Start the workbench server to import a source"
    : duplicateFilename
      ? "This filename already exists. Open it in Source files to edit."
      : !validFilename
        ? "Use a flat .md or .txt filename"
        : !hasBody
        ? "Enter a filename and source text"
        : "Write source file and receipt";
  const filenameNote = duplicateFilename
    ? "Existing source. Open it in Source files to edit."
    : filename && !validFilename
      ? "Use a flat .md or .txt filename."
      : "";
  const importedRefTarget = event && event.source_type === "source_evidence" ? "evidence files" : "source files";
  return h(
    "section",
    { className: "source-import-panel", "aria-label": "Add source" },
    h(
      "div",
      { className: "source-import-head" },
      h("span", { className: "eyebrow" }, "New source"),
      h("h2", null, "Add a source file"),
      h("p", null, message || "Write one source file into this project, record a receipt, then run file checks.")
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
        h("span", null, "Use this file as"),
        h(
          "select",
          { value: draft.source_type, onChange: (inputEvent) => setField("source_type", inputEvent.target.value) },
          SOURCE_TYPES.map((value) =>
            h("option", { key: value, value }, sourceTypeLabel(value))
          )
        ),
        h("small", { className: "source-import-note" }, SOURCE_TYPE_HELP[draft.source_type] || SOURCE_TYPE_HELP.untyped)
      ),
      h("label", { className: "source-import-body" }, h("span", null, "Text"), h("textarea", { value: draft.body, onInput: (inputEvent) => setField("body", inputEvent.target.value), rows: 5 }))
    ),
    pendingPathPreview(
      "Files that may change",
      pendingImportPaths,
      "Enter a valid filename to preview the source and receipt paths.",
      canImport
    ),
    h(WriteBoundary, {
      writeLabel: "Save source file writes one source file, file-role metadata, and a receipt.",
      readLabel: "Preview and Add to intake draft stay browser-only until you save the intake.",
      liveMode
    }),
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
        importing ? "Saving" : "Save source file"
      ),
      event
        ? h(
            "div",
            { className: "source-import-result" },
            h("strong", null, event.source_path || "source saved"),
            h("small", null, `${sourceTypeLabel(event.source_type || "source")} / ${(event.source_check && event.source_check.accepted) ? "file check passed" : "file check needs attention"}`),
            h("p", null, `Next: add this file to ${importedRefTarget}, then save the intake.`),
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
                onClick: () => onAddToIntake && onAddToIntake(event.source_path, event.source_type),
                title: `Stage this path in ${importedRefTarget}`
              },
              `Add to ${importedRefTarget}`
            ),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode,
                onClick: () => onOpenIntake && onOpenIntake(),
                title: "Open the intake editor to review and save staged source paths"
              },
              "Open intake"
            )
          )
        : null
    )
  );
}

function RawSourceManagerPanel({ sourceList, draft, setDraft, message, editing, event, liveMode, project, sourceEditContract, onOpenSource, onSave, onReload, onPreview, onOpenReadiness }) {
  const sources = (sourceList && sourceList.sources) || [];
  const sourceCount = Number((sourceList && sourceList.source_count) || sources.length || 0);
  const untypedCount = Number((sourceList && sourceList.untyped_source_count) || 0);
  const invalidTypeCount = Number((sourceList && sourceList.invalid_source_type_count) || 0);
  const typedCount = Math.max(0, sourceCount - untypedCount);
  const sourceHealth = invalidTypeCount
    ? `${invalidTypeCount} file role issue${invalidTypeCount === 1 ? "" : "s"}`
    : sourceCount
      ? `${typedCount}/${sourceCount} assigned a role`
      : "not loaded";
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const changedFields = sourceChangedFields(draft);
  const hasLoadedSource = Boolean(draft && draft.original && draft.relative_raw_path);
  const rawDir = String((sourceList && sourceList.raw_dir) || (project ? `projects/${project}/raw` : ""));
  const workspaceDir = sourceWorkspaceDir(sourceList, project);
  const sourceEditTemplates = Array.isArray(sourceEditContract && sourceEditContract.write_path_templates)
    ? sourceEditContract.write_path_templates
    : [];
  const pendingEditPaths = draft.relative_raw_path && rawDir && workspaceDir
    ? formatWriteTemplateItems(
        sourceEditContract,
        { project, relative: draft.relative_raw_path },
        sourceEditTemplates.length
          ? sourceEditTemplates
          : [
              `${rawDir}/${draft.relative_raw_path}`,
              `${rawDir}/source_type_map.json`,
              `${workspaceDir}/forensic_workbench_source_edits.jsonl`,
              `${workspaceDir}/forensic_workbench_latest_source_edit.json`
            ]
      )
    : [];
  const canSave = Boolean(liveMode && hasLoadedSource && changedFields.length && draft.body && draft.body.trim() && !editing);
  return h(
    "section",
    { className: "raw-source-manager", "aria-label": "Source files" },
    h(
      "div",
      { className: "raw-source-head" },
      h("span", { className: "eyebrow" }, "Source files"),
      h("h2", null, "Inspect and edit source files"),
      h("p", null, message || "Open a project source, edit the text or role, then save the change.")
    ),
    h(
      "div",
      { className: "raw-source-list" },
      h(
        "div",
        { className: "raw-source-list-head" },
        h(
          "div",
          { className: "raw-source-list-summary" },
          h("span", null, `${sourceCount || sources.length} files`),
          h("strong", { className: invalidTypeCount ? "attention" : "" }, sourceHealth)
        ),
        h(
          "button",
          {
            type: "button",
            className: "copy-button",
            disabled: !liveMode,
            onClick: onReload,
            title: liveMode ? "Reload source list" : "Start the workbench server to load source files"
          },
          "Reload"
        )
      ),
      sources.length
        ? sources.slice(0, 12).map((row) =>
            h(
              "div",
              { className: "raw-source-row", key: rawSourceRelative(row) || row.path },
              h("div", null, h("strong", null, rawSourceRelative(row) || row.path || "source"), h("small", null, `${sourceTypeLabel(row.source_type || "untyped")} / ${row.chars || 0} chars`)),
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
        : h("p", null, liveMode ? "No source files loaded yet." : "Start the workbench server to inspect source files.")
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
            title: "Source paths are selected from the list. Use Add source to create a new file."
          })
        ),
        h(
        "label",
        null,
          h("span", null, "Use this file as"),
          h(
            "select",
            { value: draft.source_type, onChange: (inputEvent) => setField("source_type", inputEvent.target.value) },
            SOURCE_TYPES.map((value) => h("option", { key: value, value }, sourceTypeLabel(value)))
          ),
          h("small", { className: "source-import-note" }, SOURCE_TYPE_HELP[draft.source_type] || SOURCE_TYPE_HELP.untyped)
        ),
        h("label", { className: "raw-source-body" }, h("span", null, "Text"), h("textarea", { value: draft.body, onInput: (inputEvent) => setField("body", inputEvent.target.value), rows: 8, placeholder: "Open a source to edit it here." }))
      ),
      h(
        "section",
        { className: `raw-source-pending ${changedFields.length ? "changed" : ""}`, "aria-label": "Unsaved source changes" },
        h("span", null, "Unsaved changes"),
        h("strong", null, changedFields.length ? `${changedFields.length} changed field${changedFields.length === 1 ? "" : "s"}` : "No changes"),
        h("p", null, changedFields.length ? changedFields.map(displayFieldName).join(", ") : "Open a source and edit the text or role before saving."),
        h("small", null, draft.relative_raw_path ? `Editing ${draft.relative_raw_path}` : "No source selected")
      ),
      pendingPathPreview(
        "Files that may change",
        pendingEditPaths,
        "Open a source to preview the source and receipt paths.",
        canSave
      ),
      h(WriteBoundary, {
        writeLabel: "Save source writes the source text, file role, and save receipt.",
        readLabel: "Edit opens a draft; Preview only reads the repository file.",
        liveMode
      }),
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
              h("small", null, `${sourceTypeLabel(event.source_type || "source")} / ${(event.source_check && event.source_check.accepted) ? "file check passed" : "file check needs attention"}`),
              h(SourceCheckDetail, { event }),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  disabled: !liveMode,
                  onClick: () => onOpenReadiness && onOpenReadiness(),
                  title: "Open file review after this save"
                },
                "Open file review"
              )
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
    { key: "source_refs", label: "Source files", rows: status.source_refs || [], type: "source" },
    { key: "evidence_refs", label: "Evidence files", rows: status.evidence_refs || [], type: "evidence" }
  ];

  return h(
    "section",
    { className: "intake-ref-status", "aria-label": "Intake reference status" },
    h(
      "div",
      { className: "intake-ref-summary" },
      h("span", null, "Files"),
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
                        title: liveMode ? "Preview this repository file" : "Start the workbench server to preview files"
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
          : h("p", null, "No files recorded.")
      )
    )
  );
}

function IntakeEditor({ draft, setDraft, liveMode, message, intakeEditContract, onSave, onReload, onPreviewRef }) {
  const update = (key) => (event) => {
    setDraft({ ...(draft || {}), [key]: event.target.value });
  };
  const disabled = !liveMode || !draft || draft.editable === false;
  const changedFields = intakeChangedFields(draft);
  const canSave = !disabled && changedFields.length > 0;
  const saveTitle = draft && draft.editable === false ? "Project-local intakes only" : disabled ? "Load a live intake first" : "Write intake edit receipt";
  const intakeProject = projectSlugFromProjectPath(draft && draft.path);
  const intakeWorkspaceDir = workspaceDirForProject(intakeProject);
  const intakeEditTemplates = Array.isArray(intakeEditContract && intakeEditContract.write_path_templates)
    ? intakeEditContract.write_path_templates
    : [];
  const pendingIntakePaths = draft && draft.path && intakeWorkspaceDir
    ? formatWriteTemplateItems(
        intakeEditContract,
        { project: intakeProject, intake: draft.path },
        intakeEditTemplates.length
          ? intakeEditTemplates
          : [
              draft.path,
              `${intakeWorkspaceDir}/forensic_workbench_intake_edits.jsonl`,
              `${intakeWorkspaceDir}/forensic_workbench_latest_intake_edit.json`
            ]
      )
    : [];
  return h(
    "section",
    { className: "intake-editor", "aria-label": "Project intake editor" },
    h(
      "div",
      { className: "intake-editor-head" },
      h("span", { className: "eyebrow" }, "Project intake"),
      h("h2", null, "Edit project intake"),
      h("p", null, message || (liveMode ? "Live edits write to the project intake and create an intake-edit receipt." : "Start the workbench server to edit the project intake."))
    ),
    h(
      "div",
      { className: "intake-editor-grid" },
      h(
        "label",
        null,
        h("span", null, "Working diagnosis"),
        h("textarea", {
          value: (draft && draft.bounded_claim) || "",
          onChange: update("bounded_claim"),
          disabled,
          "aria-label": "Working diagnosis"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "What would change it"),
        h("textarea", {
          value: (draft && draft.next_falsifier) || "",
          onChange: update("next_falsifier"),
          disabled,
          "aria-label": "What would change the diagnosis"
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
        h("span", null, "Ruled-out alternatives"),
        h("textarea", {
          value: (draft && draft.non_claims_text) || "",
          onChange: update("non_claims_text"),
          disabled,
          "aria-label": "Ruled-out alternatives"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Source files"),
        h("textarea", {
          value: (draft && draft.source_refs_text) || "",
          onChange: update("source_refs_text"),
          disabled,
          "aria-label": "Source files"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Evidence files"),
        h("textarea", {
          value: (draft && draft.evidence_refs_text) || "",
          onChange: update("evidence_refs_text"),
          disabled,
          "aria-label": "Evidence files"
        })
      )
    ),
    h(IntakeRefStatus, { draft, liveMode, onPreview: onPreviewRef }),
    h(
      "section",
      { className: `intake-write-preview ${changedFields.length ? "changed" : ""}`, "aria-label": "Unsaved intake changes" },
      h("span", null, "Unsaved changes"),
      h("strong", null, changedFields.length ? `${changedFields.length} changed field${changedFields.length === 1 ? "" : "s"}` : "No changes"),
      h("p", null, changedFields.length ? changedFields.map(displayFieldName).join(", ") : "Edit project-local fields before saving."),
      h("small", null, draft && draft.path ? `Editing ${draft.path}` : "No intake selected")
    ),
    pendingPathPreview(
      "Files that may change",
      pendingIntakePaths,
      "Load a project-local intake to preview the intake and receipt paths.",
      canSave
    ),
    h(WriteBoundary, {
      writeLabel: "Save intake writes the selected intake file and intake-edit receipt.",
      readLabel: "Reload and ref previews only read files from disk.",
      liveMode
    }),
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
          title: liveMode ? "Reload intake from disk" : "Start the workbench server first"
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
      h("p", null, message || (liveMode ? "Recent project writes from the local receipt ledgers." : "Start the workbench server to read receipt ledgers."))
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
            const receiptTarget = item.check_label || item.display_label || item.item_label || item.item_slug || item.row || item.row_slug || "";
            return h(
              "article",
              { className: `receipt-history-row ${item.kind || "receipt"}`, key: `${item.kind}:${item.path}:${item.line}` },
              h(
                "div",
                { className: "receipt-row-main" },
                h("strong", null, item.display_kind || displayText(item.kind || "receipt")),
                h("small", null, item.applied_at || `line ${item.line || "?"}`),
                h("p", null, item.display_summary || item.summary || "Receipt recorded.")
              ),
              h(
                "div",
                { className: "receipt-row-meta" },
                receiptTarget ? h("span", null, targetLabel(receiptTarget)) : null,
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
                    title: liveMode ? "Preview the receipt ledger" : "Start the workbench server to preview ledgers"
                  },
                  "Preview history"
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
        : h("p", null, liveMode ? "No receipts found for this project." : "Receipt history is available in live mode.")
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
  const sourcePaths = uniqueBackingFiles([
    surfaces.source_index_receipt_path ? { label: "Source receipt", path: surfaces.source_index_receipt_path } : null,
    surfaces.compile_provenance_path ? { label: "Evidence provenance", path: surfaces.compile_provenance_path } : null,
    ...graphRows.flatMap((row) =>
      (row.source_artifacts || []).map((path) => ({ label: row.graph_kind || "Graph source", path }))
    )
  ]);
  const status = (traceContext && (traceContext.display_readiness || displayText(traceContext.readiness))) || "loading";

  return h(
    "section",
    { className: `trace-console ${kernel.can_enter_kernel ? "ready" : "attention"}`, "aria-label": "Run plan console" },
    h(
      "div",
      { className: "trace-summary" },
      h("span", { className: "eyebrow" }, "Run plan"),
      h("h2", null, status),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Live run plan for this project, summarized from local checks."
            : "Start the workbench server to inspect the live run plan.")
      )
    ),
    h(
      "div",
      { className: "trace-metrics" },
      h("div", null, h("span", null, "Run check"), h("strong", null, kernel.display_status || displayText(kernel.status || "unknown"))),
      h("div", null, h("span", null, "Can run"), h("strong", null, kernel.can_enter_kernel ? "yes" : "no")),
      h("div", null, h("span", null, "Evidence"), h("strong", null, surfaces.display_evidence_status || displayText(surfaces.evidence_status || "unknown"))),
      h("div", null, h("span", null, "Plan"), h("strong", null, plan.display_status || displayText(plan.status || "unknown")))
    ),
    h(
      "div",
      { className: "trace-body" },
      h(
        "div",
        { className: "trace-section trace-commands" },
        h("span", null, "Command detail"),
        h("code", null, (traceContext && traceContext.trace_command) || "No run-plan command details loaded."),
        nextCommands.length
          ? nextCommands.slice(0, 3).map((command, index) =>
              h(
                "button",
                {
                  className: "copy-button",
                  type: "button",
                  key: `${index}:${command}`,
                  onClick: () => copyText(command),
                  title: "Copy run-plan command detail"
                },
                index === 0 ? "Copy first detail" : `Copy detail ${index + 1}`
              )
            )
          : h("p", null, "No command details loaded.")
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
                h("small", null, row.model_calls ? "model step" : "local"),
                h("p", null, row.description || displayText(row.status || "pending")),
                row.command
                  ? h(
                      "button",
                      {
                        className: "copy-button",
                        type: "button",
                        onClick: () => copyText(row.command),
                      title: "Copy plan command detail"
                      },
                      "Copy"
                    )
                  : null
              )
            )
          : h("p", null, "No plan steps loaded.")
      ),
      h(
        "div",
        { className: "trace-section trace-carriers" },
        h("span", null, "Run checks"),
        carrierRows.length
          ? carrierRows.slice(0, 8).map((row) =>
              h(
                "div",
                { className: `trace-carrier-row ${row.blocking ? "attention" : "ready"}`, key: row.surface },
                h("strong", null, row.display_surface || displayText(row.surface || "surface")),
                h("small", null, row.display_status || displayText(row.status || "unknown")),
                row.next_command
                  ? h(
                      "button",
                      {
                        className: "copy-button",
                        type: "button",
                        onClick: () => copyText(row.next_command),
                        title: "Copy run-check command detail"
                      },
                      "Copy"
                    )
                  : null
              )
            )
          : h("p", null, "No run checks loaded.")
      ),
      h(
        "div",
        { className: "trace-section" },
        h("span", null, "Evidence behind this view"),
        sourcePaths.length
          ? sourcePaths.map((item) =>
              h(
                "div",
                { className: "trace-file-row", key: item.path },
                h("strong", null, item.label),
                h("code", null, item.path),
                h(
                  "div",
                  { className: "trace-file-actions" },
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !previewableRepoPath(item.path),
                      onClick: () => onPreviewSource && onPreviewSource({ type: "file", value: item.path }),
                      title: previewFileTitle(liveMode, previewableRepoPath(item.path), "Preview this backing file")
                    },
                    "Preview"
                  ),
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      onClick: () => copyText(item.path),
                      title: "Copy backing file path"
                    },
                    "Copy path"
                  )
                )
              )
            )
          : h("p", null, "No backing files loaded.")
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
          : h("p", null, "No graph summaries loaded.")
      )
    )
  );
}

function PreflightRunPanel({ traceContext, event, message, running, liveMode, preflightContract, onRun }) {
  const kernel = (traceContext && traceContext.kernel_entry) || {};
  const loop = (event && event.trace && event.trace.loop_admission) || (traceContext && traceContext.loop_admission) || {};
  const command = kernel.preflight_command || (event && event.command) || "";
  const project = (traceContext && traceContext.project) || (event && event.project) || "";
  const canRun = Boolean(liveMode && command && !running);
  const accepted = event && event.accepted;
  const status = running ? "running" : event ? (accepted ? "accepted" : "needs attention") : command ? "ready" : "missing";
  const outputTail = event ? displayMessage(event.stderr_tail || event.stdout_tail || "").trim() : "";
  const snapshotNote = event && event.snapshot_error ? `Project refresh failed: ${displayMessage(event.snapshot_error)}` : "";
  const traceNote = event && event.trace_error ? `Run plan refresh failed: ${displayMessage(event.trace_error)}` : "";
  const writeBoundary = (event && event.write_boundary) || {};
  const writePaths = Array.isArray(writeBoundary.write_paths) ? writeBoundary.write_paths.filter(Boolean) : [];
  const preflightTemplates = Array.isArray(preflightContract && preflightContract.write_path_templates)
    ? preflightContract.write_path_templates
    : [];
  const expectedPreflightPaths = preflightTemplates.length
    ? formatWriteTemplateItems(preflightContract, { project }, preflightTemplates)
    : project
      ? formatWriteTemplateItems(preflightContract, { project }, [`projects/${project}/workspace/iteration_telemetry.jsonl`])
      : [];
  const expectedWritePaths = writePaths.length
    ? writePaths
    : expectedPreflightPaths;

  return h(
    "section",
    { className: `preflight-run-panel ${accepted ? "ready" : event ? "attention" : ""}`, "aria-label": "Preflight check" },
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
            ? "Run the local preflight only. This checks launch inputs and writes the normal preflight receipt; it does not start a model run."
            : "Start the workbench server to run preflight from the workbench.")
      )
    ),
    h(
      "div",
      { className: "preflight-run-command" },
      h("span", null, "Command detail"),
      h("code", null, command || "No command details loaded for this project."),
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
            title: canRun ? "Run local preflight only" : "Preflight requires live mode and loaded command details"
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
            title: "Copy preflight command detail"
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
      h("div", null, h("span", null, "Writes"), h("strong", null, writeBoundary.schema ? (writeBoundary.writes_project_files ? (writePaths.length ? `${writePaths.length} paths` : "preflight receipt") : "no project files") : "not run")),
      h("div", null, h("span", null, "Intake check"), h("strong", null, loop.intake_hash_verified === undefined ? "unknown" : loop.intake_hash_verified ? "verified" : "not verified"))
    ),
    pendingPathPreview(
      writePaths.length ? "Changed receipt path" : "Files that may change",
      expectedWritePaths,
      "Preflight writes the project telemetry receipt after the server runs the local check.",
      Boolean(writePaths.length)
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

function BoundedRunPanel({ traceContext, event, message, running, previewing, liveMode, runContract, onRun }) {
  const kernel = (traceContext && traceContext.kernel_entry) || {};
  const plan = (traceContext && traceContext.plan_preview) || {};
  const command = kernel.run_command || plan.recommended_first_command || (event && event.command) || "";
  const project = (traceContext && traceContext.project) || (event && event.project) || "";
  const ready = plan.status === "ready_for_bounded_run" && kernel.can_enter_kernel === true;
  const accepted = event && event.accepted;
  const canRun = Boolean(liveMode && command && ready && !running && !previewing);
  const status = running ? "running" : event ? (accepted ? "accepted" : "needs attention") : ready ? "ready" : "run preflight first";
  const modelWorkState = running ? "running" : event ? (accepted ? "started" : "not started") : ready ? "waiting for click" : "not ready";
  const outputTail = event ? displayMessage(event.stderr_tail || event.stdout_tail || "").trim() : "";
  const snapshotNote = event && event.snapshot_error ? `Project refresh failed: ${displayMessage(event.snapshot_error)}` : "";
  const traceNote = event && event.trace_error ? `Run plan refresh failed: ${displayMessage(event.trace_error)}` : "";
  const historyNote = event && event.run_history_error ? `Run history refresh failed: ${displayMessage(event.run_history_error)}` : "";
  const writeBoundary = (event && event.write_boundary) || {};
  const writePaths = Array.isArray(writeBoundary.write_paths) ? writeBoundary.write_paths.filter(Boolean) : [];
  const runTemplates = Array.isArray(runContract && runContract.write_path_templates)
    ? runContract.write_path_templates
    : [];
  const expectedRunPaths = runTemplates.length
    ? formatWriteTemplateItems(runContract, { project }, runTemplates)
    : project
      ? formatWriteTemplateItems(
          runContract,
          { project },
          [
            `projects/${project}/workspace/iteration_telemetry.jsonl`,
            `projects/${project}/latest_eval_results.json`,
            `projects/${project}/eval_results.jsonl`
          ]
        )
      : [];
  const expectedWritePaths = writePaths.length
    ? writePaths
    : expectedRunPaths;

  return h(
    "section",
    { className: `preflight-run-panel ${accepted ? "ready" : event || !ready ? "attention" : ""}`, "aria-label": "Project run" },
    h(
      "div",
      { className: "preflight-run-summary" },
      h("span", { className: "eyebrow" }, "Run"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? ready
              ? "Start the next project run from the workbench. This may call configured models and write project run files."
              : "Run preflight first; the project run becomes available after the run plan allows it."
            : "Start the workbench server to run this project.")
      )
    ),
    h(
      "div",
      { className: "preflight-run-command" },
      h("span", null, "Command detail"),
      h("code", null, command || "No command details loaded for this project."),
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
            title: canRun ? "Review model-backed run before starting" : "Run requires live mode, accepted preflight, and loaded command details"
          },
          running ? "Running" : previewing ? "Loading preview" : "Review and start"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !command,
            onClick: () => command && copyText(command),
            title: "Copy run command detail"
          },
          "Copy"
        )
      )
    ),
    h(
      "div",
      { className: "preflight-run-facts" },
      h("div", null, h("span", null, "Exit"), h("strong", null, event && event.returncode !== null && event.returncode !== undefined ? String(event.returncode) : "not run")),
      h("div", null, h("span", null, "Started"), h("strong", null, event ? (accepted ? "yes" : "no") : "not run")),
      h("div", null, h("span", null, "Run plan"), h("strong", null, displayText((event && event.plan_status) || plan.status || "unknown"))),
      h("div", null, h("span", null, "Writes"), h("strong", null, writeBoundary.schema ? (writeBoundary.writes_project_files ? (writePaths.length ? `${writePaths.length} paths` : "project run files") : "none") : "not run")),
      h("div", null, h("span", null, "Model calls"), h("strong", null, modelWorkState))
    ),
    h(
      "div",
      { className: "run-impact-strip", "aria-label": "Before you click" },
      h("span", null, "Before you click"),
      h("p", null, ready ? "Preflight accepted this project." : "Preflight must accept the project first."),
      h("p", null, "The next screen asks for confirmation before any model-backed run starts."),
      h("p", null, expectedWritePaths.length ? `Run output is written under projects/${project || "<project>"}.` : "No run-output path is loaded yet.")
    ),
    pendingPathPreview(
      "Files that may change",
      expectedWritePaths,
      "The server runs the selected project step and then refreshes run history.",
      Boolean(writePaths.length)
    ),
    outputTail || snapshotNote || traceNote || historyNote
      ? h(
          "div",
          { className: "preflight-run-output" },
          h("span", null, "Result"),
          snapshotNote ? h("p", null, snapshotNote) : null,
          traceNote ? h("p", null, traceNote) : null,
          historyNote ? h("p", null, historyNote) : null,
          outputTail ? h("pre", null, outputTail) : null
        )
      : null
  );
}

function RunHistoryPanel({ runHistory, message, liveMode, onPreview, onUseActionNote }) {
  const summary = (runHistory && runHistory.summary) || {};
  const latest = (runHistory && runHistory.latest_eval) || {};
  const synthesis = (runHistory && runHistory.synthesis_history) || {};
  const paths = (runHistory && runHistory.paths) || {};
  const recentRuns = (runHistory && runHistory.recent_runs) || [];
  const runScope = displayText((runHistory && runHistory.run_scope) || "project_run_history");
  const projectKey = (runHistory && (runHistory.project_key || runHistory.case_key)) || "";
  const intakePath = (runHistory && runHistory.intake) || "";
  const gaps = latest.evidence_gaps || [];
  const outcome = latest.probability_outcome || {};
  const probability = typeof outcome.probability === "number" ? `${Math.round(outcome.probability * 100)}%` : "not scored";
  const outcomeLabel = outcome.label || "No probability outcome recorded.";
  const scoreDelta = typeof summary.latest_score === "number" && typeof summary.best_score === "number"
    ? summary.latest_score - summary.best_score
    : null;
  const scoreDeltaLabel = scoreDelta === null ? "not available" : scoreDelta === 0 ? "matches best" : `${scoreDelta > 0 ? "+" : ""}${scoreDelta} vs best`;
  const patterns = [
    ...(synthesis.recurring_failures || []).map((text) => ({ label: "Failure", text })),
    ...(synthesis.major_pivots || []).map((text) => ({ label: "Pivot", text })),
    ...(synthesis.cross_run_patterns || []).map((text) => ({ label: "Pattern", text }))
  ].slice(0, 6);
  const stageWeakestPoint = () => {
    const weakest = latest.weakest_point || summary.latest_weakest_point || "";
    if (!weakest || !onUseActionNote) return;
    onUseActionNote(`Follow up on latest run weakest point: ${weakest}`, "next_step", "Run history");
  };
  const stageGap = (gap) => {
    if (!gap || !onUseActionNote) return;
    const target = gap.target || "evidence gap";
    const surface = gap.required_surface ? ` Required evidence: ${gap.required_surface}.` : "";
    const description = gap.description || "No gap detail recorded.";
    onUseActionNote(`Collect evidence for ${target}: ${description}${surface}`, "needs_source", "Evidence readiness");
  };

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
            : "Start the workbench server to inspect run history.")
      )
    ),
    h(
      "div",
      { className: "run-history-facts" },
      h("div", null, h("span", null, "Runs"), h("strong", null, String(summary.run_rows || 0))),
      h("div", null, h("span", null, "Best"), h("strong", null, summary.best_score === undefined || summary.best_score === null ? "none" : String(summary.best_score))),
      h("div", null, h("span", null, "Gaps"), h("strong", null, String(summary.latest_evidence_gap_count || 0))),
      h("div", null, h("span", null, "Run"), h("strong", null, summary.latest_run_id ? `${summary.latest_run_id}/${summary.latest_iteration ?? 0}` : "none")),
      h("div", null, h("span", null, "Run set"), h("strong", null, runScope)),
      h("div", null, h("span", null, "Project/intake"), h("strong", null, projectKey || "not connected")),
      intakePath ? h("div", null, h("span", null, "Intake"), h("strong", null, intakePath)) : null
    ),
    h(
      "div",
      { className: "run-history-verdict-card" },
      h("span", null, "Verdict"),
      h("strong", null, outcomeLabel),
      h(
        "div",
        { className: "run-history-verdict-grid" },
        h("div", null, h("span", null, "Confidence"), h("strong", null, probability)),
        h("div", null, h("span", null, "Latest vs best"), h("strong", null, scoreDeltaLabel)),
        h("div", null, h("span", null, "Evidence gaps"), h("strong", null, String(gaps.length || summary.latest_evidence_gap_count || 0)))
      )
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
      ),
      h(
        "button",
        {
          type: "button",
          className: "copy-button",
          disabled: !liveMode || !onUseActionNote || !(latest.weakest_point || summary.latest_weakest_point),
          onClick: stageWeakestPoint,
          title: "Stage this weakest point as a next step"
        },
        "Save next step"
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
                  "File"
                )
              )
            )
          )
        : h("p", null, "No runs found for this project.")
    ),
    h(
      "div",
      { className: "run-history-patterns" },
      h("span", null, "What still needs evidence"),
      gaps.length
        ? gaps.slice(0, 3).map((gap) =>
            h(
              "div",
              { className: "run-history-gap", key: `${gap.target}:${gap.severity}` },
              h("strong", null, gap.target || "Evidence gap"),
              h("small", null, displayText(gap.severity || "gap")),
              h("p", null, gap.description || gap.required_surface || "No gap detail recorded."),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  disabled: !liveMode || !onUseActionNote,
                  onClick: () => stageGap(gap),
                  title: "Stage this evidence gap as a next step"
                },
                "Save next step"
              )
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
          : h("p", null, "No evidence gaps or synthesis patterns loaded.")
    )
  );
}

function EvidenceSupportPanel({ claimSupport, message, liveMode, onPreview }) {
  const status = (claimSupport && claimSupport.status) || "loading";
  const displayStatus = (claimSupport && claimSupport.display_status) || displayText(status);
  const errors = (claimSupport && claimSupport.errors) || [];
  const sources = (claimSupport && claimSupport.source_context) || [];
  const rows = (claimSupport && claimSupport.rows) || [];
  const command = (claimSupport && claimSupport.command) || "";
  const evidenceFilePath =
    (claimSupport &&
      (claimSupport.evidence_support_file_path || claimSupport.evidence_file_path || claimSupport.packet_path)) ||
    "";
  const sourceIndexPath = (claimSupport && claimSupport.source_index_path) || "";
  const supportScope = displayText((claimSupport && claimSupport.support_scope) || "project_compiled_evidence");
  const projectKey = (claimSupport && (claimSupport.project_key || claimSupport.case_key)) || "";
  const intakePath = (claimSupport && claimSupport.intake) || "";
  const attention = errors.length > 0 || (claimSupport && claimSupport.accepted === false);

  return h(
    "section",
    { className: `claim-support-panel run-history-panel ${attention ? "attention" : "ready"}`, "aria-label": "Support audit" },
    h(
      "div",
      { className: "run-history-summary" },
      h("span", { className: "eyebrow" }, "Support audit"),
      h("h2", null, displayStatus),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Support summary loaded from the local project audit."
            : "Start the workbench server to inspect support-audit state.")
      )
    ),
    h(
      "div",
      { className: "run-history-facts" },
      h("div", null, h("span", null, "Evidence checks"), h("strong", null, String((claimSupport && claimSupport.claim_count) || 0))),
      h("div", null, h("span", null, "Needs stronger support"), h("strong", null, String((claimSupport && claimSupport.weak_or_unsourced_count) || 0))),
      h("div", null, h("span", null, "Source gaps"), h("strong", null, String((claimSupport && claimSupport.source_context_blocked_count) || 0))),
      h("div", null, h("span", null, "Sources"), h("strong", null, String(sources.length))),
      h("div", null, h("span", null, "Evidence set"), h("strong", null, supportScope)),
      h("div", null, h("span", null, "Project/intake"), h("strong", null, projectKey || "not connected")),
      intakePath ? h("div", null, h("span", null, "Intake"), h("strong", null, intakePath)) : null
    ),
    h(
      "div",
      { className: "run-history-verdict" },
      h("span", null, "Audit result"),
      errors.length
        ? errors.slice(0, 4).map((error) => h("p", { key: error }, displayMessage(error)))
        : h("p", null, rows.length ? `${rows.length} support note${rows.length === 1 ? "" : "s"} loaded.` : "No support gaps loaded."),
      h(
        "div",
        { className: "run-history-paths" },
        [
          { label: "Evidence file", path: evidenceFilePath },
          { label: "File index", path: sourceIndexPath }
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
              h("small", null, `${displayText(source.status || "unknown")} / ${sourceTypeLabel(source.source_type || "untyped")}`),
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
      h("span", null, "Command detail"),
      h("code", null, command || "No support-audit command details loaded."),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          disabled: !command,
          onClick: () => copyText(command),
          title: "Copy support-audit command detail"
        },
        "Copy detail"
      )
    )
  );
}

function ReportContractPanel({ reportContext, message, liveMode, onPreview }) {
  const binding = (reportContext && reportContext.synthesis_input_binding) || {};
  const reasons = (reportContext && reportContext.status_reasons) || [];
  const displayReasons = (reportContext && reportContext.display_status_reasons) || reasons.map(displayText);
  const supportIssues = (reportContext && reportContext.support_issues) || [];
  const contractPath = (reportContext && reportContext.report_support_contract) || "";
  const command = (reportContext && reportContext.command) || "";
  const reportLoaded = Boolean((reportContext && reportContext.schema) || contractPath || command);
  const bindingLoaded = Boolean(binding.schema || binding.status || binding.reason);
  const status = (reportContext && reportContext.status) || "loading";
  const displayStatus = (reportContext && reportContext.display_status) || displayText(status);
  const reportScope = displayText((reportContext && reportContext.report_scope) || "project_report_support");
  const projectKey = (reportContext && (reportContext.project_key || reportContext.case_key)) || "";
  const intakePath = (reportContext && reportContext.intake) || "";
  const backingFiles = uniqueBackingFiles(
    (reportContext && reportContext.backing_files) ||
      (contractPath ? [{ label: "Report support file", path: contractPath }] : [])
  );
  const isBlocked = status === "blocked" || supportIssues.length > 0 || reasons.length > 0 || binding.status === "unbound";

  return h(
    "section",
    { className: `report-contract-panel ${isBlocked ? "attention" : "ready"}`, "aria-label": "Report support" },
    h(
      "div",
      { className: "report-contract-summary" },
      h("span", { className: "eyebrow" }, "Report"),
      h("h2", null, displayStatus),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Report readiness loaded from the workbench server."
            : "Start the workbench server to inspect report readiness.")
      )
    ),
    h(
      "div",
      { className: "report-contract-metrics" },
      h("div", null, h("span", null, "Report inputs"), h("strong", null, binding.display_status || displayText(binding.status || "unknown"))),
      h("div", null, h("span", null, "Files"), h("strong", null, String(binding.artifact_count ?? "none"))),
      h("div", null, h("span", null, "Current file"), h("strong", null, shortDigest(binding.current_digest))),
      h("div", null, h("span", null, "Recorded file"), h("strong", null, shortDigest(binding.ledger_digest))),
      h("div", null, h("span", null, "Report set"), h("strong", null, reportScope)),
      h("div", null, h("span", null, "Project/intake"), h("strong", null, projectKey || "not connected")),
      intakePath ? h("div", null, h("span", null, "Intake"), h("strong", null, intakePath)) : null
    ),
    h(
      "div",
      { className: "report-contract-body" },
      h(
        "div",
        { className: "report-contract-section" },
        h("span", null, "Before relying on report"),
        supportIssues.length
          ? supportIssues.map((issue, index) =>
              h(
                "div",
                { className: "report-support-issue", key: issue.id || issue.reason || index },
                h("strong", null, displayMessage(issue.display_reason || issue.reason || "Report support issue")),
                issue.display_status || issue.status
                  ? h("small", null, displayText(issue.display_status || issue.status))
                  : null
              )
            )
          : reasons.length
            ? reasons.map((reason, index) => h("strong", { key: reason }, displayReasons[index] || displayText(reason)))
          : h("p", null, "No report support issues loaded.")
      ),
      h(
        "div",
        { className: "report-contract-section" },
        h("span", null, "Inputs"),
        h("p", null, binding.reason || "No binding reason loaded."),
        h("small", null, bindingLoaded ? "Report inputs loaded" : "Report inputs not loaded")
      ),
      h(
        "div",
        { className: "report-contract-section report-contract-file" },
        h("span", null, "Evidence behind report"),
        backingFiles.length
          ? backingFiles.map((item) =>
              h(
                "div",
                { className: "report-contract-backing-file", key: item.path },
                h("strong", null, item.label),
                h("code", null, item.path),
                h(
                  "div",
                  { className: "report-contract-actions" },
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !previewableRepoPath(item.path),
                      onClick: () => onPreview && onPreview({ type: "report", value: item.path }),
                      title: previewFileTitle(liveMode, previewableRepoPath(item.path), "Preview this backing file")
                    },
                    "Preview"
                  ),
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      onClick: () => copyText(item.path),
                      title: "Copy backing file path"
                    },
                    "Copy path"
                  )
                )
              )
            )
          : h("p", null, "No report backing files loaded.")
      ),
      h(
        "div",
        { className: "report-contract-section report-contract-command" },
        h("span", null, "Command detail"),
        h("small", null, reportLoaded ? "Report support loaded" : "Report support not loaded"),
        h("code", null, command || "No report command details loaded."),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !command,
            onClick: () => copyText(command),
            title: "Copy report command detail"
          },
          "Copy detail"
        )
      )
    )
  );
}

function CaseFilePanel({ snapshot, receiptHistory, projectEntry, intakeDraft, sourceImportDraft, sourceEditDraft, traceContext, workflowContext, reportContext, healthContext, serverStatus, preflightEvent, sourceListContext, sourceActionEvent, sourceImportEvent, sourceEditEvent, runHistoryContext, claimSupportContext, writeReceiptEvent, refreshResults, selectedRow, liveMode, saving, saveEvent, projectFileContract, onSave, onPreview }) {
  let caseFile = buildCaseFile(snapshot, receiptHistory, {
    projectEntry,
    intakeDraft,
    sourceImportDraft,
    sourceEditDraft,
    traceContext,
    workflowContext,
    reportContext,
    healthContext,
    serverStatus,
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
  const caseItems = Array.isArray(caseFile.project_checks)
    ? caseFile.project_checks
    : Array.isArray(caseFile.items)
      ? caseFile.items
      : caseFile.rows || [];
  const itemsWithEvidence = caseItems.filter((item) => item.evidence_refs.length).length;
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
      Object.keys(caseFile.live_context.health.action_guidance.counts || {}).length ||
      caseFile.live_context.health.action_guidance.issues.length ||
      caseFile.live_context.health.action_guidance.recommendations.length,
    caseFile.live_context.preflight_result,
    caseFile.live_context.sources.schema ||
      caseFile.live_context.sources.source_count ||
      caseFile.live_context.sources.raw_dir,
    caseFile.live_context.latest_source_action,
    caseFile.live_context.latest_source_import,
    caseFile.live_context.latest_source_edit,
    caseFile.live_context.latest_write_receipt,
    caseFile.live_context.workflow.schema || (caseFile.live_context.workflow.steps || []).length,
    pendingIntake,
    pendingSourceImport,
    pendingSourceEdit,
    caseFile.live_context.run_history.schema || Object.keys(caseFile.live_context.run_history.summary || {}).length,
    (caseFile.live_context.evidence_support || caseFile.live_context.claim_support || {}).schema ||
      (caseFile.live_context.evidence_support || caseFile.live_context.claim_support || {}).status
  ].filter(Boolean).length;
  const filename = caseFileDownloadName(snapshot);
  const caseDigest = useSha256Hex(caseKey(snapshot));
  const caseWorkspaceDir = workspaceDirForProject(snapshot.project || "");
  const projectFileTemplates = Array.isArray(projectFileContract && projectFileContract.write_path_templates)
    ? projectFileContract.write_path_templates
    : [];
  const pendingCaseFilePaths = projectFileTemplates.length && caseDigest
    ? formatWriteTemplateItems(projectFileContract, {
        project: snapshot.project,
        project_file_digest: caseDigest.slice(0, 12)
      }, projectFileTemplates)
    : caseWorkspaceDir && caseDigest
    ? formatWriteTemplateItems(
        projectFileContract,
        {
          project: snapshot.project,
          project_file_digest: caseDigest.slice(0, 12)
        },
        [
          `${caseWorkspaceDir}/forensic_workbench_case_file_${caseDigest.slice(0, 12)}.json`,
          `${caseWorkspaceDir}/forensic_workbench_case_files.jsonl`,
          `${caseWorkspaceDir}/forensic_workbench_latest_case_file_write.json`
        ]
      )
    : [];
  const preflightStatus = caseFile.live_context.preflight_result
    ? (caseFile.live_context.preflight_result.accepted ? "Accepted" : "Needs attention")
    : "Not run";
  const sourceFileCount = caseFile.live_context.sources.source_count || 0;
  const reportSupport = reportStatusLabel(snapshot.report_status, snapshot.display_report_status);
  const evidenceSupportContext = caseFile.live_context.evidence_support || caseFile.live_context.claim_support || {};
  const evidenceSupport = reportStatusLabel(evidenceSupportContext.status || "not loaded");
  const workflowNextStep =
    caseFile.live_context.workflow.next_step_label ||
    (caseFile.live_context.workflow.next_step || {}).label ||
    (caseFile.live_context.workflow.summary || {}).next_step_label ||
    "not loaded";
  const pendingDrafts = [
    pendingIntake && pendingIntake.changed_fields.length ? "intake changes" : "",
    pendingSourceImport && pendingSourceImport.status === "pending_unsaved" ? "source draft" : "",
    pendingSourceEdit && pendingSourceEdit.changed_fields.length ? "source edit" : ""
  ].filter(Boolean);
  const projectFileReady = Boolean(liveMode && caseItems.length && liveContextCount >= 5);
  const savedCasePath = saveEvent && !saveEvent.error ? saveEvent.path || "" : "";
  const savedReceiptPath = saveEvent && !saveEvent.error ? saveEvent.latest || saveEvent.receipt_path || "" : "";
  const pendingDraftText = pendingDrafts.join(", ");
  const fileChangeStatus =
    caseFile.live_context.workbench_status.file_change_summary ||
    caseFile.live_context.workbench_status.action_summary ||
    {};
  const fileChangeWriteCount = fileChangeStatus.write_count ?? fileChangeStatus.write_without_confirmation_count;
  const fileChangeAskFirstCount = fileChangeStatus.ask_first_count ?? fileChangeStatus.confirmation_required_count;
  const fileChangeSplit =
    fileChangeWriteCount !== undefined
      ? `${fileChangeWriteCount || 0} write / ${fileChangeAskFirstCount || 0} ask first / ${fileChangeStatus.read_only_count || 0} read-only`
      : "not loaded";
  const projectFileState = caseFile.live_context.workflow.project_file_saved
    ? "saved before"
    : projectFileReady
      ? "ready to save"
      : "loading context";
  const projectFileWritePlan = {
    schema: "ztare-forensic-workbench-project-file-write-plan-v1",
    writes_project_files: Boolean(liveMode && pendingCaseFilePaths.length),
    browser_writes: false,
    write_paths: pendingCaseFilePaths.map((item) => item.path).filter(Boolean),
    display_write_paths: pendingCaseFilePaths,
    read_only_actions: ["preview", "download", "copy"],
    state: projectFileState
  };
  caseFile = {
    ...caseFile,
    live_context: {
      ...caseFile.live_context,
      project_file_write_plan: projectFileWritePlan
    }
  };
  const caseFileJson = JSON.stringify(caseFile, null, 2);
  const previewCaseFile = cleanCaseFilePreview(caseFile);
  const previewJson = JSON.stringify(previewCaseFile, null, 2);
  const previewLimit = 5000;
  const previewText = previewJson.length > previewLimit ? `${previewJson.slice(0, previewLimit)}\n...` : previewJson;
  const summary = caseFileSummary(snapshot, receiptHistory, caseFile);
  const includedDetailFacts = [
    ["Receipts", String(caseFile.recent_receipts.length)],
    ["Command details", String((caseFile.audit_commands || caseFile.command_queue || []).length)],
    ["Open issues", String(caseItems.length)],
    ["Evidence-linked checks", String(itemsWithEvidence)],
    ["Next project step", workflowNextStep],
    ["Latest score", caseFile.live_context.run_history.summary.latest_score === undefined || caseFile.live_context.run_history.summary.latest_score === null ? "none" : String(caseFile.live_context.run_history.summary.latest_score)],
    ["Source check", caseFile.live_context.latest_source_action ? displayText(caseFile.live_context.latest_source_action.action) : "not run"],
    ["New source", caseFile.live_context.latest_source_import ? sourceTypeLabel(caseFile.live_context.latest_source_import.source_type) : "none"],
    ["Source edit", caseFile.live_context.latest_source_edit ? sourceTypeLabel(caseFile.live_context.latest_source_edit.source_type) : "none"],
    ["Refresh checks", writeRefreshRows.length ? `${writeRefreshOk}/${writeRefreshRows.length} checked` : "not run"],
    ["Advisories", String(caseFile.live_context.health.action_guidance.recommendations.length || 0)],
    ["File-change behavior", fileChangeSplit],
    ["Loaded project context", String(liveContextCount)],
    ["Project file", projectFileState],
    ["Receipt", "Project file receipt"]
  ];
  const handoffReadiness = [
    { label: "Open issues", ready: Boolean(caseItems.length), value: caseItems.length ? `${caseItems.length} loaded` : "not loaded" },
    { label: "Source files", ready: Boolean(sourceFileCount), value: sourceFileCount ? `${sourceFileCount} files` : "not loaded" },
    { label: "Project steps", ready: Boolean(caseFile.live_context.workflow.schema || (caseFile.live_context.workflow.steps || []).length), value: workflowNextStep },
    { label: "Report support", ready: Boolean(reportContext && (reportContext.schema || reportContext.status)), value: reportSupport },
    { label: "Receipts", ready: Boolean(caseFile.recent_receipts.length), value: caseFile.recent_receipts.length ? `${caseFile.recent_receipts.length} loaded` : "none loaded" },
    { label: "Run history", ready: Boolean(caseFile.live_context.run_history.schema || Object.keys(caseFile.live_context.run_history.summary || {}).length), value: caseFile.live_context.run_history.summary.latest_score === undefined || caseFile.live_context.run_history.summary.latest_score === null ? "not loaded" : `score ${caseFile.live_context.run_history.summary.latest_score}` },
    { label: "Support audit", ready: Boolean(evidenceSupportContext.schema || evidenceSupportContext.status), value: evidenceSupport }
  ];

  return h(
    "section",
    { className: "case-file-panel", "aria-label": "Project file" },
    h(
      "div",
      { className: "case-file-copy" },
      h("span", { className: "eyebrow" }, "Project file"),
      h("h2", null, "Save this project"),
      h("p", null, "Save the current project state, receipts, command details, and file paths.")
    ),
    h(
      "div",
      { className: "case-file-facts" },
      h(
        "div",
        { className: "case-file-primary-facts" },
        h("div", null, h("span", null, "Save status"), h("strong", null, projectFileReady ? "Ready to save" : liveMode ? "Loading context" : "Start server")),
        h("div", null, h("span", null, "Report"), h("strong", null, reportSupport)),
        h("div", null, h("span", null, "Preflight"), h("strong", null, preflightStatus)),
        h("div", null, h("span", null, "Source files"), h("strong", null, sourceFileCount ? `${sourceFileCount} files` : "Not loaded")),
        h("div", null, h("span", null, "Support audit"), h("strong", null, evidenceSupport)),
        h("div", null, h("span", null, "Unsaved work"), h("strong", null, pendingDrafts.length ? pendingDraftText : "None found"))
      ),
      h(
        "details",
        { className: "case-file-detail-facts" },
        h("summary", null, "What gets included"),
        h(
          "div",
          { className: "case-file-detail-grid" },
          includedDetailFacts.map(([label, value]) =>
            h("div", { key: label }, h("span", null, label), h("strong", null, value))
          )
        )
      )
    ),
    h(
      "section",
      { className: "case-file-readiness", "aria-label": "Project file included state" },
      h(
        "div",
        { className: "case-file-readiness-copy" },
        h("span", { className: "eyebrow" }, "Included now"),
        h("strong", null, projectFileReady ? "Project file has live context" : "Waiting for live context"),
        h(
          "p",
          null,
          projectFileReady
            ? "The saved file will include project state, support checks, receipts, and next-step context."
            : "Save waits until enough live sections are loaded. Download and copy still use the preview."
        )
      ),
      h(
        "div",
        { className: "case-file-readiness-grid" },
        handoffReadiness.map((item) =>
          h(
            "div",
            { key: item.label, className: item.ready ? "ready" : "attention" },
            h("span", null, item.label),
            h("strong", null, item.value)
          )
        )
      )
    ),
    h(WriteBoundary, {
      writeLabel: "Project file and receipt",
      readLabel: "Download, copy, preview",
      liveMode
    }),
    pendingPathPreview(
      "Files that may change",
      pendingCaseFilePaths,
      "Project file path is calculated from the selected project and intake.",
      Boolean(liveMode && pendingCaseFilePaths.length)
    ),
    h(
      "div",
      { className: "case-file-preview", "aria-label": "Project data preview" },
      h(
        "div",
        { className: "case-file-preview-head" },
        h("span", null, "Project data preview"),
        h("strong", null, "Inspectable project file"),
        h("small", null, `${previewJson.length} characters${previewJson.length > previewLimit ? " / preview truncated" : ""}`)
      ),
      h("pre", null, previewText)
    ),
    h(
      "div",
      { className: "case-file-actions" },
      h("code", null, filename),
      h(
        "small",
        { className: `case-file-boundary ${pendingDrafts.length ? "attention" : ""}` },
        liveMode
          ? !projectFileReady
            ? "Save waits for loaded project context so the project file is not thin. Download and copy use the current preview."
            : pendingDrafts.length
            ? `Save writes a project file that mentions unsaved ${pendingDraftText}; apply those edits separately. Download and copy stay browser-only.`
            : "Save updates the project folder. Download and copy stay browser-only."
          : "Save is offline. Download and copy still work."
      ),
      h(
        "button",
        {
          className: "copy-button primary",
          type: "button",
          disabled: !projectFileReady || saving,
          onClick: () => onSave && onSave(caseFile),
          title: liveMode
            ? !projectFileReady
              ? "Wait for live workflow, evidence, source, run, and receipt context before saving"
              : pendingDrafts.length
              ? "Save the project file preview; unsaved edits are not applied"
              : "Save the current project file to the project folder"
            : "Start the workbench server to save project files"
        },
        saving ? "Saving" : "Save to project folder"
      ),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: () => downloadText(filename, caseFileJson),
          title: "Download the current project file"
        },
        "Download project file"
      ),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: () => copyText(caseFileJson),
          title: "Copy project file"
        },
        "Copy project file"
      ),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: () => copyText(summary),
          title: "Copy a short project summary"
        },
        "Copy summary"
      ),
      saveEvent
        ? h(
            "div",
            { className: `case-file-save-note ${saveEvent.error ? "attention" : "ready"}` },
            h(
              "span",
              null,
              saveEvent.error
                ? `Save failed: ${saveEvent.error}`
                : `Saved ${savedCasePath || "project file"}; receipt ${savedReceiptPath || "recorded"}.`
            ),
            !saveEvent.error
              ? h(
                  "div",
                  { className: "case-file-save-actions" },
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !savedCasePath,
                      onClick: () => onPreview && onPreview({ type: "file", value: savedCasePath }),
                      title: savedCasePath ? "Preview saved project file" : "No saved project file path recorded"
                    },
                    "Preview saved file"
                  ),
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !savedReceiptPath,
                      onClick: () => onPreview && onPreview({ type: "receipt", value: savedReceiptPath }),
                      title: savedReceiptPath ? "Preview latest project-file receipt" : "No receipt path recorded"
                    },
                    "Preview receipt"
                  )
                )
              : null
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

function StageRail({ snapshot, onInspectRow }) {
  const rows = snapshot.rows || [];
  return h(
    "section",
    { className: "stage-rail", "aria-label": "Support checks" },
    STAGES.map((stage) => {
      const row = rowByLabel(rows, stage.rowLabel);
      const tone = statusClass(row);
      return h(
        "button",
        {
          key: stage.id,
          type: "button",
          className: `stage-card ${tone}`,
          onClick: () => row && onInspectRow(row.label),
          disabled: !row
        },
        h("span", { className: "stage-index" }, stage.label),
        h("strong", null, row ? itemStatus(row) : "not recorded"),
      h("small", null, row ? itemDetail(row) : "No project check loaded.")
      );
    })
  );
}

function ClaimSummary({ snapshot }) {
  const rows = snapshot.rows || [];
  const claim = rowByLabel(rows, "Bounded claim");
  const nonClaims = rowByLabel(rows, "Non-claims");
  const assumptions = rowByLabel(rows, "Assumptions and constraints");
  const falsifier = rowByLabel(rows, "Next falsifier");
  const reportSupportRow = rowByLabel(rows, "Report support");
  return h(
    "section",
    { className: "case-summary", "aria-label": "Diagnosis review summary" },
    h(
      "div",
      { className: "claim-panel" },
      h("span", { className: "eyebrow" }, "Diagnosis"),
      h("p", null, claim ? claim.detail : "No working diagnosis recorded.")
    ),
    h(
      "div",
      { className: "case-facts" },
      h("div", null, h("span", null, "Report"), h("strong", null, reportSupportRow ? itemStatus(reportSupportRow) : reportStatusLabel(snapshot.report_status, snapshot.display_report_status))),
      h("div", null, h("span", null, "Ruled-out alternatives"), h("strong", null, nonClaims ? itemStatus(nonClaims) : "none")),
      h("div", null, h("span", null, "Assumptions and constraints"), h("strong", null, assumptions ? itemStatus(assumptions) : "not loaded")),
      h("div", null, h("span", null, "What could change it"), h("strong", null, falsifier ? itemStatus(falsifier) : "not loaded"))
    )
  );
}

function ProjectReviewSummary({ snapshot, selectedRow }) {
  const rows = snapshot.rows || [];
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const reportRow = rowByLabel(rows, "Report support");
  const reviewRow = rowByLabel(rows, "Latest review receipt");
  const activeRow = activeBlocker(rows) || selectedRow || reportRow || rows[0] || null;
  const sourceStatus = sourceRow ? displayText(sourceRow.status) : "not recorded";
  const evidenceStatus = evidenceRow ? displayText(evidenceRow.status) : "not recorded";
  const reviewStatus = reviewRow ? displayText(reviewRow.status) : "no receipt";
  const activeEvidence = activeRow ? evidenceItems(activeRow) : [];

  return h(
    "section",
    { className: "case-docket", "aria-label": "Project review summary" },
    h(
      "div",
      { className: `docket-item ${snapshot.report_status === "blocked" ? "attention" : "ready"}` },
      h("span", null, "Report support"),
      h("strong", null, reportStatusLabel(snapshot.report_status, snapshot.display_report_status)),
      h("small", null, reportRow ? itemDetail(reportRow) : "No report support check recorded.")
    ),
    h(
      "div",
      { className: "docket-item ready" },
      h("span", null, "Evidence files"),
      h("strong", null, `${sourceStatus} / ${evidenceStatus}`),
      h("small", null, `${activeEvidence.length} backing links on the selected project check`)
    ),
    h(
      "div",
      { className: reviewRow && reviewRow.kind === "ready" ? "docket-item ready" : "docket-item neutral" },
      h("span", null, "Review receipt"),
      h("strong", null, reviewStatus),
      h("small", null, reviewRow ? displayMessage(reviewRow.detail) : "No review receipt recorded.")
    )
  );
}

function SourceEvidencePanel({ snapshot, traceContext, liveMode, onPreview, onInspectRow, sourceActionContracts, sourceActionEvent, sourceActionMessage, sourceActionRunning, onRunSourceAction }) {
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
    surfaces.compile_provenance_path ? { label: "Evidence receipt", value: surfaces.compile_provenance_path } : null
  ].filter(Boolean);
  const commands = [
    sourceRow.command ? { label: "Source check detail", value: sourceRow.command, row: "Source readiness" } : null,
    evidenceRow.command ? { label: "Evidence check detail", value: evidenceRow.command, row: "Evidence readiness" } : null
  ].filter(Boolean);
  const readinessRows = [sourceRow, evidenceRow].filter((row) => row.label);
  const project = (snapshot && snapshot.project) || "<project>";
  const formatProjectTemplate = (template) => String(template || "").replaceAll("{project}", project);
  const actionDefinitions = [
    {
      action: "source_check",
      label: "Check source files",
      commandTemplate: "ztare project source-check --project {project} --json",
      writes: false,
      expectedWriteTemplates: []
    },
    {
      action: "source_index",
      label: "Refresh file index",
      commandTemplate: "ztare project source-index --project {project} --index-only --json",
      writes: true,
      expectedWriteTemplates: [
        "projects/{project}/workspace/source_index.json",
        "projects/{project}/workspace/workspace_meta.json",
        "projects/{project}/workspace/source_index_receipt.json",
        "projects/{project}/workspace/forensic_workbench_source_actions.jsonl",
        "projects/{project}/workspace/forensic_workbench_latest_source_action.json"
      ]
    },
    {
      action: "evidence_bind",
      label: "Connect evidence files",
      commandTemplate: "ztare project evidence-bind --project {project} --json",
      writes: true,
      expectedWriteTemplates: [
        "projects/{project}/workspace/evidence_output_binding_receipt.json",
        "projects/{project}/workspace/forensic_workbench_source_actions.jsonl",
        "projects/{project}/workspace/forensic_workbench_latest_source_action.json"
      ]
    },
    {
      action: "evidence_replay",
      label: "Check evidence files",
      commandTemplate: "ztare project evidence-replay --project {project} --json",
      writes: false,
      expectedWriteTemplates: []
    }
  ];
  const actionButtons = actionDefinitions.map((definition) => {
    const contract = (sourceActionContracts && sourceActionContracts[definition.action]) || {};
    const writes =
      typeof contract.writes_project_files === "boolean"
        ? contract.writes_project_files
        : definition.writes;
    const commandTemplate = contract.command_template || definition.commandTemplate;
    const writeTemplates = Array.isArray(contract.write_path_templates)
      ? contract.write_path_templates
      : definition.expectedWriteTemplates;
    return {
      ...definition,
      label: contract.label || definition.label,
      command: formatProjectTemplate(commandTemplate),
      mode: contract.mode || (writes ? "writes project files" : "read-only"),
      writes,
      expectedWrites: writes ? formatWriteTemplateItems(contract, { project: snapshot.project }, writeTemplates) : []
    };
  });

  return h(
    "section",
    { className: `source-evidence-panel ${attention ? "attention" : "ready"}`, "aria-label": "Source and evidence file checks" },
    h(
      "div",
      { className: "source-evidence-summary" },
      h("span", { className: "eyebrow" }, "Sources and evidence"),
      h("h2", null, `${displayText(sourceStatus)} / ${displayText(evidenceStatus)}`),
      h("p", null, "Inspect source files, evidence files, check results, and the receipts behind them.")
    ),
    h(
      "div",
      { className: "source-evidence-metrics" },
      h("div", null, h("span", null, "Source files"), h("strong", null, displayText(sourceStatus))),
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
        h("span", null, "Check files"),
        readinessRows.length
          ? readinessRows.map((row) =>
              h(
                "button",
                {
                  key: row.label,
                  type: "button",
                  className: `source-evidence-row ${row.kind === "attention" ? "attention" : "ready"}`,
                  onClick: () => onInspectRow(row.label),
                  title: `Inspect ${itemLabel(row)}`
                },
                h("strong", null, itemLabel(row)),
                h("small", null, itemDetail(row) || itemStatus(row))
              )
            )
          : h("p", null, "No source or evidence checks loaded yet.")
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
                    title: liveMode ? "Preview source/evidence file" : "Start the workbench server to preview files"
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
        h("span", null, "Command details"),
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
                    title: "Copy file-check command"
                  },
                  "Copy"
                )
              )
            )
          : h("p", null, "No source/evidence command details loaded.")
      ),
      h(
        "div",
        { className: "source-evidence-section source-evidence-actions" },
        h("span", null, "Source checks"),
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
                  title: liveMode ? item.command : "Start the workbench server to run source checks"
                },
                sourceActionRunning && sourceActionEvent && sourceActionEvent.action === item.action ? "Running" : item.label
              ),
              h("small", null, item.mode),
              item.expectedWrites.length
                ? h(
                    "div",
                    { className: "source-evidence-expected-writes", "aria-label": `${item.label} files that may change` },
                    h("span", null, "Files that may change"),
                    item.expectedWrites.map((writeItem) =>
                      h(
                        "div",
                        { className: "pending-path-row", key: writeItem.path || writeItem },
                        h("strong", null, writeItem.label || writePathLabel(writeItem.path || writeItem)),
                        h("code", null, writeItem.path || writeItem)
                      )
                    )
                  )
                : null,
              h("code", null, item.command)
            )
          )
        ),
        h("p", null, sourceActionMessage || "Run a fixed local file check; command details and result stay visible."),
        sourceActionEvent
          ? h(
              "div",
              { className: `source-evidence-action-result ${sourceActionEvent.accepted ? "ready" : "attention"}` },
              h("strong", null, `${sourceActionEvent.label || displayText(sourceActionEvent.action)}: ${sourceActionEvent.accepted ? "accepted" : "attention"}`),
              h("code", null, sourceActionEvent.command || "No command details recorded."),
              sourceActionEvent.stdout_tail ? h("pre", null, displayMessage(sourceActionEvent.stdout_tail)) : null,
              sourceActionEvent.stderr_tail ? h("pre", null, displayMessage(sourceActionEvent.stderr_tail)) : null
            )
          : null
      )
    )
  );
}

function rowSignal(row) {
  if (row.kind === "attention") return "Review";
  if (row.kind === "ready") return "Ready";
  return "Recorded";
}

function evidenceTypeLabel(type) {
  const labels = {
    file: "File",
    source: "Source",
    evidence: "Evidence",
    command: "Audit",
    receipt: "Receipt",
    review: "Review",
    warning: "Warning"
  };
  return labels[type] || displayText(type);
}

function EvidenceType({ type }) {
  return h("span", { className: `evidence-type ${type}` }, evidenceTypeLabel(type));
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
            title: liveMode ? "Preview file" : "Start the workbench server to preview files",
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
        title: isCommand ? "Copy detail" : "Copy evidence value",
        onClick: () => copyText(item.value)
      },
      isCommand ? "Copy" : "Copy value"
    )
  );
}

function Sidebar({
  snapshot,
  counts,
  activeWorkspace,
  activeSubsection,
  setActiveWorkspace,
  setActiveSubsection,
  projects,
  projectFolders,
  selectedProjectKey,
  liveMode,
  loadingSnapshot,
  onSelectProject,
  onOpenProjects,
  onNavigateWorkspace,
  onOpenDetail
}) {
  const activeProjectKey = selectedProjectKey || projectEntryKey(snapshot);
  const activeSection = WORKSPACE_SECTIONS.find((item) => item.id === activeWorkspace) || WORKSPACE_SECTIONS[0];
  const readyRows = liveMode && projects.length
    ? projects
    : [{ project: snapshot.project, intake: snapshot.intake, rubric: snapshot.rubric, intake_source: snapshot.intake_source }];
  const readyByProject = new Map(readyRows.map((project) => [project.project, project]));
  const projectRows = liveMode && Array.isArray(projectFolders) && projectFolders.length
    ? projectFolders.map((folder) => ({ ...folder, ...(readyByProject.get(folder.project) || {}), openable: readyByProject.has(folder.project) }))
    : readyRows;
  projectRows.sort(projectInventorySort);
  const currentProjectRow = projectRows.find((project) => {
    const key = projectEntryKey(project);
    return key === activeProjectKey || (!activeProjectKey && project.project === snapshot.project);
  }) || null;
  const sideProjectRows = [
    ...(currentProjectRow ? [currentProjectRow] : []),
    ...projectRows.filter((project) => project !== currentProjectRow)
  ].slice(0, 10);
  const folderCount = Array.isArray(projectFolders) ? projectFolders.length : 0;
  const openableProjectKeys = new Set(readyRows.map((project) => project.project).filter(Boolean));
  const pendingFolderCount = Array.isArray(projectFolders)
    ? projectFolders.filter((folder) => !openableProjectKeys.has(folder.project)).length
    : 0;
  return h(
    "aside",
    { className: "sidebar" },
    h("div", { className: "brand-lockup" }, h("div", { className: "brand-mark" }, "ZT"), h("div", { className: "side-title" }, h("strong", null, "ZTARE"), h("span", null, "Project Workbench"))),
    h(
      "nav",
      { className: "side-nav", "aria-label": "Workbench sections" },
      WORKSPACE_SECTIONS.map((item) =>
        h(
          "button",
          {
            type: "button",
            key: item.id,
            className: activeWorkspace === item.id ? "active" : "",
            onClick: () => {
              if (onNavigateWorkspace) onNavigateWorkspace(item.id, item.subnav[0]);
              else {
                setActiveWorkspace(item.id);
                setActiveSubsection(item.subnav[0]);
              }
            }
          },
          h("span", { className: `nav-icon ${item.id}`, "aria-hidden": "true" }),
          h("span", { className: "nav-label" }, item.label)
        )
      )
    ),
    h(
      "section",
      { className: "side-subnav", "aria-label": `${activeSection.label} submenu` },
      h("span", null, activeSection.label),
      h(
        "div",
        { className: "side-subnav-list" },
        activeSection.subnav.map((subsection) => {
          const copy = detailCopy(activeSection.id, subsection);
          const active = activeSubsection === subsection;
          return h(
            "button",
            {
              key: subsection,
              type: "button",
              className: active ? "active" : "",
              onClick: () => {
                if (onNavigateWorkspace) {
                  onNavigateWorkspace(activeSection.id, subsection);
                } else {
                  setActiveWorkspace(activeSection.id);
                  setActiveSubsection(subsection);
                }
              },
              title: copy.body
            },
            h("strong", null, subsection),
            h("small", null, copy.title)
          );
        })
      )
    ),
    h(
      "section",
      { className: "side-projects", "aria-label": "Projects" },
      h(
        "div",
        { className: "side-projects-head" },
        h(
          "div",
          { className: "side-projects-title" },
          h("span", null, "Projects"),
          h("small", null, liveMode ? `${folderCount || projectRows.length} total / ${openableProjectKeys.size} intake ready` : "offline project data")
        ),
        h(
          "button",
          {
            type: "button",
            disabled: !liveMode,
          title: liveMode ? `Open ${folderCount || projectRows.length} project folders` : "Start the workbench server to list projects",
            onClick: () => {
              if (onOpenProjects) onOpenProjects();
            }
          },
          "All projects"
        )
      ),
      h(
        "div",
        { className: "side-project-list" },
        sideProjectRows.map((project) => {
          const key = projectEntryKey(project);
          const active = key === activeProjectKey || (!activeProjectKey && project.project === snapshot.project);
          const refSummary = project.intake_ref_summary || {};
          const openable = Boolean(project.openable || project.intake);
          const status = project.intake_error
            ? "Needs intake"
            : openable && refSummary.total
              ? `${refSummary.present || 0}/${refSummary.total} files`
              : openable
                ? displayText(project.intake_source || "project intake")
                : "needs intake";
          return h(
            "button",
            {
              key: key || project.project,
              type: "button",
              className: active ? "active" : "",
              disabled: loadingSnapshot || !liveMode || active,
              onClick: () => {
                if (openable) onSelectProject && onSelectProject(key || project.project);
                else if (onOpenProjects) onOpenProjects();
              },
              title: !openable ? "Open All projects to add an intake" : liveMode ? `Open ${project.display_label || titleFromSlug(project.project || "current project")} (${project.project || "current project"})` : "Start the workbench server to switch projects"
            },
            h("strong", null, project.display_label || titleFromSlug(project.project || "current project")),
            h("span", null, status)
          );
        })
      )
    ),
    h(
      "div",
      { className: "side-footer" },
      h("span", null, "Open issues"),
      h("strong", null, `${counts.attention ? `${counts.attention} need review` : "ready"} / ${counts.total}`),
      h("span", null, "Report support"),
      h("strong", null, reportStatusLabel(snapshot.report_status, snapshot.display_report_status))
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
    { className: "command-rail", "aria-label": "Current focus" },
    h(
      "div",
      { className: "next-action" },
      h("span", null, "Current focus"),
      h("strong", null, actionRow ? `${itemLabel(actionRow)}: ${displayText(actionRow.status)}` : "No selected project check"),
      h("p", null, actionRow ? actionRow.detail : "This project has no project checks loaded yet.")
    ),
    h(
      "div",
      { className: "command-card" },
      h("span", null, actionCommand ? "Command detail" : "Evidence"),
      actionCommand ? h("code", null, actionCommand) : h("code", null, actionRow && actionRow.provenance ? actionRow.provenance : "No command details recorded."),
      actionCommand
        ? h(
            "button",
            {
              className: "copy-button",
              type: "button",
              title: "Copy current command detail",
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
  if (blocker) add({ label: "Current report issue", command: blocker.command, source: blocker.label, rowLabel: blocker.label, priority: 5 });
  if (selectedRow) add({ label: "Current focus", command: selectedRow.command, source: selectedRow.label, rowLabel: selectedRow.label, priority: 10 });
  const plan = (traceContext && traceContext.plan_preview) || {};
  add({ label: "Recommended detail", command: plan.recommended_first_command, source: "Run plan", rowLabel: "Run readiness", priority: 15 });
  ((traceContext && traceContext.next_commands) || []).slice(0, 4).forEach((command, index) =>
    add({ label: index === 0 ? "Run-plan detail" : `Run-plan detail ${index + 1}`, command, source: "Run plan", rowLabel: "Run readiness", priority: 20 + index })
  );
  add({ label: "Report support", command: reportContext && reportContext.command, source: "Report support", rowLabel: "Report support", priority: 30 });
  add({ label: "Support audit", command: claimSupportContext && claimSupportContext.command, source: "Support audit", rowLabel: "Evidence readiness", priority: 35 });
  (((healthContext && healthContext.kernel) || {}).attention_components || []).forEach((row, index) =>
    add({ label: "Run-health detail", command: row.next_command, source: row.component || "Run health", rowLabel: "Run health", priority: 40 + index })
  );
  rows.forEach((row, index) => add({ label: "Project-check detail", command: row.command, source: itemLabel(row), rowLabel: row.label, priority: 60 + index }));
  return items.sort((left, right) => left.priority - right.priority).slice(0, 8);
}

function CommandCockpit({ snapshot, selectedRow, traceContext, reportContext, healthContext, claimSupportContext, onInspectRow }) {
  const commands = commandCockpitItems({ snapshot, selectedRow, traceContext, reportContext, healthContext, claimSupportContext });
  const firstCommand = commands[0] || null;
  return h(
    "section",
    { className: "command-cockpit", "aria-label": "Audit command details" },
    h(
      "div",
      { className: "command-cockpit-summary" },
      h("span", { className: "eyebrow" }, "Command details"),
      h("h2", null, firstCommand ? firstCommand.label : "No command details loaded"),
      h("p", null, "Use app buttons for normal work. Command details stay here for inspection.")
    ),
    h(
      "div",
      { className: "command-cockpit-primary" },
      h("span", null, "Command detail"),
      h("code", null, firstCommand ? firstCommand.command : "No command details loaded for this project."),
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
            title: "Copy detail"
          },
          "Copy detail"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !firstCommand || !firstCommand.rowLabel,
            onClick: () => firstCommand && firstCommand.rowLabel && onInspectRow(firstCommand.rowLabel),
            title: "Inspect the project check behind these command details"
          },
          "Inspect"
        )
      )
    ),
    h(
      "div",
      { className: "command-cockpit-list" },
      h("span", null, "Command details"),
      commands.length
        ? commands.map((item) =>
            h(
              "div",
              { className: "command-cockpit-row", key: item.command },
              h("strong", null, item.label),
              h("small", null, itemLabel(item.source || "project context")),
              h("code", null, item.command),
              h(
                "button",
                {
                  className: "copy-button",
                  type: "button",
                  onClick: () => copyText(item.command),
                  title: "Copy detail"
                },
                "Copy"
              )
            )
          )
        : h("p", null, "No command details loaded. Inspect evidence and receipt paths instead.")
    )
  );
}

function NextMovePanel({ snapshot, selectedRow, onInspectRow, onReviewRow, liveMode }) {
  const rows = snapshot.rows || [];
  const blocker = activeBlocker(rows);
  const actionRow = blocker || selectedRow || rows[0] || null;
  const actionCommand = (actionRow && actionRow.command) || "";
  const evidence = actionRow ? evidenceItems(actionRow)[0] : null;
  const status = actionRow ? displayText(actionRow.status) : "No project check selected";
  const title = blocker ? "Review the report issue" : "Inspect the project state";
  const why = actionRow
    ? shortText(actionRow.detail, 210)
    : "Project data has no project checks. Refresh the workbench data before reviewing this project.";
  const evidenceText = evidence ? `${evidence.label}: ${evidence.value}` : "No evidence recorded for this project check.";

  return h(
    "section",
    { className: `next-move-panel ${blocker ? "attention" : "ready"}`, "aria-label": "Next step" },
    h(
      "div",
      { className: "next-move-copy" },
      h("span", { className: "eyebrow" }, blocker ? "Needs review" : "Next step"),
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
          onClick: () => actionRow && (blocker ? onReviewRow(actionRow.label) : onInspectRow(actionRow.label))
        },
        blocker ? "Review report issue" : "Inspect"
      ),
      actionCommand
        ? h(
            "button",
            {
              type: "button",
              className: "copy-button",
              title: "Copy detail",
              onClick: () => copyText(actionCommand)
            },
            "Copy detail"
          )
        : null,
      h("a", { href: snapshotJsonHref(snapshot, liveMode), className: "text-link", title: "Open backing JSON data" }, "Project data")
    )
  );
}

function BlockerPanel({ snapshot, onReviewRow }) {
  const rows = snapshot.rows || [];
  const blocker = activeBlocker(rows);
  return h(
    "section",
    { className: `blocker-panel ${blocker ? "attention" : "ready"}`, "aria-label": "Status reasons" },
    h(
      "div",
      null,
      h("span", null, blocker ? "Current report issue" : "Report review"),
      h("strong", null, blocker ? itemLabel(blocker) : reportStatusLabel(snapshot.report_status, snapshot.display_report_status)),
      h("p", null, blocker ? itemDetail(blocker) : "No report issue is active in the loaded project data.")
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
              onClick: () => onReviewRow(blocker.label)
            },
            "Review report issue"
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
    { className: "provenance-strip", "aria-label": "File coverage" },
    h("div", null, h("span", null, "Open issues with files"), h("strong", null, coverageText)),
    h("div", null, h("span", null, "Command details"), h("strong", null, String(coverage.commandRows))),
    h("div", null, h("span", null, "Receipts"), h("strong", null, String(coverage.receiptRows))),
    h("div", null, h("span", null, "Review files"), h("strong", null, String(coverage.reviewRows)))
  );
}

function ReviewQueue({ row, reviewState, receiptHistory, snapshot, liveMode, onPreview }) {
  const decision = reviewState.decision || "unreviewed";
  const decisionLabel = (REVIEW_ACTIONS.find((action) => action.id === decision) || { label: "Unreviewed" }).label;
  const evidenceCount = row ? evidenceItems(row).length : 0;
  const lastReview = latestReceiptForRow(receiptHistory, row, "review", snapshot);
  const lastAction = latestReceiptForRow(receiptHistory, row, "next_step", snapshot);
  const lastReviewPath = receiptArtifactPath(lastReview);
  const lastActionPath = receiptArtifactPath(lastAction);
  const receiptState = row && decision !== "unreviewed" ? (liveMode ? "ready to save" : "file ready") : "review status needed";
  const renderReceiptCell = (label, receipt, path, stateText) =>
    h(
      "div",
      { className: "review-queue-receipt" },
      h("span", null, label),
      h("strong", null, receipt ? displayText(stateText || "recorded") : "none"),
      h("code", null, path || "no saved file path"),
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
            title: path ? `Copy ${label.toLowerCase()} path` : "No saved file path recorded"
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
            title: liveMode && path ? `Preview ${label.toLowerCase()}` : "Start the workbench server to preview saved files"
          },
          "Preview"
        )
      )
    );
  return h(
    "section",
    { className: `review-queue ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Review queue" },
    h("div", null, h("span", null, "Project check"), h("strong", null, row ? itemLabel(row) : "No project check selected")),
    h("div", null, h("span", null, "Review status"), h("strong", null, decisionLabel)),
    h("div", null, h("span", null, "Files"), h("strong", null, String(evidenceCount))),
    h("div", null, h("span", null, "Receipt"), h("strong", null, receiptState)),
    renderReceiptCell("Last review", lastReview, lastReviewPath, lastReview && lastReview.decision),
    renderReceiptCell("Last next step", lastAction, lastActionPath, lastAction && lastAction.action)
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
  const action = (healthContext && (healthContext.action_guidance || healthContext.action_intelligence)) || {};
  const actionCounts = action.counts || {};
  const attention = kernel.attention_components || [];
  const issues = action.issues || [];
  const recommendations = action.recommendations || [];
  const sourcePaths = action.source_paths || {};
  const status = kernelSummary.overall_status || (liveMode ? "loading" : "offline snapshot");
  const previewableSourcePaths = Object.entries(sourcePaths).filter(([_key, value]) => value);
  const recommendationSource = action.recommendations_source_path || "";
  const recommendationGeneratedAt = action.recommendations_generated_at || "";
  const sourceHealthPath = sourcePaths.source_health || "";
  const recomputeCommand = kernelSummary.recompute_command || "";
  const healthProvenanceRows = [
    { label: "Run health", value: kernelSummary.source ? displayText(kernelSummary.source) : "not loaded" },
    { label: "Full audit", value: recomputeCommand || "not loaded", copy: recomputeCommand },
    { label: "Recommendations", value: recommendationSource || "not loaded", preview: recommendationSource },
    { label: "Generated", value: recommendationGeneratedAt || "not recorded" },
    { label: "Source warnings", value: sourceHealthPath || "not loaded", preview: sourceHealthPath }
  ];
  const renderEvidenceRefs = (items) =>
    items.length
      ? h(
          "div",
          { className: "health-evidence-refs" },
          items.map((item) =>
            h(
              "div",
              { className: "health-evidence-ref", key: `${item.label}:${item.path}` },
              h("strong", null, item.label || "Evidence file"),
              h("code", null, item.path),
              h(
                "div",
                { className: "health-source-actions" },
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    onClick: () => copyText(item.path),
                    title: "Copy evidence path"
                  },
                  "Copy"
                ),
                h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !liveMode || !isPreviewableRepoPath(item.path),
                    onClick: () => onPreviewSource && onPreviewSource({ type: "file", value: item.path }),
                    title:
                      liveMode && isPreviewableRepoPath(item.path)
                        ? "Preview evidence path"
                        : "Start the workbench server to preview repository files"
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
    { className: `health-actions-panel ${status === "attention" || issues.length ? "attention" : "ready"}`, "aria-label": "Advisories and suggested next steps" },
    h(
      "div",
      { className: "health-summary" },
      h("span", { className: "eyebrow" }, "Project health"),
      h("h2", null, displayText(status)),
      h(
        "p",
        null,
        healthMessage ||
          (liveMode
            ? "Live checks and suggested next moves for this project."
            : "Start the workbench server to inspect live checks and suggested next moves.")
      ),
      h(
        "div",
        { className: "health-provenance" },
        healthProvenanceRows.map((row) =>
          h(
            "div",
            { key: row.label },
            h("span", null, row.label),
            h("code", null, row.value),
            row.preview
              ? h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    disabled: !liveMode || !isPreviewableRepoPath(row.preview),
                    onClick: () => onPreviewSource && onPreviewSource({ type: "file", value: row.preview }),
                    title: liveMode && isPreviewableRepoPath(row.preview) ? "Preview backing file" : "Start the workbench server to preview repository files"
                  },
                  "Preview"
                )
              : row.copy
                ? h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      onClick: () => copyText(row.copy),
                      title: "Copy detail"
                    },
                    "Copy"
                  )
                : null
          )
        )
      )
    ),
    h(
      "div",
      { className: "health-metrics" },
      h("div", null, h("span", null, "Run checks"), h("strong", null, displayText(kernelSummary.component_status || status))),
      h("div", null, h("span", null, "Attention"), h("strong", null, String((kernelSummary.component_counts || {}).attention || attention.length || 0))),
      h("div", null, h("span", null, "Source issues"), h("strong", null, String(actionCounts.issues || issues.length || 0))),
      h("div", null, h("span", null, "Advisory next moves"), h("strong", null, String(recommendations.length || 0))),
      h("div", null, h("span", null, "Advisories"), h("strong", null, String(actionCounts.warning || 0)))
    ),
    h(
      "div",
      { className: "health-findings" },
      h(HealthFindingList, {
        title: "Run checks",
        emptyText: "Run checks have no active attention item.",
        rows: attention,
        renderRow: (row, index) =>
          h(
            "div",
            { className: "health-finding-row kernel", key: `${row.component || "kernel"}:${index}` },
            h("strong", null, row.display_component || guidanceLabel(row.component || "run component")),
            h("small", null, row.display_status || displayText(row.status || "attention")),
            h("p", null, row.display_action || guidanceText(row.action || "Inspect component.")),
            row.next_command
              ? h(
                  "button",
                  {
                    className: "copy-button",
                    type: "button",
                    onClick: () => copyText(row.next_command),
                    title: "Copy run-health command detail"
                  },
                  "Copy detail"
                )
              : null
          )
      }),
      h(HealthFindingList, {
        title: "Source issues",
        emptyText: "No source issues.",
        rows: issues,
        renderRow: (row, index) => {
          const evidenceRefs = evidenceRefDisplayItems(row);
          const affectedDomains = Array.isArray(row.display_affected_domains) && row.display_affected_domains.length
            ? row.display_affected_domains.filter(Boolean)
            : Array.isArray(row.affected_domains) ? row.affected_domains.filter(Boolean).map(guidanceLabel) : [];
          const countText = warningCountText(row);
          const actionNote = actionIntelligenceNote(row, "Inspect source warning");
          return h(
            "div",
            { className: "health-finding-row action", key: `${row.issue_id || row.issue_type || "issue"}:${row.scope || index}` },
            h("strong", null, row.display_issue_type || guidanceLabel(row.issue_type || "source warning")),
            h("small", null, [row.display_severity || guidanceLabel(row.severity || "warning"), row.display_scope || (row.scope ? guidanceLabel(row.scope) : ""), countText].filter(Boolean).join(" | ")),
            h("p", null, row.display_blocking_rule || guidanceText(row.blocking_rule || row.recommended_action || "Inspect source warning.")),
            row.recommended_action
              ? h("p", { className: "health-action-next" }, `Next: ${row.display_recommended_action || guidanceLabel(row.recommended_action)}`)
              : null,
            affectedDomains.length
              ? h("p", { className: "health-action-domains" }, `Affects: ${affectedDomains.join(", ")}`)
              : null,
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => onUseActionNote && onUseActionNote(actionNote, actionIntelligenceAction(row)),
                title: "Stage this issue in the next-step editor"
              },
              "Stage next step"
            ),
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => copyText(actionNote),
                title: "Copy this issue as a next-step note"
              },
              "Copy note"
            ),
            renderEvidenceRefs(evidenceRefs)
          );
        }
      }),
      h(HealthFindingList, {
        title: "Advisory next moves",
        emptyText: "No advisory next moves loaded.",
        rows: recommendations,
        renderRow: (row, index) => {
          const evidenceRefs = evidenceRefDisplayItems(row).slice(0, 3);
          const estimate = recommendationEstimate(row);
          const actionNote = actionIntelligenceNote(row, "Inspect advisory recommendation");
          const boundary = recommendationBoundary(row);
          return h(
            "div",
            { className: "health-finding-row recommendation", key: `${row.recommendation_id || "recommendation"}:${index}` },
            h("strong", null, row.display_recommended_action || guidanceLabel(row.recommended_action || "recommendation")),
            h("small", null, recommendationMeta(row)),
            h("p", null, row.display_rationale || guidanceText(row.rationale || "Inspect the backing recommendation before acting.")),
            boundary
              ? h("p", { className: "health-action-domains" }, `Boundary: ${boundary}`)
              : null,
            estimate
              ? h("p", { className: "health-action-domains" }, estimate)
              : null,
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => onUseActionNote && onUseActionNote(actionNote, actionIntelligenceAction(row)),
                title: "Stage this suggestion in the next-step editor"
              },
              "Stage next step"
            ),
            h(
              "button",
              {
                className: "copy-button",
                type: "button",
                onClick: () => copyText(actionNote),
                title: "Copy this suggestion as a next-step note"
              },
              "Copy note"
            ),
            renderEvidenceRefs(evidenceRefs)
          );
        }
      }),
      h(
        "div",
        { className: "health-source-list" },
        h("span", null, "Warning source files"),
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
                      title: liveMode ? "Preview source file" : "Start the workbench server to preview files"
                    },
                    "Preview"
                  )
                )
              )
            )
        : h("p", null, "No source warning files reported.")
      )
    )
  );
}

function ReviewWorkspace({ snapshot, row, reviewState, setReviewState, liveMode, reviewContract, applyReviewLive }) {
  const decision = reviewState.decision || "unreviewed";
  const reviewFile = buildReviewFile(snapshot, row, reviewState);
  const reviewPayload = parseReviewFile(reviewFile);
  const rowKey = row ? rowSlug(row.label) : "";
  const reviewFilename = row ? caseScopedDownloadName(snapshot, rowKey, "review") : "review.json";
  const intakeArg = snapshot.intake ? ` --intake ${snapshot.intake}` : "";
  const command = row
    ? `ztare forensic-workbench apply-review --project ${snapshot.project}${intakeArg} --project-check ${rowKey} --from ${reviewFilename}`
    : "";
  const workspaceDir = workspaceDirForProject(snapshot.project || "");
  const reviewTemplates = Array.isArray(reviewContract && reviewContract.write_path_templates)
    ? reviewContract.write_path_templates
    : [];
  const pendingReviewPaths = row && workspaceDir
      ? formatWriteTemplateItems(
        reviewContract,
        { project: snapshot.project, project_check_slug: rowKey, item_slug: rowKey },
        reviewTemplates.length
          ? reviewTemplates
          : [
              stampedPayloadPattern(snapshot, rowKey, "review"),
              `${workspaceDir}/forensic_workbench_reviews.jsonl`,
              `${workspaceDir}/forensic_workbench_latest_review.json`
            ]
      )
    : [];
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
    { className: `review-workspace ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Review status" },
	    h(
	      "div",
	      { className: "review-copy" },
	      h("span", { className: "eyebrow" }, "Review status"),
	      h("h2", null, row ? itemLabel(row) : "Select a project check"),
	      h("p", null, row ? "Mark this project check reviewed, deferred, or holding the report." : "Choose a project check first.")
	    ),
    h(ReviewPointContextCard, { row }),
	    h(
	      "div",
	      { className: "review-actions", role: "group", "aria-label": "Review statuses" },
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
      placeholder: "Review note for this project check",
      "aria-label": "Review note"
    }),
    h(WriteBoundary, {
      writeLabel: "Review receipt",
      readLabel: "Download, copy, command detail",
      liveMode
    }),
    h(SavePathSummary, {
      title: "This will save",
      target: row ? `${itemLabel(row)} - ${(REVIEW_ACTIONS.find((action) => action.id === decision) || { label: "Unreviewed" }).label}` : "",
      note: liveReady
        ? "The review status and note will be saved to this project with a receipt."
        : row
          ? "Choose a review status before saving."
          : "Select a project check before saving.",
      paths: pendingReviewPaths,
      ready: liveReady
    }),
    pendingPathPreview(
      "Files that may change",
      pendingReviewPaths,
      "Select a project check to preview the review file and receipt paths.",
      liveReady
    ),
    h(
      "div",
      { className: "handoff-card" },
        h("div", null, h("span", null, "Optional command detail"), h("code", null, command || "No project check selected")),
      h(
        "p",
        null,
        liveMode ? "Review receipt is ready to save." : "Review receipt is ready for download or copy."
      ),
      h(
        "div",
        { className: "handoff-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            title: liveReady ? "Save review" : "Start the workbench server and choose a review status first",
            onClick: () => liveReady && applyReviewLive(rowKey, reviewPayload),
            disabled: !liveReady
          },
          "Save review"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: reviewReady ? "Download review file" : "Choose a review status first",
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
            title: reviewReady ? "Copy review file" : "Choose a review status first",
            onClick: () => copyText(reviewFile),
            disabled: !reviewReady
          },
          "Copy review file"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: row ? "Copy apply-review command detail" : "Select a project check first",
            onClick: () => copyText(command),
            disabled: !row
          },
          "Copy detail"
        )
      )
    ),
    h(
      "details",
      { className: "review-preview" },
      h("summary", null, "Inspect review file"),
      h("pre", null, reviewFile || "Select a project check and review status to preview the review file.")
    )
  );
}

function RowActionWorkspace({ snapshot, row, actionState, setActionState, liveMode, nextStepContract, applyRowActionLive }) {
  const suggestion = rowActionSuggestion(snapshot, row);
  const action = actionState.action || "next_step";
  const rowActionFile = buildRowActionFile(snapshot, row, actionState);
  const rowActionPayload = parseReviewFile(rowActionFile);
  const rowKey = row ? rowSlug(row.label) : "";
  const actionFilename = row ? caseScopedDownloadName(snapshot, rowKey, "action") : "next_step.json";
  const intakeArg = snapshot.intake ? ` --intake ${snapshot.intake}` : "";
  const command = row
    ? `ztare forensic-workbench save-next-step --project ${snapshot.project}${intakeArg} --project-check ${rowKey} --from ${actionFilename}`
    : "";
  const workspaceDir = workspaceDirForProject(snapshot.project || "");
  const nextStepTemplates = Array.isArray(nextStepContract && nextStepContract.write_path_templates)
    ? nextStepContract.write_path_templates
    : [];
  const pendingActionPaths = row && workspaceDir
      ? formatWriteTemplateItems(
        nextStepContract,
        { project: snapshot.project, project_check_slug: rowKey, item_slug: rowKey },
        nextStepTemplates.length
          ? nextStepTemplates
          : [
              stampedPayloadPattern(snapshot, rowKey, "action"),
              `${workspaceDir}/forensic_workbench_row_actions.jsonl`,
              `${workspaceDir}/forensic_workbench_latest_row_action.json`
            ]
      )
    : [];
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
    { className: `row-action-workspace ${row && row.kind === "attention" ? "attention" : ""}`, "aria-label": "Saved next step" },
    h(
      "div",
      { className: "review-copy" },
      h("span", { className: "eyebrow" }, "Saved next step"),
	      h("h2", null, row ? itemLabel(row) : "Select a project check"),
	      h("p", null, row ? "Write the next concrete move for this project check." : "Choose a project check first.")
	    ),
    h(ReviewPointContextCard, { row }),
	    h(
	      "div",
	      { className: "review-actions", role: "group", "aria-label": "Saved next steps" },
      ITEM_ACTIONS.map((item) =>
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
      h("span", null, "Suggested next step"),
      h("strong", null, suggestion.title),
      h("p", null, `${ITEM_ACTION_LABELS[suggestion.action] || "Next step"}: ${suggestion.note}`),
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
            title: row ? "Use the suggested next step and note" : "Select a project check first"
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
              "Copy detail"
            )
          : null
      )
    ),
    h("textarea", {
      value: actionState.note || "",
      onChange: updateNote,
      disabled: !row,
      placeholder: "Concrete next step, source need, or report issue",
      "aria-label": "Saved next-step note"
    }),
    h(WriteBoundary, {
      writeLabel: "Saved next-step receipt",
      readLabel: "Download, copy, command detail",
      liveMode
    }),
    h(SavePathSummary, {
      title: "This will save",
      target: row ? `${itemLabel(row)} - ${ITEM_ACTION_LABELS[action] || "Next step"}` : "",
      note: actionReady
        ? "The next step will be saved to this project with a receipt."
        : row
          ? "Write the concrete next step before saving."
          : "Select a project check before saving.",
      paths: pendingActionPaths,
      ready: liveReady
    }),
    pendingPathPreview(
      "Files that may change",
      pendingActionPaths,
      "Select a project check to preview the next-step file and receipt paths.",
      liveReady
    ),
    h(
      "div",
      { className: "handoff-card" },
        h("div", null, h("span", null, "Optional command detail"), h("code", null, command || "No project check selected")),
      h(
        "p",
        null,
        liveMode ? "Next-step receipt is ready to save." : "Next-step receipt is ready for download or copy."
      ),
      h(
        "div",
        { className: "handoff-actions" },
        h(
          "button",
          {
            className: "copy-button primary",
            type: "button",
            title: actionReady ? "Save this next step" : "Write a next-step note first",
            onClick: () => liveReady && applyRowActionLive(rowKey, rowActionPayload),
            disabled: !liveReady
          },
          "Save next step"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: actionReady ? "Download next-step file" : "Write a next-step note first",
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
            title: actionReady ? "Copy next-step file" : "Write a next-step note first",
            onClick: () => copyText(rowActionFile),
            disabled: !actionReady
          },
          "Copy next-step file"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            title: row ? "Copy save-next-step command detail" : "Select a project check first",
            onClick: () => copyText(command),
            disabled: !row
          },
          "Copy detail"
        )
      )
    )
  );
}

function WriteReceiptPanel({ receiptEvent, refreshResults, liveMode, onPreview }) {
  if (!receiptEvent) return null;
  const result = receiptEvent.result || {};
  const receipt = result.receipt || {};
  const writeBoundary = result.write_boundary || {};
  const noWrite = Boolean(receiptEvent.noWrite || (writeBoundary.schema && result.ok === false && !writeBoundary.writes_project_files));
  const writePaths = Array.isArray(writeBoundary.write_paths) ? writeBoundary.write_paths.filter(Boolean) : [];
  const refreshRows = Array.isArray(refreshResults) ? refreshResults.filter(Boolean) : [];
  const refreshFailures = refreshRows.filter((row) => row.ok === false);
  const refreshSuccesses = refreshRows.length - refreshFailures.length;
  const receiptSummary = noWrite
    ? `No files changed. ${displayMessage(result.error || receipt.error || "The server did not save this change.")}`
    : receiptEvent.snapshotError
    ? `Receipt written. Project refresh failed: ${receiptEvent.snapshotError}`
    : refreshFailures.length
      ? `Receipt written. Refreshed ${refreshSuccesses}/${refreshRows.length} panels; ${refreshFailures.length} need attention.`
      : refreshRows.length
        ? `Receipt written. Refreshed ${refreshRows.length} live panels.`
        : "Receipt written. Refresh status was not recorded.";
  const kindLabels = {
    intake_edit: "Intake edit",
    case_file: "Project file",
    project_create: "Project setup",
    preflight: "Preflight",
    bounded_run: "Run",
    next_step: "Saved next step",
    row_action: "Saved next step",
    source_action: "Source check",
    source_import: "New source",
    source_edit: "Source edit",
    review: "Review"
  };
  const kindLabel = kindLabels[receiptEvent.kind] || displayText(receiptEvent.kind || "write");
  const editedFields = (receipt.updated_fields || []).map(displayFieldName).join(", ");
  const actionLabel = noWrite ? "not saved" : receipt.action || receipt.decision || receipt.status || receipt.binding_mode || receipt.source_type || editedFields || "saved";
  const hash =
    receipt.review_file_sha256 ||
    receipt.action_file_sha256 ||
    receipt.after_sha256 ||
    receipt.source_sha256 ||
    receipt.source_receipt_sha256 ||
    receipt.project_file_sha256 ||
    receipt.case_file_sha256 ||
    receipt.sha256 ||
    "";
  const createdPaths = Array.isArray(receipt.created_paths) ? receipt.created_paths.filter(Boolean) : [];
  const createdFilePath = createdPaths.find((path) => /\.[A-Za-z0-9]+$/.test(path)) || "";
  const sourcePath = receipt.review_file_path || receipt.action_file_path || receipt.intake_path || receipt.source_path || receipt.project_file_path || receipt.case_file_path || receipt.path || receipt.provenance_path || createdFilePath || createdPaths[0] || "";
  const previewableSourcePath = isPreviewableRepoPath(sourcePath) && (!createdPaths.length || Boolean(createdFilePath) || sourcePath !== createdPaths[0]);
  const ledgerPath = result.ledger || result.receipt_path || "";
  const latestPath = result.latest || "";
  const changedSummary = receiptChangeSummary(receipt, receiptEvent.kind);
  const projectContext = receipt.project || "not recorded";
  const projectKeyContext = receipt.project_key || receipt.case_key || "";
  const intakeContext = receipt.intake || "";
  const receiptJson = JSON.stringify(receipt, null, 2);
  const projectFileChangeText = writeBoundary.schema
    ? writeBoundary.writes_project_files
      ? writePaths.length
        ? `${writePaths.length} ${writePaths.length === 1 ? "path" : "paths"}`
        : "paths not listed"
      : "none"
    : "receipt only";

  return h(
    "section",
    { className: `write-receipt-panel ${noWrite ? "attention" : ""}`, "aria-label": noWrite ? "Last save attempt" : "Last save receipt" },
    h(
      "div",
      { className: "write-receipt-summary" },
      h("span", { className: "eyebrow" }, noWrite ? "Last save attempt" : "Last save receipt"),
      h("h2", null, `${kindLabel}: ${displayText(actionLabel)}`),
      h("p", null, receiptSummary)
    ),
    h(
      "div",
      { className: "write-receipt-facts" },
      h("div", null, h("span", null, "Target"), h("strong", null, receiptTargetLabel(receipt, receiptEvent) || "none")),
      h("div", null, h("span", null, "Project"), h("strong", null, projectContext)),
      projectKeyContext ? h("div", null, h("span", null, "Project/intake"), h("strong", null, projectKeyContext)) : null,
      intakeContext ? h("div", null, h("span", null, "Intake"), h("strong", null, intakeContext)) : null,
      h("div", null, h("span", null, "Receipt type"), h("strong", null, receipt.schema ? kindLabel : "none")),
      h("div", null, h("span", null, "Applied"), h("strong", null, receipt.applied_at || "none")),
      h("div", null, h("span", null, "Changed"), h("strong", null, changedSummary || "not recorded")),
      h("div", null, h("span", null, "File check"), h("strong", null, shortDigest(hash))),
      h("div", null, h("span", null, "Refresh"), h("strong", null, refreshRows.length ? `${refreshSuccesses}/${refreshRows.length} panels` : "not run")),
      h("div", null, h("span", null, "Project files"), h("strong", null, projectFileChangeText)),
      h("div", null, h("span", null, "Browser changes"), h("strong", null, writeBoundary.browser_writes ? "reported" : "none"))
    ),
    refreshRows.length
      ? h(
          "div",
          { className: "write-refresh-strip" },
          refreshRows.map((row) =>
            h(
              "span",
              { key: row.label, className: row.ok === false ? "attention" : "ready", title: row.error || targetLabel(row.label) },
              targetLabel(row.label)
            )
          )
        )
      : null,
    h(
      "div",
      { className: "write-receipt-paths" },
      h("div", null, h("span", null, "Receipt history"), h("code", null, ledgerPath || "no receipt history path")),
      h("div", null, h("span", null, "Latest receipt"), h("code", null, latestPath || "no latest receipt path")),
      h("div", null, h("span", null, "Saved file"), h("code", null, sourcePath || "no saved file path")),
      writePaths.length
        ? h(
            "div",
            { className: "write-receipt-write-paths" },
            h("span", null, "Changed files or receipts"),
            h(
              "div",
              { className: "write-path-list" },
              writePaths.map((path) => h("code", { key: path }, path))
            )
          )
        : null,
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
            title: liveMode ? "Preview receipt history" : "Start the workbench server to preview files"
          },
          "Preview history"
        ),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !liveMode || !latestPath,
            onClick: () => onPreview && onPreview({ type: "receipt", value: latestPath }),
            title: liveMode ? "Preview the latest receipt file" : "Start the workbench server to preview files"
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
            title: "Copy stamped receipt"
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
      { className: "filter-tabs", role: "tablist", "aria-label": "Project check filter" },
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
      placeholder: "Filter evidence, command details, warnings",
      "aria-label": "Filter project checks"
    })
  );
}

function WorkbenchTable({ rows, selectedLabel, setSelectedLabel }) {
  const renderEvidenceMarkers = (row) => {
    const items = evidenceItems(row);
    return items.length
      ? items.map((item) => h(EvidenceType, { key: item.label, type: item.type }))
      : h("span", { className: "no-evidence-marker", title: "No file, receipt, warning, or command details listed for this project check" }, "No file/receipt");
  };
  return h(
    "div",
    { className: "table-shell" },
    h(
      "div",
      { className: "table-head" },
      h("span", null, "Priority"),
      h("span", null, "Project check"),
      h("span", null, "State"),
      h("span", null, "Files"),
      h("span", null, "Why it matters")
    ),
    h(
      "div",
      { className: "table-body" },
      rows.map((row, index) =>
        h(
          "button",
          {
            id: `item-${index}`,
            key: row.label,
            className: `table-row ${row.kind || "neutral"} ${selectedLabel === row.label ? "selected" : ""}`,
            type: "button",
            onClick: () => setSelectedLabel(row.label)
          },
          h("span", { className: `signal-cell ${row.kind || "neutral"}` }, rowSignal(row)),
          h("span", { className: "step-cell" }, h("strong", null, itemLabel(row)), h("small", null, kindLabel(row.kind))),
          h("span", { className: "status-cell" }, itemStatus(row)),
          h(
            "span",
            { className: "evidence-cell" },
            renderEvidenceMarkers(row)
          ),
          h("span", { className: "summary-cell" }, itemDetail(row))
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

function Inspector({ row, snapshot, liveMode, loadFilePreview, filePreview, filePreviewMessage, hiddenByFilter }) {
  if (!row) {
    return h("aside", { className: "inspector" }, h("p", null, "Select a project check to inspect evidence."));
  }

  const items = evidenceItems(row);
  return h(
    "aside",
    { className: `inspector ${row.kind || "neutral"}` },
    h(
      "div",
      { className: "inspector-head" },
      h("span", null, kindLabel(row.kind)),
      h("h2", null, itemLabel(row)),
      h("p", null, itemDetail(row)),
      hiddenByFilter ? h("small", { className: "filter-note" }, "This project check is selected but hidden by the current filter.") : null
    ),
    h(
      "dl",
      { className: "inspector-facts" },
      h("div", null, h("dt", null, "Status"), h("dd", null, itemStatus(row))),
      h("div", null, h("dt", null, "Project"), h("dd", null, snapshot.project)),
      h("div", null, h("dt", null, "Run check"), h("dd", null, snapshot.display_readiness || displayText(snapshot.readiness)))
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
    h("strong", null, "No project checks match the current filter."),
    h("span", null, "Clear the search field or switch to All project checks.")
  );
}

function WriteBoundary({ writeLabel, readLabel, liveMode }) {
  return h(
    "div",
    { className: `write-boundary ${liveMode ? "live" : "offline"}`, "aria-label": "Files that can change" },
    h(
      "div",
      { className: "write-boundary-item writes" },
      h("span", null, liveMode ? "Project files" : "Project files"),
      h("strong", null, writeLabel),
      h("p", null, liveMode ? "Only the listed project paths can change." : "Project files cannot change.")
    ),
    h(
      "div",
      { className: "write-boundary-item readonly" },
      h("span", null, "Preview only"),
      h("strong", null, readLabel),
      h("p", null, "Preview, copy, and download do not write project files.")
    )
  );
}

function detailKey(workspace, subsection) {
  return `${workspace}:${subsection}`;
}

function detailCopy(workspace, subsection) {
  const section = WORKSPACE_SECTIONS.find((item) => item.id === workspace) || WORKSPACE_SECTIONS[0];
  return WORKSPACE_DETAIL_COPY[detailKey(workspace, subsection)] || {
    title: subsection || section.label,
    body: section.summary
  };
}

function ModalShell({ detail, modalKey, onClose }) {
  const closeButtonRef = useRef(null);
  useEffect(() => {
    if (!detail || !modalKey) return undefined;
    const previousActive = document.activeElement;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") onClose();
    };
    const unlockBody = lockModalBody();
    window.addEventListener("keydown", closeOnEscape);
    window.requestAnimationFrame(() => closeButtonRef.current && closeButtonRef.current.focus());
    return () => {
      unlockBody();
      window.removeEventListener("keydown", closeOnEscape);
      if (previousActive && typeof previousActive.focus === "function") previousActive.focus();
    };
  }, [modalKey, onClose]);
  if (!detail) return null;
  return h(
    "div",
    { className: "modal-backdrop", role: "presentation", onMouseDown: (event) => event.target === event.currentTarget && onClose() },
    h(
      "section",
      { className: "modal-shell", role: "dialog", "aria-modal": "true", "aria-label": detail.title },
      h(
        "header",
        { className: "modal-head" },
        h(
          "div",
          null,
          h("span", { className: "eyebrow" }, detail.eyebrow || "Details"),
          h("h2", null, detail.title),
          detail.body ? h("p", null, detail.body) : null
        ),
        h("button", { type: "button", ref: closeButtonRef, className: "modal-close", onClick: onClose, "aria-label": "Close details" }, "Close")
      ),
      h("div", { className: "modal-body" }, detail.panels)
    )
  );
}

function latestWriteSummary(receiptEvent, refreshResults) {
  if (!receiptEvent) return null;
  const result = receiptEvent.result || {};
  const receipt = result.receipt || {};
  const writeBoundary = result.write_boundary || {};
  const noWrite = Boolean(receiptEvent.noWrite || (writeBoundary.schema && result.ok === false && !writeBoundary.writes_project_files));
  const kindLabels = {
    intake_edit: "Intake edit",
    case_file: "Project file",
    project_create: "Project setup",
    preflight: "Preflight",
    bounded_run: "Run",
    next_step: "Saved next step",
    row_action: "Saved next step",
    source_action: "Source check",
    source_import: "New source",
    source_edit: "Source edit",
    review: "Review"
  };
  const kind = kindLabels[receiptEvent.kind] || displayText(receiptEvent.kind || "write");
  const target = receiptTargetLabel(receipt, receiptEvent) || "not recorded";
  const action = noWrite ? "not saved" : receipt.action || receipt.decision || receipt.status || receipt.binding_mode || receipt.source_type || "saved";
  const refreshRows = Array.isArray(refreshResults) ? refreshResults.filter(Boolean) : [];
  const failed = refreshRows.filter((row) => row.ok === false).length;
  const refresh = noWrite
    ? "no files changed"
    : receiptEvent.snapshotError
    ? "refresh failed"
    : refreshRows.length
      ? failed
        ? `${refreshRows.length - failed}/${refreshRows.length} refreshed`
        : `${refreshRows.length}/${refreshRows.length} refreshed`
      : "refresh not recorded";
  const refreshDetails = refreshRows.slice(0, 6).map((row) => ({
    label: targetLabel(row.label || row.kind) || "panel",
    ok: row.ok !== false,
    message: displayMessage(row.error || row.message || "")
  }));
  return { kind, target, action: displayText(action), refresh, failed, refreshDetails, noWrite };
}

function LastWriteStrip({ receiptEvent, refreshResults, onOpen }) {
  const summary = latestWriteSummary(receiptEvent, refreshResults);
  if (!summary) return null;
  return h(
    "div",
    { className: `last-write-strip ${summary.failed || summary.noWrite ? "attention" : "ready"}`, "aria-label": summary.noWrite ? "Last save attempt" : "Last save" },
    h(
      "div",
      { className: "last-write-copy" },
      h("span", { className: "eyebrow" }, summary.noWrite ? "Last save attempt" : "Last save"),
      h("strong", null, `${summary.kind}: ${summary.action}`),
      h("small", null, `${summary.target} / ${summary.refresh}`)
    ),
    summary.refreshDetails.length
      ? h(
          "div",
          { className: "last-write-refresh", "aria-label": "Refresh details" },
          summary.refreshDetails.map((item) =>
            h(
              "span",
              {
                key: `${item.label}:${item.message || item.ok}`,
                className: item.ok ? "ready" : "attention",
                title: item.message || (item.ok ? "Refreshed" : "Needs attention")
              },
              item.label
            )
          )
        )
      : null,
    h("button", { type: "button", className: "copy-button", onClick: onOpen }, summary.noWrite ? "Open details" : "Open receipt")
  );
}

function WorkspacePageHeader({ activeSection, activeSubnav, snapshot, counts, activeBlockerRow, onOpenCurrentProject, onOpenWorkspace, onReviewItem }) {
  const copy = detailCopy(activeSection.id, activeSubnav);
  const rows = (snapshot && snapshot.rows) || [];
  const claimRow = rowByLabel(rows, "Bounded claim");
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const intakeRow = rowByLabel(rows, "Project intake");
  const assumptionsRow = rowByLabel(rows, "Assumptions and constraints");
  const falsifierRow = rowByLabel(rows, "Next falsifier");
  const runRow = rowByLabel(rows, "Run readiness") || rowByLabel(rows, "Preflight");
  const reportRow = rowByLabel(rows, "Report support");
  const reviewRow = rowByLabel(rows, "Latest review receipt");
  const nextStepRow = rowByLabel(rows, "Latest next step") || rowByLabel(rows, "Latest item action");
  const sourceReady = sourceRow && sourceRow.kind !== "attention";
  const evidenceReady = evidenceRow && evidenceRow.kind !== "attention";
  const diagnosisText = claimRow ? diagnosisLead(claimRow.detail) : "No working diagnosis recorded.";
  const statusFor = (row, fallback = "not loaded") => row ? itemStatus(row) : fallback;
  const factsByArea = {
    overview: [
      ["Diagnosis", statusFor(claimRow, "missing")],
      ["Assumptions", statusFor(assumptionsRow)],
      ["Change test", statusFor(falsifierRow)]
    ],
    sources: [
      ["Source files", statusFor(sourceRow, "missing")],
      ["Evidence files", statusFor(evidenceRow, "missing")],
      ["Intake", statusFor(intakeRow, "not loaded")]
    ],
    run: [
      ["Run check", statusFor(runRow, snapshot.display_readiness || displayText(snapshot.readiness))],
      ["Command detail", runRow && runRow.command ? "available" : "not loaded"],
      ["Advisories", activeBlockerRow ? itemLabel(activeBlockerRow) : "none open"]
    ],
    review: [
      ["Open reviews", counts.attention ? `${counts.attention} project checks` : "none"],
      ["Latest review", statusFor(reviewRow, "no receipt")],
      ["Next step", statusFor(nextStepRow, "not saved")]
    ],
    save: [
      ["Report", reportRow ? itemStatus(reportRow) : reportStatusLabel(snapshot.report_status, snapshot.display_report_status)],
      ["Project file", rows.length ? "ready to save" : "not loaded"],
      ["Open issue", activeBlockerRow ? itemLabel(activeBlockerRow) : "none"]
    ]
  };
  const factRows = factsByArea[activeSection.id] || [
    ["Evidence", sourceReady && evidenceReady ? "files ready" : "files need review"],
    ["Review", counts.attention ? `${counts.attention} need review` : "no open reviews"],
    ["Report", reportStatusLabel(snapshot.report_status, snapshot.display_report_status)]
  ];
  const attentionByArea = {
    overview: !claimRow || Boolean(assumptionsRow && assumptionsRow.kind === "attention"),
    sources: !sourceReady || !evidenceReady,
    run: Boolean(runRow && runRow.kind === "attention"),
    review: Boolean(counts.attention),
    save: snapshot.report_status === "blocked" || Boolean(reportRow && reportRow.kind === "attention")
  };
  const headerAttention = Boolean(attentionByArea[activeSection.id]);
  const primaryAction =
    activeSection.id === "sources"
      ? { label: "Check files", workspace: "sources", subsection: "File check" }
      : activeSection.id === "run"
        ? { label: "Run preflight", workspace: "run", subsection: "Preflight" }
        : activeSection.id === "review"
          ? { label: "Open reviews", workspace: "review", subsection: "Save review" }
          : activeSection.id === "save"
            ? { label: "Review support", workspace: "save", subsection: "Support check" }
            : null;
  return h(
    "section",
    { className: `workspace-page-header ${headerAttention ? "attention" : ""}`, "aria-label": `${activeSection.label} page summary` },
    h(
      "div",
      { className: "workspace-page-copy" },
      h("span", { className: "eyebrow" }, activeSection.label),
      h("h2", null, copy.title),
      h("p", null, copy.body),
      h("small", null, diagnosisText)
    ),
    h(
      "div",
      { className: "workspace-page-facts" },
      factRows.map(([label, value]) =>
        h("div", { key: label }, h("span", null, label), h("strong", null, value))
      )
    ),
    h(
      "div",
      { className: "workspace-page-actions" },
      primaryAction
        ? h(
            "button",
            {
              type: "button",
              className: "copy-button primary",
              onClick: () => onOpenWorkspace && onOpenWorkspace(primaryAction.workspace, primaryAction.subsection)
            },
            primaryAction.label
          )
        : null,
      activeBlockerRow && activeSection.id !== "review" && activeSection.id !== "save"
        ? h(
            "button",
            {
              type: "button",
              className: "copy-button",
              onClick: () => onReviewItem && onReviewItem(activeBlockerRow.label)
            },
            "Review issue"
          )
        : null,
      h(
        "button",
        {
          type: "button",
          className: primaryAction || activeBlockerRow ? "copy-button" : "copy-button primary",
          onClick: () => onOpenCurrentProject && onOpenCurrentProject()
        },
        "Current project"
      )
    )
  );
}

function SectionMenu({ activeWorkspace, activeSubsection, onOpenWorkspace }) {
  const activeSection = WORKSPACE_SECTIONS.find((section) => section.id === activeWorkspace) || WORKSPACE_SECTIONS[0];
  const activeSubnav = activeSection.subnav.includes(activeSubsection) ? activeSubsection : activeSection.subnav[0];
  return h(
    "nav",
    { className: "workspace-tabs", "aria-label": `${activeSection.label} views` },
    h(
      "div",
      { className: "workspace-tab-list" },
      activeSection.subnav.map((subsection) => {
        const copy = detailCopy(activeSection.id, subsection);
        const active = subsection === activeSubnav;
        return h(
          "button",
          {
            key: subsection,
            type: "button",
            className: active ? "active" : "",
            "aria-pressed": active,
            title: copy.body,
            onClick: () => onOpenWorkspace && onOpenWorkspace(activeSection.id, subsection)
          },
          h("strong", null, subsection),
          h("small", null, copy.title)
        );
      })
    ),
    h(
      "button",
      {
        type: "button",
        className: "workspace-tabs-home",
        onClick: () => onOpenWorkspace && onOpenWorkspace("projects", "Current project"),
        title: "Return to the current project home"
      },
      "Current project"
    )
  );
}

function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [modeMessage, setModeMessage] = useState("");
  const [traceContext, setTraceContext] = useState(null);
  const [traceMessage, setTraceMessage] = useState("");
  const [workflowContext, setWorkflowContext] = useState(null);
  const [workflowMessage, setWorkflowMessage] = useState("");
  const [preflightEvent, setPreflightEvent] = useState(null);
  const [preflightMessage, setPreflightMessage] = useState("");
  const [preflightRunning, setPreflightRunning] = useState(false);
  const [boundedRunEvent, setBoundedRunEvent] = useState(null);
  const [boundedRunMessage, setBoundedRunMessage] = useState("");
  const [boundedRunRunning, setBoundedRunRunning] = useState(false);
  const [boundedRunPreviewing, setBoundedRunPreviewing] = useState(false);
  const [projectRunPrompt, setProjectRunPrompt] = useState(null);
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
  const [serverStatus, setServerStatus] = useState(null);
  const [serverStatusMessage, setServerStatusMessage] = useState("");
  const [projects, setProjects] = useState([]);
  const [projectFolders, setProjectFolders] = useState([]);
  const [selectedProjectKey, setSelectedProjectKey] = useState("");
  const [projectCreateDraft, setProjectCreateDraft] = useState(emptyProjectCreateDraft());
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
  const [projectFileSaveEvent, setProjectFileSaveEvent] = useState(null);
  const [projectFileSaving, setProjectFileSaving] = useState(false);
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
  const [activeWorkspace, setActiveWorkspace] = useState("projects");
  const [activeSubsection, setActiveSubsection] = useState("Current project");
  const [activeModalKey, setActiveModalKey] = useState("");
  const [discardPrompt, setDiscardPrompt] = useState(null);
  const snapshotLoadedRef = useRef(false);

  const defaultSnapshotLabel = (rows) => {
    const firstAttention = rows.find((row) => row.kind === "attention");
    return (firstAttention && firstAttention.label) || (rows[0] && rows[0].label) || "";
  };

  const installSnapshot = (payload, options = {}) => {
    snapshotLoadedRef.current = true;
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

  const clearProjectActivityState = () => {
    setPreflightEvent(null);
    setSourceActionEvent(null);
    setSourceImportEvent(null);
    setSourceEditEvent(null);
    setWriteReceiptEvent(null);
    setLastRefreshResults([]);
    setProjectFileSaveEvent(null);
    setReviewMessage("");
    setActionMessage("");
    setReviewStates({});
    setActionStates({});
  };

  const resetProjectSessionState = () => {
    setTraceContext(null);
    setTraceMessage("");
    setWorkflowContext(null);
    setWorkflowMessage("");
    clearProjectActivityState();
    setPreflightMessage("");
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
    setSourceEditMessage("");
    setSourceEditDraft(emptySourceEditDraft());
    setIntakeDraft(null);
    setIntakeMessage("");
    setReceiptHistory(null);
    setReceiptHistoryMessage("");
    setFilePreview(null);
    setFilePreviewMessage("");
  };

  const refreshResult = (label, ok, error = "") => ({ label, ok, error: error ? String(error) : "" });

  const loadServerStatus = () =>
    fetch("/api/status", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`server status fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (!((payload.checks || {}).api_ready || payload.ok)) throw new Error(payload.error || "server status check failed");
        setServerStatus(payload);
        setServerStatusMessage("Local server is ready.");
        return payload;
      })
      .catch((err) => {
        setServerStatus(null);
        setServerStatusMessage(`Local server unavailable: ${err.message || err}`);
        throw err;
      });

  const refreshProjectIndex = (activeProject) =>
    fetch("/api/projects", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`project index fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        const projectRows = payload.projects || [];
        setProjectFolders(payload.all_project_folders || payload.project_folders || []);
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
        setHealthMessage("Live health context loaded from the workbench server.");
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
    setTraceMessage("Loading run plan.");
    return fetch(endpointUrl("/api/trace", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`trace fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "trace fetch failed");
        setTraceContext(payload);
        setTraceMessage("Live run plan loaded from the workbench server.");
        return refreshResult("trace", true);
      })
      .catch((err) => {
        setTraceContext(null);
        setTraceMessage(`Live run plan unavailable: ${err.message || err}`);
        return refreshResult("trace", false, err.message || err);
      });
  };

  const loadWorkflowContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setWorkflowMessage("Loading project steps.");
    return fetch(endpointUrl("/api/workflow", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`workflow fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "workflow fetch failed");
        setWorkflowContext(payload);
        setWorkflowMessage(`${(payload.steps || []).length} project steps loaded from the workbench server.`);
        return refreshResult("workflow", true);
      })
      .catch((err) => {
        setWorkflowContext(null);
        setWorkflowMessage(`Project steps unavailable: ${err.message || err}`);
        return refreshResult("workflow", false, err.message || err);
      });
  };

  const loadReportContractContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setReportContractMessage("Loading report readiness.");
    return fetch(endpointUrl("/api/report-contract", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`report contract fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false && !payload.status) throw new Error(payload.error || "report contract fetch failed");
        setReportContractContext(payload);
        setReportContractMessage("Report readiness loaded from the workbench server.");
        return refreshResult("report", true);
      })
      .catch((err) => {
        setReportContractContext(null);
        setReportContractMessage(`Report readiness unavailable: ${err.message || err}`);
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
        setReceiptHistoryMessage(`${payload.receipt_count || 0} receipts found in project ledgers.`);
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
        setRunHistoryMessage(`${(payload.summary || {}).run_rows || 0} runs loaded from project files.`);
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
    setClaimSupportMessage("Loading support audit.");
    return fetch(endpointUrl("/api/evidence-support", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`support audit fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false && !payload.status) throw new Error(payload.error || "support audit fetch failed");
        setClaimSupportContext(payload);
        setClaimSupportMessage(
          payload.accepted
            ? `${payload.claim_count || 0} evidence checks loaded from project files.`
            : `Support audit needs attention: ${payload.status || "attention"}.`
        );
        return refreshResult("support audit", true);
      })
      .catch((err) => {
        setClaimSupportContext(null);
        setClaimSupportMessage(`Support audit unavailable: ${err.message || err}`);
        return refreshResult("support audit", false, err.message || err);
      });
  };

  const loadSourceListContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setSourceListMessage("Loading source files.");
    return fetch(endpointUrl("/api/sources", { project: projectParams.project }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`source list fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "source list fetch failed");
        setSourceListContext(payload);
        setSourceListMessage(`${(payload.sources || []).length} source files loaded from ${payload.raw_dir || "project source folder"}.`);
        return refreshResult("sources", true);
      })
      .catch((err) => {
        setSourceListContext(null);
        setSourceListMessage(`Source files unavailable: ${err.message || err}`);
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
        warnings.push(`source file ${sourceEditDraft.relative_raw_path || "draft"} (${fields.map(displayFieldName).join(", ")})`);
      }
    }
    if (options.sourceImport === true) {
      const hasImportDraft = Boolean(String(sourceImportDraft.filename || "").trim() || String(sourceImportDraft.body || "").trim());
      if (hasImportDraft) warnings.push("new source draft");
    }
    return warnings;
  };

  const runAfterPendingEditors = (action, options = {}, proceed = () => {}) => {
    const warnings = pendingEditorWarnings(options);
    if (!warnings.length) {
      proceed();
      return;
    }
    setDiscardPrompt({ action, warnings, proceed });
  };

  const cancelDiscardPrompt = () => {
    if (discardPrompt) {
      setModeMessage(`Kept current project. Save or discard unsaved edits before ${discardPrompt.action.toLowerCase()}.`);
    }
    setDiscardPrompt(null);
  };

  const confirmDiscardPrompt = () => {
    const proceed = discardPrompt && discardPrompt.proceed;
    setDiscardPrompt(null);
    if (typeof proceed === "function") proceed();
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
      loadWorkflowContext(projectParams),
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
    const background = options.background === true;
    if (!background) setLoadingSnapshot(true);
    setError("");
    const url = useLiveApi && loadParams.project ? endpointUrl("/api/snapshot", loadParams) : "/workbench_snapshot.json";
    return fetch(url, { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`project data fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        installSnapshot(payload, {
          preserveSelection: options.preserveSelection === true,
          preferredLabel: options.preferredLabel || ""
        });
        setModeMessage(
          useLiveApi
            ? `Live project loaded from the workbench server: ${payload.project}.`
            : `Static project data loaded from ${payload.html_output || "workbench_snapshot.json"}.`
        );
        if (useLiveApi) {
          const liveParams = { ...loadParams, project: payload.project, rubric: payload.rubric || loadParams.rubric, intake: payload.intake || loadParams.intake };
          setSelectedProjectKey(projectEntryKey(liveParams));
          Promise.allSettled([
            loadTraceContext(liveParams),
            loadWorkflowContext(liveParams),
            loadReportContractContext(liveParams),
            loadHealthContext(liveParams),
            loadIntakeDraft(liveParams),
            loadReceiptHistory(liveParams),
            loadRunHistoryContext(liveParams),
            loadClaimSupportContext(liveParams),
            loadSourceListContext(liveParams)
          ]).then((results) => {
            setLastRefreshResults(
              results.map((result, index) => {
                if (result.status === "fulfilled") return result.value;
                return refreshResult(`live panel ${index + 1}`, false, result.reason && (result.reason.message || result.reason));
              }).filter(Boolean)
            );
          });
          return payload;
        }
        clearProjectActivityState();
        setTraceContext(null);
        setTraceMessage("Offline snapshot mode uses the last generated project data only.");
        setWorkflowContext(null);
        setWorkflowMessage("Offline snapshot mode uses the generated project data to estimate the project steps.");
        setPreflightEvent(null);
        setPreflightMessage("Offline snapshot mode cannot run live preflight.");
        setSourceActionEvent(null);
        setSourceActionMessage("Offline snapshot mode cannot run live source/evidence checks.");
        setReportContractContext(null);
        setReportContractMessage("Offline snapshot mode uses the report status from the last generated project data only.");
        setHealthContext(null);
        setHealthMessage("Offline snapshot mode uses the last generated project data only.");
        setIntakeDraft(null);
        setIntakeMessage("Offline snapshot mode cannot edit the project intake.");
        setReceiptHistory(null);
        setReceiptHistoryMessage("Offline snapshot mode uses the latest generated project data only.");
        setRunHistoryContext(null);
        setRunHistoryMessage("Offline snapshot mode uses the run-history status from the last generated project data only.");
        setClaimSupportContext(null);
        setClaimSupportMessage("Offline snapshot mode uses the source and evidence checks from the last generated project data only.");
        setSourceListContext(null);
        setSourceListMessage("Offline snapshot mode cannot inspect source files.");
        setSourceEditEvent(null);
        setSourceEditMessage("Offline snapshot mode cannot edit source files.");
        return null;
      })
      .catch((err) => {
        if (useLiveApi && allowStaticFallback) {
          setLiveMode(false);
          setModeMessage("Workbench server not available. Showing the last generated project data.");
          return loadSnapshot("", false);
        }
        throw err;
      })
      .finally(() => {
        if (!background) setLoadingSnapshot(false);
      });
  };

  useEffect(() => {
    fetch("/workbench_snapshot.json", { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`cached project data fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (snapshotLoadedRef.current) return;
        installSnapshot(payload);
        setModeMessage("Cached project data loaded while the local server warms up.");
      })
      .catch(() => {});

    loadServerStatus()
      .then(() => fetch("/api/projects", { headers: { Accept: "application/json" } }))
      .then((response) => {
        if (!response.ok) throw new Error(`project index fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        const projectRows = payload.projects || [];
        setProjectFolders(payload.all_project_folders || payload.project_folders || []);
        if (!projectRows.length) throw new Error("project index is empty");
        setProjects(projectRows);
        setLiveMode(true);
        const preferred = projectRows.find((row) => row.project === payload.default_project) || projectRows[0];
        setSelectedProjectKey(projectEntryKey(preferred));
        return loadSnapshot(preferred, true, { allowStaticFallback: true, background: true });
      })
      .catch(() =>
        loadSnapshot("", false).catch((err) => setError(String(err.message || err)))
      );
  }, []);

  const openProject = (caseKey) => {
    if (!caseKey || !liveMode) return;
    const entry = projects.find((row) => projectEntryKey(row) === caseKey) || projects.find((row) => row.project === caseKey) || { project: caseKey, rubric: caseKey };
    runAfterPendingEditors(`Opening ${entry.project}`, { sourceImport: true }, () => {
      resetProjectSessionState();
      setModeMessage(`Opening ${entry.project} from local project files.`);
      loadSnapshot(entry, true).catch((err) =>
        setModeMessage(`Could not load live project data for ${entry.project}: ${err.message || err}`)
      );
    });
  };

  const refreshCurrentProject = () => {
    if (!snapshot || !liveMode) return;
    runAfterPendingEditors("Refreshing this project", {}, () => {
      if (sourceChangedFields(sourceEditDraft).length > 0) {
        setSourceEditDraft(emptySourceEditDraft());
        setSourceEditMessage("Source file draft cleared by refresh.");
      }
      clearProjectActivityState();
      const entry = currentProjectEntry || snapshot;
      loadSnapshot(entry, true, { preserveSelection: true }).catch((err) =>
        setModeMessage(`Could not refresh live project for ${snapshot.project}: ${err.message || err}`)
      );
    });
  };

  const refreshServerReadiness = () => {
    setServerStatusMessage("Checking local server readiness.");
    loadServerStatus()
      .then(() => setModeMessage("Local server readiness refreshed."))
      .catch((err) => setModeMessage(`Local server readiness failed: ${err.message || err}`));
  };

  const refreshCurrentIntake = () => {
    if (!snapshot || !liveMode) return;
    runAfterPendingEditors("Reloading the intake", { sourceEdit: false }, () => {
      const entry = currentProjectEntry || snapshot;
      loadIntakeDraft(projectLoadParams(entry));
    });
  };

  const createProjectLive = () => {
    if (!liveMode || projectCreating) return;
    const draftProject = String(projectCreateDraft.project || "").trim();
    const existingFolder = (projectFolders || []).find((folder) => folder.project === draftProject) || null;
    const addIntakeMode = Boolean(existingFolder && !existingFolder.openable && !existingFolder.intake_count);
    runAfterPendingEditors(addIntakeMode ? "Adding intake to this project" : "Creating and opening this project", { sourceImport: true }, () => {
      setProjectCreating(true);
      setProjectCreateMessage(addIntakeMode ? "Adding intake to existing project folder." : "Creating local project and intake.");
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
          if (!response.ok) {
            const error = new Error(payload.error || `project create failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        const writeEvent = projectCreateWriteEvent(payload);
        if (!payload.accepted) {
          if (writeEvent) setWriteReceiptEvent(writeEvent);
          const written = (((payload.write_boundary || {}).write_paths) || []).filter(Boolean).length;
          setProjectCreateMessage(
            written
              ? `Project setup needs attention after writing ${written} paths. Inspect the last save receipt before retrying.`
              : "Project setup needs attention. No project files changed."
          );
          return;
        }
        const projectRows = (payload.project_index && payload.project_index.projects) || [];
        setProjectFolders((payload.project_index && (payload.project_index.all_project_folders || payload.project_index.project_folders)) || []);
        if (projectRows.length) setProjects(projectRows);
        setSelectedProjectKey(projectEntryKey(payload));
        resetProjectSessionState();
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        if (payload.snapshot) installSnapshot(payload.snapshot);
        setLiveMode(true);
        loadSnapshot({ project: payload.project, rubric: payload.rubric, intake: payload.intake }, true).catch((err) =>
          setProjectCreateMessage(`Created ${payload.project}, but live reload failed: ${err.message || err}`)
        );
        setProjectCreateDraft(emptyProjectCreateDraft());
        const writePaths = (((payload.write_boundary || {}).write_paths) || []).filter(Boolean);
        const warning = payload.intake_create_accepted === false && payload.intake_file_exists
          ? " The intake file already exists, so the server opened the project and kept the existing intake."
          : "";
        const createVerb = payload.created_mode === "add_intake" ? "Added intake to" : "Created";
        setProjectCreateMessage(`${createVerb} ${payload.project} and opened the live project. ${writePaths.length ? `${writePaths.length} project paths written.` : "Project files written."}${warning}`);
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("project_create", projectCreateDraft.project || "project setup", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setProjectCreateMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      })
      .finally(() => setProjectCreating(false));
    });
  };

  const importSourceLive = () => {
    if (!snapshot || !liveMode || sourceImporting) return;
    const params = liveProjectParams();
    setSourceImporting(true);
    setSourceImportMessage("Saving source file.");
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
      .then((response) => jsonResponseOrError(response, "source save failed"))
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Source readiness" });
        if (payload.trace) setTraceContext(payload.trace);
        setSourceImportEvent(payload);
        setSourceImportDraft({ filename: "", source_type: "source_evidence", body: "" });
        setSourceImportMessage(`Saved ${payload.source_path}. Source check ${payload.source_check && payload.source_check.accepted ? "accepted" : "needs attention"}.`);
        setWriteReceiptEvent({
          kind: "source_import",
          row: payload.relative_raw_path || payload.source_path,
          result: payload,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { sources: true });
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("source_import", sourceImportDraft.filename || "source save", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setSourceImportMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      })
      .finally(() => setSourceImporting(false));
  };

  const addImportedSourceToIntakeDraft = (sourcePath, sourceType = "") => {
    const path = String(sourcePath || "").trim();
    const targetField = sourceType === "source_evidence" ? "evidence_refs_text" : "source_refs_text";
    const targetLabel = targetField === "evidence_refs_text" ? "evidence files" : "source files";
    if (!path) return;
    if (!intakeDraft) {
      setSourceImportMessage(`Load a live intake before staging ${targetLabel}.`);
      return;
    }
    if (intakeDraft.editable === false) {
      setSourceImportMessage("This intake is read-only; the source path was not staged.");
      return;
    }
    const refs = linesFromText(intakeDraft[targetField]);
    if (refs.includes(path)) {
      setSourceImportMessage(`${path} is already in ${targetLabel}.`);
      return;
    }
    const nextRefs = [...refs, path].join("\n");
    setIntakeDraft({ ...intakeDraft, [targetField]: nextRefs });
    setSourceImportMessage(`Staged ${path} in ${targetLabel}. Save intake to write the receipt.`);
    setIntakeMessage(`Staged ${path} in ${targetLabel}. Save intake to write the receipt.`);
  };

  const reloadSourceList = () => {
    if (!snapshot || !liveMode) return;
    loadSourceListContext({ project: snapshot.project });
  };

  const loadRawSourceForEdit = (relativePath) => {
    if (!snapshot || !liveMode || !relativePath) return;
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

  const openRawSourceForEdit = (relativePath) => {
    if (!snapshot || !liveMode || !relativePath) return;
    if (sourceEditDraft.relative_raw_path && sourceChangedFields(sourceEditDraft).length) {
      runAfterPendingEditors(`Opening ${relativePath}`, { intake: false, sourceImport: false }, () => loadRawSourceForEdit(relativePath));
      return;
    }
    loadRawSourceForEdit(relativePath);
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
      .then((response) => jsonResponseOrError(response, "source edit failed"))
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
      .catch((err) => {
        const failedWrite = refusedWriteEvent("source_edit", sourceEditDraft.relative_raw_path || "source edit", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setSourceEditMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      })
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
    const allRows = snapshot.rows || [];
    const explicitSelected = allRows.find((row) => row.label === selectedLabel);
    return explicitSelected || filteredRows[0] || allRows[0] || null;
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
    const reportRow = rowByLabel(rows, "Report support") || {};
    return {
      schema: REPORT_CONTRACT_SCHEMA,
      status: (snapshot && snapshot.report_status) || reportRow.status || "unknown",
      status_reasons: (snapshot && snapshot.status_reasons) || [],
      support_issues: [],
      report_support_contract: (currentProjectEntry && currentProjectEntry.report_contract) || reportRow.file || reportRow.evidence || "",
      command: reportRow.command || "",
      synthesis_input_binding: {
        status: liveMode ? "loading" : "offline project data",
        reason: liveMode
          ? "Report readiness is still loading."
          : "Offline snapshot mode shows the report status from the last generated project data."
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
  const inspectRow = (label) => {
    if (!label) return;
    setSelectedLabel(label);
    setActiveWorkspace("overview");
    setActiveSubsection("Diagnosis");
  };
  const reviewRow = (label) => {
    if (!label) return;
    setSelectedLabel(label);
    setActiveWorkspace("review");
    setActiveSubsection("Save review");
  };
  const actionRow = (label) => {
    if (!label) return;
    setSelectedLabel(label);
    setActiveWorkspace("review");
    setActiveSubsection("Save next step");
    setActiveModalKey(detailKey("review", "Save next step"));
  };
  const useActionNote = (note, action = "next_step", preferredLabel = "") => {
    if (!snapshot || !note) return;
    const rows = snapshot.rows || [];
    const preferred = preferredLabel ? rowByLabel(rows, preferredLabel) : null;
    const target = preferred || rowForActionNote(rows, action, selectedRow);
    if (!target) return;
    actionRow(target.label);
    setActionStates((current) => ({ ...current, [target.label]: { action, note } }));
    setActionMessage(`Staged next step on ${itemLabel(target)}. Review and save it.`);
  };
  const useHealthActionNote = (note, action = "next_step") => useActionNote(note, action);

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
        project_check_slug: rowSlugValue,
        item_slug: rowSlugValue,
        row_slug: rowSlugValue,
        review_file: reviewPayload
      })
    })
      .then((response) => jsonResponseOrError(response, "review apply failed"))
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "review apply failed");
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: reviewPayload.row, preserveSelection: true });
        const reviewTarget = reviewPayload.item_label || targetLabel(reviewPayload.row);
        setReviewMessage(
          payload.snapshot_error
            ? `Applied review for ${reviewTarget}. Project refresh failed: ${payload.snapshot_error}`
            : `Applied review for ${reviewTarget}.`
        );
        setWriteReceiptEvent({
          kind: "review",
          project_check_label: reviewPayload.project_check_label || reviewPayload.item_label || targetLabel(reviewPayload.row),
          project_check_slug: reviewPayload.project_check_slug || reviewPayload.item_slug || rowSlugValue,
          item_label: reviewPayload.item_label || reviewPayload.project_check_label || targetLabel(reviewPayload.row),
          item_slug: reviewPayload.item_slug || reviewPayload.project_check_slug || rowSlugValue,
          row: reviewPayload.row,
          result: nestedReceiptResult(payload, "review"),
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params);
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("review", reviewPayload.item_label || targetLabel(reviewPayload.row) || rowSlugValue, err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReviewMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      });
  };

  const applyRowActionLive = (rowSlugValue, actionPayload) => {
    if (!snapshot || !liveMode || !rowSlugValue || !actionPayload) return;
    const params = liveProjectParams();
    setActionMessage("Saving next step.");
    setWriteReceiptEvent(null);
    fetch("/api/next-step", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        project_check_slug: rowSlugValue,
        item_slug: rowSlugValue,
        row_slug: rowSlugValue,
        action_file: actionPayload
      })
    })
      .then((response) => jsonResponseOrError(response, "next-step save failed"))
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "next-step save failed");
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: actionPayload.row, preserveSelection: true });
        const actionTarget = actionPayload.item_label || targetLabel(actionPayload.row);
        setActionMessage(
          payload.snapshot_error
            ? `Saved next step for ${actionTarget}. Project refresh failed: ${payload.snapshot_error}`
            : `Saved next step for ${actionTarget}.`
        );
        setWriteReceiptEvent({
          kind: "next_step",
          project_check_label: actionPayload.project_check_label || actionPayload.item_label || targetLabel(actionPayload.row),
          project_check_slug: actionPayload.project_check_slug || actionPayload.item_slug || rowSlugValue,
          item_label: actionPayload.item_label || actionPayload.project_check_label || targetLabel(actionPayload.row),
          item_slug: actionPayload.item_slug || actionPayload.project_check_slug || rowSlugValue,
          row: actionPayload.row,
          result: nestedReceiptResult(payload, "action"),
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params);
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("next_step", actionPayload.project_check_label || actionPayload.item_label || targetLabel(actionPayload.row) || rowSlugValue, err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setActionMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      });
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
      .then((response) => jsonResponseOrError(response, "intake save failed"))
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "intake save failed");
        if (payload.intake) setIntakeDraft(intakeDraftFromPayload(payload.intake));
        if (payload.snapshot) installSnapshot(payload.snapshot, { preserveSelection: true });
        setIntakeMessage(
          payload.snapshot_error
            ? `Saved intake edit. Project refresh failed: ${payload.snapshot_error}`
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
      .catch((err) => {
        const failedWrite = refusedWriteEvent("intake_edit", "Project intake", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setIntakeMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      });
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
        const writeEvent = preflightWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
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
        const failedWrite = refusedWriteEvent("preflight", "Preflight", err);
        if (failedWrite) {
          setWriteReceiptEvent(failedWrite);
        } else if (err.payload) {
          const writeEvent = preflightWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
        }
        setPreflightMessage(String(err.message || err));
      })
      .finally(() => setPreflightRunning(false));
  };

  const requestBoundedRunLive = () => {
    if (!snapshot || !liveMode || boundedRunRunning || boundedRunPreviewing) return;
    const params = liveProjectParams();
    const kernel = (traceContext && traceContext.kernel_entry) || {};
    const plan = (traceContext && traceContext.plan_preview) || {};
    const command = kernel.run_command || plan.recommended_first_command || "";
    setBoundedRunPreviewing(true);
    setBoundedRunMessage("Loading project-run preview.");
    fetch("/api/run", {
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
        confirmed: false
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok && payload.status !== "needs_confirmation") {
            const error = new Error(payload.error || payload.stderr_tail || payload.stdout_tail || `run preview failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        if (payload.trace_before) setTraceContext(payload.trace_before);
        if (payload.error && !/confirm/i.test(String(payload.error))) {
          setBoundedRunEvent(payload);
          setBoundedRunMessage(`${payload.error} No project files changed.`);
          return;
        }
        if (payload.command || command) {
          setProjectRunPrompt({
            ...params,
            command: payload.command || command,
            preview: payload,
            confirmedWriteBoundary: payload.confirmed_write_boundary || null
          });
          setBoundedRunMessage("Review the project run before starting it.");
        } else {
          setBoundedRunMessage(payload.error || "No project-run command details are loaded.");
        }
      })
      .catch((err) => {
        if (err.payload) {
          setBoundedRunEvent(err.payload);
          if (err.payload.trace_before) setTraceContext(err.payload.trace_before);
        }
        const failedWrite = refusedWriteEvent("bounded_run", "Run", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setBoundedRunMessage(`${String(err.message || err)} No project files changed.`);
      })
      .finally(() => setBoundedRunPreviewing(false));
  };

  const cancelProjectRunPrompt = () => {
    if (!boundedRunRunning) {
      setProjectRunPrompt(null);
      setBoundedRunMessage("Project run canceled. No project files changed.");
    }
  };

  const runBoundedLive = () => {
    if (!snapshot || !liveMode || boundedRunRunning || !projectRunPrompt) return;
    const params = projectRunPrompt;
    setProjectRunPrompt(null);
    setBoundedRunRunning(true);
    setBoundedRunMessage("Starting confirmed project run.");
    setBoundedRunEvent(null);
    fetch("/api/run", {
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
        confirmed: true
      })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok) {
            const error = new Error(payload.error || payload.stderr_tail || payload.stdout_tail || `run failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Run readiness", preserveSelection: true });
        if (payload.trace) setTraceContext(payload.trace);
        if (payload.run_history) setRunHistoryContext(payload.run_history);
        setBoundedRunEvent(payload);
        const writeEvent = boundedRunWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        setBoundedRunMessage(
          payload.accepted
            ? snapshotRefreshMessage("Project run finished", payload)
            : "Project run finished with attention; inspect the server response."
        );
      })
      .catch((err) => {
        if (err.payload) {
          setBoundedRunEvent(err.payload);
          if (err.payload.trace) setTraceContext(err.payload.trace);
          if (err.payload.run_history) setRunHistoryContext(err.payload.run_history);
          if (err.payload.snapshot) installSnapshot(err.payload.snapshot, { preferredLabel: "Run readiness", preserveSelection: true });
          const writeEvent = boundedRunWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
        }
        const failedWrite = refusedWriteEvent("bounded_run", "Run", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setBoundedRunMessage(String(err.message || err));
      })
      .finally(() => setBoundedRunRunning(false));
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
            const error = new Error(payload.error || payload.stderr_tail || payload.stdout_tail || `source check failed: ${response.status}`);
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
            : `${payload.label || displayText(payload.action)} finished with attention; inspect the server response.`
        );
      })
      .catch((err) => {
        if (err.payload) {
          setSourceActionEvent(err.payload);
          if (err.payload.trace) setTraceContext(err.payload.trace);
          if (err.payload.snapshot) installSnapshot(err.payload.snapshot, { preferredLabel: sourceActionTargetLabel(action), preserveSelection: true });
          const writeEvent = sourceActionReceiptEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
          if (!writeEvent) {
            const failedWrite = refusedWriteEvent("source_action", sourceActionTargetLabel(action), err);
            if (failedWrite) setWriteReceiptEvent(failedWrite);
          }
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

  const saveProjectFileLive = (projectFile) => {
    if (!snapshot || !liveMode || projectFileSaving) return;
    const params = liveProjectParams();
    setProjectFileSaving(true);
    fetch("/api/project-file", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        project_file: projectFile
      })
    })
      .then((response) => jsonResponseOrError(response, "project file save failed"))
      .then((payload) => {
        setProjectFileSaveEvent(payload);
        setWriteReceiptEvent({
          kind: "case_file",
          row: payload.path || "project file",
          result: payload,
          snapshotError: ""
        });
        return refreshLiveContextAfterWrite(params);
      })
      .catch((err) => {
        const error = String(err.message || err);
        const failedWrite = refusedWriteEvent("case_file", "project file", err);
        setProjectFileSaveEvent({ error });
        setLastRefreshResults([]);
        setWriteReceiptEvent(failedWrite || {
          kind: "case_file",
          row: "project file",
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
      .finally(() => setProjectFileSaving(false));
  };

  const loadFilePreview = (item) => {
    const previewPath = item && previewableRepoPath(item.value);
    if (!liveMode) {
      setFilePreview(null);
      setFilePreviewMessage("Start the workbench server to preview repository files.");
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
        setFilePreviewMessage(payload.truncated ? "Preview truncated to the first 200 KB." : "Preview loaded from the workbench server.");
      })
      .catch((err) => {
        setFilePreview(null);
        setFilePreviewMessage(String(err.message || err));
      });
  };
  const closeActiveModal = useCallback(() => setActiveModalKey(""), []);

  if (error) {
    return h("main", { className: "state-page error" }, h("h1", null, "Project Workbench"), h("p", null, error));
  }
  if (!snapshot) {
    return h("main", { className: "state-page loading" }, h("h1", null, "Project Workbench"), h("p", null, "Loading project data."));
  }

  const selectedHiddenByFilter = Boolean(selectedRow && !filteredRows.some((row) => row.label === selectedRow.label));
  const actionContracts = (serverStatus && serverStatus.api && serverStatus.api.action_contracts) || {};
  const rowTablePanel = h(
    "section",
    { className: "main-grid", key: "rows" },
    filteredRows.length
      ? h(WorkbenchTable, { rows: filteredRows, selectedLabel: selectedRow && selectedRow.label, setSelectedLabel })
      : h(EmptyState),
    h(Inspector, { row: selectedRow, snapshot, liveMode, loadFilePreview, filePreview, filePreviewMessage, hiddenByFilter: selectedHiddenByFilter })
  );
  const sourceReadinessPanel = h(SourceEvidencePanel, {
    key: "source-evidence",
    snapshot,
    traceContext,
    liveMode,
    onPreview: loadFilePreview,
    onInspectRow: inspectRow,
    sourceActionContracts: actionContracts,
    sourceActionEvent,
    sourceActionMessage,
    sourceActionRunning,
    onRunSourceAction: runSourceActionLive
  });
  const statusMetrics = h(
    "section",
    { className: "metrics", "aria-label": "Project status", key: "metrics" },
    h(Metric, { label: "Run check", value: snapshot.display_readiness || displayText(snapshot.readiness), tone: "ready" }),
    h(Metric, { label: "Report support", value: reportStatusLabel(snapshot.report_status, snapshot.display_report_status), tone: snapshot.report_status === "blocked" ? "attention" : "ready" }),
    h(Metric, { label: "Open issues", value: String(counts.total) }),
    h(Metric, { label: "Open reviews", value: String(counts.attention), tone: counts.attention ? "attention" : "ready" })
  );
  const intakePanel = h(IntakeEditor, {
        key: "intake",
        draft: intakeDraft,
        setDraft: setIntakeDraft,
        liveMode,
        message: intakeMessage,
        intakeEditContract: actionContracts.intake_edit || {},
        onSave: saveIntakeDraft,
        onReload: refreshCurrentIntake,
        onPreviewRef: loadFilePreview
      });
  const sourceImportPanel = h(SourceImportPanel, {
        key: "source-import",
        draft: sourceImportDraft,
        setDraft: setSourceImportDraft,
        message: sourceImportMessage,
        importing: sourceImporting,
        event: sourceImportEvent,
        liveMode,
        project: snapshot.project,
        sourceList: sourceListContext,
        sourceImportContract: actionContracts.source_import || {},
        onImport: importSourceLive,
        onPreview: loadFilePreview,
        onAddToIntake: addImportedSourceToIntakeDraft,
        onOpenIntake: () => openDetail("sources", "Intake")
      });
  const rawSourcePanel = h(RawSourceManagerPanel, {
        key: "raw-source",
        sourceList: sourceListContext,
        draft: sourceEditDraft,
        setDraft: setSourceEditDraft,
        message: sourceEditMessage || sourceListMessage,
        editing: sourceEditing,
        event: sourceEditEvent,
        liveMode,
        project: snapshot.project,
        sourceEditContract: actionContracts.source_edit || {},
        onOpenSource: openRawSourceForEdit,
        onSave: saveRawSourceEdit,
        onReload: reloadSourceList,
        onPreview: loadFilePreview,
        onOpenReadiness: () => openDetail("sources", "File check")
      });
  const projectFilePanel = h(CaseFilePanel, {
        key: "case-file",
        snapshot,
        receiptHistory,
        projectEntry: currentProjectEntry,
        intakeDraft,
        sourceImportDraft,
        sourceEditDraft,
        traceContext,
        workflowContext,
        reportContext: reportPanelContext,
        healthContext,
        serverStatus,
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
        saving: projectFileSaving,
        saveEvent: projectFileSaveEvent,
        projectFileContract: actionContracts.project_file || {},
        onSave: saveProjectFileLive,
        onPreview: loadFilePreview
      });
  const reviewWorkspacePanel = h(ReviewWorkspace, {
        key: "review",
        snapshot,
        row: selectedRow,
        reviewState: selectedReviewState,
        setReviewState: setSelectedReviewState,
        liveMode,
        reviewContract: actionContracts.review || {},
        applyReviewLive
      });
  const rowActionPanel = h(RowActionWorkspace, {
        key: "row-action",
        snapshot,
        row: selectedRow,
        actionState: selectedActionState,
        setActionState: setSelectedActionState,
        liveMode,
        nextStepContract: actionContracts.next_step || {},
        applyRowActionLive
      });
  const projectCreatePanel = h(ProjectCreatePanel, {
        key: "create",
        draft: projectCreateDraft,
        setDraft: setProjectCreateDraft,
        message: projectCreateMessage,
        creating: projectCreating,
        liveMode,
        projects,
        projectFolders,
        projectCreateContract: actionContracts.project_create || {},
        onCreate: createProjectLive,
        onPreview: loadFilePreview,
        filePreview,
        filePreviewMessage
      });
  const openDetail = (workspaceId, subsection) => {
    setActiveWorkspace(workspaceId);
    setActiveSubsection(subsection);
    setActiveModalKey(detailKey(workspaceId, subsection));
  };
  const navigateWorkspace = (workspaceId, subsection) => {
    setActiveWorkspace(workspaceId);
    setActiveSubsection(subsection);
    setActiveModalKey("");
  };
  const hydrateProjectCreateSources = (projectOrFolder) => {
    if (!liveMode || !projectOrFolder) return;
    const folder = typeof projectOrFolder === "string" ? { project: projectOrFolder } : projectOrFolder;
    const project = String(folder.project || "").trim();
    if (!project) return;
    const previewSourceRefs = uniqueLines(folder.raw_preview_files || []);
    fetch(endpointUrl("/api/sources", { project }), { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "source list fetch failed"))
      .then((payload) => {
        const sourceRefs = uniqueLines(
          ((payload && payload.sources) || [])
            .map((source) => source && source.path)
            .filter(Boolean)
        );
        if (!sourceRefs.length) return;
        let updated = false;
        setProjectCreateDraft((draft) => {
          if (String(draft.project || "").trim() !== project) return draft;
          const currentRefs = String(draft.source_refs_text || "").trim();
          const previewRefsText = previewSourceRefs.join("\n").trim();
          if (currentRefs && currentRefs !== previewRefsText) return draft;
          updated = sourceRefs.join("\n") !== currentRefs;
          return updated ? { ...draft, source_refs_text: sourceRefs.join("\n") } : draft;
        });
        if (updated && sourceRefs.length > previewSourceRefs.length) {
          setProjectCreateMessage(`Loaded ${sourceRefs.length} source file paths from ${project}.`);
        }
      })
      .catch((err) => {
        setProjectCreateMessage(`Could not load source files for ${project}: ${err.message || err}`);
      });
  };
  const startProjectCreate = (projectOrFolder) => {
    if (projectOrFolder) {
      setProjectCreateDraft((draft) => projectCreateDraftFromFolder(projectOrFolder, draft));
      hydrateProjectCreateSources(projectOrFolder);
    }
    navigateWorkspace("projects", "Add intake");
  };
  const projectLandingPicker = h(ProjectLandingPicker, {
        key: "project-landing-picker",
        projects,
        projectFolders,
        selectedProjectKey,
        snapshot,
        liveMode,
        loading: loadingSnapshot,
        onSelect: openProject,
        onBrowse: () => navigateWorkspace("projects", "All projects"),
        onCreate: startProjectCreate
      });
  const workspacePanels = {
    overview: {
      Status: [
        statusMetrics,
        h(ProjectWorkflowPanel, { key: "workflow", workflowContext, message: workflowMessage, liveMode, onOpenDetail: openDetail }),
        h(NextMovePanel, { key: "next", snapshot, selectedRow, onInspectRow: inspectRow, onReviewRow: reviewRow, liveMode }),
        h(ClaimSummary, { key: "claim", snapshot }),
        h(ProjectReviewSummary, { key: "review-summary", snapshot, selectedRow })
      ],
      Diagnosis: [h(ClaimSummary, { key: "claim", snapshot }), h(ProjectReviewSummary, { key: "review-summary", snapshot, selectedRow }), h(Toolbar, { key: "toolbar", filter, query, setFilter, setQuery }), rowTablePanel],
      Evidence: [sourceReadinessPanel, h(StageRail, { key: "stages", snapshot, onInspectRow: inspectRow })]
    },
    sources: {
      "File check": [sourceReadinessPanel],
      Intake: [intakePanel],
      "Add source": [sourceImportPanel],
      "Edit source": [rawSourcePanel]
    },
    run: {
      Plan: [h(TraceConsolePanel, { key: "trace", traceContext, message: traceMessage, liveMode, onPreviewSource: loadFilePreview }), h(CommandCockpit, { key: "commands", snapshot, selectedRow, traceContext, reportContext: reportPanelContext, healthContext, claimSupportContext, onInspectRow: inspectRow })],
      Preflight: [h(PreflightRunPanel, { key: "preflight", traceContext, event: preflightEvent, message: preflightMessage, running: preflightRunning, liveMode, preflightContract: actionContracts.preflight || {}, onRun: runPreflightLive })],
      "Start run": [h(BoundedRunPanel, { key: "bounded-run", traceContext, event: boundedRunEvent, message: boundedRunMessage, running: boundedRunRunning, previewing: boundedRunPreviewing, liveMode, runContract: actionContracts.run_preview_and_confirm || {}, onRun: requestBoundedRunLive })],
      Results: [h(RunHistoryPanel, { key: "run-history", runHistory: runHistoryContext, message: runHistoryMessage, liveMode, onPreview: loadFilePreview, onUseActionNote: useActionNote }), h(EvidenceSupportPanel, { key: "evidence-support", claimSupport: claimSupportContext, message: claimSupportMessage, liveMode, onPreview: loadFilePreview })],
      Advisories: [h(HealthActionsPanel, { key: "health", healthContext, healthMessage, liveMode, onPreviewSource: loadFilePreview, onUseActionNote: useHealthActionNote }), h(CommandRail, { key: "command-rail", snapshot, selectedRow })]
    },
    save: {
      "Support check": [h(BlockerPanel, { key: "blocker", snapshot, onReviewRow: reviewRow })],
      "Report inputs": [h(ReportContractPanel, { key: "report", reportContext: reportPanelContext, message: reportContractMessage, liveMode, onPreview: loadFilePreview }), h(ProvenanceStrip, { key: "provenance", rows: snapshot.rows || [] })],
      "Project file": [projectFilePanel]
    },
    review: {
      "Open issues": [rowTablePanel],
      "Save review": [h(ReviewQueue, { key: "queue", row: selectedRow, reviewState: selectedReviewState, receiptHistory, snapshot, liveMode, onPreview: loadFilePreview }), reviewMessage ? h("div", { className: "review-message", key: "review-message" }, reviewMessage) : null, reviewWorkspacePanel],
      "Save next step": [rowActionPanel],
      Receipts: [h(WriteReceiptPanel, { key: "write-receipt", receiptEvent: writeReceiptEvent, refreshResults: lastRefreshResults, liveMode, onPreview: loadFilePreview }), h(ReceiptHistoryPanel, { key: "receipts", history: receiptHistory, message: receiptHistoryMessage, liveMode, onPreview: loadFilePreview })]
    },
    projects: {
      "Current project": [],
      "All projects": [
        h(ProjectSwitchboard, {
          key: "switchboard",
          projects,
          projectFolders,
          selectedProjectKey,
          snapshot,
          liveMode,
          loading: loadingSnapshot,
          onSelect: openProject,
          onCreate: startProjectCreate,
          onPreview: loadFilePreview,
          filePreview,
          filePreviewMessage
        })
      ],
      "Add intake": [projectCreatePanel],
      Files: [
        h(ServerStatusPanel, { key: "server-status", status: serverStatus, liveMode, message: serverStatusMessage, onRefresh: refreshServerReadiness }),
        h(ProjectContextPanel, { key: "context", projectEntry: currentProjectEntry, snapshot, liveMode, onPreview: loadFilePreview })
      ]
    }
  };
  const activeSection = WORKSPACE_SECTIONS.find((section) => section.id === activeWorkspace) || WORKSPACE_SECTIONS[0];
  const activeSubnav = activeSection.subnav.includes(activeSubsection) ? activeSubsection : activeSection.subnav[0];
  const activeWorkspacePanels = ((workspacePanels[activeWorkspace] || {})[activeSubnav]) || [];
  const modalDetails = Object.fromEntries(
    Object.entries(workspacePanels).flatMap(([workspaceId, sections]) =>
      Object.entries(sections).map(([subsection, panels]) => {
        const section = WORKSPACE_SECTIONS.find((item) => item.id === workspaceId) || WORKSPACE_SECTIONS[0];
        const copy = detailCopy(workspaceId, subsection);
        return [
          detailKey(workspaceId, subsection),
          {
            ...copy,
            eyebrow: `${section.label} / ${subsection}`,
            panels
          }
        ];
      })
    )
  );
  const activeModal = activeModalKey ? modalDetails[activeModalKey] : null;
  const openReviewItem = (label) => {
    if (label) setSelectedLabel(label);
    openDetail("review", "Save review");
  };
  const openInspectItem = (label) => {
    if (label) setSelectedLabel(label);
    openDetail("overview", "Diagnosis");
  };
  const projectHomeSummary = h(ProjectHomeSummary, {
    key: "project-home-summary",
    snapshot,
    runHistory: runHistoryContext,
    traceContext,
    workflowContext,
    reportContext: reportPanelContext,
    receiptHistory,
    claimSupport: claimSupportContext,
    sourceList: sourceListContext,
    liveMode,
    onOpenDetail: openDetail,
    onInspectItem: openInspectItem
  });
  const projectsWorkspace = activeWorkspace === "projects";
  const projectsHome = projectsWorkspace && activeSubnav === "Current project";
  const topbarClaimRow = rowByLabel((snapshot && snapshot.rows) || [], "Bounded claim");
  const topbarTitle = humanProjectTitle(snapshot, topbarClaimRow);
  return h(
    "main",
    { className: "app-shell" },
    h(Sidebar, {
      snapshot,
      counts,
      activeWorkspace,
      activeSubsection: activeSubnav,
      setActiveWorkspace,
      setActiveSubsection,
      projects,
      projectFolders,
      selectedProjectKey,
      liveMode,
      loadingSnapshot,
      onSelectProject: openProject,
      onOpenProjects: () => navigateWorkspace("projects", "All projects"),
      onNavigateWorkspace: navigateWorkspace,
      onOpenDetail: openDetail
    }),
    h(
      "section",
      { className: "workbench" },
      h(
        "header",
        { className: "topbar" },
        h(
          "div",
          { className: "topbar-copy" },
          h("span", { className: "eyebrow" }, "Project Workbench"),
          h("h1", null, topbarTitle),
          h(ProjectIdentity, { snapshot })
        ),
        h(
          "div",
          { className: "topbar-actions" },
          liveMode
            ? h(
                "button",
                {
                  type: "button",
                  className: "snapshot-link mobile-project-picker",
                  onClick: () => navigateWorkspace("projects", "All projects"),
                  disabled: loadingSnapshot,
                  title: loadingSnapshot ? "Refreshing project list" : "Open the full project inventory"
                },
                loadingSnapshot ? "Refreshing projects" : "All projects"
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
          h("a", { href: snapshotJsonHref(snapshot, liveMode), className: "snapshot-link", title: "Open backing JSON data" }, "Project data")
        )
      ),
      modeMessage ? h("div", { className: `mode-banner ${liveMode ? "live" : "offline"}` }, modeMessage) : null,
      actionMessage ? h("div", { className: `mode-banner ${liveMode ? "live" : "offline"}` }, actionMessage) : null,
      h(PendingEditsStrip, { items: pendingEditorItems, onOpenDetail: openDetail }),
      h(
        "section",
        { className: `workspace-view ${activeWorkspace}`, "aria-label": "Active project area" },
        projectsHome ? projectLandingPicker : null,
        projectsHome ? projectHomeSummary : null,
        projectsHome || projectsWorkspace
          ? null
          : h(WorkspacePageHeader, {
              activeSection,
              activeSubnav,
              snapshot,
              counts,
              activeBlockerRow: activeBlocker(snapshot.rows || []),
              onOpenCurrentProject: () => navigateWorkspace("projects", "Current project"),
              onOpenWorkspace: navigateWorkspace,
              onReviewItem: openReviewItem
            }),
        projectsHome || projectsWorkspace
          ? null
          : h(SectionMenu, {
              activeWorkspace,
              activeSubsection: activeSubnav,
              onOpenWorkspace: navigateWorkspace
            }),
        activeWorkspacePanels.length
          ? h(
              "section",
              { className: "active-workspace-panels", "aria-label": `${activeSection.label} ${activeSubnav}` },
              activeWorkspacePanels
            )
          : null
      )
    ),
    h(ModalShell, { detail: activeModal, modalKey: activeModalKey, onClose: closeActiveModal }),
    h(ProjectRunConfirmDialog, { prompt: projectRunPrompt, onCancel: cancelProjectRunPrompt, onConfirm: runBoundedLive }),
    h(UnsavedChangesDialog, { prompt: discardPrompt, onCancel: cancelDiscardPrompt, onDiscard: confirmDiscardPrompt })
  );
}

createRoot(document.getElementById("root")).render(h(WorkbenchErrorBoundary, null, h(App)));
