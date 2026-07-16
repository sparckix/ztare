import React from "react";

const h = React.createElement;

const DISPLAY_OVERRIDES = {
  valid_packet: "valid project brief",
  missing_packet: "missing evidence file",
  ready_for_in_loop_candidate: "ready for run",
  ready_for_evidence_prepare: "ready for evidence prep",
  report_blockers_present: "report not ready",
  report_support_unavailable: "report readiness unavailable",
  synthesis_input_binding_unbound: "report input is not connected",
  runtime_risks_present: "caveats on how this ran",
  loop_admission: "run saved work",
  "loop admission preflight path": "pre-run history path",
  "Loop admission": "Pre-run check",
  "Bounded claim": "Your claim",
  "Non-claims": "What you've ruled out",
  "Project intake": "Project brief",
  "Assumptions and constraints": "Assumptions and constraints",
  "Source readiness": "File status",
  "Evidence readiness": "Evidence summary",
  "Run readiness": "Ready to test",
  "Next falsifier": "What would change your mind",
  "Latest saved review": "Latest review",
  "Latest review receipt": "Latest review",
  "Latest intake edit": "Latest project brief change",
  "Report support": "Verdict check",
  "Report/export": "Verdict check",
  report_export: "Verdict check",
  report_support: "Verdict check",
  "Report readiness": "Verdict check",
  "Report readiness check": "Verdict check",
  "report readiness check": "Verdict check",
  Preflight: "Pre-run check",
  "Preflight receipt": "Pre-run check",
  preflight: "pre-run check",
  "Check readiness": "Check it's ready",
  "Readiness check": "Pre-run check",
  "Readiness history": "Pre-run history",
  "Run readiness check": "Pre-run check",
  receipt: "saved work",
  receipts: "saved history",
  "Receipt": "Saved work",
  "Receipts": "Saved history",
  "Receipt ledger": "Saved history",
  blocked: "not ready",
  weak: "thinly backed",
  missing: "missing",
  stale: "out of date",
  stale_or_invalid: "out of date",
  pending: "not run yet",
  degrading: "weakening",
  partial_trace: "only partly tested",
  needs_support: "not fully backed",
  ready_for_bounded_run: "ready to test",
  ready_for_in_loop_candidate: "ready to test",
  "Latest item action": "Latest next step",
  "latest item action": "latest next step",
  item_action: "saved next step",
  latest_item_action: "latest saved next step",
  row_action: "saved next step",
  latest_row_action: "latest saved next step",
  no_action_saved: "no next step saved",
  no_intake_edit_saved: "no saved project-brief change",
  next_step: "next step",
  needs_source: "needs source",
  ready_to_run: "ready to run",
  export_blocker: "fix report readiness",
  public_example_intake: "example project brief",
  project_local_intake: "project brief",
  project_compiled_evidence: "project evidence file",
  project_run_history: "project run history",
  project_report_support: "project report readiness",
  unknown_intake_source: "project brief source unknown",
  carrier_chain: "run evidence chain",
  graph_carriers: "graph summaries",
  kernel_entry: "run readiness",
  weak_gp233_linkage: "evidence links need repair",
  stale_trajectory_output: "run-history archive is stale",
  unconsumed_surface: "work log is missing",
  repair_source_emitter: "repair source logs",
  attention: "needs a look",
  not_loaded: "not loaded yet",
  none_loaded: "nothing yet",
  not_checked: "not checked yet",
  needs_review: "needs your review",
  project_object: "project state",
  project_object_contract: "project state",
  loop_admission_receipt: "saved readiness check",
  kernel_entry_contract: "run readiness",
  bounded_run: "project run",
  in_loop_candidate: "ready to run",
  evidence_prepare: "compile evidence",
  source_preflight: "file check",
  non_claims: "what you've ruled out",
  next_falsifier: "what would change your mind",
  bounded_claim: "your claim",
  project_intake: "project brief"
};

export function displayText(value) {
  const raw = String(value || "none");
  return (DISPLAY_OVERRIDES[raw] || raw)
    .replace(/_/g, " ")
    .replace(/^Reject or demote the claim if\s+/i, "Revise the thesis if ")
    .replace(/report[\s_-]*readiness is current/gi, "The verdict matches your current files")
    .replace(/\breport[\s_-]*readiness check\b/gi, (m) => (m[0] === "R" ? "Verdict check" : "verdict check"))
    .replace(/\breport[\s_-]*readiness\b/gi, (m) => (m[0] === "R" ? "Verdict check" : "verdict check"))
    .replace(/\bsource-health\b/gi, "file/evidence warning")
    .replace(/\breport-support\b/gi, "the verdict")
    .replace(/\bsupport-contract\b/gi, "backing")
    .replace(/\bgating test\b/gi, "decisive test")
    .replace(/\baction-intelligence\b/gi, "guidance")
    .replace(/\bcommand previews\b/gi, "commands")
    .replace(/\bcommand preview\b/gi, "command")
    .replace(/\bkernel\b/gi, "run")
    .replace(/\bcarrier chain\b/gi, "run evidence chain")
    .replace(/\bgraph carriers\b/gi, "graph summaries")
    .replace(/\bGP-?233\b/gi, "evidence ledger")
    .replace(/\bGP-?230\b/gi, "forecast record")
    .replace(/\bGP-(\d+)\b/g, "research record GP-$1")
    .replace(/\bcheck readiness\b/gi, (m) => (m[0] === "C" ? "Check it's ready" : "check it's ready"))
    .replace(/\breadiness check\b/gi, (m) => (m[0] === "R" ? "Pre-run check" : "pre-run check"))
    .replace(/\bpreflight\b/gi, "pre-run check")
    .replace(/\bprobability dag\b/gi, "probability model")
    .replace(/\bloop admission\b/gi, "readiness check")
    .replace(/\bkernel entry\b/gi, "run readiness")
    .replace(/\bbounded run\b/gi, "project run")
    .replace(/\bintake declared run\b/gi, "project brief asks for a run")
    .replace(/\btrace health\b/gi, "run-log health")
    .replace(/\brepair surfaces\b/gi, "fix missing inputs")
    .replace(/\bthes(i|e)s\b/gi, (m) => (m[0] === "T" ? "Claim" : "claim"))
    .replace(/\bartifact surface\b/gi, "output file")
    .replace(/\brubric\b/gi, "scoring guide")
    .replace(/\bevaluator\b/gi, "scorer")
    .replace(/\bintake\b/gi, "project brief");
}

export function displayMessage(value) {
  return String(value || "")
    .replace(/report[\s_-]*readiness is current/gi, "The verdict matches your current files")
    .replace(/\breport[\s_-]*readiness check\b/gi, (m) => (m[0] === "R" ? "Verdict check" : "verdict check"))
    .replace(/\breport[\s_-]*readiness\b/gi, (m) => (m[0] === "R" ? "Verdict check" : "verdict check"))
    .replace(/report support[\s_-]+contract missing/gi, "The report makes a claim your files don't back yet")
    .replace(/support[\s_-]+contract/gi, "backing")
    .replace(/\bset to hold\b/gi, "holding the verdict back")
    .replace(/\bhold report\b/gi, "hold the verdict back")
    .replace(/\bthes(i|e)s\b/gi, (m) => (m[0] === "T" ? "Claim" : "claim"))
    .replace(/\bwithout (?:the )?mutator (?:or|and) judge model calls\b/gi, "without using any paid models")
    .replace(/\bmutator (?:or|and) judge model calls\b/gi, "paid model calls")
    .replace(/\bjudge model calls\b/gi, "scoring-model calls")
    .replace(/\bartifact surface\b/gi, "output file")
    .replace(/\brubric\b/gi, "scoring guide")
    .replace(/\bevaluator\b/gi, "scorer")
    .replace(/\bReport\/export\b/g, "Verdict check")
    .replace(/\bready_for_run=True\b/g, "ready for run: yes")
    .replace(/\bready_for_run=False\b/g, "ready for run: no")
    .replace(/\bready_for_in_loop_candidate\b/g, "ready for run")
    .replace(/\bready_for_evidence_prepare\b/g, "ready for evidence prep")
    .replace(/\bintake_hash_verified=True\b/g, "intake hash verified: yes")
    .replace(/\bintake_hash_verified=False\b/g, "intake hash verified: no")
    .replace(/\breceipt_count=/g, "saved changes: ")
    .replace(/\breceipt paths\b/gi, "saved-history paths")
    .replace(/\breceipt path\b/gi, "saved-history path")
    .replace(/\breceipts\b/gi, "saved history")
    .replace(/\breceipt\b/gi, "saved work")
    .replace(/\beval_history_rows=/g, "run records: ")
    .replace(/\blatest_exit=/g, "latest exit: ")
    .replace(/\bsource_index=/g, "file index: ")
    .replace(/\bsource index:/gi, "file index:")
    .replace(/\boutput_binding=/g, "evidence connection: ")
    .replace(/\boutput binding:/gi, "evidence connection:")
    .replace(/\breplay=/g, "replay: ")
    .replace(/\breadiness=/g, "readiness: ")
    .replace(/\bevidence_refs\[(\d+)\]/g, "evidence summary $1")
    .replace(/\bevidence_refs=/g, "evidence summaries: ")
    .replace(/\bevidence refs\b/gi, "evidence summaries")
    .replace(/\bsource refs\b/gi, "original files")
    .replace(/Run the model-free launch preflight to verify local setup\.?/gi, "Run the pre-run check to verify setup.")
    .replace(/Run the model-free launch preflight\.?:/gi, "Run the pre-run check:")
    .replace(/Run the model-free launch preflight\b/gi, "Run the pre-run check")
    .replace(/Run the local preflight before starting a project run\./gi, "Run the pre-run check before starting a project run.")
    .replace(/\bpreflight receipts\b/gi, "pre-run history")
    .replace(/\bPreflight receipt\b/g, "Pre-run check")
    .replace(/\bRun preflight\b/gi, "Check it's ready")
    .replace(/\bPreflight\b/g, "Pre-run check")
    .replace(/\bpreflight\b/g, "pre-run check")
    .replace(/\bcheck readiness\b/gi, (m) => (m[0] === "C" ? "Check it's ready" : "check it's ready"))
    .replace(/\breadiness check\b/gi, (m) => (m[0] === "R" ? "Pre-run check" : "pre-run check"))
    .replace(/\bsha256=/g, "hash: ")
    .replace(/;\s*hash\s+[a-f0-9]{16,}/gi, "")
    .replace(/\bhash\s+[a-f0-9]{16,}/gi, "file fingerprint recorded")
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
    .replace(/\bpacket boundary\b/gi, "project-brief boundary")
    .replace(/\bsource-health\b/gi, "file/evidence warning")
    .replace(/\breport-support\b/gi, "report readiness")
    .replace(/\bsupport-contract\b/gi, "readiness file")
    .replace(/\baction-intelligence\b/gi, "guidance")
    .replace(/\bkernel\b/gi, "run")
    .replace(/\bcarrier chain\b/gi, "run evidence chain")
    .replace(/\bgraph carriers\b/gi, "graph summaries");
}

// Plain-language teaching glossary. Every concept a non-expert user can hit on the
// surface gets one calm sentence — what it is, in their terms, not the kernel's.
export const GLOSSARY = {
  claim: "The thing you're arguing is true — stated tightly enough to be tested.",
  evidence: "The files and facts that back your claim — or weaken it.",
  source: "An original file you brought in: a log, a doc, a dataset.",
  "pressure-test": "Running your claim against its weakest points to see if it survives.",
  run: "One pass of the analysis: it reads your evidence and stress-tests the claim.",
  verdict: "Whether the evidence lets you trust the claim, and how strongly.",
  "weak spot": "A place where the claim isn't fully backed by your evidence.",
  "what would change your mind": "The one finding that would force you to drop or rewrite the claim.",
  "ruled out": "Alternative explanations you checked and set aside, with why.",
  readiness: "Whether the project has enough in place to run a useful test yet.",
  "evidence gap": "Something the claim leans on that you haven't backed with a file yet.",
  caveat: "A limit on how far you should trust the result, given how it was produced.",
  "source claim graph": "A map of how your sources connect to the claim — what supports or undercuts what.",
  "probability model": "A forecast the run built from your evidence, with how confident it is.",
  "evidence provenance": "The record of where each piece of evidence came from.",
  "file-index history": "The log of when your files were indexed and checked.",
  "graph source": "A working file the run built while mapping how your sources relate.",
  thesis: "Your main claim — what you're arguing is true.",
  assumption: "Something taken as true without proof, that your claim leans on.",
  assumptions: "Things taken as true without proof, that your claim leans on.",
  constraint: "A limit or boundary your claim has to respect.",
  constraints: "Limits or boundaries your claim has to respect.",
  "confirmed constraint": "A limit the run checked against your evidence — it holds.",
  "provisional constraint": "A limit the run assumed but hasn't verified yet — treat it as tentative.",
  confirmed: "Checked against your evidence — you can rely on it.",
  provisional: "Assumed but not verified yet — tentative.",
  "supported point": "A part of the claim your evidence backs up.",
  tension: "A place where the evidence pushes against your claim.",
  tensions: "Places where the evidence pushes against your claim.",
  branch: "An alternative explanation worth testing.",
  demotion: "When the run weakens a claim because the evidence doesn't fully hold it.",
  "weakest point": "The part of the claim least backed by evidence — where it's most likely to break.",
};

// Auto-teaching: wrap any known concept appearing in plain text with a Term affordance,
// so explanations show up everywhere without hand-placing each one.
const GLOSSARY_KEYS = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);
const GLOSSARY_RE = new RegExp(
  `\\b(${GLOSSARY_KEYS.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`,
  "gi"
);

export function Teach({ text, children }) {
  const str = String(text != null ? text : children || "");
  if (!str) return children != null ? children : null;
  GLOSSARY_RE.lastIndex = 0;
  const parts = [];
  let last = 0;
  let match;
  let i = 0;
  while ((match = GLOSSARY_RE.exec(str)) !== null) {
    if (match.index > last) parts.push(str.slice(last, match.index));
    parts.push(h(Term, { key: `t${i++}`, term: match[0].toLowerCase() }, match[0]));
    last = match.index + match[0].length;
    if (GLOSSARY_RE.lastIndex === match.index) GLOSSARY_RE.lastIndex++;
  }
  if (last < str.length) parts.push(str.slice(last));
  return h(React.Fragment, null, ...parts);
}

// A word with a quiet "what's this?" affordance — dotted underline + plain definition.
// ponytail: native title tooltip, no tooltip library.
export function Term({ term, children }) {
  const key = String(term || children || "").toLowerCase();
  const def = GLOSSARY[key];
  if (!def) return children || term || null;
  return h("span", { className: "term", title: def, tabIndex: 0, role: "note" }, children || term);
}

// One status vocabulary, one set of colors. Map any raw kernel status to a human
// phrase + a tone (ok / warn / bad / neutral). Never show "attention" / "blocked" raw.
export function statusMeaning(status) {
  const s = String(status || "").toLowerCase();
  if (!s || /loading|unknown|not loaded|^—$|none/.test(s)) return { label: "loading…", tone: "neutral" };
  if (/refut|contradict|reject|\bfail(?:ed|ure)?\b|invalid|\berror\b/.test(s)) return { label: "does not hold", tone: "bad" };
  if (/block|missing|unbound|not ready|attention|weak|needs|partial|stale|pending|gap|degrading|support|advisory|review/.test(s)) return { label: "needs a look", tone: "warn" };
  if (/ready|fresh|\bok\b|connected|current|done|accepted|strong|solid|complete|pass/.test(s)) return { label: "ready", tone: "ok" };
  return { label: displayText(status), tone: "neutral" };
}

// A calm status pill: a colored dot + the plain word (Linear/Mercury pattern).
export function StatusDot({ status, label }) {
  const m = statusMeaning(status);
  return h(
    "span",
    { className: `status-dot status-dot-${m.tone}` },
    h("span", { className: "status-dot-mark", "aria-hidden": "true" }),
    h("span", null, label || m.label)
  );
}

export function repoPathCandidate(value) {
  return String(value || "").trim().split("#")[0].trim();
}

export function isPreviewableRepoPath(value) {
  const raw = repoPathCandidate(value);
  if (!raw || raw.startsWith("/") || raw.includes("..")) return false;
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(raw)) return false;
  if (/[\r\n]/.test(raw)) return false;
  if (/[<>|{}]/.test(raw)) return false;
  const pathLike = raw.includes("/") || /^[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+$/.test(raw);
  if (!pathLike) return false;
  return true;
}

export function previewableRepoPath(value) {
  const path = repoPathCandidate(value);
  return isPreviewableRepoPath(path) ? path : "";
}

export function previewFileTitle(liveMode, previewable, readyTitle = "Preview the saved file") {
  if (!liveMode) return "Start the workbench server to preview files";
  if (!previewable) return "Saved file is not a repository file";
  return readyTitle;
}

export function writePathLabel(path) {
  const text = String(path || "");
  if (!text) return "Project file path";
  if (text.endsWith("/project_charter.md")) return "Project charter";
  if (text.includes("_intake.json") || /\/[^/]+_intake\.json$/.test(text)) return "Project brief";
  if (text.includes("/raw/source_type_map.json")) return "Source role map";
  if (text.includes("/raw/")) return "Source file";
  if (text.includes("source_index_receipt")) return "File-index history";
  if (text.includes("source_index.json")) return "File index";
  if (text.includes("workspace_meta.json")) return "Workspace metadata";
  if (text.includes("evidence_output_binding_receipt")) return "Evidence connection history";
  if (text.includes("iteration_telemetry")) return "Run telemetry";
  if (text.includes("latest_eval_results")) return "Latest run result";
  if (text.includes("eval_results")) return "Run result history";
  if (text.includes("forensic_workbench_applied") && text.includes("_review_")) return "Review handoff file";
  if (text.includes("forensic_workbench_reviews")) return "Review ledger";
  if (text.includes("forensic_workbench_latest_review")) return "Latest review";
  if (text.includes("forensic_workbench_applied") && text.includes("_action_")) return "Next-step handoff file";
  if (text.includes("forensic_workbench_row_actions")) return "Next-step ledger";
  if (text.includes("forensic_workbench_latest_row_action")) return "Latest next step";
  if (text.includes("forensic_workbench_intake_edits")) return "Project-brief edit ledger";
  if (text.includes("forensic_workbench_latest_intake_edit")) return "Latest project-brief change";
  if (text.includes("forensic_workbench_source_imports")) return "Added-file history";
  if (text.includes("forensic_workbench_latest_source_import")) return "Latest added-file record";
  if (text.includes("forensic_workbench_source_edits")) return "Edited-file history";
  if (text.includes("forensic_workbench_latest_source_edit")) return "Latest edited-file record";
  if (text.includes("forensic_workbench_source_actions")) return "File-check ledger";
  if (text.includes("forensic_workbench_latest_source_action")) return "Latest file check";
  if (text.includes("forensic_workbench_project_file_") || text.includes("forensic_workbench_case_file_")) return "Project file";
  if (text.includes("forensic_workbench_project_files") || text.includes("forensic_workbench_case_files")) return "Project-file ledger";
  if (text.includes("forensic_workbench_latest_project_file_write") || text.includes("forensic_workbench_latest_case_file_write")) return "Latest project file";
  if (/^projects\/[^/]+\/workspace$/.test(text)) return "Workspace folder";
  if (/^projects\/[^/]+\/raw$/.test(text)) return "Project folder";
  if (/^projects\/[^/]+$/.test(text)) return "Project folder";
  return "Project file path";
}

export function PendingPathPreview({ label, paths, emptyText, ready = false }) {
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

export function pendingPathPreview(label, paths, emptyText, ready = false) {
  return h(PendingPathPreview, { label, paths, emptyText, ready });
}

export function WriteBoundary({ writeLabel, readLabel, liveMode }) {
  const noChangeText = liveMode
    ? "Preview, cancel, validation failure, and refused confirmation write no files."
    : "Offline mode cannot write project files.";
  return h(
    "div",
    { className: `write-boundary ${liveMode ? "live" : "offline"}`, "aria-label": "Files that can change" },
    h(
      "div",
      { className: "write-boundary-item writes" },
      h("span", null, "Files"),
      h("strong", null, writeLabel),
      h("p", null, liveMode ? "Only the listed project paths can change." : "Project files cannot change.")
    ),
    h(
      "div",
      { className: "write-boundary-item readonly" },
      h("span", null, "Preview only"),
      h("strong", null, readLabel),
      h("p", null, "Preview, copy, and download do not write project files.")
    ),
    h(
      "div",
      { className: "write-boundary-item readonly" },
      h("span", null, "Why files might not change"),
      h("strong", null, noChangeText),
      h("p", null, "Accepted writes can change only the listed paths.")
    )
  );
}

// ─── Layout & typography kit ─────────────────────────────────────────────────
// The shared primitives every section composes from, so hierarchy, spacing, and the type scale are
// uniform — never per-section bespoke CSS. Grounded in Linear/Notion/Mercury (see the design brief).

// A titled subsection: a real subhead + an optional lead, hairline-separated with generous rhythm.
// THE anti-wall-of-text primitive — wrap each part of a section in one of these.
export function Block({ id, title, lead, actions, tone, className, children }) {
  return h(
    "section",
    { id, className: `ds-block ${tone || ""} ${className || ""}`.trim() },
    title || actions
      ? h(
          "div",
          { className: "ds-block-head" },
          title ? h("h3", { className: "ds-block-title" }, title) : h("span", null),
          actions || null
        )
      : null,
    lead ? h("p", { className: "ds-block-lead" }, lead) : null,
    children
  );
}

// Page and major-section heading. Keeps the primary job, supporting sentence, and actions aligned
// without each surface inventing its own type scale or responsive collapse.
export function SectionHeader({ eyebrow, title, description, actions, className, as = "h2" }) {
  return h("header", { className: `ds-section-head ${className || ""}`.trim() },
    h("div", { className: "ds-section-head-copy" },
      eyebrow ? h("span", { className: "eyebrow" }, eyebrow) : null,
      title ? h(as, null, title) : null,
      description ? h("p", null, description) : null),
    actions ? h("div", { className: "ds-section-actions" }, actions) : null);
}

export function ActionButton({ variant = "secondary", icon, busy = false, className, children, ...props }) {
  return h("button", { type: "button", "aria-busy": busy ? "true" : undefined, ...props,
    className: `ds-button ${variant}${busy ? " is-busy" : ""} ${className || ""}`.trim() }, icon || null, children);
}

export function IconButton({ label, busy = false, className, children, ...props }) {
  return h("button", { type: "button", title: label, "aria-label": label,
    "aria-busy": busy ? "true" : undefined, "data-busy": busy ? "true" : undefined, ...props,
    className: `ds-icon-button ${className || ""}`.trim() }, children);
}

export function SegmentedControl({ label, value, options, onChange, className }) {
  return h("div", { className: `ds-segmented ${className || ""}`.trim(), role: "tablist", "aria-label": label },
    (options || []).map((option) => h("button", { key: option.value, type: "button", role: "tab",
      "aria-selected": value === option.value, className: value === option.value ? "active" : "",
      onClick: () => onChange && onChange(option.value) }, option.label)));
}

// Scenario panels are the plugin contract at the visual layer. Plugins supply
// nouns and composition; these primitives supply the spacing, responsive grid,
// callout, list, and action affordances from the shared token system.
export function ScenarioSurface({ tone = "soft", className, children }) {
  return h("div", { className: `scenario-surface ${tone} ${className || ""}`.trim() }, children);
}

export function ScenarioGrid({ className, children }) {
  return h("div", { className: `scenario-grid ${className || ""}`.trim() }, children);
}

export function ScenarioColumn({ eyebrow, title, description, actions, className, children }) {
  return h("div", { className: `scenario-column ${className || ""}`.trim() },
    eyebrow ? h("span", { className: "eyebrow" }, eyebrow) : null,
    title ? h("strong", { className: "scenario-column-title" }, title) : null,
    description ? h("small", { className: "scenario-column-description" }, description) : null,
    children,
    actions ? h("div", { className: "scenario-column-actions" }, actions) : null);
}

export function ScenarioList({ className, children }) {
  return h("ul", { className: `scenario-list ${className || ""}`.trim() }, children);
}

export function ScenarioListItem({ className, children }) {
  return h("li", { className: `scenario-list-item ${className || ""}`.trim() }, children);
}

// A bordered card — the container for a discrete finding/item (a red-team attempt, a claim, a gap).
export function Card({ label, title, tone, className, children }) {
  return h(
    "article",
    { className: `ds-card ${tone || ""} ${className || ""}`.trim() },
    label ? h("span", { className: "ds-card-label" }, label) : null,
    title ? h("strong", { className: "ds-card-title" }, title) : null,
    children
  );
}

// A small uppercase tag/pill — tones: neutral | accent | ok | warn | danger.
export function Tag({ tone, children }) {
  return h("span", { className: `ds-tag ${tone || "neutral"}` }, children);
}

// A labeled fact row: a tag on the left, the value after it. For "Killed if", "Holds if", facts, etc.
export function MetaRow({ label, tone, children }) {
  return h(
    "p",
    { className: `ds-row ${tone || ""}`.trim() },
    label ? h("span", { className: `ds-tag ${tone || "neutral"}` }, label) : null,
    h("span", { className: "ds-row-value" }, children)
  );
}

// A labeled fact row: plain label left (--subtle), value right (--ink, tabular) — Mercury's account-row
// pattern. For any label→value set that isn't a status/tag (use MetaRow for those).
export function FactRow({ label, children }) {
  return h(
    "div",
    { className: "ds-fact" },
    h("span", { className: "ds-fact-label" }, label),
    h("span", { className: "ds-fact-value" }, children)
  );
}

// A single coloured status WORD (never a pill — brief law 2). tone: ok | warn | danger | neutral.
export function StatusLine({ tone, children }) {
  return h("strong", { className: `ds-status ds-status-${tone || "neutral"}` }, children);
}

// One calm sentence + one primary action. The ONE empty-state primitive — replaces every bespoke
// wall-of-zeros / "nothing here" renderer with a single guard every section can reuse.
export function EmptyState({ text, action }) {
  return h("div", { className: "ds-empty" }, h("p", null, text), action || null);
}

// A lead sentence + body split — for long statements that should read as a titled card, not a wall.
// Splits on the first sentence; pass an explicit lead to override.
export function Lead({ lead, text }) {
  const full = String(text || "");
  let head = lead || full;
  let rest = "";
  if (!lead) {
    const m = full.match(/^(.*?[.!?])\s+([\s\S]+)$/);
    if (m) { head = m[1]; rest = m[2]; }
  } else {
    rest = full;
  }
  return h(
    "div",
    { className: "ds-lead" },
    h("strong", { className: "ds-lead-head" }, head),
    rest ? h("p", { className: "ds-lead-body" }, rest) : null
  );
}
