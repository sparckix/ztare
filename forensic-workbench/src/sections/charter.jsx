import React from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { displayText, displayMessage } from "../design-system.js";

const h = React.createElement;
const { useState } = React;

// Render the charter markdown to real document structure (headings, lists, emphasis) — the Notion/
// Linear way, not a wall of pre-wrapped text.
function prose(markdown) {
  const html = DOMPurify.sanitize(marked.parse(String(markdown || ""), { breaks: false, gfm: true }));
  return h("div", { className: "charter-prose", dangerouslySetInnerHTML: { __html: html } });
}

// A sticky rail SummaryCard (shares the global .summary-card styles with Thesis).
function RailCard({ label, headline, fact, tone, linkText, onClick }) {
  return h("aside", { className: `summary-card ${tone || ""}` },
    h("span", { className: "summary-card-label" }, label),
    headline ? h("strong", { className: "summary-card-headline" }, headline) : null,
    fact ? h("p", { className: "summary-card-fact" }, fact) : null,
    linkText ? h("button", { type: "button", className: "summary-card-link", onClick }, linkText) : null);
}

// Charter — the project's mandate, the thing the kernel treats as MANDATORY CONTEXT and the thesis
// must keep serving. Reads like a Notion doc: a calm titled document + a sticky rail (no dead margin,
// no boxes). Editing is a mode toggle. Pure view + a local editing flag. Data via /api/charter.
export function Charter({ view, draft, setDraft, liveMode, saving, changed, onSave, onReload, onPreview, onOpenDetail }) {
  const v = view || {};
  const [editing, setEditing] = useState(false);
  const sections = Array.isArray(v.sections) ? v.sections : [];
  const editable = v.editable !== false && liveMode;
  const enforced = detectContracts(sections);

  const drift = v.drift
    ? h("div", { className: "charter-drift" },
        h("span", { className: "eyebrow" }, "A run found your thesis drifting from this charter"),
        h("p", null, displayMessage(v.drift.gap || "")),
        v.drift.added_criterion
          ? h("small", null, "The evaluator added a check for it: ", displayMessage(v.drift.added_criterion))
          : null)
    : null;

  // Edit mode — the raw markdown, de-chromed (one textarea + save/cancel), full width.
  if (editing) {
    return h("section", { className: "charter", "aria-label": "Edit charter" },
      h("div", { className: "charter-edit-head" },
        h("span", { className: "eyebrow" }, "Editing the mandate"),
        h("span", { className: "charter-path" }, displayText(v.path || ""))),
      h("textarea", {
        className: "charter-textarea", value: (draft && draft.text) || "", rows: 24,
        spellCheck: false, disabled: !editable,
        onChange: (e) => setDraft({ ...(draft || {}), text: e.target.value })
      }),
      h("div", { className: "charter-actions" },
        h("button", { type: "button", className: "chip primary", disabled: !editable || saving || !changed,
          onClick: () => { onSave && onSave(); setEditing(false); } }, saving ? "Saving…" : "Save the charter"),
        h("button", { type: "button", className: "chip ghost",
          onClick: () => { onReload && onReload(); setEditing(false); } }, "Cancel")));
  }

  // Empty state.
  if (!v.exists || !(v.markdown || "").trim()) {
    return h("section", { className: "charter", "aria-label": "Charter" },
      drift,
      h("div", { className: "charter-empty" },
        h("p", null, "No charter yet. The charter is the mandate this project serves — the question, the working thesis, scope limits, and what would change your mind. The loop reads it on every iteration."),
        editable ? h("button", { type: "button", className: "chip primary", onClick: () => setEditing(true) }, "Write the charter") : null));
  }

  return h("section", { className: "charter", "aria-label": "Charter" },
    // A thin action row (the page header already names + describes the charter — no duplicate title).
    h("div", { className: "charter-actions-row" },
      v.path ? h("button", { type: "button", className: "text-link", onClick: () => onPreview && onPreview({ type: "file", value: v.path }) }, "Open file") : null,
      editable ? h("button", { type: "button", className: "chip", onClick: () => setEditing(true) }, "Edit") : null),

    drift,

    // Doc + rail — the document (rendered markdown, real hierarchy) fills the main column, the rail
    // fills the right (no dead margin, no wall of text).
    h("div", { className: "charter-body" },
      h("div", { className: "charter-main" }, prose(v.markdown || "")),

      h("div", { className: "charter-rail" },
        h(RailCard, {
          label: "Mandate", tone: v.complete ? "ready" : "attention",
          headline: v.complete ? "Complete" : "Needs work",
          fact: v.complete ? "Every required section is present." : (v.missing && v.missing.length ? `Missing: ${v.missing.map(displayText).join(", ")}` : "Some required sections are missing.")
        }),
        enforced.length
          ? h(RailCard, { label: "What the loop enforces", fact: enforced.join(" · ") })
          : h(RailCard, { label: "What the loop enforces", fact: "The mutator reads this charter as mandatory context on every iteration." }),
        h(RailCard, {
          label: "Charter drift", tone: v.drift ? "attention" : "",
          headline: v.drift ? "Flagged this run" : "Clean",
          fact: v.drift ? "A run found the thesis straying — see above." : "The last run's thesis stayed on the mandate."
        }),
        h(RailCard, {
          label: "Your answer", fact: "The thesis is what tackles this mandate.",
          linkText: onOpenDetail ? "Open the thesis →" : null,
          onClick: () => onOpenDetail && onOpenDetail("overview", "Thesis")
        }))));
}

// Which kernel-enforced contracts this charter declares (so the rail says what the run will police).
function detectContracts(sections) {
  const titles = sections.map((s) => String(s.title || "").toLowerCase());
  const out = [];
  if (titles.some((t) => t.includes("forecast type"))) out.push("forecast-type grammar");
  if (titles.some((t) => t.includes("anchor prox"))) out.push("anchor-proxy coverage");
  if (titles.some((t) => t.includes("asymptotic"))) out.push("asymptotic-claim contract");
  if (titles.some((t) => t.includes("run contract") || t.includes("grading") || t.includes("deterministic gate"))) out.push("run contract");
  return out;
}
