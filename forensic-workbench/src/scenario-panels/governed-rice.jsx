import React from "react";
import { Pencil, RefreshCw, Save, X } from "lucide-react";
import { displayText, Block, FactRow, Tag, EmptyState } from "../design-system.js";
import { ModalPortal, useModalBehavior } from "../modal-behavior.js";

const h = React.createElement;
const FACTORS = ["reach", "impact", "effort"];
const TIER_TONE = { proven: "ok", reproducible: "ok", cited: "warn", unchecked: "neutral", none: "neutral" };

export const scenarioPanel = Object.freeze({
  id: "governed-rice",
  host: "results",
  label: "RICE priority",
  description: "Prioritization with evidence-derived confidence and bounded estimate sensitivity.",
  contract: {
    schema: "plugin_contribution_contract_v1",
    carriers: ["decision_state", "strength_profile", "rice_inputs"],
    actions: [
      { id: "refresh", mode: "read" },
      { id: "update-estimates", mode: "write" },
    ],
  },
});

function weakestText(weakest) {
  const factor = weakest && weakest.factor;
  if (!factor) return "—";
  return `${String(factor).charAt(0).toUpperCase()}${String(factor).slice(1)} is ${displayText(weakest.tier || "unchecked")}`;
}

function scoreLabel(row) {
  const likely = Number(row.score || 0);
  const low = Number(row.score_low || 0);
  const high = Number(row.score_high || 0);
  if (Math.abs(high - low) < 1e-9) return `score ${likely.toFixed(1)}`;
  return `${likely.toFixed(1)} likely · ${low.toFixed(1)}–${high.toFixed(1)}`;
}

function estimateText(factor) {
  const item = factor || {};
  const value = Number(item.value || 0);
  const low = Number(item.low ?? value);
  const high = Number(item.high ?? value);
  const unit = item.unit ? ` ${displayText(item.unit)}` : "";
  return Math.abs(high - low) < 1e-9
    ? `${value}${unit}`
    : `${value}${unit} (${low}–${high})`;
}

function rankRow(row, i, onEdit) {
  const none = row.confidence_tier === "none";
  const conf = Number(row.confidence) || 0;
  const band = row.rank_band || [row.rank, row.rank];
  return h("li", { key: row.id || i, className: "scenario-priority-row" },
    h("div", { className: "scenario-priority-row-head" },
      h("span", { className: "scenario-priority-rank", title: row.rank_stable ? "Rank is stable across the stated ranges" :
        `Rank can move from ${band[0]} to ${band[1]} across the stated ranges` },
        row.rank_stable ? row.rank : `${band[0]}–${band[1]}`),
      h("strong", { className: "scenario-priority-title" }, displayText(row.initiative || row.id || "—")),
      h(Tag, { tone: none ? "neutral" : "accent" }, none ? "not rankable" : scoreLabel(row)),
      h("button", { type: "button", className: "icon-button scenario-priority-edit", title: "Edit estimates",
        "aria-label": `Edit estimates for ${displayText(row.initiative || row.id)}`,
        onClick: () => onEdit(row) }, h(Pencil, { size: 15, "aria-hidden": "true" }))),
    h("div", { className: "scenario-priority-factors" },
      FACTORS.map((name) => h("span", { key: name },
        h("strong", null, `${name.charAt(0).toUpperCase()}${name.slice(1)} `), estimateText(row[name])))),
    h(FactRow, { label: "Confidence" },
      none ? "no backing yet" : h("span", null, `${conf.toFixed(2)} · `,
        h(Tag, { tone: TIER_TONE[row.confidence_tier] || "neutral" }, displayText(row.confidence_tier)))),
    h(FactRow, { label: "Weakest factor" }, weakestText(row.weakest)));
}

function factorDraft(raw, name) {
  const value = Number((raw && raw.value) ?? (name === "effort" ? 1 : 0));
  return {
    low: Number((raw && raw.low) ?? value),
    value,
    high: Number((raw && raw.high) ?? value),
    unit: String((raw && raw.unit) || ""),
    ref: String((raw && raw.ref) || ""),
  };
}

function EstimateEditor({ row, stored, evidence, saving, error, onCancel, onSave }) {
  const [draft, setDraft] = React.useState(() => Object.fromEntries(
    FACTORS.map((name) => [name, factorDraft((stored || {})[name], name)])));
  const [validationError, setValidationError] = React.useState("");
  const closeButtonRef = React.useRef(null);
  const dialogRef = useModalBehavior({ open: true, onClose: onCancel, initialFocusRef: closeButtonRef });
  const update = (name, key, value) => {
    setValidationError("");
    setDraft((current) => ({ ...current, [name]: { ...current[name], [key]: value } }));
  };
  const submit = () => {
    const factors = Object.fromEntries(FACTORS.map((name) => [name, {
      ...draft[name], low: Number(draft[name].low), value: Number(draft[name].value),
      high: Number(draft[name].high),
    }]));
    const invalid = FACTORS.find((name) => {
      const factor = factors[name];
      return ![factor.low, factor.value, factor.high].every(Number.isFinite)
        || factor.low < 0 || factor.low > factor.value || factor.value > factor.high;
    });
    if (invalid) {
      setValidationError(`${invalid.charAt(0).toUpperCase()}${invalid.slice(1)} must satisfy 0 ≤ low ≤ likely ≤ high.`);
      return;
    }
    onSave(factors);
  };

  return h(ModalPortal, null,
    h("div", { className: "modal-backdrop", role: "presentation",
      onMouseDown: (event) => event.target === event.currentTarget && !saving && onCancel() },
      h("section", { ref: dialogRef, tabIndex: -1, className: "modal-shell scenario-estimate-modal",
        role: "dialog", "aria-modal": "true", "aria-label": "Prioritization estimates" },
        h("header", { className: "modal-head scenario-estimate-modal-head" },
          h("div", null, h("span", { className: "eyebrow" }, "Estimates"),
            h("h2", null, displayText(row.initiative || row.id))),
          h("button", { ref: closeButtonRef, type: "button", className: "icon-button", title: "Close",
            "aria-label": "Close estimate editor", disabled: saving, onClick: onCancel },
            h(X, { size: 16, "aria-hidden": "true" }))),
        h("div", { className: "scenario-estimate-modal-body" },
          validationError || error
            ? h("p", { className: "decision-error", role: "alert" }, displayText(validationError || error))
            : null,
          h("div", { className: "scenario-estimate-grid" },
            h("div", { className: "scenario-estimate-columns" },
              ["Factor", "Low", "Likely", "High", "Unit", "Evidence"].map((label) =>
                h("span", { key: label, className: "scenario-estimate-label" }, label))),
            FACTORS.map((name) => h("div", { key: name, className: "scenario-estimate-row" },
              h("strong", { className: "scenario-estimate-factor" },
                `${name.charAt(0).toUpperCase()}${name.slice(1)}`),
              ...["low", "value", "high"].map((key) => h("input", { key, type: "number", min: 0,
                step: "any", className: "form-input", value: draft[name][key], disabled: saving,
                "aria-label": `${name} ${key === "value" ? "likely" : key}`,
                onChange: (event) => update(name, key, event.target.value) })),
              h("input", { className: "form-input scenario-estimate-unit", value: draft[name].unit, disabled: saving,
                placeholder: name === "effort" ? "weeks" : "unit", "aria-label": `${name} unit`,
                onChange: (event) => update(name, "unit", event.target.value) }),
              h("select", { className: "form-input scenario-estimate-source", value: draft[name].ref, disabled: saving,
                "aria-label": `${name} evidence`, onChange: (event) => update(name, "ref", event.target.value) },
                h("option", { value: "" }, "No cited source"),
                (evidence || []).map((source) => h("option", { key: source.id, value: source.id },
                  displayText(source.text || source.id).slice(0, 90))))))),
          h("div", { className: "scenario-estimate-actions" },
            h("button", { type: "button", className: "chip", disabled: saving, onClick: onCancel }, "Cancel"),
            h("button", { type: "button", className: `chip primary ${saving ? "is-busy" : ""}`,
              disabled: saving, onClick: submit }, h(Save, { size: 15, "aria-hidden": "true" }),
              saving ? "Saving…" : "Save estimates"))))));
}

export function RicePanel({ project, liveMode }) {
  const canRun = liveMode && !!project;
  const [state, setState] = React.useState({ running: false, data: null, error: "", saving: false });
  const [editing, setEditing] = React.useState(null);

  const load = React.useCallback(async () => {
    if (!canRun) return;
    setState((current) => ({ ...current, running: true, error: "" }));
    try {
      const res = await fetch("/api/scenario-rice", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project }) });
      const data = await res.json();
      setState({ running: false, data, error: "", saving: false });
    } catch (error) {
      setState((current) => ({ ...current, running: false, error: String(error) }));
    }
  }, [project, canRun]);

  React.useEffect(() => { setEditing(null); load(); }, [project, liveMode]);  // eslint-disable-line

  const save = async (factors) => {
    if (!editing) return;
    setState((current) => ({ ...current, saving: true, error: "" }));
    try {
      const response = await fetch("/api/scenario-rice-inputs", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, claim_id: editing.id, factors }) });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || "Could not save estimates");
      setState({ running: false, data, error: "", saving: false });
      setEditing(null);
    } catch (error) {
      setState((current) => ({ ...current, saving: false, error: String(error.message || error) }));
    }
  };

  const data = state.data;
  const rows = (data && data.rows) || [];
  return h(Block, {
    title: "Prioritize",
    lead: "A PM scenario view over the core claim graph — confidence is read from backing, never typed here.",
    actions: h("button", { type: "button", className: `icon-button ${state.running ? "is-busy" : ""}`,
      disabled: !canRun || state.running, onClick: load, title: "Refresh ranking", "aria-label": "Refresh ranking" },
      h(RefreshCw, { size: 16, "aria-hidden": "true" })),
  },
    !canRun ? h("p", { className: "muted" }, "Open a project first.") : null,
    state.error ? h("p", { className: "decision-error" }, displayText(state.error)) : null,
    data && data.ok === false ? h("p", { className: "muted" }, displayText(data.error) || "Run this project first.") : null,
    data && data.ok ? h("p", { className: "scenario-priority-note" }, "This panel belongs to the active scenario. It does not add a Workbench section or change the underlying decision.") : null,
    data && data.ok && rows.length
      ? h("ol", { className: "scenario-priority-list" }, rows.map((row, index) => rankRow(row, index, setEditing)))
      : (data && data.ok ? h(EmptyState, { text: "No initiative claims to rank yet." }) : null),
    editing && data && data.ok
      ? h(EstimateEditor, { key: editing.id, row: editing,
          stored: (data.inputs || {})[editing.id], evidence: data.evidence || [], saving: state.saving,
          error: state.error, onCancel: () => setEditing(null), onSave: save })
      : null);
}

export default RicePanel;
