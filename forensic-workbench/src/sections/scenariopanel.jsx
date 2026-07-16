import React from "react";
import { AlertTriangle, Check, FileSearch, RefreshCw, Search, Sparkles } from "lucide-react";
import { displayText, StatusLine } from "../design-system.js";

const h = React.createElement;

const STATUS = {
  BACKED: {
    label: "Backed",
    tone: "ok",
    explanation: "This passage matches a project claim with checked evidence behind it.",
    next: "Keep the scope and qualifiers intact when you edit this passage.",
  },
  CONTRADICTED: {
    label: "Contradicted",
    tone: "danger",
    explanation: "The project evidence conflicts with the claim made in this passage.",
    next: "Revise the claim or resolve the conflicting evidence before relying on it.",
  },
  UNTESTED: {
    label: "Untested assumption",
    tone: "warn",
    explanation: "The argument depends on this claim, but the project has not tested it yet.",
    next: "Add evidence or turn this assumption into the next discriminating test.",
  },
  INERT: {
    label: "No match",
    tone: "neutral",
    explanation: "No governed claim was matched. The surfacer can miss claims, so this remains unknown.",
    next: "Review this passage manually if it carries an important claim.",
  },
};

const FOCUS_OPTIONS = [
  { id: "all", label: "All passages", matches: () => true },
  { id: "attention", label: "Needs review", matches: (a) => a.status === "UNTESTED" || a.status === "CONTRADICTED" },
  { id: "backed", label: "Backed", matches: (a) => a.status === "BACKED" },
  { id: "unmatched", label: "Unmatched", matches: (a) => a.status === "INERT" },
];

function focusOption(id) {
  return FOCUS_OPTIONS.find((option) => option.id === id) || FOCUS_OPTIONS[0];
}

function statusCount(annotations, id) {
  const option = focusOption(id);
  return annotations.filter(option.matches).length;
}

function AnnotationSummary({ result, onEdit }) {
  const counts = result.counts || {};
  const needsReview = (counts.UNTESTED || 0) + (counts.CONTRADICTED || 0);
  const matched = (counts.BACKED || 0) + needsReview;
  const unmatched = counts.INERT || 0;
  const headline = needsReview
    ? `${needsReview} passage${needsReview === 1 ? "" : "s"} need review`
    : !matched && unmatched
      ? "No project claims matched this draft"
      : unmatched
        ? "Matched passages are backed"
        : matched
          ? "Every passage matched and is backed"
          : "No claim-bearing passages surfaced";
  return h(
    "header",
    { className: "draft-check-summary" },
    h(
      "div",
      { className: "draft-check-summary-copy" },
      h("span", { className: "eyebrow" }, "How this document maps to the project"),
      h(
        "h3",
        null,
        headline
      ),
      h(
        "p",
        null,
        `${counts.BACKED || 0} backed · ${counts.UNTESTED || 0} untested · ${counts.CONTRADICTED || 0} contradicted · ${counts.INERT || 0} unmatched`
      )
    ),
    h(
      "button",
      { type: "button", className: "chip", onClick: onEdit },
      h(FileSearch, { size: 15, "aria-hidden": "true" }),
      "Change draft"
    )
  );
}

function AnnotationInspector({ annotation, index }) {
  if (!annotation) return null;
  const meta = STATUS[annotation.status] || STATUS.INERT;
  return h(
    "aside",
    { className: `draft-inspector status-${String(annotation.status || "INERT").toLowerCase()}`, "aria-live": "polite" },
    h("span", { className: "eyebrow" }, `Passage ${index + 1}`),
    h(StatusLine, { tone: meta.tone }, meta.label),
    h("p", { className: "draft-inspector-explanation" }, meta.explanation),
    h(
      "dl",
      { className: "draft-inspector-facts" },
      h("div", null,
        h("dt", null, "Matched project claim"),
        h("dd", null,
          annotation.element_text
            ? h(React.Fragment, null,
                h("span", null, displayText(annotation.element_text)),
                annotation.element_id
                  ? h("small", { className: "draft-inspector-id" },
                      displayText(annotation.element_kind || "claim"), " · ", h("code", null, annotation.element_id))
                  : null)
            : "No matched claim")),
      h("div", null,
        h("dt", null, "Next move"),
        h("dd", null, meta.next))
    ),
    h("blockquote", null, String(annotation.sentence || ""))
  );
}

function AnnotationResult({ result, onEdit }) {
  const annotations = Array.isArray(result.annotations) ? result.annotations : [];
  const allUnmatched = Boolean(annotations.length && annotations.every((annotation) => annotation.status === "INERT"));
  const firstAttention = Math.max(0, annotations.findIndex((a) => a.status === "CONTRADICTED" || a.status === "UNTESTED"));
  const [selectedIndex, setSelectedIndex] = React.useState(firstAttention);
  const [focus, setFocus] = React.useState(statusCount(annotations, "attention") ? "attention" : "all");

  React.useEffect(() => {
    const nextAttention = annotations.findIndex((a) => a.status === "CONTRADICTED" || a.status === "UNTESTED");
    setSelectedIndex(Math.max(0, nextAttention));
    setFocus(nextAttention >= 0 ? "attention" : "all");
  }, [result]);

  const chooseFocus = (nextFocus) => {
    setFocus(nextFocus);
    const matcher = focusOption(nextFocus).matches;
    const nextIndex = annotations.findIndex(matcher);
    if (nextIndex >= 0) setSelectedIndex(nextIndex);
  };

  const matcher = focusOption(focus).matches;
  const selected = annotations[selectedIndex] || null;

  return h(
    "div",
    { className: "draft-check-result" },
    h(AnnotationSummary, { result, onEdit }),
    result.pre_run
      ? h("div", { className: "draft-check-notice" },
          h(AlertTriangle, { size: 16, "aria-hidden": "true" }),
          h("span", null, "No completed project run yet. Assumptions can be surfaced, but evidence status has not been tested."))
      : null,
    allUnmatched || result.note
      ? h("p", { className: "draft-check-note" }, allUnmatched
          ? "Nothing in this draft matched the current project map. Turn on Find new assumptions to inspect claims the map does not already know."
          : displayText(result.note))
      : null,
    h(
      "div",
      { className: "draft-focus-bar" },
      h("span", { className: "draft-focus-label" }, "Focus"),
      h(
        "div",
        { className: "draft-focus-control", role: "group", "aria-label": "Focus passages" },
        FOCUS_OPTIONS.map((option) =>
          h(
            "button",
            {
              key: option.id,
              type: "button",
              className: focus === option.id ? "is-active" : "",
              "aria-pressed": focus === option.id,
              onClick: () => chooseFocus(option.id),
            },
            option.label,
            h("span", null, statusCount(annotations, option.id))
          )
        )
      )
    ),
    annotations.length
      ? h(
          "div",
          { className: "draft-review-layout" },
          h(
            "article",
            { className: "draft-document", "aria-label": "Checked draft" },
            h("div", { className: "draft-document-head" },
              h("span", null, "Draft"),
              h("span", null, `${annotations.length} passages`)),
            h(
              "div",
              { className: "draft-document-body" },
              annotations.map((annotation, index) => {
                const status = String(annotation.status || "INERT").toLowerCase();
                const statusMeta = STATUS[annotation.status] || STATUS.INERT;
                const matchesFocus = matcher(annotation);
                return h(
                  "button",
                  {
                    key: `${index}:${annotation.element_id || "none"}`,
                    type: "button",
                    className: [
                      "draft-passage",
                      `status-${status}`,
                      selectedIndex === index ? "is-selected" : "",
                      matchesFocus ? "" : "is-muted",
                    ].filter(Boolean).join(" "),
                    "aria-pressed": selectedIndex === index,
                    "aria-label": `Passage ${index + 1}, ${statusMeta.label}: ${String(annotation.sentence || "")}`,
                    title: statusMeta.label,
                    onClick: () => setSelectedIndex(index),
                  },
                  h("span", { className: "draft-passage-number", "aria-hidden": "true" }, index + 1),
                  h("span", { className: "draft-passage-text" }, String(annotation.sentence || ""))
                );
              })
            )
          ),
          h(AnnotationInspector, { annotation: selected, index: selectedIndex })
        )
      : h("p", { className: "draft-check-empty" }, "No prose passages were found in this draft."),
    result.dropped
      ? h("p", { className: "draft-check-footnote" },
          `${result.dropped} proposed anchor${result.dropped === 1 ? " was" : "s were"} omitted because the exact text could not be verified.`)
      : null
  );
}

function ReingestResult({ result, onEdit, onPromote, promotion }) {
  const violations = Array.isArray(result.ungoverned) ? result.ungoverned : [];
  const dropped = Array.isArray(result.dropped_claims) ? result.dropped_claims : [];
  const cleanViolation = (value) => String(value || "").replace(/^UNGOVERNED:\s*/i, "");
  const passed = Boolean(result.ok && result.governed);
  const promoted = promotion && promotion.result && promotion.result.promoted;
  return h(
    "div",
    { className: `draft-trace-result ${passed ? "is-clear" : "needs-review"}` },
    h(
      "div",
      { className: "draft-trace-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, "Edited-copy trace"),
        h("h3", null, passed
          ? "Every claim still traces"
          : `${violations.length} passage${violations.length === 1 ? "" : "s"} lost their trace`),
          h("p", null, passed
          ? `Checked against ${result.elements || 0} recorded project elements.`
          : "These passages no longer match the current project record.")),
      h("button", { type: "button", className: "chip", onClick: onEdit },
        h(RefreshCw, { size: 14, "aria-hidden": "true" }), "Check another version")
    ),
    passed
      ? h("div", { className: "draft-trace-clear" },
          h(Check, { size: 18, "aria-hidden": "true" }),
          h("span", null, `The edited copy preserved ${result.traced_claims || 0} recorded claim${result.traced_claims === 1 ? "" : "s"} and their qualifiers.`))
      : result.error
        ? h("p", { className: "draft-check-error" }, displayText(result.error))
        : h("ol", { className: "draft-trace-violations" },
            violations.map((violation, index) => h("li", { key: index }, cleanViolation(violation)))),
    dropped.length
      ? h("details", { className: "draft-trace-dropped" },
          h("summary", null, `${dropped.length} recorded claim${dropped.length === 1 ? " is" : "s are"} omitted from this copy`),
          h("ul", null, dropped.slice(0, 12).map((claim, index) => h("li", { key: index }, displayText(claim)))))
      : null,
    passed
      ? h("div", { className: "draft-promote" },
          h("div", null,
            h("strong", null, promoted ? "Current rendering saved" : "Make this the current rendering"),
            h("p", null, promoted
              ? `Saved to ${promotion.result.path}. The decision graph was not changed.`
              : "Writes this trace-clean copy and an audit receipt bound to the checked decision. It does not turn prose into evidence or alter the decision graph.")),
          promoted
            ? h(StatusLine, { tone: "ok" }, "current")
            : h("button", { type: "button", className: `chip primary ${promotion && promotion.running ? "is-busy" : ""}`,
                disabled: !onPromote || (promotion && promotion.running), onClick: onPromote },
                promotion && promotion.running ? "Promoting" : "Promote copy"),
          promotion && promotion.error ? h("p", { className: "draft-check-error" }, displayText(promotion.error)) : null)
      : null
  );
}

function DraftEditor({ mode, value, setValue, canRun, busy, useModel, setUseModel, onSubmit, sourcePath }) {
  const inputId = React.useId();
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const annotateMode = mode === "coverage";
  return h(
    "form",
    { className: "draft-editor", onSubmit: (event) => { event.preventDefault(); onSubmit(); } },
    h("div", { className: "draft-editor-label" },
      h("label", { htmlFor: inputId }, annotateMode ? "Draft" : "Edited copy"),
      h("span", null, `${wordCount} word${wordCount === 1 ? "" : "s"}`)),
    sourcePath
      ? h("p", { className: "draft-editor-source" }, "Loaded from checked draft ", h("code", null, sourcePath),
          ". Revise it, then use Edited-copy trace before relying on rewritten prose.")
      : null,
    h("textarea", {
      id: inputId,
      className: "draft-editor-input",
      placeholder: canRun
        ? annotateMode
          ? "Paste a memo, PRD, proposal, or other decision document."
          : "Paste the edited version you plan to use."
        : "Open a project to check a draft against its current decision record.",
      value,
      disabled: !canRun || busy,
      onChange: (event) => setValue(event.target.value),
      autoFocus: canRun,
    }),
    h(
      "footer",
      { className: "draft-editor-actions" },
      annotateMode
        ? h("label", { className: "draft-model-toggle" },
            h("input", {
              type: "checkbox",
              checked: useModel,
              disabled: !canRun || busy,
              onChange: (event) => setUseModel(event.target.checked),
            }),
            h("span", { className: "draft-toggle-track", "aria-hidden": "true" }, h("span", null)),
            h("span", { className: "draft-toggle-copy" },
              h("strong", null, "Find new assumptions"),
              h("small", null, h(Sparkles, { size: 12, "aria-hidden": "true" }), "Uses a model")))
        : h("p", { className: "draft-editor-boundary" }, "Strict trace check first · saving is a separate action"),
      h(
        "button",
        {
          type: "submit",
          className: `chip primary ${busy ? "is-busy" : ""}`,
          disabled: !canRun || busy || !value.trim(),
        },
        annotateMode
          ? h(Search, { size: 15, "aria-hidden": "true" })
          : h(Check, { size: 15, "aria-hidden": "true" }),
        busy ? "Checking" : annotateMode ? "Check draft" : "Check trace"
      )
    )
  );
}

export function ScenarioPanel({ project, liveMode, annotate, reingest, promotion, onAnnotate, onReingest, onPromote, draftSeed }) {
  const [mode, setMode] = React.useState("coverage");
  const [doc, setDoc] = React.useState("");
  const [polished, setPolished] = React.useState("");
  const [useModel, setUseModel] = React.useState(false);
  const [editing, setEditing] = React.useState(true);
  const canRun = Boolean(liveMode && project);
  const annotateBusy = Boolean(annotate && annotate.running);
  const reingestBusy = Boolean(reingest && reingest.running);
  const activeResult = mode === "coverage" ? annotate && annotate.result : reingest && reingest.result;
  const activeError = mode === "coverage" ? annotate && annotate.error : reingest && reingest.error;
  const activeSeed = draftSeed && draftSeed.project === project ? draftSeed : null;

  React.useEffect(() => {
    if (activeResult) setEditing(false);
  }, [activeResult]);

  React.useEffect(() => {
    if (!activeSeed) return;
    setMode(activeSeed.mode === "trace" ? "trace" : "coverage");
    setEditing(true);
    if (activeSeed.loading || activeSeed.error) {
      setDoc("");
      setPolished("");
      return;
    }
    if (activeSeed.text) {
      setDoc(activeSeed.text);
      setPolished(activeSeed.text);
    }
  }, [activeSeed && activeSeed.token]);

  const switchMode = (nextMode) => {
    setMode(nextMode);
    const nextResult = nextMode === "coverage" ? annotate && annotate.result : reingest && reingest.result;
    setEditing(!nextResult);
  };

  const submit = () => {
    if (mode === "coverage") {
      if (onAnnotate && doc.trim()) onAnnotate(doc, useModel);
      return;
    }
    if (onReingest && polished.trim()) onReingest(polished);
  };

  return h(
    "section",
    { className: "draft-check", "aria-label": "Check a draft" },
    h(
      "div",
      { className: "draft-check-modebar" },
      h(
        "div",
        { className: "draft-check-modes", role: "tablist", "aria-label": "Draft check type" },
        h("button", {
          type: "button", role: "tab", "aria-selected": mode === "coverage",
          className: mode === "coverage" ? "is-active" : "", onClick: () => switchMode("coverage"),
        }, "Inspect a document"),
        h("button", {
          type: "button", role: "tab", "aria-selected": mode === "trace",
          className: mode === "trace" ? "is-active" : "", onClick: () => switchMode("trace"),
        }, "Verify an edited draft")
      ),
      h("span", { className: "draft-check-readonly" }, mode === "coverage" ? "Read-only comparison" : "Saving requires a clean trace")
    ),
    activeSeed && activeSeed.loading
      ? h("div", { className: "draft-check-notice" },
          h(RefreshCw, { size: 16, "aria-hidden": "true" }),
          h("span", null, "Loading the checked draft…"))
      : null,
    activeSeed && activeSeed.error
      ? h("div", { className: "draft-check-error", role: "alert" },
          h(AlertTriangle, { size: 16, "aria-hidden": "true" }),
          h("span", null, displayText(activeSeed.error)))
      : null,
    activeError
      ? h("div", { className: "draft-check-error", role: "alert" },
          h(AlertTriangle, { size: 16, "aria-hidden": "true" }),
          h("span", null, displayText(activeError)))
      : null,
    editing || !activeResult
      ? h(DraftEditor, {
          mode,
          value: mode === "coverage" ? doc : polished,
          setValue: mode === "coverage" ? setDoc : setPolished,
          canRun,
          busy: Boolean((mode === "coverage" ? annotateBusy : reingestBusy) || (activeSeed && activeSeed.loading)),
          useModel,
          setUseModel,
          onSubmit: submit,
          sourcePath: activeSeed && activeSeed.text ? activeSeed.path : "",
        })
      : mode === "coverage"
        ? h(AnnotationResult, { result: activeResult, onEdit: () => setEditing(true) })
        : h(ReingestResult, { result: activeResult, onEdit: () => setEditing(true), promotion,
            onPromote: onPromote ? () => onPromote(polished, activeResult.base_hash, activeSeed && activeSeed.path) : null })
  );
}
