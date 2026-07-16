import React from "react";
import { AlertTriangle, ArrowDown, ArrowUp, FileJson, HelpCircle, Layers3, Plus, RefreshCw, X } from "lucide-react";
import { ActionButton, displayText, EmptyState, IconButton, SectionHeader, StatusLine, Tag } from "../design-system.js";
import { ModalPortal, useModalBehavior } from "../modal-behavior.js";

const h = React.createElement;

// The example scenarios shipped with this checkout — the clone-from-example picker offers whichever of these
// are actually installed (never a dead button naming a scenario that isn't there).
const EXAMPLE_SCENARIOS = ["product-manager", "activist-short", "self-audit"];

function truncate(text, n) {
  const s = String(text || "").trim();
  return s.length > n ? `${s.slice(0, n).trimEnd()}…` : s;
}

// Plugin manager — install AND edit the three plugin kinds WITHOUT touching code: SCENARIOS (use-case bundles)
// and RUBRICS (judge dimensions) are data, created/edited here and live immediately (filesystem is the
// registry); CAPABILITIES (@capability code — evidence / renderer / solver) drop as a .py into a plugin dir and
// go live on Reload. Editing opens a modal pre-filled from the installed plugin. Pure view; main.js owns the
// fetch/install/reload. Domain-neutral: "product-manager" is just an example.

function pill(text, tone, onClick, tip) {
  return h("button", {
    key: text,
    type: "button", title: tip || (onClick ? `Edit ${text}` : text), onClick: onClick || undefined,
    disabled: !onClick,
    className: `plugin-pill ${tone === "ok" ? "is-active" : ""}`,
  }, displayText(text));
}

function field(label, node, tip) {
  return h("label", { className: "plugin-field", title: tip || "" },
    h("span", { className: "plugin-field-label" }, label), node);
}

function toggleListValue(values, value) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

const EMPTY_DOCUMENT_DESIGN = {
  name: "",
  label: "",
  audience: "",
  description: "",
  presentation_brief: "",
  sectionRows: [
    { label: "Decision", kinds: ["thesis", "claim"], limit: 0 },
    { label: "Evidence", kinds: ["evidence"], limit: 0 },
  ],
};

const GOVERNED_KINDS = ["thesis", "claim", "evidence", "tension", "gap", "constraint", "falsifier", "rejected"];

function designDraft(spec) {
  const sections = (spec && spec.sections) || [];
  return {
    ...EMPTY_DOCUMENT_DESIGN,
    ...(spec || {}),
    sectionRows: sections.length
      ? sections.map((section) => ({ label: section.label || "Section", kinds: section.kinds || [], limit: Number(section.limit) || 0 }))
      : EMPTY_DOCUMENT_DESIGN.sectionRows.map((section) => ({ ...section, kinds: [...section.kinds] })),
  };
}

function designPayload(draft) {
  const sections = (draft.sectionRows || []).map((section) => {
    const label = String(section.label || "").trim();
    const kinds = (section.kinds || []).filter((kind) => GOVERNED_KINDS.includes(kind));
    if (!label || !kinds.length) return null;
    const limit = Number(section.limit) || 0;
    return limit > 0 ? { label, kinds, limit } : { label, kinds };
  }).filter(Boolean);
  return {
    name: String(draft.name || "").trim(),
    label: String(draft.label || "").trim(),
    audience: String(draft.audience || "").trim(),
    description: String(draft.description || "").trim(),
    presentation_brief: String(draft.presentation_brief || "").trim(),
    sections,
  };
}

function updateDesign(setDesigns, index, change) {
  setDesigns((current) => current.map((item, itemIndex) => itemIndex === index
    ? { ...item, ...(typeof change === "function" ? change(item) : change) }
    : item));
}

function updateSection(setDesigns, designIndex, sectionIndex, change) {
  updateDesign(setDesigns, designIndex, (design) => ({
    sectionRows: design.sectionRows.map((row, rowIndex) => rowIndex === sectionIndex
      ? { ...row, ...(typeof change === "function" ? change(row) : change) }
      : row),
  }));
}

function moveSection(setDesigns, designIndex, sectionIndex, direction) {
  updateDesign(setDesigns, designIndex, (design) => {
    const destination = sectionIndex + direction;
    if (destination < 0 || destination >= design.sectionRows.length) return design;
    const sectionRows = [...design.sectionRows];
    [sectionRows[sectionIndex], sectionRows[destination]] = [sectionRows[destination], sectionRows[sectionIndex]];
    return { sectionRows };
  });
}

function DocumentOutline({ design }) {
  const sections = (design.sectionRows || []).filter((section) => section.label || section.kinds.length);
  if (!sections.length) return h("p", { className: "plugin-document-outline-empty" }, "Add a section to preview the reading order.");
  return h("ol", { className: "plugin-document-outline", "aria-label": "Document reading order" },
    sections.map((section, index) => h("li", { key: `${section.label}-${index}` },
      h("span", null, String(index + 1).padStart(2, "0")),
      h("div", null,
        h("strong", null, section.label || "Untitled section"),
        h("small", null, section.kinds.length ? section.kinds.map(displayText).join(" · ") : "Choose recorded material")))));
}

function DocumentSectionRow({ design, designIndex, section, sectionIndex, setDesigns, busy }) {
  const total = design.sectionRows.length;
  const kinds = section.kinds || [];
  return h("div", { className: "plugin-document-section-row" },
    h("div", { className: "plugin-document-section-row-head" },
      h("input", { className: "form-input", value: section.label, disabled: busy, placeholder: "Section heading",
        onChange: (e) => updateSection(setDesigns, designIndex, sectionIndex, { label: e.target.value }) }),
      h("span", { className: "plugin-document-section-order" },
        h("button", { type: "button", className: "icon-button", disabled: busy || sectionIndex === 0,
          title: "Move section earlier", "aria-label": "Move section earlier",
          onClick: () => moveSection(setDesigns, designIndex, sectionIndex, -1) }, h(ArrowUp, { size: 13, "aria-hidden": "true" })),
        h("button", { type: "button", className: "icon-button", disabled: busy || sectionIndex === total - 1,
          title: "Move section later", "aria-label": "Move section later",
          onClick: () => moveSection(setDesigns, designIndex, sectionIndex, 1) }, h(ArrowDown, { size: 13, "aria-hidden": "true" })),
        h("button", { type: "button", className: "icon-button", disabled: busy || total <= 1,
          title: "Remove section", "aria-label": "Remove section",
          onClick: () => updateDesign(setDesigns, designIndex, (item) => ({
            sectionRows: item.sectionRows.filter((_, rowIndex) => rowIndex !== sectionIndex),
          })) }, h(X, { size: 13, "aria-hidden": "true" })))),
    h("div", { className: "plugin-document-kind-chips", role: "group", "aria-label": `Content for ${section.label || "section"}` },
      GOVERNED_KINDS.map((kind) => h("button", { key: kind, type: "button", className: `plugin-document-kind ${kinds.includes(kind) ? "is-selected" : ""}`,
        "aria-pressed": kinds.includes(kind), title: `Include recorded ${kind} items`, disabled: busy,
        onClick: () => updateSection(setDesigns, designIndex, sectionIndex, (row) => ({
          kinds: row.kinds.includes(kind) ? row.kinds.filter((value) => value !== kind) : [...row.kinds, kind],
        })) }, kind))),
    field("Maximum items (optional)", h("input", { type: "number", min: 1, className: "form-input plugin-document-limit", disabled: busy,
      value: Number(section.limit) > 0 ? section.limit : "", placeholder: "All",
      onChange: (e) => updateSection(setDesigns, designIndex, sectionIndex, { limit: Math.max(0, Number(e.target.value) || 0) }) }),
    "Leave blank to include all matching recorded items."));
}

function DocumentDesignCard({ design, index, setDesigns, busy }) {
  const rows = design.sectionRows || [];
  return h("div", { className: "plugin-document-design" },
    h("div", { className: "plugin-document-design-head" },
      h("div", { className: "plugin-document-design-title" },
        h("strong", null, design.label || design.name || "New document"),
        design.audience ? h("small", null, `For ${design.audience}`) : null),
      h("button", { type: "button", className: "icon-button", disabled: busy, title: "Remove document design", "aria-label": "Remove document design",
        onClick: () => setDesigns((current) => current.filter((_, item) => item !== index)) }, h(X, { size: 14, "aria-hidden": "true" }))),
    h("div", { className: "plugin-document-shape" },
      h("span", { className: "plugin-field-label" }, "Reading shape"),
      h(DocumentOutline, { design })),
    h("div", { className: "plugin-document-meta-grid" },
      field("Document ID", h("input", { className: "form-input", value: design.name, disabled: busy, placeholder: "tradeoff_register",
        onChange: (e) => updateDesign(setDesigns, index, { name: e.target.value }) }),
      "Stable identifier. It is added to this scenario's handoff set automatically."),
      field("Title", h("input", { className: "form-input", value: design.label, disabled: busy, placeholder: "Trade-off register",
        onChange: (e) => updateDesign(setDesigns, index, { label: e.target.value }) })),
      field("Recipient", h("input", { className: "form-input", value: design.audience, disabled: busy, placeholder: "Decision team",
        onChange: (e) => updateDesign(setDesigns, index, { audience: e.target.value }) })),
      field("Decision it supports", h("input", { className: "form-input", value: design.description, disabled: busy,
        placeholder: "What this document helps someone decide", onChange: (e) => updateDesign(setDesigns, index, { description: e.target.value }) }))),
    h("div", { className: "plugin-document-section-field" },
      h("span", { className: "plugin-field-label" }, "Reading order"),
      h("div", { className: "plugin-document-section-list" },
        ...rows.map((section, sectionIndex) => h(DocumentSectionRow, {
          key: sectionIndex, design, designIndex: index, section, sectionIndex, setDesigns, busy,
        })),
        h("button", { type: "button", className: "chip ghost plugin-add-section", disabled: busy,
          onClick: () => updateDesign(setDesigns, index, (item) => ({
            sectionRows: [...item.sectionRows, { label: "New section", kinds: [], limit: 0 }],
          })) }, h(Plus, { size: 13, "aria-hidden": "true" }), "Add section"))),
    h("details", { className: "plugin-document-editorial" },
      h("summary", null, "Editorial note"),
      h("p", null, "Guide the audience-focused version. The checked draft preserves recorded wording; this note can change emphasis and order, but cannot add or rewrite claims."),
      h("textarea", { className: "form-input", rows: 2, value: design.presentation_brief, disabled: busy,
        placeholder: "Lead with the decision boundary; keep unresolved risks visible.",
        onChange: (e) => updateDesign(setDesigns, index, { presentation_brief: e.target.value }) })));
}

function DocumentDesignFields({ designs, setDesigns, busy, compact = false }) {
  const children = [
    h("div", { key: "head", className: "plugin-document-designs-head" },
      h("div", null,
        h("strong", null, "Document designs"),
        h("p", { className: "muted" }, compact
          ? "Define reusable documents for a recipient. Sections select only material already recorded in the decision."
          : "Optional reusable documents. The current checked decision supplies the material; a design never creates a second record.")),
      h(Tag, { tone: "neutral" }, `${designs.length} design${designs.length === 1 ? "" : "s"}`)),
    ...designs.map((design, index) => h(DocumentDesignCard, { key: `${design.name || "new"}-${index}`, design, index, setDesigns, busy })),
    h("button", { key: "add", type: "button", className: "chip ghost plugin-add-document", disabled: busy,
      onClick: () => setDesigns((current) => [...current, designDraft()]) }, h(Plus, { size: 14, "aria-hidden": "true" }), "Add document design"),
  ];
  return h("section", { className: `plugin-document-designs ${compact ? "is-standalone" : ""}` }, ...children);
}

function ScenarioForm({ installed, panelCatalog, busy, initial, nameLocked, submitLabel, onSubmit }) {
  const i = initial || {};
  const [name, setName] = React.useState(i.name || "");
  const [desc, setDesc] = React.useState(i.description || "");
  const [rubric, setRubric] = React.useState(i.rubric || "");
  const [renderer, setRenderer] = React.useState(i.renderer || "markdown");
  const [iters, setIters] = React.useState(Number(i.iters) || 8);
  const [dynamic, setDynamic] = React.useState(i.dynamic !== false);
  const [goalType, setGoalType] = React.useState(i.goal_type || "");
  const [solvers, setSolvers] = React.useState((i.solvers || []).join(", "));
  const [gates, setGates] = React.useState((i.gate_package || []).join(", "));
  const [evidence, setEvidence] = React.useState((i.evidence_sources || ["local_files"]).join(", "));
  const [rechecks, setRechecks] = React.useState((i.rechecks || []).join(", "));
  const [panels, setPanels] = React.useState(i.workbench_panels || []);
  // A named declarative design is already part of the document set. Keep
  // the advanced field strictly for genuinely code-owned template IDs so
  // removing a design cannot leave its old name behind as a hidden fallback.
  const designNames = new Set((i.deliverable_specs || []).map((spec) => spec.name));
  const [deliverables, setDeliverables] = React.useState((i.deliverables || []).filter((name) => !designNames.has(name)).join(", "));
  const [designs, setDesigns] = React.useState((i.deliverable_specs || []).map(designDraft));
  const caps = (installed || {}).capabilities || {};
  const invalidDesign = designs.some((design) => design.name.trim() && (design.sectionRows || []).some((section) => !section.label.trim() || !section.kinds.length));
  return h("div", { className: "plugin-form" },
    field("Name", h("input", { className: "form-input", value: name, disabled: busy || nameLocked,
      placeholder: "e.g. finance-review", onChange: (e) => setName(e.target.value) }),
      "The slug this scenario is stored + run under (spaces become dashes)."),
    field("Description", h("input", { className: "form-input", value: desc, disabled: busy,
      onChange: (e) => setDesc(e.target.value) }), "One line: what claims/decisions this scenario pressure-tests."),
    field("Rubric", h("select", { className: "form-input", value: rubric, disabled: busy,
      onChange: (e) => setRubric(e.target.value) },
      h("option", { value: "" }, "(same name as the scenario)"),
      ((installed || {}).rubrics || []).map((r) => h("option", { key: r, value: r }, r))),
      "The rubric is the main lever — it drives the judge's scoring dimensions and persona across the whole run."),
    h("div", { className: "plugin-run-defaults" },
      field("Iterations", h("input", { type: "number", min: 1, max: 100, className: "form-input",
        value: iters, disabled: busy, onChange: (e) => setIters(Math.max(1, Number(e.target.value) || 1)) }),
        "Default pressure-test rounds; an explicit run setting still wins."),
      h("label", { className: "plugin-toggle" },
        h("input", { type: "checkbox", checked: dynamic, disabled: busy,
          onChange: (e) => setDynamic(e.target.checked) }),
        h("span", null, "Dynamic claim graph"))),
    field("Renderer", h("select", { className: "form-input", value: renderer, disabled: busy,
      onChange: (e) => setRenderer(e.target.value) },
      (caps.renderer || ["markdown"]).map((r) => h("option", { key: r, value: r }, r))),
      "How the post-run artifacts are laid out (markdown, decision_brief, …)."),
    field("Evidence sources", h("input", { className: "form-input", value: evidence, disabled: busy,
      onChange: (e) => setEvidence(e.target.value) }), "Where evidence comes from (local_files today; connectors are plugins)."),
    h(DocumentDesignFields, { designs, setDesigns, busy }),
    field("Workbench panels", h("div", { className: "plugin-choice-list" },
      [...(panelCatalog || []),
        ...panels.filter((ref) => !(panelCatalog || []).some((panel) => panel.ref === ref))
          .map((ref) => ({ ref, label: ref, description: "Panel is not present in this frontend build", missing: true }))]
        .map((panel) => h("label", { key: panel.ref, className: `plugin-choice ${panel.missing ? "is-missing" : ""}` },
          h("input", { type: "checkbox", checked: panels.includes(panel.ref), disabled: busy,
            onChange: () => setPanels((current) => toggleListValue(current, panel.ref)) }),
          h("span", null, h("strong", null, displayText(panel.label)),
            h("small", null, displayText(panel.description || panel.ref)))))),
      "Panels render only in their declared host; they do not add navigation."),
    h("details", { className: "plugin-advanced" },
      h("summary", null, "Advanced wiring"),
      field("Other document IDs", h("input", { className: "form-input", value: deliverables, disabled: busy,
        placeholder: "decision_memo, prd", onChange: (e) => setDeliverables(e.target.value) }),
        "For code-owned templates only. A document design above is declared automatically and does not need to appear here."),
      field("Solvers", h("input", { className: "form-input", value: solvers, disabled: busy,
        placeholder: (caps.solver || []).join(", "), onChange: (e) => setSolvers(e.target.value) }),
        "Optional bounded reasoning engines this scenario can invoke."),
      field("Gate package", h("input", { className: "form-input", value: gates, disabled: busy,
        onChange: (e) => setGates(e.target.value) }), "Optional deterministic gates already registered in the kernel."),
      field("Goal type", h("input", { className: "form-input", value: goalType, disabled: busy,
        onChange: (e) => setGoalType(e.target.value) }), "Optional goal-type policy id."),
      field("Rechecks", h("input", { className: "form-input", value: rechecks, disabled: busy,
        placeholder: (caps.recheck || []).join(", "), onChange: (e) => setRechecks(e.target.value) }),
        "Re-executable checks that can earn or renew stronger backing.")),
    h("div", { className: "plugin-form-actions plugin-form-actions-sticky" },
      h("button", {
        type: "button", className: `chip primary ${busy ? "is-busy" : ""}`, disabled: busy || !name.trim() || invalidDesign,
        title: invalidDesign ? "Every named document section needs a heading and at least one governed kind" : "Writes + validates the scenario; it is live immediately",
        onClick: () => onSubmit(name, { description: desc, rubric, renderer, iters, dynamic,
          mutator_model: i.mutator_model || "", judge_model: i.judge_model || "", goal_type: goalType,
          solvers: solvers.split(",").map((s) => s.trim()).filter(Boolean),
          gate_package: gates.split(",").map((s) => s.trim()).filter(Boolean),
          evidence_sources: evidence.split(",").map((s) => s.trim()).filter(Boolean),
          rechecks: rechecks.split(",").map((s) => s.trim()).filter(Boolean),
          workbench_panels: panels,
          deliverables: [...new Set([
            ...deliverables.split(",").map((s) => s.trim()).filter(Boolean),
            ...designs.map(designPayload).map((spec) => spec.name).filter(Boolean),
          ])],
          deliverable_specs: designs.map(designPayload).filter((spec) => spec.name) }),
      }, busy ? "Saving…" : (submitLabel || "Install scenario"))));
}

function RubricForm({ busy, initial, nameLocked, submitLabel, onSubmit }) {
  const i = initial || {};
  const [name, setName] = React.useState(i.name || "");
  const [persona, setPersona] = React.useState(i.persona || "");
  const [dims, setDims] = React.useState(
    (i.dimensions && i.dimensions.length ? i.dimensions : [{ name: "", description: "", weight: 100 }])
      .map((d) => ({ name: d.name || "", description: d.description || "", weight: d.weight || 0 })));
  const total = dims.reduce((a, d) => a + (parseInt(d.weight, 10) || 0), 0);
  const setDim = (idx, key, val) => setDims(dims.map((d, j) => (j === idx ? { ...d, [key]: val } : d)));
  return h("div", { className: "plugin-form" },
    field("Name", h("input", { className: "form-input", value: name, disabled: busy || nameLocked,
      placeholder: "e.g. finance-review", onChange: (e) => setName(e.target.value) })),
    field("Reviewer stance", h("textarea", { className: "form-input plugin-persona-input", rows: 4,
      value: persona, disabled: busy, onChange: (e) => setPersona(e.target.value) }),
      "The paragraph that sets how the judge reviews — its bar and what it rewards/penalizes."),
    h("div", { className: "plugin-dimensions-head",
      title: "The weighted criteria the judge scores; weights must total 100" },
      h("span", null, "Dimensions"),
      h(Tag, { tone: total === 100 ? "ok" : "warn" }, `${total}%`)),
    dims.map((d, idx) => h("div", { key: idx, className: "plugin-dimension-row" },
      h("input", { className: "form-input plugin-dimension-name", placeholder: "Criterion", value: d.name, disabled: busy,
        onChange: (e) => setDim(idx, "name", e.target.value) }),
      h("input", { className: "form-input plugin-dimension-description", placeholder: "What the judge checks", value: d.description, disabled: busy,
        onChange: (e) => setDim(idx, "description", e.target.value) }),
      h("input", { type: "number", className: "form-input plugin-dimension-weight", value: d.weight, disabled: busy,
        title: "weight (0-100)", onChange: (e) => setDim(idx, "weight", e.target.value) }),
      h("button", { type: "button", className: "icon-button", disabled: busy || dims.length <= 1,
        title: "Remove this dimension", "aria-label": "Remove dimension",
        onClick: () => setDims(dims.filter((_, j) => j !== idx)) }, h(X, { size: 15, "aria-hidden": "true" })))),
    h("button", { type: "button", className: "chip ghost plugin-add-dimension", disabled: busy,
      onClick: () => setDims([...dims, { name: "", description: "", weight: 0 }]) },
      h(Plus, { size: 14, "aria-hidden": "true" }), "Add dimension"),
    h("div", { className: "plugin-form-actions plugin-form-actions-sticky" },
      h("button", {
        type: "button", className: `chip primary ${busy ? "is-busy" : ""}`,
        disabled: busy || !name.trim() || total !== 100,
        title: total === 100 ? "Writes + validates the rubric; it is live immediately" : "Weights must total 100 first",
        onClick: () => onSubmit(name, { persona,
          dimensions: dims.filter((d) => d.name.trim()).map((d) => ({ name: d.name, description: d.description,
            weight: parseInt(d.weight, 10) || 0 })) }),
      }, busy ? "Saving…" : (submitLabel || "Install rubric")),
      total !== 100 ? h("span", { className: "muted", style: { marginLeft: "8px", fontSize: "12px" } },
        "weights must total 100 to save") : null));
}

// The authoring-mirror preview body: what a scenario BINDS (rubric/run/capabilities) + its rubric EFFECT
// (judge dimensions/persona) — GET /api/scenario-preview, a pure read of ztare.scenarios.resolver.scenario_effect.
// Never fabricates: an empty `notes` list means every declared capability resolved; a non-empty one is shown
// plainly, and a rubric-less scenario just shows no dimensions rather than guessing at an effect.
function previewBody(data, panelCatalog) {
  const eff = data.effect || {};
  const b = data.bindings || {};
  const run = b.run || {};
  const dims = eff.dimensions || [];
  const notes = data.notes || [];
  const documents = b.deliverable_specs || [];
  const selectedPanels = (b.workbench_panels || []).map((ref) => ({
    ref,
    panel: (panelCatalog || []).find((candidate) => candidate.ref === ref),
  }));
  return h("div", { className: "plugin-effect-preview" },
    data.description ? h("p", { className: "plugin-effect-lead" }, displayText(data.description)) : null,
    h("section", { className: "plugin-effect-section" },
      h("span", { className: "eyebrow" }, "Evaluation"),
      h("div", { className: "plugin-effect-heading" },
        h("div", null,
          h("h3", null, b.rubric ? displayText(b.rubric) : "No scoring guide"),
          h("p", null, `${run.iters ?? "—"} pressure-test rounds${run.dynamic ? " · claim graph can evolve" : ""}`)),
        dims.length ? h(StatusLine, { tone: eff.weights_sum === 100 ? "ok" : "warn" }, `${eff.weights_sum}% allocated`) : null),
      dims.length
        ? h("div", { className: "plugin-effect-dimensions" }, dims.map((dimension, index) =>
            h("div", { key: index },
              h("span", null, displayText(dimension.name) || `Dimension ${index + 1}`),
              h("strong", null, `${dimension.weight}%`))))
        : h(EmptyState, { text: "No scoring dimensions are available. Choose a scoring guide before relying on this scenario." }),
      eff.persona ? h("p", { className: "plugin-effect-persona" }, truncate(eff.persona, 260)) : null),
    h("section", { className: "plugin-effect-section" },
      h("span", { className: "eyebrow" }, "Workbench experience"),
      h("h3", null, `${documents.length} document design${documents.length === 1 ? "" : "s"} · ${selectedPanels.length} contextual view${selectedPanels.length === 1 ? "" : "s"}`),
      h("p", { className: "plugin-effect-source" }, `Evidence comes from ${((b.evidence || []).map(displayText).join(" and ") || "the project defaults")}.`),
      documents.length
        ? h("div", { className: "plugin-preview-documents" }, documents.map((spec) =>
            h("div", { key: spec.name, className: "plugin-preview-document" },
              h("strong", null, displayText(spec.label || spec.name)),
              spec.audience ? h("small", null, `For ${displayText(spec.audience)}`) : null,
              spec.description ? h("p", null, displayText(spec.description)) : null)))
        : null,
      selectedPanels.length
        ? h("div", { className: "plugin-effect-panels" }, selectedPanels.map(({ ref, panel }) =>
            h("div", { key: ref, className: panel ? "" : "is-missing" },
              h("strong", null, displayText((panel && panel.label) || ref)),
              h("span", null, panel ? displayText(panel.description || `Appears in ${panel.host}`) : "Unavailable in this Workbench build"))))
        : null),
    h("details", { className: "plugin-effect-technical" },
      h("summary", null, "Technical bindings"),
      h("dl", null,
        h("div", null, h("dt", null, "Renderer"), h("dd", null, displayText(b.renderer || "default"))),
        h("div", null, h("dt", null, "Solvers"), h("dd", null, (b.solvers || []).map(displayText).join(", ") || "None")),
        h("div", null, h("dt", null, "Rechecks"), h("dd", null, (b.rechecks || []).map(displayText).join(", ") || "None")),
        h("div", null, h("dt", null, "Gate package"), h("dd", null, (b.gate_package || []).map(displayText).join(", ") || "None")))),
    notes.length ? h("div", { className: "plugin-effect-notes" },
      h(StatusLine, { tone: "warn" }, `${notes.length} unresolved binding${notes.length === 1 ? "" : "s"}`),
      h("ul", null, notes.map((note, index) => h("li", { key: index }, displayText(note))))) : null);
}

function previewModal(preview, onClose, panelCatalog, dialogRef, closeButtonRef) {
  return h("div", {
    className: "modal-backdrop", role: "presentation",
    onMouseDown: (e) => e.target === e.currentTarget && onClose(),
  }, h("div", { ref: dialogRef, tabIndex: -1, className: "modal-shell plugin-modal", role: "dialog", "aria-modal": "true",
    "aria-label": `Preview ${preview.name}` },
    h("div", { className: "modal-head plugin-modal-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, "Scenario effect"),
        h("h2", null, displayText(preview.name))),
      h("button", { ref: closeButtonRef, type: "button", className: "icon-button", title: "Close", "aria-label": "Close preview",
        onClick: onClose }, h(X, { size: 17, "aria-hidden": "true" }))),
    h("div", { className: "modal-body plugin-modal-body" },
      preview.loading
        ? h("p", { className: "muted" }, "Loading…")
        : preview.error
          ? h("p", { className: "decision-error" }, displayText(preview.error))
          : preview.data && preview.data.ok === false
            ? h("p", { className: "decision-error" }, displayText(preview.data.error || "could not load preview"))
            : previewBody(preview.data, panelCatalog))));
}

function installedList(inst, scenarioDetails, panelCatalog, panelDiagnostics, onEdit, onPreview, onDocuments) {
  const caps = inst.capabilities || {};
  const details = inst.capability_details || {};
  const errors = [...(inst.plugin_errors || []), ...(panelDiagnostics || [])];
  const capabilityKinds = ["evidence", "renderer", "solver", "recheck"];
  const capabilityCount = capabilityKinds.reduce((total, kind) =>
    total + ((details[kind] && details[kind].length) ? details[kind].length : (caps[kind] || []).length), 0);
  return h("div", { className: "plugin-installed" },
    h("div", { className: "plugin-inventory-head" },
      h("h3", null, "Installed"),
      h(StatusLine, { tone: errors.length ? "warn" : "ok" }, errors.length ? `${errors.length} issue${errors.length === 1 ? "" : "s"}` : "Healthy")),
    h("section", { className: "plugin-inventory-section" },
      h("h4", null, "Scenarios"),
      (inst.scenarios || []).length
        ? h("div", { className: "plugin-scenario-list" }, (inst.scenarios || []).map((name) =>
            h("article", { key: name, className: "plugin-scenario-row" },
              h("div", { className: "plugin-scenario-copy" },
                h("strong", null, displayText(name)),
                scenarioDetails[name] && scenarioDetails[name].description
                  ? h("p", null, displayText(truncate(scenarioDetails[name].description, 230)))
                  : h("p", { className: "is-loading" }, "Loading scenario purpose…"),
                scenarioDetails[name]
                  ? h("small", null,
                      `${displayText(scenarioDetails[name].rubric || "default scoring guide")} · ` +
                      `${(scenarioDetails[name].deliverable_specs || []).length} document design${(scenarioDetails[name].deliverable_specs || []).length === 1 ? "" : "s"} · ` +
                      `${(scenarioDetails[name].workbench_panels || []).length} contextual view${(scenarioDetails[name].workbench_panels || []).length === 1 ? "" : "s"}`)
                  : null),
              h("span", { className: "plugin-row-actions" },
                h("button", { type: "button", className: "text-link", onClick: () => onPreview(name) }, "Preview effect"),
                h("button", { type: "button", className: "text-link", onClick: () => onDocuments(name) }, "Design documents"),
                h("button", { type: "button", className: "text-link", onClick: () => onEdit("scenario", name) }, "Edit"))))
          )
        : h(EmptyState, { text: "No scenarios installed." })),
    h("section", { className: "plugin-inventory-section" },
      h("h4", null, "Scoring guides"),
      h("details", { className: "plugin-rubric-browser" },
        h("summary", null, `View ${(inst.rubrics || []).length} scoring guide${(inst.rubrics || []).length === 1 ? "" : "s"}`),
        h("div", { className: "plugin-pill-list" },
          (inst.rubrics || []).map((n) => pill(n, "muted", () => onEdit("rubric", n)))))),
    h("details", { className: "plugin-runtime-details" },
      h("summary", null,
        h("span", null,
          h("strong", null, "Runtime integrations"),
          h("small", null, "Technical inventory used by scenarios")),
        h("span", { className: "plugin-runtime-count" },
          `${capabilityCount} available · ${(panelCatalog || []).length} contextual view${(panelCatalog || []).length === 1 ? "" : "s"}`)),
      h("div", { className: "plugin-runtime-body" },
        capabilityKinds.map((kind) => h("div", { key: kind, className: "plugin-runtime-row" },
          h("strong", null, kind === "recheck" ? "Rechecks" : `${kind[0].toUpperCase()}${kind.slice(1)}`),
          h("div", null,
            ((details[kind] && details[kind].length) ? details[kind] : (caps[kind] || []).map((name) => ({ name })))
              .map((item) => h("span", { key: item.name, className: "plugin-runtime-item" },
                displayText(item.name), item.distribution === "external" ? h(Tag, { tone: "accent" }, "external") : null))))),
        (panelCatalog || []).length
          ? h("div", { className: "plugin-runtime-row plugin-runtime-panels" },
              h("strong", null, "Contextual views"),
              h("div", null, (panelCatalog || []).map((panel) => h("span", { key: panel.ref, className: "plugin-runtime-panel",
                title: panel.contract ? `${panel.contract.carriers.length} governed carriers · ${panel.contract.actions.length} actions` : "" },
                h("span", null, displayText(panel.label)),
                h("small", null, `${displayText(panel.host)} · ${displayText(panel.description || "Scenario-specific view")}`)))))
          : null),
        h("details", { className: "plugin-paths" },
          h("summary", null, "Installation paths"),
          h("code", null, (inst.plugin_dirs || []).join("\n") || "$ZTARE_SCENARIO_PLUGINS is not set"))),
    errors.length
      ? h("div", { className: "plugin-load-errors" },
          h("div", { className: "plugin-error-head" }, h(AlertTriangle, { size: 16, "aria-hidden": "true" }),
            h("strong", null, "Load issues")),
          errors.map((row, index) => h("p", { key: `${row.path || row.source}-${index}`, className: "muted" },
            `${displayText(row.path || row.source)}: ${displayText(row.error)}`)))
      : null);
}

function editModal(editing, inst, panelCatalog, busy, onClose, onSave, dialogRef, closeButtonRef) {
  const common = { installed: inst, panelCatalog, busy, initial: { name: editing.name, ...(editing.spec || {}) },
    nameLocked: true, submitLabel: `Save ${editing.kind}` };
  return h("div", {
    className: "modal-backdrop", role: "presentation",
    onMouseDown: (e) => e.target === e.currentTarget && onClose(),
  }, h("div", { ref: dialogRef, tabIndex: -1, className: "modal-shell plugin-modal", role: "dialog", "aria-modal": "true", "aria-label": `Edit ${editing.kind}` },
    h("div", { className: "modal-head plugin-modal-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, editing.kind === "scenario" ? "Scenario" : "Scoring guide"),
        h("h2", null, displayText(editing.name))),
      h("button", { ref: closeButtonRef, type: "button", className: "icon-button", title: "Close", "aria-label": "Close editor",
        onClick: onClose }, h(X, { size: 17, "aria-hidden": "true" }))),
    h("div", { className: "modal-body plugin-modal-body" },
      editing.loading
        ? h("p", { className: "muted" }, "Loading…")
        : editing.error
          ? h("p", { className: "decision-error" }, displayText(editing.error))
          : editing.kind === "scenario"
            ? h(ScenarioForm, { ...common, onSubmit: (name, spec) => onSave("scenario", name, spec) })
            : h(RubricForm, { ...common, onSubmit: (name, spec) => onSave("rubric", name, spec) }))));
}

function documentDesignModal(documents, busy, onClose, onSave, dialogRef, closeButtonRef) {
  return h("div", {
    className: "modal-backdrop", role: "presentation",
    onMouseDown: (e) => e.target === e.currentTarget && onClose(),
  }, h("div", { ref: dialogRef, tabIndex: -1, className: "modal-shell plugin-modal plugin-document-modal", role: "dialog", "aria-modal": "true",
    "aria-label": `Document designs for ${documents.name}` },
    h("div", { className: "modal-head plugin-modal-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, "Scenario documents"),
        h("h2", null, displayText(documents.name)),
        h("p", null, "Shape repeatable documents without changing the project’s decision record.")),
      h("button", { ref: closeButtonRef, type: "button", className: "icon-button", title: "Close", "aria-label": "Close document designs",
        onClick: onClose }, h(X, { size: 17, "aria-hidden": "true" }))),
    h("div", { className: "modal-body plugin-modal-body" },
      documents.loading
        ? h("p", { className: "muted" }, "Loading document designs…")
        : documents.error
          ? h("p", { className: "decision-error" }, displayText(documents.error))
          : h(DocumentDesignEditor, { documents, busy, onClose, onSave }))));
}

function extensionGuideModal(onClose, dialogRef, closeButtonRef) {
  const paths = [
    {
      title: "Scenario",
      where: "Configured here",
      body: "Sets the review stance, run defaults, evidence providers, renderer, and optional contextual views. Its effects appear in the existing research loop; it does not create navigation.",
    },
    {
      title: "Document design",
      where: "Configured here",
      body: "Selects governed claims, evidence, constraints, and open questions into a reusable reading order. The result appears under Verdict → Handoff and becomes stale when the decision changes.",
    },
    {
      title: "Contextual view",
      where: "Code contribution",
      body: "Declares one supported host, the core carriers it reads, and typed actions it invokes. It renders inline through shared Workbench primitives; RICE and the PM decision kit live in Pressure-test results.",
    },
    {
      title: "Runtime capability",
      where: "Code plugin",
      body: "Adds a provider or bounded engine such as evidence, rendering, recheck, or solving. A scenario selects it by registered name; Reload makes newly installed capabilities available.",
    },
  ];
  return h("div", { className: "modal-backdrop", role: "presentation",
    onMouseDown: (event) => event.target === event.currentTarget && onClose() },
    h("div", { ref: dialogRef, tabIndex: -1, className: "modal-shell plugin-modal", role: "dialog", "aria-modal": "true",
      "aria-label": "How Workbench extensions work" },
      h("header", { className: "modal-head plugin-modal-head" },
        h("div", null,
          h("span", { className: "eyebrow" }, "Extension guide"),
          h("h2", null, "How extensions appear in the Workbench"),
          h("p", null, "Choose the smallest extension that changes the job. Core evidence, decisions, and navigation remain shared.")),
        h("button", { ref: closeButtonRef, type: "button", className: "icon-button", title: "Close", "aria-label": "Close extension guide", onClick: onClose },
          h(X, { size: 16, "aria-hidden": true }))),
      h("div", { className: "modal-body plugin-modal-body" },
        h("div", { className: "plugin-guide-paths" },
          paths.map((path) => h("section", { key: path.title, className: "plugin-guide-path" },
            h("div", null, h("strong", null, path.title), h(Tag, { tone: path.where === "Configured here" ? "ok" : "neutral" }, path.where)),
            h("p", null, path.body)))),
        h("section", { className: "plugin-guide-contract" },
          h("span", { className: "eyebrow" }, "Contribution contract"),
          h("p", null, "A contextual view must declare a supported host, at least one governed carrier, and typed read, write, or navigate actions. Invalid contributions stay unloaded and appear in Plugins health."),
          h("p", null, "Use shared panel and modal primitives. A domain view may compose the core record, but it may not add a second verdict, worklist, ranker, or evidence store.")),
        h("section", { className: "plugin-guide-contract" },
          h("span", { className: "eyebrow" }, "Install paths"),
          h("p", null, h("code", null, "scenarios/<name>.yaml"), " for scenarios and document designs; these are editable here and live immediately."),
          h("p", null, h("code", null, "plugins/scenarios/<name>.py"), " for runtime capabilities registered with ", h("code", null, "@capability(kind, name)"), "; use Reload after changing one."),
          h("p", null, h("code", null, "forensic-workbench/src/scenario-panels/<id>.jsx"), " for contextual views. These are validated at build time and require a frontend rebuild; arbitrary browser code is intentionally not hot-loaded.")),
        h("div", { className: "plugin-guide-actions" },
          h("button", { type: "button", className: "chip primary", onClick: onClose }, "Done")))));
}

function DocumentDesignEditor({ documents, busy, onClose, onSave }) {
  const original = documents.spec || {};
  const [designs, setDesigns] = React.useState((original.deliverable_specs || []).map(designDraft));
  const invalidDesign = designs.some((design) => design.name.trim()
    && (design.sectionRows || []).some((section) => !section.label.trim() || !section.kinds.length));
  const save = () => {
    const specs = designs.map(designPayload).filter((spec) => spec.name);
    const existing = (original.deliverables || []).filter((name) => !((original.deliverable_specs || []).some((spec) => spec.name === name)));
    onSave("scenario", documents.name, {
      ...original,
      deliverables: [...new Set([...existing, ...specs.map((spec) => spec.name)])],
      deliverable_specs: specs,
    });
  };
  return h("div", { className: "plugin-document-editor" },
    h(DocumentDesignFields, { designs, setDesigns, busy, compact: true }),
    invalidDesign ? h("p", { className: "decision-error" }, "Every named section needs a heading and at least one kind of recorded material.") : null,
    h("div", { className: "plugin-form-actions plugin-form-actions-sticky" },
      h("button", { type: "button", className: "chip ghost", disabled: busy, onClick: onClose }, "Cancel"),
      h("button", { type: "button", className: `chip primary ${busy ? "is-busy" : ""}`, disabled: busy || invalidDesign,
        title: invalidDesign ? "Complete the named document sections first" : "Save document designs for this scenario",
        onClick: save }, busy ? "Saving…" : "Save document designs")));
}

function createModal({ kind, inst, panelCatalog, busy, example, cloneSpec, cloneBusy, cloneError,
  availableExamples, onExample, onClose, onCreate, dialogRef, closeButtonRef }) {
  return h("div", { className: "modal-backdrop", role: "presentation",
    onMouseDown: (event) => event.target === event.currentTarget && onClose() },
  h("div", { ref: dialogRef, tabIndex: -1, className: "modal-shell plugin-modal", role: "dialog", "aria-modal": "true",
    "aria-label": `New ${kind}` },
    h("div", { className: "modal-head plugin-modal-head" },
      h("div", null,
        h("span", { className: "eyebrow" }, kind === "scenario" ? "New scenario" : "New scoring guide"),
        h("h2", null, kind === "scenario" ? "Adapt the research loop" : "Define the review bar")),
      h("button", { ref: closeButtonRef, type: "button", className: "icon-button", title: "Close", "aria-label": "Close creator",
        onClick: onClose }, h(X, { size: 17, "aria-hidden": "true" }))),
    h("div", { className: "modal-body plugin-modal-body" },
      kind === "scenario" && availableExamples.length
        ? h("div", { className: "plugin-template-picker" },
            h("span", { className: "plugin-field-label" }, "Start from"),
            h("div", { className: "plugin-template-options" },
              h("button", { type: "button", className: `chip ${!example ? "primary" : "ghost"}`,
                disabled: busy || cloneBusy, onClick: () => onExample("") }, "Blank"),
              availableExamples.map((name) => h("button", { key: name, type: "button",
                className: `chip ${example === name ? "primary" : "ghost"}`, disabled: busy || cloneBusy,
                onClick: () => onExample(name) }, displayText(name)))),
            cloneBusy ? h("p", { className: "muted" }, "Loading template…") : null,
            cloneError ? h("p", { className: "decision-error" }, displayText(cloneError)) : null)
        : null,
      kind === "scenario"
        ? h(ScenarioForm, { key: cloneSpec ? cloneSpec.name : "blank", installed: inst, panelCatalog, busy,
            submitLabel: "Create scenario", initial: cloneSpec || undefined,
            onSubmit: (name, spec) => onCreate("scenario", name, spec) })
        : h(RubricForm, { busy, submitLabel: "Create rubric",
            onSubmit: (name, spec) => onCreate("rubric", name, spec) }))));
}

export function PluginManager({ installed, busy, message, onInstall, onReload, onFetchDetail,
  panelCatalog, panelDiagnostics }) {
  const inst = installed || {};
  const [editing, setEditing] = React.useState(null);   // {kind, name, spec, loading?, error?}
  const [documents, setDocuments] = React.useState(null); // {name, spec, loading?, error?}
  const [creating, setCreating] = React.useState("");
  const [guideOpen, setGuideOpen] = React.useState(false);
  const [scenarioDetails, setScenarioDetails] = React.useState(inst.scenario_details || {});
  const modalCloseRef = React.useRef(null);
  const scenarioKey = (inst.scenarios || []).join("|");
  React.useEffect(() => {
    let cancelled = false;
    const names = inst.scenarios || [];
    if (!onFetchDetail || !names.length) return undefined;
    if (names.every((name) => inst.scenario_details && inst.scenario_details[name])) {
      setScenarioDetails(inst.scenario_details);
      return undefined;
    }
    Promise.all(names.map((name) => Promise.resolve(onFetchDetail("scenario", name))
      .then((result) => [name, result && result.ok ? result.spec || {} : null])
      .catch(() => [name, null])))
      .then((rows) => {
        if (!cancelled) setScenarioDetails(Object.fromEntries(rows.filter(([, spec]) => spec)));
      });
    return () => { cancelled = true; };
  }, [scenarioKey]); // onFetchDetail is recreated by App; scenario identity is the meaningful dependency.
  const openEdit = (kind, name) => {
    setCreating("");
    setDocuments(null);
    setPreview(null);
    setEditing({ kind, name, loading: true });
    Promise.resolve(onFetchDetail && onFetchDetail(kind, name)).then((res) => {
      if (res && res.ok) setEditing({ kind, name: res.name || name, spec: res.spec });
      else setEditing({ kind, name, error: (res && res.error) || "could not load plugin" });
    });
  };
  const openDocuments = (name) => {
    setCreating("");
    setEditing(null);
    setPreview(null);
    setDocuments({ name, loading: true });
    Promise.resolve(onFetchDetail && onFetchDetail("scenario", name)).then((res) => {
      if (res && res.ok) setDocuments({ name: res.name || name, spec: res.spec || {} });
      else setDocuments({ name, error: (res && res.error) || "could not load scenario" });
    }).catch((error) => setDocuments({ name, error: String(error) }));
  };
  const saveEdit = (kind, name, spec) =>
    Promise.resolve(onInstall(kind, name, spec, true)).then((res) => { if (res && res.ok) setEditing(null); });
  const saveDocuments = (kind, name, spec) =>
    Promise.resolve(onInstall(kind, name, spec, true)).then((res) => { if (res && res.ok) setDocuments(null); });
  const saveNew = (kind, name, spec) =>
    Promise.resolve(onInstall(kind, name, spec, false)).then((res) => { if (res && res.ok) setCreating(""); });

  // Preview effect — GET /api/scenario-preview?name=…, a pure read (ztare.scenarios.resolver.scenario_effect),
  // so the author sees what a scenario makes the judge do BEFORE running it. This section owns its own fetch,
  // same as the other self-contained panels (deliverablespanel.jsx et al.) — no state lives outside this view.
  const [preview, setPreview] = React.useState(null);   // {name, loading?, error?, data?}
  const openPreview = (name) => {
    setCreating("");
    setEditing(null);
    setDocuments(null);
    setPreview({ name, loading: true });
    fetch(`/api/scenario-preview?name=${encodeURIComponent(name)}`, { headers: { Accept: "application/json" } })
      .then((r) => r.json())
      .then((data) => setPreview({ name, data }))
      .catch((e) => setPreview({ name, error: String(e) }));
  };

  // Clone-from-example — GET /api/plugin?kind=scenario&name=… returns the exact raw fields the "New scenario"
  // form already expects (its `initial` prop), so a working example prefills the form directly. `key` below
  // forces the form to remount with the fresh initial values (a plain prop change won't reset its internal
  // useState).
  const [example, setExample] = React.useState("");
  const [cloneSpec, setCloneSpec] = React.useState(null);
  const [cloneBusy, setCloneBusy] = React.useState(false);
  const [cloneError, setCloneError] = React.useState("");
  const loadExample = (ex) => {
    setExample(ex);
    setCloneError("");
    if (!ex) { setCloneSpec(null); return; }
    setCloneBusy(true);
    fetch(`/api/plugin?kind=scenario&name=${encodeURIComponent(ex)}`, { headers: { Accept: "application/json" } })
      .then((r) => r.json())
      .then((res) => {
        if (res && res.ok) setCloneSpec({ name: `${ex}-copy`, ...res.spec });
        else { setCloneSpec(null); setCloneError((res && res.error) || `could not load "${ex}"`); }
      })
      .catch((e) => { setCloneSpec(null); setCloneError(String(e)); })
      .finally(() => setCloneBusy(false));
  };
  const availableExamples = EXAMPLE_SCENARIOS.filter((ex) => (inst.scenarios || []).includes(ex));
  const closeActiveModal = () => {
    if (guideOpen) setGuideOpen(false);
    else if (creating) setCreating("");
    else if (preview) setPreview(null);
    else if (editing) setEditing(null);
    else if (documents) setDocuments(null);
  };
  const dialogRef = useModalBehavior({
    open: Boolean(guideOpen || creating || preview || editing || documents),
    onClose: closeActiveModal,
    initialFocusRef: modalCloseRef,
  });
  const modal = guideOpen
    ? extensionGuideModal(() => setGuideOpen(false), dialogRef, modalCloseRef)
    : creating
    ? createModal({ kind: creating, inst, panelCatalog, busy, example, cloneSpec, cloneBusy, cloneError,
        availableExamples, onExample: loadExample, onClose: () => setCreating(""), onCreate: saveNew,
        dialogRef, closeButtonRef: modalCloseRef })
    : preview
      ? previewModal(preview, () => setPreview(null), panelCatalog, dialogRef, modalCloseRef)
      : editing
        ? editModal(editing, inst, panelCatalog, busy, () => setEditing(null), saveEdit, dialogRef, modalCloseRef)
        : documents
          ? documentDesignModal(documents, busy, () => setDocuments(null), saveDocuments, dialogRef, modalCloseRef)
          : null;

  return h(React.Fragment, null,
    h("section", { className: "plugin-manager", "aria-label": "Plugins" },
      h(SectionHeader, { className: "plugin-manager-head", eyebrow: "Workbench extensions", title: "Adapt the research loop",
        description: "Set a domain’s review stance, contextual tools, and reusable documents. The core evidence and decision record stay unchanged.",
        actions: h(React.Fragment, null,
          h(ActionButton, { variant: "quiet", icon: h(HelpCircle, { size: 15, "aria-hidden": true }), disabled: busy,
            onClick: () => { setCreating(""); setEditing(null); setDocuments(null); setPreview(null); setGuideOpen(true); } },
            "How extensions work"),
          h(ActionButton, { variant: "primary", icon: h(Layers3, { size: 15, "aria-hidden": "true" }), disabled: busy,
            onClick: () => { setEditing(null); setDocuments(null); setPreview(null); loadExample(""); setCreating("scenario"); } },
            "Create scenario"),
          h(ActionButton, { icon: h(FileJson, { size: 15, "aria-hidden": "true" }), disabled: busy,
            onClick: () => { setEditing(null); setDocuments(null); setPreview(null); setCreating("rubric"); } },
            "Create scoring guide"),
          h(IconButton, { label: "Reload plugins", disabled: busy, onClick: () => onReload && onReload() },
            h(RefreshCw, { size: 16, "aria-hidden": "true" }))) }),
      message ? h("p", { key: message, className: `plugin-message ${message.startsWith("✓") ? "is-ok" : "is-error"}` },
        displayText(message)) : null,
      installedList(inst, scenarioDetails, panelCatalog, panelDiagnostics, openEdit, openPreview, openDocuments)),
    h(ModalPortal, null, modal));
}
