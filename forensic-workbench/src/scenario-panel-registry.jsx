import React from "react";

const h = React.createElement;
const MODULES = import.meta.glob("./scenario-panels/*.jsx", { eager: true });
const HOSTS = new Set(["results"]);
const CONTRACT = "plugin_contribution_contract_v1";
const ACTION_MODES = new Set(["read", "write", "navigate"]);

export function discoverScenarioPanels(modules = MODULES) {
  const registry = {};
  const catalog = [];
  const diagnostics = [];
  Object.entries(modules || {}).sort(([left], [right]) => left.localeCompare(right)).forEach(([source, mod]) => {
    const metadata = (mod && mod.scenarioPanel) || {};
    const id = String(metadata.id || "").trim();
    const host = String(metadata.host || "").trim();
    const Component = mod && mod.default;
    const contract = metadata.contract && typeof metadata.contract === "object" ? metadata.contract : {};
    const carriers = Array.isArray(contract.carriers)
      ? contract.carriers.map((value) => String(value || "").trim()).filter(Boolean)
      : [];
    const actions = Array.isArray(contract.actions) ? contract.actions : [];
    const contractValid = contract.schema === CONTRACT
      && carriers.length > 0
      && actions.every((action) => action && /^[a-z0-9][a-z0-9-]*$/.test(String(action.id || ""))
        && ACTION_MODES.has(String(action.mode || "")));
    const ref = `${host}:${id}`;
    if (!/^[a-z0-9][a-z0-9-]*$/.test(id) || !HOSTS.has(host) || typeof Component !== "function" || !contractValid) {
      diagnostics.push({ source, error: contractValid
        ? "panel needs a default React component, a kebab-case id, and a supported host"
        : `panel needs ${CONTRACT}, at least one carrier, and typed read/write/navigate actions` });
      return;
    }
    if (registry[ref]) {
      diagnostics.push({ source, error: `duplicate panel ref ${ref}` });
      return;
    }
    const entry = {
      ref, id, host, source,
      label: String(metadata.label || id),
      description: String(metadata.description || ""),
      contract: { schema: contract.schema, carriers, actions },
      Component,
    };
    registry[ref] = entry;
    catalog.push({ ref, id, host, source, label: entry.label, description: entry.description, contract: entry.contract });
  });
  return { registry, catalog, diagnostics };
}

export const scenarioPanelDiscovery = discoverScenarioPanels();

export function contributedScenarioPanels(scenarios, selectedScenario, host, props) {
  const scenario = (scenarios || []).find((row) => row && row.name === selectedScenario);
  return ((scenario && scenario.workbench_panels) || [])
    .map((panelRef) => {
      const entry = scenarioPanelDiscovery.registry[String(panelRef || "")];
      return entry && entry.host === host
        ? h(entry.Component, { key: `scenario-panel-${entry.ref}`, scenarioConfig: scenario, ...props })
        : null;
    })
    .filter(Boolean);
}
