import React from "react";
import { displayText, Tag, EmptyState, StatusLine } from "../design-system.js";

const h = React.createElement;

// Deliverables — folded into Verdict's "The deliverable" block (PRD §4.2a), not a separate screen. A required
// deliverable is a VIEW of what's already governed, never fabricated: this shows, per deliverable, whether it
// composes now (a re-view of checked content) or needs more evidence first. Document design belongs in the
// plugin editor; this surface is the operator's home for current, governed handoffs. Returns a FRAGMENT (no
// outer heading) — it nests under Verdict's own heading.

const STATUS_TONE = { composable: "ok", needs_content: "warn", no_template: "neutral", ungoverned: "danger", error: "danger" };
const STATUS_WORD = {
  composable: "can assemble", needs_content: "needs evidence", no_template: "needs a document design",
  ungoverned: "blocked by backing", error: "needs attention",
};

function readableName(value) {
  return String(value || "document").replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function documentLabel(d) {
  return displayText((d.spec && d.spec.label) || d.label || readableName(d.name));
}

function documentDescription(d) {
  if (d.spec && d.spec.description) return displayText(d.spec.description);
  if (d.status === "composable") return "A checked draft can be assembled from the current decision state. It may still record unresolved gaps.";
  if (d.status === "needs_content") return "This document needs more checked material before a draft would be useful.";
  if (d.status === "no_template") return "Define its sections in the plugin editor before creating it.";
  if (d.status === "ungoverned") return "Some required material is not yet backed well enough to include.";
  return "The document design needs attention before it can be generated.";
}

function artifactState(d) {
  if (d.stale) return h(Tag, { tone: "warn" }, d.decision_fingerprint ? "decision changed — regenerate" : "artifact not current");
  if (d.generated) return h(Tag, { tone: "ok" }, "current checked draft");
  return null;
}

function generateResultLine(res, onPreview, onCheckDraft) {
  if (!res) return null;
  if (res.ok && res.generated) return h("div", { className: "deliverable-generated" },
    h("span", null, "Checked draft created from the current decision."),
    res.path && onPreview
      ? h("button", { type: "button", className: "text-link", onClick: () => onPreview({ type: "file", value: res.path }) }, "Open checked draft")
      : null,
    res.path && onCheckDraft
      ? h("button", { type: "button", className: "text-link", onClick: () => onCheckDraft(res.path) }, "Revise and trace")
      : null);
  if (res.ok) return h("p", { className: "muted" }, displayText(res.verdict || "Done."));
  return h("p", { className: "deliverable-error" }, displayText(res.action || res.status || "Can't generate this yet."));
}

function editorialResultLine(res, onPreview, onCheckDraft) {
  if (!res) return null;
  if (res.running) return h("p", { className: "muted" }, "Shaping the audience draft…");
  if (res.error || res.ok === false) return h("p", { className: "deliverable-error" }, displayText(res.error || "Audience shaping was refused."));
  return h("div", { className: "deliverable-generated" },
    h("span", null, "Audience draft created from exact governed wording."),
    res.path && onPreview
      ? h("button", { type: "button", className: "text-link", onClick: () => onPreview({ type: "file", value: res.path }) }, "Open draft")
      : null,
    res.path && onCheckDraft
      ? h("button", { type: "button", className: "text-link", onClick: () => onCheckDraft(res.path) }, "Review trace and promote")
      : null);
}

// The anti-cherry-pick teeth: was this deliverable declared BEFORE the run that first pinned it (pre-
// registered, ungameable) or added after the fact? Computed server-side off the append-only receipt —
// this just labels it.
function provenanceTag(entry) {
  if (!entry) return null;
  return entry.status === "pre-registered"
    ? h(Tag, { tone: "ok" }, `pre-registered (run ${entry.first_run_id})`)
    : h(Tag, { tone: "neutral" }, "added later");
}

function deliverableRow(d, { canRun, busyName, results, onGenerate, busyEditorial, editorialResults, onEditorial, provenanceByName, onPreview, onCheckDraft }) {
  const busy = busyName === d.name;
  const shaping = busyEditorial === d.name;
  return h("li", { key: d.name, className: "deliverable-row" },
    h("div", { className: "deliverable-row-copy" },
      h("div", { className: "deliverable-row-head" },
        h("strong", null, documentLabel(d)),
        h(Tag, { tone: STATUS_TONE[d.status] || "neutral" }, STATUS_WORD[d.status] || d.status),
        artifactState(d),
        provenanceTag(provenanceByName[d.name])),
      h("p", null, documentDescription(d)),
      (d.detail || []).length
        ? h("ul", { className: "deliverable-detail" },
            d.detail.map((x, i) => h("li", { key: i }, displayText(x))))
        : null),
    h("div", { className: "deliverable-row-action" },
      d.status === "composable"
        ? d.generated && !d.stale
          ? h("div", { className: "deliverable-row-buttons" },
              d.path && onPreview
                ? h("button", { type: "button", className: "chip ghost", onClick: () => onPreview({ type: "file", value: d.path }) }, "Open checked draft")
                : null,
              h("button", { type: "button", className: `chip primary ${shaping ? "is-busy" : ""}`,
                disabled: !canRun || shaping, onClick: () => onEditorial(d.name) }, shaping ? "Shaping…" : "Shape for audience"))
          : h("button", { type: "button", className: `chip ${busy ? "is-busy" : ""}`, disabled: !canRun || busy,
              onClick: () => onGenerate(d.name) }, busy ? "Creating…" : d.stale ? "Refresh draft" : "Create checked draft")
        : null),
    generateResultLine(results[d.name], onPreview, onCheckDraft),
    editorialResultLine(editorialResults[d.name], onPreview, onCheckDraft));
}

// Contract drift since the last pinned run — charter changed and/or deliverables added, either one
// alone is worth flagging; an empty drift (nothing pinned yet) renders nothing.
function driftLine(drift) {
  if (!drift || !drift.pinned) return null;
  const clauses = [];
  if (drift.charter_changed) clauses.push("charter changed");
  if ((drift.declared_added || []).length) clauses.push(`added ${drift.declared_added.map(displayText).join(", ")}`);
  if (!clauses.length) return null;
  return h(StatusLine, { tone: "warn" }, `Contract drift since run ${drift.latest_run_id}: ${clauses.join("; ")}`);
}

function produceResultLine(produce, onPreview, onCheckDraft) {
  if (!produce) return null;
  if (produce.running) return h("p", { className: "muted" }, "Creating the ready drafts…");
  if (produce.error) return h("p", { className: "decision-error" }, displayText(produce.error));
  const out = produce.data;
  if (!out) return null;
  if (out.ok === false) return h("p", { className: "decision-error" }, displayText(out.error || "Could not produce these."));
  const written = (out.written || []).map(displayText);
  return h("div", { className: "deliverable-produce-result" },
    h("p", { className: "muted" }, written.length
      ? `${written.length} checked draft${written.length === 1 ? "" : "s"} created from the current decision.`
      : "No drafts were ready to create."),
    written.length && out.dir && onPreview
      ? h("div", { className: "deliverable-produce-links" }, written.flatMap((name) => {
          const path = `${out.dir}/${name}.md`;
          return [
            h("button", { key: `${name}:open`, type: "button", className: "text-link",
              onClick: () => onPreview({ type: "file", value: path }) }, `Open ${readableName(name)}`),
            onCheckDraft
              ? h("button", { key: `${name}:trace`, type: "button", className: "text-link",
                onClick: () => onCheckDraft(path) }, "Revise and trace")
              : null,
          ].filter(Boolean);
        }))
      : null,
    (out.violations || []).length
      ? h("p", { className: "decision-error" }, "Some document designs remain blocked by their backing requirements.")
      : null);
}

export function DeliverablesPanel({ project, liveMode, scenario = "", onPreview, onManageDocuments, onCheckDraft }) {
  const canRun = liveMode && !!project;
  const [state, setState] = React.useState(null);
  const [busyName, setBusyName] = React.useState("");
  const [results, setResults] = React.useState({});
  const [busyEditorial, setBusyEditorial] = React.useState("");
  const [editorialResults, setEditorialResults] = React.useState({});
  const [provenance, setProvenance] = React.useState(null);
  const [produce, setProduce] = React.useState(null);

  const load = React.useCallback(async () => {
    if (!canRun) return;
    setState({ running: true });
    try {
      const res = await fetch("/api/scenario-deliverables", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project, scenario }) });
      setState({ running: false, data: await res.json() });
    } catch (e) { setState({ running: false, error: String(e) }); }
  }, [project, canRun, scenario]);

  const loadProvenance = React.useCallback(async () => {
    if (!canRun) { setProvenance(null); return; }
    try {
      const res = await fetch(`/api/scenario-provenance?project=${encodeURIComponent(project)}`, { headers: { Accept: "application/json" } });
      setProvenance(await res.json());
    } catch (e) { setProvenance({ ok: false, error: String(e) }); }
  }, [project, canRun]);

  React.useEffect(() => { load(); }, [project, liveMode, scenario]);  // eslint-disable-line
  React.useEffect(() => { loadProvenance(); }, [project, liveMode]);  // eslint-disable-line

  const produceAll = async () => {
    if (!canRun) return;
    setProduce({ running: true });
    try {
      const res = await fetch("/api/scenario-produce-all", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project, scenario }) });
      setProduce({ running: false, data: await res.json() });
      load();
    } catch (e) { setProduce({ running: false, error: String(e) }); }
  };

  const data = state && state.data;
  const deliverables = (data && data.deliverables) || [];
  const busy = !!(state && state.running);
  const prov = (provenance && provenance.ok && provenance.provenance) || null;
  const provenanceByName = {};
  ((prov && prov.deliverables) || []).forEach((d) => { provenanceByName[d.name] = d; });
  const readyCount = deliverables.filter((d) => d.status === "composable").length;

  const generate = async (dname) => {
    if (!canRun) return;
    setBusyName(dname);
    try {
      const res = await fetch("/api/scenario-deliverable-generate", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project, name: dname, scenario }) });
      const out = await res.json();
      setResults((prev) => ({ ...prev, [dname]: out }));
      if (out && out.ok) load();
    } catch (e) { setResults((prev) => ({ ...prev, [dname]: { ok: false, action: String(e) } })); }
    setBusyName("");
  };

  const shapeForAudience = async (dname) => {
    if (!canRun) return;
    setBusyEditorial(dname);
    setEditorialResults((previous) => ({ ...previous, [dname]: { running: true } }));
    try {
      const response = await fetch("/api/scenario-deliverable-editorial", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project, name: dname, scenario }) });
      const payload = await response.json();
      setEditorialResults((previous) => ({ ...previous, [dname]: payload }));
    } catch (error) {
      setEditorialResults((previous) => ({ ...previous, [dname]: { ok: false, error: String(error) } }));
    }
    setBusyEditorial("");
  };

  return h(React.Fragment, null,
    h("div", { className: "deliverable-note" },
      h("strong", null, "Documents from the current decision"),
      h("p", null, "Each checked draft is bound to the decision state that produced it. A draft can preserve unresolved work; creating it does not make the decision ready to rely on. When the decision changes, refresh the draft before using it.")),

    !canRun ? h("p", { className: "muted" }, "Open a project first (documents use its current checked decision).") : null,
    state && state.error ? h("p", { className: "decision-error" }, displayText(state.error)) : null,
    data && data.ok === false ? h("p", { className: "muted" }, displayText(data.error) || "Run this project first.") : null,

    prov && !prov.any_pinned
      ? h("p", { className: "muted" }, "Source history starts with the first checked run — these labels are not a verdict on a project that has not been pressure-tested yet.")
      : null,
    provenance && provenance.ok ? driftLine(provenance.drift) : null,

    (data && data.ok)
      ? (deliverables.length
          ? h("ul", { className: "deliverable-list" },
              deliverables.map((d) => deliverableRow(d, { canRun, busyName, results, onGenerate: generate,
                busyEditorial, editorialResults, onEditorial: shapeForAudience,
                provenanceByName, onPreview, onCheckDraft })))
          : h(EmptyState, { text: "No document designs are declared for this scenario." }))
      : null,

    busy ? h("p", { className: "muted" }, "Loading…") : null,

    liveMode
      ? h("div", { className: "deliverable-actions" },
          h("div", { className: "deliverable-actions-copy" },
            h("strong", null, "Create the current document set"),
            h("p", null, readyCount
              ? `${readyCount} document design${readyCount === 1 ? " can" : "s can"} assemble a checked draft.`
              : "No document designs are ready to create yet.")),
          h("div", { className: "deliverable-actions-buttons" },
            onManageDocuments
              ? h("button", { type: "button", className: "chip ghost", onClick: () => onManageDocuments() }, "Manage document designs")
              : null,
            h("button", { type: "button", className: `chip primary ${produce && produce.running ? "is-busy" : ""}`,
              disabled: !canRun || !readyCount || (produce && produce.running), onClick: produceAll,
              title: "Create every document that is ready from the same checked decision state" },
              produce && produce.running ? "Creating…" : "Create ready drafts")),
          produceResultLine(produce, onPreview, onCheckDraft))
      : null);
}
