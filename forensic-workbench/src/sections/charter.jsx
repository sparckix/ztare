import React from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { displayText, displayMessage, Block, FactRow, Tag, EmptyState } from "../design-system.js";

const h = React.createElement;
const { useState } = React;

// Render the charter markdown to real document structure (headings, lists, emphasis) — the Notion/
// Linear way, not a wall of pre-wrapped text.
function slugify(value) {
  return String(value || "").toLowerCase().replace(/<[^>]+>/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "section";
}

function charterHeadingAnchors(markdown) {
  const seen = new Set();
  return String(markdown || "").split(/\r?\n/).flatMap((line) => {
    const match = line.match(/^(#{1,2})\s+(.+?)\s*#*$/);
    if (!match) return [];
    const label = match[2].replace(/[*_`]/g, "").trim();
    const base = slugify(label);
    let id = base; let suffix = 2;
    while (seen.has(id)) id = `${base}-${suffix++}`;
    seen.add(id);
    return [{ id: `charter-${id}`, label, depth: match[1].length }];
  });
}

function prose(markdown) {
  const renderer = new marked.Renderer();
  const seen = new Set();
  renderer.heading = ({ tokens, depth }) => {
    const text = renderer.parser.parseInline(tokens);
    const label = text.replace(/<[^>]+>/g, "").trim();
    const base = slugify(label);
    let id = base; let suffix = 2;
    while (seen.has(id)) id = `${base}-${suffix++}`;
    seen.add(id);
    return `<h${depth} id="charter-${id}">${text}</h${depth}>\n`;
  };
  const html = DOMPurify.sanitize(marked.parse(String(markdown || ""), { breaks: false, gfm: true, renderer }));
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

// Contract lint — the IDE-lint readout over the free-prose charter (Fable's C-as-lint): what the kernel
// actually extracted (forecast type / anchor proxies / asymptotic claim), so the author sees what lands
// without a form fighting the loop's own writes. Self-contained: owns its own fetch (GET /api/charter-lint).
function contractLintPanel(lint) {
  if (!lint) return h(Block, { className: "charter-lint-block", title: "What the compiler extracted" }, h("p", { className: "muted" }, "Reading declared contracts…"));
  if (lint.ok === false) return h(Block, { className: "charter-lint-block", title: "What the compiler extracted" }, h("p", { className: "muted" }, displayText(lint.error || "Could not read this charter.")));
  if (!lint.has_charter) return h(Block, { className: "charter-lint-block", title: "What the compiler extracted" }, h(EmptyState, { text: "No charter yet — nothing for the loop to read." }));
  const contracts = Array.isArray(lint.contracts) ? lint.contracts : [];
  return h(Block, { className: "charter-lint-block", title: "What the compiler extracted" },
    contracts.map((c, i) =>
      h(FactRow, { key: c.name || i, label: displayText(c.name) },
        h("span", { className: "charter-lint-value" },
          h(Tag, { tone: c.parsed ? "ok" : "neutral" }, c.parsed ? "parsed" : "not declared"),
          " ", h("span", { className: "muted" }, displayText(c.value)),
          " ", h("small", null, displayText(c.enforces))))));
}

// Charter — the project's mandate, the thing the kernel treats as MANDATORY CONTEXT and the thesis
// must keep serving. Reads like a Notion doc: a calm titled document + a sticky rail (no dead margin,
// no boxes). Editing is a mode toggle. Pure view + a local editing flag. Data via /api/charter.
export function Charter({ view, draft, setDraft, liveMode, saving, changed, onSave, onReload, onPreview, onOpenDetail }) {
  const v = view || {};
  const [editing, setEditing] = useState(false);
  const sections = Array.isArray(v.sections) ? v.sections : [];
  const anchors = charterHeadingAnchors(v.markdown || "").filter((anchor) => anchor.depth <= 2);
  const editable = v.editable !== false && liveMode;
  const enforced = detectContracts(sections);

  // project slug isn't passed as a prop here — every other charter read comes from v.path
  // ("projects/<slug>/project_charter.md"), so derive it the same way rather than threading a new prop.
  const projectSlug = ((v.path || "").match(/^projects\/([^/]+)\//) || [])[1] || "";
  const [lint, setLint] = useState(null);
  React.useEffect(() => {
    if (!projectSlug) { setLint(null); return undefined; }
    let cancelled = false;
    fetch(`/api/charter-lint?project=${encodeURIComponent(projectSlug)}`, { headers: { Accept: "application/json" } })
      .then((res) => res.json())
      .then((json) => { if (!cancelled) setLint(json); })
      .catch((e) => { if (!cancelled) setLint({ ok: false, error: String(e) }); });
    return () => { cancelled = true; };
  }, [projectSlug]);

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
        anchors.length > 1
          ? h("nav", { className: "charter-toc", "aria-label": "On this page" },
              h("span", { className: "eyebrow" }, "On this page"),
              anchors.map((anchor) => h("a", { key: anchor.id, className: anchor.depth === 2 ? "is-subsection" : "", href: `#${anchor.id}` }, anchor.label)))
          : null,
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
        }))),

    contractLintPanel(lint));
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
