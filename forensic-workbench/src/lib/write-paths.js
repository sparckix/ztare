// Write-path / template helpers extracted from main.js (behavior-preserving).
// Pure functions that compute project write paths from contracts and items.

import { writePathLabel } from "../design-system.js";

export function formatWorkbenchTemplate(template, values = {}) {
  return String(template || "").replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key) => String(values[key] || ""));
}

export function formatWriteTemplateItems(contract, values = {}, fallbackTemplates = []) {
  const displayTemplates = Array.isArray(contract && contract.display_write_path_templates)
    ? contract.display_write_path_templates
    : [];
  if (displayTemplates.length) {
    return displayTemplates
      .map((item) => ({
        label: item.label || writePathLabel(item.path_template || item.path || item.template),
        path: formatWorkbenchTemplate(item.path_template || item.path || item.template, values)
      }))
      .filter((item) => item.path);
  }
  return fallbackTemplates
    .map((template) => formatWorkbenchTemplate(template, values))
    .filter(Boolean)
    .map((path) => ({ label: writePathLabel(path), path }));
}

export function writePathsFromItems(items) {
  return (Array.isArray(items) ? items : [])
    .map((item) => String((item && item.path) || item || "").trim())
    .filter(Boolean);
}

export function receiptPathFromWriteItems(items, fragment) {
  const needle = String(fragment || "").toLowerCase();
  return writePathsFromItems(items).find((path) => path.toLowerCase().includes(needle)) || "";
}

export function workspaceDirForProject(project) {
  return project ? `projects/${project}/workspace` : "";
}

export function stampedPayloadPattern(snapshot, rowKey, kind) {
  const workspaceDir = workspaceDirForProject((snapshot && snapshot.project) || "");
  return workspaceDir && rowKey ? `${workspaceDir}/forensic_workbench_applied/<timestamp>_${rowKey}_${kind}_<hash>.json` : "";
}
