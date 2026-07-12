import React from "react";
import { RefreshCw } from "lucide-react";
import {
  displayText, Block, EmptyState, StatusLine,
  ScenarioSurface, ScenarioGrid, ScenarioColumn, ScenarioList, ScenarioListItem,
} from "../design-system.js";

const h = React.createElement;

// PM is a scenario contribution, not a Workbench section. This panel composes
// the core decision/agenda carriers and the governed deliverable read model.
export const scenarioPanel = Object.freeze({
  id: "pm-decision-kit",
  host: "results",
  label: "PM decision kit",
  description: "A compact PM view of the current decision, next test, and checked handoffs.",
  contract: {
    schema: "plugin_contribution_contract_v1",
    carriers: ["decision_state", "test_agenda", "deliverable_bindings"],
    actions: [
      { id: "refresh", mode: "read" },
      { id: "open-decision-test", mode: "navigate" },
      { id: "open-handoffs", mode: "navigate" },
    ],
  },
});

const ARTIFACTS = [
  { name: "leadership_packet", label: "Leadership brief", description: "Executive claim, evidence, scope, risks, and what would change the call." },
  { name: "roadmap_backing", label: "Roadmap with backing", description: "Roadmap claims with recorded dependencies, risks, and resequencing triggers." },
  { name: "bet_registry", label: "Decision-test register", description: "Open tests and their settlement conditions from the same decision agenda." },
  { name: "tradeoff_register", label: "Trade-off register", description: "Tensions, constraints, and the claims they put under pressure." },
];

function coreDecision(decision) {
  const result = (decision && decision.result) || decision || {};
  return (result && result.decision_state) || result || {};
}

function coreAgenda(agenda) {
  const result = (agenda && agenda.result) || agenda || {};
  return (result && (result.agenda || result.test_agenda)) || [];
}

function standingTone(status) {
  const value = String(status || "").toUpperCase();
  if (value === "SUPPORTED") return "ok";
  if (value === "REFUTED") return "danger";
  return "warn";
}

function shortText(value, limit = 190) {
  const text = displayText(value || "").replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 1).trim()}…` : text;
}

function handoffStatus(row, loading) {
  if (loading) return { tone: "neutral", label: "checking" };
  if (!row) return { tone: "neutral", label: "not available" };
  if (row.stale) return { tone: "warn", label: "refresh" };
  if (row.generated) return { tone: "ok", label: "current" };
  if (row.status === "composable") return { tone: "neutral", label: "can assemble" };
  if (row.status === "needs_content") return { tone: "warn", label: "needs evidence" };
  if (row.status === "ungoverned") return { tone: "danger", label: "blocked by backing" };
  return { tone: "neutral", label: displayText(row.status || "waiting") };
}

export function PMDecisionKit({ project, liveMode, decision, agenda, scenarioConfig, onDecisionRefresh, onAgendaRefresh, onOpenDetail }) {
  const [state, setState] = React.useState({ running: false, data: null, error: "" });

  const scenarioName = String((scenarioConfig && scenarioConfig.name) || "");
  const artifactDescriptors = ((scenarioConfig && scenarioConfig.deliverable_specs) || []).length
    ? scenarioConfig.deliverable_specs.map((spec) => ({
        name: spec.name,
        label: spec.label || spec.name,
        audience: spec.audience || "",
        description: spec.description || spec.presentation_brief || "Scenario handoff from the current decision.",
      }))
    : ARTIFACTS;

  const load = React.useCallback(async () => {
    if (!liveMode || !project) return;
    setState((current) => ({ ...current, running: true, error: "" }));
    try {
      const response = await fetch("/api/scenario-deliverables", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ project, scenario: scenarioName }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "deliverables unavailable");
      setState({ running: false, data, error: "" });
    } catch (error) {
      setState((current) => ({ ...current, running: false, error: String(error.message || error) }));
    }
  }, [project, liveMode, scenarioName]);

  React.useEffect(() => { load(); }, [project, liveMode, scenarioName]); // eslint-disable-line

  const refresh = () => {
    load();
    if (onDecisionRefresh) onDecisionRefresh();
    if (onAgendaRefresh) onAgendaRefresh();
  };

  const stateData = state.data || {};
  const rowsByName = Object.fromEntries((stateData.deliverables || []).map((row) => [row.name, row]));
  const deliverableRows = artifactDescriptors.map((descriptor) => rowsByName[descriptor.name]).filter(Boolean);
  const staleCount = deliverableRows.filter((row) => row.stale).length;
  const currentCount = deliverableRows.filter((row) => row.generated && !row.stale).length;
  const readyCount = deliverableRows.filter((row) => row.status === "composable" && !row.stale).length;
  const compiled = coreDecision(decision);
  const next = coreAgenda(agenda).find((row) => row && row.test) || null;
  const hasProject = liveMode && !!project;
  const status = String(compiled.status || "").toUpperCase();
  const headline = compiled.headline || compiled.reason || (status ? displayText(status) : "Decision state is loading");
  const packetDecision = stateData.decision || {};
  const packetStatus = String(packetDecision.status || "").toUpperCase();
  const decisionBlocked = packetStatus === "BLOCKED";
  const handoffTone = staleCount || decisionBlocked ? "warn" : "ok";

  return h(Block, {
    title: "PM decision kit",
    lead: "A scenario view over the current decision: see the call, choose the next test, and prepare only current handoffs.",
    actions: h("button", { type: "button", className: `icon-button ${state.running ? "is-busy" : ""}`, disabled: !hasProject || state.running,
      onClick: refresh, title: "Refresh the decision kit", "aria-label": "Refresh PM decision kit" }, h(RefreshCw, { size: 16, "aria-hidden": "true" })),
  },
    !hasProject ? h(EmptyState, { text: "Open a project to compile the PM decision kit." }) : null,
    state.error ? h("p", { className: "decision-error", role: "alert" }, displayText(state.error)) : null,
    hasProject
      ? h(React.Fragment, null,
          h(ScenarioSurface, null,
            h("div", { className: "scenario-surface-head" },
              h("span", { className: "eyebrow" }, "Current call"),
              h(StatusLine, { tone: standingTone(status) }, status ? displayText(status) : "loading")),
            h("strong", null, shortText(headline, 240)),
            compiled.reason && compiled.reason !== headline ? h("p", null, shortText(compiled.reason, 260)) : null),
          h(ScenarioGrid, null,
            h(ScenarioColumn, { eyebrow: "Next decision move" },
              next
                ? h(React.Fragment, null,
                    h("strong", null, shortText(next.test, 180)),
                    h("small", null, [
                      next.flips_crisp ? "could change the decision" : next.status_change ? "could change the standing" : "decision effect still bounded",
                      next.cost != null ? `declared effort ${next.cost}` : "effort not declared",
                      next.on_frontier ? "best tradeoff" : "",
                    ].filter(Boolean).join(" · ")),
                    onOpenDetail ? h("button", { type: "button", className: "text-link", onClick: () => onOpenDetail("review", "Things to review") }, "Open the test →") : null)
                : h("p", { className: "muted" }, "No admitted next test is available yet.")),
            h(ScenarioColumn, {
              eyebrow: "Decision posture",
              title: !packetDecision.fingerprint ? "Waiting for decision state" : decisionBlocked ? "Decision still blocked" : "Decision current",
              description: !packetDecision.fingerprint
                ? "Handoffs stay blocked until the decision is readable."
                : decisionBlocked
                  ? `${(stateData.compose_now || []).length} handoff${(stateData.compose_now || []).length === 1 ? " can" : "s can"} assemble as checked drafts, but unresolved work still prevents a reliance-ready handoff.`
                  : `${(stateData.compose_now || []).length} handoff${(stateData.compose_now || []).length === 1 ? " can" : "s can"} assemble from the current decision state.` })),
          h(ScenarioSurface, { tone: staleCount || decisionBlocked ? "warn" : "soft" },
            h("div", { className: "scenario-surface-head" },
              h("span", { className: "eyebrow" }, "PM handoffs"),
              h(StatusLine, { tone: handoffTone }, staleCount ? `${staleCount} need refresh` : decisionBlocked ? "decision blocked" : "current record")),
            h("strong", null, `${artifactDescriptors.length} handoff design${artifactDescriptors.length === 1 ? "" : "s"} on this scenario`),
            h("p", null, staleCount
              ? `${staleCount} handoff${staleCount === 1 ? " is" : "s are"} older than the current decision. Refresh from the Verdict before sharing.`
              : currentCount
                ? `${currentCount} current handoff${currentCount === 1 ? " is" : "s are"} already composed${readyCount ? `; ${readyCount} more can compose now` : ""}.`
                : "Assemble the handoff set from the Verdict to capture the current decision record."),
            h(ScenarioList, null,
              artifactDescriptors.map((descriptor) => {
                const row = rowsByName[descriptor.name];
                const handoff = handoffStatus(row, state.running);
                return h(ScenarioListItem, { key: descriptor.name, className: row && row.stale ? "is-stale" : "" },
                  h("div", { className: "scenario-list-item-head" },
                    h("div", { className: "scenario-list-item-title" }, h("strong", null, displayText(descriptor.label))),
                    h(StatusLine, { tone: handoff.tone }, handoff.label)),
                  h("p", null, shortText(descriptor.description, 150)),
                  descriptor.audience ? h("span", { className: "scenario-list-item-meta" }, `For ${displayText(descriptor.audience)}`) : null);
              })),
            onOpenDetail ? h("button", { type: "button", className: "text-link", onClick: () => onOpenDetail("save", "Report readiness") }, "Open handoffs in Verdict →") : null),
          state.running ? h("p", { className: "muted" }, "Checking the current handoffs…") : null)
      : null);
}

export default PMDecisionKit;
