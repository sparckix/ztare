import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@mantine/core/styles.css";  // the create-project form uses raw Mantine components; without this it renders styleless
import "./styles.css";              // loaded AFTER Mantine so the workbench's design system wins any conflict
import {
  GUIDANCE_LABELS, sourceBasename, linesFromText, uniqueLines, parseJsonLikeText,
  guidanceLabel, guidanceText, projectKeyFromPreviewPath, jsonLineRecordsFromPreview,
  receiptRecordTitle, receiptRecordStatus, receiptRecordArtifactPaths,
  sourceWarningIssueLabel, sourceWarningIssueAction,
  savedProjectSummaryFromPreview, projectIntakeSummaryFromPreview, projectLaunchBundleSummaryFromPreview,
  scoringGuideSummaryFromPreview, sourceIndexSummaryFromPreview, sourceNoteSummaryFromPreview,
  evidenceGapSummaryFromPreview, evidenceGapResolutionSummaryFromPreview, runResultSummaryFromPreview,
  probabilityModelSummaryFromPreview, evidenceFetchSummaryFromPreview, evidencePacketSummaryFromPreview,
  evidenceProvenanceSummaryFromPreview, reportSupportSummaryFromPreview, sourceWarningSummaryFromPreview,
  actionRecommendationSummaryFromPreview, derivedConstraintSummaryFromPreview, receiptLedgerSummaryFromPreview,
  runSetupDecisionSummaryFromPreview, reportSynthesisAttemptSummaryFromPreview, runHistorySummaryFromPreview
} from "./preview-parsers.js";
import {
  StatusDot,
  Teach,
  Term,
  WriteBoundary,
  displayMessage,
  displayText,
  isPreviewableRepoPath,
  pendingPathPreview,
  previewFileTitle,
  previewableRepoPath,
  repoPathCandidate
} from "./design-system.js";
import {
  LeanMillPanel,
  emptyLeanMillActionDraft,
  emptyLeanMillBlueprintDraft
} from "./workspaces/leanmill.jsx";
import { DayZeroStartPanel } from "./workspaces/start.jsx";
import { Thesis } from "./sections/thesis.jsx";
import { Assumptions } from "./sections/assumptions.jsx";
import { RunFindings } from "./sections/results.jsx";
import { Evidence } from "./sections/evidence.jsx";
import { OpenPoints } from "./sections/openpoints.jsx";
import { Verdict } from "./sections/verdict.jsx";
import { ResearchMap } from "./sections/researchmap.jsx";
import { ScoringGuide } from "./sections/scoringguide.jsx";
import { Charter } from "./sections/charter.jsx";
import { History } from "./sections/history.jsx";
import { RunConsole } from "./sections/runconsole.jsx";
import { marked } from "marked";
import markedKatex from "marked-katex-extension";
import "katex/dist/katex.min.css";
import {
  ScrollText, Target, FolderOpen, Zap, Workflow, ListChecks, Gavel, Clock,
  LayoutGrid, FunctionSquare, Settings as SettingsIcon, FileText, Beaker, Network,
  Upload as IconUpload,
} from "lucide-react";
import DOMPurify from "dompurify";

// One quiet line icon per destination (lucide). Keyed by the nav label so it works for top-level and
// per-section menus alike. 16px, currentColor — reads as wayfinding, not decoration.
const NAV_ICON = {
  "Charter": ScrollText, "Thesis": Target, "Evidence": FolderOpen,
  "Pressure-test the thesis": Zap, "Map": Network, "Open points": ListChecks,
  "Verdict": Gavel, "History": Clock, "ZTARE Projects": LayoutGrid,
  "LeanMill": FunctionSquare, "Settings": SettingsIcon,
  // home-link aliases — same destinations, plainer labels
  "My claim": Target, "Test it": Zap,
};
function navIcon(label, size = 16) {
  const Ico = NAV_ICON[String(label || "").trim()];
  return Ico ? h(Ico, { size, strokeWidth: 1.9, "aria-hidden": "true" }) : null;
}
// LaTeX math in markdown ($$…$$ block, $…$ inline) — renders in every marked.parse site (file viewer,
// charter, detail modals). nonStandard so single-$ inline works; throwOnError off so bad TeX shows raw.
marked.use(markedKatex({ throwOnError: false, nonStandard: true }));
import { copyText, downloadText } from "./lib/browser.js";
import {
  caseScopedDownloadName,
  itemLabel,
  parseReviewFile,
  rowSlug,
  safeFilePart
} from "./lib/rows.js";
import {
  formatWorkbenchTemplate,
  formatWriteTemplateItems,
  receiptPathFromWriteItems,
  stampedPayloadPattern,
  workspaceDirForProject,
  writePathsFromItems
} from "./lib/write-paths.js";
import { MantineProvider, TextInput as MTextInput, Textarea as MTextarea, Button as MButton, Stack as MStack, Group as MGroup, Box as MBox, Text as MText, Title as MTitle, Collapse as MCollapse, Anchor as MAnchor } from "@mantine/core";
import { workbenchTheme } from "./theme.js";

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

const WORKSPACE_SECTIONS = [
  { id: "projects", label: "ZTARE Projects", summary: "Open a project, connect a folder, or create a new project", subnav: ["Projects", "Current project", "Connect project", "Files", "Settings"] },
  { id: "overview", label: "Thesis", summary: "What you're arguing, what would change your mind, where it's weakest, and how it held up", subnav: ["Thesis", "Assumptions", "Charter", "Evidence summary", "Research map"] },
  { id: "sources", label: "Evidence", summary: "What backs your thesis, what's missing, and add more", subnav: ["Prepare files", "Project brief"] },
  { id: "run", label: "Pressure-test the thesis", summary: "Run the loop that attacks your thesis to find its strongest, best-defended version", subnav: ["Ready to run", "Scoring guide", "Run settings", "Check readiness", "Results", "Fix warnings"] },
  { id: "leanmill", label: "LeanMill", summary: "Formalize & solve, fix a failing proof, or kernel-ratify a finished one", subnav: ["Start", "Draft target", "Run a proof", "Proof files", "Proof status"] },
  { id: "review", label: "Open points", summary: "Loose ends to look at, with your notes on each", subnav: ["Things to review", "Save review", "Save next step", "Saved history"] },
  { id: "save", label: "Verdict", summary: "Whether you can trust this, what's weak, and what to fix", subnav: ["Report readiness", "Report inputs", "Project file"] }
];


const WORKSPACE_DETAIL_COPY = {
  "overview:Overview": {
    title: "Overview",
    body: "Where your thesis stands: what backs it, how it has been tested, and what still needs a look."
  },
  "overview:Thesis": {
    title: "Thesis",
    body: ""
  },
  "overview:Assumptions": {
    title: "Assumptions",
    body: "The constraints this thesis is committed to — derived by the loop, provisional until they survive repeated pressure-testing."
  },
  "overview:Charter": {
    title: "Charter",
    body: "The mandate this project serves. Your thesis is the answer that has to keep serving it."
  },
  "overview:Evidence summary": {
    title: "Evidence",
    body: "Which of your files back the thesis, and what's still missing."
  },
  "overview:Research map": {
    title: "Research map",
    body: "Your claim, its strongest support, the open tensions, and what's left to test — in one view."
  },
  "overview:Help": {
    title: "How this works",
    body: "What this tool does, the steps a project goes through, and the words you'll run into."
  },
  "sources:Prepare files": {
    title: "Evidence",
    body: "What backs your thesis, what's still missing, and add more."
  },
  "sources:Project brief": {
    title: "Edit project brief",
    body: "Edit your thesis, what would change your mind, files, notes, and caveats."
  },
  "sources:Add file": {
    title: "Add a file",
    body: "Add a file from your computer and line it up for the project."
  },
  "sources:Edit file": {
    title: "Edit a file",
    body: "Open and revise a file you've already added."
  },
  "projects:Settings": {
    title: "Workbench Settings",
    body: "Choose the model and evidence-fetch defaults used by local workbench actions."
  },
  "run:Ready to run": {
    title: "Pressure-test the thesis",
    body: "Run the loop that attacks your thesis to find its strongest version. See if it's ready, what's blocking it, and the next step."
  },
  "run:Scoring guide": {
    title: "Scoring guide",
    body: "The rubric every run uses to score your thesis. See how it's graded, and edit it."
  },
  "run:Check readiness": {
    title: "Is it ready to run?",
    body: "A quick local check before you spend model time."
  },
  "run:Start run": {
    title: "Start the test",
    body: "Run the analysis once the readiness check passes."
  },
  "run:Results": {
    title: "Results",
    body: "How your thesis held up, where it's weak, and what evidence is thin."
  },
  "run:Fix warnings": {
    title: "Warnings",
    body: "Turn warnings and suggested moves into your next saved step."
  },
  "leanmill:Start": {
    title: "LeanMill",
    body: "Start from notes, a theorem-shaped target, or an existing proof file."
  },
  "leanmill:Draft target": {
    title: "Draft Target",
    body: "Save the target statement and research notes LeanMill should try next."
  },
  "leanmill:Run a proof": {
    title: "Run a proof",
    body: "Launch a proof attempt from a saved target or a Lean file. The outcome lands on Proof status."
  },
  "leanmill:Proof files": {
    title: "Proof Files",
    body: "Review saved targets, Lean files, and project-local formal work."
  },
  "leanmill:Proof status": {
    title: "Proof Status",
    body: "See what LeanMill tried, what passed, what failed, and which files support the status."
  },
  "save:Report readiness": {
    title: "Can I trust this report?",
    body: "See whether the report matches current project files, and what must be fixed first."
  },
  "save:Report inputs": {
    title: "What the verdict is built on",
    body: "See what backs the verdict and where each input came from."
  },
  "save:Project file": {
    title: "Save your project",
    body: "Save the current state of the project, its history, and where the files live."
  },
  "review:Things to review": {
    title: "Open points",
    body: "The parts of your thesis — pick one to see what backs it and note where it stands."
  },
  "review:Save review": {
    title: "Save where this point stands",
    body: "Mark the point you picked as looked at, set aside for now, or still holding back the verdict."
  },
  "review:Save next step": {
    title: "Save the next step",
    body: "Write down what should happen next."
  },
  "review:Saved history": {
    title: "History",
    body: "How this investigation has evolved — every run, what it concluded, and the decisions and evidence changes along the way."
  },
  "projects:Current project": {
    title: "Where this stands",
    body: "The claim, how it's holding up, and the next thing to do."
  },
  "projects:Projects": {
    title: "Projects",
    body: "Open a connected project, connect an existing folder, or create a new project."
  },
  "projects:Connect project": {
    title: "Connect Project",
    body: "Create a project, or save the project brief that makes an existing folder editable."
  },
  "projects:Files": {
    title: "Project Files",
    body: "Inspect where this project lives in the repository."
  }
};

const WORKSPACE_ALIASES = {
  cases: "projects",
  case: "projects"
};

const WORKSPACE_SUBSECTION_ALIASES = {
  projects: {
    "All projects": "Projects",
    "Project library": "Projects",
    "Add intake": "Connect project",
    Intake: "Connect project"
  },
  overview: {
    Status: "Thesis",
    Overview: "Thesis",
    Diagnosis: "Thesis",
    "My claim": "Thesis",
    Claim: "Thesis",
    Evidence: "Evidence summary",
    "Evidence map": "Evidence summary"
  },
  sources: {
    Intake: "Project brief",
    Readiness: "Prepare files",
    "Prepare sources": "Prepare files",
    "Check files": "Prepare files",
    "File check": "Prepare files",
    "Add source": "Add file",
    "Add source file": "Add file",
    "Edit source": "Edit file",
    "Edit source file": "Edit file"
  },
  run: {
    Plan: "Ready to run",
    "Can it run?": "Ready to run",
    "Start run": "Ready to run",
    Advisories: "Fix warnings",
    "Suggested fixes": "Fix warnings"
  },
  review: {
    "Review points": "Things to review",
    "Project checks": "Things to review",
    "Open issues": "Things to review",
    Review: "Save review",
    "Next step": "Save next step",
    Receipts: "Saved history"
  },
  save: {
    "Report support": "Report readiness",
    "Support check": "Report readiness",
    "Report/export": "Report readiness",
    Report: "Report inputs"
  },
  leanmill: {
    Overview: "Start",
    Blueprint: "Draft target",
    Formalizations: "Proof files",
    History: "Proof status",
    "Saved history": "Proof status",
    Receipts: "Proof status"
  }
};

const REVIEW_ACTIONS = [
  { id: "reviewed", label: "Mark reviewed" },
  { id: "deferred", label: "Defer" },
  { id: "blocked", label: "Hold for support" }
];

const REPORT_CONTRACT_SCHEMA = "ztare-forensic-workbench-report-contract-v1";
const PROJECT_FILE_SCHEMA = "ztare-forensic-workbench-project-file-v1";
const PROJECT_FILE_WRITE_SCHEMA = "ztare-forensic-workbench-project-file-write-receipt-v1";
const SOURCE_TYPES = ["source_evidence", "seed_hypothesis", "research_question", "collection_todo", "untyped"];
const SOURCE_ARTIFACT_KINDS = [
  "project_note",
  "agent_notes",
  "source_summary",
  "computation_output",
  "script_or_code",
  "report_draft",
  "proof_note",
  "search_summary",
  "raw_evidence"
];
const SOURCE_TYPE_LABELS = {
  source_evidence: "Evidence file",
  seed_hypothesis: "Starting note",
  research_question: "Research question",
  collection_todo: "To collect",
  untyped: "Other"
};
const SOURCE_ARTIFACT_KIND_LABELS = {
  project_note: "Project note",
  agent_notes: "Agent session notes",
  source_summary: "Source summary",
  computation_output: "Computation output",
  script_or_code: "Script or code",
  report_draft: "Report draft",
  proof_note: "Proof note",
  search_summary: "Search summary",
  raw_evidence: "Raw evidence"
};

const SOURCE_TYPE_HELP = {
  source_evidence: "Use this file as support for the thesis.",
  seed_hypothesis: "Use this file as an early project note.",
  research_question: "Use this file to capture an open question.",
  collection_todo: "Use this file as something to collect or verify later.",
  untyped: "Keep this file in the project without assigning a specific role."
};

const PROJECT_SLUG_RE = /^[A-Za-z0-9_.-]+$/;
const SOURCE_IMPORT_FILENAME_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(md|txt)$/;
const SOURCE_UPLOAD_MAX_BYTES = 512 * 1024;

function emptySourceImportDraft() {
  return { filename: "", source_type: "source_evidence", artifact_kind: "project_note", created_by: "", body: "", evidence_gap: null };
}

function uploadedSourceBody(text, fallbackSourceType = "source_evidence") {
  const raw = String(text || "");
  const fallback = SOURCE_TYPES.includes(fallbackSourceType) ? fallbackSourceType : "source_evidence";
  if (!raw.startsWith("---\n")) return { source_type: fallback, artifact_kind: "project_note", created_by: "", body: raw };
  const end = raw.indexOf("\n---\n", 4);
  if (end === -1) return { source_type: fallback, artifact_kind: "project_note", created_by: "", body: raw };
  const frontmatter = raw.slice(4, end).split(/\r?\n/);
  const frontmatterValue = (key) => {
    const line = frontmatter.find((item) => item.trim().startsWith(`${key}:`));
    return line ? line.split(":").slice(1).join(":").trim() : "";
  };
  const parsedType = frontmatterValue("source_type");
  const parsedKind = frontmatterValue("artifact_kind");
  const body = raw.slice(end + "\n---\n".length).replace(/^\n/, "");
  return {
    source_type: SOURCE_TYPES.includes(parsedType) ? parsedType : fallback,
    artifact_kind: SOURCE_ARTIFACT_KINDS.includes(parsedKind) ? parsedKind : "project_note",
    created_by: frontmatterValue("created_by"),
    body
  };
}

function emptySourceEditDraft() {
  return { relative_raw_path: "", source_type: "source_evidence", artifact_kind: "", created_by: "", body: "" };
}

function emptyEvidenceGapDraft() {
  return { index: "", reason: "", evidence_refs_text: "" };
}

function sourceTypeLabel(value) {
  return SOURCE_TYPE_LABELS[value] || displayText(value || "source");
}

function sourceArtifactKindLabel(value) {
  return SOURCE_ARTIFACT_KIND_LABELS[value] || displayText(value || "project note");
}

function sourceWorkSummary(row) {
  if (!row || typeof row !== "object") return "";
  const parts = [];
  if (row.artifact_kind) parts.push(sourceArtifactKindLabel(row.artifact_kind));
  if (row.source_type) parts.push(sourceTypeLabel(row.source_type));
  if (row.created_by) parts.push(`by ${displayText(row.created_by)}`);
  if (row.chars !== undefined) parts.push(`${row.chars || 0} chars`);
  return parts.filter(Boolean).join(" / ");
}

function itemStatus(row) {
  if (row && row.display_status) return displayMessage(row.display_status);
  return displayText(row && row.status);
}

function itemDetail(row) {
  if (row && row.display_detail) return displayMessage(row.display_detail);
  return displayMessage(row && row.detail);
}


function admissionDestination(admission, projectState, fallback = ["run", "Ready to run"]) {
  const state = admission && typeof admission === "object" ? admission : {};
  const blockers = Array.isArray(state.blockers) ? state.blockers.filter(Boolean) : [];
  const firstBlocker = blockers[0] || {};
  const channel = String(firstBlocker.recovery_channel || firstBlocker.id || "").toLowerCase();
  const command = String(firstBlocker.next_command || state.recommended_first_command || "").toLowerCase();
  if (channel.includes("evidence") || command.includes("evidence-prepare") || command.includes("evidence-fetch")) {
    return ["sources", "Prepare files"];
  }
  if (channel.includes("source") || command.includes("source-check") || command.includes("source-index")) {
    return ["sources", "Prepare files"];
  }
  if (channel.includes("scoring") || command.includes("validate-rubric")) {
    return ["run", "Ready to run"];
  }
  const nextAction = projectState && projectState.next_action && typeof projectState.next_action === "object"
    ? projectState.next_action
    : {};
  const destination = nextAction.ui_destination || {};
  if (destination.workspace || destination.subsection) {
    return [destination.workspace || nextAction.workspace || fallback[0], destination.subsection || nextAction.subsection || fallback[1]];
  }
  if (state.can_start_run) return ["run", "Ready to run"];
  if (state.can_enter_kernel) return ["run", "Check readiness"];
  return fallback;
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
    .replace(/\bbest-supported explanation\b/gi, "thesis");
  const candidate = claimSubject ? `${claimSubject[1]} thesis` : withoutLead;
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
    if (subject) return subject;
  }
  return titleFromSlug((snapshot && snapshot.project) || "Local project");
}

function thesisLead(value) {
  const text = compactWhitespace(value);
  const match = text.match(/best-supported explanation for (?:the )?(.+?) is (.+?);/i);
  if (match) return `Your claim about ${cleanProjectSubject(match[1])}: ${shortText(match[2], 140)}.`;
  return shortText(firstSentence(text) || text, 220);
}

function falsifierLead(value) {
  const text = compactWhitespace(value).replace(/^Reject or demote the claim if\s+/i, "");
  return shortText(text, 155);
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
    row: "Readiness check",
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
  add(items, "Command", row.command, "command");
  add(items, "Saved work", row.receipt, "receipt");
  add(items, "Review file", row.review_artifact, "review");
  add(items, "Warning", row.warning, "warning");
  return items;
}

function shellDoubleQuoted(value, fallback = "") {
  const text = String(value || fallback || "")
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\s+/g, " ")
    .trim();
  return `"${text || fallback}"`;
}

function caseFileDownloadName(snapshot) {
  const project = safeFilePart((snapshot && snapshot.project) || "ztare");
  const intake = safeFilePart((snapshot && snapshot.intake) || "project");
  return `${project}_${intake}_project_file.json`;
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

function sourceNoteFilename(value, fallback = "evidence_gap") {
  const slug = String(value || fallback)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 72);
  return `${slug || fallback}_evidence.md`;
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
    non_claims_text: "",
    uploaded_sources: [],
    recovery_payload: null
  };
}

function uniqueTextLines(value) {
  return uniqueLines(String(value || "").split(/\r?\n/));
}

function projectCreateDraftFromFolder(projectOrFolder, currentDraft = emptyProjectCreateDraft()) {
  if (!projectOrFolder) return currentDraft;
  const folder = typeof projectOrFolder === "string" ? { project: projectOrFolder } : projectOrFolder;
  const project = String(folder.project || "").trim();
  if (!project) return currentDraft;

  const projectChanged = String(currentDraft.project || "").trim() !== project;
  const sourceRefs = uniqueLines([
    ...(folder.source_preview_files || []),
    ...(folder.raw_preview_files || []),
    ...(folder.root_preview_files || [])
  ]);
  const workspaceRefs = uniqueLines(folder.workspace_preview_files || []);
  const evidenceRefs = uniqueLines([
    ...sourceRefs.filter((path) => /(^|\/)(evidence|compiled_evidence|.*evidence_gaps)\.(txt|json|md)$/i.test(path)),
    ...workspaceRefs
  ]);
  const existingRefs = uniqueLines([...sourceRefs, ...workspaceRefs]);
  const notes = [
    folder.project_dir ? `Existing folder: ${folder.project_dir}` : `Existing folder: projects/${project}`,
    existingRefs.length ? `Existing files to review:\n${existingRefs.join("\n")}` : ""
  ].filter(Boolean).join("\n\n");

  return {
    ...currentDraft,
    project,
    recovery_payload: projectChanged ? null : currentDraft.recovery_payload || null,
    task: projectChanged || !String(currentDraft.task || "").trim()
      ? `Review ${titleFromSlug(project)}`
      : currentDraft.task,
    notes: projectChanged || !String(currentDraft.notes || "").trim()
      ? notes
      : currentDraft.notes,
    source_refs_text: projectChanged || !String(currentDraft.source_refs_text || "").trim()
      ? sourceRefs.join("\n")
      : currentDraft.source_refs_text,
    evidence_refs_text: projectChanged || !String(currentDraft.evidence_refs_text || "").trim()
      ? evidenceRefs.join("\n")
      : currentDraft.evidence_refs_text
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

function folderHasProjectMaterial(folder) {
  if (!folder) return false;
  if (typeof folder.has_project_files === "boolean") return folder.has_project_files;
  if (typeof folder.has_project_material === "boolean") return folder.has_project_material;
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
  if (refSummary.total) return `${refSummary.present || 0}/${refSummary.total} project-brief files`;
  const sourceCount = Number(project.raw_source_file_count ?? project.raw_file_count ?? project.root_source_file_count ?? 0);
  const workspaceCount = Number(project.workspace_file_count ?? 0);
  const sourceText = sourceCount
    ? `${cappedCountText(sourceCount, project.raw_source_file_count_capped || project.raw_file_count_capped || project.root_source_file_count_capped)} source`
    : "";
  const workspaceText = workspaceCount
    ? `${cappedCountText(workspaceCount, project.workspace_file_count_capped)} workspace`
    : "";
  const parts = [sourceText, workspaceText].filter(Boolean);
  if (parts.length) return parts.join(" / ");
  if (project.has_project_files || project.has_project_material || project.has_case_material) return "project files present";
  return "empty folder";
}

function projectInventorySort(a, b) {
  const aOpen = a && (a.openable || a.intake) ? 1 : 0;
  const bOpen = b && (b.openable || b.intake) ? 1 : 0;
  if (aOpen !== bOpen) return bOpen - aOpen;
  const aHidden = folderHiddenByDefault(a) ? 1 : 0;
  const bHidden = folderHiddenByDefault(b) ? 1 : 0;
  if (aHidden !== bHidden) return aHidden - bHidden;
  const aFiles = folderHasProjectMaterial(a) ? 1 : 0;
  const bFiles = folderHasProjectMaterial(b) ? 1 : 0;
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



function receiptArtifactPath(receipt) {
  if (!receipt) return "";
  const createdPaths = Array.isArray(receipt.created_paths) ? receipt.created_paths.filter(Boolean) : [];
  return receipt.review_file_path || receipt.action_file_path || receipt.project_file_path || receipt.case_file_path || receipt.source_path || receipt.intake_path || createdPaths[0] || "";
}

function actionIntelligenceNote(row, fallback = "Inspect guidance") {
  if (!row) return fallback;
  const backingFiles = evidenceRefDisplayItems(row).map((item) => `${item.label}: ${item.path}`);
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
    backingFiles.length ? `supporting files: ${backingFiles.slice(0, 4).join(", ")}` : ""
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

function actionIntelligencePrimaryPath(row, fallbackPath = "") {
  const refs = evidenceRefDisplayItems(row);
  if (refs.length && refs[0].path) return refs[0].path;
  return fallbackPath || "";
}

function rowForActionNote(rows, action, selectedRow) {
  if (action === "needs_source") {
    return rowByLabel(rows, "Source readiness") || rowByLabel(rows, "Evidence readiness") || selectedRow;
  }
  if (action === "export_blocker") return rowByLabel(rows, "Report readiness") || activeBlocker(rows) || selectedRow;
  if (action === "ready_to_run") return rowByLabel(rows, "Run readiness") || rowByLabel(rows, "Preflight") || selectedRow;
  return selectedRow || activeBlocker(rows) || rowByLabel(rows, "Report readiness") || rowByLabel(rows, "Run readiness") || rows[0] || null;
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


function evidenceGapJustifyWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  const resolution = payload.resolution || {};
  return {
    kind: "evidence_gap_justify",
    row: resolution.target || "Evidence gap",
    result: {
      ...payload,
      receipt: {
        schema: payload.schema || "ztare-forensic-workbench-evidence-gap-justify-v1",
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        receipt_path: payload.receipt_path || "",
        receipt_sha256: payload.receipt_sha256 || "",
        resolution_id: resolution.resolution_id || "",
        gap_sha256: resolution.gap_sha256 || "",
        target: resolution.target || "",
        reason: resolution.reason || ""
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function evidenceFetchWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  const receipt = payload.receipt || {};
  return {
    kind: "evidence_fetch",
    row: "Fetch evidence",
    result: {
      ...payload,
      receipt: {
        schema: receipt.schema || "ztare-forensic-workbench-evidence-fetch-receipt-v1",
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        command: payload.command || "",
        receipt_path: payload.receipt_path || "",
        manifest_path: payload.manifest_path || receipt.manifest_path || "",
        manifest_sha256: receipt.manifest_sha256 || "",
        total_attempted: receipt.total_attempted,
        total_accepted: receipt.total_accepted,
        skipped_duplicates: receipt.skipped_duplicates,
        search_backend: receipt.search_backend || "",
        failure_counts: receipt.failure_counts || payload.failure_counts || {},
        recovery_hints: receipt.recovery_hints || payload.recovery_hints || []
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function evidenceFetchFailureMessage(payload, receipt = {}) {
  const failureCounts = payload.failure_counts && typeof payload.failure_counts === "object"
    ? payload.failure_counts
    : receipt.failure_counts && typeof receipt.failure_counts === "object"
      ? receipt.failure_counts
      : {};
  const recoveryHints = Array.isArray(payload.recovery_hints)
    ? payload.recovery_hints
    : Array.isArray(receipt.recovery_hints)
      ? receipt.recovery_hints
      : [];
  const failureText = Object.entries(failureCounts)
    .map(([key, value]) => `${displayText(key)}=${value}`)
    .join(", ");
  const hint = recoveryHints.find(Boolean);
  return [failureText ? ` Reason: ${failureText}.` : "", hint ? ` Next: ${hint}.` : ""].join("");
}

function evidenceFetchStatusMessage(payload) {
  if (!payload) return "";
  const receipt = payload.receipt || {};
  const attempted = payload.total_attempted ?? receipt.total_attempted;
  const accepted = payload.total_accepted ?? receipt.total_accepted;
  const receiptPath = payload.receipt_path || receipt.receipt_path || "";
  const status = payload.status || (payload.accepted ? "accepted" : "attention");
  const countText = attempted !== undefined || accepted !== undefined
    ? ` Accepted ${accepted ?? 0} of ${attempted ?? 0} attempted.`
    : "";
  const failureText = evidenceFetchFailureMessage(payload, receipt);
  const receiptText = receiptPath ? ` Saved work: ${receiptPath}.` : "";
  if (payload.accepted) return `Evidence fetch finished.${countText}${receiptText}`;
  if (status === "no_new_evidence") return `Evidence fetch ran but found no new evidence.${countText}${failureText}${receiptText}`;
  if (payload.returncode === 0) return `Evidence fetch finished with attention.${countText}${failureText}${receiptText}`;
  return `Evidence fetch failed before closing the gap.${countText}${failureText}${receiptText}`.trim();
}

function reportSupportWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  const isReportSynthesis = payload.schema === "ztare-forensic-workbench-report-synthesis-v1";
  const receipt = payload.receipt || {};
  return {
    kind: isReportSynthesis ? "report_synthesis" : "report_support_refresh",
    row: isReportSynthesis ? "Report inputs" : "Report readiness",
    result: {
      ...payload,
      receipt: {
        schema: receipt.schema || (isReportSynthesis ? "ztare-forensic-workbench-report-synthesis-v1" : "ztare-forensic-workbench-report-contract-refresh-receipt-v1"),
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        command: payload.command || "",
        receipt_path: payload.receipt_path || "",
        report_support_contract: receipt.report_support_contract || payload.report_support_contract || "",
        report_support_sha256: receipt.report_support_sha256 || "",
        returncode: payload.returncode
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function claimCardWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  const receipt = payload.receipt || {};
  return {
    kind: "claim_card",
    row: "Report readiness",
    result: {
      ...payload,
      receipt: {
        schema: receipt.schema || "ztare-forensic-workbench-claim-card-receipt-v1",
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        command: payload.command || "",
        receipt_path: payload.receipt_path || receipt.receipt_path || "",
        json_path: payload.json_path || receipt.json_path || "",
        markdown_path: payload.markdown_path || receipt.markdown_path || "",
        html_path: payload.html_path || receipt.html_path || "",
        card_hash: payload.card_hash || receipt.card_hash || ""
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function projectTestWriteEvent(payload) {
  if (!payload || !payload.write_boundary) return null;
  const receipt = payload.receipt || {};
  return {
    kind: "project_test",
    row: "Project test",
    result: {
      ...payload,
      receipt: {
        schema: receipt.schema || "ztare-forensic-workbench-project-test-receipt-v1",
        status: payload.accepted ? "accepted" : "attention",
        project: payload.project || "",
        rubric: payload.rubric || "",
        intake: payload.intake || "",
        command: payload.command || "",
        receipt_path: payload.receipt_path || "",
        latest_path: payload.latest_path || "",
        test_path: payload.test_path || "",
        returncode: payload.returncode
      }
    },
    snapshotError: payload.snapshot_error || ""
  };
}

function isProjectTestAction(action) {
  const command = String((action && action.command) || "").trim();
  return /\bpython(?:3)?\s+projects\/[^ ]+\/test_model\.py\b/.test(command);
}

function isCompletedReportAction(action) {
  return String((action && action.status) || "") === "completed" || Boolean(action && action.completed_by);
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

function hasContent(value) {
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === "object") return Object.keys(value).length > 0;
  if (typeof value === "string") return Boolean(value.trim());
  return value !== null && value !== undefined;
}

function projectToThesisAudit(projectState = {}, projectObjectContract = {}) {
  const section = (name) => (projectState && projectState[name] && typeof projectState[name] === "object" ? projectState[name] : {});
  const actions = Array.isArray(projectState.actions) ? projectState.actions.filter(Boolean) : [];
  const projectActions = actions.filter((action) => String(action.action_type || "").startsWith("project_"));
  const repairActions = actions.filter((action) => action.action_type === "project_repair");
  const writeActions = projectActions.filter((action) => {
    const boundary = action.write_boundary || {};
    return Boolean(
      boundary.writes_project_files ||
        boundary.writes_repo_files ||
        boundary.receipt_path ||
        (Array.isArray(boundary.write_paths) && boundary.write_paths.length)
    );
  });
  const writeBoundaryReady = writeActions.filter((action) => {
    const boundary = action.write_boundary || {};
    return Boolean(
      boundary.no_change_boundary &&
        (boundary.receipt_path || (Array.isArray(boundary.write_paths) && boundary.write_paths.length))
    );
  });
  const charter = section("charter");
  const thesis = section("thesis");
  const thesisSupport = section("thesis_support");
  const sources = section("sources");
  const evidence = section("evidence");
  const sourceHealth = section("source_health");
  const run = section("run");
  const report = section("report");
  const nextAction = section("next_action");
  const recentChanges = section("recent_changes");
  const files = section("files");
  const recovery = section("recovery");
  const checks = [
    {
      id: "project_object",
      label: "Project object coherent",
      ok: Boolean(projectObjectContract.ok),
      detail: String(projectObjectContract.summary || "")
    },
    {
      id: "charter",
      label: "Project charter visible",
      ok: hasContent(charter.file) && hasContent(charter.status) && charter.exists !== false,
      detail: String(charter.summary || charter.status || "")
    },
    {
      id: "thesis",
      label: "Thesis visible",
      ok: hasContent(thesis.text) && hasContent(thesis.status),
      detail: String(thesis.status || "")
    },
    {
      id: "source_and_evidence",
      label: "Source and evidence state visible",
      ok: hasContent(sources.status) && (hasContent(evidence.status) || hasContent(thesisSupport.status) || hasContent(thesisSupport.display_status)),
      detail: `sources=${sources.status || ""}; evidence=${evidence.status || thesisSupport.display_status || thesisSupport.status || ""}`
    },
    {
      id: "source_health",
      label: "File and evidence warnings visible",
      ok: hasContent(sourceHealth.status) && Object.prototype.hasOwnProperty.call(sourceHealth, "issue_count"),
      detail: String(sourceHealth.summary || "")
    },
    {
      id: "run_state",
      label: "Run state visible",
      ok: hasContent(run.status) && ("run_count" in run || "latest_score" in run || "blocking" in run),
      detail: String(run.summary || run.status || "")
    },
    {
      id: "report_state",
      label: "Report readiness visible",
      ok: hasContent(report.status),
      detail: String(report.summary || report.status || "")
    },
    {
      id: "next_action",
      label: "Next action visible",
      ok: hasContent(nextAction.label) && hasContent(nextAction.workspace),
      detail: `${nextAction.label || ""} -> ${nextAction.workspace || ""}/${nextAction.subsection || ""}`
    },
    {
      id: "repair_actions",
      label: "Repair actions visible",
      ok: repairActions.length > 0,
      detail: `${repairActions.length} repair action(s), ${actions.length} total action(s)`
    },
    {
      id: "write_boundaries",
      label: "Write boundaries visible",
      ok: writeBoundaryReady.length === writeActions.length,
      detail: `${writeBoundaryReady.length}/${writeActions.length} write-capable action(s) name target or saved-history paths and no-change behavior`
    },
    {
      id: "latest_change",
      label: "Latest change visible",
      ok: hasContent(recentChanges.summary) || hasContent(recentChanges.latest_run),
      detail: String(recentChanges.summary || "")
    },
    {
      id: "files",
      label: "Project files visible",
      ok: Number(files.item_count || 0) > 0 && Array.isArray(files.file_groups) && files.file_groups.length > 0,
      detail: `${Number(files.item_count || 0)} files; ${Number(files.previewable_count || 0)} previewable`
    }
  ];
  if (hasContent(recovery)) {
    checks.push({
      id: "recovery_path",
      label: "Recovery path visible",
      ok: hasContent(recovery.intake_target) && actions.some((action) => action.id === "add_intake"),
      detail: String(recovery.summary || "")
    });
  }
  const failedChecks = checks.filter((check) => !check.ok);
  return {
    schema: "ztare-project-to-thesis-audit-v1",
    ok: failedChecks.length === 0,
    check_count: checks.length,
    failed_count: failedChecks.length,
    failed_checks: failedChecks,
    checks,
    action_counts: {
      total: actions.length,
      project_repair: repairActions.length,
      write_capable: writeActions.length,
      write_boundary_ready: writeBoundaryReady.length
    },
    summary: failedChecks.length
      ? `Project path has ${failedChecks.length} missing part${failedChecks.length === 1 ? "" : "s"}.`
      : "Project path is inspectable."
  };
}

function savedProjectSummaryFromContext(snapshot, projectState = {}, workflow = {}, report = {}, items = [], receipts = []) {
  const section = (name) => (projectState && projectState[name] && typeof projectState[name] === "object" ? projectState[name] : {});
  const charter = section("charter");
  const thesis = section("thesis");
  const changeTest = section("change_test");
  const sources = section("sources");
  const evidence = section("evidence");
  const recentChanges = section("recent_changes");
  const admission = section("admission");
  const run = section("run");
  const reportState = section("report");
  const nextAction = section("next_action");
  const actions = Array.isArray(projectState.actions) ? projectState.actions : [];
  const projectObjectContract = workflow && workflow.project_object_contract && typeof workflow.project_object_contract === "object"
    ? workflow.project_object_contract
    : {};
  const projectAudit = projectToThesisAudit(projectState, projectObjectContract);
  const proofPaths = [];
  actions.slice(0, 5).forEach((action) => {
    (Array.isArray(action.receipt_paths) ? action.receipt_paths : []).forEach((path) => path && proofPaths.push(String(path)));
    (Array.isArray(action.outcome_receipt_paths) ? action.outcome_receipt_paths : []).forEach((path) => path && proofPaths.push(String(path)));
    if (action.source) proofPaths.push(String(action.source));
  });
  [charter.file, evidence.file, evidence.gap_file, reportState.contract, report.report_support_contract].forEach((path) => {
    if (path) proofPaths.push(String(path));
  });
  [
    recentChanges.latest_receipt_path,
    recentChanges.latest_review && recentChanges.latest_review.receipt_path,
    recentChanges.latest_review && recentChanges.latest_review.artifact_path,
    recentChanges.latest_next_step && recentChanges.latest_next_step.receipt_path,
    recentChanges.latest_next_step && recentChanges.latest_next_step.artifact_path,
    recentChanges.latest_source_or_evidence_change && recentChanges.latest_source_or_evidence_change.receipt_path,
    recentChanges.latest_source_or_evidence_change && recentChanges.latest_source_or_evidence_change.artifact_path,
    recentChanges.latest_project_file && recentChanges.latest_project_file.receipt_path,
    recentChanges.latest_project_file && recentChanges.latest_project_file.artifact_path
  ].forEach((path) => {
    if (path) proofPaths.push(String(path));
  });
  const seen = new Set();
  return {
    schema: "ztare-saved-project-summary-v1",
    project: snapshot.project || "",
    intake: snapshot.intake || "",
    display_label: displayText(snapshot.project || "project"),
    charter: {
      status: String(charter.status || ""),
      summary: String(charter.summary || ""),
      file: String(charter.file || ""),
      exists: charter.exists !== false
    },
    thesis: thesis.text || snapshot.bounded_claim || "",
    change_test: changeTest.text || snapshot.next_falsifier || "",
    next_action: {
      label: nextAction.label || "not loaded",
      detail: nextAction.detail || "",
      workspace: nextAction.workspace || "",
      subsection: nextAction.subsection || ""
    },
    readiness: {
      sources: sources.status || "",
      evidence: evidence.status || "",
      admission: admission.status || "",
      run: run.status || snapshot.readiness || "",
      report: reportState.status || report.status || snapshot.report_status || ""
    },
    open_action_count: actions.length || items.length,
    recent_receipt_count: receipts.length,
    project_object_ok: Boolean(projectObjectContract.ok),
    project_to_thesis_audit: projectAudit,
    proof_paths: proofPaths.filter((path) => {
      if (!path || seen.has(path)) return false;
      seen.add(path);
      return true;
    }).slice(0, 10)
  };
}

function SourceCheckDetail({ event }) {
  if (!event || !event.source_check) return null;
  const detail = sourceCheckDetail(event);
  const output = detail.error || detail.stderr_tail || detail.stdout_tail || "";
  return h(
    "div",
    { className: `source-check-detail ${detail.accepted ? "ready" : "attention"}` },
    h("span", null, detail.accepted ? "File review passed" : "File review needs attention"),
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
  const projectState = workflow.project_state || {};
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
  const evidenceGapDraft = context.evidenceGapDraft || null;
  const readinessChecks = (trace.readiness_checks || trace.carrier_chain || []).slice(0, 8);
  const graphSummaries = (trace.graph_summaries || trace.graph_carriers || []).slice(0, 8);
  const preflightReceipt = trace.preflight_receipt || trace.loop_admission || {};
  const pendingIntakeFields = intakeChangedFields(intakeDraft);
  const sourceImportStarted = Boolean(
    sourceImportDraft &&
      (String(sourceImportDraft.filename || "").trim() ||
        String(sourceImportDraft.created_by || "").trim() ||
        (sourceImportDraft.artifact_kind && sourceImportDraft.artifact_kind !== "project_note") ||
        String(sourceImportDraft.body || "").trim())
  );
  const pendingEvidenceGapRefs = linesFromText((evidenceGapDraft && evidenceGapDraft.evidence_refs_text) || "");
  const evidenceGapJustificationStarted = Boolean(
    evidenceGapDraft &&
      (String(evidenceGapDraft.reason || "").trim() ||
        pendingEvidenceGapRefs.length ||
        String(evidenceGapDraft.index || "").trim())
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
  const projectSummary = savedProjectSummaryFromContext(snapshot, projectState, workflow, report, items, receipts);
  return {
    schema: PROJECT_FILE_SCHEMA,
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
    project_summary: projectSummary,
    generated_from: snapshot.served_from === "local_api" ? "local_api_snapshot" : "static_snapshot",
    project_check_count: items.length,
    item_count: items.length,
    row_count: items.length,
    project_to_thesis_audit: projectSummary.project_to_thesis_audit || {},
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
      project_state: projectState,
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
            artifact_kind: sourceImportDraft.artifact_kind || "project_note",
            created_by: sourceImportDraft.created_by || "",
            body_chars: String(sourceImportDraft.body || "").length,
            evidence_gap: sourceImportDraft.evidence_gap || null
          }
        : null,
      pending_evidence_gap_justification: evidenceGapJustificationStarted
        ? {
            status: "pending_unsaved",
            index: evidenceGapDraft.index || "",
            reason: evidenceGapDraft.reason || "",
            evidence_refs: pendingEvidenceGapRefs
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
      updated_fields: receipt.updated_fields || [],
      project_file_inventory_count: receipt.project_file_inventory_count,
      project_file_previewable_count: receipt.project_file_previewable_count,
      project_file_missing_count: receipt.project_file_missing_count
    }))
  };
}

function caseFileSummary(snapshot, receiptHistory, caseFile) {
  const blocker = activeBlocker((snapshot && snapshot.rows) || []);
  const receipts = ((receiptHistory && receiptHistory.receipts) || []).length;
  const auditCommands = caseFile ? (caseFile.audit_commands || caseFile.command_queue || []) : [];
  return [
    `Project: ${snapshot.project}`,
    `Run readiness: ${snapshot.display_readiness || displayText(snapshot.readiness)}`,
    `Report: ${reportStatusLabel(snapshot.report_status, snapshot.display_report_status)}`,
    `Current report issue: ${blocker ? itemLabel(blocker) : "none"}`,
    `Recent saved changes: ${receipts}`,
    `commands: ${auditCommands.length}`,
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
    updated_fields: receipt.updated_fields || [],
    project_file_inventory_count: receipt.project_file_inventory_count,
    project_file_previewable_count: receipt.project_file_previewable_count,
    project_file_missing_count: receipt.project_file_missing_count
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
    project_summary: caseFile.project_summary || {},
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
      title: "Select a review point",
      note: "Select a review point before saving a next step.",
      evidence: "No review point selected.",
      command: ""
    };
  }

  const rowName = itemLabel(row);
  const status = itemStatus(row);
  const evidence = firstEvidenceText(row);
  const command = row.command || "";
  const warning = row.warning ? ` Warning: ${row.warning}.` : "";
  const reportBlocked = (row.label === "Report readiness" || row.label === "Report support") && snapshot.report_status === "blocked";
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
      title: "Resolve this point",
      note: `Resolve ${rowName} before relying on this project. Inspect ${evidence}.${warning}${command ? " Use the matching project step to rerun when ready." : ""}`.trim(),
      evidence,
      command
    };
  }

  if (row.label === "Run readiness" || row.label === "Preflight" || /ready|available/.test(row.status)) {
    return {
      action: command ? "ready_to_run" : "next_step",
      title: command ? "Run the project step" : "Keep this point as evidence",
      note: command
        ? `Use the Runs area for ${rowName}; keep the command available if you need to debug.`
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

function canPreviewEvidence(item) {
  if (!["file", "source", "evidence", "receipt", "review"].includes(item.type)) return false;
  const value = String(item.value || "");
  if (!isPreviewableRepoPath(value) || !value.includes("/")) return false;
  const filename = value.split("/").pop() || "";
  return filename.includes(".");
}

function fileRoleLabel(path) {
  const text = String(path || "").toLowerCase();
  if (text.includes("thesis.md")) return "Thesis";
  if (text.endsWith("/current_iteration.md")) return "Current draft";
  if (text.endsWith("/test_model.py")) return "Project test";
  if (text.endsWith("_intake.json") || text.endsWith("/intake.json")) return "Project brief";
  if (text.endsWith("/source_index.json")) return "File index";
  if (text.endsWith("/source_index_receipt.json")) return "File-index history";
  if (text.includes("/source_notes/")) return "Source note";
  if (text.includes("evidence_fetch") || text.includes("forensic_workbench_evidence_fetches")) return "Evidence fetch";
  if (text.endsWith("/evidence_gap_resolutions.json")) return "Evidence-gap history";
  if (text.includes("evidence_gap")) return "Evidence gap";
  if (text.includes("compiled_evidence") || text.endsWith("/evidence.txt") || text.includes("/evidence")) return "Evidence";
  if (text.endsWith("source_health.json")) return "File and evidence warnings";
  if (text.endsWith("shadow_recommendations.json")) return "Suggested next moves";
  if (text.includes("/action_intelligence/")) return "Action guidance";
  if (text.endsWith("_packet.json")) return "Project launch bundle";
  if (text.includes("/raw/")) return "Source";
  if (text.includes("latest_information_yield")) return "Truth-yield signal";
  if (text.includes("latest_eval_results") || text.includes("eval_history") || text.includes("run_history") || text.includes("iteration_telemetry")) return "Run results";
  if (text.includes("cold_shot_runs")) return "Run setup choices";
  if (text.includes("post_run_synthesis_attempts")) return "Report synthesis attempts";
  if (text.includes("probability_dag")) return "Probability model";
  if (text.includes("derived_constraints") || text.includes("axiom")) return "Axioms and constraints";
  if (text.startsWith("rubrics/")) return "Scoring guide";
  if (text.includes("forensic_workbench_project_file")) return "Saved project file";
  if (text.includes("receipt") || text.includes("forensic_workbench_")) return "Saved history";
  if (text.includes("report")) return "Report";
  if (text.startsWith("docs/") || text.endsWith("readme.md") || text.endsWith("priority_roadmap.md")) return "Guide";
  if (text.endsWith(".json")) return "Project data";
  return "Project file";
}

function filePreviewKindLabel(filePreview) {
  return displayText((filePreview && filePreview.display_kind) || fileRoleLabel(filePreview && filePreview.path));
}

function fileFormatLabel(path) {
  const text = String(path || "").toLowerCase();
  if (text.endsWith(".md")) return "Markdown";
  if (text.endsWith(".json") || text.endsWith(".jsonl")) return text.endsWith(".jsonl") ? "JSON lines" : "JSON";
  if (text.endsWith(".txt")) return "Text";
  if (text.endsWith(".csv")) return "CSV";
  if (text.endsWith(".yaml") || text.endsWith(".yml")) return "YAML";
  return "Text";
}

function fileViewerGuide(path) {
  const role = fileRoleLabel(path);
  const guides = {
    Thesis: {
      lookFor: "The claim, assumptions, and the next thing that could change the answer.",
      useFor: "Decide whether the evidence and scoring guide match the project.",
      next: "Open Evidence & gaps, then Run if support is ready."
    },
    "Current draft": {
      lookFor: "The latest thesis draft, rival hypotheses, discriminator, observables, limits, and demotion triggers.",
      useFor: "Understand what the last run produced before deciding whether to review, rerun, or save a next step.",
      next: "Open the latest run result, evidence gaps, or project test behind this draft."
    },
    "Project test": {
      lookFor: "Executable discriminators, constants, assertions, and future counterexample cases.",
      useFor: "Check whether the thesis has a runnable test instead of only prose.",
      next: "Open the scoring guide or run result to see how this check affected the verdict."
    },
    Evidence: {
      lookFor: "The source, what it supports, and what remains missing.",
      useFor: "Check whether the thesis is backed by inspectable material.",
      next: "Repair gaps or check report readiness again."
    },
    "Evidence fetch": {
      lookFor: "Which evidence gap was searched, which backend ran, how many sources were accepted, and why any fetch failed.",
      useFor: "Decide whether to switch search backend, justify the gap, or rerun fetch.",
      next: "Open Settings if the backend failed, or open Evidence gaps to justify the remaining gap."
    },
    "Project brief": {
      lookFor: "The thesis, source paths, evidence paths, and declared limits.",
      useFor: "Check what the project is asking the system to test.",
      next: "Edit the project brief if the thesis or file links are wrong."
    },
    "Evidence gap": {
      lookFor: "The missing support, the reason it matters, and the proposed repair.",
      useFor: "Turn a vague weakness into a specific next step.",
      next: "Save the repair note or fetch the needed evidence."
    },
    "Evidence-gap history": {
      lookFor: "Which gap was justified, why, which evidence summaries backed it, and which gap file it came from.",
      useFor: "Check whether a missing-evidence warning was actually resolved or only noted.",
      next: "Open the backing evidence file or the original gap file."
    },
    "File and evidence warnings": {
      lookFor: "Warnings that affect whether suggested next moves are diagnostic, stale, or ready to use.",
      useFor: "Repair project files, evidence, run-history, or work-log state before relying on a suggestion.",
      next: "Open the backing file, then save a repair, deferral, or next-step note."
    },
    "Suggested next moves": {
      lookFor: "The recommendation, why it was suggested, what authority it has, and which files support it.",
      useFor: "Decide whether a suggestion is usable now, diagnostic only, or waiting on missing evidence.",
      next: "Open backing evidence before staging the suggestion as the project next step."
    },
    "Action guidance": {
      lookFor: "Suggested actions, file/evidence warnings, backing evidence, and the boundary between advice and project state.",
      useFor: "Understand why the workbench suggests a repair, deferral, or next check.",
      next: "Open the warning file or recommendation file behind the action."
    },
    "Project launch bundle": {
      lookFor: "The thesis, original files, evidence summaries, expected run command, limits, and what would change the answer.",
      useFor: "Check what was admitted into a run before trusting its score.",
      next: "Open the evidence file, raw sources, or latest run result."
    },
    Source: {
      lookFor: "Original material and collection notes before they are compiled into evidence.",
      useFor: "Verify that the evidence map is grounded in a real source.",
      next: "Attach or classify the source if it is not yet in the project brief."
    },
    "File index": {
      lookFor: "The raw project files, notes, file purposes, hashes, and freshness status.",
      useFor: "Check whether the project is grounded in the expected files before reviewing evidence.",
      next: "Open the referenced raw file or note, then repair any missing or stale file."
    },
    "File-index history": {
      lookFor: "When the file index was refreshed, which files were scanned, and what changed.",
      useFor: "Confirm that file status was rebuilt from the current local files.",
      next: "Open the file index or the changed file."
    },
    "Source note": {
      lookFor: "The source summary, stable facts, claims to test, gaps, conflicts, and backing raw source.",
      useFor: "Decide what this source can safely support before reading compiled evidence.",
      next: "Open the raw source or the evidence gap that still needs repair."
    },
    Report: {
      lookFor: "Claims, cited support, stale sections, and unsupported conclusions.",
      useFor: "Decide whether the report can be used or needs more support.",
      next: "Open Report and resolve the first support issue."
    },
    "Saved work": {
      lookFor: "What changed, where it was written, and which inputs were used.",
      useFor: "Confirm the workbench changed only the expected files.",
      next: "Copy the path or open the changed file."
    },
    "Run results": {
      lookFor: "Scores, weak points, failed assumptions, learned constraints, and next actions.",
      useFor: "Understand what the last run changed about the project.",
      next: "Open backing files or save the next step."
    },
    "Truth-yield signal": {
      lookFor: "The latest continue, refresh, pivot, or underidentified decision and the reason behind it.",
      useFor: "Decide whether another run is likely to teach something or whether the project should narrow, pivot, or repair evidence first.",
      next: "Save the run-control lesson as the next step, or open the run result that produced it."
    },
    "Run setup choices": {
      lookFor: "Which optional run helpers were eligible, selected, skipped, or only advisory.",
      useFor: "Check why the run started from the inputs it used instead of another seed or helper.",
      next: "Open the run result or launch bundle to compare setup choices against the final score."
    },
    "Report synthesis attempts": {
      lookFor: "Whether post-run report synthesis was attempted, skipped, and why.",
      useFor: "Decide whether the report can be refreshed from run results or whether more scored iterations are needed.",
      next: "Open report readiness or run history before refreshing report inputs."
    },
    "Probability model": {
      lookFor: "The outcome probability, supporting nodes, watch signals, and edge weights.",
      useFor: "Understand why the run believes one explanation is stronger than its rivals.",
      next: "Open the run result, evidence gap, or source tied to the weakest node."
    },
    "Axioms and constraints": {
      lookFor: "Assumptions the run treated as constraints and the files backing them.",
      useFor: "Check whether generated constraints are useful or need review.",
      next: "Open the listed backing files before relying on the constraint."
    },
    "Scoring guide": {
      lookFor: "The criteria, scoring scale, and failure conditions.",
      useFor: "Check whether the project is being reviewed against the right standard.",
      next: "Edit or replace the scoring guide if it rewards the wrong thing."
    },
    Guide: {
      lookFor: "The concrete workflow, commands, and expected file changes.",
      useFor: "Learn how to do the next project step without leaving the workbench.",
      next: "Return to the project area and run the matching action."
    },
    "Project data": {
      lookFor: "Structured project state, paths, scores, and generated metadata.",
      useFor: "Debug project state without guessing from the UI.",
      next: "Use the page action rather than editing raw JSON unless needed."
    },
    "Project file": {
      lookFor: "Project notes, backing state, or saved artifacts.",
      useFor: "Understand the file before choosing the next action.",
      next: "Copy the path or save a review note."
    }
  };
  return guides[role] || guides["Project file"];
}



function topJsonKeys(value) {
  if (Array.isArray(value)) {
    const keys = new Set();
    value.slice(0, 5).forEach((item) => {
      if (item && typeof item === "object" && !Array.isArray(item)) {
        Object.keys(item).slice(0, 8).forEach((key) => keys.add(key));
      }
    });
    return Array.from(keys).slice(0, 10);
  }
  if (value && typeof value === "object") return Object.keys(value).slice(0, 10);
  return [];
}

function collectJsonStringValues(value, keyPattern, limit = 6) {
  const found = [];
  const seen = new Set();
  const visit = (item, depth = 0) => {
    if (found.length >= limit || depth > 5 || item === null || item === undefined) return;
    if (Array.isArray(item)) {
      item.slice(0, 20).forEach((entry) => visit(entry, depth + 1));
      return;
    }
    if (typeof item !== "object") return;
    Object.entries(item).forEach(([key, child]) => {
      if (found.length >= limit) return;
      if (keyPattern.test(key) && typeof child === "string" && child.trim()) {
        const valueText = child.trim();
        if (!seen.has(valueText)) {
          seen.add(valueText);
          found.push(valueText);
        }
      }
      if (keyPattern.test(key) && Array.isArray(child)) {
        child.forEach((entry) => {
          if (found.length >= limit || typeof entry !== "string" || !entry.trim()) return;
          const valueText = entry.trim();
          if (!seen.has(valueText)) {
            seen.add(valueText);
            found.push(valueText);
          }
        });
      }
      visit(child, depth + 1);
    });
  };
  visit(value);
  return found;
}

function splitCsvLine(value) {
  const cells = [];
  let current = "";
  let quoted = false;
  const chars = String(value || "");
  for (let index = 0; index < chars.length; index += 1) {
    const char = chars[index];
    if (char === '"' && chars[index + 1] === '"') {
      current += '"';
      index += 1;
      continue;
    }
    if (char === '"') {
      quoted = !quoted;
      continue;
    }
    if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }
  cells.push(current.trim());
  return cells;
}

function fileViewerInsights(filePreview) {
  if (!filePreview) return [];
  const path = filePreview.path || "";
  const text = filePreview.text || "";
  const role = filePreviewKindLabel(filePreview);
  const format = filePreview.format || fileFormatLabel(path);
  const lines = text.split(/\r?\n/);
  const insights = [];
  if (format === "Markdown") {
    const headings = lines
      .map((line) => line.match(/^(#{1,4})\s+(.+?)\s*#*$/))
      .filter(Boolean)
      .map((match) => ({ level: match[1].length, text: match[2].trim() }))
      .slice(0, 8);
    if (headings.length) {
      insights.push({
        title: "Sections",
        body: headings.map((item) => `${"  ".repeat(Math.max(0, item.level - 1))}${item.text}`)
      });
    }
    const bullets = lines
      .map((line) => line.match(/^\s*[-*]\s+(.+)/))
      .filter(Boolean)
      .map((match) => match[1].trim())
      .slice(0, 5);
    if (bullets.length) insights.push({ title: "First bullets", body: bullets });
  } else if (format === "JSON" || format === "JSON lines") {
    const parsed = parseJsonLikeText(text);
    const savedProject = savedProjectSummaryFromPreview(filePreview);
    const launchBundleSummary = projectLaunchBundleSummaryFromPreview(filePreview);
    const intakeSummary = launchBundleSummary ? null : projectIntakeSummaryFromPreview(filePreview);
    const scoringGuideSummary = scoringGuideSummaryFromPreview(filePreview);
    const sourceIndexSummary = sourceIndexSummaryFromPreview(filePreview);
    const sourceNoteSummary = sourceNoteSummaryFromPreview(filePreview);
    const evidenceGapResolutionSummary = evidenceGapResolutionSummaryFromPreview(filePreview);
    const runResultSummary = runResultSummaryFromPreview(filePreview);
    const probabilityModelSummary = probabilityModelSummaryFromPreview(filePreview);
    const evidenceGapSummary = evidenceGapSummaryFromPreview(filePreview);
    const evidenceFetchSummary = evidenceFetchSummaryFromPreview(filePreview);
    const evidencePacketSummary = evidencePacketSummaryFromPreview(filePreview);
    const evidenceProvenanceSummary = evidenceProvenanceSummaryFromPreview(filePreview);
    const reportSupportSummary = reportSupportSummaryFromPreview(filePreview);
    const sourceWarningSummary = sourceWarningSummaryFromPreview(filePreview);
    const actionRecommendationSummary = actionRecommendationSummaryFromPreview(filePreview);
    const derivedConstraintSummary = derivedConstraintSummaryFromPreview(filePreview);
    const receiptLedgerSummary = receiptLedgerSummaryFromPreview(filePreview);
    const runSetupDecisionSummary = runSetupDecisionSummaryFromPreview(filePreview);
    const reportSynthesisAttemptSummary = reportSynthesisAttemptSummaryFromPreview(filePreview);
    if (savedProject) {
      const charter = savedProject.charter && typeof savedProject.charter === "object" ? savedProject.charter : {};
      const reportAuthority = savedProject.report_authority && typeof savedProject.report_authority === "object" ? savedProject.report_authority : {};
      const recentChanges = savedProject.recent_changes && typeof savedProject.recent_changes === "object" ? savedProject.recent_changes : {};
      const projectAudit = savedProject.project_to_thesis_audit && typeof savedProject.project_to_thesis_audit === "object"
        ? savedProject.project_to_thesis_audit
        : {};
      const latestChange = recentChanges.latest_source_or_evidence_change && typeof recentChanges.latest_source_or_evidence_change === "object"
        ? recentChanges.latest_source_or_evidence_change
        : {};
      const projectObjectFailedChecks = Array.isArray(savedProject.project_object_failed_checks)
        ? savedProject.project_object_failed_checks.filter(Boolean)
        : [];
      const firstProjectObjectFailure = projectObjectFailedChecks[0] && typeof projectObjectFailedChecks[0] === "object"
        ? projectObjectFailedChecks[0]
        : {};
      const summaryLines = [
        charter.status || charter.file ? `Charter: ${displayText(charter.status || "recorded")}` : "",
        savedProject.thesis ? `Thesis: ${shortText(savedProject.thesis, 140)}` : "",
        savedProject.next_action && savedProject.next_action.label ? `Next: ${displayText(savedProject.next_action.label)}` : "",
        savedProject.project_check_count ? `Things to review: ${savedProject.project_check_count}` : "",
        projectAudit.summary ? shortText(projectAudit.summary, 140) : "",
        savedProject.recent_receipts && savedProject.recent_receipts.length ? `Recent saved changes: ${savedProject.recent_receipts.length}` : "",
        savedProject.project_object_ok === false
          ? `Project object: ${displayText(firstProjectObjectFailure.label || firstProjectObjectFailure.id || "needs review")}`
          : savedProject.project_object_ok === true
            ? "Project object: coherent"
            : "",
        latestChange.summary ? `Latest change: ${shortText(latestChange.summary, 140)}` : "",
        reportAuthority.first_forbidden_upgrade ? `Do not claim: ${shortText(reportAuthority.first_forbidden_upgrade, 120)}` : "",
        savedProject.file_inventory ? `Files: ${savedProject.file_inventory.item_count || 0} total, ${savedProject.file_inventory.previewable_count || 0} previewable` : ""
      ].filter(Boolean);
      if (summaryLines.length) insights.push({ title: "Project summary", body: summaryLines });
    }
    if (launchBundleSummary) {
      const launchLines = [
        launchBundleSummary.claim ? `Claim: ${shortText(launchBundleSummary.claim, 150)}` : "",
        launchBundleSummary.executionBoundary ? `Boundary: ${displayText(launchBundleSummary.executionBoundary)}` : "",
        `Sources: ${launchBundleSummary.sourceRefs.length}`,
        `Evidence: ${launchBundleSummary.evidenceRefs.length}`,
        launchBundleSummary.nextFalsifier ? `Change if: ${shortText(launchBundleSummary.nextFalsifier, 120)}` : ""
      ].filter(Boolean);
      if (launchLines.length) insights.push({ title: "Launch bundle", body: launchLines });
    }
    if (intakeSummary) {
      const intakeLines = [
        intakeSummary.claim ? `Thesis: ${shortText(intakeSummary.claim, 140)}` : "",
        intakeSummary.nextFalsifier ? `Change if: ${shortText(intakeSummary.nextFalsifier, 120)}` : "",
        `Sources: ${intakeSummary.sourceRefs.length}`,
        `Evidence: ${intakeSummary.evidenceRefs.length}`
      ].filter(Boolean);
      if (intakeLines.length) insights.push({ title: "Project setup", body: intakeLines });
    }
    if (scoringGuideSummary) {
      const firstDimension = scoringGuideSummary.dimensions[0] || {};
      const guideLines = [
        scoringGuideSummary.project ? `Project: ${displayText(scoringGuideSummary.project)}` : "",
        scoringGuideSummary.hasDimensions
          ? `Dimensions: ${scoringGuideSummary.dimensions.length}; weight total ${scoringGuideSummary.totalWeight}`
          : "Missing dimension list",
        firstDimension.name ? `First dimension: ${firstDimension.name}${firstDimension.weight !== undefined ? ` (${firstDimension.weight})` : ""}` : "",
        scoringGuideSummary.penaltyRows[0] ? `Penalty: ${shortText(scoringGuideSummary.penaltyRows[0].name, 120)}` : ""
      ].filter(Boolean);
      if (guideLines.length) insights.push({ title: "Scoring guide", body: guideLines });
    }
    if (sourceIndexSummary) {
      const firstSource = sourceIndexSummary.sources[0] || {};
      const sourceLines = [
        `Sources: ${sourceIndexSummary.sourceCount || sourceIndexSummary.sources.length}`,
        firstSource.path ? `First source: ${firstSource.path}` : "",
        firstSource.type ? `Type: ${displayText(firstSource.type)}` : "",
        sourceIndexSummary.generatedOn ? `Updated: ${sourceIndexSummary.generatedOn}` : ""
      ].filter(Boolean);
      if (sourceLines.length) insights.push({ title: "Source index", body: sourceLines });
    }
    if (sourceNoteSummary) {
      const noteLines = [
        sourceNoteSummary.sourceId ? `Source: ${sourceNoteSummary.sourceId}` : "",
        sourceNoteSummary.sourceType ? `Type: ${displayText(sourceNoteSummary.sourceType)}` : "",
        sourceNoteSummary.summary ? `Summary: ${shortText(sourceNoteSummary.summary, 150)}` : "",
        `Claims to test: ${sourceNoteSummary.claimsToTest.length}`,
        `Gaps: ${sourceNoteSummary.gaps.length}`
      ].filter(Boolean);
      if (noteLines.length) insights.push({ title: "Source note", body: noteLines });
    }
    if (evidenceGapResolutionSummary) {
      const latestResolution = evidenceGapResolutionSummary.resolutions[0] || {};
      const resolutionLines = [
        `Justifications: ${evidenceGapResolutionSummary.resolutionCount || evidenceGapResolutionSummary.resolutions.length}`,
        latestResolution.target ? `Latest target: ${latestResolution.target}` : "",
        latestResolution.reason ? `Reason: ${shortText(latestResolution.reason, 150)}` : "",
        evidenceGapResolutionSummary.updatedAt ? `Updated: ${evidenceGapResolutionSummary.updatedAt}` : ""
      ].filter(Boolean);
      if (resolutionLines.length) insights.push({ title: "Evidence-gap history", body: resolutionLines });
    }
    if (runResultSummary) {
      const runLines = [
        runResultSummary.score !== undefined && runResultSummary.score !== null ? `Score: ${runResultSummary.score}` : "",
        runResultSummary.weakestPoint ? `Weakest point: ${shortText(runResultSummary.weakestPoint, 150)}` : "",
        `Evidence gaps: ${runResultSummary.evidenceGapCount || 0}`,
        `Run-learned assumptions: ${runResultSummary.derivedConstraintCount || 0}`,
        runResultSummary.judgeModel ? `Review model: ${displayText(runResultSummary.judgeModel)}` : ""
      ].filter(Boolean);
      if (runLines.length) insights.push({ title: "Run result", body: runLines });
    }
    if (probabilityModelSummary) {
      const topNode = probabilityModelSummary.topNodes[0] || {};
      const probabilityLines = [
        probabilityModelSummary.outcome.label
          ? `Outcome: ${shortText(probabilityModelSummary.outcome.label, 150)} (${displayText(probabilityModelSummary.outcome.probability)})`
          : "",
        `Nodes: ${probabilityModelSummary.nodes.length}`,
        `Edges: ${probabilityModelSummary.edges.length}`,
        topNode.label ? `Strongest node: ${shortText(topNode.label, 120)} (${displayText(topNode.probability)})` : ""
      ].filter(Boolean);
      if (probabilityLines.length) insights.push({ title: "Probability model", body: probabilityLines });
    }
    if (evidenceGapSummary) {
      const gapLines = [
        evidenceGapSummary.weakestPoint ? `Weakest point: ${shortText(evidenceGapSummary.weakestPoint, 140)}` : "",
        `Active gaps: ${evidenceGapSummary.gaps.length}`,
        evidenceGapSummary.firstGap ? `First gap: ${shortText(evidenceGapSummary.firstGap.target || evidenceGapSummary.firstGap.description || "Evidence gap", 120)}` : ""
      ].filter(Boolean);
      if (gapLines.length) insights.push({ title: "Evidence gaps", body: gapLines });
    }
    if (evidenceFetchSummary) {
      const fetchLines = [
        evidenceFetchSummary.backend ? `Backend: ${displayText(evidenceFetchSummary.backend)}` : "",
        evidenceFetchSummary.attempted !== undefined || evidenceFetchSummary.accepted !== undefined
          ? `Accepted: ${evidenceFetchSummary.accepted ?? 0}/${evidenceFetchSummary.attempted ?? 0}`
          : "",
        evidenceFetchSummary.failureText ? `Reason: ${evidenceFetchSummary.failureText}` : "",
        evidenceFetchSummary.hint ? `Next: ${evidenceFetchSummary.hint}` : "",
        evidenceFetchSummary.firstTarget ? `First target: ${shortText(evidenceFetchSummary.firstTarget, 120)}` : ""
      ].filter(Boolean);
      if (fetchLines.length) insights.push({ title: "Fetch outcome", body: fetchLines });
    }
    if (evidencePacketSummary) {
      const packetLines = [
        evidencePacketSummary.summary ? shortText(evidencePacketSummary.summary, 180) : "",
        `${evidencePacketSummary.facts.length} sampled facts / ${evidencePacketSummary.claimsToTest.length} tests / ${evidencePacketSummary.gaps.length} gaps`,
        evidencePacketSummary.claimsToTest[0] && evidencePacketSummary.claimsToTest[0].claim
          ? `Next test: ${shortText(evidencePacketSummary.claimsToTest[0].claim, 140)}`
          : ""
      ].filter(Boolean);
      if (packetLines.length) insights.push({ title: "Evidence bundle", body: packetLines });
    }
    if (evidenceProvenanceSummary) {
      const provenanceLines = [
        evidenceProvenanceSummary.sourceCount !== undefined ? `Sources: ${evidenceProvenanceSummary.sourceCount}` : "",
        evidenceProvenanceSummary.gapCount !== undefined ? `Evidence gaps: ${evidenceProvenanceSummary.gapCount}` : "",
        evidenceProvenanceSummary.packetPath ? `Evidence bundle: ${evidenceProvenanceSummary.packetPath}` : "",
        evidenceProvenanceSummary.replayPath ? `Replay: ${evidenceProvenanceSummary.replayPath}` : ""
      ].filter(Boolean);
      if (provenanceLines.length) insights.push({ title: "Evidence build", body: provenanceLines });
    }
    if (reportSupportSummary) {
      const reportLines = [
        reportSupportSummary.status ? `Status: ${displayText(reportSupportSummary.status)}` : "",
        reportSupportSummary.allowed[0] && reportSupportSummary.allowed[0].label
          ? `Next: ${shortText(reportSupportSummary.allowed[0].label, 150)}`
          : "",
        reportSupportSummary.hardestConclusion.claim ? `Hardest claim: ${shortText(reportSupportSummary.hardestConclusion.claim, 130)}` : "",
        reportSupportSummary.claimCount !== undefined ? `Supported claims: ${reportSupportSummary.claimCount}` : ""
      ].filter(Boolean);
      if (reportLines.length) insights.push({ title: "Report readiness", body: reportLines });
    }
    if (sourceWarningSummary) {
      const firstIssue = sourceWarningSummary.issues[0] || {};
      const warningLines = [
        `Warnings: ${sourceWarningSummary.issueCount || sourceWarningSummary.issues.length}`,
        firstIssue.label ? `First warning: ${firstIssue.label}` : "",
        firstIssue.action ? `Do next: ${shortText(firstIssue.action, 150)}` : "",
        firstIssue.evidenceRefs && firstIssue.evidenceRefs[0] ? `Backing file: ${firstIssue.evidenceRefs[0]}` : ""
      ].filter(Boolean);
      if (warningLines.length) insights.push({ title: "File and evidence warnings", body: warningLines });
    }
    if (actionRecommendationSummary) {
      const firstRecommendation = actionRecommendationSummary.recommendations[0] || {};
      const recommendationLines = [
        `Suggestions: ${actionRecommendationSummary.recommendations.length}`,
        firstRecommendation.label ? `First suggestion: ${firstRecommendation.label}` : "",
        firstRecommendation.authority ? `Authority: ${firstRecommendation.authority}` : "",
        firstRecommendation.rationale ? `Why: ${shortText(firstRecommendation.rationale, 150)}` : ""
      ].filter(Boolean);
      if (recommendationLines.length) insights.push({ title: "Suggested next moves", body: recommendationLines });
    }
    if (derivedConstraintSummary) {
      const constraintLines = [
        `${derivedConstraintSummary.confirmedCount || 0} confirmed / ${derivedConstraintSummary.provisionalCount || 0} provisional`,
        derivedConstraintSummary.provisional[0] && derivedConstraintSummary.provisional[0].constraint
          ? `First provisional: ${shortText(derivedConstraintSummary.provisional[0].constraint, 150)}`
          : "",
        derivedConstraintSummary.updatedOn ? `Updated: ${derivedConstraintSummary.updatedOn}` : ""
      ].filter(Boolean);
      if (constraintLines.length) insights.push({ title: "Run-learned assumptions", body: constraintLines });
    }
    if (receiptLedgerSummary) {
      const receiptLines = [
        `Saved changes: ${receiptLedgerSummary.receiptCount}`,
        receiptLedgerSummary.latestStatus ? `Latest status: ${displayText(receiptLedgerSummary.latestStatus)}` : "",
        receiptLedgerSummary.latestTitle ? `Latest item: ${displayText(receiptLedgerSummary.latestTitle)}` : "",
        receiptLedgerSummary.latestArtifacts[0] ? `Changed file: ${receiptLedgerSummary.latestArtifacts[0]}` : ""
      ].filter(Boolean);
      if (receiptLines.length) insights.push({ title: "Saved history", body: receiptLines });
    }
    if (runSetupDecisionSummary) {
      const setupLines = [
        `Run choices: ${runSetupDecisionSummary.decisionCount}`,
        runSetupDecisionSummary.latestEvent ? `Latest: ${displayText(runSetupDecisionSummary.latestEvent)}` : "",
        `Eligible helpers: ${runSetupDecisionSummary.eligibleCount}`,
        `Selected helpers: ${runSetupDecisionSummary.selectedFamilies.length}`,
        runSetupDecisionSummary.routerReason ? `Reason: ${displayText(runSetupDecisionSummary.routerReason)}` : ""
      ].filter(Boolean);
      if (setupLines.length) insights.push({ title: "Run setup choices", body: setupLines });
    }
    if (reportSynthesisAttemptSummary) {
      const synthesisLines = [
        `Records: ${reportSynthesisAttemptSummary.recordCount}`,
        `Latest attempts: ${reportSynthesisAttemptSummary.attemptsCount}`,
        reportSynthesisAttemptSummary.note ? `Reason: ${displayText(reportSynthesisAttemptSummary.note)}` : "",
        reportSynthesisAttemptSummary.latestTimestamp ? `Updated: ${reportSynthesisAttemptSummary.latestTimestamp}` : ""
      ].filter(Boolean);
      if (synthesisLines.length) insights.push({ title: "Report synthesis attempts", body: synthesisLines });
    }
    if (format === "JSON lines") {
      const runHistorySummary = runHistorySummaryFromPreview(filePreview);
      if (runHistorySummary) {
        const lines = [
          `Records: ${runHistorySummary.totalRecords}`,
          runHistorySummary.latestScore !== null ? `Latest score: ${runHistorySummary.latestScore}` : "",
          runHistorySummary.bestScore !== null ? `Best score: ${runHistorySummary.bestScore}` : "",
          runHistorySummary.scoreDelta !== null ? `Change: ${runHistorySummary.scoreDelta >= 0 ? "+" : ""}${runHistorySummary.scoreDelta}` : "",
          runHistorySummary.latestWeakestPoint ? `Latest weak point: ${shortText(runHistorySummary.latestWeakestPoint, 140)}` : ""
        ].filter(Boolean);
        if (lines.length) insights.push({ title: "Run history", body: lines });
      }
      const records = jsonLineRecordsFromPreview(filePreview, 4);
      const events = records
        .map((record) => [record.record_type || record.event || "record", record.run_id ? `run ${record.run_id}` : "", record.run_exit_reason || record.status || ""].filter(Boolean).join(" / "))
        .filter(Boolean);
      if (events.length) insights.push({ title: "Events", body: events });
    }
    const keys = topJsonKeys(parsed);
    if (keys.length) insights.push({ title: "Top fields", body: keys });
    const changedPaths = collectJsonStringValues(parsed, /(^|_)(path|paths|file|files|receipt|receipts|latest_path|receipt_path|source_path|write_paths)$/i, 8);
    if (changedPaths.length) insights.push({ title: role === "Saved work" ? "Files named by saved work" : "Referenced files", body: changedPaths });
    const statuses = collectJsonStringValues(parsed, /(^|_)(status|decision|action|label|summary)$/i, 6);
    if (statuses.length) insights.push({ title: "State", body: statuses });
  } else if (format === "CSV") {
    const nonEmpty = lines.filter((line) => line.trim()).slice(0, 6);
    if (nonEmpty.length) {
      const columns = splitCsvLine(nonEmpty[0]).slice(0, 10);
      if (columns.length) insights.push({ title: "Columns", body: columns });
      if (nonEmpty[1]) insights.push({ title: "First record", body: splitCsvLine(nonEmpty[1]).slice(0, 10) });
    }
  } else {
    const meaningful = linesFromText(text).slice(0, 5);
    if (meaningful.length) insights.push({ title: "First lines", body: meaningful });
  }
  const referencedPaths = Array.isArray(filePreview.referenced_paths)
    ? filePreview.referenced_paths.filter(Boolean).slice(0, 8)
    : [];
  if (referencedPaths.length && !insights.some((item) => item.title === "Referenced files")) {
    const referencedItems = filePreviewReferencedItems(filePreview, 8);
    insights.push({ title: "Related files", body: referencedItems.length ? referencedItems : referencedPaths });
  }
  if (filePreview.truncated) {
    insights.push({ title: "Limit", body: ["Preview is truncated. Use the path to inspect the full file locally."] });
  }
  return insights.slice(0, 4);
}








function filePreviewReferencedItems(filePreview, limit = 10) {
  const items = Array.isArray(filePreview && filePreview.referenced_items)
    ? filePreview.referenced_items.filter((item) => item && item.path)
    : [];
  if (items.length) return items.slice(0, limit);
  const paths = Array.isArray(filePreview && filePreview.referenced_paths)
    ? filePreview.referenced_paths.filter(Boolean)
    : [];
  return paths.slice(0, limit).map((path) => ({
    path,
    display_kind: fileRoleLabel(path),
    format: fileFormatLabel(path),
    label: `${fileRoleLabel(path)}: ${sourceBasename(path)}`
  }));
}





function ProjectIdentity({ snapshot }) {
  const sourceLabel = snapshot.served_from === "local_api" ? "live server" : "saved file";
  const rows = snapshot.rows || [];
  const claimRow = rowByLabel(rows, "Bounded claim");
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const ready = sourceRow && evidenceRow && sourceRow.kind !== "attention" && evidenceRow.kind !== "attention";
  const stateWord = ready ? "Evidence ready" : sourceRow || evidenceRow ? "Evidence still coming together" : "No evidence yet";
  return h(
    MText,
    { className: "project-identity", c: "dimmed", fz: "sm", mt: 4 },
    `${stateWord} · ${sourceLabel === "saved file" ? "loaded from a saved file" : "live from your local server"}`
  );
}


function pendingEditDestination(item) {
  const text = String(item || "").toLowerCase();
  if (text.includes("scoring guide")) return ["run", "Ready to run", "Open scoring guide"];
  if (text.includes("source import")) return ["sources", "Add file", "Open new file draft"];
  if (text.includes("source file")) return ["sources", "Edit file", "Open file editor"];
  return ["sources", "Project brief", "Open project brief"];
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
        h(
          "div",
          null,
          h("span", { className: "eyebrow" }, "Unsaved edits"),
          h("h2", null, "Save or discard before continuing"),
          h("p", null, `${prompt.action} would discard these drafts.`)
        ),
        h(ModalNavControls, { label: "Dialog history" })
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

function ModalNavControls({ canGoBack = false, canGoForward = false, onBack, onForward, label = "Modal history" }) {
  return h(
    "div",
    { className: "modal-nav-controls", "aria-label": label },
    h(
      "button",
      {
        type: "button",
        className: "modal-nav-button",
        disabled: !canGoBack,
        onClick: canGoBack && onBack ? onBack : undefined,
        title: canGoBack ? "Go back (Alt+Left)" : "Nothing to go back to"
      },
      "Back"
    ),
    h(
      "button",
      {
        type: "button",
        className: "modal-nav-button",
        disabled: !canGoForward,
        onClick: canGoForward && onForward ? onForward : undefined,
        title: canGoForward ? "Go forward (Alt+Right)" : "Nothing to go forward to"
      },
      "Forward"
    )
  );
}

function handleModalHistoryKey(event, modalNav) {
  if (!modalNav || !(event.altKey || event.metaKey)) return false;
  if (event.key === "ArrowLeft" && modalNav.canGoBack && modalNav.onBack) {
    event.preventDefault();
    modalNav.onBack();
    return true;
  }
  if (event.key === "ArrowRight" && modalNav.canGoForward && modalNav.onForward) {
    event.preventDefault();
    modalNav.onForward();
    return true;
  }
  return false;
}

function ProjectRunConfirmDialog({ prompt, onCancel, onConfirm }) {
  const cancelButtonRef = useRef(null);
  const allowInstructions = Boolean(prompt && prompt.allowInstructions);
  const [instructions, setInstructions] = useState("");
  useEffect(() => { setInstructions(""); }, [prompt]);
  const confirmedBoundary = (prompt && prompt.confirmedWriteBoundary) || {};
  const confirmedWritePaths = Array.isArray(confirmedBoundary.write_paths) ? confirmedBoundary.write_paths.filter(Boolean) : [];
  const noChangeBoundary = String(
    confirmedBoundary.no_change_boundary ||
      "Preview and cancellation write no files. A confirmed run can change only the listed project files."
  ).trim();
  const settings = (prompt && prompt.effectiveSettings) || {};
  const customFacts = Array.isArray(prompt && prompt.dialogFacts) ? prompt.dialogFacts.filter(Boolean) : [];
  const canConfirm = Boolean(confirmedBoundary.writes_project_files && confirmedWritePaths.length);
  const title = (prompt && prompt.dialogTitle) || "Start this project run?";
  const body = (prompt && prompt.dialogBody) || "This can call configured models and write run files under the selected project.";
  const eyebrow = (prompt && prompt.dialogEyebrow) || "Project run";
  const confirmLabel = (prompt && prompt.confirmLabel) || "Start project run";
  const ariaLabel = (prompt && prompt.ariaLabel) || "Confirm project run";
  const disabledTitle =
    (prompt && prompt.disabledTitle) ||
    "Files that may change must load before this run can start";
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
      { className: "case-run-dialog", role: "dialog", "aria-modal": "true", "aria-label": ariaLabel },
      h(
        "header",
        { className: "case-run-dialog-head" },
        h(
          "div",
          null,
          h("span", { className: "eyebrow" }, eyebrow),
          h("h2", null, title),
          h("p", null, body)
        ),
        h(ModalNavControls, { label: "Dialog history" })
      ),
      h(
        "div",
        { className: "case-run-dialog-facts" },
        customFacts.length
          ? customFacts.map((fact) =>
              h(
                "div",
                { key: `${fact.label}:${fact.value}` },
                h("span", null, fact.label),
                fact.monospace
                  ? h("code", null, fact.value || "not loaded")
                  : h("strong", null, fact.value || "not loaded")
              )
            )
          : [
              h("div", { key: "project" }, h("span", null, "Project"), h("strong", null, prompt.project || "not loaded")),
              h("div", { key: "intake" }, h("span", null, "Project brief"), h("code", null, prompt.intake || "not loaded")),
              h("div", { key: "draft" }, h("span", null, "Draft model"), h("strong", null, settings.mutator || "not loaded")),
              h("div", { key: "review" }, h("span", null, "Review model"), h("strong", null, settings.judge || "not loaded")),
              h("div", { key: "stress" }, h("span", null, "Stress-test model"), h("strong", null, settings.inverter || "none")),
              h("div", { key: "timeout" }, h("span", null, "Timeout/retries"), h("strong", null, [settings.llm_timeout_seconds ? `${settings.llm_timeout_seconds}s` : "", settings.llm_retries ? `${settings.llm_retries} retries` : ""].filter(Boolean).join(" / ") || "not loaded")),
              h("div", { key: "fallback" }, h("span", null, "Fallback"), h("strong", null, settings.model_fallback === "1" ? "allowed" : "off")),
              h("div", { key: "engine" }, h("span", null, "Run engine"), h("strong", null, settings.transport === "subscription" ? "Subscription CLI (Codex/Claude)" : "Provider API")),
              h("div", { key: "judging" }, h("span", null, "Scored by"), h("strong", null, settings.judging === "committee" ? `3-panel committee${settings.cross_family === "1" ? ", mixed models" : ""}` : "Single judge")),
              h("div", { key: "rubric" }, h("span", null, "Rubric"), h("strong", null, settings.rubric_mode === "rotating" ? "Rotating (auto-evolve)" : "Fixed")),
              h("div", { key: "files" }, h("span", null, "Files after confirm"), h("strong", null, canConfirm ? `${confirmedWritePaths.length} listed paths` : "not available"))
            ]
      ),
      h(
        "div",
        { className: "case-run-dialog-paths" },
        h("span", null, "Files that may change"),
        confirmedWritePaths.length
          ? confirmedWritePaths.map((path) => h("code", { key: path }, path))
          : h("p", null, "The server did not return write paths for this preview."),
        h("p", null, noChangeBoundary)
      ),
      !canConfirm
        ? h(
            "p",
            { className: "case-run-dialog-warning" },
            "Start is disabled until the server returns the exact project files this run would write."
          )
        : null,
      allowInstructions
        ? h(
            "div",
            { className: "case-run-dialog-instructions" },
            h("label", { htmlFor: "report-instructions" }, "Direction for this report ", h("span", null, "optional")),
            h("textarea", {
              id: "report-instructions",
              rows: 3,
              placeholder: "e.g. Lead with the downside case. Keep it to one page for the IC. Flag every assumption that isn't yet evidenced.",
              value: instructions,
              onChange: (event) => setInstructions(event.target.value)
            }),
            h("p", null, "Plain-language guidance the report model follows when it writes — tone, audience, emphasis, length.")
          )
        : null,
      h(
      "div",
      { className: "case-run-dialog-command" },
        h("span", null, "Command"),
      h("code", null, prompt.command || "No run command loaded.")
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
            title: canConfirm ? confirmLabel : disabledTitle,
            onClick: () => onConfirm(allowInstructions ? instructions : undefined)
          },
          confirmLabel
        )
      )
    )
  );
}

function SourceFileDropModal({ open, initialSourceType = "source_evidence", mode = "add_file", onClose, onUseFile }) {
  const closeButtonRef = useRef(null);
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [sourceType, setSourceType] = useState(initialSourceType || "source_evidence");
  const [selectedFile, setSelectedFile] = useState(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!open) return undefined;
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
  }, [open, onClose]);
  useEffect(() => {
    if (!open) return;
    setDragActive(false);
    setSourceType(initialSourceType || "source_evidence");
    setSelectedFile(null);
    setMessage("");
  }, [open, initialSourceType]);
  if (!open) return null;
  const createMode = mode === "create_project";
  const introCopy = createMode
    ? "Drop a Markdown or text file. The app stages it below; creating the project writes it to raw/."
    : "Drop a Markdown or text file. The app fills the Add file draft; Save file writes it to the project.";
  const waitingCopy = createMode
    ? "The file stays in the browser until you create the project."
    : "The file stays in the browser until you press Save file in the Add file panel.";
  const handleFiles = (files) => {
    const file = files && files[0];
    if (!file) return;
    const filename = sourceBasename(file.name || "");
    if (!SOURCE_IMPORT_FILENAME_RE.test(filename)) {
      setSelectedFile(null);
      setMessage("Use a flat .md or .txt filename with letters, numbers, dot, dash, or underscore.");
      return;
    }
    if (file.size > SOURCE_UPLOAD_MAX_BYTES) {
      setSelectedFile(null);
      setMessage(`File is too large for browser import. Limit: ${Math.round(SOURCE_UPLOAD_MAX_BYTES / 1024)} KB.`);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const parsed = uploadedSourceBody(String(reader.result || ""), sourceType);
      setSelectedFile({
        filename,
        source_type: parsed.source_type,
        body: parsed.body,
        bytes: file.size
      });
      setSourceType(parsed.source_type);
      setMessage(`Loaded ${filename}. Review the text before saving.`);
    };
    reader.onerror = () => {
      setSelectedFile(null);
      setMessage("Could not read this file in the browser.");
    };
    reader.readAsText(file);
  };
  const applyFile = () => {
    if (!selectedFile) return;
    onUseFile && onUseFile({ ...selectedFile, source_type: sourceType });
    onClose && onClose();
  };
  return h(
    "div",
    { className: "modal-backdrop", role: "presentation", onMouseDown: (event) => event.target === event.currentTarget && onClose() },
    h(
      "section",
      { className: "modal-shell source-upload-modal", role: "dialog", "aria-modal": "true", "aria-label": "Upload project file" },
      h(
        "header",
        { className: "modal-head" },
        h(
          "div",
          null,
          h("span", { className: "eyebrow" }, "Upload file"),
          h("h2", null, "Add a local text file"),
          h("p", null, introCopy)
        ),
        h(
          "div",
          { className: "modal-header-actions" },
          h(ModalNavControls, { label: "Dialog history" }),
          h("button", { type: "button", ref: closeButtonRef, className: "modal-close", onClick: onClose, "aria-label": "Close upload" }, "Close")
        )
      ),
      h(
        "div",
        { className: "modal-body source-upload-body" },
        h(
          "div",
          {
            className: `source-upload-dropzone ${dragActive ? "active" : ""}`,
            onDragEnter: (event) => {
              event.preventDefault();
              setDragActive(true);
            },
            onDragOver: (event) => {
              event.preventDefault();
              setDragActive(true);
            },
            onDragLeave: (event) => {
              event.preventDefault();
              if (event.currentTarget === event.target) setDragActive(false);
            },
            onDrop: (event) => {
              event.preventDefault();
              setDragActive(false);
              handleFiles(event.dataTransfer && event.dataTransfer.files);
            }
          },
          h("strong", null, selectedFile ? selectedFile.filename : "Drop .md or .txt here"),
          h("p", null, selectedFile ? `${selectedFile.bytes} bytes loaded` : waitingCopy),
          h("input", {
            ref: fileInputRef,
            type: "file",
            accept: ".md,.txt,text/markdown,text/plain",
            onChange: (event) => handleFiles(event.target.files)
          }),
          h(
            "button",
            { type: "button", className: "copy-button", onClick: () => fileInputRef.current && fileInputRef.current.click() },
            "Choose file"
          )
        ),
        h(
          "label",
          { className: "source-upload-type" },
          h("span", null, "Purpose"),
          h(
            "select",
            { value: sourceType, onChange: (event) => setSourceType(event.target.value) },
            SOURCE_TYPES.map((value) => h("option", { key: value, value }, sourceTypeLabel(value)))
          ),
          h("small", null, SOURCE_TYPE_HELP[sourceType] || SOURCE_TYPE_HELP.untyped)
        ),
        message ? h("p", { className: "source-import-note" }, message) : null,
        selectedFile
          ? h(
              "div",
              { className: "source-upload-preview" },
              h("span", null, "Preview"),
              h("pre", null, String(selectedFile.body || "").slice(0, 2400))
            )
          : null,
        h(
          "div",
          { className: "source-upload-actions" },
          h("button", { type: "button", className: "copy-button", onClick: onClose }, "Cancel"),
          h("button", { type: "button", className: "snapshot-link", disabled: !selectedFile, onClick: applyFile }, "Use this file")
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

function settingsDraftFromPayload(payload) {
  return { ...((payload && payload.values) || {}) };
}

function scoringGuideDraftFromPayload(payload) {
  return {
    text: String((payload && payload.text) || ""),
    original: {
      text: String((payload && payload.text) || "")
    }
  };
}

function scoringGuideChangedFields(draft) {
  if (!draft || !draft.original) return [];
  return String(draft.text || "") !== String(draft.original.text || "") ? ["text"] : [];
}

const STARTER_SCORING_DIMENSIONS = [
  {
    name: "Boundary",
    weight: 25,
    description: "The thesis is specific, scoped, and avoids claims the project has not earned."
  },
  {
    name: "Source support",
    weight: 30,
    description: "The thesis is backed by named project sources and compiled evidence."
  },
  {
    name: "Alternatives",
    weight: 20,
    description: "Important objections, rival explanations, and missing evidence are handled directly."
  },
  {
    name: "Next test",
    weight: 25,
    description: "The project names the next check or evidence that would weaken or strengthen the thesis."
  }
];

function scoringGuideTextWithStarterDimensions(text) {
  const payload = JSON.parse(String(text || "{}"));
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("Scoring guide must be a JSON object.");
  }
  if (Array.isArray(payload.dimensions) && payload.dimensions.length) {
    return { changed: false, text: String(text || "") };
  }
  const nextPayload = {
    ...payload,
    dimensions: STARTER_SCORING_DIMENSIONS
  };
  return { changed: true, text: `${JSON.stringify(nextPayload, null, 2)}\n` };
}

// Per-option meaning for the settings whose choices are jargon (degrading vs blocking, api vs
// subscription…). Rendered as quiet dotted-underline terms under the greyed help — ADDITIVE detail
// on hover, never a repeat of the one-liner. Add a key here to teach a new setting's options.
const SETTINGS_OPTION_HELP = {
  ZTARE_WORKBENCH_FETCH_SEVERITY: {
    degrading: "Weakens the verdict — the claim still stands, but this part is thinly backed.",
    enriching: "Nice-to-have support — adds depth, but the claim doesn't hinge on it.",
    blocking: "Stops the thesis — the claim can't stand until this gap is filled."
  },
  ZTARE_EVIDENCE_SEARCH_BACKEND: {
    auto: "Picks the search provider that matches your evidence model's family.",
    openai: "Forces OpenAI web search, whatever the evidence model is.",
    anthropic: "Forces Anthropic web search, whatever the evidence model is."
  },
  ZTARE_WORKBENCH_RUN_TRANSPORT: {
    api: "Bills each model call to your API key — runs headless, no login.",
    subscription: "Routes calls through your logged-in CLI plan instead of the API meter."
  },
  ZTARE_WORKBENCH_RUN_JUDGING: {
    single: "One reviewer model scores each candidate.",
    committee: "A 3-reviewer panel scores each candidate and combines verdicts — slower, harder to game."
  },
  ZTARE_WORKBENCH_RUN_RUBRIC_MODE: {
    fixed: "The same rubric every round.",
    rotating: "The rubric rotates across rounds to resist over-fitting to one scoring angle (anti-Goodhart)."
  }
};

function settingsGroupForKey(key) {
  if (["ZTARE_WORKBENCH_MODEL", "ZTARE_WORKBENCH_REPORT_MODEL", "ZTARE_EVIDENCE_SEARCH_BACKEND", "ZTARE_WORKBENCH_FETCH_SEVERITY", "ZTARE_WORKBENCH_MAX_FETCHES", "ZTARE_WORKBENCH_AUTO_COMPILE"].includes(key)) {
    return "Evidence and reports";
  }
  if (["ZTARE_WORKBENCH_RUN_MUTATOR_MODEL", "ZTARE_WORKBENCH_RUN_JUDGE_MODEL", "ZTARE_WORKBENCH_RUN_INVERTER_MODEL", "ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT", "ZTARE_WORKBENCH_AUTORESEARCH_LLM_RETRIES"].includes(key)) {
    return "Project runs";
  }
  return "Limits and fallback";
}

function settingsGroupSummary(group, fields) {
  const values = Object.fromEntries(fields.map((field) => [String(field.key || ""), String(field.value || field.default || "")]));
  if (group === "Evidence and reports") {
    const model = values.ZTARE_WORKBENCH_MODEL || "runtime default";
    const backend = values.ZTARE_EVIDENCE_SEARCH_BACKEND || "auto";
    const maxFetches = values.ZTARE_WORKBENCH_MAX_FETCHES || "3";
    return `Evidence uses ${model}, ${backend} search, and up to ${maxFetches} fetched gaps.`;
  }
  if (group === "Project runs") {
    const draft = values.ZTARE_WORKBENCH_RUN_MUTATOR_MODEL || "run default";
    const review = values.ZTARE_WORKBENCH_RUN_JUDGE_MODEL || "run default";
    const timeout = values.ZTARE_WORKBENCH_AUTORESEARCH_LLM_TIMEOUT || "600";
    return `Runs use ${draft} for drafts, ${review} for reviews, and a ${timeout}s timeout.`;
  }
  return values.ZTARE_WORKBENCH_MODEL_FALLBACK === "1"
    ? "Fallback is allowed when the runtime supports it."
    : "Fallback is off; calls stay on the configured model family.";
}

function settingsOptionValue(option) {
  return typeof option === "object" && option !== null ? String(option.value || "") : String(option || "");
}

function settingsOptionLabel(option) {
  if (typeof option === "object" && option !== null && option.label) return String(option.label);
  const value = settingsOptionValue(option);
  return value || "Runtime default";
}

function WorkbenchSettingsPanel({ settings, draft, setDraft, message, saving, liveMode, settingsContract, onSave, onRefresh }) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const fields = Array.isArray(settings && settings.fields) ? settings.fields : [];
  const providerKeys = Array.isArray(settings && settings.provider_keys) ? settings.provider_keys : [];
  const envFile = (settings && settings.env_file) || ".env";
  const writeTemplates = Array.isArray(settingsContract && settingsContract.write_path_templates)
    ? settingsContract.write_path_templates
    : [envFile];
  const pendingPaths = formatWriteTemplateItems(settingsContract || {}, {}, writeTemplates);
  const setField = (key, value) => setDraft({ ...(draft || {}), [key]: value });
  const draftFields = fields.map((field) => {
    const key = String(field.key || "");
    return { ...field, value: String((draft && draft[key]) || field.value || field.default || "") };
  });
  const groupedFields = ["Evidence and reports", "Project runs", "Limits and fallback"].map((group) => ({
    group,
    fields: draftFields.filter((field) => settingsGroupForKey(String(field.key || "")) === group),
  })).filter((group) => group.fields.length);
  const providerKeyCount = providerKeys.filter((row) => row.present).length;
  const renderField = (field) => {
    const key = String(field.key || "");
    const value = String(field.value || field.default || "");
    const label = field.label || displayText(key);
    const optionHelp = SETTINGS_OPTION_HELP[key];
    const affects = Array.isArray(field.affects) ? field.affects.filter(Boolean).map((item) => String(item)) : [];
    const common = {
      value,
      disabled: !liveMode || saving,
      onChange: (event) => setField(key, event.target.value)
    };
    const control = field.kind === "select"
      ? h(
          "select",
          common,
          (field.options || []).map((option, index) => {
            const optionValue = settingsOptionValue(option);
            return h("option", { key: optionValue || `blank-${index}`, value: optionValue }, settingsOptionLabel(option));
          })
        )
      : field.kind === "boolean"
        ? h(
            "button",
            {
              type: "button",
              role: "switch",
              "aria-checked": value === "1",
              "aria-label": label,
              className: `settings-toggle ${value === "1" ? "on" : "off"}`,
              disabled: !liveMode || saving,
              onClick: () => setField(key, value === "1" ? "0" : "1")
            },
            h("span", { className: "settings-toggle-knob" })
          )
        : h("input", { ...common, inputMode: field.kind === "number" ? "numeric" : "text" });
    return h(
      "div",
      { key, className: "settings-row" },
      h(
        "label",
        { className: "settings-row-copy" },
        h("span", null, label),
        h("small", null, field.help || key),
        optionHelp
          ? h(
              "div",
              { className: "settings-option-legend", "aria-label": "What each choice means" },
              Object.entries(optionHelp).map(([opt, def]) =>
                h("span", { key: opt, className: "term settings-option-term", title: def, tabIndex: 0, role: "note" }, opt)
              )
            )
          : null
      ),
      h("div", { className: "settings-row-control" }, control),
      showTechnicalDetails ? h("code", null, key) : null
    );
  };
  return h(
    "section",
    { className: "workbench-settings-panel", "aria-label": "Workbench settings" },
    h(
      "div",
      { className: "workbench-settings-head" },
      h("div", null, h("h2", null, "Set up model access"), h("p", null, message || "Choose the providers and defaults used by project actions.")),
      h(
        "div",
        { className: "settings-actions compact" },
        h("button", { type: "button", className: "copy-button quiet", disabled: !liveMode || saving, onClick: onRefresh }, "Reload"),
        h(
          "button",
          {
            type: "button",
            className: "snapshot-link",
            disabled: !liveMode || saving || !fields.length,
            onClick: onSave
          },
          saving ? "Saving" : "Save"
        )
      )
    ),
    h(
      "section",
      { className: "settings-section provider-key-panel", "aria-label": "Provider keys" },
      h("div", { className: "settings-section-head" }, h("h3", null, "Provider keys"), h("p", null, `${providerKeyCount} of ${providerKeys.length} configured. Add or replace keys here; saved keys stay hidden.`)),
      providerKeys.length
        ? h(
            "div",
            { className: "provider-key-list" },
            providerKeys.map((row) =>
              h(
                "label",
                { key: row.key, className: `provider-key-row ${row.present ? "present" : ""}` },
                h("span", { className: "provider-key-name" }, row.label || row.key),
                h("span", { className: "provider-key-status" }, h(StatusDot, { status: row.present ? "ready" : "none", label: row.present ? "Configured" : "Not set" })),
                h("input", {
                  type: "password",
                  value: String((draft && draft[row.key]) || ""),
                  disabled: !liveMode || saving,
                  autoComplete: "off",
                  placeholder: row.present ? "Keep current key" : "Paste key",
                  onInput: (event) => setField(row.key, event.target.value)
                }),
                showTechnicalDetails ? h("code", null, row.key) : null
              )
            )
          )
        : h("p", null, liveMode ? "Provider-key status has not loaded yet." : "Start the local server to edit provider keys.")
    ),
    fields.length
      ? groupedFields.map((group) =>
          group.group === "Limits and fallback"
            ? h(
                "details",
                { className: "settings-section create-disclosure", key: group.group },
                h("summary", null, `${group.group} — timeouts, retries, fallback`),
                h("div", { className: "create-disclosure-body settings-row-list" }, group.fields.map(renderField))
              )
            : h(
                "section",
                { className: "settings-section", key: group.group },
                h("div", { className: "settings-section-head" }, h("h3", null, group.group), h("p", null, settingsGroupSummary(group.group, group.fields))),
                h("div", { className: "settings-row-list" }, group.fields.map(renderField))
              )
        )
      : h("p", null, liveMode ? "Settings have not loaded yet." : "Start the local server to edit workbench settings."),
    h(
      "section",
      { className: "settings-technical" },
      h(
        "button",
        {
          type: "button",
          className: "copy-button quiet",
          onClick: () => setShowTechnicalDetails(!showTechnicalDetails)
        },
        showTechnicalDetails ? "Hide technical details" : "Show technical details"
      ),
      showTechnicalDetails
        ? h(
            "div",
            { className: "settings-technical-body" },
            h(
              "div",
              { className: "settings-env-summary" },
              h("div", null, h("span", null, "Settings file"), h("code", null, envFile)),
              h("div", null, h("span", null, "Exists"), h("strong", null, settings && settings.env_file_exists ? "yes" : "not yet"))
            ),
            pendingPathPreview("Settings write", pendingPaths, "Saving changes only the local settings file.", liveMode),
            h(WriteBoundary, {
              writeLabel: "Save writes only the allowed workbench defaults in .env.",
              readLabel: "Reading settings and provider-key presence does not call models.",
              liveMode
            })
          )
        : h("p", null, `Saved to ${envFile}. Blank provider-key fields leave existing keys unchanged.`)
    )
  );
}

function runConfigGroupForKey(key) {
  if (["ZTARE_WORKBENCH_RUN_MUTATOR_MODEL", "ZTARE_WORKBENCH_RUN_JUDGE_MODEL", "ZTARE_WORKBENCH_RUN_INVERTER_MODEL"].includes(key)) {
    return "Which models run";
  }
  if (["ZTARE_WORKBENCH_RUN_TRANSPORT", "ZTARE_WORKBENCH_RUN_JUDGING", "ZTARE_WORKBENCH_RUN_RUBRIC_MODE", "ZTARE_WORKBENCH_RUN_CROSS_FAMILY", "ZTARE_WORKBENCH_RUN_ITERS"].includes(key)) {
    return "How the run works";
  }
  return "Limits";
}

function runConfigOptionLabel(field, value) {
  if (field.kind === "boolean") return value === "1" ? "on" : "off";
  const match = (field.options || []).find((option) => settingsOptionValue(option) === String(value));
  return match ? settingsOptionLabel(match) : (String(value) || "runtime default");
}

// Per-project run config: overrides on the global Settings, saved in the project (web only), surfaced
// right on the run surface so a researcher tunes one project's run without touching global defaults.
function RunConfigPanel({ runConfig, overrides, setOverrides, message, saving, liveMode, onSave, onRefresh }) {
  const fields = Array.isArray(runConfig && runConfig.fields) ? runConfig.fields : [];
  const draft = overrides && typeof overrides === "object" ? overrides : {};
  const overrideCount = Object.keys(draft).length;
  const setOverride = (key, value) => setOverrides({ ...draft, [key]: value });
  const clearOverride = (key) => {
    const next = { ...draft };
    delete next[key];
    setOverrides(next);
  };
  const groups = ["Which models run", "How the run works", "Limits"]
    .map((group) => ({ group, fields: fields.filter((field) => runConfigGroupForKey(String(field.key || "")) === group) }))
    .filter((group) => group.fields.length);

  const renderField = (field) => {
    const key = String(field.key || "");
    const isOverride = Object.prototype.hasOwnProperty.call(draft, key);
    const globalValue = String(field.global_value || "");
    const value = isOverride ? String(draft[key]) : globalValue;
    const label = field.label || displayText(key);
    const common = {
      value,
      disabled: !liveMode || saving,
      onChange: (event) => setOverride(key, event.target.value)
    };
    const control = field.kind === "select"
      ? h("select", common, (field.options || []).map((option, index) => {
          const optionValue = settingsOptionValue(option);
          return h("option", { key: optionValue || `blank-${index}`, value: optionValue }, settingsOptionLabel(option));
        }))
      : field.kind === "boolean"
        ? h(
            "button",
            {
              type: "button",
              role: "switch",
              "aria-checked": value === "1",
              "aria-label": label,
              className: `settings-toggle ${value === "1" ? "on" : "off"}`,
              disabled: !liveMode || saving,
              onClick: () => setOverride(key, value === "1" ? "0" : "1")
            },
            h("span", { className: "settings-toggle-knob" })
          )
        : h("input", { ...common, inputMode: field.kind === "number" ? "numeric" : "text", placeholder: globalValue || "runtime default" });
    return h(
      "div",
      { key, className: `settings-row run-config-row ${isOverride ? "is-override" : ""}` },
      h(
        "label",
        { className: "settings-row-copy" },
        h("span", null, label),
        h("small", null, field.help || key)
      ),
      h(
        "div",
        { className: "settings-row-control" },
        control,
        h(
          "div",
          { className: "run-config-origin" },
          isOverride
            ? h(
                React.Fragment,
                null,
                h("span", { className: "run-config-badge" }, "this project"),
                h("button", { type: "button", className: "run-config-reset", disabled: !liveMode || saving, onClick: () => clearOverride(key), title: `Use the global default (${runConfigOptionLabel(field, globalValue)})` }, "Use global")
              )
            : h("span", { className: "run-config-inherit" }, `Global: ${runConfigOptionLabel(field, globalValue)}`)
        )
      )
    );
  };

  return h(
    "section",
    { className: "workbench-settings-panel run-config-panel", "aria-label": "Run settings for this project" },
    h(
      "div",
      { className: "workbench-settings-head" },
      h(
        "div",
        null,
        h("h2", null, "Run settings for this project"),
        h("p", null, message || "Change how this project's runs behave. Anything you set here overrides your global Settings — but only for this project, and it's saved with the project, not in global Settings.")
      ),
      h(
        "div",
        { className: "settings-actions compact" },
        overrideCount
          ? h("button", { type: "button", className: "copy-button quiet", disabled: !liveMode || saving, onClick: () => setOverrides({}) }, "Reset all to global")
          : null,
        h("button", { type: "button", className: "copy-button quiet", disabled: !liveMode || saving, onClick: onRefresh }, "Reload"),
        h("button", { type: "button", className: "snapshot-link", disabled: !liveMode || saving || !fields.length, onClick: onSave }, saving ? "Saving" : "Save")
      )
    ),
    h(
      "p",
      { className: "run-config-summary" },
      overrideCount
        ? `${overrideCount} setting${overrideCount === 1 ? "" : "s"} overridden for this project. The rest follow your global defaults.`
        : "This project follows your global defaults. Change anything below to override it just here."
    ),
    fields.length
      ? groups.map((group) =>
          h(
            "section",
            { className: "settings-section", key: group.group },
            h("div", { className: "settings-section-head" }, h("h3", null, group.group)),
            h("div", { className: "settings-row-list" }, group.fields.map(renderField))
          )
        )
      : h("p", null, liveMode ? "Run settings have not loaded yet." : "Start the local server to set per-project run settings.")
  );
}

function ScoringGuidePanel({ guide, draft, setDraft, message, saving, liveMode, onSave, onReload, onPreview, onUseStarterDimensions }) {
  const path = (guide && guide.path) || "";
  const readiness = (guide && guide.readiness) || {};
  const writeBoundary = (guide && guide.write_boundary) || {};
  const writePaths = Array.isArray(writeBoundary.write_paths) ? writeBoundary.write_paths : path ? [path] : [];
  const changed = scoringGuideChangedFields(draft).length > 0;
  const validationStatus = readiness.status || (guide && guide.parse_error ? "needs scoring guide" : "not loaded");
  const validationSummary = guide && guide.parse_error
    ? `JSON needs repair: ${guide.parse_error}`
    : readiness.summary || "Load the scoring guide to edit it.";
  const blockers = Array.isArray(readiness.blocking) ? readiness.blocking.filter(Boolean) : [];
  // Readable view of the rubric so users can SEE how their claim gets scored, not just raw JSON.
  const parsed = parseJsonLikeText((draft && draft.text) || (guide && guide.text) || "") || {};
  const persona = typeof parsed.persona === "string" ? parsed.persona : "";
  const dims = Array.isArray(parsed.dimensions)
    ? parsed.dimensions.filter((row) => row && typeof row === "object").slice(0, 16)
    : [];
  const weightTotal = dims.reduce((sum, row) => (Number.isFinite(Number(row.weight)) ? sum + Number(row.weight) : sum), 0);
  return h(
    "section",
    { className: `scoring-guide-panel ${validationStatus === "usable" ? "ready" : "attention"}`, "aria-label": "Scoring guide editor" },
    h(
      "div",
      { className: "scoring-guide-head" },
      h("span", { className: "eyebrow" }, "The scoring guide (rubric)"),
      h("h2", null, validationStatus === "usable" ? "How this claim is scored" : "How this claim is scored — needs a fix"),
      h(
        "p",
        null,
        message ||
          "Every run scores your thesis against this guide. It sets the reviewer's point of view and the weighted things they grade — so the score means something you can defend."
      )
    ),
    persona
      ? h(
          "div",
          { className: "rubric-readable" },
          h("span", { className: "rubric-readable-label" }, "Reviewer's point of view"),
          h("p", { className: "rubric-persona" }, persona)
        )
      : null,
    dims.length
      ? h(
          "div",
          { className: "rubric-readable" },
          h(
            "span",
            { className: "rubric-readable-label" },
            `What gets graded — ${dims.length} dimension${dims.length === 1 ? "" : "s"}, weights total ${weightTotal}${weightTotal === 100 ? "" : " (should be 100)"}`
          ),
          h(
            "div",
            { className: "rubric-dims" },
            dims.map((row, index) =>
              h(
                "div",
                { className: "rubric-dim", key: row.name || index },
                h("span", { className: "rubric-dim-weight" }, Number.isFinite(Number(row.weight)) ? `${row.weight}` : "—"),
                h(
                  "div",
                  { className: "rubric-dim-body" },
                  h("strong", null, row.name || `Dimension ${index + 1}`),
                  row.description ? h("p", null, row.description) : null
                )
              )
            )
          )
        )
      : null,
    h(
      "div",
      { className: "scoring-guide-summary" },
      h("div", null, h("span", null, "File"), h("code", null, path || "not loaded")),
      h("div", null, h("span", null, "Validation"), h("strong", null, validationStatus)),
      h("div", null, h("span", null, "Needs attention"), h("strong", null, blockers.length ? blockers.join(", ") : validationSummary))
    ),
    h(CompactWritePreview, {
      title: "What this saves",
      writePaths,
      receiptPath: writeBoundary.receipt_path || "",
      latestPath: writeBoundary.latest_path || "",
      noChangeBoundary: writeBoundary.no_change_boundary || ""
    }),
    h(
      "label",
      { className: "scoring-guide-editor" },
      h("span", null, "Edit the rubric (raw JSON)"),
      h("textarea", {
        value: (draft && draft.text) || "",
        disabled: !liveMode || saving,
        spellCheck: "false",
        onChange: (event) => setDraft({ ...(draft || {}), text: event.target.value })
      })
    ),
    h(
      "div",
      { className: "scoring-guide-actions" },
      h("button", { type: "button", className: "copy-button", disabled: !liveMode || saving || !path, onClick: () => onPreview && onPreview({ type: "file", value: path }) }, "Preview file"),
      h("button", { type: "button", className: "copy-button", disabled: !liveMode || saving || !draft, onClick: onUseStarterDimensions }, "Add starter dimensions"),
      h("button", { type: "button", className: "copy-button", disabled: !liveMode || saving, onClick: onReload }, "Reload"),
      h(
        "button",
        {
          type: "button",
          className: "snapshot-link",
          disabled: !liveMode || saving || !changed,
          title: changed ? "Save and validate this scoring guide" : "No scoring-guide changes to save",
          onClick: onSave
        },
        saving ? "Saving" : "Save scoring guide"
      )
    ),
    guide && guide.command ? h("code", { className: "scoring-guide-command" }, guide.command) : null
  );
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
    { label: "Project brief", value: intake },
    { label: "Report readiness file", value: reportContract },
    { label: "Latest review", value: latestReview },
    { label: "Latest next step", value: latestAction },
    { label: "Latest project brief change", value: latestIntakeEdit },
    { label: "Latest added file", value: latestSourceImport },
    { label: "Latest file edit", value: latestSourceEdit },
    { label: "Latest file check", value: latestSourceAction },
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
    h("div", null, h("span", null, "Project brief files"), h("strong", null, refSummary.total ? `${refSummary.present || 0}/${refSummary.total} present` : "not counted")),
    h("div", { className: intakeError ? "project-context-attention" : "" }, h("span", null, "Project brief check"), h("strong", null, intakeError ? displayMessage(intakeError) : "checked")),
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
    { key: "projects_available", label: "Connected projects", value: checks.projects_available ? `${readyCount} open now` : "not loaded", tone: checks.projects_available ? "ready" : "attention" },
    { key: "projects_needing_intake", label: "Existing folders to connect", value: pendingFolderCount === undefined ? "not counted" : String(pendingFolderCount), tone: pendingFolderCount ? "neutral" : "ready" },
    { key: "folder_split", label: "Useful folders / empty folders", value: folderSummary.needs_intake_with_files === undefined ? "not counted" : `${needsIntakeWithFiles} / ${needsIntakeEmpty}`, tone: needsIntakeWithFiles ? "neutral" : "ready" },
    { key: "live_routes", label: "Workbench actions", value: actionCoverage, tone: liveActionCount ? "ready" : "attention" },
    { key: "write_boundary", label: "File changes", value: writeCoverage, tone: writeContract.browser_writes ? "attention" : "ready" },
    { key: "file_preview", label: "File preview", value: previewCoverage, tone: filePreviewContract.mode ? "ready" : "attention" },
    { key: "app_built", label: "Web app", value: checks.app_built ? "built" : "dev server only", tone: checks.app_built ? "ready" : "neutral" },
    { key: "snapshot_available", label: "Offline project data", value: checks.snapshot_available ? "available" : "missing", tone: checks.snapshot_available ? "ready" : "neutral" }
  ];
  const actionRows = [
    ["project_inventory", "Projects"],
    ["snapshot", "Project data"],
    ["workflow", "Project path"],
    ["evidence_support", "Evidence summary"],
    ["project_create", "Create or connect project"],
    ["intake_edit", "Project brief save"],
    ["source_import", "Add file"],
    ["source_edit", "Save file"],
    ["source_check", "Check files"],
    ["source_index", "Refresh file index"],
    ["evidence_bind", "Connect evidence summaries"],
    ["evidence_replay", "Inspect evidence readiness"],
    ["preflight", "Check readiness"],
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
      label: "Writes files or saved history",
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
  const [inventoryFilter, setInventoryFilter] = useState("ready");
  useEffect(() => setPendingFolderLimit(48), [projectQuery]);
  if (!liveMode || (!projects.length && !projectFolders.length)) {
    const message = liveMode
      ? "Project folders are loading from projects/."
      : "Start the local workbench server to browse every project folder and edit project files.";
    return h(
      "section",
    { className: "project-switchboard empty", "aria-label": "Projects" },
      h(
        "div",
        { className: "project-switchboard-head" },
        h("span", { className: "eyebrow" }, "Projects"),
        h("h2", null, "Choose a project"),
        h("p", null, message)
      ),
      liveMode
        ? h("div", { className: "project-switchboard-section-label" }, h("span", null, "Project folders"), h("strong", null, "Loading"))
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
        has_project_files: folderHasProjectMaterial(folder),
        intake_count: folder.intake_count || (readyEntry && readyEntry.intake ? 1 : 0),
        display_label: (readyEntry && readyEntry.display_label) || folder.display_label || titleFromSlug(folder.project || "Project"),
        display_status: readyEntry ? "connected" : "needs project brief"
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
      if (inventoryFilter === "needs_intake_with_files") return !row.openable && row.has_project_files;
      return true;
    })
    .sort(projectInventorySort);
  const readyCount = (projectFolders || []).filter((folder) => entriesByProject.has(folder.project)).length;
  const needsIntakeWithFilesCount = (projectFolders || []).filter((folder) => !entriesByProject.has(folder.project) && folderHasProjectMaterial(folder)).length;
  const setupCopy =
    needsIntakeWithFilesCount > 0
      ? `${needsIntakeWithFilesCount} folder${needsIntakeWithFilesCount === 1 ? "" : "s"} already have useful files. Connect one to review its claim, evidence, runs, and saved history.`
      : "Every folder with useful files is connected, or the remaining folders are empty generated output.";
  const filterOptions = [
    { id: "ready", label: "Ready", count: readyCount, title: "Projects with a saved project brief" },
    { id: "needs_intake_with_files", label: "Connect", count: needsIntakeWithFilesCount, title: "Folders with useful files that need a project brief" },
    { id: "all", label: "All", count: (projectFolders || []).length, title: "Every folder under projects/" }
  ];
  const visibleInventoryRows = inventoryRows.slice(0, pendingFolderLimit);
  const remainingRows = Math.max(inventoryRows.length - visibleInventoryRows.length, 0);
  const filtersActive = Boolean(normalizedQuery || inventoryFilter !== "ready");
  const projectSummary = normalizedQuery
    ? `${inventoryRows.length} matching projects`
    : inventoryFilter === "ready"
      ? `${readyCount} connected projects`
      : inventoryFilter === "needs_intake_with_files"
        ? `${needsIntakeWithFilesCount} folders can connect`
      : `${inventoryRows.length} projects in view`;
  const visibleSummary = inventoryRows.length
    ? `${visibleInventoryRows.length} visible of ${inventoryRows.length} matching`
    : "No projects match";
  const resetInventoryView = () => {
    setProjectQuery("");
    setInventoryFilter("ready");
    setPendingFolderLimit(48);
  };
  return h(
    "section",
    { className: "project-switchboard", "aria-label": "Projects" },
    h(
      "div",
      { className: "project-switchboard-head" },
        h("span", { className: "eyebrow" }, "Projects"),
        h("h2", null, "Open a project"),
        h("p", null, "Start with connected projects. Connect an existing folder only when it already has useful files.")
      ),
    h(
      "div",
      { className: "project-switchboard-tools" },
      h(
        "label",
        null,
        h("span", null, "Search"),
        h("input", {
          value: projectQuery,
          onInput: (event) => setProjectQuery(event.target.value),
          placeholder: "billing, ns, forecast, ops"
        })
      ),
      h(
        "div",
        { className: "project-switchboard-action-buttons" },
        h(
          "button",
          {
            type: "button",
            className: "copy-button",
            disabled: !filtersActive,
            onClick: resetInventoryView,
            title: filtersActive ? "Clear project search and filters" : "No project filters active"
          },
          "Clear"
        ),
        h(
          "button",
          { type: "button", className: "copy-button primary", onClick: () => onCreate && onCreate() },
          "Create"
        )
      ),
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
              title: option.title,
              onClick: () => {
                setInventoryFilter(option.id);
                setPendingFolderLimit(48);
              }
            },
            h("span", null, option.label),
            h("strong", null, String(option.count))
          )
        )
      )
    ),
    inventoryFilter !== "ready" || needsIntakeWithFilesCount
      ? h(
          "div",
          { className: "project-switchboard-note" },
          h("strong", null, inventoryFilter === "ready" ? "Folders ready to connect" : projectSummary),
          h("span", null, setupCopy)
        )
      : null,
    filePreviewMessage || filePreview
      ? h("div", { className: "project-switchboard-preview" }, h(FilePreview, { filePreview, filePreviewMessage }))
      : null,
    h(
      "div",
      { className: "project-switchboard-grid" },
      h(
        "div",
        { className: "project-switchboard-section-label" },
        h("span", null, inventoryFilter === "ready" ? "Connected projects" : "Project folders"),
        h("strong", null, visibleSummary)
      ),
      visibleInventoryRows.map((project) => {
        const projectKey = projectEntryKey(project);
        const refSummary = project.intake_ref_summary || {};
        const intakeError = project.intake_error || "";
        const active = projectKey === activeKey;
        const openable = Boolean(project.openable && project.intake);
        const folderNextAction = project.next_action && typeof project.next_action === "object" ? project.next_action : {};
        const folderNextActionLabel = folderNextAction.label || (openable ? "Open project" : "Create project brief");
        const folderNextActionDetail = folderNextAction.detail || "";
        const intakeMode = intakeError ? "Brief needs attention" : openable ? (project.intake_editable === false ? "Brief is read-only" : "Brief ready to edit") : "No project brief yet";
        const fileSummary = projectInventoryFileSummary(project, refSummary);
        const rawPreview = ([
          ...(project.source_preview_files || []),
          ...(project.raw_preview_files || []),
          ...(project.root_preview_files || [])
        ]).find(isPreviewableRepoPath) || "";
        const workspacePreview = (project.workspace_preview_files || []).find(isPreviewableRepoPath) || "";
        const recoveryActions = Array.isArray(project.recovery_actions) ? project.recovery_actions.filter(Boolean) : [];
        const addIntakeAction = recoveryActions.find((action) => action.id === "add_intake") || recoveryActions[0] || null;
        const addIntakeBoundary = addIntakeAction && addIntakeAction.write_boundary && typeof addIntakeAction.write_boundary === "object"
          ? addIntakeAction.write_boundary
          : {};
        const addIntakeWritePaths = Array.isArray(addIntakeBoundary.write_paths) ? addIntakeBoundary.write_paths.filter(Boolean) : [];
        const addIntakeNoChange = String(addIntakeBoundary.no_change_boundary || "").trim();
        const addIntakeRule = String((addIntakeAction && addIntakeAction.rule) || "").trim();
        const addIntakeTarget = writeBoundaryTargetSummary(addIntakeBoundary);
        const addIntakeReceipt = String(addIntakeBoundary.receipt_path || "").trim();
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
            h("div", { className: "project-tile-title" },
              h("strong", null, project.display_label || titleFromSlug(project.project || "Local project")),
              // Research standing at a glance — a stress-tested claim with a confidence, not just a folder.
              project.standing && project.standing.tested
                ? h("span", { className: `project-tile-standing tier-${project.standing.tier}`,
                    title: "How likely the champion says the thesis holds (probability, not the judge score)" },
                    `${project.standing.label} · ${Math.round((project.standing.confidence || 0) * 100)}%`)
                : null),
            h("small", null, project.project_dir || `projects/${project.project}`)
          ),
          h(
            "div",
            { className: "project-tile-facts" },
            // For openable projects the "Open project" button already says it — drop the redundant label.
            // Keep "Create project brief" for folders that still need connecting (it's the real next step).
            openable ? null : h("span", { className: "attention" }, folderNextActionLabel),
            h("span", null, fileSummary)
          ),
          h(
            "details",
            { className: "project-tile-details" },
            h("summary", null, "Project details"),
            h(
              "div",
              null,
              h("span", { className: intakeError ? "attention" : "" }, intakeMode),
              h("span", null, project.report_contract ? "Pressure-tested · verdict ready" : "Not pressure-tested yet"),
              h("span", null, receiptCount ? `${receiptCount} recent changes` : recoveryActions.length ? `${recoveryActions.length} setup step${recoveryActions.length === 1 ? "" : "s"}` : "no recent changes"),
              rawPreview || workspacePreview
                ? h(
                    "div",
                    { className: "project-tile-preview-actions" },
                    rawPreview
                      ? h(
                          "button",
                          {
                            type: "button",
                            className: "copy-button",
                            disabled: !liveMode,
                            onClick: () => onPreview && onPreview({ type: "file", value: rawPreview }),
                            title: "A source you added — open to read it"
                          },
                          "View " + (String(rawPreview).split("/").pop() || "a source")
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
                            title: "A file the workbench built while working — open to read it"
                          },
                          "View " + (String(workspacePreview).split("/").pop() || "a built file")
                        )
                      : null
                  )
                : null
            )
          ),
          intakeError ? h("p", { className: "project-tile-error" }, displayMessage(intakeError)) : null,
          !openable
            ? h(
                "p",
                { className: "project-tile-error" },
                displayMessage(
                  folderNextActionDetail ||
                    (addIntakeAction && addIntakeAction.detail) ||
                    "Save a project brief to start working on the thesis, evidence, and runs."
                )
              )
            : null,
          !openable && addIntakeWritePaths.length
            ? h(
                "details",
                { className: "project-tile-boundary" },
                h("summary", null, "Show files that will change"),
                h(
                  "div",
                  null,
                  addIntakeRule ? h("span", null, "Rule") : null,
                  addIntakeRule ? h("small", null, displayMessage(addIntakeRule)) : null,
                  h("span", null, "Main file"),
                  h("code", null, addIntakeTarget),
                  addIntakeReceipt ? h("span", null, "Project brief path") : null,
                  addIntakeReceipt ? h("code", null, addIntakeReceipt) : null,
                  addIntakeWritePaths.length > 1 ? h("small", null, `${addIntakeWritePaths.length} possible changed files or saved-history files`) : null,
                  addIntakeNoChange ? h("small", null, displayMessage(addIntakeNoChange)) : null
                )
              )
            : null,
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
                title: !openable
                  ? folderNextActionDetail || (addIntakeAction && addIntakeAction.detail) || "Connect this project folder"
                  : active
                    ? "This project is open"
                    : `Open ${project.display_label || titleFromSlug(project.project || "Local project")} / ${sourceBasename(project.intake || "") || "project"}`
              },
              active ? "Current" : folderNextActionLabel
            ),
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
            ),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                onClick: () => setPendingFolderLimit(inventoryRows.length)
              },
              "Show all"
            )
          )
        : null
    )
  );
}


function projectWorkflowSteps({ snapshot, traceContext, reportContext, runHistory, receiptHistory, liveMode, onOpenDetail }) {
  const rows = (snapshot && snapshot.rows) || [];
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const reportRow = rowByLabel(rows, "Report readiness");
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
  const projectFileDone = receipts.some((receipt) => receipt.kind === "project_file" || receipt.kind === "case_file");
  const serverTone = liveMode ? "ready" : "attention";

  return [
    {
      label: "Choose project",
      state: liveMode ? "Ready" : "Server needed",
      detail: liveMode ? "Project is loaded from the local API." : "Start live mode to browse and edit projects.",
      tone: serverTone,
      onClick: () => onOpenDetail && onOpenDetail("projects", "Projects")
    },
    {
      label: "Prepare files",
      state: inputReady ? "Ready" : "Needs review",
      detail: inputReady ? "Original files and evidence summary are usable." : "Check the project brief, original files, and evidence summary.",
      tone: inputReady ? "ready" : "attention",
      onClick: () => onOpenDetail && onOpenDetail("sources", inputReady ? "Project brief" : "Prepare files")
    },
    {
      label: "Check readiness",
      state: preflightDone ? "Accepted" : "Not run",
      detail: preflightDone ? "The project can move forward." : "Run the cheap local readiness check before model work.",
      tone: preflightDone ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("run", "Check readiness")
    },
    {
      label: "Project run",
      state: runDone ? "Scored" : planStatus === "ready_for_bounded_run" ? "Ready" : "Waiting",
      detail: runDone ? "Recent run history is available." : planStatus === "ready_for_bounded_run" ? "Review files that may change before starting." : "The readiness check must accept the project first.",
      tone: runDone || planStatus === "ready_for_bounded_run" ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("run", runDone ? "Results" : "Ready to run")
    },
    {
      label: "Review report",
      state: reportReady ? reviewDone ? "Reviewed" : "Ready" : "Needs work",
      detail: reportReady ? "Report looks ready; record a review if needed." : reportRow ? itemDetail(reportRow) : "Check report readiness before relying on it.",
      tone: reportReady ? "ready" : "attention",
      onClick: () => onOpenDetail && onOpenDetail(reportReady && !reviewDone ? "review" : "save", reportReady && !reviewDone ? "Save review" : "Report readiness")
    },
    {
      label: "Save project",
      state: projectFileDone ? "Saved" : "Not saved",
      detail: projectFileDone ? "A saved project record is in history." : "Save a project file when the current state is ready to hand off.",
      tone: projectFileDone ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("save", "Project file")
    }
  ];
}

function workflowStepDestination(step) {
  const destination = (step && step.ui_destination) || {};
  if (destination.workspace && destination.subsection) {
    return normalizeWorkspaceTarget(destination.workspace, destination.subsection);
  }
  const id = String((step && step.id) || "");
  if (id === "open_project") return ["projects", "Projects"];
  if (id === "prepare_files") return ["sources", step.status === "ready" ? "Project brief" : "Prepare files"];
  if (id === "preflight") return ["run", "Check readiness"];
  if (id === "project_run") return ["run", step.status === "done" ? "Results" : "Ready to run"];
  if (id === "review_report") {
    const label = String((step && step.label) || "").toLowerCase();
    if (label.includes("run check")) return ["run", "Results"];
    if (label.includes("next report action")) return ["save", "Report readiness"];
    return [step.status === "ready" ? "review" : "save", step.status === "ready" ? "Save review" : "Report readiness"];
  }
  if (id === "save_project") return ["save", "Project file"];
  return ["overview", "Overview"];
}

function workflowTone(status) {
  if (["ready", "done", "reviewed"].includes(status)) return "ready";
  if (["needs_attention", "blocked", "failed"].includes(status)) return "attention";
  return "neutral";
}

function workflowServerActionLabel(step) {
  if (step && (step.local_step || step.local_action)) return displayText(step.local_step || step.local_action);
  const id = String((step && step.id) || "");
  const labels = {
    open_project: "Load project",
    prepare_files: "Edit project brief and original files",
    preflight: "Check readiness",
    project_run: "Start or inspect run",
    review_report: "Check report readiness",
    save_project: "Save project file"
  };
  return labels[id] || "Open project step";
}

function writeBoundaryTargetSummary(writeBoundary) {
  const boundary = writeBoundary && typeof writeBoundary === "object" ? writeBoundary : {};
  const writePaths = Array.isArray(boundary.write_paths) ? boundary.write_paths.filter(Boolean) : [];
  if (writePaths.length) {
    const first = String(writePaths[0]);
    return writePaths.length > 1 ? `${first} (+${writePaths.length - 1} more)` : first;
  }
  if (boundary.writes_project_files || boundary.writes_repo_files) return "paths not listed";
  return "read-only";
}

function writeBoundaryStorageLabel(writeBoundary) {
  const boundary = writeBoundary && typeof writeBoundary === "object" ? writeBoundary : {};
  const backend = String(boundary.storage_backend || (boundary.storage && boundary.storage.backend) || "").trim();
  if (!backend || !(boundary.writes_project_files || boundary.writes_repo_files || (Array.isArray(boundary.write_paths) && boundary.write_paths.length))) {
    return "";
  }
  if (backend === "file") return "Local project store";
  return displayText(backend);
}



function CompactWritePreview({ title, writePaths, receiptPath, latestPath, noChangeBoundary }) {
  const paths = Array.isArray(writePaths) ? writePaths.filter(Boolean) : [];
  const target = paths.length ? (paths.length > 1 ? `${paths[0]} (+${paths.length - 1} more)` : paths[0]) : "";
  const receipt = String(receiptPath || "").trim();
  const latest = String(latestPath || "").trim();
  const boundary = String(noChangeBoundary || "").trim();
  if (!target && !receipt && !latest && !boundary) return null;
  return h(
    "div",
    { className: "compact-write-preview" },
    h("span", null, title || "What this writes"),
    target ? h("div", null, h("small", null, "Target"), h("code", null, target)) : null,
    receipt ? h("div", null, h("small", null, "History file"), h("code", null, receipt)) : null,
    latest && latest !== receipt ? h("div", null, h("small", null, "Latest copy"), h("code", null, latest)) : null,
    boundary ? h("p", null, displayMessage(boundary)) : null
  );
}

function serverWorkflowSteps(workflowContext, onOpenDetail) {
  const steps = (workflowContext && workflowContext.steps) || [];
  if (!Array.isArray(steps) || !steps.length) return [];
  return steps.map((step) => {
    const status = String(step.status || "unknown");
    const [workspace, subsection] = workflowStepDestination(step);
    const target = writeBoundaryTargetSummary(step.write_boundary || {});
    const detail = [
      displayMessage(step.detail),
      `Next action: ${workflowServerActionLabel(step)}`,
      target && target !== "read-only" ? `Target: ${target}` : ""
    ].filter(Boolean).join(" / ");
    return {
      label: displayText(step.label || step.id || "Project step"),
      state: displayMessage(step.display_status || status),
      detail,
      tone: workflowTone(status),
      onClick: () => onOpenDetail && onOpenDetail(workspace, subsection)
    };
  });
}





function ProjectEvidenceMap({ claimSupport, thesisSupport, evidenceState, onOpenDetail, onPreview }) {
  const liveSupport = claimSupport && typeof claimSupport === "object" ? claimSupport : {};
  const compactSupport = thesisSupport && typeof thesisSupport === "object" ? thesisSupport : {};
  const support = Array.isArray(liveSupport.rows) && liveSupport.rows.length ? liveSupport : compactSupport;
  const compactRows = [
    ...((Array.isArray(compactSupport.supported_points) ? compactSupport.supported_points : []) || []),
    ...((Array.isArray(compactSupport.weak_or_open_points) ? compactSupport.weak_or_open_points : []) || [])
  ];
  const claimCards = Array.isArray(support.claim_cards) && support.claim_cards.length
    ? support.claim_cards.filter(Boolean)
    : Array.isArray(compactSupport.claim_cards) && compactSupport.claim_cards.length
      ? compactSupport.claim_cards.filter(Boolean)
      : [];
  const rows = claimCards.length ? claimCards : Array.isArray(support.rows) ? support.rows.filter(Boolean) : compactRows.filter(Boolean);
  const sources = Array.isArray(support.source_context) ? support.source_context.filter(Boolean) : [];
  const statusCounts = support.status_counts && typeof support.status_counts === "object" ? support.status_counts : {};
  const activeGapCount = Number((evidenceState && evidenceState.gap_count) || 0);
  const supportRows = rows.filter((row) => row.kind === "supported" || !/weak|missing|unsourced|blocked/i.test(`${row.support_status || row.status || ""} ${row.issue || ""}`));
  const weakRows = rows.filter((row) => row.kind === "weak_or_open" || /weak|missing|unsourced|blocked/i.test(`${row.support_status || row.status || ""} ${row.issue || ""}`));
  const shownSupport = supportRows.slice(0, 4);
  const shownWeak = weakRows.slice(0, 3);
  const normalizeSourcePath = (path) => {
    const value = String(path || "").trim();
    if (!value) return "";
    if (value.includes("/")) return value;
    if (support.project) return `projects/${support.project}/raw/${value}`;
    return value;
  };
  const sourcePathsFor = (row) => {
    const paths = [];
    const sourceIds = Array.isArray(row && row.source_ids)
      ? row.source_ids.filter(Boolean)
      : row && row.source_id
        ? [row.source_id]
        : [];
    sourceIds.forEach((sourceId) => {
      const source = sources.find((item) => item && item.source_id === sourceId);
      if (source && source.path) paths.push(source.path);
      if (source && source.relative_raw_path) paths.push(normalizeSourcePath(source.relative_raw_path));
    });
    (Array.isArray(row && row.source_paths) ? row.source_paths : []).forEach((path) => paths.push(normalizeSourcePath(path)));
    return Array.from(new Set(paths.filter(Boolean))).slice(0, 4);
  };
  const supportCountText = [
    support.claim_count ? `${support.claim_count} support notes` : "",
    statusCounts.direct_source_support ? `${statusCounts.direct_source_support} direct` : "",
    statusCounts.synthesized_across_sources ? `${statusCounts.synthesized_across_sources} cross-source` : "",
  ].filter(Boolean).join(" / ");
  const supportFacts = [
    ["Supported", String(support.supported_count || supportRows.length || compactSupport.supported_count || 0)],
    ["Open", String(support.weak_or_open_count || weakRows.length || compactSupport.weak_or_open_count || activeGapCount || 0)],
    ["Sources", String(support.source_count || sources.length || compactSupport.source_count || 0)]
  ];
  const evidencePath = support.evidence_support_file_path || support.evidence_file_path || support.packet_path || "";
  const sourceIndexPath = support.source_index_path || "";
  const emptyText = support.status
    ? "No support notes are loaded for this project."
    : "Start the local server to load thesis support from project files.";
  return h(
    "section",
    { className: "project-evidence-map", "aria-label": "Thesis evidence map" },
    h(
      "div",
      { className: "project-evidence-map-head" },
      h("span", { className: "eyebrow" }, "What supports the thesis"),
      h("strong", null, support.display_status || displayText(support.status || "not loaded")),
      h("small", null, supportCountText || emptyText),
      h(
        "div",
        { className: "project-evidence-map-actions" },
        h(
          "button",
          {
            type: "button",
            className: "copy-button",
            onClick: () => onOpenDetail && onOpenDetail("run", "Results")
          },
          activeGapCount ? "Review evidence gap" : "Open support"
        ),
        evidencePath
          ? h(
              "button",
              {
                type: "button",
                className: "copy-button",
                onClick: () => onPreview && onPreview({ type: "file", value: evidencePath })
              },
              "Preview evidence"
            )
          : null,
        sourceIndexPath
          ? h(
              "button",
              {
                type: "button",
                className: "copy-button",
                onClick: () => onPreview && onPreview({ type: "file", value: sourceIndexPath })
              },
              "Preview file index"
            )
          : null
      )
    ),
    h(
      "div",
      { className: "project-evidence-map-facts", "aria-label": "Evidence summary" },
      supportFacts.map(([label, value]) => h("div", { key: label }, h("span", null, label), h("strong", null, value)))
    ),
    h(
      "div",
      { className: "project-evidence-map-grid" },
      h(
        "div",
        { className: "project-evidence-map-lane" },
        h("span", null, "Supported claim cards"),
        shownSupport.length
          ? shownSupport.map((row) => {
              const sourcePaths = sourcePathsFor(row);
              return h(
                "article",
                { key: row.card_id || row.claim_id || row.claim, className: "ready" },
                h("strong", null, shortText(row.claim || row.claim_id || "Supported claim", 150)),
                h("small", null, displayText(row.issue || row.evidence_level || row.support_status || row.status || "supported")),
                sourcePaths.length
                  ? h(
                      "div",
                      { className: "project-evidence-source-list" },
                      sourcePaths.map((sourcePath) =>
                        h(
                          "button",
                          {
                            key: sourcePath,
                            type: "button",
                            className: "inline-path-button",
                            onClick: () => onPreview && onPreview({ type: "file", value: sourcePath })
                          },
                          sourcePath
                        )
                      )
                    )
                  : h("small", null, "No source file path attached.")
              );
            })
          : h("p", null, emptyText)
      ),
      h(
        "div",
        { className: "project-evidence-map-lane" },
        h("span", null, activeGapCount || shownWeak.length ? "Weak or open support" : "No weak support loaded"),
        activeGapCount
          ? h(
              "article",
              { className: "attention" },
              h("strong", null, `${activeGapCount} active evidence gap${activeGapCount === 1 ? "" : "s"}`),
              h("small", null, displayMessage((evidenceState && evidenceState.gap_summary) || "Fetch or justify the active evidence gap.")),
              evidenceState && evidenceState.gap_file
                ? h(
                    "button",
                    {
                      type: "button",
                      className: "inline-path-button",
                      onClick: () => onPreview && onPreview({ type: "file", value: evidenceState.gap_file })
                    },
                    evidenceState.gap_file
                  )
                : null
            )
          : null,
        shownWeak.length
          ? shownWeak.map((row) =>
              h(
                "article",
                { key: row.card_id || row.claim_id || row.claim, className: "attention" },
                h("strong", null, shortText(row.claim || row.claim_id || "Open claim", 150)),
                h("small", null, displayMessage(row.issue || row.next_action || row.support_status || row.status || "Needs stronger support")),
                sourcePathsFor(row).length
                  ? h(
                      "div",
                      { className: "project-evidence-source-list" },
                      sourcePathsFor(row).map((sourcePath) =>
                        h(
                          "button",
                          {
                            key: sourcePath,
                            type: "button",
                            className: "inline-path-button",
                            onClick: () => onPreview && onPreview({ type: "file", value: sourcePath })
                          },
                          sourcePath
                        )
                      )
                    )
                  : null
              )
            )
          : !activeGapCount
            ? h("p", null, "No weak or unsourced support notes are loaded.")
            : null
      )
    )
  );
}

function ProjectFileInventoryPanel({ inventory, liveMode, onPreview, onOpenDetail }) {
  const [activeGroup, setActiveGroup] = useState("all");
  const files = inventory && Array.isArray(inventory.items) ? inventory.items.filter(Boolean) : [];
  const roleCounts = inventory && inventory.role_counts && typeof inventory.role_counts === "object" ? inventory.role_counts : {};
  const latestProjectFile = inventory && inventory.latest_project_file ? String(inventory.latest_project_file) : "";
  const latestProjectFileWrite = inventory && inventory.latest_project_file_write ? String(inventory.latest_project_file_write) : "";
  const latestProjectFileReceipt = inventory && inventory.latest_project_file_receipt ? String(inventory.latest_project_file_receipt) : "";
  const latestProjectFileSummary = inventory && inventory.latest_project_file_summary ? String(inventory.latest_project_file_summary) : "";
  const latestProjectButtons = [
    ["Saved project", latestProjectFile, "file"],
    ["Latest copy", latestProjectFileWrite, "file"],
    ["Saved history", latestProjectFileReceipt, "receipt"],
  ].filter((entry, index, rows) => entry[1] && rows.findIndex((candidate) => candidate[1] === entry[1]) === index);
  const countText = inventory && inventory.item_count
    ? `${inventory.item_count} project file${inventory.item_count === 1 ? "" : "s"}`
    : "No project files loaded";
  const fallbackFileGroups = [
    {
      id: "all",
      label: "All files",
      roles: null,
      help: "Every project file the workbench can inspect.",
      action: ["sources", "Prepare files", "Open file work"]
    },
    {
      id: "overview",
      label: "Thesis & brief",
      roles: ["intake", "thesis"],
      help: "The thesis, limits, and original files the project is built around.",
      action: ["overview", "Thesis", "Open thesis"]
    },
    {
      id: "source",
      label: "Original files",
      roles: ["source"],
      help: "Raw notes, imports, and file-purpose maps before they become evidence.",
      action: ["sources", "Prepare files", "Prepare original files"]
    },
    {
      id: "evidence",
      label: "Evidence summary",
      roles: ["evidence", "evidence_gap"],
      help: "The compiled view of what the original files support, weaken, or leave missing.",
      action: ["run", "Results", "Open evidence work"]
    },
    {
      id: "run",
      label: "Runs & lessons",
      roles: ["run"],
      help: "Scores, run output, learned constraints, and the next check suggested by a run.",
      action: ["run", "Results", "Open run results"]
    },
    {
      id: "report",
      label: "Report readiness",
      roles: ["report"],
      help: "Files that show whether the report matches the current project state.",
      action: ["save", "Report readiness", "Open report readiness"]
    },
    {
      id: "saved",
      label: "Saved project",
      roles: ["project_file"],
      help: "Saved project files that package the current project state.",
      action: ["review", "Saved history", "Open saved work"]
    },
    {
      id: "receipt",
      label: "Saved history",
      roles: ["receipt"],
      help: "Saved edits, reviews, next steps, and file-change records.",
      action: ["review", "Saved history", "Open saved history"]
    },
    {
      id: "axiom",
      label: "Assumptions",
      roles: ["axiom"],
      help: "Run-learned assumptions and constraints that should be inspected before reuse.",
      action: ["run", "Results", "Open assumptions"]
    }
  ];
  const backendGroups = inventory && Array.isArray(inventory.file_groups) ? inventory.file_groups : [];
  const fileGroups = backendGroups.length
    ? backendGroups.map((group) => {
        const action = group.action && typeof group.action === "object" ? group.action : {};
        const roles = Array.isArray(group.roles) && group.roles.length ? group.roles : null;
        return {
          id: group.id || group.label || "group",
          label: group.label || displayText(group.id || "Files"),
          roles,
          help: group.help || "Project files for this part of the work.",
          count: Number.isFinite(Number(group.count)) ? Number(group.count) : null,
          previewableCount: Number.isFinite(Number(group.previewable_count)) ? Number(group.previewable_count) : null,
          missingCount: Number.isFinite(Number(group.missing_count)) ? Number(group.missing_count) : null,
          action: action.workspace || action.subsection
            ? [action.workspace || "projects", action.subsection || "Current project", action.label || action.subsection || "Open"]
            : null
        };
      }).filter((group) => group.id === "all" || Number(group.count || 0) > 0)
    : fallbackFileGroups;
  const groupCount = (group) => {
    if (Number.isFinite(Number(group.count))) return Number(group.count);
    if (!group.roles) return files.length;
    return group.roles.reduce((total, role) => total + Number(roleCounts[role] || 0), 0);
  };
  const activeGroupConfig = fileGroups.find((group) => group.id === activeGroup) || fileGroups[0];
  const sortFilesForReading = (rows) => [...rows].sort((left, right) => {
    const leftRoleOrder = Number.isFinite(Number(left.role_order)) ? Number(left.role_order) : 999;
    const rightRoleOrder = Number.isFinite(Number(right.role_order)) ? Number(right.role_order) : 999;
    if (leftRoleOrder !== rightRoleOrder) return leftRoleOrder - rightRoleOrder;
    const leftPriority = Number.isFinite(Number(left.priority)) ? Number(left.priority) : 999;
    const rightPriority = Number.isFinite(Number(right.priority)) ? Number(right.priority) : 999;
    if (leftPriority !== rightPriority) return leftPriority - rightPriority;
    if (Boolean(left.exists) !== Boolean(right.exists)) return left.exists ? -1 : 1;
    return String(left.label || left.path || "").localeCompare(String(right.label || right.path || ""));
  });
  const activeFiles = activeGroupConfig.roles
    ? sortFilesForReading(files.filter((item) => activeGroupConfig.roles.includes(item.role)))
    : sortFilesForReading(files);
  const visibleFiles = activeFiles.filter((item) => item && item.previewable).slice(0, 10);
  const activeAction = Array.isArray(activeGroupConfig.action) ? activeGroupConfig.action : null;
  const previewFile = (item) => {
    if (!item || !item.previewable || !item.path || !onPreview) return;
    onPreview({ type: "file", value: item.path });
  };
  return h(
    "section",
    { className: "project-file-inventory", "aria-label": "Project files" },
    h(
      "div",
      { className: "project-file-inventory-head" },
      h(
        "div",
        null,
        h("span", { className: "eyebrow" }, "Project file viewer"),
        h("h3", null, countText),
        h("p", null, visibleFiles.length ? "Pick the job first, then open the file behind the answer." : "Project files will appear here when the local server can read them.")
      ),
      activeAction
        ? h("button", { type: "button", className: "copy-button", onClick: () => onOpenDetail && onOpenDetail(activeAction[0], activeAction[1]) }, activeAction[2])
        : null
    ),
    latestProjectButtons.length
      ? h(
          "div",
          { className: "project-file-latest", "aria-label": "Latest saved project file" },
          h(
            "div",
            null,
            h("span", null, "Latest saved project"),
            h("strong", null, latestProjectFile ? sourceBasename(latestProjectFile) : "Saved history only"),
            h("small", null, latestProjectFileSummary || "Open the saved file or saved history before relying on the packaged state.")
          ),
          h(
            "div",
            { className: "project-file-latest-actions" },
            latestProjectButtons.map(([label, path, type]) =>
              h(
                "button",
                {
                  key: `${label}:${path}`,
                  type: "button",
                  className: "copy-button",
                  disabled: !liveMode || !isPreviewableRepoPath(path),
                  onClick: () => onPreview && onPreview({ type, value: path }),
                  title: liveMode && isPreviewableRepoPath(path) ? `Preview ${path}` : "Start the workbench server to preview this file"
                },
                label
              )
            )
          )
        )
      : null,
    h(
      "div",
      { className: "project-file-role-strip", "aria-label": "Project file groups" },
      fileGroups.map((group) =>
        h(
          "button",
          {
            key: group.id,
            type: "button",
            className: activeGroupConfig.id === group.id ? "active" : "",
            onClick: () => setActiveGroup(group.id),
            title: group.help
          },
          h("span", null, group.label),
          h("strong", null, String(groupCount(group)))
        )
      )
    ),
    h(
      "div",
      { className: "project-file-group-context" },
      h("strong", null, activeGroupConfig.label),
      h("span", null, activeGroupConfig.help),
      activeFiles.length
        ? h(
            "em",
            null,
            `${Number.isFinite(Number(activeGroupConfig.previewableCount)) ? activeGroupConfig.previewableCount : activeFiles.filter((item) => item.previewable).length} previewable / ${Number.isFinite(Number(activeGroupConfig.missingCount)) ? activeGroupConfig.missingCount : activeFiles.filter((item) => !item.exists).length} missing`
          )
        : h("em", null, "No files in this group")
    ),
    visibleFiles.length
      ? h(
          "div",
          { className: "project-file-shortlist" },
          visibleFiles.map((item) =>
            h(
              "button",
              {
                key: item.path,
                type: "button",
                className: "project-file-chip",
                disabled: !liveMode,
                onClick: () => previewFile(item),
                title: liveMode ? `Preview ${item.path}` : "Start the workbench server to preview files"
              },
              h("strong", null, item.label || item.display_kind || sourceBasename(item.path)),
              h("span", null, `${item.display_kind || fileRoleLabel(item.path)} / ${item.format || fileFormatLabel(item.path)}`),
              item.reason ? h("small", null, item.reason) : null,
              h("code", null, item.path)
            )
          )
        )
      : h("p", { className: "empty-copy" }, liveMode ? "No previewable project files loaded yet." : "Start the local server to load project files."),
    activeFiles.length > visibleFiles.length
      ? h(
          "details",
          { className: "project-file-all" },
          h("summary", null, `Show ${activeFiles.length - visibleFiles.length} more file${activeFiles.length - visibleFiles.length === 1 ? "" : "s"}`),
          h(
            "div",
            { className: "project-file-all-list" },
            activeFiles.slice(visibleFiles.length, 80).map((item) =>
              h(
                "div",
                { key: item.path, className: `project-file-line ${item.exists ? "" : "missing"}` },
                h("span", null, item.label || item.display_kind || "Project file"),
                h("small", null, item.reason || item.display_kind || "Project file"),
                h("code", null, item.path),
                h(
                  "button",
                  {
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode || !item.previewable,
                    onClick: () => previewFile(item)
                  },
                  item.previewable ? "Preview" : "Missing"
                )
              )
            )
          )
        )
      : null
  );
}

function projectActionDestination(action) {
  const explicit = action && action.ui_destination && typeof action.ui_destination === "object" ? action.ui_destination : {};
  if (explicit.workspace || explicit.subsection) {
    return {
      workspace: explicit.workspace || "projects",
      subsection: explicit.subsection || "Current project",
      label: explicit.label || explicit.subsection || "Open"
    };
  }
  if (action && (action.workspace || action.subsection)) {
    return {
      workspace: action.workspace || "projects",
      subsection: action.subsection || "Current project",
      label: action.primary_label || action.subsection || "Open"
    };
  }
  const fallback = {
    follow_report_next_action: ["save", "Report readiness"],
    run_report_allowed_check: ["run", "Check readiness"],
    repair_report_support: ["save", "Report readiness"],
    rerun_report_support: ["save", "Report inputs"],
    save_report_review: ["review", "Save review"],
    recover_evidence_gaps: ["run", "Results"],
    prepare_evidence: ["sources", "Prepare files"],
    fix_scoring_guide: ["run", "Ready to run"],
    source_health_1: ["run", "Fix warnings"],
    source_health_2: ["run", "Fix warnings"],
    source_health_3: ["run", "Fix warnings"],
  }[String((action && action.id) || "")];
  if (fallback) return { workspace: fallback[0], subsection: fallback[1], label: fallback[1] };
  return { workspace: "projects", subsection: "Current project", label: "Current project" };
}


function ProjectAxiomPanel({ axiomsState, onPreview }) {
  const state = axiomsState && typeof axiomsState === "object" ? axiomsState : {};
  const verified = Array.isArray(state.verified) ? state.verified.filter(Boolean).slice(0, 4) : [];
  const derived = Array.isArray(state.derived_constraints) ? state.derived_constraints.filter(Boolean).slice(0, 4) : [];
  const retiredCount = Number(state.retired_count || 0);
  const file = state.file || "";
  const backingFiles = Array.isArray(state.backing_files) && state.backing_files.length
    ? Array.from(new Set(state.backing_files.filter(Boolean)))
    : file
      ? [file]
      : [];
  if (!backingFiles.length && !verified.length && !derived.length && !retiredCount) return null;
  return h(
    "details",
    { className: "project-home-axioms" },
    h(
      "summary",
      null,
      h("span", { className: "eyebrow" }, "Axioms"),
      h("strong", null, state.summary || "Run-learned axioms and constraints"),
      backingFiles.length
        ? h("code", null, backingFiles.length === 1 ? backingFiles[0] : `${backingFiles[0]} (+${backingFiles.length - 1} more)`)
        : null
    ),
    h(
      "section",
      { "aria-label": "Run-learned axioms and constraints" },
      verified.length
        ? h(
            "div",
            null,
            h("h3", null, "Verified axioms"),
            h(
              "ul",
              null,
              verified.map((item, index) => h("li", { key: `${index}-${item}` }, displayMessage(item)))
            )
          )
        : null,
      derived.length
        ? h(
            "div",
            null,
            h("h3", null, "Derived constraints"),
            h(
              "ul",
              null,
              derived.map((item, index) => {
                const text = typeof item === "object" ? item.text : item;
                const appliesTo = typeof item === "object" ? item.applies_to : "";
                return h(
                  "li",
                  { key: `${index}-${text}` },
                  h("span", null, displayMessage(text || "")),
                  appliesTo ? h("small", null, `Applies to: ${displayMessage(appliesTo)}`) : null
                );
              })
            )
          )
        : null,
      retiredCount
        ? h("p", null, `${retiredCount} retired axiom${retiredCount === 1 ? "" : "s"} recorded in the run file.`)
        : null,
      backingFiles.length
        ? h(
            "div",
            { className: "project-home-axiom-files" },
            h("h3", null, "Backing files"),
            backingFiles.map((path) =>
              h(
                "button",
                {
                  key: path,
                  type: "button",
                  className: "inline-path-button",
                  disabled: !isPreviewableRepoPath(path),
                  onClick: () => onPreview && onPreview({ type: "file", value: path }),
                  title: isPreviewableRepoPath(path) ? `Preview ${path}` : "This file is not previewable from the workbench"
                },
                path
              )
            )
          )
        : null
    )
  );
}


function ProjectResearchMapPanel({ researchMap, liveMode, onPreview, onSave }) {
  const map = researchMap && typeof researchMap === "object" ? researchMap : {};
  const sections = Array.isArray(map.sections) ? map.sections : [];
  const nodes = Array.isArray(map.nodes) ? map.nodes : [];
  const edges = Array.isArray(map.edges) ? map.edges : [];
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const attentionSections = sections.filter((section) => /gap|warning|blocked|missing|needs|attention|review/i.test(`${section.status} ${section.summary}`));
  const nextSection = attentionSections[0] || sections.find((section) => /branch|next|handoff/i.test(`${section.id} ${section.label}`)) || sections[0] || {};
  const fileRefCount = Array.isArray(map.file_refs) ? map.file_refs.length : 0;
  const targetPath = map.target_path || "";
  const jsonPath = map.json_path || "";
  const graphCount = Number(map.graph_summary_count || 0);
  const meaning = map.project_meaning && typeof map.project_meaning === "object" ? map.project_meaning : {};
  const nextAction = map.next_action && typeof map.next_action === "object" ? map.next_action : {};
  const tensionCount = Number(map.tension_count ?? attentionSections.length);
  const branchCount = Number(map.branch_count ?? 0);
  const supportCount = Number(map.supported_point_count ?? 0);
  const workFileCount = Number(map.project_work_file_count ?? 0);
  const meaningRows = [
    ["Claim", meaning.thesis],
    ["Support", meaning.support],
    ["Limits", meaning.limits],
    ["Next", nextAction.detail || meaning.next || nextAction.label]
  ].filter((row) => row[1]);
  // The raw graph edges ("Orientation organized into Project work") are plumbing the reader can't act
  // on — the argument structure IS the sections, in order. De-jargon their labels to what they mean.
  const SECTION_LABELS = {
    orientation: "What we're investigating",
    project_work: "Working notes",
    strongest_support: "Strongest support",
    support: "Strongest support",
    tensions: "Tensions & weak spots",
    branches: "What's left to test",
    branches_to_test: "What's left to test",
    run_lessons: "What the runs taught us",
    synthesis: "Where it stands now",
    handoffs: "Outputs & handoffs"
  };
  const sectionLabel = (section) => SECTION_LABELS[String(section.id || "").toLowerCase()] || section.label || displayText(section.id || "Section");
  return h(
    "section",
    { className: "project-research-map", "aria-label": "Research map" },
    h(
      "div",
      { className: "project-research-map-head" },
      h("span", { className: "eyebrow" }, "Research map"),
      h("h3", null, "What this project means now"),
      h("p", null, map.summary || "Map the current claim, support, limits, and next useful check."),
      h(
        "div",
        { className: "project-research-map-actions" },
        targetPath
          ? h(
              "button",
              { type: "button", className: "copy-button", onClick: () => onPreview && onPreview({ type: "file", value: targetPath }) },
              "Preview map"
            )
          : null,
        jsonPath
          ? h(
              "button",
              { type: "button", className: "copy-button", onClick: () => onPreview && onPreview({ type: "file", value: jsonPath }) },
              "Preview data"
            )
          : null,
        h(
          "button",
          { type: "button", className: "copy-button primary", disabled: !liveMode, onClick: onSave },
          "Save map"
        )
      )
    ),
    meaningRows.length
      ? h(
          "div",
          { className: "project-research-map-meaning", "aria-label": "Project meaning" },
          meaningRows.map(([label, value]) =>
            h(
              "div",
              { key: label },
              h("span", null, label),
              h("p", null, shortText(value, label === "Claim" ? 260 : 190))
            )
          )
        )
      : null,
    (supportCount + tensionCount + branchCount + (workFileCount || fileRefCount) + graphCount) > 0
      ? h(
          "div",
          { className: "project-research-map-strip", "aria-label": "Research map summary" },
          h("div", null, h("span", null, "Support"), h("strong", null, `${supportCount}`), h("small", null, "points")),
          h("div", null, h("span", null, "Tensions"), h("strong", null, `${tensionCount}`), h("small", null, "to review")),
          h("div", null, h("span", null, "Branches"), h("strong", null, `${branchCount}`), h("small", null, "to test")),
          h("div", null, h("span", null, "Work files"), h("strong", null, `${workFileCount || fileRefCount}`), h("small", null, "linked")),
          h("div", null, h("span", null, "Graph"), h("strong", null, `${graphCount}`), h("small", null, graphCount === 1 ? "summary" : "summaries"))
        )
      : null,
    sections.length
      ? h(
          "div",
          { className: "research-map-sections", "aria-label": "Research map sections" },
          sections.map((section) => {
            const details = (Array.isArray(section.details) ? section.details : []).filter(Boolean);
            // Sections carry a `files` array of {label, path} — these are the inspect links. Keep only
            // real, previewable files (drop directories like the leanmill folder).
            const files = (Array.isArray(section.files) ? section.files : []).filter(
              (f) => f && f.path && /\.[a-z0-9]+$/i.test(String(f.path)) && isPreviewableRepoPath(f.path)
            );
            return h(
              "div",
              { className: "research-map-section", key: section.id || section.label },
              h(
                "div",
                { className: "research-map-section-head" },
                h("span", { className: "research-map-section-label" }, sectionLabel(section)),
                h(StatusDot, { status: section.status })
              ),
              section.summary ? h("p", { className: "research-map-section-summary" }, displayMessage(section.summary)) : null,
              details.length || files.length
                ? h(
                    "details",
                    { className: "research-map-section-more create-disclosure" },
                    h("summary", null, details.length ? "Read the detail" : `Open the ${files.length === 1 ? "file" : "files"}`),
                    h(
                      "div",
                      { className: "create-disclosure-body" },
                      details.map((detail, index) => h("p", { key: index, className: "research-map-detail-line" }, displayMessage(detail))),
                      files.length
                        ? h(
                            "div",
                            { className: "research-map-section-files" },
                            files.map((f) =>
                              h(
                                "button",
                                {
                                  type: "button",
                                  key: f.path,
                                  className: "evidence-preview-link",
                                  onClick: () => onPreview && onPreview({ type: "file", value: f.path })
                                },
                                `Open ${displayText(f.label) || sourceBasename(f.path)}`
                              )
                            )
                          )
                        : null
                    )
                  )
                : null
            );
          })
        )
      : (supportCount + tensionCount + branchCount + graphCount) === 0 && !meaningRows.length
        ? h(MText, { c: "dimmed", fz: "sm" }, "This map fills in as you record support, tensions, and checks. Use Save map to capture the current project state.")
        : null
  );
}

function projectObjectFailure(contract) {
  if (!contract || typeof contract !== "object") return {};
  const compactFailures = Array.isArray(contract.failed_checks) ? contract.failed_checks.filter(Boolean) : [];
  if (compactFailures.length) return compactFailures[0] || {};
  const checks = Array.isArray(contract.checks) ? contract.checks : [];
  return checks.find((check) => check && check.ok === false) || {};
}

function projectObjectFailureDetail(contract, fallback) {
  const failure = projectObjectFailure(contract);
  const label = displayText(failure.label || failure.id || "");
  const detail = displayMessage(failure.detail || "");
  if (label && detail) return `${label}: ${detail}`;
  return detail || label || fallback;
}

function ProjectHomeSummary({ snapshot, runHistory, traceContext, workflowContext, reportContext, receiptHistory, claimSupport, sourceList, pendingEditorItems, liveMode, onOpenDetail, onInspectItem, onPreview, onDraftFormalTarget, onSaveResearchMap }) {
  const rows = (snapshot && snapshot.rows) || [];
  const projectState = (workflowContext && workflowContext.project_state) || {};
  const claimRow = rowByLabel(rows, "Bounded claim");
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const assumptionsRow = rowByLabel(rows, "Assumptions and constraints");
  const runRow = rowByLabel(rows, "Run readiness");
  const reportRow = rowByLabel(rows, "Report readiness");
  const falsifierRow = rowByLabel(rows, "Next falsifier");
  const summary = (runHistory && runHistory.summary) || {};
  const latest = (runHistory && runHistory.latest_eval) || {};
  const projectSlug = (projectState && projectState.project) || (snapshot && snapshot.project) || "";
  const rubricSlug = (projectState && projectState.rubric) || (snapshot && snapshot.rubric) || projectSlug;
  const stateRun = projectState.run || {};
  const stateSources = projectState.sources || {};
  const stateSourceHealth = projectState.source_health || {};
  const stateEvidence = projectState.evidence || {};
  const stateAssumptions = projectState.assumptions || {};
  const stateAxioms = projectState.axioms || {};
  const formalizationState = projectState.formalization || {};
  const researchMap = projectState.research_map || {};
  const stateAdmission = projectState.admission || {};
  const stateReport = projectState.report || {};
  const stateCharter = projectState.charter || {};
  const projectObjectContract =
    workflowContext && workflowContext.project_object_contract && typeof workflowContext.project_object_contract === "object"
      ? workflowContext.project_object_contract
      : projectState.project_object_contract && typeof projectState.project_object_contract === "object"
        ? projectState.project_object_contract
        : {};
  const score = summary.latest_score === undefined || summary.latest_score === null ? "none" : String(summary.latest_score);
  const runLabel = summary.latest_run_id ? `${summary.latest_run_id} / ${summary.latest_iteration ?? 0}` : "not run";
  const thesisText = (projectState.thesis && projectState.thesis.text) || (claimRow ? thesisLead(claimRow.detail) : "No thesis is recorded in the project brief.");
  const charterStatus = stateCharter.status || "missing";
  const charterPath = stateCharter.file || (projectSlug ? `projects/${projectSlug}/project_charter.md` : "");
  const charterExists = stateCharter.exists !== false && charterStatus !== "missing";
  const changeText =
    (projectState.change_test && projectState.change_test.text) ||
    (falsifierRow ? falsifierLead(falsifierRow.detail) || itemStatus(falsifierRow) : "No change test recorded.");
  const sourceState = stateSources.status || (sourceRow ? itemStatus(sourceRow) : "source missing");
  const sourceHealthIssueCount = Number(stateSourceHealth.issue_count || 0);
  const sourceHealthState = stateSourceHealth.status || "";
  const sourceHealthValue = sourceHealthIssueCount
    ? `${sourceHealthIssueCount} warning${sourceHealthIssueCount === 1 ? "" : "s"}`
    : sourceHealthState ? displayText(sourceHealthState) : "not loaded";
  const evidenceState = stateEvidence.status || (evidenceRow ? itemStatus(evidenceRow) : "evidence missing");
  const assumptionState = stateAssumptions.status || (assumptionsRow ? itemStatus(assumptionsRow) : "not loaded");
  const assumptionDetail = stateAssumptions.summary || (assumptionsRow ? itemDetail(assumptionsRow) : "No assumptions or constraints file is loaded for this project.");
  const axiomState = stateAxioms.status || "not loaded";
  const axiomDetail = stateAxioms.summary || "No run-learned axioms or derived constraints are loaded yet.";
  const admissionBlockers = Array.isArray(stateAdmission.blockers) ? stateAdmission.blockers.filter(Boolean) : [];
  const admissionState = stateAdmission.display_status || displayText(stateAdmission.status || "not loaded");
  const admissionDetail =
    admissionBlockers.length && admissionBlockers[0].next_command
      ? admissionBlockers[0].next_command
      : stateAdmission.recommended_first_command || "Run readiness has not been checked yet.";
  const [admissionWorkspace, admissionSubsection] = admissionDestination(stateAdmission, projectState);
  const runScore = stateRun.latest_score === undefined || stateRun.latest_score === null ? score : String(stateRun.latest_score);
  const runStatus = stateRun.status || "";
  const runValue = runScore === "none" && runStatus ? displayText(runStatus) : `Score ${runScore}`;
  const runWeakestPoint = stateRun.latest_weakest_point || latest.weakest_point || (runRow ? itemDetail(runRow) : runLabel);
  const runBaseDetail = stateRun.summary || runWeakestPoint;
  const runCompressionAlignment = stateRun.compression_controller_alignment || {};
  const runCompressionLabel = stateRun.compression_progress_label || "";
  const runCompressionDetail = runCompressionAlignment.summary || stateRun.compression_progress_summary || "";
  const runDetail = runCompressionLabel || runCompressionDetail
    ? `${runBaseDetail} Explanation: ${runCompressionLabel || displayText(stateRun.compression_progress_recommendation || "not measured")}. ${runCompressionDetail}`.trim()
    : runBaseDetail;
  const reportState = stateReport.status || (reportRow ? itemStatus(reportRow) : reportStatusLabel(snapshot.report_status, snapshot.display_report_status));
  const reportDetail = stateReport.summary || (reportRow ? itemDetail(reportRow) : "Report readiness has not been loaded.");
  const reviewState = projectState.review || {};
  const recentChanges = projectState.recent_changes || {};
  const projectFiles = projectState.files || {};
  const receiptCount = Number(recentChanges.receipt_count || reviewState.receipt_count || (receiptHistory && receiptHistory.receipt_count) || 0);
  const latestReview = recentChanges.latest_review || reviewState.latest_review || {};
  const latestNextStep = recentChanges.latest_next_step || reviewState.latest_next_step || {};
  const latestSourceChange = recentChanges.latest_source_or_evidence_change || {};
  const nextInspection = recentChanges.next_inspection && typeof recentChanges.next_inspection === "object" ? recentChanges.next_inspection : {};
  const substantiveInspection = recentChanges.substantive_inspection && typeof recentChanges.substantive_inspection === "object" ? recentChanges.substantive_inspection : {};
  const latestReviewText = latestReview.summary || latestReview.decision || latestReview.label || "No review saved yet.";
  const latestNextStepText = latestNextStep.summary || latestNextStep.action || latestNextStep.label || "No next step saved yet.";
  const latestSourceChangeText = latestSourceChange.summary || latestSourceChange.label || "No source or evidence change saved yet.";
  const latestReceiptPath =
    recentChanges.latest_receipt_path ||
    reviewState.latest_receipt ||
    latestReview.receipt_path ||
    latestReview.path ||
    latestNextStep.receipt_path ||
    latestNextStep.path ||
    "";
  const latestSourceArtifactPath = latestSourceChange.artifact_path || "";
  const latestSourceArtifactPreviewPath = previewableRepoPath(latestSourceArtifactPath);
  const latestInspectionPreviewPath = previewableRepoPath(nextInspection.preview_path || "");
  const substantiveInspectionPreviewPath = previewableRepoPath(substantiveInspection.preview_path || "");
  const showSubstantiveInspection = Boolean(
    substantiveInspectionPreviewPath && substantiveInspectionPreviewPath !== latestInspectionPreviewPath
  );
  const projectObjectLoaded = Boolean(projectObjectContract.schema);
  const projectObjectOk = projectObjectLoaded && projectObjectContract.ok !== false;
  const projectObjectFailedCount = Number(projectObjectContract.failed_count || 0);
  const projectObjectFailureText = projectObjectFailureDetail(projectObjectContract, "Project state does not agree across the workbench surfaces.");
  const projectObjectCard = {
    label: "Project state",
    value: projectObjectLoaded
      ? projectObjectOk
        ? "consistent"
        : projectObjectFailedCount
          ? `${projectObjectFailedCount} to review`
          : "needs review"
      : "not run yet",
    detail: projectObjectLoaded
      ? projectObjectOk
        ? "The thesis, files, runs, and saved history all agree with each other."
        : projectObjectFailureText
      : "Start the local server to check the project's state.",
    tone: projectObjectLoaded ? (projectObjectOk ? "ready" : "attention") : "neutral",
    action: projectObjectOk ? "View" : "Review",
    onClick: () => onOpenDetail && onOpenDetail("overview", "Overview")
  };
  const facts = [
    {
      label: "Project charter",
      value: displayText(charterStatus),
      detail: stateCharter.summary || "The project charter records the question, thesis, scope limits, and change test used by project runs.",
      tone: charterExists ? "ready" : "attention",
      action: charterExists ? "Preview charter" : "Open setup",
      onClick: () => {
        if (charterExists && charterPath && onPreview) onPreview({ type: "file", value: charterPath });
        else onOpenDetail && onOpenDetail("overview", "Charter");
      }
    },
    {
      label: "Thesis",
      value: claimRow ? itemStatus(claimRow) : "missing",
      detail: thesisText,
      tone: claimRow ? statusClass(claimRow) : "attention",
      action: "Open thesis",
      onClick: () => onOpenDetail && onOpenDetail("overview", "Thesis")
    },
    {
      label: "Evidence",
      value: `${sourceState} / ${evidenceState}`,
      detail: stateEvidence.summary || (evidenceRow ? itemDetail(evidenceRow) : "Attach original files and build the evidence summary before relying on the project."),
      tone: (sourceRow && sourceRow.kind === "attention") || (evidenceRow && evidenceRow.kind === "attention") ? "attention" : "ready",
      action: "Open files",
      onClick: () => onOpenDetail && onOpenDetail("sources", "Prepare files")
    },
    {
      label: "File and evidence warnings",
      value: sourceHealthValue,
      detail: stateSourceHealth.summary || "File/evidence warning state is not loaded.",
      tone: sourceHealthIssueCount ? "attention" : sourceHealthState ? "ready" : "neutral",
      action: sourceHealthIssueCount ? "Open fixes" : "Open status",
      onClick: () => onOpenDetail && onOpenDetail(sourceHealthIssueCount ? "run" : "overview", sourceHealthIssueCount ? "Fix warnings" : "Overview")
    },
    {
      label: "Assumptions",
      value: assumptionState,
      detail: assumptionDetail,
      tone: assumptionState === "not loaded" || (assumptionsRow && assumptionsRow.kind === "attention") ? "attention" : "ready",
      action: "Open constraints",
      onClick: () => {
        if (assumptionsRow && onInspectItem) onInspectItem(assumptionsRow.label);
        else onOpenDetail && onOpenDetail("overview", "Thesis");
      }
    },
    {
      label: "Axioms",
      value: axiomState,
      detail: axiomDetail,
      tone: axiomState === "recorded" ? "ready" : "neutral",
      action: "Open results",
      onClick: () => onOpenDetail && onOpenDetail("run", "Results")
    },
    {
      label: "Run readiness",
      value: admissionState,
      detail: admissionDetail,
      tone: stateAdmission.can_enter_kernel ? "ready" : "attention",
      action: stateAdmission.can_enter_kernel ? "Ready to run" : "Open first repair",
      onClick: () => onOpenDetail && onOpenDetail(admissionWorkspace, admissionSubsection)
    },
    {
      label: "Runs",
      value: runValue,
      detail: runDetail,
      tone: runRow && runRow.kind === "attention" ? "attention" : "neutral",
      action: "Open results",
      onClick: () => onOpenDetail && onOpenDetail("run", "Results")
    },
    {
      label: "Report",
      value: reportState,
      detail: reportDetail,
      tone: reportRow ? statusClass(reportRow) : snapshot.report_status === "blocked" ? "attention" : "neutral",
      action: "Check report",
      onClick: () => onOpenDetail && onOpenDetail("save", "Report readiness")
    }
  ];
  const workflowSteps = serverWorkflowSteps(workflowContext, onOpenDetail);
  const fallbackWorkflowSteps = projectWorkflowSteps({ snapshot, traceContext, reportContext, runHistory, receiptHistory, liveMode, onOpenDetail });
  const activeWorkflowSteps = workflowSteps.length ? workflowSteps : fallbackWorkflowSteps;
  const nextStep = (workflowContext && workflowContext.next_step) || (projectState && projectState.next_action) || {};
  const nextStepLabel = nextStep.label || "Open the next step";
  const jobs = [
    {
      label: "1",
      title: "Open or recover a project",
      detail: liveMode
        ? "Open any project with a project brief, or connect an existing folder before editing it."
        : "Start the local server to browse and recover project folders.",
      action: "Browse projects",
      tone: liveMode ? "ready" : "attention",
      onClick: () => onOpenDetail && onOpenDetail("projects", "Projects")
    },
    {
      label: "2",
      title: "Check evidence",
      detail: stateEvidence.summary || (evidenceRow ? itemDetail(evidenceRow) : "Inspect original files, the evidence summary, and assumptions before running."),
      action: "Prepare files",
      tone: (sourceRow && sourceRow.kind === "attention") || (evidenceRow && evidenceRow.kind === "attention") ? "attention" : "ready",
      onClick: () => onOpenDetail && onOpenDetail("sources", "Prepare files")
    },
    {
      label: "3",
      title: "Continue the project",
      detail: nextStep.detail || (
        stateAdmission.status
          ? `${admissionState}: ${admissionDetail}`
          : runRow ? itemDetail(runRow) : "Check readiness first; start a run only after the inputs are accepted."
      ),
      action: nextStepLabel,
      tone: nextStep.status === "needs attention"
        ? "attention"
        : stateAdmission.status ? (stateAdmission.can_enter_kernel ? "ready" : "attention") : runRow && runRow.kind === "attention" ? "attention" : "neutral",
      onClick: () => {
        const destination = (nextStep && nextStep.ui_destination) || {};
        onOpenDetail && onOpenDetail(
          destination.workspace || nextStep.workspace || "run",
          destination.subsection || nextStep.subsection || "Check readiness"
        );
      }
    },
    {
      label: "4",
      title: "Leave a handoff",
      detail: receiptCount
        ? `${receiptCount} saved project change${receiptCount === 1 ? "" : "s"} found. Save reviews and next steps here.`
        : "Save a review, a next step, or a project file so the next person can pick up cleanly.",
      action: "Review and save",
      tone: receiptCount ? "ready" : "neutral",
      onClick: () => onOpenDetail && onOpenDetail("review", "Save next step")
    }
  ];
  const workRail = [
    {
      label: "1",
      title: "Choose project",
      detail: "Open any project folder with a project brief.",
      action: "Projects",
      onClick: () => onOpenDetail && onOpenDetail("projects", "Projects")
    },
    {
      label: "2",
      title: "Read thesis",
      detail: "Check the thesis, caveats, and change test.",
      action: "Thesis",
      onClick: () => onOpenDetail && onOpenDetail("overview", "Thesis")
    },
    {
      label: "3",
      title: "Check support",
      detail: "Inspect original files, the evidence summary, and assumptions.",
      action: "Files",
      onClick: () => onOpenDetail && onOpenDetail("sources", "Prepare files")
    },
    {
      label: "4",
      title: "Continue work",
      detail: "Check readiness first, then start the project run.",
      action: "Runs",
      onClick: () => onOpenDetail && onOpenDetail("run", "Check readiness")
    },
    {
      label: "5",
      title: "Save review",
      detail: "Save the review, next step, and project file.",
      action: "Review",
      onClick: () => onOpenDetail && onOpenDetail("review", "Save review")
    }
  ];
  const noReviewText = "No review saved yet.";
  const noNextStepText = "No next step saved yet.";
  const noSourceChangeText = "No source or evidence change saved yet.";
  const recentWorkPreviewPath = substantiveInspectionPreviewPath || latestInspectionPreviewPath || latestSourceArtifactPreviewPath;
  const recentWorkTitle = receiptCount
    ? latestNextStepText !== noNextStepText
      ? "Latest next step"
      : latestSourceChangeText !== noSourceChangeText
        ? "Latest saved file"
        : latestReviewText !== noReviewText
          ? "Latest review"
          : "Saved work"
    : "No saved work yet";
  const recentWorkBody = receiptCount
    ? latestNextStepText !== noNextStepText
      ? latestNextStepText
      : latestSourceChangeText !== noSourceChangeText
        ? latestSourceChangeText
        : latestReviewText !== noReviewText
          ? latestReviewText
          : "Saved history is available."
    : "Save a review or next step so the project has a clear handoff.";
  const recentWorkSupport = nextInspection.reason || (
    nextInspection.label
      ? `Open next: ${nextInspection.label}`
      : latestSourceChangeText !== noSourceChangeText
        ? latestSourceChangeText
        : ""
  );
  const openRecentWork = () => {
    if (liveMode && recentWorkPreviewPath && onPreview) {
      onPreview({ type: "file", value: recentWorkPreviewPath });
      return;
    }
    onOpenDetail && onOpenDetail("review", "Saved history");
  };
  const HOME_NEXT = {
    sources: { title: "Prepare your evidence", cta: "Open evidence \u2192", to: ["sources", "Prepare files"] },
    run: { title: "Pressure-test your thesis", cta: "Test it \u2192", to: ["run", "Ready to run"] },
    save: { title: "Check whether you can trust the result", cta: "See the verdict \u2192", to: ["save", "Report readiness"] },
    review: { title: "Look at the open points", cta: "Open points \u2192", to: ["review", "Things to review"] },
    overview: { title: "Sharpen your thesis", cta: "My claim \u2192", to: ["overview", "Thesis"] }
  };
  const homeNext = HOME_NEXT[admissionWorkspace] || HOME_NEXT.run;
  const homeStandsWarn = /attention|block|weak|missing|support|needs|stale|invalid|not ready/i.test(`${reportState} ${admissionState}`);
  return h(
    "section",
    { className: "project-home", "aria-label": "Project home" },
    h(
      "div",
      { className: "home-head" },
      h(MTitle, { order: 2 }, humanProjectTitle(snapshot, claimRow)),
      h(MText, { c: "dimmed", mt: 6 }, thesisText),
      changeText
        ? h(MText, { c: "dimmed", fz: "sm", mt: 4 }, h(Term, { term: "what would change your mind" }, "What would change your mind"), `: ${changeText}`)
        : null,
      h(
        MGroup,
        { gap: "xs", mt: "md", align: "center" },
        h(MText, { fz: "sm", c: "dimmed" }, "Where it stands:"),
        h(StatusDot, { status: reportState })
      )
    ),
    h(
      "div",
      { className: "home-next" },
      h("span", { className: "eyebrow" }, "Do next"),
      h("strong", null, homeNext.title),
      h(
        "button",
        { type: "button", className: "copy-button primary", onClick: () => onOpenDetail && onOpenDetail(homeNext.to[0], homeNext.to[1]) },
        homeNext.cta
      )
    ),
    h(
      "nav",
      { className: "home-links", "aria-label": "Project sections" },
      [
        ["My claim", "overview", "Thesis"],
        ["Evidence", "sources", "Prepare files"],
        ["Test it", "run", "Ready to run"],
        ["Verdict", "save", "Report readiness"],
        ["History", "review", "Saved history"]
      ].map(([label, ws, sub]) =>
        h("button", { key: label, type: "button", className: "home-link", onClick: () => onOpenDetail && onOpenDetail(ws, sub) },
          h("span", { className: "home-link-icon", "aria-hidden": "true" }, navIcon(label, 17)),
          h("span", null, label))
      )
    ),
    receiptCount ? h("p", { className: "home-saved" }, `Last saved: ${latestNextStepText.length > 84 ? `${latestNextStepText.slice(0, 84).trim()}…` : latestNextStepText}`) : null,
    h(
      "details",
      { className: "create-disclosure" },
      h("summary", null, "See the research map \u2014 claim, support, and tensions"),
      h(ProjectResearchMapPanel, { researchMap, liveMode, onPreview, onSave: onSaveResearchMap })
    )
  );
}

function ProjectCreatePanel({ draft, setDraft, message, creating, liveMode, projects, projectFolders, projectCreateContract, startIntent = "", onCreate, onPreview, onNavigateWorkspace, onDraft, projectDraft, filePreview, filePreviewMessage }) {
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [docText, setDocText] = useState("");
  const pd = projectDraft || {};
  const handledStartIntentRef = useRef("");
  useEffect(() => {
    if (!liveMode || !startIntent || handledStartIntentRef.current === startIntent) return;
    handledStartIntentRef.current = startIntent;
    if (startIntent === "files") setUploadModalOpen(true);
  }, [liveMode, startIntent]);
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
  const rawPreviewFiles = (previewExistingFolder
    ? [
        ...(previewExistingFolder.source_preview_files || []),
        ...(previewExistingFolder.raw_preview_files || []),
        ...(previewExistingFolder.root_preview_files || [])
      ]
    : []
  ).filter(isPreviewableRepoPath);
  const workspacePreviewFiles = (previewExistingFolder && previewExistingFolder.workspace_preview_files || []).filter(isPreviewableRepoPath);
  const contextRows = previewExistingFolder
    ? [
        {
          label: "Original files",
          value: previewExistingFolder.raw_source_file_count || previewExistingFolder.raw_file_count || previewExistingFolder.root_source_file_count
            ? cappedCountText(
                previewExistingFolder.raw_source_file_count || previewExistingFolder.raw_file_count || previewExistingFolder.root_source_file_count,
                previewExistingFolder.raw_source_file_count_capped || previewExistingFolder.raw_file_count_capped || previewExistingFolder.root_source_file_count_capped
              )
            : "0",
          detail: rawPreviewFiles.length ? rawPreviewFiles.join("\n") : "No previewable original-file sample found."
        },
        {
          label: "Workspace files",
          value: previewExistingFolder.workspace_file_count
            ? cappedCountText(previewExistingFolder.workspace_file_count, previewExistingFolder.workspace_file_count_capped)
            : "0",
          detail: workspacePreviewFiles.length ? workspacePreviewFiles.join("\n") : "No previewable workspace sample found."
        },
        {
          label: "Project brief",
          value: previewExistingFolder.intake_count ? String(previewExistingFolder.intake_count) : "missing",
          detail: previewCanReceiveIntake ? "This folder can receive a project brief." : "Pick a folder without a project brief."
        }
      ]
    : [];
  const projectCreateTemplates = Array.isArray(projectCreateContract && projectCreateContract.write_path_templates)
    ? projectCreateContract.write_path_templates
    : [];
  const addIntakeMode = Boolean(project && projectCanReceiveIntake);
  const createActionLabel = addIntakeMode ? "Save project brief" : "Create project";
  const createWriteTitle = addIntakeMode ? "What saving changes" : "What creating changes";
  const createNoChangeBoundary = addIntakeMode
    ? "Previewing files and editing the draft does not write project files. Saving writes only the listed project files."
    : "Suggestions and field edits stay in the browser. Creating writes only the listed project folder files.";
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
              `projects/${previewProject}/project_charter.md`,
              `projects/${previewProject}/${previewProject}_intake.json`
            ]
          : [])
      ]
    : [];
  const pendingCreatePaths = contractCreatePaths.length ? contractCreatePaths : fallbackCreatePaths;
  const pendingCreatePathValues = writePathsFromItems(pendingCreatePaths);
  const recoveryPayload = draft.recovery_payload && draft.recovery_payload.project === previewProject ? draft.recovery_payload : null;
  const recoverySummary = recoveryPayload && recoveryPayload.recovery_summary && typeof recoveryPayload.recovery_summary === "object"
    ? recoveryPayload.recovery_summary
    : {};
  const recoveryAfterConnectSteps = Array.isArray(recoveryPayload && recoveryPayload.after_connect_steps)
    ? recoveryPayload.after_connect_steps.filter(Boolean)
    : [];
  const recoveryCandidateFiles = Array.isArray(recoveryPayload && recoveryPayload.candidate_files)
    ? recoveryPayload.candidate_files.filter((file) => file && file.path)
    : [];
  const addIntakeBoundary = (recoveryPayload && (
    recoveryPayload.add_intake_write_boundary ||
    ((recoveryPayload.add_intake_action || {}).write_boundary)
  )) || null;
  const baseAddIntakeWritePaths = addIntakeBoundary && Array.isArray(addIntakeBoundary.write_paths)
    ? addIntakeBoundary.write_paths.filter(Boolean)
    : pendingCreatePathValues;
  const draftSourceLines = uniqueTextLines(draft.source_refs_text);
  const draftEvidenceLines = uniqueTextLines(draft.evidence_refs_text);
  const draftCaveatLines = uniqueTextLines(draft.non_claims_text);
  const uploadedSources = Array.isArray(draft.uploaded_sources) ? draft.uploaded_sources.filter(Boolean) : [];
  const uploadedSourcePaths = uploadedSources.map((file) => `projects/${previewProject || "<project>"}/raw/${file.filename || "<file>"}`);
  const pendingCreatePathValuesWithUploads = uniqueLines([...pendingCreatePathValues, ...uploadedSourcePaths.filter((path) => !path.includes("<"))]);
  const addIntakeWritePaths = uniqueLines([...baseAddIntakeWritePaths, ...uploadedSourcePaths.filter((path) => !path.includes("<"))]);
  const uploadedInvalidCount = uploadedSources.filter((file) => !SOURCE_IMPORT_FILENAME_RE.test(String(file.filename || "")) || !String(file.body || "").trim()).length;
  const uploadedEvidenceCount = uploadedSources.filter((file) => file.source_type === "source_evidence").length;
  const intakeTarget = pendingCreatePathValuesWithUploads.find((path) => String(path || "").includes("_intake.json")) || "";
  const draftedFieldCount = [
    draft.task,
    draft.bounded_claim,
    draft.next_falsifier,
    draft.source_refs_text,
    draft.evidence_refs_text
  ].filter((value) => String(value || "").trim()).length;
  const recoverySummaryCards = previewExistingFolder
    ? [
        {
          label: "What we found",
          value: recoverySummary.drafted_from_file_count !== undefined
            ? `${recoverySummary.drafted_from_file_count} useful file${Number(recoverySummary.drafted_from_file_count) === 1 ? "" : "s"}`
            : projectInventoryFileSummary(previewExistingFolder, {}),
          detail: recoverySummary.folder || previewExistingFolder.project_dir || `projects/${previewProject}`
        },
        {
          label: "Draft ready",
          value: `${draftedFieldCount}/5 fields`,
          detail: recoveryPayload && recoveryPayload.summary ? recoveryPayload.summary : "Task, thesis, change test, original files, evidence summaries."
        },
        {
          label: "Evidence to connect",
          value: recoveryPayload
            ? `${recoveryPayload.evidence_ref_count || 0} evidence summar${Number(recoveryPayload.evidence_ref_count || 0) === 1 ? "y" : "ies"} / ${recoveryPayload.source_ref_count || 0} original file${Number(recoveryPayload.source_ref_count || 0) === 1 ? "" : "s"}`
            : `${draftEvidenceLines.length} evidence summar${draftEvidenceLines.length === 1 ? "y" : "ies"} / ${draftSourceLines.length} original file${draftSourceLines.length === 1 ? "" : "s"}`,
          detail: draftCaveatLines.length ? `${draftCaveatLines.length} caveats carried into the intake.` : "Add caveats before saving if the folder has known limits."
        },
        {
          label: "Save target",
          value: intakeTarget ? "project brief" : "not ready",
          detail: recoverySummary.intake_target || intakeTarget || "Enter a valid project folder to see the project-brief path."
        }
      ]
    : [];
  const canCreate = Boolean(liveMode && !creating && validProject && !duplicateProject && hasRequiredFields);
  const canCreateWithUploads = Boolean(canCreate && uploadedInvalidCount === 0);
  const createTitle = !liveMode
    ? "Start the workbench server to create or connect a project"
    : duplicateProject
      ? "This project is already connected. Pick another folder."
      : !validProject
        ? "Use letters, numbers, dot, dash, or underscore"
        : !hasRequiredFields
          ? "Enter task, thesis, and what would change it"
          : uploadedInvalidCount
            ? "Fix uploaded file names or empty file text before creating the project"
          : addIntakeMode
            ? "Save the project brief for this folder"
            : "Create local project and project brief";
  const projectNote = duplicateProject
    ? "Existing project is already connected. Pick another folder."
    : projectCanReceiveIntake
      ? "Existing folder. Save the project brief and any missing source metadata."
    : project && !validProject
      ? "Use letters, numbers, dot, dash, or underscore."
      : "";
  // A name is only a real *suggestion* when it's derived from the question you've typed — not the empty
  // "new_project" fallback. Otherwise there's nothing to suggest, so we say how naming works instead.
  const hasRealSuggestion = Boolean(suggestedProject) && suggestedProject !== "new_project";
  const suggestionNote = duplicateSuggestion
    ? `${suggestedProject} is already connected.`
    : suggestionCanReceiveIntake && hasRealSuggestion
      ? `Suggested existing folder: ${suggestedProject}`
    : hasRealSuggestion
      ? `From your question: ${suggestedProject}`
    : "Leave blank to name it automatically from your question.";
  const commandProject = validProject ? project : (suggestedProject || "<project>");
  const commandBrief = String(draft.bounded_claim || draft.task || "").trim() || "one paragraph thesis question";
  const commandIntake = `projects/${commandProject}/${commandProject}_intake.json`;
  const setupCommandRows = [
    {
      label: "Scaffold from a paragraph",
      body: "Use this when you want the repository to draft the project structure and scoring guide from a short brief.",
      command: `make generate-gp PROJECT=${commandProject} BRIEF=${shellDoubleQuoted(commandBrief)} JUDGE_MODEL="$ZTARE_WORKBENCH_RUN_JUDGE_MODEL"`
    },
    {
      label: "Validate the project brief",
      body: "Use this before a run when you want to know whether files, labels, and the brief line up.",
      command: `ztare project intake validate --path ${commandIntake}`
    },
    {
      label: "Check original files",
      body: "Use this when the project folder exists but you are unsure whether the original files are ready.",
      command: `ztare project source-check --project ${commandProject} --json`
    },
    {
      label: "Explore substrate choices",
      body: "Use this when the question may need a different reasoning approach before a full project run.",
      command: "make autoresearch-substrate-recommend RECOMMENDER_MODE=cold AGENT_RECOMMENDER=1"
    }
  ];
  const setUploadedSources = (files) => setField("uploaded_sources", files);
  const addUploadedProjectFile = (file) => {
    const nextFile = {
      filename: file.filename || "",
      source_type: file.source_type || "source_evidence",
      body: file.body || ""
    };
    const existingIndex = uploadedSources.findIndex((item) => item.filename === nextFile.filename);
    const next = existingIndex >= 0
      ? uploadedSources.map((item, index) => (index === existingIndex ? nextFile : item))
      : [...uploadedSources, nextFile];
    setUploadedSources(next);
  };
  const updateUploadedProjectFile = (index, field, value) => {
    setUploadedSources(uploadedSources.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item));
  };
  const removeUploadedProjectFile = (index) => {
    setUploadedSources(uploadedSources.filter((_item, itemIndex) => itemIndex !== index));
  };
  return h(
    "section",
      { className: "project-create-panel", "aria-label": addIntakeMode ? "Create project brief for existing folder" : "Create project" },
    h(
      "div",
      { className: "project-create-head" },
      h("span", { className: "eyebrow" }, addIntakeMode ? "Existing folder" : "New project"),
      h("h2", null, addIntakeMode ? "Create the project brief" : "Create a project"),
        h("p", null, message || (addIntakeMode ? "Use the files already in this folder, then save the brief so you can edit and run it." : "Set up a new investigation: your question, your current answer, and what would change your mind."))
    ),
    uploadedSources.length
      ? h(
          "section",
          { className: "project-create-uploaded", "aria-label": "Uploaded project files" },
          h(
            "div",
            { className: "project-create-uploaded-head" },
            h("span", { className: "eyebrow" }, "Files to save"),
            h("strong", null, `${uploadedSources.length} file${uploadedSources.length === 1 ? "" : "s"} staged for raw/`),
            h("p", null, `${uploadedEvidenceCount} marked as evidence. These files are editable until you create the project.`)
          ),
          h(
            "div",
            { className: "project-create-uploaded-list" },
            uploadedSources.map((file, index) =>
              h(
                "article",
                { key: `${file.filename || "file"}:${index}` },
                h(
                  "label",
                  null,
                  h("span", null, "Filename"),
                  h("input", {
                    value: file.filename || "",
                    onInput: (event) => updateUploadedProjectFile(index, "filename", event.target.value)
                  })
                ),
        h(
          "label",
          null,
          h("span", null, "Purpose"),
                  h(
                    "select",
                    {
                      value: file.source_type || "source_evidence",
                      onChange: (event) => updateUploadedProjectFile(index, "source_type", event.target.value)
                    },
                    SOURCE_TYPES.map((value) => h("option", { key: value, value }, sourceTypeLabel(value)))
                  )
                ),
                h(
                  "label",
                  { className: "project-create-uploaded-body" },
                  h("span", null, "Text"),
                  h("textarea", {
                    value: file.body || "",
                    rows: 5,
                    onInput: (event) => updateUploadedProjectFile(index, "body", event.target.value)
                  })
                ),
                h(
                  "div",
                  { className: "project-create-uploaded-actions" },
                  h("code", null, uploadedSourcePaths[index] || ""),
                  h(
                    "button",
                    { type: "button", className: "copy-button", onClick: () => removeUploadedProjectFile(index) },
                    "Remove"
                  )
                )
              )
            )
          )
        )
      : null,
    previewExistingFolder
      ? h(
          "section",
          { className: "project-create-recovery-strip", "aria-label": "Project recovery summary" },
          recoverySummaryCards.map((card) =>
            h(
              "article",
              { key: card.label },
              h("span", null, card.label),
              h("strong", null, card.value),
              h("p", null, card.detail)
            )
          )
        )
      : null,
    h(
      MStack,
      { gap: "md" },
      // Activation — start from a document instead of a blank page. Paste a memo/paper/brief and a model
      // drafts the question, a testable thesis, the falsifier, and scope guards into the fields below.
      onDraft
        ? h(
            MBox,
            { className: "create-draft" },
            h(MText, { fw: 600, fz: "sm", mb: 2 }, "Start from a document"),
            h(MText, { c: "dimmed", fz: "xs", mb: 8 }, "Have a memo, paper, or brief? Paste it and the workbench drafts the question, a testable thesis, and the falsifier into the fields below — you refine, you don't start blank."),
            h(MTextarea, {
              autosize: true, minRows: 3, maxRows: 9, disabled: pd.running,
              placeholder: "Paste your memo / paper / brief here…",
              value: docText, onChange: (event) => setDocText(event.currentTarget.value),
            }),
            h(
              MGroup,
              { gap: "sm", align: "center", mt: 8 },
              h(MButton, {
                variant: "light", loading: !!pd.running, disabled: !!pd.running || !docText.trim() || !liveMode,
                onClick: () => onDraft(docText),
              }, pd.running ? "Drafting…" : "Draft the mandate for me"),
              pd.error ? h(MText, { c: "red", fz: "xs" }, String(pd.error)) : null,
              (pd.result && pd.result.ok) ? h(MText, { c: "dimmed", fz: "xs" }, "Drafted below — review and edit before you create.") : null
            )
          )
        : null,
      h(MTextInput, {
        label: "Project name",
        placeholder: "billing_review",
        value: draft.project,
        onChange: (event) => setField("project", event.currentTarget.value),
        description: projectNote || suggestionNote,
        rightSectionWidth: 116,
        // Only offer "Use this name" when we actually derived one from the question — never to fill "new_project".
        rightSection: hasRealSuggestion && !duplicateSuggestion && suggestedProject !== draft.project
          ? h(MButton, { size: "compact-xs", variant: "subtle", disabled: creating, onClick: () => setField("project", suggestedProject) }, "Use this name")
          : null
      }),
      h(MTextInput, { label: "Question", withAsterisk: true, placeholder: "Check whether the cache flag caused the export failures…", value: draft.task, onChange: (event) => setField("task", event.currentTarget.value) }),
      h(MTextarea, { label: "Your current answer", withAsterisk: true, autosize: true, minRows: 2, placeholder: "What do you currently think is true?", value: draft.bounded_claim, onChange: (event) => setField("bounded_claim", event.currentTarget.value) }),
      h(MTextarea, { label: "What would change it", withAsterisk: true, autosize: true, minRows: 2, placeholder: "What evidence would make you revise or reject it?", value: draft.next_falsifier, onChange: (event) => setField("next_falsifier", event.currentTarget.value) }),
      h(
        MBox,
        null,
        h(MText, { fw: 600, fz: "sm", mb: 6 }, "Materials"),
        h(
          MGroup,
          { gap: "sm", align: "center" },
          h(MButton, { variant: "light", disabled: !liveMode, leftSection: h(IconUpload, { size: 16 }), onClick: () => setUploadModalOpen(true) }, "Upload files"),
          h(MText, { c: "dimmed", fz: "xs" }, uploadedSources.length ? `${uploadedSources.length} file${uploadedSources.length === 1 ? "" : "s"} staged` : "Drop Markdown or text files — no need to type paths.")
        )
      ),
      h(
        MAnchor,
        { component: "button", type: "button", fz: "sm", c: "indigo", onClick: () => setAdvancedOpen((open) => !open) },
        advancedOpen ? "Hide advanced" : "Advanced — notes, repo-path references, caveats"
      ),
      h(
        MCollapse,
        { in: advancedOpen },
        h(
          MStack,
          { gap: "md", pt: 4 },
          h(MTextarea, { label: "Notes", autosize: true, minRows: 2, placeholder: "optional context", value: draft.notes, onChange: (event) => setField("notes", event.currentTarget.value) }),
          h(MTextarea, { label: "Original file paths", description: "Reference existing repo paths instead of uploading.", autosize: true, minRows: 2, placeholder: "raw/memo.md, raw/transcript.txt", value: draft.source_refs_text, onChange: (event) => setField("source_refs_text", event.currentTarget.value) }),
          h(MTextarea, { label: "Evidence summary paths", autosize: true, minRows: 2, placeholder: "workspace/evidence.txt", value: draft.evidence_refs_text, onChange: (event) => setField("evidence_refs_text", event.currentTarget.value) }),
          h(MTextarea, { label: "Scope limits — what this isn't claiming", autosize: true, minRows: 2, placeholder: "one scope limit per line — e.g. not a real customer incident", value: draft.non_claims_text, onChange: (event) => setField("non_claims_text", event.currentTarget.value) })
        )
      )
    ),
    previewExistingFolder
      ? h(
          MoreDetail,
          { title: "Inspect existing files" },
          h(
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
        )
      : null,
    recoveryCandidateFiles.length
      ? h(
          MoreDetail,
          { title: `Recovered files (${recoveryCandidateFiles.length})` },
          h(
            "section",
            { className: "project-recovery-files", "aria-label": "Recovered project files" },
            h(
              "div",
              { className: "project-recovery-files-head" },
              h("span", { className: "eyebrow" }, "Recovered files"),
              h("strong", null, `${recoveryCandidateFiles.length} files suggested for this project brief`),
              h("p", null, "Review these files before saving the project brief. The original-file and evidence-summary lists above were suggested from this folder.")
            ),
            h(
              "div",
              { className: "project-recovery-file-list" },
              recoveryCandidateFiles.slice(0, 10).map((file) =>
                h(
                  "article",
                  { key: file.path },
                  h("div", null, h("strong", null, sourceBasename(file.path)), h("small", null, displayText(file.role || fileRoleLabel(file.path)))),
                  h("code", null, file.path),
                  h(
                    "div",
                    { className: "project-recovery-file-flags" },
                    file.binds_as_source ? h("span", null, "source") : null,
                    file.binds_as_evidence ? h("span", null, "evidence") : null,
                    file.previewable ? h("span", null, "previewable") : null
                  ),
                  file.previewable
                    ? h(
                        "button",
                        {
                          type: "button",
                          className: "copy-button",
                          disabled: !liveMode || !isPreviewableRepoPath(file.path),
                          onClick: () => onPreview && onPreview({ type: "file", value: file.path }),
                          title: liveMode ? `Preview ${file.path}` : "Start the workbench server to preview files"
                        },
                        "Preview"
                      )
                    : null
                )
              )
            )
          )
        )
      : null,
    recoveryAfterConnectSteps.length
      ? h(
          "section",
          { className: "project-recovery-next", "aria-label": "After connecting this project" },
          h("span", { className: "eyebrow" }, "After connecting"),
          h("strong", null, "What happens next"),
          h(
            "div",
            { className: "project-recovery-next-grid" },
            recoveryAfterConnectSteps.map((step, index) =>
              h(
                "article",
                { key: `${step.label || "step"}:${index}` },
                h("span", null, String(index + 1)),
                h("strong", null, displayText(step.label || "Next step")),
                h("p", null, displayMessage(step.detail || "")),
                step.workspace && step.subsection
                  ? h(
                      "button",
                      {
                        type: "button",
                        className: "copy-button",
                        onClick: () => onNavigateWorkspace && onNavigateWorkspace(step.workspace, step.subsection),
                        title: `Open ${displayText(step.subsection)}`
                      },
                      `Open ${displayText(step.subsection)}`
                    )
                  : null
              )
            )
          )
        )
      : null,
    h(
      MStack,
      { gap: "sm" },
      h(
        MText,
        { c: "dimmed", fz: "sm" },
        addIntakeMode
          ? "Saving writes a project brief (and any missing source metadata) into this folder. Nothing else is touched."
          : `Creating writes ${previewProject ? `projects/${previewProject}/` : "a new project folder"} — a charter and a project brief. Nothing else is touched; preview and download never write files.`
      ),
      h(
        "details",
        { className: "create-disclosure" },
        h("summary", null, "See the exact files this writes"),
        h(
          "div",
          { className: "create-disclosure-body" },
          pendingCreatePathValuesWithUploads.length
            ? pendingCreatePathValuesWithUploads.map((path) => h("code", { key: path }, path))
            : h(MText, { fz: "sm", c: "dimmed" }, "Enter a project name to preview the files.")
        )
      ),
      setupCommandRows.length
        ? h(
            "details",
            { className: "create-disclosure" },
            h("summary", null, "Prefer the terminal? Show the equivalent CLI commands"),
            h(
              "div",
              { className: "create-disclosure-body project-create-command-list" },
              setupCommandRows.map((row) =>
                h(
                  "article",
                  { key: row.label },
                  h("div", null, h("strong", null, row.label), h("p", null, row.body)),
                  h("code", null, row.command),
                  h(MButton, { size: "compact-xs", variant: "subtle", onClick: () => copyText(row.command) }, "Copy")
                )
              )
            )
          )
        : null,
      h(
        MGroup,
        { mt: "xs" },
        h(
          MButton,
          { size: "md", disabled: !canCreateWithUploads, loading: creating, onClick: onCreate, title: createTitle },
          creating ? (addIntakeMode ? "Connecting…" : "Creating…") : createActionLabel
        )
      )
    ),
    h(SourceFileDropModal, {
      open: uploadModalOpen,
      initialSourceType: "source_evidence",
      mode: "create_project",
      onClose: () => setUploadModalOpen(false),
      onUseFile: addUploadedProjectFile
    })
  );
}

function sourceWorkspaceDir(sourceList, project = "") {
  const rawDir = String((sourceList && sourceList.raw_dir) || (project ? `projects/${project}/raw` : ""));
  return rawDir.endsWith("/raw") ? rawDir.slice(0, -4) + "/workspace" : "";
}



function projectSlugFromProjectPath(path) {
  const match = String(path || "").match(/^projects\/([^/]+)\//);
  return match ? match[1] : "";
}

function editableProjectFileTarget(filePreview, snapshot) {
  const path = String((filePreview && filePreview.path) || "").trim();
  const project = String((snapshot && snapshot.project) || "").trim();
  if (!path || !project) return null;
  const rubric = String((snapshot && snapshot.rubric) || project).trim();
  if (path === `rubrics/${rubric}.json`) {
    return {
      kind: "scoring_guide",
      label: "Edit scoring guide",
      workspace: "run",
      subsection: "Ready to run",
      description: "The rubric the loop scores your thesis against — the bar each iteration has to clear. Toughen it to raise the standard.",
      readOnlyBoundary: "Opening the scoring-guide editor writes no files. Saving from that editor writes the scoring guide and saved history."
    };
  }
  if (projectSlugFromProjectPath(path) !== project) return null;
  if (path === `projects/${project}/project_charter.md`) {
    return {
      kind: "charter",
      label: "Open project charter",
      workspace: "overview",
      subsection: "Charter",
      description: "The project's charter — its scope, the anchors it's pinned to, and the rules the loop must respect while it works.",
      readOnlyBoundary: "Opening the project charter writes no files. Saving from that editor writes the charter and saved history."
    };
  }
  if (path === String((snapshot && snapshot.intake) || "")) {
    return {
      kind: "intake",
      label: "Edit project brief",
      workspace: "sources",
      subsection: "Project brief",
      description: "The project brief — the question you're investigating, your current answer, and what would change your mind. The loop's starting point.",
      readOnlyBoundary: "Opening the project-brief editor writes no files. Saving from that editor writes the project brief and saved history."
    };
  }
  if (path === `projects/${project}/thesis.md`) {
    return {
      kind: "thesis",
      label: "Open thesis",
      workspace: "overview",
      subsection: "Thesis",
      description: "The thesis as the loop reads it — the claim you're arguing, its scope, and the limits of what it asserts.",
      readOnlyBoundary: "Opening the thesis section writes no files. Edit the project thesis through the project-brief editor when the thesis or limits need to change."
    };
  }
  const rawPrefix = `projects/${project}/raw/`;
  if (path.startsWith(rawPrefix) && !path.endsWith("/source_type_map.json")) {
    return {
      kind: "source",
      label: "Edit file",
      workspace: "sources",
      subsection: "Edit file",
      relativeRawPath: path.slice(rawPrefix.length),
      description: "One of your source files — raw evidence the loop reads. Edit it, then re-compile so the loop sees your changes.",
      readOnlyBoundary: "Opening the file editor writes no files. Saving from that editor writes the file, its role map, and saved history."
    };
  }
  if (path === `projects/${project}/synthesis/report_support_contract.json`) {
    return {
      kind: "report_support",
      label: "How claims were checked",
      workspace: "save",
      subsection: "Report readiness",
      description: "The support behind the verdict: for every claim in the report, whether it's directly sourced, synthesized across several sources, or unsupported — the evidence trail the trust score is built on.",
      readOnlyBoundary: "Opening report readiness writes no files. Checking readiness, refreshing report inputs, or saving review uses the Report panel write boundaries."
    };
  }
  const evidenceFiles = [
    `projects/${project}/compiled_evidence_packet.json`,
    `projects/${project}/compiled_evidence.txt`,
    `projects/${project}/evidence.txt`,
    `projects/${project}/compiled_evidence_provenance.json`
  ];
  if (evidenceFiles.includes(path)) {
    return {
      kind: "evidence",
      label: "Open evidence summary",
      workspace: "overview",
      subsection: "Evidence summary",
      readOnlyBoundary: "Opening the evidence map writes no files. Evidence prep, fetch, and gap-justification actions keep their own write boundaries."
    };
  }
  const workspacePrefix = `projects/${project}/workspace/`;
  const sourceIndexFiles = [
    `${workspacePrefix}source_index.json`,
    `${workspacePrefix}source_index_receipt.json`
  ];
  if (sourceIndexFiles.includes(path) || path.startsWith(`${workspacePrefix}source_notes/`)) {
    return {
      kind: "source_index",
      label: "Open file status",
      workspace: "sources",
      subsection: "Prepare files",
      readOnlyBoundary: "Opening file status writes no files. Add file, edit file, and evidence-prep actions show their write boundaries before saving."
    };
  }
  if (
    path.startsWith(`${workspacePrefix}forensic_workbench_project_file_`) ||
    path.startsWith(`${workspacePrefix}forensic_workbench_case_file_`) ||
    path === `${workspacePrefix}forensic_workbench_latest_project_file_write.json` ||
    path === `${workspacePrefix}forensic_workbench_latest_case_file_write.json` ||
    path === `${workspacePrefix}forensic_workbench_project_files.jsonl` ||
    path === `${workspacePrefix}forensic_workbench_case_files.jsonl`
  ) {
    return {
      kind: "project_file",
      label: "Open project file",
      workspace: "save",
      subsection: "Project file",
      readOnlyBoundary: "Opening the project-file panel writes no files. Saving a new project file shows the target path, saved-history path, and no-change boundary first."
    };
  }
  if (
    path.startsWith(`${workspacePrefix}forensic_workbench_`)
  ) {
    return {
      kind: "receipt",
      label: "Open saved history",
      workspace: "review",
      subsection: "Saved history",
      readOnlyBoundary: "Opening saved history writes no files. Review and next-step saves use their own write boundaries."
    };
  }
  const evidenceGapFiles = [
    `${workspacePrefix}latest_evidence_gaps.json`,
    `${workspacePrefix}evidence_gap_action.json`,
    `${workspacePrefix}evidence_gap_brief.md`,
    `${workspacePrefix}evidence_gap_resolutions.json`
  ];
  if (evidenceGapFiles.includes(path)) {
    return {
      kind: "evidence_gap",
      label: "Handle evidence gap",
      workspace: "run",
      subsection: "Results",
      readOnlyBoundary: "Opening evidence-gap actions writes no files. Fetching evidence or saving a justification shows its write boundary before confirmation."
    };
  }
  const runFiles = [
    `projects/${project}/latest_eval_results.json`,
    `projects/${project}/eval_history.jsonl`,
    `projects/${project}/latest_probability_dag.json`,
    `${workspacePrefix}iteration_telemetry.jsonl`,
    `${workspacePrefix}derived_constraints.json`
  ];
  if (runFiles.includes(path)) {
    return {
      kind: "run_result",
      label: "Open run results",
      workspace: "run",
      subsection: "Results",
      readOnlyBoundary: "Opening run results writes no files. Follow-up evidence fetches, reviews, or next steps use their own write boundaries."
    };
  }
  return null;
}

function SourceImportPanel({ draft, setDraft, message, importing, event, liveMode, project, sourceList, sourceImportContract, onImport, onPreview, onAddToIntake, onOpenIntake, onOpenEvidenceGap }) {
  const setField = (field, value) => setDraft({ ...draft, [field]: value });
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
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
        ? "Start the workbench server to add a file"
    : duplicateFilename
      ? "This filename already exists. Open it in Files to edit."
      : !validFilename
        ? "Use a flat .md or .txt filename"
        : !hasBody
        ? "Enter a filename and source text"
        : "Save file and record";
  const filenameNote = duplicateFilename
    ? "Existing file. Open it in Files to edit."
    : filename && !validFilename
      ? "Use a flat .md or .txt filename."
      : "";
  const importedRefTarget = event && event.source_type === "source_evidence" ? "evidence summaries" : "original files";
  const stagedGapRecovery = Boolean(event && event.evidence_gap_staged);
  const stagedIntakeRef = Boolean(event && event.intake_ref_staged);
  const sourceResultNext = stagedGapRecovery
    ? stagedIntakeRef
      ? "Next: save the project brief, then save the evidence-gap justification."
      : `Next: add this file to ${importedRefTarget}, save the project brief, then save the evidence-gap justification.`
    : `Next: add this file to ${importedRefTarget}, then save the project brief.`;
  const importWritePaths = writePathsFromItems(pendingImportPaths);
  const importReceiptPath = receiptPathFromWriteItems(pendingImportPaths, "forensic_workbench_source_imports");
  const importLatestPath = receiptPathFromWriteItems(pendingImportPaths, "forensic_workbench_latest_source_import");
  const useUploadedFile = (file) => {
    setDraft({
      ...draft,
      filename: file.filename || "",
      source_type: file.source_type || draft.source_type || "source_evidence",
      artifact_kind: file.artifact_kind || draft.artifact_kind || "project_note",
      created_by: file.created_by || draft.created_by || "",
      body: file.body || "",
      evidence_gap: draft.evidence_gap || null
    });
  };
  // Read a dropped/picked local file into the form (real upload — the old "Upload file" button set
  // state nothing rendered). Text files only; its text fills the body and the name fills the filename.
  const readLocalFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setDraft({ ...draft, filename: file.name, body: String((ev.target && ev.target.result) || "") });
    reader.readAsText(file);
  };
  return h(
    "section",
    { className: "source-import-panel", "aria-label": "Add file" },
    message ? h("p", { className: "source-import-message" }, message) : null,
    // 1. Drop or choose a local file — reads its text straight into the form.
    h(
      "label",
      { className: `source-import-drop ${liveMode ? "" : "is-disabled"}` },
      h("input", {
        type: "file", accept: ".md,.txt,.csv,.json,.tsv,.log", disabled: !liveMode,
        onChange: (ev) => readLocalFile(ev.target.files && ev.target.files[0]),
      }),
      h("strong", null, "Drop a file here, or choose one"),
      h("span", null, ".md · .txt · .csv · .json — its text fills in below, ready to save")
    ),
    // 2. Or type it in. Filename + what kind of evidence it is.
    h(
      "div",
      { className: "source-import-fields" },
      h(
        "label",
        null,
        h("span", null, "Filename"),
        h("input", { value: draft.filename, onInput: (inputEvent) => setField("filename", inputEvent.target.value), placeholder: "source_note.md" }),
        filenameNote ? h("small", { className: "source-import-note attention" }, filenameNote) : null
      ),
      h(
        "label",
        null,
        h("span", null, "What kind of evidence"),
        h(
          "select",
          { value: draft.source_type, onChange: (inputEvent) => setField("source_type", inputEvent.target.value) },
          SOURCE_TYPES.map((value) =>
            h("option", { key: value, value }, sourceTypeLabel(value))
          )
        ),
        h("small", { className: "source-import-note" }, SOURCE_TYPE_HELP[draft.source_type] || SOURCE_TYPE_HELP.untyped)
      ),
      h("label", { className: "source-import-body" }, h("span", null, "Text"), h("textarea", { value: draft.body, onInput: (inputEvent) => setField("body", inputEvent.target.value), rows: 7, placeholder: "Paste the source text, or drop a file above." }))
    ),
    // Advanced provenance — tucked; most users don't need it.
    h(
      "details",
      { className: "source-import-more" },
      h("summary", null, "Provenance (optional)"),
      h(
        "div",
        { className: "source-import-fields" },
        h("label", null, h("span", null, "Kind of work"),
          h("select", { value: draft.artifact_kind || "project_note", onChange: (e) => setField("artifact_kind", e.target.value) },
            SOURCE_ARTIFACT_KINDS.map((value) => h("option", { key: value, value }, sourceArtifactKindLabel(value))))),
        h("label", null, h("span", null, "Created by"),
          h("input", { value: draft.created_by || "", onInput: (e) => setField("created_by", e.target.value), placeholder: "Codex, Claude Code, notebook, human" }))
      )
    ),
    h(
      "div",
      { className: "source-import-actions" },
      h("small", { className: "source-import-saveline" }, duplicateFilename ? "" : "Saves the file into your project's evidence, then compile to make it count."),
      h(
        "button",
        {
          type: "button",
          className: "chip primary",
          disabled: !canImport,
          onClick: onImport,
          title: importTitle
        },
        importing ? "Saving…" : "Save file"
      ),
      event
        ? h(
            "div",
            { className: "source-import-result" },
            h("strong", null, event.source_path || "file saved"),
            h("small", null, `${sourceArtifactKindLabel(event.artifact_kind || "project_note")}; ${sourceTypeLabel(event.source_type || "source")}; ${(event.source_check && event.source_check.accepted) ? "file review passed" : "file review needs attention"}`),
            h("p", null, sourceResultNext),
            h(SourceCheckDetail, { event }),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode || !event.source_path,
                onClick: () => onPreview && onPreview({ type: "file", value: event.source_path }),
                title: "Preview added file"
              },
              "Preview"
            ),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode || !event.source_path || stagedIntakeRef,
                onClick: () => onAddToIntake && onAddToIntake(event.source_path, event.source_type),
                title: stagedIntakeRef ? `Already staged in ${importedRefTarget}` : `Stage this path in ${importedRefTarget}`
              },
              stagedIntakeRef ? `Staged in ${importedRefTarget}` : `Add to ${importedRefTarget}`
            ),
            h(
              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode,
                onClick: () => onOpenIntake && onOpenIntake(),
                title: "Open the project-brief editor to review and save staged source paths"
              },
              "Open project brief"
            ),
            stagedGapRecovery
              ? h(
                  "button",
                  {
                    type: "button",
                    className: "copy-button",
                    disabled: !liveMode,
                    onClick: () => onOpenEvidenceGap && onOpenEvidenceGap(),
                    title: "Open the active evidence gap to review and save the staged justification"
                  },
                  "Open evidence gap"
                )
              : null
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
    ? `${invalidTypeCount} file purpose issue${invalidTypeCount === 1 ? "" : "s"}`
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
  const editWritePaths = writePathsFromItems(pendingEditPaths);
  const editReceiptPath = receiptPathFromWriteItems(pendingEditPaths, "forensic_workbench_source_edits");
  const editLatestPath = receiptPathFromWriteItems(pendingEditPaths, "forensic_workbench_latest_source_edit");
  return h(
    "section",
    { className: "raw-source-manager", "aria-label": "Project files" },
    h(
      "div",
      { className: "raw-source-head" },
      h("span", { className: "eyebrow" }, "Edit file"),
      h("h2", null, hasLoadedSource ? `Editing ${draft.relative_raw_path}` : "Open a project file"),
      h("p", null, message || (hasLoadedSource
        ? "Change the text or its purpose, then save."
        : "Pick a file below to edit its text or purpose."))
    ),
    // The file list is for picking a file. Once one's loaded, fold it away so the editor leads.
    h(
      "details",
      { className: "raw-source-switch", open: !hasLoadedSource },
      h(
        "summary",
        null,
        h("span", null, hasLoadedSource ? "Switch to another file" : "Choose a file"),
        h("strong", { className: invalidTypeCount ? "attention" : "" }, `${sourceCount || sources.length} files · ${sourceHealth}`)
      ),
      h(
        "div",
        { className: "raw-source-list-head" },
        h(
          "button",
          {
            type: "button",
            className: "copy-button",
            disabled: !liveMode,
            onClick: onReload,
            title: liveMode ? "Reload file list" : "Start the workbench server to load project files"
          },
          "Reload list"
        )
      ),
      sources.length
        ? sources.slice(0, 12).map((row) =>
            h(
              "div",
              { className: "raw-source-row", key: rawSourceRelative(row) || row.path },
              h("div", null, h("strong", null, rawSourceRelative(row) || row.path || "source"), h("small", null, sourceWorkSummary(row) || `${sourceTypeLabel(row.source_type || "untyped")} / ${row.chars || 0} chars`)),
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
        : h("p", null, liveMode ? "No project files loaded yet." : "Start the workbench server to inspect project files.")
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
            title: "File paths are selected from the list. Use Add file to create a new one."
          })
        ),
        h(
        "label",
        null,
          h("span", null, "Purpose"),
          h(
            "select",
            { value: draft.source_type, onChange: (inputEvent) => setField("source_type", inputEvent.target.value) },
            SOURCE_TYPES.map((value) => h("option", { key: value, value }, sourceTypeLabel(value)))
          ),
          h("small", { className: "source-import-note" }, SOURCE_TYPE_HELP[draft.source_type] || SOURCE_TYPE_HELP.untyped)
        ),
        h(
          "label",
          null,
          h("span", null, "Kind of work"),
          h(
            "select",
            { value: draft.artifact_kind || "project_note", onChange: (inputEvent) => setField("artifact_kind", inputEvent.target.value) },
            SOURCE_ARTIFACT_KINDS.map((value) => h("option", { key: value, value }, sourceArtifactKindLabel(value)))
          ),
          h("small", { className: "source-import-note" }, "Use this to keep notes, search summaries, reports, proof work, and computation outputs distinct.")
        ),
        h(
          "label",
          null,
          h("span", null, "Created by"),
          h("input", { value: draft.created_by || "", onInput: (inputEvent) => setField("created_by", inputEvent.target.value), placeholder: "Codex, Claude Code, notebook, human" }),
          h("small", { className: "source-import-note" }, "Optional. Leave blank for ordinary project files.")
        ),
        h("label", { className: "raw-source-body" }, h("span", null, "Text"), h("textarea", { value: draft.body, onInput: (inputEvent) => setField("body", inputEvent.target.value), rows: 8, placeholder: "Open a source to edit it here." }))
      ),
      h(
        "section",
        { className: `raw-source-pending ${changedFields.length ? "changed" : ""}`, "aria-label": "Unsaved source changes" },
        h("span", null, "Unsaved changes"),
        h("strong", null, changedFields.length ? `${changedFields.length} changed field${changedFields.length === 1 ? "" : "s"}` : "No changes"),
        h("p", null, changedFields.length ? changedFields.map(displayFieldName).join(", ") : "Open a file and edit the text or purpose before saving."),
        h("small", null, draft.relative_raw_path ? `Editing ${draft.relative_raw_path}` : "No file selected")
      ),
      h(CompactWritePreview, {
        title: "What this saves",
        writePaths: editWritePaths,
        receiptPath: editReceiptPath,
        latestPath: editLatestPath,
        noChangeBoundary: changedFields.length
          ? "Saving records the file text or purpose change."
          : "Opening and previewing a file does not change project files."
      }),
      h(
        "details",
        { className: "write-path-details" },
        h("summary", null, "Show exact files"),
        pendingPathPreview(
          "Files that may change",
          pendingEditPaths,
          "Open a file to preview the changed paths.",
          canSave
        )
      ),
      h(WriteBoundary, {
        writeLabel: "Save file writes the file text, purpose, and saved history.",
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
            title: canSave ? "Save file and write a record" : "Open a file and make a change before saving"
          },
          editing ? "Saving" : "Save file"
        ),
        event
          ? h(
              "div",
              { className: "raw-source-result" },
              h("strong", null, event.source_path || "file edited"),
              h("small", null, `${sourceArtifactKindLabel(event.artifact_kind || "project_note")}; ${sourceTypeLabel(event.source_type || "source")}; ${(event.source_check && event.source_check.accepted) ? "file review passed" : "file review needs attention"}`),
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

function charterDraftFromPayload(payload) {
  const draft = {
    path: (payload && payload.path) || "",
    text: (payload && payload.text) || "",
    editable: payload ? payload.editable !== false : true,
    validation: (payload && payload.validation) || null
  };
  return { ...draft, original: { ...draft } };
}

function charterChanged(draft) {
  if (!draft || !draft.original) return false;
  return String(draft.text || "") !== String(draft.original.text || "");
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
  const names = { source_refs_text: "original files", evidence_refs_text: "evidence summaries" };
  return names[value] || String(value || "").replace(/_text$/, "").replace(/_/g, " ");
}

function sourceDraftFields(draft) {
  if (!draft) return {};
  return {
    source_type: draft.source_type || "",
    artifact_kind: draft.artifact_kind || "",
    created_by: draft.created_by || "",
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
    { key: "source_refs", label: "Original files", rows: status.source_refs || [], type: "source" },
    { key: "evidence_refs", label: "Evidence summaries", rows: status.evidence_refs || [], type: "evidence" }
  ];

  return h(
    "section",
    { className: "intake-ref-status", "aria-label": "Project brief reference status" },
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
                        title: "Copy path"
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
  const saveTitle = draft && draft.editable === false ? "Project-local briefs only" : disabled ? "Load a live project brief first" : "Save project brief";
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
  const intakeWritePaths = writePathsFromItems(pendingIntakePaths);
  const intakeReceiptPath = receiptPathFromWriteItems(pendingIntakePaths, "forensic_workbench_intake_edits");
  const intakeLatestPath = receiptPathFromWriteItems(pendingIntakePaths, "forensic_workbench_latest_intake_edit");
  const canPreviewBrief = Boolean(draft && draft.path);
  return h(
    "section",
    { className: "intake-editor", "aria-label": "Project brief editor" },
    h(
      "div",
      { className: "intake-editor-head" },
      h("span", { className: "eyebrow" }, "Project brief"),
      h("h2", null, "Edit project brief"),
      h("p", null, message || (liveMode ? "Live edits write to the project brief and saved history." : "Start the workbench server to edit the project brief."))
    ),
    h(
      "section",
      { className: "handoff-card", "aria-label": "Current project brief file" },
      h(
        "div",
        null,
        h("span", null, "Current file"),
        h("code", null, draft && draft.path ? draft.path : "No live project brief loaded."),
        h(
          "p",
          null,
          intakeReceiptPath
            ? `Save writes this file and records the edit in ${intakeReceiptPath}.`
            : "Load a live project brief to see the write target and saved-history path."
        )
      ),
      h(
        "div",
        { className: "handoff-actions" },
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            disabled: !liveMode || !canPreviewBrief,
            onClick: () => onPreviewRef && onPreviewRef({ type: "file", value: draft.path }),
            title: liveMode ? "Preview the current project brief" : "Start the workbench server to preview files"
          },
          "Preview brief"
        ),
        intakeReceiptPath
          ? h(
              "button",
              {
                className: "copy-button",
                type: "button",
                disabled: !liveMode,
                onClick: () => onPreviewRef && onPreviewRef({ type: "receipt", value: intakeReceiptPath }),
                title: liveMode ? "Preview project-brief saved history" : "Start the workbench server to preview files"
              },
              "Saved history"
            )
          : null,
        intakeLatestPath
          ? h(
              "button",
              {
                className: "copy-button",
                type: "button",
                disabled: !liveMode,
                onClick: () => onPreviewRef && onPreviewRef({ type: "receipt", value: intakeLatestPath }),
                title: liveMode ? "Preview the latest saved project-brief copy" : "Start the workbench server to preview files"
              },
              "Latest copy"
            )
          : null
      )
    ),
    h(
      "div",
      { className: "intake-editor-grid" },
      h(
        "label",
        null,
        h("span", null, "Thesis"),
        h("textarea", {
          value: (draft && draft.bounded_claim) || "",
          onChange: update("bounded_claim"),
          disabled,
          "aria-label": "Thesis"
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
          "aria-label": "What would change the thesis"
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
        h("span", null, "Scope limits — what this isn't claiming"),
        h("textarea", {
          value: (draft && draft.non_claims_text) || "",
          onChange: update("non_claims_text"),
          disabled,
          placeholder: "one scope limit per line — e.g. not a real customer incident",
          "aria-label": "Scope limits — what this isn't claiming"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Original files"),
        h("textarea", {
          value: (draft && draft.source_refs_text) || "",
          onChange: update("source_refs_text"),
          disabled,
          "aria-label": "Original files"
        })
      ),
      h(
        "label",
        null,
        h("span", null, "Evidence summaries"),
        h("textarea", {
          value: (draft && draft.evidence_refs_text) || "",
          onChange: update("evidence_refs_text"),
          disabled,
          "aria-label": "Evidence summaries"
        })
      )
    ),
    h(IntakeRefStatus, { draft, liveMode, onPreview: onPreviewRef }),
    h(
      "section",
      { className: `intake-write-preview ${changedFields.length ? "changed" : ""}`, "aria-label": "Unsaved project brief changes" },
      h("span", null, "Unsaved changes"),
      h("strong", null, changedFields.length ? `${changedFields.length} changed field${changedFields.length === 1 ? "" : "s"}` : "No changes"),
      h("p", null, changedFields.length ? changedFields.map(displayFieldName).join(", ") : "Edit project-local fields before saving."),
      h("small", null, draft && draft.path ? `Editing ${draft.path}` : "No project brief selected")
    ),
    h(CompactWritePreview, {
      title: "What this saves",
      writePaths: intakeWritePaths,
      receiptPath: intakeReceiptPath,
      latestPath: intakeLatestPath,
      noChangeBoundary: changedFields.length
        ? "Saving updates the project brief and saves a record."
        : "Reload and file previews do not change project files."
    }),
    h(
      "details",
      { className: "write-path-details" },
      h("summary", null, "Show exact files"),
      pendingPathPreview(
        "Files that may change",
        pendingIntakePaths,
        "Load a project brief to preview the project and saved-history paths.",
        canSave
      )
    ),
    h(WriteBoundary, {
      writeLabel: "Save project brief writes the selected project file and saved history.",
      readLabel: "Reload and ref previews only read files from disk.",
      liveMode
    }),
    h(
      "div",
      { className: "intake-editor-actions" },
      h("code", null, draft && draft.path ? draft.path : "No live project brief loaded."),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          onClick: onReload,
          disabled: !liveMode,
          title: liveMode ? "Reload project brief from disk" : "Start the workbench server first"
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
        "Save project brief"
      )
    )
  );
}

function humanizeReceiptSummary(value) {
  // Clean kernel jargon, then collapse long repo paths to a readable file name so saved-history
  // rows read as plain sentences instead of path dumps.
  return displayMessage(String(value || ""))
    .replace(/\b(?:projects|rubrics|docs|src)\/\S+\/([^\s/]+)/g, "$1")
    .trim();
}

function TraceConsolePanel({ traceContext, message, liveMode, onPreviewSource, onOpenDetail }) {
  const kernel = (traceContext && traceContext.kernel_entry) || {};
  const plan = (traceContext && traceContext.plan_preview) || {};
  const surfaces = (traceContext && traceContext.surfaces) || {};
  const carrierRows = (traceContext && traceContext.carrier_chain) || [];
  const planRows = plan.dependency_order || [];
  const graphRows = (traceContext && traceContext.graph_carriers) || [];
  const nextCommands = (traceContext && traceContext.next_commands) || [];
  const sourcePaths = uniqueBackingFiles([
    surfaces.source_index_receipt_path ? { label: "File-index history", path: surfaces.source_index_receipt_path } : null,
    surfaces.compile_provenance_path ? { label: "Evidence provenance", path: surfaces.compile_provenance_path } : null,
    ...graphRows.flatMap((row) =>
      (row.source_artifacts || []).map((path) => ({ label: row.graph_kind || "Graph source", path }))
    )
  ]);
  const status = (traceContext && (traceContext.display_readiness || displayText(traceContext.readiness))) || "loading";
  const canRun = Boolean(kernel.can_enter_kernel || plan.status === "ready_for_bounded_run");
  const blockingRows = [
    ...carrierRows.filter((row) => row && row.blocking),
    ...planRows.filter((row) => row && /blocked|missing|failed|pending/i.test(`${row.status || ""} ${row.display_status || ""}`) && !row.model_calls)
  ].slice(0, 4);
  const firstLocalStep = planRows.find((row) => row && !row.model_calls && row.command) || null;
  const firstModelStep = planRows.find((row) => row && row.model_calls && row.command) || null;
  const nextActionTitle = canRun
    ? "Your claim is ready to test"
    : firstLocalStep
      ? "One thing to do first"
      : blockingRows.length
        ? "Something's blocking the test"
        : "Checking if it's ready…";
  const nextActionDetail = canRun
    ? "Run it whenever you're ready — it checks with you before using any paid models."
    : firstLocalStep
      ? displayMessage(firstLocalStep.description) || "There's a quick prep step before you can run."
      : blockingRows[0]
        ? displayMessage(blockingRows[0].description || blockingRows[0].display_surface || blockingRows[0].surface || blockingRows[0].status)
        : "Reading the project's current state.";
  const localStepCount = planRows.filter((row) => row && !row.model_calls).length;
  const modelStepCount = planRows.filter((row) => row && row.model_calls).length;

  return h(
    "section",
    { className: `trace-console ${canRun ? "ready" : "attention"}`, "aria-label": "Run readiness" },
    h(
      "div",
      { className: "trace-summary" },
      h("h2", null, nextActionTitle),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? nextActionDetail
            : "Start the workbench server to inspect live readiness.")
      ),
      canRun && onOpenDetail
        ? h(
            "button",
            { type: "button", className: "copy-button primary", onClick: () => onOpenDetail("run", "Ready to run") },
            "Run the test →"
          )
        : !canRun && firstLocalStep && onOpenDetail
          ? h(
              "button",
              { type: "button", className: "copy-button primary", onClick: () => onOpenDetail("run", "Check readiness") },
              "Do the prep step →"
            )
          : null,
      h(
        "p",
        { className: "trace-readyline" },
        h(Term, { term: "evidence" }, "Evidence"),
        ` ${surfaces.display_evidence_status || displayText(surfaces.evidence_status || "unknown")}`,
        localStepCount ? ` · ${localStepCount} thing${localStepCount === 1 ? "" : "s"} to do first` : "",
        modelStepCount ? " · it checks with you before using paid models" : ""
      )
    ),
    h(
      "div",
      { className: "trace-body" },
      !canRun && blockingRows.length
        ? h(
            "div",
            { className: "trace-section" },
            h("span", null, "Fix first"),
            blockingRows.map((row) =>
              h(
                "div",
                { className: "trace-plan-row attention", key: row.id || row.surface || row.description },
                h("strong", null, displayText(row.display_surface || row.id || row.surface || "Project input")),
                h("small", null, row.display_status || displayText(row.status || "needs attention")),
                h("p", null, displayMessage(row.description || row.detail) || "Fix this before you can test.")
              )
            )
          )
        : null,
      h(
        "details",
        { className: "create-disclosure" },
        h("summary", null, "Show the details — steps, files, and commands"),
        h(
          "div",
          { className: "create-disclosure-body" },
          h("p", { className: "detail-teach" }, "This is exactly what the test will do and read — here so you can check it, not because you need to act on it."),
          planRows.length ? h("p", { className: "detail-subhead" }, "Steps it runs, in order") : null,
          planRows.map((row) =>
            h(
              "div",
              { className: `trace-plan-row ${row.model_calls ? "model" : "local"}`, key: row.id || row.description },
              h("strong", null, row.model_calls ? "Pressure-test the claim" : displayText(row.id || "Preparation step")),
              h("small", null, row.model_calls ? "uses a model — asks you first" : "local check, no model"),
              h("p", null, row.description || displayText(row.status || "pending"))
            )
          ),
          sourcePaths.length ? h("p", { className: "detail-subhead" }, "Files it reads") : null,
          sourcePaths.map((item) =>
            h(
              "div",
              { className: "trace-file-row", key: item.path },
              h("strong", null, h(Term, { term: String(item.label || "").toLowerCase() }, item.label)),
              h("code", null, item.path),
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
              )
            )
          ),
          traceContext && traceContext.trace_command
            ? h(
                React.Fragment,
                null,
                h("p", { className: "detail-subhead" }, "The exact terminal command, if you'd rather run it yourself"),
                h("code", { className: "trace-command-line" }, traceContext.trace_command)
              )
            : null
        )
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
      h("h2", null, accepted ? "It's ready to run" : event ? "Not ready yet — a few things to fix" : "Is it ready to run?"),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "A quick local check before you spend any model budget — it doesn't call models or change your thesis."
            : "Start the workbench server to run this check.")
      ),
      canRun
        ? h(
            "button",
            { className: "copy-button primary", type: "button", disabled: !canRun, onClick: onRun, title: "Run the quick local check" },
            running ? "Checking…" : "Check it's ready"
          )
        : null
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
      : null,
    h(
      "details",
      { className: "create-disclosure" },
      h("summary", null, "What this check does and changes"),
      h(
        "div",
        { className: "create-disclosure-body" },
        h("p", { className: "detail-teach" }, "It runs the checks locally and writes a small record — no model calls, no change to your thesis."),
        pendingPathPreview("Files that may change", writePaths, "The check writes a small record.", Boolean(writePaths.length)),
        command ? h(React.Fragment, null, h("p", { className: "detail-subhead" }, "The exact command"), h("code", { className: "trace-command-line" }, command)) : null
      )
    )
  );
}

function ScoreSparkline({ iterations }) {
  const pts = (iterations || []).filter((it) => typeof it.score === "number");
  if (pts.length < 2) return null;
  const w = 320;
  const h = 64;
  const stepX = pts.length > 1 ? w / (pts.length - 1) : w;
  const yOf = (score) => h - 5 - (Math.max(0, Math.min(100, score)) / 100) * (h - 10);
  const line = pts.map((it, i) => `${(i * stepX).toFixed(1)},${yOf(it.score).toFixed(1)}`).join(" ");
  return h(
    "svg",
    { className: "score-spark", width: "100%", height: h, viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none", role: "img", "aria-label": "Score per round" },
    // 85 is the auto-evolve threshold — above it the rubric can toughen.
    h("line", { x1: 0, y1: yOf(85), x2: w, y2: yOf(85), stroke: "#dcdce4", strokeWidth: 1, strokeDasharray: "4 4" }),
    h("polyline", { points: line, fill: "none", stroke: "#4263eb", strokeWidth: 2, strokeLinejoin: "round" }),
    pts.map((it, i) =>
      h("circle", {
        key: i,
        cx: (i * stepX).toFixed(1),
        cy: yOf(it.score).toFixed(1),
        r: 3.2,
        fill: it.score_cap_reason ? "#d6a94f" : "#4263eb"
      })
    )
  );
}

function ScoreTrajectoryPanel({ trajectory, liveMode }) {
  const runs = (trajectory && trajectory.runs) || [];
  const withScores = runs.filter((run) => (run.iterations || []).some((it) => typeof it.score === "number"));
  if (!liveMode || !withScores.length) return null;
  return h(
    "section",
    { className: "score-trajectory", "aria-label": "Score trajectory" },
    h(
      "div",
      { className: "score-trajectory-head" },
      h("span", { className: "eyebrow" }, "Score over the run"),
      h("h2", null, "How the score moved"),
      h(
        "p",
        null,
        "Each round, the loop drafts a sharper version of your thesis and the judge scores it 0–100. A gold dot means a gate capped the score below what the judge gave — the claim over-reached on that round."
      )
    ),
    withScores.map((run) => {
      const capped = (run.iterations || []).filter((it) => it.score_cap_reason);
      return h(
        "div",
        { className: "score-run", key: run.run_id },
        h(
          "div",
          { className: "score-run-head" },
          h("strong", null, withScores.length > 1 ? `Run ${run.run_id}` : "This run"),
          h("span", { className: "score-run-stat" }, `${run.iteration_count} round${run.iteration_count === 1 ? "" : "s"}`),
          run.best_score != null ? h("span", { className: "score-run-best" }, `best ${run.best_score}`) : null,
          run.final_score != null ? h("span", { className: "score-run-final" }, `ended ${run.final_score}`) : null
        ),
        h(ScoreSparkline, { iterations: run.iterations }),
        capped.length
          ? h("p", { className: "score-cap-note" }, `${capped.length} round${capped.length === 1 ? "" : "s"} capped by a gate — e.g. ${displayMessage(capped[0].score_cap_reason)}`)
          : null
      );
    }),
    trajectory && trajectory.rubric_changed_vs_champion
      ? h(
          "p",
          { className: "score-rubric-flag" },
          "The rubric changed since your saved-best run — so a lower score here can mean a tougher bar, not a worse claim."
        )
      : null
  );
}

function RunHistoryPanel({ runHistory, message, liveMode, onPreview, onUseActionNote }) {
  const summary = (runHistory && runHistory.summary) || {};
  const latest = (runHistory && runHistory.latest_eval) || {};
  const synthesis = (runHistory && runHistory.synthesis_history) || {};
  const informationYield = (runHistory && runHistory.information_yield) || {};
  const compression = (runHistory && runHistory.compression_progress) || {};
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
    const surface = gap.required_surface ? ` Needed evidence: ${gap.required_surface}.` : "";
    const description = gap.description || "No gap detail recorded.";
    onUseActionNote(`Collect evidence for ${target}: ${description}${surface}`, "needs_source", "Evidence readiness");
  };
  const stageCompressionAction = () => {
    if (!compression || !onUseActionNote) return;
    const action = compression.next_action || {};
    const note = action.detail || compression.summary || "Review whether the latest run made the explanation simpler.";
    onUseActionNote(note, "next_step", "Compression progress");
  };
  const stageInformationYieldAction = () => {
    if (!informationYield || !onUseActionNote) return;
    const action = informationYield.next_action || {};
    const note = action.detail || informationYield.summary || informationYield.rationale || "Review whether the latest run taught the project enough to continue.";
    onUseActionNote(note, informationYield.action === "UNDERIDENTIFIED" ? "needs_source" : "next_step", "Truth-yield signal");
  };
  const informationYieldStatus = informationYield.status || "not_loaded";
  const informationYieldAction = informationYield.action ? displayText(informationYield.action) : "not loaded";
  const informationYieldMotion = Array.isArray(informationYield.motion_classes) && informationYield.motion_classes.length
    ? informationYield.motion_classes.map(displayText).join(", ")
    : "not recorded";
  const informationYieldScore = informationYield.score === undefined || informationYield.score === null ? "none" : String(informationYield.score);
  const compressionSourceRefs = Array.isArray(compression.source_refs) ? compression.source_refs.filter(Boolean) : [];
  const compressionStatus = compression.status || "no_signal";
  const compressionAdvice = compression.latest_iteration_advice || {};
  const compressionAlignment = compression.controller_alignment || {};
  const compressionAdviceLabel = compressionAdvice.recommendation
    ? displayText(compressionAdvice.recommendation)
    : displayText(compression.recommendation || "no signal");
  const loopActionLabel = compression.prior_loop_action ? displayText(compression.prior_loop_action) : "not recorded";
  const compressionWeight = typeof compression.future_progress_weight === "number"
    ? compression.future_progress_weight.toFixed(3)
    : "not available";
  const compressionEffort = typeof compression.total_effort_seconds === "number" && compression.total_effort_seconds > 0
    ? `${Math.round(compression.total_effort_seconds)}s`
    : "not available";
  const compressionCost = typeof compression.total_cost_usd === "number" && compression.total_cost_usd > 0
    ? `$${compression.total_cost_usd.toFixed(3)}`
    : "not available";
  const compressionProfile = Array.isArray(compression.complexity_runtime_profile)
    ? compression.complexity_runtime_profile.filter((point) => point && typeof point === "object")
    : [];
  const formatCompressionNumber = (value) => {
    if (typeof value !== "number" || !Number.isFinite(value)) return "not available";
    const abs = Math.abs(value);
    if (abs >= 100) return value.toFixed(1);
    if (abs >= 10) return value.toFixed(2);
    return value.toFixed(3);
  };
  const formatCompressionSeconds = (value) => {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "not available";
    if (value < 60) return `${Math.round(value)}s`;
    const minutes = value / 60;
    if (minutes < 60) return `${minutes.toFixed(minutes >= 10 ? 0 : 1)}m`;
    const hours = minutes / 60;
    return `${hours.toFixed(hours >= 10 ? 0 : 1)}h`;
  };
  const compressionProfileRows = compressionProfile.slice(-6).reverse().map((point, index, rows) => {
    const previous = rows[index + 1];
    const complexity = typeof point.complexity === "number" ? point.complexity : null;
    const previousComplexity = previous && typeof previous.complexity === "number" ? previous.complexity : null;
    const improved = complexity !== null && previousComplexity !== null && complexity < previousComplexity;
    const worsened = complexity !== null && previousComplexity !== null && complexity > previousComplexity;
    const delta = complexity !== null && previousComplexity !== null ? complexity - previousComplexity : null;
    return { point, complexity, improved, worsened, delta };
  });

  const latestScore = summary.latest_score;
  const hasScore = latestScore !== undefined && latestScore !== null;
  const weakest = latest.weakest_point || summary.latest_weakest_point || "";
  return h(
    "section",
    { className: "run-history-panel", "aria-label": "Results" },
    h(
      "div",
      { className: "run-history-summary" },
      h("h2", null, hasScore ? `Your claim scored ${latestScore}` : "You haven't tested this claim yet"),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? hasScore
              ? displayText(outcomeLabel)
              : "Run a test from Test it to see how your thesis holds up."
            : "Start the workbench server to see results.")
      ),
      hasScore && probability !== "not scored"
        ? h("p", { className: "trace-readyline" }, `Confidence it holds: ${probability} · ${scoreDeltaLabel}`)
        : null
    ),
    weakest
      ? h(
          "div",
          { className: "trace-section" },
          h("span", null, "Weakest point"),
          h("p", null, h(Teach, { text: displayText(weakest) })),
          onUseActionNote ? h("button", { className: "copy-button", type: "button", onClick: stageWeakestPoint }, "Make this my next step") : null
        )
      : null,
    gaps.length
      ? h(
          "div",
          { className: "trace-section" },
          h("span", null, `What's still unbacked (${gaps.length})`),
          gaps.slice(0, 4).map((gap, idx) =>
            h(
              "div",
              { className: "trace-plan-row attention", key: gap.target || idx },
              h("strong", null, h(Teach, { text: displayText(gap.target || "Evidence gap") })),
              gap.description ? h("p", null, h(Teach, { text: displayText(gap.description) })) : null,
              onUseActionNote ? h("button", { className: "copy-button", type: "button", onClick: () => stageGap(gap) }, "Collect this evidence") : null
            )
          )
        )
      : null,
    patterns.length
      ? h(
          "details",
          { className: "create-disclosure" },
          h("summary", null, `Patterns across runs (${patterns.length})`),
          h(
            "div",
            { className: "create-disclosure-body" },
            patterns.map((pt, idx) => h("p", { key: idx }, h("strong", null, `${pt.label}: `), h(Teach, { text: displayText(pt.text || "") })))
          )
        )
      : null
  );
}

function EvidenceSupportPanel({ claimSupport, message, evidenceGaps, evidenceGapMessage, evidenceGapDraft, setEvidenceGapDraft, evidenceGapRunning, evidenceGapEvent, evidenceFetchRunning, evidenceFetchEvent, liveMode, onPreview, onJustify, onFetch, onRefresh, onPrepareSource }) {
  const status = (claimSupport && claimSupport.status) || "loading";
  const displayStatus = (claimSupport && claimSupport.display_status) || displayText(status);
  const errors = (claimSupport && claimSupport.errors) || [];
  const sources = (claimSupport && claimSupport.source_context) || [];
  const rows = (claimSupport && claimSupport.rows) || [];
  const gapRows = (evidenceGaps && evidenceGaps.evidence_gaps) || [];
  const activeGapCount = Number((evidenceGaps && evidenceGaps.active_evidence_gap_count) || gapRows.length || 0);
  const gapSourcePath = (evidenceGaps && evidenceGaps.source_path) || "";
  const gapNextAction = (evidenceGaps && evidenceGaps.next_action) || {};
  const gapCommand = ((gapNextAction.next_action || {}).command) || (evidenceGaps && evidenceGaps.fetch_command) || "";
  const justifyWritePaths = Array.isArray(evidenceGaps && evidenceGaps.justify_write_paths)
    ? evidenceGaps.justify_write_paths.filter(Boolean)
    : [];
  const justifyReceiptPaths = Array.isArray(evidenceGaps && evidenceGaps.justify_receipt_paths)
    ? evidenceGaps.justify_receipt_paths.filter(Boolean)
    : [];
  const fetchWritePaths = Array.isArray(evidenceGaps && evidenceGaps.fetch_write_paths)
    ? evidenceGaps.fetch_write_paths.filter(Boolean)
    : [];
  const fetchReceiptPaths = Array.isArray(evidenceGaps && evidenceGaps.fetch_receipt_paths)
    ? evidenceGaps.fetch_receipt_paths.filter(Boolean)
    : [];
  const selectedGapIndex = evidenceGapDraft && evidenceGapDraft.index !== "" ? Number(evidenceGapDraft.index) : 0;
  const selectedGap = gapRows[selectedGapIndex] || gapRows[0] || {};
  const evidenceGapReason = (evidenceGapDraft && evidenceGapDraft.reason) || "";
  const evidenceGapRefs = (evidenceGapDraft && evidenceGapDraft.evidence_refs_text) || "";
  const setGapDraftField = (field, value) => setEvidenceGapDraft && setEvidenceGapDraft({ ...(evidenceGapDraft || emptyEvidenceGapDraft()), [field]: value });
  const fetchReceipt = evidenceFetchEvent && evidenceFetchEvent.receipt && typeof evidenceFetchEvent.receipt === "object"
    ? evidenceFetchEvent.receipt
    : {};
  const fetchResultStatus = evidenceFetchEvent && evidenceFetchEvent.status && evidenceFetchEvent.status !== "needs_confirmation"
    ? evidenceFetchEvent.status
    : "";
  const fetchAttempted = evidenceFetchEvent ? (evidenceFetchEvent.total_attempted ?? fetchReceipt.total_attempted) : undefined;
  const fetchAccepted = evidenceFetchEvent ? (evidenceFetchEvent.total_accepted ?? fetchReceipt.total_accepted) : undefined;
  const fetchManifestPath = evidenceFetchEvent ? (evidenceFetchEvent.manifest_path || fetchReceipt.manifest_path || "") : "";
  const fetchReceiptPath = evidenceFetchEvent ? (evidenceFetchEvent.receipt_path || fetchReceipt.receipt_path || "") : "";
  const fetchLatestPath = evidenceFetchEvent ? (evidenceFetchEvent.latest || fetchReceipt.latest_path || "") : "";
  const fetchBackend = evidenceFetchEvent ? (fetchReceipt.search_backend || (evidenceFetchEvent.settings || {}).evidence_search_backend || "") : "";
  const latestGapReceiptPath =
    (evidenceGapEvent && evidenceGapEvent.receipt_path) ||
    (evidenceFetchEvent && (evidenceFetchEvent.receipt_path || fetchReceipt.receipt_path)) ||
    "";
  const latestGapReceiptLabel = evidenceGapEvent && evidenceGapEvent.receipt_path
    ? "Preview justification history"
    : evidenceFetchEvent && (evidenceFetchEvent.receipt_path || fetchReceipt.receipt_path)
      ? "Preview fetch record"
      : "Preview saved history";
  const selectedGapContract = selectedGap && selectedGap.recovery_contract && typeof selectedGap.recovery_contract === "object"
    ? selectedGap.recovery_contract
    : {};
  const selectedGapTarget = selectedGap.target || selectedGap.gap_id || selectedGap.id || "Evidence gap";
  const selectedGapSeverity = selectedGap.severity || selectedGapContract.severity || "gap";
  const selectedGapRequiredSurface = selectedGap.required_surface || selectedGapContract.required_surface || "";
  const selectedGapFetchQuery = selectedGap.fetch_query || "";
  const selectedGapRecoveryKind = selectedGap.recovery_kind || selectedGapContract.recovery_kind || selectedGap.recovery_channel || selectedGapContract.recovery_channel || "";
  const selectedGapCanFetch = Boolean(selectedGap.can_public_fetch || selectedGapContract.can_public_fetch);
  const selectedGapDescription = selectedGap.description || selectedGap.producer_rationale || "";
  const selectedGapRequiredFilename = sourceBasename(selectedGapRequiredSurface);
  const canDraftRequiredSurface = Boolean(liveMode && onPrepareSource && gapRows.length);
  const fetchFailureCounts = evidenceFetchEvent && evidenceFetchEvent.failure_counts && typeof evidenceFetchEvent.failure_counts === "object"
    ? evidenceFetchEvent.failure_counts
    : fetchReceipt.failure_counts && typeof fetchReceipt.failure_counts === "object"
      ? fetchReceipt.failure_counts
      : {};
  const fetchFailureText = Object.entries(fetchFailureCounts)
    .map(([key, value]) => `${displayText(key)}=${value}`)
    .join(", ");
  const fetchRecoveryHints = Array.isArray(evidenceFetchEvent && evidenceFetchEvent.recovery_hints)
    ? evidenceFetchEvent.recovery_hints
    : Array.isArray(fetchReceipt.recovery_hints)
      ? fetchReceipt.recovery_hints
      : [];
  const fetchRecoveryHint = fetchRecoveryHints.find(Boolean) || "";
  const selectedGapNext = selectedGapCanFetch
    ? "Fetch public evidence if the needed evidence can be found. If you already know why the gap should not hold the project, save a justification instead."
    : "Save a justification or add a local evidence file; this gap is not marked as public-fetchable.";
  const appendEvidenceRef = (value) => {
    const ref = String(value || "").trim();
    if (!ref) return;
    const refs = linesFromText(evidenceGapRefs);
    if (!refs.includes(ref)) refs.push(ref);
    setGapDraftField("evidence_refs_text", refs.join("\n"));
  };
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
    { className: `claim-support-panel run-history-panel ${attention ? "attention" : "ready"}`, "aria-label": "Evidence summary" },
    h(
      "div",
      { className: "run-history-summary" },
      h("span", { className: "eyebrow" }, "Evidence summary"),
      h("h2", null, displayStatus),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? "Evidence summary loaded from local project files."
            : "Start the workbench server to inspect the evidence summary.")
      ),
      h(
        "button",
        {
          type: "button",
          className: "copy-button primary",
          disabled: !liveMode || !onRefresh,
          onClick: () => onRefresh && onRefresh(),
          title: "Refresh the evidence summary and active gaps from local project files"
        },
        "Refresh support"
      )
    ),
    h(
      "div",
      { className: "run-history-facts" },
      h("div", null, h("span", null, "Support notes"), h("strong", null, String((claimSupport && claimSupport.claim_count) || 0))),
      h("div", null, h("span", null, "Needs stronger support"), h("strong", null, String((claimSupport && claimSupport.weak_or_unsourced_count) || 0))),
      h("div", null, h("span", null, "Source gaps"), h("strong", null, String((claimSupport && claimSupport.source_context_blocked_count) || 0))),
      h("div", null, h("span", null, "Sources"), h("strong", null, String(sources.length))),
      h("div", null, h("span", null, "Evidence set"), h("strong", null, supportScope)),
      h("div", null, h("span", null, "Project"), h("strong", null, projectKey || "not connected")),
      intakePath ? h("div", null, h("span", null, "Project brief"), h("strong", null, intakePath)) : null
    ),
    h(
      "div",
      { className: "run-history-verdict" },
      h("span", null, "Evidence result"),
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
      { className: "evidence-gap-workspace" },
      h("span", null, "Evidence gaps"),
      h(
        "div",
        { className: "run-history-facts compact" },
        h("div", null, h("span", null, "Active gaps"), h("strong", null, String(activeGapCount))),
        h("div", null, h("span", null, "Gap source"), h("strong", null, gapSourcePath || "not loaded")),
        h("div", null, h("span", null, "Last save"), h("strong", null, (evidenceGapEvent && evidenceGapEvent.receipt_path) || (evidenceFetchEvent && evidenceFetchEvent.receipt_path) || "not saved"))
      ),
      evidenceGapMessage ? h("p", { className: "source-import-note" }, evidenceGapMessage) : null,
      fetchResultStatus
        ? h(
            "section",
            { className: `evidence-fetch-result ${evidenceFetchEvent.accepted ? "ready" : "attention"}`, "aria-label": "Latest evidence fetch result" },
            h("span", { className: "eyebrow" }, "Latest fetch"),
            h("strong", null, displayText(fetchResultStatus)),
            h(
              "div",
              { className: "run-history-facts compact" },
              h("div", null, h("span", null, "Accepted"), h("strong", null, `${fetchAccepted ?? 0} / ${fetchAttempted ?? 0}`)),
              h("div", null, h("span", null, "Backend"), h("strong", null, fetchBackend || "not recorded")),
              h("div", null, h("span", null, "Saved work"), h("strong", null, fetchReceiptPath || "not recorded")),
              fetchFailureText ? h("div", null, h("span", null, "Reason"), h("strong", null, fetchFailureText)) : null,
              fetchRecoveryHint ? h("div", null, h("span", null, "Next"), h("strong", null, fetchRecoveryHint)) : null
            ),
            h(
              "div",
              { className: "evidence-gap-brief-actions" },
              h("button", { type: "button", className: "copy-button", onClick: () => copyText(evidenceFetchStatusMessage(evidenceFetchEvent)) }, "Copy result"),
              !evidenceFetchEvent.accepted && onPrepareSource
                ? h("button", { type: "button", className: "copy-button", disabled: !liveMode || !gapRows.length, onClick: () => onPrepareSource(selectedGap, selectedGapIndex) }, "Draft source note")
                : null,
              fetchManifestPath
                ? h("button", { type: "button", className: "copy-button", disabled: !liveMode, onClick: () => onPreview && onPreview({ type: "file", value: fetchManifestPath }) }, "Preview manifest")
                : null,
              fetchLatestPath
                ? h("button", { type: "button", className: "copy-button", disabled: !liveMode, onClick: () => onPreview && onPreview({ type: "file", value: fetchLatestPath }) }, "Preview latest save")
                : null
            )
          )
        : null,
      h(
        "div",
        { className: "evidence-gap-write-previews" },
        h(CompactWritePreview, {
          title: "Save justification writes",
          writePaths: justifyWritePaths,
          receiptPath: justifyReceiptPaths[0],
          latestPath: justifyReceiptPaths[1],
          noChangeBoundary: "Preview, missing reason text, and validation failure write no files."
        }),
        h(CompactWritePreview, {
          title: "Fetch evidence writes",
          writePaths: fetchWritePaths,
          receiptPath: fetchReceiptPaths[1] || fetchReceiptPaths[0],
          latestPath: fetchReceiptPaths[2],
          noChangeBoundary: "Preview and cancellation write no files. Confirmed fetch may call configured providers and write only the listed project files."
        })
      ),
      gapRows.length
        ? h(
            "div",
            { className: "evidence-gap-grid" },
            h(
              "label",
              null,
              h("span", null, "Active gap"),
              h(
                "select",
                {
                  value: String(selectedGapIndex),
                  disabled: !liveMode || evidenceGapRunning,
                  onChange: (event) => setGapDraftField("index", event.target.value)
                },
                gapRows.map((gap, index) =>
                  h("option", { key: `${gap.target || "gap"}:${index}`, value: String(index) }, `${index + 1}. ${gap.target || gap.id || "Evidence gap"}`)
                )
              )
            ),
            h(
              "section",
              { className: "evidence-gap-brief", "aria-label": "Selected evidence gap" },
              h("span", { className: "eyebrow" }, "Selected gap"),
              h("strong", null, shortText(selectedGapTarget, 120)),
              selectedGapDescription ? h("p", null, displayMessage(selectedGapDescription)) : null,
              h(
                "div",
                { className: "evidence-gap-brief-facts" },
                h("div", null, h("span", null, "Severity"), h("strong", null, displayText(selectedGapSeverity))),
                h("div", null, h("span", null, "Missing evidence"), h("strong", null, selectedGapRequiredSurface || "not specified")),
                h("div", null, h("span", null, "Recovery"), h("strong", null, displayText(selectedGapRecoveryKind || "choose path"))),
                h("div", null, h("span", null, "Public fetch"), h("strong", null, selectedGapCanFetch ? "available" : "not marked"))
              ),
              selectedGapFetchQuery
                ? h(
                    "div",
                    { className: "evidence-gap-question" },
                    h("span", null, "Question to answer"),
                    h("p", null, selectedGapFetchQuery)
                  )
                : null,
              h("p", null, selectedGapNext),
              h(
                "div",
                { className: "evidence-gap-brief-actions" },
                selectedGapRequiredSurface
                  ? h(
                      "button",
                      {
                        type: "button",
                        className: "copy-button",
                        disabled: !liveMode || evidenceGapRunning,
                        onClick: () => appendEvidenceRef(selectedGapRequiredSurface),
                        title: "Add the missing evidence path to the evidence field"
                      },
                      "Use missing evidence"
                    )
                  : null,
                selectedGapRequiredSurface
                  ? h(
                      "button",
                      {
                        type: "button",
                        className: "copy-button",
                        disabled: !canDraftRequiredSurface,
                        onClick: () => onPrepareSource && onPrepareSource(selectedGap, selectedGapIndex),
                        title: canDraftRequiredSurface
                          ? "Draft a file note from this evidence gap in Add file"
                          : "Start the local server before drafting a source note"
                      },
                      "Draft source note"
                    )
                  : null,
                isPreviewableRepoPath(selectedGapRequiredSurface)
                  ? h(
                      "button",
                      {
                        type: "button",
                        className: "copy-button",
                        disabled: !liveMode,
                        onClick: () => onPreview && onPreview({ type: "file", value: selectedGapRequiredSurface })
                      },
                      "Preview file"
                    )
                  : null,
                selectedGapFetchQuery
                  ? h(
                      "button",
                      {
                        type: "button",
                        className: "copy-button",
                        onClick: () => copyText(selectedGapFetchQuery)
                      },
                      "Copy question"
                    )
                  : null
              )
            ),
            h(
              "label",
              null,
              h("span", null, "Why this can be closed"),
              h("textarea", {
                value: evidenceGapReason,
                disabled: !liveMode || evidenceGapRunning,
                onChange: (event) => setGapDraftField("reason", event.target.value),
                placeholder: "Explain the source, file, or scope decision that resolves this gap."
              })
            ),
            h(
              "label",
              null,
              h("span", null, "Evidence file or note"),
              h("input", {
                value: evidenceGapRefs,
                disabled: !liveMode || evidenceGapRunning,
                onChange: (event) => setGapDraftField("evidence_refs_text", event.target.value),
                placeholder: "projects/example/raw/source.md or a short note"
              })
            ),
            h(
              "div",
              { className: "evidence-gap-actions" },
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button primary",
                  disabled: !liveMode || evidenceGapRunning || evidenceGapReason.trim().length < 16,
                  onClick: () => onJustify && onJustify(selectedGapIndex, selectedGap)
                },
                evidenceGapRunning ? "Saving..." : "Save justification"
              ),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button primary",
                  disabled: !liveMode || evidenceFetchRunning || !selectedGapCanFetch || !selectedGap.target,
                  onClick: () => onFetch && onFetch(selectedGap.target || ""),
                  title: selectedGapCanFetch
                    ? "Fetch public evidence for this gap, then preview and confirm"
                    : "This gap is not marked as public-fetchable — save a justification or add a local file instead"
                },
                evidenceFetchRunning ? "Fetching..." : "Fetch this gap"
              ),
              gapRows.length > 1
                ? h(
                    "button",
                    {
                      type: "button",
                      className: "copy-button",
                      disabled: !liveMode || evidenceFetchRunning || !gapCommand,
                      onClick: () => onFetch && onFetch(""),
                      title: gapCommand ? "Fetch every degrading gap in one batch" : "No batch fetch command is available"
                    },
                    "Fetch all degrading"
                  )
                : null,
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  disabled: !gapSourcePath || !liveMode,
                  onClick: () => onPreview && onPreview({ type: "file", value: gapSourcePath }),
                  title: gapSourcePath ? `Preview ${gapSourcePath}` : "No evidence-gap file loaded"
                },
                "Preview gaps"
              ),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  disabled: !liveMode || !isPreviewableRepoPath(latestGapReceiptPath),
                  onClick: () => latestGapReceiptPath && onPreview && onPreview({ type: "file", value: latestGapReceiptPath }),
                  title: latestGapReceiptPath ? `Preview ${latestGapReceiptPath}` : "No saved evidence-gap record yet"
                },
                latestGapReceiptLabel
              ),
              h(
                "button",
                {
                  type: "button",
                  className: "copy-button",
                  disabled: !gapCommand,
                  onClick: () => copyText(gapCommand),
                  title: "Copy the fetch command for gaps that need new sources"
                },
                "Copy fetch command"
              )
            ),
            selectedGap && (selectedGap.description || selectedGap.required_surface)
              ? h("p", { className: "source-import-note" }, selectedGap.description || selectedGap.required_surface)
              : null
          )
        : h("p", null, liveMode ? "No active evidence gaps loaded." : "Start the workbench server to inspect evidence gaps.")
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
              h("small", null, [displayText(source.status || "unknown"), sourceWorkSummary(source) || sourceTypeLabel(source.source_type || "untyped")].filter(Boolean).join(" / ")),
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
      h("code", null, command || "No evidence-support command loaded."),
      h(
        "button",
        {
          className: "copy-button",
          type: "button",
          disabled: !command,
          onClick: () => copyText(command),
          title: "Copy evidence-support step"
        },
        "Copy detail"
      )
    )
  );
}

function MoreDetail({ title = "More detail", children, defaultOpen = false }) {
  const panels = React.Children.toArray(children).filter(Boolean);
  if (!panels.length) return null;
  return h(
    "details",
    { className: "more-detail-panel create-disclosure", open: defaultOpen || undefined },
    h("summary", null, title),
    h("div", { className: "more-detail-body" }, panels)
  );
}

function reportVerdictTitle(status) {
  if (status === "ready") return "You can rely on this report";
  if (status === "blocked") return "This report isn't ready to rely on yet";
  if (status === "attention") return "Almost there — a couple of things to check";
  return "Checking this report…";
}

function reportVerdictWhy(status) {
  if (status === "ready") return "Every claim is backed by your current files.";
  if (status === "blocked") return "Fix the points below before you rely on it.";
  if (status === "attention") return "It's usable, but read what's flagged below first.";
  return "Reading the report against your current files.";
}

function ReportContractPanel({ reportContext, message, running, liveMode, onPreview, onRefresh, onRerun, onRefreshInputs, onBuildClaimCard, onRunProjectTest, onOpenDetail, onUseActionNote }) {
  const binding = (reportContext && reportContext.synthesis_input_binding) || {};
  const reasons = (reportContext && reportContext.status_reasons) || [];
  const displayReasons = (reportContext && reportContext.display_status_reasons) || reasons.map(displayText);
  const supportIssues = (reportContext && reportContext.support_issues) || [];
  const allowedActions = (reportContext && reportContext.allowed_actions) || [];
  const conditionalActions = (reportContext && reportContext.conditional_actions) || [];
  const deferredActions = (reportContext && reportContext.deferred_actions) || [];
  const forbiddenUpgrades = (reportContext && reportContext.forbidden_upgrades) || [];
  const openAllowedActions = allowedActions.filter((action) => !isCompletedReportAction(action));
  const completedAllowedActions = allowedActions.filter((action) => isCompletedReportAction(action));
  const repairActions = Array.isArray(reportContext && reportContext.repair_actions) ? reportContext.repair_actions.filter(Boolean) : [];
  const synthesisAction = repairActions.find((action) => action && action.id === "refresh_report_inputs") || null;
  const rerunAction = repairActions.find((action) => action && action.id === "rerun_report_support") || null;
  const synthesisReceiptPaths = Array.isArray(synthesisAction && synthesisAction.receipt_paths) ? synthesisAction.receipt_paths.filter(Boolean) : [];
  const rerunReceiptPaths = Array.isArray(rerunAction && rerunAction.receipt_paths) ? rerunAction.receipt_paths.filter(Boolean) : [];
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
      (contractPath ? [{ label: "Report readiness file", path: contractPath }] : [])
  );
  const isBlocked = status === "blocked" || supportIssues.length > 0 || reasons.length > 0 || binding.status === "unbound";
  // status often arrives as "not_loaded"/empty even when the report is clearly blocked/ready — map
  // anything non-canonical back to a real verdict so the headline never sticks on "Checking this report…".
  const effectiveStatus = /^(ready|blocked|attention)$/.test(String(status))
    ? status
    : isBlocked
      ? "blocked"
      : reportLoaded
        ? "ready"
        : "loading";
  const firstAction = openAllowedActions.find(Boolean) || null;
  const firstIssue = supportIssues.find(Boolean) || null;
  const firstDestination = firstAction ? projectActionDestination(firstAction) : null;
  const firstActionIsProjectTest = firstAction ? isProjectTestAction(firstAction) : false;
  const firstActionBoundary = firstAction && firstAction.write_boundary ? firstAction.write_boundary : {};
  const firstActionTarget = firstAction ? writeBoundaryTargetSummary(firstActionBoundary) : "";
  const firstActionStorage = firstAction ? writeBoundaryStorageLabel(firstActionBoundary) : "";
  const reportNextText = firstAction
    ? displayMessage(firstAction.label || "Review this report action")
    : firstIssue
      ? displayMessage(firstIssue.display_reason || firstIssue.reason || "Review this report point")
      : isBlocked
        ? "Review why the report is not ready before relying on it."
        : "The report looks ready; save a review only if you need to record a decision.";
  const reportNextNote = [
    "Report readiness",
    reportNextText,
    firstDestination ? `Opens: ${firstDestination.subsection}` : "",
    firstActionTarget ? `File change: ${firstActionTarget}` : "",
    contractPath ? `Backing file: ${contractPath}` : "",
    firstAction && firstAction.source ? `Source: ${firstAction.source}` : "",
    firstIssue && firstIssue.status ? `Status: ${displayText(firstIssue.status)}` : ""
  ].filter(Boolean).join("\n");
  const noteForReportAction = (action) =>
    [
      "Report readiness",
      displayMessage((action && action.label) || "Review this report action"),
      action && (action.workspace || action.subsection) ? `Opens: ${(projectActionDestination(action) || {}).subsection || ""}` : "",
      action && action.write_boundary ? `File change: ${writeBoundaryTargetSummary(action.write_boundary)}` : "",
      contractPath ? `Backing file: ${contractPath}` : "",
      action && action.source ? `Source: ${action.source}` : "",
      "Saved from: Report readiness"
    ].filter(Boolean).join("\n");

  return h(
    "section",
    { className: `report-contract-panel ${isBlocked ? "attention" : "ready"}`, "aria-label": "Report readiness" },
    h(
      "div",
      { className: "report-contract-summary" },
      h("h2", null, reportVerdictTitle(effectiveStatus)),
      h(
        "p",
        null,
        message ||
          (liveMode
            ? reportVerdictWhy(effectiveStatus)
            : "Start the workbench to see whether this report holds up.")
      ),
      h(
        "div",
        { className: "report-summary-actions" },
        contractPath
          ? h(
              "button",
              {
                type: "button",
                className: "copy-button primary",
                disabled: !liveMode,
                onClick: () => onPreview && onPreview({ type: "report", value: contractPath }),
                title: "Open the full report as a readable document"
              },
              "View the full report"
            )
          : null,
        onBuildClaimCard
          ? h(
              "button",
              {
                type: "button",
                className: `copy-button${running ? " is-busy" : ""}`,
                disabled: !liveMode || running,
                onClick: () => onBuildClaimCard(),
                title: "Generate a portable, verifiable claim card you can share"
              },
              running ? "Working…" : "Make a claim card"
            )
          : null,
        h(
          "button",
          {
            type: "button",
            className: "copy-button",
            disabled: !liveMode || running || !onRerun,
            onClick: () => onRerun && onRerun(),
            title: "Check the report against your current files again"
          },
          running ? "Checking…" : "Re-check"
        ),
        synthesisAction && onRefreshInputs
          ? h(
              "button",
              {
                type: "button",
                className: `copy-button quiet${running ? " is-busy" : ""}`,
                disabled: !liveMode || running,
                onClick: () => onRefreshInputs(),
                title: "Rewrite the report from your current files — you can give the model direction first"
              },
              running ? "Working…" : "Rewrite the report"
            )
          : null
      )
    ),
    h(
      "section",
      { className: "report-next-action", "aria-label": "Report readiness next action" },
      h(
        "div",
        { className: "report-next-action-copy" },
	        h("span", { className: "eyebrow" }, "What to do next"),
	        h("strong", null, reportNextText),
	        h("p", null, completedAllowedActions.length ? "A saved project test is available below. Continue with the next unfinished report action." : isBlocked ? "Record a review or next step, or check readiness again after the inputs change." : "The report readiness file is available for inspection."),
	        firstDestination
	          ? h(
	              "div",
	              { className: "report-action-route" },
	              h("span", null, `Opens ${firstDestination.subsection}`),
	              firstActionTarget ? h("span", null, firstActionTarget === "read-only" ? "Read-only" : `Changes ${firstActionTarget}`) : null,
	              firstActionStorage ? h("span", null, firstActionStorage) : null
	            )
	          : null
	      ),
      h(
        "div",
        { className: "report-next-action-buttons" },
        firstActionIsProjectTest
          ? h(
              "button",
              {
                type: "button",
                className: "copy-button primary",
                disabled: !liveMode || running || !onRunProjectTest,
                onClick: () => onRunProjectTest && onRunProjectTest(firstAction),
                title: "Run the project-local test and save the result"
              },
              running ? "Running..." : "Run project test"
            )
          : null,
        h(
          "button",
          {
            type: "button",
            className: firstActionIsProjectTest ? "copy-button" : "copy-button primary",
            disabled: !onUseActionNote || !reportNextNote,
            onClick: () => onUseActionNote && onUseActionNote(reportNextNote, "export_blocker", "Report readiness"),
            title: "Stage this report readiness issue as the next saved step"
          },
          "Save next step"
        ),
	        contractPath
	          ? h(
	              "button",
              {
                type: "button",
                className: "copy-button",
                disabled: !liveMode || !previewableRepoPath(contractPath),
                onClick: () => onPreview && onPreview({ type: "report", value: contractPath }),
                title: previewFileTitle(liveMode, previewableRepoPath(contractPath), "Preview report readiness file")
              },
	              "Preview file"
	            )
	          : null
	      )
	    ),
    h(
      "details",
      { className: "report-contract-more create-disclosure" },
      h("summary", null, "What's weak, and what the verdict is built on"),
    h(
      "p",
      { className: "detail-teach", style: { padding: "10px 0 2px" } },
      "Where the verdict is still unsure, plus the files and checks it was computed from — here so you can audit how it was reached, not because you need to act on it."
    ),
    h(
      "div",
      { className: "report-contract-metrics" },
      h("div", null, h("span", null, "Report inputs"), h("strong", null, binding.display_status || displayText(binding.status || "unknown"))),
      h("div", null, h("span", null, "Files"), h("strong", null, String(binding.artifact_count ?? "none"))),
      h("div", null, h("span", null, "Current file"), h("strong", null, shortDigest(binding.current_digest))),
      h("div", null, h("span", null, "Recorded file"), h("strong", null, shortDigest(binding.ledger_digest))),
      h("div", null, h("span", null, "Report set"), h("strong", null, reportScope)),
      h("div", null, h("span", null, "Project"), h("strong", null, projectKey || "not connected")),
      intakePath ? h("div", null, h("span", null, "Project brief"), h("strong", null, intakePath)) : null
    ),
    h(
      "div",
      { className: "report-contract-body" },
      h(
        "div",
        { className: "report-contract-section" },
        h("span", null, "Next report actions"),
        allowedActions.length
	          ? allowedActions.slice(0, 5).map((action, index) =>
	              {
	                const destination = projectActionDestination(action);
	                const writeBoundary = action && action.write_boundary ? action.write_boundary : {};
	                const writeTarget = writeBoundaryTargetSummary(writeBoundary);
	                const storageLabel = writeBoundaryStorageLabel(writeBoundary);
	                const projectTestAction = isProjectTestAction(action);
	                const completed = isCompletedReportAction(action);
	                return h(
	                  "div",
	                  { className: `report-support-issue ${completed ? "done" : ""}`, key: action.id || action.label || index },
	                  h("strong", null, displayMessage(action.label || "Review this report action")),
	                  completed
	                    ? h(
	                        "div",
	                        { className: "report-action-route done" },
	                        h("span", null, "Done"),
	                        action.completed_summary ? h("span", null, displayMessage(action.completed_summary)) : null
	                      )
	                    : null,
	                  h(
	                    "div",
	                    { className: "report-action-route" },
	                    h("span", null, `Opens ${destination.subsection}`),
	                    writeTarget ? h("span", null, writeTarget === "read-only" ? "Read-only" : `Changes ${writeTarget}`) : null,
	                    storageLabel ? h("span", null, storageLabel) : null
	                  ),
	                  action.source ? h("small", null, displayText(action.source)) : null,
	                  h(
	                    "div",
	                    { className: "report-support-issue-actions" },
	                    projectTestAction && !completed
	                      ? h(
	                          "button",
	                          {
	                            type: "button",
	                            className: "copy-button primary",
	                            disabled: !liveMode || running || !onRunProjectTest,
	                            onClick: () => onRunProjectTest && onRunProjectTest(action),
	                            title: "Run the project-local test and save the result"
	                          },
	                          running ? "Running..." : "Run project test"
	                        )
	                      : null,
	                    completed && action.completed_by
	                      ? h(
	                          "button",
	                          {
	                            type: "button",
	                            className: "copy-button primary",
	                            disabled: !liveMode || !previewableRepoPath(action.completed_by),
	                            onClick: () => onPreview && onPreview({ type: "receipt", value: action.completed_by }),
	                            title: previewFileTitle(liveMode, previewableRepoPath(action.completed_by), "Preview saved check result")
	                          },
	                          "Preview result"
	                        )
	                      : null,
	                    destination && onOpenDetail
	                      ? h(
	                          "button",
	                          {
	                            type: "button",
	                            className: projectTestAction || completed ? "copy-button" : "copy-button primary",
	                            onClick: () => onOpenDetail(destination.workspace, destination.subsection),
	                            title: `Open ${destination.subsection}`
	                          },
	                          destination.label || "Open section"
	                        )
	                      : null,
	                    h(
	                      "button",
	                      {
	                        type: "button",
	                        className: "copy-button",
	                        disabled: !onUseActionNote,
	                        onClick: () => onUseActionNote && onUseActionNote(noteForReportAction(action), "export_blocker", "Report readiness"),
	                        title: "Stage this report action as the saved next step"
	                      },
	                      "Save next step"
                    )
	                  )
	                );
	              }
	            )
          : h("p", null, "No report action list loaded.")
      ),
      // Decision rules, do-not-claim and defer are the report's OWN content — they live in the report
      // now (View the full report), so they don't get re-dumped on the trust-status surface.
      h(
        "div",
        { className: "report-contract-section" },
        h("span", null, supportIssues.length > 4 ? `Before relying on report (${supportIssues.length})` : "Before relying on report"),
        supportIssues.length
          ? supportIssues.slice(0, 4).map((issue, index) =>
              h(
                "div",
                { className: "report-support-issue", key: issue.id || issue.reason || index },
                h("strong", null, displayMessage(issue.display_reason || issue.reason || "Report readiness issue")),
                issue.display_status || issue.status
                  ? h("small", null, displayText(issue.display_status || issue.status))
                  : null,
                issue.why_it_matters ? h("p", null, displayMessage(issue.why_it_matters)) : null,
                issue.what_to_check ? h("p", { className: "health-action-check" }, `Check: ${displayMessage(issue.what_to_check)}`) : null,
                issue.done_when ? h("p", { className: "health-action-check" }, `Done when: ${displayMessage(issue.done_when)}`) : null,
                Array.isArray(issue.runtime_risks) && issue.runtime_risks.length
                  ? h(
                      "ul",
                      { className: "report-risk-list" },
                      issue.runtime_risks.slice(0, 3).map((risk, riskIndex) => h("li", { key: `${issue.id || index}-risk-${riskIndex}` }, displayMessage(risk)))
                    )
                  : null
              )
            )
          : reasons.length
            ? reasons.map((reason, index) => h("strong", { key: reason }, displayReasons[index] || displayText(reason)))
          : h("p", null, "No report readiness notes loaded.")
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
                  )
                )
              )
            )
          : h("p", null, "No report backing files loaded.")
      ),
      command
        ? h(
            "details",
            { className: "report-contract-section terminal-equivalent" },
            h("summary", null, "Prefer the terminal? Show the equivalent command"),
            h("code", null, command)
          )
        : null
    )
    )
  );
}

function CaseFilePanel({ snapshot, receiptHistory, projectEntry, intakeDraft, sourceImportDraft, sourceEditDraft, evidenceGapDraft, traceContext, workflowContext, reportContext, healthContext, serverStatus, preflightEvent, sourceListContext, sourceActionEvent, sourceImportEvent, sourceEditEvent, runHistoryContext, claimSupportContext, writeReceiptEvent, refreshResults, selectedRow, liveMode, saving, saveEvent, projectFileContract, onSave, onPreview }) {
  let caseFile = buildCaseFile(snapshot, receiptHistory, {
    projectEntry,
    intakeDraft,
    sourceImportDraft,
    sourceEditDraft,
    evidenceGapDraft,
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
  const pendingEvidenceGap = caseFile.live_context.pending_evidence_gap_justification;
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
    pendingEvidenceGap,
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
          `${caseWorkspaceDir}/forensic_workbench_project_file_${caseDigest.slice(0, 12)}.json`,
          `${caseWorkspaceDir}/forensic_workbench_project_files.jsonl`,
          `${caseWorkspaceDir}/forensic_workbench_latest_project_file_write.json`
        ]
      )
    : [];
  const projectFileWritePaths = writePathsFromItems(pendingCaseFilePaths);
  const projectFileReceiptPath =
    receiptPathFromWriteItems(pendingCaseFilePaths, "forensic_workbench_project_files") ||
    receiptPathFromWriteItems(pendingCaseFilePaths, "forensic_workbench_case_files");
  const projectFileLatestPath =
    receiptPathFromWriteItems(pendingCaseFilePaths, "forensic_workbench_latest_project_file_write") ||
    receiptPathFromWriteItems(pendingCaseFilePaths, "forensic_workbench_latest_case_file_write");
  const runReadinessStatus = caseFile.live_context.preflight_result
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
  const liveProjectState = caseFile.live_context.project_state || {};
  const liveProjectStateReady = Boolean(liveProjectState.schema);
  const liveProjectStateNextAction =
    liveProjectState.next_action ||
    liveProjectState.next_action_label ||
    (liveProjectState.summary || {}).next_action ||
    workflowNextStep;
  const liveProjectActionCount = Array.isArray(liveProjectState.actions) ? liveProjectState.actions.length : 0;
  const pendingDrafts = [
    pendingIntake && pendingIntake.changed_fields.length ? "project-brief changes" : "",
    pendingSourceImport && pendingSourceImport.status === "pending_unsaved" ? "file draft" : "",
    pendingEvidenceGap && pendingEvidenceGap.status === "pending_unsaved" ? "evidence-gap justification" : "",
    pendingSourceEdit && pendingSourceEdit.changed_fields.length ? "file edit" : ""
  ].filter(Boolean);
  const projectFileReady = Boolean(liveMode && caseItems.length && liveContextCount >= 5);
  const savedCasePath = saveEvent && !saveEvent.error ? saveEvent.path || "" : "";
  const savedReceiptPath = saveEvent && !saveEvent.error ? saveEvent.latest || saveEvent.receipt_path || "" : "";
  const savedSummaryFacts = saveEvent && !saveEvent.error
    ? [
        ["Project state", saveEvent.project_state_schema || "saved"],
        ["Next action", saveEvent.project_state_next_action || "not loaded"],
        ["Things to review", saveEvent.item_count === undefined || saveEvent.item_count === null ? "not loaded" : String(saveEvent.item_count)],
        ["Saved changes", saveEvent.receipt_count === undefined || saveEvent.receipt_count === null ? "not loaded" : String(saveEvent.receipt_count)]
      ]
    : [];
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
  const projectSummary = caseFile.project_summary || {};
  const projectSummaryNextAction = projectSummary.next_action || {};
  const projectSummaryReadiness = projectSummary.readiness || {};
  const projectSummaryLatestReview = projectSummary.latest_review || {};
  const projectSummaryLatestNextStep = projectSummary.latest_next_step || {};
  const projectSummaryAxioms = projectSummary.axioms || {};
  const projectSummaryProofPaths = Array.isArray(projectSummary.proof_paths)
    ? projectSummary.proof_paths.filter(Boolean).slice(0, 8)
    : [];
  const projectSummaryProofPathCount =
    projectSummary.proof_path_count === undefined || projectSummary.proof_path_count === null
      ? projectSummaryProofPaths.length
      : Number(projectSummary.proof_path_count) || 0;
  const latestReviewText = projectSummaryLatestReview.summary ||
    projectSummaryLatestReview.decision ||
    projectSummaryLatestReview.label ||
    "not saved";
  const latestNextStepText = projectSummaryLatestNextStep.summary ||
    projectSummaryLatestNextStep.action ||
    projectSummaryLatestNextStep.label ||
    "not saved";
  const projectSummaryFacts = [
    ["Next action", projectSummaryNextAction.label || workflowNextStep],
    ["Original files", projectSummaryReadiness.sources || (sourceFileCount ? `${sourceFileCount} files` : "not loaded")],
    ["Evidence summaries", projectSummaryReadiness.evidence || evidenceSupport],
    ["Ready to run", projectSummaryReadiness.admission || "not loaded"],
    ["Latest run setup", projectSummaryReadiness.run || runReadinessStatus],
    ["Report", projectSummaryReadiness.report || reportSupport],
    ["Latest review", latestReviewText],
    ["Latest next step", latestNextStepText],
    ["Axioms", projectSummaryAxioms.summary || "not loaded"],
    ["Project repairs", projectSummary.open_project_repair_count === undefined || projectSummary.open_project_repair_count === null ? "not loaded" : String(projectSummary.open_project_repair_count)],
    ["Inspections", projectSummary.open_project_inspect_count === undefined || projectSummary.open_project_inspect_count === null ? "not loaded" : String(projectSummary.open_project_inspect_count)],
    ["Guidance items", projectSummary.open_advisory_count === undefined || projectSummary.open_advisory_count === null ? "not loaded" : String(projectSummary.open_advisory_count)],
    ["Proof paths", String(projectSummaryProofPathCount)]
  ];
  const includedDetailFacts = [
    ["Saved changes", String(caseFile.recent_receipts.length)],
    ["Commands", String((caseFile.audit_commands || caseFile.command_queue || []).length)],
    ["Things to review", String(caseItems.length)],
    ["Evidence-linked points", String(itemsWithEvidence)],
    ["Next project step", workflowNextStep],
    ["Latest score", caseFile.live_context.run_history.summary.latest_score === undefined || caseFile.live_context.run_history.summary.latest_score === null ? "none" : String(caseFile.live_context.run_history.summary.latest_score)],
    ["File status", caseFile.live_context.latest_source_action ? displayText(caseFile.live_context.latest_source_action.action) : "not run"],
    ["Added file", caseFile.live_context.latest_source_import ? sourceTypeLabel(caseFile.live_context.latest_source_import.source_type) : "none"],
    ["File edit", caseFile.live_context.latest_source_edit ? sourceTypeLabel(caseFile.live_context.latest_source_edit.source_type) : "none"],
    ["Refresh status", writeRefreshRows.length ? `${writeRefreshOk}/${writeRefreshRows.length} panels` : "not run"],
    ["Warnings to fix", String(caseFile.live_context.health.action_guidance.recommendations.length || 0)],
    ["File-change behavior", fileChangeSplit],
    ["Loaded project context", String(liveContextCount)],
    ["Live project state", liveProjectStateReady ? "loaded" : "not loaded"],
    ["Project actions", liveProjectActionCount ? String(liveProjectActionCount) : "none loaded"],
    ["Project file", projectFileState],
    ["Saved work", "Project file"]
  ];
  const handoffReadiness = [
    { label: "Live project state", ready: liveProjectStateReady, value: liveProjectStateReady ? liveProjectStateNextAction : "not loaded" },
    { label: "Things to review", ready: Boolean(caseItems.length), value: caseItems.length ? `${caseItems.length} loaded` : "not loaded" },
    { label: "Original files", ready: Boolean(sourceFileCount), value: sourceFileCount ? `${sourceFileCount} files` : "not loaded" },
    { label: "Project path", ready: Boolean(caseFile.live_context.workflow.schema || (caseFile.live_context.workflow.steps || []).length), value: workflowNextStep },
    { label: "Report readiness", ready: Boolean(reportContext && (reportContext.schema || reportContext.status)), value: reportSupport },
    { label: "Saved history", ready: Boolean(caseFile.recent_receipts.length), value: caseFile.recent_receipts.length ? `${caseFile.recent_receipts.length} loaded` : "none loaded" },
    { label: "Run history", ready: Boolean(caseFile.live_context.run_history.schema || Object.keys(caseFile.live_context.run_history.summary || {}).length), value: caseFile.live_context.run_history.summary.latest_score === undefined || caseFile.live_context.run_history.summary.latest_score === null ? "not loaded" : `score ${caseFile.live_context.run_history.summary.latest_score}` },
    { label: "Evidence summaries", ready: Boolean(evidenceSupportContext.schema || evidenceSupportContext.status), value: evidenceSupport }
  ];

  return h(
    "section",
    { className: "case-file-panel", "aria-label": "Project file" },
    h(
      "div",
      { className: "case-file-copy" },
      h("span", { className: "eyebrow" }, "Project file"),
      h("h2", null, "Save project state"),
      h("p", null, "Keep the current thesis, evidence summary, next action, and saved history together so the project can be reopened later.")
    ),
    h(
      "div",
      { className: "case-file-facts" },
      h(
        "div",
        { className: "case-file-primary-facts" },
        h("div", null, h("span", null, "Save status"), h("strong", null, projectFileReady ? "Ready to save" : liveMode ? "Loading context" : "Start server")),
        h("div", null, h("span", null, "Original files"), h("strong", null, sourceFileCount ? `${sourceFileCount} files` : "Not loaded")),
        h("div", null, h("span", null, "Evidence summary"), h("strong", null, evidenceSupport)),
        h("div", null, h("span", null, "Unsaved edits"), h("strong", null, pendingDrafts.length ? pendingDraftText : "None found"))
      ),
      h(
        "details",
        { className: "case-file-detail-facts" },
        h("summary", null, "Show included details"),
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
      MoreDetail,
      { title: "Check what will be saved" },
      h(
        "section",
        { className: "case-file-readiness", "aria-label": "Project file included state" },
        h(
          "div",
          { className: "case-file-readiness-copy" },
          h("strong", null, projectFileReady ? "Live project context loaded" : "Waiting for live project context"),
          h(
            "p",
            null,
            projectFileReady
              ? "Saving includes the live project state, run readiness, saved history, and next action. The server refreshes project state once more before it writes."
              : "Saving waits until enough live sections are loaded. Download and copy use the current preview."
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
        writeLabel: "Save to project folder",
        readLabel: "Download, copy, preview",
        liveMode
      })
    ),
    h(
      "section",
      { className: "case-file-summary-preview", "aria-label": "Saved project summary" },
      h(
        "div",
        { className: "case-file-summary-copy" },
        h("span", { className: "eyebrow" }, "Project summary"),
        h("strong", null, projectSummary.thesis || "No thesis loaded yet"),
        h("p", null, projectSummary.change_test || "No change test loaded yet")
      ),
      h(
        MoreDetail,
        { title: "Open project details" },
        h(
          "div",
          { className: "case-file-summary-grid" },
          projectSummaryFacts.map(([label, value]) =>
            h("div", { key: label }, h("span", null, label), h("strong", null, value))
          )
        ),
        projectSummaryProofPaths.length
          ? h(
              "div",
              { className: "case-file-proof-paths", "aria-label": "Saved project proof paths" },
              h("span", null, "Backing paths"),
              projectSummaryProofPaths.map((path) =>
                h(
                  "button",
                  {
                    key: path,
                    type: "button",
                    className: "inline-path-button",
                    disabled: !liveMode || !isPreviewableRepoPath(path),
                    onClick: () => onPreview && onPreview({ type: "file", value: path }),
                    title: liveMode && isPreviewableRepoPath(path) ? `Preview ${path}` : "This path is not previewable from the workbench"
                  },
                  path
                )
              ),
              projectSummaryProofPathCount > projectSummaryProofPaths.length
                ? h("small", null, `${projectSummaryProofPathCount - projectSummaryProofPaths.length} more path${projectSummaryProofPathCount - projectSummaryProofPaths.length === 1 ? "" : "s"} in the saved project file.`)
                : null
            )
          : null
      )
    ),
    h(
      MoreDetail,
      { title: "Show saved files and JSON" },
      h(CompactWritePreview, {
        title: "Files saved by this action",
        writePaths: projectFileWritePaths,
        receiptPath: projectFileReceiptPath,
        latestPath: projectFileLatestPath,
        noChangeBoundary: projectFileReady
          ? "Saving writes a project file and updates saved history. Download and copy do not change files."
          : "No project file is saved until enough live context is loaded and you choose Save."
      }),
      pendingPathPreview(
        "Files that may change",
        pendingCaseFilePaths,
        "Project file path is calculated from the selected project and project brief.",
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
      )
    ),
    h(
      "div",
      { className: "case-file-actions" },
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
              ? "Wait for live workflow, evidence, source, run, and saved-history context before saving"
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
      h(MoreDetail, { title: "Copy summary or filename" },
        h("code", null, filename),
        h(
          "button",
          {
            className: "copy-button",
            type: "button",
            onClick: () => copyText(summary),
            title: "Copy a short project summary"
          },
          "Copy summary"
        )
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
                : "Saved. Project state and saved history were updated."
            ),
            !saveEvent.error
              ? [
                h(
                  "div",
                  { className: "case-file-save-actions", key: "save-actions" },
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !savedCasePath,
                      onClick: () => onPreview && onPreview({ type: "file", value: savedCasePath }),
                      title: savedCasePath ? "Preview saved project file" : "No saved project file path recorded"
                    },
                    "Open saved file"
                  ),
                  h(
                    "button",
                    {
                      className: "copy-button",
                      type: "button",
                      disabled: !liveMode || !savedReceiptPath,
                      onClick: () => onPreview && onPreview({ type: "receipt", value: savedReceiptPath }),
                      title: savedReceiptPath ? "Preview latest project-file history" : "No saved-history path recorded"
                    },
                    "Open saved history"
                  )
                ),
                h(
                  MoreDetail,
                  { title: "Save details", key: "save-facts" },
                  h(
                    "div",
                    { className: "case-file-save-facts" },
                    savedSummaryFacts.map(([label, value]) =>
                      h("div", { key: label }, h("span", null, label), h("strong", null, value))
                    )
                  )
                )
              ]
              : null
          )
        : null
    )
  );
}

function rowByLabel(rows, label) {
  const accepted = label === "Report readiness" || label === "Report support"
    ? new Set(["Report readiness", "Report support"])
    : new Set([label]);
  return rows.find((row) => accepted.has(row.label)) || null;
}

function reviewRowFromRows(rows) {
  return rowByLabel(rows, "Latest saved review") || rowByLabel(rows, "Latest review receipt");
}

function statusClass(row) {
  if (!row) return "neutral";
  if (row.kind === "attention" || row.status === "blocked") return "attention";
  if (row.kind === "ready" || row.status === "ready" || row.status === "fresh") return "ready";
  return "neutral";
}



// View-model for the Assumptions ledger (sections/assumptions.jsx): verified axioms (the foundation),
// plus the derived-constraint ledger (confirmed/provisional) — all from the eval-results payload.
function buildAssumptionsView(evalResults) {
  const evalOk = evalResults && evalResults.ok;
  const c = (evalOk && evalResults.constraints) || {};
  const provisional = Array.isArray(c.provisional) ? c.provisional : [];
  // The CLI returns a newly-proposed constraint in BOTH proposed_this_run and provisional — dedup so
  // the analyst doesn't see the same assumption twice.
  const _ctext = (x) => String((x && (x.constraint || x.text)) || x || "").trim();
  const provSet = new Set(provisional.map(_ctext));
  const proposedThisRun = (Array.isArray(c.proposed_this_run) ? c.proposed_this_run : []).filter((p) => !provSet.has(_ctext(p)));
  return {
    hasRun: Boolean(evalOk),
    verifiedAxioms: (evalOk && Array.isArray(evalResults.verified_axioms)) ? evalResults.verified_axioms : [],
    confirmed: Array.isArray(c.confirmed) ? c.confirmed : [],
    provisional,
    proposedThisRun,
    // Assumptions the loop RETRACTED — a ledger that only grows is dishonest; show what it gave up.
    retiredAxioms: (evalOk && Array.isArray(evalResults.retired_axioms)) ? evalResults.retired_axioms : [],
    threshold: c.confirmation_threshold_runs,
  };
}

// View-model for the Evidence screen (sections/evidence.jsx). Data via /api/sources (files) +
// claim-support (backing) + snapshot Evidence-readiness (compile freshness) + evidence gaps.
function buildEvidenceView(sourceList, claimSupport, snapshot, evidenceGaps, sourceActionRunning, evalResults) {
  const sources = Array.isArray(sourceList && sourceList.sources) ? sourceList.sources.filter(Boolean) : [];
  // Source health: does each COMPILED source still match the file on disk? A mismatch silently
  // invalidates every claim bound to it — the cheapest-fix soundness signal (claim_support.source_context,
  // kernel-verified by content hash). Join to the file rows by basename.
  const _base = (p) => String(p || "").split("/").pop() || "";
  const ctxList = Array.isArray(claimSupport && claimSupport.source_context) ? claimSupport.source_context : [];
  const ctxByBase = {};
  ctxList.forEach((c) => { const b = _base(c.path || c.relative_path); if (b) ctxByBase[b] = c; });
  const byType = {};
  for (const f of sources) {
    const t = f.source_type || "untyped";
    const fp = f.path || f.relative_raw_path || "";
    const ctx = ctxByBase[_base(fp)];
    (byType[t] = byType[t] || []).push({
      path: fp,
      chars: f.chars,
      provenance: f.sha256 || "",
      invalid: Boolean(f.invalid_source_type_declaration),
      // Stale = the loop compiled a different version than what's on disk now (or the source is missing).
      stale: Boolean(ctx && (ctx.status !== "verified" || ctx.hash_matches_index === false)),
    });
  }
  // evidence first, then the rest in a stable order.
  const order = ["source_evidence", "seed_hypothesis", "research_question", "collection_todo", "untyped"];
  const fileGroups = Object.keys(byType)
    .sort((a, b) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99))
    .map((type) => ({ type, files: byType[type] }));

  const rows = (snapshot && snapshot.rows) || [];
  const evidenceRow = rows.find((r) => r.label === "Evidence readiness");
  const project = snapshot && snapshot.project;
  const total = Number((claimSupport && claimSupport.claim_count) || 0);
  const thin = Number((claimSupport && claimSupport.weak_or_unsourced_count) || 0);
  const gapCount = Number(
    (evidenceGaps && (evidenceGaps.active_evidence_gap_count ?? (evidenceGaps.evidence_gaps || []).length)) || 0
  );
  // Source health — how many compiled sources no longer match the file on disk (the loop is reading
  // a stale version). Plain language for the ICP, not "hash mismatch".
  const staleCount = Object.keys(byType).reduce((acc, t) => acc + byType[t].filter((f) => f.stale).length, 0);
  const sourceHealth = { total: ctxList.length, stale: staleCount, blocked: Number((claimSupport && claimSupport.source_context_blocked_count) || 0) };
  // Gap severity — a "degrading" gap weakens the score; "blocking" stops the thesis; a boundary
  // ceiling means the gap can't be closed with more evidence (so "fetch a file" is the wrong move).
  const sc = (evalResults && evalResults.ok && evalResults.score_contract) || {};
  // The actual gaps — each one the run flagged as missing. The kernel marks which can be FETCHED from
  // the web (can_public_fetch / public_evidence) vs which need a local check (local_verification).
  const _sev = { blocking: 0, degrading: 1, enriching: 2 };
  const activeGaps = (Array.isArray(evidenceGaps && evidenceGaps.active_gaps) ? evidenceGaps.active_gaps : [])
    .map((g) => ({
      target: String(g.target || g.gap_id || g.id || ""),
      what: String(g.description || g.producer_rationale || g.target || ""),
      severity: String(g.severity || "degrading"),
      online: Boolean(g.can_public_fetch || (g.recovery_kind === "public_evidence") || (g.recovery_channel === "out_of_loop_evidence_recovery")),
      query: String(g.fetch_query || ""),
    }))
    .filter((g) => g.target || g.what)
    .sort((a, b) => (_sev[a.severity] ?? 1) - (_sev[b.severity] ?? 1));
  const gaps = {
    count: gapCount,
    blocking: Number(sc.blocking_evidence_gap_count || 0),
    degrading: Number(sc.degrading_evidence_gap_count || 0),
    ceiling: Boolean(sc.evidence_boundary_ceiling_detected),
    items: activeGaps,
    fetchable: activeGaps.filter((g) => g.online).length,
  };

  return {
    fileGroups,
    fileCount: sources.length,
    untypedCount: Number((sourceList && sourceList.untyped_source_count) || 0),
    invalidCount: Number((sourceList && sourceList.invalid_source_type_count) || 0),
    rawDir: (sourceList && sourceList.raw_dir) || (project ? `projects/${project}/raw` : "raw/"),
    backing: { total, thin, strong: total > 0 ? Math.max(0, total - thin) : 0 },
    sourceHealth,
    compile: {
      fresh: Boolean(evidenceRow && evidenceRow.kind === "ready"),
      running: Boolean(sourceActionRunning),
    },
    compiledFile: project ? `projects/${project}/compiled_evidence_packet.json` : "",
    gaps,
    gapCount,
  };
}

// Plain-language meaning of each rubric flag (the "rubric spec" gates README, written for the
// PE/consultant/researcher persona). Matched by substring against the stripped flag name so
// enable_/disable_/require_ variants all resolve. Source: src/ztare/gates/README.md + global_gates.py.
const GATE_GLOSS = [
  [/evidence_fit/, "The thesis must actually fit the evidence you gave it — fails if the argument drifts from what the data shows."],
  [/uniqueness_gap/, "The thesis must beat rival explanations by a clear margin — fails if an alternative explains the evidence just as well."],
  [/holdout/, "Tests the thesis against evidence held back from it — hard-fails if it only works on the data it was built on."],
  [/extrapolation/, "Checks the thesis still holds when stretched past the range of the evidence (visible vs held-out span)."],
  [/fit_primitive/, "Fits the thesis's quantitative model to the numbers with a real optimizer — for forecasts and unit-economics claims."],
  [/i_model_in_submission/, "Requires a falsification model in the submission — the thesis must ship the test that could prove it wrong."],
  [/falsif/, "Scores whether the thesis states explicit kill criteria: what observation would refute it."],
  [/asymptotic/, "Catches 'always / never / infinite' claims the finite evidence can't actually support."],
  [/domain_match/, "The thesis's variables must match the evidence's schema — fails on a name or scope mismatch."],
  [/derived_constraint/, "Carries hard constraints learned in earlier iterations forward, so the thesis can't relitigate settled points."],
  [/bridge_scope/, "If the thesis claims a class, it must apply to that class only or explicitly declare the extension."],
  [/per_class_farther_tail|farther_tail|_tail/, "Stress-tests the thesis in the extreme tail of the data, not just the easy middle."],
  [/coordinate_invariance/, "The thesis's predictions must survive declared coordinate/units changes."],
  [/continuum_limit/, "Sanity-checks any discrete-to-continuous (or small-to-large) extrapolation the thesis makes."],
];
const MODE_GLOSS = {
  newton: "Newton mode — the thesis must show a mechanism/derivation, not just a curve that fits.",
  kepler: "Kepler mode — an empirical pattern that fits the evidence is enough; mechanism isn't required.",
};
function gateGloss(name) {
  for (const [re, text] of GATE_GLOSS) if (re.test(name)) return text;
  return "";
}

// View-model for the humane Scoring guide (sections/scoringguide.jsx) — from the rubric spec.
function buildScoringView(scoringGuideContext) {
  const g = scoringGuideContext || {};
  const r = (g.parsed && typeof g.parsed === "object") ? g.parsed : {};
  const exists = Boolean(g.exists && r && Object.keys(r).length);
  const gates = [];
  Object.keys(r).forEach((k) => {
    if (typeof r[k] !== "boolean") return;
    if (!(/^(enable_|disable_|require_)/.test(k) || /_gate$|_mode$/.test(k))) return;
    let name = k, on = r[k];
    if (k.startsWith("disable_")) { name = k.slice(8); on = !r[k]; }       // disabled ⇒ gate is OFF
    else if (k.startsWith("enable_")) { name = k.slice(7); }
    else if (k.startsWith("require_")) { name = k.slice(8); }
    const label = name.replace(/_/g, " ").replace(/\s*gate$/, "").replace(/^\w/, (c) => c.toUpperCase());
    gates.push({
      key: k,
      label: label + (/_gate$/.test(name) || k.includes("gate") ? " gate" : ""),
      on,
      value: r[k],                       // raw stored boolean — what a toggle flips
      gloss: gateGloss(name),            // what this gate actually does (the spec)
      reason: r[`${k}_reason`] || "",    // why it's set this way for THIS thesis
    });
  });
  const mode = r.rubric_mode || "";
  return {
    exists,
    mode,
    modeReason: r.rubric_mode_reason || "",
    modeGloss: MODE_GLOSS[String(mode).toLowerCase()] || "",
    dimensions: Array.isArray(r.dimensions) ? r.dimensions : [],
    gates,
    persona: r.persona || "",
    committee: Array.isArray(g.committee) ? g.committee : [],
  };
}

// View-model for the Charter screen (sections/charter.jsx). Parses the charter markdown into titled
// mandate sections, carries the kernel's validation, and joins charter-drift from the latest run.
function buildCharterView(charterDraft, evalResults) {
  const d = charterDraft || {};
  const text = String(d.text || "").replace(/\r\n/g, "\n");
  const validation = d.validation || {};
  // Parse "## " section titles only — the rail uses them to name the kernel-enforced contracts.
  const cleaned = (text.match(/^##\s+(.+?)\s*$/gm) || []).map((line) => ({ title: line.replace(/^##\s+/, "").trim() }));
  const issues = Array.isArray(validation.issues) ? validation.issues : [];
  const drift = (evalResults && evalResults.ok && evalResults.charter_drift && evalResults.charter_drift.drift_detected)
    ? evalResults.charter_drift : null;
  return {
    exists: Boolean(d.path) && text.trim().length > 0,
    editable: d.editable,
    path: d.path || "",
    // The document for rendering — drop a single leading H1 (the screen already titles it).
    markdown: text.replace(/^\s*#\s+.*\n/, "").trim(),
    sections: cleaned,
    complete: validation.ok === true || (issues.length === 0 && cleaned.length > 0),
    missing: issues,
    drift,
  };
}

// View-model for History (sections/history.jsx) — the saved trail as a grouped activity list. Reuses
// the receipt helpers; leads with what makes each save distinct (the group header already names the kind).
// What each saved-work kind MEANS to a human + its timeline dot tone. [regex, verb, tone].
const _HISTORY_VERBS = [
  [/report.?support|verdict|report.?contract|report.?readiness/, "Checked the report's backing", "muted"],
  [/synthes|report.?inputs/, "Refreshed the report", "muted"],
  [/decision|review|next.?step|row.?action/, "Recorded a decision", "accent"],
  [/source.?import/, "Added evidence", "ok"],
  [/source.?edit/, "Edited an evidence file", "ok"],
  [/source|evidence/, "Changed evidence", "ok"],
  [/charter/, "Revised the charter", "indigo"],
  [/scoring.?guide|rubric/, "Adjusted the scoring guide", "accent"],
  [/intake|claim|thesis/, "Sharpened the claim", "accent"],
  [/project.?file/, "Saved the project file", "muted"],
  [/run|harden/, "Pressure-tested the thesis", "accent"],
];
function _historyMeta(item) {
  const k = `${item.kind || ""} ${item.display_kind || ""}`.toLowerCase();
  for (const [re, verb, tone] of _HISTORY_VERBS) if (re.test(k)) return { verb, tone };
  return { verb: displayMessage(item.display_kind || item.kind || "Saved work"), tone: "muted" };
}
// Relative, human time ("just now" / "12 min ago" / "3h ago" / "Jun 28"). Browser-side, real clock.
function _humaneTime(iso) {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return displayText(iso);
  const min = Math.round((Date.now() - t) / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.round(hr / 24);
  if (days < 7) return `${days}d ago`;
  try { return new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric" }); } catch (_e) { return ""; }
}
function _dayLabel(iso) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "Earlier";
  const d = new Date(t), now = new Date();
  const same = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  if (same(d, now)) return "Today";
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (same(d, y)) return "Yesterday";
  try { return d.toLocaleDateString(undefined, { month: "long", day: "numeric", year: d.getFullYear() !== now.getFullYear() ? "numeric" : undefined }); } catch (_e) { return "Earlier"; }
}

// A LeanMill/autoresearch run_id is a unix-seconds timestamp string → ISO.
function _runIso(runId) {
  const n = parseInt(runId, 10);
  if (!n || n < 1e9) return "";
  try { return new Date(n * 1000).toISOString(); } catch (_e) { return ""; }
}

// View-model for History (sections/history.jsx) — the investigation's NARRATIVE, not the workbench's
// internal save log. Leads with the runs (how the score evolved — the real research progress) + the
// meaningful saves (decisions / evidence / charter); the process save-receipts (report-readiness
// refreshes, file saves) are demoted to a quiet footnote. Activity timeline: day groups + a spine of
// type-coloured nodes, human verbs + relative time. See PRD §7.8.
function buildHistoryView(receiptHistory, scoreTrajectory, runHistory, compression) {
  const events = [];

  // 1. RUN events — the investigation's research log. A PE/research lead reading history wants more
  // than a score: did the thesis actually reach a NEW BEST (champion promoted) or just get re-tested;
  // what WEAKNESS the run exposed (the thread of the inquiry); whether an independent model checked it
  // (trust) or it self-judged; what it cost; whether it cleared the gates. We join the per-run
  // weakest_point + gate count from run-history (recent_runs) onto the score-trajectory by run_id.
  const runs = (scoreTrajectory && Array.isArray(scoreTrajectory.runs)) ? scoreTrajectory.runs : [];
  const recentRuns = (runHistory && Array.isArray(runHistory.recent_runs)) ? runHistory.recent_runs : [];
  const byRunId = {};
  recentRuns.forEach((rr) => { if (rr && rr.run_id) byRunId[String(rr.run_id)] = rr; });
  const rubricChanged = Boolean(scoreTrajectory && scoreTrajectory.rubric_changed_vs_champion);
  // The newest real run is the only one whose rubric we can compare to the champion fingerprint.
  let newestRunId = "";
  runs.forEach((r) => { const id = String(r.run_id || ""); if (id > newestRunId) newestRunId = id; });
  let probeCount = 0;
  let probeLatest = "";
  runs.forEach((r) => {
    const iters = Number(r.iteration_count) || 0;
    const best = typeof r.best_score === "number" ? r.best_score : null;
    const final = typeof r.final_score === "number" ? r.final_score : null;
    const score = best !== null ? best : final;
    const promoted = (r.iterations || []).some((it) => it && it.champion_promoted);
    // A run that neither promoted a champion nor produced a score changed nothing — quiet probe.
    if (!promoted && score === null) {
      if (iters >= 1) { probeCount += 1; if (!probeLatest) probeLatest = _humaneTime(_runIso(r.run_id)); }
      return;
    }
    const iso = _runIso(r.run_id);
    const rr = byRunId[String(r.run_id)] || {};
    const revisedRubric = rubricChanged && String(r.run_id) === newestRunId;
    // Headline is the QUALITATIVE outcome, not the number. The score is rubric-relative — under
    // autoevolve the rubric drifts across runs, so a raw score is a partial signal, never the verdict.
    // What's real: did the kernel find a STRONGER version (champion promoted) or only re-test and hold.
    const detail = promoted
      ? "Produced a stronger version of the claim"
      : (score !== null ? "Re-tested — held, no stronger version found" : `Ran ${iters} round${iters === 1 ? "" : "s"}`);
    // The weakness this run exposed — the substance of the research log (rubric-independent).
    const weakSpot = typeof rr.weakest_point === "string" ? rr.weakest_point.trim() : "";
    // Signals, in priority order. The score is one chip among several, explicitly caveated when the
    // rubric moved. Self-judged is an honest trust caveat for diligence.
    const meta = [];
    if (score !== null) meta.push(revisedRubric ? `scored ${score} (revised rubric — not comparable to earlier runs)` : `scored ${score}`);
    const judge = r.judge_model || "";
    const mutator = r.mutator_model || "";
    if (judge && mutator) meta.push(judge !== mutator ? "Cross-checked by a different model" : "Self-judged (same model drafted and scored)");
    const cost = (r.iterations || []).reduce((s, it) => s + (Number(it && it.estimated_cost_usd) || 0), 0);
    if (cost > 0) meta.push(cost < 0.01 ? "<$0.01" : `$${cost.toFixed(2)}`);
    const gatesFailed = Number(rr.gate_failure_count) || 0;
    if (rr.gate_failure_count !== undefined) meta.push(gatesFailed ? `${gatesFailed} gate${gatesFailed === 1 ? "" : "s"} failed` : "all gates clear");
    events.push({
      verb: "Pressure-tested the thesis", tone: promoted ? "accent" : "ok", detail, noCollapse: true,
      weakSpot, meta, iso, when: _humaneTime(iso), day: _dayLabel(iso), openType: "", openValue: "",
    });
  });

  // 2. MEANINGFUL saves (decisions / evidence / charter / scoring / claim). Process saves → footnote.
  const receipts = (receiptHistory && receiptHistory.receipts) || [];
  let processCount = 0;
  let processLatest = "";
  receipts.forEach((item) => {
    const { verb, tone } = _historyMeta(item);
    if (tone === "muted") { processCount += 1; if (!processLatest) processLatest = _humaneTime(item.applied_at); return; }
    const target = item.check_label || item.display_label || item.item_label || item.row || "";
    let detail = humanizeReceiptSummary(item.display_summary || item.summary || "").trim();
    if (/(accepted|saved|recorded|done|complete|check)\b/i.test(detail) && detail.split(/\s+/).length <= 4) detail = "";
    if (detail && verb && detail.toLowerCase().startsWith(verb.toLowerCase())) detail = detail.slice(verb.length).replace(/^[\s:·.-]+/, "").trim();
    if (!detail && target && !/[\/]/.test(String(target))) detail = targetLabel(target);
    const artifactPath = receiptArtifactPath(item);
    const previewable = isPreviewableRepoPath(artifactPath);
    events.push({
      verb, tone, detail: detail || "", iso: item.applied_at || "",
      when: _humaneTime(item.applied_at), day: _dayLabel(item.applied_at),
      openType: previewable ? "file" : "receipt",
      openValue: previewable ? artifactPath : (item.path || ""),
    });
  });

  // Newest first across both sources.
  events.sort((a, b) => (Date.parse(b.iso) || 0) - (Date.parse(a.iso) || 0));

  // 3. Collapse only TRULY IDENTICAL consecutive events (same verb AND same detail) within a day —
  // e.g. repeated "Changed evidence" with no distinguishing text. Runs carry a distinct score each,
  // so they never collapse: every run's score arc stays visible (that's the point of run history).
  const nodes = [];
  events.forEach((e) => {
    const last = nodes[nodes.length - 1];
    // Runs never collapse — each is a distinct milestone with its own weak-spot, score, and trust.
    if (!e.noCollapse && last && !last.items[0].noCollapse && last.verb === e.verb && last.day === e.day && (last.items[0].detail || "") === (e.detail || "")) { last.items.push(e); }
    else { nodes.push({ verb: e.verb, tone: e.tone, day: e.day, latestWhen: e.when, items: [e] }); }
  });
  // 3. Group nodes by day.
  const days = [];
  nodes.forEach((n) => {
    n.count = n.items.length;
    n.hasDetail = n.items.some((i) => i.detail);
    let day = days.find((d) => d.label === n.day);
    if (!day) { day = { label: n.day, nodes: [] }; days.push(day); }
    day.nodes.push(n);
  });
  // Quiet footnotes — things that happened but didn't change the investigation's standing.
  const footnotes = [];
  if (probeCount) footnotes.push(`${probeCount} exploratory run${probeCount === 1 ? "" : "s"} that didn't change the standing${probeLatest ? ` · latest ${probeLatest}` : ""}`);
  if (processCount) footnotes.push(`${processCount} routine save${processCount === 1 ? "" : "s"} — readiness refreshes and file writes${processLatest ? ` · latest ${processLatest}` : ""}`);
  // The advisory "worth another pass?" read — surfaced only when the kernel has enough history to judge
  // (recommendation != no_signal). Verdict + tooltip come from run-history's compression_progress object
  // (kernel-computed, universal via the DAG-MDL fallback); the workbench only maps it to a tone and renders.
  const CP_TONE = { continue: "ok", watch: "neutral", measure_before_continuing: "warn", narrow_or_pivot: "warn" };
  const cp = (compression && compression.recommendation && compression.recommendation !== "no_signal")
    ? { headline: compression.label || "", detail: compression.summary || "",
        tone: CP_TONE[compression.recommendation] || "neutral", how_computed: compression.how_computed || "",
        stagnation: compression.stagnation_length, drops: compression.compression_drop_count }
    : null;
  return {
    // The timeline itself is the summary; no count headline (that's the count-and-link smell).
    summary: "",
    days,
    footnotes,
    compression: cp,
  };
}

// View-model for the research Map (sections/researchmap.jsx) — the program's node/edge graph + threads.
function buildMapView(researchMap, researchGraph) {
  const rm = researchMap || {};
  const sections = Array.isArray(rm.sections) ? rm.sections : [];
  // The kernel emits the SAME generic scaffold sections (Orientation / Project work / Synthesis /
  // Handoffs …) for every project — that's noise. The program's live structure is three things the
  // ICP actually steers by: what's contested, what's left to test, what holds it up. Bucket to those.
  const find = (re) => {
    const s = sections.find((x) => re.test(String(x.id || x.label || "").toLowerCase()));
    return (s && Array.isArray(s.details) ? s.details : []).map((d) => String(d).trim()).filter(Boolean);
  };
  const tensions = find(/tension/);
  const toTest = find(/branch|frontier|discrimin|to.?test/);
  const support = find(/support/);
  const scaffoldRe = /tension|branch|frontier|discrimin|support|orientation|project.?work|run.?lesson|synthesis|handoff/;
  const other = sections
    .filter((s) => !scaffoldRe.test(String(s.id || s.label || "").toLowerCase()))
    .map((s) => ({ label: displayText(s.label || s.id || ""), detail: (Array.isArray(s.details) && s.details[0]) ? String(s.details[0]).trim() : "" }))
    .filter((s) => s.label && s.detail);
  // The GRAPH is the research-landscape PROJECTION (research-graph CLI) — a typed aggregate over the
  // project's artifacts (thesis · sub-claims · evidence · tensions · gaps · constraints · branches ·
  // falsifiers · rejected), not the fixed scaffold. GraphView applies lenses + node typing.
  const rg = researchGraph || {};
  const graphNodes = Array.isArray(rg.nodes) ? rg.nodes : [];
  const graphEdges = Array.isArray(rg.edges) ? rg.edges : [];

  return {
    tensions, toTest, support, other,
    hasContent: Boolean(tensions.length || toTest.length || support.length || graphNodes.length),
    graphNodes, graphEdges,
    graphTruncated: (rg && rg.truncated) || null,
    // Graph-algorithmic structural reads (kernel-computed): linchpin source, weakest link,
    // most-contested claim, unsupported assertions, circular reasoning.
    graphInsights: (rg && rg.insights) || null,
  };
}

// View-model for Verdict (sections/verdict.jsx) — the trust judgment + deliverable. The substance is
// the per-claim support breakdown (claim_support) + the report's weak spots, not freshness.
// Plain labels for the kernel's per-claim support statuses (no jargon).
const _SUPPORT_LABEL = {
  direct_source_support: "directly sourced",
  synthesized_across_sources: "synthesized across sources",
  mixed_source_support: "mixed support",
  local_or_seed_support: "local/seed evidence only",
  unsupported_no_sources: "no source",
  unsupported_missing_sources: "source file missing",
};
function buildVerdictView(snapshot, reportContext, claimSupport, evalResults) {
  const rc = reportContext || {};
  const cs = claimSupport || {};
  // The score is capped by un-sourceable evidence, not a weak thesis — a different next action.
  const ceilingCapped = Boolean(evalResults && evalResults.ok && evalResults.score_contract && evalResults.score_contract.evidence_boundary_ceiling_detected);
  // Reuse the CLI-computed reliability verdict (same judgment Thesis shows — one source of truth).
  const verdictV = claimSupportVerdict(cs, ceilingCapped);
  const toneMap = { rely: "rely", verify_inference: "almost", do_not_rely: "no", not_checked: "almost" };
  const tone = toneMap[verdictV.tier] || "almost";

  // Resolve a claim row's bare source filename (e.g. "change_and_staffing_notes.md") to a previewable
  // repo path. claim_support.source_context carries the real full paths — join by basename; fall back
  // to projects/<p>/raw/<name>. (Passing the bare name to the file viewer 400s.)
  const project = snapshot && snapshot.project;
  const _b = (p) => String(p || "").split("/").pop() || "";
  const ctxByBase = {};
  (Array.isArray(cs.source_context) ? cs.source_context : []).forEach((c) => {
    const full = c && (c.path || c.relative_path);
    if (full) ctxByBase[_b(full)] = full;
  });
  const resolveSource = (s) => {
    const base = _b(s);
    if (ctxByBase[base]) return ctxByBase[base];
    if (String(s).startsWith("projects/")) return s;
    return project ? `projects/${project}/raw/${base}` : String(s);
  };

  // "Exactly where is it thin" — the per-claim rows that aren't directly sourced, each with its plain
  // status + clickable source files. The CLI classifies each claim; we just surface the ones to verify.
  const rows = Array.isArray(cs.rows) ? cs.rows : [];
  const rank = (s) => (/unsupported/.test(s) ? 0 : /mixed|local_or_seed/.test(s) ? 1 : 2);
  const toVerify = rows
    .filter((r) => String(r.support_status || "") && String(r.support_status || "") !== "direct_source_support")
    .map((r) => ({
      claim: String(r.claim || r.field || ""),
      statusLabel: _SUPPORT_LABEL[r.support_status] || String(r.support_status || "").replace(/_/g, " "),
      statusTone: /unsupported/.test(String(r.support_status || "")) ? "no" : "almost",
      sources: (Array.isArray(r.source_paths) ? r.source_paths.filter(Boolean) : []).map((s) => ({ name: _b(s).replace(/\.[a-z0-9]+$/i, ""), path: resolveSource(s) })),
      issue: String(r.issue || ""),
    }))
    .sort((a, b) => rank(a.statusLabel) - rank(b.statusLabel));
  // Total claims needing verification = everything not directly sourced (rows may show a subset).
  const directCount = Number((cs.status_counts || {}).direct_source_support || 0);
  const attentionTotal = Math.max(0, Number(cs.claim_count || 0) - directCount);

  // The report filename is renderer-dependent (Report.<renderer>.md — decision_brief / founder_memo /
  // research_note / …). Take the renderer from the report context, never hardcode it.
  const renderer = String(rc.renderer || (snapshot && snapshot.renderer) || "decision_brief").trim();
  return {
    status: rc.status || (snapshot && snapshot.report_status) || "unknown",
    tone,
    phrase: verdictV.phrase,
    why: verdictV.why,
    breakdown: verdictV.breakdown,
    ceilingCapped,
    toVerify,
    attentionTotal,
    backing: { total: Number(cs.claim_count || 0), thin: Number(cs.weak_or_unsourced_count || 0) },
    contractFile: rc.report_support_contract || "",
    // The loop's probability the thesis holds (probability_dag.outcome) — a confidence read at the verdict.
    confidence: (evalResults && evalResults.ok && evalResults.probability_dag && evalResults.probability_dag.outcome
      && typeof evalResults.probability_dag.outcome.probability === "number")
      ? evalResults.probability_dag.outcome.probability : null,
    // The thesis itself — the question a fresh on-demand forecast (scratch contract) would price.
    question: (() => {
      const cr = rowByLabel((snapshot && snapshot.rows) || [], "Bounded claim");
      return String((cr && (cr.detail || cr.display_detail)) || "").trim();
    })(),
    // The actual deliverables — the rendered report doc + the claim card (markdown the file viewer renders).
    reportFile: project ? `projects/${project}/Report.${renderer}.md` : "",
    cardFile: project ? `projects/${project}/synthesis/claim_card.md` : "",
  };
}

// View-model for Open points (sections/openpoints.jsx) — the loop's kernel-generated open questions
// + discriminators, from the eval-results CLI facets.
function buildOpenPointsView(evalResults) {
  const evalOk = evalResults && evalResults.ok;
  const inverter = (evalOk && evalResults.inverter) || {};
  // The post-champion adversary's own attempts to break the thesis — the sharpest open points.
  const redTeam = (Array.isArray(inverter.tests) ? inverter.tests : [])
    .filter((t) => t && t.doubt)
    .map((t) => ({
      doubt: String(t.doubt || ""),
      steps: Array.isArray(t.steps) ? t.steps.map(String).filter(Boolean) : [],
      autoTestable: Boolean(t.auto_testable),
    }));
  return {
    hasRun: Boolean(evalOk),
    redTeam,
    // Holes in the REASONING (distinct from open_questions, which are missing-data gaps).
    logicGaps: (evalOk && Array.isArray(evalResults.logic_gaps)) ? evalResults.logic_gaps.map(String).filter(Boolean) : [],
    openQuestions: (evalOk && Array.isArray(evalResults.open_questions)) ? evalResults.open_questions : [],
    discriminators: (evalOk && Array.isArray(evalResults.discriminators)) ? evalResults.discriminators : [],
  };
}

// View-model for the Harden run console (sections/runconsole.jsx). Effective run config comes from the
// CLI's /api/run-config (per-project overrides on global defaults); readiness + live status from trace
// + run-status telemetry. Grounded — no assumptions about defaults the kernel doesn't give us.
// Translate the kernel's information-yield decision (will another run learn anything?) into a humane
// pre-launch line — the ICP's "is it worth spending on another run?" answer.
const _YIELD_GUIDANCE = {
  CONTINUE: { tone: "ok", text: "The last run was still learning — another run should keep sharpening the thesis." },
  REFRESH_SPECIALISTS: { tone: "warn", text: "Progress is stalling — change the run settings (models or judging) before running again." },
  PIVOT_REQUIRED: { tone: "warn", text: "The thesis has stopped improving — it may need reframing, not another run." },
  UNDERIDENTIFIED: { tone: "warn", text: "There isn't enough evidence yet to learn more — add evidence before another run." },
};

function buildRunConsoleView(runConfig, runConfigOverrides, runStatus, traceContext, runHistory) {
  const fields = (runConfig && Array.isArray(runConfig.fields)) ? runConfig.fields : [];
  const globals = {};
  fields.forEach((f) => { if (f && f.key) globals[f.key] = f.global_value; });
  const ov = runConfigOverrides || {};
  const eff = (key) => (ov[key] !== undefined && ov[key] !== "" ? ov[key] : globals[key]);

  const itersRaw = eff("ZTARE_WORKBENCH_RUN_ITERS");
  const iters = itersRaw === undefined || itersRaw === null || itersRaw === "" ? "12" : String(itersRaw);
  const modes = [
    eff("ZTARE_WORKBENCH_RUN_TRANSPORT") === "subscription" ? "Codex/Claude subscription" : "Provider API",
    eff("ZTARE_WORKBENCH_RUN_JUDGING") === "committee" ? "3-panel committee" : "Single judge",
    eff("ZTARE_WORKBENCH_RUN_RUBRIC_MODE") === "rotating" ? "Rotating rubric" : "Fixed rubric",
  ];

  const plan = (traceContext && traceContext.plan_preview) || {};
  const kernel = (traceContext && traceContext.kernel_entry) || {};
  const ready = plan.status === "ready_for_bounded_run" && kernel.can_enter_kernel === true;

  const rs = runStatus || {};
  const status = rs.active
    ? {
        active: true,
        iteration: rs.iteration || rs.iteration_count || 1,
        budget: rs.iteration_budget || null,
        score: typeof rs.latest_score === "number" ? rs.latest_score : null,
        mutator: rs.mutator_model || "",
      }
    : { active: false };

  // Will another run learn anything? (information-yield decision from the last run, if present.)
  const iy = (runHistory && runHistory.information_yield) || {};
  const yieldGuidance = (iy.action && _YIELD_GUIDANCE[iy.action]) || null;

  return {
    iters,
    modes,
    ready,
    blockedReason: ready ? "" : "Run the quick readiness check first — it confirms the files and rubric before anything spends a model call.",
    status,
    yieldGuidance,
  };
}

// View-model for "What the run found" (sections/results.jsx) — the run's epistemic payload from the
// eval-results CLI. Surfaces the powerful run-generated outputs that were invisible in the old UI.
function buildRunFindingsView(evalResults, scoreTrajectory) {
  const evalOk = evalResults && evalResults.ok;
  const align = (evalOk && evalResults.adversarial_alignment) || {};
  // The thesis evolves across iterations (mutator proposes → AI panel judges → champion survives).
  // Surface that evolution: the score series from the latest run + iteration/run counts.
  const runs = (scoreTrajectory && Array.isArray(scoreTrajectory.runs)) ? scoreTrajectory.runs : [];
  const lastRun = runs.length ? runs[runs.length - 1] : null;
  const series = lastRun && Array.isArray(lastRun.iterations)
    ? lastRun.iterations.map((it) => it.score).filter((s) => typeof s === "number")
    : [];
  return {
    hasRun: Boolean(evalOk),
    score: evalOk ? evalResults.score : null,
    series,
    // A score under a CHANGED rubric isn't comparable to the saved-best — flag it so a lower number
    // reads as "tougher bar", not "worse claim" (the score is rubric-relative).
    rubricChanged: Boolean(scoreTrajectory && scoreTrajectory.rubric_changed_vs_champion),
    iterationCount: lastRun ? (lastRun.iteration_count || series.length) : 0,
    runCount: runs.length,
    firstScore: series.length ? series[0] : null,
    weakestPoint: (evalOk && String(evalResults.weakest_point || "").trim()) || "",
    logicGaps: (evalOk && Array.isArray(evalResults.logic_gaps)) ? evalResults.logic_gaps : [],
    frictionPoints: (evalOk && Array.isArray(evalResults.friction_points)) ? evalResults.friction_points : [],
    debateSummary: (evalOk && String(evalResults.debate_summary || "").trim()) || "",
    trust: {
      mode: (evalOk && evalResults.score_contract && evalResults.score_contract.mode) || "",
      alignmentText: String(align.text || "").trim(),
      alignmentRead: align.read || "",
    },
    dag: (evalOk && evalResults.probability_dag) || {},
    // The post-champion adversary's falsification tests — the strongest "what would change my mind".
    inverter: (evalOk && evalResults.inverter && Array.isArray(evalResults.inverter.tests) && evalResults.inverter.tests.length)
      ? evalResults.inverter : null,
    // Did the thesis drift off the charter's real intent during the run?
    charterDrift: (evalOk && evalResults.charter_drift && evalResults.charter_drift.drift_detected)
      ? evalResults.charter_drift : null,
    // Is the score TRUSTWORTHY? — why it capped (gaming/narrow gate) + deterministic structural checks.
    metaAudit: (evalOk && evalResults.meta_audit && (evalResults.meta_audit.cap_pattern || (evalResults.meta_audit.gates_missed || []).length))
      ? evalResults.meta_audit : null,
    coherence: (evalOk && evalResults.coherence && Array.isArray(evalResults.coherence.checks) && evalResults.coherence.checks.length)
      ? evalResults.coherence : null,
    // The score is capped by MISSING EVIDENCE, not by a weak thesis — a different next action.
    evidenceCeiling: Boolean(evalOk && evalResults.score_contract && evalResults.score_contract.evidence_boundary_ceiling_detected),
  };
}

// Map a report_status to the secondary verdict phrase (the score is the headline; this is secondary).
// Reads the CLI-computed reliability verdict (claim_support.py `reliability`) — the CLI is the master,
// the workbench only renders + maps the tier to a colour. Falls back to "not checked" if absent.
// The evidence-boundary ceiling (from eval_results) is appended as a caveat when present.
const _VERDICT_TONE = { rely: "high", verify_inference: "mid", do_not_rely: "low", not_checked: "mid" };
function claimSupportVerdict(claimSupport, ceilingCapped) {
  const r = (claimSupport && claimSupport.reliability) || {};
  const tier = r.tier || "not_checked";
  const why = (r.summary || "Run a backing check to see how each claim is supported.")
    + (ceilingCapped ? " · score capped by missing evidence" : "");
  return {
    phrase: r.headline || "Not checked yet",
    why,
    tone: _VERDICT_TONE[tier] || "mid",
    warn: tier !== "rely",
    tier,
    breakdown: Array.isArray(r.breakdown) ? r.breakdown : [],
  };
}

// View-model for the Thesis screen (sections/thesis.jsx). main.js owns the data; the section is a
// pure view. Reuses the snapshot row helpers + claim-support; the run's epistemic payload (score,
// weakest_point, constraints ledger) comes from the eval-results CLI via /api/eval-results.
function buildThesisView(snapshot, claimSupport, evalResults) {
  const rows = (snapshot && snapshot.rows) || [];
  const claimRow = rowByLabel(rows, "Bounded claim");
  const falsifierRow = rowByLabel(rows, "Next falsifier");
  const nonClaimRow = rowByLabel(rows, "Non-claims");
  const assumptionRow = rowByLabel(rows, "Assumptions and constraints");
  const sourceRow = rowByLabel(rows, "Source readiness");
  const evidenceRow = rowByLabel(rows, "Evidence readiness");
  const reportStatus = (snapshot && snapshot.report_status) || "unknown";

  const total = Number((claimSupport && claimSupport.claim_count) || 0);
  const thin = Number((claimSupport && claimSupport.weak_or_unsourced_count) || 0);
  const evidenceReady =
    sourceRow && sourceRow.kind !== "attention" && evidenceRow && evidenceRow.kind !== "attention";

  const evalOk = evalResults && evalResults.ok;
  const score = evalOk && (typeof evalResults.score === "number") ? evalResults.score : null;
  const scoreBand = score === null ? null : score >= 80 ? "high" : score >= 60 ? "mid" : "low";
  const constraints = (evalOk && evalResults.constraints) || {};
  const topProvisional = Array.isArray(constraints.provisional) && constraints.provisional[0]
    ? shortText(constraints.provisional[0].constraint, 90)
    : "";
  // Score-contract: is the score capped by missing evidence (go find data) rather than a weak claim?
  const scoreContract = (evalOk && evalResults.score_contract) || {};
  const ceilingCapped = Boolean(scoreContract.evidence_boundary_ceiling_detected);
  // Constraints the loop LEARNED this run — distinct from the standing provisional ledger.
  const learnedThisRun = Array.isArray(constraints.proposed_this_run) ? constraints.proposed_this_run.length : 0;
  const weakSpotsMore =
    ((evalOk && Array.isArray(evalResults.logic_gaps) && evalResults.logic_gaps.length) || 0) +
    ((evalOk && Array.isArray(evalResults.friction_points) && evalResults.friction_points.length) || 0);

  // Assumptions: prefer the eval-results ledger; fall back to parsing the snapshot row's count text.
  let confirmed = Number(constraints.confirmed_count || 0);
  let provisional = Number(constraints.provisional_count || 0);
  if (!evalOk && assumptionRow && assumptionRow.detail) {
    const m = String(assumptionRow.detail).match(/(\d+)\s+confirmed[^\d]+(\d+)\s+provisional/i);
    if (m) { confirmed = Number(m[1]); provisional = Number(m[2]); }
  }

  const verdictV = claimSupportVerdict(claimSupport, ceilingCapped);
  return {
    score,
    scoreBand,
    verdict: {
      status: reportStatus,
      phrase: verdictV.phrase,
      why: verdictV.why,
      tone: verdictV.tone,
      weakCount: thin,
      warn: verdictV.warn,
    },
    claim: (claimRow && (claimRow.detail || claimRow.display_detail)) || "",
    claimWarning: (claimRow && claimRow.warning) || "",
    falsifierText: (falsifierRow && falsifierRow.detail) || "",
    weakestPoint: (evalOk && String(evalResults.weakest_point || "").trim()) || "",
    weakSpotsMore,
    ruledOut: nonClaimRow
      ? { summary: nonClaimRow.detail || "", file: nonClaimRow.file || nonClaimRow.source || "" }
      : null,
    assumptions: { confirmed, provisional, topConstraint: topProvisional, learnedThisRun },
    backing: {
      total,
      thin,
      strong: total > 0 ? Math.max(0, total - thin) : 0,
      ready: Boolean(evidenceReady),
      ceilingCapped,
      sourceDetail: (sourceRow && sourceRow.detail) || "",
    },
  };
}



function Sidebar({
  activeWorkspace,
  activeSubsection,
  setActiveWorkspace,
  setActiveSubsection,
  day0Mode = false,
  onNavigateWorkspace
}) {
  const activeSection = WORKSPACE_SECTIONS.find((item) => item.id === activeWorkspace) || WORKSPACE_SECTIONS[0];
  const leanMillActive = activeWorkspace === "leanmill";
  const productNavItems = [
    { id: "research", label: "ZTARE Projects", workspace: "projects", subsection: "Projects", icon: "projects" },
    { id: "leanmill", label: "LeanMill", workspace: "leanmill", subsection: "Overview", icon: "leanmill" },
    { id: "settings", label: "Settings", workspace: "projects", subsection: "Settings", icon: "settings" }
  ];
  const day0TaskItems = [
    { label: "Create project", workspace: "projects", subsection: "Connect project", body: "Start from a question, uploaded files, or a new local project folder." },
    { label: "Settings", workspace: "projects", subsection: "Settings", body: "Set model and evidence-fetch defaults before running project actions." }
  ];
  const projectTaskItems = day0Mode ? day0TaskItems : [
    { label: "Charter", workspace: "overview", subsection: "Charter", body: "The mandate this project serves — the question, scope limits, and what would change it. Your thesis tackles this." },
    { label: "Thesis", workspace: "overview", subsection: "Thesis", body: "What you're arguing, what would change your mind, where it's weakest, and how it held up." },
    { label: "Evidence", workspace: "sources", subsection: "Prepare files", body: "What backs the thesis. Add files and see what's missing." },
    { label: "Pressure-test the thesis", workspace: "run", subsection: "Ready to run", body: "Run the loop that attacks your thesis. Run settings and the scoring guide live here as prep." },
    { label: "Map", workspace: "overview", subsection: "Research map", body: "The structure of your research program — threads, sub-questions, and how they connect." },
    { label: "Open points", workspace: "review", subsection: "Things to review", body: "Loose ends to look at, with your notes on each." },
    { label: "Verdict", workspace: "save", subsection: "Report readiness", body: "Can you trust this? What's weak, and what to fix." },
    { label: "History", workspace: "review", subsection: "Saved history", body: "What you've changed and saved, with a trail." }
  ];
  const sideSubnavItems = leanMillActive
    ? activeSection.subnav.map((subsection) => ({
        label: subsection,
        workspace: "leanmill",
        subsection,
        body: detailCopy("leanmill", subsection).body,
        title: detailCopy("leanmill", subsection).title
      }))
    : projectTaskItems.map((item) => ({
        ...item,
        title: detailCopy(item.workspace, item.subsection).title
      }));
  return h(
    "aside",
    { className: "sidebar" },
    h("div", { className: "brand-lockup" }, h("div", { className: "brand-mark" }, "ZT"), h("div", { className: "side-title" }, h("strong", null, "ZTARE"), h("span", null, leanMillActive ? "LeanMill" : "Project Workbench"))),
    h(
      "nav",
      { className: "side-nav", "aria-label": "Workbench sections" },
      productNavItems.map((item) =>
        h(
          "button",
          {
            type: "button",
            key: item.id,
            className: (
              item.id === "leanmill"
                ? leanMillActive
                : item.id === "settings"
                  ? activeWorkspace === "projects" && activeSubsection === "Settings"
                  : !leanMillActive && !(activeWorkspace === "projects" && activeSubsection === "Settings")
            ) ? "active" : "",
            onClick: () => {
              if (onNavigateWorkspace) onNavigateWorkspace(item.workspace, item.subsection);
              else {
                const [normalizedWorkspace, normalizedSubsection] = normalizeWorkspaceTarget(item.workspace, item.subsection);
                setActiveWorkspace(normalizedWorkspace);
                setActiveSubsection(normalizedSubsection);
              }
            }
          },
          h("span", { className: "nav-icon", "aria-hidden": "true" }, navIcon(item.label, 18) || h("span", { className: `nav-icon-dot ${item.icon || item.workspace}` })),
          h("span", { className: "nav-label" }, item.label)
        )
      )
    ),
    h(
      "section",
      { className: "side-subnav", "aria-label": leanMillActive ? "LeanMill submenu" : "Selected project menu" },
      h("span", null, leanMillActive ? "Proof work" : "Selected project"),
      h(
        "div",
        { className: "side-subnav-list" },
        sideSubnavItems.map((item) => {
          const active = activeWorkspace === item.workspace && activeSubsection === item.subsection;
          return h(
            "button",
            {
              key: `${item.workspace}:${item.subsection}:${item.label}`,
              type: "button",
              className: active ? "active" : "",
              onClick: () => {
                if (onNavigateWorkspace) {
                  onNavigateWorkspace(item.workspace, item.subsection);
                } else {
                  const [normalizedWorkspace, normalizedSubsection] = normalizeWorkspaceTarget(item.workspace, item.subsection);
                  setActiveWorkspace(normalizedWorkspace);
                  setActiveSubsection(normalizedSubsection);
                }
              },
              title: item.body
            },
            navIcon(item.label),
            h("strong", null, item.label)
          );
        })
      )
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
      h("strong", null, actionRow ? `${itemLabel(actionRow)}: ${displayText(actionRow.status)}` : "No selected review point"),
      h("p", null, actionRow ? actionRow.detail : "This project has no review points loaded yet.")
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
  if (blocker) add({ label: "Current report issue", command: blocker.command, source: blocker.label, rowLabel: blocker.label, priority: 5 });
  if (selectedRow) add({ label: "Current focus", command: selectedRow.command, source: selectedRow.label, rowLabel: selectedRow.label, priority: 10 });
  const plan = (traceContext && traceContext.plan_preview) || {};
  add({ label: "Recommended command", command: plan.recommended_first_command, source: "Run readiness", rowLabel: "Run readiness", priority: 15 });
  ((traceContext && traceContext.next_commands) || []).slice(0, 4).forEach((command, index) =>
    add({ label: index === 0 ? "Run readiness command" : `Run readiness command ${index + 1}`, command, source: "Run readiness", rowLabel: "Run readiness", priority: 20 + index })
  );
  add({ label: "Report readiness", command: reportContext && reportContext.command, source: "Report readiness", rowLabel: "Report readiness", priority: 30 });
  add({ label: "Evidence summary", command: claimSupportContext && claimSupportContext.command, source: "Evidence summary", rowLabel: "Evidence readiness", priority: 35 });
  (((healthContext && healthContext.kernel) || {}).attention_components || []).forEach((row, index) =>
    add({ label: "Run-health command", command: row.next_command, source: row.component || "Run health", rowLabel: "Run health", priority: 40 + index })
  );
  rows.forEach((row, index) => add({ label: "Project step", command: row.command, source: itemLabel(row), rowLabel: row.label, priority: 60 + index }));
  return items.sort((left, right) => left.priority - right.priority).slice(0, 8);
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
    h("div", null, h("span", null, "Review items with files"), h("strong", null, coverageText)),
    h("div", null, h("span", null, "Commands"), h("strong", null, String(coverage.commandRows))),
    h("div", null, h("span", null, "Saved changes"), h("strong", null, String(coverage.receiptRows))),
    h("div", null, h("span", null, "Review files"), h("strong", null, String(coverage.reviewRows)))
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
    { label: "File and evidence warnings", value: sourceHealthPath || "not loaded", preview: sourceHealthPath }
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

  const primarySourceAction = issues[0] || recommendations[0] || null;
  const primarySourcePath = actionIntelligencePrimaryPath(primarySourceAction, sourceHealthPath || recommendationSource);
  const primarySourceLabel = primarySourceAction
    ? primarySourceAction.source_label || (evidenceRefDisplayItems(primarySourceAction)[0] || {}).label || "Backing file"
    : "";
  const primarySourceNote = primarySourceAction
    ? actionIntelligenceNote(primarySourceAction, "Inspect file or evidence warning")
    : "";
  const primarySourceTitle = primarySourceAction
    ? (
        primarySourceAction.display_issue_type ||
        primarySourceAction.display_recommended_action ||
        guidanceLabel(primarySourceAction.issue_type || primarySourceAction.recommended_action || "file or evidence warning")
      )
    : "";
  const primarySourceDetail = primarySourceAction
    ? (
        primarySourceAction.display_blocking_rule ||
        primarySourceAction.display_rationale ||
        guidanceText(primarySourceAction.blocking_rule || primarySourceAction.rationale || "Inspect the backing file/evidence warning.")
      )
    : "";

  const allItems = [
    ...issues.map((it) => ({ item: it, kind: "Warning" })),
    ...recommendations.map((it) => ({ item: it, kind: "Suggestion" }))
  ];
  const count = allItems.length;
  return h(
    "section",
    { className: `health-actions-panel ${issues.length ? "attention" : "ready"}`, "aria-label": "Warnings" },
    h(
      "div",
      { className: "health-summary" },
      h("h2", null, count ? `${count} thing${count === 1 ? "" : "s"} worth a look` : "Nothing flagged"),
      h(
        "p",
        null,
        healthMessage ||
          (liveMode
            ? count
              ? "Each is a warning or a suggested move. Turn any into your next saved step."
              : "No warnings or suggestions for this project right now."
            : "Start the workbench server to see warnings.")
      )
    ),
    allItems.length
      ? h(
          "div",
          { className: "trace-body" },
          allItems.slice(0, 8).map(({ item, kind }, idx) => {
            const title = item.display_issue_type || guidanceLabel(item.issue_type || item.recommended_action || "Suggestion");
            const detail = item.display_blocking_rule || guidanceText(item.blocking_rule || item.recommended_action || item.what_to_check || "");
            const note = actionIntelligenceNote(item, kind === "Warning" ? "Inspect warning" : "Follow this suggestion");
            return h(
              "div",
              { className: `trace-section ${kind === "Warning" ? "attention" : ""}`, key: idx },
              h("span", null, kind),
              h("strong", null, h(Teach, { text: displayText(title) })),
              detail ? h("p", null, h(Teach, { text: displayText(detail) })) : null,
              item.done_when ? h("p", { className: "trace-readyline" }, `Done when: ${displayText(item.done_when)}`) : null,
              onUseActionNote
                ? h(
                    "button",
                    { className: "copy-button", type: "button", onClick: () => onUseActionNote(note, actionIntelligenceAction(item), "Warnings") },
                    "Make this my next step"
                  )
                : null
            );
          })
        )
      : null
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
  const reviewWritePaths = writePathsFromItems(pendingReviewPaths);
  const reviewReceiptPath = receiptPathFromWriteItems(pendingReviewPaths, "forensic_workbench_reviews");
  const reviewLatestPath = receiptPathFromWriteItems(pendingReviewPaths, "forensic_workbench_latest_review");

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
    { className: "save-flow", "aria-label": "Save review" },
    h(
      "div",
      { className: "save-flow-head" },
      h("h2", null, row ? `Where does "${itemLabel(row)}" stand?` : "Pick a point first"),
      h("p", null, row ? "Mark it reviewed, set it aside, or flag it as holding the report \u2014 and note why." : "Choose a point from Open points first.")
    ),
    h(
      "div",
      { className: "save-flow-choices", role: "group", "aria-label": "Where it stands" },
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
      className: "save-flow-note",
      value: reviewState.note || "",
      onChange: updateNote,
      disabled: !row,
      placeholder: "Why \u2014 what you checked, what you\u2019re waiting on\u2026",
      "aria-label": "Review note"
    }),
    h(
      "div",
      { className: "save-flow-actions" },
      h(
        "button",
        {
          className: "copy-button primary",
          type: "button",
          title: reviewReady ? "Save this review" : "Choose where it stands first",
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
          title: reviewReady ? "Download the review file" : "Choose where it stands first",
          onClick: () => downloadText(reviewFilename, reviewFile),
          disabled: !reviewReady
        },
        "Download"
      )
    ),
    h(
      "details",
      { className: "create-disclosure" },
      h("summary", null, "What this saves"),
      h(
        "div",
        { className: "create-disclosure-body" },
        pendingPathPreview("Files that may change", pendingReviewPaths, "Pick a point to preview the saved files.", liveReady),
        command ? h("code", { className: "trace-command-line" }, command) : null
      )
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
  const nextStepWritePaths = writePathsFromItems(pendingActionPaths);
  const nextStepReceiptPath = receiptPathFromWriteItems(pendingActionPaths, "forensic_workbench_row_actions");
  const nextStepLatestPath = receiptPathFromWriteItems(pendingActionPaths, "forensic_workbench_latest_row_action");

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
    { className: "save-flow", "aria-label": "Save next step" },
    h(
      "div",
      { className: "save-flow-head" },
      h("h2", null, row ? `Next step for ${itemLabel(row)}` : "Pick a point first"),
      h("p", null, row ? "Write the next concrete move for this point, then save it to your trail." : "Choose a point from Open points first.")
    ),
    row && suggestion && suggestion.note
      ? h(
          "button",
          { type: "button", className: "save-flow-suggestion", onClick: useSuggestion, disabled: !row, title: "Use this suggestion" },
          h("span", null, "Suggested"),
          h("strong", null, suggestion.note)
        )
      : null,
    h("textarea", {
      className: "save-flow-note",
      value: actionState.note || "",
      onChange: updateNote,
      disabled: !row,
      placeholder: "The next concrete step, source need, or report issue\u2026",
      "aria-label": "Next-step note"
    }),
    h(
      "div",
      { className: "save-flow-actions" },
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
          title: actionReady ? "Download the next-step file" : "Write a next-step note first",
          onClick: () => downloadText(actionFilename, rowActionFile),
          disabled: !actionReady
        },
        "Download"
      )
    ),
    h(
      "details",
      { className: "create-disclosure" },
      h("summary", null, "What this saves"),
      h(
        "div",
        { className: "create-disclosure-body" },
        pendingPathPreview("Files that may change", pendingActionPaths, "Pick a point to preview the saved files.", liveReady),
        command ? h("code", { className: "trace-command-line" }, command) : null
      )
    )
  );
}


// These rows are not one kind of thing — claim substance, evidence, process checks, and activity
// are different jobs. Grouping by what they ARE is what makes the list mean something.
function FilePreview({ filePreview, filePreviewMessage, onOpenViewer }) {
  const kind = filePreview ? filePreviewKindLabel(filePreview) : "";
  const format = filePreview ? filePreview.format || fileFormatLabel(filePreview.path) : "";
  const quickRows = filePreview
    ? fileViewerInsights(filePreview)
        .slice(0, 3)
        .flatMap((item) => (item.body || []).slice(0, 2).map((entry) => ({ title: item.title, text: displayText(entry) })))
        .slice(0, 5)
    : [];
  const fallbackRows = filePreview && !quickRows.length
    ? linesFromText(filePreview.text).slice(0, 4).map((line) => ({ title: "Line", text: line }))
    : [];
  const summaryRows = quickRows.length ? quickRows : fallbackRows;
  return h(
    "section",
    { className: "file-preview", "aria-label": "File preview" },
    h(
      "div",
      { className: "file-preview-head" },
      h("h3", null, "File preview"),
      filePreview && onOpenViewer
        ? h("button", { type: "button", className: "copy-button", onClick: onOpenViewer }, "Open viewer")
        : null
    ),
    filePreviewMessage ? h("p", null, filePreviewMessage) : null,
    filePreview
      ? h(
          "div",
          { className: "file-preview-body" },
          h(
            "div",
            { className: "file-preview-meta" },
            h("span", null, filePreview.path),
            h(
              "span",
              null,
              `${kind} / ${format} / ${filePreview.bytes} bytes${filePreview.truncated ? " (truncated)" : ""}`
            )
          ),
          summaryRows.length
            ? h(
                "div",
                { className: "file-preview-summary", "aria-label": "File preview summary" },
                summaryRows.map((row, index) =>
                  h(
                    "div",
                    { key: `${row.title}:${index}`, className: "file-preview-summary-row" },
                    h("span", null, row.title),
                    h("p", null, row.text)
                  )
                )
              )
            : h("p", { className: "file-preview-empty" }, "Open the viewer to inspect this file.")
        )
      : null
  );
}

function jsonKeyLabel(key) {
  return String(key).replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

// A descriptive snippet of what's inside — the meaningful text, not a bare count, so a collapsed
// node still tells you what it holds (tasteful: numbers alone make you expand to learn anything).
function jsonDescriptiveText(value) {
  if (value === null || value === undefined) return "";
  if (typeof value !== "object") return String(value);
  if (Array.isArray(value)) {
    const first = value.find((item) => item !== null && item !== undefined);
    return first === undefined ? "" : jsonDescriptiveText(first);
  }
  const labelKey = ["label", "name", "title", "constraint", "statement", "text", "claim", "summary", "description", "detail", "reason", "id"].find(
    (key) => typeof value[key] === "string" && value[key].trim()
  );
  return labelKey ? String(value[labelKey]) : "";
}

function jsonValuePreview(value) {
  if (Array.isArray(value)) {
    const text = jsonDescriptiveText(value);
    const more = value.length > 1 ? ` · +${value.length - 1} more` : "";
    return text ? `${shortText(text, 70)}${more}` : `${value.length} item${value.length === 1 ? "" : "s"}`;
  }
  if (value && typeof value === "object") {
    const text = jsonDescriptiveText(value);
    if (text) return shortText(text, 80);
    const n = Object.keys(value).length;
    return `${n} field${n === 1 ? "" : "s"}`;
  }
  return "";
}

// Render parsed JSON as a navigable tree: scalars inline, nested objects/arrays collapse behind a
// labelled summary so deep structures stay readable instead of becoming a wall of nested rows.
function jsonView(value, depth = 0) {
  if (value === null || value === undefined) return h("span", { className: "json-empty" }, "—");
  if (typeof value === "boolean") return h("span", { className: "json-bool" }, value ? "yes" : "no");
  if (typeof value !== "object") return h("span", { className: "json-scalar" }, String(value));
  const isArray = Array.isArray(value);
  const entries = isArray ? value.map((item, index) => [index, item]) : Object.entries(value);
  if (!entries.length) return h("span", { className: "json-empty" }, isArray ? "(empty list)" : "(none)");
  const renderEntry = ([key, val]) => {
    const label = isArray ? `${Number(key) + 1}` : jsonKeyLabel(key);
    const isNested = val && typeof val === "object" && (Array.isArray(val) ? val.length : Object.keys(val).length);
    if (isNested) {
      // Open the first couple of levels so content shows without clicking; deeper nodes collapse
      // but still carry a descriptive preview of what's inside.
      const small = (Array.isArray(val) ? val.length : Object.keys(val).length) <= 6;
      return h(
        "details",
        { className: "json-node", key, open: depth < 2 || small },
        h(
          "summary",
          null,
          h("span", { className: "json-key" }, label),
          h("span", { className: "json-preview" }, jsonValuePreview(val))
        ),
        h("div", { className: "json-node-body" }, jsonView(val, depth + 1))
      );
    }
    return h(
      "div",
      { className: "json-row", key },
      h("span", { className: "json-key" }, label),
      h("span", { className: "json-val" }, jsonView(val, depth + 1))
    );
  };
  return h("div", { className: "json-block" }, entries.map(renderEntry));
}

function slugifyHeading(text, index) {
  const base = String(text || "")
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return base || `section-${index}`;
}

// Render markdown to sanitized HTML with stable heading ids, and collect a table of contents
// from the same pass so the ToC links always resolve to a real anchor.
function markdownDocument(text) {
  const rawHtml = DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }));
  const toc = [];
  const seen = Object.create(null);
  const html = rawHtml.replace(/<h([1-3])([^>]*)>([\s\S]*?)<\/h\1>/gi, (match, level, attrs, inner) => {
    if (/\bid=/.test(attrs)) return match;
    const plain = inner.replace(/<[^>]+>/g, "").trim();
    if (!plain) return match;
    let slug = slugifyHeading(plain, toc.length + 1);
    if (seen[slug]) {
      seen[slug] += 1;
      slug = `${slug}-${seen[slug]}`;
    } else {
      seen[slug] = 1;
    }
    toc.push({ level: Number(level), text: plain, slug });
    return `<h${level}${attrs} id="${slug}">${inner}</h${level}>`;
  });
  return { html, toc };
}

// Returns { toc, body } so the viewer can lay out a contents rail beside the reading column.
function renderFileBody(filePreview, path) {
  const text = (filePreview && filePreview.text) || "";
  if (!text) return { toc: [], body: h("div", { className: "file-viewer-loading" }, "Empty file.") };
  const isMarkdown = /\.(md|markdown)$/i.test(path || "") || /markdown/i.test((filePreview && filePreview.format) || "");
  if (isMarkdown) {
    const { html, toc } = markdownDocument(text);
    return { toc, body: h("article", { className: "file-viewer-prose", dangerouslySetInnerHTML: { __html: html } }) };
  }
  const format = (filePreview && filePreview.format) || "";
  // JSON lines (.jsonl) — receipts, telemetry, queues. Render each line as its own JSON record card
  // (the raw <pre> dump was what read as "ugly json in the files").
  const isJsonl = /\.jsonl$/i.test(path || "") || /json\s*lines/i.test(format);
  if (isJsonl) {
    const records = text.split("\n").map((l) => l.trim()).filter(Boolean)
      .map((l) => { try { return JSON.parse(l); } catch (_e) { return undefined; } });
    if (records.some((r) => r !== undefined)) {
      return { toc: [], body: h("div", { className: "file-viewer-json file-viewer-jsonl" },
        records.map((rec, i) => rec === undefined ? null :
          h("section", { className: "jsonl-record", key: i },
            h("span", { className: "jsonl-record-num" }, `${i + 1}`),
            h("div", { className: "jsonl-record-body" }, jsonView(rec))))) };
    }
  }
  const isJson = /\.json$/i.test(path || "") || (/json/i.test(format) && !isJsonl);
  if (isJson) {
    try {
      return { toc: [], body: h("div", { className: "file-viewer-json" }, jsonView(JSON.parse(text))) };
    } catch (_err) {
      // Fall through to the raw view if it isn't valid JSON.
    }
  }
  return { toc: [], body: h("pre", { className: "file-viewer-content" }, text) };
}

function FileViewerModal({ filePreview, message, open, onClose, onPreview, editTarget, onOpenEditor, modalNav }) {
  const closeButtonRef = useRef(null);
  const nav = modalNav || {};
  const navRef = useRef(nav);
  const previewPathKey = filePreview && filePreview.path ? filePreview.path : "";
  const [viewerMode, setViewerMode] = useState("read");
  useEffect(() => {
    navRef.current = nav;
  }, [nav]);
  useEffect(() => {
    setViewerMode("read");
  }, [previewPathKey]);
  useEffect(() => {
    if (!open) return undefined;
    const previousActive = document.activeElement;
    const closeOnEscape = (event) => {
      if (handleModalHistoryKey(event, navRef.current)) return;
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
  }, [open, onClose]);
  if (!open) return null;
  const path = filePreview && filePreview.path ? filePreview.path : "";
  const kind = filePreview ? filePreviewKindLabel(filePreview) : path ? fileRoleLabel(path) : "Preview";
  const title = path ? `${kind} viewer` : "File viewer";
  const format = filePreview ? filePreview.format || fileFormatLabel(path) : path ? fileFormatLabel(path) : "Text";
  const size = filePreview ? `${filePreview.bytes} bytes${filePreview.truncated ? " / truncated" : ""}` : "loading";
  const guide = path ? fileViewerGuide(path) : null;
  const fileRole = path ? fileRoleLabel(path) : kind;
  const quickRead = filePreview ? fileViewerInsights(filePreview) : [];
  const lineSummary = filePreview && filePreview.line_count !== undefined
    ? `${filePreview.line_count} lines / ${filePreview.non_empty_line_count || 0} with content`
    : "loading";
  const viewerModes = [
    { id: "read", label: "Read" },
    { id: "structure", label: "Structure" },
    { id: "raw", label: "Raw" }
  ];
  const hasSummary = Boolean(message || guide || quickRead.length);
  return h(
    "div",
    { className: "modal-backdrop file-viewer-backdrop", role: "presentation", onMouseDown: (event) => event.target === event.currentTarget && onClose() },
    h(
      "section",
      { className: "file-viewer-modal", role: "dialog", "aria-modal": "true", "aria-label": title },
      h(
        "header",
        { className: "file-viewer-head" },
        h(
          "div",
          null,
          h("span", { className: "eyebrow" }, path ? kind : "Preview"),
          h("h2", null, title),
          path ? h("code", null, path) : h("p", null, message || "Loading file.")
        ),
        h(
          "div",
          { className: "file-viewer-actions" },
          h(ModalNavControls, { ...nav, label: "File viewer history" }),
          filePreview
            ? h("button", { type: "button", className: "copy-button", onClick: () => copyText(filePreview.text || "") }, "Copy text")
            : null,
          editTarget && onOpenEditor
            ? h(
                "button",
                {
                  type: "button",
                  className: "copy-button primary",
                  onClick: () => onOpenEditor(editTarget),
                  title: editTarget.readOnlyBoundary || "Open the existing project editor"
                },
                editTarget.label || "Edit"
              )
            : null,
          path ? h("button", { type: "button", className: "copy-button", onClick: () => copyText(path) }, "Copy path") : null,
          h("button", { type: "button", ref: closeButtonRef, className: "modal-close", onClick: onClose, "aria-label": "Close file viewer" }, "Close")
        )
      ),
      h(
        "div",
        { className: "file-viewer-meta", "aria-label": "File metadata" },
        h("div", null, h("span", null, "Type"), h("strong", null, path ? kind : "File")),
        h("div", null, h("span", null, "Format"), h("strong", null, format)),
        h("div", null, h("span", null, "Size"), h("strong", null, size)),
        h("div", null, h("span", null, "Lines"), h("strong", null, lineSummary)),
        editTarget
          ? h(
              "div",
              null,
              h("span", null, "Project action"),
              h("strong", null, [editTarget.workspace, editTarget.subsection].filter(Boolean).join(" / "))
            )
          : null
      ),
      editTarget
        ? h(
            "div",
            { className: "file-viewer-edit-boundary" },
            h("strong", null, editTarget.label),
            // Say what this file IS (real utility). Fall back to the write-boundary note only when there's
            // no description — a generic "writes no files" alone is noise.
            h("p", null, editTarget.description || editTarget.readOnlyBoundary)
          )
        : null,
      message ? h("p", { className: "file-viewer-message" }, message) : null,
      (() => {
        const { toc, body } = renderFileBody(filePreview, path);
        const onTocClick = (slug) => (event) => {
          event.preventDefault();
          const target = document.getElementById(slug);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        };
        const tocRail = toc.length > 1
          ? h(
              "nav",
              { className: "file-viewer-toc", "aria-label": "On this page" },
              h("span", { className: "file-viewer-toc-title" }, "On this page"),
              toc.map((item) =>
                h(
                  "a",
                  { key: item.slug, href: `#${item.slug}`, className: `toc-link toc-l${item.level}`, onClick: onTocClick(item.slug) },
                  item.text
                )
              )
            )
          : null;
        return h(
          "div",
          { className: "file-viewer-read" },
          h(
            "div",
            { className: `file-viewer-doc ${tocRail ? "" : "single"}` },
            tocRail,
            h("div", { className: "file-viewer-doc-body" }, body)
          )
        );
      })()
    )
  );
}

function detailKey(workspace, subsection) {
  return `${workspace}:${subsection}`;
}

function normalizeWorkspaceTarget(workspace, subsection) {
  const requestedWorkspace = String(workspace || "").trim();
  const workspaceId = WORKSPACE_ALIASES[requestedWorkspace] || requestedWorkspace;
  const section = WORKSPACE_SECTIONS.find((item) => item.id === workspaceId) || WORKSPACE_SECTIONS[0];
  const rawSubsection = String(subsection || "").trim() || section.subnav[0];
  const subsectionAliases = WORKSPACE_SUBSECTION_ALIASES[section.id] || {};
  const aliasedSubsection = subsectionAliases[rawSubsection] || rawSubsection;
  const normalizedSubsection = section.subnav.includes(aliasedSubsection)
    ? aliasedSubsection
    : section.subnav[0];
  return [section.id, normalizedSubsection];
}

function readWorkbenchRouteFromUrl() {
  try {
    const params = new URLSearchParams(window.location.search);
    const hasExplicitRoute = ["workspace", "w", "section", "subsection", "s", "day0", "mode"].some((key) => params.has(key));
    const day0 = params.get("day0") === "1" || params.get("mode") === "day0" || !hasExplicitRoute;
    const requestedWorkspace = params.get("workspace") || params.get("w") || "projects";
    const requestedSubsection = params.get("section") || params.get("subsection") || params.get("s") || (day0 ? "Current project" : "Current project");
    const requestedStart = String(params.get("start") || "").trim().toLowerCase();
    const start = ["files", "thesis", "folder"].includes(requestedStart) ? requestedStart : "";
    const [workspace, subsection] = normalizeWorkspaceTarget(requestedWorkspace, requestedSubsection);
    const project = String(params.get("project") || "").trim();
    return { workspace, subsection, day0, start, project };
  } catch (_err) {
    return { workspace: "projects", subsection: "Current project", day0: false, start: "", project: "" };
  }
}

function syncWorkbenchRouteToUrl({ workspace, subsection, day0, start = "", replace = false }) {
  try {
    const [nextWorkspace, nextSubsection] = normalizeWorkspaceTarget(workspace, subsection);
    const url = new URL(window.location.href);
    url.searchParams.set("workspace", nextWorkspace);
    url.searchParams.set("section", nextSubsection);
    if (day0) {
      url.searchParams.set("day0", "1");
    } else {
      url.searchParams.delete("day0");
      if (url.searchParams.get("mode") === "day0") url.searchParams.delete("mode");
    }
    if (start && nextWorkspace === "projects" && nextSubsection === "Connect project") {
      url.searchParams.set("start", start);
    } else {
      url.searchParams.delete("start");
    }
    const nextUrl = url.toString();
    if (nextUrl === window.location.href) return;
    if (replace) window.history.replaceState({}, "", nextUrl);
    else window.history.pushState({}, "", nextUrl);
  } catch (_err) {
    // URL sync is best effort; state navigation still works.
  }
}

function detailCopy(workspace, subsection) {
  const [workspaceId, normalizedSubsection] = normalizeWorkspaceTarget(workspace, subsection);
  const section = WORKSPACE_SECTIONS.find((item) => item.id === workspaceId) || WORKSPACE_SECTIONS[0];
  // Modal-only sections (Add file, Edit file) are off the subnav, so prefer their own copy on the
  // raw key before falling back to the normalized (subnav) copy. Otherwise an Edit-file modal would
  // borrow the "Prepare files" heading.
  const rawSub = String(subsection || "").trim();
  return WORKSPACE_DETAIL_COPY[detailKey(workspaceId, rawSub)]
    || WORKSPACE_DETAIL_COPY[detailKey(workspaceId, normalizedSubsection)]
    || {
      title: normalizedSubsection || section.label,
      body: section.summary
    };
}

function ModalShell({ detail, modalKey, onClose, modalNav }) {
  const closeButtonRef = useRef(null);
  const nav = modalNav || {};
  const navRef = useRef(nav);
  useEffect(() => {
    navRef.current = nav;
  }, [nav]);
  useEffect(() => {
    if (!detail || !modalKey) return undefined;
    const previousActive = document.activeElement;
    const closeOnEscape = (event) => {
      if (handleModalHistoryKey(event, navRef.current)) return;
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
  }, [detail, modalKey, onClose]);
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
        h(
          "div",
          { className: "modal-header-actions" },
          h(ModalNavControls, { ...nav, label: "Detail modal history" }),
          h("button", { type: "button", ref: closeButtonRef, className: "modal-close", onClick: onClose, "aria-label": "Close details" }, "Close")
        )
      ),
      h("div", { className: "modal-body" }, detail.panels)
    )
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
  const reportRow = rowByLabel(rows, "Report readiness");
  const reviewRow = reviewRowFromRows(rows);
  const nextStepRow = rowByLabel(rows, "Latest next step") || rowByLabel(rows, "Latest item action");
  const sourceReady = sourceRow && sourceRow.kind !== "attention";
  const evidenceReady = evidenceRow && evidenceRow.kind !== "attention";
  const thesisText = claimRow ? thesisLead(claimRow.detail) : "No claim recorded yet.";
  const statusFor = (row, fallback = "not loaded") => row ? itemStatus(row) : fallback;
  const factsByArea = {
    overview: [
      ["Your claim", statusFor(claimRow, "missing")],
      ["Assumptions", statusFor(assumptionsRow)],
      ["Change test", statusFor(falsifierRow)]
    ],
    sources: [
      ["Original files", statusFor(sourceRow, "missing")],
      ["Evidence summary", statusFor(evidenceRow, "missing")],
      ["Project brief", statusFor(intakeRow, "not loaded")]
    ],
    run: [
      ["Run readiness", statusFor(runRow, snapshot.display_readiness || displayText(snapshot.readiness))],
      ["Readiness command", runRow && runRow.command ? "available" : "not loaded"],
      ["Warnings", activeBlockerRow ? itemLabel(activeBlockerRow) : "none open"]
    ],
    review: [
      ["Open reviews", counts.attention ? `${counts.attention} issue${counts.attention === 1 ? "" : "s"}` : "none"],
      ["Latest review", statusFor(reviewRow, "no saved work")],
      ["Next step", statusFor(nextStepRow, "not saved")]
    ],
    save: [
      ["Report", reportRow ? itemStatus(reportRow) : reportStatusLabel(snapshot.report_status, snapshot.display_report_status)],
      ["Project file", rows.length ? "ready to save" : "not loaded"],
      ["Open issue", activeBlockerRow ? itemLabel(activeBlockerRow) : "none"]
    ]
  };
  const factRows = factsByArea[activeSection.id] || [
    ["Evidence", sourceReady && evidenceReady ? "summary ready" : "summary needs review"],
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
      ? { label: "Prepare files", workspace: "sources", subsection: "Prepare files" }
      : activeSection.id === "run"
        ? { label: "Check readiness", workspace: "run", subsection: "Check readiness" }
        : activeSection.id === "review"
          ? { label: "Open reviews", workspace: "review", subsection: "Save review" }
          : activeSection.id === "save"
            ? { label: "Check report", workspace: "save", subsection: "Report readiness" }
            : null;
  // ponytail: page header is now a thin label only — each panel owns its own hero answer + single
  // primary action, so the old duplicate claim line and competing buttons here just read as clutter.
  return h(
    "section",
    { className: "workspace-page-header", "aria-label": `${activeSection.label} page summary` },
    h(
      "div",
      { className: "workspace-page-copy" },
      h("h2", null, copy.title),
      h("p", null, h(Teach, { text: copy.body }))
    )
  );
}

// --- Global in-flight fetch tracking → drives the top progress bar for ANY foreground request ---
// Patched once. Background telemetry (run-status poll, background snapshot refresh) opts out via
// `__wbSilent` on its fetch init, so only foreground loads — navigation prefetch AND user actions — count.
let __wbInflight = 0;
const __wbFetchSubs = new Set();
function __wbNotify() {
  __wbFetchSubs.forEach((fn) => {
    try { fn(__wbInflight); } catch (_err) { /* subscriber errors must not break fetch */ }
  });
}
if (typeof window !== "undefined" && window.fetch && !window.__wbFetchPatched) {
  window.__wbFetchPatched = true;
  const _origFetch = window.fetch.bind(window);
  window.fetch = function patchedFetch(...args) {
    const init = args[1];
    if (init && init.__wbSilent) return _origFetch(...args);
    __wbInflight += 1;
    __wbNotify();
    let pending;
    try {
      pending = _origFetch(...args);
    } catch (err) {
      __wbInflight = Math.max(0, __wbInflight - 1);
      __wbNotify();
      throw err;
    }
    return Promise.resolve(pending).finally(() => {
      __wbInflight = Math.max(0, __wbInflight - 1);
      __wbNotify();
    });
  };
}
// True while any (non-silent) fetch is in flight — held a `minVisibleMs` minimum so quick calls register,
// and HARD-CAPPED at `maxVisibleMs` so a slow prefetch wave (or a long action) can never pin it on. Once
// capped it stays hidden until activity fully stops, so the next burst re-triggers cleanly.
function useAnyFetching(minVisibleMs, maxVisibleMs) {
  const [active, setActive] = useState(false);
  useEffect(() => {
    let tailTimer = null;
    let capTimer = null;
    let capped = false;
    const onChange = (count) => {
      if (count > 0) {
        if (tailTimer) { clearTimeout(tailTimer); tailTimer = null; }
        if (capped) return;
        if (!capTimer) {
          capTimer = setTimeout(() => { capped = true; capTimer = null; setActive(false); }, maxVisibleMs);
        }
        setActive(true);
      } else {
        capped = false;
        if (capTimer) { clearTimeout(capTimer); capTimer = null; }
        if (tailTimer) clearTimeout(tailTimer);
        tailTimer = setTimeout(() => { setActive(false); tailTimer = null; }, minVisibleMs);
      }
    };
    __wbFetchSubs.add(onChange);
    onChange(__wbInflight);
    return () => {
      __wbFetchSubs.delete(onChange);
      if (tailTimer) clearTimeout(tailTimer);
      if (capTimer) clearTimeout(capTimer);
    };
  }, [minVisibleMs, maxVisibleMs]);
  return active;
}

function App() {
  const initialRoute = useMemo(() => readWorkbenchRouteFromUrl(), []);
  const [day0Mode, setDay0Mode] = useState(initialRoute.day0);
  const [projectStartIntent, setProjectStartIntent] = useState(initialRoute.start);
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [modeMessage, setModeMessage] = useState("");
  const [runStatus, setRunStatus] = useState(null);
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
  const [sourceActionPrompt, setSourceActionPrompt] = useState(null);
  const [runHistoryContext, setRunHistoryContext] = useState(null);
  const [runHistoryMessage, setRunHistoryMessage] = useState("");
  const [scoreTrajectory, setScoreTrajectory] = useState(null);
  const [evalResults, setEvalResults] = useState(null);
  const [researchMapData, setResearchMapData] = useState(null);
  const [researchGraph, setResearchGraph] = useState(null);
  const [runConfig, setRunConfig] = useState(null);
  const [runConfigOverrides, setRunConfigOverrides] = useState({});
  const [runConfigMessage, setRunConfigMessage] = useState("");
  const [runConfigSaving, setRunConfigSaving] = useState(false);
  const scoreTrajectoryProject = snapshot && snapshot.project;
  const [claimSupportContext, setClaimSupportContext] = useState(null);
  const [claimSupportMessage, setClaimSupportMessage] = useState("");
  const [evidenceGapContext, setEvidenceGapContext] = useState(null);
  const [evidenceGapMessage, setEvidenceGapMessage] = useState("");
  const [evidenceGapDraft, setEvidenceGapDraft] = useState(emptyEvidenceGapDraft());
  const [evidenceGapEvent, setEvidenceGapEvent] = useState(null);
  const [evidenceGapRunning, setEvidenceGapRunning] = useState(false);
  const [evidenceFetchEvent, setEvidenceFetchEvent] = useState(null);
  const [evidenceFetchPrompt, setEvidenceFetchPrompt] = useState(null);
  const [evidenceFetchRunning, setEvidenceFetchRunning] = useState(false);
  const [healthContext, setHealthContext] = useState(null);
  const [healthMessage, setHealthMessage] = useState("");
  const [reportContractContext, setReportContractContext] = useState(null);
  const [reportContractMessage, setReportContractMessage] = useState("");
  const [reportSupportEvent, setReportSupportEvent] = useState(null);
  const [reportSupportPrompt, setReportSupportPrompt] = useState(null);
  const [reportSynthesisPrompt, setReportSynthesisPrompt] = useState(null);
  const [reportSupportRunning, setReportSupportRunning] = useState(false);
  const [forecastScratch, setForecastScratch] = useState(null);
  const [eigenquestion, setEigenquestion] = useState(null);
  const [isomorphism, setIsomorphism] = useState(null);
  const [rubricReview, setRubricReview] = useState(null);
  const [falsify, setFalsify] = useState(null);
  const [projectDraft, setProjectDraft] = useState(null);
  const [obsidianExport, setObsidianExport] = useState(null);
  const [serverStatus, setServerStatus] = useState(null);
  const [serverStatusMessage, setServerStatusMessage] = useState("");
  const [capabilityContext, setCapabilityContext] = useState(null);
  const [capabilityMessage, setCapabilityMessage] = useState("");
  const [workbenchSettings, setWorkbenchSettings] = useState(null);
  const [settingsDraft, setSettingsDraft] = useState({});
  const [settingsMessage, setSettingsMessage] = useState("");
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [scoringGuideContext, setScoringGuideContext] = useState(null);
  const [scoringGuideDraft, setScoringGuideDraft] = useState(null);
  const [scoringGuideMessage, setScoringGuideMessage] = useState("");
  const [scoringGuideSaving, setScoringGuideSaving] = useState(false);
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
  const [principleContext, setPrincipleContext] = useState(null);
  const [leanMillContext, setLeanMillContext] = useState(null);
  const [leanMillMessage, setLeanMillMessage] = useState("");
  const [leanMillBlueprintDraft, setLeanMillBlueprintDraft] = useState(emptyLeanMillBlueprintDraft());
  const [leanMillBlueprintEvent, setLeanMillBlueprintEvent] = useState(null);
  const [leanMillBlueprintMessage, setLeanMillBlueprintMessage] = useState("");
  const [leanMillBlueprintRunning, setLeanMillBlueprintRunning] = useState(false);
  const [leanMillActionDraft, setLeanMillActionDraft] = useState(emptyLeanMillActionDraft());
  const [leanMillActionEvent, setLeanMillActionEvent] = useState(null);
  const [leanMillActionMessage, setLeanMillActionMessage] = useState("");
  const [leanMillActionRunning, setLeanMillActionRunning] = useState(false);
  const [sourceEditDraft, setSourceEditDraft] = useState(emptySourceEditDraft());
  const [sourceEditMessage, setSourceEditMessage] = useState("");
  const [sourceEditEvent, setSourceEditEvent] = useState(null);
  const [sourceEditing, setSourceEditing] = useState(false);
  const [liveMode, setLiveMode] = useState(false);
  useEffect(() => {
    if (!liveMode || !scoreTrajectoryProject) {
      setScoreTrajectory(null);
      return undefined;
    }
    let active = true;
    fetch(endpointUrl("/api/score-trajectory", { project: scoreTrajectoryProject }), { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (active && payload) setScoreTrajectory(payload);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [liveMode, scoreTrajectoryProject]);
  // Keep run-history (recent_runs → per-run weakest_point + gates) loaded alongside the trajectory, so
  // History/Results show the run narrative even when the page boots static then flips live.
  useEffect(() => {
    if (!liveMode || !scoreTrajectoryProject) return undefined;
    let active = true;
    fetch(endpointUrl("/api/run-history", { project: scoreTrajectoryProject, limit: 8 }), { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => { if (active && payload) setRunHistoryContext(payload); })
      .catch(() => {});
    return () => { active = false; };
  }, [liveMode, scoreTrajectoryProject]);
  useEffect(() => {
    if (!liveMode || !scoreTrajectoryProject) {
      setEvalResults(null);
      return undefined;
    }
    let active = true;
    fetch(endpointUrl("/api/eval-results", { project: scoreTrajectoryProject }), { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (active && payload) setEvalResults(payload);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [liveMode, scoreTrajectoryProject]);
  useEffect(() => {
    if (!liveMode || !scoreTrajectoryProject) {
      setResearchMapData(null);
      return undefined;
    }
    let active = true;
    fetch(endpointUrl("/api/research-map", { project: scoreTrajectoryProject }), { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (active && payload && Array.isArray(payload.nodes)) setResearchMapData(payload);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [liveMode, scoreTrajectoryProject]);
  // The research-landscape graph projection (aggregated over the project's artifacts via the CLI).
  useEffect(() => {
    if (!liveMode || !scoreTrajectoryProject) { setResearchGraph(null); return undefined; }
    let active = true;
    fetch(endpointUrl("/api/research-graph", { project: scoreTrajectoryProject }), { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => { if (active && payload && payload.ok && Array.isArray(payload.nodes)) setResearchGraph(payload); })
      .catch(() => {});
    return () => { active = false; };
  }, [liveMode, scoreTrajectoryProject]);
  useEffect(() => {
    if (!liveMode || !scoreTrajectoryProject) {
      setRunConfig(null);
      setRunConfigOverrides({});
      return undefined;
    }
    let active = true;
    fetch(endpointUrl("/api/run-config", { project: scoreTrajectoryProject }), { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (active && payload) {
          setRunConfig(payload);
          setRunConfigOverrides({ ...(payload.overrides || {}) });
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [liveMode, scoreTrajectoryProject]);
  // Poll for runs actively in progress (autoresearch / LeanMill) so the UI can show a run is happening
  // instead of the user grepping for the process. Quiet on 404 (older server without the endpoint).
  const runStatusProject = snapshot && snapshot.project;
  useEffect(() => {
    if (!liveMode || !runStatusProject) {
      setRunStatus(null);
      return undefined;
    }
    let active = true;
    const poll = () => {
      fetch(endpointUrl("/api/run-status", { project: runStatusProject }), { headers: { Accept: "application/json" }, __wbSilent: true })
        .then((response) => (response.ok ? response.json() : null))
        .then((payload) => {
          if (active && payload) setRunStatus(payload);
        })
        .catch(() => {});
    };
    poll();
    // poll faster while a run is in flight so the iteration count feels live
    const id = setInterval(poll, 4000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [liveMode, runStatusProject]);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [writeReceiptEvent, setWriteReceiptEvent] = useState(null);
  const [lastRefreshResults, setLastRefreshResults] = useState([]);
  const [projectFileSaveEvent, setProjectFileSaveEvent] = useState(null);
  const [projectFileSaving, setProjectFileSaving] = useState(false);
  const [researchMapSaving, setResearchMapSaving] = useState(false);
  // Top progress bar: lit by ANY foreground network activity — navigation prefetch AND user actions —
  // held a 500ms minimum so it's perceptible and CAPPED at 4s so a slow prefetch wave can never pin it on.
  // Background polling opts out via __wbSilent (see the fetch patch above the component).
  const loadBarActive = useAnyFetching(500, 4000);
  const [charterDraft, setCharterDraft] = useState(null);
  const [charterMessage, setCharterMessage] = useState("");
  const [intakeDraft, setIntakeDraft] = useState(null);
  const [intakeMessage, setIntakeMessage] = useState("");
  const [receiptHistory, setReceiptHistory] = useState(null);
  const [receiptHistoryMessage, setReceiptHistoryMessage] = useState("");
  const [filePreview, setFilePreview] = useState(null);
  const [filePreviewMessage, setFilePreviewMessage] = useState("");
  const [filePreviewOpen, setFilePreviewOpen] = useState(false);
  // When the editor/detail modal is opened FROM the file viewer, remember the file so the modal's
  // Back can return to the viewer (the two modals are separate history stacks).
  const [editorReturnPath, setEditorReturnPath] = useState("");
  const [filePreviewHistory, setFilePreviewHistory] = useState([]);
  const [filePreviewHistoryIndex, setFilePreviewHistoryIndex] = useState(-1);
  const [selectedLabel, setSelectedLabel] = useState("");
  const [reviewStates, setReviewStates] = useState({});
  const [actionStates, setActionStates] = useState({});
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [activeWorkspace, setActiveWorkspace] = useState(initialRoute.workspace);
  const [activeSubsection, setActiveSubsection] = useState(initialRoute.subsection);
  const [activeModalKey, setActiveModalKey] = useState("");
  const [detailModalHistory, setDetailModalHistory] = useState([]);
  const [detailModalHistoryIndex, setDetailModalHistoryIndex] = useState(-1);
  const [discardPrompt, setDiscardPrompt] = useState(null);
  const snapshotLoadedRef = useRef(false);

  useEffect(() => {
    const restoreRoute = () => {
      const route = readWorkbenchRouteFromUrl();
      setDay0Mode(route.day0);
      setProjectStartIntent(route.start);
      setActiveWorkspace(route.workspace);
      setActiveSubsection(route.subsection);
      setActiveModalKey("");
    };
    window.addEventListener("popstate", restoreRoute);
    syncWorkbenchRouteToUrl({
      workspace: activeWorkspace,
      subsection: activeSubsection,
      day0: day0Mode,
      start: projectStartIntent,
      replace: true
    });
    return () => window.removeEventListener("popstate", restoreRoute);
  }, []);

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
    setSourceActionPrompt(null);
    setEvidenceFetchEvent(null);
    setEvidenceFetchPrompt(null);
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
    setSourceActionPrompt(null);
    setRunHistoryContext(null);
    setRunHistoryMessage("");
    setClaimSupportContext(null);
    setClaimSupportMessage("");
    setEvidenceGapContext(null);
    setEvidenceGapMessage("");
    setEvidenceGapDraft(emptyEvidenceGapDraft());
    setEvidenceGapEvent(null);
    setEvidenceGapRunning(false);
    setEvidenceFetchEvent(null);
    setEvidenceFetchPrompt(null);
    setEvidenceFetchRunning(false);
    setHealthContext(null);
    setHealthMessage("");
    setReportContractContext(null);
    setReportContractMessage("");
    setReportSupportEvent(null);
    setScoringGuideContext(null);
    setScoringGuideDraft(null);
    setScoringGuideMessage("");
    setScoringGuideSaving(false);
    setReportSupportPrompt(null);
    setReportSynthesisPrompt(null);
    setReportSupportRunning(false);
    setSourceImportEvent(null);
    setSourceImportMessage("");
    setSourceImportDraft(emptySourceImportDraft());
    setSourceListContext(null);
    setSourceListMessage("");
    setSourceEditMessage("");
    setSourceEditDraft(emptySourceEditDraft());
    setCharterDraft(null);
    setCharterMessage("");
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

  const loadWorkbenchSettings = () =>
    fetch("/api/settings", { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "settings fetch failed"))
      .then((payload) => {
        setWorkbenchSettings(payload);
        setSettingsDraft(settingsDraftFromPayload(payload));
        setSettingsMessage(payload.env_file_exists ? `Loaded ${payload.env_file}.` : "No .env file yet; saving will create one.");
        return payload;
      })
      .catch((err) => {
        setWorkbenchSettings(null);
        setSettingsMessage(`Settings unavailable: ${err.message || err}`);
        return null;
      });

  const loadCapabilityContext = () =>
    fetch("/api/capabilities", { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "capability map fetch failed"))
      .then((payload) => {
        setCapabilityContext(payload);
        setCapabilityMessage(
          payload.ok
            ? `${payload.capability_count || 0} project tests loaded.`
            : `Project-test grounding loaded with ${((payload.audit || {}).finding_count || 0)} issue(s).`
        );
        return refreshResult("capabilities", payload.ok !== false);
      })
      .catch((err) => {
        setCapabilityContext(null);
        setCapabilityMessage(`Project-check grounding unavailable: ${err.message || err}`);
        return refreshResult("capabilities", false, err.message || err);
      });

  const loadPrincipleContext = () =>
    fetch("/api/principles", { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "principles fetch failed"))
      .then((payload) => {
        setPrincipleContext(payload);
        return refreshResult("principles", payload.ok !== false);
      })
      .catch((err) => {
        setPrincipleContext(null);
        return refreshResult("principles", false, err.message || err);
      });

  const saveWorkbenchSettings = () => {
    if (!liveMode || settingsSaving) return;
    setSettingsSaving(true);
    setSettingsMessage("Saving workbench settings.");
    fetch("/api/settings", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ values: settingsDraft })
    })
      .then((response) => jsonResponseOrError(response, "settings save failed"))
      .then((payload) => {
        setWorkbenchSettings(payload);
        setSettingsDraft(settingsDraftFromPayload(payload));
        setSettingsMessage(`Saved ${payload.env_file}. Commands now use these defaults.`);
        return loadServerStatus();
      })
      .catch((err) => {
        setSettingsMessage(`Settings save failed: ${err.message || err}`);
      })
      .finally(() => setSettingsSaving(false));
  };

  const loadRunConfig = () => {
    if (!liveMode) return Promise.resolve(null);
    const params = liveProjectParams();
    return fetch(`/api/run-config?project=${encodeURIComponent(params.project)}`, { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "run config fetch failed"))
      .then((payload) => {
        setRunConfig(payload);
        setRunConfigOverrides({ ...(payload.overrides || {}) });
        setRunConfigMessage("");
        return payload;
      })
      .catch((err) => {
        setRunConfig(null);
        setRunConfigMessage(`Run settings unavailable: ${err.message || err}`);
        return null;
      });
  };

  const saveRunConfig = (overridesOverride) => {
    if (!liveMode || runConfigSaving) return;
    // Guard: onClick handlers pass the event — only a plain overrides map counts.
    const values = (overridesOverride && typeof overridesOverride === "object" && !overridesOverride.nativeEvent)
      ? overridesOverride : runConfigOverrides;
    const params = liveProjectParams();
    setRunConfigSaving(true);
    setRunConfigMessage("Saving run settings for this project.");
    fetch("/api/run-config", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ project: params.project, values })
    })
      .then((response) => jsonResponseOrError(response, "run config save failed"))
      .then((payload) => {
        setRunConfig(payload);
        setRunConfigOverrides({ ...(payload.overrides || {}) });
        const count = payload.override_count || 0;
        setRunConfigMessage(count ? `Saved. ${count} setting${count === 1 ? "" : "s"} now override your global defaults for this project.` : "Saved. This project follows your global defaults.");
      })
      .catch((err) => {
        setRunConfigMessage(`Run settings save failed: ${err.message || err}`);
      })
      .finally(() => setRunConfigSaving(false));
  };

  // Set iterations from the Harden run console — persists the RUN_ITERS override (CLI-backed) inline.
  const setRunIters = (value) => {
    const n = Math.max(1, Math.min(50, parseInt(value, 10) || 0));
    if (!n) return;
    const next = { ...runConfigOverrides, ZTARE_WORKBENCH_RUN_ITERS: String(n) };
    setRunConfigOverrides(next);
    saveRunConfig(next);
  };

  const saveScoringGuide = (textOverride) => {
    const text = typeof textOverride === "string" ? textOverride : (scoringGuideDraft && scoringGuideDraft.text);
    if (!snapshot || !liveMode || scoringGuideSaving || !text) return;
    const params = liveProjectParams();
    setScoringGuideSaving(true);
    setScoringGuideMessage("Saving and validating scoring guide.");
    fetch("/api/scoring-guide", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        text
      })
    })
      .then((response) => jsonResponseOrError(response, "scoring guide save failed"))
      .then((payload) => {
        setScoringGuideContext(payload);
        setScoringGuideDraft(scoringGuideDraftFromPayload(payload));
        setScoringGuideMessage(
          payload.accepted
            ? `Saved and validated ${payload.path}.`
            : `Saved ${payload.path}; validation still needs attention.`
        );
        setWriteReceiptEvent({
          kind: "scoring_guide",
          row: "Scoring guide",
          result: payload,
          snapshotError: payload.workflow_error || ""
        });
        if (payload.workflow) setWorkflowContext(payload.workflow);
        refreshLiveContextAfterWrite(params, { intake: false });
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("scoring_guide", "Scoring guide", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setScoringGuideMessage(`${String(err.message || err)}${failedWrite ? " No scoring-guide file changed." : ""}`);
      })
      .finally(() => setScoringGuideSaving(false));
  };

  // Flip one boolean rubric flag (gate/check) in place and save — no JSON editing needed.
  const toggleScoringGate = (key, value) => {
    if (!liveMode || scoringGuideSaving || !scoringGuideContext) return;
    let obj;
    try {
      obj = JSON.parse(scoringGuideContext.text);
    } catch (err) {
      setScoringGuideMessage(`Fix the raw scoring guide JSON before toggling: ${err.message || err}`);
      return;
    }
    obj[key] = value;
    saveScoringGuide(JSON.stringify(obj, null, 2));
  };

  const useStarterScoringDimensions = () => {
    if (!scoringGuideDraft) return;
    try {
      const result = scoringGuideTextWithStarterDimensions(scoringGuideDraft.text);
      if (!result.changed) {
        setScoringGuideMessage("This scoring guide already has dimensions.");
        return;
      }
      setScoringGuideDraft({ ...scoringGuideDraft, text: result.text });
      setScoringGuideMessage("Starter dimensions added to the draft. Review them, then save the scoring guide.");
    } catch (err) {
      setScoringGuideMessage(`Cannot add starter dimensions until the JSON parses: ${err.message || err}`);
    }
  };

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
    setTraceMessage("Loading readiness.");
    return fetch(endpointUrl("/api/trace", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`trace fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "trace fetch failed");
        setTraceContext(payload);
        setTraceMessage("");
        return refreshResult("trace", true);
      })
      .catch((err) => {
        setTraceContext(null);
        setTraceMessage(`Live readiness unavailable: ${err.message || err}`);
        return refreshResult("trace", false, err.message || err);
      });
  };

  const loadWorkflowContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setWorkflowMessage("Loading project steps.");
    return fetch(endpointUrl("/api/workflow", { ...projectParams, mode: "full" }), { headers: { Accept: "application/json" } })
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
        setWorkflowMessage(`Project path unavailable: ${err.message || err}`);
        return refreshResult("workflow", false, err.message || err);
      });
  };

  const loadScoringGuideContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setScoringGuideMessage("Loading scoring guide.");
    return fetch(endpointUrl("/api/scoring-guide", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "scoring guide fetch failed"))
      .then((payload) => {
        setScoringGuideContext(payload);
        setScoringGuideDraft(scoringGuideDraftFromPayload(payload));
        const status = (payload.readiness && payload.readiness.status) || "loaded";
        setScoringGuideMessage(`Scoring guide ${status}: ${payload.path || "not loaded"}.`);
        return refreshResult("scoring guide", true);
      })
      .catch((err) => {
        setScoringGuideContext(null);
        setScoringGuideDraft(null);
        setScoringGuideMessage(`Scoring guide unavailable: ${err.message || err}`);
        return refreshResult("scoring guide", false, err.message || err);
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
        setReportContractMessage("");
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
    setIntakeMessage("Loading project brief.");
    return fetch(endpointUrl("/api/intake", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`intake fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "intake fetch failed");
        setIntakeDraft(intakeDraftFromPayload(payload));
        setIntakeMessage(payload.editable === false ? `Loaded read-only project brief: ${payload.path}.` : `Loaded project brief: ${payload.path}.`);
        return refreshResult("intake", true);
      })
      .catch((err) => {
        setIntakeDraft(null);
        setIntakeMessage(`Live project brief unavailable: ${err.message || err}`);
        return refreshResult("intake", false, err.message || err);
      });
  };

  const loadCharterDraft = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setCharterMessage("Loading project charter.");
    return fetch(endpointUrl("/api/charter", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`charter fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false && !payload.exists) throw new Error(payload.error || "project charter is missing");
        setCharterDraft(charterDraftFromPayload(payload));
        setCharterMessage(payload.exists ? `Loaded project charter: ${payload.path}.` : `No project charter yet: ${payload.path}.`);
        return refreshResult("charter", true);
      })
      .catch((err) => {
        setCharterDraft(null);
        setCharterMessage(`Live project charter unavailable: ${err.message || err}`);
        return refreshResult("charter", false, err.message || err);
      });
  };

  const loadReceiptHistory = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setReceiptHistoryMessage("Loading saved history.");
    return fetch(endpointUrl("/api/receipts", { project: projectParams.project, intake: projectParams.intake, limit: 12 }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`saved history fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "saved history fetch failed");
        setReceiptHistory(payload);
        setReceiptHistoryMessage(`${payload.receipt_count || 0} saved change${Number(payload.receipt_count || 0) === 1 ? "" : "s"} found in project history.`);
        return refreshResult("receipts", true);
      })
      .catch((err) => {
        setReceiptHistory(null);
        setReceiptHistoryMessage(`Saved history unavailable: ${err.message || err}`);
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
    setClaimSupportMessage("Loading evidence summary.");
    return fetch(endpointUrl("/api/evidence-support", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`evidence summary fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false && !payload.status) throw new Error(payload.error || "evidence summary fetch failed");
        setClaimSupportContext(payload);
        setClaimSupportMessage(
          payload.accepted
            ? `${payload.claim_count || 0} evidence-summary items loaded from project files.`
            : `Evidence summary needs attention: ${payload.status || "attention"}.`
        );
        return refreshResult("evidence summary", true);
      })
      .catch((err) => {
        setClaimSupportContext(null);
        setClaimSupportMessage(`Evidence summary unavailable: ${err.message || err}`);
        return refreshResult("evidence summary", false, err.message || err);
      });
  };

  const loadEvidenceGapContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setEvidenceGapMessage("Loading evidence gaps.");
    return fetch(endpointUrl("/api/evidence-gaps", projectParams), { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "evidence gaps fetch failed"))
      .then((payload) => {
        const gaps = payload.evidence_gaps || [];
        setEvidenceGapContext(payload);
        setEvidenceGapMessage(
          gaps.length
            ? `${gaps.length} active evidence gap${gaps.length === 1 ? "" : "s"} loaded.`
            : "No active evidence gaps loaded."
        );
        setEvidenceGapDraft((draft) => {
          const currentIndex = draft && draft.index !== "" ? Number(draft.index) : 0;
          return currentIndex >= gaps.length ? { ...(draft || emptyEvidenceGapDraft()), index: gaps.length ? "0" : "" } : draft;
        });
        return refreshResult("evidence gaps", true);
      })
      .catch((err) => {
        setEvidenceGapContext(null);
        setEvidenceGapMessage(`Evidence gaps unavailable: ${err.message || err}`);
        return refreshResult("evidence gaps", false, err.message || err);
      });
  };

  const loadSourceListContext = (projectParams) => {
    if (!projectParams || !projectParams.project) return Promise.resolve();
    setSourceListMessage("Loading original files.");
    return fetch(endpointUrl("/api/sources", { project: projectParams.project }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`source list fetch failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "source list fetch failed");
        setSourceListContext(payload);
        setSourceListMessage(`${(payload.sources || []).length} original files loaded from ${payload.raw_dir || "project folder"}.`);
        return refreshResult("sources", true);
      })
      .catch((err) => {
        setSourceListContext(null);
        setSourceListMessage(`Original files unavailable: ${err.message || err}`);
        return refreshResult("sources", false, err.message || err);
      });
  };

  const loadLeanMillContext = () => {
    setLeanMillMessage("Loading LeanMill state.");
    return fetch("/api/leanmill", { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "LeanMill state fetch failed"))
      .then((payload) => {
        setLeanMillContext(payload);
        setLeanMillMessage("LeanMill files loaded from local files.");
        return refreshResult("LeanMill", true);
      })
      .catch((err) => {
        setLeanMillContext(null);
        setLeanMillMessage(`LeanMill state unavailable: ${err.message || err}`);
        return refreshResult("LeanMill", false, err.message || err);
      });
  };

  const leanMillBlueprintRequest = (confirmed) => {
    const draft = leanMillBlueprintDraft || emptyLeanMillBlueprintDraft();
    const payload = {
      project: draft.project,
      slug: draft.slug,
      title: draft.title,
      target_statement: draft.target_statement,
      notes: draft.notes,
      non_claims: linesFromText(draft.non_claims_text),
      confirmed
    };
    if (confirmed && leanMillBlueprintEvent && leanMillBlueprintEvent.preview_sha256) {
      payload.preview_sha256 = leanMillBlueprintEvent.preview_sha256;
    }
    return payload;
  };

  const updateLeanMillBlueprintDraft = (draft) => {
    setLeanMillBlueprintDraft(draft);
    setLeanMillBlueprintEvent(null);
    if (leanMillBlueprintEvent && leanMillBlueprintEvent.preview_sha256) {
      setLeanMillBlueprintMessage("Draft changed. Preview again before saving.");
    }
  };

  const submitLeanMillBlueprint = (confirmed) => {
    if (!liveMode || leanMillBlueprintRunning) return;
    if (confirmed && !(leanMillBlueprintEvent && leanMillBlueprintEvent.preview_sha256)) {
      setLeanMillBlueprintMessage("Preview the target and notes before saving. No files changed.");
      return;
    }
    setLeanMillBlueprintRunning(true);
    setLeanMillBlueprintMessage(confirmed ? "Saving LeanMill target and notes." : "Previewing LeanMill target and notes.");
    fetch("/api/leanmill/target", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(leanMillBlueprintRequest(confirmed))
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok && payload.status !== "needs_confirmation") {
            const error = new Error(payload.error || `LeanMill target ${confirmed ? "save" : "preview"} failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        setLeanMillBlueprintEvent(payload);
        setLeanMillBlueprintMessage(
          payload.accepted
            ? `Saved ${payload.blueprint_path || payload.target_path || payload.path}; saved history ${payload.latest || payload.receipt_path || "recorded"}.`
            : "Preview ready. No files changed."
        );
        if (payload.accepted) {
          setWriteReceiptEvent({
            kind: "leanmill_target",
            label: "Save LeanMill target and notes",
            row: "LeanMill",
            result: payload,
            snapshotError: ""
          });
          loadLeanMillContext();
          if (payload.project) refreshCurrentProject();
        }
      })
      .catch((err) => {
        if (err.payload) setLeanMillBlueprintEvent(err.payload);
        const failedWrite = refusedWriteEvent("leanmill_target", "Save LeanMill target and notes", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setLeanMillBlueprintMessage(`${String(err.message || err)} No files changed.`);
      })
      .finally(() => setLeanMillBlueprintRunning(false));
  };

  const submitLeanMillScaffold = (project) => {
    const slug = String(project || "").trim();
    if (!liveMode || !slug) {
      setLeanMillMessage(slug ? "Start the workbench server to create a LeanMill area." : "Enter a project slug first.");
      return;
    }
    setLeanMillMessage(`Creating LeanMill area for ${slug}.`);
    fetch("/api/leanmill/scaffold", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: slug, confirmed: true })
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok) throw new Error(payload.error || `LeanMill area creation failed: ${response.status}`);
          return payload;
        })
      )
      .then((payload) => {
        setLeanMillMessage(
          payload.already_existed
            ? `LeanMill area already exists at ${(payload.folder_contract || {}).root || `projects/${slug}/leanmill`}.`
            : `Created LeanMill area: ${(payload.folder_contract || {}).root || `projects/${slug}/leanmill`}.`
        );
        loadLeanMillContext();
      })
      .catch((err) => setLeanMillMessage(`${String(err.message || err)} No files changed.`));
  };

  const updateLeanMillActionDraft = (patch) => {
    setLeanMillActionDraft({ ...(leanMillActionDraft || emptyLeanMillActionDraft()), ...patch });
    if (leanMillActionEvent && leanMillActionEvent.status === "needs_confirmation") {
      setLeanMillActionEvent(null);
      setLeanMillActionMessage("Launch details changed. Preview again before starting.");
    }
  };

  const leanMillActionRequest = (action, confirmed) => {
    const draft = leanMillActionDraft || emptyLeanMillActionDraft();
    if (action === "autoformalize") {
      return {
        project: draft.project || "",
        notes_path: draft.notes_path || (leanMillBlueprintEvent && (leanMillBlueprintEvent.target_path || leanMillBlueprintEvent.blueprint_path || leanMillBlueprintEvent.path)) || "",
        timeout_s: Number(draft.timeout_s || 0) || 0,
        confirmed
      };
    }
    return {
      project: draft.project || "",
      target_name: draft.target_name || "",
      source_file: draft.source_file || "",
      goal: draft.goal || "",
      provider: draft.provider || "",
      notes_path: draft.notes_path || "",
      substrate: draft.substrate || "",
      mode: draft.mode || "dag_search",
      timeout_s: Number(draft.timeout_s || 500) || 500,
      confirmed
    };
  };

  const submitLeanMillAction = (action, confirmed) => {
    if (!liveMode || leanMillActionRunning) return;
    setLeanMillActionRunning(true);
    const label = action === "autoformalize" ? "the proof from your notes" : "the proof for this Lean target";
    setLeanMillActionMessage(confirmed ? `Starting ${label}.` : `Previewing ${label}.`);
    fetch(action === "autoformalize" ? "/api/leanmill/autoformalize-notes" : "/api/leanmill/solve-adhoc", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(leanMillActionRequest(action, confirmed))
    })
      .then((response) =>
        response.json().then((payload) => {
          if (!response.ok && payload.status !== "needs_confirmation") {
            const error = new Error(payload.error || `${label} failed: ${response.status}`);
            error.payload = payload;
            throw error;
          }
          return payload;
        })
      )
      .then((payload) => {
        setLeanMillActionEvent(payload);
        const job = payload.job || {};
        const paths = job.paths || {};
        setLeanMillActionMessage(
          payload.accepted
            ? `${label} started. Watch ${paths.result || paths.job || "the job file"}.`
            : "Preview ready. No job started."
        );
        if (payload.accepted) {
          setWriteReceiptEvent({
            kind: action === "autoformalize" ? "leanmill_autoformalize_notes" : "leanmill_solve_adhoc",
            label,
            row: "LeanMill",
            result: payload,
            snapshotError: ""
          });
          loadLeanMillContext();
        }
      })
      .catch((err) => {
        if (err.payload) setLeanMillActionEvent(err.payload);
        const failedWrite = refusedWriteEvent(action === "autoformalize" ? "leanmill_autoformalize_notes" : "leanmill_solve_adhoc", label, err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setLeanMillActionMessage(`${String(err.message || err)} No job started.`);
      })
      .finally(() => setLeanMillActionRunning(false));
  };

  const liveProjectParams = () => ({
    project: snapshot.project,
    rubric: (currentProjectEntry && currentProjectEntry.rubric) || snapshot.rubric,
    intake: (currentProjectEntry && currentProjectEntry.intake) || snapshot.intake
  });

  const saveResearchMap = () => {
    if (!snapshot || !liveMode || researchMapSaving) return;
    const params = liveProjectParams();
    setResearchMapSaving(true);
    setWorkflowMessage("Saving research map.");
    fetch("/api/research-map", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(params)
    })
      .then((response) => jsonResponseOrError(response, "research map save failed"))
      .then((payload) => {
        setWorkflowMessage(`Saved ${payload.receipt && payload.receipt.markdown_path ? payload.receipt.markdown_path : "research map"}.`);
        setWriteReceiptEvent({
          kind: "research_map",
          label: "Save research map",
          row: "Research map",
          result: payload,
          snapshotError: ""
        });
        refreshLiveContextAfterWrite(params, { intake: false });
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("research_map", "Save research map", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setWorkflowMessage(`${String(err.message || err)} No research-map files changed.`);
      })
      .finally(() => setResearchMapSaving(false));
  };

  const pendingEditorWarnings = (options = {}) => {
    const warnings = [];
    if (options.intake !== false) {
      const fields = intakeChangedFields(intakeDraft);
      if (fields.length) warnings.push(`project brief (${fields.map(displayFieldName).join(", ")})`);
    }
    if (options.charter !== false && charterChanged(charterDraft)) {
      warnings.push("project charter");
    }
    if (options.sourceEdit !== false) {
      const fields = sourceChangedFields(sourceEditDraft);
      if (fields.length) {
        warnings.push(`source file ${sourceEditDraft.relative_raw_path || "draft"} (${fields.map(displayFieldName).join(", ")})`);
      }
    }
    if (options.scoringGuide !== false) {
      const fields = scoringGuideChangedFields(scoringGuideDraft);
      if (fields.length) warnings.push(`scoring guide (${fields.map(displayFieldName).join(", ")})`);
    }
    if (options.sourceImport === true) {
      const hasImportDraft = Boolean(
        String(sourceImportDraft.filename || "").trim() ||
        String(sourceImportDraft.created_by || "").trim() ||
        (sourceImportDraft.artifact_kind && sourceImportDraft.artifact_kind !== "project_note") ||
        String(sourceImportDraft.body || "").trim()
      );
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
        return Promise.resolve(refreshResult("project brief", false, "unsaved project-brief draft preserved"));
      }
      return loadIntakeDraft(projectParams);
    };
    const refreshCharterAfterWrite = () => {
      if (options.charter === false) return null;
      if (charterChanged(charterDraft)) {
        return Promise.resolve(refreshResult("project charter", false, "unsaved project-charter draft preserved"));
      }
      return loadCharterDraft(projectParams);
    };
    const tasks = [
      loadTraceContext(projectParams),
      loadWorkflowContext(projectParams),
      loadScoringGuideContext(projectParams),
      loadReportContractContext(projectParams),
      loadHealthContext(projectParams),
      refreshCharterAfterWrite(),
      refreshIntakeAfterWrite(),
      loadReceiptHistory(projectParams),
      loadClaimSupportContext(projectParams),
      loadEvidenceGapContext(projectParams),
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
    return fetch(url, { headers: { Accept: "application/json" }, ...(background ? { __wbSilent: true } : {}) })
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
            loadScoringGuideContext(liveParams),
            loadReportContractContext(liveParams),
            loadHealthContext(liveParams),
            loadCharterDraft(liveParams),
            loadIntakeDraft(liveParams),
            loadReceiptHistory(liveParams),
            loadRunHistoryContext(liveParams),
            loadClaimSupportContext(liveParams),
            loadEvidenceGapContext(liveParams),
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
        setPreflightMessage("Offline snapshot mode cannot run the live readiness check.");
        setSourceActionEvent(null);
        setSourceActionMessage("Offline snapshot mode cannot run live file and evidence checks.");
        setReportContractContext(null);
        setReportContractMessage("Offline snapshot mode uses the report status from the last generated project data only.");
        setReportSupportEvent(null);
        setReportSupportPrompt(null);
        setReportSynthesisPrompt(null);
        setHealthContext(null);
        setHealthMessage("Offline snapshot mode uses the last generated project data only.");
        setCharterDraft(null);
        setCharterMessage("Offline snapshot mode cannot edit the project charter.");
        setIntakeDraft(null);
        setIntakeMessage("Offline snapshot mode cannot edit the project brief.");
        setReceiptHistory(null);
        setReceiptHistoryMessage("Offline snapshot mode uses the latest generated project data only.");
        setRunHistoryContext(null);
        setRunHistoryMessage("Offline snapshot mode uses the run-history status from the last generated project data only.");
        setClaimSupportContext(null);
        setClaimSupportMessage("Offline snapshot mode uses source and evidence readiness from the last generated project data only.");
        setEvidenceGapContext(null);
        setEvidenceGapMessage("Offline snapshot mode cannot save evidence-gap justifications.");
        setEvidenceGapDraft(emptyEvidenceGapDraft());
        setEvidenceGapEvent(null);
        setSourceListContext(null);
        setSourceListMessage("Offline snapshot mode cannot inspect original files.");
        setSourceEditEvent(null);
        setSourceEditMessage("Offline snapshot mode cannot edit original files.");
        setWorkbenchSettings(null);
        setSettingsDraft({});
        setSettingsMessage("Offline snapshot mode cannot edit workbench settings.");
        setCapabilityContext(null);
        setCapabilityMessage("Offline snapshot mode cannot inspect the live reasoning-capability map.");
        setScoringGuideContext(null);
        setScoringGuideDraft(null);
        setScoringGuideMessage("Offline snapshot mode cannot edit scoring guides.");
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
      .then(() => {
        loadWorkbenchSettings();
        loadCapabilityContext();
        loadPrincipleContext();
        return fetch("/api/projects", { headers: { Accept: "application/json" } });
      })
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
        loadLeanMillContext();
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

  // Deep-link support: `?project=<slug>` opens that project once on load (also lets `?section=Verdict`
  // land on a real section instead of the picker). One-shot, guarded so it never re-fires.
  const autoOpenedProjectRef = React.useRef(false);
  React.useEffect(() => {
    if (autoOpenedProjectRef.current) return;
    if (!initialRoute.project || !liveMode || !projects.length) return;
    autoOpenedProjectRef.current = true;
    if (!snapshot || snapshot.project !== initialRoute.project) openProject(initialRoute.project);
  }, [liveMode, projects, snapshot]);

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

  const refreshEvidenceSupportLive = () => {
    if (!snapshot || !liveMode) return;
    const params = liveProjectParams();
    Promise.all([loadClaimSupportContext(params), loadEvidenceGapContext(params)])
      .then(() => setModeMessage("Evidence summary refreshed from local project files."))
      .catch((err) => setModeMessage(`Could not refresh evidence summary: ${err.message || err}`));
  };

  const refreshReportSupportLive = () => {
    if (!snapshot || !liveMode) return;
    const params = liveProjectParams();
    loadReportContractContext(params)
      .then(() => setModeMessage("Report readiness refreshed from local project files."))
      .catch((err) => setModeMessage(`Could not refresh report readiness: ${err.message || err}`));
  };

  const requestReportSupportRefreshLive = () => {
    if (!snapshot || !liveMode || reportSupportRunning) return;
    const params = liveProjectParams();
    setReportSupportRunning(true);
    setReportContractMessage("Loading report readiness preview.");
    setReportSupportEvent(null);
    fetch("/api/report-contract", {
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
      .then((response) => jsonResponseOrError(response, "report readiness preview failed"))
      .then((payload) => {
        setReportSupportEvent(payload);
        setReportSupportPrompt({
          ...params,
          command: payload.command || "",
          preview: payload,
          confirmedWriteBoundary: payload.confirmed_write_boundary || null,
          dialogEyebrow: "Report readiness",
          dialogTitle: "Check report readiness again?",
          dialogBody: "This refreshes the local report readiness file and saves a record. It does not call a model.",
          confirmLabel: "Check readiness",
          ariaLabel: "Confirm report readiness check",
          disabledTitle: "Files that may change must load before the check can run"
        });
        setReportContractMessage("Review the report readiness check before it runs.");
      })
      .catch((err) => {
        if (err.payload) setReportSupportEvent(err.payload);
        const failedWrite = refusedWriteEvent("report_support_refresh", "Report readiness", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReportContractMessage(`${String(err.message || err)} No project files changed.`);
      })
      .finally(() => setReportSupportRunning(false));
  };

  const requestReportSynthesisRefreshLive = () => {
    if (!snapshot || !liveMode || reportSupportRunning) return;
    const params = liveProjectParams();
    setReportSupportRunning(true);
    setReportContractMessage("Loading report-input refresh preview.");
    setReportSupportEvent(null);
    fetch("/api/report-synthesis", {
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
      .then((response) => jsonResponseOrError(response, "report-input refresh preview failed"))
      .then((payload) => {
        setReportSupportEvent(payload);
        setReportSynthesisPrompt({
          ...params,
          command: payload.command || "",
          preview: payload,
          confirmedWriteBoundary: payload.confirmed_write_boundary || null,
          dialogEyebrow: "Report inputs",
          dialogTitle: "Refresh report inputs?",
          dialogBody: "This rebuilds the report inputs from current project files, then checks report readiness. It may call the configured report model.",
          allowInstructions: true,
          confirmLabel: "Refresh report inputs",
          ariaLabel: "Confirm report input refresh",
          disabledTitle: "Files that may change must load before report inputs can refresh"
        });
        setReportContractMessage("Review the report-input refresh before it runs.");
      })
      .catch((err) => {
        if (err.payload) setReportSupportEvent(err.payload);
        const failedWrite = refusedWriteEvent("report_synthesis", "Report inputs", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReportContractMessage(`${String(err.message || err)} No project files changed.`);
      })
      .finally(() => setReportSupportRunning(false));
  };

  const cancelReportSupportPrompt = () => {
    if (!reportSupportRunning) {
      setReportSupportPrompt(null);
      setReportContractMessage("Report readiness check canceled. No project files changed.");
    }
  };

  const cancelReportSynthesisPrompt = () => {
    if (!reportSupportRunning) {
      setReportSynthesisPrompt(null);
      setReportContractMessage("Report-input refresh canceled. No project files changed.");
    }
  };

  const runConfirmedReportSupportRefreshLive = () => {
    if (!reportSupportPrompt || reportSupportRunning) return;
    const params = reportSupportPrompt;
    setReportSupportPrompt(null);
    setReportSupportRunning(true);
    setReportContractMessage("Checking report readiness.");
    fetch("/api/report-contract", {
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
      .then((response) => jsonResponseOrError(response, "report readiness check failed"))
      .then((payload) => {
        setReportContractContext(payload);
        setReportSupportEvent(payload);
        const writeEvent = reportSupportWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        loadReceiptHistory(params);
        setReportContractMessage(payload.accepted ? `Report readiness refreshed. Saved work: ${payload.receipt_path || "recorded"}.` : "Report readiness finished with attention.");
      })
      .catch((err) => {
        if (err.payload) {
          setReportSupportEvent(err.payload);
          setReportContractContext(err.payload);
          const writeEvent = reportSupportWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
        }
        const failedWrite = refusedWriteEvent("report_support_refresh", "Report readiness", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReportContractMessage(String(err.message || err));
      })
      .finally(() => setReportSupportRunning(false));
  };

  const runConfirmedReportSynthesisRefreshLive = (instructions) => {
    if (!reportSynthesisPrompt || reportSupportRunning) return;
    const params = reportSynthesisPrompt;
    const direction = String(instructions || "").trim();
    setReportSynthesisPrompt(null);
    setReportSupportRunning(true);
    setReportContractMessage(direction ? "Refreshing report inputs with your direction." : "Refreshing report inputs.");
    fetch("/api/report-synthesis", {
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
        confirmed: true,
        instructions: direction
      })
    })
      .then((response) => jsonResponseOrError(response, "report-input refresh failed"))
      .then((payload) => {
        setReportContractContext(payload);
        setReportSupportEvent(payload);
        const writeEvent = reportSupportWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        loadReceiptHistory(params);
        setReportContractMessage(payload.accepted ? `Report inputs refreshed. Saved work: ${payload.receipt_path || "recorded"}.` : "Report input refresh finished with attention.");
      })
      .catch((err) => {
        if (err.payload) {
          setReportSupportEvent(err.payload);
          setReportContractContext(err.payload);
          const writeEvent = reportSupportWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
        }
        const failedWrite = refusedWriteEvent("report_synthesis", "Report inputs", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReportContractMessage(String(err.message || err));
      })
      .finally(() => setReportSupportRunning(false));
  };

  // On-demand forecast (#78): elicit a probability for the thesis + price it via the sealed pool.
  // Calls a model (the confirmed path), so it runs with a clear running state. CLI-master via /api/forecast-scratch.
  const runForecastScratchLive = (question) => {
    if (!snapshot || !liveMode) return;
    const q = String(question || "").trim();
    if (!q) return;
    const params = liveProjectParams();
    setForecastScratch({ running: true, question: q });
    fetch("/api/forecast-scratch", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: params.project, question: q, domain: "thesis", confirmed: true }),
    })
      .then((response) => jsonResponseOrError(response, "forecast failed"))
      .then((payload) => setForecastScratch({ running: false, result: payload }))
      .catch((err) => setForecastScratch({ running: false, error: String(err.message || err) }));
  };

  // Eigenquestion (advisory) — the one question that most moves the thesis. Calls a model.
  const runEigenquestionLive = () => {
    if (!snapshot || !liveMode) return;
    const params = liveProjectParams();
    setEigenquestion({ running: true });
    fetch("/api/eigenquestion", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: params.project, confirmed: true }),
    })
      .then((response) => jsonResponseOrError(response, "eigenquestion failed"))
      .then((payload) => setEigenquestion({ running: false, result: payload }))
      .catch((err) => setEigenquestion({ running: false, error: String(err.message || err) }));
  };

  // Isomorphism (advisory) — "what is this like, and what does that predict?" Surfaces a cross-field
  // analogy for the project's claim + its forecastable predict-then-falsify. Calls a model.
  const runIsomorphismLive = () => {
    if (!snapshot || !liveMode) return;
    const params = liveProjectParams();
    setIsomorphism({ running: true });
    fetch("/api/isomorphism", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: params.project, confirmed: true }),
    })
      .then((response) => jsonResponseOrError(response, "isomorphism failed"))
      .then((payload) => setIsomorphism({ running: false, result: payload }))
      .catch((err) => setIsomorphism({ running: false, error: String(err.message || err) }));
  };

  // Rubric review (advisory) — a PRE-RUN critique of the scoring rubric: can it be gamed before you pay for a
  // run? Six checks (gaming coverage, evidence anchoring, score-without-evidence, criterion independence,
  // persona blind spots, charter-spirit). Calls a model; writes a review + candidate patch (never auto-edits).
  const runRubricReviewLive = () => {
    if (!snapshot || !liveMode) return;
    const params = liveProjectParams();
    setRubricReview({ running: true });
    fetch("/api/rubric-review", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: params.project, rubric: params.rubric, confirmed: true }),
    })
      .then((response) => jsonResponseOrError(response, "rubric review failed"))
      .then((payload) => setRubricReview({ running: false, result: payload }))
      .catch((err) => setRubricReview({ running: false, error: String(err.message || err) }));
  };

  // Stress-test the thesis — the adversarial inverter against the bounded claim. It loads the probability
  // DAG and targets the weakest node itself (exactly what the in-loop inverter does), so one click returns
  // the concrete tests that would break the soft spot. One model call, no full run, no run-artifact writes.
  const runFalsifyLive = (claim) => {
    if (!snapshot || !liveMode) return;
    const claimRow = rowByLabel((snapshot.rows) || [], "Bounded claim");
    const c = String(claim || (claimRow && (claimRow.detail || claimRow.value)) || "").trim();
    if (!c) return;
    const params = liveProjectParams();
    setFalsify({ running: true });
    fetch("/api/falsify-claim", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: params.project, claim: c, confirmed: true }),
    })
      .then((response) => jsonResponseOrError(response, "falsification failed"))
      .then((payload) => setFalsify({ running: false, result: payload }))
      .catch((err) => setFalsify({ running: false, error: String(err.message || err) }));
  };

  // Activation — drop a document, a model drafts the question / thesis / falsifier / scope guards, and the
  // create form fills in for you to refine (never a blank page; you edit + create). Advisory, one model call.
  const runProjectDraftLive = (text) => {
    const doc = String(text || "").trim();
    if (!liveMode || !doc) return;
    setProjectDraft({ running: true });
    fetch("/api/project-draft", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ text: doc, confirmed: true }),
    })
      .then((response) => jsonResponseOrError(response, "drafting failed"))
      .then((payload) => {
        if (payload && payload.ok) {
          setProjectCreateDraft((cur) => {
            const base = cur || emptyProjectCreateDraft();
            const nonClaims = Array.isArray(payload.non_claims) ? payload.non_claims.filter(Boolean) : [];
            return {
              ...base,
              task: payload.task || base.task || "",
              bounded_claim: payload.bounded_claim || base.bounded_claim || "",
              next_falsifier: payload.next_falsifier || base.next_falsifier || "",
              notes: nonClaims.length
                ? ["Scope — what this does NOT claim:", ...nonClaims.map((n) => `- ${n}`)].join("\n")
                : base.notes || "",
            };
          });
        }
        setProjectDraft({ running: false, result: payload });
      })
      .catch((err) => setProjectDraft({ running: false, error: String(err.message || err) }));
  };

  // Export the verified research graph as an Obsidian vault — the capstone for a researcher writing an
  // article FROM the stress-tested thesis. No model call; shells the CLI, which reuses the Map's projection.
  const runObsidianExportLive = () => {
    if (!snapshot || !liveMode || (obsidianExport && obsidianExport.running)) return;
    const params = liveProjectParams();
    setObsidianExport({ running: true });
    fetch("/api/export-obsidian", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ project: params.project }),
    })
      .then((response) => jsonResponseOrError(response, "Obsidian export failed"))
      .then((payload) => setObsidianExport({ running: false, result: payload }))
      .catch((err) => setObsidianExport({ running: false, error: String(err.message || err) }));
  };

  const buildClaimCardLive = () => {
    if (!snapshot || !liveMode || reportSupportRunning) return;
    const params = liveProjectParams();
    setReportSupportRunning(true);
    setReportContractMessage("Building shareable claim card.");
    setReportSupportEvent(null);
    fetch("/api/claim-card", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake
      })
    })
      .then((response) => jsonResponseOrError(response, "claim card build failed"))
      .then((payload) => {
        setReportSupportEvent(payload);
        const writeEvent = claimCardWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        loadReceiptHistory(params);
        if (payload.preview_path && previewableRepoPath(payload.preview_path)) {
          loadFilePreview({ type: "file", value: payload.preview_path });
        }
        setReportContractMessage(
          payload.accepted
            ? `Claim card built and verified: ${payload.html_path || payload.json_path || "saved"}.`
            : "Claim card built, but verification needs attention."
        );
      })
      .catch((err) => {
        if (err.payload) {
          setReportSupportEvent(err.payload);
          const writeEvent = claimCardWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
        }
        const failedWrite = refusedWriteEvent("claim_card", "Claim card", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReportContractMessage(String(err.message || err));
      })
      .finally(() => setReportSupportRunning(false));
  };

  const runProjectTestLive = (action = {}) => {
    if (!snapshot || !liveMode || reportSupportRunning || !isProjectTestAction(action)) return;
    const params = liveProjectParams();
    setReportSupportRunning(true);
    setReportContractMessage("Running project test.");
    setReportSupportEvent(null);
    fetch("/api/project-test", {
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
        action_id: action.id || "",
        action_label: action.label || ""
      })
    })
      .then((response) => jsonResponseOrError(response, "project test failed"))
      .then((payload) => {
        setReportSupportEvent(payload);
        const writeEvent = projectTestWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Report readiness", preserveSelection: true });
        return refreshLiveContextAfterWrite(params, { intake: false, charter: false, runHistory: true }).then(() => payload);
      })
      .then((payload) => {
        setReportContractMessage(
          payload.accepted
            ? `Project test passed. Saved work: ${payload.receipt_path || "recorded"}.`
            : `Project test needs attention. Saved work: ${payload.receipt_path || "recorded"}.`
        );
      })
      .catch((err) => {
        if (err.payload) {
          setReportSupportEvent(err.payload);
          const writeEvent = projectTestWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
        }
        const failedWrite = refusedWriteEvent("project_test", "Project test", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setReportContractMessage(String(err.message || err));
      })
      .finally(() => setReportSupportRunning(false));
  };

  const refreshServerReadiness = () => {
    setServerStatusMessage("Checking local server readiness.");
    loadServerStatus()
      .then(() => setModeMessage("Local server readiness refreshed."))
      .catch((err) => setModeMessage(`Local server readiness failed: ${err.message || err}`));
  };

  const refreshCurrentIntake = () => {
    if (!snapshot || !liveMode) return;
    runAfterPendingEditors("Reloading the project brief", { sourceEdit: false }, () => {
      const entry = currentProjectEntry || snapshot;
      loadIntakeDraft(projectLoadParams(entry));
    });
  };

  const refreshCurrentCharter = () => {
    if (!snapshot || !liveMode) return;
    runAfterPendingEditors("Reloading the project charter", { sourceEdit: false, intake: false }, () => {
      const entry = currentProjectEntry || snapshot;
      loadCharterDraft(projectLoadParams(entry));
    });
  };

  const createProjectLive = () => {
    if (!liveMode || projectCreating) return;
    const draftProject = String(projectCreateDraft.project || "").trim();
    const existingFolder = (projectFolders || []).find((folder) => folder.project === draftProject) || null;
    const addIntakeMode = Boolean(existingFolder && !existingFolder.openable && !existingFolder.intake_count);
    runAfterPendingEditors(addIntakeMode ? "Connecting this project" : "Creating and opening this project", { sourceImport: true }, () => {
      setProjectCreating(true);
      setProjectCreateMessage(addIntakeMode ? "Connecting existing project folder." : "Creating local project and project brief.");
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
        uploaded_sources: Array.isArray(projectCreateDraft.uploaded_sources) ? projectCreateDraft.uploaded_sources : [],
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
              ? `Project setup needs attention after writing ${written} paths. Inspect the last saved work before retrying.`
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
          ? " The project brief already exists, so the server opened the project and kept the existing file."
          : "";
        const createVerb = payload.created_mode === "add_intake" ? "Connected" : "Created";
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
        artifact_kind: sourceImportDraft.artifact_kind || "project_note",
        created_by: sourceImportDraft.created_by || "",
        body: sourceImportDraft.body
      })
    })
      .then((response) => jsonResponseOrError(response, "source save failed"))
      .then((payload) => {
        const gapSourceDraft = sourceImportDraft && sourceImportDraft.evidence_gap;
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Source readiness" });
        if (payload.trace) setTraceContext(payload.trace);
        setSourceImportDraft(emptySourceImportDraft());
        if (gapSourceDraft && payload.source_path) {
          const gapIndex = gapSourceDraft.index === undefined || gapSourceDraft.index === null ? "" : String(gapSourceDraft.index);
          const target = gapSourceDraft.target || "the active evidence gap";
          const requiredSurface = gapSourceDraft.required_surface || sourceBasename(payload.source_path);
          const reason = [
            `Added ${payload.source_path} for ${target}.`,
            requiredSurface ? `Needed evidence: ${requiredSurface}.` : "",
            "Review the source text before saving this justification."
          ].filter(Boolean).join(" ");
          setEvidenceGapDraft({
            index: gapIndex,
            reason,
            evidence_refs_text: payload.source_path
          });
          const intakeRefStaged = addImportedSourceToIntakeDraft(payload.source_path, payload.source_type);
          setSourceImportEvent({
            ...payload,
            evidence_gap_staged: true,
            intake_ref_staged: intakeRefStaged,
            evidence_gap_target: target,
            evidence_gap_index: gapIndex
          });
          setSourceImportMessage(
            intakeRefStaged
              ? `Saved ${payload.source_path}. The project brief and evidence-gap justification drafts now reference it; review and save each record.`
              : `Saved ${payload.source_path}. The evidence-gap justification draft references it; add it to the project brief before closing the gap.`
          );
        } else {
          setSourceImportEvent(payload);
          setSourceImportMessage(`Saved ${payload.source_path}. File status ${payload.source_check && payload.source_check.accepted ? "accepted" : "needs attention"}.`);
        }
        setWriteReceiptEvent({
          kind: "source_import",
          row: payload.relative_raw_path || payload.source_path,
          result: payload,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, {
          sources: true,
          intake: gapSourceDraft && payload.source_path ? false : undefined
        });
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
    const targetLabel = targetField === "evidence_refs_text" ? "evidence summaries" : "original files";
    if (!path) return false;
    if (!intakeDraft) {
      setSourceImportMessage(`Load a live project brief before staging ${targetLabel}.`);
      return false;
    }
    if (intakeDraft.editable === false) {
      setSourceImportMessage("This project brief is read-only; the source path was not staged.");
      return false;
    }
    const refs = linesFromText(intakeDraft[targetField]);
    if (refs.includes(path)) {
      setSourceImportMessage(`${path} is already in ${targetLabel}.`);
      return true;
    }
    const nextRefs = [...refs, path].join("\n");
    setIntakeDraft({ ...intakeDraft, [targetField]: nextRefs });
    setSourceImportMessage(`Staged ${path} in ${targetLabel}. Save the project brief to update saved history.`);
    setIntakeMessage(`Staged ${path} in ${targetLabel}. Save the project brief to update saved history.`);
    return true;
  };

  const prepareEvidenceGapSourceDraft = (gap, gapIndex = 0) => {
    const contract = gap && gap.recovery_contract && typeof gap.recovery_contract === "object" ? gap.recovery_contract : {};
    const requiredSurface = String((gap && (gap.required_surface || contract.required_surface)) || "").trim();
    const question = String((gap && gap.fetch_query) || "").trim();
    const target = String((gap && (gap.target || gap.id || gap.gap_id)) || "evidence gap").trim();
    const requiredFilename = sourceBasename(requiredSurface);
    const filename = SOURCE_IMPORT_FILENAME_RE.test(requiredFilename)
      ? requiredFilename
      : sourceNoteFilename(target || requiredSurface);
    const description = String((gap && (gap.description || gap.producer_rationale)) || "").trim();
    const body = [
      `# ${filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ")}`,
      "",
      `Target gap: ${target}`,
      requiredSurface ? `Needed evidence: ${requiredSurface}` : "",
      "",
      "Question to answer:",
      question || "Describe the evidence that resolves this gap.",
      "",
      description ? "Why this matters:" : "",
      description,
      "",
      "Evidence:",
      "- Replace this line with the source, rule, schema, or file that answers the question.",
      "",
      "Boundary:",
      "- State what this source does not prove."
    ].filter((line, index, lines) => line || lines[index - 1] !== "").join("\n");
    setSourceImportDraft({
      filename,
      source_type: "source_evidence",
      body,
      evidence_gap: {
        index: gapIndex,
        target,
        required_surface: requiredSurface,
        fetch_query: question
      }
    });
    setSourceImportEvent(null);
    setSourceImportMessage(`Drafted ${filename} from the active evidence gap. Replace the placeholder with the file details, then save the file.`);
    openDetail("sources", "Add file");
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
          artifact_kind: payload.artifact_kind || "",
          created_by: payload.created_by || "",
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

  const openFileEditorFromViewer = (target) => {
    if (!target || !snapshot || !liveMode) return;
    // Remember which file we came from so the modal's Back returns to this viewer.
    setEditorReturnPath((filePreview && filePreview.path) || "");
    setFilePreviewOpen(false);
    if (target.kind === "source" && target.relativeRawPath) {
      openModal(target.workspace, target.subsection);
      openRawSourceForEdit(target.relativeRawPath);
      return;
    }
    if (target.kind === "intake") {
      openModal(target.workspace, target.subsection);
      return;
    }
    if (target.kind === "charter") {
      openModal(target.workspace, target.subsection);
      loadCharterDraft(liveProjectParams());
      return;
    }
    if (target.kind === "scoring_guide") {
      openModal(target.workspace, target.subsection);
      loadScoringGuideContext(liveProjectParams());
      return;
    }
    openModal(target.workspace, target.subsection);
  };

  const saveRawSourceEdit = () => {
    if (!snapshot || !liveMode || sourceEditing) return;
    const params = liveProjectParams();
    setSourceEditing(true);
    setSourceEditMessage(`Saving ${sourceEditDraft.relative_raw_path || "file"}.`);
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
        artifact_kind: sourceEditDraft.artifact_kind || "",
        created_by: sourceEditDraft.created_by || "",
        body: sourceEditDraft.body
      })
    })
      .then((response) => jsonResponseOrError(response, "file save failed"))
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Source readiness", preserveSelection: true });
        if (payload.trace) setTraceContext(payload.trace);
        setSourceEditEvent(payload);
        const nextDraft = {
          relative_raw_path: payload.relative_raw_path || sourceEditDraft.relative_raw_path,
          source_type: payload.source_type || sourceEditDraft.source_type,
          artifact_kind: payload.artifact_kind || sourceEditDraft.artifact_kind || "",
          created_by: payload.created_by || sourceEditDraft.created_by || "",
          body: sourceEditDraft.body
        };
        setSourceEditDraft({ ...nextDraft, original: { ...sourceDraftFields(nextDraft) } });
        setSourceEditMessage(`Saved ${payload.source_path}. File status ${payload.source_check && payload.source_check.accepted ? "accepted" : "needs attention"}.`);
        setWriteReceiptEvent({
          kind: "source_edit",
          row: payload.relative_raw_path || payload.source_path,
          result: payload,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { sources: true });
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("source_edit", sourceEditDraft.relative_raw_path || "file edit", err);
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
    const matched = (snapshot.rows || []).filter((row) => {
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
    // The job here is "what needs my attention" — so loose ends surface first, settled items last,
    // whatever tab you're on. Stable within each band so the kernel's own order is preserved.
    const rank = (row) => (row.kind === "attention" ? 0 : row.kind === "ready" ? 2 : 1);
    return matched.map((row, index) => ({ row, index })).sort((a, b) => rank(a.row) - rank(b.row) || a.index - b.index).map((entry) => entry.row);
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
    const reportRow = rowByLabel(rows, "Report readiness") || {};
    return {
      schema: REPORT_CONTRACT_SCHEMA,
      status: (snapshot && snapshot.report_status) || reportRow.status || "unknown",
      status_reasons: (snapshot && snapshot.status_reasons) || [],
      support_issues: [],
      allowed_actions: [],
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
  const fileViewerEditTarget = editableProjectFileTarget(filePreview, snapshot);

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
    navigateWorkspace("overview", "Thesis");
  };
  const reviewRow = (label) => {
    if (!label) return;
    setSelectedLabel(label);
    navigateWorkspace("review", "Save review");
  };
  const actionRow = (label) => {
    if (!label) return;
    setSelectedLabel(label);
    openDetail("review", "Save next step");
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
  const useHealthActionNote = (note, action = "next_step", preferredLabel = "") => useActionNote(note, action, preferredLabel);

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
      setIntakeMessage("This project brief is read-only in the local workbench.");
      return;
    }
    if (!intakeChangedFields(intakeDraft).length) {
      setIntakeMessage("No changed project-brief fields to write.");
      return;
    }
    setIntakeMessage("Saving project brief.");
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
            ? `Saved project brief. Project refresh failed: ${payload.snapshot_error}`
            : `Saved project brief. Saved work: ${(payload.edit && payload.edit.latest) || "recorded"}.`
        );
        setWriteReceiptEvent({
          kind: "intake_edit",
          row: "Project intake",
          result: nestedReceiptResult(payload, "edit"),
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { intake: false });
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("intake_edit", "Project brief", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setIntakeMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      });
  };

  const saveCharterDraft = () => {
    if (!snapshot || !liveMode || !charterDraft) return;
    const params = liveProjectParams();
    if (charterDraft.editable === false) {
      setCharterMessage("This project charter is read-only in the local workbench.");
      return;
    }
    if (!charterChanged(charterDraft)) {
      setCharterMessage("No project-charter changes to write.");
      return;
    }
    setCharterMessage("Saving project charter.");
    setWriteReceiptEvent(null);
    fetch("/api/charter", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        text: charterDraft.text
      })
    })
      .then((response) => jsonResponseOrError(response, "charter save failed"))
      .then((payload) => {
        if (!payload.ok) throw new Error(payload.error || "charter save failed");
        if (payload.charter) setCharterDraft(charterDraftFromPayload(payload.charter));
        setCharterMessage(`Saved project charter. Saved history: ${payload.latest || "recorded"}.`);
        setWriteReceiptEvent({
          kind: "charter_edit",
          row: "Project charter",
          result: payload,
          snapshotError: payload.snapshot_error || ""
        });
        refreshLiveContextAfterWrite(params, { charter: false });
      })
      .catch((err) => {
        const failedWrite = refusedWriteEvent("charter_edit", "Project charter", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setCharterMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      });
  };

  const runPreflightLive = () => {
    if (!snapshot || !liveMode || preflightRunning) return;
    setPreflightRunning(true);
    setPreflightMessage("Running local readiness check.");
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
            const error = new Error(payload.error || payload.stderr_tail || payload.stdout_tail || `readiness check failed: ${response.status}`);
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
            ? snapshotRefreshMessage("Readiness accepted", payload)
            : "Readiness check finished without an acceptance marker."
        );
      })
      .catch((err) => {
        if (err.payload) {
          setPreflightEvent(err.payload);
          if (err.payload.trace) setTraceContext(err.payload.trace);
          if (err.payload.snapshot) installSnapshot(err.payload.snapshot, { preferredLabel: "Run readiness", preserveSelection: true });
        }
        const failedWrite = refusedWriteEvent("preflight", "Readiness check", err);
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
          setBoundedRunEvent(payload);
          setProjectRunPrompt({
            ...params,
            command: payload.command || command,
            preview: payload,
            effectiveSettings: payload.effective_settings || {},
            confirmedWriteBoundary: payload.confirmed_write_boundary || null
          });
          setBoundedRunMessage("Review the project run before starting it.");
        } else {
          setBoundedRunMessage(payload.error || "No project run command is loaded.");
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
    action === "evidence_bind" || action === "evidence_replay" || action === "evidence_prepare" ? "Evidence readiness" : "Source readiness";

  const runSourceActionLive = (action, options = {}) => {
    if (!snapshot || !liveMode || sourceActionRunning) return;
    const params = liveProjectParams();
    setSourceActionRunning(true);
    const confirmed = options.confirmed === true;
    setSourceActionMessage(confirmed ? `Running ${displayText(action)}.` : `Loading ${displayText(action)} preview.`);
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
        action,
        confirmed
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
        if (payload.status === "needs_confirmation") {
          const actionSettings = payload.effective_settings || {};
          const writePathCount = payload.confirmed_write_boundary && Array.isArray(payload.confirmed_write_boundary.write_paths)
            ? payload.confirmed_write_boundary.write_paths.length
            : 0;
          setSourceActionEvent(payload);
          setSourceActionPrompt({
            ...params,
            action,
            command: payload.command || "",
            preview: payload,
            effectiveSettings: actionSettings,
            confirmedWriteBoundary: payload.confirmed_write_boundary || null,
            dialogEyebrow: payload.label || "File check",
            dialogTitle: `${payload.label || displayText(action)}?`,
            dialogBody: payload.confirmation_reason || "This action can call configured models and write project files.",
            dialogFacts: [
              { label: "Project", value: params.project },
              { label: "Project brief", value: params.intake || "default", monospace: true },
              { label: "Evidence model", value: actionSettings.model || "runtime default" },
              { label: "Fallback", value: actionSettings.model_fallback === "1" ? "allowed" : "off" },
              {
                label: "Timeout/retries",
                value: [
                  actionSettings.evidence_llm_timeout ? `${actionSettings.evidence_llm_timeout}s` : "",
                  actionSettings.evidence_llm_retries ? `${actionSettings.evidence_llm_retries} retries` : ""
                ].filter(Boolean).join(" / ") || "not loaded"
              },
              { label: "Files after confirm", value: writePathCount ? `${writePathCount} listed paths` : "not available" }
            ],
            confirmLabel: payload.label || "Run action",
            ariaLabel: `Confirm ${payload.label || displayText(action)}`,
            disabledTitle: "Files that may change must load before this action can run"
          });
          setSourceActionMessage(`Review ${payload.label || displayText(action)} before it runs.`);
          return;
        }
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

  const cancelSourceActionPrompt = () => {
    if (!sourceActionRunning) {
      setSourceActionPrompt(null);
      setSourceActionMessage("File check canceled. No project files changed.");
    }
  };

  const runConfirmedSourceActionLive = () => {
    if (!sourceActionPrompt || sourceActionRunning) return;
    const action = sourceActionPrompt.action;
    setSourceActionPrompt(null);
    runSourceActionLive(action, { confirmed: true });
  };

  const requestEvidenceFetchLive = (target = "") => {
    if (!snapshot || !liveMode || evidenceFetchRunning) return;
    const params = liveProjectParams();
    const fetchTarget = typeof target === "string" ? target.trim() : "";
    setEvidenceFetchRunning(true);
    setEvidenceGapMessage(fetchTarget ? "Loading fetch preview for this gap." : "Loading evidence-fetch preview.");
    setEvidenceFetchEvent(null);
    fetch("/api/evidence-fetch", {
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
        target: fetchTarget,
        confirmed: false
      })
    })
      .then((response) => jsonResponseOrError(response, "evidence fetch preview failed"))
      .then((payload) => {
        setEvidenceFetchEvent(payload);
        const fetchSettings = payload.settings || {};
        const activeGapText = payload.active_gap_count || payload.gap_count
          ? `${payload.active_gap_count || payload.gap_count} active`
          : "not loaded";
        const fetchDialogBody = [
          payload.gap_summary,
          payload.confirmation_reason || "This action can call configured search/model providers and write project files."
        ].filter(Boolean).join(" ");
        setEvidenceFetchPrompt({
          ...params,
          target: fetchTarget,
          command: payload.command || "",
          preview: payload,
          confirmedWriteBoundary: payload.confirmed_write_boundary || null,
          dialogEyebrow: "Evidence recovery",
          dialogTitle: fetchTarget ? "Fetch evidence for this gap?" : "Fetch missing evidence?",
          dialogBody: fetchDialogBody,
          dialogFacts: [
            { label: "Project", value: params.project },
            { label: "Project brief", value: params.intake, monospace: true },
            { label: "Active gaps", value: activeGapText },
            { label: "Evidence model", value: fetchSettings.model || "runtime default" },
            { label: "Search backend", value: fetchSettings.evidence_search_backend || "auto" },
            { label: "Auto-compile", value: fetchSettings.auto_compile === "1" ? "yes" : "no" },
            { label: "Fallback", value: fetchSettings.model_fallback === "1" ? "allowed" : "off" },
            { label: "Files after confirm", value: payload.confirmed_write_boundary && Array.isArray(payload.confirmed_write_boundary.write_paths) ? `${payload.confirmed_write_boundary.write_paths.length} listed paths` : "not available" }
          ],
          confirmLabel: "Fetch evidence",
          ariaLabel: "Confirm evidence fetch",
          disabledTitle: "Files that may change must load before evidence fetch can run"
        });
        setEvidenceGapMessage("Review evidence fetch before it runs.");
      })
      .catch((err) => {
        if (err.payload) setEvidenceFetchEvent(err.payload);
        const failedWrite = refusedWriteEvent("evidence_fetch", "Fetch evidence", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setEvidenceGapMessage(`${String(err.message || err)} No project files changed.`);
      })
      .finally(() => setEvidenceFetchRunning(false));
  };

  const cancelEvidenceFetchPrompt = () => {
    if (!evidenceFetchRunning) {
      setEvidenceFetchPrompt(null);
      setEvidenceGapMessage("Evidence fetch canceled. No project files changed.");
    }
  };

  const runConfirmedEvidenceFetchLive = () => {
    if (!evidenceFetchPrompt || evidenceFetchRunning) return;
    const params = evidenceFetchPrompt;
    setEvidenceFetchPrompt(null);
    setEvidenceFetchRunning(true);
    setEvidenceGapMessage("Fetching evidence with configured providers.");
    fetch("/api/evidence-fetch", {
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
        target: params.target || "",
        confirmed: true
      })
    })
      .then((response) => jsonResponseOrError(response, "evidence fetch failed"))
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Evidence readiness", preserveSelection: true });
        if (payload.evidence_gaps) setEvidenceGapContext(payload.evidence_gaps);
        if (payload.claim_support) setClaimSupportContext(payload.claim_support);
        setEvidenceFetchEvent(payload);
        const writeEvent = evidenceFetchWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        setEvidenceGapMessage(evidenceFetchStatusMessage(payload));
        return refreshLiveContextAfterWrite(params, { sources: true });
      })
      .catch((err) => {
        if (err.payload) {
          setEvidenceFetchEvent(err.payload);
          if (err.payload.evidence_gaps) setEvidenceGapContext(err.payload.evidence_gaps);
          if (err.payload.claim_support) setClaimSupportContext(err.payload.claim_support);
          if (err.payload.snapshot) installSnapshot(err.payload.snapshot, { preferredLabel: "Evidence readiness", preserveSelection: true });
          const writeEvent = evidenceFetchWriteEvent(err.payload);
          if (writeEvent) setWriteReceiptEvent(writeEvent);
          setEvidenceGapMessage(evidenceFetchStatusMessage(err.payload));
          if (writeEvent) refreshLiveContextAfterWrite(params, { sources: true });
        } else {
          setEvidenceGapMessage(String(err.message || err));
        }
        const failedWrite = refusedWriteEvent("evidence_fetch", "Fetch evidence", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
      })
      .finally(() => setEvidenceFetchRunning(false));
  };

  const justifyEvidenceGapLive = (gapIndex, gap) => {
    if (!snapshot || !liveMode || evidenceGapRunning) return;
    const params = liveProjectParams();
    const selector = { index: Number.isFinite(Number(gapIndex)) ? Number(gapIndex) : 0 };
    if (gap && gap.id) selector.gap_id = gap.id;
    const reason = (evidenceGapDraft && evidenceGapDraft.reason) || "";
    const evidenceRefs = linesFromText((evidenceGapDraft && evidenceGapDraft.evidence_refs_text) || "");
    setEvidenceGapRunning(true);
    setEvidenceGapMessage("Saving evidence-gap justification.");
    setEvidenceGapEvent(null);
    fetch("/api/evidence-gap-justify", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        project: params.project,
        rubric: params.rubric,
        intake: params.intake,
        selector,
        status: "justified",
        reason,
        evidence_refs: evidenceRefs
      })
    })
      .then((response) => jsonResponseOrError(response, "evidence-gap justification failed"))
      .then((payload) => {
        if (payload.snapshot) installSnapshot(payload.snapshot, { preferredLabel: "Evidence readiness", preserveSelection: true });
        if (payload.evidence_gaps) setEvidenceGapContext(payload.evidence_gaps);
        setEvidenceGapEvent(payload);
        const writeEvent = evidenceGapJustifyWriteEvent(payload);
        if (writeEvent) setWriteReceiptEvent(writeEvent);
        setEvidenceGapMessage(`Saved justification record: ${payload.receipt_path || "recorded"}.`);
        setEvidenceGapDraft({ ...emptyEvidenceGapDraft(), index: evidenceGapDraft && evidenceGapDraft.index ? evidenceGapDraft.index : String(selector.index) });
        refreshLiveContextAfterWrite(params);
      })
      .catch((err) => {
        if (err.payload) setEvidenceGapEvent(err.payload);
        const failedWrite = refusedWriteEvent("evidence_gap_justify", (gap && (gap.target || gap.id)) || "Evidence gap", err);
        if (failedWrite) setWriteReceiptEvent(failedWrite);
        setEvidenceGapMessage(`${String(err.message || err)}${failedWrite ? " No project files changed." : ""}`);
      })
      .finally(() => setEvidenceGapRunning(false));
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
          kind: "project_file",
          row: payload.path || "project file",
          result: payload,
          snapshotError: ""
        });
        return refreshLiveContextAfterWrite(params);
      })
      .catch((err) => {
        const error = String(err.message || err);
        const failedWrite = refusedWriteEvent("project_file", "project file", err);
        setProjectFileSaveEvent({ error });
        setLastRefreshResults([]);
        setWriteReceiptEvent(failedWrite || {
          kind: "project_file",
          row: "project file",
          result: {
            receipt: {
              schema: PROJECT_FILE_WRITE_SCHEMA,
              status: "save_failed",
              error
            }
          },
          snapshotError: error
        });
      })
      .finally(() => setProjectFileSaving(false));
  };

  const filePreviewEntryFromItem = (item) => {
    const rawPath = item && (item.value || item.path || item.preview_path || item.ref);
    const previewPath = previewableRepoPath(rawPath);
    if (!previewPath) return null;
    return { type: item.type || "file", value: previewPath };
  };

  const rememberFilePreview = (entry, options = {}) => {
    if (!entry || options.fromHistory) return;
    setFilePreviewHistory((current) => {
      const currentEntry = current[filePreviewHistoryIndex];
      if (currentEntry && currentEntry.value === entry.value && currentEntry.type === entry.type) return current;
      const base = filePreviewHistoryIndex >= 0 ? current.slice(0, filePreviewHistoryIndex + 1) : [];
      const next = [...base, entry].slice(-80);
      setFilePreviewHistoryIndex(next.length - 1);
      return next;
    });
  };

  const loadFilePreview = (item, options = {}) => {
    // inline mode loads the content into the embedded inspector preview WITHOUT popping the modal,
    // so selecting a point can show its content in place instead of intruding with a dialog.
    const openModal = !options.inline;
    const entry = filePreviewEntryFromItem(item);
    const previewPath = entry && entry.value;
    if (!liveMode) {
      setFilePreview(null);
      setFilePreviewMessage("Start the workbench server to preview repository files.");
      if (openModal) setFilePreviewOpen(true);
      return;
    }
    if (!previewPath) {
      if (options.inline) return;
      setFilePreview(null);
      setFilePreviewMessage("Selected path is not a previewable repository file.");
      setFilePreviewOpen(true);
      return;
    }
    setFilePreview(null);
    setFilePreviewMessage(`Loading ${previewPath}.`);
    if (openModal) setFilePreviewOpen(true);
    fetch(endpointUrl("/api/file", { path: previewPath }), { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`file preview failed: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (payload.ok === false) throw new Error(payload.error || "file preview failed");
        rememberFilePreview(entry, options);
        setFilePreview(payload);
        setFilePreviewMessage(payload.truncated ? "Preview truncated to the first 200 KB." : "Preview loaded from the workbench server.");
      })
      .catch((err) => {
        setFilePreview(null);
        setFilePreviewMessage(String(err.message || err));
      });
  };
  const navigateFilePreviewHistory = (offset) => {
    const nextIndex = filePreviewHistoryIndex + offset;
    const entry = filePreviewHistory[nextIndex];
    if (!entry) return;
    setFilePreviewHistoryIndex(nextIndex);
    loadFilePreview(entry, { fromHistory: true });
  };
  const closeActiveModal = useCallback(() => { setActiveModalKey(""); setEditorReturnPath(""); }, []);
  const closeFilePreview = useCallback(() => setFilePreviewOpen(false), []);

  if (error) {
    return h("main", { className: "state-page error" }, h("h1", null, "Project Workbench"), h("p", null, error));
  }
  if (!snapshot) {
    return h("main", { className: "state-page loading" }, h("h1", null, "Project Workbench"), h("p", null, "Loading project data."));
  }

  const selectedHiddenByFilter = Boolean(selectedRow && !filteredRows.some((row) => row.label === selectedRow.label));
  const actionContracts = (serverStatus && serverStatus.api && serverStatus.api.action_contracts) || {};
  const sourceReadinessPanel = h(Evidence, {
    key: "evidence",
    view: buildEvidenceView(sourceListContext, claimSupportContext, snapshot, evidenceGapContext, sourceActionRunning, evalResults),
    onPreview: loadFilePreview,
    onCompile: () => runSourceActionLive("evidence_prepare"),
    onAddFile: () => openModal("sources", "Add file"),
    onOpenGaps: () => navigateWorkspace("run", "Results"),
    onFetchGap: (target) => requestEvidenceFetchLive(target || ""),
    fetchRunning: evidenceFetchRunning,
  });
  const scoringGuidePanel = h(ScoringGuidePanel, {
    key: "scoring-guide",
    guide: scoringGuideContext,
    draft: scoringGuideDraft,
    setDraft: setScoringGuideDraft,
    message: scoringGuideMessage,
    saving: scoringGuideSaving,
    liveMode,
    onSave: saveScoringGuide,
    onReload: () => loadScoringGuideContext(liveProjectParams()),
    onPreview: loadFilePreview,
    onUseStarterDimensions: useStarterScoringDimensions
  });
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
        onOpenIntake: () => openDetail("sources", "Project brief"),
        onOpenEvidenceGap: () => openDetail("run", "Results")
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
        onOpenReadiness: () => openDetail("sources", "Prepare files")
      });
  const projectFilePanel = h(CaseFilePanel, {
        key: "case-file",
        snapshot,
        receiptHistory,
        projectEntry: currentProjectEntry,
        intakeDraft,
        sourceImportDraft,
        sourceEditDraft,
        evidenceGapDraft,
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
  const activeProjectState = (workflowContext && workflowContext.project_state) || {};
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
  const projectEvidenceMapPanel = h(ProjectEvidenceMap, {
        key: "project-evidence-map",
        claimSupport: claimSupportContext,
        thesisSupport: activeProjectState.thesis_support,
        evidenceState: activeProjectState.evidence || {},
        onOpenDetail: openDetail,
        onPreview: loadFilePreview
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
        startIntent: projectStartIntent,
        onCreate: createProjectLive,
        onPreview: loadFilePreview,
        onNavigateWorkspace: navigateWorkspace,
        onDraft: liveMode ? runProjectDraftLive : null,
        projectDraft,
        filePreview,
        filePreviewMessage
      });
  const dayZeroPanel = h(DayZeroStartPanel, {
        key: "day-zero",
        liveMode,
        onCreateProject: (start) => navigateWorkspace("projects", "Connect project", { start }),
        onShowProjects: () => setDayZero(false),
        onOpenSettings: () => navigateWorkspace("projects", "Settings")
      });
  function openDetailKey(nextKey, options = {}) {
    if (!nextKey) return;
    setActiveModalKey(nextKey);
    if (options.fromHistory) return;
    setDetailModalHistory((current) => {
      const currentKey = current[detailModalHistoryIndex];
      if (currentKey === nextKey) return current;
      const base = detailModalHistoryIndex >= 0 ? current.slice(0, detailModalHistoryIndex + 1) : [];
      const next = [...base, nextKey].slice(-80);
      setDetailModalHistoryIndex(next.length - 1);
      return next;
    });
  }
  function openDetail(workspaceId, subsection) {
    const [normalizedWorkspace, normalizedSubsection] = normalizeWorkspaceTarget(workspaceId, subsection);
    setActiveWorkspace(normalizedWorkspace);
    setActiveSubsection(normalizedSubsection);
    setProjectStartIntent("");
    syncWorkbenchRouteToUrl({
      workspace: normalizedWorkspace,
      subsection: normalizedSubsection,
      day0: day0Mode
    });
    openDetailKey(detailKey(normalizedWorkspace, normalizedSubsection));
  }
  // Open the detail modal as a pure OVERLAY — without navigating the background view. Closing it
  // returns you to where you were (e.g. "View the ledger" from the Thesis stays on the Thesis).
  function openModal(workspaceId, subsection) {
    // Modals can show sections that are intentionally OFF the subnav (Add file, Edit file).
    // normalizeWorkspaceTarget folds those back to subnav[0] for navigation safety, which would
    // silently drop you on "Prepare files". For modals, resolve the workspace + alias the
    // subsection but keep off-subnav targets intact so the right detail panel renders.
    const requestedWorkspace = String(workspaceId || "").trim();
    const wsId = WORKSPACE_ALIASES[requestedWorkspace] || requestedWorkspace;
    const section = WORKSPACE_SECTIONS.find((item) => item.id === wsId) || WORKSPACE_SECTIONS[0];
    const aliases = WORKSPACE_SUBSECTION_ALIASES[section.id] || {};
    const rawSub = String(subsection || "").trim() || section.subnav[0];
    const sub = aliases[rawSub] || rawSub;
    openDetailKey(detailKey(section.id, sub));
  }
  function navigateWorkspace(workspaceId, subsection, options = {}) {
    const [normalizedWorkspace, normalizedSubsection] = normalizeWorkspaceTarget(workspaceId, subsection);
    const nextStartIntent = String(options.start || "").trim().toLowerCase();
    const routeStartIntent = ["files", "thesis", "folder"].includes(nextStartIntent) ? nextStartIntent : "";
    setActiveWorkspace(normalizedWorkspace);
    setActiveSubsection(normalizedSubsection);
    setProjectStartIntent(routeStartIntent);
    setActiveModalKey("");
    syncWorkbenchRouteToUrl({
      workspace: normalizedWorkspace,
      subsection: normalizedSubsection,
      day0: day0Mode,
      start: routeStartIntent
    });
  }
  function setDayZero(enabled) {
    const nextDay0 = Boolean(enabled);
    const [workspace, subsection] = normalizeWorkspaceTarget("projects", nextDay0 ? "Current project" : "Projects");
    setDay0Mode(nextDay0);
    setProjectStartIntent("");
    setActiveWorkspace(workspace);
    setActiveSubsection(subsection);
    setActiveModalKey("");
    syncWorkbenchRouteToUrl({ workspace, subsection, day0: nextDay0 });
  }
  function navigateDetailModalHistory(offset) {
    const nextIndex = detailModalHistoryIndex + offset;
    const nextKey = detailModalHistory[nextIndex];
    if (!nextKey) return;
    const [workspaceId, subsection] = nextKey.split(":");
    const [normalizedWorkspace, normalizedSubsection] = normalizeWorkspaceTarget(workspaceId, subsection);
    setDetailModalHistoryIndex(nextIndex);
    setActiveWorkspace(normalizedWorkspace);
    setActiveSubsection(normalizedSubsection);
    setProjectStartIntent("");
    syncWorkbenchRouteToUrl({
      workspace: normalizedWorkspace,
      subsection: normalizedSubsection,
      day0: day0Mode
    });
    openDetailKey(detailKey(normalizedWorkspace, normalizedSubsection), { fromHistory: true });
  }
  const hydrateProjectCreateSources = (projectOrFolder) => {
    if (!liveMode || !projectOrFolder) return;
    const folder = typeof projectOrFolder === "string" ? { project: projectOrFolder } : projectOrFolder;
    const project = String(folder.project || "").trim();
    if (!project) return;
    const previewSourceRefs = uniqueLines([
      ...(folder.source_preview_files || []),
      ...(folder.raw_preview_files || []),
      ...(folder.root_preview_files || [])
    ]);
    fetch(endpointUrl("/api/project-recovery-draft", { project }), { headers: { Accept: "application/json" } })
      .then((response) => jsonResponseOrError(response, "project recovery draft failed"))
      .then((payload) => {
        if (!payload || !payload.ok) return;
        setProjectCreateDraft((draft) => {
          if (String(draft.project || "").trim() !== project) return draft;
          return {
            ...draft,
            recovery_payload: payload,
            task: String(draft.task || "").trim() ? draft.task : payload.task || draft.task,
            bounded_claim: String(draft.bounded_claim || "").trim() ? draft.bounded_claim : payload.bounded_claim || draft.bounded_claim,
            next_falsifier: String(draft.next_falsifier || "").trim() ? draft.next_falsifier : payload.next_falsifier || draft.next_falsifier,
            notes: String(draft.notes || "").trim() ? draft.notes : payload.notes || draft.notes,
            source_refs_text: String(draft.source_refs_text || "").trim()
              ? draft.source_refs_text
              : (payload.source_refs || []).join("\n"),
            evidence_refs_text: String(draft.evidence_refs_text || "").trim()
              ? draft.evidence_refs_text
              : (payload.evidence_refs || []).join("\n"),
            non_claims_text: String(draft.non_claims_text || "").trim()
              ? draft.non_claims_text
              : (payload.non_claims || []).join("\n")
          };
        });
        const addIntakeAction = payload.add_intake_action || {};
        const addIntakeBoundary = addIntakeAction.write_boundary || payload.add_intake_write_boundary || {};
        const addIntakeTarget = addIntakeBoundary.receipt_path
          ? ` Target: ${addIntakeBoundary.receipt_path}.`
          : "";
        const addIntakeRule = addIntakeAction.rule
          ? ` Rule: ${displayMessage(addIntakeAction.rule)}`
          : "";
        setProjectCreateMessage(
          `Loaded a project-brief draft from ${payload.source_file_count || 0} original files and ${payload.evidence_file_count || 0} evidence summaries.${addIntakeTarget}${addIntakeRule}`
        );
      })
      .catch((err) => {
        setProjectCreateMessage(`Could not draft project brief from ${project}: ${err.message || err}`);
        setProjectCreateDraft((draft) => String(draft.project || "").trim() === project ? { ...draft, recovery_payload: null } : draft);
      });
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
        if (!previewSourceRefs.length) {
          setProjectCreateMessage(`Could not load original files for ${project}: ${err.message || err}`);
        }
      });
  };
  const startProjectCreate = (projectOrFolder) => {
    if (projectOrFolder) {
      setProjectCreateDraft((draft) => projectCreateDraftFromFolder(projectOrFolder, draft));
      hydrateProjectCreateSources(projectOrFolder);
    }
    navigateWorkspace("projects", "Connect project");
  };
  const projectSwitchPanel = h(
    "section",
    { className: "project-switch-actions", "aria-label": "Switch project" },
    h(
      "div",
      null,
      h("strong", null, "Open another project"),
      h(
        "p",
        null,
        liveMode
          ? `${projectFolders.length || projects.length || 0} project folder${(projectFolders.length || projects.length || 0) === 1 ? "" : "s"} available.`
          : "Start the local server to browse project folders."
      )
    ),
    h(
      "div",
      { className: "project-switch-actions-buttons" },
      h(
        "button",
        {
          type: "button",
          className: "copy-button primary",
          disabled: !liveMode || loadingSnapshot,
          onClick: () => navigateWorkspace("projects", "Projects")
        },
        loadingSnapshot ? "Refreshing" : "Projects"
      ),
      h(
        "button",
        {
          type: "button",
          className: "copy-button",
          disabled: !liveMode,
          onClick: () => startProjectCreate()
        },
        "Create project"
      )
    )
  );
  const leanMillProps = {
    state: leanMillContext,
    message: leanMillMessage,
    liveMode,
    blueprintDraft: leanMillBlueprintDraft,
    setBlueprintDraft: updateLeanMillBlueprintDraft,
    blueprintEvent: leanMillBlueprintEvent,
    blueprintMessage: leanMillBlueprintMessage,
    blueprintRunning: leanMillBlueprintRunning,
    onPreviewBlueprint: () => submitLeanMillBlueprint(false),
    onSaveBlueprint: () => submitLeanMillBlueprint(true),
    actionDraft: leanMillActionDraft,
    actionEvent: leanMillActionEvent,
    actionMessage: leanMillActionMessage,
    actionRunning: leanMillActionRunning,
    setActionDraft: updateLeanMillActionDraft,
    onPreviewAction: submitLeanMillAction,
    onStartAction: submitLeanMillAction,
    onRefresh: loadLeanMillContext,
    onPreview: loadFilePreview,
    onScaffoldArea: submitLeanMillScaffold,
    onNavigateWorkspace: navigateWorkspace
  };
  const leanMillView = (view, key) => [h(LeanMillPanel, { key, view, ...leanMillProps })];
  const workspacePanels = {
    overview: {
      Thesis: [
        h(Thesis, { key: "thesis", view: buildThesisView(snapshot, claimSupportContext, evalResults), onOpenDetail: navigateWorkspace, onOpenModal: openModal, onPreview: loadFilePreview, onEigenquestion: runEigenquestionLive, eigenquestion })
      ],
      Assumptions: [
        h(Assumptions, { key: "assumptions", view: buildAssumptionsView(evalResults), onOpenDetail: navigateWorkspace })
      ],
      Charter: [
        h(Charter, {
          key: "charter",
          view: buildCharterView(charterDraft, evalResults),
          draft: charterDraft,
          setDraft: setCharterDraft,
          liveMode,
          changed: charterChanged(charterDraft),
          onSave: saveCharterDraft,
          onReload: refreshCurrentCharter,
          onPreview: loadFilePreview
        })
      ],
      "Evidence summary": [projectEvidenceMapPanel, sourceReadinessPanel],
      "Research map": [
        h(ResearchMap, {
          key: "research-map",
          view: buildMapView(researchMapData || ((workflowContext && workflowContext.project_state) || {}).research_map || {}, researchGraph),
          onPreview: loadFilePreview,
          onOpenDetail: navigateWorkspace,
          onIsomorphism: runIsomorphismLive,
          isomorphism: isomorphism
        })
      ]
    },
    sources: {
      "Prepare files": [sourceReadinessPanel],
      "Project brief": [intakePanel],
      "Add file": [sourceImportPanel],
      "Edit file": [rawSourcePanel]
    },
    run: {
      // Harden's JTBD (PRD §7.2): view the last run, then launch the loop again for N rounds. The
      // run console LEADS — set rounds + launch + live progress — then the findings from the last run.
      // The cost-preview/confirm + readiness checks tuck behind disclosures (not the primary surface).
      "Ready to run": (() => {
        const console = h(RunConsole, {
          key: "run-console",
          view: buildRunConsoleView(runConfig, runConfigOverrides, runStatus, traceContext, runHistoryContext),
          liveMode, running: boundedRunRunning, previewing: boundedRunPreviewing, message: boundedRunMessage,
          onIters: setRunIters, onLaunch: requestBoundedRunLive,
          onResolve: () => navigateWorkspace("run", "Check readiness"),
          onOpenSettings: () => navigateWorkspace("run", "Run settings"),
          onOpenScoring: () => navigateWorkspace("run", "Scoring guide"),
        });
        // The "Run N rounds →" button previews the cost then opens the confirm MODAL
        // (ProjectRunConfirmDialog) — the button-and-modal the run-again flow should be.
        const out = [console];
        if (evalResults && evalResults.ok) {
          out.push(h(RunFindings, { key: "run-findings-landing", view: buildRunFindingsView(evalResults, scoreTrajectory), onOpenDetail: navigateWorkspace }));
        } else {
          // No run yet — readiness console so the user can get the project launch-ready.
          out.push(h(TraceConsolePanel, { key: "trace", traceContext, message: traceMessage, liveMode, onPreviewSource: loadFilePreview, onOpenDetail: openDetail }));
        }
        return out;
      })(),
      "Scoring guide": [
        h(ScoringGuide, { key: "scoring-humane", view: buildScoringView(scoringGuideContext), onToggleGate: toggleScoringGate, saving: scoringGuideSaving, onReviewRubric: liveMode ? runRubricReviewLive : null, rubricReview }),
        h(MoreDetail, { key: "scoring-raw", title: "Edit the raw scoring guide" }, scoringGuidePanel)
      ],
      "Run settings": [h(RunConfigPanel, { key: "run-config", runConfig, overrides: runConfigOverrides, setOverrides: setRunConfigOverrides, message: runConfigMessage, saving: runConfigSaving, liveMode, onSave: saveRunConfig, onRefresh: loadRunConfig })],
      "Check readiness": [h(PreflightRunPanel, { key: "preflight", traceContext, event: preflightEvent, message: preflightMessage, running: preflightRunning, liveMode, preflightContract: actionContracts.preflight || {}, onRun: runPreflightLive })],
      Results: (() => {
        const activeGapCount = Number(
          (evidenceGapContext && (evidenceGapContext.active_evidence_gap_count ?? (evidenceGapContext.evidence_gaps || []).length)) || 0
        );
        const constraintCount = Array.isArray(activeProjectState.axioms && activeProjectState.axioms.derived_constraints)
          ? activeProjectState.axioms.derived_constraints.filter(Boolean).length
          : 0;
        const openParts = [];
        if (activeGapCount) openParts.push(`${activeGapCount} evidence gap${activeGapCount === 1 ? "" : "s"} to close`);
        if (constraintCount) openParts.push(`${constraintCount} constraint${constraintCount === 1 ? "" : "s"} learned`);
        const detailTitle = openParts.length
          ? openParts.join(" · ")
          : "Evidence gaps and run-learned assumptions";
        return [
          h(RunFindings, { key: "run-findings", view: buildRunFindingsView(evalResults, scoreTrajectory), onOpenDetail: navigateWorkspace }),
          h(ScoreTrajectoryPanel, { key: "score-trajectory", trajectory: scoreTrajectory, liveMode }),
          h(RunHistoryPanel, { key: "run-history", runHistory: runHistoryContext, message: runHistoryMessage, liveMode, onPreview: loadFilePreview, onUseActionNote: useActionNote }),
          h(MoreDetail, { key: "results-detail", title: detailTitle, defaultOpen: openParts.length > 0 }, [
            h(ProjectAxiomPanel, { key: "axioms", axiomsState: activeProjectState.axioms, onPreview: loadFilePreview }),
            h(EvidenceSupportPanel, { key: "evidence-support", claimSupport: claimSupportContext, message: claimSupportMessage, evidenceGaps: evidenceGapContext, evidenceGapMessage, evidenceGapDraft, setEvidenceGapDraft, evidenceGapRunning, evidenceGapEvent, evidenceFetchRunning, evidenceFetchEvent, liveMode, onPreview: loadFilePreview, onJustify: justifyEvidenceGapLive, onFetch: requestEvidenceFetchLive, onRefresh: refreshEvidenceSupportLive, onPrepareSource: prepareEvidenceGapSourceDraft })
          ])
        ];
      })(),
      "Fix warnings": [
        h(HealthActionsPanel, { key: "health", healthContext, healthMessage, liveMode, onPreviewSource: loadFilePreview, onUseActionNote: useHealthActionNote }),
        h(MoreDetail, { key: "warning-detail", title: "Command reference" }, h(CommandRail, { key: "command-rail", snapshot, selectedRow }))
      ]
    },
    leanmill: {
      Start: leanMillView("Start", "leanmill-start"),
      "Draft target": leanMillView("Draft target", "leanmill-draft-target"),
      "Run a proof": leanMillView("Run a proof", "leanmill-run-a-proof"),
      "Proof files": leanMillView("Proof files", "leanmill-proof-files"),
      "Proof status": leanMillView("Proof status", "leanmill-proof-status")
    },
    save: {
      // The BlockerPanel "Review points" just re-stated the active issue the verdict panel already
      // shows — a confusing duplicate, removed. The verdict panel is the single source here.
      "Report readiness": [
        h(Verdict, { key: "verdict", view: buildVerdictView(snapshot, reportPanelContext, claimSupportContext, evalResults), onOpenReport: () => navigateWorkspace("save", "Report inputs"), onMakeCard: buildClaimCardLive, onPreview: loadFilePreview, onOpenDetail: navigateWorkspace, onForecast: runForecastScratchLive, forecast: forecastScratch, onExportObsidian: liveMode ? runObsidianExportLive : null, obsidianExport: obsidianExport, onFalsify: liveMode ? runFalsifyLive : null, falsify: falsify })
      ],
      "Report inputs": [
        h(ReportContractPanel, { key: "report", reportContext: reportPanelContext, message: reportContractMessage, running: reportSupportRunning, liveMode, onPreview: loadFilePreview, onRefresh: refreshReportSupportLive, onRerun: requestReportSupportRefreshLive, onRefreshInputs: requestReportSynthesisRefreshLive, onBuildClaimCard: buildClaimCardLive, onRunProjectTest: runProjectTestLive, onOpenDetail: openDetail, onUseActionNote: useActionNote }),
        h(MoreDetail, { key: "report-detail", title: "Backing review points" }, h(ProvenanceStrip, { key: "provenance", rows: snapshot.rows || [] }))
      ],
      "Project file": [projectFilePanel]
    },
    review: {
      "Things to review": [h(OpenPoints, { key: "open-points", view: buildOpenPointsView(evalResults), onOpenDetail: navigateWorkspace, onAddEvidence: () => openModal("sources", "Add file"), onForecast: runForecastScratchLive, forecast: forecastScratch })],
      "Save review": [reviewMessage ? h("div", { className: "review-message", key: "review-message" }, reviewMessage) : null, reviewWorkspacePanel],
      "Save next step": [rowActionPanel],
      "Saved history": [
        h(History, { key: "history", view: buildHistoryView(receiptHistory, scoreTrajectory, runHistoryContext, runHistoryContext && runHistoryContext.compression_progress), liveMode, onPreview: loadFilePreview })
      ]
    },
    projects: {
      "Current project": day0Mode ? [dayZeroPanel] : [],
      Projects: day0Mode
        ? [dayZeroPanel]
        : [
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
      // day0: show the choice cards, OR the focused create form once a choice is picked — never both
      // stacked. The form sits in a centered, dialog-like surface so it reads as a deliberate step.
      "Connect project": day0Mode
        ? projectStartIntent
          ? [h("div", { key: "create-focus", className: "create-focus" }, h("div", { className: "create-focus-card" }, projectCreatePanel))]
          : [dayZeroPanel]
        : [projectCreatePanel],
      Files: [
        h(ProjectFileInventoryPanel, { key: "inventory", inventory: activeProjectState.files || {}, liveMode, onPreview: loadFilePreview, onOpenDetail: openDetail }),
        h(MoreDetail, { key: "files-detail", title: "Server and project context" }, [
          h(ServerStatusPanel, { key: "server-status", status: serverStatus, liveMode, message: serverStatusMessage, onRefresh: refreshServerReadiness }),
          h(ProjectContextPanel, { key: "context", projectEntry: currentProjectEntry, snapshot, liveMode, onPreview: loadFilePreview })
        ])
      ],
      Settings: [
        h(WorkbenchSettingsPanel, {
          key: "settings",
          settings: workbenchSettings,
          draft: settingsDraft,
          setDraft: setSettingsDraft,
          message: settingsMessage,
          saving: settingsSaving,
          liveMode,
          settingsContract: actionContracts.settings || {},
          onSave: saveWorkbenchSettings,
          onRefresh: loadWorkbenchSettings
        })
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
  const detailModalNav = {
    // At the base of the modal history, Back returns to the file viewer we came from (if any).
    canGoBack: detailModalHistoryIndex > 0 || Boolean(editorReturnPath),
    canGoForward: detailModalHistoryIndex >= 0 && detailModalHistoryIndex < detailModalHistory.length - 1,
    onBack: () => {
      if (detailModalHistoryIndex <= 0 && editorReturnPath) {
        setActiveModalKey("");
        const path = editorReturnPath;
        setEditorReturnPath("");
        loadFilePreview({ type: "file", value: path });
        return;
      }
      navigateDetailModalHistory(-1);
    },
    onForward: () => navigateDetailModalHistory(1)
  };
  const fileViewerNav = {
    canGoBack: filePreviewHistoryIndex > 0,
    canGoForward: filePreviewHistoryIndex >= 0 && filePreviewHistoryIndex < filePreviewHistory.length - 1,
    onBack: () => navigateFilePreviewHistory(-1),
    onForward: () => navigateFilePreviewHistory(1)
  };
  const openReviewItem = (label) => {
    if (label) setSelectedLabel(label);
    openDetail("review", "Save review");
  };
  const openInspectItem = (label) => {
    if (label) setSelectedLabel(label);
    openDetail("overview", "Thesis");
  };
  const draftProjectFormalTarget = () => {
    const project = (activeProjectState && activeProjectState.project) || (snapshot && snapshot.project) || "";
    const currentDraft = leanMillBlueprintDraft || emptyLeanMillBlueprintDraft();
    setLeanMillBlueprintDraft({
      ...emptyLeanMillBlueprintDraft(),
      ...currentDraft,
      project,
      title: currentDraft.title || `${displayText(project)} target notes`
    });
    setLeanMillBlueprintEvent(null);
    setLeanMillBlueprintMessage(project ? `Drafting a formal target under projects/${project}/leanmill/.` : "Drafting a formal target.");
    navigateWorkspace("leanmill", "Draft target");
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
    pendingEditorItems,
    liveMode,
    onOpenDetail: openDetail,
    onInspectItem: openInspectItem,
    onPreview: loadFilePreview,
    onDraftFormalTarget: draftProjectFormalTarget,
    onSaveResearchMap: saveResearchMap
  });
  const projectsWorkspace = activeWorkspace === "projects";
  const leanMillWorkspace = activeWorkspace === "leanmill";
  const projectsHome = !day0Mode && projectsWorkspace && activeSubnav === "Current project";
  const topbarClaimRow = rowByLabel((snapshot && snapshot.rows) || [], "Bounded claim");
  const topbarTitle = leanMillWorkspace ? "LeanMill — machine-checked proofs" : day0Mode ? "Start a project" : humanProjectTitle(snapshot, topbarClaimRow);
  return h(
    "main",
    { className: `app-shell ${day0Mode ? "day-zero" : ""}${loadBarActive ? " is-loading" : ""}` },
    loadBarActive
      ? h("div", { className: "app-progress-bar", role: "progressbar", "aria-label": "Loading", "aria-busy": "true" })
      : null,
    h(Sidebar, {
      snapshot,
      counts,
      activeWorkspace,
      activeSubsection: activeSubnav,
      setActiveWorkspace,
      setActiveSubsection,
      projects,
      projectFolders,
      leanMillState: leanMillContext,
      selectedProjectKey,
      liveMode,
      loadingSnapshot,
      day0Mode,
      onSelectProject: openProject,
      onOpenProjects: () => {
        if (day0Mode) setDayZero(false);
        else navigateWorkspace("projects", "Projects");
      },
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
          h("span", { className: "eyebrow" }, leanMillWorkspace ? "LeanMill" : "Project Workbench"),
          h("h1", null, topbarTitle),
          leanMillWorkspace
            ? h("p", { className: "topbar-day-zero" }, "Formalize and solve a statement, rescue a failing proof, or kernel-ratify a finished one — for math and non-math targets alike.")
            : day0Mode
            ? h("p", { className: "topbar-day-zero" }, "Create a project from a question, raw files, or an existing folder. The full project list is hidden until you ask for it.")
            : h(ProjectIdentity, { snapshot })
        ),
        h(
          "div",
          { className: "topbar-actions" },
          liveMode && leanMillWorkspace
            ? h(
                "button",
                {
                  type: "button",
                  className: "snapshot-link",
                  onClick: () => navigateWorkspace("projects", "Projects"),
                  title: "Go to ZTARE projects"
                },
                "ZTARE Projects"
              )
            : null,
          liveMode && !leanMillWorkspace
            ? h(
                "button",
                {
                  type: "button",
                  className: "snapshot-link mobile-project-picker",
                  onClick: () => day0Mode ? setDayZero(false) : navigateWorkspace("projects", "Projects"),
                  disabled: loadingSnapshot,
                  title: day0Mode ? "Show the full project inventory" : loadingSnapshot ? "Refreshing project list" : "Open the full project inventory"
                },
                day0Mode ? "Show projects" : loadingSnapshot ? "Refreshing projects" : "Projects"
              )
            : null,
          liveMode && !day0Mode && !leanMillWorkspace
            ? h(
                "button",
                {
                  type: "button",
                  className: "snapshot-link",
                  onClick: () => setDayZero(true),
                  title: "Open the clean project-start screen"
                },
                "New project"
              )
            : null,
          liveMode
            ? h(
                "button",
                {
                  type: "button",
                  className: "snapshot-link",
                  onClick: leanMillWorkspace ? loadLeanMillContext : refreshCurrentProject,
                  disabled: loadingSnapshot,
                  title: leanMillWorkspace ? "Refresh LeanMill files and history" : "Refresh from local project files"
                },
                loadingSnapshot ? "Refreshing" : "Refresh"
              )
            : null
        )
      ),
      runStatus && runStatus.active
        ? h(
            "div",
            { className: "run-progress-banner", "aria-label": "Run in progress" },
            h("span", { className: "run-progress-dot", "aria-hidden": "true" }),
            h(
              "div",
              { className: "run-progress-copy" },
              h(
                "strong",
                null,
                runStatus.iteration_budget
                  ? `Pressure-testing the thesis — iteration ${runStatus.iteration} of ${runStatus.iteration_budget}`
                  : `Pressure-testing the thesis — iteration ${runStatus.iteration || runStatus.iteration_count || 1}`
              ),
              h(
                "small",
                null,
                [
                  (typeof runStatus.latest_score === "number") ? `best so far ${runStatus.latest_score}` : "",
                  runStatus.mutator_model ? `mutator ${displayText(runStatus.mutator_model)}` : "",
                  runStatus.judge_model ? `judge ${displayText(runStatus.judge_model)}` : ""
                ].filter(Boolean).join(" · ")
              )
            )
          )
        : null,
      modeMessage ? h("div", { className: `mode-banner ${liveMode ? "live" : "offline"}` }, modeMessage) : null,
      actionMessage ? h("div", { className: `mode-banner ${liveMode ? "live" : "offline"}` }, actionMessage) : null,
      h(PendingEditsStrip, { items: pendingEditorItems, onOpenDetail: openDetail }),
      h(
        "section",
        { className: `workspace-view ${activeWorkspace}${loadingSnapshot ? " is-loading" : ""}`, "aria-label": "Active project area", "aria-busy": loadingSnapshot ? "true" : undefined },
        projectsHome ? projectHomeSummary : null,
        projectsHome
          ? h(MoreDetail, { title: "Switch project" }, projectSwitchPanel)
          : null,
        projectsHome || projectsWorkspace || leanMillWorkspace
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
        activeWorkspacePanels.length
          ? h(
              "section",
              { className: "active-workspace-panels", "aria-label": `${activeSection.label} ${activeSubnav}` },
              activeWorkspacePanels
            )
          : null,
        loadingSnapshot
          ? h(
              "div",
              { className: "workspace-loading-overlay", role: "status", "aria-live": "polite" },
              h(
                "div",
                { className: "workspace-loading-card" },
                h("span", { className: "workspace-loading-spinner", "aria-hidden": "true" }),
                h("span", null, "Loading…")
              )
            )
          : null
      )
    ),
    h(ModalShell, { detail: activeModal, modalKey: activeModalKey, onClose: closeActiveModal, modalNav: detailModalNav }),
    h(FileViewerModal, {
      filePreview,
      message: filePreviewMessage,
      open: filePreviewOpen,
      onClose: closeFilePreview,
      onPreview: loadFilePreview,
      editTarget: fileViewerEditTarget,
      onOpenEditor: openFileEditorFromViewer,
      modalNav: fileViewerNav
    }),
    h(ProjectRunConfirmDialog, { prompt: projectRunPrompt, onCancel: cancelProjectRunPrompt, onConfirm: runBoundedLive }),
    h(ProjectRunConfirmDialog, { prompt: sourceActionPrompt, onCancel: cancelSourceActionPrompt, onConfirm: runConfirmedSourceActionLive }),
    h(ProjectRunConfirmDialog, { prompt: evidenceFetchPrompt, onCancel: cancelEvidenceFetchPrompt, onConfirm: runConfirmedEvidenceFetchLive }),
    h(ProjectRunConfirmDialog, { prompt: reportSupportPrompt, onCancel: cancelReportSupportPrompt, onConfirm: runConfirmedReportSupportRefreshLive }),
    h(ProjectRunConfirmDialog, { prompt: reportSynthesisPrompt, onCancel: cancelReportSynthesisPrompt, onConfirm: runConfirmedReportSynthesisRefreshLive }),
    h(UnsavedChangesDialog, { prompt: discardPrompt, onCancel: cancelDiscardPrompt, onDiscard: confirmDiscardPrompt })
  );
}

createRoot(document.getElementById("root")).render(
  h(
    MantineProvider,
    { theme: workbenchTheme, forceColorScheme: "light" },
    h(WorkbenchErrorBoundary, null, h(App))
  )
);





